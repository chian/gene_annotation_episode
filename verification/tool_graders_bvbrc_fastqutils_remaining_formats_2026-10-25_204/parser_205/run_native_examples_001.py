"""Retain small, actual Cutadapt 4.9 producer runs from explicit synthetic inputs.

Evidence generation only. This is neither a parser nor a production operation.
No wall-time limit is supplied. Existing receipts are never overwritten.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
EXE = WORK / 'native_environment_001/venv/bin/cutadapt'
OUT = ROOT / 'native_examples_001'
CASES = {
    'front': (['-g', 'front=ACGTAC', '-e', '0.2'], ['ACGTACGGGG', 'TTACGTACCCCC', 'CCCCCC'], None),
    'anchored_front': (['-g', '^ACGTAC', '-e', '0.2'], ['ACGTACGGGG', 'ACGTATGGGG', 'CCCCCC'], None),
    'anchored_back': (['-a', 'AGATCG$'], ['CCCCAGATCG', 'TTTTAGATCG', 'CCCCCC'], None),
    'anywhere': (['-b', 'any=ACGTAC'], ['ACGTACGGGG', 'TTACGTACCCCC', 'CCCCACGTAC', 'CCCCCC'], None),
    'linked': (['-a', 'link=ACGTAC...AGATCG'], ['ACGTACGGGGAGATCG', 'ACGTACCCCC', 'CCCCCC'], None),
    'linked_unanchored': (['-g', 'link=ACGTAC...AGATCG'], ['TTACGTACGGGGAGATCG', 'ACGTACCCCCAGATCG', 'CCCCCC'], None),
    'repeated': (['-g', 'repeat=ACGTAC', '-n', '3'], ['ACGTACACGTACACGTACGGGG', 'ACGTACACGTACCCCC'], None),
    'repeated_names': (['-a', 'same=AGATCG', '-a', 'same=GATTAC'], ['CCCCAGATCG', 'CCCCGATTAC', 'CCCCCC'], None),
    'no_matches': (['-a', 'AGATCG'], ['CCCCCCCC', 'GGGGGGGG'], None),
    'poly_a': (['--poly-a'], ['CCCCCAAAAAAAA', 'GCGCAAAAA', 'ACGT'], None),
    'paired_poly_a': (['--poly-a', '-q', '20'], ['CCCCCAAAAAAAA', 'GCGCAAAAA', 'ACGT'], ['TTTTTTTTCCCC', 'TTTTTGCGC', 'ACGT']),
    'reverse_complemented': (['-a', 'AGATCG', '--revcomp'], ['CCCCAGATCG', 'CGATCTGGGG', 'GGGG'], None),
    'filters': (['-a', 'AGATCG', '-m', '5', '-M', '12', '--max-n', '0', '--max-ee', '0.1'], ['ACGT', 'ACGTACGTACGTACGT', 'ACGTNNNN', 'ACGTAC', 'CCCCAGATCG'], None),
    'discard_trimmed': (['-a', 'AGATCG', '--discard-trimmed'], ['CCCCAGATCG', 'GGGGGG'], None),
    'discard_untrimmed': (['-a', 'AGATCG', '--discard-untrimmed'], ['CCCCAGATCG', 'GGGGGG'], None),
    'indel': (['-a', 'AGATCGGAAGAGC', '-e', '0.2', '-O', '3'], ['TTTTAGATCGGAAAGAGC', 'TTTTAGATCGAAGAGC', 'TTTTAGATCGGAAGAGC'], None),
}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))


def fastq(path, seqs):
    path.write_text(''.join(f'@synthetic_{i}\n{s}\n+\n{"I" * len(s)}\n' for i, s in enumerate(seqs)))


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    all_receipts = []
    for name, (options, left, right) in CASES.items():
        directory = OUT / name
        directory.mkdir()
        fastq(directory / 'input.fastq', left)
        argv = [str(EXE), '-j', '1', *options, '--json', str(directory / 'native.json'), '-o', str(directory / 'output.fastq')]
        if right is not None:
            fastq(directory / 'input2.fastq', right)
            argv += ['-p', str(directory / 'output2.fastq')]
        argv += [str(directory / 'input.fastq')]
        if right is not None:
            argv += [str(directory / 'input2.fastq')]
        started = datetime.now(timezone.utc).isoformat()
        tick = time.monotonic()
        env = dict(os.environ, TMPDIR=str(directory), PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run(argv, cwd=directory, env=env, capture_output=True, preexec_fn=limits)
        (directory / 'stdout.log').write_bytes(result.stdout)
        (directory / 'stderr.log').write_bytes(result.stderr)
        receipt = dict(case=name, argv=argv, cwd=str(directory), started_at=started,
                       ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - tick,
                       exit_code=result.returncode, synthetic_input=True, native_executable_run=True,
                       BV_BRC_service_run=False, no_wall_time_limit=True, address_space_limit_bytes=20*1024**3,
                       scratch_budget_bytes=4*1024**3, files={})
        for path in sorted(directory.iterdir()):
            if path.is_file():
                raw = path.read_bytes()
                receipt['files'][path.name] = dict(sha256=sha256(raw).hexdigest(), byte_count=len(raw))
        (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        all_receipts.append(receipt)
        print(name, 'exit', result.returncode)
    retained_bytes = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    assert retained_bytes < 4 * 1024**3
    (OUT / 'receipt.json').write_text(json.dumps(dict(cases=all_receipts, retained_bytes=retained_bytes,
        all_exit_zero=all(r['exit_code'] == 0 for r in all_receipts)), indent=2) + '\n')


if __name__ == '__main__':
    main()
