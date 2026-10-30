"""One-off format study; this is not a production adapter or a test suite."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
BIN = ROOT / 'resources/software/infernal-1.1.5-install/bin'
TUTORIAL = ROOT / 'resources/software/infernal-1.1.5/tutorial'
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def run(name, argv, inputs=(), text_inputs=None):
    directory = BASE / 'native' / name
    directory.mkdir(parents=True, exist_ok=False)
    descriptors = []
    for source, destination in inputs:
        shutil.copyfile(source, directory / destination)
        descriptors.append({'source': str(source), 'path': destination,
                            'sha256': sha(source), 'size_bytes': source.stat().st_size})
    for filename, content in (text_inputs or {}).items():
        (directory / filename).write_text(content)
        descriptors.append({'source': 'synthetic_format_fixture', 'path': filename,
                            'sha256': sha(directory / filename),
                            'size_bytes': (directory / filename).stat().st_size})
    (directory / 'cache').mkdir()
    command = [str(BIN / argv[0]), *argv[1:]]
    request = {'command': command, 'policy': POLICY.to_dict(), 'cwd': str(directory),
               'binary_sha256': sha(BIN / argv[0]), 'inputs': descriptors,
               'started_at': datetime.now(timezone.utc).isoformat()}
    write(directory / 'request.json', request)
    result = run_local_job(command, cwd=directory, policy=POLICY,
        stdout_path=directory / 'stdout.txt', stderr_path=directory / 'stderr.txt',
        env={'XDG_CACHE_HOME': str(directory / 'cache'), 'OMP_NUM_THREADS': '1',
             'INFERNAL_NCPU': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    write(directory / 'receipt.json', {**request, 'returncode': result.returncode,
        'metadata': result.metadata, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'files': [{'path': str(p.relative_to(directory)), 'size_bytes': p.stat().st_size,
                   'sha256': sha(p)} for p in sorted(directory.rglob('*')) if p.is_file()]})
    print(name, result.returncode, flush=True)
    return directory


if __name__ == '__main__':
    for tool in ('cmbuild', 'cmcalibrate', 'cmconvert', 'cmemit', 'cmfetch', 'cmpress', 'cmstat'):
        run('help_' + tool, [tool, '-h'])
    seed = '# STOCKHOLM 1.0\n#=GF ID fixture246\n#=GF AC TEST246\ns1 GCGCAAAAGCGC\ns2 GCGCUAAAGCGC\ns3 GCGCAUAAGCGC\n#=GC SS_cons <<<<....>>>>\n#=GC RF xxxxxxxxxxxx\n//\n'
    built = run('cmbuild_hand', ['cmbuild', '--hand', '-O', 'post.sto', 'built.cm', 'seed.sto'], text_inputs={'seed.sto': seed})
    run('cmbuild_default', ['cmbuild', 'built.cm', 'seed.sto'], text_inputs={'seed.sto': seed})
    noss = run('cmbuild_noss', ['cmbuild', '--noss', 'built.cm', 'seed.sto'], text_inputs={'seed.sto': seed})
    model = built / 'built.cm'
    calibrated = run('cmcalibrate_tiny', ['cmcalibrate', '--cpu', '1', '-L', '0.01', '--tailp', '0.1', '--seed', '181', '--noforecast', '--hfile', 'hist.dat', '--sfile', 'survival.dat', '--qqfile', 'qq.dat', '--ffile', 'fits.dat', '--xfile', 'tail.dat', 'model.cm'], [(model, 'model.cm'), (model, 'original.cm')])
    run('cmcalibrate_memreq', ['cmcalibrate', '--memreq', '-L', '0.01', 'model.cm'], [(model, 'model.cm')])
    run('cmcalibrate_split', ['cmcalibrate', '--split', '--ptot', '2', '--cfile', 'commands.txt', '--proot', 'part', '-L', '0.02', '--tailp', '0.1', 'model.cm'], [(model, 'model.cm')])
    native_model = calibrated / 'model.cm'
    for label, flags in [('ascii', ['-a']), ('binary', ['-b']), ('legacy', ['-1']), ('filter_hmm', ['--fhmm']), ('ml_hmm', ['--mlhmm'])]:
        run('cmconvert_' + label, ['cmconvert', *flags, '-o', 'converted.out', 'model.cm'], [(native_model, 'model.cm')])
    for label, flags in [('fasta', ['-u', '-N', '2']), ('stockholm', ['-a', '-N', '2']), ('consensus', ['-c']), ('embedded', ['-u', '-N', '2', '-e', '40', '--iid', '--u5p']), ('hmm', ['-a', '-N', '2', '--hmmonly'])]:
        run('cmemit_' + label, ['cmemit', *flags, '--seed', '181', '-o', 'emitted.out', 'model.cm'], [(native_model, 'model.cm')])
    models = (TUTORIAL / 'tRNA5.c.cm').read_bytes() + (TUTORIAL / 'tRNA5-hand.c.cm').read_bytes()
    source = BASE / 'two_models.cm'
    source.write_bytes(models)
    indexed = run('cmfetch_index', ['cmfetch', '--index', 'models.cm'], [(source, 'models.cm')])
    run('cmfetch_single', ['cmfetch', '-o', 'fetched.cm', 'models.cm', 'tRNA5'], [(source, 'models.cm')])
    keys = 'tRNA5-hand\ntRNA5\n'
    run('cmfetch_multiple_unindexed', ['cmfetch', '-f', '-o', 'fetched.cm', 'models.cm', 'keys.txt'], [(source, 'models.cm')], {'keys.txt': keys})
    run('cmfetch_multiple_indexed', ['cmfetch', '-f', '-o', 'fetched.cm', 'models.cm', 'keys.txt'], [(source, 'models.cm'), (indexed / 'models.cm.ssi', 'models.cm.ssi')], {'keys.txt': keys})
    run('cmfetch_missing_unindexed', ['cmfetch', '-f', '-o', 'fetched.cm', 'models.cm', 'keys.txt'], [(source, 'models.cm')], {'keys.txt': 'absent_key\ntRNA5\n'})
    run('cmpress_uncalibrated', ['cmpress', 'model.cm'], [(model, 'model.cm')])
    for label, flags in [('summary', []), ('E', ['-E', '0.01']), ('P', ['-P', '0.01']), ('T', ['-T', '10']), ('GA', ['--cut_ga']), ('NC', ['--cut_nc']), ('TC', ['--cut_tc']), ('hmm_E', ['--hmmonly', '-E', '0.01']), ('hmm_T', ['--hmmonly', '-T', '10'])]:
        run('cmstat_' + label, ['cmstat', *flags, 'model.cm'], [(native_model, 'model.cm')])
    run('cmstat_noss_summary', ['cmstat', 'model.cm'], [(noss / 'built.cm', 'model.cm')])
    write(BASE / 'NATIVE_RUN_INDEX.json', [{'directory': str(p.parent.relative_to(BASE)), **json.loads(p.read_text())} for p in sorted((BASE / 'native').glob('*/receipt.json'))])
