"""Eprints CV Generator.

Usage:
  genCV.py fetch [TYPES ...] [--debug] [--refresh]
  genCV.py make <template_file> <output_types>...  [--debug]
  genCV.py (-h | --help)
  genCV.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --debug       Enable debug output.
  --refresh     Delete cached versions and do a hard refresh from eprints.

Info:

Valid options for "types" for the fetch operation are:

* all_books
* unedited_books
* edited_books
* all_peer_reviewed_articles
* peer_reviewed_articles
* other_articles
* reviews
* book_chapters
* conference_items
"""
from docopt import docopt
import logging
import pygogo as gogo
import config
from repository import Repository

app = "ePrints CV Generator 2.0"

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(log_format)

logger = gogo.Gogo(
    app,
    low_formatter=formatter,
    high_formatter=formatter,
    monolog=True).logger


def main(args):
    if args['--debug']:
        logger.setLevel('DEBUG')
    else:
        logger.setLevel('INFO')

    logger.info(app)

    if 'fetch' in args:
        repo = Repository(config, logger, args['--refresh'])
        if len(args['TYPES']) > 0:
            repo.fetch(args['TYPES'])
        else:
            repo.fetch(config.default_types)

    elif 'build' in args:
        pass


if __name__ == "__main__":
    arguments = docopt(__doc__, version=app)
    main(arguments)
