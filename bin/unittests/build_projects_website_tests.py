import unittest
from io import StringIO
from os.path import join
import json

from build_projects_website import Library, config

config.reset() # discard any config/config.txt customizations

class TestLibrary(unittest.TestCase):

    def __init__(self, name):
        super(TestLibrary, self).__init__(name)
        self.maxDiff = 1024
    
    def test_config(self):
        lib = Library(should_read_all=False)
        lib.process_config(StringIO('''
            {
                "foo": "bar"
            }
        '''.replace('\n        ', '').strip()))
        self.assertEqual(lib.root['config'], { 'foo': 'bar' })
    
    def test_iconic_fields(self):
        lib = Library(should_read_all=False)
        lib.process_iconic_fields('status', StringIO('''
            [
                {
                    "icon": "X",
                    "name": "Abandoned",
                    "description": "Not working, but not under development either"
                }
            ]
        '''.replace('\n        ', '').strip()))
        self.assertEqual(lib.root['icons']['status'], {
            'Abandoned': 'X',
            'None': '🚫',
            'Unclassified': '🐟',
        })
        self.assertEqual(lib.root['iconic_fields']['status'], [{
            'name': 'Abandoned',
            'icon': 'X',
            'description': 'Not working, but not under development either',
        }])
    
    def test_bucket(self):
        self.maxDiff = None
        lib = Library(should_read_all=False)
        lib.process_bucket('2026', StringIO('''
            [
                {
                    "name": "My Project",
                    "abspath": "~/Projects/2026/My Project",
                    "relpath": "2026/My Project",
                    "commenced": "2026/02/14",
                    "completed": "2026/03/15",
                    "last_touched_file": "README.md",
                    "type": "Webapp",
                    "status": "Completed"
                }
            ]
        '''.replace('\n        ', '').strip()))
        # print('GOT', json.dumps(lib.root, indent=4, ensure_ascii=False))
        self.assertEqual(json.loads(json.dumps(lib.root['buckets']['2026'])), [{ 
            'name': 'My Project',
            'abspath': '~/Projects/2026/My Project',
            'relpath': '2026/My Project',
            'commenced': '14-Feb-2026', # note new date format
            'completed': '15-Mar-2026',
            'timestamp': '2026-03-15',
            'last_touched_file': 'README.md',
            'type': 'Webapp',
            'status': 'Completed',
            'date': '15-Mar-2026',
            'css_class': 'webapp completed no-tag',
            'tags': [],
        }])
