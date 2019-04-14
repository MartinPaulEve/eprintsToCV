"""Eprints CV Generator.

Usage:
  genCV.py fetch [TYPES ...] [--debug] [--refresh]
  genCV.py make OUTPUT_TYPES... [--citeproc] [--debug]
  genCV.py (-h | --help)
  genCV.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --debug       Enable debug output.
  --refresh     Delete cached versions and do a hard refresh from eprints.
  --citeproc    Use new experimental citeproc mode

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
"""
from docopt import docopt
import logging
import pygogo as gogo
import config
from citeproc import CiteProc
from repository import Repository
from templateBuilder import TemplateBuilder

app = "ePrints CV Generator 2.0"

log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
formatter = logging.Formatter(log_format)

logger = gogo.Gogo(
    app,
    low_formatter=formatter,
    high_formatter=formatter,
    monolog=True).logger


def main(args):
    if '--debug' in args and args['--debug']:
        logger.setLevel('DEBUG')
    else:
        logger.setLevel('INFO')

    logger.info(app)

    repo = Repository(config, logger, args['--refresh'])

    citeproc = None

    try:
        # start the citeproc server if the flag is passed
        if '--citeproc' in args and args['--citeproc']:
            citeproc = CiteProc(config, logger)

        if 'fetch' in args and args['fetch']:
            if len(args['TYPES']) > 0:
                repo.fetch(args['TYPES'])
            else:
                repo.fetch(config.default_types)

        elif 'make' in args and args['make']:
            template_builder = TemplateBuilder(repo, config, logger)
            template_builder.build(args['OUTPUT_TYPES'])
    except:
        logger.error("An uncaught error was thrown.")
    finally:
        # always try to shutdown the citeproc server
        if '--citeproc' in args and args['--citeproc']:
            citeproc.shutdown()


if __name__ == "__main__":
    arguments = docopt(__doc__, version=app)
    main(arguments)
