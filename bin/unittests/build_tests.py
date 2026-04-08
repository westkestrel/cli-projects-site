import unittest
from io import StringIO
from os.path import join
import json

from build import Library

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
        })
        self.assertEqual(lib.root['iconic_fields']['status'], [{
            'name': 'Abandoned',
            'icon': 'X',
            'description': 'Not working, but not under development either',
        }, {
            'name': 'None',
            'icon': '🚫',
        }])
    
    def test_bucket(self):
        lib = Library(should_read_all=False)
        lib.process_bucket('2026', StringIO('''
            [
                {
                    "name": "My Project",
                    "abspath": "~/Projects/2026/My Project",
                    "relpath": "2026/My Project",
                    "commenced": "2026/02/14",
                    "completed": "2026/03/15",
                    "newest_file": "README.md",
                    "type": "Webapp",
                    "status": "Complete"
                }
            ]
        '''.replace('\n        ', '').strip()))
        # print('GOT', json.dumps(lib.root, indent=4, ensure_ascii=False))
        self.assertEqual(lib.root['buckets']['2026'], [{ 
            'name': 'My Project',
            'abspath': '~/Projects/2026/My Project',
            'relpath': '2026/My Project',
            'commenced': '14-Feb-2026', # note new date format
            'completed': '15-Mar-2026',
            'newest_file': 'README.md',
            'type': 'Webapp',
            'status': 'Complete',
            'css_class': 'webapp complete',
        }])
