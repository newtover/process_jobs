from collections import deque, namedtuple
import logging
import lxml.html as etree
import pathlib
import re
import sys
from urllib.parse import urlparse, parse_qs, urlencode
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
    """Object representing page parsing results."""
    def __init__(self, url, company, techs, site):
        self.url = url
        self.company = company
        self.techs = techs
        self.site = site

    def __str__(self):
        return '{} | {} | {} | {}'.format(self.url, self.company, 
                                          ', '.join(self.techs), self.site)

# a common pair to reference job id in aggregator sites
JobId = namedtuple('JobId', 'company_id job_id')


class PageParser:
    """A generic page parser. It may use parsers for vacancy aggregators (agg_parsers)
    to look for common markers of injected vacancies.

    save_pages_to parameter turns on saving of requested pages into the specified directory.

    """
    def __init__(self, save_pages_to=None, agg_parsers=None):
        if save_pages_to:
            save_pages_to = pathlib.Path(save_pages_to)
        self.save_pages_to = save_pages_to
        self._agg_parsers = [] if agg_parsers is None else agg_parsers

    def save_if_needed(self, url, text, page_name=None):
        """Save page contents if bool(self.save_pages_to) is True"""
        if not self.save_pages_to:
            return
        if not page_name:
            page_name = hash_url(url)
        urlp = urlparse(url)
        prefix = urlp.netloc.replace(':', '_')
        suffix = '' if page_name.endswith('.html') else '.html'

        page_name = prefix + '.' + page_name + suffix

        G_LOG.info('saving page {} as {}'.format(url, page_name))
        with self.save_pages_to.joinpath(page_name).open(mode='w') as f1:
            print(text, file=f1)

    def _extract_company_name(self, url, text, tree):
        # we need a generic way of company name extraction from an arbitrary page
        # a naive assumption is that the company name should be in the page title
        # but its not clear how to extract it.
        # If we have a large collection of pages, we could collect a test set of job page titles
        # and try to find out how to extract company names by machine learning
        # title = tree.xpath('string(head/title)')
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
        if not company and not terms and not site:
            return None, 'Nothing extracted. The job is probably no longer active.'

        return Result(url, company, terms, site), None

    def parse_page(self, url, text, extractor):
        """Default implementation of page parsing.

        It assumes we are parsing a job description and delegating parsing to parse_job_page."""
        self.save_if_needed(url, text)

        tree = etree.fromstring(text)

        for parser in self._agg_parsers:
            new_url = parser.check_for_job_url(url, text, tree)
            if new_url:
                return None, 'External job description found:\t' + new_url

        return self.parse_job_page(url, text, extractor, tree)


class AggregatorParser:
    netloc = None
    def check_for_job_url(self, url, text, tree=None):
        """Check whether the page contains a link to an external job description.

        If the link is found, it is returned. None otherwise.
        """
        return

    def extract_job_id(self, url, text, tree):
        """Find conpany_id and job_id on the page."""
        return

    def parse_page(self, url, text, extractor):
        tree = etree.fromstring(text)

        # check if the page is a job description
        job_id = self.extract_job_id(url, text, tree)
        if job_id:
            self.save_if_needed(url, text, '{}.{}'.format(job_id.company_id, job_id.job_id))
            return self.parse_job_page(url, text, extractor, tree)
        else:
            self.save_if_needed(url, text)
            return None, 'The url is not a job description/vacancy.'


class IndeedParser(AggregatorParser, PageParser):
    # mobile version of jobs contains less noise: https://www.indeed.com/m/viewjob?jk=ce09ccbdef05dafc
    netloc = "www.indeed.com"

    def extract_job_id(self, url, text, tree):
        alt_url = tree.xpath('string(.//link[@rel="alternate" and @media="handheld"]/@href)')
        if alt_url:
            job_id = re.search(r'[?]jk=(\w+)', alt_url)
            if job_id:
                return JobId('', job_id.group(1))

    def _extract_company_name(self, url, text, tree):
        # lxml lowercases the attribute names!
        return tree.xpath('string(.//span[@class="company"])')

    def _extract_description(self, url, text, tree):
        return tree.xpath('string(.//span[@id="job_summary"])')

    def _extract_company_site(self, url, text, tree):
        # there is no link on th page
        # to be able to extract the company site we should visit tha company page on the site
        return ''


class NewtonSoftwareParser(AggregatorParser, PageParser):
    netloc = "newton.newtonsoftware.com"

    def extract_job_id(self, url, text, tree):
        urlp = urlparse(url)
        query = parse_qs(urlp.query)
        if 'clientId' in query and 'id' in query and tree.xpath('.//table[@id="gnewtonJobDescription"]'):
            # ids are hex chars
            client_id = re.match('\w+$', query['clientId'][0])
            job_id = re.match('\w+$', query['id'][0])
            if not client_id or not job_id:
                return
            return JobId(client_id.group(0), job_id.group(0))

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

    def check_for_job_url(self, url, text, tree=None):
        """Check whether the page contains a link to an external job description.

        If the link is found, it is returned. None otherwise.
        """
        if tree is None:
            tree = etree.fromstring(text)

        # an example url:
        # http://www.alteryx.com/careers?gnk=job&gni=8a7886f8518a669b01518ee8e5c07d58&gns=Indeed
        query = parse_qs(urlparse(url).query)
        if 'gni' not in query or 'gnk' not in query or query['gnk'][0] != 'job':
            return

        job_id = query['gni'][0]

        # looking for [https:]//newton.newtonsoftware.com/career/iframe.action?clientId=[0-9af]+
        # src might lack the http(s) prefix using relative urls
        marker = '//newton.newtonsoftware.com/career/iframe.action'
        marker = tree.xpath('string(.//script[contains(@src, "{}")]/@src)'.format(marker))
        if not marker:
            return

        query = parse_qs(urlparse(marker).query)

        if not 'clientId' in query:
            return

        client_id = query['clientId'][0]

        query = [('clientId', client_id), ('id', job_id), ('source', 'Indeed')]

        return 'https://newton.newtonsoftware.com/career/JobIntroduction.action?{}'.format(urlencode(query))


class GreenHouseParser(AggregatorParser, PageParser):
    """Specific parser for greenhouse.io.

    The greenhouse.io job descriptions are injected into the client companies website.
    Here is the typical url of a job description:
    https://boards.greenhouse.io/embed/job_app?for=pantheon&token=619056&b=https://pantheon.io/careers/apply

    for - is the short company id
    token - is the vacancy unique id
    b - contains a reference to the job list on the site of the client company.

    The list is as well taken from the greenhouse.io site:
    https://boards.greenhouse.io/embed/job_board?for=pantheon

    The job description page contains the company name and the link to the site of the company.
    It has a marker, a meta tag of the format:

    <meta property="og:url" content="https://boards.greenhouse.io/pantheon/jobs/619056"></meta>

    """
    netloc = "boards.greenhouse.io"

    def extract_job_id(self, url, text, tree):
        # example https://boards.greenhouse.io/pantheon/jobs/619056
        permanent_url = tree.xpath('string(head/meta[@property="og:url"]/@content)').strip()
        match = re.match(r'https://boards.greenhouse.io/([^/]+)/jobs/(\d+)$', permanent_url)
        if match:
            return JobId(match.group(1), match.group(2))

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

    def check_for_job_url(self, url, text, tree=None):
        """Check whether the page contains a link to an external job description.

        If the link is found, it is returned. None otherwise.
        """
        if tree is None:
            tree = etree.fromstring(text)

        # the url should contain a numeric `gh_jid` parameter and there should be 
        # a script tag with @src to boards.greenhouse.io
        query = parse_qs(urlparse(url).query)
        if 'gh_jid' not in query:
            return

        job_id = query['gh_jid'][0]

        # looking for [https:]//boards.greenhouse.io/embed/job_board/js?for=pantheon
        # src might lack the http(s) prefix using relative urls
        marker = '//boards.greenhouse.io/embed/job_board/js'
        marker = tree.xpath('string(.//script[contains(@src, "{}")]/@src)'.format(marker))
        if not marker:
            return

        query = parse_qs(urlparse(marker).query)

        if 'for' not in query:
            return

        client_id = query['for'][0]

        query = [('for', client_id), ('token', job_id)]

        return 'https://boards.greenhouse.io/embed/job_app?{}'.format(urlencode(query))


class HireBridgeParser(AggregatorParser, PageParser):
    netloc = 'recruit.hirebridge.com'

    def extract_job_id(self, url, text, tree):
        # example http://recruit.hirebridge.com/v3/Jobs/JobDetails.aspx?cid=7744&jid=451687&locvalue=1059
        permanent_url = tree.xpath('string(head/meta[@property="og:url"]/@content)').strip()
        if not permanent_url:
            return 
        urlp = urlparse(permanent_url)
        query = parse_qs(urlp.query)
        if 'cid' in query and 'jid' in query:
            return JobId(query['cid'][0], query['jid'][0])
        return

    def _extract_company_name(self, url, text, tree):
        chunk = tree.xpath('string(.//div[@id="logo"]/h1/img/@alt)')
        return chunk

    def _extract_company_site(self, url, text, tree):
        jobs_url = tree.xpath('.//div[@id="rightcol"]//a/@href')
        jobs_url = [url1 for url1 in jobs_url if url1.startswith('http')]
        # naive assumption that the job descriptions contains references to its own site
        if jobs_url:
            return extract_site_url(jobs_url[0])
        else:
            return ''


class JobviteParser(AggregatorParser, PageParser):
    netloc = "jobs.jobvite.com"

    def extract_job_id(self, url, text, tree):
        # example http://jobs.jobvite.com/cloudera/job/oNg44fwV
        if url:
            urlp = urlparse(url)
            match = re.match('/([^/]+)/job/([^/?]+)$', urlp.path)
            if match:
                return JobId(match.group(1), match.group(2))
            else:
                return
        # else we may try to extract from the page

    def _extract_company_site(self, url, text, tree):
        jobs_url = tree.xpath('.//a/@href')
        jobs_url = [url1 for url1 in jobs_url if url1.startswith('http')]
        # naive assumption that the job descriptions contains references to its own site
        if jobs_url:
            return extract_site_url(jobs_url[0])
        else:
            return ''

    def _extract_company_name(self, url, text, tree):
        chunk = tree.xpath('string(.//div[@class="jv-logo"]/a/img/@alt)')
        return chunk

   
def build_netloc_to_parser_map():
    cur_module = sys.modules[__name__]
    the_map = {}
    for attr in dir(cur_module):
        obj = getattr(cur_module, attr)
        if isinstance(obj, type) and issubclass(obj, AggregatorParser) and obj.netloc:
            the_map[obj.netloc] = obj
    return the_map

netloc_to_parser_map = build_netloc_to_parser_map()
