"""Bounded, source-pinned verification of the exact RNA form registration."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
run = packet / sys.argv[1]
run.mkdir(exist_ok=False)
names = [
    'gene_annotation_episode/communication.py', 'gene_annotation_episode/runtime.py',
    'gene_annotation_episode/rna_structure_result_views.py',
    'gene_annotation_episode/rna_structure_contracts.py',
    'gene_annotation_episode/native_blast_database_result_views.py',
    'gene_annotation_episode/native_blast_standard_database_result_views.py',
    'gene_annotation_episode/form_reference_validation.py',
    'gene_annotation_episode/local_jobs.py', 'gene_annotation_episode/native_lifecycle.py',
    'tests/test_rna_structure_report_boundary.py', 'tests/test_communication.py',
    'tests/test_structure_selector_communication.py',
]
before = {}
for name in names:
    raw = (ROOT / name).read_bytes()
    before[name] = hashlib.sha256(raw).hexdigest()
    saved = run / 'source' / name
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_bytes(raw)
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q',
    *[str(ROOT / name) for name in names if name.startswith('tests/')],
    '--basetemp=' + str(run / 'pytest')]
policy = LocalJobPolicy(20*1024**3, 4*1024**3, None)
for name in ('tmp', 'cache'):
    (run / name).mkdir()
environment = {'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(run / 'tmp'), 'TMP': str(run / 'tmp'), 'TEMP': str(run / 'tmp'),
    'XDG_CACHE_HOME': str(run / 'cache')}
(run / 'request.json').write_text(json.dumps(dict(command=command, policy=policy.to_dict(),
    environment=environment, source_sha256_before=before), indent=2) + '\n')
result = run_local_job(command, cwd=run, policy=policy, stdout_path=run/'stdout.txt',
    stderr_path=run/'stderr.txt', env=environment)
after = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}
(run / 'receipt.json').write_text(json.dumps(dict(returncode=result.returncode,
    metadata=result.metadata, source_sha256_after=after, sources_unchanged=before == after), indent=2) + '\n')
print((run / 'stdout.txt').read_text())
print((run / 'stderr.txt').read_text())
print(json.dumps(dict(returncode=result.returncode, sources_unchanged=before == after)))
