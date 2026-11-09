"""Shared coordinate constraints for force fields and geometric contact cleanup.

Rigid bodies use rotations/translations, never stiff bond penalties. The core
is the reference frame; bonded ligand branches form one body.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

SCOPES = {
    'core_fixed': '코어만 고정',
    'all': '모든 원자 움직이기',
    'core_only': '코어만 움직이기',
    'rigid': '코어·리간드 모양만 고정',
}


def scope_plan(project, scope='core_fixed', respect_fixed=True):
    if scope not in SCOPES:
        raise ValueError('알 수 없는 계산 범위입니다.')
    atoms = project['atoms']
    core = {a['id'] for a in atoms if a.get('core')}
    ids = {a['id'] for a in atoms}
    if not ids:
        raise ValueError('계산할 원자가 없습니다.')
    if scope != 'all' and not core:
        raise ValueError('코어로 지정된 원자가 없습니다. 코어 템플릿을 사용하거나 전체 범위를 선택하세요.')
    manual = {a['id'] for a in atoms if respect_fixed and a.get('fixed')}
    fixed = core.copy() if scope in ('core_fixed', 'rigid') else ids-core if scope == 'core_only' else set()
    fixed |= manual
    graph = {i: set() for i in ids-core}
    for b in project['bonds']:
        i, j = b['a'], b['b']
        if i in graph and j in graph:
            graph[i].add(j); graph[j].add(i)
    groups = []
    unseen = set(graph)
    while unseen:
        start = min(unseen); group = {start}; todo = [start]; unseen.remove(start)
        while todo:
            for i in graph[todo.pop()] & unseen:
                unseen.remove(i); group.add(i); todo.append(i)
        groups.append(sorted(group))
    locked_groups = []
    if scope == 'rigid':
        for group in groups:
            if manual.intersection(group):
                fixed.update(group); locked_groups.append(group)
    moving = ids-fixed
    return dict(scope=scope, label=SCOPES[scope], fixedIds=sorted(fixed), movingIds=sorted(moving),
                coreIds=sorted(core), groups=groups, lockedGroups=locked_groups,
                manualFixedIds=sorted(manual), respectFixed=bool(respect_fixed),
                rigid=scope == 'rigid', fixedCount=len(fixed), movingCount=len(moving))


class Coordinates:
    """Map free Cartesian coordinates or exact rigid poses to the full structure."""
    def __init__(self, project, plan):
        self.initial = np.array([[a[k] for k in ('x', 'y', 'z')] for a in project['atoms']], dtype=float)
        index = {a['id']:i for i,a in enumerate(project['atoms'])}
        self.moving = np.array([index[i] for i in plan['movingIds']], dtype=int)
        self.rigid = plan['rigid']; self.bodies = []
        if self.rigid:
            movable = set(plan['movingIds'])
            for group in plan['groups']:
                if not set(group) <= movable: continue
                ix = np.array([index[i] for i in group], dtype=int)
                center = self.initial[ix].mean(axis=0)
                self.bodies.append((ix, center, self.initial[ix]-center))
            self.x0 = np.zeros(6*len(self.bodies))
        else:
            self.x0 = self.initial[self.moving].ravel().copy()

    def decode(self, values):
        points = self.initial.copy()
        if self.rigid:
            for k,(ix,center,local) in enumerate(self.bodies):
                pose = values[6*k:6*k+6]
                points[ix] = local @ Rotation.from_rotvec(pose[3:]).as_matrix().T + center + pose[:3]
        else:
            points[self.moving] = values.reshape(-1,3)
        return points

    def gradient(self, values, gradient):
        if not self.rigid: return gradient[self.moving].ravel()
        result = np.zeros_like(values)
        # Derivative of only a 3x3 rotation; no repeated chemistry evaluations.
        for k,(ix,center,local) in enumerate(self.bodies):
            result[6*k:6*k+3] = gradient[ix].sum(axis=0)
            v = values[6*k+3:6*k+6]
            for j in range(3):
                dv = np.zeros(3); dv[j] = 1.e-6
                derivative = (Rotation.from_rotvec(v+dv).as_matrix()-Rotation.from_rotvec(v-dv).as_matrix())/2.e-6
                result[6*k+3+j] = np.sum(gradient[ix]*(local @ derivative.T))
        return result


def minimize_coordinates(project, plan, energy_gradient, steps=500, cancel=None, progress=None):
    if isinstance(steps, bool) or not isinstance(steps, (int, np.integer)) or not 1 <= steps <= 10000:
        raise ValueError('최대 반복 수는 1–10000입니다.')
    coordinates = Coordinates(project, plan)
    if not len(coordinates.x0): raise ValueError('이 범위에서 움직일 원자가 없습니다. 개별 고정 설정을 확인하세요.')
    iteration = 0
    def check():
        if cancel is not None and cancel.is_set(): raise InterruptedError('계산을 취소했습니다.')
    def objective(values):
        check()
        energy, gradient = energy_gradient(coordinates.decode(values))
        grad = coordinates.gradient(values, gradient)
        if not np.isfinite(energy) or not np.isfinite(grad).all():
            raise ValueError('유한하지 않은 에너지/기울기입니다. 구조를 확인하세요.')
        return float(energy), grad
    def callback(values):
        nonlocal iteration
        check(); iteration += 1
        if progress: progress(dict(message=f'최적화 반복 {iteration}/{steps} (최대 반복 예산)', percent=95*iteration/steps))
    check()
    if progress: progress(dict(message='좌표·제약 준비', percent=0))
    before = objective(coordinates.x0)[0]
    result = minimize(objective, coordinates.x0, jac=True, method='L-BFGS-B', callback=callback,
                      options=dict(maxiter=int(steps), maxls=40, ftol=1.e-10, gtol=1.e-5))
    check()
    after = objective(result.x)[0]
    if after > before + 1.e-7:
        raise ValueError('목적함수가 증가하여 계산 결과를 적용하지 않았습니다.')
    points = coordinates.decode(result.x)
    for i in coordinates.moving:
        project['atoms'][i].update(zip(('x','y','z'),map(float, points[i])))
    return dict(before=before, after=after, converged=bool(result.success), iterations=int(result.nit),
                termination=str(result.message), scope=plan['scope'], fixedCount=plan['fixedCount'],
                movingCount=plan['movingCount'], respectFixed=plan['respectFixed'])


class ContactObjective:
    """Contact penalty + initial bond/1-3 restraints, in arbitrary score units.

Same excluded pairs, core-core exclusion and cutoff as the contact inspector.
Spatial neighbors are rebuilt per evaluation, avoiding a dense N x N matrix.
"""
    def __init__(self, project, radius, criteria):
        self.initial = np.array([[a[k] for k in ('x','y','z')] for a in project['atoms']], dtype=float)
        self.core = np.array([bool(a.get('core')) for a in project['atoms']])
        ix = {a['id']:i for i,a in enumerate(project['atoms'])}
        graph = [set() for a in project['atoms']]
        bonds = set()
        for b in project['bonds']:
            i,j = ix[b['a']],ix[b['b']]; graph[i].add(j); graph[j].add(i); bonds.add(tuple(sorted((i,j))))
        excluded = set(bonds)
        for i,ns in enumerate(graph):
            for j in ns:
                excluded.update(tuple(sorted((i,k))) for k in graph[j] if i != k)
        self.excluded = excluded
        self.pairs = np.array(sorted(excluded),dtype=int).reshape(-1,2)
        self.targets = np.linalg.norm(self.initial[self.pairs[:,0]]-self.initial[self.pairs[:,1]],axis=1)
        self.weights = np.array([20. if tuple(pair) in bonds else 2. for pair in self.pairs])
        self.radii = np.array([[radius(a['element'],'vdw'),radius(a['element'])] for a in project['atoms']])
        self.criteria = criteria
        self.maxcut = float(criteria['minimum']) if criteria['mode']=='minimum' else float(max(2*self.radii[:,0].max()*criteria['vdw'],2*self.radii[:,1].max()*criteria['covalent']))

    def __call__(self, points):
        gradient = np.zeros_like(points); energy = 0.
        def accumulate(pairs, residual, weight):
            nonlocal energy
            if not len(pairs): return
            i,j = pairs[:,0],pairs[:,1]; delta=points[i]-points[j]; distance=np.linalg.norm(delta,axis=1)
            direction=delta/np.maximum(distance[:,None],1.e-12)
            # At exact overlap choose a deterministic separating direction.
            direction[distance<1.e-12] = (1.,0.,0.)
            force=(2*weight*residual)[:,None]*direction
            np.add.at(gradient,i,force); np.add.at(gradient,j,-force)
            energy += float(np.sum(weight*residual**2))
        pairs=cKDTree(points).query_pairs(self.maxcut,output_type='ndarray')
        if len(pairs):
            mask=np.array([tuple(pair) not in self.excluded and not(self.core[pair[0]] and self.core[pair[1]]) for pair in pairs])
            pairs=pairs[mask]
        if len(pairs):
            i,j=pairs[:,0],pairs[:,1]; c=self.criteria
            cuts=float(c['minimum']) if c['mode']=='minimum' else np.maximum((self.radii[i,0]+self.radii[j,0])*c['vdw'],(self.radii[i,1]+self.radii[j,1])*c['covalent'])
            residual=np.minimum(0.,np.linalg.norm(points[i]-points[j],axis=1)-cuts)
            accumulate(pairs,residual,np.ones(len(pairs)))
        if len(self.pairs):
            residual=np.linalg.norm(points[self.pairs[:,0]]-points[self.pairs[:,1]],axis=1)-self.targets
            accumulate(self.pairs,residual,self.weights)
        # Small displacement restraint prevents unconnected fragments drifting away.
        delta=points-self.initial; energy+=.001*float(np.sum(delta*delta)); gradient+=.002*delta
        return energy,gradient
