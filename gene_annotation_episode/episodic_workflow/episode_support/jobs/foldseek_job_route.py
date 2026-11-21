"""The route of ``job_access`` to the Foldseek web server (https://search.foldseek.com): one structure search of one database
with one query structure, the application ``StructureSearch``.

The sibling of ``bvbrc_job_route.BvbrcJobRoute``, built the same way on ``api_job_route.ApiJobRoute``: from the base it
takes the job directory, the one-submission-per-handle record (an intent before the one POST, the service's answer after
it), the provider spacing kept in ``<workspace>/rate.json`` (``spacing``, ``_contact``), ``wait`` and ``cancel``; the
requests are this module's. The server needs no key, no login and no email, and none is sent; every request carries the
one browser-like User-Agent of A102 (``target_model_sources.BROWSER_USER_AGENT``).

The service's protocol (retained as ``forms/application_service_specs/original/StructureSearch.json`` with the server's
documentation beside it; verified 2026-11-21, ``docs/plan/designs/a102_structure_search_episode.md``):

* ``submit``: ``POST /api/ticket``, ``multipart/form-data``: ``q`` the staged structure file, ``database[]`` one database,
  ``mode`` ``tmalign``. Reply ``{"id", "status"}``.
* ``status``: ``GET /api/ticket/{id}``, reply ``{"id", "status"}``, the status one of ``PENDING`` (queued), ``RUNNING``
  (running), ``COMPLETE`` (finished), ``ERROR`` (failed), ``UNKNOWN`` (unknown).
* ``results`` and ``read``: ``GET /api/result/{id}/0``, the JSON result of the one query; the one file of the catalog,
  ``result.json``. It is fetched once into the job's directory and read from there.
* ``cancel``: the service has none; the base class's ``cancel`` is the failed request ``cancel_not_offered_by_the_service``.

**The duration of a job is observed, not the service's own.** The BV-BRC route's status reply carries the service's task
record (``submit_time``, ``completed_time``), which the ledger writer (``bvbrc_job_child.monitor_job``) prefers. The Foldseek
ticket carries no times at all, so this route's status reply has none: the ledger writer then records the seconds from the
launch to the first status that showed the end (``observed_seconds``, ``duration_seconds`` equal to it, ``duration_source``
``first_status_showing_the_end``). That duration includes the wait until the job asked, and is an upper bound of the
search's own time.

The job is ``{'application': 'StructureSearch', 'database', 'query_file'}``: ``database`` a value of ``DATABASES``,
``query_file`` the staged PDB text of the model. The mode is the constant ``MODE`` and is not a field of the job.

Configuration (every part named, nothing has a default): ``service`` (``foldseek``), ``endpoints`` (``{'Foldseek': url}``),
``workspace`` (the local directory of the job records, inside the run directory), ``request_spacing_seconds``,
``poll_spacing_seconds``, ``transport_timeout_seconds``.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from episode_runtime.job_access import RouteRequestError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.protein_structure.target_model_sources import (
    BROWSER_USER_AGENT)

from .api_job_route import (CATALOG_FILE, ENDED, INTENT_FILE, REQUEST_FILE, RESULT_DIRECTORY, STATUS_FILE,
                            SUBMISSION_FILE, ApiJobRoute, _NoRedirect, _entity, _publish, utc_now)

SERVICE = 'foldseek'
CONFIGURATION = ('service', 'endpoints', 'workspace', 'request_spacing_seconds', 'poll_spacing_seconds',
                 'transport_timeout_seconds')
# The databases of the server the route offers, by the value of ``database[]`` (the ``path`` of GET /api/databases).
# Round 1 offers one; 'pdb100' and 'cath50' are verified to exist (a102_services.md, section 3) and are added when their
# round is built, with the name lookup their hits need.
DATABASES = ('afdb-swissprot',)
MODE = 'tmalign'
# The service's ticket states as job states (the states of ``job_access.STATES``).
STATES = {'PENDING': 'queued', 'RUNNING': 'running', 'COMPLETE': 'finished', 'ERROR': 'failed', 'UNKNOWN': 'unknown'}
RESULT_FILE = 'result.json'


def _prepare(job, files):
    """The facts a ``StructureSearch`` request is built from, with the staged structure read: PDB text with at least one
    C-alpha atom. A job that is not of the form raises ``ValueError``."""
    if job['database'] not in DATABASES:
        raise ValueError('foldseek_job_database_invalid')
    data = files[job['query_file']]
    text = data.decode('ascii')
    residues = sum(1 for line in text.splitlines() if line.startswith('ATOM') and line[12:16].strip() == 'CA')
    if residues == 0:
        raise ValueError('foldseek_job_query_is_not_a_pdb_structure_with_c_alpha_atoms')
    return {'database': job['database'], 'mode': MODE, 'query_residues': residues,
            'query_sha256': hashlib.sha256(data).hexdigest(), 'query_bytes': len(data), 'query_pdb': text}


APPLICATIONS = {
    'StructureSearch': {'job': ('application', 'database', 'query_file'), 'prepare': _prepare, 'bulk': 'query_pdb',
                        'result_files': {RESULT_FILE: 'the JSON result of the one query: per database the hits with '
                                                      'their alignments and aligned C-alpha coordinates'}}}


def _multipart(fields, files):
    """The body of a ``multipart/form-data`` request and its content type: ``fields`` ``[(name, text)]``, ``files``
    ``[(name, file name, bytes)]``."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields:
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    for name, filename, data in files:
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                      'Content-Type: application/octet-stream\r\n\r\n' % (boundary, name, filename)).encode()
                     + data + b'\r\n')
    parts.append(('--%s--\r\n' % boundary).encode())
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary


class FoldseekJobRoute(ApiJobRoute):
    """The Foldseek structure searches of one run, below one workspace directory."""

    kind = 'foldseek'

    def __init__(self, configuration, *, resource_id):
        if not isinstance(configuration, dict) or set(configuration) != set(CONFIGURATION):
            raise ValueError('foldseek_route_configuration_requires_exactly:' + ','.join(CONFIGURATION))
        if configuration['service'] != SERVICE:
            raise ValueError('foldseek_route_service_must_be_' + SERVICE)
        endpoints = configuration['endpoints']
        if not isinstance(endpoints, dict) or set(endpoints) != {'Foldseek'}:
            raise ValueError('foldseek_route_endpoints_requires_exactly:Foldseek')
        address = urllib.parse.urlsplit(endpoints['Foldseek'])
        if (address.scheme not in ('http', 'https') or not address.hostname or address.username is not None
                or address.password is not None or address.query or address.fragment):
            raise ValueError('foldseek_route_endpoint_must_be_a_plain_http_address_without_credentials')
        for name in ('request_spacing_seconds', 'poll_spacing_seconds', 'transport_timeout_seconds'):
            if type(configuration[name]) not in (int, float) or not configuration[name] > 0:
                raise ValueError('foldseek_route_' + name + '_must_be_positive')
        if type(resource_id) is not str or not resource_id:
            raise ValueError('foldseek_route_resource_id_must_be_text')
        self.configuration, self.resource_id = json.loads(json.dumps(configuration)), resource_id
        self.workspace = Path(configuration['workspace']).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._opener = urllib.request.build_opener(_NoRedirect())
        self.base_url = endpoints['Foldseek'].rstrip('/')

    def _send(self, method, path, *, body=None, content_type=None):
        """One request to the service and its whole reply, whatever its status: ``{'status', 'content_type', 'body'}``.
        No credential is sent and no redirect is followed."""
        headers = {'User-Agent': BROWSER_USER_AGENT, 'Accept': '*/*'}
        if content_type is not None:
            headers['Content-Type'] = content_type
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers=headers)
        try:
            with self._opener.open(request, timeout=self.configuration['transport_timeout_seconds']) as response:
                return {'status': response.status, 'body': response.read(),
                        'content_type': response.headers.get('Content-Type', 'application/octet-stream')}
        except urllib.error.HTTPError as error:
            return {'status': error.code, 'body': error.read(),
                    'content_type': error.headers.get('Content-Type', 'application/octet-stream')}
        except TimeoutError as error:
            raise RouteRequestError('provider_request_timeout', {'method': method, 'detail': str(error)}) from error
        except OSError as error:
            if isinstance(getattr(error, 'reason', None), TimeoutError):
                raise RouteRequestError('provider_request_timeout', {'method': method,
                                                                     'detail': str(error)}) from error
            raise RouteRequestError('provider_connection_failed', {
                'method': method, 'exception_type': type(error).__name__, 'detail': str(error)}) from error

    def describe(self):
        configuration = self.configuration
        return {'resource_id': self.resource_id, 'kind': self.kind, 'service': SERVICE,
                'applications': sorted(APPLICATIONS), 'base_url': self.base_url, 'authentication': 'none',
                'request_spacing_seconds': configuration['request_spacing_seconds'],
                'poll_spacing_seconds': configuration['poll_spacing_seconds'], 'cancel_offered': False,
                'jobs': {name: list(spec['job']) for name, spec in APPLICATIONS.items()},
                'databases': list(DATABASES), 'mode': MODE, 'states': dict(STATES),
                'duration': 'observed: the service gives no task times',
                'result_files': {name: dict(spec['result_files']) for name, spec in APPLICATIONS.items()}}

    # -- submit ----------------------------------------------------------------------------------------------
    def prepare(self, job, files):
        """The request the job is, with its structure read: a job that is not of the form raises ``ValueError``."""
        if not isinstance(job, dict) or job.get('application') not in APPLICATIONS:
            raise ValueError('foldseek_job_requires_an_application_of:' + ','.join(sorted(APPLICATIONS)))
        spec = APPLICATIONS[job['application']]
        if set(job) != set(spec['job']):
            raise ValueError('foldseek_' + job['application'] + '_job_requires:' + ','.join(spec['job']))
        return {'application': job['application'], **spec['prepare'](job, files)}

    def submit(self, handle, job, files, owner):
        prepared = self.prepare(job, files)
        directory = self._directory(handle)
        adopted = (directory / SUBMISSION_FILE).exists()
        if not adopted:
            if (directory / INTENT_FILE).exists():
                raise RouteRequestError('submission_outcome_unknown', {'job': handle, 'sent': 'unknown'})
            body, content_type = _multipart(
                [('database[]', prepared['database']), ('mode', prepared['mode'])],
                [('q', 'query.pdb', prepared['query_pdb'].encode('ascii'))])
            with self._contact('submit'):
                directory.mkdir(parents=True, exist_ok=True)
                _publish(directory / REQUEST_FILE, {name: prepared[name] for name in prepared if name != 'query_pdb'})
                (directory / INTENT_FILE).touch()
                try:
                    reply = self._send('POST', '/api/ticket', body=body, content_type=content_type)
                except RouteRequestError as error:
                    # The POST may have reached the service: the intent stays, and nothing is sent again.
                    raise RouteRequestError(error.failure['code'], {**error.failure['detail'],
                                                                    'sent': 'unknown'}) from error
                (directory / 'submit.response').write_bytes(reply['body'])
                made = {'outcome': 'refused', 'failure': self._refusal(reply)}
                if made['failure'] is None:
                    try:
                        ticket = json.loads(reply['body'])
                        remote_id, provider_status = ticket['id'], ticket['status']
                        if type(remote_id) is not str or not remote_id or provider_status not in STATES:
                            raise ValueError('ticket_is_not_an_id_and_a_known_status')
                    except (ValueError, KeyError, TypeError) as error:
                        made['failure'] = {'code': 'provider_submission_response_invalid',
                                           'detail': {**_entity(reply), 'reason': type(error).__name__ + ':' + str(error)}}
                    else:
                        made = {'outcome': 'accepted', 'remote_id': remote_id, 'expected_seconds': None,
                                'submitted_at': utc_now(),
                                'reply': {**_entity(reply), 'remote_id': remote_id, 'provider_status': provider_status}}
                _publish(directory / SUBMISSION_FILE, made)
        made = self._recorded(directory / SUBMISSION_FILE)
        if made['outcome'] != 'accepted':
            raise RouteRequestError(made['failure']['code'], {**made['failure']['detail'], 'sent': True})
        request = self._recorded(directory / REQUEST_FILE)
        return {'native': {'service': SERVICE, 'remote_id': made['remote_id'], 'expected_seconds': None,
                           'directory': str(directory), 'request': request},
                'submitted_at': made['submitted_at'], 'adopted': adopted, 'reply': made['reply']}

    # -- status ----------------------------------------------------------------------------------------------
    def status(self, handle, native):
        directory = self._directory(handle)
        known = self._recorded(directory / STATUS_FILE)
        if known is not None and known['state'] in ENDED:
            return {**known, 'reply': {**known['reply'], 'from_record': True}}
        with self._contact('status', native['remote_id']):
            reply = self._send('GET', '/api/ticket/' + urllib.parse.quote(native['remote_id'], safe=''))
        observed_at = utc_now()
        (directory / 'status.response').write_bytes(reply['body'])
        refusal = self._refusal(reply)
        if refusal is not None:
            raise RouteRequestError(refusal['code'], refusal['detail'])
        try:
            ticket = json.loads(reply['body'])
            provider_status = ticket['status']
            if ticket['id'] != native['remote_id'] or provider_status not in STATES:
                raise ValueError('ticket_is_not_the_job_with_a_known_status')
        except (ValueError, KeyError, TypeError) as error:
            raise RouteRequestError('provider_status_response_invalid', {
                **_entity(reply), 'reason': type(error).__name__ + ':' + str(error)}) from error
        state = STATES[provider_status]
        observation = {'state': state, 'result_available': state == 'finished', 'observed_at': observed_at,
                       'reply': {**_entity(reply), 'remote_id': native['remote_id'], 'provider_status': provider_status,
                                 'from_record': False}}
        _publish(directory / STATUS_FILE, observation)
        return observation

    # -- results ---------------------------------------------------------------------------------------------
    def results(self, handle, native):
        directory = self._directory(handle)
        known = self._recorded(directory / STATUS_FILE)
        if known is None or known['state'] != 'finished':
            raise RouteRequestError('results_not_available', {
                'job': handle, 'state': None if known is None else known['state']})
        if not (directory / CATALOG_FILE).exists():
            with self._contact('fetch', native['remote_id']):
                reply = self._send('GET', '/api/result/' + urllib.parse.quote(native['remote_id'], safe='') + '/0')
            (directory / 'result.response').write_bytes(reply['body'])
            refusal = self._refusal(reply)
            if refusal is not None:
                raise RouteRequestError(refusal['code'], refusal['detail'])
            request = self._recorded(directory / REQUEST_FILE)
            try:
                result = json.loads(reply['body'])
                if (result['type'] != 'structuresearch' or result['mode'] != request['mode']
                        or len(result['queries']) != 1
                        or [item['db'] for item in result['results']] != [request['database']]):
                    raise ValueError('result_is_not_the_search_of_this_job')
            except (ValueError, KeyError, TypeError) as error:
                raise RouteRequestError('provider_result_response_invalid', {
                    **_entity(reply), 'reason': type(error).__name__ + ':' + str(error)}) from error
            (directory / RESULT_DIRECTORY).mkdir(exist_ok=True)
            (directory / RESULT_DIRECTORY / RESULT_FILE).write_bytes(reply['body'])
            _publish(directory / CATALOG_FILE, [{'name': RESULT_FILE, 'bytes': len(reply['body']),
                                                 'media_type': 'application/json'}])
        return self._recorded(directory / CATALOG_FILE)

    def read(self, handle, native, name, offset, limit):
        directory = self._directory(handle)
        catalog = self._recorded(directory / CATALOG_FILE)
        if catalog is None or name not in [item['name'] for item in catalog]:
            raise RouteRequestError('result_file_missing', {'job': handle, 'name': name})
        with (directory / RESULT_DIRECTORY / name).open('rb') as stream:
            stream.seek(offset)
            return stream.read(limit)


__all__ = ['APPLICATIONS', 'CONFIGURATION', 'DATABASES', 'FoldseekJobRoute', 'MODE', 'SERVICE', 'STATES']
