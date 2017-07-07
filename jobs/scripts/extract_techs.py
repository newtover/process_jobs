"""A script to generate a list of products we are interested in found in job descriptions.

The script takes a list of urls in stdin and returns a |-separated output for each url.
The urls that led to exceptions are writte to a separate errors.txt file
"""

import time
import threading
import sys
import random
import requests
import multiprocessing as mp
from urllib.parse import urlparse
import logging

from jobs.common import DEFAULT_HEADERS, iter_good_lines
from jobs.fetcher import ThrottledFetcher
from jobs.parser import PageParser, IndeedParser, TermsExtractor, NewtonSoftwareParser, GreenHouseParser

G_LOG = logging.getLogger(__name__)

URLS = [
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
'https://boards.greenhouse.io/embed/job_app?for=pantheon&token=619056&b=https://pantheon.io/careers/apply',
'https://www.indeed.com/viewjob?jk=8539193e3a45a062&q=sales+operations&l=San+Francisco%2C+CA&tk=1aevt39cab9rbe1v&from=web',
'http://www.indeed.com/cmp/Exablox/jobs/Devop-Cloud-Management-System-053c56b763ebd5c5?sjdu=QwrRXKrqZ3CNX5W-O9jEvVKh33UeeQGaPWHksPPR7jOVeKpHgZBD8uj-JYSLVQQdOzuvtcRZqR1VUgvQgUCLrlSAZIc8VspZ09RpfJLmZ1g',
'http://www.indeed.com/cmp/The-Resource-Corner,-LLC/jobs/Bookkeeper-ce09ccbdef05dafc?sjdu=QwrRXKrqZ3CNX5W-O9jEvZYUjcFz8G6VtThA0LDUaBBKkXOI7HyNUFAgnmvj10geaet8H1fzoalk9SEj0AgHMA',
]

def main1():
    start = time.time()
    for url in URLS:
       res = requests.get(url, headers=DEFAULT_HEADERS)
       print(url, 'length', len(res.text))
    end = time.time()
    print('took {:0.3f}'.format(end-start))


def init_fetchers(q_out, q_err, save_page=False, terms_path='techs.txt'):
    terms_extractor = TermsExtractor(terms_path)
    fetchers = {
        'www.indeed.com': 
            ThrottledFetcher(
                parser=IndeedParser(save_page=save_page),
                terms_extractor=terms_extractor,
                q_out=q_out, q_err=q_err,
                max_workers=5),
        'newton.newtonsoftware.com':
            ThrottledFetcher(
                parser=NewtonSoftwareParser(save_page=save_page),
                terms_extractor=terms_extractor,
                q_out=q_out, q_err=q_err,
                max_workers=5),
        'boards.greenhouse.io':
            ThrottledFetcher(
                parser=GreenHouseParser(save_page=save_page),
                terms_extractor=terms_extractor,
                q_out=q_out, q_err=q_err,
                max_workers=5),        
        'default':
            ThrottledFetcher(
                parser=PageParser(save_page=save_page),
                terms_extractor=terms_extractor,
                q_out=q_out, q_err=q_err,
                max_workers=5, max_rps=0),
                
    }
    return fetchers

def main2():
    import argparse
    parser = argparse.ArgumentParser(description=sys.modules[__name__].__doc__)
    args = parser.parse_args()

    start = time.time()
    q_out = mp.Queue()
    q_err = mp.Queue()
    fetchers = init_fetchers(q_out, q_err, save_page=False)
    default_fetcher = fetchers['default']
    for fetcher in fetchers.values():
        fetcher.start()

    def write_results(q_out):
        while True:
            result = q_out.get()
            if not result:
                break
            print(result)

    def write_errors(q_err):
        with open('errors.txt', 'w') as f1:
            while True:
                result = q_err.get()
                if not result:
                    break
                print(*result, sep='\t', file=f1)

    
    writer1 = threading.Thread(target=write_results, args=(q_out,))
    writer2 = threading.Thread(target=write_errors, args=(q_err,))
    writer1.start()
    writer2.start()


    #for url in URLS:
    for url in iter_good_lines(sys.stdin):
       urlp = urlparse(url)
       fetcher = fetchers.get(urlp.netloc, default_fetcher)       
       fetcher.q_in.put(url)

    for fetcher in fetchers.values():
        fetcher.q_in.put(None)
        fetcher.q_in.join()
    end = time.time()
    q_out.put(None)
    q_err.put(None)
    G_LOG.info('took {:0.3f}'.format(end-start))    


if __name__ == '__main__':
    import sys
    #logging.basicConfig(level=logging.ERROR, stream=sys.stderr)   
    logging.basicConfig(filename='log.txt')   
    #main1()
    main2()
