"""Pin sources and interpreter; retain the one original bounded native handle."""
from pathlib import Path
import hashlib
import json
import sys



def note_provenance_path(value):
    """Exclude recognized governance names and the known retired note paths."""
    path = Path(value)
    if path.name.lower() in {'agents.md', 'agent.md', 'goal.md'}:
        return True
    known_paths = (
        'verification/tool_graders_chromatin_interaction_contract_2026-10-27_439/CONTRACT.md',
        'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_IMPLEMENTATION_HANDOFF_014.md',
        'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/HIC_WORKFLOW_VERIFICATION_015.md',
        'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/FULL_WORKFLOW_VERIFICATION_011.md',
        'verification/tool_graders_chromatin_interaction_implementation_2026-10-27_441/COMPLETE_EMPTY_POPULATION_CHECK_012.md',
        'verification/tool_graders_atac_native_contract_2026-10-27_461/CONTRACT.md',
        'verification/tool_graders_atac_execution_contract_2026-10-27_466/CONTRACT.md',
    )
    normalized = path.as_posix()
    return any(normalized == known or normalized.endswith('/' + known)
               for known in known_paths)


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
    sources.extend(path for path in (REPO / package).rglob('*')
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
sources.extend(REPO / path for path in ('tests/test_atac_differential_returns.py',
    'pyproject.toml',   
     
    ))
sources.extend(path for path in (REPO / 'tests').glob('test_atac_differential_*') if path.is_file())
for packet in ('tool_graders_atac_execution_contract_2026-10-27_466',
    'tool_graders_atac_native_contract_2026-10-27_461'):
    sources.extend(path for path in (REPO / 'verification' / packet).glob('*.md')
        if path.is_file() and not note_provenance_path(path))
sources.extend([Path(__file__), PACKET / 'verify_worker.py'])
entries = [(path, path.relative_to(REPO)) for path in sorted(set(sources))]
pins = []
for source, relative in entries:
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
    'sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest()}
(attempt / 'binary_pin_before.json').write_text(json.dumps(binary_pin, indent=2) + '\n')
sys.path.insert(0, str(snapshot))
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_lifecycle import NativeJobHandle, start_job, status, wait_job

policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(interpreter), '-B', str(snapshot / (PACKET / 'verify_worker.py').relative_to(REPO)),
    str(attempt), str(snapshot), *sys.argv[2:]]
environment = {'PYTHONPATH': str(snapshot), 'PYTHONDONTWRITEBYTECODE': '1',
    'TMPDIR': str(temporary), 'TMP': str(temporary), 'TEMP': str(temporary),
    'XDG_CACHE_HOME': str(cache), 'PIP_CACHE_DIR': str(cache / 'pip')}
handle_path = attempt / 'native.handle.json'
(attempt / 'selected_request.json').write_text(json.dumps({'argv': argv, 'cwd': str(attempt),
    'policy': policy.to_dict(), 'environment': environment, 'swap_bytes': 0,
    'source_snapshot_readonly': True, 'executed_source_root': str(snapshot),
    'handle_path': str(handle_path)}, indent=2) + '\n')
try:
    handle = start_job(argv, cwd=attempt, policy=policy, handle_path=handle_path,
        stdout_path=attempt / 'stdout.txt', stderr_path=attempt / 'stderr.txt', env=environment)
    outcome = wait_job(handle)
    receipt = {'returncode': outcome.returncode, 'metadata': outcome.metadata,
        'stdout_path': str(outcome.stdout_path), 'stderr_path': str(outcome.stderr_path),
        'original_handle': str(handle_path), 'final_status': status(handle)}
except Exception as error:
    receipt = {'returncode': None, 'exception_type': type(error).__name__, 'exception': str(error),
        'original_handle': str(handle_path)}
    if handle_path.exists():
        receipt['final_status'] = status(NativeJobHandle(handle_path))
finally:
    after, checkout = [], []
    for pin in pins:
        for path, rows in ((snapshot / pin['path'], after), (Path(pin['source_path']), checkout)):
            raw = path.read_bytes()
            rows.append({**pin, 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
    for name, rows in (('source_pins_after', after), ('checkout_source_pins_after', checkout)):
        (attempt / (name + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    binary_after = {'path': str(interpreter), 'resolved': str(interpreter.resolve()),
        'sha256': hashlib.sha256(interpreter.read_bytes()).hexdigest()}
    (attempt / 'binary_pin_after.json').write_text(json.dumps(binary_after, indent=2) + '\n')
    receipt.update(executed_source_pins_unchanged=after == pins, binary_pins_unchanged=binary_pin == binary_after,
        checkout_drift=[{'before': a, 'after': b} for a, b in zip(pins, checkout) if a != b],
        executed_source_root=str(snapshot))
    (attempt / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'attempt': str(attempt), 'returncode': receipt['returncode'],
    'executed_source_pins_unchanged': receipt['executed_source_pins_unchanged'],
    'checkout_source_drift_count': len(receipt['checkout_drift']), 'original_handle': str(handle_path)}))
raise SystemExit(receipt['returncode'] if receipt['returncode'] is not None else 99)
