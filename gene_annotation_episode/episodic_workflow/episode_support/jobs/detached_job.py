"""The process of one detached local job: run its command, commit its receipt, publish it as the job's event.

``LocalJobRoute`` starts this file as the command of the job's systemd service (inside the job's own control
group, through ``gene_annotation_episode._local_job_worker``). It runs after the Episode that launched the job has
returned and needs no Store, no journal and no run: it writes the receipt of the command into the job's own
directory (``result.json``) and publishes the same bytes once to the native event ledger as the job target's
``state_changed`` event. A unit that waits on the ledger wakes on that event and reads the receipt into custody
(``NativeEvents.wait``).

    python detached_job.py <ledger directory> <native handle file> <receipt file> -- <command> [arguments...]
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

RECEIPT_VERSION = 'detached_job_receipt'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def commit(path, data):
    """Write ``data`` to ``path`` so that the file is either absent or complete."""
    path = Path(path)
    temporary = path.with_name(path.name + '.writing')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main(arguments):
    if len(arguments) < 5 or arguments[3] != '--':
        raise SystemExit('usage: detached_job.py <ledger directory> <native handle file> <receipt file> -- command')
    ledger_directory, native_path, receipt_path = arguments[:3]
    command = arguments[4:]
    from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_event_ledger import (
        NativeEventLedger, native_target_handle)
    started = utc_now()
    try:
        returncode, start_failure = subprocess.run(command, check=False).returncode, None
    except OSError as error:
        returncode, start_failure = 127, {'exception_type': type(error).__name__, 'errno': error.errno}
    ended = utc_now()
    receipt = json.dumps({'version': RECEIPT_VERSION, 'command': command, 'returncode': returncode,
                          'start_failure': start_failure, 'started_at': started, 'ended_at': ended},
                         sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    commit(receipt_path, receipt)
    native = json.loads(Path(native_path).read_text())
    target = native_target_handle({'kind': 'systemd_user_service', 'unit': native['unit'],
                                   'request_sha256': native['request_sha256']})
    digest = hashlib.sha256(receipt).hexdigest()
    NativeEventLedger(ledger_directory).publish_native_event(target, {
        'version': 'native_event_publication', 'event': 'state_changed',
        'cause': 'service_exit_receipt_committed', 'record_ref': 'native_event_record_' + digest[:24],
        'receipt_sha256': digest, 'occurred_at': ended}, receipt_bytes=receipt)
    raise SystemExit(returncode if 0 <= returncode < 256 else 1)


if __name__ == '__main__':
    main(sys.argv[1:])
