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

*⚠️ This suite of scripts was implemented on a MacOS system. It will probably work with
minor modifications on Windows or Linux, but I have not tested it there.*

## Preparing the local web server

If you want to view your projects in a web browser it is helpful if the static projects
site is located within your web server's document root.  You accomplish this with commands
similar to the following, though you might need to make adjustments for you local
environment:

```bash
sudo mkdir /Library/WebServer/Documents/projects
sudo chown $(whoami) /Library/WebServer/Documents/projects
sudo apachectl -t && sudo apachectl restart
```

Note that this is not necessary, since you can simply double-click the *index.html* file
to open the website using the **file:** protocol rather than **http:**.

## Installation

*It does not matter where you keep these scripts, but "within your projects-root folder"
is a convenient location.*

```bash
cd $HOME/Projects
git clone github.com:westkestrel/cli-projects-website zProjectsWebsiteScripts
ln zProjectsWebsiteScripts/bin ./bin
bin/configure_projects_website.py
```

Because you do not have a *config* folder, the script will offer to create one and give
you an opportunity to say where your projects live and where you want the static website
to be created.

After the script creates your *config* folder, you should examine all of the configuration
files and make any edits that are appropriate to your projects.

To actually create the static website, run the build script. 

```bash
bin/build_projects_website.py
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

```bash
bin/configure_projects_website.py
```

Reads the .txt files in the config folder and writes out corresponding .json files. Also,
if you do not have a config/ folder yet it will offer to create one for you and populate
it with configuration files.

*Tab-completion is your friend. Type `bin/co` and press the Tab key and it will*
*autocomplete the full command name.*

```bash
bin/scan_projects_for_website.py
```

Reads the README files in your **projects** folder tree, updates the .json files in the
**data** folder. By default, this also runs the configure script. Pass -k/--skip-preflight
to bypass this.

```bash
bin/build_projects_website.py
```

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
project-folder-scan process by running `bin/build_projects_website.py --skip-scan` or (`-S`).

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

### Project type and alt_type

Most projects have a single type, and so the **type** column contains a single icon.  If
you add an **alt_type** field to the project metadata then the type column will contain
two icons. This is useful for a folder that contains both an iOS app and a desktop
application, or which contains both print design and a website.

At the moment only a single alt_type is supported.

### Project tags

You can add a **tags** field to a project. At the moment the only effect of tags is that
a project tagged *favorite* (or *favourite*) will have a heart drawn next to it in the
project table.

## Project Briefs

The project metadata is harvested from README and/or METADATA files in the individual
project dirctories.  This is convenient when you are working on a single project, but less
so when you are working on the projects website and wanting to update several projects at
once.

If you run `bin/scan_projects_for_website.py -b` (or `bin/build_projects_website.py -b`)
then the script will generate file into the *data/briefs/* folder, one file per project
group. These are simple text files listing the project-folder paths followed by all of the
metadata key-value pairs.

You can edit these files, and when you build the website with
`bin/build_projects_website.py [-S|-k]` your edits will override the values extracted from
the project README and METADATA files.  You can run `bind/scan.py -B` or `bin/build.py -B`
to update the README and METADATA files with 

## Redacting and Renaming

These scripts are intended to create a project website for your own personal consumption
as you look at your own projects.  But maybe you want to share your project history with
other people.  And maybe when you do so you want to hold back certain projects, or rename
them in some way.  To that end, in the *config/* folder you can create *redact.txt* and
*rename.txt* files, and then run the build script with **-r/--redact** to customize the
website creation.

By default your redacted website will replace the standard website. If you want to change
that, add a line to the *rename.txt* file that changes the output folder.

