"""Authenticate the already interpreted058 case and its proposed source spans."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.literature_binding_interaction_inputs import binding_interaction_arguments_schema


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Article(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag == 'article':
            self.inside = True
    def handle_endtag(self, tag):
        if tag == 'article':
            self.inside = False
    def handle_data(self, value):
        if self.inside:
            self.parts.append(value)


def main():
    proposal = BASE / 'a105_binding_primary_example_058'
    case = BASE / 'a105_binding_case_042'
    manifest = json.loads((proposal / 'MANIFEST_001.json').read_bytes())
    for name, row in manifest['files'].items():
        path = proposal / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    identities = json.loads((proposal / 'SOURCE_IDENTITIES_001.json').read_bytes())
    for name, row in identities.items():
        path = case / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    html = (case / 'primary.html').read_text()
    parser = Article()
    parser.feed(html)
    article = ''.join(''.join(parser.parts).split())
    text_raw = (case / 'primary_text.txt').read_bytes()
    assert article == ''.join(text_raw.decode().split())
    assert 'nihms-454929-t0001.jpg' in html
    requests = json.loads((proposal / 'PROPOSED_SOURCE_NOMINATIONS_001.json').read_bytes())['cases']
    witnessed = 0
    def visit(value):
        nonlocal witnessed
        if isinstance(value, dict):
            if value.get('kind') == 'text':
                assert value['source_ref'] == 'source_primary_058_proposal'
                assert value['representation'] == 'text'
                assert text_raw[value['start']:value['end']].decode() == value['quote']
                witnessed += 1
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for request in requests.values():
        validate_schema(request, binding_interaction_arguments_schema())
        visit(request)
    reset = json.loads((BASE / 'binding_primary_parent_reset_058/READ_RECEIPT.json').read_bytes())
    assert reset['complete'] and len(reset['acknowledged_chunks']) == reset['chunks_total'] == 51
    for row in reset['documents']:
        assert digest(Path(row['path'])) == row['sha256'], row['path']
    receipt = {'passed': True, 'manifest_entries_verified': len(manifest['files']),
        'source_identities_verified': identities, 'full_article_text_equal_ignoring_whitespace': True,
        'article_text_nonwhitespace_characters': len(article), 'original_table_link_present': True,
        'proposed_requests_validated': len(requests), 'exact_text_witness_occurrences_verified': witnessed,
        'root_post_paper_reset_chunks': 51,
        'scope': 'Already interpreted retained primary; original image visually inspected before complete root reset. Mechanical source binding checks only; no native operation/Store/Episode/model execution or independent experimental truth claim'}
    with (OUT / 'PROPOSAL_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in receipt.items() if key != 'source_identities_verified'}))


if __name__ == '__main__':
    main()
