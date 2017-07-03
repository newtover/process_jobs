import time
import random
import requests
import multiprocessing as mp
import concurrent.futures
import asyncio
import aiohttp
import threading
import logging

from jobs.common import DEFAULT_HEADERS
from jobs.fetcher import ThrottledFetcher
from jobs.parser import PageParser, IndeedParser, TermsExtractor

G_LOG = logging.getLogger(__name__)

URLS = ['http://localhost:5000/{}'.format(i) for i in range(10)]
URLS = [
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
'https://newton.newtonsoftware.com/career/JobIntroduction.action?clientId=8aa0050632afa2010132b69b35493eab&id=8a7880665cb19ccc015cc1f77b0a6410&source=Indeed',
]
URLS = [
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



def main2():
    start = time.time()
    q_out = mp.Queue()
    q_err = mp.Queue()
    fetcher = ThrottledFetcher(parser=IndeedParser(save_page=True), 
                               terms_extractor=TermsExtractor('techs.txt'),
                               q_out=q_out, q_err=q_err,
                               max_workers=5)
    fetcher.start()

    def write_results(q_out):
        while True:
            result = q_out.get()
            if not result:
                break
            print(result)
    
    writer1 = threading.Thread(target=write_results, args=(q_out,))
    writer2 = threading.Thread(target=write_results, args=(q_err,))
    writer1.start()
    writer2.start()


    for url in URLS:
       fetcher.q_in.put(url)
    fetcher.q_in.put(None)

    fetcher.q_in.join()
    end = time.time()
    q_out.put(None)
    q_err.put(None)
    print('took {:0.3f}'.format(end-start))    


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)   
    #main1()
    main2()
