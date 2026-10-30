"""Materialize authorized stable inputs in private unsealed staging only."""
from collections import Counter
import hashlib
import json
from pathlib import Path


OUT = Path('/tmp/api-planning-publication-preparation-20261022-001')
plan_path = OUT/'COPY_PLAN.DRAFT.json'
plan = json.loads(plan_path.read_text())
stage = OUT/'candidate'
stage.mkdir(mode=0o700)
exclude = {'component_or_development_evidence_historical_status_retained'}
copied = []
for row in plan['entries']:
    if row['category'] in exclude:
        continue
    source = Path(row['source'])
    expected = row['source_identity']
    raw = source.read_bytes()
    assert len(raw) == expected['bytes']
    assert hashlib.sha256(raw).hexdigest() == expected['sha256'], str(source)
    target = stage/row['destination_relative_path']
    assert not target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    target.chmod(0o755 if row['planned_published_mode'] == '0555' else 0o644)
    assert target.read_bytes() == raw
    copied.append({**row, 'stage_path': str(target), 'copy_state': 'copied_unsealed_staging_only'})

# Source/test and unchanged lineage checks are read-only; no source snapshot is
# finalized or chmodded. Root still owns final evidence and publication review.
for row in copied:
    path = Path(row['source'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == row['source_identity']['sha256']
    assert path.stat().st_size == row['source_identity']['bytes']
result = {'version': 'api004_stable_inputs_staged_v1', 'stage': str(stage),
    'root_authorization': 'Root confirmed scope029 source pin and corrected detached1pass26.97s before staging.',
    'copy_plan': str(plan_path), 'copy_plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
    'runtime_pin': plan['runtime_pin'], 'categories': dict(Counter(row['category'] for row in copied)),
    'copied_files': len(copied), 'copied_bytes': sum(row['source_identity']['bytes'] for row in copied),
    'entries': copied, 'source_and_parent_bytes_rechecked_unchanged': True,
    'state': 'private_unsealed_candidate_not_published', 'final_test_counts': None,
    'still_pending': ['completed root legacy/consumer logs/XML/results', 'final exact component metadata membership',
        'root fixture backup/archive paths and copy scope', 'root independent final review/publication']}
path = OUT/'STAGED_STATIC_INPUTS.json'
with path.open('x') as stream:
    stream.write(json.dumps(result, indent=2, sort_keys=True)+'\n')
print(json.dumps({key: result[key] for key in ('stage', 'runtime_pin', 'categories', 'copied_files', 'copied_bytes', 'state')}, indent=2))
