import logging
import lxml.html as etree
from urllib.parse import urlparse, parse_qs
from hashlib import sha1

from jobs.common import iter_good_lines

G_LOG = logging.getLogger(__name__)

def hash_url(url):
    return sha1(url.encode('utf-8')).hexdigest()

class TermsExtractor:
    def __init__(self, terms_filename):
        self.terms_filename = terms_filename
        self._terms = set()
        self.reload_terms()

    def reload_terms(self):
        self._terms.clear()
        with open(self.terms_filename) as f1:
            for line in iter_good_lines(f1):
                term = tuple(line.lower().split())
                self._terms.add(term)

    def extract_terms(self, text):
        print(self._terms)
        return set()

    def terms_to_list(self, terms):
        """Convert set of term-tuples into a sorted list of strings."""
        return sorted(' '.join(term) for term in terms)

class Result:
    def __init__(self, url, company, techs, site):
        self.url = url
        self.company = company
        self.techs = techs
        self.site = site

    def __str__(self):
        return '{} | {} | {} | {}'.format(self.url, self.company, 
                                          ', '.join(self.techs), self.site)


class PageParser:
    def __init__(self, save_page=False):
        self.save_page = save_page

    def do_save_page(self, url, text, filename=None):
        if not filename:
            filename = '{}.html'.format(hash_url(url))
        G_LOG.info('saving page {} as {}'.format(url, filename))
        with open(filename, 'w') as f1:
            print(text, file=f1)

    def parse_page(self, url, text, extractor):
        print('parsing body for {}, len={}'.format(url, len(text)))
        if self.save_page:
            self.do_save_page(url, text)
        return Result(url, '', '', ''), None


class IndeedParser(PageParser):
    # mobile version of jobs contains less noise: https://www.indeed.com/m/viewjob?jk=ce09ccbdef05dafc
    def parse_job(self, text, extractor):
        tree = etree.fromstring(text)
        result = {
            'company': tree.xpath('string(.//span[@class="company"])'),
        }
        description = tree.xpath('string(.//span[@id="job_summary"])')
        terms = extractor.extract_terms(description)
        result['techs'] = extractor.terms_to_list(terms)
        return result

    def parse_page(self, url, text, extractor):
        urlp = urlparse(url)
        if """rel="alternate" media="handheld" href="/m/viewjob?jk=""" in text:
            qs = parse_qs(urlp.query)
            job = self.parse_job(text, extractor)
            if self.save_page:
                self.do_save_page(url, text, 'indeed.{}.html'.format(qs.get('jk', ['empty'])[0]))
                
            res = Result(url, job.get('company'), job.get('techs', ''), '')
            return res, None
        else:
            return super().parse_page(url, text, extractor)
