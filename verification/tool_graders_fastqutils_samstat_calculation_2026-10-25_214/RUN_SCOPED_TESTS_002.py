"""Record local pytest evidence against an unchanged candidate source manifest."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

EVIDENCE = Path(__file__).resolve().parent
REPOSITORY = EVIDENCE.parents[1]
CANDIDATE = REPOSITORY / 'verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate'
label, *selectors = sys.argv[1:]
assert label.isidentifier() and selectors
scratch = EVIDENCE / ('scratch_' + label)
scratch.mkdir()

def snapshot():
    return {str(path.relative_to(CANDIDATE)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(CANDIDATE.rglob('*')) if path.is_file()
            and not any(part in {'__pycache__', '.pytest_cache'} for part in path.parts)}

before = snapshot()
manifest = EVIDENCE / (label + '_SOURCE.json')
manifest.write_text(json.dumps(before, indent=2) + '\n')
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
command = [str(REPOSITORY / '.venv/bin/python'), '-m', 'pytest', *selectors,
           '-q', '--tb=short', '--basetemp=' + str(scratch / 'pytest')]
started = datetime.now(timezone.utc).isoformat()
start = time.monotonic()
log = EVIDENCE / (label + '.log')
with log.open('w') as stream:
    result = subprocess.run(command, cwd=CANDIDATE, stdout=stream, stderr=subprocess.STDOUT)
elapsed = time.monotonic() - start
after = snapshot()
scratch_bytes = sum(p.stat().st_size for p in scratch.rglob('*') if p.is_file())
record = dict(command=command, cwd=str(CANDIDATE), started_at=started,
              exit_code=result.returncode, elapsed_seconds=elapsed,
              log=str(log.relative_to(REPOSITORY)), log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
              source_manifest=str(manifest.relative_to(REPOSITORY)),
              source_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
              source_unchanged=before == after,
              changed_files=[name for name in sorted(before.keys() | after.keys()) if before.get(name) != after.get(name)],
              limits=dict(address_space_bytes=20 * 1024**3, per_file_bytes=4 * 1024**3,
                          scratch_budget_bytes=4 * 1024**3, measured_scratch_bytes=scratch_bytes, wall_time_cap=None),
              max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
(EVIDENCE / (label + '.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record))
print(log.read_text())
assert before == after
assert scratch_bytes < 4 * 1024**3
raise SystemExit(result.returncode)
