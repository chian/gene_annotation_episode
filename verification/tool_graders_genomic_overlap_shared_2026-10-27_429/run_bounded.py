"""One retained readonly-source check of the shared overlap hooks."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
ATTEMPT = PACKET / sys.argv[1]
ATTEMPT.mkdir(exist_ok=False)
snapshot = ATTEMPT / 'source_snapshot'
sources = []
for package in ('gene_annotation_episode', 'method_loop'):
    sources += [p for p in (ROOT / package).rglob('*')
                if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
sources += list((ROOT / 'tests').glob('*.py'))
sources += [ROOT / 'pyproject.toml']
sources.append(ROOT / 'verification/tool_graders_genomic_overlap_execution_contracts_2026-10-27_426/fixtures.py')
for directory in ('tool_graders_genomic_overlap_contract_2026-10-27_418',
                  'tool_graders_genomic_overlap_native_contract_2026-10-27_425',
                  'tool_graders_genomic_overlap_implementation_2026-10-27_422'):
    sources += [p for p in (ROOT / 'verification' / directory).iterdir()
                if p.is_file()]
for label in ('nhmmer_sequence_ordinary', 'nhmmer_profile_ordinary', 'hmmscan_search_ordinary'):
    sources.append(ROOT / 'verification/tool_graders_native_hmmer_producer_2026-10-24/runs' / label / 'plan.json')
for relative in (
        'tool_graders_mauve_sidecars_2026-10-25/FILLED_EXAMPLES_001.json',
        'tool_graders_mauve_v4_2026-10-25/official_small.document.json',
        'tool_graders_mauve_v4_2026-10-25/official_small.components.json',
        'tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/retained_sources/mauve/testdata/small.mauve'):
    sources.append(ROOT / 'verification' / relative)
sources.append(Path(__file__))
pins = []
for source in sorted(set(sources)):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    relative = source.relative_to(ROOT)
    raw = source.read_bytes()
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    destination.chmod(0o444)
    pins.append({'path': str(relative), 'source_path': str(source),
                 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw)})
for directory in sorted((p for p in snapshot.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    directory.chmod(0o555)
snapshot.chmod(0o555)
for name in ('temporary', 'cache'):
    (ATTEMPT / name).mkdir()
(ATTEMPT / 'source_pins_before.json').write_text(json.dumps(pins, indent=2) + '\n')
interpreter = ROOT / '.venv/bin/python'
binary_pin = {'path': str(interpreter), 'resolved': str(interpreter.resolve()),
              'sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest()}
(ATTEMPT / 'binary_pin_before.json').write_text(json.dumps(binary_pin, indent=2) + '\n')
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
tests = sys.argv[2:] or ['test_native_genomic_overlap_shared.py', 'test_practical_execution_state.py', 'test_execution_progress.py',
         'test_execution_episodes_family.py', 'test_execution_tool_contract_declarations.py',
         'test_native_genomic_overlap_contracts.py', 'test_native_genomic_overlap_tool_info.py']
argv = [str(interpreter), '-B', '-m', 'pytest', '-q', '-c', str(snapshot / 'pyproject.toml'),
        *[str(snapshot / 'tests' / name) for name in tests],
        '--basetemp', str(ATTEMPT / 'temporary/pytest'), '--junitxml', str(ATTEMPT / 'pytest.xml'),
        '-o', 'cache_dir=' + str(ATTEMPT / 'cache')]
environment = {'PYTHONPATH': str(snapshot), 'PYTHONDONTWRITEBYTECODE': '1',
               'TMPDIR': str(ATTEMPT / 'temporary'), 'XDG_CACHE_HOME': str(ATTEMPT / 'cache')}
(ATTEMPT / 'selected_request.json').write_text(json.dumps({'argv': argv, 'policy': policy.to_dict(),
    'environment': environment, 'cwd': str(ATTEMPT)}, indent=2) + '\n')
try:
    result = run_local_job(argv, cwd=ATTEMPT, policy=policy, stdout_path=ATTEMPT / 'stdout.txt',
                           stderr_path=ATTEMPT / 'stderr.txt', env=environment)
    receipt = {'returncode': result.returncode, 'metadata': result.metadata}
except Exception as error:
    receipt = {'returncode': None, 'exception_type': type(error).__name__, 'exception': str(error)}
finally:
    executed, checkout = [], []
    for pin in pins:
        for path, output in ((snapshot / pin['path'], executed), (Path(pin['source_path']), checkout)):
            if path.is_file():
                raw = path.read_bytes()
                output.append({**pin, 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_length': len(raw)})
            else:
                output.append({'path': pin['path'], 'missing': True})
    (ATTEMPT / 'source_pins_after.json').write_text(json.dumps(executed, indent=2) + '\n')
    (ATTEMPT / 'checkout_source_pins_after.json').write_text(json.dumps(checkout, indent=2) + '\n')
    binary_after = {'path': str(interpreter), 'resolved': str(interpreter.resolve()),
                    'sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest()}
    (ATTEMPT / 'binary_pin_after.json').write_text(json.dumps(binary_after, indent=2) + '\n')
    receipt.update(executed_source_pins_unchanged=executed == pins,
        binary_pins_unchanged=binary_pin == binary_after,
        checkout_source_drift=[{'before': a, 'after': b} for a, b in zip(pins, checkout) if a != b])
    (ATTEMPT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
raise SystemExit(receipt['returncode'] if receipt['returncode'] is not None else 99)
