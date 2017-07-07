"""A script to generate a list of products we are interested in found in job descriptions.

It takes a list of urls from infile (stdin by default) and returns a |-separated output for each url.
The script requires a file with techs we are searching for, the file is specified by --techs-file option.
The urls that led to exceptions are written to a separate file, configured by --errors-file.
"""

import argparse
import logging
import multiprocessing as mp
import pathlib
import random
import sys
import time
import threading
from urllib.parse import urlparse

import requests

from jobtechs.common import DEFAULT_HEADERS, iter_good_lines
from jobtechs.fetcher import ThrottledFetcher
from jobtechs.parser import PageParser, IndeedParser, TermsExtractor, NewtonSoftwareParser, GreenHouseParser

G_LOG = logging.getLogger(__name__)

URLS = [
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
'https://boards.greenhouse.io/embed/job_app?for=pantheon&token=619056&b=https://pantheon.io/careers/apply',
'https://www.indeed.com/viewjob?jk=8539193e3a45a062&q=sales+operations&l=San+Francisco%2C+CA&tk=1aevt39cab9rbe1v&from=web',
'http://www.indeed.com/cmp/Exablox/jobs/Devop-Cloud-Management-System-053c56b763ebd5c5?sjdu=QwrRXKrqZ3CNX5W-O9jEvVKh33UeeQGaPWHksPPR7jOVeKpHgZBD8uj-JYSLVQQdOzuvtcRZqR1VUgvQgUCLrlSAZIc8VspZ09RpfJLmZ1g',
'http://www.indeed.com/cmp/The-Resource-Corner,-LLC/jobs/Bookkeeper-ce09ccbdef05dafc?sjdu=QwrRXKrqZ3CNX5W-O9jEvZYUjcFz8G6VtThA0LDUaBBKkXOI7HyNUFAgnmvj10geaet8H1fzoalk9SEj0AgHMA',
]


class TechsExtractionRunner:
    def __init__(self, terms_path='techs.txt', errors_path='failed_urls.txt', save_pages=False):
        self.save_pages = save_pages
        self.terms_path = terms_path
        self.errors_path = errors_path
        self._q_out = self._q_err = None
        self._init_queues()
        self._fetchers = {}
        self._init_fetchers()
        self._writers = []
        self._init_writers()

    def make_terms_extractor(self, terms_path):
        return TermsExtractor(terms_path)

    def make_queue(self):
        return mp.Queue()

    def _init_queues(self):
        self._q_out = self.make_queue()
        self._q_err = self.make_queue()

    def _init_fetchers(self):
        terms_extractor = self.make_terms_extractor(self.terms_path)
        self._fetchers = {
            'www.indeed.com': 
                ThrottledFetcher(
                    parser=IndeedParser(save_page=self.save_pages),
                    terms_extractor=terms_extractor,
                    q_out=self._q_out, q_err=self._q_err,
                    max_workers=5),
            'newton.newtonsoftware.com':
                ThrottledFetcher(
                    parser=NewtonSoftwareParser(save_page=self.save_pages),
                    terms_extractor=terms_extractor,
                    q_out=self._q_out, q_err=self._q_err,
                    max_workers=5),
            'boards.greenhouse.io':
                ThrottledFetcher(
                    parser=GreenHouseParser(save_page=self.save_pages),
                    terms_extractor=terms_extractor,
                    q_out=self._q_out, q_err=self._q_err,
                    max_workers=5),        
            'default':
                ThrottledFetcher(
                    parser=PageParser(save_page=self.save_pages),
                    terms_extractor=terms_extractor,
                    q_out=self._q_out, q_err=self._q_err,
                    max_workers=5, max_rps=0),
                    
        }
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
        """Release resources by sending messages to subprocesses and threads that there is no more urls to process."""

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
        parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
        parser.add_argument('--techs-file', type=pathlib.Path, default='techs.txt',
                            help='A file where the searched techs are listed: each tech on a separate line.')
        parser.add_argument('infile', nargs='*', type=argparse.FileType('r'), default=[sys.stdin],
                            help='A file with a list of urls. Each url is supposed to contain a job description.')
        parser.add_argument('--errors-file', type=pathlib.Path, default='failed_urls.txt',
                            help=('A tab-separated file to which we are going to dump urls requesting or parsing '
                                  'of which resulted in an error. The error message is dumped after the url.'))
        parser.add_argument('--log-file', type=argparse.FileType('a'), default='extract_techs.log',
                            help='A file where we write logs to')
        parser.add_argument('--save-pages-to',
                            help=('Save copies of the html into the specified directory. '
                                  'By default html-files are not saved.'))
        args = parser.parse_args()
        if not args.techs_file.exists():
            parser.error('The file with techs {} does not exist. Use --techs-file option'.format(args.techs_file.as_posix()))

        try:
            with args.errors_file.open('w') as f1:
                pass
        except IOError as err:
            parser.error('Can not open {} for writing.'.format(args.errors_path.as_posix()))

        if args.save_pages_to:
            save_pages_to = pathlib.Path(args.save_pages_to)
            save_pages_to.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(level=logging.INFO, stream=args.log_file)

        start = time.time()

        runner = TechsExtractionRunner(
            terms_path=args.techs_file.as_posix(),
            errors_path=args.errors_file.as_posix(),
            save_pages=args.save_pages_to)

        for file_ in args.infile:
            runner.run(file_)

        runner.close()

        end = time.time()
        G_LOG.info('The execution of the script took {:0.3f}.'.format(end-start))


if __name__ == '__main__':
    TechsExtractionRunner.main2()
