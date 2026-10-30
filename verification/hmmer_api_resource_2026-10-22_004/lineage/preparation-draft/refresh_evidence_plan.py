"""Refresh only evidence planning after owners finish; retain original drafts."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import stat
import xml.etree.ElementTree as ET

OUT = Path('/tmp/api-planning-publication-preparation-20261022-001')
old = json.loads((OUT/'COPY_PLAN.DRAFT.json').read_text())
entries = [row for row in old['entries'] if row['category'] !=
    'component_or_development_evidence_historical_status_retained']

def add(source, destination, category):
    source = Path(source)
    raw = source.read_bytes()
    entries.append({'source': str(source), 'destination_relative_path': destination,
        'category': category, 'source_identity': {'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'mode': f'{stat.S_IMODE(source.stat().st_mode):04o}'},
        'planned_published_mode': '0444', 'copy_state': 'planned_only_not_materialized'})

for directory, prefix in (
    (Path('/tmp/hmmer-api-p-004-evidence'), 'evidence/p-preparation-and-dispatch'),
    (Path('/tmp/gene-annotation-hmmer-api-planning-binding-evidence-20261022-004'), 'evidence/b-planning-binding'),
    (Path('/tmp/hmmer-api-r-004-evidence'), 'evidence/r-runtime'),
    (Path('/tmp/hmmer-api-root-connected-20261022-004'), 'evidence/root-development')):
    for path in sorted(directory.rglob('*')):
        if path.is_file():
            add(path, prefix+'/'+str(path.relative_to(directory)),
                'component_or_development_evidence_historical_status_retained')
root = Path('/tmp/api-planning-root-final-20261022-004')
for name in ('CONSUMERS_INPUTS.json', 'detached.log', 'detached.xml'):
    add(root/name, 'evidence/root-final/'+name, 'confirmed_root_final_input_or_detached_result')
xml = ET.parse(root/'detached.xml')
cases = list(xml.iter('testcase'))
assert len(cases) == 1 and not list(xml.iter('failure')) and not list(xml.iter('error'))
assert '1 passed in 26.97s' in (root/'detached.log').read_text()
assert len({row['destination_relative_path'] for row in entries}) == len(entries)
value = {**old, 'version': 'api004_publication_copy_plan_draft_v2', 'entries': entries,
    'categories': dict(Counter(row['category'] for row in entries)),
    'prior_draft': str(OUT/'COPY_PLAN.DRAFT.json'),
    'confirmed_actual_detached_fixture_path': '/tmp/pytest-of-chia/pytest-901/test_actual_scientific_worker_0',
    'fixture_database_policy': 'Do not open fixture DB. Await root-supplied backup/archive paths and explicit copy scope.',
    'root_final_detached': {'passed': 1, 'seconds': 26.97,
        'xml_testcase': cases[0].attrib, 'command_source': str(root/'INPUTS.json')},
    'pending': ['Completed root legacy/consumer log/XML/RESULTS/source guards and complete disjoint count ledger.',
        'Root-supplied fixture backup/archive paths and explicit copy scope.',
        'Final root/component evidence membership/hash recheck at materialization.',
        'Independent final review, exact report bytes, declared modes and final publication.'],
    'pending_root_final_files': ['legacy.log', 'legacy.xml', 'consumers.log', 'consumers.xml', 'RESULTS.json']}
path = OUT/'COPY_PLAN_002.DRAFT.json'
with path.open('x') as stream:
    stream.write(json.dumps(value, indent=2, sort_keys=True)+'\n')
print(json.dumps({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'entries': len(entries), 'categories': value['categories'], 'final_counts': None,
    'detached': value['root_final_detached']}, indent=2))
