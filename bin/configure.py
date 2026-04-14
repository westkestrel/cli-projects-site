#!/usr/bin/env python3
'''
Reads the .txt files in the config directory and writes out .json files.
'''

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import OrderedDict
from os.path import basename, exists, expanduser, join, splitext
from os import getcwd, mkdir
from glob import glob
from sys import argv, exit, stderr, stdin, stdout
import json
import re

options = None
config = None

def make_parser(description=__doc__, suppress_sources=False):
    '''
    Create an argparse.ArgumentsParser instance with script-appropriate arguments.
    '''
    parser = ArgumentParser(description=description, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('-s', '--silent',
        dest='silent', action='store_const',
        const=True,
        default=False,
        help='produce less output')
    parser.add_argument('-v', '--verbose',
        dest='verbose', action='store_const',
        const=True,
        default=False,
        help='produce more output')
    parser.add_argument('-t', '--test',
        dest='testing', action='store_const',
        const=True,
        default=False,
        help='read and process source files, but do not write output files')
    if not suppress_sources:
        parser.add_argument(
            dest='config_sources', action='store',
            default=list(),
            nargs="*",
            metavar='sources',
            help='process SOURCES rather than config/*.txt')
    return parser
    
class ConfigError(Exception):
    def __init__(self, message, filename, line_number, line_content):
        super(ConfigError, self).__init__(message)
        self.message = message
        self.filename = filename
        self.line_number = line_number
        self.line_content = line_content
    def __str__(self):
        if self.line_number == None and self.line_content == None and self.filename == None:
            text = message
        elif self.line_number == None and self.line_content == None:
            text = '%s: %s' % (
                self.message,
                self.filename
            )
        else:
            text = '%s: %s\n%s\n%s' % (
                self.filename if self.filename != None else 'stdin',
                self.line_number,
                self.line_content,
                self.message
            )
        return text.replace(': None', '').replace('\nNone', '')

class Config:
    '''
    The project configuration is a collection of key-value pairs read from the
    config/config.txt file.
    
    If you access a nonexistent config using dictionary notation (e.g., config['title'])
    a KeyError will be raised. If you use field notation (e.g., config.title) no exception
    will be raised and the value will be None.

    Calling Config('/path/to/file.txt') will initialize the config from the file content
    Calling Config() will create initialize from 'config/config.txt'
    Calling Config(False) or Config(None) will create an empty config
    '''
    def __init__(self, path='config/config.txt'):
        self.reset()
        if path != False and path != None and exists(path):
            self.read(path)
        if 'skip' in self.values:
            self.values['skip_regex'] = self.make_regex(self.values['skip'])
            
    def reset(self):
        '''
        Resets configuration to factory defaults. You should invoke this in unit tests
        to ensure that your tests are not affected by the local config.
        '''
        self.values = {
            'projects_root_dir': '~/Projects',
            'data_dir': 'data',
            'template_dir': 'template',
            'website_dir': 'website',
            'skip': '.*, _*, tmp, node_modules, PackageCache, wp-content',
            'json_date_format': '%Y-%m-%d',
            'html_date_format': '%d-%b-%Y',
            'title': 'Past Projects',
            'author': None,
            'email': None,
        }
        self.values['skip_regex'] = self.make_regex(self.values['skip'])

    def read(self, path):
        # we cannot refer to options because we may read config before parse_args() is called
        if '-v' in argv or '--verbose' in argv: print('reading %s' % path)
        if path.endswith('.json'):
            for key, value in json.load(open(path, encoding='utf-8')).items():
                self.values[key] = re.sub(r'^\./', '', value) # turn './data' into 'data'
        elif path.endswith('.txt'):
            with open(path, encoding='utf-8') as file:
                for i, orig_line in enumerate(file, start=1):
                    line = re.sub(r'#.*', '', orig_line).strip()
                    if line == '': continue
                    try: key, value = re.match(r'(.+):\s*(.+)', line).group(1, 2)
                    except ValueError:
                        print('**error: malformed line in %s line %s:\n%s' % (path, i, orig_line), file=stderr)
                        exit(1)
                    self.values[key] = re.sub(r'^\./', '', value) # turn './data' into 'data'
                if 'skip' in self.values:
                    self.values['skip_regex'] = self.make_regex(self.values['skip'])
        else:
            raise ValueError('%s has unexpected file extension' % path)
                
    def __str__(self):
        return '{\n  %s\n}' % ',\n  '.join(map(lambda key_and_value: '%s: "%s"' % key_and_value, self.values.items()))
            
    def __getattr__(self, key):
        try: return self.values[key]
        except KeyError: return None
    
    def __getitem__(self, key):
        return self.values[key]
        
    def __setitem__(self, key, value):
        self.values[key] = value
        if key == 'skip':
            self.values['skip_regex'] = self.make_regex(value)
        
    def make_regex(self, glob_list_string):
        glob_list = list(map(self.make_regex_from_glob, re.split(r'[,\s]+', glob_list_string)))
        return '^(?:%s)$' % '|'.join(glob_list)
        
    def make_regex_from_glob(self, text):
        return text.replace('.', '[.]').replace('?', '.').replace('*', '.*')

def preflight(options):
    '''
    The configure script has no preflight requirements, so this
    function does nothing.
    '''
    return 0

def main(args=None):
    '''
    Reads text files and writes json files.
    '''
    global options
    global config
    if __name__ == '__main__': options = make_parser().parse_args(args)
    else: options, unknown = make_parser(suppress_sources=True).parse_known_args(args)
    config = Config()
    
    try: sources = options.config_sources
    except AttributeError: sources = []
    if len(sources) == 0: sources = sorted(glob('config/*.txt'))
        
    if len(sources) == 0 and not exists('config'):
        offer_to_create_configuration_files('config')
        sources = sorted(glob('config/*.txt'))
    if len(sources) == 0:
        print('no configuration files found in config/ folder', file=stderr)
        return 1
    elif not options.silent:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %d json files into %s/ folder' % (preamble, len(sources), config.data_dir))
    result = 0
    if not options.testing and not exists(config.data_dir): mkdir(config.data_dir)
    for source in sources:
        try: process(source, join(config.data_dir, '%s%s' % (splitext(basename(source))[0], '.json')))
        except ConfigError as e:
            print('**error: %s' % e, file=stderr)
            result = 1
            continue
    return result
        
def offer_to_create_configuration_files(path):
    print('no %s/ folder found. Would you like to create one? [y] ' % path, end='')
    stdout.flush()
    reply = stdin.readline()
    if len(reply.strip()) == 0 or reply[0].lower() == 'y':
        create_configuration_folder(path)
        
def create_configuration_folder(path):
    print('creating %s' % path)
    mkdir(path)
    create_configuration_file(join(path, 'config.txt'), '''
        # Edit this configuration text file, then run bin/configure.py
        # to convert it to a JSON file.
        
        
        # The folder where you keep your projects
        #projects_root_dir: CWD
        projects_root_dir: ~/Projects
        
        # A comma-separated list of glob patterns that match
        # project folders in your project-root folder
        projects: *19[0-9][0-9]/*, *20[0-9][0-9]/*
        
        # a comma-separated list of glob patterns to skip when scanning project folders
        skip: _*, .*, node_modules, tmp
        
        
        # A data folder where intermediate JSON files will be stored
        data_dir: ./data
        
        # A folder containing Jinja2 templates for the project-list website
        template_dir: ./templates
        
        
        # The location of the generated project-list website
        website_dir: ./website
        
        # How dates should be formatted in JSON files and the website.
        # See https://docs.python.org/3/library/datetime.html#format-codes
        # and note one exception: in these scripts %d is NOT zero-padded if it appears
        # at the start of the format string.
        json_date_format: %Y-%m-%d # e.g., 2025-03-01
        html_date_format: %d-%b-%Y # e.g., 1-Mar-2025
        
        # Metadata to be included in the generated website
        title: My Recent Projects
        author: None
        email: None
    ''')
    create_values_file(join(path, 'fields.txt'), '''
        # Edit this configuration text file, then run bin/configure.py
        # to convert it to a JSON file.
        #
        # Possible field types are text, path, and date.
        # The order in which you list the fields is the order they will
        # appear in the data/briefs/*.txt and data/buckets/*.json files.
        
        name: text
        description: text
        abspath: path
        relpath: path
        created: date
        commenced: date
        completed: date
        delivered: date
        paused: date
        abandoned: date
        date: date
        last_touched: date
        last_touched_file: path
        type: text
        status: text
        inferred_type: text # based on presence of specific files within the project
        inferred_type_triggering_filename: path # the file in question
        versioning: text
        git_host: text
        git_origin: text
    ''')
    create_values_file(join(path, 'type_values.txt'), '''
        # List your project-type values here, then run bin/configure.py
        # to convert it to a JSON file.
        #
        # Put project-type descriptions in parenthesis or after a colon
        # (if your description contains a comma you must use parenthesis)
        #
        # Comma-separated items will share an icon, but retain their names
        # aka items will be renamed (i.e, "Photos" projects become "Photography")
        
        🎙️ Audio, Podcast, Sound
        🎬 Movie, Video, Flash
        🎞️️ Photography (aka Photos)
        🖋️ Prose, Poetry, Blog, Writing
        📝 Notes, Docs, Documents
        ＞ Script (aka Shellscript), Command-Line Utility (compiled code)
        🖥️ Application (desktop)
        📱 App (tablet or phone)
        🕸️ Website, Web App
        🔧 Admin, Sysadmin, Webadmin
    ''')
    create_values_file(join(path, 'type_patterns.txt'), '''
        # List your project-type glob patterns here, then run bin/configure.py
        # to convert it to a JSON file.
        #
        # If the project directory name or the name of any top-level file or folder
        # matches the patterns then the project type will be set appropriately. The
        # first rule that matches will be used (e.g., if MySite.com contains a
        # a package.json file then the type will be 'Web App')
        
        Web App: package.json
        Website: www.* *.ca *.com *.org
        App: *.xcodeproj # this may falsely identify an Application as an App
        Notes: *Notes *Quotes *Repairs
        Documents: *.pages *.numbers
    ''')
    create_values_file(join(path, 'status_values.txt'), '''
        # List your project-status values here, then run bin/configure.py
        # to convert it to a JSON file.
        #
        # Put project-status descriptions in parenthesis or after a colon
        # (if your description contains a comma you must use parenthesis)
        #
        # Comma-separated items will share an icon, but retain their names
        # aka items will be renamed (i.e, "Broken" projects become "Unstable")
        
        ✏️ Sketch: Initial sketches for an idea that never really took off
        ▶️ Active: Under active development
        ⏸️ Paused: Briefly paused due to competing priorities
        📸 Snapshot (Project is open-ended, and this is a copy at a particular point in time)
        🟡 Unstable (aka Broken): Paused indefinitely and not currently functional
        🟢 Stable: Paused indefinitely in a usable state
        ✅ Completed: Has accomplished its objectives
        🎁 Delivered: Delivered to a client
        💀 Abandoned: Abandoned after a fairly substantial investment
        🪦 Obsolete: Superceded by a newer version
    ''')
    
def create_configuration_file(path, content):
    print('creating %s' % path)
    with open(path, 'w', encoding="utf-8") as file:
        home = expanduser('~')
        content = content.replace('CWD', getcwd().replace(home, '~'))
        file.write('\n'.join(map(str.strip, content.strip().split('\n'))))
        file.write('\n')
        
def create_values_file(path, content):
    create_configuration_file(path, content)
    
def process(path, destination_path):
    if not path.endswith('.txt'):
        raise ConfigError('Not a text file: %s' % path, None, None, None)
    if basename(path) == 'config.txt':
        process_config_file(path, destination_path)
    elif basename(path) == 'fields.txt':
        process_config_file(path, destination_path)
    elif basename(path).endswith('_values.txt'):
        process_values_file(path, destination_path)
    elif basename(path).endswith('_patterns.txt'):
        process_patterns_file(path, destination_path)
    else:
        raise ConfigError('unrecognized configuration file', path, None, None)
        
def process_config_file(path, destination_path):
    '''
    Reads a config.txt file and writes config.json
    '''
    if options.verbose: print('reading %s' % path)
    with open(path, encoding="utf-8") as file:
        data = process_config_content(file, path)
    if options.verbose:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %s' % (preamble, destination_path))
    if options.testing: return
    with open(destination_path, 'w', encoding="utf-8") as file:
        # note that ensure_ascii=False == "leave emoji as emoji"
        file.write(json.dumps(data, indent=4, ensure_ascii=False))

def process_config_content(lines, filename=None):
    '''
    Scans lines with the format
        key: value
    and returns the corresponding dictionary.
    '''
    config = OrderedDict()
    for i, line in enumerate(lines, start=1):
        line = re.sub(r'\s*#.*', '', line).strip()
        if len(line) == 0: continue
        parts = re.split(r':\s*', line)
        if len(parts) != 2:
            raise ConfigError('expected "key: value"', filename, i, line)
        key, value = parts
        config[key] = value
    return config
    
def process_values_file(path, destination_path):
    '''
    Reads a type_values.txt or status_values.txt file and writes the corresponding json file.
    '''
    if options.verbose: print('reading %s' % path)
    with open(path, encoding="utf-8") as file:
        data = process_tag_content(file, path)
    if options.verbose:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %s' % (preamble, destination_path))
    if options.testing: return
    with open(destination_path, 'w', encoding="utf-8") as file:
        # note that ensure_ascii=False == "leave emoji as emoji"
        file.write(json.dumps(data, indent=4, ensure_ascii=False))

def process_tag_content(lines, path=None):
    '''
    Scans lines of the "project type_values" format
        📝 Notes (including spreadsheets), Docs (aka Documentation)
    or the "project status_values" format
        🪦 Obsolete: Superceded by a later project
    and returns an array of dictionaries:
        [{
            "names": ["Notes", "Docs"],
            "descriptions": {
                "Notes": "including spreadsheets"
            },
            "aliases": {
                "Documentation": "Docs"
            },
            "icon": "📝"
        }, {
            "name": "Obsolete",
            "description": "Superceded by a later project",
            "icon": "🪦"
        }]
    '''
    aliases = OrderedDict()
    descriptions = OrderedDict()
    
    def capture(match):
        key = str(len(descriptions))
        colon, parenthesis = match.group(1, 2)
        value = parenthesis if parenthesis != None else colon
        if value.startswith('aka '):
            aliases[key] = re.split(r',\s*', value[4:])
            return '@%s' % key
        else:
            descriptions[key] = value
            return ':%s' % key
        
    tags = []
    for i, line in enumerate(lines, start=1):
        aliases = OrderedDict()
        descriptions = OrderedDict()
        tag = {}
        line = re.sub(r'\s*#.*', '', line).strip()
        if len(line) == 0: continue
        
        match = re.match(r'(\S+)\s+(.+)', line)
        if not match: raise ConfigError('malformed line', path, i, line)
        
        icon, tail = match.group(1, 2)
        tail = re.sub(r':\s+([^,]+)|\s*\(([^)]+)\)', capture, tail)
        terms = re.split(r',\s*', tail)
        for i, term_plus in enumerate(list(terms)):
            term, alias_id, desc_id = re.match('^(.*?)(?:@(.+?))?(?::(.+?))?$', term_plus).group(1, 2, 3)
            terms[i] = term
            if alias_id != None:
                for alias in aliases[alias_id]:
                    aliases[alias] = term
                del aliases[alias_id]
            if desc_id != None:
                descriptions[term] = descriptions[desc_id]
                del descriptions[desc_id]
            else:
                descriptions[term] = None
                
        for key, value in list(descriptions.items()):
            if value == None:
                del descriptions[key]
        
        if len(terms) == 1: tag['name'] = terms[0]
        else: tag['names'] = terms
        num_descriptions = len(list(filter(lambda v: v != None, descriptions.values())))
        
        try: primary_description = descriptions[terms[0]]
        except KeyError: primary_description = None
        
        if len(aliases) > 0:
            tag['aliases'] = aliases
            
        if num_descriptions == 0:
            pass
        elif num_descriptions > 1 or len(terms) > 1 or primary_description == None:
            tag['descriptions'] = descriptions
        else:
            tag['description'] = primary_description
        tag['icon'] = icon
        tags.append(tag)
        
    return tags
    
def process_patterns_file(path, destination_path):
    '''
    Reads a type_patterns.txt or status_patterns.txt file and writes the corresponding json file.
    '''
    if options.verbose: print('reading %s' % path)
    with open(path, encoding="utf-8") as file:
        data = process_patterns_content(file, path)
    if options.verbose:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %s' % (preamble, destination_path))
    if options.testing: return
    with open(destination_path, 'w', encoding="utf-8") as file:
        file.write(json.dumps(data, indent=4, ensure_ascii=False))
        
def process_patterns_content(content, path):
    data = list()
    for line in content:
        line = re.sub(r'\s*#.*', '', line).strip()
        if len(line) == 0: continue
        value, globs = re.match(r'^([^:]+):\s*(.+)', line).group(1, 2)
        data.append(OrderedDict([
            ('value', value),
            ('globs', re.split(r'[,\s]+', globs)),
        ]))
    return data

if __name__ == '__main__':
    try:
        options = make_parser().parse_args()
        status = preflight(options)
        if status != 0: exit(status)
        exit(main(argv[1:]))
    except KeyboardInterrupt:
        print('INTERRUPTED', file=stderr)
        exit(1)

