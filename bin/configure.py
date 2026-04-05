#!/usr/bin/env python3
'''
Reads the .txt files in the config directory and writes out .json files.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from os.path import basename, exists, join, splitext
from os import getcwd, mkdir
from glob import glob
from sys import stderr, stdin, stdout
import json
import re

options = None
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
    
class ConfigError(Exception):
    def __init__(self, message, filename, line_number, line_content):
        super(ConfigError, self).__init__(message)
        self.message = message
        self.filename = filename
        self.line_number = line_number
        self.line_content = line_content
    def __str__(self):
        return '%s: %s\n%s\n%s' % (
            self.filename if self.filename != None else 'stdin',
            self.line_number,
            self.line_content,
            self.message
        )

def main():
    if len(options.sources) == 0: sources = sorted(glob('config/*.txt'))
    else: sources = options.sources
    if len(sources) == 0 and not exists('config'):
        offer_to_create_configuration_files('config')
        sources = sorted(glob('config/*.txt'))
    if len(sources) == 0:
        print('no configuration files found in config/ folder', file=stderr)
        return 1
    for source in sources:
        process(source)
        
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
    ''')
    
def create_configuration_file(path, content):
    print('creating %s' % path)
    with open(path, 'w') as file:
        content = content.replace('ROOT', getcwd())
        file.write('\n'.join(map(str.strip, content.strip().split('\n'))))
        file.write('\n')
    
def process(path):
    if not path.endswith('.txt'):
        raise ConfigError('Not a text file: %s' % path, None, None, None)
    if basename(path) == 'config.txt':
        process_config_file(path)
    else:
        raise ConfigError('unrecognized configuration file', path, None, None)
        
def process_config_file(path):
    '''
    Reads a config.txt file and writes config.json
    '''
    if not options.silent: print('reading %s' % path)
    with open(path) as file:
        data = process_config_content(file, path)
    output_path = splitext(path)[0] + '.json'
    if options.testing:
        print('NOT writing %s' % output_path)
        return
    if not options.silent: print('writing %s' % output_path)
    with open(output_path, 'w') as file:
        file.write(json.dumps(data, indent=4))

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
    
if __name__ == '__main__':
    options = parser.parse_args()
    main()
