import unittest
from os.path import join
from scan import config, Config, Normalizer, Folder, TestableFolder, Project, Library

class TestNormalizer(unittest.TestCase):

    def test_date(self):
        n = Normalizer()
        self.assertEqual(n.date('2026-02-14'), '2026/02/14')
        self.assertEqual(n.date('2026/02/14'), '2026/02/14')
        self.assertEqual(n.date('14-Feb-2026'), '2026/02/14')
        self.assertEqual(n.date('14-February-2026'), '2026/02/14')
        self.assertEqual(n.date('2026-02-14T12:30:00Z'), '2026/02/14')
        self.assertEqual(n.date(60*60*24*5), '1970/01/05')

    def test_key(self):
        n = Normalizer()
        self.assertEqual(n.key('Name'), 'name')
        self.assertEqual(n.key('CreationDate'), 'creation_date')
        self.assertEqual(n.key('creation-date'), 'creation_date')
        
    def test_value(self):
        n = Normalizer()
        self.assertEqual(n.value('MyProject', 'Name'), 'MyProject')
        self.assertEqual(n.value('14-Feb-2026', 'Commenced'), '2026/02/14')
        self.assertEqual(n.value('14-Feb-2026', 'Completed'), '2026/02/14')
        self.assertEqual(n.value('14-Feb-2026', 'Abandoned'), '2026/02/14')
        
    def test_item(self):
        n = Normalizer()
        self.assertEqual(n.item('Name', 'MyProject'), ('name', 'MyProject'))
        self.assertEqual(n.item('Commenced', '14-Feb-2026'), ('commenced', '2026/02/14'))
        self.assertEqual(n.item('Completed', '14-Feb-2026'), ('completed', '2026/02/14'))
        self.assertEqual(n.item('Abandoned', '14-Feb-2026'), ('abandoned', '2026/02/14'))
        
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
        self.assertEqual(d['relpath'], '2026/MyProject') # relative path
        self.assertEqual(d['name'], 'MyProject')
        self.assertEqual(d['commenced'], '1970/01/05')
        self.assertEqual(d['completed'], '1970/01/10')
        self.assertEqual(d['newest_file'], 'README.md')
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

    def test_init_in_project_root(self):
        r = config.root
        path = join(config.root, '2026/MyProject')
        p = Project(path)
        self.assertEqual(p.abspath, path)
        self.assertEqual(p.relpath, '2026/MyProject')
        self.assertEqual(p.get_bucket_name(), '2026')

    def test_init_outside_project_root(self):
        p = Project('/2026/MyProject')
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.relpath, None)
        self.assertEqual(p.get_bucket_name(), '2026')

    def test_scan(self):
        p = Project('/2026/MyProject')
        self.assertEqual(p.name, 'MyProject') # inferred from path in constructor
        p.scan_readme_content('''
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        '''.split('\n'))
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.name, 'MyProject')
        self.assertEqual(p.commenced, '2026/02/14')
        self.assertEqual(p.completed, '2026/03/15')

    def test_scan_without_apply(self):
        p = Project('/2026/MyProject')
        self.assertEqual(p.name, 'MyProject') # inferred from path in constructor
        p.scan_readme_content('''
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        '''.split('\n'), apply=False)
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.name, 'MyProject')
        self.assertEqual(p.commenced, None)
        self.assertEqual(p.completed, None)

    def test_scan_inferred_values(self):
        content = '''
        # My Great Project
        
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        '''
        p = Project('/2026/MyProject')
        p.scan_readme_content(map(str.strip, content.split('\n')[1:]))
        self.assertEqual(p.abspath, '/2026/MyProject')
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
        self.assertEqual(p1.abspath, join(c.root, '2026/MyProject'))
        p2 = lib.get_project(join(c.root, '2026/MyProject/README.txt'))
        self.assertEqual(p2.abspath, join(c.root, '2026/MyProject'))
    
