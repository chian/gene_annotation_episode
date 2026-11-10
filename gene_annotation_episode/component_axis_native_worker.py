"""Run the frozen A107/A110 calculator inside its original HPC allocation."""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
import zlib


VERSION = 'component_axis_native_v1'
PROGRAM = 'component_axis_scientific_native'


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
    require(request['version'] == VERSION, 'component_native_request_version_conflict')
    unit = Path(os.environ['HPC_UNIT_DIRECTORY']).resolve()
    unit.mkdir(parents=True, exist_ok=True)
    result = {'version': VERSION, 'program': PROGRAM,
        'request_sha256': sha(raw_request), 'worker_sha256': sha(Path(__file__).read_bytes()),
        'code_manifest_sha256': request['code_manifest_sha256'],
        'pbs_job_id': os.environ.get('PBS_JOBID'), 'compute_hostname': socket.gethostname(),
        'python_version': sys.version, 'completed': False, 'returncode': 1, 'failure': None}
    started = time.time()
    try:
        require(result['pbs_job_id'] and not result['compute_hostname'].startswith(('aurora-uan', 'login')),
            'component_native_original_compute_allocation_required')
        snapshot_raw = (path.parent/'component-sources.json').read_bytes()
        require(sha(snapshot_raw) == request['source_snapshot_sha256'], 'component_native_source_snapshot_conflict')
        sources = json.loads(snapshot_raw)
        require(set(sources) == set(request['code_manifest'])-{'component-worker.py'},
            'component_native_source_membership_conflict')
        require(sha(canonical(request['code_manifest']).encode()) == request['code_manifest_sha256'],
            'component_native_code_manifest_conflict')
        package = unit/'source-snapshot'
        package.mkdir(exist_ok=True)
        for name, digest in request['code_manifest'].items():
            if name == 'component-worker.py':
                require(sha(Path(__file__).read_bytes()) == digest, 'component_native_worker_conflict')
                continue
            raw = sources[name].encode()
            require(sha(raw) == digest, 'component_native_scientific_implementation_conflict')
            target = (package/name).resolve()
            require(target.is_relative_to(package), 'component_native_source_path_invalid')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        for name in ('tmp', 'cache', 'inputs'):
            (unit/name).mkdir(exist_ok=True)
        os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(unit/'tmp'),
            XDG_CACHE_HOME=str(unit/'cache'))
        dependencies = path.parent/'dependencies'
        if dependencies.is_dir():
            sys.path.insert(0, str(dependencies))
        sys.path.insert(0, str(package))
        from importlib.metadata import version
        require(version('jsonschema') == request['jsonschema_version'], 'component_native_validator_version_conflict')
        from axis_native.component_axis_native_contracts import load_json
        raw = base64.b64decode(request['input']['bytes_base64'], validate=True)
        require(sha(raw) == request['input']['file']['sha256'] and len(raw) == request['input']['file']['size_bytes'],
            'component_native_original_input_bytes_conflict')
        input_name = ('searched-cds.faa' if request['operation'] == 'partner.request_detection_hpc'
            else 'declared-panel.json')
        (unit/'inputs'/input_name).write_bytes(raw)
        if request['operation'] == 'chemistry.request_flux_balance_hpc':
            from axis_native.a110_fba_native import calculate
            native = calculate(request, unit)
        elif request['operation'] == 'partner.request_detection_hpc':
            from axis_native.a107_genomic_detection_native import calculate
            native = calculate(request, unit)
        elif request['axis'] == 'A107':
            from axis_native.a107_expression_components import calculate
            native = calculate(load_json(raw), request['selection'])
        elif request['axis'] == 'A110':
            from axis_native.a110_chemical_accounting import calculate
            native = calculate(load_json(raw), request['selection'])
        else:
            raise ValueError('component_native_unknown_axis')
        require(native['version'] == request['scientific_profile'], 'component_native_scientific_profile_conflict')
        payload = canonical(native).encode()
        require(len(payload) <= 32*1024**2, 'component_native_selected_result_exceeds_receipt_capacity')
        (unit/'native-components.json').write_bytes(payload)
        result.update(completed=True, returncode=0, axis=request['axis'],
            scientific_profile=request['scientific_profile'], jsonschema_version=version('jsonschema'),
            input_sha256=sha(raw), payload_encoding='zlib_base64', payload_sha256=sha(payload),
            payload=base64.b64encode(zlib.compress(payload)).decode())
        require(len(canonical(result).encode()) < 500*1024,
            'component_native_selected_result_exceeds_HPC_transport_capacity; select_smaller_panel')
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
