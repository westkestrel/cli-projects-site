import unittest
from scan import Library, Project

class TestProject(unittest.TestCase):
    def test_scan(self):
        p = Project('/foo/bar')
        p.scan_readme_content('''
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        '''.split('\n'))
        self.assertEqual(p.path, '/foo/bar')
        self.assertEqual(p.name, None)
        self.assertEqual(p.commenced, '2026/02/14')
        self.assertEqual(p.completed, '2026/03/15')

    def test_scan_inferred_values(self):
        content = '''
        # My Great Project
        
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        '''
        p = Project('/foo/bar')
        p.scan_readme_content(map(str.strip, content.split('\n')[1:]))
        self.assertEqual(p.path, '/foo/bar')
        self.assertEqual(p.name, 'My Great Project')
        self.assertEqual(p.commenced, '2026/02/14')
        self.assertEqual(p.completed, '2026/03/15')
        self.assertEqual(p.status, 'Completed')

class TestLibrary(unittest.TestCase):
    def test_regex(self):
        lib = Library()
        self.assertEqual(lib.make_regex('.*, _*, node_modules'), '^(?:[.].*|_.*|node_modules)$')

