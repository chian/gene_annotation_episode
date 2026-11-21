"""The route of ``job_access`` to the BV-BRC application service: one job of an application of ``APPLICATIONS``
(``Homology``: a BLAST search of one query against a precomputed BV-BRC database; ``MSA``: a multiple sequence
alignment of protein sequences), run on the owner's BV-BRC account.

One route and one table of applications. Every application shares ``AppService.start_app2``, ``AppService.query_tasks``,
the Workspace result calls, the spacing and the one-submission-per-handle record; an application is an entry of
``APPLICATIONS``: the keys of its job (``job``, always led by ``application``), ``prepare`` (the job and its staged
files to the facts the request is built from), ``parameters`` (the application's parameters from those facts and the
job's folder), ``output_file`` (the basename of the result files), ``bulk`` (the prepared fact that holds the staged text,
kept out of the job's native request) and ``result_files`` (what the application writes, for ``describe``). A child that
needs another application adds an entry; nothing else of the route changes.

``BvbrcJobRoute`` is one resource of the ``JobAccess`` service (``episode_runtime/job_access.py`` states the route
protocol). It is the authenticated sibling of ``api_job_route.ApiJobRoute``, which sends no credential and stays that
way. The login is read by the existing transport, ``BVBRCAnalysisClient``
(``acquisition/service_calls/gene_context_evidence/bvbrc_analysis_transport.py``), from the environment variable the
configuration names (``authorization_env``): the configuration never holds the token, and the client sends it only to
the configured service origins. Nothing here prints, stores or returns it.

What exists and is called, not written again: the transport (``BVBRCAnalysisClient``), the RPC preparation and decoding
(``prepare_rpc_request``, ``decode_rpc_response``), the task and Workspace record readers (``parse_task_records``,
``parse_workspace_records``), the application preparation (``prepare_application``: the retained ``Homology``
definition), the sequence parser, and from ``ApiJobRoute`` the provider spacing kept in ``<workspace>/rate.json``
(``spacing``, ``_contact``), the job directory, the atomic record write and ``wait`` (inherited, unchanged). Every method
that contacts the service is replaced here; ``_send`` of the public route is made unreachable.

The ``Homology`` job is ``{'application', 'program', 'database', 'query_file'}``: ``database`` is a name of
``PRECOMPUTED_DATABASES`` (a value of the application's ``db_precomputed_database`` with ``db_source``
``precomputed_database``), ``query_file`` the staged query. The ``MSA`` job is ``{'application', 'aligner', 'alphabet',
'sequences_file'}``: ``sequences_file`` the staged FASTA (at least two sequences), sent as the application's
``fasta_keyboard_input`` with ``input_type`` ``input_sequence``.
The ``MetaCATS`` job is ``{'application', 'p_value', 'alignment_file', 'group_file'}``: the staged aligned FASTA and group
file are created in the job's own folder (an entry's ``uploads``) and the job takes their workspace paths with
``input_type`` ``files`` (the service takes a workspace path of the same account; nothing is uploaded elsewhere).

* ``submit``: finds the home workspace of the login in the service (the listing of ``/``: the one workspace named
  ``home`` the login owns), creates ONE folder for the job under ``<home>/<root_folder>/<handle>`` (the owner's folder
  of this work; the application writes its result files below it, in the folder ``.<output_file>`` it makes) and starts
  the job's application with ``AppService.start_app2``. At most one submission per handle (an intent file before the first
  contact that writes, the service's answer after): an intent without an answer is ``submission_outcome_unknown``.
* ``status``: ``AppService.query_tasks`` for the task, the application's state mapped to a job state.
* ``results``: the files of the result folder (a Workspace listing; each entry also names ``workspace_path``, where the
  file lies in the BV-BRC workspace); ``read``: one file by its download address (``Workspace.get_download_url``, then
  the download), kept in the job's directory. The address is never kept.

The provider spacing is kept by sleeping before a contact that is part of one operation (a submission, a fetch has
several), and by refusing a status request that would come too early (``provider_spacing_required``: nothing sent). A
refusal of the service (an HTTP error status) keeps the service's own JSON-RPC error in the failure detail; other
failures use the codes of ``database_blast_search.FAILURE_CODES``.

Configuration (every part named, nothing has a default): ``service`` (``bvbrc_blast``), ``endpoints``
(``{'AppService': url, 'Workspace': url}``), ``authorization_env``, ``workspace`` (the local directory of the job
records), ``root_folder`` (the one folder of the home workspace this work writes to), ``request_spacing_seconds``,
``poll_spacing_seconds``, ``transport_timeout_seconds``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import time

from episode_runtime.job_access import RouteRequestError

from gene_annotation_episode.episodic_workflow.episode_support.acquisition.gene_context_evidence.acquisition import (
    AcquisitionError)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_analysis_protocol import (
    decode_rpc_response, parse_task_records, parse_workspace_records, prepare_rpc_request)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.bvbrc_application_definitions import (
    prepare_application)
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.gene_context_evidence.bvbrc_analysis_transport import (
    BVBRCAnalysisClient)
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import (
    parse_sequences)
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search import blast_search as blast
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.bvbrc_metacats_analysis import (
    ALIGNMENT_FILE, CHISQ_FILE, GROUP_FILE, GROUP_HEADER, MC_FILE, MINIMUM_GROUPS, P_VALUES as METACATS_P_VALUES,
    parse_alignment)

from .api_job_route import (CATALOG_FILE, ENDED, INTENT_FILE, REQUEST_FILE, RESULT_DIRECTORY, SPACING,
                            STATUS_FILE, SUBMISSION_FILE, ApiJobRoute, _publish, utc_now)

SERVICE = 'bvbrc_blast'
CONFIGURATION = ('service', 'endpoints', 'authorization_env', 'workspace', 'root_folder', 'request_spacing_seconds',
                 'poll_spacing_seconds', 'transport_timeout_seconds')
# The precomputed protein databases the route offers, by the value of ``db_precomputed_database``: the application's
# ``db_type``, the unit of its sequences and the file name the report names as its database (``search_target.db``,
# the last path component).
PRECOMPUTED_DATABASES = {
    'bacteria-archaea': {'db_type': 'faa', 'unit': 'aa', 'database_file': 'bacteria-archaea.features.faa'}}
FEATURE_GROUP = 'hits'
MSA_ALIGNERS = ('Muscle',)
MSA_ALPHABETS = ('protein',)
SPECS = Path(__file__).parents[1] / 'forms' / 'application_service_specs' / 'original'
# The service's task states (``query_tasks``: the ``status`` field) as job states.
STATES = {'queued': 'queued', 'pending': 'queued', 'running': 'running', 'in-progress': 'running',
          'completed': 'finished', 'failed': 'failed', 'deleted': 'failed'}
MEDIA_TYPES = {'json': 'application/json', 'txt': 'text/plain'}
HOME_FILE, RESULT_OBJECTS_FILE = 'home.json', 'result_objects.json'
_ROOT = re.compile(r'[A-Za-z0-9_.-]+')


def _entity(snapshot):
    return {'http_status': snapshot.transport['status'], 'content_type': snapshot.media_type,
            'bytes': len(snapshot.content), 'sha256': hashlib.sha256(snapshot.content).hexdigest()}


def refusal(error):
    """The route failure an ``AcquisitionError`` of the transport is. An HTTP error status keeps the service's JSON-RPC
    error (its name, code and message: what the service objects to); a failure to reach the service is a connection or
    timeout failure. Any other error (the login unavailable, an origin not configured) is the caller's configuration
    and is not a request failure: it is not converted."""
    snapshot = error.snapshot
    if error.code.startswith('bvbrc_http_'):
        detail = _entity(snapshot)
        try:
            body = json.loads(snapshot.content).get('error')
        except (ValueError, AttributeError):
            body = None
        if isinstance(body, dict):
            detail['rpc_error'] = {name: body.get(name) for name in ('name', 'code', 'message')
                                   if isinstance(body.get(name), (str, int))}
        return RouteRequestError('provider_http_' + error.code.removeprefix('bvbrc_http_'), detail)
    if error.code == 'bvbrc_redirect_not_followed':
        return RouteRequestError('provider_redirect_not_followed', _entity(snapshot))
    if error.code == 'bvbrc_native_transport_failed':
        kind = (error.diagnostic or {}).get('exception_type')
        return RouteRequestError('provider_request_timeout' if kind == 'TimeoutError' else 'provider_connection_failed',
                                 {'exception_type': kind})
    if error.code.startswith('bvbrc_response_'):
        return RouteRequestError('provider_connection_failed', {'reason': error.code})
    raise error


def _homology_prepare(job, files):
    """The facts a ``Homology`` request is built from, with the query read: a job that is not of the form raises
    ``ValueError``."""
    if job['program'] not in blast.PROGRAM_UNITS or job['database'] not in PRECOMPUTED_DATABASES:
        raise ValueError('bvbrc_blast_job_program_or_database_invalid')
    units = blast.PROGRAM_UNITS[job['program']]
    if units[1] != PRECOMPUTED_DATABASES[job['database']]['unit']:
        raise ValueError('bvbrc_blast_job_database_does_not_hold_what_the_program_searches')
    text = files[job['query_file']].decode('ascii')
    records = parse_sequences(text, format='fasta' if text.lstrip().startswith('>') else 'raw', name='query')
    if len(records) != 1:
        raise ValueError('bvbrc_blast_job_requires_a_single_query_sequence')
    query = records[0]
    return {'program': job['program'], 'database': job['database'], 'query_title': query.name,
            'query_length': len(query.sequence), 'input_type': 'aa' if units[0] == 'aa' else 'dna',
            'sequence_sha256': hashlib.sha256(query.sequence.encode()).hexdigest(),
            'query_fasta': '>' + query.name + '\n' + query.sequence + '\n'}


def _homology_parameters(prepared, folder, output_file):
    catalog = PRECOMPUTED_DATABASES[prepared['database']]
    return {'input_type': prepared['input_type'], 'input_source': 'fasta_data',
            'input_fasta_data': prepared['query_fasta'], 'db_type': catalog['db_type'],
            'db_source': 'precomputed_database', 'db_precomputed_database': prepared['database'],
            'blast_program': prepared['program'], 'output_path': folder, 'output_file': output_file}


def _msa_prepare(job, files):
    """The facts an ``MSA`` request is built from, with the sequences read: at least two protein sequences with distinct
    names, of the aligner and alphabet the route offers."""
    if job['aligner'] not in MSA_ALIGNERS or job['alphabet'] not in MSA_ALPHABETS:
        raise ValueError('bvbrc_msa_job_aligner_or_alphabet_invalid')
    text = files[job['sequences_file']].decode('ascii')
    records = parse_sequences(text, format='fasta', name='sequence')
    ids = [] if 'feature_group_file' not in job else json.loads(files[job['feature_group_file']])['feature_ids']
    if (len(records) + len(ids) < 2 or len({record.name for record in records}) != len(records)
            or len(set(ids)) != len(ids) or not all(isinstance(item, str) and item for item in ids)):
        raise ValueError('bvbrc_msa_job_requires_two_or_more_sequences_with_distinct_names')
    return {'aligner': job['aligner'], 'alphabet': job['alphabet'], 'sequence_count': len(records),
            'residues': sum(len(record.sequence) for record in records), 'feature_ids': ids,
            'sequences_sha256': hashlib.sha256(text.encode()).hexdigest(), 'sequences_fasta': text}


def _msa_parameters(prepared, folder, output_file):
    """Pasted FASTA alone: ``input_sequence``. With a feature group (its path is ``folder`` + ``/`` + ``FEATURE_GROUP``)
    the group and the pasted FASTA are given together: ``input_group``."""
    group = {'input_type': 'input_group', 'feature_groups': [folder + '/' + FEATURE_GROUP]} if prepared['feature_ids'] else {
        'input_type': 'input_sequence'}
    return {**group, 'alphabet': prepared['alphabet'], 'aligner': prepared['aligner'],
            'fasta_keyboard_input': prepared['sequences_fasta'], 'output_path': folder, 'output_file': output_file}


def _metacats_prepare(job, files):
    """The facts a ``MetaCATS`` request is built from, with its two staged files read: the aligned FASTA and the group file
    (a header line, then one ``identifier<TAB>label`` line per sequence); every sequence of the alignment is in a group
    (the service makes a sequence of no group a group of its own), at least two groups."""
    if job['p_value'] not in METACATS_P_VALUES:
        raise ValueError('bvbrc_metacats_job_p_value_invalid')
    alignment, groups = (files[job[name]].decode('ascii') for name in ('alignment_file', 'group_file'))
    rows = parse_alignment(alignment)
    lines = [line.split('\t') for line in groups.splitlines()[1:]]
    labels = {label for _, label in lines}
    if (groups.splitlines()[0] != 'Seq_ID\t' + GROUP_HEADER or any(len(line) != 2 for line in lines)
            or sorted(name for name, _ in lines) != sorted(name for name, _ in rows) or len(labels) < MINIMUM_GROUPS):
        raise ValueError('bvbrc_metacats_job_requires_every_sequence_of_the_alignment_in_one_of_two_or_more_groups')
    return {'p_value': job['p_value'], 'sequence_count': len(rows), 'group_count': len(labels),
            'columns': len(rows[0][1]), 'alignment_sha256': hashlib.sha256(alignment.encode()).hexdigest(),
            'groups_sha256': hashlib.sha256(groups.encode()).hexdigest(),
            'staged': {'alignment': alignment, 'groups': groups}}


def _metacats_parameters(prepared, folder, output_file):
    return {'input_type': 'files', 'alphabet': 'aa', 'alignment_type': 'aligned_protein_fasta',
            'alignment_file': folder + '/' + ALIGNMENT_FILE, 'group_file': folder + '/' + GROUP_FILE,
            'p_value': prepared['p_value'], 'output_path': folder, 'output_file': output_file}


def _metacats_uploads(prepared, folder):
    """The two input files, created in the job's own folder (as the Workspace takes them: type and the text itself)."""
    return [[folder + '/' + ALIGNMENT_FILE, 'aligned_protein_fasta', {}, prepared['staged']['alignment']],
            [folder + '/' + GROUP_FILE, 'tsv', {}, prepared['staged']['groups']]]


def native_params(application, parameters):
    """The ``start_app2`` operands of ``application`` with ``parameters``, checked against the retained definition of the
    application (``forms/application_service_specs/original/<application>.json``, the service's own app spec): every
    parameter is declared by it, an enum parameter takes a declared value and every required parameter is given. The
    ``Homology`` entry goes through ``prepare_application`` instead (it holds the checks of that application)."""
    definition = json.loads((SPECS / (application + '.json')).read_text())
    declared = {item['id']: item for item in definition['parameters']}
    unknown = sorted(set(parameters) - set(declared))
    missing = sorted(name for name, item in declared.items() if item.get('required') == 1 and name not in parameters)
    wrong = sorted(name for name, value in parameters.items() if 'enum' in declared.get(name, {})
                   and value not in declared[name]['enum'])
    if unknown or missing or wrong:
        raise ValueError('bvbrc_' + application + '_application_request_invalid:' + repr(
            {'unknown': unknown, 'missing': missing, 'wrong': wrong}))
    return [definition['id'], parameters, {}]


def _homology_native(prepared, parameters):
    application = prepare_application('Homology', parameters, {})
    if application['status'] != 'ok':
        raise ValueError('bvbrc_blast_application_request_invalid:' + application['diagnostics'][0]['code'])
    return application['value']['native_params']


# The applications the route submits, by the BV-BRC application id (see the module's description).
APPLICATIONS = {
    'Homology': {'job': ('application', 'program', 'database', 'query_file'), 'prepare': _homology_prepare,
                 'parameters': _homology_parameters, 'native': _homology_native, 'output_file': 'blast',
                 'bulk': 'query_fasta',
                 'result_files': {'blast_out.raw.json': 'the single-query JSON15 report'}},
    'MSA': {'job': ('application', 'aligner', 'alphabet', 'sequences_file'), 'optional': ('feature_group_file',),
            'prepare': _msa_prepare,
            'parameters': _msa_parameters, 'native': lambda prepared, parameters: native_params('MSA', parameters),
            'output_file': 'msa', 'bulk': 'sequences_fasta',
            'result_files': {'msa.afa': 'the aligned FASTA of the sequences'}},
    'MetaCATS': {'job': ('application', 'p_value', 'alignment_file', 'group_file'), 'prepare': _metacats_prepare,
                 'parameters': _metacats_parameters, 'native': lambda prepared, parameters: native_params(
                     'MetaCATS', parameters), 'uploads': _metacats_uploads, 'output_file': 'metacats',
                 'bulk': 'staged',
                 'result_files': {CHISQ_FILE: 'the positions that differ between the groups (chi-square, TSV)',
                                  MC_FILE: 'the groups that differ at each such position (TSV)'}}}


class BvbrcJobRoute(ApiJobRoute):
    """The BV-BRC ``Homology`` jobs of one run, below one workspace directory."""

    kind = 'bvbrc'

    def __init__(self, configuration, *, resource_id):
        if not isinstance(configuration, dict) or set(configuration) != set(CONFIGURATION):
            raise ValueError('bvbrc_route_configuration_requires_exactly:' + ','.join(CONFIGURATION))
        if configuration['service'] != SERVICE:
            raise ValueError('bvbrc_route_service_must_be_' + SERVICE)
        if (not isinstance(configuration['root_folder'], str)
                or _ROOT.fullmatch(configuration['root_folder']) is None):
            raise ValueError('bvbrc_route_root_folder_must_be_one_plain_name')
        for name in ('request_spacing_seconds', 'poll_spacing_seconds', 'transport_timeout_seconds'):
            if type(configuration[name]) not in (int, float) or not configuration[name] > 0:
                raise ValueError('bvbrc_route_' + name + '_must_be_positive')
        if type(resource_id) is not str or not resource_id:
            raise ValueError('bvbrc_route_resource_id_must_be_text')
        self.configuration, self.resource_id = json.loads(json.dumps(configuration)), resource_id
        self.workspace = Path(configuration['workspace']).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.client = BVBRCAnalysisClient(configuration['endpoints'], timeout=configuration['transport_timeout_seconds'],
                                          authorization_env=configuration['authorization_env'])

    def _send(self, method, fields):
        raise RuntimeError('bvbrc_route_sends_through_its_client_only')

    def describe(self):
        configuration = self.configuration
        return {'resource_id': self.resource_id, 'kind': self.kind, 'service': SERVICE, 'applications': sorted(APPLICATIONS),
                'base_url': configuration['endpoints']['AppService'],
                'authentication': 'environment_variable:' + configuration['authorization_env'],
                'request_spacing_seconds': configuration['request_spacing_seconds'],
                'poll_spacing_seconds': configuration['poll_spacing_seconds'], 'cancel_offered': False,
                'jobs': {name: list(spec['job']) for name, spec in APPLICATIONS.items()},
                'databases': json.loads(json.dumps(PRECOMPUTED_DATABASES)), 'states': dict(STATES),
                'result_files': {name: dict(spec['result_files']) for name, spec in APPLICATIONS.items()}}

    # -- one service request ----------------------------------------------------------------------------------
    def _request(self, method, params, action, *, remote_id=None, wait=True):
        """One RPC to the service and its decoded value. ``wait``: sleep what the provider spacing needs first (the
        later requests of one operation); otherwise a request that comes too early is refused, nothing sent."""
        request = prepare_rpc_request(method, params, request_id=utc_now())
        if wait:
            time.sleep(self.spacing(action, remote_id))
        with self._contact(action, remote_id):
            try:
                snapshot = self.client.rpc(request)
            except AcquisitionError as error:
                raise refusal(error) from error
        decoded = decode_rpc_response(snapshot.content, method=method, request_id=request['id'],
                                      http_status=snapshot.transport['status'])
        if decoded['status'] != 'ok':
            raise RouteRequestError('provider_' + ('status' if action == 'status' else 'submission'
                                                   if action == 'submit' else 'result') + '_response_invalid',
                                    {**_entity(snapshot), 'diagnostics': decoded['diagnostics']})
        return decoded['value'], snapshot

    def _home(self):
        """The home workspace of the login (``/<user>/home``), found in the service once and kept in the route's
        workspace: the one workspace named ``home`` that the login owns."""
        path = self.workspace / HOME_FILE
        if not path.exists():
            value, _ = self._request('Workspace.ls', [{'paths': ['/'], 'excludeDirectories': 0, 'excludeObjects': 1}],
                                     'submit')
            owned = [row['object_path'] for row in parse_workspace_records(value, operation='ls')['records']
                     if row['name'] == 'home' and row['type'] == 'folder' and row['user_permission'] == 'o']
            if len(owned) != 1:
                raise RouteRequestError('provider_submission_response_invalid', {'owned_home_workspaces': len(owned)})
            _publish(path, {'home': owned[0]})
        return json.loads(path.read_text())['home']

    # -- submit -----------------------------------------------------------------------------------------------
    def prepare(self, job, files):
        """The request the job is, with its input read: a job that is not of the form of its application raises
        ``ValueError``."""
        if not isinstance(job, dict) or job.get('application') not in APPLICATIONS:
            raise ValueError('bvbrc_job_requires_an_application_of:' + ','.join(sorted(APPLICATIONS)))
        spec = APPLICATIONS[job['application']]
        if not set(spec['job']) <= set(job) <= set(spec['job']) | set(spec.get('optional', ())):
            raise ValueError('bvbrc_' + job['application'] + '_job_requires:' + ','.join(spec['job'])
                             + ':and_may_have:' + ','.join(spec.get('optional', ())))
        return {'application': job['application'], **spec['prepare'](job, files)}

    def submit(self, handle, job, files, owner):
        prepared = self.prepare(job, files)
        directory = self._directory(handle)
        adopted = (directory / SUBMISSION_FILE).exists()
        if not adopted:
            if (directory / INTENT_FILE).exists():
                raise RouteRequestError('submission_outcome_unknown', {'job': handle, 'sent': 'unknown'})
            folder = self._home() + '/' + self.configuration['root_folder'] + '/' + handle
            spec = APPLICATIONS[prepared['application']]
            output_file = spec['output_file']
            parameters = spec['parameters'](prepared, folder, output_file)
            native_params_ = spec['native'](prepared, parameters)
            directory.mkdir(parents=True, exist_ok=True)
            _publish(directory / REQUEST_FILE, {**prepared, 'output_path': folder, 'output_file': output_file})
            (directory / INTENT_FILE).touch()
            made = {'outcome': 'refused', 'failure': None}
            try:
                self._request('Workspace.create', [{'objects': [[folder, 'folder']]}], 'submit')
                if prepared.get('feature_ids'):
                    self._request('Workspace.create', [{'objects': [[folder + '/' + FEATURE_GROUP, 'feature_group', {},
                                                                    {'id_list': {'feature_id': prepared['feature_ids']}}]]}],
                                  'submit')
                if 'uploads' in spec:
                    self._request('Workspace.create', [{'objects': spec['uploads'](prepared, folder)}], 'submit')
                value, snapshot = self._request('AppService.start_app2', native_params_, 'submit')
            except RouteRequestError as error:
                if error.failure['code'] == SPACING:
                    raise
                # The service may have received the request: the intent stays and nothing is sent again.
                made['failure'] = error.failure
            else:
                parsed = parse_task_records(value, operation='start_app2')
                if parsed['status'] != 'ok':
                    made['failure'] = {'code': 'provider_submission_response_invalid',
                                       'detail': {**_entity(snapshot), 'diagnostics': parsed['diagnostics']}}
                else:
                    task = str(parsed['records'][0]['task_id'])
                    made = {'outcome': 'accepted', 'remote_id': task, 'expected_seconds': None,
                            'submitted_at': utc_now(), 'output_path': folder,
                            'reply': {**_entity(snapshot), 'remote_id': task,
                                      'provider_status': parsed['records'][0]['native_state']}}
            _publish(directory / SUBMISSION_FILE, made)
        made = self._recorded(directory / SUBMISSION_FILE)
        if made['outcome'] != 'accepted':
            raise RouteRequestError(made['failure']['code'], {**made['failure']['detail'], 'sent': True})
        request = self._recorded(directory / REQUEST_FILE)
        return {'native': {'service': SERVICE, 'remote_id': made['remote_id'], 'expected_seconds': None,
                           'directory': str(directory),
                           'request': {name: request[name] for name in request
                            if name != APPLICATIONS[request['application']]['bulk']}},
                'submitted_at': made['submitted_at'], 'adopted': adopted, 'reply': made['reply']}

    # -- status -----------------------------------------------------------------------------------------------
    def status(self, handle, native):
        directory = self._directory(handle)
        known = self._recorded(directory / STATUS_FILE)
        if known is not None and known['state'] in ENDED:
            return {**known, 'reply': {**known['reply'], 'from_record': True}}
        value, snapshot = self._request('AppService.query_tasks', [[native['remote_id']]], 'status',
                                        remote_id=native['remote_id'], wait=False)
        observed_at = utc_now()
        parsed = parse_task_records(value, operation='query_tasks', requested_task_ids=[native['remote_id']])
        if parsed['status'] != 'ok':
            raise RouteRequestError('provider_status_response_invalid', {**_entity(snapshot),
                                                                         'diagnostics': parsed['diagnostics']})
        (task,) = parsed['records']
        if task['native_state'] not in STATES:
            raise RouteRequestError('provider_status_response_invalid', {**_entity(snapshot),
                                                                         'native_status': task['native_state']})
        state = STATES[task['native_state']]
        observation = {'state': state, 'result_available': state == 'finished', 'observed_at': observed_at,
                       'reply': {**_entity(snapshot), 'remote_id': native['remote_id'],
                                 'provider_status': task['native_state'], 'from_record': False,
                                 'submit_time': task['submit_time'], 'start_time': task['start_time'],
                                 'completed_time': task['completed_time'], 'elapsed_time': task['elapsed_time']}}
        _publish(directory / STATUS_FILE, observation)
        return observation

    # -- results ----------------------------------------------------------------------------------------------
    def results(self, handle, native):
        directory = self._directory(handle)
        known = self._recorded(directory / STATUS_FILE)
        if known is None or known['state'] != 'finished':
            raise RouteRequestError('results_not_available', {
                'job': handle, 'state': None if known is None else known['state']})
        if not (directory / CATALOG_FILE).exists():
            made = self._recorded(directory / SUBMISSION_FILE)
            folder = made['output_path'] + '/.' + self._recorded(directory / REQUEST_FILE)['output_file']
            value, snapshot = self._request('Workspace.ls', [{'paths': [folder], 'excludeDirectories': 1}],
                                            'fetch', remote_id=native['remote_id'])
            parsed = parse_workspace_records(value, operation='ls', requested_paths=[folder])
            files = [row for row in parsed['records'] if row['type'] != 'folder']
            if parsed['status'] != 'ok' or not files:
                raise RouteRequestError('provider_result_response_invalid', {
                    **_entity(snapshot), 'diagnostics': parsed['diagnostics'], 'files': len(files)})
            _publish(directory / RESULT_OBJECTS_FILE, {row['name']: row['object_path'] for row in files})
            _publish(directory / CATALOG_FILE, [{'name': row['name'], 'bytes': row['size'],
                                                 'media_type': MEDIA_TYPES.get(row['name'].rsplit('.', 1)[-1],
                                                                               'application/octet-stream'),
                                                 'workspace_path': row['object_path']}
                                                for row in files])
        return self._recorded(directory / CATALOG_FILE)

    def read(self, handle, native, name, offset, limit):
        directory = self._directory(handle)
        catalog = self._recorded(directory / CATALOG_FILE)
        if catalog is None or name not in [item['name'] for item in catalog]:
            raise RouteRequestError('result_file_missing', {'job': handle, 'name': name})
        stored = directory / RESULT_DIRECTORY / name
        if not stored.exists():
            path = self._recorded(directory / RESULT_OBJECTS_FILE)[name]
            (address,), _ = self._request('Workspace.get_download_url', [{'objects': [path]}], 'fetch',
                                          remote_id=native['remote_id'])
            size = [item['bytes'] for item in catalog if item['name'] == name][0]
            time.sleep(self.spacing('fetch', native['remote_id']))
            with self._contact('fetch', native['remote_id']):
                try:
                    snapshot = self.client.download(address, max_bytes=max(size, 1))
                except AcquisitionError as error:
                    raise refusal(error) from error
            (directory / RESULT_DIRECTORY).mkdir(exist_ok=True)
            stored.write_bytes(snapshot.content)
        with stored.open('rb') as stream:
            stream.seek(offset)
            return stream.read(limit)


__all__ = ['APPLICATIONS', 'BvbrcJobRoute', 'CONFIGURATION', 'PRECOMPUTED_DATABASES', 'SERVICE', 'STATES', 'native_params']
