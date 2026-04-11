#!/usr/bin/env python3
'''
Scans your project folders
    ~/Projects/*20??/* (e.g., '~/Projects/2026/My Great Website')
for metadata in README (and other) files and creates project-description JSON files in
the data/buckets/ folder.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from time import localtime, strftime
from glob import glob
from os.path import basename, dirname, exists, expanduser, getmtime, isdir, join, splitext
from os import mkdir, listdir, walk
from sys import argv, exit, stderr
from time import localtime, strftime
import json
import re
import subprocess

from configure import Config, preflight as preflight_configure, main as main_configure, make_parser as make_configure_parser
    
config = None
options = None
def make_parser(description=__doc__, suppress_sources=False):
    bucket_dir = join(join(config.data_dir, 'buckets'), '')
    projects = list(map(lambda g: join(config.projects_root_dir, g), re.split(r'[\s,]+', config.projects)))
    description = description.replace('data/buckets/', bucket_dir)
    description = re.sub('.*~/Projects.*\n', '    ' + '\n    '.join(projects) + '\n', description)
    parser = make_configure_parser(description=description, suppress_sources=True)
    parser.add_argument('-k', '--skip-preflight',
        dest='skip_preflight', action='store_const',
        const=True,
        default=False,
        help='do *not* first invoke configure.py; just do the scan')
    if not suppress_sources:
        parser.add_argument(
            dest='scan_sources', action='store',
            default=list(),
            nargs="*",
            metavar='project_paths',
            help='process the given folders rather than the folders described above')
    return parser
    
class FileError(Exception):
    pass
    
config = Config()

class KnownValueGroup:
    '''
    A known value group represents one or more known values which share an icon, and is
    defined by a single line in a *_values.txt file, e.g.,
        > Script (aka Python, Perl, Bash), Command-Line Utility
    defines the group with icon '>' and two values 'Script' and 'Command-Line Utility',
    as well as three aliases for Script.
    '''
    def __init__(self, data):
        self.icon = data['icon']
        try: self.names = data['names']
        except KeyError: self.names = [data['name']]
        try: self.aliases = data['aliases']
        except KeyError: self.aliases = dict()

class KnownValues:
    '''
    A known values object represents all of the known value groups for a given key.
    '''
    def __init__(self, path):
        name = splitext(basename(path))[0] # e.g., 'type_values'
        bits = name.split('_')
        self.key = '_'.join(bits[0:len(bits)-1])
        self.aliases = OrderedDict()
        self.by_icon = OrderedDict()
        self.groups = list()
        self.values = set()
        data = json.load(open(path, encoding='utf-8'))
        for record in data:
            group = KnownValueGroup(record)
            for value in group.names:
                self.values.add(value)
            if group.icon not in self.by_icon:
                self.by_icon[group.icon] = group
            else:
                raise ValueError('two groups with the same icon: %s' % group.icon)
            for key, value in group.aliases.items():
                self.aliases[key] = value
            self.groups.append(group)
            
        def is_known(self, value):
            return value in self.values
            
class PatternRuleGroup:
    '''
    A pattern-rule group is a collection of field values, and glob patterns that will
    signal that field value if any files in the project match. e.g.
        XCode: *.xcodeproj
        Web App: node_modules
    '''
    
    def __init__(self, path):
        if path != None:
            name = splitext(basename(path))[0] # e.g., 'type_values'
            bits = name.split('_')
            self.key = '_'.join(bits[0:len(bits)-1])
        self.rules = []
        if path != None: self.read(path)
        
    def read(self, path):
        with open(path, encoding='utf-8') as file:
            data = json.load(file)
            for item in data:
                self.rules.append(PatternRule(item['value'], ', '.join(item['globs'])))
                
    def match_any(self, filenames):
        for filename in filenames:
            match = self.match(filename)
            if match != None: return match
        return None
                
    def match(self, filename):
        for rule in self.rules:
            if re.match(rule.regex, filename):
                return rule.value
        return None
                
class PatternRule:
    '''
    A pattern rule is a value and the glob pattern(s) that will trigger it if they match.
    '''
    def __init__(self, value, glob_list_string):
        self.value = value
        self.globs = glob_list_string
        self.regex = config.make_regex(self.globs)

class Normalizer:
    '''
    Converts keys, values, and date strings to standard form
    '''
    def __init__(self):
        self.aliases_by_key = OrderedDict()
        self.known_values_by_key = OrderedDict()
        self.found_values_by_key = OrderedDict()
        self.date_fields = set(['created', 'commenced', 'last_touched', 'completed', 'paused', 'resumed', 'abandoned'])
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
        
    def add_alias(self, key, value, new_value):
        '''
        Registers a value alias for the given key. e.g., if you call
          normalizer.add_alias('Type', 'Python', 'Script')
        then
          normalizer.value('Python', 'Type')
        will have the value 'Script'.
        '''
        key = self.key(key)
        if key not in self.aliases_by_key: self.aliases_by_key[key] = OrderedDict()
        key_aliases = self.aliases_by_key[key]
        key_aliases[value] = new_value
        
    def set_known_values_for_key(self, known_value_set, key):
        self.known_values_by_key[key] = set(known_value_set)
        
    def key(self, text):
        '''
        Converts keys to snake_case
        '''
        return re.sub(r'([a-z])([A-Z])', r'\1_\2', text).replace('-', '_').lower()
        
    def value(self, text, key):
        '''
        Convertes date strings for known date fields.
        '''
        key = self.key(key)
        try:
            key_aliases = self.aliases_by_key[key]
            text = key_aliases[text]
        except KeyError:
            pass
            
        if key in self.date_fields:
            return self.date(text)
            
        try:
            known_value_set = self.known_values_by_key[key]
            if text != None and text not in known_value_set and options.verbose:
                print('**warning: "%s" is not a known value for field "%s"' % (text, key), file=stderr)
            if key not in self.found_values_by_key: self.found_values_by_key[key] = set()
            self.found_values_by_key[key].add(text)
        except KeyError:
            pass
            
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
        self.rootpath = expanduser(config.projects_root_dir.rstrip('/'))
        root = join(self.rootpath, '') # add trailing slash
        self.abspath = path
        self.relpath = path[len(root):] if path.startswith(root) else None
        
    def scan_for_project_metadata(self):
        data = OrderedDict()
        root = join(config.projects_root_dir,) # add trailing slash
        files = self.walk
        data['name'] = basename(self.abspath)
        data['abspath'] = self.abspath
        data['relpath'] = self.relpath
        data['created'] = self.normalizer.date(self.get_ctime(self.abspath))
        last_touched_file, timestamp = self.get_last_touched_file(self.abspath)
        if last_touched_file != None: last_touched_file = last_touched_file[len(self.abspath) + 1: ]
        if timestamp == None: timestamp = Folder(self.abspath).get_ctime()
        data['last_touched'] = self.normalizer.date(timestamp)
        data['last_touched_file'] = last_touched_file
        data['inferred_type'] = None
        data['inferred_status'] = None
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
        
    def get_last_touched_file(self, path=None):
        '''
        Returns the path nd timestamp of the last_touched_file file within the given folder.
        '''
        last_touched_file = None
        timestamp = None
        for root, dirs, files in self.walk(path if path != None else self.abspath):
            dirs[0:len(dirs)] = sorted(filter(lambda d: not re.match(config.skip_regex, d), dirs))
            for file in sorted(filter(lambda f: not re.match(config.skip_regex, f), files)):
                subpath = join(root, file)
                subtime = self.get_mtime(subpath)
                if  subtime != None and (timestamp == None or subtime > timestamp):
                    last_touched_file = subpath
                    timestamp = subtime
        return last_touched_file, timestamp
        
    def listdir(self, path):
        '''
        Returns the files and folders within the given folder path.
        '''
        return listdir(path)
                        
        
    def walk(self, path=None):
        return walk(path if path != None else self.abspath)

class TestableFolder(Folder):
    '''
    A testable subclass of Folder. To use it, you provide the path and a dictionary
    of fake timestamps relative to config.projects_root_dir, e.g.,
      // assuming config.projects_root_dir is '~/Projects'
      f = TestableFolder('~/Projects/2026/MyProject', {
        '2026/MyProject': (0, 1),
        '2026/MyProject/README.md': (10, 50),
      })
    '''
    def __init__(self, path, content):
        '''
        path: absolute path to the folder (which need not actually exist on disk)
        content: a dictionary mapping paths (relative to config.projects_root_dir) to a tuple
          (creation timestamp, modification timestamp)
        '''
        super(TestableFolder, self).__init__(path)
        self.content = content
        
    def exists(self, path):
        rootpath_slash = join(self.rootpath, '') # add trailing slash
        if not path.startswith(self.rootpath):
            raise ValueError('TestableFolder asked about a path (%s) not in the folder (%s)' % (path, self.rootpath))
        rpath = path[len(rootpath_slash):]
        return rpath in self.content
        
    def get_ctime(self, path):
        rootpath_slash = join(self.rootpath, '') # add trailing slash
        if not path.startswith(self.rootpath):
            raise ValueError('TestableFolder asked about a path (%s) not in the folder (%s)' % (path, self.rootpath))
        rpath = path[len(rootpath_slash):]
        return self.content[rpath][0]
        
    def get_mtime(self, path):
        rootpath_slash = join(self.rootpath, '') # add trailing slash
        if not path.startswith(self.rootpath):
            raise ValueError('TestableFolder asked about a path (%s) not in the folder (%s)' % (path, self.rootpath))
        rpath = path[len(rootpath_slash):]
        return self.content[rpath][1]
        
    def listdir(self, path):
        rootpath_slash = join(self.rootpath, '') # add trailing slash
        if not path.startswith(self.rootpath):
            raise ValueError('TestableFolder asked about a path (%s) not in the folder (%s)' % (path, self.rootpath))
        rpath = path[len(rootpath_slash):]
        rpath_slash = join(rpath, '')
        paths = sorted(self.content.keys())
        paths = map(lambda p: p[len(rpath_slash):], filter(lambda p: p.startswith(rpath_slash), paths))
        paths = filter(lambda p: dirname(p) == '', paths)
        paths = list(paths)
        return paths
        
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
    
    DATE_KEYS = set(['date', 'commenced', 'last_touched', 'completed', 'abandoned', 'paused', 'resumed'])
    STATUS_KEYS = set(['completed', 'abandoned', 'paused', 'resumed'])
    
    def __init__(self, path, folder=None, normalizer=None, type_patterns_by_key=None):
        self.folder = folder if folder != None else Folder(path)
        self.normalizer = normalizer if normalizer != None else Normalizer()
        self.type_patterns_by_key = type_patterns_by_key if type_patterns_by_key != None else dict()
        self.metadata = OrderedDict()
        root = join(expanduser(config.projects_root_dir), '') # add trailing slash
        self['name'] = basename(path)
        self['abspath'] = path
        self['relpath'] = path[len(root):] if path.startswith(root) else None
        
    def get_bucket_name(self):
        if self.relpath != None:
            return dirname(self.relpath).replace('/', '--')
        else:
            return basename(dirname(self.abspath))
        
    def scan(self, project_dir, readme_path, apply=True):
        if project_dir != None:
            self.scan_folder_metadata(project_dir, apply=apply)
            self.scan_filenames(project_dir, apply=apply)
        if readme_path != None:
            self.scan_readme_file(join(project_dir, readme_path), apply=apply)

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
        
    def scan_filenames(self, project_dir, apply=True):
        '''
        Examines the filenames in the folder (and the and the foldername itself) and
        returns any key-value pairs that are suggested by the appearance of certain
        filenames.
        '''
        data = OrderedDict()
        filenames = self.folder.listdir(project_dir)
        filenames = filter(lambda f: not re.match(config.skip_regex, f), filenames)
        filenames = sorted(filenames)
        filenames = [basename(project_dir)] + filenames
        for key, pattern_group in self.type_patterns_by_key.items():
            inferred_key = 'inferred_%s' % key
            match = pattern_group.match_any(filenames)
            if match != None:
                data[inferred_key] = match
        if apply: self.apply(data)
        return data
        
    def scan_readme_file(self, path, apply=True):
        '''
        Extracts project name, date, etc. from the given README file, optionally applies
        it to the project metadata, and returns it.
        
        Note that even if apply==True, the returned data is what was just extracted,
        not the result of merging.
        '''
        if options.verbose: print('reading %s' % path)
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
                if (value == None or value == 'None') and key in self: continue
                self[key] = value
                
    def __contains__(self, key):
        return key in self.metadata or self.normalizer.key(key) in self.metadata
                
    def __getattr__(self, key):
        try:
            return self[self.normalizer.key(key)]
        except KeyError:
            return None
                
    def __getitem__(self, key):
        try:
            return self.metadata[key]
        except KeyError:
            key = self.normalizer.key(key)
            try:
                return self.metadata[key]
            except KeyError:
                if not key.startswith('inferred_'):
                    inferred_key = 'inferred_%s' % key
                return self.metadata[inferred_key]
        
    def __setitem__(self, key, value):
        key, value = self.normalizer.item(key, value)
        self.metadata[key] = value
    
class Library:
    '''
    A library is a collection of projects.
    '''
    
    def __init__(self, normalizer=None):
        self.normalizer = normalizer if normalizer != None else Normalizer()
        self.known_values_by_key = dict()
        self.type_patterns_by_key = dict()
        self.projects = OrderedDict() # projects keyed by absolute path
        self.buckets = OrderedDict() # arrays of projects, keyed by bucket name
        
    def read_config_files(self):
        paths = sorted(glob(join(config.data_dir, '*_values.json')))
        if not options.silent: print('reading %d known-values files from %s/ folder' % (len(paths), 'config'))
        for path in paths:
            self.read_known_values_file(path)
            
        paths = sorted(glob(join(config.data_dir, '*_patterns.json')))
        if not options.silent: print('reading %d type-pattern files from %s/ folder' % (len(paths), 'config'))
        for path in paths:
            self.read_type_patterns_file(path)
            
    def read_known_values_file(self, path):
        if options.verbose: print('reading %s' % path)
        parts = splitext(basename(path))[0].split('_') # e.g., type_values.json => ['type', 'values']
        key = '_'.join(parts[0:len(parts)-1])
        known_values = KnownValues(path)
        self.known_values_by_key[key] = known_values
        for value, new_value in known_values.aliases.items():
            self.normalizer.add_alias(key, value, new_value)
        self.normalizer.set_known_values_for_key(known_values.values, key)
        
    def read_type_patterns_file(self, path):
        if options.verbose: print('reading %s' % path)
        parts = splitext(basename(path))[0].split('_') # e.g., type_values.json => ['type', 'values']
        key = '_'.join(parts[0:len(parts)-1])
        patterns = PatternRuleGroup(path)
        self.type_patterns_by_key[key] = patterns
        
    def get_project(self, path, create=True):
        if self.is_readme_path(path): path = dirname(path)
        try:
            return self.projects[path]
        except KeyError:
            if not create: return None
        project = Project(path, normalizer=self.normalizer, type_patterns_by_key=self.type_patterns_by_key)
        self.projects[path] = project
        bucket_name = project.get_bucket_name()
        try: self.buckets[bucket_name].append(project)
        except KeyError: self.buckets[bucket_name] = [project]
        return project
        
    def is_readme_path(self, path):
        return 'readme' in basename(path).lower()
        
    def scan_for_project_dirs(self, path):
        '''
        Scans the given path (i.e., the projects_root_dir) for subpaths matching the
        projects glob pattern(s).
        '''
        if config.projects == None:
            self.walk_for_readme_files(path)
        else:
            globs = re.split(r', +', config.projects) if ',' in config.projects else re.split(r' +', config.projects)
            projects = []
            regex = config.skip_regex
            for single_glob in globs:
                dirs = glob(join(path, single_glob))
                skipped_dirs = sorted(filter(lambda d: re.match(regex, basename(d)), dirs))
                considered_dirs = sorted(filter(lambda d: not re.match(regex, basename(d)), dirs))
                projects.extend(sorted(considered_dirs))
                if options.verbose:
                    for dir in skipped_dirs:
                        print('skipping %s' % dir)
            if len(projects) == 0 and not options.silent:
                print('**error: no projects found in %s' % path, file=stderr)
                print('**error: searching for paths matching %s' % config.projects, file=stderr)
            for subpath in projects:
                self.walk_for_readme_files(subpath, deep=False)
            
    def walk_for_readme_files(self, project_path, deep=True):
        for root, dirs, files in walk(project_path):
            if deep:
                dirs[0:len(dirs)] = sorted(filter(lambda f: not re.match(config.skip_regex, d)), dirs)
            else:
                dirs[0:len(dirs)] = [] # do not recurse into subdirectories
            
            files = sorted(filter(lambda f: re.match(r'_?readme.(txt|md|markdown)', f.lower()), files))
            project = self.get_project(project_path, create=True)
            if len(files) == 0:
                if not options.silent: print('**warning: no README file found in %s' % root, file=stderr)
                project.scan(root, None)
            elif len(files) > 1:
                raise FileError('found more than one README file:\n%s' % '\n'.join(map(lambda f: join(root, f), files)))
            else:
                project.scan(root, join(root, files[0]))
                
    def scan_readme_file(self, path):
        project_path = dirname(path)
        project = self.get_project(path)
        project.scan_readme_file(path)
    
    def write_buckets(self):
        data_dir = expanduser(config.data_dir)
        bucket_dir = join(data_dir, 'buckets')
        if not exists(data_dir) and not options.testing:
            if not options.silent:
                print('mkdir -p "%s"' % data_dir)
            mkdir(data_dir)
        if not exists(bucket_dir) and not options.testing:
            if not options.silent:
                print('mkdir -p "%s"' % bucket_dir)
            mkdir(bucket_dir)
            
        if not options.silent: print('writing %d json files into %s/ folder' % (len(self.buckets), bucket_dir))
        for bucket_name in sorted(self.buckets.keys()):
            self.write_bucket(bucket_dir, join(bucket_dir, '%s.json' % bucket_name), self.buckets[bucket_name])
            
    def write_bucket(self, bucket_dir, path, projects):
        data = list(map(lambda p: p.metadata, projects))
        if options.testing:
            print('NOT writing %s' % path)
            return
        if options.verbose: print('writing %s' % path)
        with open(path, 'w', encoding='utf-8') as file:
            if path.endswith('.json'):
                json.dump(data, file, indent=4, ensure_ascii=False)
            else:
                for datum in data:
                    self.write_project_text(datum, file)
                
    def write_bucket_list(self):
        path = join(expanduser(config.data_dir), 'buckets.json')
        if options.testing:
            print('NOT writing %s' % path)
            return
        if options.verbose: print('writing %s' % path)
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(list(self.buckets.keys()), file, indent=4, ensure_ascii=False)
            
def preflight(options):
    '''
    Runs the configure script to ensure that the config/*.json files
    are up to date.
    '''
    if not options.skip_preflight:
        if not options.silent: print('running bin/config.py (pass -k/--skip-preflight to bypass)')
        status = main_configure()
        if status != 0: return status
        if not options.silent: print('bin/config.py completed successfully\n')
    return 0
        

def main(args=None):
    global options
    global config
    config = Config()
    if __name__ == '__main__': options = make_parser().parse_args(args)
    else: options, unknown = make_parser().parse_known_args(args)
    
    try: sources = options.scan_sources
    except AttributeError: sources = []
        
    library = Library()
    library.read_config_files()
    
    if not options.silent: print('scanning project folders...')
    if len(sources) > 0:
        for source in map(expanduser, sources):
            if isdir(source): library.walk_for_readme_files(source, deep=False)
            else: library.scan_readme_file(source)
    else:
        for root in [config.projects_root_dir]:
            root = expanduser(root)
            if isdir(root):
                if options.verbose: print('scanning %s/' % root)
                library.scan_for_project_dirs(root)
            else:
                print('**error: %s is not a directory' % root, file=stderr)
                continue
            
    for key, values in sorted(library.normalizer.found_values_by_key.items()):
        unexpected_values = ', '.join(map(lambda s: "'%s'" % s, sorted(filter(lambda v: v != None, values))))
        if unexpected_values == '': continue
        print('**warning: field \'%s\' had unexpected values %s' % (
            key,
            unexpected_values),
            file=stderr,
        )
    library.write_buckets() # e.g., 2020.json, 2021.json, 2022.json, etc.
    # If the user only rebuilt 2026.json, do not emit a library.json containing just that one name
    if not hasattr(options, 'scan_source') or len(options.scan_sources) == 0:
        library.write_bucket_list() # e.g., library.json containing ['2020', '2021', ]
    return 0
    
if __name__ == '__main__':
    options = make_parser().parse_args()
    status = preflight(options)
    if status != 0: exit(status)
    result = main(argv[1:])
    exit(result)
