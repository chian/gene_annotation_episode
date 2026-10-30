#!/usr/bin/env python3
"""Source-only harness validation, with an audited actual check-only invocation.

Never call the application or post-copy probe. An audit hook forbids writes
outside this directory, network, child processes and candidate runtime imports.
"""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
manifest = json.loads((HERE / 'DELTA_MANIFEST_001.json').read_text())
receipt = {'scope': 'source-only harness validation and audited --check-only; no application or post-copy probe',
           'started_at': datetime.now(timezone.utc).isoformat(), 'passed': False,
           'application_executed': False, 'post_apply_probe_executed': False,
           'write_events': [], 'forbidden_events': []}
clock = time.monotonic()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def allowed_write(path, event):
    if isinstance(path, int):
        return
    resolved = Path(os.fsdecode(path)).resolve()
    if not resolved.is_relative_to(HERE):
        receipt['forbidden_events'].append({'event': event, 'path': str(resolved)})
        raise RuntimeError('validation_forbids_external_write:' + str(resolved))
    receipt['write_events'].append({'event': event, 'path': str(resolved.relative_to(HERE))})


def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        writable = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writable:
            allowed_write(path, event)
    elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.truncate', 'os.utime'):
        allowed_write(args[0], event)
    elif event in ('os.rename', 'os.link', 'os.symlink'):
        allowed_write(args[0], event)
        allowed_write(args[1], event)
    elif event in ('subprocess.Popen', 'os.system', 'os.fork', 'os.posix_spawn', 'socket.connect', 'socket.bind'):
        receipt['forbidden_events'].append({'event': event})
        raise RuntimeError('validation_forbids_execution_or_network:' + event)
    elif event == 'import' and args[0].split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        receipt['forbidden_events'].append({'event': event, 'module': args[0]})
        raise RuntimeError('validation_forbids_runtime_import:' + args[0])


sys.addaudithook(audit)
try:
    compiled = {}
    for path in sorted(HERE.glob('*.py')):
        compile(path.read_bytes(), str(path), 'exec')
        compiled[path.name] = digest(path)
    receipt['compiled_source_sha256'] = compiled
    before, after = manifest['expected_post182_sources'], manifest['candidate_sources']
    delta = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
    if delta != {row['path'] for row in manifest['files']} or len(delta) != 99:
        raise RuntimeError('independent_full_map_delta_mismatch')
    if not set(before) <= set(after) or len(set(after) - set(before)) != 93:
        raise RuntimeError('independent_new_or_deleted_count_mismatch')
    production_before = {name: digest(ROOT / name) if (ROOT / name).is_file() else None for name in after}
    candidate_before = {name: digest(Path(manifest['candidate']) / name) for name in after}
    if candidate_before != after:
        raise RuntimeError('candidate_freeze_changed_before_validation')
    sys.argv = [str(HERE / 'APPLY_001.py'), '--check-only']
    captured = io.StringIO()
    with redirect_stdout(captured):
        try:
            runpy.run_path(str(HERE / 'APPLY_001.py'), run_name='__main__')
        except SystemExit as error:
            code = error.code
        else:
            raise RuntimeError('check_only_did_not_return_an_exit_code')
    result = json.loads(captured.getvalue())
    receipt['check_only_exit_code'] = code
    receipt['check_only_summary'] = result
    check_receipt = Path(result['receipt_directory']) / 'CHECK_RECEIPT.json'
    receipt['check_only_receipt_sha256'] = digest(check_receipt)
    if code not in (0, 2) or result['failed_prerequisites']:
        raise RuntimeError('check_only_unexpected_prerequisite_failure')
    if result['passed'] or result['production_applied'] or result['written_paths']:
        raise RuntimeError('check_only_claimed_application')
    if any(name.split('.')[0] in ('gene_annotation_episode', 'method_loop') for name in sys.modules):
        raise RuntimeError('check_only_imported_runtime')
    production_after = {name: digest(ROOT / name) if (ROOT / name).is_file() else None for name in after}
    candidate_after = {name: digest(Path(manifest['candidate']) / name) for name in after}
    receipt['production_hash_changes_during_validation'] = [name for name in after if production_before[name] != production_after[name]]
    receipt['candidate_hash_changes_during_validation'] = [name for name in after if candidate_before[name] != candidate_after[name]]
    if receipt['production_hash_changes_during_validation'] or receipt['candidate_hash_changes_during_validation']:
        raise RuntimeError('source_changed_during_validation; no external write was permitted by this process')
    receipt.update(passed=True, no_runtime_imports=True, no_external_writes=True,
                   source_paths_checked=len(after), exact_delta_paths=len(delta))
except BaseException as error:
    receipt.update(error_type=type(error).__name__, error=str(error))
finally:
    receipt.update(ended_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic() - clock)
    destination = HERE / ('SOURCE_VALIDATION_' + str(time.time_ns()) + '.json')
    with destination.open('x') as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'receipt': str(destination), 'passed': receipt['passed'],
                      'check_only_exit_code': receipt.get('check_only_exit_code'),
                      'application_executed': False, 'error': receipt.get('error')}))
sys.exit(0 if receipt['passed'] else 1)
