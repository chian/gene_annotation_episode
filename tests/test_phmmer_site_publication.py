"""Retained phmmer selected-site numbers and original engine-version custody.

The historical probe is real native output, parsed through HomologyResults.
Explicit journal fixtures establish the host boundary, not Workflow commissioning.
Altered original grades below are synthetic metadata corruption/absence fixtures.
"""
from copy import deepcopy
from dataclasses import replace
import builtins
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from gene_annotation_episode.alignment_site_calculators import calculate_reference_site_components
from gene_annotation_episode.alignment_site_native import source_descriptor
from gene_annotation_episode.alignment_site_returns import (
    requested_site_projections, project_site_action_return, validate_frozen_site_return,
)
from gene_annotation_episode.communication import (
    form_with_facts, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.homology_results import HomologyResults
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import (
    retain_tool_grading, source_tool_gradings,
)
from gene_annotation_episode.tools import ToolRegistry
from test_alignment_site_action_records import (
    REFERENCE, RUN, change_grading, page, perform, requested, saved_context, setup_case,
)
from test_homology_results import JOB, prepared, extract


POLICY = LocalJobPolicy(20 * 1024 ** 3, 4 * 1024 ** 3)
SELF = 'sp|P0AAW1|YBHP_ECOLI'
GAPPED = 'sp|A6H7I3|ANGE2_BOVIN'


def _example(name, value):
    directory = os.environ.get('EPISODE_PHMMER_SITES_EXAMPLES_DIR')
    if directory:
        path = Path(directory)
        path.mkdir(exist_ok=True, parents=True)
        (path / (name + '.json')).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


@pytest.fixture(scope='module')
def phmmer_base(tmp_path_factory):
    directory = tmp_path_factory.mktemp('retained_phmmer_base')
    store, _, inputs, scope = prepared(directory)
    adapter = HomologyResults(store, policy=POLICY)
    inputs = replace(inputs, domain_table=JOB / 'domains.tbl')
    with store:
        result = extract(adapter, inputs, scope, limit=100)
        assert result['status'] == 'completed', result
        assert len(result['result']['comparison_refs']) == 20
        alignments = {}
        for reference in result['result']['comparison_refs']:
            observed = store.get(reference)
            body = json.loads(store.get_artifact(store.get(observed['source_ref'])['artifact_ref']))
            alignments[(body['reference_id'], body['domain_index'])] = reference
        _example('retained_publication', {'evidence_class': 'retained_native_output',
            'result': result, 'policy': POLICY.to_dict(),
            'inputs': {name: str(getattr(inputs, name)) for name in
                ('query_fasta', 'reference_fasta', 'native_text', 'hit_table', 'domain_table')}})
    return store.path, alignments, scope


@pytest.fixture
def phmmer_case(tmp_path, phmmer_base):
    original, alignments, scope = phmmer_base
    shutil.copytree(original, tmp_path / 'state')
    with Store(tmp_path / 'state') as store:
        case = setup_case(store, ToolRegistry(store), scope=scope)
        case.alignments = alignments
        yield case


def _original(case, reference_id=SELF):
    observed = case.store.get(case.alignments[reference_id, 1])
    source = case.store.get(observed['source_ref'])
    grade, = source_tool_gradings(case.store, source['id'])
    return observed, source, grade


def _synthetic_original_grades(case, grades, reference_id=SELF):
    """Bind deliberately altered metadata to new, honestly synthetic records.

    Complete retained native alignment/operand bytes remain unchanged; no native
    execution, receipt or scientific measurement is invented by this fixture.
    """
    observed, original, _ = _original(case, reference_id)
    source_payload = {k: deepcopy(v) for k, v in original.items()
                      if k not in {'id', 'origin', 'record_type'}}
    source_payload['auxiliary_artifact_refs'] = [retain_tool_grading(case.store,
        provider=original['provider'], native_artifact_ref=original['artifact_ref'], grading=g)
        for g in grades]
    replacement = case.store.put('source', source_payload, origin=original['origin'])
    observation_payload = {k: deepcopy(v) for k, v in observed.items()
                           if k not in {'id', 'origin', 'record_type'}}
    observation_payload['source_ref'] = replacement['id']
    replacement_observation = case.store.put('observation', observation_payload,
        origin=observed['origin'], scope=case.scope)
    assert replacement['version'] == original['version']
    assert replacement['artifact_ref'] == original['artifact_ref']
    return replacement_observation, replacement


def _projection(case, context):
    schema = plain(context.request)['report_contract']['measurements']['schema']
    selection = requested_site_projections(schema)[REFERENCE]
    records = page(case, context)['records']
    return records, [project_site_action_return(record, selection['fields']) for record in records]


def _state(case):
    return {name: [tuple(row) for row in case.store.db.execute('SELECT * FROM ' + name + ' ORDER BY rowid')]
            for name in ('records', 'tool_operations', 'runtime_actions', 'runtime_observations')}


def test_retained_phmmer_engine_version_geometry_and_frozen_parent_form(phmmer_case, monkeypatch):
    case = phmmer_case
    original, source, native_grade = _original(case)
    original_before = deepcopy((original, source, native_grade))
    native = json.loads(case.store.get_artifact(source['artifact_ref']))
    engine = native_grade['sheet']['operation']['engine_version']
    assert isinstance(engine, str) and engine and engine != source['version']
    positions = [2, 0, 252, 2]
    schema = requested(policy='matching_alignment_position_set', alignment=original['id'],
                       positions=[0, 2, 252])
    validate_closed_schema(schema)
    context = saved_context(case, schema)
    result = perform(case, context, 1, 'sequence.sites',
        {'alignment_ref': original['id'], 'positions': positions})
    records, projected = _projection(case, context)
    record, = records
    grade = record['grading']
    sheet, scores = grade['sheet'], grade['scores']
    assert sheet['mode'] == 'native_phmmer_sequence_alignment'
    assert sheet['source'] == {'alignment_ref': original['id'], 'source_ref': source['id'],
        'native_artifact_ref': source['artifact_ref'], 'provider': 'native.phmmer.alignment',
        'format': 'native_phmmer_alignment_json', 'native_version': engine, 'native_locator': {}}
    assert sheet['native_input'] == native
    assert sheet['selection'] == {'kind': 'reference_positions', 'positions': positions}
    assert sheet['requested_positions'] == positions
    assert sheet['unique_requested_positions'] == [2, 0, 252]
    for role, refs in (('query', original['subject_refs']), ('reference', original['source_subject_refs'])):
        assert sheet['operands'][role] == {'subject_ref': refs[0], 'length': 253,
            'unit': 'aa', 'alignment_unit': 'aa', 'molecule': 'protein'}
    assert [row['query_interval'] for row in sheet['sites']] == [[2, 3], [0, 1], [252, 253], [2, 3]]
    assert [row['reference_interval'] for row in sheet['sites']] == [[2, 3], [0, 1], [252, 253], [2, 3]]
    assert [row['query_symbol'] for row in sheet['sites']] == ['D', 'M', 'L', 'D']
    assert [row['alignment_column'] for row in sheet['sites']] == positions
    assert all(row['relationship'] == 'identical' for row in sheet['sites'])
    summary = scores['summary']
    assert {k: summary[k] for k in ('requested_position_count', 'unique_requested_position_count',
        'duplicate_requested_position_count', 'paired_positions', 'identical_positions',
        'query_gap_positions', 'substituted_positions', 'selected_insertion_events')} == {
            'requested_position_count': 4, 'unique_requested_position_count': 3,
            'duplicate_requested_position_count': 1, 'paired_positions': 3,
            'identical_positions': 3, 'query_gap_positions': 0,
            'substituted_positions': 0, 'selected_insertion_events': 0}
    assert scores['ratios']['selected_paired_identity'] == {'numerator': 3, 'denominator': 3, 'value': 1.0}
    for role in ('query', 'reference'):
        assert scores['ratios'][f'selected_{role}_paired_coverage'] == {
            'numerator': 3, 'denominator': 253, 'value': 3 / 253}
    assert (case.store.get(original['id']), case.store.get(source['id']),
            source_tool_gradings(case.store, source['id'])[0]) == original_before
    assert record['binding']['native_artifact_ref'] == source['artifact_ref']
    assert record['arguments'] == {'alignment_ref': original['id'], 'positions': positions}
    assert record['availability'] == 'bound'
    returned, = projected
    assert returned['components']['selected_query_paired_coverage'] == {
        'value': 3 / 253, 'numerator': 3, 'denominator': 253, 'unit': 'fraction'}
    assert [row['reference_position'] for row in returned['rows']] == positions
    facts = {REFERENCE: projected}
    form = form_with_facts({}, schema, facts)
    validate_form(form, schema, lambda ref, namespace: ref in case.store.reference_subset([ref], case.scope)
                  and (namespace is None or case.store.get(ref)['record_type'] == namespace
                       or namespace == 'subject' and case.store.get(ref)['record_type'] in
                       {'input', 'feature', 'product', 'read_subject'}))
    case.journal.save('runtime_forms', {'episode_id': context.episode_id,
        'facts': canonical(facts), 'form': canonical(form)})
    frozen = case.service.frozen_facts(context, sources=(REFERENCE,))
    validate_frozen_site_return(form, schema, frozen)
    assert 'native_input' not in json.dumps(form) and 'grading_artifact_ref' not in json.dumps(form)
    _example('retained_self_sites', {'evidence_class': 'retained_native_host_boundary',
        'original_engine_version': engine, 'original_parser_version': source['version'],
        'sheet': sheet, 'scores': scores, 'own_action_record': record, 'form': form})
    before = _state(case)
    replay = case.tools.execute('sequence.sites', record['arguments'], scope=case.scope,
        operation_key=f'{RUN}:{context.episode_id}:1')
    assert replay == result and _state(case) == before
    assert _projection(case, context) == (records, projected)
    def forbidden(*args, **kwargs):
        pytest.fail('Frozen return reacquired or recalculated original native/site data')
    monkeypatch.setattr(case.service, 'own_action_results', forbidden)
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    validate_frozen_site_return(form, schema, case.service.frozen_facts(context, sources=(REFERENCE,)))
    assert _state(case) == before


def test_retained_phmmer_nonidentical_selected_window_and_full_gapped_numbers(phmmer_case):
    case = phmmer_case
    original, source, native_grade = _original(case, GAPPED)
    schema = requested(policy='matching_alignment_window', alignment=original['id'],
                       window={'start': 197, 'end': 203})
    context = saved_context(case, schema)
    perform(case, context, 1, 'sequence.sites',
        {'alignment_ref': original['id'], 'window': {'start': 197, 'end': 203}})
    records, projected = _projection(case, context)
    sheet, scores = records[0]['grading']['sheet'], records[0]['grading']['scores']
    assert [r['query_symbol'] for r in sheet['sites']] == list('RFILPE')
    assert [r['reference_symbol'] for r in sheet['sites']] == list('SFRFPN')
    assert [r['query_position'] for r in sheet['sites']] == list(range(26, 32))
    assert scores['summary']['identical_positions'] == 2
    assert scores['summary']['substituted_positions'] == 4
    assert scores['ratios']['selected_paired_identity'] == {'numerator': 2, 'denominator': 6, 'value': 2 / 6}
    assert scores['ratios']['selected_query_paired_coverage'] == {'numerator': 6, 'denominator': 253, 'value': 6 / 253}
    assert scores['ratios']['selected_reference_paired_coverage'] == {'numerator': 6, 'denominator': 544, 'value': 6 / 544}
    # All retained native gapped columns, not only the 12-row preview.
    full = case.tools.execute('sequence.sites', {'alignment_ref': original['id'],
        'window': {'start': 197, 'end': 354}}, scope=case.scope, operation_key='full-gapped-window')
    assert full['status'] == 'completed', full
    grade, = source_tool_gradings(case.store, full['result']['source_ref'])
    assert len(full['result']['sites']) == 12 and len(grade['sheet']['sites']) == 157
    assert grade['scores']['summary']['paired_positions'] == 147
    assert grade['scores']['summary']['query_gap_positions'] == 10
    assert grade['scores']['summary']['selected_insertion_events'] == 3
    assert grade['scores']['summary']['inserted_query_positions'] == 5
    assert grade['sheet']['source']['native_version'] == native_grade['sheet']['operation']['engine_version']
    assert source['version'] != grade['sheet']['source']['native_version']
    _example('retained_nonidentical_and_gapped_sites', {'evidence_class': 'retained_native_output',
        'selected_sheet': sheet, 'selected_scores': scores, 'selected_return': projected,
        'full_sheet': grade['sheet'], 'full_scores': grade['scores']})


@pytest.mark.parametrize('absence', ['grade', 'engine_version_key', 'engine_version_null'])
def test_missing_original_engine_metadata_stays_null_through_host(phmmer_case, absence):
    case = phmmer_case
    _, original_source, native_grade = _original(case)
    synthetic = deepcopy(native_grade)
    if absence == 'engine_version_key':
        del synthetic['sheet']['operation']['engine_version']
    elif absence == 'engine_version_null':
        synthetic['sheet']['operation']['engine_version'] = None
    observation, source = _synthetic_original_grades(case, [] if absence == 'grade' else [synthetic])
    assert source_descriptor(case.store, source, observation)['native_version'] is None
    context = saved_context(case, requested(policy='matching_alignment', alignment=observation['id']))
    perform(case, context, 1, 'sequence.sites', {'alignment_ref': observation['id'], 'positions': [0]})
    records, projected = _projection(case, context)
    assert records[0]['grading']['sheet']['source']['native_version'] is None
    assert records[0]['grading']['scores']['summary']['paired_positions'] == 1
    assert projected[0]['rows'][0]['relationship'] == 'identical'
    assert case.store.get(original_source['id']) == original_source
    assert source_tool_gradings(case.store, original_source['id']) == [native_grade]


@pytest.mark.parametrize('corruption,code', [('wrong_program', 'site_native_program_conflict'),
    ('ambiguous', 'site_native_version_ambiguous'), ('empty', 'site_native_version_invalid'),
    ('number', 'site_native_version_invalid'), ('boolean', 'site_native_version_invalid'),
    ('missing_operation', 'site_native_operation_invalid'),
    ('null_operation', 'site_native_operation_invalid'),
    ('string_operation', 'site_native_operation_invalid'),
    ('array_operation', 'site_native_operation_invalid')])
def test_wrong_or_ambiguous_original_engine_metadata_cannot_publish(phmmer_case, corruption, code):
    case = phmmer_case
    _, _, native_grade = _original(case)
    synthetic = deepcopy(native_grade)
    operation = synthetic['sheet']['operation']
    if corruption == 'missing_operation':
        del synthetic['sheet']['operation']
    elif corruption.endswith('_operation'):
        synthetic['sheet']['operation'] = {'null_operation': None,
            'string_operation': 'synthetic_invalid_operation', 'array_operation': []}[corruption]
    elif corruption == 'wrong_program':
        operation['program'] = 'hmmsearch'
    else:
        operation['engine_version'] = {'ambiguous': 'synthetic_other_engine', 'empty': '',
            'number': 3.4, 'boolean': True}[corruption]
    observation, source = _synthetic_original_grades(case,
        [native_grade, synthetic] if corruption == 'ambiguous' else [synthetic])
    with pytest.raises(ContractError, match=code):
        source_descriptor(case.store, source, observation)
    before = {kind: case.store.count(kind) for kind in ('source', 'observation')}
    outcome = case.tools.execute('sequence.sites', {'alignment_ref': observation['id'],
        'positions': [0]}, scope=case.scope, operation_key='rejected-original-metadata')
    assert outcome['status'] not in {'completed', 'partial'}
    assert outcome['feedback']['code'] == code
    assert {kind: case.store.count(kind) for kind in before} == before


@pytest.mark.parametrize('replacement', ['parser_version', 'other_engine_version', None])
def test_modified_saved_site_engine_version_rejected_by_original_host(phmmer_case, replacement):
    case = phmmer_case
    original, source, _ = _original(case)
    context = saved_context(case, requested(policy='matching_alignment', alignment=original['id']))
    perform(case, context, 1, 'sequence.sites', {'alignment_ref': original['id'], 'positions': [0, 2]})
    assert page(case, context)['records'][0]['availability'] == 'bound'
    value = source['version'] if replacement == 'parser_version' else replacement
    change_grading(case, context, 1, REFERENCE,
        lambda grade: grade['sheet']['source'].update(native_version=value))
    with pytest.raises(ValueError, match='alignment_site_return_sheet_source_conflict'):
        page(case, context)


def test_saved_phmmer_site_calculation_has_no_acquisition_execution_or_mutation(phmmer_case, monkeypatch):
    case = phmmer_case
    original, _, _ = _original(case, GAPPED)
    result = case.tools.execute('sequence.sites', {'alignment_ref': original['id'],
        'window': {'start': 197, 'end': 354}}, scope=case.scope, operation_key='saved-recalculation')
    assert result['status'] == 'completed', result
    grading, = source_tool_gradings(case.store, result['result']['source_ref'])
    sheet, scores = deepcopy(grading['sheet']), deepcopy(grading['scores'])
    before = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        pytest.fail('Saved selected-site calculation attempted I/O, acquisition or execution')
    with monkeypatch.context() as guard:
        for module, name in ((builtins, 'open'), (io, 'open'), (socket, 'socket'),
                             (subprocess, 'Popen'), (os, 'system')):
            guard.setattr(module, name, forbidden)
        guard.setattr(case.store, 'get_artifact', forbidden)
        guard.setattr(HomologyResults, 'extract', forbidden)
        guard.setattr(ToolRegistry, 'execute', forbidden)
        assert calculate_reference_site_components(sheet) == scores
    assert sheet == before


def test_tiny_real_phmmer_results_child_sites_child_and_parent_return(tmp_path, monkeypatch):
    """One genuine tiny job through the existing flat HomologyEpisodes route.

    Scripted decisions/zero credit are engineering fixtures. No fake receipt or
    preloaded alignment is used. This does not claim nested resource branching.
    """
    from gene_annotation_episode.episode_services import WorkflowServices
    from gene_annotation_episode.native_lifecycle import wait_job
    from gene_annotation_episode.runtime import Workflow
    from test_alignment_site_workflow import (
        _commission, _context, _controller, _descriptor, _redeliver_frozen, _run,
        _snapshot, _assert_action_counts, _assert_no_private_sheet,
    )
    from test_homology_episode_runtime import Provider, action, commission
    from test_resource_episode_branches import resources
    from test_sequence_views_integration import LocalOnly
    from test_tool_grading_child_returns import zero_fixture_credit
    generator = resources.__wrapped__(tmp_path)
    r = next(generator)
    try:
        assert r.policy == POLICY
        tools = ToolRegistry(r.store, clients=LocalOnly())
        directory = tmp_path / 'workflow'
        descriptor, library = _descriptor(directory, tools)
        captured = {}

        def acquire(current):
            handoff = current['child_reports'][-1]['job_handoff']
            finished = wait_job(r.jobs._handle(handoff['job_ref']))
            assert finished.returncode == 0
            captured['handoff'] = handoff
            return commission(r.homology, 'job_results', r.scope, handoff=handoff)

        def sites_child(current):
            alignment, = current['child_reports'][-1]['comparisons']
            assert alignment in set(workflow.receipts.known(parent.source.episode_id))
            captured['alignment_ref'] = alignment
            # The original parent form deliberately requests only these positions.
            schema = requested(policy='matching_alignment_position_set', alignment=alignment,
                               positions=[0, 2, 252])
            captured['schema'] = schema
            return _commission(library, r.scope, ['sequence.sites'], [r.query, alignment], schema)

        def select_sites(current):
            assert 'scientific_process' in current
            return action('sequence.sites', {'alignment_ref': captured['alignment_ref'],
                                           'positions': [2, 0, 252, 2]})

        launch = commission(r.homology, 'job_launch', r.scope, query_ref=r.query, cpu=2)
        launch['selection']['search_mode'] = 'native_defaults'
        decisions = Provider([launch, action('homology.environment'), action('homology.configure'),
            action('homology.stage'), action('homology.submit'), action('homology.check_handoff'),
            acquire, action('homology.extract', {'limit': 10}), sites_child, select_sites])
        workflow = Workflow(r.store, tools, decisions, directory, 'phmmer-site-workflow-291',
            _controller({'annotation': 3, 'job_launch': 5, 'job_results': 1, 'scientific_process': 1}),
            zero_fixture_credit, job_episodes=r.homology, episode_binding_descriptors=[descriptor],
            annotation_child_roles=('job_launch', 'job_results', 'scientific_process'),
            episode_record_receipts=True, initial_known_record_refs=[])
        parent = workflow.build('annotation', 'root', 'Compare selected protein correspondence', r.scope)
        assert workflow.catalog(r.scope, source=parent.source) == []
        assert not workflow.permits_common_action(parent.source, 'tool')
        assert not list(workflow.receipts.known(parent.source.episode_id, record_type='observation'))
        record = _run(parent, workflow)
        assert record.units_consumed == 3 and len(decisions.contexts) == 10
        child_row, = r.store.db.execute("SELECT * FROM runtime_episodes WHERE "
            "json_extract(path,'$[#-1][0]')='scientific_process'").fetchall()
        child_id = child_row['episode_id']
        assert captured['alignment_ref'] in set(workflow.receipts.known(child_id))
        saved = workflow.journal.row('runtime_forms', child_id)
        returned, frozen = json.loads(saved['form']), json.loads(saved['facts'])
        group, = returned['selected']
        assert returned['selected'] == frozen[REFERENCE]
        assert group['alignment_ref'] == captured['alignment_ref']
        assert [row['reference_position'] for row in group['rows']] == [2, 0, 252, 2]
        assert group['components']['paired_positions'] == group['components']['identical_positions'] == 3
        assert group['components']['duplicate_requested_position_count'] == 1
        assert group['components']['selected_query_paired_coverage'] == {
            'numerator': 3, 'denominator': 253, 'value': 3 / 253, 'unit': 'fraction'}
        _assert_no_private_sheet(returned)
        operation, = r.store.db.execute("SELECT * FROM tool_operations WHERE name='sequence.sites'").fetchall()
        result = json.loads(operation['result'])
        grade, = source_tool_gradings(r.store, result['result']['source_ref'])
        original = r.store.get(captured['alignment_ref'])
        original_source = r.store.get(original['source_ref'])
        original_grade, = source_tool_gradings(r.store, original['source_ref'])
        assert grade['sheet']['source']['native_version'] == original_grade['sheet']['operation']['engine_version']
        assert grade['sheet']['source']['native_version'] != original_source['version']
        assert r.jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert r.jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 1
        native_handle = r.jobs._handle(captured['handoff']['job_ref']).read()
        assert native_handle['metadata']['policy'] == POLICY.to_dict()
        assert native_handle['command'][native_handle['command'].index('--cpu') + 1] == '2'
        _assert_action_counts(r.store, parent.source.episode_id, 3)
        _assert_action_counts(r.store, child_id, 1)
        assert r.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 10
        assert r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 10
        assert r.store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0] == 10
        assert r.store.count('annotation') == 0
        parent_site_action, = [row for row in r.store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=?',
            (parent.source.episode_id,)) if json.loads(row['action'])['role'] == 'scientific_process']
        attempt, = r.store.db.execute('SELECT form FROM runtime_report_attempts '
            'WHERE parent_episode_id=? AND child_episode_id=?',
            (parent.source.episode_id, child_id)).fetchall()
        assert json.loads(attempt['form']) == returned
        for current in decisions.contexts:
            _assert_no_private_sheet(current.get('child_reports', []))
            assert 'hmmer_search_sheet_v1' not in json.dumps(current)
            assert 'reference_site_comparison_sheet_v1' not in json.dumps(current)
        _example('tiny_real_phmmer_workflow', {'evidence_class': 'fresh_tiny_local_native_full_workflow',
            'route': 'flat_HomologyEpisodes_job_launch_job_results_then_scientific_process',
            'native_handle': native_handle, 'original_source': original_source,
            'original_operation': original_grade['sheet']['operation'], 'sheet': grade['sheet'],
            'scores': grade['scores'], 'parent_form': returned,
            'parent_actions': 3, 'scientific_child_actions': 1, 'total_actions': 10})
        before = _snapshot(r.store)
        assert tools.execute('sequence.sites', json.loads(operation['arguments']), scope=r.scope,
            operation_key=operation['operation_key']) == result
        workflow.receive_form(parent.source, returned, captured['schema'],
                              parent_site_action['decision_index'], redelivery=True)
        assert _snapshot(r.store) == before
        def forbidden(*args, **kwargs):
            pytest.fail('Closed phmmer Workflow return accessed live grading or own-action data')
        monkeypatch.setattr(WorkflowServices, 'alignment_site_own_action_results', forbidden)
        import gene_annotation_episode.alignment_site_calculators as calculators
        monkeypatch.setattr(calculators, 'calculate_reference_site_components', forbidden)
        workflow.scientific_process_binding.validate_report(_context(workflow, child_id), returned, captured['schema'])
        _redeliver_frozen(workflow, parent, child_id, captured['schema'], returned, 3)
        assert _snapshot(r.store) == before and len(decisions.contexts) == 10
    finally:
        generator.close()
