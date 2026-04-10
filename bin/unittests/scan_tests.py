import unittest
from os.path import expanduser, join
from scan import config, Config, PatternRuleGroup, PatternRule, Normalizer, Folder, TestableFolder, Project, Library

class TestConfig(unittest.TestCase):

    def test_regex(self):
        c = Config(None)
        self.assertEqual(c.make_regex('.*, _*, node_modules'), '^(?:[.].*|_.*|node_modules)$')
        
    def test_skip(self):
        c = Config(None)
        self.assertEqual(c.skip_regex, r'^(?:[.].*|_.*|tmp|node_modules|PackageCache|wp-content)$')
        c['skip'] = '.*, tmp'
        self.assertEqual(c.skip_regex, r'^(?:[.].*|tmp)$')

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
        self.assertEqual(n.item('Concluded', '14-Feb-2026'), ('concluded', '2026/02/14'))
        self.assertEqual(n.item('Completed', '14-Feb-2026'), ('completed', '2026/02/14'))
        self.assertEqual(n.item('Abandoned', '14-Feb-2026'), ('abandoned', '2026/02/14'))
        
class TestFolder(unittest.TestCase):

    def test_testable_folder(self):
        root = expanduser(config.projects_root_dir)
        path = '2026/MyProject'
        f = TestableFolder(path, {
            '2026/MyProject': [10, 20],
            '2026/MyProject/README.md': [30, 40],
            '2026/MyProject/package.json': [50, 60],
            '2026/MyProject/src': [70, 80],
            '2026/MyProject/src/App.js': [90, 100],
        })
        self.assertEqual(f.get_ctime(join(root, '2026/MyProject/README.md')), 30)
        self.assertEqual(f.get_mtime(join(root, '2026/MyProject/README.md')), 40)
        self.assertEqual(f.listdir(join(root, '2026/MyProject')), [
            'README.md',
            'package.json',
            'src',
        ])

    def test_init(self):
        self.assertNotEqual(config.projects_root_dir, '')
        root = expanduser(config.projects_root_dir)
        path = join(root, '2026/MyProject')
        f = Folder(path)
        self.assertEqual(f.rootpath, root)
        self.assertEqual(f.abspath, path)
        self.assertEqual(f.relpath, '2026/MyProject')
        
    def test_scan(self):
        root = expanduser(config.projects_root_dir)
        path = join(root, '2026/MyProject')
        day = 60*60*24
        f = TestableFolder(path, {
            '2026/MyProject': [day * 5, day * 5],
            '2026/MyProject/README.md': [day * 6, day * 10],
        })
        d = f.scan_for_project_metadata()
        self.assertEqual(d['abspath'], join(root, '2026/MyProject'))
        self.assertEqual(d['relpath'], '2026/MyProject')
        self.assertEqual(d['name'], 'MyProject')
        self.assertEqual(d['commenced'], '1970/01/05')
        self.assertEqual(d['concluded'], '1970/01/10')
        self.assertEqual(d['newest_file'], 'README.md')
        self.assertEqual(d['type'], None)
        self.assertEqual(d['status'], None)
        
class TestProject(unittest.TestCase):

    def test_init_in_project_root(self):
        root = expanduser(config.projects_root_dir)
        path = join(root, '2026/MyProject')
        p = Project(path)
        self.assertEqual(p.abspath, path)
        self.assertEqual(p.relpath, '2026/MyProject')
        self.assertEqual(p.get_bucket_name(), '2026')

    def test_init_outside_project_root(self):
        p = Project('/2026/MyProject')
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.relpath, None)
        self.assertEqual(p.get_bucket_name(), '2026')
        
    def test_scan_filenames_no_glob_case(self):
        root = expanduser(config.projects_root_dir)
        path = join(root, '2026/MyProject')
        f = TestableFolder(path, {
            '2026/MyProject': [0, 0],
            '2026/MyProject/README.md': [0, 0],
            '2026/MyProject/package.json': [0, 0],
        })
        p = Project(path, folder=f)
        group = PatternRuleGroup(None)
        group.key = 'type'
        group.rules.append(PatternRule('Web App', 'package.json'))
        group.rules.append(PatternRule('Script', '*.py *.pl *.rb'))
        p.type_patterns_by_key['type'] = group
        data = p.scan_filenames(path)
        self.assertEqual(data, {
            'type': 'Web App',
        })

    def test_scan_filenames_glob_case(self):
        root = expanduser(config.projects_root_dir)
        path = join(root, '2026/MyProject')
        f = TestableFolder(path, {
            '2026/MyProject': [0, 0],
            '2026/MyProject/README.md': [0, 0],
            '2026/MyProject/foo.py': [0, 0],
        })
        p = Project(path, folder=f)
        group = PatternRuleGroup(None)
        group.key = 'type'
        group.rules.append(PatternRule('Web App', 'package.json'))
        group.rules.append(PatternRule('Script', '*.py *.pl *.rb'))
        p.type_patterns_by_key['type'] = group
        data = p.scan_filenames(path)
        self.assertEqual(data, {
            'type': 'Script',
        })

    def test_scan_filenames_no_match_case(self):
        root = expanduser(config.projects_root_dir)
        path = join(root, '2026/MyProject')
        f = TestableFolder(path, {
            '2026/MyProject': [0, 0],
            '2026/MyProject/README.md': [0, 0],
            '2026/MyProject/foo.swift': [0, 0],
        })
        p = Project(path, folder=f)
        group = PatternRuleGroup(None)
        group.key = 'type'
        group.rules.append(PatternRule('Web App', 'package.json'))
        group.rules.append(PatternRule('Script', '*.py *.pl *.rb'))
        p.type_patterns_by_key['type'] = group
        data = p.scan_filenames(path)
        self.assertEqual(data, { })

    def test_scan_readme(self):
        p = Project('/2026/MyProject')
        self.assertEqual(p.name, 'MyProject') # inferred from path in constructor
        data = p.scan_readme_content('''
        *Commenced: 2026/02/14*
        *Concluded: 15-Mar-2026*
        *Type: Video*
        *Status: Abandoned*
        '''.split('\n'))
        self.assertEqual(data, {
            'commenced': '2026/02/14',
            'concluded': '2026/03/15',
            'type': 'Video',
            'status': 'Abandoned',
        })
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.name, 'MyProject')
        self.assertEqual(p.commenced, '2026/02/14')
        self.assertEqual(p.concluded, '2026/03/15')
        self.assertEqual(p.type, 'Video')
        self.assertEqual(p.status, 'Abandoned')

    def test_scan_readme_without_apply(self):
        p = Project('/2026/MyProject')
        self.assertEqual(p.name, 'MyProject') # inferred from path in constructor
        data = p.scan_readme_content('''
        *Commenced: 2026/02/14*
        *Concluded: 15-Mar-2026*
        *Type: Video*
        *Status: Abandoned*
        '''.split('\n'), apply=False)
        self.assertEqual(data, {
            'commenced': '2026/02/14',
            'concluded': '2026/03/15',
            'type': 'Video',
            'status': 'Abandoned',
        })
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.name, 'MyProject')
        self.assertEqual(p.commenced, None)
        self.assertEqual(p.completed, None)
        self.assertEqual(p.type, None)
        self.assertEqual(p.status, None)

    def test_scan_readme_inferred_values(self):
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

    def test_scan_inferred_values_not_completed(self):
        content = '''
        # My Great Project
        
        *Commenced: 2026/02/14*
        *Concluded: 15-Mar-2026*
        '''
        p = Project('/2026/MyProject')
        p.scan_readme_content(map(str.strip, content.split('\n')[1:]))
        self.assertEqual(p.abspath, '/2026/MyProject')
        self.assertEqual(p.name, 'My Great Project')
        self.assertEqual(p.commenced, '2026/02/14')
        self.assertEqual(p.concluded, '2026/03/15')
        self.assertEqual(p.status, None)

    def test_scan_aliased_values(self):
        content = '''
        # My Great Project
        
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        *Type: Python*
        '''
        n = Normalizer()
        n.add_alias('Type', 'Python', 'Script')
        p = Project('/2026/MyProject', normalizer=n)
        p.scan_readme_content(map(str.strip, content.split('\n')[1:]))
        self.assertEqual(p.type, 'Script')


class TestLibrary(unittest.TestCase):

    def test_get_project(self):
        lib = Library()
        c = Config(None)
        p1 = lib.get_project(join(c.root, '2026/MyProject'))
        self.assertEqual(p1.abspath, join(c.root, '2026/MyProject'))
        p2 = lib.get_project(join(c.root, '2026/MyProject/README.txt'))
        self.assertEqual(p2.abspath, join(c.root, '2026/MyProject'))
    
    def test_scan_aliased_values(self):
        content = '''
        # My Great Project
        
        *Commenced: 2026/02/14*
        *Completed: 15-Mar-2026*
        *Type: Python*
        '''
        lib = Library()
        lib.normalizer.add_alias('Type', 'Python', 'Script')
        p = lib.get_project('/2026/MyProject') # project should use library normalizer
        p.scan_readme_content(map(str.strip, content.split('\n')[1:]))
        self.assertEqual(p.type, 'Script')

