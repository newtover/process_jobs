"""The module defines a class for fetching pages by the urls.

Each fetcher is a separate process which processes its own input queue and passes
results to the output queue and the error queue, which are shared among several
fetchers. The processing of the pages is performed in several threads
by ThreadExecutor. The executor's map method allows processing the input queue
while it is filled by other processes.
"""

import concurrent.futures
import logging
import multiprocessing as mp
import random
import threading
import time

import requests

from jobtechs.common import DEFAULT_HEADERS

G_LOG = logging.getLogger(__name__)

class ThrottledFetcher(mp.Process):
    """The class represents a fetcher which can be configured to limit its rps rate.

    It is a demonic process, so that the main process would not wait for it after it exits.
    Some processes should populate its q_in and then the main process should join its q_in.
    A None value in q_in marks the end of the processing.
    It is assumed that the fetcher is the only consumer of its q_in."""
    # pylint: disable=too-many-instance-attributes,too-many-arguments

    def __init__(self, parser, terms_extractor, q_out=None, q_err=None,
                 name=None, max_workers=None, max_rps=3):
        super().__init__(name=None)
        if not q_out:
            q_out = mp.Queue()
        if not q_err:
            q_err = mp.Queue()
        self.daemon = True
        self.parser = parser
        self.terms_extractor = terms_extractor
        self.q_in = mp.JoinableQueue()
        self.q_out = q_out
        self.q_err = q_err
        self.max_workers = max_workers
        self._last_call = 0
        self._last_call_lock = threading.Lock()
        self.min_period = 1./max_rps if max_rps > 0 else 0

    def _iter_q_in(self):
        # it is assumed that the fetcher is the only consumer of the q_in
        # None value stops processing
        while True:
            url = self.q_in.get()
            if url is None:
                self.q_in.task_done()
                break
            yield url

    def _process_url(self, url):
        """Request the url, parse its request and put into q_out.

        Report an error to q_err otherwise.
        """
        # pylint: disable=broad-except

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
            result, error = self.parser.parse_page(url, res.text, self.terms_extractor)
            if error:
                G_LOG.error('parsing failed url=%s | %s', url, error)
                self.q_err.put((url, error))
            else:
                self.q_out.put(result)

        # we should probably gracefully shutdown: for that we need to pass a message
        # to the parent process stating the reason.
        except requests.ConnectionError as err:
            G_LOG.error(
                'requests.ConnectionError: Failed to establish a new connection to %s.', url)
            self.q_err.put((url, 'requests.ConnectionError: Failed to establish a new connection.'))

        # we do not try to process any exceptions here. We just log them into q_err and continue
        except Exception as err:
            G_LOG.exception('Uncaught exception on processing url=%s | %s', url, str(err))
            self.q_err.put((url, str(err)))
        finally:
            self.q_in.task_done()
        return True

    def run(self):
        """The method starts max_workers threads and starts processing urls from the q_in.

        Thre results are put into q_out, the url requesting or parsing of which
        resulted in an error are put into q_err.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = executor.map(self._process_url, self._iter_q_in())
            for _ in results:
                pass
