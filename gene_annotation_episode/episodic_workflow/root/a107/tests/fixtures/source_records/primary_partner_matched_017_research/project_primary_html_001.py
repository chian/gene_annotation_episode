"""Reproduce this research packet's text projection; no scientific extraction."""
from html.parser import HTMLParser
from pathlib import Path


class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'table', 'tr', 'li'):
            self.out.append('\n')
        if tag in ('td', 'th'):
            self.out.append('\t')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1
        if tag in ('p', 'h1', 'h2', 'h3', 'h4', 'tr', 'li'):
            self.out.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def project(raw):
    parser = Text()
    parser.feed(raw.decode())
    lines = [line.strip() for line in ''.join(parser.out).splitlines() if line.strip()]
    return ('\n'.join(lines) + '\n').encode()


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    actual = project((root / 'PRIMARY_PMC_001.html').read_bytes())
    assert actual == (root / 'PRIMARY_ARTICLE_TEXT_001.txt').read_bytes()
    print('Retained HTML text projection reproduced exactly.')
