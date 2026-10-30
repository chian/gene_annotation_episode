"""Selected tiny native-format examples; not a production execution adapter."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
OLD = ROOT / 'verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native'
BIN = ROOT / 'resources/software/infernal-1.1.5-install/bin'
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(case, arguments, inputs):
    directory = BASE / 'native' / case
    directory.mkdir(parents=True, exist_ok=False)
    descriptors = []
    for name, content in inputs.items():
        (directory / name).write_bytes(content)
        descriptors.append({'path': name, 'sha256': digest(directory/name), 'size_bytes': len(content)})
    command = [str(BIN/arguments[0]), *arguments[1:]]
    request = {'command': command, 'policy': POLICY.to_dict(), 'inputs': descriptors,
               'binary_sha256': digest(BIN/arguments[0]), 'started_at': datetime.now(timezone.utc).isoformat()}
    (directory/'request.json').write_text(json.dumps(request, indent=2)+'\n')
    result = run_local_job(command, cwd=directory, policy=POLICY,
        stdout_path=directory/'stdout.txt', stderr_path=directory/'stderr.txt',
        env={'XDG_CACHE_HOME': str(directory/'cache'), 'OMP_NUM_THREADS': '1',
             'INFERNAL_NCPU': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    receipt = {**request, 'returncode': result.returncode, 'metadata': result.metadata,
               'finished_at': datetime.now(timezone.utc).isoformat(),
               'files': [{'path': str(p.relative_to(directory)), 'sha256': digest(p),
                          'size_bytes': p.stat().st_size} for p in sorted(directory.rglob('*')) if p.is_file()]}
    (directory/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(case, result.returncode, flush=True)


if __name__ == '__main__':
    seed = (OLD/'cmbuild_hand/seed.sto').read_bytes()
    run('cmbuild_refine', ['cmbuild', '--refine', 'refined.sto', '-O', 'processed.sto', 'built.cm', 'seed.sto'], {'seed.sto': seed})
    model = (OLD/'cmcalibrate_tiny/model.cm').read_bytes()
    run('cmstat_hmm_P', ['cmstat', '--hmmonly', '-P', '0.01', 'model.cm'], {'model.cm': model})
    second = model.replace(b'NAME     fixture246\n', b'NAME     second249\n').replace(b'NAME  fixture246\n', b'NAME  second249\n').replace(b'ACC      TEST246\n', b'ACC      SECOND249\n').replace(b'ACC   TEST246\n', b'ACC   SECOND249\n')
    run('cmstat_key', ['cmstat', '--key', 'SECOND249', '-E', '0.01', 'model.cm'], {'model.cm': model+second})
    for kind in ('GA', 'NC', 'TC'):
        tagged = model.replace(b'CM\n', (kind+'       10.00\nCM\n').encode(), 1)
        run('cmstat_'+kind+'_present', ['cmstat', '--cut_'+kind.lower(), 'model.cm'], {'model.cm': tagged})
