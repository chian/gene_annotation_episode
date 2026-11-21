"""The route of ``job_access`` to a public web API whose work is asynchronous: submit, ask status, fetch results.

``ApiJobRoute`` is one resource of the ``JobAccess`` service (``episode_runtime/job_access.py``, which states the
route protocol). A job is one request the service works on after the submission has returned. Every method that
contacts the service makes **one HTTP request**; nothing here loops, retries or follows a redirect, except
``wait``, which is the explicit wait of a unit that asked for one. The route sends no credential of any kind: no
login, token, cookie or ``Authorization`` header. It is for services that answer anyone.

The service's own protocol is a **protocol object** of this module (``PROTOCOLS``, by service name): it says what
a job is, builds the three requests and reads the three replies. One is written, ``NcbiBlastUrlApi``: the NCBI
BLAST Common URL API (``CMD=Put``; ``CMD=Get`` with ``FORMAT_OBJECT=SearchInfo``; ``CMD=Get`` with
``FORMAT_TYPE=JSON2``). It reads the replies with the library's own BLAST protocol functions
(``tools/similarity_search/blast_search.py``: ``submission``, ``status``, ``document``, ``validate_identity``) and
the query with the library's sequence parser; no reading of a reply is written a second time here.

**At most one submission per handle.** The job's directory is ``<workspace>/<handle>``. The handle comes from the
launching unit's operation key, so a unit that runs again names the same directory. ``submit`` writes its intent
(``submitting``) before the one POST and the service's answer (``submission.json``) after it:

- a recorded answer is returned as it was (``adopted``); a recorded refusal is raised again; nothing is sent;
- an intent without an answer means the POST may have reached the service: the request fails with
  ``submission_outcome_unknown`` and nothing is sent a second time on a guess.

The job's records are found by its handle below the workspace the route is configured with. A workspace that was
moved or copied (with its Store, to go on with a job in another run directory) therefore serves the jobs recorded
in it, and its copied ``submission.json`` keeps the job from being submitted again; the directory a handoff row
recorded at launch (``native['directory']``) is not compared.

**The provider's spacing rules are kept, not waited for.** The service's documented minimum time between two
contacts (``request_spacing_seconds``) and between two status requests of one remote job
(``poll_spacing_seconds``) are kept in ``<workspace>/rate.json`` under a file lock, shared by every process that
uses the workspace. A request that would come too early is not sent: it fails with ``provider_spacing_required``
and says when it may be sent (``retry_after_seconds``, ``earliest_at``). Only ``wait`` sleeps.

**What is known is not asked again.** A status that ended the job (``finished``, ``failed``) is recorded and
answered from the record. The results are fetched once into the job's directory and read from there.

A request that cannot be made, or that the service refuses, raises ``RouteRequestError``: ``job_access`` returns
it as the failed outcome of the tool unit. The service has no cancel operation: ``cancel`` is such a failure.

Configuration (every part named, nothing has a default): ``service`` (a name of ``PROTOCOLS``), ``base_url``,
``workspace``, ``client_name`` (the name this client gives the service), ``contact_email`` (the contact address
the caller chose to give the service, or ``None``: then none is sent), ``request_spacing_seconds``,
``poll_spacing_seconds``, ``transport_timeout_seconds`` (the socket timeout of one HTTP request).
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from episode_runtime.job_access import RouteRequestError

from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    parse_sequences)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search import blast_search as blast

CONFIGURATION = ('service', 'base_url', 'workspace', 'client_name', 'contact_email', 'request_spacing_seconds',
                 'poll_spacing_seconds', 'transport_timeout_seconds')
ENDED = ('finished', 'failed')
SPACING = 'provider_spacing_required'
REQUEST_FILE, INTENT_FILE, SUBMISSION_FILE, STATUS_FILE, CATALOG_FILE = (
    'request.json', 'submitting', 'submission.json', 'status.json', 'results.json')
RESULT_DIRECTORY, RATE_FILE = 'results', 'rate.json'
_INFO = re.compile(r'QBlastInfoBegin(.*?)QBlastInfoEnd', re.S)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _publish(path, value):
    """Write ``value`` as the whole of ``path`` or not at all."""
    pending = path.with_name(path.name + '.writing')
    with pending.open('w') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)


def _entity(reply):
    return {'http_status': reply['status'], 'content_type': reply['content_type'], 'bytes': len(reply['body']),
            'sha256': hashlib.sha256(reply['body']).hexdigest()}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class NcbiBlastUrlApi:
    """The NCBI BLAST Common URL API: one search of one query sequence against one database.

    A job is ``{'program', 'database', 'hitlist_size', 'query_file'}``: ``query_file`` names the staged input that
    holds the query, either the residues alone or one FASTA record. The service's states are kept as it gives them
    (``provider_status``) and mapped to the job states of ``job_access``: ``WAITING`` (an accepted, unfinished
    search; the service does not say whether it has begun) is ``queued``, ``READY`` is ``finished`` (also when
    there are no hits), ``FAILED`` is ``failed``, ``UNKNOWN`` (the service does not know the job, or no longer)
    is ``unknown``."""

    service = 'ncbi_blast'
    JOB = ('program', 'database', 'hitlist_size', 'query_file')
    STATES = {'WAITING': 'queued', 'READY': 'finished', 'FAILED': 'failed', 'UNKNOWN': 'unknown'}
    REQUEST_SCHEMA = {
        'type': 'object', 'additionalProperties': False, 'required': ['program', 'database', 'hitlist_size'],
        'properties': {
            'program': {'type': 'string', 'enum': sorted(blast.PROGRAM_UNITS),
                        'description': 'The BLAST program; it must take a query of the assigned molecule'},
            'database': {'type': 'string', 'pattern': '^[A-Za-z0-9_./-]+$',
                         'description': "The name of one of the service's databases, as the service spells it"},
            'hitlist_size': {'type': 'integer', 'minimum': 1,
                             'description': 'The largest number of database sequences to report'}}}

    def describe(self):
        return {'protocol': 'NCBI BLAST Common URL API', 'job': list(self.JOB),
                'request_schema': json.loads(json.dumps(self.REQUEST_SCHEMA)),
                'staged_inputs': {'query_file': 'the one query sequence: its residues, or one FASTA record'},
                'query_unit_by_program': {name: units[0] for name, units in sorted(blast.PROGRAM_UNITS.items())},
                'result_files': {'blast_result.json': 'the single-query JSON2 report',
                                 'blast_result.json2.zip': 'the archive the service sent, when it sent one'},
                'states': dict(self.STATES)}

    def prepare(self, job, files):
        """The request the job is, with its query read: a job that is not of the form raises ``ValueError``."""
        if not isinstance(job, dict) or set(job) != set(self.JOB):
            raise ValueError('ncbi_blast_job_requires_exactly:' + ','.join(self.JOB))
        if (job['program'] not in blast.PROGRAM_UNITS or type(job['database']) is not str
                or re.fullmatch(self.REQUEST_SCHEMA['properties']['database']['pattern'], job['database']) is None
                or type(job['hitlist_size']) is not int or job['hitlist_size'] < 1):
            raise ValueError('ncbi_blast_job_program_database_or_hitlist_size_invalid')
        text = files[job['query_file']].decode('ascii')
        records = parse_sequences(text, format='fasta' if text.lstrip().startswith('>') else 'raw', name='query')
        if len(records) != 1:
            raise ValueError('ncbi_blast_job_requires_a_single_query_sequence')
        query = records[0]
        return {'program': job['program'], 'database': job['database'], 'hitlist_size': job['hitlist_size'],
                'query_title': query.name, 'query_length': len(query.sequence),
                'sequence_sha256': hashlib.sha256(query.sequence.encode()).hexdigest(),
                'query_fasta': '>' + query.name + '\n' + query.sequence + '\n'}

    @staticmethod
    def submission_request(prepared):
        return 'POST', {'CMD': 'Put', 'PROGRAM': prepared['program'], 'DATABASE': prepared['database'],
                        'QUERY': prepared['query_fasta'], 'FORMAT_TYPE': 'Text',
                        'HITLIST_SIZE': prepared['hitlist_size']}

    @staticmethod
    def read_submission(body):
        """``(remote id, the service's estimate of seconds to completion or None)``; ``ValueError`` without an id."""
        return blast.submission(body)

    @staticmethod
    def status_request(remote_id):
        return 'GET', {'CMD': 'Get', 'FORMAT_OBJECT': 'SearchInfo', 'RID': remote_id}

    def read_status(self, body):
        read = blast.status(body)
        return {'state': self.STATES[read['status']], 'provider_status': read['status'], 'has_hits': read['has_hits']}

    @staticmethod
    def result_request(remote_id):
        return 'GET', {'CMD': 'Get', 'RID': remote_id, 'FORMAT_TYPE': 'JSON2'}

    @staticmethod
    def read_result(body, prepared):
        """The result files of a fetched reply, ``[(name, media type, bytes)]``: the report of the one query as
        the service wrote it, and the archive when the service sent one. A reply that is not the report of this
        job's program and query raises ``ValueError``."""
        parsed = blast.document(body)
        blast.validate_identity(parsed, {'algorithm': prepared['program'], 'subject_ref': prepared['query_title'],
                                         'query_length': prepared['query_length']})
        found = [('blast_result.json', 'application/json', parsed['json_bytes'])]
        if parsed['member'] is not None:
            found.append(('blast_result.json2.zip', 'application/zip', body))
        return found

    @staticmethod
    def information(body):
        """The protocol lines of a reply (what stands between ``QBlastInfoBegin`` and ``QBlastInfoEnd``)."""
        return [line.strip() for block in _INFO.findall(body.decode('utf-8', 'replace'))
                for line in block.splitlines() if line.strip()]


PROTOCOLS = {NcbiBlastUrlApi.service: NcbiBlastUrlApi}


class ApiJobRoute:
    """The jobs of one public web service, below one workspace directory."""

    kind = 'api'

    def __init__(self, configuration, *, resource_id):
        if not isinstance(configuration, dict) or set(configuration) != set(CONFIGURATION):
            raise ValueError('api_route_configuration_requires_exactly:' + ','.join(CONFIGURATION))
        if configuration['service'] not in PROTOCOLS:
            raise ValueError('api_route_service_has_no_protocol:' + str(configuration['service']))
        address = urllib.parse.urlsplit(configuration['base_url'])
        if (address.scheme not in ('http', 'https') or not address.hostname or address.username is not None
                or address.password is not None or address.query or address.fragment):
            raise ValueError('api_route_base_url_must_be_a_plain_http_address_without_credentials')
        if type(configuration['client_name']) is not str or not configuration['client_name'].strip():
            raise ValueError('api_route_client_name_must_be_text')
        if configuration['contact_email'] is not None and type(configuration['contact_email']) is not str:
            raise ValueError('api_route_contact_email_must_be_text_or_none')
        for name in ('request_spacing_seconds', 'poll_spacing_seconds', 'transport_timeout_seconds'):
            if type(configuration[name]) not in (int, float) or not configuration[name] > 0:
                raise ValueError('api_route_' + name + '_must_be_positive')
        if type(resource_id) is not str or not resource_id:
            raise ValueError('api_route_resource_id_must_be_text')
        self.configuration, self.resource_id = json.loads(json.dumps(configuration)), resource_id
        self.protocol = PROTOCOLS[configuration['service']]()
        self.workspace = Path(configuration['workspace']).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._opener = urllib.request.build_opener(_NoRedirect())

    def describe(self):
        configuration = self.configuration
        return {'resource_id': self.resource_id, 'kind': self.kind, 'service': configuration['service'],
                'base_url': configuration['base_url'], 'authentication': 'none',
                'contact_configured': configuration['contact_email'] is not None,
                'request_spacing_seconds': configuration['request_spacing_seconds'],
                'poll_spacing_seconds': configuration['poll_spacing_seconds'], 'cancel_offered': False,
                **self.protocol.describe()}

    # -- the job's directory ---------------------------------------------------------------------------------
    def _directory(self, handle):
        return self.workspace / handle

    @staticmethod
    def _recorded(path):
        return json.loads(path.read_text()) if path.exists() else None

    # -- the provider's spacing ------------------------------------------------------------------------------
    def _remaining(self, state, action, remote_id):
        now, configuration = time.time(), self.configuration
        remaining = configuration['request_spacing_seconds'] - (now - state['last_request'])
        if action == 'status' and remote_id in state['polls']:
            remaining = max(remaining, configuration['poll_spacing_seconds'] - (now - state['polls'][remote_id]))
        return max(0.0, remaining)

    def spacing(self, action, remote_id=None):
        """Seconds until a contact of ``action`` (``submit``, ``status``, ``fetch``) may be sent; 0.0 when now."""
        with (self.workspace / RATE_FILE).open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_SH)
            stream.seek(0)
            state = json.loads(stream.read() or '{"last_request": 0, "polls": {}}')
        return self._remaining(state, action, remote_id)

    @contextmanager
    def _contact(self, action, remote_id=None):
        """One permitted contact. The lock is held until the contact has ended and its end is the time the next
        one is spaced from, so a slow request does not make its start look like an old contact."""
        with (self.workspace / RATE_FILE).open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            state = json.loads(stream.read() or '{"last_request": 0, "polls": {}}')
            remaining = self._remaining(state, action, remote_id)
            if remaining > 0:
                raise RouteRequestError(SPACING, {
                    'action': action, 'sent': False, 'retry_after_seconds': remaining,
                    'earliest_at': (datetime.now(timezone.utc) + timedelta(seconds=remaining)).isoformat()})
            try:
                yield
            finally:
                state['last_request'] = time.time()
                if action == 'status':
                    state['polls'][remote_id] = state['last_request']
                stream.seek(0)
                stream.truncate()
                json.dump(state, stream)
                stream.flush()
                os.fsync(stream.fileno())

    # -- one HTTP request ------------------------------------------------------------------------------------
    def _send(self, method, fields):
        """One request to the service and its whole reply, whatever its status: ``{'status', 'content_type',
        'body'}``. No credential is sent and no redirect is followed."""
        configuration = self.configuration
        fields = {**fields, 'tool': configuration['client_name']}
        if configuration['contact_email'] is not None:
            fields['email'] = configuration['contact_email']
        encoded = urllib.parse.urlencode(fields)
        url = configuration['base_url'] + ('?' + encoded if method == 'GET' else '')
        request = urllib.request.Request(url, data=encoded.encode() if method == 'POST' else None, method=method,
                                         headers={'User-Agent': configuration['client_name'], 'Accept': '*/*'})
        try:
            with self._opener.open(request, timeout=configuration['transport_timeout_seconds']) as response:
                return {'status': response.status, 'body': response.read(),
                        'content_type': response.headers.get('Content-Type', 'application/octet-stream')}
        except urllib.error.HTTPError as error:
            return {'status': error.code, 'body': error.read(),
                    'content_type': error.headers.get('Content-Type', 'application/octet-stream')}
        except TimeoutError as error:
            raise RouteRequestError('provider_request_timeout', {'method': method, 'detail': str(error)}) from error
        except OSError as error:        # urllib.error.URLError and the socket errors below it
            if isinstance(getattr(error, 'reason', None), TimeoutError):
                raise RouteRequestError('provider_request_timeout', {'method': method,
                                                                     'detail': str(error)}) from error
            raise RouteRequestError('provider_connection_failed', {
                'method': method, 'exception_type': type(error).__name__, 'detail': str(error)}) from error

    @staticmethod
    def _refusal(reply):
        """The failure an HTTP reply is when the service did not answer the request: ``None`` for status 200."""
        if reply['status'] == 200:
            return None
        code = ('provider_redirect_not_followed' if 300 <= reply['status'] < 400
                else 'provider_http_' + str(reply['status']))
        return {'code': code, 'detail': _entity(reply)}

    # -- submit ----------------------------------------------------------------------------------------------
    def submit(self, handle, job, files, owner):
        prepared = self.protocol.prepare(job, files)
        directory = self._directory(handle)
        adopted = (directory / SUBMISSION_FILE).exists()
        if not adopted:
            if (directory / INTENT_FILE).exists():
                raise RouteRequestError('submission_outcome_unknown', {'job': handle, 'sent': 'unknown'})
            method, fields = self.protocol.submission_request(prepared)
            with self._contact('submit'):
                directory.mkdir(parents=True, exist_ok=True)
                _publish(directory / REQUEST_FILE, prepared)
                (directory / INTENT_FILE).touch()
                try:
                    reply = self._send(method, fields)
                except RouteRequestError as error:
                    # The POST may have reached the service: the intent stays, and nothing is sent again.
                    raise RouteRequestError(error.failure['code'], {**error.failure['detail'],
                                                                    'sent': 'unknown'}) from error
                (directory / 'submit.response').write_bytes(reply['body'])
                made = {'outcome': 'refused', 'failure': self._refusal(reply)}
                if made['failure'] is None:
                    try:
                        remote_id, expected = self.protocol.read_submission(reply['body'])
                    except ValueError as error:
                        made['failure'] = {'code': 'provider_submission_response_invalid',
                                           'detail': {**_entity(reply), 'reason': str(error),
                                                      'information': self.protocol.information(reply['body'])}}
                    else:
                        made = {'outcome': 'accepted', 'remote_id': remote_id, 'expected_seconds': expected,
                                'submitted_at': utc_now(),
                                'reply': {**_entity(reply), 'remote_id': remote_id, 'expected_seconds': expected,
                                          'information': self.protocol.information(reply['body'])}}
                _publish(directory / SUBMISSION_FILE, made)
        made = self._recorded(directory / SUBMISSION_FILE)
        if made['outcome'] != 'accepted':
            raise RouteRequestError(made['failure']['code'], {**made['failure']['detail'], 'sent': True})
        return {'native': {'service': self.configuration['service'], 'remote_id': made['remote_id'],
                           'expected_seconds': made['expected_seconds'], 'directory': str(directory),
                           'request': {name: prepared[name] for name in prepared if name != 'query_fasta'}},
                'submitted_at': made['submitted_at'], 'adopted': adopted, 'reply': made['reply']}

    # -- status ----------------------------------------------------------------------------------------------
    def status(self, handle, native):
        directory = self._directory(handle)
        known = self._recorded(directory / STATUS_FILE)
        if known is not None and known['state'] in ENDED:
            return {**known, 'reply': {**known['reply'], 'from_record': True}}
        method, fields = self.protocol.status_request(native['remote_id'])
        with self._contact('status', native['remote_id']):
            reply = self._send(method, fields)
        observed_at = utc_now()
        (directory / 'status.response').write_bytes(reply['body'])
        refusal = self._refusal(reply)
        if refusal is not None:
            raise RouteRequestError(refusal['code'], refusal['detail'])
        try:
            read = self.protocol.read_status(reply['body'])
        except ValueError as error:
            raise RouteRequestError('provider_status_response_invalid', {
                **_entity(reply), 'reason': str(error)}) from error
        observation = {'state': read['state'], 'result_available': read['state'] == 'finished',
                       'observed_at': observed_at,
                       'reply': {**_entity(reply), 'remote_id': native['remote_id'],
                                 'provider_status': read['provider_status'], 'has_hits': read['has_hits'],
                                 'information': self.protocol.information(reply['body']), 'from_record': False}}
        _publish(directory / STATUS_FILE, observation)
        return observation

    async def wait(self, handle, native):
        """Return when the job has ended and the service may be contacted again (so the results can be fetched):
        one status request at a time, each when the provider's spacing permits it, the first not before the
        service's own estimate of the job's duration. No deadline."""
        directory = self._directory(handle)
        made = self._recorded(directory / SUBMISSION_FILE)
        expected = datetime.fromisoformat(made['submitted_at']) + timedelta(seconds=made['expected_seconds'] or 0)
        while True:
            remaining = self.spacing('status', native['remote_id'])
            if self._recorded(directory / STATUS_FILE) is None:
                remaining = max(remaining, (expected - datetime.now(timezone.utc)).total_seconds())
            if remaining > 0:
                await asyncio.sleep(remaining)
            try:
                status = self.status(handle, native)
            except RouteRequestError as error:
                if error.failure['code'] == SPACING:        # another user of the workspace came first
                    continue
                raise
            if status['state'] in ENDED:
                await asyncio.sleep(self.spacing('fetch'))
                return
            if status['state'] == 'unknown':
                raise RouteRequestError('job_state_unknown', status['reply'])

    # -- results ---------------------------------------------------------------------------------------------
    def results(self, handle, native):
        directory = self._directory(handle)
        known = self._recorded(directory / STATUS_FILE)
        if known is None or known['state'] != 'finished':
            raise RouteRequestError('results_not_available', {
                'job': handle, 'state': None if known is None else known['state']})
        if not (directory / CATALOG_FILE).exists():
            method, fields = self.protocol.result_request(native['remote_id'])
            with self._contact('fetch', native['remote_id']):
                reply = self._send(method, fields)
            (directory / 'result.response').write_bytes(reply['body'])
            refusal = self._refusal(reply)
            if refusal is not None:
                raise RouteRequestError(refusal['code'], refusal['detail'])
            try:
                found = self.protocol.read_result(reply['body'], self._recorded(directory / REQUEST_FILE))
            except (ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
                raise RouteRequestError('provider_result_response_invalid', {
                    **_entity(reply), 'reason': type(error).__name__ + ':' + str(error)}) from error
            (directory / RESULT_DIRECTORY).mkdir(exist_ok=True)
            for name, _media_type, data in found:
                (directory / RESULT_DIRECTORY / name).write_bytes(data)
            _publish(directory / CATALOG_FILE, [{'name': name, 'bytes': len(data), 'media_type': media_type}
                                                for name, media_type, data in found])
        return self._recorded(directory / CATALOG_FILE)

    def read(self, handle, native, name, offset, limit):
        directory = self._directory(handle)
        catalog = self._recorded(directory / CATALOG_FILE)
        if catalog is None or name not in [item['name'] for item in catalog]:
            raise RouteRequestError('result_file_missing', {'job': handle, 'name': name})
        with (directory / RESULT_DIRECTORY / name).open('rb') as stream:
            stream.seek(offset)
            return stream.read(limit)

    # -- cancel ----------------------------------------------------------------------------------------------
    def cancel(self, handle, native):
        raise RouteRequestError('cancel_not_offered_by_the_service', {
            'job': handle, 'service': self.configuration['service'], 'remote_id': native['remote_id']})


__all__ = ['ApiJobRoute', 'CONFIGURATION', 'NcbiBlastUrlApi', 'PROTOCOLS', 'SPACING']
