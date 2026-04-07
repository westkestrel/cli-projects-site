#!/usr/bin/env python3
'''
Reads the .txt files in the config directory and writes out .json files.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from os.path import basename, exists, expanduser, join, splitext
from os import getcwd, mkdir
from glob import glob
from sys import argv, stderr, stdin, stdout
import json
import re

options = None
def make_parser():
    parser = ArgumentParser(description=__doc__)
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
    parser.add_argument(
        dest='sources', action='store',
        default=list(),
        nargs="*",
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
        text = '%s: %s\n%s\n%s' % (
            self.filename if self.filename != None else 'stdin',
            self.line_number,
            self.line_content,
            self.message
        )
        return text.replace(': None', '').replace('\nNone', '')

def main(args=None):
    global options
    options = make_parser().parse_args(args)
    if len(options.sources) == 0: sources = sorted(glob('config/*.txt'))
    else: sources = options.sources
    if len(sources) == 0 and not exists('config'):
        offer_to_create_configuration_files('config')
        sources = sorted(glob('config/*.txt'))
    if len(sources) == 0:
        print('no configuration files found in config/ folder', file=stderr)
        return 1
    elif not options.silent:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %d json files into %s/ folder' % (preamble, len(sources), 'config'))
    result = 0
    for source in sources:
        try: process(source)
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
        
        title: My Recent Projects
        root: ROOT
        projects: *19[0-9][0-9]/*, *20[0-9][0-9]/*
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
        📝 Notes, Docs
        ＞ Script (aka Shellscript), Command-Line Utility (compiled code)
        🖥️ Application (desktop)
        📱 App (tablet or phone)
        🕸️ Website
        🔧 Admin, Sysadmin, Webadmin
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
        🟡 Unstable (aka Broken): Paused indefinitely and not in a functional state
        🟢 Stable: Paused indefinitely
        ✅ Complete: Project is complete
        🎁 Delivered: Delivered to a client
        💀 Abandoned: Abandoned after a fairly substantial investment
        🪦 Obsolete: Superceded by a newer version
    ''')
    
def create_configuration_file(path, content):
    print('creating %s' % path)
    with open(path, 'w', encoding="utf-8") as file:
        home = expanduser('~')
        content = content.replace('ROOT', getcwd().replace(home, '~'))
        file.write('\n'.join(map(str.strip, content.strip().split('\n'))))
        file.write('\n')
        
def create_values_file(path, content):
    create_configuration_file(path, content)
    
def process(path):
    if not path.endswith('.txt'):
        raise ConfigError('Not a text file: %s' % path, None, None, None)
    if basename(path) == 'config.txt':
        process_config_file(path)
    elif basename(path).endswith('_values.txt'):
        process_values_file(path)
    else:
        raise ConfigError('unrecognized configuration file', path, None, None)
        
def process_config_file(path):
    '''
    Reads a config.txt file and writes config.json
    '''
    if options.verbose: print('reading %s' % path)
    with open(path, encoding="utf-8") as file:
        data = process_config_content(file, path)
    output_path = splitext(path)[0] + '.json'
    if options.verbose:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %s' % (preamble, output_path))
    if options.testing: return
    with open(output_path, 'w', encoding="utf-8") as file:
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
    
def process_values_file(path):
    '''
    Reads a type_values.txt or status_values.txt file and writes the corresponding json file.
    '''
    if options.verbose: print('reading %s' % path)
    with open(path, encoding="utf-8") as file:
        data = process_tag_content(file, path)
    output_path = splitext(path)[0] + '.json'
    if options.verbose:
        preamble = 'NOT ' if options.testing else ''
        print('%swriting %s' % (preamble, output_path))
    if options.testing: return
    with open(output_path, 'w', encoding="utf-8") as file:
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
    
if __name__ == '__main__':
    main(argv[1:])
