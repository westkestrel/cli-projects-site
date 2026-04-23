#!/usr/bin/env python3
'''
Reads the JSON files in the data/ folder and builds a website that
describes your projects.
'''

from argparse import ArgumentParser
from collections import OrderedDict
from datetime import datetime
from glob import glob
from os.path import basename, dirname, exists, expanduser, join
from os import mkdir
from sys import argv, exit, stderr
from time import localtime, strftime, strptime
import json
import re
import subprocess

from configure_projects_website import preflight as preflight_configure, main as main_configure
from scan_projects_for_website import Config, config, preflight as preflight_scan, Normalizer, BriefManager, main as main_scan, make_parser as make_scan_parser

options = None
def make_parser(description=__doc__):
    '''
    Create an argparse.ArgumentsParser instance with script-appropriate arguments.
    '''
    parser = make_scan_parser(description, suppress_sources=True)
    buckets = join(config.data_dir, 'buckets.json')
    parser.add_argument('-S', '--skip-scan',
        dest='skip_scan', action='store_const',
        const=True,
        default=False,
        help='preflight the config, but do not re-scan the project folders')
    parser.add_argument('-g', '--debug',
        dest='debug', action='store_const',
        const=True,
        default=False,
        help='output the jinja2 commands')
    parser.add_argument('-r', '--redact',
        dest='redact', action='store_const',
        const=True,
        default=False,
        help='redact projects, types, statuses, and tags found in redact.txt')
    parser.add_argument(
        dest='build_sources', action='store',
        default=list(),
        nargs="*",
        metavar='sources',
        help='process SOURCES rather than the files listed in %s' % buckets)
    return parser
    
class Library:
    DATE_FIELDS = set(['created', 'commenced', 'completed', 'abandoned', 'last_touched'])
    
    def __init__(self, should_read_all=True):
        self.root = OrderedDict()
        self.brief_manager = BriefManager()
        self.unclassified_types = set()
        self.unclassified_statuses = set()
        self.unclassified_tags = set()

        self.populate_core_fields()
        if should_read_all:
            self.brief_manager.read_briefs()
            self.read_all()
            
    def populate_core_fields(self):
        now = localtime(datetime.now().timestamp())
        self.root['year'] = strftime('%Y', now)
        self.root['month'] = strftime('%B', now)
        self.root['day'] = strftime('%d', now)
        self.root['weekday'] = strftime('%A', now)
        self.root['date'] = strftime(config.html_date_format, now)
        self.root['time'] = strftime('%I:%M:%S %p', now)
        self.root['time12'] = strftime('%I:%M:%S %p', now)
        self.root['time24'] = strftime('%H:%M:%S', now)
        
    def read_all(self):
        data_dir = config.data_dir
        self.read_config(join(data_dir, 'config.json'))
        
        fields = json.load(open(join(data_dir, 'fields.json'), encoding='utf-8'))
        self.DATE_FIELDS = set(map(lambda p: p[0], filter(lambda p: p[1] == 'date', fields.items())))
        
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
        has_alt_type = False
        for project in data:
        
            # if we preflighted, scan.py:main() will have applied the briefs, but
            # if not then we will need to do it here
            if hasattr(options, 'skip_preflight') and options.skip_preflight:
                self.brief_manager.update_project(project)
            elif hasattr(options, 'skip_scan') and options.skip_scan:
                self.brief_manager.update_project(project)
                
            # detect if this bucket contains any alt types
            if 'alt_type' in project: has_alt_type = True
            
            # if we have inferred_x but no x, then set x = inferred_x
            if 'created' in project and 'commenced' not in project:
                project['commenced'] = project['created']
            for field in list(project.keys()):
                if field.startswith('inferred_'):
                    true_field = field[9:]
                    if true_field not in project or project[true_field] == None:
                        project[true_field] = project[field]
                        
            if project['name'] != basename(project['relpath']):
                project['renamed'] = True
                        
            project_date = None
            normalizer = Normalizer()
            output_format = config.html_date_format
            # note that 'created' and 'last_touched' are fields of last resort, only used
            # if no other date field was found
            for field in project:
                if field not in self.DATE_FIELDS: continue
                if field == 'last_touched' or field == 'created': continue
                date_string = project[field]
                if date_string == None or date_string == 'None': continue
                
                date = normalizer.parse_date(date_string)
                if date == None:
                    raise ValueError("time data '%s' does not match format '%s'" % (date_string, "', '".join(normalizer.KNOWN_DATE_FORMATS)))
                project[field] = normalizer.date(date, output_format)
                # strftime(output_format, date).lstrip('0')
                project_date = project[field]
            if project_date == None and 'last_touched' in project: project_date = project['last_touched']
            if project_date == None and 'created' in project: project_date = project['created']
            project['date'] = project_date
            project['timestamp'] = normalizer.date(project_date, '%Y-%m-%d')
            
            for field, value in list(project.items()):
                if value == None or value == 'None':
                    del project[field]
                    
            if 'type' not in project: project_type = 'no-type'
            elif project['type'] == 'None': project_type = 'no-type'
            else: project_type = project['type']
            
            if 'status' not in project: project_status = 'no-status'
            elif project['status'] == 'None': project_status = 'no-status'
            else: project_status = project['status']
            
            if 'tags' not in project and 'tag' in project: project['tags'] = project['tag']
            if 'tags' not in project: project_tags = 'no-tag'
            elif project['tags'] == 'None': project_tags = 'no-tag'
            else: project_tags = project['tags']
            
            type_class = re.sub(r'[\W_]+', '-', project_type).lower().strip('-')
            if 'alt_type' in project:
                alt_type_class = re.sub(r'[\W_]+', '-', project['alt_type']).lower().strip('-')
            else:
                alt_type_class = ''
            for key, value in {
                '0': 'zero-', '1': 'one-', '2': 'two-', '3': 'three-', '4': 'four-',
                '5': 'five-', '6': 'six-', '7': 'seven-', '8': 'eight-', '9': 'nine-'
            }.items():
                type_class = type_class.replace(key, value)
                alt_type_class = alt_type_class.replace(key, value)
            status_class = re.sub(r'[\W_]+', '-', project_status).lower().strip('-')
            tags_class = re.sub(r'[\W_]+', '-', project_tags).lower().strip('-')
            css_classes = filter(lambda s: s != '', [type_class, alt_type_class, status_class, tags_class])
            project['css_class'] = ' '.join(css_classes).strip()
            try: type_icons = self.root['icons']['type']
            except KeyError: type_icons = {}
            try: status_icons = self.root['icons']['status']
            except KeyError: status_icons = {}
            try: tag_icons = self.root['icons']['tag']
            except KeyError: tag_icons = {}
            if project_type not in type_icons:
                self.unclassified_types.add(project_type)
            if project_status not in status_icons:
                self.unclassified_statuses.add(project_status)
            for tag in re.split(r'[, ]+', project_tags):
                if tag not in tag_icons:
                    self.unclassified_tags.add(tag)
                
            try: project['tags'] = list(filter(lambda t: t != 'no-tag', re.split(r'[, ]+', project_tags)))
            except KeyError: pass
                
        bucket_name = bucket_name.replace('--', '/').replace('--', '/')
        if has_alt_type:
            if 'has_alt_types' not in self.root: self.root['has_alt_types'] = OrderedDict()
            self.root['has_alt_types'][basename(bucket_name)] = True
        self.root['buckets'][basename(bucket_name)] = data
        
    def process_unclassified_values(self):
        self.root['unclassified'] = OrderedDict()
        if 'no-type' in self.unclassified_types: self.unclassified_types.remove('no-type')
        if 'no-status' in self.unclassified_statuses: self.unclassified_statuses.remove('no-status')
        if 'no-tag' in self.unclassified_tags: self.unclassified_tags.remove('no-tag')
        self.root['unclassified']['type'] = sorted(self.unclassified_types)
        self.root['unclassified']['status'] = sorted(self.unclassified_statuses)
        self.root['unclassified']['tag'] = sorted(self.unclassified_tags)
        
    def write(self, path):
        if options.verbose:
            if options.testing: print('NOT writing %s' % path)
            else: print('writing %s' % path)
        if options.testing: return
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(self.root, file, indent=4, ensure_ascii=False)
            
class Redactor:
    def __init__(self, redactions=True, renamings=True):
        if redactions == True:
            redactfile = join(config.data_dir, 'redact.json')
            try: redacted_words = json.load(open(redactfile, encoding='utf-8'))
            except FileNotFoundError:
                print('Fatal Error: Redaction file not found!', file=stderr)
                exit(1)
            self.redactions = set(redacted_words)
        elif redactions == None:
            self.redactions = set()
        else:
            self.redactions = set(redactions)
            
        globbed_redactions = filter(lambda r: '*' in r, self.redactions)
        regex_redactions = map(lambda s: s.replace(r'[.|()]', r'[\1]').replace('?', '.').replace('*', '.*'), globbed_redactions)
        self.redaction_regex = '^(%s)$' % '|'.join(regex_redactions)
        if self.redaction_regex == '^()$': self.redaction_regex = None
            
        if renamings == True:
            renamefile = join(config.data_dir, 'rename.json')
            try: self.renamings = json.load(open(renamefile, encoding='utf-8'))
            except FileNotFoundError:
                self.renamings = dict()
        elif renamings == None:
            self.renamings = dict()
        else:
            self.renamings = renamings
    
    def redact_library(self, lib):
        root = lib.root
        self.redact_config(root['config'])
        self.redact_buckets(root['buckets'])
        self.redact_iconic_fields(root['iconic_fields'])
        self.redact_icons(root['icons'])
        
    def redact_config(self, data):
        redactions, renamings = self.redactions, self.renamings
        for key, value in list(data.items()):
            if type(value) == str and value in renamings:
                value = renamings[value]
                data[key] = value
            if type(value) == str and value in redactions:
                data[key] = ''
        return data
                    
    def redact_buckets(self, buckets):
        redactions, renamings = self.redactions, self.renamings
        for bucket_name, bucket in list(buckets.items()):
            if bucket_name in redactions:
                self.redacting('entire bucket', 'bucket', bucket_name)
                del buckets[bucket_name]
                continue
            if bucket_name in renamings:
                del buckets[bucket_name]
                bucket_name = renamings[bucket_name]
                buckets[bucket_name] = bucket
            redacted = list(filter(lambda p: p != None, map(self.redact_project, bucket)))
            if len(redacted) == len(bucket): pass
            elif len(redacted) == 0 or bucket_name in redactions: del buckets[bucket_name]
            else: buckets[bucket_name] = redacted
        return buckets
            
    def redact_project(self, project):
        redactions, renamings = self.redactions, self.renamings
        for key in ['name', 'type', 'alt_type', 'status', 'tag']:
            try:
                if project[key] in redactions: return self.redacting(project['name'], 'key', project[key])
                if project[key] in renamings: project[key] = renamings[project[key]]
            except KeyError: pass
        if 'tags' not in project: return project
        for tag in project['tags']:
            if tag in redactions: return self.redacting(project['name'], 'tag', tag)
        tags = list(filter(lambda t: t != None, map(self.redact_tag, project['tags'])))
        project['tags'] = tags
        if self.redaction_regex != None:
            if re.match(self.redaction_regex, project['name']): return None
            if re.match(self.redaction_regex, project['description']): return None
        return project
        
    def redact_tag(self, tag):
        if tag in self.redactions: return self.redacting('project tag', 'tag', tag)
        if tag in self.renamings: return self.renamings[tag]
        return tag
            
    def redact_iconic_fields(self, iconic_fields):
        redactions, renamings = self.redactions, self.renamings
        for field_name, icon_bucket in list(iconic_fields.items()):
            if field_name in renamings:
                del iconic_fields[field_name]
                field_name = renamings[field_name]
            icon_bucket = list(filter(lambda b: b != None, map(self.redact_iconic_record, icon_bucket)))
            iconic_fields[field_name] = icon_bucket
        return iconic_fields
            
    def redact_iconic_record(self, iconic_record):
        redactions, renamings = self.redactions, self.renamings
        if iconic_record['icon'] in renamings:
            iconic_record['icon'] = renamings[iconic_record['icon']]
        if 'name' in iconic_record and iconic_record['name'] in redactions: return None
        elif 'name' in iconic_record and iconic_record['name'] in renamings:
            iconic_record['name'] = renamings[iconic_record['name']]
        if not 'names' in iconic_record: return iconic_record
        names = self.redact_list(iconic_record['names'])
        if len(names) == 1:
            del iconic_record['names']
            iconic_record['name'] = names[0]
        elif len(names) == 0:
            return None
        else:
            iconic_record['names'] = names
        return iconic_record
            
    def redact_icons(self, icons):
        redactions, renamings = self.redactions, self.renamings
        for icon_bucket in icons.values():
            for key, icon in list(icon_bucket.items()):
                if icon in renamings:
                    icon_bucket[key] = renamings[icon]
                if key in redactions:
                    del icon_bucket[key]
                elif key in renamings:
                    icon_bucket[renamings[key]] = icon_bucket[key]
                    del icon_bucket[key]
                    key = renamings[key]
        return icons
            
    def redact_list(self, words):
        redactions, renamings = self.redactions, self.renamings
        renamed = map(lambda w: renamings[w] if w in renamings else w, words)
        redacted = list(filter(lambda w: w not in redactions, renamed))
        if len(redacted) == len(words): return words
        words[0:] = redacted
        return words
        
    def redacting(self, project_name, key, value):
        print('redacting "%s" due to %s %s' % (project_name, key, value))
        return None
        
            
class Builder:
    def __init__(self, library_path, data_dir, template_dir, website_dir):
        self.failures = 0
        self.library_path = expanduser(library_path)
        self.data_dir = expanduser(data_dir)
        self.template_dir = expanduser(template_dir)
        self.website_dir = expanduser(website_dir)
        
    def build_all(self):
        template_dir, website_dir = self.template_dir, self.website_dir
        templates = sorted(glob(join(template_dir, '*')))
        if len(templates) == 0:
            print('**error: no template files found in %s' % template_dir, file=stderr)
        for template in templates:
            if 'block' in template: continue
            if 'hide-checkboxes-' in template: continue
            self.build(template, template.replace(template_dir, website_dir))
        return len(templates)
            
    def build(self, template_path, output_path):
        if template_path == output_path:
            raise ValueError('template and output path are both "%s"' % template_path)
            
        website_dir = dirname(output_path)
        if not exists(website_dir) and not options.testing:
            if options.verbose: print('mkdir %s' % website_dir)
            mkdir(website_dir)
            
        data_path = join(self.data_dir, 'library.json')
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
    if options.skip_scan:
        if not options.silent: print('running bin/config.py (pass -k/--skip-preflight to bypass)')
        status = main_configure()
        if status != 0: return status
        if not options.silent: print('bin/config.py completed successfully\n')
    elif options.skip_preflight:
        pass
    else:
        if not options.silent: print('running bin/scan.py (pass -k/--skip-preflight or -S/--skip-scan to bypass)')
        status = main_scan()
        if status != 0: return status
        if not options.silent: print('bin/scan.py completed successfully\n')
    return 0
    
def main(args=None):
    global options
    options = make_parser().parse_args(args)
    lib = Library()
    if options.redact:
        Redactor().redact_library(lib)
    
    # get these from the library rather than the global config in case
    # the redaction process has altered the values
    data_dir =  expanduser(lib.root['config']['data_dir'])
    template_dir = expanduser(lib.root['config']['template_dir'])
    website_dir = expanduser(lib.root['config']['website_dir'])
    library_path = join(data_dir, 'library.json')
    lib.write(library_path)
    builder = Builder(library_path, data_dir, template_dir, website_dir)
    count = builder.build_all()
    if not options.silent: print('updated %d files in %s' % (count, website_dir))
    
if __name__ == '__main__':
    try:
        config = Config()
        options = make_parser().parse_args()
        if options.skip_scan:
            status = preflight_configure(options)
            if status != 0: exit(status)
            status = preflight(options)
            if status != 0: exit(status)
        elif not options.skip_preflight:
            status = preflight_configure(options)
            if status != 0: exit(status)
            status = preflight_scan(options)
            if status != 0: exit(status)
            status = preflight(options)
            if status != 0: exit(status)
        exit(main(argv[1:]))
    except KeyboardInterrupt:
        print('INTERRUPTED', file=stderr)
        exit(1)
