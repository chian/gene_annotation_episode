"""Bounded tiny Infernal verification, retaining complete native artifacts."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil
import os

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
SOURCE = ROOT / 'resources/software/infernal-1.1.5/tutorial'
BIN = ROOT / 'resources/software/infernal-1.1.5-install/bin'
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, argv, inputs):
    folder = BASE / 'native' / name
    folder.mkdir(parents=True, exist_ok=True)
    input_receipts = []
    for src, target in inputs:
        shutil.copyfile(src, folder / target)
        input_receipts.append({'source': str(src), 'destination': target, 'sha256': digest(src)})
    tmp = folder / 'tmp'
    tmp.mkdir(exist_ok=True)
    executable = BIN / argv[0]
    command = [str(executable), *argv[1:]]
    receipt = {'command': command, 'cwd': str(folder), 'binary_sha256': digest(executable),
               'inputs': input_receipts, 'started_utc': datetime.now(timezone.utc).isoformat(),
               'policy': POLICY.to_dict()}
    (folder / 'request.json').write_text(json.dumps(receipt, indent=2) + '\n')
    result = run_local_job(command, cwd=folder, policy=POLICY,
                           stdout_path=folder / 'stdout.txt', stderr_path=folder / 'stderr.txt',
                           env={**os.environ, 'TMPDIR': str(tmp), 'OMP_NUM_THREADS': '1'})
    receipt.update(returncode=result.returncode, metadata=result.metadata,
                   finished_utc=datetime.now(timezone.utc).isoformat(),
                   files=[{'path': str(p.relative_to(folder)), 'bytes': p.stat().st_size, 'sha256': digest(p)}
                          for p in sorted(folder.rglob('*')) if p.is_file()])
    (folder / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(name, 'exit', result.returncode, flush=True)
    if result.returncode:
        raise RuntimeError((folder / 'stderr.txt').read_text())
    return folder


if __name__ == '__main__':
    staged = BASE / 'inputs'
    staged.mkdir(exist_ok=True)
    for name in ('tRNA5.c.cm', 'tRNA5-hand.c.cm', 'mrum-tRNAs10.fa'):
        shutil.copyfile(SOURCE / name, staged / name)
    models = staged / 'two_models.cm'
    models.write_bytes((staged / 'tRNA5.c.cm').read_bytes() + (staged / 'tRNA5-hand.c.cm').read_bytes())
    fasta = (staged / 'mrum-tRNAs10.fa').read_text()
    entries = [(block.splitlines()[0], ''.join(block.splitlines()[1:])) for block in fasta.split('>')[1:]]
    seq = entries[0][1]
    reverse = seq.translate(str.maketrans('ACGUT', 'UGCAA'))[::-1]
    targets = staged / 'tiny.fa'
    targets.write_text(f'>native_forward\n{seq}\n>native_reverse\n{reverse}\n'
                       f'>native_repeat\n{seq + "A" * 50 + seq}\n>native_second\n{entries[1][1]}\n')
    (staged / 'no_hits.fa').write_text('>no_match\n' + 'A' * 160 + '\n')
    prepared = run('cmpress', ['cmpress', 'two_models.cm'], [(models, 'two_models.cm')])
    pressed = [(p, p.name) for p in prepared.glob('two_models.cm*')]
    for fmt in (1, 3):
        run(f'cmsearch_fmt{fmt}', ['cmsearch', '--cpu', '1', '--fmt', str(fmt), '--tblout', 'hits.tbl',
            '--notextw', '--verbose', '-E', '10', '--incE', '1e-30', 'two_models.cm', 'tiny.fa'],
            [(models, 'two_models.cm'), (targets, 'tiny.fa')])
    for fmt in (1, 2, 3):
        run(f'cmscan_fmt{fmt}', ['cmscan', '--cpu', '1', '--fmt', str(fmt), '--tblout', 'hits.tbl',
            '--notextw', '--verbose', '-E', '10', '--incE', '1e-30', 'two_models.cm', 'tiny.fa'],
            [*pressed, (targets, 'tiny.fa')])
    run('cmsearch_no_hits', ['cmsearch', '--cpu', '1', '--fmt', '3', '--tblout', 'hits.tbl',
        'two_models.cm', 'no_hits.fa'], [(models, 'two_models.cm'), (staged / 'no_hits.fa', 'no_hits.fa')])
    run('cmscan_no_hits', ['cmscan', '--cpu', '1', '--fmt', '2', '--tblout', 'hits.tbl',
        'two_models.cm', 'no_hits.fa'], [*pressed, (staged / 'no_hits.fa', 'no_hits.fa')])
