"""Retain source-bound native documents and a compact leaf implementation receipt."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate'
FIXTURES = CANDIDATE / 'tests/fixtures/bvbrc_fastqutils_samstat_legacy'
sys.path.insert(0, str(CANDIDATE))
from gene_annotation_episode.bvbrc_fastqutils_samstat_legacy import parse_samstat_html_2_2_3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


rows = []
metrics = Counter()
for path in sorted(FIXTURES.rglob('*.html')):
    raw = path.read_bytes()
    relative = str(path.relative_to(FIXTURES))
    context = {'analysis_id': 'samstat_legacy_evidence', 'document_id': 'report', 'task_ref': 'task:local_synthetic',
        'content': {'source_ref': 'source:local_synthetic', 'artifact_field': 'artifact_ref', 'artifact_ref': 'content:' + digest(path),
                    'sha256': digest(path), 'byte_count': len(raw)},
        'native_name': path.name, 'declared_format': 'samstat_html', 'producer_version': None,
        'transfer_scope': 'complete', 'identity': 'source_executed_synthetic'}
    document = parse_samstat_html_2_2_3(raw, context=context)
    target = HERE / 'parsed_native_002' / (relative + '.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, allow_nan=False) + '\n')
    metric_counts = Counter(c['metric'] for c in document['cells'])
    metrics.update(metric_counts)
    rows.append({'fixture': str(path.relative_to(ROOT)), 'sha256': digest(path),
                 'parsed_document': str(target.relative_to(ROOT)), 'parse_scope': document['parse_scope'],
                 'cell_count': len(document['cells']), 'metric_counts': dict(sorted(metric_counts.items()))})
owned = [CANDIDATE / 'gene_annotation_episode/bvbrc_fastqutils_samstat_legacy.py',
         CANDIDATE / 'tests/test_bvbrc_fastqutils_samstat_legacy.py']
manifest = {'public_signature': 'parse_samstat_html_2_2_3(raw: bytes, *, context: dict) -> dict',
            'owned_code': {str(p.relative_to(ROOT)): digest(p) for p in owned},
            'fixture_directory': str(FIXTURES.relative_to(ROOT)), 'fixture_count': len(rows),
            'native_documents': rows, 'observed_native_metric_counts': dict(sorted(metrics.items())),
            'proof': 'pure native parser and local source-executed synthetic fixtures only',
            'not_established': ['live BV-BRC deployment/version', 'full selected tool through episode return',
                                'calculator integration (root ownership)', 'production installation'],
            'preserved_failures': ['NATIVE_RUN_RECEIPTS_001.json: two loader failures exit127',
                                  'PYTEST_ATTEMPT_002.log: terminal empty native cluster label',
                                  'PYTEST_ATTEMPT_004.log: test variable shadowed fixture name'],
            'final_focused_log': 'PYTEST_ATTEMPT_007.log',
            'mode_port': {'kind': 'native_label', 'value': 'Mapping statistics', 'section_key': 'samstat_summary', 'section_ordinal': 0},
            'population_port': 'samstat_report_records ordinal1/2 with mutual disjoint_from_refs; conditional ordinal0 is their parent, never disjoint',
            'dependencies': ['bvbrc_fastqutils_contracts', 'bvbrc_fastqutils_fastqc_reader']}
(HERE / 'IMPLEMENTATION_HANDOFF_002.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'fixtures': len(rows), 'native_cells': sum(metrics.values()), 'metrics': sorted(metrics),
                  'code_hashes': manifest['owned_code']}, indent=2))
