"""Verify exact provider delivery from a retained snapshot using local_jobs."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
tests = sys.argv[2:] or [
    'tests/test_rna_structure_results_prompt.py',
    'tests/test_rna_structure_prompt_delivery.py',
    'tests/test_rna_structure_presentation.py',
    'tests/test_rna_comparison_prompt_delivery.py',
    'tests/test_rna_comparison_results_prompt.py',
    'tests/test_rna_comparison_receiver_prompt.py',
    'tests/test_rna_comparison_scientific_prompt.py',
    'tests/test_rna_comparison_presentation.py',
    'tests/test_scientific_process_prompt_delivery.py',
    'tests/test_decision_provider_frames.py',
    'tests/test_literature_experimental_prompt_delivery.py',
]
snapshot = directory / 'source_snapshot'
files = [path for package in ('gene_annotation_episode', 'method_loop')
    for path in (ROOT / package).rglob('*') if path.is_file() and '__pycache__' not in path.parts
    and path.suffix in {'.py', '.json', '.md', '.toml', '.txt'}]
files += [ROOT / 'pyproject.toml', Path(__file__), PACKET / 'baseline_providers.py']
files += [ROOT / test.split('::')[0] for test in tests]
files += [ROOT / 'tests' / name for name in (
    'test_rna_structure_results_prompt.py', 'test_rna_structure_prompt_delivery.py',
    'test_rna_comparison_prompt_delivery.py', 'test_rna_comparison_receiver_prompt.py',
    'test_rna_comparison_results_prompt.py', 'test_rna_comparison_presentation.py',
    'test_scientific_process_prompt_delivery.py', 'test_literature_experimental_prompt_delivery.py')]
files += [ROOT / 'verification' / name / 'fixture_helpers.py' for name in (
    'tool_graders_rna_comparison_inputs_2026-10-26_366',
    'tool_graders_rna_comparison_calculations_2026-10-26_367')]
files += [ROOT / 'verification' / path for path in (
    'tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_PAIR_001.json',
    'tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_SCAN_001.json',
    'tool_graders_rna_scientific_text_integration_2026-10-27_379/baseline_scientific_process_prompt.py',
    'tool_graders_rna_results_text_2026-10-27_381/baseline_execution_instructions.txt',
    'tool_graders_rna_comparison_prompt_delivery_2026-10-27_383/baseline_providers.py',
    'tool_graders_rna_structure_integration_2026-10-26_360/NUMERICAL_EXAMPLES.json',
)]


def identity(path):
    data = path.read_bytes()
    return dict(sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))


before = []
for path in sorted(set(files)):
    relative = path.relative_to(ROOT)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes())
    before.append(dict(path=str(relative), **identity(path)))
(directory / 'source_pins_before.json').write_text(json.dumps(before, indent=2) + '\n')
temporary, cache = directory / 'temporary', directory / 'cache'
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-x', '-p', 'no:cacheprovider',
    '--basetemp', str(temporary / 'pytest'), *[str(snapshot / test) for test in tests]]
environment = dict(PYTHONPATH=str(snapshot), PYTHONDONTWRITEBYTECODE='1',
    TMPDIR=str(temporary), TMP=str(temporary), TEMP=str(temporary), XDG_CACHE_HOME=str(cache))
(directory / 'request.json').write_text(json.dumps(dict(command=command, cwd=str(directory),
    policy=policy.to_dict(), environment=environment, execution_source='source_snapshot'), indent=2) + '\n')
result = run_local_job(command, cwd=directory, policy=policy, env=environment,
    stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt')
after = [dict(path=row['path'], **identity(ROOT / row['path'])) for row in before]
executed = [dict(path=row['path'], **identity(snapshot / row['path'])) for row in before]
(directory / 'source_pins_after.json').write_text(json.dumps(after, indent=2) + '\n')
(directory / 'snapshot_pins_after.json').write_text(json.dumps(executed, indent=2) + '\n')
receipt = dict(returncode=result.returncode, metadata=result.metadata,
    live_source_pins_unchanged=after == before, executed_snapshot_pins_unchanged=executed == before)
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
print((directory / 'stdout.txt').read_text()[-5500:])
print((directory / 'stderr.txt').read_text()[-1500:])
raise SystemExit(result.returncode)
