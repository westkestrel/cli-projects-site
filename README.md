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


## Command-Line Interface

*Run the scripts from the top-level folder e.g., `cd ~/Projects; bin/build.py`, **not** from within the bin folder itself.*

```
bin/configure.py
```

Reads the .txt files in the config folder and writes out corresponding .json files.

```
bin/scan.py
```

Reads the README files in your **projects** folder tree, updates the .json files in the **data** folder.
By default, this also runs the configure script. Pass -k/--skip-preflight to bypass this.

```
bin/build.py
```

Reads the .json files in the **data** folder, writes a **library.json** file, then uses that file and the **templates** folder to populate the **website** folder.
By default, this also runs the configure and scan scripts. Pass -k/--skip-preflight to bypass this.

Note that the build process makes use of the [Jinja](https://jinja.palletsprojects.com) command-line interface.
If you have not already done so, you will need to run `brew install jinja-cli` before building your site.


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
project-folder-scan process by running `bin/configure.py && bin/build.py --skip-preflight`.

## The Website

### Types and Statuses

The first section of the generated website lists the possible project types and project
status.  The values are organized into groups with icons (as described by the
*XXX_values.txt* files in the *config/* folder), and clicking a group will toggle the
visibility of matching projects in the table below. Command-clicking will toggle the
visibility of all non-matching projects.

### Projects

The second section of the website contains a table that lists all of the projects,
grouped by containing folder.  The group folders are sorted in reverse order based
on the **project** glob pattern (e.g., if projects is _20??/* Active/*_ then the
active projects will be listed before the 2026 projects, which will be listed before
the 2025 projects).

Within a group, the projects are listed in reverse chronological order.

The type and status group icons appear in a project row, and hovering over the icons will
bring up a tooltip that names the specific type or status.
