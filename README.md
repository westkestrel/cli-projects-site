# Projects-Website Builder

Python scripts to build a static website that describes your various projects, where
projects can be source code, collections of photographs, notes about a home renovation,
or whatever else you can think of.


The scripts assume that you have a root folder (e.g. *~/Projects/*) where you create
subfolders for projects, organized into meaningful groups (e.g., *~/Projects/2026/* group
which contains *~/Projects/2026/MyGreatApp/* and *~/Projects/2026/MyAppWebsite/*).  When
you run the build script it will will create a project-website folder whose *index.html*
file lists all of your projects, tagged with their type and status, and allows you to
filter by type and status to focus in the projects of interest to you.


## Installation

*This suite of scripts was implemented on a MacOS system. It will probably work fine
on Windows or Linux, but I have not tested it there.*

You *could* save this folder as just another project folder within your project root,
but a more convenient approach is if it *is* your project root.

For example, if you organize your projects by year you could do the following:

```
cd $HOME
git clone github.com:westkestrel/cli-projects-website Projects
cd Projects
echo '20[0-9][0-9]*' >> .gitignore
echo 'Active' >> .gitignore
echo 'Evergreen' >> .gitignore
mkdir -p 2020-2020/202{0,1,2,3,4,5,6,7,8,9} # Projects completed or abandoned in the 2020s
mkdir -p 2010-2010/201{0,1,2,3,4,5,6,7,8,9} # ... 2010s
mkdir -p 2000-2009/200{0,1,2,3,4,5,6,7,8,9} # ... 2000s (if you are that old)
mkdir Active # Projects under active development
mkdir Evergreen # Projects that will never end
```

and then edit *config/config.txt* as follows:

```
projects_root_dir: ~/Projects
projects: 20??-20??/20??/* Evergreen Active
data_dir: ./data
website_dir: /Library/WebServer/Documents/projects
```

and finally

```
sudo mkdir /Library/WebServer/Documents/projects
sudo chown $(whoami) /Library/WebServer/Documents/projects
sudo apachectl -t && sudo apachectl restart
bin/build.py # this reads your project folders and builds a website
```

and then open [http://localhost/projects](http://localhost/projects) in a web browser.


## Project Metadata

The purpose of these scripts is to build a website describing your project name, type,
status, creation and/or completion date, etc. Where does the project metadata come from?

- **name** is inferred from the project folder name
- **creation date** is inferred from the creation timestamp of the project folder
- **last-touched date** is the modification timestamp of the newest file
- **type** is inferred (if possible) from the presence of certain files (e.g., *.xcodeproj implies 'Application')
- **status** is never inferred from the filesystem, and must be stated in a README or METADATA file

Any `key: value` lines at the top of your project README (.md, .markdown, or .txt, with or
without a leading underscore) are considered project metadata.

The title of your README file (e.g., `# My Great Project`) is taken as the **name**,
though this can be overridden by a `name: This is the real name` line in the file.

The key-value pair `completed: <date>` will both capture the date and set the status to
'Completed'. Similarly, `abandoned: <date>` sets the status to 'Abandoned'.

If there is a METADATA.txt or _METADATA.txt file it will be used instead of the README
file. This allows you to keep the metadata out of the README file that will be displayed
by GitHub.

## Command-Line Interface

*Run the scripts from the top-level folder e.g., `cd ~/Projects; bin/build.py`, **not**
from within the bin folder itself.*

```
bin/configure.py
```

Reads the .txt files in the config folder and writes out corresponding .json files.

```
bin/scan.py
```

Reads the README files in your **projects** folder tree, updates the .json files in the
**data** folder. By default, this also runs the configure script. Pass -k/--skip-preflight
to bypass this.

``` bin/build.py ```

Reads the .json files in the **data** folder, writes a **library.json** file, then uses
that file and the **templates** folder to populate the **website** folder. By default,
this also runs the configure and scan scripts. Pass -S/--skip-scan to bypass the (fairly
long) scan step, or pass -k/--skip-preflight to bypass both configure and scan steps.

Note that the build process makes use of the [Jinja](https://jinja.palletsprojects.com)
command-line interface. If you have not already done so, you will need to run `brew
install jinja-cli` before building your site.


## Configuration

Your configuration file takes the form

```
title: My recent projects
author: My Name
project_root: ~/Projects
projects: 20*/* Evergreen/* Active/*
data_dir: ./data
website_dir: /Library/WebServer/Documents/projects
```

Note that if you have only changed your configuration you can skip the (relatively long)
project-folder-scan process by running `bin/build.py --skip-scan` or (`-S`).

## The Website

### Types and Statuses

The first section of the generated website lists the possible project types and project
status.  The values are organized into groups with icons (as described by the
*XXX_values.txt* files in the *config/* folder), and clicking a group will toggle the
visibility of matching projects in the table below. Command-clicking will toggle the
visibility of all non-matching projects.

### Projects

The second section of the website contains a table that lists all of the projects,
grouped by containing folder (aka the *bucket* or *group*).  The groups are sorted in
reverse order based on the **projects** glob pattern (e.g., if **projects** is _20??/* Active/*_
then the active projects will be listed before the 2026 projects, which will be listed
before the 2025 projects).

Within a group, the projects are listed in a table in reverse chronological order. The
table has columns for the project date (when it was finished, abandoned, or otherwise last
modified), the project type and status, the project name, and the project description. 
The type and status are represented by icons from te previous section, and hovering over
them presents a tooltip with the type or status text.

## Project Briefs

The project metadata is harvested from README and/or METADATA files in the individual
project dirctories.  This is convenient when you are working on a single project, but less
so when you are working on the projects website and wanting to update several projects at
once.

If you run `bin/scan.py -b` (or `bin/build.py -b`) then the script will generate files
into the *data/briefs/* folder, one file per project group. These are simple text files
listing the project-folder paths followed by all of the metadata key-value pairs.

You can edit these files, and when you build the website with `bin/build.py [-S|-k]` your
edits will override the values extracted from the project README and METADATA files.  You
can run `bind/scan.py -B` or `bin/build.py -B` to update the README and METADATA files
with 
