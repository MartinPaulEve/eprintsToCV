"""Eprints CV Generator.

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

This tool requires a working copy of citeproc-js-server https://github.com/zotero/citeproc-js-server.
"""
import sys

from docopt import docopt
import logging
import pygogo as gogo
import config
from citeproc import CiteProc
from repository import Repository

app = "ePrints CV Generator 2.2"

from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(log_format)

logger = logging.getLogger("rich")

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)



def main(args):
    if '--debug' in args and args['--debug']:
        logger.setLevel('DEBUG')
    else:
        logger.setLevel('DEBUG')

    logger.info(app)

    repo = Repository(config, logger, args['--refresh'])
    citeproc = CiteProc(repo, config, logger)
    try:
        # start the citeproc server if the flag is passed
        if 'fetch' in args and args['fetch']:
            if len(args['TYPES']) > 0:
                repo.fetch(args['TYPES'])
            else:
                repo.fetch(config.default_types)

        elif 'make' in args and args['make']:
            citeproc.start()
            citeproc.build(args['OUTPUT_TYPES'])
    finally:
        # always try to shutdown the citeproc server
        citeproc.shutdown()


if __name__ == "__main__":
    arguments = docopt(__doc__, version=app)
    main(arguments)
