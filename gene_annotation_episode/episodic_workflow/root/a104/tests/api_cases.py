"""Actual A104 API boundaries with explicitly controlled service responses.

The singleton saved contexts below are controlled test invocations, not HPC
admission. Real parent admission is exercised separately by admission_cases.
No external HTTP, model, native execution or scientific conclusion is produced.
"""
from __future__ import annotations
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

HOMES = (
    'execution_job_submission/api_job_execution',
    'evolutionary_history_evidence/execution_job_submission/api_job_execution',
    'hpc_work_planning/execution_job_submission/api_job_execution',
    'hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution',
    'evolutionary_history_evidence/hpc_work_planning/execution_job_submission/api_job_execution',
    'evolutionary_history_evidence/hpc_work_planning/hpc_allocation_execution/execution_job_submission/api_job_execution')
PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
JOB = '81bddc6e-f6ef-4f16-a8c1-32d262016ccb'


def module(name):
    return importlib.import_module(PREFIX + name.replace('/', '.'))


def canonical(value):
    return module('communication').plain(value)


def rows(store):
    """Logical custody; byte blobs are hashed, nothing is discarded by table."""
    result = {}
    for name, in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        quoted = '"' + name.replace('"', '""') + '"'
        values = [[{'bytes_sha256': hashlib.sha256(v).hexdigest()} if isinstance(v, bytes) else v
            for v in row] for row in store.db.execute('SELECT * FROM ' + quoted)]
        result[name] = sorted(values, key=lambda value: json.dumps(value, sort_keys=True))
    return result


def error_record(error):
    return {'type': type(error).__module__ + '.' + type(error).__qualname__,
        'message': str(error), 'failure': canonical(getattr(error, 'failure', None))}


def outcome(function):
    try:
        return {'returned': canonical(function())}
    except Exception as error:
        return {'raised': error_record(error)}


def resources():
    return {'uniprot': {'kind': 'api', 'service': 'uniprot'},
            'ebi': {'kind': 'hmmer_api'},
            'ncbi-blast': {'kind': 'api', 'service': 'ncbi_blast'}}


def assignment(subject, service='uniprot'):
    if service == 'ebi_hmmer':
        return {'version': 'api_execution_assignment_v1', 'resource_id': 'ebi',
            'service': service, 'subject_ref': subject, 'algorithm': 'phmmer',
            'database': 'swissprot', 'parameters': {}, 'page_size': 50,
            'endpoint': 'usable_handoff', 'constraints': {}}
    return {'version': 'api_service_assignment_v1',
        'resource_id': 'ncbi-blast' if service == 'ncbi_blast' else 'uniprot',
        'service': service, 'request': ({'subject_ref': subject, 'program': 'blastp',
            'database': 'swissprot'} if service == 'ncbi_blast' else
            {'operation': 'record', 'accession': 'P12345'}),
        'endpoint': 'usable_handoff', 'constraints': {}}


class Responses:
    """Original protocol fixtures adapted only to own-A104 SourceSnapshot.

    UniProt body: root/tests/test_api_service_integration.PublicResponses.
    HMMER accepted ID/status: tests/test_public_search.Client.
    BLAST POST/status bytes: original NCBI Common URL response fixtures.
    The labels explicitly describe source metadata, not target evidence.
    """
    ncbi_email = 'synthetic-fixture@example.invalid'

    def __init__(self):
        self.calls, self.mode = [], 'ordinary'

    def snapshot(self, service, operation, arguments, body, content_type='application/json'):
        self.calls.append((service, operation, deepcopy(arguments)))
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        return module('acquisition').SourceSnapshot(service,
            {'uniprot': 'https://rest.uniprot.org/uniprotkb/',
             'ebi_hmmer': 'https://www.ebi.ac.uk/Tools/hmmer/api/v1/',
             'ncbi_blast': 'https://blast.ncbi.nlm.nih.gov/Blast.cgi?'}[service] + operation,
            arguments, '2026-10-23T12:00:01+00:00', raw, content_type,
            {'response': {'status': 200, 'headers': {}},
             'representation': 'controlled_native_service_response'})

    def uniprot_record(self, accession):
        return self.snapshot('uniprot', accession, {'accession': accession},
            {'primaryAccession': accession, 'sequence': {'value': 'MACDEFGH'},
             'organism': {'taxonId': 511145, 'scientificName': 'Escherichia coli'},
             'proteinDescription': {'recommendedName': {'fullName': {
                 'value': 'Synthetic source label; not an annotation of the target'}}}})

    def hmmer_submit(self, query_fasta, **arguments):
        return self.snapshot('ebi_hmmer', 'search/phmmer', arguments, {'id': JOB})

    def hmmer_status(self, jobid):
        assert jobid == JOB
        return self.snapshot('ebi_hmmer', 'result/' + JOB, {},
            {'task': {'status': 'SUCCESS'}, 'database': {'id': 'swissprot',
                'version': 'fixture-release'}, 'algo': 'phmmer'})

    def blast_delay(self, action, rid=None):
        return 60. if action == 'status' else 10.

    def blast(self, action, **arguments):
        if self.mode in {'unknown', 'not_sent'}:
            self.calls.append(('ncbi_blast', action, deepcopy(arguments)))
            raise module('acquisition').AcquisitionError('controlled_submission_failure',
                phase='submission' if self.mode == 'unknown' else 'local_preflight',
                submission_outcome=self.mode)
        request = {'action': action, **{k: v for k, v in arguments.items() if k != 'query_fasta'}}
        if action == 'submit':
            request['query_sha256'] = hashlib.sha256(arguments['query_fasta'].encode()).hexdigest()
            return self.snapshot('ncbi_blast', action, request,
                b'    RID = FIXTURE_ORIGINAL_RID\n    RTOE = 17\n', 'text/plain')
        assert action == 'status' and arguments['rid'] == 'FIXTURE_ORIGINAL_RID'
        return self.snapshot('ncbi_blast', action, request, b'Status=WAITING\n', 'text/plain')


class Case:
    def __init__(self, directory, home, *, service='uniprot', existing=False,
                 parented=False, initialize=True):
        self.store = None
        try:
            self._initialize(directory, home, service=service, existing=existing,
                parented=parented, initialize=initialize)
        except BaseException as original:
            if self.store is not None:
                try:
                    self.store.close()
                except BaseException as closing:
                    raise BaseExceptionGroup('API fixture constructor and close failures', [original, closing])
            raise

    def _initialize(self, directory, home, *, service, existing, parented, initialize):
        assert home in HOMES
        self.directory, self.home = Path(directory), home
        self.store = module('state').Store(self.directory / 'store')
        self.client = Responses()
        self.tools = module('tools').ToolRegistry(self.store, clients=self.client)
        self.run_id = 'controlled-a104-api'
        if not existing:
            self.store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        self.scope = self.store.validate_scope(None)
        self.assignment = assignment(self.scope['subject_refs'][0], service)
        self.services = SimpleNamespace(annotation_task_required=lambda: False)
        self.options = dict(store=self.store, directory=self.directory / 'execution',
            run_id=self.run_id, resources=resources(), initial_information={},
            tool_registry=self.tools, handoff_unit=3., acquired_record_unit=2.,
            log_window_bytes=1024, log_roles=('stdout', 'stderr'), require_private_yield=True,
            task_yield_profiles={'launch_api:api_uniprot_handoff': {'cutoff': .5, 'parameters': {}},
                'launch_api:api_ebi_hmmer_phmmer_swissprot_handoff': {'cutoff': .5, 'parameters': {}},
                'launch_api:api_ncbi_blast_handoff': {'cutoff': .5, 'parameters': {}}})
        parent = home.rsplit('/execution_job_submission/', 1)[0]
        if home == HOMES[0]:
            self.factory = None
            self.binding = module(home + '/episode').ExecutionEpisode(self.services, **self.options)
            self.family = (self.binding,)
        else:
            self.factory = module(parent + '/episode').create_execution_bindings
            self.family = tuple(self.factory(self.services, **self.options))
            matches = [binding for binding in self.family if binding.binding_path == home]
            assert len(matches) == 1 and len(self.family) == 5
            self.binding = matches[0]
        self.journal = module('episode_journal').Journal(self.store, self.run_id)
        self.receipts = module('episode_receipts').EpisodeReceipts(self.store, self.run_id)
        self.parent_context = None
        self.path = (('launch_api', 'controlled-saved-api'),)
        if parented:
            # An explicitly saved parent request, not an admitted HPC plan.
            # The API request is real; its original parent validation is never
            # suppressed. The direct two copies currently reject this context.
            parent_path = (('launch', 'controlled-saved-parent'),)
            parent_id = module('method_loop.identities').EpisodeRef(self.run_id, parent_path).episode_id
            launch = {'version': 'execution_launch_assignment_v1',
                'requests': {self.assignment['resource_id']: deepcopy(self.assignment)},
                'immutable_input_versions': [], 'constraints': {}}
            parent_manifest = self.receipts.bind(parent_id)
            self.receipts.receive(parent_id, self.scope['subject_refs'], kind='initial')
            parent_request = {'message': {'scope': deepcopy(self.scope),
                'episode_assignment': launch, 'knowledge_inheritance': parent_manifest}}
            self.journal.save('runtime_episodes', {'episode_id': parent_id,
                'path': module('runtime')._json(parent_path), 'request': module('runtime')._json(parent_request),
                'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            self.parent_context = module('episode_bindings').BindingContext(self.run_id,
                parent_id, 'launch', parent_path, self.scope, launch, parent_request)
            self.path = parent_path + (('launch_api', 'child_3'),)
        self.episode_id = module('method_loop.identities').EpisodeRef(self.run_id, self.path).episode_id
        manifest = self.receipts.bind(self.episode_id,
            None if self.parent_context is None else self.parent_context.episode_id)
        self.receipts.receive(self.episode_id, self.scope['subject_refs'], kind='initial')
        self.request = {'message': {'scope': deepcopy(self.scope),
            'episode_assignment': deepcopy(self.assignment), 'knowledge_inheritance': manifest}}
        self.context = module('episode_bindings').BindingContext(self.run_id, self.episode_id,
            'launch_api', self.path, self.scope, self.assignment, self.request)
        old = self.journal.row('runtime_episodes', self.episode_id)
        if old is None:
            self.journal.save('runtime_episodes', {'episode_id': self.episode_id,
                'path': module('runtime')._json(self.path), 'request': module('runtime')._json(self.request),
                'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
        else:
            assert json.loads(old['request']) == self.request
        if initialize:
            self.binding.initialize(self.context)

    def close(self):
        self.store.close()

    def selection(self):
        return {'run_id': self.run_id, 'episode_id': self.episode_id,
            'known_record_refs': list(self.receipts.known(self.episode_id)),
            'initial_known_record_refs': list(self.receipts.known(self.episode_id, baseline=True))}

    def selected(self, name, arguments, index):
        chosen = {'kind': 'tool', 'tool': name, 'arguments': deepcopy(arguments)}
        old = self.journal.row('runtime_actions', self.episode_id, index)
        if old is not None:
            assert json.loads(old['action']) == chosen
        else:
            self.journal.save('runtime_actions', {'episode_id': self.episode_id,
                'decision_index': index, 'action': module('runtime')._json(chosen),
                'result': None, 'credit': None})
        return f'{self.run_id}:{self.episode_id}:{index}'

    def act(self, name, arguments=None, index=0):
        arguments = {} if arguments is None else arguments
        key = self.selected(name, arguments, index)
        value = asyncio.run(self.binding.execute(self.context, name, arguments, key))
        with self.store.transaction():
            self.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? '
                'AND episode_id=? AND decision_index=?',
                (module('runtime')._json(value), self.run_id, self.episode_id, index))
        self.receipts.receive(self.episode_id, value.get('record_refs', []), kind='own_action', source_index=index)
        return value


def task_case(case):
    """Actual selected task + actual Journal, receipts, projection/controller input.

    No model, event service or reasoning engine is started. Those operation ports
    are explicitly supplied by tests of their returned/persisted outcomes.
    """
    runtime = module('runtime')
    task = object.__new__(getattr(case.binding, 'decision_source_type', runtime.DecisionSource))
    task.episode_id, task.path, task.scope = case.episode_id, case.path, deepcopy(case.scope)
    task.calls = 0
    task._execution_context = task._delivery_resolution_ref = None
    task.report_values, task.report_basis, task.interpret_schema = {}, [], runtime._object({})
    task.last_outcome = task.last_outcome_index = task.feedback = None
    task.request = SimpleNamespace(goal=SimpleNamespace(as_record=lambda: {'objective': 'Controlled original API request'}),
        message=SimpleNamespace(as_record=lambda: deepcopy(case.request['message'])), report_contract=None)
    task.checkpoint = lambda: None  # Source checkpoint is outside this iterator-only fixture.
    observations, projections, executions = [], [], []
    workflow = SimpleNamespace(store=case.store, run_id=case.run_id, journal=case.journal,
        execution_binding=None, inprocess_replay=None, pending_work=lambda source: {'items': []},
        receipts=case.receipts, progress_provider=None,
        progress_receipt_order='received_progress_order_v1',
        specialist=lambda source: case.binding, binding_context=lambda source: case.context,
        is_job_source=lambda source: False, receive_tool_attributions=lambda *a, **k: [],
        receive_native_outcome=lambda *a: None)
    async def execute(source, name, arguments, **kwargs):
        executions.append(kwargs['operation_key'])
        return await case.binding.execute(case.context, name, arguments, kwargs['operation_key'])
    def receive(source, chosen, result, index):
        observations.append((index, deepcopy(chosen), deepcopy(result)))
        runtime.Workflow.receive_outcome(workflow, source, chosen, result, index)
    async def score(source, index, result):
        return await runtime.Workflow.automatic_score_updates(workflow, source, index, result)
    def project(source):
        view = case.binding.credit_view(case.context, case.selection())
        projections.append(deepcopy(view))
        return view
    workflow.execute, workflow.receive_outcome = execute, receive
    workflow.automatic_score_updates, workflow.source_credit_view = score, project
    workflow.controller_value = lambda source, index, credit: runtime.Workflow.controller_value(workflow, source, index, credit)
    task.workflow = workflow
    return SimpleNamespace(task=task, workflow=workflow, observations=observations,
        projections=projections, executions=executions)


def prepare_decision(case, task, protocol, *, declared=True):
    """Use actual task.call/Journal/exchange codec with a controlled model port."""
    runtime, workflow = module('runtime'), task.workflow
    task.calls = 0
    task._model_snapshot = task._presented_conversation_key = None
    task.decision_inputs = lambda context, index, profile: context
    workflow.decision_exchanges = module('decision_exchanges').DecisionExchanges(case.journal)
    workflow.controller_binding, workflow.decision_protocol = {}, protocol
    workflow.contract_information_profile = lambda source: None
    workflow.receipts = None  # Prompt input capture only; actual action tests keep receipts.
    workflow.available_child_roles = lambda source: ()
    workflow.scientific_library_available = lambda source: False
    workflow.permits_common_action = lambda source, action: action in case.binding.permitted_common_actions(case.context)
    workflow.native_event_information = None
    workflow.resource_context = workflow.shared_information_context = lambda source: None
    workflow.episode_bindings = SimpleNamespace(initial_decision_context=lambda context: {})
    workflow.pending_work = lambda source: []
    workflow.waiting_support = lambda source, context: {
        'controlled_received_wait_information': 'Original request remains open; no event is performed by prompt capture'}
    workflow.execution_expectations = workflow.resource_estimator = None
    workflow.native_estimation_context = lambda *args: None
    workflow.freeze_literature_numerical_contracts = lambda *args: None
    workflow.knowledge = SimpleNamespace(instructions='Selected knowledge.')
    workflow.launch_instructions = SimpleNamespace(instructions='Selected launch instructions.',
        context=lambda: {}, materialize=lambda selection: None)
    workflow.services = SimpleNamespace(instructions=module('runtime_prompt').instructions,
        decision_exchange_instructions=lambda: module('decision_context').INSTRUCTIONS)
    selected = {'selection': {'kind': 'tool', 'tool': 'api.uniprot.record', 'arguments': {}}, 'report_update': {}}
    wire = {'response': {'response_type': 'select_action', **selected}} if protocol else selected
    calls = []
    async def complete(*args, **kwargs):
        calls.append((args, kwargs))
        return deepcopy(wire)
    workflow.provider = SimpleNamespace(has_session=lambda *args: True, complete=complete)
    if declared:
        from .provider_dispatch_fixtures import controlled_config, controlled_serial_model
        workflow.provider = controlled_serial_model(controlled_config(),
            case.directory / "decision-model", case.directory, complete)
        workflow.provider.has_session = lambda *args: True
    schema = runtime._object({'selection': runtime._object({'kind': {'const': 'tool'},
        'tool': {'const': 'api.uniprot.record'}, 'arguments': runtime._object({})}), 'report_update': runtime._object({})})
    state = {'execution_assignment': deepcopy(case.assignment), 'api_service': 'uniprot',
        'api_request': deepcopy(case.assignment['request']), 'goal': {'objective': 'Original source request'},
        'scope': deepcopy(case.scope)}
    return state, schema, selected, calls
