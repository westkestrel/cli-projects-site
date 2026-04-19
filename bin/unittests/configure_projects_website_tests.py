import unittest
from configure_projects_website import process_config_content, process_tag_content

class TestConfigFile(unittest.TestCase):
    def test_basic(self):
        input = '''
            foo: bar
            bat: flies
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_config_content(input)
        self.assertEqual(content, {
            'foo': 'bar',
            'bat': 'flies',
        })
        
    def test_ignore_blank_lines_and_whitespace(self):
        input = '''
            foo: bar    
            bat:     flies
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_config_content(input)
        self.assertEqual(content, {
            'foo': 'bar',
            'bat': 'flies',
        })
        
    def test_ignore_comments(self):
        input = '''
            foo: bar # this is a comment
            bat: flies
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_config_content(input)
        self.assertEqual(content, {
            'foo': 'bar',
            'bat': 'flies',
        })
        
class TestTagFile(unittest.TestCase):
    def test_basic(self):
        input = '''
            🖥️ Application
            📱 App
            🕸️ Website
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "name": "Application",
                "icon": "🖥️",
            },
            {
                "name": "App",
                "icon": "📱",
            },
            {
                "name": "Website",
                "icon": "🕸️",
            },
        ])
        
    def test_ignore_comments(self):
        input = '''
            foo: bar # this is a comment
            bat: flies
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_config_content(input)
        self.assertEqual(content, {
            'foo': 'bar',
            'bat': 'flies',
        })
        
    def test_multiple_tags(self):
        input = '''
            🖥️ Application
            ＞ Script, Command-Line Utility
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "name": "Application",
                "icon": "🖥️",
            },
            {
                "names": ["Script", "Command-Line Utility"],
                "icon": "＞",
            },
        ])
        
    def test_one_tag_one_colon_description(self):
        input = '''
            🖥️ Application: runs on the computer
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "name": "Application",
                "description": "runs on the computer",
                "icon": "🖥️",
            },
        ])
        
    def test_multiple_tags_one_colon_description(self):
        input = '''
            🖥️ Application: runs on the computer, App
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "names": ["Application", "App"],
                "descriptions": {
                    "Application": "runs on the computer",
                },
                "icon": "🖥️",
            },
        ])
        
    def test_multiple_colon_description(self):
        input = '''
            🖥️ Application: runs on the computer, App: phone or tablet
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "names": ["Application", "App"],
                "descriptions": {
                    "Application": "runs on the computer",
                    "App": "phone or tablet",
                },
                "icon": "🖥️",
            },
        ])
        
    def test_one_tag_parenthesized_descriptions(self):
        input = '''
            🖥️ Application (runs on the computer), App (phone or tablet)
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "names": ["Application", "App"],
                "descriptions": {
                    "Application": "runs on the computer",
                    "App": "phone or tablet",
                },
                "icon": "🖥️",
            },
        ])
        
    def test_tags_with_aliases(self):
        input = '''
            > Script (aka Shellscript), Command-Line Utility (compiled code)
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "names": ["Script", "Command-Line Utility"],
                "aliases": {
                    "Shellscript": "Script",
                },
                "descriptions": {
                    "Command-Line Utility": "compiled code",
                },
                "icon": ">",
            },
        ])
        
    def test_tags_with_aliases_and_descriptions(self):
        input = '''
            > Script (aka Shellscript) (perl, python, bash, etc.), Command-Line Utility (aka CLU): compiled code
        '''
        input = list(map(str.strip, input.split('\n')))
        content = process_tag_content(input)
        self.assertEqual(content, [
            {
                "names": ["Script", "Command-Line Utility"],
                "aliases": {
                    "Shellscript": "Script",
                    "CLU": "Command-Line Utility",
                },
                "descriptions": {
                    "Script": "perl, python, bash, etc.",
                    "Command-Line Utility": "compiled code",
                },
                "icon": ">",
            },
        ])
        
