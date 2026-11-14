"""Original root unit/replay diagnostic with genuine selected A105 bindings.

Only the constructor supplies an actual private tree. The diagnose body is the
unchanged project nonempty_outcome_support implementation; no child authority,
scientific evidence, returned failure, controller or stopping gate is fabricated.
"""
from contextlib import contextmanager
from dataclasses import fields, replace
import hashlib
import inspect
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.tests.nonempty_outcome_support import EstimateCaller, need, save


@contextmanager
def root_at(out, provider, *, initialize):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
    from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow
    from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import ConstructorTools, ActualRoot
    from gene_annotation_episode.episodic_workflow.root.tests.private_setup_support import validate_library_input, canonical_owner, ROOT
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.episode import ScientificProcessEpisode
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.episode import create_binding_tree
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_library import ScientificToolLibrary
    prefix = 'gene_annotation_episode.episodic_workflow.root.a105.'
    base = 'gene_annotation_episode/episodic_workflow/root/a105/'
    for value, name in ((ScientificProcessEpisode, 'scientific_process.episode'),
                        (ScientificProcessLibrary, 'scientific_process_library'),
                        (ScientificToolLibrary, 'scientific_tool_library')):
        canonical_owner(value, prefix + name, base + name.replace('.', '/') + '.py')
    fixture = (ROOT / 'tests/fixtures/fresh_decision_binding.json').read_bytes()
    need(hashlib.sha256(fixture).hexdigest() == '14abad6673f40e74f2494ed9dec06125d4883720d903a30596b47fcfe662b437',
         'original_root_binding_fixture_changed')
    binding = SignedRootEpisodeBinding.from_record(json.loads(fixture))
    tools = ConstructorTools()
    library = ScientificProcessLibrary.freeze(out / 'scientific_library', source=validate_library_input())
    tool_library = ScientificToolLibrary.freeze(out / 'tool_library', catalog=tools.catalog(), tool_info=True)
    captured = {}

    def head_factory(services):
        head = ScientificProcessEpisode(services, library=library, tool_library=tool_library,
            child_roles=('scientific_process', 'literature'), tool_retrieval=None)
        children = tuple(create_binding_tree(services))
        need(len(children) == 7 and all(item.services is services for item in (head, *children)),
             'genuine_private_tree_ports_changed')
        captured.update(head=head, children=children, services=services)
        return head

    def child_factory(index):
        def from_actual_tree(services):
            need(captured['services'] is services, 'private_tree_receiver_changed')
            return captured['children'][index]
        return from_actual_tree

    with Store(out / 'store') as store:
        if initialize:
            store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        scope = store.validate_scope()
        workflow = create_signed_evidence_root_workflow(store, tools, provider, out / 'workflow',
            'engineering-root-nonempty-outcome', binding.yield_controller,
            initial_known_record_refs=binding.initial_known_record_refs, project_credit=binding.task_credit,
            credit_binding=binding.task_credit.as_record(), controller_binding=binding.controller_record(),
            episode_binding_factories=(head_factory, *(child_factory(index) for index in range(7))),
            annotation_child_roles=('scientific_process',))
        need(workflow.scientific_process_binding is captured['head']
             and captured['head'].services is workflow.services
             and workflow.provider is provider and workflow.tools is tools,
             'actual_selected_binding_or_constructor_ports_changed')
        episode = workflow.build('annotation', 'root', 'Engineering nonempty root outcome connection', scope)
        episode.source.bind_execution_context(workflow.context)
        yield ActualRoot(store, binding, workflow, episode, tools, provider, scope)


async def diagnose(out, result):
    from gene_annotation_episode.episodic_workflow.root.task_values import _plain
    from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import action_rows
    provider = EstimateCaller()
    saved = None
    for label, initialize in (('original', True), ('replay', False)):
        result['stage'] = label + '_construction'
        with root_at(out, provider, initialize=initialize) as root:
            source, episode, ctx = root.source, root.episode, root.workflow.context
            row = result[label] = {'episode_id': source.episode_id, 'request': _plain(source.request),
                'scope': _plain(root.scope)}
            try:
                row['credit_before_unit'] = _plain(root.workflow.source_credit_view(source)['credit'])
                row['original_initial_credit'] = _plain(root.workflow.journal.row('runtime_episodes', source.episode_id)['initial_credit'])
                need(row['credit_before_unit'] == row['original_initial_credit'], 'initial_binding_credit_changed')
                catalog = root.workflow.catalog(root.scope, source=source)
                row['catalog'] = catalog
                need('shared.request_information' not in {item['name'] for item in catalog}, 'parentless_shared_route_unexpectedly_available')
                need('episode.estimate_wait' in {item['name'] for item in catalog}, 'actual_estimate_operation_unavailable')
                result['stage'] = label + '_actual_run_unit_async'
                captured = []
                original_hook = episode.on_unit
                need(callable(original_hook), 'original_observation_hook_required')

                async def capture_after_original(item, contribution, actual_unit_view):
                    callback_result = original_hook(item, contribution, actual_unit_view)
                    if inspect.isawaitable(callback_result):
                        callback_result = await callback_result
                    need(ctx.path == source.path and actual_unit_view.unit_ref.episode_id == source.episode_id,
                         'actual_observation_scope_identity_changed')
                    observed_view = episode._view(ctx, ctx.path, [],
                        unit_offset=actual_unit_view.unit_ref.unit_index + 1)
                    captured.append((observed_view, actual_unit_view))
                    return callback_result

                observed_episode = replace(episode, on_unit=capture_after_original)
                need(type(observed_episode) is type(episode) and all(
                    getattr(observed_episode, field.name) is getattr(episode, field.name)
                    for field in fields(episode) if field.name != 'on_unit'), 'observation_wrapper_changed_episode_operands')
                unit = await observed_episode.run_unit_async(ctx, expected_label='tool:0')
                need(len(captured) == 1, 'original_unit_hook_not_captured_exactly_once')
                view, captured_unit_view = captured[0]
                need(captured_unit_view.unit_ref == unit.unit_ref
                     and captured_unit_view.controller_input is unit.controller_input
                     and captured_unit_view.controller_step is unit.controller_step
                     and view.units_consumed == unit.unit_ref.unit_index + 1,
                     'captured_observation_differs_from_returned_unit')
                row['unit'] = _plain(unit)
                row['last_outcome'] = _plain(source.last_outcome)
                row['rows'] = action_rows(root)
                actions, observations, calls = (row['rows'][name] for name in
                    ('runtime_actions', 'runtime_observations', 'runtime_model_calls'))
                need(len(actions) == len(observations) == len(calls) == 1, 'nonunique_actual_unit_records')
                selected = json.loads(actions[0]['action'])
                response = provider.requests[0]['response']
                need(selected == response['selection'] and selected['tool'] == 'episode.estimate_wait', 'saved_action_changed')
                need(source.last_outcome == json.loads(actions[0]['result']), 'saved_outcome_changed')
                outcome = source.last_outcome
                need(outcome['status'] == 'completed' and outcome['record_refs'] == []
                     and outcome['changed_record_refs'] == [], 'estimate_did_not_return_original_completed_empty_references')
                estimate = outcome['result']
                need(estimate['version'] == 'wait_estimate_v1'
                     and estimate['condition'] == selected['arguments']['condition']
                     and estimate['condition']['events'] == []
                     and estimate['condition']['reconsider_at'] == provider.requests[0]['captured_utc']
                     and estimate['scientific_gain'] is None and estimate['monitoring_gain'] is None,
                     'estimate_changed_timestamp_or_invented_gain')
                observation = json.loads(observations[0]['observation'])
                need(observation['unit_ref'] == row['unit']['unit_ref']
                     and observation['credit'] == row['unit']['controller_input']
                     and observation['step'] == row['unit']['controller_step'], 'actual_observation_identity_changed')
                recorded_credit = root.workflow.journal.row('runtime_actions', source.episode_id, 0)['credit']
                need(_plain(recorded_credit) == observation['credit']['credit'], 'original_action_credit_not_observed')
                row['credit_after_unit'] = _plain(root.workflow.source_credit_view(source)['credit'])
                need(row['credit_before_unit'] == row['credit_after_unit'] == _plain(recorded_credit),
                     'estimate_changed_original_scientific_credit')
                # ReleasingContext has now removed the controller. Use only the
                # actual post-observation view captured before release, not reentry.
                row['next_view'] = {'units_consumed': view.units_consumed, 'path': _plain(view.path),
                    'controller_state': _plain(view.controller_state), 'episode_ref': _plain(view.episode_ref),
                    'request': _plain(view.request)}
                need(view.units_consumed == 1 and view.episode_ref.episode_id == source.episode_id,
                     'next_view_lost_actual_position')
                stable = {'request': row['request'], 'unit': row['unit'], 'outcome': row['last_outcome'],
                    'action': selected, 'observation': observation, 'model_request': calls[0]['request'],
                    'model_response': calls[0]['response']}
                if saved is None:
                    saved = stable
                    save(out / 'observed_original.json', row)
                else:
                    need(stable == saved and len(provider.requests) == 1, 'genuine_replay_changed_identity_or_called_provider')
                    save(out / 'observed_replay.json', row)
                    result['replayed_original_without_provider_call'] = True
                    result['stage'] = 'actual_next_decision_inputs_after_observation_and_replay'
                    context, schema = source._decision_inputs(view)
                    save(out / 'next_decision_inputs.json', {'context': context, 'schema': schema})
                    result['next_decision_inputs_completed'] = True
            finally:
                row['rows_at_exit'] = action_rows(root)
                row['selected_waits'] = [dict(item) for item in root.store.db.execute(
                    'SELECT * FROM episode_waits WHERE run_id=?', (root.workflow.run_id,))]
                row['timed_commissions'] = [dict(item) for item in root.store.db.execute(
                    'SELECT * FROM runtime_timed_commissions WHERE run_id=?', (root.workflow.run_id,))]
                row['tools_execution_calls'] = _plain(root.tools.execution_calls)
                result['provider_requests'] = provider.requests
                need(not root.tools.execution_calls and not row['selected_waits'] and not row['timed_commissions'],
                     'unexpected_external_tool_acquisition_or_wait_schedule')


"""Real root/A105 catalogs and one original root estimate unit; no science claim."""
import asyncio
from contextlib import contextmanager
from dataclasses import replace
import json
import sys
import traceback

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.composition_information import metadata_catalog
from gene_annotation_episode.episodic_workflow.root.tests.private_setup_support import actual_private_root, actual_rows
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_library import catalog as library_catalog
from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_library import catalog as retriever_catalog
from gene_annotation_episode.episodic_workflow.root.a105.scientific_support_metadata import annotation_policy_routes


@pytest.fixture(scope='module')
def private_root(tmp_path_factory):
    with actual_private_root(tmp_path_factory.mktemp('genuine-catalog')) as root:
        assert root.workflow.scientific_process_binding is root.head
        assert root.head.services is root.workflow.services
        yield root


@pytest.fixture
def root(private_root):
    before = actual_rows(private_root)
    credit = private_root.workflow.source_credit_view(private_root.episode.source)['credit']
    assert all(rows == [] for rows in before.values())
    yield private_root
    assert actual_rows(private_root) == before
    assert private_root.workflow.source_credit_view(private_root.episode.source)['credit'] == credit


@contextmanager
def actual_calls(function):
    """Observe the original function; never replace its call, result or errors."""
    events = []
    previous = sys.getprofile()
    def observe(frame, event, value):
        if frame.f_code is function.__code__ and event in ('call', 'return'):
            events.append((event, dict(frame.f_locals), value))
    try:
        sys.setprofile(observe)
        yield events
    finally:
        sys.setprofile(previous)


def test_selected_catalogs_use_original_private_owner_and_configuration(root):
    with actual_calls(library_catalog) as events:
        assert root.head.scientific_library_catalog() == library_catalog()
    assert len([row for row in events if row[0] == 'call']) == 2
    with actual_calls(retriever_catalog) as events:
        actual = root.workflow.scientific_retriever_catalog()
    calls = [row for row in events if row[0] == 'call']
    assert len(calls) == 1 and calls[0][1] == {'retrieval_mode': None, 'tool_info': True}
    assert actual == retriever_catalog(retrieval_mode=None, tool_info=True)


def test_unscoped_catalog_and_detached_composition_metadata_keep_actual_operations(root):
    expected = {entry['name']: entry for entry in library_catalog() + retriever_catalog(tool_info=True)}
    catalog = {entry['name']: entry for entry in root.workflow.catalog(root.episode.source.scope)}
    assert {name: catalog[name] for name in expected} == expected
    first = metadata_catalog(root.workflow, root.episode.source)
    assert {entry['name']: entry for entry in first if entry['name'] in expected} == expected
    next(entry for entry in first if entry['name'] == 'process.entry')['input_schema']['required'].clear()
    second = {entry['name']: entry for entry in metadata_catalog(root.workflow, root.episode.source)}
    assert second['process.entry'] == expected['process.entry']


@pytest.mark.parametrize('name,arguments,code', [
    ('process.entry', {'option_id': 'P99999'}, 'scientific_process_option_unknown'),
    ('process.entry', {}, 'scientific_process_arguments_invalid'),
    ('process.absent', {}, 'scientific_process_tool_unknown'),
], ids=['unknown-option', 'malformed-arguments', 'unknown-operation'])
def test_original_library_failures_return_unchanged_without_executed_unit(root, name, arguments, code):
    original = root.head.library.execute(name, arguments)
    assert original['status'] == 'failed' and original['result'] is None
    assert original['record_refs'] == original['changed_record_refs'] == []
    assert original['feedback'] == {'code': code, 'operation': name, 'exception_type': 'ValueError'}
    with actual_calls(type(root.head.library).execute) as events:
        result = root.head.execute_scientific_library(root.context, name, arguments)
    calls = [row for row in events if row[0] == 'call']
    assert len(calls) == 1 and calls[0][1]['self'] is root.head.library
    assert calls[0][1]['arguments'] is arguments
    assert result == original


def test_completed_original_instruction_entry_does_not_become_scientific_support(root):
    arguments = {'option_id': 'P01'}
    original = root.head.library.execute('process.entry', arguments)
    assert original['status'] == 'completed'
    assert root.head.execute_scientific_library(root.context, 'process.entry', arguments) == original
    assert 'annotation_support_routes' not in original['result']
    assert original['record_refs'] == original['changed_record_refs'] == []


def test_support_routes_keep_original_unavailable_qualification_and_receiver(root):
    workflow = root.workflow
    expected = annotation_policy_routes(workflow.project_annotation_score,
        workflow.annotation_score_binding, observation_kinds=[])
    with actual_calls(annotation_policy_routes) as events:
        actual = workflow.services.scientific_support_routes(root.context, observation_kinds=[])
    calls = [row for row in events if row[0] == 'call']
    assert len(calls) == 1
    assert calls[0][1]['projector'] is workflow.project_annotation_score
    assert calls[0][1]['annotation_score_binding'] is workflow.annotation_score_binding
    assert actual == expected and actual['status'] == 'unavailable'
    assert actual['annotation_binding_sha256'] is None and actual['routes'] == []
    with pytest.raises(ValueError, match='^scientific_support_routes_receiver_identity_mismatch$'):
        workflow.services.scientific_support_routes(replace(root.context, run_id='foreign-engineering-run'), observation_kinds=[])
    with pytest.raises(ValueError, match='^scientific_support_observation_kinds_invalid$'):
        workflow.services.scientific_support_routes(root.context, observation_kinds=['not-an-observation-kind'])


def test_root_rejects_undeclared_process_tool_before_acquisition(root):
    selection = {'kind': 'tool', 'tool': 'process.entry', 'arguments': {'option_id': 'P01'}}
    with pytest.raises(ValueError, match='^action_not_available_to_episode$'):
        root.workflow.selected(root.episode.source, selection, 0)


def test_actual_private_assignment_requires_received_proposed_annotation(root):
    assert root.workflow.services.annotation_task_required() is True
    received = root.store.reference_subset(root.context.received_record_refs, root.episode.source.scope)
    assert set(root.episode.source.scope["subject_refs"]).issubset(received)
    assert all(root.store.get(ref)["record_type"] != "hypothesis" for ref in received)
    selection = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': root.head.library.reference('A105'),
        'thought_pattern': root.head.library.reference('P01'), 'child_tool_info': []},
        'evidence_refs': [], 'constraints': {}, 'context': {}}
    with pytest.raises(ContractError, match='^scientific_task_requires_proposed_annotation$'):
        root.head.prepare_assignment(root.context, 'scientific_process', selection,
            root.episode.source.scope, root.workflow.run_id + ':' + root.episode.source.episode_id + ':0')


def test_original_root_estimate_unit_with_actual_private_tree_replays_and_presents(tmp_path):
    result = {'version': 'selected_private_catalog_root_unit_v1', 'status': 'blocked',
        'scripted_engineering_caller': True, 'scientific_or_autonomous_validation_claim': False,
        'private_scientific_unit_claim': False, 'estimated_timestamp_schedules_no_wait_or_timer': True,
        'replayed_original_without_provider_call': False, 'next_decision_inputs_completed': False}
    try:
        asyncio.run(diagnose(tmp_path, result))
        assert result['replayed_original_without_provider_call'] is True
        assert result['next_decision_inputs_completed'] is True
        assert len(result['provider_requests']) == 1
        assert result['original']['unit'] == result['replay']['unit']
        assert result['original']['last_outcome'] == result['replay']['last_outcome']
        presented = json.loads((tmp_path / 'next_decision_inputs.json').read_bytes())
        assert presented['context']['last_local_outcome'] == result['replay']['last_outcome']
        result['status'] = 'passed'
    except BaseException as error:
        result['error'] = {'type': type(error).__name__, 'detail': str(error), 'traceback': traceback.format_exc()}
        raise
    finally:
        save(tmp_path / 'diagnostic.json', result)


@pytest.mark.parametrize('arguments,status,code', [
    ({'option_id': 'P99999'}, 'failed', 'scientific_process_option_unknown'),
    ({}, 'invalid', 'composition_arguments_invalid'),
    ({'option_id': 'P01'}, 'completed', None),
], ids=['real-missing-option', 'invalid-metadata-arguments', 'original-instruction'])
def test_actual_root_metadata_dispatch_preserves_failed_invalid_and_completed_results(root, arguments, status, code):
    """Call the original metadata API; no pending exchange or executed unit claim."""
    result = asyncio.run(root.workflow.execute(root.episode.source, 'process.entry', arguments,
        decision_index=0, operation_key=root.workflow.run_id + ':' + root.episode.source.episode_id + ':0',
        _composition_lookup=True))
    assert result['status'] == status and result['record_refs'] == result['changed_record_refs'] == []
    if status == 'invalid':
        assert result == {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
            'feedback': {'category': 'decision_exchange', 'code': code}}
    else:
        assert result == root.head.library.execute('process.entry', arguments)
        if code is not None:
            assert result['feedback']['code'] == code
