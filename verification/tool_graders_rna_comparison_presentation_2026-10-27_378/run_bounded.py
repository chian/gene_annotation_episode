"""Run the focused pure presentation checks under the existing local policy."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

packet = Path(__file__).resolve().parent
out = packet / sys.argv[1]
out.mkdir(exist_ok=False)
for name in ('tmp', 'cache', 'source_snapshot'):
    (out / name).mkdir()
sources = [ROOT / 'gene_annotation_episode' / name for name in (
    'rna_structure_comparison_presentation.py', 'rna_structure_comparison_views.py',
    'rna_structure_comparison_contracts.py', 'rna_structure_comparison_inputs.py',
    'rna_structure_comparison_calculations.py', 'rna_structure_scan_calculations.py',
    'rna_structure_contracts.py', 'rna_structure_topology.py', 'rna_structure_native.py',
    'rna_structure_calculations.py', 'local_jobs.py', 'native_lifecycle.py', '_local_job_worker.py')]
sources += [ROOT / 'tests/test_rna_comparison_presentation.py', Path(__file__),
    packet / 'IMPLEMENTATION_CONTRACT_001.md']
sources += [ROOT / 'verification' / name / 'fixture_helpers.py' for name in (
    'tool_graders_rna_comparison_inputs_2026-10-26_366', 'tool_graders_rna_comparison_calculations_2026-10-26_367')]
sources += [ROOT / 'verification/tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_SCAN_001.json']


def pins(before):
    rows = []
    for path in sources:
        raw = path.read_bytes()
        rows.append(dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
        if before:
            target = out / 'source_snapshot' / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    (out / ('source_before.json' if before else 'source_after.json')).write_text(json.dumps(rows, indent=2) + '\n')
    return rows


before = pins(True)
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp', str(out / 'tmp/pytest'), str(ROOT / 'tests/test_rna_comparison_presentation.py')]
environment = dict(PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(out / 'tmp'),
    TMP=str(out / 'tmp'), TEMP=str(out / 'tmp'), XDG_CACHE_HOME=str(out / 'cache'))
(out / 'request.json').write_text(json.dumps(dict(command=command, cwd=str(out), policy=policy.to_dict()), indent=2) + '\n')
result = run_local_job(command, cwd=out, policy=policy, env=environment,
    stdout_path=out / 'stdout.txt', stderr_path=out / 'stderr.txt')
after = pins(False)
(out / 'receipt.json').write_text(json.dumps(dict(returncode=result.returncode, metadata=result.metadata,
    source_pins_unchanged=before == after), indent=2) + '\n')
print(json.dumps(dict(returncode=result.returncode, source_pins_unchanged=before == after)))
print((out / 'stdout.txt').read_text()[-5500:])
print((out / 'stderr.txt').read_text()[-1500:])
sys.exit(result.returncode)
