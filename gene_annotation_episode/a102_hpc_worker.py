"""Portable runner for the existing A102 native algorithms inside an allocation.

The staged package is a hash-pinned snapshot of the existing implementation.
Preparation acquires official assets only. Compilation and structural algorithms
run in the original HPC unit; this module is never a local execution fallback.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import time
from urllib.request import urlopen
import zlib


VERSION = 'a102_shared_hpc_native_v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def prepare_assets(request, directory):
    """Download/verify/extract pinned software, without executing a program."""
    directory.mkdir(parents=True, exist_ok=True)
    pin = request['software_pin']
    archive = directory/'program.tar.gz'
    if not archive.exists():
        with urlopen(pin['url']) as source, archive.open('wb') as target:
            while chunk := source.read(1024*1024):
                target.write(chunk)
    require(sha(archive.read_bytes()) == pin['archive_sha256'], 'a102_hpc_software_archive_conflict')
    with tarfile.open(archive) as source:
        source.extractall(directory, filter='data')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    request_path = Path(argv[0]).resolve()
    request_raw = request_path.read_bytes()
    request = json.loads(request_raw)
    require(request['version'] == VERSION, 'a102_hpc_native_request_version')
    root = request_path.parent
    software_dir = root/'a102-software'
    if len(argv) == 2 and argv[1] == '--prepare-assets':
        prepare_assets(request, software_dir)
        return 0
    unit = Path(os.environ['HPC_UNIT_DIRECTORY']).resolve()
    unit.mkdir(parents=True, exist_ok=True)
    result = {'version': VERSION, 'program': 'a102_structural_native',
        'request_sha256': sha(request_raw), 'worker_sha256': sha(Path(__file__).read_bytes()),
        'code_manifest_sha256': request['code_manifest_sha256'],
        'pbs_job_id': os.environ.get('PBS_JOBID'), 'compute_hostname': socket.gethostname(),
        'python_version': sys.version,
        'completed': False, 'returncode': 1, 'failure': None}
    started = time.time()
    try:
        require(result['pbs_job_id'] and not result['compute_hostname'].startswith(('aurora-uan', 'login')),
            'a102_native_execution_requires_original_compute_allocation')
        snapshot_raw = (root/'a102-sources.json').read_bytes()
        require(sha(snapshot_raw) == request['source_snapshot_sha256'], 'a102_hpc_source_snapshot_conflict')
        sources = json.loads(snapshot_raw)
        require(set(sources) == set(request['code_manifest'])-{'a102-worker.py'},
            'a102_hpc_source_snapshot_membership_conflict')
        package = unit/'source-snapshot'
        package.mkdir(exist_ok=True)
        for relative, expected in request['code_manifest'].items():
            if relative == 'a102-worker.py':
                require(sha(Path(__file__).read_bytes()) == expected, 'a102_hpc_staged_worker_conflict')
                continue
            data = sources[relative].encode()
            require(sha(data) == expected, 'a102_hpc_staged_implementation_conflict')
            path = (package/relative).resolve()
            require(path.is_relative_to(package), 'a102_hpc_snapshot_path_invalid')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        require(sha(canonical(request['code_manifest']).encode()) == request['code_manifest_sha256'],
            'a102_hpc_code_manifest_conflict')
        for name in ('tmp', 'cache'):
            (unit/name).mkdir(exist_ok=True)
        os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(unit/'tmp'),
            XDG_CACHE_HOME=str(unit/'cache'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        sys.path.insert(0, str(package))
        from gene_annotation_episode.a102_native_worker import usalign, foldseek
        pin = request['software_pin']
        require(sha((software_dir/'program.tar.gz').read_bytes()) == pin['archive_sha256'],
            'a102_hpc_prepared_software_required')
        verified = unit/'software'
        verified.mkdir(exist_ok=True)
        with tarfile.open(software_dir/'program.tar.gz') as source:
            source.extractall(verified, filter='data')
        if request['algorithm'] == 'US-align':
            source = verified/('USalign-'+pin['commit'])
            binary = unit/'USalign'
            command = ['g++', '-O3', '-o', str(binary), 'USalign.cpp']
            with (unit/'compile.stdout').open('wb') as stdout, (unit/'compile.stderr').open('wb') as stderr:
                compiled = subprocess.run(command, cwd=source, stdout=stdout, stderr=stderr, check=False)
            require(compiled.returncode == 0, 'a102_hpc_native_compilation_failed')
            algorithm = usalign
        else:
            require(request['algorithm'] == 'Foldseek', 'a102_hpc_native_algorithm_unknown')
            binary = verified/'foldseek/bin/foldseek'
            algorithm = foldseek
        software = {**pin, 'program': request['algorithm'], 'path': str(binary),
            'sha256': sha(binary.read_bytes())}
        native_request = {**request['native_request'], 'executable': str(binary), 'software': software}
        native = algorithm(native_request, unit)
        raw = canonical(native).encode()
        (unit/'native-result.json').write_bytes(raw)
        result.update(completed=True, returncode=0, payload_sha256=sha(raw),
            payload_encoding='zlib_base64', payload=base64.b64encode(zlib.compress(raw)).decode(),
            comparison_count=len(native['comparisons']), lead_count=len(native['leads']))
        require(len(canonical(result).encode()) < 500*1024, 'a102_hpc_result_requires_smaller_reference_panel')
    except Exception as error:
        result.update(completed=False, returncode=1,
            failure={'code': str(error), 'type': type(error).__name__})
        result.pop('payload', None)
    result['duration_seconds'] = time.time()-started
    temporary = unit/'result.writing'
    temporary.write_text(canonical(result)+'\n')
    temporary.replace(unit/'result.json')
    return result['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
