#!/usr/bin/env python3
'''
Scans the project-root folder for README files, reads them, and updates
(or creates) project-description text files in the data data folder.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from glob import glob
from os.path import basename, dirname, exists, expanduser, isdir, join
from os import mkdir, walk
from sys import argv
import json
import re

from configure import main as configure_main
    
config = None
options = None
def make_parser():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('-k', '--skip-configure',
        dest='skip_configure', action='store_const',
        const=True,
        default=False,
        help='do *not* first invoke configure.py; just do the scan')
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
        help='process SOURCES rather than %s' % config['root'])
    return parser
    
class FileError(Exception):
    pass
    
class Config:
    '''
    The project configuration is a collection of key-value pairs read from the
    config/config.json file.
    
    If you access a nonexistent config using dictionary notation (e.g., config['root'])
    a KeyError will be raised. If you use field notation (e.g., config.root) no exception
    will be raised and the value will be None.
    '''
    def __init__(self, path):
        self.values = {
            'name': 'Past Projects',
            'root': '~/Projects',
            'skip': '.*, _*, tmp, node_modules, PackageCache, wp-content',
        }
        if path != None:
            for key, value in json.load(open(path)).items():
                self.values[key] = value
            
    def __getattr__(self, key):
        try: return self.values[key]
        except KeyError: return None
    
    def __getitem__(self, key):
        return self.values[key]

class Project:
    '''
    A project is a folder with associated metadata such as start date,
    stop date, project type, project status, etc.
    '''
    
    DATE_KEYS = set(['date', 'commenced', 'completed', 'abandoned', 'paused', 'resumed'])
    STATUS_KEYS = set(['completed', 'abandoned', 'paused', 'resumed'])
    
    def __init__(self, path):
        self.metadata = OrderedDict()
        self.metadata['Path'] = path
        
    def get_bucket_name(self):
        parent_folder = dirname(self.path)
        root = config.root
        if not parent_folder.startswith(root):
            raise ValueError('%s is not a subdirectory of %s' % (parent_folder, root))
        return parent_folder[len(root)+1:]
        
    def scan_readme_file(self, path):
        if not options.silent: print('reading %s' % path)
        try:
            with open(path, encoding='utf-8') as file:
                self.scan_readme_content(file)
        except UnicodeDecodeError:
            with open(path, encoding='macroman') as file:
                self.scan_readme_content(file)
    
    def scan_readme_content(self, content):
        for i, line in enumerate(content, start=1):
            if i == 1 and line.startswith('# '):
                self.metadata['Name'] = line[1:].strip()
            line = re.sub(r'#.*', '', line).strip().strip('*')
            match = re.match(r'([\w-]+):\s*(.+)', line)
            if match:
                key, value = match.group(1, 2)
                lkey = key.lower()
                if lkey in self.DATE_KEYS: value = normalize_date_string(value)
                if lkey in self.STATUS_KEYS: self['Status'] = key
                self[key] = value
                
    def __getattr__(self, key):
        key = key[0].upper() + key[1:]
        try: return self.metadata[key]
        except KeyError: return None
        
    def __getitem__(self, key):
        return self.metadata[key]
        
    def __setitem__(self, key, value):
        self.metadata[key] = value
    
class Library:
    '''
    A library is a collection of projects.
    '''
    
    def __init__(self):
        self.projects = OrderedDict()
        
    def get_project(self, path, create=True):
        if self.is_readme_path(path): path = dirname(path)
        try:
            return self.projects[path]
        except KeyError:
            if not create: return None
        project = Project(path)
        self.projects[path] = project
        return project
        
    def is_readme_path(self, path):
        return 'readme' in basename(path).lower()
        
    def make_regex(self, glob_list_string):
        glob_list = list(map(self.make_regex_from_glob, re.split(r', *', glob_list_string)))
        return '^(?:%s)$' % '|'.join(glob_list)
        
    def make_regex_from_glob(self, text):
        return text.replace('.', '[.]').replace('?', '.').replace('*', '.*')
        
    def scan_for_readme_files(self, path):
        if config.projects == None:
            self.walk_for_readme_files(path)
        else:
            projects = sorted(glob(join(path, config.projects)))
            for subpath in projects:
                self.walk_for_readme_files(subpath, deep=False)
            
    def walk_for_readme_files(self, path, deep=True):
        skip_regex = self.make_regex(config.skip)
        for root, dirs, files in walk(path):
            if deep: dirs[0:len(dirs)] = sorted(dirs)
            else: dirs[0:len(dirs)] = []
            files[0:len(files)] = sorted(files)
            for i in reversed(range(0, len(dirs))):
                if re.match(skip_regex, dirs[i]):
                    dirs[i:i+1] = []
            files = list(filter(lambda f: re.match(r'_?readme.(txt|md|markdown)', f.lower()), files))
            if len(files) == 0:
                continue
            elif len(files) > 1:
                raise FileError('found more than one README file:\n%s' % '\n'.join(map(lambda f: join(root, f), files)))
            else:
                self.scan_readme_file(join(root, files[0]))
    
    def scan_readme_file(self, path):
        project = self.get_project(path, create=True)
        project.scan_readme_file(path)
        
    def write_buckets(self):
        data_dir = 'data'
        if not exists(data_dir) and not options.testing:
            if not options.silent:
                print('mkdir -p "%s"' % data_dir)
            mkdir(data_dir)
        buckets = dict()
        for project in self.projects.values():
            bucket_name = project.get_bucket_name()
            try: buckets[bucket_name].append(project)
            except KeyError: buckets[bucket_name] = [project]
        for bucket_name in sorted(buckets.keys()):
            self.write_bucket(bucket_name, buckets[bucket_name])
            
    def write_bucket(self, bucket_name, projects):
        data = list(map(lambda p: p.metadata, projects))
        path = join('data', '%s.json' % bucket_name)
        if options.testing:
            print('NOT writing %s' % path)
            return
        print('writing %s' % path)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

def main(args=None):
    global options
    global config
    config = Config('config/config.json')
    options = make_parser().parse_args(args)
    if not options.skip_configure:
        configure_main()
        config = Config('config/config.json')
    if len(options.sources) == 0: sources = sorted(glob(expanduser(config.root)))
    else: sources = options.sources
    library = Library()
    for source in sources:
        source = expanduser(source)
        if isdir(source):
            if not options.silent: print('scanning %s/' % source)
            library.scan_for_readme_files(source)
        else:
            library.scan_readme_file(source)
    library.write_buckets()
    
    
MONTHS = {
    'jan': '01',
    'feb': '02',
    'mar': '03',
    'apr': '04',
    'may': '05',
    'jun': '06',
    'jul': '07',
    'aug': '08',
    'sep': '09',
    'oct': '10',
    'nov': '11',
    'dec': '12',
}
def normalize_date_string(text):
    text = re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),? *', '', text)
    match = re.match(r'(\d{1,2})-(\w{3,})-(\d{4})', text)
    if match:
        day, month, year = match.group(1, 2, 3)
        text = '%s/%s/%s' % (year, MONTHS[month.lower()[0:3]], day.rjust(2, '0'))
    match = re.match(r'(\w{3,}) (\d{1,2}), (\d{4})', text)
    if match:
        month, day, year = match.group(1, 2, 3)
        text = '%s/%s/%s' % (year, MONTHS[month.lower()[0:3]], day.rjust(2, '0'))
    text = text.replace('-', '/')
    return text

if __name__ == '__main__':
    main(argv[1:])
