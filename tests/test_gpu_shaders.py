"""Optional native Mesa EGL/GLES pixel checks. This is not browser/GPU FPS QA."""
import ctypes as ct
import ctypes.util
from pathlib import Path
import re
import unittest

EGL=ctypes.util.find_library('EGL')


@unittest.skipUnless(EGL,'native EGL is unavailable (optional shader check)')
class ShaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.egl=ct.CDLL(EGL)
        def bind(name,ret,*args):
            fn=getattr(cls.egl,name);fn.restype=ret;fn.argtypes=args;return fn
        cls.proc=bind('eglGetProcAddress',ct.c_void_p,ct.c_char_p)
        address=cls.proc(b'eglGetPlatformDisplayEXT')
        if not address:raise unittest.SkipTest('surfaceless EGL unavailable')
        getdisplay=ct.CFUNCTYPE(ct.c_void_p,ct.c_uint,ct.c_void_p,ct.POINTER(ct.c_int))(address)
        cls.display=getdisplay(0x31DD,None,None)
        cls.initialize=bind('eglInitialize',ct.c_uint,ct.c_void_p,ct.POINTER(ct.c_int),ct.POINTER(ct.c_int))
        if not cls.initialize(cls.display,None,None):raise unittest.SkipTest('surfaceless EGL cannot initialize')
        cls.terminate=bind('eglTerminate',ct.c_uint,ct.c_void_p)
        bind('eglBindAPI',ct.c_uint,ct.c_uint)(0x30A0)
        attribs=(ct.c_int*15)(0x3033,1,0x3040,4,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3025,16,0x3038)
        config=ct.c_void_p();count=ct.c_int()
        choose=bind('eglChooseConfig',ct.c_uint,ct.c_void_p,ct.POINTER(ct.c_int),ct.POINTER(ct.c_void_p),ct.c_int,ct.POINTER(ct.c_int))
        if not choose(cls.display,attribs,ct.byref(config),1,ct.byref(count)) or not count.value:raise unittest.SkipTest('GLES2 pbuffer config unavailable')
        create=bind('eglCreatePbufferSurface',ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.POINTER(ct.c_int))
        cls.surface=create(cls.display,config,(ct.c_int*5)(0x3057,128,0x3056,128,0x3038))
        create=bind('eglCreateContext',ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.POINTER(ct.c_int))
        cls.context=create(cls.display,config,None,(ct.c_int*3)(0x3098,2,0x3038))
        cls.makecurrent=bind('eglMakeCurrent',ct.c_uint,ct.c_void_p,ct.c_void_p,ct.c_void_p,ct.c_void_p)
        if not cls.makecurrent(cls.display,cls.surface,cls.surface,cls.context):raise unittest.SkipTest('GLES2 context unavailable')
        cls.sources=dict(re.findall(r'export const (\w+) = `([\s\S]*?)`;', (Path(__file__).resolve().parents[1]/'web/viewer.js').read_text()))
    @classmethod
    def tearDownClass(cls):
        cls.makecurrent(cls.display,None,None,None)
        cls.egl.eglDestroyContext.argtypes=[ct.c_void_p,ct.c_void_p];cls.egl.eglDestroyContext(cls.display,cls.context)
        cls.egl.eglDestroySurface.argtypes=[ct.c_void_p,ct.c_void_p];cls.egl.eglDestroySurface(cls.display,cls.surface)
        cls.terminate(cls.display)
    def gl(self,name,ret,*types):
        addr=self.proc(name.encode())
        if not addr:raise unittest.SkipTest(name+' unavailable')
        return ct.CFUNCTYPE(ret,*types)(addr)
    def program(self,name):
        p=self.gl('glCreateProgram',ct.c_uint)()
        for kind,suffix in ((0x8B31,'VERTEX'),(0x8B30,'FRAGMENT')):
            sh=self.gl('glCreateShader',ct.c_uint,ct.c_uint)(kind);source=ct.c_char_p(self.sources[name+'_'+suffix].encode())
            self.gl('glShaderSource',None,ct.c_uint,ct.c_int,ct.POINTER(ct.c_char_p),ct.c_void_p)(sh,1,ct.byref(source),None)
            self.gl('glCompileShader',None,ct.c_uint)(sh);ok=ct.c_int()
            self.gl('glGetShaderiv',None,ct.c_uint,ct.c_uint,ct.POINTER(ct.c_int))(sh,0x8B81,ct.byref(ok))
            log=ct.create_string_buffer(4096);self.gl('glGetShaderInfoLog',None,ct.c_uint,ct.c_int,ct.c_void_p,ct.c_void_p)(sh,4096,None,log)
            self.assertTrue(ok.value,log.value.decode())
            self.gl('glAttachShader',None,ct.c_uint,ct.c_uint)(p,sh);self.gl('glDeleteShader',None,ct.c_uint)(sh)
        self.gl('glLinkProgram',None,ct.c_uint)(p);ok=ct.c_int();self.gl('glGetProgramiv',None,ct.c_uint,ct.c_uint,ct.POINTER(ct.c_int))(p,0x8B82,ct.byref(ok));self.assertTrue(ok.value,'program link failed')
        return p
    def render(self,name,vertices,spec,stride,count,mode):
        p=self.program(name);self.gl('glUseProgram',None,ct.c_uint)(p)
        def uniform(key,kind,values):
            loc=self.gl('glGetUniformLocation',ct.c_int,ct.c_uint,ct.c_char_p)(p,key.encode())
            if kind=='matrix':self.gl('glUniformMatrix3fv',None,ct.c_int,ct.c_int,ct.c_ubyte,ct.POINTER(ct.c_float))(loc,1,0,(ct.c_float*9)(*values))
            else:self.gl('glUniform'+str(len(values))+('i' if kind=='i' else 'f'),None,ct.c_int,*([ct.c_int if kind=='i' else ct.c_float]*len(values)))(loc,*values)
        uniform('rotation','matrix',[1,0,0,0,1,0,0,0,1]);uniform('center','f',[0,0,0]);uniform('viewport','f',[128,128]);uniform('pan','f',[0,0]);uniform('scale','f',[8]);uniform('depth','f',[30]);uniform('dpr','f',[1]);uniform('selectionColor','f',[0,1,1]);uniform('detail','i',[1])
        buffer=ct.c_uint();self.gl('glGenBuffers',None,ct.c_int,ct.POINTER(ct.c_uint))(1,ct.byref(buffer));self.gl('glBindBuffer',None,ct.c_uint,ct.c_uint)(0x8892,buffer)
        data=(ct.c_float*len(vertices))(*vertices);self.gl('glBufferData',None,ct.c_uint,ct.c_ssize_t,ct.c_void_p,ct.c_uint)(0x8892,ct.sizeof(data),data,0x88E4)
        for i in range(8):self.gl('glDisableVertexAttribArray',None,ct.c_uint)(i)
        for key,n,offset in spec:
            loc=self.gl('glGetAttribLocation',ct.c_int,ct.c_uint,ct.c_char_p)(p,key.encode());self.assertGreaterEqual(loc,0)
            self.gl('glEnableVertexAttribArray',None,ct.c_uint)(loc);self.gl('glVertexAttribPointer',None,ct.c_uint,ct.c_int,ct.c_uint,ct.c_ubyte,ct.c_int,ct.c_void_p)(loc,n,0x1406,0,stride,ct.c_void_p(offset))
        self.gl('glViewport',None,ct.c_int,ct.c_int,ct.c_int,ct.c_int)(0,0,128,128);self.gl('glClearColor',None,*([ct.c_float]*4))(0,0,0,1);self.gl('glClear',None,ct.c_uint)(0x4000|0x0100)
        self.gl('glDrawArrays',None,ct.c_uint,ct.c_int,ct.c_int)(mode,0,count)
        pixels=(ct.c_ubyte*(128*128*4))();self.gl('glReadPixels',None,ct.c_int,ct.c_int,ct.c_int,ct.c_int,ct.c_uint,ct.c_uint,ct.c_void_p)(0,0,128,128,0x1908,0x1401,pixels)
        error=self.gl('glGetError',ct.c_uint)();self.assertEqual(error,0,hex(error))
        self.gl('glDeleteBuffers',None,ct.c_int,ct.POINTER(ct.c_uint))(1,ct.byref(buffer));self.gl('glDeleteProgram',None,ct.c_uint)(p)
        return lambda x,y:tuple(pixels[(y*128+x)*4:(y*128+x)*4+3])
    def test_point_shader_pixels_and_selection_ring(self):
        pixel=self.render('POINT',[0,0,0,0,0,1,1,1],[('position',3,0),('color',3,12),('radius',1,24),('selected',1,28)],32,1,0)
        self.assertGreater(pixel(64,64)[2],100);self.assertEqual(pixel(74,64),(0,255,255));self.assertEqual(pixel(78,64),(0,0,0))
    def test_bond_shader_pixels(self):
        vertices=[]
        for t,side in ((0,1),(0,-1),(1,1),(1,1),(0,-1),(1,-1)):vertices.extend([-3,0,0,3,0,0,1,0,0,t,side,0])
        pixel=self.render('BOND',vertices,[('position',3,0),('endpoint',3,12),('color',3,24),('fraction',1,36),('side',1,40),('offset',1,44)],48,6,4)
        self.assertEqual(pixel(64,64),(255,0,0));self.assertEqual(pixel(64,68),(0,0,0));self.assertEqual(pixel(35,64),(0,0,0))


if __name__=='__main__':unittest.main()
