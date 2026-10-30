"""Retain actual Cutadapt and Trim Galore output from declared synthetic reads."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'native_examples_001'
OUT.mkdir(exist_ok=False)
ENV = HERE / 'native_environment_001'
assert json.loads((ENV / 'receipt.json').read_text())['passed']
CUTADAPT = ENV / 'venv/bin/cutadapt'
TRIM = ROOT / 'verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/sources/TrimGalore/trim_galore'
ADAPTER = 'AGATCGGAAGAGC'
READS = [('adapter-long', 'ACGTACGT' + ADAPTER, 'I' * 21),
    ('unchanged', 'GGCCGGCC', 'I' * 8),
    ('adapter-short', 'TTTT' + ADAPTER, 'I' * 17),
    ('quality-tail', 'CCCCGGGGTTTT', 'I' * 8 + '!' * 4)]
RAW = ''.join('@' + name + '\n' + sequence + '\n+\n' + quality + '\n'
    for name, sequence, quality in READS).encode()
assert all(len(sequence) == len(quality) for _, sequence, quality in READS)
assert sum(len(sequence) for _, sequence, _ in READS) == 58


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
environment.pop('PYTHONPATH', None)
specimens = [
    ('cutadapt_single', ['-a', ADAPTER, '-q', '20'], False, False),
    ('cutadapt_filtered', ['-a', ADAPTER, '-q', '20', '-m', '6'], False, False),
    ('cutadapt_empty', ['-a', ADAPTER, '-q', '20'], False, True),
    ('cutadapt_paired', ['-a', ADAPTER, '-A', ADAPTER, '-q', '20'], True, False),
    ('trimgalore_single', [], False, False),
]
receipts = []
for name, options, paired, empty in specimens:
    directory = OUT / name
    directory.mkdir()
    input_path = directory / 'synthetic.fastq'
    input_path.write_bytes(b'' if empty else RAW)
    if name == 'trimgalore_single':
        command = ['perl', str(TRIM), '--path_to_cutadapt', str(CUTADAPT),
            '--adapter', ADAPTER, '--quality', '20', '--length', '6', '--dont_gzip',
            '--output_dir', str(directory), str(input_path)]
    else:
        command = [str(CUTADAPT), '-j', '1', *options, '--json', str(directory / 'native.json'),
            '-o', str(directory / 'output.fastq')]
        if paired:
            (directory / 'synthetic2.fastq').write_bytes(RAW)
            command += ['-p', str(directory / 'output2.fastq'), str(input_path), str(directory / 'synthetic2.fastq')]
        else:
            command += [str(input_path)]
    receipt = {'case': name, 'argv': command, 'cwd': str(directory),
        'started_at': datetime.now(timezone.utc).isoformat(), 'input_sha256': sha(input_path),
        'synthetic_input': True, 'native_executable_run': True, 'BV_BRC_service_run': False,
        'no_wall_time_limit': True}
    clock = time.monotonic()
    with (directory / 'stdout.log').open('x') as stdout, (directory / 'stderr.log').open('x') as stderr:
        result = subprocess.run(command, cwd=directory, env=environment, stdout=stdout, stderr=stderr, preexec_fn=limits)
    receipt.update(exit_code=result.returncode, ended_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=time.monotonic() - clock,
        files={str(path.relative_to(directory)): {'sha256': sha(path), 'byte_count': path.stat().st_size}
            for path in directory.iterdir() if path.is_file()})
    if (directory / 'native.json').is_file():
        native = json.loads((directory / 'native.json').read_text())
        receipt['native_summary'] = {key: native[key] for key in ('cutadapt_version', 'schema_version',
            'read_counts', 'basepair_counts')}
    with (directory / 'receipt.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    receipts.append(receipt)
summary = {'cases': receipts, 'all_exit_zero': all(row['exit_code'] == 0 for row in receipts),
    'trimgalore_source_sha256': sha(TRIM), 'environment_receipt_sha256': sha(ENV / 'receipt.json'),
    'scratch_bytes': sum(path.stat().st_size for path in OUT.rglob('*') if path.is_file()),
    'scope': 'Producer-output examination only; no new parser, calculator, application or live BV-BRC claim.'}
with (OUT / 'receipt.json').open('x') as stream:
    json.dump(summary, stream, indent=2)
print(json.dumps({'all_exit_zero': summary['all_exit_zero'],
    'cases': [{'name': r['case'], 'exit_code': r['exit_code'], 'native_summary': r.get('native_summary')} for r in receipts]}))
raise SystemExit(0 if summary['all_exit_zero'] else 1)
