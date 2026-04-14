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
from time import localtime, strftime, strptime
import json
import re
import subprocess

from configure import Config, preflight as preflight_configure, main as main_configure, make_parser as make_configure_parser
    
config = None
options = None
def make_parser(description=__doc__, suppress_sources=False):
    briefs_dir = join(join(config.data_dir, 'briefs'), '')
    bucket_dir = join(join(config.data_dir, 'buckets'), '')
    projects = list(map(lambda g: join(config.projects_root_dir, g), re.split(r'[\s,]+', config.projects)))
    description = description.replace('data/buckets/', bucket_dir)
    description = re.sub('.*~/Projects.*\n', '    ' + '\n    '.join(projects) + '\n', description)
    parser = make_configure_parser(description=description, suppress_sources=True)
    parser.add_argument('-b', '--update-briefs',
        dest='update_briefs', action='store_const',
        const=True,
        default=False,
        help='create/update summary files in %s folder' % briefs_dir)
    parser.add_argument('-B', '--export-briefs',
        dest='export_briefs', action='store_const',
        const=True,
        default=False,
        help='copy the metadata in %s folder back into the README files' % briefs_dir)
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
            if match != None: return match, filename
        return None, None
                
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

    DATE_FIELDS = set(['created', 'commenced', 'last_touched', 'completed', 'paused', 'resumed', 'abandoned'])

    def __init__(self):
        self.aliases_by_key = OrderedDict()
        self.known_values_by_key = OrderedDict()
        self.found_values_by_key = OrderedDict()
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
            
        if key in self.DATE_FIELDS:
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
        
    def date(self, text, format='%Y/%m/%d'):
        '''
        Accepts date strings in a variety of formats (and integers and floats representing
        seconds since epoch) and returns an ISO8601 date string (e.g., '2026/01/01')
        '''
        if text == None:
            return None
        if type(text) == int or type(text) == float:
            return strftime(format, localtime(text))
            
        text = re.sub(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),? *', '', text)
        match = re.match(r'(\d{1,2})-(\w{3,})-(\d{4})', text)
        if match:
            day, month, year = match.group(1, 2, 3)
            text = '%s/%s/%s' % (year, self.months[month.lower()[0:3]], day.rjust(2, '0'))
        match = re.match(r'(\w{3,}) (\d{1,2}), (\d{4})', text)
        if match:
            month, day, year = match.group(1, 2, 3)
            text = '%s/%s/%s' % (year, self.months[month.lower()[0:3]], day.rjust(2, '0'))
        text = text.replace('-', '/')[0:10]
        
        if format != '%Y/%m/%d':
            text = strftime(format, strptime(text, '%Y/%m/%d'))
        
        return text
        
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
        self.add_rcs_metadata(data)
        self.add_cvs_metadata(data)
        self.add_subversion_metadata(data)
        self.add_git_metadata(data)
        data['inferred_type'] = None
        data['inferred_status'] = None
        return data
        
    def add_rcs_metadata(self, data):
        '''
        RCS (Revision Control System) is one of the first revision-tracking packages.
        We are unlikely to encounter any projects that use it, but will check.
        '''
        rcspath = join(self.abspath, 'RCS')
        rcsglob = join(self.abspath, '*,v')
        if not self.exists(rcspath) and len(self.glob(rcsglob)) == 0:
            return
        data['versioning'] = 'rcs'
        
    def add_cvs_metadata(self, data):
        '''
        CVS (Concurrent Versions System) is the most widely-useed revision-tracking
        package circa 1990, so we will detect when it is being used by a project.
        '''
        cvspath = join(self.abspath, 'CVS')
        if not self.exists(cvspath):
            return
        data['versioning'] = 'cvs'
        
    def add_subversion_metadata(self, data):
        '''
        Subversion is the most widely-useed revision-tracking package circa 2000,
        so we will detect when it is being used by a project.
        '''
        svnpath = join(self.abspath, '.subversion')
        if not self.exists(svnpath):
            return
        data['versioning'] = 'subversion'
        
    def add_git_metadata(self, data):
        '''
        Git is the most widely-useed revision-tracking package circa 2025,
        so we will detect when it is being used by a project.
        '''
        gitpath = join(self.abspath, '.git')
        if not self.exists(gitpath):
            return
        data['versioning'] = 'git'
        configpath = join(gitpath, 'config')
        if not self.exists(configpath):
            return
        next_url_is_origin = False
        with open(configpath) as file:
            for line in map(str.strip, file):
                if line == '[remote "origin"]':
                    next_url_is_origin = True
                elif next_url_is_origin and line.startswith('url = '):
                    next_url_is_origin = False
                    data['git_origin'] = line[6:]
                    try: data['git_host'] = re.match(r'[^@]+@([\w.-]+)', line[6:]).group(1)
                    except AttributeError: pass # match failed
        
    def exists(self, path):
        '''
        Returns whether a file or folder exists at the given path.
        '''
        return exists(path)
        
    def glob(self, pattern):
        '''
        Returns the files that match a glob pattern.
        '''
        return glob(pattern)
        
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
                if re.match(r'^Icon\W?$', file): continue # a MacOS-specific filename containing a nonprintable character
                if file == '.DS_Store': continue # a MacOS-specific file used by Finder
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
        
    def glob(self, pattern):
        rootpath_slash = join(self.rootpath, '') # add trailing slash
        if not pattern.startswith(self.rootpath):
            raise ValueError('TestableFolder asked about a path (%s) not in the folder (%s)' % (pattern, self.rootpath))
        pattern = pattern[len(rootpath_slash):]
        regex = pattern.replace('.', '[.]').replace('?', '[^/]').replace('*', '[^/]*')
        return list(filter(lambda p: re.match(regex, p), self.content.keys()))
        
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
    STATUS_KEYS = set(['completed', 'delivered', 'abandoned', 'paused', 'resumed'])
    
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
            return dirname(self.relpath)
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
            (match, filename) = pattern_group.match_any(filenames)
            if match != None:
                data[inferred_key] = match
                data[inferred_key + '_triggering_filename'] = filename
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
        
        Metadata in a README file consists of lines of the forms
            # value         (only in line 1, and the key is inferred to be "name")
            key: value      (basic key-value pair)
            *key: value*    (italicized key-value pair; italics will be striped)
        This "x: y" structure is such a common way to write that is possible that such
        lines might occur farther down in the body of the file and not be intended as
        project metadata.  To avoid accidentally including such lines, this script stops
        any (non-blank) lines that do NOT match one of these patterns.
        
        Note that even if apply==True, the returned data is what was just extracted,
        not the result of merging.
        '''
        data = OrderedDict()
        for i, line in enumerate(map(str.strip, content), start=1):
        
            if i == 1 and line.startswith('# '):
                self['name'] = line[2:]
                continue
                
            line = re.sub(r'#.*', '', line).strip('*') # strip comments and italics
            if line == '': continue
            
            match = re.match(r'([\w-]+):\s*(.+)', line)
            if match:
                key, value = match.group(1, 2)
                nkey, nvalue = self.normalizer.item(key, value)
                if nkey in self.STATUS_KEYS and 'status' not in data:
                    data['status'] = key[0].upper() + key[1:]
                data[nkey] = nvalue
            elif i > 1:
                break
                
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
                
    def items(self):
        return self.metadata.items()
                
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
        
    def __len__(self):
        return len(self.metadata)
        
    def __str__(self):
        return 'project "%s" with %d key-value pairs' % (self.name, len(self.metadata))
    
class Library:
    '''
    A library is a collection of projects.
    '''
    
    def __init__(self, normalizer=None):
        self.normalizer = normalizer if normalizer != None else Normalizer()
        self.fields_types = OrderedDict()
        self.known_values_by_key = dict()
        self.type_patterns_by_key = dict()
        self.projects = OrderedDict() # projects keyed by absolute path
        self.buckets = OrderedDict() # arrays of projects, keyed by bucket name
        self.brief_manager = BriefManager()
        
    def read_config_files(self):
        data_dir = expanduser(config.data_dir)
        
        path = join(data_dir, 'fields.json')
        if not options.silent: print('reading field order and types from %s' % path)
        self.field_types = json.load(open(path, encoding='utf-8'))
        
        paths = sorted(glob(join(data_dir, '*_values.json')))
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
        for key in self.field_types: # establish field orders (note that a project uses an OrderedDict)
            if key not in project:
                project[key] = None
        
        self.projects[path] = project
        bucket_name = project.get_bucket_name()
        try: self.buckets[bucket_name].append(project)
        except KeyError: self.buckets[bucket_name] = [project]
        return project
        
    def is_readme_path(self, path):
        lowercased = basename(path).lower()
        return 'readme' in lowercased or 'brief' in lowercased
        
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
            
            files = sorted(filter(lambda f: re.match(r'_?(metadata|readme).(txt|md|markdown)', f.lower()), files))
            if len(files) > 1 and 'metadata' in ','.join(files).lower():
                files = list(filter(lambda f: 'metadata' in f.lower(), files)) # ignore README if METADATA found
            project = self.get_project(project_path, create=True)
            if len(files) == 0:
                if options.verbose: print('**warning: no README file found in %s' % root, file=stderr)
                project.scan(root, None)
            elif len(files) > 1:
                raise FileError('found more than one README file:\n%s' % '\n'.join(map(lambda f: join(root, f), files)))
            else:
                project.scan(root, join(root, files[0]))
                
    def scan_readme_file(self, path):
        project_path = dirname(path)
        project = self.get_project(path)
        project.scan_readme_file(path)
        
    def read_briefs(self):
        '''
        Reads the text files in the data/briefs/ folder and returns a dictionary
        mapping project relative pathnames to project metadata.
        '''
        return self.brief_manager.read_briefs()
        
    def apply_briefs(self, briefs):
        '''
        Updates the library projects with the given metadata (a dictionary mapping
        relative project pathnames to dictionaries of key-value pairs).
        '''
        if briefs == None: return
        root_dir = expanduser(config.projects_root_dir)
        data_dir = config.data_dir
        bucket_dir = join(data_dir, 'buckets')
        glob_path = join(bucket_dir, '*.json')
        for relpath, brief in briefs.items():
            abspath = join(root_dir, relpath)
            proj = self.get_project(abspath, create=False)
            if proj == None:
                print('**warning: %s: %s\nno such project "%s" in %s' % (
                    brief.source_file, brief.source_line,
                    relpath,
                    join(bucket_dir, dirname(relpath).replace('/', '--')) + '.json'),
                    file=stderr)
            else:
                self.brief_manager.update_project(proj)
                
    def write_briefs_to_data_dir(self):
        '''
        Takes the metadata from the loaded projects and writes it to files in the
        data/briefs/ folder.
        '''
        data_dir = expanduser(config.data_dir)
        briefs_dir = join(data_dir, 'briefs')
        if not exists(briefs_dir) and not options.testing:
            if not options.silent:
                print('mkdir -p "%s"' % briefs_dir)
            recursive_mkdir(briefs_dir)
            
        if not options.silent: print('writing %d text files into %s/ folder' % (len(self.buckets), briefs_dir))
        for bucket_name in sorted(self.buckets.keys()):
            self.write_bucket(briefs_dir, join(briefs_dir, '%s.txt' % bucket_name), self.buckets[bucket_name])
            
    def write_briefs_to_project_dir(self):
        '''
        Takes the metadata from the data/briefs/ folder and writes it into the README
        and/or METADATA files in the project directories.
        '''
        briefs = self.read_briefs()
        for relpath, brief in briefs.items():
            self.write_brief_to_project_dir(brief, relpath)
    
    def write_brief_to_project_dir(self, brief, relpath):
        '''
        Writes the given brief key-value pairs into the METADATA or README file of
        the project at the given path.
        
        If no README or METADATA file exists, a README will be created.
        If a METADATA file exists, it will be updated.
        If not, but a README file exists, then that file will be updated.
        If neither exist, a README will be created.
        
        As a special case, if there is a README file but the metadata indicates that
        the project lives on GitHub then a METADATA file will be created.
        '''
        root_dir = expanduser(config.projects_root_dir)
        project_dir = join(root_dir, relpath)
        folder = Folder(project_dir)
        if not folder.exists(project_dir):
            print('**error: project path %s does not exist' % project_dir, file=stderr)
            return
        metadata_paths = list(filter(lambda p: p.endswith('.md') or p.endswith('.txt'), glob(join(project_dir, '*METADATA*.*'))))
        if len(metadata_paths) > 1:
            print('**error: multiple METADATA paths:\n  %s' % '\n  '.join(metadata_paths))
            return
        if len(metadata_paths) == 0 and 'git_host' in brief:
            metadata_paths.append(join(project_dir, '_METADATA.txt'))
        if len(metadata_paths) == 1:
            self.write_brief_to_file(brief, metadata_paths[0])
            return
        readme_paths = list(filter(lambda p: p.endswith('.md') or p.endswith('.txt'), glob(join(project_dir, '*README*.*'))))
        if len(readme_paths) == 0:
            readme_paths.append(join(project_dir, '_README.md'))
        if len(readme_paths) > 1:
            print('**error: multiple README paths:\n  %s' % '\n  '.join(readme_paths))
            return
        self.write_brief_to_file(brief, readme_paths[0])
        
    def write_brief_to_file(self, brief, path):
        is_markdown = path.endswith('.md') or path.endswith('.markdown')
        try:
            with open(path, encoding='utf-8') as file:
                content = list(file)
        except FileNotFoundError:
            content = list()
            
        new_content = self.write_brief_to_content(brief, content, is_markdown)
        pruned_content = list(filter(lambda s: s != '', map(str.strip, content)))
        pruned_new_content = list(filter(lambda s: s != '', map(str.strip, new_content)))
        if pruned_content == pruned_new_content:
            return # do not update if the only changes are whitespace
        if len(pruned_content) == 0 and len(pruned_new_content) == 1 and pruned_new_content[0].startswith('#'):
            return # or if there was no old file, and the new file only defined the project name
        
        if options.testing:
            print('NOT updating %s' % path)
            return
        if not options.silent: print('updating %s' % path)

        try:
            with open(path, 'w', encoding='utf-8') as file:
                for line in new_content:
                    print(line.rstrip(), file=file)
        except PermissionError:
            print('**error: not permitted to write to %s' % path)
                
    SUPPRESSED_METADATA_KEYS = set([
        'name', 'abspath', 'relpath',
        'created', 'last_modified', 'last_touched', 'last_touched_file',
        'inferred_type', 'inferred_status'
    ])
    
    def write_brief_to_content(self, brief, content, is_markdown):
        new_content = []
        new_content.append('# %s' % brief.name)
        new_content.append('')
        line_pattern = '*%s: %s*' if is_markdown else '%s: %s'
        for key, value in brief.items():
            if not key in self.SUPPRESSED_METADATA_KEYS:
                new_content.append(line_pattern % (key, value))
        new_content.append('')
                
        copy_all_lines = False
        for i, line in enumerate(map(str.rstrip, content), start=1):
            if copy_all_lines:
                new_content.append(line)
                continue
            if i == 1 and line.startswith('# '): continue
            if line == '': continue
            if re.match(r'^\*?[\w. -]+:\s+.+', line):
                continue
            copy_all_lines = True
            new_content.append(line)
        
        return new_content
         
    def write_buckets(self):
        data_dir = expanduser(config.data_dir)
        bucket_dir = join(data_dir, 'buckets')
        if not exists(bucket_dir) and not options.testing:
            if not options.silent:
                print('mkdir -p "%s"' % bucket_dir)
            recursive_mkdir(bucket_dir)
            
        if not options.silent: print('writing %d json files into %s/ folder' % (len(self.buckets), bucket_dir))
        for bucket_name in sorted(self.buckets.keys()):
            self.write_bucket(bucket_dir, join(bucket_dir, '%s.json' % bucket_name), self.buckets[bucket_name])
            
    def write_bucket(self, bucket_dir, path, projects):
        data = list(map(lambda p: p.metadata, projects))
        if options.testing:
            print('NOT writing %s' % path)
            return
        bucketfile_dir = dirname(path)
        if options.verbose and not exists(bucketfile_dir): print('mkdir -p %s' % bucketfile_dir)
        if options.verbose: print('writing %s' % path)
        if not exists(bucketfile_dir): recursive_mkdir(bucketfile_dir)
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
            
    # There are some fields that we never want to include in the brief because the user
    # should never edit them.
    FIELDS_EXCLUDED_FROM_BRIEF = set(['path', 'abspath', 'relpath'])
    
    # Fenerally we exclude keys with value = None, but some fields we want to include
    # even if None as a signal to the user that they should provide a value.
    FIELDS_ALWAYS_INCLUDED_IN_BRIEF = set(['description', 'type', 'status'])
    
    def write_project_text(self, project_dict, file):
        '''
        Writes out the project key-value pairs as plain text.  Note that the given
        project is a dictionary, not an instance of the Project class.
        '''
        print('# %s' % project_dict['relpath'], file=file)
        for key, value in project_dict.items():
            if (value == None or value == 'None') and key not in self.FIELDS_ALWAYS_INCLUDED_IN_BRIEF:
                continue
            elif key not in self.FIELDS_EXCLUDED_FROM_BRIEF:
                if value != None and key in self.normalizer.DATE_FIELDS: value = self.normalizer.date(value, '%d-%b-%Y').lstrip('0')
                print('%s: %s' % (key, value), file=file)
        print("", file=file)
        
class BriefManager:
    '''
    "Briefs" are text files in the data directory, produced by passing -b/--update-briefs
    to the script.  Their primary purpose is convenience; the user can read the metadata
    for all projects in a bucket in a single place rather than having to open each
    project's README or METADATA file separately.
    
    The user can also edit the briefs files, and can run with -B/--export-briefs to write
    those changes back into the original README or METADATA files.
    
    Also, when the user runs the scan (or build) scripts the edits will override values
    found in the README or METADATA files.
    '''
    
    def __init__(self):
        self.briefs_by_relpath = OrderedDict()
        self.have_delivered_overwrite_warning = False
        self.last_reported_file_and_line = None
        
    def read_briefs(self, brief_dir=None, data=None):
        '''
        Reads the brief files in the given directory, or ./data/briefs/ if none is given.
        The resulting briefs are stored in the given dictionary keyed by relative path,
        or in self.briefs_by_relpath if no dictionary is given. 
        '''
        if data == None:
            data = self.briefs_by_relpath
        if brief_dir == None:
            data_dir = expanduser(config.data_dir)
            brief_dir = join(data_dir, 'briefs')
        paths = recursive_glob('*.txt', brief_dir)
        if len(paths) == 0: return None
        for path in paths:
            self.read_brief(path, data)
        return data
        
    def read_brief(self, path, data=None):
        '''
        Reads a single brief file and stored the resulting brief records in the given
        dictionary.
        '''
        if type(path) != str: raise ValueError('readBrief() first argument should be a path string, not %s' % type(path))
        if data == None:
            data = self.briefs_by_relpath
        with open(path, encoding='utf-8') as file:
            data = self.process_brief(file, path, data)
        return data
                
    def process_brief(self, content, path=None, data=None):
        '''
        Processes the given content (an collection of lines of text) and returns a
        dictionary mapping project relative pathnames to project metadata.
        '''
        if path == None:
            path = 'stdin'
        if data == None:
            data = OrderedDict()
        proj = None
        data_dir = expanduser(config.data_dir)
        briefs_dir = join(data_dir, 'briefs')
        bucket_name = splitext(path[len(briefs_dir) + 1:])[0]
        for i, line in enumerate(map(str.strip, content)):
            if line == '':
                continue
            elif line.startswith('# '):
                project_relpath = line[2:].strip()
                project_abspath = join(config.projects_root_dir, project_relpath)
                brief = Project(project_abspath)
                brief.source_file = path
                brief.source_line = i
                data[project_relpath] = brief
            else:
                try:
                    key, value = re.match(r'([^:]+): (.+)', line).group(1, 2)
                except AttributeError:
                    print('**error: %s: %d\n%s\nMalformed line' % (path, i, line), file=stderr)
                    continue
                brief[key] = value
                if key.lower() in Project.STATUS_KEYS and 'status' not in brief:
                    brief['status'] = key[0].upper() + key[1:]
        return data
        
    def update_project(self, project, brief=None):
        '''
        Applies the contents of a record from the brief text files to a project.
        '''
        if brief == None:
            try: brief = self.briefs_by_relpath[project['relpath']]
            except KeyError: return
        
        for key, brief_value in brief.metadata.items():
            if key == 'source_file' or key == 'source_line': continue
            if key == 'abspath' or key == 'relpath': continue
            if brief_value == None or brief_value == 'None' or brief_value == 'null': continue
            try: value = project[key]
            except KeyError: value = None
            if brief_value == value: continue
            file_and_line = '%s: %s' % (brief.source_file, brief.source_line)
            if file_and_line != self.last_reported_file_and_line:
                print('**warning: %s for project %s' % (file_and_line, project['relpath']))
                self.last_reported_file_and_line = file_and_line
            print('**warning: overwriting "%s" value "%s" with "%s"' % (
                key, value, brief_value),
                file=stderr)
            if not self.have_delivered_overwrite_warning:
                self.have_delivered_overwrite_warning = True
                briefs_dir = join(config.data_dir, 'briefs')
                briefs_glob = join(briefs_dir, '*.txt')
                print('(run with -b to update %s files, or -B to update README and METADATA files in %s)'
                    % (briefs_glob, config.projects_root_dir), file=stderr)
            project[key] = brief_value
            
def recursive_glob(pattern, starting_dir):
    results = []
    results.extend(glob(join(starting_dir, pattern)))
    for root, dirs, files in walk(starting_dir):
        for d in dirs:
            results.extend(glob(join(join(root, d), pattern)))
    return sorted(results)
    
def recursive_mkdir(path):
    parent = dirname(path)
    if parent != '' and parent != '/' and not exists(parent):
        recursive_mkdir(parent)
    mkdir(path)
            
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
    
    if options.export_briefs:
        library.write_briefs_to_project_dir()
        return 0
        
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
        known_values = library.normalizer.known_values_by_key[key]
        found_values = filter(lambda v: v != None and v != 'None', values)
        unexpected_values = filter(lambda v: v not in known_values, found_values)
        unexpected_values_string = ', '.join(unexpected_values)
        if unexpected_values_string == '': continue
        print('**warning: field \'%s\' had unexpected values %s' % (
            key,
            unexpected_values_string),
            file=stderr,
        )
    
    library.apply_briefs(library.read_briefs())
    if options.update_briefs:
        library.write_briefs_to_data_dir()
        
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
