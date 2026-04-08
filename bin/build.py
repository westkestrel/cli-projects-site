#!/usr/bin/env python3
'''
Reads the JSON files in the data/ folder and builds a website that
describes your projects.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from glob import glob
from os.path import basename, dirname, exists, join
from os import mkdir
from sys import argv, exit, stderr
from time import localtime, strftime, strptime
import json
import re
import subprocess

from configure import preflight as preflight_configure, main as main_configure
from scan import Config, preflight as preflight_scan, main as main_scan

CONFIG_FILE_PATH = join('config', 'config.json')

options = None
def make_parser():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-k', '--skip-preflight',
        dest='skip_preflight', action='store_const',
        const=True,
        default=False,
        help='do *not* first invoke scan.py; just build the website')
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
    parser.add_argument('-g', '--debug',
        dest='debug', action='store_const',
        const=True,
        default=False,
        help='output the jinja2 commands')
    parser.add_argument('-t', '--test',
        dest='testing', action='store_const',
        const=True,
        default=False,
        help='read and process source files, but do not write output files')
    parser.add_argument(
        dest='sources', action='store',
        default=list(),
        nargs="*",
        help='process SOURCES rather than data/*.json')
    return parser
    
class Library:
    def __init__(self, should_read_all=True):
        self.root = OrderedDict()
        if should_read_all:
            self.read_all()
        
    def read_all(self):
        self.read_config(CONFIG_FILE_PATH)
        
        config_dir = dirname(CONFIG_FILE_PATH)
        data_dir = config.data_dir
        for path in sorted(glob(join(config_dir, '*_values.json'))):
            self.read_iconic_fields(path)
            
        bucket_files = sorted(filter(lambda d: basename(d) != 'library.json', glob(join(data_dir, '*.json'))))
        if len(bucket_files) == 0:
            print('**error: no data files found in %s' % data_dir, file=stderr)
        for path in bucket_files:
            self.read_bucket(path)
            
    def read_config(self, path, content=None):
        '''
        Load the config JSON file and put it into the data dictionary.
        '''
        if options.verbose: print('reading %s' % path)
        with open(path, encoding='utf-8') as file:
            self.process_config(file)
        
    def process_config(self, content):
        data = json.load(content, object_pairs_hook=OrderedDict)
        self.root['config'] = data
        
    def read_iconic_fields(self, path):
        '''
        Load the given known-field-values JSON file and put it into the data dictionary.
        '''
        if options.verbose: print('reading %s' % path)
        field_name = basename(path).replace('_values.json', '')
        with open(path, encoding='utf-8') as file:
            self.process_iconic_fields(field_name, file)
            
    def process_iconic_fields(self, field_name, content):
        if 'iconic_fields' not in self.root:
            self.root['iconic_fields'] = OrderedDict()
        if 'icons' not in self.root:
            self.root['icons'] = OrderedDict()
            
        data = json.load(content, object_pairs_hook=OrderedDict)
        data.append(OrderedDict([('name', 'None'), ('icon', '🚫')]))
        icons = OrderedDict()
        for group in data:
            names = [group['name']] if 'name' in group else group['names']
            for name in names:
                icons[name] = group['icon']
        self.root['iconic_fields'][field_name] = data
        self.root['icons'][field_name] = icons
        
    def read_bucket(self, path):
        '''
        Load the given project-array JSON file and put it into the data dictionary.
        '''
        if options.verbose: print('reading %s' % path)
        bucket_name = basename(path).replace('.json', '')
        with open(path, encoding='utf-8') as file:
            self.process_bucket(bucket_name, file)
        
    def process_bucket(self, bucket_name, content):
        if 'buckets' not in self.root:
            self.root['buckets'] = OrderedDict()
            
        data = json.load(content, object_pairs_hook=OrderedDict)
        for project in data:
            for field in ['commenced', 'completed', 'abandoned', 'date']:
                if field in project:
                    try: date = strptime(project[field], '%Y/%m/%d')
                    except ValueError:
                        date = strptime(project[field], '%B %d, %Y')
                    project[field] = strftime('%d-%b-%Y', date)
        self.root['buckets'][bucket_name] = data
        
    def write(self, path):
        if options.verbose:
            if options.testing: print('NOT writing %s' % path)
            else: print('writing %s' % path)
        if options.testing: return
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(self.root, file, indent=4, ensure_ascii=False)
            
class Builder:
    def __init__(self):
        self.failures = 0
        
    def build_all(self):
        template_dir = config.template_dir
        website_dir = config.website_dir
        templates = sorted(glob(join(template_dir, '*')))
        if len(templates) == 0:
            print('**error: no template files found in %s' % template_dir, file=stderr)
        for template in templates:
            self.build(template, template.replace(template_dir, website_dir))
        return len(templates)
            
    def build(self, template_path, output_path):
        if template_path == output_path:
            raise ValueError('template and output path are both "%s"' % template_path)
            
        website_dir = dirname(output_path)
        if not exists(website_dir) and not options.testing:
            if options.verbose: print('mkdir %s' % website_dir)
            mkdir(website_dir)
            
        data_path = join(config.data_dir, 'library.json')
        command = ['jinja2', template_path, data_path]
        if options.debug: print(' '.join(command))
        
        output = subprocess.run(command, capture_output=True, text=True)
        if output.returncode != 0: self.failures = self.failures + 1
        if options.verbose:
            if options.testing: print('NOT writing %s' % output_path)
            else: print('writing %s' % output_path)
        stderr.write(output.stderr)
        if options.testing: return
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(output.stdout)
    
def preflight(options):
    if not options.skip_preflight:
        if not options.silent: print('running bin/scan.py (pass -k/--skip-preflight to bypass)')
        status = main_scan()
        if status != 0: return status
        if not options.silent: print('bin/scan.py completed successfully\n')
    return 0
    
def main(args=None):
    global options
    global config
    config = Config(CONFIG_FILE_PATH)
    options = make_parser().parse_args(args)
    lib = Library()
    lib.read_all()
    lib.write(join(config.data_dir, 'library.json'))
    builder = Builder()
    count = builder.build_all()
    if not options.silent: print('updated %d files in %s' % (count, config.website_dir))
    
if __name__ == '__main__':
    options = make_parser().parse_args()
    if not options.skip_preflight:
        status = preflight_configure(options)
        if status != 0: exit(status)
        status = preflight_scan(options)
        if status != 0: exit(status)
        status = preflight(options)
        if status != 0: exit(status)
    exit(main(argv[1:]))
