# Projects-Website Change Log

## 1.0.0 (9-Apr-2026)

The initial release.  The bin/ folder contains the following scripts

- bin/config.py: creates a data directory and converts all .txt files in config/ to .json files in data/.
- bin/scan.py: scans your projects-root folder and writes project-summary .json files to the data/ folder.
- bin/build.py: converts the contents of the data/ folder to a single unified data/library.json file, then uses that file to build a website.

The website lists all known project types and statuses, followed by a reverse-chronological table of projects.  Clicking any type or status will toggle the visibility of the corresponding projects. Command-clicking will toggle the visibility of all non-corresponding projects.
