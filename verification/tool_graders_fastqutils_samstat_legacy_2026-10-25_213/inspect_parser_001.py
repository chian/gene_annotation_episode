"""Focused diagnostic execution; retains failures and exact candidate binding."""
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / 'verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate'
sys.path.insert(0, str(CANDIDATE))
from gene_annotation_episode.bvbrc_fastqutils_samstat_legacy import parse_samstat_html_2_2_3

rows = []
for path in sorted((CANDIDATE / 'tests/fixtures/bvbrc_fastqutils_samstat_legacy').rglob('*.html')):
    raw = path.read_bytes()
    context = {'analysis_id': 'legacy_test', 'document_id': 'report', 'task_ref': 'task:test',
        'content': {'source_ref': 'source:test', 'artifact_field': 'artifact_ref', 'artifact_ref': 'content:test',
                    'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)},
        'native_name': path.name, 'declared_format': 'samstat_html', 'producer_version': None,
        'transfer_scope': 'complete', 'identity': 'source_executed_synthetic'}
    row = {'fixture': str(path.relative_to(CANDIDATE))}
    try:
        doc = parse_samstat_html_2_2_3(raw, context=context)
        row.update(parse_scope=doc['parse_scope'], cells=len(doc['cells']), diagnostics=sorted({r['code'] for r in doc['diagnostics']}))
        if doc['parse_scope'] != 'complete':
            row['bad_sections'] = [s for s in doc['sections'] if s['state'] in ('malformed', 'partial')]
    except Exception as error:
        row.update(error=str(error), traceback=traceback.format_exc())
    rows.append(row)
print(json.dumps(rows, indent=2))
