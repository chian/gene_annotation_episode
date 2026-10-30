"""Tiny source-executed synthetic2.2.3 cases; not a BV-BRC service run."""
import hashlib
import json
from pathlib import Path
import resource
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT = ROOT / 'verification/tool_graders_fastqutils_samstat_contract_2026-10-25_207'
BINARY = CONTRACT / 'sources/build_2_2_3/src/samstat'
OUT = HERE / 'native_additional_001'
OUT.mkdir(exist_ok=True)
shutil.copyfile(CONTRACT / 'native_examples_001/inputs/missing_quality.sam', OUT / 'missing_quality.sam')
header = '@HD\tVN:1.6\tSO:unsorted\n@SQ\tSN:ref\tLN:1000\n'
records = []
for base in 'ACGTN':
    other = 'C' if base == 'A' else 'A'
    records.append(f'mismatch_{base}\t0\tref\t1\t30\t300M\t*\t0\t0\t{base * 300}\t{"I" * 300}\tMD:Z:250{other}49\n')
records.append(f'insertion\t0\tref\t1\t30\t250M2I50M\t*\t0\t0\t{"A" * 302}\t{"I" * 302}\tMD:Z:300\n')
records.append(f'deletion\t0\tref\t1\t30\t250M2D50M\t*\t0\t0\t{"A" * 300}\t{"I" * 300}\tMD:Z:250^GG50\n')
(OUT / 'clustered_errors.sam').write_text(header + ''.join(records))


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


rows = []
for filename, options in [('missing_quality.sam', ['--norm', '--plotend']), ('clustered_errors.sam', [])]:
    command = [str(BINARY), '-t', '1', *options, '-d', str(OUT), str(OUT / filename)]
    start = time.monotonic()
    result = subprocess.run(command, cwd=OUT, capture_output=True, preexec_fn=limits)
    (OUT / (filename + '.stdout')).write_bytes(result.stdout)
    (OUT / (filename + '.stderr')).write_bytes(result.stderr)
    row = {'command': command, 'cwd': str(OUT), 'exit_code': result.returncode,
           'elapsed_seconds': time.monotonic() - start, 'binary_sha256': hashlib.sha256(BINARY.read_bytes()).hexdigest(),
           'input_sha256': hashlib.sha256((OUT / filename).read_bytes()).hexdigest(), 'identity': 'source_executed_synthetic'}
    artifact = OUT / (filename + '.samstat.html')
    row['html_produced'] = artifact.exists()
    if artifact.exists():
        row['html_sha256'] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        target = ROOT / 'verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate/tests/fixtures/bvbrc_fastqutils_samstat_legacy/additional'
        target.mkdir(exist_ok=True)
        shutil.copyfile(artifact, target / artifact.name)
    rows.append(row)
(HERE / 'NATIVE_RUN_RECEIPTS_001.json').write_text(json.dumps(rows, indent=2) + '\n')
print(json.dumps(rows, indent=2))
