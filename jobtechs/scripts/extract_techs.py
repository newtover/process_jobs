"""A script to generate a list of products we are interested in found in job descriptions.

It takes a list of urls from infile (stdin by default) and returns a |-separated output
for each url. The script requires a file with techs we are searching for, the file is
specified by --techs-file option. The urls that led to exceptions are written to a separate
file, configured by --errors-file.
"""

import argparse
import logging
import multiprocessing as mp
import pathlib
import sys
import time
import threading
from urllib.parse import urlparse

from jobtechs.common import iter_good_lines
from jobtechs.fetcher import ThrottledFetcher
from jobtechs.parser import NETLOC_TO_PARSER_MAP, TermsExtractor, PageParser

G_LOG = logging.getLogger(__name__)

class TechsExtractionRunner:
    """Class containing the functionality of running the techs extraction process."""
    # pylint: disable=no-self-use

    def __init__(self, terms_path='techs.txt', errors_path='failed_urls.txt', save_pages_to=None):
        self.save_pages_to = save_pages_to
        self.terms_path = terms_path
        self.errors_path = errors_path
        self._q_out = self._q_err = None
        self._init_queues()
        self._fetchers = {}
        self._init_fetchers()
        self._writers = []
        self._init_writers()

    def make_terms_extractor(self, terms_path):
        """A factory method for instantiating a terms extractor."""
        return TermsExtractor(terms_path)

    def make_queue(self):
        """A factory method for the queue."""
        return mp.Queue()

    def _init_queues(self):
        self._q_out = self.make_queue()
        self._q_err = self.make_queue()

    def _init_fetchers(self):
        terms_extractor = self.make_terms_extractor(self.terms_path)
        # add specific parsers for job aggregators
        self._fetchers = {
            netloc:
                ThrottledFetcher(
                    parser=parser_cls(save_pages_to=self.save_pages_to),
                    terms_extractor=terms_extractor,
                    q_out=self._q_out, q_err=self._q_err,
                    max_workers=5)
            for netloc, parser_cls in NETLOC_TO_PARSER_MAP.items()
        }
        # add general parser for other pages
        generic_parser = PageParser(
            save_pages_to=self.save_pages_to,
            agg_parsers=[fetcher.parser for fetcher in self._fetchers.values()]
        )
        self._fetchers['default'] = \
            ThrottledFetcher(
                parser=generic_parser,
                terms_extractor=terms_extractor,
                q_out=self._q_out, q_err=self._q_err,
                max_workers=5, max_rps=0)

        for fetcher in self._fetchers.values():
            fetcher.start()

    def _write_results(self, q_out):
        while True:
            result = q_out.get()
            if not result:
                break
            print(result)

    def _write_errors(self, q_err, errors_path):
        with open(errors_path, 'w') as errors_file:
            while True:
                result = q_err.get()
                if not result:
                    break
                print(*result, sep='\t', file=errors_file)

    def _init_writers(self):
        self._writers = [
            threading.Thread(target=self._write_results, args=(self._q_out,)),
            threading.Thread(target=self._write_errors, args=(self._q_err, self.errors_path)),
        ]

        for writer in self._writers:
            writer.start()

    def run(self, infile):
        """Process urls from the infile.

        The method can be run several times (for several files)."""
        fetchers = self._fetchers
        default_fetcher = fetchers['default']

        for url in iter_good_lines(infile):
            urlp = urlparse(url)
            fetcher = fetchers.get(urlp.netloc, default_fetcher)
            fetcher.q_in.put(url)

        for fetcher in fetchers.values():
            fetcher.q_in.join()

        G_LOG.info('finished processing urls')

    def close(self):
        """Release resources by sending messages to subprocesses and threads
        that there is no more urls to process.
        """
        # signal to fetchers
        for fetcher in self._fetchers.values():
            fetcher.q_in.put(None)
            fetcher.q_in.join()

        # signal to writers
        self._q_out.put(None)
        self._q_err.put(None)
        G_LOG.info('poison pills sent to subprocesses and threads.')

    @classmethod
    def main2(cls):
        """Run the functionality of the script."""

        parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
        parser.add_argument(
            '--techs-file', type=pathlib.Path, default='techs.txt',
            help=('A file where the searched techs are listed: each tech on a separate line. '
                  'Defaults to techs.txt.'))
        parser.add_argument(
            'infile', nargs='*', type=argparse.FileType('r'), default=[sys.stdin],
            help=('A file or a list of files with a list of urls. Each url is supposed '
                  'to contain a job description. Defaults to stdin.'))
        parser.add_argument(
            '--errors-file', type=pathlib.Path, default='failed_urls.txt',
            help=('A tab-separated file to which we are going to dump urls requesting or parsing '
                  'of which resulted in an error. The error message is dumped after the url. '
                  'Defaults to failed_urls.txt.'))
        parser.add_argument(
            '--log-file', type=argparse.FileType('a'), default='extract_techs.log',
            help='A file where we write logs to. Defaults to extract_techs.log.')
        parser.add_argument(
            '--save-pages-to',
            help=('Save copies of the html into the specified directory. '
                  'By default html-files are not saved.'))
        parser.add_argument(
            '--outfile', type=argparse.FileType('w'), default='-',
            help='A file where the results are saved to. Defaults to stdout.')

        args = parser.parse_args()
        if not args.techs_file.exists():
            parser.error(
                ('The file with techs {} does not exist. '
                 'Use --techs-file option').format(args.techs_file.as_posix()))

        try:
            with args.errors_file.open('w'):
                pass
        except IOError:
            parser.error('Can not open {} for writing.'.format(args.errors_path.as_posix()))

        if args.save_pages_to:
            save_pages_to = pathlib.Path(args.save_pages_to)
            save_pages_to.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(level=logging.INFO, stream=args.log_file)

        start = time.time()

        runner = TechsExtractionRunner(
            terms_path=args.techs_file.as_posix(),
            errors_path=args.errors_file.as_posix(),
            save_pages_to=args.save_pages_to)

        for file_ in args.infile:
            runner.run(file_)

        runner.close()

        end = time.time()
        G_LOG.info('The execution of the script took {:0.3f}.'.format(end-start))


if __name__ == '__main__':
    TechsExtractionRunner.main2()
