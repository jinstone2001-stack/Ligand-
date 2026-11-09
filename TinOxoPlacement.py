"""Core mass frame and geometric interior exclusion for new ligand poses.

This is an initial-placement rule, separate from force-field energy. A convex
envelope deliberately fills a hollow core's cavity, where contact-only scores
can otherwise prefer an inward ligand. Coordinates and bonds are never bent.
"""
import numpy as np
from rdkit.Chem import GetPeriodicTable
from scipy.spatial import ConvexHull, QhullError


def atom_mass(atom):
    table=GetPeriodicTable();number=table.GetAtomicNumber(atom['element'])
    isotope=int(atom.get('isotope',0))
    mass=table.GetMassForIsotope(number,isotope) if isotope else 0.
    return mass if mass>0 else table.GetAtomicWeight(number)


def core_atoms(project,parents):
    """Use the connected core belonging to the hosts, not another cluster."""
    atoms={a['id']:a for a in project['atoms']};core={i for i,a in atoms.items() if a.get('core')}
    if not core:return []
    graph={i:set() for i in atoms}
    for b in project['bonds']:graph[b['a']].add(b['b']);graph[b['b']].add(b['a'])
    groups=[];unseen=core.copy()
    while unseen:
        group={min(unseen)};todo=list(group);unseen-=group
        while todo:
            new=graph[todo.pop()] & unseen;group.update(new);unseen-=new;todo.extend(new)
        groups.append(group)
    hits=set()
    for parent in parents:
        seen=set();front={parent}
        while front:
            reached=front & core
            if reached:hits.update(reached);break
            seen.update(front);front={j for i in front for j in graph[i]}-seen
    if hits:chosen=set().union(*(g for g in groups if g & hits))
    else:
        def distance(group):
            members=[atoms[j] for j in sorted(group)]
            center=np.average([[a[k] for k in ('x','y','z')] for a in members],axis=0,weights=[atom_mass(a) for a in members])
            return min(np.linalg.norm(np.array([atoms[i][k] for k in ('x','y','z')])-center) for i in parents)
        chosen=min(groups,key=distance)
    return [a for a in project['atoms'] if a['id'] in chosen]


class CorePlacement:
    """Reject ligand atoms or internal bonds entering a core envelope.

    A 0.05 Å inward tolerance avoids treating a face touch as penetration.
    Planar cores have a +/-0.75 Å slab; line/point cores use the analogous box.
    """
    depth=.05
    def __init__(self,project,parents,new_atoms,new_bonds):
        core=core_atoms(project,parents);self.center=None;self.equations=None;self.kind='none';self.ids=[]
        index={a['id']:i for i,a in enumerate(new_atoms)}
        self.bonds=np.array([(index[b['a']],index[b['b']]) for b in new_bonds if b['a'] in index and b['b'] in index],dtype=int).reshape(-1,2)
        old={a['id']:a for a in project['atoms']};self.external=[]
        for b in new_bonds:
            for i,j in ((b['a'],b['b']),(b['b'],b['a'])):
                if i in index and j not in index and j in old and not old[j].get('core'):
                    self.external.append((index[i],np.array([old[j][k] for k in ('x','y','z')])))
        if not core:return
        self.ids=[a['id'] for a in core]
        self.center=np.average([[a[k] for k in ('x','y','z')] for a in core],axis=0,weights=[atom_mass(a) for a in core])
        heavy=[a for a in core if a['element']!='H'] or core
        points=np.array([[a[k] for k in ('x','y','z')] for a in heavy]);origin=points.mean(0)
        _,singular,basis=np.linalg.svd(points-origin,full_matrices=len(points)<3)
        rank=int(np.sum(singular>max(1.e-8,float(singular.max())*1.e-8)))
        local=(points-origin)@basis.T
        try:
            if rank<2:raise QhullError('Use a finite box for a line/point core')
            hull=ConvexHull(local[:,:rank]);normals=hull.equations[:,:rank]@basis[:rank]
            offsets=hull.equations[:,rank]-normals@origin;self.kind='convex-hull' if rank==3 else 'planar-hull'
            equations=np.column_stack((normals,offsets)).tolist()
            for axis in range(rank,3):
                n=basis[axis]
                equations.extend([list(n)+[-float(n@origin)-.75],list(-n)+[float(n@origin)-.75]])
        except QhullError:
            self.kind='core-box';equations=[]
            for axis in range(3):
                n=basis[axis];lo=float(local[:,axis].min());hi=float(local[:,axis].max())
                if axis>=rank:lo-=.75;hi+=.75
                equations.extend([list(n)+[-float(n@origin)-hi],list(-n)+[float(n@origin)+lo]])
        self.equations=np.array(equations)

    def outward(self,point):
        if self.center is None:return None
        vector=np.asarray(point)-self.center;length=np.linalg.norm(vector)
        return vector/length if length>1.e-8 else None

    def safe(self,points):
        points=np.asarray(points)
        if not np.isfinite(points).all():return False
        if self.equations is None:return True
        values=points@self.equations[:,:3].T+self.equations[:,3]+self.depth
        if np.any(np.all(values<=0.,axis=1)):return False
        if not len(self.bonds) and not self.external:return True
        start=values[self.bonds[:,0]];slope=values[self.bonds[:,1]]-start
        if self.external:
            extra=values[[i for i,point in self.external]]
            ends=np.array([point for i,point in self.external])@self.equations[:,:3].T+self.equations[:,3]+self.depth
            start=np.concatenate((start,extra));slope=np.concatenate((slope,ends-extra))
        crossing=np.zeros_like(start);np.divide(-start,slope,out=crossing,where=np.abs(slope)>1.e-12)
        lower=np.maximum(0.,np.max(np.where(slope < -1.e-12,crossing,-np.inf),axis=1))
        upper=np.minimum(1.,np.min(np.where(slope > 1.e-12,crossing,np.inf),axis=1))
        parallel_outside=np.any((np.abs(slope)<=1.e-12)&(start>0.),axis=1)
        return not np.any((lower<upper-1.e-9)&~parallel_outside)

    def record(self):
        return dict(policy='core-outward-5.2' if self.center is not None else 'local-valence',
                    coreCenterOfMass=self.center.tolist() if self.center is not None else None,
                    coreIds=self.ids,envelope=self.kind,interiorTolerance_A=self.depth)
