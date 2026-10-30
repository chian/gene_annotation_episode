"""Check additive planning bytes only; no application imports/data/DB opens."""
from pathlib import Path
import hashlib
import json
root=Path(__file__).resolve().parent
prior=Path('/tmp/scientific-checkpoint-custody-contract-20261022-001-9ILLrc')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
expected={p.name for p in prior.iterdir() if p.is_file()}
actual={p.name for p in (root/'prior001').iterdir() if p.is_file()}
assert expected==actual
for name in expected:
    assert sha(prior/name)==sha(root/'prior001'/name)
    assert (prior/name).stat().st_size==(root/'prior001'/name).stat().st_size
assert sha(root/'SCHEMAS002.json')=='947bd0293030cbfa7cb995b240c1a27cf4b726d4728ad557d017fb453f29b0f2'
assert sha(root/'CONTRACT004.md')=='4f28639c2c2f3be8cfc779d82c19507d3bab1cf4d71ce69319cde054a36425d6'
text=(root/'CONTRACT004.md').read_text()
assert 'Source, run, implementation, case directories and destination must not overlap' not in text
assert 'The DESTINATION must neither equal, contain nor lie inside' in text
assert 'target.faa is required/copied only when actually declared' in text
proof=json.loads((root/'ACTUAL_CASE_AUTHORITY.json').read_text())
assert proof['target_faa_declared'] is True
assert {row['declared_name'] for row in proof['declared_target_files']}=={'target.fna','target.faa'}
assert all(row['matches'] is True and row['actual']['sha256']==row['declared_sha256'] for row in proof['declared_target_files'])
print(json.dumps({'status':'additive_planning_guards_passed','prior_files_exact':len(expected),
    'schema_unchanged':True,'contract_corrections_present':True,
    'actual_selected_case_declared_target_files':2,'scientific_DB_opens':0,
    'application_imports':0,'application_tests':0,'actual_forks':0},sort_keys=True))
