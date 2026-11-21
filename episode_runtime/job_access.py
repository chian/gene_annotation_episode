"""Job access: the run's service for work that keeps running after the Episode that started it has returned.

``JobAccess`` is a service of the run (``ctx.services['job_access']``; the run's caller supplies its factory in the
``services`` collaborator). It is built with the run's **routes**: one object per resource id that reaches a
scheduler, a transport or the local job worker. This module knows no route; the real ones are library modules
(``episode_support/jobs/local_job_route.py``, ``pbs_job_route.py``).

**Custody is built in.** Every operation that acts takes the tool's ``ctx`` and writes the job's record through
``ctx.store``: a row of the declared work table ``JOB_LEDGER`` (the job record kind) with the route's reply as an
artifact, in one transaction. The Episode therefore holds the row as produced by the unit, returns it to its
parent in a ``record_refs`` field, and a later Episode reads it only when it was handed it. Nothing travels through
the service: ``check``, ``fetch`` and ``cancel`` take the reference of a held handoff row and read it through
``ctx.store`` (a row the Episode does not hold raises ``CustodyError``).

| Event of a row | Written by | ``detail`` |
|---|---|---|
| ``handoff`` | ``launch`` | resource id, route kind, the route's native identity of the job, digest of the job, the input references, the estimates made at launch |
| ``check`` | ``check`` | state, whether results are available, the handoff reference, the caller's assessment |
| ``closure`` | ``fetch``, ``cancel`` | outcome (``results_acquired``, ``cancelled``), state, the results (name, reference, bytes, sha256) |
| ``window`` | ``window`` | the file name, the offset and limit asked, the bytes read and their sha256, the handoff reference; the bytes are the artifact in ``result_refs`` |

**No relaunch on resume.** The job's handle is derived from the unit's ``ctx.operation_key``, so it is the same on
every attempt of the unit. A unit that began and did not finish runs again with ``ctx.resumed`` true and
``ctx.abandoned`` naming what its abandoned attempt wrote. ``launch`` then finds the abandoned handoff row of its
handle, takes it over (``ctx.store.reclaim``) and returns it: the route is not asked. When the attempt was cut
before the row committed, ``launch`` asks the route again with the same handle, and a route submits a handle at
most once: it returns the job it already holds under that handle, with its original submission time
(``adopted``). ``check``, ``fetch``, ``cancel`` and ``window`` take over their abandoned row in the same way.
There is no table of operations that already ran: the receipts of the unit are the memory, and the journal replays
a finished unit without running it.

**A request that fails** (transport down, scheduler error, results not available) is raised by the route as
``RouteRequestError`` and returned by the operation as ``{'status': 'failed', 'failure': {'code', 'detail'}}``: it
is an outcome of the tool unit, never a state of the job. No row is written for it. Any other error propagates and
ends the run.

**Decisions read; tools act.** ``decide`` and ``action`` reach the service only through its read handle
(``ctx.services['job_access'].read('resources')``, ``.read('describe', resource_id)``); the system records each
read with the decision.

The route protocol (each method synchronous; replies are closed JSON):

| Member | Returns |
|---|---|
| ``kind`` | text: the kind of resource (``'local'``, ``'pbs'``, ...) |
| ``describe()`` | what a decision may know of the resource |
| ``submit(handle, job, files, owner)`` | ``{'native', 'submitted_at' (UTC text), 'adopted' (bool), 'reply'}``; at most one submission per handle |
| ``status(handle, native)`` | ``{'state' (one of ``STATES``), 'result_available' (bool), 'observed_at' (UTC text), 'reply'}`` |
| ``results(handle, native)`` | ``[{'name', 'bytes', 'media_type'}]``: the result files of a job that ended |
| ``read(handle, native, name, offset, limit)`` | bytes of one file of the job (a result; a log while the job runs) |
| ``cancel(handle, native)`` | ``{'reply'}`` |
| ``await wait(handle, native)`` | returns when the job has ended (used by ``run``) |
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib

from method_loop.jsonvalue import canonical, closed_copy, content_digest

from .work_tables import TableDeclaration

JOB_LEDGER = TableDeclaration(name='job_ledger',
                              columns=('job', 'event', 'at', 'detail', 'source_ref', 'result_refs'),
                              key=('job', 'event', 'at'), record_refs=('source_ref', 'result_refs'))
STATES = ('queued', 'running', 'finished', 'failed', 'cancelled', 'unknown')
ROUTE_MEMBERS = ('kind', 'describe', 'submit', 'status', 'results', 'read', 'cancel', 'wait')


class RouteRequestError(RuntimeError):
    """A request to a resource failed; ``failure`` is ``{'code': text, 'detail': closed JSON}``."""

    def __init__(self, code, detail=None):
        if type(code) is not str or not code:
            raise ValueError('route_request_failure_code_must_be_text')
        self.failure = {'code': code, 'detail': closed_copy(detail, 'route_request_failure_detail', TypeError)}
        super().__init__(code)


def job_handle(operation_key, resource_id, name):
    """The handle of the job a unit launches on a resource: the same on every attempt of the unit."""
    return 'job_' + content_digest([operation_key, resource_id, name])[:32]


class JobAccess:
    """The routes of one run, and the launch, check, window, fetch and cancel of a job with its records in
    custody."""

    def __init__(self, routes):
        if not isinstance(routes, Mapping) or not routes:
            raise ValueError('job_access_requires_a_route_for_each_resource_id')
        for resource_id, route in routes.items():
            if type(resource_id) is not str or not resource_id:
                raise ValueError('job_access_resource_id_must_be_text')
            missing = [name for name in ROUTE_MEMBERS if not hasattr(route, name)]
            if missing:
                raise TypeError('job_access_route_lacks:' + resource_id + ':' + ','.join(missing))
        self._routes = dict(routes)

    def _route(self, resource_id):
        if resource_id not in self._routes:
            raise LookupError('job_resource_not_bound:' + str(resource_id))
        return self._routes[resource_id]

    # -- what a decision may read (closed JSON; recorded by the system per unit position) --------------------
    def resources(self):
        """The bound resources: ``[{'resource_id', 'kind'}]``, by resource id."""
        return [{'resource_id': name, 'kind': self._routes[name].kind} for name in sorted(self._routes)]

    def describe(self, resource_id):
        """What the route says of its resource."""
        return closed_copy(self._route(resource_id).describe(), 'job_resource_description', TypeError)

    # -- custody ---------------------------------------------------------------------------------------------
    @staticmethod
    def _handoff(ctx, handoff_ref):
        row = ctx.store.table(JOB_LEDGER).get(handoff_ref)
        if row['event'] != 'handoff':
            raise ValueError('job_record_is_not_a_handoff:' + str(handoff_ref))
        return row

    @staticmethod
    def _taken_over(ctx, handle, event, detail=None):
        """The row of ``event`` for ``handle`` (with the values ``detail`` in its detail, when given) that an
        abandoned attempt of this unit wrote, taken over as this attempt's own with the artifacts it names;
        ``None`` when no attempt wrote one."""
        if not ctx.resumed:
            return None
        rows = [item for item in ctx.abandoned
                if item['written'] is not None and item['written']['table'] == JOB_LEDGER.name
                and item['written']['job'] == handle and item['written']['event'] == event
                and all(item['written']['detail'][name] == value for name, value in (detail or {}).items())]
        if not rows:
            return None
        abandoned = {item['ref'] for item in ctx.abandoned}
        written = rows[-1]['written']
        with ctx.store.transaction():
            for ref in (written['source_ref'], *written['result_refs']):
                if ref in abandoned and not ctx.store.holds(ref):
                    ctx.store.reclaim(ref)
            ctx.store.reclaim(rows[-1]['ref'])
        return ctx.store.table(JOB_LEDGER).get(rows[-1]['ref'])

    @staticmethod
    def _failed(handle, resource_id, error):
        return {'status': 'failed', 'job': handle, 'resource_id': resource_id, 'failure': error.failure}

    @staticmethod
    def _write(ctx, handle, event, at, detail, reply, results=()):
        with ctx.store.transaction():
            reply_ref = ctx.store.artifact(canonical(reply), 'application/json')
            return ctx.store.table(JOB_LEDGER).put({
                'job': handle, 'event': event, 'at': at, 'detail': detail, 'source_ref': reply_ref,
                'result_refs': list(dict.fromkeys(results))})

    # -- launch ----------------------------------------------------------------------------------------------
    def launch(self, ctx, resource_id, job, *, inputs=None, estimates=None, name='job'):
        """Submit ``job`` on the resource and write its handoff row. ``inputs`` is ``{file name: reference}``:
        each is read through ``ctx.store`` (it must be held) and staged for the job under that name;
        ``estimates`` is what was expected of the job before it ran, kept in the row. Several launches of one
        unit carry different ``name``s."""
        route = self._route(resource_id)
        job = closed_copy(job, 'job', TypeError)
        estimates = closed_copy(estimates, 'job_estimates', TypeError)
        inputs = closed_copy({} if inputs is None else inputs, 'job_inputs', TypeError)
        handle = job_handle(ctx.operation_key, resource_id, name)
        row = self._taken_over(ctx, handle, 'handoff')
        replayed = row is not None
        if row is None:
            files = {path: ctx.store.get_artifact(ref) for path, ref in sorted(inputs.items())}
            try:
                submitted = route.submit(handle, job, files, {'run_id': ctx.run_id, 'episode_id': ctx.episode_id})
            except RouteRequestError as error:
                return self._failed(handle, resource_id, error)
            detail = {'resource_id': resource_id, 'kind': route.kind, 'native': submitted['native'],
                      'job_sha256': content_digest(job), 'input_refs': inputs, 'estimates': estimates,
                      'adopted': submitted['adopted']}
            row = self._write(ctx, handle, 'handoff', submitted['submitted_at'], detail, submitted['reply'])
        return {'status': 'completed', 'job': handle, 'resource_id': resource_id, 'kind': row['detail']['kind'],
                'submitted_at': row['at'], 'adopted': row['detail']['adopted'], 'replayed': replayed,
                'handoff_ref': row['id'], 'reply_ref': row['source_ref']}

    # -- check -----------------------------------------------------------------------------------------------
    def check(self, ctx, handoff_ref, *, assess=None):
        """One status request for the job of the held handoff row, written as a check row. ``assess(status,
        handoff)`` is the caller's own reading of the reply (a time-remaining estimate, the score of the earlier
        one); what it returns is kept in the row."""
        handoff = self._handoff(ctx, handoff_ref)
        handle, resource_id = handoff['job'], handoff['detail']['resource_id']
        row = self._taken_over(ctx, handle, 'check')
        replayed = row is not None
        if row is None:
            try:
                status = self._status(self._route(resource_id), handle, handoff)
            except RouteRequestError as error:
                return self._failed(handle, resource_id, error)
            assessment = None if assess is None else closed_copy(assess(status, handoff), 'job_assessment', TypeError)
            detail = {'resource_id': resource_id, 'kind': handoff['detail']['kind'], 'state': status['state'],
                      'result_available': status['result_available'], 'handoff_ref': handoff_ref,
                      'assessment': assessment}
            row = self._write(ctx, handle, 'check', status['observed_at'], detail, status['reply'])
        return {'status': 'completed', 'job': handle, 'resource_id': resource_id, 'state': row['detail']['state'],
                'result_available': row['detail']['result_available'], 'observed_at': row['at'],
                'assessment': row['detail']['assessment'], 'replayed': replayed, 'check_ref': row['id'],
                'reply_ref': row['source_ref']}

    @staticmethod
    def _status(route, handle, handoff):
        status = route.status(handle, handoff['detail']['native'])
        if status['state'] not in STATES or type(status['result_available']) is not bool:
            raise ValueError('job_route_status_invalid:' + repr(status['state']))
        return status

    # -- window ----------------------------------------------------------------------------------------------
    def window(self, ctx, handoff_ref, name, *, offset, limit):
        """One byte window of a file of the job of the held handoff row (a log, also while the job runs): at most
        ``limit`` bytes from ``offset``, read through the route. The bytes are written as an artifact and a
        ``window`` row names it, so the window is a record of the job in custody. The job is not closed and its
        state is not asked: this is no check and no fetch. A file the route does not have is a failed request."""
        handoff = self._handoff(ctx, handoff_ref)
        handle, resource_id = handoff['job'], handoff['detail']['resource_id']
        asked = {'name': name, 'offset': offset, 'limit': limit}
        row = self._taken_over(ctx, handle, 'window', asked)
        replayed = row is not None
        if row is None:
            try:
                data = self._route(resource_id).read(handle, handoff['detail']['native'], name, offset, limit)
            except RouteRequestError as error:
                return self._failed(handle, resource_id, error)
            if type(data) is not bytes or len(data) > limit:
                raise ValueError('job_route_window_invalid:' + repr(name))
            with ctx.store.transaction():
                content_ref = ctx.store.artifact(data, 'application/octet-stream')
                detail = {'resource_id': resource_id, 'kind': handoff['detail']['kind'], **asked,
                          'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                          'handoff_ref': handoff_ref}
                row = self._write(ctx, handle, 'window', datetime.now(timezone.utc).isoformat(), detail,
                                  {**asked, 'bytes': len(data)}, [content_ref])
        return {'status': 'completed', 'job': handle, 'resource_id': resource_id, 'name': row['detail']['name'],
                'offset': row['detail']['offset'], 'limit': row['detail']['limit'], 'bytes': row['detail']['bytes'],
                'sha256': row['detail']['sha256'], 'read_at': row['at'], 'replayed': replayed,
                'window_ref': row['id'], 'content_ref': row['result_refs'][0], 'reply_ref': row['source_ref']}

    # -- fetch -----------------------------------------------------------------------------------------------
    def fetch(self, ctx, handoff_ref, *, names=None):
        """Fetch the result files of the job (all of them, or ``names``), write each as an artifact with its
        digest, and write the closure row (outcome ``results_acquired``). Whether the job is done is not decided
        here: a route refuses the results of a job that has not ended, and that is a failed request."""
        handoff = self._handoff(ctx, handoff_ref)
        handle, resource_id, native = handoff['job'], handoff['detail']['resource_id'], handoff['detail']['native']
        row = self._taken_over(ctx, handle, 'closure')
        replayed = row is not None
        if row is None:
            route = self._route(resource_id)
            try:
                status = self._status(route, handle, handoff)
                catalog = route.results(handle, native)
                listed = {item['name']: item for item in catalog}
                wanted = list(listed) if names is None else list(names)
                absent = [name for name in wanted if name not in listed]
                if absent:
                    raise RouteRequestError('result_not_in_catalog', {'names': absent, 'catalog': sorted(listed)})
                contents = []
                for name in wanted:
                    data = route.read(handle, native, name, 0, listed[name]['bytes'])
                    if type(data) is not bytes or len(data) != listed[name]['bytes']:
                        raise RouteRequestError('result_differs_from_its_catalog_entry', {'name': name})
                    contents.append((listed[name], data))
            except RouteRequestError as error:
                return self._failed(handle, resource_id, error)
            with ctx.store.transaction():
                results = [{'name': item['name'], 'ref': ctx.store.artifact(data, item['media_type']),
                            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                           for item, data in contents]
                detail = {'resource_id': resource_id, 'kind': handoff['detail']['kind'],
                          'outcome': 'results_acquired', 'state': status['state'], 'results': results,
                          'handoff_ref': handoff_ref}
                row = self._write(ctx, handle, 'closure', status['observed_at'], detail,
                                  {'status': status['reply'], 'catalog': catalog},
                                  [item['ref'] for item in results])
        return self._closed(row, replayed)

    # -- cancel ----------------------------------------------------------------------------------------------
    def cancel(self, ctx, handoff_ref):
        """Cancel the job, confirm with one status request, and write the closure row (outcome ``cancelled``)."""
        handoff = self._handoff(ctx, handoff_ref)
        handle, resource_id, native = handoff['job'], handoff['detail']['resource_id'], handoff['detail']['native']
        row = self._taken_over(ctx, handle, 'closure')
        replayed = row is not None
        if row is None:
            route = self._route(resource_id)
            try:
                cancelled = route.cancel(handle, native)
                status = self._status(route, handle, handoff)
            except RouteRequestError as error:
                return self._failed(handle, resource_id, error)
            detail = {'resource_id': resource_id, 'kind': handoff['detail']['kind'], 'outcome': 'cancelled',
                      'state': status['state'], 'results': [], 'handoff_ref': handoff_ref}
            row = self._write(ctx, handle, 'closure', status['observed_at'], detail,
                              {'cancel': cancelled['reply'], 'status': status['reply']})
        return self._closed(row, replayed)

    @staticmethod
    def _closed(row, replayed):
        return {'status': 'completed', 'job': row['job'], 'resource_id': row['detail']['resource_id'],
                'outcome': row['detail']['outcome'], 'state': row['detail']['state'], 'closed_at': row['at'],
                'results': row['detail']['results'], 'result_refs': row['result_refs'], 'replayed': replayed,
                'closure_ref': row['id'], 'reply_ref': row['source_ref']}

    # -- a command that is waited for --------------------------------------------------------------------------
    async def run(self, ctx, resource_id, job, *, inputs=None, name='command'):
        """Launch ``job``, wait until it has ended and fetch its results, in the one unit that calls this (a
        command whose result the unit needs). It is launched at most once: a unit that runs again finds its
        handoff row or the route's job under the same handle and waits for that job. Returns ``{'status',
        'launch', 'fetch'}``; a failed launch or fetch is the returned status ``failed``."""
        launched = self.launch(ctx, resource_id, job, inputs=inputs, name=name)
        if launched['status'] != 'completed':
            return {'status': 'failed', 'launch': launched, 'fetch': None}
        handoff = self._handoff(ctx, launched['handoff_ref'])
        try:
            await self._route(resource_id).wait(launched['job'], handoff['detail']['native'])
        except RouteRequestError as error:
            return {'status': 'failed', 'launch': launched,
                    'fetch': self._failed(launched['job'], resource_id, error)}
        fetched = self.fetch(ctx, launched['handoff_ref'])
        return {'status': fetched['status'], 'launch': launched, 'fetch': fetched}


__all__ = ['JOB_LEDGER', 'JobAccess', 'ROUTE_MEMBERS', 'RouteRequestError', 'STATES', 'job_handle']
