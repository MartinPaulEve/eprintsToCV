# eprintsToCV

This tool will build a PDF and HTML CV from an eprints repository.

# Usage
```
Eprints CV Generator.

Usage:
  genCV.py fetch [TYPES ...] [--debug] [--refresh]
  genCV.py make OUTPUT_TYPES... [--debug]
  genCV.py (-h | --help)
  genCV.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --debug       Enable debug output.
  --refresh     Delete cached versions and do a hard refresh from eprints.

Info:

Valid options for "types" for the fetch operation, by default, are:

* all_books
* unedited_books
* edited_books
* all_peer_reviewed_articles
* peer_reviewed_articles
* other_articles
* reviews
* book_chapters
* conference_items

These can be extended using the configuration mapping system.

The tool includes two output options by default, "html" and "pdf".
```
