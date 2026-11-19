"""Store-free launcher/status hook for an isolated local systemd service."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


def atomic_json(path, body):
    path = Path(path)
    temporary = path.with_name(path.name + '.writing')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(body, stream, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


if __package__:
    from .local_scratch import allocated_bytes
else:
    # The native environment can enable PYTHONSAFEPATH; bind this exact sibling
    # without depending on the script directory being present in sys.path.
    import importlib.util
    _scratch_spec = importlib.util.spec_from_file_location(
        'gene_annotation_episode.local_scratch', Path(__file__).with_name('local_scratch.py'))
    _scratch_module = importlib.util.module_from_spec(_scratch_spec)
    _scratch_spec.loader.exec_module(_scratch_module)
    allocated_bytes = _scratch_module.allocated_bytes

def event_time():
    return {'at': datetime.now(timezone.utc).isoformat(), 'monotonic_ns': time.monotonic_ns(),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def report(status_path):
    """Commit the physical exit."""
    service_exit = {name: os.environ.get(name) for name in ('SERVICE_RESULT', 'EXIT_CODE', 'EXIT_STATUS')}
    atomic_json(status_path, {**service_exit, 'ended': event_time()})


def main() -> None:
    operation, request_name, *extra = sys.argv[1:]
    request_path = Path(request_name)
    if operation == "report":
        if extra:
            raise SystemExit('report_takes_only_the_status_path')
        report(request_path)
        return
    raw_request = request_path.read_bytes()
    if len(extra) != 1 or hashlib.sha256(raw_request).hexdigest() != extra[0]:
        print(json.dumps({'code': 'native_request_identity_mismatch'}), file=sys.stderr)
        raise SystemExit(2)
    request = json.loads(raw_request)
    resource.setrlimit(resource.RLIMIT_FSIZE, (request["file_bytes"], request["file_bytes"]))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    atomic_json(request['ready_path'], {**event_time(), 'request_sha256': extra[0]})
    while not Path(request["release_path"]).exists():
        time.sleep(0.01)
    environment = dict(os.environ)
    environment.update(request["env"])
    # Native temporary output belongs to this job's monitored directory.
    environment.update({name: request["cwd"] for name in ("TMPDIR", "TMP", "TEMP")})
    # The wrapper and all native descendants share this verified cgroup. The
    # scratch monitor outlives any launching/monitoring Episode or workflow.
    started = event_time()
    maximum = allocated_bytes(request['cwd'])
    failure = None
    try:
        with open(request.get('stdin_path') or os.devnull, 'rb') as inp:
            native = subprocess.Popen(request['command'], cwd=request['cwd'], env=environment, stdin=inp)
        while native.poll() is None:
            maximum = max(maximum, allocated_bytes(request['cwd']))
            if maximum > request['file_bytes']:
                failure = {'resource': 'scratch_bytes', 'limit': request['file_bytes'],
                           'evidence': {'observed_allocated_bytes': maximum}}
                native.kill()
                break
            time.sleep(.05)  # Resource enforcement cadence, not Episode polling.
        code = native.wait()
        maximum = max(maximum, allocated_bytes(request['cwd']))
        if maximum > request['file_bytes'] and failure is None:
            failure = {'resource': 'scratch_bytes', 'limit': request['file_bytes'],
                       'evidence': {'observed_allocated_bytes': maximum}}
        atomic_json(request['result_path'], {'started': started, 'ended': event_time(),
            'native_returncode': code, 'observed_scratch_bytes': maximum, 'resource_failure': failure,
            'execution_failure': None})
        # This is the wrapper's actual exit. Native signal/exit identity remains
        # explicit in its receipt rather than being relabeled as wrapper state.
        raise SystemExit(code if code >= 0 else 1)
    except OSError as error:
        atomic_json(request['result_path'], {'started': started, 'ended': event_time(),
            'native_returncode': None, 'observed_scratch_bytes': maximum, 'resource_failure': failure,
            'execution_failure': {'exception_type': type(error).__name__, 'errno': error.errno}})
        raise SystemExit(127)


if __name__ == "__main__":
    main()
