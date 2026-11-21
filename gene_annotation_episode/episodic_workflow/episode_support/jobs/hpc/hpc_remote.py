"""A remote HPC resource reached through the run's job access: the commands, file reads and file writes the HPC
planning episodes make outside a batch job, and the handed-off job they observe.

Every function is handed the tool's ``ctx`` and acts through ``ctx.services['job_access']`` (the episode declares
``job_access``). Nothing here opens a transport: the route the run bound to the resource id is the only way out,
so a run whose route has no transport gets a failed request and contacts nothing.

- ``command``: one login-mode command (``JobAccess.run``: launched once under the unit's operation key, waited
  for, its files fetched as artifacts the unit holds). ``read_file`` and ``write_file`` are such commands.
- ``handoff_target`` and ``job_status``: the job a launch child handed off (a held ``JOB_LEDGER`` handoff row) and
  one status request for it (``JobAccess.check``, which writes the check row).

A request the route could not make, or a command that could not do its work, comes back as ``{'status': 'failed',
'failure': {'code', 'detail'}}``: an outcome for the calling unit to return, never an exception and never a state
of a job.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shlex

from episode_runtime.job_access import JOB_LEDGER


def _failed(code, detail):
    return {'status': 'failed', 'failure': {'code': code, 'detail': detail}}


async def command(ctx, resource_id, script, *, name, inputs=None):
    """Run the shell text ``script`` once on the resource and wait for it. ``inputs`` is ``{file name: held
    artifact reference}``, staged in the command's directory. ``{'status': 'completed', 'returncode', 'files':
    {name: bytes} (what the command left in its directory, with ``stdout.log`` and ``stderr.log``), 'file_refs':
    {name: artifact reference}}``. Several commands of one unit carry different ``name``s."""
    ran = await ctx.services['job_access'].run(
        ctx, resource_id, {'mode': 'login', 'script': script, 'arguments': [], 'env': {}}, inputs=inputs, name=name)
    if ran['status'] != 'completed':
        return {'status': 'failed', 'failure': (ran['fetch'] or ran['launch'])['failure']}
    fetched = ran['fetch']
    reply = json.loads(ctx.store.get_artifact(fetched['reply_ref']))
    refs = {item['name']: item['ref'] for item in fetched['results']}
    return {'status': 'completed', 'returncode': reply['status']['native']['returncode'],
            'files': {item: ctx.store.get_artifact(ref) for item, ref in refs.items()}, 'file_refs': refs}


async def read_file(ctx, resource_id, path, limit, *, name):
    """The first ``limit + 1`` bytes of the file ``path`` on the resource (one byte more than the caller accepts,
    so that it can tell a larger file): ``{'status': 'completed', 'path', 'bytes_base64', 'size_bytes', 'sha256',
    'artifact_ref'}``; ``remote_file_unreadable`` when the file cannot be read."""
    ran = await command(ctx, resource_id, 'head -c ' + str(limit + 1) + ' -- ' + shlex.quote(path) + ' > window.bin',
                        name=name)
    if ran['status'] != 'completed':
        return ran
    if ran['returncode']:
        return _failed('remote_file_unreadable', {'path': path, 'returncode': ran['returncode'],
                                                  'stderr': ran['files']['stderr.log'].decode('utf-8', 'replace')})
    payload = ran['files']['window.bin']
    return {'status': 'completed', 'path': path, 'bytes_base64': base64.b64encode(payload).decode(),
            'size_bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
            'artifact_ref': ran['file_refs']['window.bin']}


async def write_file(ctx, resource_id, path, artifact_ref, *, name):
    """Publish the held artifact as the file ``path`` on the resource (written beside it, then renamed):
    ``{'status': 'completed', 'path', 'artifact_ref'}``; ``remote_file_not_written`` when it could not be."""
    quoted = shlex.quote(path)
    ran = await command(ctx, resource_id, 'cp content.bin ' + quoted + '.writing && mv ' + quoted + '.writing '
                        + quoted, name=name, inputs={'content.bin': artifact_ref})
    if ran['status'] != 'completed':
        return ran
    if ran['returncode']:
        return _failed('remote_file_not_written', {'path': path, 'returncode': ran['returncode'],
                                                   'stderr': ran['files']['stderr.log'].decode('utf-8', 'replace')})
    return {'status': 'completed', 'path': path, 'artifact_ref': artifact_ref}


def handoff_target(store, handoff_ref):
    """The batch job a held handoff row names: ``{'handoff_ref', 'job' (the handle), 'resource_id',
    'execution_id' (the scheduler's job id)}``. The row must be held (``CustodyError`` otherwise)."""
    row = store.table(JOB_LEDGER).get(handoff_ref)
    if row['event'] != 'handoff' or row['detail']['native']['mode'] != 'batch':
        raise ValueError('record_is_not_the_handoff_of_a_batch_job:' + str(handoff_ref))
    return {'handoff_ref': handoff_ref, 'job': row['job'], 'resource_id': row['detail']['resource_id'],
            'execution_id': row['detail']['native']['job_id']}


def job_status(ctx, target):
    """One status request for the handed-off job, written as its check row: ``{'status': 'completed', 'state'
    (``submitted``, ``running``, ``completed``, ``failed``), 'observed_at', 'native': {'pbs_fields': the
    scheduler's own fields of the job}, 'check_ref', 'reply_ref'}``."""
    checked = ctx.services['job_access'].check(ctx, target['handoff_ref'])
    if checked['status'] != 'completed':
        return {'status': 'failed', 'failure': checked['failure']}
    reply = json.loads(ctx.store.get_artifact(checked['reply_ref']))
    state = {'queued': 'submitted', 'finished': 'completed', 'cancelled': 'failed'}.get(checked['state'],
                                                                                         checked['state'])
    return {'status': 'completed', 'state': state, 'observed_at': checked['observed_at'],
            'native': {'pbs_fields': reply['native']}, 'check_ref': checked['check_ref'],
            'reply_ref': checked['reply_ref']}


__all__ = ['command', 'handoff_target', 'job_status', 'read_file', 'write_file']
