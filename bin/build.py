#!/usr/bin/env python3
'''
Reads the JSON files in the data/ folder and builds a website that
describes your projects.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from glob import glob
from os.path import basename, dirname, exists, expanduser, join
from os import mkdir
from sys import argv, exit, stderr
from time import localtime, strftime, strptime
import json
import re
import subprocess

from configure import preflight as preflight_configure, main as main_configure
from scan import Config, preflight as preflight_scan, main as main_scan, make_parser as make_scan_parser

options = None
def make_parser(description=__doc__):
    '''
    Create an argparse.ArgumentsParser instance with script-appropriate arguments.
    '''
    parser = make_scan_parser(description, suppress_sources=True)
    buckets = join(config.data_dir, 'buckets.json')
    parser.add_argument('-g', '--debug',
        dest='debug', action='store_const',
        const=True,
        default=False,
        help='output the jinja2 commands')
    parser.add_argument(
        dest='build_sources', action='store',
        default=list(),
        nargs="*",
        metavar='sources',
        help='process SOURCES rather than the files listed in %s' % buckets)
    return parser
    
class Library:
    def __init__(self, should_read_all=True):
        self.root = OrderedDict()
        self.unclassified_types = set()
        self.unclassified_statuses = set()

        if should_read_all:
            self.read_all()
        
    def read_all(self):
        data_dir = config.data_dir
        self.read_config(join(data_dir, 'config.json'))
        
        for path in sorted(glob(join(data_dir, '*_values.json'))):
            self.read_iconic_fields(path)
            
        bucket_list_path = join(expanduser(config.data_dir), 'buckets.json')
        try: sources = options.build_sources
        except AttributeError: sources = []
        if len(sources) == 0:
            sources = self.read_bucket_list(bucket_list_path)
        if len(sources) == 0:
            print('**error: no buckets found in %s' % (bucket_list_path), file=stderr)
        for path in sources:
            if not path.endswith('.json'):
                path = join(join(expanduser(config.data_dir), 'buckets'), path) + '.json'
            self.read_bucket(path)
        
        self.process_unclassified_values()
            
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
        capitalized_field_name = field_name[0].upper() + field_name[1:]
        icons = OrderedDict()
        for group in data:
            names = [group['name']] if 'name' in group else group['names']
            for name in names:
                icons[name] = group['icon']
        icons['None'] = '🚫'
        icons['Unclassified'] = '🐟'
        self.root['iconic_fields'][field_name] = data
        self.root['icons'][field_name] = icons
        
    def read_bucket_list(self, path):
        '''
        Load the array of bucket names.
        '''
        if options.verbose: print('reading %s' % path)
        with open(path, encoding='utf-8') as file:
            return json.load(file)
        
    def read_bucket(self, path):
        '''
        Load the given project-array JSON file and put it into the data dictionary.
        '''
        if options.verbose: print('reading %s' % path)
        bucket_name = basename(path).replace('.json', '')
        with open(path, encoding='utf-8') as file:
            self.process_bucket(bucket_name, file)
        
    def process_bucket(self, bucket_name, content):
        if 'unclassified' not in self.root:
            self.root['unclassified'] = OrderedDict() # we want this above the buckets in the JSON
        if 'buckets' not in self.root:
            self.root['buckets'] = OrderedDict()
            
        data = json.load(content, object_pairs_hook=OrderedDict)
        for project in data:
        
            # if we have inferred_x but no x, then set x = inferred_x
            if 'created' in project and 'commenced' not in project:
                project['commenced'] = project['created']
            for field in list(project.keys()):
                if field.startswith('inferred_'):
                    true_field = field[9:]
                    if true_field not in project or project[true_field] == None:
                        project[true_field] = project[field]
                        
            for field in ['commenced', 'last_touched', 'completed', 'abandoned', 'date']:
                if field in project:
                    date = None
                    for date_format in ['%Y/%m/%d', '%d-%B-%Y', '%d-%b-%Y', '%B %d, %Y']:
                        try:
                            date = strptime(project[field], date_format)
                            break
                        except ValueError:
                            pass
                    if date == None:
                        raise ValueError('%s cannot be parsed as a date' % project[field])
                    project[field] = strftime('%d-%b-%Y', date)
            for field, value in list(project.items()):
                if value == 'None':
                    project[field] = None
            project_type = project['type'] if project['type'] != None else 'no-type'
            project_status = project['status'] if project['status'] != None else 'no-status'
            type_class = re.sub(r'[\W_]+', '-', project_type).lower().strip('-')
            status_class = re.sub(r'[\W_]+', '-', project_status).lower().strip('-')
            project['css_class'] = ' '.join([type_class, status_class]).strip()
            try: type_icons = self.root['icons']['type']
            except KeyError: type_icons = {}
            try: status_icons = self.root['icons']['status']
            except KeyError: status_icons = {}
            if project_type not in type_icons:
                self.unclassified_types.add(project_type)
            if project_status not in status_icons:
                self.unclassified_statuses.add(project_status)
        bucket_name = bucket_name.replace('--', '/').replace('--', '/')
        self.root['buckets'][basename(bucket_name)] = data
        
    def process_unclassified_values(self):
        self.root['unclassified'] = OrderedDict()
        if 'no-type' in self.unclassified_types: self.unclassified_types.remove('no-type')
        if 'no-status' in self.unclassified_statuses: self.unclassified_statuses.remove('no-status')
        self.root['unclassified']['type'] = sorted(self.unclassified_types)
        self.root['unclassified']['status'] = sorted(self.unclassified_statuses)
        
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
        template_dir = expanduser(config.template_dir)
        website_dir = expanduser(config.website_dir)
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
            
        data_dir = expanduser(config.data_dir)
        data_path = join(data_dir, 'library.json')
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
    config = Config()
    options = make_parser().parse_args(args)
    lib = Library()
    lib.read_all()
    data_dir =  expanduser(config.data_dir)
    lib.write(join(data_dir, 'library.json'))
    builder = Builder()
    count = builder.build_all()
    if not options.silent: print('updated %d files in %s' % (count, config.website_dir))
    
if __name__ == '__main__':
    config = Config()
    options = make_parser().parse_args()
    if not options.skip_preflight:
        status = preflight_configure(options)
        if status != 0: exit(status)
        status = preflight_scan(options)
        if status != 0: exit(status)
        status = preflight(options)
        if status != 0: exit(status)
    exit(main(argv[1:]))
