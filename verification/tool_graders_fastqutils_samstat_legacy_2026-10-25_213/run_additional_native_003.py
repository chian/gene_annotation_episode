"""Tiny unclustered native counterpart covers every mismatch-base symbol."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = ROOT / 'verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207'
BINARY = CONTRACT / 'sources/build_2_2_3/src/samstat'
OUT = HERE / 'native_additional_003'
OUT.mkdir(exist_ok=True)
path = OUT / 'short_errors.sam'
records = []
for base in 'ACGTN':
    other = 'C' if base == 'A' else 'A'
    records.append(f'mismatch_{base}\t0\tref\t1\t30\t4M\t*\t0\t0\t{base * 4}\tIIII\tMD:Z:1{other}2\n')
records.append('insertion\t0\tref\t1\t30\t2M2I2M\t*\t0\t0\tAAAAAA\tIIIIII\tMD:Z:4\n')
records.append('deletion\t0\tref\t1\t30\t2M2D2M\t*\t0\t0\tAAAA\tIIII\tMD:Z:2^GG2\n')
path.write_text('@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:ref\tLN:1000\n' + ''.join(records))
env = os.environ.copy()
env['LD_LIBRARY_PATH'] = str(CONTRACT / 'sources/deps/root/usr/lib/x86_64-linux-gnu')
env['TMPDIR'] = str(OUT)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


command = [str(BINARY), '-t', '1', '-d', str(OUT), str(path)]
start = time.monotonic()
result = subprocess.run(command, cwd=OUT, capture_output=True, preexec_fn=limits, env=env)
(OUT / 'stdout').write_bytes(result.stdout)
(OUT / 'stderr').write_bytes(result.stderr)
artifact = OUT / (path.name + '.samstat.html')
row = {'command': command, 'cwd': str(OUT), 'exit_code': result.returncode, 'elapsed_seconds': time.monotonic() - start,
       'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(),
       'library_path': env['LD_LIBRARY_PATH'], 'tmpdir': env['TMPDIR'], 'html_produced': artifact.exists(),
       'identity': 'source_executed_synthetic'}
if artifact.exists():
    row['html_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    shutil.copyfile(artifact, ROOT / 'verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate/tests/fixtures/bvbrc_fastqutils_samstat_legacy/additional' / artifact.name)
(HERE / 'NATIVE_RUN_RECEIPTS_003.json').write_text(json.dumps(row, indent=2) + '\n')
print(json.dumps(row, indent=2))
