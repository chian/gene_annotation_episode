"""Actual A104 source reads/admission and controlled task connection checks.

The article and acquisition client are explicit fixtures. Store, ToolRegistry,
Journal, source validation and receipt storage are real. The task test injects
an explicitly controlled zero scientific projector and boundary counters; the
separate original-commission diagnostic exercises A104's actual task projector
and continuation admission. These checks claim no scientific evidence or autonomy.
"""
import asyncio
import ast
from copy import deepcopy
from dataclasses import replace
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ..acquisition import SourceSnapshot
from ..communication import plain
from ..domain import ContractError
from ..episode_bindings import BindingContext, EpisodeBindingRegistry
from ..episode_journal import Journal
from ..episode_receipts import EpisodeReceipts
from ..episode_services import WorkflowServices
from ..method_loop.identities import EpisodeRef
from ..state import Store
from ..tools import ToolRegistry
from .. import runtime
from .provider_dispatch_fixtures import controlled_serial_model, controlled_config

PREFIX = 'gene_annotation_episode.episodic_workflow.root.a104.'
TOP = 'published_evidence_assessment'
STRATEGY = TOP + '/evidence_search_strategy_improvement'
SEARCH = STRATEGY + '/source_relevance_assessment'
PAGE = SEARCH + '/source_evidence_examination'
RELATIVE = (
    (TOP, 'literature'), (STRATEGY, 'literature_strategy'),
    (SEARCH, 'literature_search'), (PAGE, 'literature_page'),
    (PAGE + '/table_evidence_extraction', 'literature_table'),
    (PAGE + '/source_coverage_improvement', 'literature_ordered'),
    (PAGE + '/passage_evidence_extraction', 'literature_targeted'))
HOMES = tuple((prefix + path, role) for prefix in ('', 'evolutionary_history_evidence/') for path, role in RELATIVE)
EDGES = tuple((prefix + parent, prefix + child, role) for prefix in ('', 'evolutionary_history_evidence/')
    for parent, child, role in ((TOP, STRATEGY, 'literature_strategy'),
        (STRATEGY, SEARCH, 'literature_search'), (SEARCH, PAGE, 'literature_page'),
        (PAGE, PAGE + '/table_evidence_extraction', 'literature_table'),
        (PAGE, PAGE + '/source_coverage_improvement', 'literature_ordered'),
        (PAGE, PAGE + '/passage_evidence_extraction', 'literature_targeted')))


def binding_type(home):
    return importlib.import_module(PREFIX + home.replace('/', '.') + '.episode').LiteratureEpisode


def path_for(home):
    prefix = (('annotation', 'root'),)
    own = home
    if home.startswith('evolutionary_history_evidence/'):
        prefix += (('evolutionary_history_evidence', 'original-process'),)
        own = home.removeprefix('evolutionary_history_evidence/')
    return prefix + tuple((role, 'child_0') for path, role in RELATIVE
        if own == path or own.startswith(path + '/'))


def assignment(role, source):
    page = {'version': 'page_assignment_v1', 'source_ref': source['id'],
        'representation': 'original', 'artifact_ref': source['artifact_ref'],
        'question_context_refs': [], 'prior_delivery_refs': []}
    window = {'source_ref': source['id'], 'representation': 'original', 'offset': 0, 'limit': 64}
    if role == 'literature_page': return page
    if role in {'literature_table', 'literature_ordered', 'literature_targeted'}:
        return {'version': 'reading_assignment_v1', 'page': page,
            'selection': {'spans': [window]} if role == 'literature_targeted' else window}
    version, field = {'literature': ('literature_assignment_v1', 'source_refs'),
        'literature_strategy': ('strategy_assignment_v1', 'prior_search_refs'),
        'literature_search': ('search_assignment_v1', 'search_result_refs')}[role]
    return {'version': version, 'question_context_refs': [], field: [source['id']]}


class Services:
    def __init__(self, store, tools):
        self.store, self.tools = store, tools
        self.projections = []

    def tool_catalog(self, scope):
        return self.tools.catalog(plain(scope))

    def execute_tool(self, name, arguments, *, scope, operation_key, **authorization):
        return self.tools.execute_async(name, arguments, scope=plain(scope),
            operation_key=operation_key, **authorization)

    def read_record(self, reference):
        return self.store.get(reference)

    def reference_in_scope(self, reference, scope, namespace):
        if not self.store.reference_subset([reference], plain(scope)): return False
        kind = self.store.get(reference)['record_type']
        return namespace is None or namespace == kind or namespace == 'subject' and kind in {
            'input', 'feature', 'product', 'read_subject'}

    def own_outcomes(self, episode_id, *, tools, offset, limit):
        return {'records': [], 'offset': offset, 'limit': limit, 'next_offset': None}

    def scientific_credit(self, context, receiver_selection):
        # This explicit controlled projector tests the task connection only.
        # It cannot stand in for the separate actual service diagnostic below.
        self.projections.append((context.episode_id, plain(receiver_selection)))
        return {'credit': 0.0, 'definition': 'controlled source-task connection fixture'}


@pytest.fixture(scope='module')
def family(tmp_path_factory):
    root = tmp_path_factory.mktemp('a104-source-family')
    raw = (Path(__file__).parent / 'fixtures/source_investigation/article.xml').read_bytes()
    class RetainedClient:
        def literature_read(self, pmcid):
            assert pmcid == 'PMC123'
            return SourceSnapshot('europepmc', 'https://example.invalid/a104-controlled-source',
                {'pmcid': pmcid}, '2026-11-11T00:00:00+00:00', raw, 'application/xml',
                {'representation': 'controlled-test-input'})
    with Store(root / 'store') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        tools = ToolRegistry(store, clients=RetainedClient())
        result = asyncio.run(tools.execute_async('public.literature.read', {'pmcid': 'PMC123'},
            operation_key='required-controlled-article'))
        assert result['status'] == 'completed', result
        services = Services(store, tools)
        source = store.get(result['result']['source_ref'])
        bindings = {home: binding_type(home)(services) for home, _ in HOMES}
        # Actual commissioning binding, explicit empty metadata-only libraries.
        # These operands do not select a scientific instruction or credit owner.
        science_type = importlib.import_module(PREFIX + 'evolutionary_history_evidence.episode').EvolutionaryHistoryEvidenceEpisode
        science = science_type(services,
            library=SimpleNamespace(as_record=lambda: {}, headers=lambda: []),
            tool_library=SimpleNamespace(as_record=lambda: {}),
            child_roles=('evolutionary_history_evidence', 'hpc'))
        yield SimpleNamespace(root=root, store=store, tools=tools, raw=raw, source=source,
            services=services, bindings=bindings,
            registry=EpisodeBindingRegistry((science, *bindings.values())))


def case(family, home, label):
    role = dict(HOMES)[home]
    run_id = 'source-family-' + label
    path = path_for(home)
    identity = EpisodeRef(run_id, path).episode_id
    scope = family.store.validate_scope()
    value = assignment(role, family.source)
    context = BindingContext(run_id, identity, role, path, scope, value,
        {'message': {'scope': scope, 'episode_assignment': value}},
        (family.source['id'], family.source['artifact_ref']))
    return family.bindings[home], context


@pytest.mark.parametrize('home,role', HOMES)
def test_original_source_read_summary_and_goal_retain_actual_custody(family, home, role):
    binding, context = case(family, home, 'read')
    goal = binding.instructions(context)
    assert "Preserve the source's actual subject, experimental conditions" in goal
    assert binding.permitted_common_actions(context) == ('tool', 'reason', 'child', 'redeliver_report')
    assert binding.reasoning_action_schema(context, {}) is None
    assert getattr(binding, 'automatic_score_judgments', None) is None
    assert binding.yield_controller(context, 0, 0) is None
    assert binding.supports_wait is False
    summary = binding.decision_context(context, None)
    assert summary['literature_assignment'] == plain(context.assignment)
    if role in {'literature_strategy', 'literature_search'}:
        # Original summary exposes only source_refs or the assigned page;
        # prior_search_refs/search_result_refs are retained in the assignment.
        assert summary['literature_source_custody'] == []
    else:
        assert summary['literature_source_custody'][0]['source_ref'] == family.source['id']
        assert summary['literature_source_custody'][0]['artifact_ref'] == family.source['artifact_ref']
    result = asyncio.run(binding.execute(context, 'source.read', {
        'source_ref': family.source['id'], 'representation': 'original', 'offset': 0, 'limit': 64},
        context.episode_id + ':actual-read'))
    assert result['status'] == 'completed', result
    assert result['result']['artifact_ref'] == family.source['artifact_ref']
    assert result['result']['text'] == family.raw[:64].decode()
    assert not family.store.list('assessment') and not family.store.list('observation')


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
def test_original_request_admission_and_typed_report(family, parent_home, child_home, role):
    parent, parent_context = case(family, parent_home, 'exchange')
    child, child_context = case(family, child_home, 'exchange')
    selected = plain(child_context.assignment)
    prepare = getattr(parent, 'prepare_child_request', None)
    prepared = selected if prepare is None else prepare(parent_context, role, selected)
    admitted = child.prepare_assignment(parent_context, role, prepared, child_context.scope, 'original-source-request')
    assert admitted == selected
    assert family.registry.for_child(parent_context.path, role) is child
    schema = {'type': 'object', 'properties': {'qualification': {
        'type': 'string', 'enum': ['unresolved', 'source-supported']}},
        'required': ['qualification'], 'additionalProperties': False}
    child.validate_report(child_context, {'qualification': 'unresolved'}, schema)
    with pytest.raises(ContractError):
        child.prepare_assignment(parent_context, role, {**selected, 'unexpected': True},
            child_context.scope, 'invalid-source-request')
    with pytest.raises(runtime.ReportBoundaryError):
        child.validate_report(child_context, {'qualification': 'invented'}, schema)


@pytest.mark.parametrize('home,role', HOMES)
def test_original_task_credit_and_continuation_require_actual_commission(family, home, role):
    from ..domain import validate_schema
    from ..literature_task_credit import LiteratureTaskCredit, commissioned_task
    binding, context = case(family, home, 'actual-projector-baseline')
    # The authenticated original validates the commission at projector
    # selection too; the incomplete pre-union body deferred this first check.
    for boundary in (lambda: binding.credit_projector(context),
            LiteratureTaskCredit(binding, context).as_record,
            lambda: binding.continuation_task(context)):
        with pytest.raises(ContractError, match='^literature_original_task_credit_required$'):
            boundary()

    # A real typed commission preserves the original projector identity checks.
    # Its hypothesis is a synthetic test operand, never scientific support.
    proposed = family.store.put('hypothesis', {
        'subject_refs': list(context.scope['subject_refs']), 'predicate': 'biological_role',
        'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []},
        origin='reasoning')['id']
    task = {'version': 'literature_local_task_v1', 'evidence_axis': 'A105',
        'credit_unit': 1.75, 'kind': 'source_answer', 'answer_kind': 'assessment',
        'source_refs': [family.source['id']]}
    selected = {**plain(context.assignment), 'literature_task': task,
        'proposed_annotation_ref': proposed}
    validate_schema(selected, binding.assignment_schema(role))
    schema = {'type': 'object', 'properties': {'assessments': {
        'type': 'array', 'x-source': 'changed_assessment_refs', 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'assessment'}}},
        'required': ['assessments'], 'additionalProperties': False}
    request = {'goal': 'Assess the acquired source for the original proposed annotation',
        'report_contract': {'decision': 'retain the qualified source assessment',
            'measurements': {'schema': schema}},
        'message': {'scope': plain(context.scope), 'episode_assignment': selected,
            'initial_report': {'assessments': []}}}
    commissioned = replace(context, assignment=selected, request=request,
        received_record_refs=(*context.received_record_refs, proposed))
    assert commissioned_task(commissioned) == (task, proposed)
    projector = binding.credit_projector(commissioned)
    assert type(projector) is LiteratureTaskCredit
    assert projector.binding is binding and projector.context is commissioned
    assert projector.as_record()['task'] == 'A105:source_answer:assessment'
    assert binding.continuation_task(commissioned) == 'A105:source_answer:assessment'

    # Original own-A104 factory selected A105-named assay grading. Preserve
    # its original axis guard, including rejection of a different typed axis.
    assay = binding_type(home)(family.services, rate_population=True, assay_grading_population=True)
    assay_projector = assay.credit_projector(commissioned)
    assert type(assay_projector) is LiteratureTaskCredit
    assert assay_projector.binding is assay and assay_projector.context is commissioned
    other_selected = {**selected, 'literature_task': {**task, 'evidence_axis': 'A108'}}
    other_request = {**request, 'message': {**request['message'], 'episode_assignment': other_selected}}
    other = replace(commissioned, assignment=other_selected, request=other_request)
    assert commissioned_task(other) == (other_selected['literature_task'], proposed)
    with pytest.raises(ContractError, match='^literature_task_original_axis_mismatch$'):
        assay.credit_projector(other)


@pytest.mark.parametrize('home,role', HOMES)
@pytest.mark.parametrize('status', ['invalid', 'failed', 'unavailable'])
def test_returned_outcome_and_saved_replay_reach_original_action_unit(family, home, role, status):
    binding, context = case(family, home, 'task-' + status)
    if status != 'invalid':
        class ControlledReturnedOutcome(Services):
            def execute_tool(self, name, arguments, *, scope, operation_key, **authorization):
                assert name == 'source.read' and arguments['source_ref'] == family.source['id']
                return {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'controlled_returned_tool_failure', 'code': status}}
        # Actual binding validates the real source arguments, then the explicit
        # tool port supplies a returned failure. No provider/native failure is claimed.
        binding = type(binding)(ControlledReturnedOutcome(family.store, family.tools))
    task_type = getattr(binding, 'decision_source_type', runtime.DecisionSource)
    task = object.__new__(task_type)
    task.episode_id, task.path, task.scope = context.episode_id, context.path, plain(context.scope)
    task.last_outcome = task.last_outcome_index = task.feedback = None
    task.checkpoint = lambda: None
    journal = Journal(family.store, context.run_id)
    executions, receipts, score_calls, projections = [], [], [], []
    async def execute(source, name, arguments, **kwargs):
        executions.append(kwargs['operation_key'])
        return await binding.execute(context, name, arguments, kwargs['operation_key'])
    async def score(source, index, result):
        assert getattr(binding, 'automatic_score_judgments', None) is None
        score_calls.append(index)
        return result
    def project(source):
        projections.append(source.episode_id)
        return binding.credit_view(context, {})
    task.workflow = SimpleNamespace(run_id=context.run_id, store=family.store,
        journal=journal, execution_binding=None, pending_work=lambda source: {'items': []},
        execute=execute,
        receive_native_outcome=lambda *args: None,
        receive_outcome=lambda source, selection, result, index: receipts.append((index, result['status'])),
        automatic_score_updates=score, source_credit_view=project,
        controller_value=lambda source, index, credit: {'index': index, 'credit': credit})
    task.workflow.permits_common_action = lambda source, action: action in binding.permitted_common_actions(context)
    task.workflow._closed_child_commission = lambda *args: runtime.Workflow._closed_child_commission(task.workflow, *args)
    task.workflow.receipts = task.workflow.native_timing_information = task.workflow.inprocess_replay = None
    selected = ({'kind': 'tool', 'tool': 'not-an-owned-source-tool', 'arguments': {}}
        if status == 'invalid' else {'kind': 'tool', 'tool': 'source.read', 'arguments': {
            'source_ref': family.source['id'], 'representation': 'original', 'offset': 0, 'limit': 64}})
    unit = runtime.Workflow.selected(task.workflow, task, selected, 0)
    assert isinstance(unit, runtime.ActionLeaf) and unit.decision_index == 0
    actual = asyncio.run(unit.acquire_async(None)).contribution.controller_input
    first = journal.row('runtime_actions', context.episode_id, 0)
    assert actual == {'index': 0, 'credit': 0.0}
    assert json.loads(first['result'])['status'] == status
    assert json.loads(first['action']) == selected
    assert json.loads(first['result'])['feedback']['code'] == (
        'tool_not_available_to_literature_role' if status == 'invalid' else status)
    replay = runtime.Workflow.selected(task.workflow, task, selected, 0)
    assert asyncio.run(replay.acquire_async(None)).contribution.controller_input == actual
    assert journal.row('runtime_actions', context.episode_id, 0) == first
    assert executions == [context.run_id + ':' + context.episode_id + ':0']
    assert receipts == [(0, status)] and score_calls == [0] and projections == [context.episode_id]
    assert runtime.observes_action_outcome('tool', status)


@pytest.mark.parametrize('home,role', HOMES)
def test_saved_full_decision_payload_is_returned_without_rebuilding_inputs(family, home, role):
    binding, context = case(family, home, 'saved-model')
    task = object.__new__(getattr(binding, 'decision_source_type', runtime.DecisionSource))
    task.episode_id, task.path, task.calls = context.episode_id, context.path, 0
    journal = Journal(family.store, context.run_id)
    original = {'scope': plain(context.scope), 'literature_assignment': plain(context.assignment),
        'source_body': family.raw.decode(), 'qualification': {'state': 'unresolved',
            'target_correspondence': None, 'alternative_explanations': ['identity not established']},
        'child_reports': [{'delivery_ref': 'exact-original', 'form': {'source': family.source['id']}}]}
    schema = {'type': 'object', 'properties': {'selected': {'const': 'saved'}},
        'required': ['selected'], 'additionalProperties': False}
    response = {'selected': 'saved'}
    journal.save('runtime_model_calls', {'episode_id': context.episode_id, 'call_index': 0,
        'purpose': 'decision', 'request': runtime._json({'context': original, 'schema': schema, 'assignment_transport': {
            'version': runtime._ASSIGNMENT_TRANSPORT, 'action_schema_sha256': runtime._digest(schema)}}),
        'response': runtime._json(response)})
    before = journal.row('runtime_model_calls', context.episode_id, 0)
    task.workflow = SimpleNamespace(journal=journal,
        contract_information_profile=lambda source: None, decision_protocol=None)
    assert asyncio.run(task.call({'replacement': 'must not be used'}, {})) == (response, 0, original, schema)
    assert journal.row('runtime_model_calls', context.episode_id, 0) == before


@pytest.mark.parametrize('home,role', HOMES)
def test_actual_runtime_build_selects_and_constructs_its_private_source(family, home, role, monkeypatch):
    binding, context = case(family, home, 'actual-build-selection')
    selected_type = getattr(binding, 'decision_source_type', runtime.DecisionSource)
    instances = []
    class ConstructionObserved(Exception):
        pass
    original_init = selected_type.__init__
    def capture(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        instances.append(self)
        raise ConstructionObserved()
    monkeypatch.setattr(selected_type, '__init__', capture)
    # Only the constructor selection boundary is under test. The original
    # constructor runs in full; the intentional exception prevents commission,
    # initialization, model, controller or scientific projection claims.
    workflow = SimpleNamespace(run_id=context.run_id, episode_bindings=family.registry,
        context=SimpleNamespace(require_run_id=lambda: context.run_id),
        grains={role: SimpleNamespace(name=role)}, inprocess_completion_order=None,
        evolutionary_history_evidence_binding=None, receipts=None,
        launch_instructions=SimpleNamespace(materialize=lambda value: None))
    with pytest.raises(ConstructionObserved):
        runtime.Workflow.build(workflow, role, context.path[-1][1], 'Read this actual source',
            plain(context.scope), parent_path=context.path[:-1], episode_assignment=plain(context.assignment))
    assert len(instances) == 1 and type(instances[0]) is selected_type
    assert instances[0].episode_id == context.episode_id
    assert instances[0].path == context.path
    assert instances[0].report_values == {}


@pytest.mark.parametrize('parent_home,child_home,role', EDGES)
def test_actual_saved_receipt_cache_and_redelivery_preserve_source_and_child_identity(
        family, parent_home, child_home, role):
    parent, owner = case(family, parent_home, 'receipt-' + role)
    child, declared_child = case(family, child_home, 'receipt-' + role)
    schema = {'type': 'object', 'properties': {'source': {
        'type': 'string', 'format': 'reference'}, 'qualification': {'type': 'string', 'enum': ['unresolved']}},
        'required': ['source', 'qualification'], 'additionalProperties': False}
    form = {'source': family.source['id'], 'qualification': 'unresolved'}
    contract = {'decision': 'examine the actual source', 'measurements': {'schema': schema}}
    request = {**plain(declared_child.request), 'report_contract': contract}
    child_context = replace(declared_child, request=request)
    journal = Journal(family.store, owner.run_id)
    receipts = EpisodeReceipts(family.store, owner.run_id)
    for context in (owner, child_context):
        journal.save('runtime_episodes', {'episode_id': context.episode_id, 'path': runtime._json(context.path),
            'request': runtime._json(context.request), 'initial_credit': 0, 'state': 'yielded',
            'completion': None, 'archive': None})
    receipts.bind(owner.episode_id)
    receipts.bind(child_context.episode_id, owner.episode_id)
    child.validate_report(child_context, form, schema)
    journal.save('runtime_forms', {'episode_id': child_context.episode_id,
        'facts': runtime._json({}), 'form': runtime._json(form)})
    child_before = journal.row('runtime_episodes', child_context.episode_id)
    form_before = journal.row('runtime_forms', child_context.episode_id)
    journal.save('runtime_actions', {'episode_id': owner.episode_id, 'decision_index': 0,
        'action': runtime._json({'kind': 'episode_child', 'role': role}), 'result': None, 'credit': None})
    def attempt(index, selected_child=child_context.episode_id):
        journal.save('runtime_report_attempts', {'parent_episode_id': owner.episode_id,
            'decision_index': index, 'delivery_ref': 'original-source-delivery',
            'child_episode_id': selected_child, 'contract': runtime._json(contract),
            'form': runtime._json(form), 'failure': None})
    attempt(0)
    progress, attributions = [], []
    source = SimpleNamespace(episode_id=owner.episode_id, path=owner.path, scope=plain(owner.scope))
    workflow = SimpleNamespace(store=family.store, journal=journal, run_id=owner.run_id,
        receipts=receipts, progress_provider=SimpleNamespace(receive_form=lambda *args: progress.append(args)),
        specialist=lambda source: parent, binding_context=lambda source: owner,
        is_job_source=lambda source: False, native_timing_information=None, job_episodes=None,
        episode_bindings=family.registry,
        receive_tool_attributions=lambda source, index, **kwargs: attributions.append((index, kwargs)) or [])
    workflow._receive_form = lambda *args, **kwargs: runtime.Workflow._receive_form(workflow, *args, **kwargs)
    first = runtime.Workflow.receive_form(workflow, source, form, schema, 0)
    assert family.source['id'] in first
    assert family.source['id'] in tuple(receipts.known(owner.episode_id))
    journal.save('runtime_actions', {'episode_id': owner.episode_id, 'decision_index': 0,
        'action': runtime._json({'kind': 'episode_child', 'role': role}),
        'result': runtime._json({'status': 'completed', 'record_refs': first}), 'credit': 0.0})
    assert runtime.Workflow.receive_form(workflow, source, form, schema, 0) == first
    assert len(progress) == len(attributions) == 1  # Actual admission cache, no patched reader.
    # Real saved redelivery selection/attempt. No runtime action or yield unit is invented.
    redelivery = {'kind': 'redeliver_report', 'delivery_ref': 'original-source-delivery',
        'purpose': contract['decision'], 'schema_json': json.dumps(schema)}
    journal.save('runtime_model_calls', {'episode_id': owner.episode_id, 'call_index': 1,
        'purpose': 'decision', 'request': '{}', 'response': runtime._json({'selection': redelivery})})
    attempt(1)
    assert runtime.Workflow.receive_form(workflow, source, form, schema, 1, redelivery=True) == first
    assert len(progress) == len(attributions) == 2
    assert journal.row('runtime_actions', owner.episode_id, 1) is None
    assert journal.row('runtime_episodes', child_context.episode_id) == child_before
    assert journal.row('runtime_forms', child_context.episode_id) == form_before
    assert family.store.db.execute('SELECT count(*) FROM runtime_record_receipts '
        'WHERE run_id=? AND episode_id=? AND record_ref=?',
        (owner.run_id, owner.episode_id, family.source['id'])).fetchone()[0] == 1
    if getattr(parent, 'child_report_receiver', None) is not None:
        foreign = replace(child_context, path=(('annotation', 'another-parent'), (role, 'child_0')),
            episode_id=EpisodeRef(owner.run_id, (('annotation', 'another-parent'), (role, 'child_0'))).episode_id)
        journal.save('runtime_episodes', {'episode_id': foreign.episode_id, 'path': runtime._json(foreign.path),
            'request': runtime._json(foreign.request), 'initial_credit': 0, 'state': 'yielded',
            'completion': None, 'archive': None})
        attempt(2, foreign.episode_id)
        with pytest.raises(runtime.WorkflowError, match='original_delivery_parent_conflict'):
            runtime.Workflow.receive_form(workflow, source, form, schema, 2, redelivery=True)




@pytest.mark.parametrize('home,role', HOMES)
def test_connected_original_renderer_receives_the_full_payload(family, tmp_path, home, role):
    binding, context = case(family, home, 'renderer-port')
    task_type = getattr(binding, 'decision_source_type', runtime.DecisionSource)
    task = object.__new__(task_type)
    task.episode_id = context.episode_id
    payload = {'literature_assignment': plain(context.assignment), 'complete_source': family.raw.decode(),
        'qualified_findings': [{'source_ref': family.source['id'], 'subject': 'synthetic assay sample',
            'qualification': 'target correspondence unresolved'}]}
    selected_schema = {'type': 'object', 'properties': {'selection': {'const': 'controlled'}},
        'required': ['selection'], 'additionalProperties': False}
    calls = []
    async def complete(episode_id, purpose, instructions, supplied, schema, *, prompt_renderer):
        calls.append((episode_id, purpose, instructions, supplied, schema, prompt_renderer))
        return {'selection': 'controlled'}
    provider = controlled_serial_model(controlled_config(), tmp_path / 'renderer-model', tmp_path, complete)
    task.workflow = SimpleNamespace(provider=provider, specialist=lambda source: binding)
    pending = (task.decision_completion()(task.episode_id, 'REASONING', 'exact instructions', payload, selected_schema)
        if hasattr(task, 'decision_completion') else task.complete_decision('exact instructions', payload, selected_schema))
    assert asyncio.run(pending) == {'selection': 'controlled'}
    assert calls == [(context.episode_id, 'REASONING', 'exact instructions', payload, selected_schema,
        binding.decision_prompt_renderer)]
    assert calls[0][3] is payload and calls[0][4] is selected_schema
