# ProjectSite

Python scripts to build a website that describes your various projects.

The script assumes that you have a root folder (e.g. ~/Projects/) where you create
subfolders for projects, organized into meaningful groups (e.g., ~/Projects/2026/ group
which contains ~/Projects/2026/MyGreatApp/ and ~/Projects/2026/MyAppWebsite/).  When
you run the script will will create a project-website folder whose index.html file lists
all of your projects, tagged with their type and status, and allows you to filter by
type and status to home in the projects of interest to you.

## Usage

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
projects: ~/Projects
data: data
output: ~/Sites/projects
```

## The Website

### Types and Statuses

The first section of the generated website lists the possible project types and project
status.  The values are organized into groups with icons (as described by the
*XXX_values.txt* files in the *config/* folder), and clicking a group will toggle the
visibility of matching projects in the table below. Command-clicking will toggle the
visibility of all non-matching projects.

### Projects

The second section of the website contains a table that lists all of the projects in
reverse chronological order (i.e., newest projects on top).  The type and status group
icons appear in a project row, and hovering over the icons will bring up a tooltip that
names the specific type or status.
