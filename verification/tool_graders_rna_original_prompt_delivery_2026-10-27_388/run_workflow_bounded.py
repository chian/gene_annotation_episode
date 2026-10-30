"""Verify current388 messages through the existing one-input and native RNA Workflow."""
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
    'tests/test_rna_one_structure_workflow.py',
    'tests/test_native_rna_structure_results_integration.py',
]

snapshot = directory / 'source_snapshot'
files = [path for package in ('gene_annotation_episode', 'method_loop')
    for path in (ROOT / package).rglob('*') if path.is_file() and '__pycache__' not in path.parts
    and path.suffix in {'.py', '.json', '.md', '.toml', '.txt'}]
files += [ROOT / 'pyproject.toml', Path(__file__), ROOT / 'verification/tool_graders_rna_one_structure_workflow_2026-10-27_385/helpers.py',
    ROOT / 'verification/tool_graders_rna_one_structure_workflow_2026-10-27_385/baseline_rna_structure_comparison_prompt.py']
files += [ROOT / test.split('::')[0] for test in tests]
files += [ROOT / 'tests' / name for name in (
    'test_native_rna_structure_results_integration.py', 'test_native_rna_structure_contracts.py',
    'test_native_rna_structure_acquisition.py', 'test_scientific_process_prompt_delivery.py',
    'test_rna_comparison_prompt_delivery.py', 'test_rna_comparison_receiver_prompt.py',
    'test_rna_comparison_results_prompt.py', 'test_rna_comparison_presentation.py',
    'test_literature_experimental_prompt_delivery.py', 'fixtures/rna_comparison_shared_372/helpers.py')]
files += [ROOT / 'verification' / name / 'fixture_helpers.py' for name in (
    'tool_graders_rna_structure_core_2026-10-26_354',
    'tool_graders_rna_structure_results_2026-10-26_358',
    'tool_graders_rna_comparison_inputs_2026-10-26_366',
    'tool_graders_rna_comparison_calculations_2026-10-26_367')]
files += [ROOT / 'verification' / path for path in (
    'tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_PAIR_001.json',
    'tool_graders_rna_comparison_shared_integration_2026-10-26_372/FILLED_ACTUAL_SCAN_001.json',
    'tool_graders_rna_scientific_text_integration_2026-10-27_379/baseline_scientific_process_prompt.py',
    'tool_graders_rna_results_text_2026-10-27_381/baseline_execution_instructions.txt',
    'tool_graders_rna_comparison_prompt_delivery_2026-10-27_383/baseline_providers.py')]
files += [path for path in (ROOT / 'research/slotted_process_library/publications/2026-10-24-001').rglob('*')
    if path.is_file() and '__pycache__' not in path.parts]
native_packet = ROOT / 'verification/tool_graders_rna_structure_producer_2026-10-26_357'
files.append(native_packet / 'probe001/probe.json')
files += [path for path in (native_packet / 'native-site').rglob('*')
    if path.is_file() and '__pycache__' not in path.parts]


def identity(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}


before = []
for path in sorted(set(files)):
    relative = path.relative_to(ROOT)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(path.read_bytes())
    before.append({'path': str(relative), **identity(path)})
(directory / 'source_pins_before.json').write_text(json.dumps(before, indent=2) + '\n')
temporary, cache = directory / 'temporary', directory / 'cache'
temporary.mkdir()
cache.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [str(ROOT / '.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-x', '-p', 'no:cacheprovider',
    '--basetemp', str(temporary / 'pytest'), *[str(snapshot / test) for test in tests]]
environment = {'PYTHONPATH': str(snapshot), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(cache), 'PIP_CACHE_DIR': str(cache / 'pip')}
(directory / 'request.json').write_text(json.dumps({'command': command, 'cwd': str(directory),
    'policy': policy.to_dict(), 'environment': environment, 'execution_source': 'source_snapshot'}, indent=2) + '\n')
result = run_local_job(command, cwd=directory, policy=policy, env=environment,
    stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt')
after = [{'path': row['path'], **identity(ROOT / row['path'])} for row in before]
executed = [{'path': row['path'], **identity(snapshot / row['path'])} for row in before]
(directory / 'source_pins_after.json').write_text(json.dumps(after, indent=2) + '\n')
(directory / 'snapshot_pins_after.json').write_text(json.dumps(executed, indent=2) + '\n')
receipt = {'returncode': result.returncode, 'metadata': result.metadata,
    'live_source_pins_unchanged': after == before, 'executed_snapshot_pins_unchanged': executed == before}
(directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
print((directory / 'stdout.txt').read_text()[-6500:])
print((directory / 'stderr.txt').read_text()[-1500:])
raise SystemExit(result.returncode)
