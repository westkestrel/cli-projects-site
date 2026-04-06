import unittest
from os.path import join
from scan import config, Config, Folder, TestableFolder, Project, Library, normalize_date_string

class TestDateConversion(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalize_date_string('2026-02-14'), '2026/02/14')
        self.assertEqual(normalize_date_string('2026/02/14'), '2026/02/14')
        self.assertEqual(normalize_date_string('2026-02-14T12:30:00Z'), '2026/02/14')
        self.assertEqual(normalize_date_string(60*60*24*5), '1970/01/05')

class TestFolder(unittest.TestCase):

    def test_init(self):
        self.assertNotEqual(config.root, '')
        path = join(config.root, '2026/MyProject')
        f = Folder(path)
        self.assertEqual(f.rootpath, config.root)
        self.assertEqual(f.abspath, path)
        self.assertEqual(f.relpath, '2026/MyProject')
        
    def test_scan(self):
        path = join(config.root, '2026/MyProject')
        day = 60*60*24
        f = TestableFolder(path, {
            '2026/MyProject': [day * 5, day * 5],
            '2026/MyProject/README.md': [day * 6, day * 10],
        })
        d = f.scan_for_project_metadata()
        self.assertEqual(d['path'], '2026/MyProject') # relative path
        self.assertEqual(d['name'], 'MyProject')
        self.assertEqual(d['commenced'], '1970/01/05')
        self.assertEqual(d['completed'], '1970/01/10')
        self.assertEqual(d['newest'], 'README.md')
        self.assertEqual(d['type'], None)
        self.assertEqual(d['status'], None)
        
    def test_scan_website(self):
        path = join(config.root, '2026/www.MyProject.com')
        f = TestableFolder(path, {
            '2026/www.MyProject.com': [0, 0],
            '2026/www.MyProject.com/README.md': [0, 0],
        })
        d = f.scan_for_project_metadata()
        self.assertEqual(d['type'], 'Website')
        
    def test_scan_react_app(self):
        path = join(config.root, '2026/MyProject')
        f = TestableFolder(path, {
            '2026/MyProject': [0, 0],
            '2026/MyProject/README.md': [0, 0],
            '2026/MyProject/package.json': [0, 0],
        })
        d = f.scan_for_project_metadata()
        self.assertEqual(d['type'], 'Web App')

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

    def test_get_project(self):
        lib = Library()
        c = Config(None)
        p1 = lib.get_project(join(c.root, '2026/MyProject'))
        self.assertEqual(p1.path, join(c.root, '2026/MyProject'))
        p2 = lib.get_project(join(c.root, '2026/MyProject/README.txt'))
        self.assertEqual(p2.path, join(c.root, '2026/MyProject'))
    
