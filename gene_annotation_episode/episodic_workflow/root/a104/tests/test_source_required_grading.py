"""Actual own-A104 grading, qualified publication and saved replay.

Scientific inputs are the authenticated original synthetic assay fixture. Only
the final numerical progress port is controlled, to observe publication order;
these tests do not assert biological support or replace commissioned credit.
The actual source admission, original source bytes, Store, original grader,
saved sheet, investigation finding and action journal remain real.
"""
import asyncio
import ast
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from .. import runtime
from ..communication import plain
from ..domain import ContractError, REASONING_SCHEMA, validate_schema
from ..episode_bindings import BindingContext
from ..episode_journal import Journal
from ..literature_assay_grading import COMPONENTS, CRITERIA_BY_TYPE
from ..literature_assay_grading_storage import (
    LiteratureAssayGradingRepository, REQUESTED, assay_grading_cells_schema)
from ..method_loop.identities import EpisodeRef
from .test_source_investigation_family import (
    HOMES, Services, assignment, binding_type, family as source_family, path_for)

ORIGINAL_FIXTURE_SHA = 'fbf450c8d8d606f76f832537e0b82a22ce5d1cb08cd1e7230d9ff58e460ba6cd'


@pytest.fixture
def family(tmp_path_factory):
    # The original synthetic fixture has stable record identities. Each case
    # needs its own real Store, as in the authentic fixture's original tests.
    # Preserve the complete existing factory, source bytes and actual services.
    yield from source_family.__wrapped__(tmp_path_factory)


@pytest.fixture(scope='module')
def original_grading_fixture():
    path = Path(__file__).parent / 'fixtures/source_grading/original_assay_grading_fixture.py.txt'
    raw = path.read_bytes(); assert hashlib.sha256(raw).hexdigest() == ORIGINAL_FIXTURE_SHA
    tree = ast.parse(raw)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'grading_fixture')
    # Only this exact retained fixture function runs. Its original A105-named
    # assay operands are used by the original A104 factory too; all executable
    # Store, schema and repository objects below are actual own-A104 objects.
    namespace = {'BindingContext': BindingContext, 'REQUESTED': REQUESTED,
        'COMPONENTS': COMPONENTS, 'CRITERIA_BY_TYPE': CRITERIA_BY_TYPE}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
        '<authenticated-original-synthetic-assay-fixture>', 'exec'), namespace)
    return namespace['grading_fixture']


def grading_case(family, original_grading_fixture, home, role, label, assay_type='endpoint_conversion'):
    original, arguments, artifact = original_grading_fixture(family.store, assay_type)
    source = family.store.get(arguments['source_ref'])
    selected = assignment(role, source)
    selected[REQUESTED] = []  # Requesting no immediate cells must not omit the sheet.
    run_id = 'a104-source-grading-' + label + '-' + home.replace('/', '_')
    path = path_for(home); episode_id = EpisodeRef(run_id, path).episode_id
    request = {'message': {'scope': plain(original.scope), 'episode_assignment': selected}}
    context = replace(original, run_id=run_id, episode_id=episode_id, role=role,
        path=path, assignment=selected, request=request)
    journal = Journal(family.store, run_id)
    journal.save('runtime_episodes', {'episode_id': episode_id, 'path': runtime._json(path),
        'request': runtime._json(request), 'initial_credit': 0, 'state': 'active',
        'completion': None, 'archive': None})
    services = Services(family.store, family.tools)
    services.workflow = SimpleNamespace(store=family.store, run_id=run_id)
    binding = binding_type(home)(services, rate_population=True, assay_grading_population=True)
    return context, arguments, artifact, binding, journal


def scientific_selection(store, context, arguments):
    experiment = store.get(arguments['experiment_ref'])
    hypothesis = store.get(arguments['assertion_ref'])
    finding = {'source_claim': {'subject_refs': [experiment['id']],
        'predicate': hypothesis['predicate'], 'value': hypothesis['value'], 'context_refs': []},
        'qualification': {'kind': 'different_source_subject', 'context_refs': [], 'assumption_refs': []},
        'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
        'same_source_claim_as_ref': None, 'replaces_refs': []}
    commit = {name: [] for name in REASONING_SCHEMA['required']}
    commit['observations'] = [{'alias': 'original_observation',
        'subject_refs': [context.scope['subject_refs'][0]], 'source_subject_refs': [experiment['id']],
        'kind': 'source_content', 'source_ref': arguments['source_ref'], 'measurements': [],
        'dependencies': [experiment['id']], 'anchor': experiment['anchor']}]
    commit['assessments'] = [{'alias': 'qualified_finding', 'hypothesis_ref': hypothesis['id'],
        'observation_ref': '@original_observation', 'relation': 'does_not_discriminate',
        'applicability': 'contextual', 'extent_basis': 'inferred_extent',
        'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0,
        'investigation_finding': finding}]
    return {'kind': 'reason', 'commit': commit, 'evidence_processing': {
        'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]}}, finding


@pytest.mark.parametrize('home,role', HOMES)
@pytest.mark.parametrize('partial_inputs', (False, True), ids=('complete-inputs', 'unresolved-inputs'))
def test_connected_same_action_sheet_and_qualified_finding_precede_progress_and_replay(
        family, original_grading_fixture, home, role, partial_inputs):
    context, arguments, _, binding, journal = grading_case(family, original_grading_fixture,
        home, role, 'publication-' + str(partial_inputs))
    if partial_inputs:
        arguments['quantities']['effect_variance'] = None
        arguments['interpretations']['attribution_supported'] = {'status': 'unknown', 'support_refs': []}
    selected, finding = scientific_selection(family.store, context, arguments)
    task_type = getattr(binding, 'decision_source_type', runtime.DecisionSource)
    task = object.__new__(task_type)
    task.episode_id, task.path, task.scope = context.episode_id, context.path, plain(context.scope)
    task.last_outcome = task.last_outcome_index = task.feedback = None
    task.checkpoint = lambda: None
    progress, receipts = [], []
    repository = binding._assay_grading_repository()
    def project(source):
        outcome = source.last_outcome
        assert outcome['status'] in ('completed', 'partial'), outcome
        assessment = family.store.get(outcome['aliases']['qualified_finding'])
        assert assessment['investigation_finding'] == finding
        assert assessment['relation'] == 'does_not_discriminate'
        grading = outcome['evidence_processing']['gradings'][0]
        sheet_ref = grading['result']['sheet_ref']; saved = repository.read(sheet_ref)
        assert saved['selection']['experiment_ref'] == arguments['experiment_ref']
        assert saved['selection']['assertion_ref'] == arguments['assertion_ref']
        assert sheet_ref in outcome['record_refs'] and grading['result']['cells'] == []
        cells = saved['sheet']['cells']
        assert cells['measured_effect']['value'] == 0.8
        if partial_inputs:
            assert cells['source_log_evidence_ratio']['value'] is None
            assert 'attribution_supported_unknown' in cells['source_log_evidence_ratio']['reasons']
        else:
            assert cells['source_log_evidence_ratio']['value'] == pytest.approx(7.5)
        # Explicit observation port: no fabricated commissioned scientific credit.
        progress.append((assessment['id'], sheet_ref)); return {'credit': 0.0}
    async def unchanged(source, index, outcome): return outcome
    workflow = SimpleNamespace(run_id=context.run_id, journal=journal, store=family.store,
        execution_binding=None, wait_inputs_version=None, completed_action_inputs_version=None,
        specialist=lambda source: binding, binding_context=lambda source: context,
        receive_native_outcome=lambda *args: None,
        receive_outcome=lambda source, selection, result, index: receipts.append(index),
        automatic_score_updates=unchanged, source_credit_view=project,
        controller_value=lambda source, index, credit: {'index': index, 'credit': credit})
    workflow.permits_common_action = lambda source, action: action in binding.permitted_common_actions(context)
    workflow._closed_child_commission = lambda *args: runtime.Workflow._closed_child_commission(workflow, *args)
    workflow.receipts = workflow.native_timing_information = workflow.inprocess_replay = None
    task.workflow = workflow
    unit = runtime.Workflow.selected(workflow, task, selected, 4)
    assert isinstance(unit, runtime.ActionLeaf) and unit.decision_index == 4
    result = asyncio.run(unit.acquire_async(None)).contribution.controller_input
    assert result == {'index': 4, 'credit': 0.0} and len(progress) == 1 and receipts == [4]
    before = journal.row('runtime_actions', context.episode_id, 4)
    assert json.loads(before['action']) == selected
    assert json.loads(before['result'])['aliases']['qualified_finding'] == progress[0][0]
    replay = runtime.Workflow.selected(workflow, task, selected, 4)
    assert asyncio.run(replay.acquire_async(None)).contribution.controller_input == result
    assert journal.row('runtime_actions', context.episode_id, 4) == before
    assert len(progress) == 1 and receipts == [4]


@pytest.mark.parametrize('home,role', HOMES)
@pytest.mark.parametrize('boundary', ('missing_finding', 'missing_grading'))
def test_connected_interpretation_admission_keeps_original_invalid_result_without_publication(
        family, original_grading_fixture, home, role, boundary):
    context, arguments, _, binding, _ = grading_case(family, original_grading_fixture,
        home, role, 'invalid-' + boundary)
    selected, _ = scientific_selection(family.store, context, arguments)
    if boundary == 'missing_finding': del selected['commit']['assessments'][0]['investigation_finding']
    else: del selected['evidence_processing']
    before = {kind: family.store.list(kind) for kind in ('observation', 'assessment')}
    result = binding.execute_reasoning(context, selected, context.episode_id + ':original-invalid')
    assert result['status'] == 'invalid' and result['record_refs'] == result['changed_record_refs'] == []
    assert result['feedback']['code'] == ('evidence_assessment_source_finding_required'
        if boundary == 'missing_finding' else 'applicable_evidence_requires_grading')
    assert {kind: family.store.list(kind) for kind in before} == before
    repository = binding._assay_grading_repository()
    if repository._installed(repository.operations_table):
        assert family.store.db.execute('SELECT count(*) FROM ' + repository.operations_table +
            ' WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()[0] == 0


@pytest.mark.parametrize('assay_type', ('activity_rate', 'endpoint_conversion', 'product_distribution', 'reaction_coupling'))
def test_connected_own_assay_repository_preserves_original_numerical_operands(
        family, original_grading_fixture, assay_type, monkeypatch):
    from .. import literature_assay_grading_storage as storage
    original, arguments, artifact = original_grading_fixture(family.store, assay_type)
    context = replace(original, run_id='a104-own-grader-' + assay_type)
    repository = LiteratureAssayGradingRepository(family.store, context.run_id)
    result = repository.populate(context, arguments, 'original-numerical-fixture')
    assert result['status'] in ('completed', 'partial'), result
    rows = result['result']['cells']; validate_schema(rows, assay_grading_cells_schema())
    values = {row['component']: row for row in rows}
    expected = {'measured_effect': 0.8, 'effect_precision': 25,
        'recovery_deviation': -0.1, 'attributed_fraction': 0.75,
        'condition_response': 0.8, 'source_log_evidence_ratio': 7.5}
    for key, value in expected.items(): assert values[key]['value'] == pytest.approx(value)
    assert values['source_log_evidence_ratio']['status'] == 'conditional'
    assert values['source_log_evidence_ratio']['input_origins'] == ['synthetic']
    # A new repository instance reuses the durable exact operation and sheet.
    # Re-reading input text or recalculating the numerical result is forbidden.
    def forbidden(*args, **kwargs): raise AssertionError('saved grading replay re-read or recalculated science')
    original_artifact = family.store.get_artifact
    def retained_other_artifact(reference):
        assert reference != artifact
        return original_artifact(reference)
    before = family.store.db.total_changes
    with monkeypatch.context() as patch:
        patch.setattr(storage, 'read_assay_grading_inputs', forbidden)
        patch.setattr(storage, 'grade_assay', forbidden)
        patch.setattr(LiteratureAssayGradingRepository, 'read_inputs', staticmethod(forbidden))
        patch.setattr(LiteratureAssayGradingRepository, 'grade', staticmethod(forbidden))
        patch.setattr(family.store, 'get_artifact', retained_other_artifact)
        family.store.db.execute('PRAGMA query_only=ON')
        try:
            fresh = LiteratureAssayGradingRepository(family.store, context.run_id)
            assert fresh.populate(context, arguments, 'original-numerical-fixture') == result
            assert fresh.read(result['result']['sheet_ref'])['sheet']['cells']['source_log_evidence_ratio']['value'] == pytest.approx(7.5)
            assert family.store.db.total_changes == before
        finally:
            family.store.db.execute('PRAGMA query_only=OFF')


@pytest.mark.parametrize('home,role', HOMES)
def test_connected_uncovered_observation_rolls_back_actual_sheet_and_interpretation(
        family, original_grading_fixture, home, role):
    context, arguments, artifact, binding, _ = grading_case(family, original_grading_fixture,
        home, role, 'uncovered-rollback')
    raw = family.store.get_artifact(artifact).decode()
    quote = 'Experiment B: effect 0.2 fraction; variance 0.09 fraction_squared.'
    offset = raw.index(quote)
    anchor = {'source_ref': arguments['source_ref'], 'artifact_ref': artifact,
        'start': offset, 'end': offset + len(quote), 'quote': quote}
    other = family.store.put('reference', {'reference_type': 'assay',
        'source_ref': arguments['source_ref'], 'accession': 'synthetic_distinct_assay_B',
        'label': 'Experiment B', 'sequence_ref': None, 'molecule': None, 'length': None,
        'term_refs': [], 'context_refs': [], 'anchor': anchor}, origin='caller')['id']
    context = replace(context, received_record_refs=(*context.received_record_refs, other))
    commit = {name: [] for name in REASONING_SCHEMA['required']}
    commit['observations'] = [{'alias': 'different_experiment_observation',
        'subject_refs': [context.scope['subject_refs'][0]], 'source_subject_refs': [other],
        'kind': 'source_content', 'source_ref': arguments['source_ref'],
        'measurements': [], 'dependencies': [other], 'anchor': anchor}]
    selected = {'kind': 'reason', 'commit': commit, 'evidence_processing': {
        'kind': 'graded', 'gradings': [{'arguments': json.dumps(arguments)}]}}
    before = {kind: family.store.list(kind) for kind in ('source', 'observation', 'assessment')}
    result = binding.execute_reasoning(context, selected, context.episode_id + ':uncovered')
    assert result['status'] == 'failed' and result['feedback']['code'] == 'required_grading_interpretation_uncovered'
    assert result['record_refs'] == result['changed_record_refs'] == []
    assert {kind: family.store.list(kind) for kind in before} == before
    repository = binding._assay_grading_repository()
    if repository._installed(repository.operations_table):
        assert family.store.db.execute('SELECT count(*) FROM ' + repository.operations_table +
            ' WHERE run_id=? AND episode_id=?', (context.run_id, context.episode_id)).fetchone()[0] == 0
