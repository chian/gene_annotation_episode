"""Real007 counterexample and017 closure correction on constructed records."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
HERE = Path(__file__).resolve().parent
IMPL = BASE / 'a105_ratio_episode_integration_077/implementation_005'
name = 'gene_annotation_episode/literature_ratio_source_render.py'
current = (ROOT / name).read_text()
old_body = '''    sources = {row['evidence_source_ref'] for row in rows}
    return {ref for row in rows for ref in _refs(row)} | {
        ref for ref, record in records.items() if record.get('source_ref') in sources}'''
new_body = '''    hidden = {ref for row in rows for ref in _refs(row)}
    pending = list(hidden)
    while pending:
        reference = pending.pop()
        for dependency in _refs(records.get(reference, {})):
            if dependency not in hidden:
                hidden.add(dependency)
                pending.append(dependency)
    return hidden'''
assert current.count(new_body) == 1
original = current.replace(new_body, old_body)
old_manifest = json.loads((IMPL / 'source_review_007/SOURCE_REVIEW_MANIFEST_007.json').read_text())
expected = next(r for r in old_manifest['files'] if r['path'] == name)
assert hashlib.sha256(original.encode()).hexdigest() == expected['sha256']
old, new = {}, {}
exec(compile(original, 'verified_original007', 'exec'), old)
exec(compile(current, 'actual_current017', 'exec'), new)
row = {'candidate_basis': 'selected_received_source_representations',
       'uncertainty_evaluation': 'numeric_uncertainty_reader_unimplemented',
       'evidence_source_ref': 'source_constructed', 'sheet_ref': 'sheet_constructed',
       'condition_ref': 'context_constructed'}
records = {'context_constructed': {'source_ref': 'source_constructed', 'related_refs': ['private_operand']},
           'private_operand': {'source_ref': 'source_constructed', 'label': '128.000 / 200.000'},
           'separate_received_fact': {'source_ref': 'source_constructed', 'label': 'Independent received fact'}}
reports = [{'requested_signal': [row]}]
before = old['hidden_records'](reports, records)
after = new['hidden_records'](reports, records)
assert 'separate_received_fact' in before and 'separate_received_fact' not in after
assert 'context_constructed' in after and 'private_operand' in after
cyclic = dict(records)
cyclic['private_operand'] = {**records['private_operand'], 'related_refs': ['context_constructed']}
assert new['hidden_records'](reports, cyclic) == after
result = {'utc': datetime.now(timezone.utc).isoformat(),
    'evidence_class': 'Constructed display-only counterexample against hash-verified actual007 module',
    'original007_incorrectly_hides_unlinked_same_source_fact': True,
    'current017_preserves_unlinked_same_source_fact': True,
    'current017_hides_actual_context_related_operand_closure': True,
    'cycle_terminates_without_added_refs': True,
    'old_source_sha256': expected['sha256'], 'new_source_sha256': hashlib.sha256(current.encode()).hexdigest(),
    'source_or_model_or_repository_callbacks': False,
    'scope': 'Pure display selection only; final017 coherent integration tests still pending', 'goal_complete': False}
with (HERE / 'SAME_SOURCE_DISPLAY_ROOT_RECEIPT_055.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
