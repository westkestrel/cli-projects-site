# Projects-Website Change Log

## 1.2.0 (21-Apr-2026)

### Improved installation experience

You can now install the package wherever you want and then simply symlink the *bin/* folder into your *~/Projects* folder. Then from with your projects folder you run any one of

```
mkdir config # optional
bin/configure_projects_website.py
bin/scan_projects_for_website.py
bin/build_projects_website.py
```

The first time you run you will be prompted to populate the config folder you just created. If you did not create a config folder, you will be prompted to create (and populate) one next to the bin folder in its original, non-symlinked location.

### New script names

The script names are now much more verbose (e.g., *build_projects_website.py* rather than just *build.py*). This means that rather than the symlink described above you can just add the location of the *bin/* folder to your **PATH** environment variable and run the commands from any directory.

### Improved user experience

#### Filters

You can now long-press in addition to Command-clicking to trigger the "select this and deselect everything else" behaviour, which improves the phone experience where there is no Command key.

If a project has both a **type** and an **alt_type** then it will be shown if either value is selected in the filter area (in the previous version, if a project had two types then de-selecting either value would result in the project being hidden).

#### Project List

There is a list of project-group name links that the user can use to jump to specific project groups.  This navigation does affect browser history (so the user can the the back button to return to the previous scroll location) but does *not* affect the page URL.

The table layout on the website has been replaced with a flexbox-based layout that leads to a much better experience when viewing the page on a phone.

The project-group names are now checkbox labels rather than mere DOM elements with click handlers. This improves the site accessibility for people who  use a screen reader. *Unfortunately there does not appear to be a way to trigger either a command-click or a long-press using a screen reader.*

The expanding and collapsing project groups is now animated, which makes the behavior more understandable.

#### Tags

If you add the metadata **tags: favorite** (or **favourite**) to a project then it will get a heart drawn in front of the project description. You use the tags_values.txt config file to define other tags and their icons.

### Redaction

Normally you run this script to create a website for your personal consumption. If you run the build script with `-r/--redact` then the *redact.txt* and *rename.txt* config files will be used to create a pruned and polished version for public consumption.

### Improved code reusability

The JavaScript code was completely rewritten into a more maintainable format.  In particular, each piece of functionality (using filter checkboxes to show & hide data rows, clicking section headers to collapse and expand the sections, recalling checkbox state across page reloads, etc.) is now encapsulated in its own isolated and well-documented .js file that can be used in other projects.

## 1.1.0 (17-Apr-2026)

### Project Briefs

Add support for "project briefs". Running the scan or build script with -b or --update-briefs will create a data/briefs/ folder similar to the data/buckets/ folder... except that this file is plain text and lists the metadata for each project in the bucket.  You can edit this metadata and when you re-run the build script your edits will trump any values found in the project folders. You can also run with -B or –export-briefs to copy your edits back into the README or METADATA files in the project directories.

Make the code that detects last-modified-files more intelligent. Specifically, it now ignores macOS .DS_Store and Icon? Files, and the README and METADATA files that the script might update.

### Dates

The standard date format in the web page is *d-mmm-yyyy* (e.g., "1-Jan-2025"). You can change this via the new **html_date_format** configuration property.

You can configure **limit_dates_to_project_year: true** so that the scan script will ignore files touched after the project year when determining the last-touched file. This is useful to avoid having your dates changed when you edit a info file years after the project has been completed.

### Alternate Types

You can specify an **alt_type** in your metadata to give your project two type icons. This is useful for projects that contain both websites and marketing brochures, or both iOS apps and web apps.

### Version Control

The project table now has a revision control column that lists what form of version control (git, Subversion, etc.) the project uses.

### Table Sorting

You can now configure whether the projects or sorted alphabetically or reverse-chronologically. Alphabetic sorting is case- and diacritical-insensitive.

### Configuration

Add support for a new **fields.txt** configuration file that lists the metadata that you care about. The key purpose of this file is that the fields in the briefs files will have the same order that they appear in this configuration file.

Add more configuration fields. To see all of the new options, move aside your *config/* folder and re-run the configure script to regenerate a new set of starting files.

## 1.0.0 (9-Apr-2026)

The initial release.  The bin/ folder contains the following scripts

- **configure.py**: creates a data directory and converts all .txt files in *config/* to .json files in *data/*.
- **scan.py**: scans your projects-root folder and writes project-summary .json files to the *data/* folder.
- **build.py**: converts the contents of the *data/* folder to a single unified data/library.json file, then uses that file to build a website.

The website lists all known project types and statuses, followed by a reverse-chronological table of projects organized into "buckets" (all the project folders within a given parent folder; parent folders are typically named after the year but can have any name).  Clicking any type or status will toggle the visibility of the corresponding projects. Command-clicking will toggle the visibility of all non-corresponding projects.

When you first run the **configure** script it will offer to create a *config/* folder for you, which will contain the following files:

- **config.txt**: contains various key-value pairs to configure the system
- **status_values.txt**: a list of all porject statuses, their descriptions, and emoji icons to represent them
- **ype_values.txt**: a list of all project types, their descriptions, and emoji icons to represent them
- **type_patterns.txt**: glob patterns corresponding to various project types. If a project matches the pattern it will be be inferred to be of that project type.
