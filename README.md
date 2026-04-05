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
bin/update.py
```

Reads the README files in your **projects** folder tree (creating boilerplate files if absent), updates the .txt files in the **data** folder, and then generates static HTML files to view your project descriptions into the **output** folder.

## Configuration

Your configuration file takes the form

```
title: My recent projects
projects: ~/Projects
data: data
output: ~/Sites/projects
```

