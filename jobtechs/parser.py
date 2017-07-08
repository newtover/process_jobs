from collections import deque
import logging
import lxml.html as etree
import pathlib
import re
from urllib.parse import urlparse, parse_qs
from hashlib import sha1

from jobtechs.common import iter_good_lines

G_LOG = logging.getLogger(__name__)

def hash_url(url):
    return sha1(url.encode('utf-8')).hexdigest()

def extract_site_url(url):
    urlp = urlparse(url)
    return '{}://{}'.format(urlp.scheme, urlp.netloc)

def iter_n_grams(text, max_n):
    if not text:
        return []
    chunks = re.split('(\W+)', text)
    words = deque(maxlen=max_n)
    words.append(chunks[0])
    yield (chunks[0],)

    for i in range(2, len(chunks), 2):
        word = chunks[i]
        yield (word,)
        prev_sep = chunks[i-1].strip()
        # we are not interested in n-grams split by punctuation
        if prev_sep:  # some punctuation
            words.clear()
            words.append(word)
        elif max_n > 1:  # only spacesi as separator
            words.append(word)
            max_n_gram = tuple(words)
            yield max_n_gram
            for i in range(2, len(max_n_gram)):
                yield max_n_gram[-i:]


class TermsExtractor:
    """A simple implementation of extracting terms based on n-gram matching.

    We split text into n-grams, building a set of n-grams and intersect
    the set with the set of existing terms.

    For simplicity we will lowercase all words and slightly normalize
    the text.
    """
    def __init__(self, terms_filename):
        self.terms_filename = terms_filename
        self._terms = set()
        # the longest n in terms n-grams
        self.max_n = 1
        self.reload_terms()

    def reload_terms(self):
        self._terms.clear()
        max_n = 1
        with open(self.terms_filename) as f1:
            for line in iter_good_lines(f1):
                term = tuple(line.lower().split())
                self._terms.add(term)
                if len(term) > max_n:
                    max_n = len(term)
        self.max_n = max_n

    def iter_n_grams(self, text):
        return iter_n_grams(text, self.max_n)

    def extract_terms(self, text):
        """Extract terms from the text description."""
        text = text.lower()
        n_grams = set(self.iter_n_grams(text))
        common = n_grams & self._terms
        return common

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
    def __init__(self, save_pages_to=None):
        if save_pages_to:
            save_pages_to = pathlib.Path(save_pages_to)
        self.save_pages_to = save_pages_to

    def do_save_page(self, url, text, filename=None):
        if not filename:
            filename = '{}.html'.format(hash_url(url))
        G_LOG.info('saving page {} as {}'.format(url, filename))
        if self.save_pages_to:
            with self.save_pages_to.joinpath(filename).open(mode='w') as f1:
                print(text, file=f1)

    def _extract_company_name(self, url, text, tree):
        # we need a generic way of company name extraction from an arbitrary page
        return ''

    def _extract_company_site(self, url, text, tree):
        # if it is not an aggregator with its own parser, it is a separate company site
        return extract_site_url(url)

    def _extract_description(self, url, text, tree):
       return tree.xpath('string(./body)')

    def parse_job_page(self, url, text, extractor, tree=None):
        """A generic method for parsing pages containing a job description.

        It is a template method, allowing to override methods for extracting terms,
        company name and site in inheritants.
        """
        if self.save_pages_to:
            self.do_save_page(url, text)
        if tree is None:
            tree = etree.fromstring(text)

        company = self._extract_company_name(url, text, tree)
        site = self._extract_company_site(url, text, tree)

        for elem in tree.xpath('.//script'):
            elem.drop_tree()
        for elem in tree.xpath('.//style'):
            elem.drop_tree()

        description = self._extract_description(url, text, tree)
        ## print(description)
        terms = extractor.extract_terms(description)
        terms = extractor.terms_to_list(terms)
        return Result(url, company, terms, site), None

    def parse_page(self, url, text, extractor):
        """Default implementation of page parsing.

        It assumes we are parsing a job description and delegating parsing to parse_job_page."""
        tree = etree.fromstring(text)
        return self.parse_job_page(url, text, extractor, tree)


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
            if self.save_pages_to:
                self.do_save_page(url, text, 'indeed.{}.html'.format(qs.get('jk', ['empty'])[0]))
                
            res = Result(url, job.get('company'), job.get('techs', ''), '')
            return res, None
        else:
            return super().parse_page(url, text, extractor)


class NewtonSoftwareParser(PageParser):
    def _extract_company_name(self, url, text, tree):
        # lxml lowercases the attribute names!
        return tree.xpath('string(.//span[@id="indeed-apply-widget"]/@data-indeed-apply-jobcompanyname)')

    def _extract_company_site(self, url, text, tree):
       continue_url = tree.xpath('string(.//span[@id="indeed-apply-widget"]/@data-indeed-apply-continueurl)')
       if continue_url:
           return extract_site_url(continue_url)
       else:
           return '' 

    def _extract_description(self, url, text, tree):
        return tree.xpath('string(.//td[@id="gnewtonJobDescriptionText"])')


class GreenHouseParser(PageParser):
    def _extract_company_site(self, url, text, tree):
        jobs_url = tree.xpath('string(.//div[@id="header"]/a/@href)')
        if jobs_url:
            return extract_site_url(jobs_url)
        else:
            return ''

    def _extract_company_name(self, url, text, tree):
        chunk = tree.xpath('string(.//div[@id="header"]/span[@class="company-name"])').strip()
        if chunk.startswith('at '):
            return chunk[3:]
        else:
            return chunk

    def _exract_description(self, url, text, tree):
        return tree.xpath('string(.//div[@id="content"])')
