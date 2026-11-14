"""Install the pinned small A102 native toolchain beneath a chosen runs/ dir."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import urllib.request

from .local_jobs import LocalJobPolicy,run_local_job


USALIGN_COMMIT='23f14ffcf8647f2dc1c0e01043db3a7f3a661c28'
PINS={
    'US-align':{'version':'20261019','commit':USALIGN_COMMIT,
        'url':'https://codeload.github.com/pylelab/USalign/tar.gz/'+USALIGN_COMMIT,
        'archive_sha256':'2d485ac1e10ce04ce78372d4c7ea9b59567cffe3fa0463882b17bd71e9f79765'},
    'Foldseek':{'version':'941cd33ff0771cd2e3f144e3293e22a2b87e9fda','release':'10-941cd33',
        'url':'https://github.com/steineggerlab/foldseek/releases/download/10-941cd33/foldseek-linux-avx2.tar.gz',
        'archive_sha256':'e6a3e3860e76b0b7b858736f627fe680d4d7f0fc7298301d8a92b9f711d74ac7'},
}


def install(run_directory):
    run=Path(run_directory).resolve()
    if 'runs' not in run.parts:raise ValueError('a102_native_installation_requires_runs_directory')
    for name in ('software','downloads','tmp','cache'):(run/name).mkdir(parents=True,exist_ok=True)
    os.environ.update(TMPDIR=str(run/'tmp'),XDG_CACHE_HOME=str(run/'cache'),PYTHONDONTWRITEBYTECODE='1')
    if 'avx2' not in Path('/proc/cpuinfo').read_text():raise ValueError('a102_pinned_foldseek_requires_avx2')
    for name,pin in PINS.items():
        archive=run/'downloads'/('usalign.tar.gz' if name=='US-align' else 'foldseek.tar.gz')
        if not archive.exists():urllib.request.urlretrieve(pin['url'],archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=pin['archive_sha256']:
            raise ValueError('a102_dependency_archive_hash_conflict:'+name)
        with tarfile.open(archive) as source:source.extractall(run/'software',filter='data')
    compiler=shutil.which('g++')
    if not compiler:raise ValueError('a102_usalign_requires_cpp_compiler')
    source=run/'software'/('USalign-'+USALIGN_COMMIT)
    binary=source/'USalign'
    if not binary.exists():
        result=run_local_job([compiler,'-O3','-o',str(binary),'USalign.cpp'],cwd=source,
            policy=LocalJobPolicy(2 * 1024 ** 3, 1024 ** 3),cpu_threads=1)
        if result.returncode:raise ValueError('a102_usalign_compilation_failed')
    binaries={'US-align':binary,'Foldseek':run/'software/foldseek/bin/foldseek'}
    lock={name:{**PINS[name],'executable':str(path),
        'executable_sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in binaries.items()}
    (run/'native-toolchain.json').write_text(json.dumps(lock,indent=2)+'\n')
    return lock


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory',required=True)
    print(json.dumps(install(parser.parse_args().run_directory),indent=2))


if __name__=='__main__':main()
