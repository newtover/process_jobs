"""Common utility functions used in other modules."""
from collections import OrderedDict

def parse_headers(text):
    """Parse a string of headers (copied from Firefox) into a dict used in requests."""
    return OrderedDict(line.split(': ') for line in text.splitlines() if line)


DEFAULT_HEADERS = parse_headers("""
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:53.0) Gecko/20100101 Firefox/53.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate
Connection: keep-alive
Upgrade-Insecure-Requests: 1
""")

def dump_html(text, filename):
    """Helper to save text into a file."""
    with open(filename, 'w') as file_:
        print(text, file=file_)

def skip_comments(lines):
    """Filter out lines starting with a #."""
    return (line for line in lines if not line.startswith('#'))

def rstrip_lines(lines):
    """Apply rstrip to every line."""
    return (line.rstrip() for line in lines)

def skip_blanks(lines):
    """Filter out blank lines."""
    return (line for line in lines if line)

def iter_good_lines(lines):
    """Iterate over rstripped lines with skipped empty and comment lines."""
    return skip_blanks(rstrip_lines(skip_comments(lines)))
