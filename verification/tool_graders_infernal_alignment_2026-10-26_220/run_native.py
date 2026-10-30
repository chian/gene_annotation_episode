"""Small retained native cmalign runs; no timeout or hidden analysis retries."""
from pathlib import Path
import hashlib
import json
import os
import resource
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BIN = ROOT / 'resources/software/infernal-1.1.5-install/bin/cmalign'
TUTORIAL = ROOT / 'resources/software/infernal-1.1.5/tutorial'
MEM = 20 * 1024**3
SCRATCH = 4 * 1024**3

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def limits():
    resource.setrlimit(resource.RLIMIT_AS, (MEM, MEM))
    resource.setrlimit(resource.RLIMIT_FSIZE, (SCRATCH, SCRATCH))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

def main():
    inputs = HERE / 'native/inputs'
    inputs.mkdir(parents=True, exist_ok=True)
    sources = ['tRNA5.c.cm', 'tRNA5.sto', 'Cobalamin.c.cm', 'Cobalamin.fa',
               'orig_files/toalign.1.fa', 'orig_files/toalign.1trunc.fa']
    hashes = {}
    for name in sources:
        src = TUTORIAL / name
        dst = inputs / Path(name).name
        shutil.copyfile(src, dst)
        assert digest(src) == digest(dst)
        hashes[name] = digest(src)
    (inputs / 'combined.fa').write_bytes((inputs / 'toalign.1.fa').read_bytes() + (inputs / 'toalign.1trunc.fa').read_bytes())
    # Explicit synthetic sequence input for native >200-column format stress.
    cobalamin = ''.join(line.strip() for line in (inputs/'Cobalamin.fa').read_text().splitlines() if not line.startswith('>'))
    (inputs/'Cobalamin-insertion-test.fa').write_text('>Cobalamin.synthetic-insertion-test\n'+cobalamin[:61]+'U'*32+cobalamin[61:]+'\n')
    (inputs/'tRNA-name-collision.fa').write_text((inputs/'toalign.1.fa').read_text().replace('>tRNA6', '>tRNA1', 1))
    cases = [
        ('full_trunc', 'tRNA5.c.cm', 'combined.fa', ['--miss', '--ileaved']),
        ('matchonly', 'tRNA5.c.cm', 'combined.fa', ['--miss', '--matchonly']),
        ('noprob', 'tRNA5.c.cm', 'toalign.1.fa', ['--cyk', '--noprob']),
        ('local_end', 'Cobalamin.c.cm', 'Cobalamin.fa', ['--miss']),
        ('local_end_matchonly', 'Cobalamin.c.cm', 'Cobalamin.fa', ['--miss', '--matchonly']),
        ('global', 'tRNA5.c.cm', 'toalign.1.fa', ['-g', '--notrunc']),
        ('mapali', 'tRNA5.c.cm', 'toalign.1.fa', ['--mapali', str(inputs / 'tRNA5.sto')]),
        ('sample_serial', 'tRNA5.c.cm', 'toalign.1.fa', ['--sample', '--seed', '181']),
        ('local_end_interleaved', 'Cobalamin.c.cm', 'Cobalamin.fa', ['--miss', '--ileaved', '--verbose']),
        ('global_nonbanded', 'tRNA5.c.cm', 'toalign.1.fa', ['-g', '--notrunc', '--nonbanded']),
        ('interleaved_stress', 'Cobalamin.c.cm', 'Cobalamin-insertion-test.fa', ['--miss', '--ileaved']),
        ('pfam_stress', 'Cobalamin.c.cm', 'Cobalamin-insertion-test.fa', ['--miss', '--outformat', 'Pfam']),
        ('submodel', 'tRNA5.c.cm', 'toalign.1trunc.fa', ['-g', '--notrunc', '--sub']),
        ('mapali_collision', 'tRNA5.c.cm', 'tRNA-name-collision.fa', ['--mapali', str(inputs/'tRNA5.sto')]),
    ]
    receipts = {'binary': str(BIN), 'binary_sha256': digest(BIN), 'source_input_sha256': hashes,
        'ram_limit_bytes': MEM, 'scratch_limit_bytes': SCRATCH, 'wall_time_limit': None,
        'limits': 'RLIMIT_AS, RLIMIT_FSIZE; aggregate native directory size monitored every 0.02 s', 'runs': []}
    receipt_path = HERE / 'NATIVE_RECEIPTS.json'
    if receipt_path.exists():
        receipts = json.loads(receipt_path.read_text())
    receipts['derived_inputs'] = {'Cobalamin-insertion-test.fa': {
        'source': 'Cobalamin.fa', 'transformation': 'insert 32 U symbols after original position 61; rename explicitly synthetic-insertion-test',
        'kind': 'artificial_sequence_for_native_format_stress_not_biological_measurement',
        'sha256': digest(inputs/'Cobalamin-insertion-test.fa')}}
    receipts['derived_inputs']['tRNA-name-collision.fa'] = {'source':'orig_files/toalign.1.fa',
        'transformation':'rename tRNA6 to tRNA1 to collide with one inherited training-row name; sequence unchanged',
        'kind':'identifier_collision_format_test', 'sha256':digest(inputs/'tRNA-name-collision.fa')}
    for name, model, fasta, extra in cases:
        if any(r['case'] == name for r in receipts['runs']):
            continue
        directory = HERE / 'native' / name
        directory.mkdir(exist_ok=True)
        tmp = directory / 'tmp'
        tmp.mkdir(exist_ok=True)
        argv = [str(BIN), '--cpu', '0' if '--sample' in extra else '1', '--mxsize', '256', '-o', 'alignment.sto',
                '--sfile', 'scores.txt', '--ifile', 'inserts.txt']
        if '-g' not in extra:
            argv += ['--elfile', 'local_ends.txt']
        argv += extra + [str(inputs / model), str(inputs / fasta)]
        start = time.monotonic()
        peak_scratch = 0
        with (directory / 'stdout.txt').open('w') as out, (directory / 'stderr.txt').open('w') as err:
            proc = subprocess.Popen(argv, cwd=directory, env={**os.environ, 'TMPDIR': str(tmp)},
                stdout=out, stderr=err, preexec_fn=limits)
            while proc.poll() is None:
                size = sum(p.stat().st_size for p in (HERE / 'native').rglob('*') if p.is_file())
                peak_scratch = max(peak_scratch, size)
                if size > SCRATCH:
                    proc.kill()
                    raise RuntimeError('aggregate scratch limit exceeded')
                time.sleep(.02)
        receipts['runs'].append({'case': name, 'argv': argv, 'cwd': str(directory),
            'returncode': proc.returncode, 'elapsed_seconds': time.monotonic()-start,
            'observed_directory_bytes': peak_scratch,
            'files': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in directory.iterdir() if p.is_file()}})
        (HERE / 'NATIVE_RECEIPTS.json').write_text(json.dumps(receipts, indent=2) + '\n')
        if proc.returncode:
            raise RuntimeError(f'{name}: native exit {proc.returncode}')
    assert digest(BIN) == receipts['binary_sha256']
    for name in sources:
        assert digest(TUTORIAL / name) == hashes[name]
    receipts['observed_child_maxrss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    receipt_path.write_text(json.dumps(receipts, indent=2) + '\n')
    print(json.dumps({'successful_cases': sum(r['returncode'] == 0 for r in receipts['runs']),
        'retained_failed_cases': sum(r['returncode'] != 0 for r in receipts['runs']),
        'maxrss_kib': receipts['observed_child_maxrss_kib']}))

if __name__ == '__main__':
    main()
