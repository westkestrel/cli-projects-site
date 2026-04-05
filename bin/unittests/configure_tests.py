import unittest
from configure import process_config_content

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
        
