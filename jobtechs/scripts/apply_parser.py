"""A script to apply a page parser to an HTML file.

Used for easier debugging and visual checks."""

import argparse
from jobtechs.parser import netloc_to_parser_map, TermsExtractor

def main():
    # pylint: disable=missing-docstring
    parser = argparse.ArgumentParser()
    parser.add_argument('parser_netloc', choices=list(netloc_to_parser_map.keys()))
    parser.add_argument(
        'infile', type=argparse.FileType('r'),
        help='An HTML-file we are trying to apply the parser to.')
    parser.add_argument(
        '--techs-file', default='techs.txt',
        help='A file where the searched techs are listed: each tech on a separate line.')

    args = parser.parse_args()

    page_parser = netloc_to_parser_map[args.parser_netloc]()
    text = args.infile.read()
    extractor = TermsExtractor(args.techs_file)
    url = ''
    res, err = page_parser.parse_page(url, text, extractor)
    if err:
        print(err)
    else:
        print(res.url)
        print(res.company)
        print(*res.techs, sep=', ')
        print(res.site)

if __name__ == '__main__':
    main()
