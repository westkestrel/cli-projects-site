#!/usr/bin/env python3
'''
Scans the project-root folder for README files, reads them, and updates
(or creates) project-description text files in the data data folder.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from time import localtime, strftime
from glob import glob
from os.path import basename, dirname, exists, expanduser, getmtime, isdir, join
from os import mkdir, walk
from sys import argv
from time import localtime, strftime
import json
import re
import subprocess

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
            self.read(path)
        if self.skip == None: raise ValueError('config is missing "skip" field')
        self.values['skip_regex'] = self.make_regex(self.skip)
            
    def read(self, path):
        if path.endswith('.json'):
            for key, value in json.load(open(path)).items():
                self.values[key] = value
        elif path.endswith('.txt'):
            with open(path, encoding='utf-8') as file:
                for line in file:
                    line = re.sub(r'#.*', '', line).strip()
                    if line == '': continue
                    key, value = re.match(r'^([^:]+):\s*(.+)', line).group(1, 2)
                    if value == 'None' or value == 'null': value = None
                    self.values[key] = value
        else:
            raise ValueError('%s has unexpected file extension' % path)
            
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
        glob_list = list(map(self.make_regex_from_glob, re.split(r', *', glob_list_string)))
        return '^(?:%s)$' % '|'.join(glob_list)
        
    def make_regex_from_glob(self, text):
        return text.replace('.', '[.]').replace('?', '.').replace('*', '.*')
        


config = Config('config/config.txt')

class Normalizer:
    '''
    Converts keys, values, and date strings to standard form
    '''
    def __init__(self):
        self.date_fields = set(['created', 'commenced', 'completed', 'paused', 'resumed', 'abandoned'])
        self.months = {
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
        
    def key(self, text):
        '''
        Converts keys to snake_case
        '''
        return re.sub(r'([a-z])([A-Z])', r'\1_\2', text).replace('-', '_').lower()
        
    def value(self, text, key):
        '''
        Convertes date strings for known date fields.
        '''
        if self.key(key) in self.date_fields:
            return self.date(text)
        return text
        
    def item(self, key, value):
        key = self.key(key)
        value = self.value(value, key)
        return key, value
        
    def date(self, text):
        '''
        Accepts date strings in a variety of formats (and integers and floats representing
        seconds since epoch) and returns an ISO8601 date string (e.g., '2026/01/01')
        '''
        if text == None:
            return None
        if type(text) == int or type(text) == float:
            return strftime('%Y/%m/%d', localtime(text))
            
        text = re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),? *', '', text)
        match = re.match(r'(\d{1,2})-(\w{3,})-(\d{4})', text)
        if match:
            day, month, year = match.group(1, 2, 3)
            text = '%s/%s/%s' % (year, self.months[month.lower()[0:3]], day.rjust(2, '0'))
        match = re.match(r'(\w{3,}) (\d{1,2}), (\d{4})', text)
        if match:
            month, day, year = match.group(1, 2, 3)
            text = '%s/%s/%s' % (year, self.months[month.lower()[0:3]], day.rjust(2, '0'))
        text = text.replace('-', '/')
        return text[0:10]
        
class Folder:
    '''
    A folder is directory in the filesystem
    '''
    
    def __init__(self, path, normalizer=None):
        self.normalizer = normalizer if normalizer != None else Normalizer()
        self.rootpath = config.root
        root = join(config.root, '') # add trailing slash
        self.abspath = path
        self.relpath = path[len(root):] if path.startswith(root) else None
        
    def scan_for_project_metadata(self):
        data = OrderedDict()
        root = join(config.root,) # add trailing slash
        files = self.walk
        data['name'] = basename(self.abspath)
        data['abspath'] = self.abspath
        data['relpath'] = self.relpath
        data['commenced'] = self.normalizer.date(self.get_ctime(self.abspath))
        newest, timestamp = self.get_newest_file(self.abspath)
        if newest != None: newest = newest[len(self.abspath) + 1: ]
        if timestamp == None: timestamp = Folder(self.abspath).get_ctime()
        data['completed'] = self.normalizer.date(timestamp)
        data['newest_file'] = newest
        data['type'] = None
        data['status'] = None
        if data['name'].startswith('www.'): data['type'] = 'Website'
        if self.exists(join(self.abspath, 'package.json')): data['type'] = 'Web App'
        return data
        
    def exists(self, path):
        '''
        Returns whether a file or folder exists at the given path.
        '''
        return exists(path)
        
    def get_ctime(self, path=None):
        '''
        Returns the timestamp (seconds since epoch) of the creation date of the file
        or folder at the given path.  Note that you *cannot* simply use getctime(), as that
        always returns "now" for a directory on MacOS.
        '''
        command = ['stat', '-f', '%B', path if path != None else self.abspath]
        output = subprocess.run(command, capture_output=True, text=True)
        timestamp = output.stdout
        return int(timestamp)
        
    def get_mtime(self, path=None):
        '''
        Returns the timestamp (seconds since epoch) of the modification date of the file
        or folder at the given path.
        '''
        try: return getmtime(path if path != None else self.abspath)
        except FileNotFoundError: return None
        
    def get_newest_file(self, path=None):
        '''
        Returns the path nd timestamp of the newest file within the given folder.
        '''
        newest = None
        timestamp = None
        for root, dirs, files in self.walk(path if path != None else self.abspath):
            dirs[0:len(dirs)] = sorted(filter(lambda d: not re.match(config.skip_regex, d), dirs))
            for file in sorted(filter(lambda f: not re.match(config.skip_regex, f), files)):
                subpath = join(root, file)
                subtime = self.get_mtime(subpath)
                if  subtime != None and (timestamp == None or subtime > timestamp):
                    newest = subpath
                    timestamp = subtime
        return newest, timestamp
        
    def walk(self, path=None):
        return walk(path if path != None else self.abspath)

class TestableFolder(Folder):
    '''
    A testable subclass of Folder. To use it, you provide the path and a dictionary
    of fake timestamps relative to config.root, e.g.,
      // assuming config.root is '~/Projects'
      f = TestableFolder('~/Projects/2026/MyProject', {
        '2026/MyProject': (0, 1),
        '2026/MyProject/README.md': (10, 50),
      })
    '''
    def __init__(self, path, content):
        '''
        path: absolute path to the folder (which need not actually exist on disk)
        content: a dictionary mapping paths (relative to config.root) to a tuple
          (creation timestamp, modification timestamp)
        '''
        super(TestableFolder, self).__init__(path)
        self.content = content
        
    def exists(self, path):
        rpath = path[len(self.rootpath) + 1:]
        return rpath in self.content
        
    def get_ctime(self, path):
        rpath = path[len(self.rootpath) + 1:]
        return self.content[rpath][0]
        
    def get_mtime(self, path):
        rpath = path[len(self.rootpath) + 1:]
        return self.content[rpath][1]
        
    def walk(self, path):
        '''
        Walks the entire content tree in a single step. This is not strictly accurate,
        but is good enough for unit tests.
        '''
        root_relative_paths = sorted(self.content.keys())
        index = len(self.relpath) + 1
        project_relative_paths = list(filter(lambda p: p != '', map(lambda p: p[index:], root_relative_paths)))
        return [[self.abspath, [], project_relative_paths]]


class Project:
    '''
    A project is a folder with associated metadata such as start date,
    stop date, project type, project status, etc.
    '''
    
    DATE_KEYS = set(['date', 'commenced', 'completed', 'abandoned', 'paused', 'resumed'])
    STATUS_KEYS = set(['completed', 'abandoned', 'paused', 'resumed'])
    
    def __init__(self, path, normalizer=None):
        self.normalizer = normalizer if normalizer != None else Normalizer()
        self.metadata = OrderedDict()
        root = join(config.root, '') # add trailing slash
        self['name'] = basename(path)
        self['abspath'] = path
        self['relpath'] = path[len(root):] if path.startswith(root) else None
        
    def get_bucket_name(self):
        return basename(dirname(self.abspath))
        
    def scan_folder_metadata(self, path, apply=True):
        '''
        Extracts project name, date, etc. from the filesystem, optionally applies it
        to the project metadata, and returns it.
        
        Note that even if apply==True, the returned data is what was just extracted,
        not the result of merging.
        '''
        data = Folder(path).scan_for_project_metadata()
        if apply: self.apply(data)
        return data
        
    def scan_readme_file(self, path, apply=True):
        '''
        Extracts project name, date, etc. from the given README file, optionally applies
        it to the project metadata, and returns it.
        
        Note that even if apply==True, the returned data is what was just extracted,
        not the result of merging.
        '''
        if not options.silent: print('reading %s' % path)
        try:
            with open(path, encoding='utf-8') as file:
                return self.scan_readme_content(file, apply)
        except UnicodeDecodeError:
            with open(path, encoding='macroman') as file:
                return self.scan_readme_content(file, apply)
    
    def scan_readme_content(self, content, apply=True):
        '''
        Extracts project name, date, etc. from the given README content, optionally applies
        it to the project metadata, and returns it.
        
        Note that even if apply==True, the returned data is what was just extracted,
        not the result of merging.
        '''
        data = OrderedDict()
        for i, line in enumerate(content, start=1):
            if i == 1 and line.startswith('# '):
                self['name'] = line[1:].strip()
            line = re.sub(r'#.*', '', line).strip().strip('*')
            match = re.match(r'([\w-]+):\s*(.+)', line)
            if match:
                key, value = match.group(1, 2)
                nkey, nvalue = self.normalizer.item(key, value)
                if nkey in self.STATUS_KEYS: data['status'] = key
                data[nkey] = nvalue
        if apply: self.apply(data)
        return data
        
    def apply(self, *args):
        '''
        Takes one or more data dictionaries and applies them to the
        project metadata.
        '''
        for data in args:
            for key, value in data.items():
                self[key] = value
                
    def __getattr__(self, key):
        try:
            return self.metadata[key]
        except KeyError:
            try:
                return self.metadata[self.normalizer.key(key)]
            except KeyError:
                return None
                
    def __getitem__(self, key):
        try:
            return self.metadata[key]
        except KeyError:
            return self.metadata[self.normalizer.key(key)]
        
    def __setitem__(self, key, value):
        key, value = self.normalizer.item(key, value)
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
        
    def scan_for_readme_files(self, path):
        if config.projects == None:
            self.walk_for_readme_files(path)
        else:
            projects = sorted(glob(join(path, config.projects)))
            for subpath in projects:
                self.walk_for_readme_files(subpath, deep=False)
            
    def walk_for_readme_files(self, path, deep=True):
        for root, dirs, files in walk(path):
            if deep: dirs[0:len(dirs)] = sorted(dirs)
            else: dirs[0:len(dirs)] = []
            files[0:len(files)] = sorted(files)
            for i in reversed(range(0, len(dirs))):
                if re.match(config.skip_regex, dirs[i]):
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
        project.apply(
            project.scan_folder_metadata(dirname(path)),
            project.scan_readme_file(path)
        )
        
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
    config = Config('config/config.txt')
    options = make_parser().parse_args(args)
    if not options.skip_configure:
        configure_main()
        config = Config('config/config.txt')
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
    
if __name__ == '__main__':
    main(argv[1:])
