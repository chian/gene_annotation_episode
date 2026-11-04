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


def allocated_bytes(directory):
    """Visible allocated blocks, without following links; not a hard quota."""
    total, stack = 0, [Path(directory)]
    while stack:
        try:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    try:
                        total += entry.stat(follow_symlinks=False).st_blocks * 512
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                    except FileNotFoundError:
                        pass
        except FileNotFoundError:
            pass
    return total


def event_time():
    return {'at': datetime.now(timezone.utc).isoformat(), 'monotonic_ns': time.monotonic_ns(),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def report(status_path, handle_path=None):
    """Commit the physical exit, then independently try optional exports."""
    body = None
    if handle_path is not None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        body = json.loads(Path(handle_path).read_bytes())
    service_exit = {name: os.environ.get(name) for name in ('SERVICE_RESULT', 'EXIT_CODE', 'EXIT_STATUS')}
    if body is not None and 'native_events' in body:
        try:
            from gene_annotation_episode.native_events import commit_service_exit_receipt
            commit_service_exit_receipt(handle_path, status_path, service_exit=service_exit, event_time=event_time)
        except Exception as error:
            print(json.dumps({'code': 'native_event_receipt_hook_failed',
                              'exception_type': type(error).__name__}), file=sys.stderr)
    else:
        # Unbound hooks retain their original wire representation.
        atomic_json(status_path, {**service_exit, 'ended': event_time()})
    if body is not None and 'statistics' in body:
        try:
            from gene_annotation_episode.execution_recording import publish_native_statistics
            publish_native_statistics(handle_path)
        except Exception as error:
            print(json.dumps({'code': 'statistics_export_hook_failed',
                              'exception_type': type(error).__name__}), file=sys.stderr)
    if body is not None and 'native_events' in body:
        try:
            from gene_annotation_episode.native_events import publish_native_events
            publish_native_events(handle_path)
        except Exception as error:
            print(json.dumps({'code': 'native_event_export_hook_failed',
                              'exception_type': type(error).__name__}), file=sys.stderr)


def main() -> None:
    operation, request_name, *extra = sys.argv[1:]
    request_path = Path(request_name)
    if operation == "report":
        report(request_path, extra[0] if extra else None)
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
    environment.update(request.get("env") or {})
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
