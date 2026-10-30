"""Independent actual-contract text roundtrip; no runtime or evidence sources."""
import hashlib
import importlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
SOURCE = BASE / 'a105_contract_information_design_059'
sys.path[:0] = [str(ROOT), str(SOURCE)]
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((SOURCE / 'MANIFEST_001.json').read_bytes())
    entries = manifest
    for name, row in entries.items():
        path = SOURCE / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    first = importlib.import_module('probe_contract_information_001')
    second = importlib.import_module('probe_contract_information_002')
    actual = [('operation', entry['name'], entry['input_schema']) for entry in _population_catalog()]
    actual += [('fact', name, row['report_schema']) for name, row in
               LiteratureEpisodes(None, rate_population=True)._rate_fact_sources().items()]
    rows = []
    for kind, name, schema in actual:
        text = second.render(first.NamedDefinitions(schema), name + ' complete declared contract')
        rebuilt = second.parse_rendered(text)
        assert first.canonical(rebuilt) == first.canonical(schema), name
        rows.append({'kind': kind, 'name': name, 'rendered_text_bytes': len(text.encode()),
                     'canonical_schema_sha256': hashlib.sha256(first.canonical(schema).encode()).hexdigest()})
    edge = (SOURCE / 'SYNTHETIC_EDGE_TEXT_002.txt').read_text()
    rebuilt = second.parse_rendered(edge)
    assert rebuilt['enum'] == [None, False, 0, 'null', 'false', '0']
    assert type(rebuilt['enum'][1]) is bool and type(rebuilt['enum'][2]) is int
    assert 'a|b' in rebuilt['description'] and '\n' in rebuilt['description']
    dependencies = json.loads((SOURCE / 'INPUT_BASELINE_001.json').read_bytes())
    for name, row in dependencies.items():
        path = ROOT / 'gene_annotation_episode' / name
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], name
    receipt = {'passed': True, 'manifest_entries_verified': len(entries),
        'all_actual_contracts_reproduced_from_rendered_text': len(rows),
        'actual_contract_measurements': rows, 'scalar_type_and_escaping_edge_reproduced': True,
        'current_relevant_dependencies_verified': len(dependencies),
        'scope': 'Proposal-only pure text/canonical-contract reproduction. No Store/provider/model/source or selected runtime work; no provider acceptance or full implementation claim'}
    with (OUT / 'PROPOSAL_RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: value for key, value in receipt.items() if key != 'actual_contract_measurements'}))


if __name__ == '__main__':
    main()
