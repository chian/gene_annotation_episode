"""Controlled private-source boundaries; no model or autonomous-science claim."""
import asyncio
from contextlib import nullcontext
from importlib import import_module
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a107.domain import ContractError, identity
from gene_annotation_episode.episodic_workflow.root.a107.communication import plain
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext

SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'b' * 24
OTHER = 'source_' + 'c' * 24

def context(binding, assignment=None):
    ROLE = binding.roles[0]
    if assignment is None:
        page = {'version': 'page_assignment_v1', 'source_ref': SOURCE,
            'representation': 'original', 'artifact_ref': ARTIFACT,
            'question_context_refs': [], 'prior_delivery_refs': []}
        if ROLE == 'literature_page': assignment = page
        elif ROLE in {'literature_table', 'literature_ordered', 'literature_targeted'}:
            window = {'source_ref': SOURCE, 'representation': 'original', 'offset': 0, 'limit': 5}
            assignment = {'version': 'reading_assignment_v1', 'page': page,
                'selection': {'spans': [window]} if ROLE == 'literature_targeted' else window}
        else:
            version, field = {'literature': ('literature_assignment_v1', 'source_refs'),
                'literature_strategy': ('strategy_assignment_v1', 'prior_search_refs'),
                'literature_search': ('search_assignment_v1', 'search_result_refs')}[ROLE]
            assignment = {'version': version, 'question_context_refs': [], field: []}
    return BindingContext('run', 'episode', ROLE, ((ROLE, 'key'),), {}, assignment, {}, (SOURCE, ARTIFACT))

@pytest.fixture
def binding(home):
    Episode = import_module(home + '.episode').LiteratureEpisode
    db = sqlite3.connect(':memory:'); db.row_factory = sqlite3.Row
    records = {SOURCE: {'id': SOURCE, 'record_type': 'source', 'artifact_ref': ARTIFACT, 'parent_source_refs': []},
        ARTIFACT: {'id': ARTIFACT, 'record_type': 'artifact', 'size': 64},
        OTHER: {'id': OTHER, 'record_type': 'source', 'artifact_ref': ARTIFACT, 'parent_source_refs': []}}
    services = SimpleNamespace(workflow=SimpleNamespace(run_id='run', store=SimpleNamespace(db=db)),
        reference_in_scope=lambda ref, scope, namespace=None: ref in records,
        read_record=records.__getitem__, own_outcomes=lambda *args, **kwargs: [],
        tool_catalog=lambda scope: {'source.read': {'input_schema': {'type': 'object',
            'properties': {'source_ref': {'type': 'string'}, 'representation': {'enum': ['original']}},
            'required': ['source_ref', 'representation'], 'additionalProperties': False}}})
    value = Episode(services)
    yield value
    db.close()

def test_original_assignment_schema_is_preserved(binding):
    ROLE = binding.roles[0]
    expected = json.loads((Path(__file__).parent / 'fixtures/private_literature/original_assignment_schemas.json').read_text())[binding.binding_path]
    assert binding.assignment_schema(ROLE) == expected['schema']
    assert binding._validate_assignment(ROLE, context(binding).assignment, {}) == plain(context(binding).assignment)
    assert binding.roles == (ROLE,)
    with pytest.raises(ValueError, match='unsupported_literature_role'):
        binding.assignment_schema('scientific_process')

def test_private_task_and_messages_are_declared(binding):
    HOME = type(binding).__module__.rsplit('.', 1)[0]
    task = binding.decision_source_type
    assert task.__module__ == HOME + '.task'
    assert task.next.__module__ == HOME + '.task'
    assert task.execute.__module__ == HOME + '.task_action'
    assert task.finish.__module__ == HOME + '.task_report_delivery'
    assert binding.instructions.__module__ == HOME + '.goal'
    assert binding.validate_report.__module__ == HOME + '.to_parent'
    assert binding.credit_view.__module__ == HOME + '.credit'
    assert binding.permitted_common_actions(context(binding)) == ('tool', 'child', 'redeliver_report')
    assert binding.supports_wait is False

@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
def test_source_operation_keeps_returned_outcome(binding, status):
    returned = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': {'source_note': 'controlled read'}, 'feedback': None}
    calls = []
    def execute(name, arguments, **kwargs):
        calls.append((name, arguments, kwargs)); return returned
    binding.services.execute_tool = execute
    actual = asyncio.run(binding.execute(context(binding), 'source.read',
        {'source_ref': SOURCE, 'representation': 'original'}, 'original-operation'))
    assert actual is returned
    assert len(calls) == 1 and calls[0][2]['operation_key'] == 'original-operation'

def test_rejected_source_selection_does_not_execute(binding):
    calls = []
    binding.services.execute_tool = lambda *args, **kwargs: calls.append(args)
    actual = asyncio.run(binding.execute(context(binding), 'unavailable.operation', {}, 'rejected'))
    assert actual['status'] == 'invalid'
    assert actual['feedback']['code'] == 'tool_not_available_to_literature_role'
    assert calls == []

def test_explicit_partner_family_metadata_preserves_custody(binding):
    from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import LiteraturePartnerRepository
    from gene_annotation_episode.episodic_workflow.root.a107.library.literature_partner_sheet_records import PROVIDER
    assert not hasattr(binding, 'rate_population')
    ctx = context(binding)
    assert binding._owned_population_task_sources(ctx) == ()
    db = binding.services.workflow.store.db
    table = LiteraturePartnerRepository.operations_table
    db.execute(f'CREATE TABLE {table}(run_id TEXT, episode_id TEXT, operation_key TEXT, outcome TEXT)')
    metadata = {'id': SOURCE, 'record_type': 'source', 'origin': 'tool', 'provider': PROVIDER,
        'version': LiteraturePartnerRepository.record_version}
    binding.services.read_record = lambda ref: metadata
    outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': 'run', 'episode_id': 'episode', 'key': 'owned'}),
        'result': {'sheet_ref': SOURCE}, 'record_refs': [SOURCE]}
    db.execute(f'INSERT INTO {table} VALUES(?,?,?,?)', ('run', 'episode', 'owned', json.dumps(outcome)))
    assert binding._owned_population_task_sources(ctx) == ('literature_partner_cells',)
    outcome['operation_ref'] = 'operation_' + 'd' * 24
    db.execute(f'UPDATE {table} SET outcome=?', (json.dumps(outcome),))
    assert binding._owned_population_task_sources(ctx) == ()
    assert binding._population_task_context(ctx) == {'literature_owned_population_sources': ()}

class Journal:
    def __init__(self): self.rows = {}
    def row(self, table, episode, index): return self.rows.get((table, episode, index))
    def save(self, table, row): self.rows[(table, row['episode_id'], row['decision_index'])] = dict(row)
    def measure(self, *args): return nullcontext()

@pytest.mark.parametrize('status', ['completed', 'partial', 'invalid', 'failed', 'unavailable'])
def test_original_task_observes_returned_action_and_replays_without_reexecution(binding, status):
    # Real private execution method and its original outcome-observation policy;
    # controlled provider/credit ports isolate this changed ownership boundary.
    calls, events = [], []
    journal = Journal()
    outcome = {'status': status, 'record_refs': [], 'changed_record_refs': [], 'result': None,
        'feedback': None if status in {'completed', 'partial'} else {'code': 'controlled_failure'}}
    async def score(source, index, result): events.append('score'); return result
    def execute(*args, **kwargs): calls.append((args, kwargs)); return outcome
    workflow = SimpleNamespace(run_id='run', journal=journal, execution_binding=None, inprocess_replay=None,
        wait_inputs_version=None, completed_action_inputs_version=None,
        execute=execute, receive_native_outcome=lambda *args: events.append('native'),
        receive_outcome=lambda *args: events.append('receive'), automatic_score_updates=score,
        source_credit_view=lambda source: {'credit': 2.0}, controller_value=lambda source, index, credit: credit)
    task = object.__new__(binding.decision_source_type)
    task.workflow, task.path, task.scope, task.episode_id = workflow, ((binding.roles[0], 'key'),), {}, 'episode'
    task.feedback = task.last_outcome = task.last_outcome_index = None
    selection = {'kind': 'tool', 'tool': 'source.read', 'arguments': {'source_ref': SOURCE}}
    assert asyncio.run(task.execute(selection, 0)) == 2.0
    assert events == ['native', 'receive', 'score']
    assert len(calls) == 1
    assert json.loads(journal.row('runtime_actions', 'episode', 0)['result']) == outcome
    assert journal.row('runtime_actions', 'episode', 0)['credit'] == 2.0
    assert task.last_outcome_index == 0
    assert asyncio.run(task.execute(selection, 0)) == 2.0
    assert len(calls) == 1 and events == ['native', 'receive', 'score', 'native']

def test_injected_instruction_callback_retains_precedence(binding):
    supplied = []
    task = object.__new__(binding.decision_source_type)
    task.workflow = SimpleNamespace(services=SimpleNamespace(instructions=lambda source, context: supplied.append(context) or 'caller-selected'))
    assert task.instructions({'input': 'actual'}) == 'caller-selected'
    assert supplied == [{'input': 'actual'}]

def test_declared_provider_path_and_fallback(binding):
    # The actual current port captures complete before argument evaluation.
    # The original ModelConnection selects its declared private renderer;
    # replacing complete retains the caller's original callable and arguments.
    from gene_annotation_episode.episodic_workflow.root.a107.providers import ModelConnection
    calls = []
    provider = object.__new__(ModelConnection)
    provider.worker_lock = asyncio.Lock()
    async def declared(*args, **kwargs):
        calls.append((args, kwargs)); return {'chosen': 'declared'}
    provider._complete_serial = declared
    task = object.__new__(binding.decision_source_type); task.episode_id = 'episode'
    task.workflow = SimpleNamespace(provider=provider, specialist=lambda source: binding)
    arguments = ('episode', 'REASONING', 'instructions', {'state': 1}, {'schema': 1})
    assert asyncio.run(task.decision_completion()(*arguments)) == {'chosen': 'declared'}
    assert calls[0][1]['prompt_renderer'] is binding.decision_prompt_renderer
    async def fallback(*args): calls.append((args, {})); return {'chosen': 'fallback'}
    provider.complete = fallback
    captured = task.decision_completion()
    provider.complete = None
    assert asyncio.run(captured(*arguments)) == {'chosen': 'fallback'}
    assert calls[-1][0][:2] == ('episode', 'REASONING')
    assert all(left is right for left, right in zip(calls[-1][0], arguments))


"""Own source prompt/frame preservation through the real provider selector.

Only local presentation executes. No provider process, model or science runs.
"""
from copy import deepcopy
from importlib import import_module

from gene_annotation_episode.episodic_workflow.root.a107.decision_context import state_frame
from gene_annotation_episode.episodic_workflow.root.a107.providers import _SessionConnection
from gene_annotation_episode.episodic_workflow.root.a107.library.scientific_decision_presentation import text_instructions

@pytest.fixture
def present(home):
    return import_module(home + '.task_presentation').present_source_context

@pytest.fixture
def render(home):
    return import_module(home + '.task_reading_prompt').render_literature_experimental_prompt

def state():
    scope = {'subject_refs': []}
    return {'goal': {'objective': 'Inspect the actual source partner comparison.'},
        'scope': scope, 'working_state': {'subjects': [], 'scope': scope}, 'tools': [],
        'requested_form': None, 'controller': {}, 'current_report_update': {}, 'last_local_outcome': None,
        'literature_experimental_work': {'version': 'literature_experimental_task_v1', 'aspect': 'source_experimental_evidence'},
        'literature_assignment': {'version': 'literature_assignment_v1', 'source_refs': [], 'question_context_refs': [],
            'requested_partner_components': ['partner_loss_fraction']},
        'contract_information_profile': 'operation_contract_information_v1'}

def wire():
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    return connection

def test_actual_provider_routes_the_private_source_protocol(present, render):
    connection, supplied = wire(), state()
    before = deepcopy(supplied)
    assert present.presentation_protocol == 'episode_context_presentation_v1'
    assert connection._presentation('episode', 'REASONING', 'Source steering.', supplied,
        prompt_renderer=present) == (render(supplied, 'Source steering.'), text_instructions('Source steering.'))
    assert supplied == before

def test_source_full_bootstrap_delta_lookup_and_cold_reconstruction(present, render):
    connection = wire(); first = state(); second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'partial', 'result': {'source_note': 'Actual synthetic retained context; missing addback remains unknown.'}}
    instruction = 'Preserve the actual assayed subject and unresolved correspondence.'
    full, first_frame, second_frame = deepcopy(first), state_frame(first), state_frame(second, first)
    originals = deepcopy((full, first_frame, second_frame))
    assert present(connection, 'full', 'REASONING', instruction, full)[0] == render(first, instruction)
    assert present(connection, 'framed', 'REASONING', instruction, first_frame)[0] == render(first, instruction)
    assert present(connection, 'framed', 'REASONING', instruction, second_frame)[0] == render(second, instruction)
    result = {'status': 'completed', 'result': {'text': 'Source-bound selected operand contract.'}}
    pending = {'status': 'completed', 'result': {'text': 'Earlier pending contract.'}}
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result', 'decision_index': 1,
        'exchange_index': 1, 'result': result, 'pending_contract_information': [pending]}
    assert present(connection, 'framed', 'REASONING', instruction, lookup)[0] == render(second, instruction, lookup_results=[pending, result])
    restored = state_frame(second)
    restored['restored_public_exchanges'] = [{'lookup_result': pending}, {'lookup_result': result}]
    restored['restored_pending_decision_index'] = lookup['decision_index']
    assert present(wire(), 'cold', 'REASONING', instruction, restored)[0] == render(second, instruction, lookup_results=[pending, result])
    assert (full, first_frame, second_frame) == originals
    assert "dependence on a particular partner" in render(first, instruction)


"""Actual source schema/admission order and unchanged default callback behavior."""
from contextlib import nullcontext
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a107.runtime import Workflow

HOMES = ['gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment', 'gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment.evidence_search_strategy_improvement', 'gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment', 'gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination', 'gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction', 'gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement', 'gene_annotation_episode.episodic_workflow.root.a107.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.table_evidence_extraction', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.source_coverage_improvement', 'gene_annotation_episode.episodic_workflow.root.a107.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.passage_evidence_extraction']

def actual_source_schema(home):
    Episode = import_module(home + '.episode').LiteratureEpisode
    role, = Episode.roles
    services = SimpleNamespace(tool_catalog=lambda scope: {
        'source.read': {'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}},
        'reads.map': {'input_schema': {'type': 'object', 'properties': {}, 'additionalProperties': False}}},
        capabilities=lambda: {}, reasoning_commit_requirement=lambda: 'Original nonempty-commit requirement.')
    binding = Episode(services)
    family = home.split('.published_evidence_assessment')[0] + '.published_evidence_assessment'
    family_bindings = import_module(family + '.episode').create_binding_tree(services)
    by_role = {b.roles[0]: b for b in family_bindings}
    context = BindingContext('run', 'source', role, ((role, 'key'),), {'subject_refs': []}, {}, {}, ())
    workflow = object.__new__(Workflow)
    workflow.specialist = lambda source: binding
    workflow.binding_context = lambda source: context
    workflow.services = services
    workflow.is_job_source = lambda source: False
    workflow.annotation_child_roles = None
    workflow.project_credit = None
    workflow.scientific_process_binding = None
    workflow.job_episodes = None
    workflow.catalog = lambda scope, source=None: binding.catalog(context)
    workflow.root_child_return_sources = lambda source, role: ()
    workflow.episode_bindings = SimpleNamespace(roles=tuple(by_role), for_child=lambda path, role: by_role[role])
    source = SimpleNamespace(scope=context.scope, path=context.path, interpret_schema={'type': 'object', 'properties': {}, 'additionalProperties': False})
    return binding, workflow, source, context, Workflow.action_schema(workflow, source)

def test_exact_callbacks_are_configuration_capabilities_and_preserve_runtime_fallback(home):
    binding, workflow, source, context, schema = actual_source_schema(home)
    assert binding.reasoning_action_schema.__module__ == home + '.configuration'
    assert binding.accept_reasoning_action_schema.__module__ == home + '.configuration'
    assert binding.reasoning_has_task_content.__module__ == home + '.configuration'
    assert binding.execute_reasoning.__module__ == home + '.configuration'
    assert binding.reasoning_action_schema(context, {}) is None
    assert binding.accept_reasoning_action_schema(context, {}) is None
    assert binding.reasoning_has_task_content(context, {}) is False
    assert binding.execute_reasoning(context, {}, 'original-operation') is None
    commit = {'type': 'object', 'properties': {'claims': {'type': 'array'}}, 'required': ['claims'], 'additionalProperties': False}
    actual = Workflow.reasoning_action_schema(workflow, source, commit)
    workflow.specialist = lambda source: SimpleNamespace()
    expected = Workflow.reasoning_action_schema(workflow, source, commit)
    assert actual == expected
    assert actual['properties']['kind']['const'] == 'reason'

@pytest.mark.parametrize('selection', [
    {'kind': 'reason', 'commit': {}},
    {'kind': 'wait', 'condition': {}},
    {'kind': 'job_child', 'role': 'launch', 'goal': 'invalid source selection'},
    {'kind': 'tool', 'tool': 'reads.map', 'arguments': {}},
])
@pytest.mark.parametrize('recorded', [False, True])
def test_current_source_schema_rejects_before_acquisition_even_with_recorded_selection(home, selection, recorded):
    binding, workflow, declaration, context, schema = actual_source_schema(home)
    offered = schema['properties']['selection']['anyOf']
    assert not any(branch['properties'].get('kind', {}).get('const') in {'reason', 'wait', 'job_child'} for branch in offered)
    assert not any(branch['properties'].get('tool', {}).get('const') == 'reads.map' for branch in offered)
    module = import_module(home + '.task_action'); source = object.__new__(module.SourceTaskAction)
    source.workflow = workflow; source.episode_id = 'source'; source.scope = declaration.scope; source.path = declaration.path
    source._delivery_resolution_ref = None; source.report_values = {}; source.interpret_schema = declaration.interpret_schema
    effects = []; acquisitions = []
    source.record_effect = lambda index, effect: effects.append((index, effect))
    workflow.decision_exchanges = None; workflow.execution_binding = None
    workflow.store = SimpleNamespace(transaction=lambda: nullcontext())
    workflow.journal = SimpleNamespace(row=lambda table, *args: {'action': json.dumps(selection)} if recorded and table == 'runtime_actions' else None)
    workflow.selected = lambda *args: acquisitions.append(args)
    response = {'selection': selection, 'report_update': {}}
    assert source.apply_response(response, 0, {'visible_record_refs': []}, schema) is None
    assert source.feedback['status'] == 'invalid' and source.feedback['category'] == 'action_contract'
    assert effects == [(0, 'rejected')] and acquisitions == []

def test_legacy_selection_contract_still_preserves_job_acquisition_failure_identity():
    # A controlled permissive saved contract illustrates why present catalog
    # exclusion is not authority to erase the historical error handler. It is
    # not evidence that an original source workflow offered a job action.
    home = HOMES[0]
    binding, workflow, declaration, context, current = actual_source_schema(home)
    module = import_module(home + '.task_action'); source = object.__new__(module.SourceTaskAction)
    source.workflow = workflow; source.episode_id = 'source'; source.scope = declaration.scope; source.path = declaration.path
    source._delivery_resolution_ref = None; source.report_values = {}; source.interpret_schema = declaration.interpret_schema
    effects = []; source.record_effect = lambda index, effect: effects.append((index, effect))
    selection = {'kind': 'job_child', 'role': 'launch', 'existing_job_ref': 'job-original'}
    workflow.journal = SimpleNamespace(row=lambda table, *args: {'action': json.dumps(selection)} if table == 'runtime_actions' else None)
    workflow.decision_exchanges = None; workflow.execution_binding = None; workflow.store = SimpleNamespace(transaction=lambda: nullcontext())
    def unavailable(*args): raise OSError('controlled original acquisition failure')
    workflow.selected = unavailable
    schema = {'type': 'object', 'properties': {'selection': {'type': 'object'}, 'report_update': declaration.interpret_schema}}
    assert source.apply_response({'selection': selection, 'report_update': {}}, 0, {'visible_record_refs': []}, schema) is None
    assert source.feedback == {'status': 'failed', 'category': 'job_assignment', 'code': 'job_operation_failed', 'exception_type': 'OSError', 'role': 'launch', 'job_ref': 'job-original'}
    assert effects == [(0, 'rejected')]


from gene_annotation_episode.episodic_workflow.root.a107.state import Store
from copy import deepcopy

def source(store, raw, *, parents=(), text=False):
    artifact = store.artifact(raw)
    return store.put('source', {'provider': 'synthetic_native_partner_fixture',
        'accession': None, 'uri': None, 'artifact_ref': artifact,
        'text_ref': artifact if text else None, 'request_ref': None,
        'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')


def witness(row, raw, quote, *, offset=0, representation='original'):
    data = raw if isinstance(raw, bytes) else raw.encode()
    start = data.index(quote.encode(), offset)
    return {'source_ref': row['id'], 'representation': representation,
        'start': start, 'end': start + len(quote.encode()), 'quote': quote}


def selector(row, raw, token, *, offset=0):
    selected = witness(row, raw, token, offset=offset)
    return {'witness': selected, 'number_start': 0, 'number_end': len(token)}


def partner_fixture(path, *, mode='matched', page=True, extra_unit=False):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    records = {'ancestor': source(store, 'Synthetic provenance.')}
    records['root'] = source(store, b'\xff\x00Synthetic original binary source.',
        parents=[records['ancestor']['id']])
    omitted = '<0.005' if mode == 'censored' else '0.02'
    raw = ('SubjectS; PartnerP; PLP assay; product formation; per mg SubjectS; '
        'glutamine; ammonium_sulfate; temperature 37 degC; pH 8; '
        'physicalW; physicalO; physicalA; '
        f'W rate 0.1 nmol/min/mg ± 0.01 SD; O rate {omitted} nmol/min/mg; '
        'A rate 0.09 nmol/min/mg. All declared conditions matched.').encode()
    records['data'] = source(store, raw, parents=[records['root']['id']], text=True)
    data = records['data']
    w = lambda quote: witness(data, raw, quote)
    n = lambda token: selector(data, raw, token)
    unit = w('nmol/min/mg')
    if extra_unit:
        records['unit'] = source(store, 'Assay units: nmol/min/mg.', parents=[records['root']['id']])
        unit = witness(records['unit'], b'Assay units: nmol/min/mg.', 'nmol/min/mg')
    arms = {}
    for role, token, physical in (('reference', '0.1', 'physicalW'),
            ('omitted', '0.005' if mode == 'censored' else '0.02', 'physicalO'),
            ('addback', '0.09', 'physicalA')):
        arms[role] = {'subject': w('SubjectS'), 'partner': w('PartnerP'),
            'endpoint': w('product formation'), 'normalization': w('per mg SubjectS'),
            'partner_state': 'absent' if role == 'omitted' else 'present',
            'conditions': {'coverage': 'complete', 'factors': [
                {'factor': 'nitrogen_source', 'level': {'kind': 'literal', 'witness': w('glutamine')}},
                {'factor': 'temperature', 'level': {'kind': 'number', 'selector': n('37'), 'unit_witness': w('degC')}},
                {'factor': 'pH', 'level': {'kind': 'number', 'selector': n('8'), 'unit_witness': None}}]},
            'measurement_identity': w(physical), 'origin': 'synthetic',
            'rate': {'value': n(token), 'unit': deepcopy(unit), 'spread': {
                'kind': 'SD' if role == 'reference' else 'unreported',
                'magnitude': n('0.01') if role == 'reference' else None,
                'unit': None,
                'witnesses': [w('SD')] if role == 'reference' else []}}}
    if mode == 'crossed':
        arms['omitted']['conditions']['coverage'] = 'partial'
        arms['omitted']['conditions']['factors'][0]['level']['witness'] = w('ammonium_sulfate')
        arms['reference']['normalization'] = arms['omitted']['normalization'] = None
        arms['addback'] = None
    elif mode == 'missing':
        arms['addback'] = None
    elif mode == 'unknown_identity':
        arms['omitted']['measurement_identity'] = None
    elif mode == 'all_missing':
        arms = dict.fromkeys(('reference', 'omitted', 'addback'))
    literal_quotes = ('SubjectS', 'PartnerP', 'PLP assay', 'product formation',
        'per mg SubjectS', 'glutamine', 'ammonium_sulfate' if mode == 'crossed' else 'glutamine',
        'glutamine', 'PLP assay')
    fields = ('subject', 'partner', 'experiment', 'endpoint', 'normalization',
        'reference_condition', 'omitted_condition', 'addback_condition', 'function')
    args = {'source_ref': records['root']['id'], 'data_source_ref': data['id'],
        'source_kind': 'synthetic_fixture', 'literals': {field: w(quote) for field, quote in zip(fields, literal_quotes)},
        'interpretation_witnesses': [w('All declared conditions matched.')],
        'input_mode': 'native_source_spans', 'arms': arms}
    if mode == 'crossed':
        args['literals']['normalization'] = None
    context = BindingContext('synthetic-native-partner-run', 'native-child', 'literature',
        (('literature', 'fixture'),), store.validate_scope(),
        {'page': {'source_ref': records['root']['id']}} if page else {}, {},
        tuple(row['id'] for key, row in records.items() if key != 'ancestor'))
    return store, context, args, records



"""Real local A107 numerical/publication boundaries with declared synthetic inputs.

No external source, model, parent scientific inference or autonomy is exercised.
"""
from copy import deepcopy
from fractions import Fraction
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import LiteraturePartnerRepository
from gene_annotation_episode.episodic_workflow.root.a107.library import literature_partner_sheet_population as population
from gene_annotation_episode.episodic_workflow.root.a107.library import literature_sheet_updates as updates

ADAPTER = 'gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage:LiteraturePartnerRepository'

def test_original_population_and_repository_share_one_implementation():
    assert LiteraturePartnerRepository.populate is population.populate
    assert population.populate.__name__ == 'populate'
    assert population.populate._automatic_literature_updates is True
    assert LiteraturePartnerRepository.__module__ + ':' + LiteraturePartnerRepository.__name__ == ADAPTER

@pytest.mark.parametrize('mode', ['matched', 'missing', 'unknown_identity', 'all_missing', 'censored', 'crossed'])
def test_actual_saved_partner_values_and_partial_meanings(tmp_path, mode):
    store, context, args, records = partner_fixture(tmp_path, mode=mode)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        result = population.populate(repo, context, args, 'scientific-populate')
        reference = result['result']['sheet_ref']
        saved = repo.read(reference)
        rows = repo.project_cells([reference], permitted_record_refs=result['record_refs'])
        assert len(rows) == 8
        assert all(row['statistical_uncertainty'] == 'not_evaluated' for row in rows)
        assert all(row['partner_necessity'] == 'not_inferred' for row in rows)
        assert all(row['target_correspondence'] == 'not_evaluated' for row in rows)
        if mode == 'matched':
            assert [row['value'] for row in rows] == [100, 20, 90, 80, .8, 70, .875, .7]
            assert saved['extraction']['native_evidence']['reference']['rate']['value']['raw_number'] == '0.1'
        elif mode == 'missing':
            assert rows[4]['value'] == .8 and rows[6]['unavailable_reason'] == 'arm_unreported'
        elif mode == 'unknown_identity':
            assert rows[4]['unavailable_reason'] == 'measurement_identity_unreported'
        elif mode == 'all_missing':
            assert all(row['value'] is None for row in rows)
        elif mode == 'censored':
            assert rows[1]['value'] is None and (rows[1]['lower'], rows[1]['upper']) == (0, 5)
            fraction = next(row for row in rows if row['component'] == 'addback_fraction')
            assert Fraction(fraction['lower']) <= Fraction(85, 95)
            assert Fraction(fraction['upper']) >= Fraction(9, 10)
        elif mode == 'crossed':
            assert rows[0]['value'] == 100 and rows[1]['value'] == 20
            assert all(row['value'] is None for row in rows[3:])
        assert not store.list('observation') and not store.list('assessment')

def test_actual_publication_identity_current_sheet_update_and_exact_replay(tmp_path, monkeypatch):
    store, context, args, records = partner_fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        first = population.populate(repo, context, args, 'first-publication')
        first_reference = first['result']['sheet_ref']
        first_row = dict(store.db.execute(f'SELECT * FROM {updates.TABLE} WHERE sheet_ref=?', (first_reference,)).fetchone())
        first_receipt = json.loads(first_row['receipt'])
        assert first_row['adapter'] == first_receipt['scientific_calculator'] == ADAPTER
        assert first_row['method'] == 'populate'
        assert first_receipt['publication_operation_ref'] == first['operation_ref']
        assert first_receipt['returned_record_refs'] == {name: first[name] for name in ('record_refs', 'changed_record_refs')}
        assert updates.current_sheet_refs(store, context) == [first_reference]
        second = repo.populate(context, args, 'second-publication')
        assert second['result']['cells'] == first['result']['cells']
        assert second['result']['sheet_ref'] != first_reference
        assert updates.current_sheet_refs(store, context) == [second['result']['sheet_ref']]
        before = [tuple(row) for row in store.db.execute(f'SELECT * FROM {updates.TABLE} ORDER BY rowid')]
        def forbidden(*args, **kwargs): raise AssertionError('saved replay attempted source reading/calculation')
        monkeypatch.setattr(population, 'read_partner_inputs', forbidden)
        assert population.populate(repo, context, deepcopy(args), 'first-publication') == first
        assert repo.populate(context, deepcopy(args), 'second-publication') == second
        assert before == [tuple(row) for row in store.db.execute(f'SELECT * FROM {updates.TABLE} ORDER BY rowid')]
        assert store.db.execute(f'SELECT count(*) FROM {repo.operations_table}').fetchone()[0] == 2
        assert updates.current_sheet_refs(store, context) == [second['result']['sheet_ref']]
        # A107's original partner component policy has no separate main sheet.
        assert updates.current_scoring_sheets(store, context) == []

def test_actual_population_failure_rolls_back_operation_and_sheet(tmp_path, monkeypatch):
    store, context, args, records = partner_fixture(tmp_path)
    with store:
        repo = LiteraturePartnerRepository(store, context.run_id)
        before = [row['id'] for row in store.list('source')]
        def fail(*args, **kwargs): raise ValueError('controlled-publication-failure')
        monkeypatch.setattr(updates, '_register', fail)
        with pytest.raises(ValueError, match='controlled-publication-failure'):
            population.populate(repo, context, args, 'failed-publication')
        assert [row['id'] for row in store.list('source')] == before
        assert store.db.execute(f'SELECT count(*) FROM {repo.operations_table}').fetchone()[0] == 0
