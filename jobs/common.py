from collections import OrderedDict

def parse_headers(text):
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
    with open(filename, 'w') as f1:
        print(text, file=f1)

