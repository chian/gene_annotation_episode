"""Execute only pinned437 tests inside the existing bounded local lifecycle."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
attempt = PACKET / sys.argv[1]
attempt.mkdir(exist_ok=False)
snapshot = attempt / 'source_snapshot'
temporary, cache = attempt / 'temporary', attempt / 'cache'
temporary.mkdir()
cache.mkdir()
sources = []
for package in ('gene_annotation_episode', 'method_loop'):
    sources.extend(p for p in (REPO / package).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
sources.extend(REPO / p for p in ('tests/test_native_genomic_overlap_workflow.py', 'pyproject.toml'))
for packet in ('tool_graders_genomic_overlap_contract_2026-10-27_418',
    'tool_graders_genomic_overlap_native_contract_2026-10-27_425',
    'tool_graders_genomic_overlap_result_contract_2026-10-27_428',
    'tool_graders_genomic_overlap_implementation_2026-10-27_422'):
    sources.extend(p for p in (REPO / 'verification' / packet).glob('*')
        if p.is_file())
for packet in ('tool_graders_protein_structure_workflow_2026-10-27_410',
    'tool_graders_protein_structure_execution_2026-10-27_390',
    'tool_graders_protein_structure_inputs_2026-10-27_386',
    'tool_graders_genomic_overlap_native_driver_2026-10-27_427'):
    sources.append(REPO / 'verification' / packet / 'fixture_helpers.py')
sources.extend(p for p in (REPO / 'research/slotted_process_library/publications/2026-10-24-001').rglob('*') if p.is_file())
sources.extend([Path(__file__), PACKET / 'fixture_helpers.py'])
pins = []
for source in sorted(set(sources)):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    target.chmod(0o444)
    pins.append({'path': str(relative), 'source_path': str(source),
        'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
for path in sorted([p for p in snapshot.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(attempt / 'source_pins_before.json').write_text(json.dumps(pins, indent=2) + '\n')
interpreter = REPO / '.venv/bin/python'
bedtools = REPO / 'software/bedtools/ubuntu-2.31.1+dfsg-2/installation/usr/bin/bedtools'
def binary_pins():
    return [{'path': str(path), 'resolved': str(path.resolve()),
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size_bytes': path.stat().st_size}
        for path in (interpreter, bedtools)]
binaries = binary_pins()
(attempt / 'binary_pins_before.json').write_text(json.dumps(binaries, indent=2) + '\n')
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(interpreter), '-B', '-m', 'pytest', '-vv', '--tb=short', '-p', 'no:cacheprovider',
    '--basetemp', str(temporary / 'pytest'), '--rootdir', str(snapshot),
    '--junitxml', str(attempt / 'junit.xml'), str(snapshot / 'tests/test_native_genomic_overlap_workflow.py'),
    *sys.argv[2:]]
environment = {'PYTHONPATH': str(snapshot), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(cache), 'PIP_CACHE_DIR': str(cache / 'pip')}
(attempt / 'selected_request.json').write_text(json.dumps({'argv': argv, 'cwd': str(attempt),
    'policy': policy.to_dict(), 'environment': environment, 'source_snapshot_readonly': True,
    'executed_source_root': str(snapshot)}, indent=2) + '\n')
receipt = {'returncode': None}
try:
    outcome = run_local_job(argv, cwd=attempt, policy=policy, stdout_path=attempt / 'stdout.txt',
        stderr_path=attempt / 'stderr.txt', env=environment)
    receipt = {'returncode': outcome.returncode, 'metadata': outcome.metadata,
        'stdout_path': str(outcome.stdout_path), 'stderr_path': str(outcome.stderr_path)}
except Exception as error:
    receipt.update(exception_type=type(error).__name__, exception=str(error),
        operational=getattr(error, 'operational', None))
finally:
    after, checkout = [], []
    for pin in pins:
        for path, values in ((snapshot / pin['path'], after), (Path(pin['source_path']), checkout)):
            if path.is_file():
                raw = path.read_bytes()
                values.append({**pin, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
            else:
                values.append({**pin, 'missing': True})
    for name, values in (('source_pins_after', after), ('checkout_source_pins_after', checkout)):
        (attempt / (name + '.json')).write_text(json.dumps(values, indent=2) + '\n')
    binaries_after = binary_pins()
    (attempt / 'binary_pins_after.json').write_text(json.dumps(binaries_after, indent=2) + '\n')
    receipt.update(executed_source_pins_unchanged=after == pins, binary_pins_unchanged=binaries == binaries_after,
        checkout_drift=[{'before': a, 'after': b} for a, b in zip(pins, checkout) if a != b],
        executed_source_root=str(snapshot))
    (attempt / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'attempt': str(attempt), 'returncode': receipt['returncode'],
    'executed_source_pins_unchanged': receipt['executed_source_pins_unchanged'],
    'checkout_source_drift_count': len(receipt['checkout_drift'])}))
raise SystemExit(receipt['returncode'] if receipt['returncode'] is not None else 99)
