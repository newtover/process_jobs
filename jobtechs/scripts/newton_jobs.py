#!/usr/bin/env python3
"""Check for a newtonsoftware marker on a page and if found output a list of urls to job
descriptions for the found company id."""

import argparse
import logging
import re
import lxml.html as ET
import requests

from jobtechs.common import DEFAULT_HEADERS, dump_html

G_LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_URL = 'https://www.alteryx.com/careers'


def try_find_newton_jobs(text):
    """Search for newton marjer on the page and return the client id if found."""
    # for simplicity, we think that no other CGI-params is specified
    # we might look for the handler with text.find(), then extract the whole url from the position
    # and then parse the query_string looking for the clientId
    pattern = r'//newton[.]newtonsoftware[.]com/career/iframe[.]action[?]clientId=([0-9a-f]+)'
    match = re.search(pattern, text)
    if match:
        return match.group(1)


def extract_newton_jobs(text):
    """Extract urls of job descriptions from A elements"""
    dom = ET.fromstring(text)
    for elem in dom.xpath('.//div[@class="gnewtonCareerGroupJobTitleClass"]/a'):
        yield elem.attrib['href'], elem.text.strip()


def main():
    # pylint: disable=missing-docstring
    parser = argparse.ArgumentParser(('check whether the page includes newtonsoftware carrees jobs'
                                      ' and lists the jobs urls'))
    parser.add_argument('url', nargs='?', default=DEFAULT_URL)
    parser.add_argument('--save-html', action='store_true')
    args = parser.parse_args()

    G_LOG.info('Checking %s', args.url)

    res = requests.get(args.url, headers=DEFAULT_HEADERS)
    if args.save_html:
        dump_html(res.text, 'newton1.orig.html')

    newton_id = try_find_newton_jobs(res.text)
    if not newton_id:
        print('the page does not contain the block')
        exit()

    jobs_url = 'https://newton.newtonsoftware.com/career/CareerHome.action?clientId=' + newton_id
    G_LOG.info('Newton cliend id found, checking the jobs url: %s', jobs_url)

    res2 = requests.get(jobs_url, headers=DEFAULT_HEADERS)
    for url, job in extract_newton_jobs(res2.text):
        print(job, url, sep='\t')

    if args.save_html:
        dump_html(res.text, 'newton2.jobs.html')


if __name__ == '__main__':
    main()
