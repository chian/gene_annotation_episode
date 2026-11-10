"""Execute the existing A103 calculations inside the original HPC unit."""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
import zlib


VERSION = 'a103_shared_hpc_native_v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError(code)


def main():
    path = Path(sys.argv[1]).resolve()
    raw_request = path.read_bytes()
    request = json.loads(raw_request)
    require(request['version'] == VERSION, 'a103_hpc_request_version')
    unit = Path(os.environ['HPC_UNIT_DIRECTORY']).resolve()
    unit.mkdir(parents=True, exist_ok=True)
    result = {'version': VERSION, 'program': 'a103_gene_context_native',
        'request_sha256': sha(raw_request), 'worker_sha256': sha(Path(__file__).read_bytes()),
        'code_manifest_sha256': request['code_manifest_sha256'], 'python_version': sys.version,
        'pbs_job_id': os.environ.get('PBS_JOBID'), 'compute_hostname': socket.gethostname(),
        'completed': False, 'returncode': 1, 'failure': None}
    started = time.time()
    try:
        require(result['pbs_job_id'] and not result['compute_hostname'].startswith(('aurora-uan', 'login')),
            'a103_native_work_requires_original_compute_allocation')
        snapshot_raw = (path.parent/'a103-sources.json').read_bytes()
        require(sha(snapshot_raw) == request['source_snapshot_sha256'], 'a103_hpc_source_snapshot_conflict')
        sources = json.loads(snapshot_raw)
        require(set(sources) == set(request['code_manifest'])-{'a103-worker.py'}, 'a103_hpc_source_membership_conflict')
        require(sha(canonical(request['code_manifest']).encode()) == request['code_manifest_sha256'],
            'a103_hpc_code_manifest_conflict')
        package = unit/'source-snapshot'
        package.mkdir(exist_ok=True)
        for relative, expected in request['code_manifest'].items():
            if relative == 'a103-worker.py':
                require(sha(Path(__file__).read_bytes()) == expected, 'a103_hpc_worker_conflict')
                continue
            data = sources[relative].encode()
            require(sha(data) == expected, 'a103_hpc_implementation_conflict')
            target = (package/relative).resolve()
            require(target.is_relative_to(package), 'a103_hpc_snapshot_path_invalid')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for name in ('tmp', 'cache', 'inputs'):
            (unit/name).mkdir(exist_ok=True)
        os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(unit/'tmp'),
            XDG_CACHE_HOME=str(unit/'cache'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        dependencies = path.parent/'dependencies'
        if dependencies.is_dir():sys.path.insert(0,str(dependencies))
        sys.path.insert(0, str(package))
        import Bio
        require(Bio.__version__ == request['biopython_version'], 'a103_hpc_biopython_version_conflict')
        from gene_annotation_episode.a103_scoring import execute, VERSION as profile
        require(profile == request['scientific_profile'], 'a103_hpc_scientific_profile_conflict')
        native = dict(request['plan']['native_request'])
        for field, asset in request['assets'].items():
            require(field in {'input_path', 'sequence_path', 'native_path', 'database_path'},
                'a103_hpc_input_role_invalid')
            data = base64.b64decode(asset['bytes_base64'], validate=True)
            require(len(data) == asset['byte_length'] and sha(data) == asset['sha256'], 'a103_hpc_input_bytes_conflict')
            target = unit/'inputs'/field
            target.write_bytes(data)
            native[field] = str(target)
        measured = execute(native)
        raw = canonical(measured).encode()
        (unit/'native-result.json').write_bytes(raw)
        result.update(completed=True, returncode=0, payload_encoding='zlib_base64',
            payload_sha256=sha(raw), payload=base64.b64encode(zlib.compress(raw)).decode(),
            scientific_profile=profile, biopython_version=Bio.__version__)
        require(len(canonical(result).encode()) < 500*1024, 'a103_hpc_result_requires_bounded_inputs')
    except Exception as error:
        result.update(completed=False, returncode=1, failure={'code': str(error), 'type': type(error).__name__})
        result.pop('payload', None)
    result['duration_seconds'] = time.time()-started
    temporary = unit/'result.writing'
    temporary.write_text(canonical(result)+'\n')
    temporary.replace(unit/'result.json')
    return result['returncode']


if __name__ == '__main__':
    raise SystemExit(main())
