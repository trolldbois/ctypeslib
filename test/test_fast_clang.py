import unittest
import ctypes

from util import get_cursor
from util import get_tu
from util import ArchTest
    
'''Compare python sizes with the clang framework.
'''
class CompareSizes(ArchTest):
    ''' Python versus Clang sizeof. Python should always return the same size 
    as the native clang results. ''' 
    def assertSizes(self, name):
        target = get_cursor(self.parser.tu, name)
        self.assertTrue(target is not None, '%s was not found in source'%name )
        _clang = target.type.get_size()
        _python = ctypes.sizeof(getattr(self.namespace,name))
        self.assertEquals( _clang, _python, 
            'Sizes for target: %s Clang:%d Python:%d flags:%s'%(name, _clang, _python, self.parser.flags))

    def assertOffsets(self, name):
        target = get_cursor(self.parser.tu, name).type.get_declaration()
        self.assertTrue(target is not None, '%s was not found in source'%name )
        members = [c.displayname for c in target.get_children() if c.kind.name == 'FIELD_DECL']
        if members == []:
            import code
            code.interact(local=locals())
        _clang_type = target.type
        _python_type = getattr(self.namespace,name)
        # Does not handle bitfield
        for member in members:
            _c_offset = _clang_type.get_offset(member)
            _p_offset = 8*getattr(_python_type, member).offset
            self.assertEquals( _c_offset, _p_offset, 
                'Offsets for target: %s.%s Clang:%d Python:%d flags:%s'%(
                    name, member, _c_offset, _p_offset, self.parser.flags))

    @unittest.skip('')
    def test_simple2(self):
        targets = ['structName', 'structName2','Node','Node2','myEnum',
            'my__quad_t','my_bitfield','mystruct']
        flags = ['-target','i386-linux']
        self.namespace = self.gen('test/data/test-clang3.c', flags)
        for name in targets:
            self.assertSizes(name)

    #@unittest.skip('')
    def test_simple(self):
        targets = ['badaboum', 'you_badaboum', 'big_badaboum', 
            'you_big_badaboum', 'double_badaboum', 'long_double_badaboum',
            'float_badaboum', 'ptr']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.namespace = self.gen('test/data/test-clang0.c', flags)
            for name in targets:
                self.assertSizes(name)

    #@unittest.skip('')
    def test_records(self):
        targets = ['structName', 'structName2','Node','Node2','myEnum',
            'my__quad_t','my_bitfield','mystruct']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.namespace = self.gen('test/data/test-clang1.c', flags)
            for name in targets:
                self.assertSizes(name)
                self.assertOffsets(name)

    #@unittest.skip('')
    def test_includes(self):
        targets = ['int8_t', 'intptr_t', 'intmax_t' ] 
        #no size here ['a','b','c','d','e','f','g','h']
        for flags in [ ['-target','i386-linux'], ['-target','x86_64-linux'] ]:
            self.namespace = self.gen('test/data/test-clang2.c', flags)
            for name in targets:
                self.assertSizes(name)
        





if __name__ == "__main__":
    unittest.main()
