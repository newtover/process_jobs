import concurrent.futures
import logging
import multiprocessing as mp
import random
import requests
import threading
import time

from jobs.common import DEFAULT_HEADERS

G_LOG = logging.getLogger(__name__)

class ThrottledFetcher(mp.Process):
    def __init__(self, parser, q_in=None, q_out=None, q_err=None, name=None, max_workers=None, max_rps=3):
        super().__init__(name=None)
        if not q_in:
            q_in = mp.JoinableQueue()
        if not q_out:
            q_out = mp.Queue()
        if not q_err:
            q_err = mp.Queue()
        self.parser = parser
        self.q_in = q_in
        self.q_out = q_out
        self.q_err = q_err
        self.max_workers = max_workers
        self._last_call = 0
        self._last_call_lock = threading.Lock()
        self.min_period = 1./max_rps if max_rps > 0 else 0

    def _iter_q_in(self):
        while True:
            url = self.q_in.get()
            if url is None:
                self.q_in.task_done()
                break
            yield url

    def _process_url(self, url):
        thread_name = threading.current_thread().name
        if self.min_period:
            while True:
                cur_time = time.time()
                with self._last_call_lock:
                    next_call = self._last_call + self.min_period
                    diff = cur_time - next_call
                    if diff >= 0:
                        self._last_call = cur_time
                        break
                # add some additional timeout, so that several threads 
                # would not wake up simultaneously
                time.sleep(-diff + random.random() * self.min_period * 2)
        try:
            res = requests.get(url, headers=DEFAULT_HEADERS)
            res.raise_for_status()
            result, error = self.parser.parse_page(url, res.text)
            if error:
                G_LOG.error('parsing failed url={} | {}'.format(url, error))
                self.q_err.put((url, error))
            else:
                self.q_out.put(result)            
        except Exception as err:
            G_LOG.exception('Uncaught exception on processing url={} | {}'.format(url, str(err)))
            self.q_err.put((url, str(err)))
        finally:
            self.q_in.task_done()
        return True

    def run(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = executor.map(self._process_url, self._iter_q_in())
            for res in results:
                pass       
                        
