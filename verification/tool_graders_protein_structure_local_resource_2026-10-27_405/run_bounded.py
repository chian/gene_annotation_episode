"""Execute only retained selected source bytes in the caller's fixed boundary."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[1]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

directory = PACKET / sys.argv[1]
directory.mkdir(exist_ok=False)
snapshot = directory / 'source_snapshot'
temporary, cache = directory / 'temporary', directory / 'cache'
temporary.mkdir()
cache.mkdir()
tests = sys.argv[2:] or ['tests/test_native_protein_structure_local_resource.py']
files = [p for p in (REPO/'gene_annotation_episode').rglob('*')
    if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
files += [REPO/t.split('::')[0] for t in tests]
files += [PACKET/'run_bounded.py']
for packet, names in (
    ('tool_graders_protein_structure_execution_2026-10-27_390', ['fixture_helpers.py']),
    ('tool_graders_protein_structure_inputs_2026-10-27_386', ['fixture_helpers.py']),
):
    files.extend(REPO/'verification'/packet/name for name in names)
files.extend((REPO/'verification/tool_graders_protein_structure_inputs_2026-10-27_386/fixtures').glob('*'))
files.extend(p for p in (REPO / 'verification/tool_graders_protein_structure_shared_contract_2026-10-27_380').glob('*.md')
    if p.name.casefold() not in {'agents.md', 'agent.md', 'goal.md'})
pins = []
for source in dict.fromkeys(files):
    if source.name.casefold() in {'agents.md', 'agent.md', 'goal.md'}:
        continue
    if not source.is_file():
        continue
    raw = source.read_bytes()
    relative = source.relative_to(REPO)
    retained = snapshot/relative
    retained.parent.mkdir(parents=True, exist_ok=True)
    retained.write_bytes(raw)
    retained.chmod(0o444)
    pins.append({'path': str(relative), 'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
(directory/'source_pins_before.json').write_text(json.dumps(pins, indent=2)+'\n')
policy = LocalJobPolicy(memory_bytes=21474836480, scratch_bytes=4294967296, wall_seconds=None)
argv = [str(REPO/'.venv/bin/python'), '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
    '--basetemp', str(temporary/'pytest'), *[str(snapshot/t) for t in tests]]
environment = {'PYTHONPATH': str(snapshot), 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(temporary),
    'TMP': str(temporary), 'TEMP': str(temporary), 'XDG_CACHE_HOME': str(cache), 'PIP_CACHE_DIR': str(cache/'pip')}
(directory/'selected_request.json').write_text(json.dumps({'argv': argv, 'cwd': str(directory),
    'policy': policy.to_dict(), 'environment': environment}, indent=2)+'\n')
try:
    result = run_local_job(argv, cwd=directory, policy=policy, stdout_path=directory/'stdout.txt',
        stderr_path=directory/'stderr.txt', env=environment)
    receipt = {'returncode': result.returncode, 'metadata': result.metadata,
        'stdout_path': str(result.stdout_path), 'stderr_path': str(result.stderr_path)}
except Exception as error:
    receipt = {'returncode': None, 'exception_type': type(error).__name__, 'exception': str(error)}
finally:
    after = [{'path': p['path'], 'sha256': hashlib.sha256((snapshot/p['path']).read_bytes()).hexdigest(),
        'size_bytes': (snapshot/p['path']).stat().st_size} for p in pins]
    (directory/'source_pins_after.json').write_text(json.dumps(after, indent=2)+'\n')
    receipt['source_pins_unchanged'] = pins == after
    receipt['source_drift'] = [{'before': a, 'after': b} for a, b in zip(pins, after) if a != b]
    (directory/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'directory': str(directory), 'returncode': receipt['returncode'],
    'source_pins_unchanged': receipt['source_pins_unchanged']}))
raise SystemExit(receipt['returncode'] if receipt['returncode'] is not None else 99)
