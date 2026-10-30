"""Additional small, explicitly selected format observations after work 001."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
BIN = ROOT / 'resources/software/infernal-1.1.5-install/bin'
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, args, inputs):
    directory = BASE / 'native' / name
    directory.mkdir(parents=True, exist_ok=False)
    (directory / 'cache').mkdir()
    for source, destination in inputs:
        shutil.copyfile(source, directory / destination)
    environment = {'XDG_CACHE_HOME': str(directory / 'cache'), 'OMP_NUM_THREADS': '1',
                   'PYTHONDONTWRITEBYTECODE': '1'}
    request = {'command': [str(BIN / 'cmcalibrate'), *args], 'environment': environment,
        'policy': POLICY.to_dict(), 'cwd': str(directory),
        'binary_sha256': sha(BIN / 'cmcalibrate'),
        'inputs': [{'source': str(p), 'path': n, 'sha256': sha(p)} for p, n in inputs],
        'started_at': datetime.now(timezone.utc).isoformat()}
    (directory / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    result = run_local_job(request['command'], cwd=directory, policy=POLICY,
        stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt', env=environment)
    receipt = {**request, 'returncode': result.returncode, 'metadata': result.metadata,
        'finished_at': datetime.now(timezone.utc).isoformat(), 'files': [
            {'path': str(p.relative_to(directory)), 'size_bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(directory.rglob('*')) if p.is_file()]}
    (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(name, result.returncode, flush=True)
    return directory


if __name__ == '__main__':
    model = BASE / 'native/cmbuild_hand/built.cm'
    run('cmcalibrate_memreq_without_cpu_env', ['--memreq', '-L', '0.01', 'model.cm'], [(model, 'model.cm')])
    run('cmcalibrate_forecast', ['--forecast', '--nforecast', '1', '-L', '0.01', 'model.cm'], [(model, 'model.cm')])
    partitions = []
    for p in (1, 2):
        folder = run('cmcalibrate_partition_' + str(p), ['--part', str(p), '--ptot', '2', '--pfile', 'scores.dat', '--cpu', '1', '--noforecast', '-L', '0.02', '--tailp', '0.1', '--seed', '181', 'model.cm'], [(model, 'model.cm')])
        partitions.append((folder / 'scores.dat', 'part.' + str(p)))
    run('cmcalibrate_merge', ['--merge', '--ptot', '2', '--proot', 'part', '-L', '0.02', '--tailp', '0.1', 'model.cm'], [(model, 'model.cm'), (model, 'original.cm'), *partitions])
