"""Retain each 434 attempt and execute only readonly pinned sources."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
attempt = PACKET / sys.argv[1]
attempt.mkdir(exist_ok=False)
(attempt / 'temporary').mkdir()
snapshot = attempt / 'source_snapshot'
sources = []
for package in ('gene_annotation_episode', 'method_loop'):
    sources.extend(p for p in (REPO / package).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
sources.extend(REPO / p for p in ('tests/test_native_genomic_overlap_preparation.py', 'pyproject.toml'))
for packet in ('tool_graders_genomic_overlap_contract_2026-10-27_418',
    'tool_graders_genomic_overlap_native_contract_2026-10-27_425',
    'tool_graders_genomic_overlap_result_contract_2026-10-27_428',
    'tool_graders_genomic_overlap_implementation_2026-10-27_422'):
    sources.extend(p for p in (REPO / 'verification' / packet).glob('*')
        if p.is_file())
fixture_root = REPO / 'verification/tool_graders_genomic_overlap_result_worker_2026-10-27_432'
for case in ('three', 'empty_c'):
    sources.extend(p for p in (fixture_root / 'fixtures' / case).rglob('*') if p.is_file())
sources.extend([fixture_root / 'FIXTURE_PINS.json', Path(__file__), PACKET / 'verify_preparation.py'])
pins = []
for source, relative in [(p, p.relative_to(REPO)) for p in sorted(set(sources))]:
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    raw = source.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    target = snapshot / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    target.chmod(0o444)
    pins.append({'path': str(relative), 'source_path': str(source), 'sha256': sha, 'size_bytes': len(raw)})
for path in sorted([p for p in snapshot.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
snapshot.chmod(0o555)
(attempt / 'source_pins_before.json').write_text(json.dumps(pins, indent=2) + '\n')
interpreter = REPO / '.venv/bin/python'
binary_pin = {'path': str(interpreter), 'resolved': str(interpreter.resolve()),
    'sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest(), 'size_bytes': interpreter.stat().st_size}
(attempt / 'binary_pin_before.json').write_text(json.dumps(binary_pin, indent=2) + '\n')
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(interpreter), '-B', str(snapshot / (PACKET / 'verify_preparation.py').relative_to(REPO)),
        str(attempt), str(snapshot), *sys.argv[2:]]
environment = {'PYTHONPATH': str(snapshot), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(attempt), 'TMP': str(attempt), 'TEMP': str(attempt),
    'XDG_CACHE_HOME': str(attempt / 'cache'), 'PIP_CACHE_DIR': str(attempt / 'cache/pip')}
(attempt / 'selected_request.json').write_text(json.dumps({'argv': argv, 'cwd': str(attempt),
    'policy': policy.to_dict(), 'environment': environment, 'executed_source_root': str(snapshot)}, indent=2) + '\n')
receipt = {}
try:
    outcome = run_local_job(argv, cwd=attempt, policy=policy, stdout_path=attempt / 'stdout.txt',
                            stderr_path=attempt / 'stderr.txt', env=environment)
    receipt = {'returncode': outcome.returncode, 'metadata': outcome.metadata,
               'stdout_path': str(outcome.stdout_path), 'stderr_path': str(outcome.stderr_path)}
except Exception as error:
    receipt = {'returncode': None, 'exception_type': type(error).__name__, 'exception': str(error),
        'operational': getattr(error, 'operational', None)}
finally:
    after, checkout = [], []
    for pin in pins:
        for path, rows in ((snapshot / pin['path'], after), (Path(pin['source_path']), checkout)):
            raw = path.read_bytes()
            rows.append({**pin, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
    for name, rows in (('source_pins_after', after), ('checkout_source_pins_after', checkout)):
        (attempt / (name + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    binary_after = {'path': str(interpreter), 'resolved': str(interpreter.resolve()),
        'sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest(), 'size_bytes': interpreter.stat().st_size}
    (attempt / 'binary_pin_after.json').write_text(json.dumps(binary_after, indent=2) + '\n')
    receipt.update(executed_source_pins_unchanged=after == pins, binary_pins_unchanged=binary_pin == binary_after,
        checkout_drift=[{'before': a, 'after': b} for a, b in zip(pins, checkout) if a != b],
        executed_source_root=str(snapshot))
    (attempt / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'attempt': str(attempt), 'returncode': receipt['returncode'],
    'executed_source_pins_unchanged': receipt['executed_source_pins_unchanged'],
    'checkout_source_drift_count': len(receipt['checkout_drift'])}))
raise SystemExit(receipt['returncode'] if receipt['returncode'] is not None else 99)
