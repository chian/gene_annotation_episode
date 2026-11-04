"""Continue the genuine355 pending prefix; repeat no model worker or solve.

The optional input is an original checkpoint, not a portable run bundle. Its
recorded Software and producer paths remain literal. Only the owned database,
archive, caches and newly selected saved-sheet worker are writable.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode import flux_balance_tools as ordinary
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.runtime import DecisionSource
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_flux_balance_ordinary_workflow import (FIELDS, QUESTION, RUN_ID, ScriptedProvider,
    _arguments, _byte_probe_source, _file_selection, _forbidden, _inventory, _json,
    _projection, _retained_file_refs, _tables, _workflow)
from test_scientific_process_runtime import action


def _readonly_store(directory):
    """Use actual Store initialization attributes without its writable setup."""
    store = Store.__new__(Store)
    store.path = Path(directory).resolve(strict=True)
    store.db = sqlite3.connect((store.path / 'state.sqlite3').as_uri() + '?mode=ro&immutable=1', uri=True)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    return store


def _clone_checkpoint(original, checkpoint, destination):
    destination.mkdir()
    copied_store = destination / 'store'
    copied_store.mkdir()
    connection = sqlite3.connect(copied_store / 'state.sqlite3')
    try:
        original.db.backup(connection)
    finally:
        connection.close()
    for name in ('artifacts', 'cache'):
        if (checkpoint / 'store' / name).exists():
            shutil.copytree(checkpoint / 'store' / name, copied_store / name)
    for name in ('run', 'source', 'native-workspace'):
        shutil.copytree(checkpoint / name, destination / name)
    return copied_store


def _retained_configuration(store, episodes):
    """Recover the actual declaration, without refreshing a scientific library."""
    operations = list(store.db.execute('SELECT * FROM tool_operations ORDER BY operation_key'))
    assert len(operations) == 3
    arguments = [json.loads(row['arguments']) for row in operations]
    outcomes = [json.loads(row['result']) for row in operations]
    assert [value['mode'] for value in arguments] == ['inspect', 'edit', 'solve']
    assert all(value['status'] in {'completed', 'partial'} for value in outcomes)
    sources = [store.get(value['result']['source_ref']) for value in outcomes]
    capsules = [_json(store, source['request_ref']) for source in sources]
    selected = deepcopy(capsules[0]['prepared']['selected'])
    assert selected['binding_ordinal_0based'] == 0
    assert all(capsule['prepared']['selected'] == selected for capsule in capsules)
    policy = capsules[2]['prepared']['native']['metadata']['policy']
    assert policy == POLICY
    assert all(capsule['prepared']['model']['execution']['metadata']['policy'] == policy
        for capsule in capsules[:2])
    resources = {selected['resource_id']: {'kind': 'local', 'workspace': selected['workspace'],
        'policy': deepcopy(policy), 'native_flux_balance': [deepcopy(selected['binding'])]}}
    environments = [{'resource_id': selected['resource_id'], 'binding_ordinal_0based': 0,
        'environment': deepcopy(selected['environment'])}]
    requests = [json.loads(row['request']) for row in episodes]
    mechanics = requests[1]['message']['scientific_process']['mechanics_binding']
    descriptors = [deepcopy(mechanics), LiteratureEpisodes(None).as_record()]
    original, = [row['file'] for row in capsules[0]['prepared']['resolved_inputs']]
    return resources, environments, descriptors, deepcopy(original), operations, outcomes, capsules


def test_genuine_pending_fba_continuation_saved_calculation_and_closed_replay(tmp_path, monkeypatch):
    supplied = os.environ.get('HMMER_NATIVE_ORACLE_FBA_PENDING_CHECKPOINT')
    if not supplied:
        pytest.skip('requires an explicitly supplied genuine original FBA pending checkpoint')
    checkpoint = Path(supplied).expanduser().resolve(strict=True)
    original_root = checkpoint.parent
    checkpoint_before, original_before = _inventory(checkpoint), _inventory(original_root)
    original = _readonly_store(checkpoint / 'store')
    try:
        before_tables = _tables(original)
        episodes = list(original.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2 and all(row['state'] == 'active' for row in episodes)
        assert {row['run_id'] for row in episodes} == {RUN_ID}
        assert [json.loads(row['path'])[-1][0] for row in episodes] == ['annotation', 'scientific_process']
        parent_request, science_request = [json.loads(row['request']) for row in episodes]
        assert parent_request['goal']['objective'] == science_request['goal']['objective'] == QUESTION
        scope = parent_request['message']['scope']
        assert scope == science_request['message']['scope']
        pending, = list(original.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? AND result IS NULL',
            (episodes[1]['episode_id'],)))
        pending_selection = json.loads(pending['action'])
        assert pending['decision_index'] == 2 and pending['credit'] is None
        assert pending_selection['tool'] == ordinary.FBA_TOOL and pending_selection['arguments']['mode'] == 'solve'
        prefix_counts = {name: original.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
            ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls',
                'tool_operations', 'runtime_forms', 'runtime_report_attempts')}
        assert prefix_counts == dict(runtime_episodes=2, runtime_actions=4, runtime_observations=2,
            runtime_model_calls=4, tool_operations=3, runtime_forms=0, runtime_report_attempts=0)
        resources, environments, descriptors, original_file, operations, prefix_outcomes, prefix_capsules = (
            _retained_configuration(original, episodes))
        assert json.loads(operations[2]['arguments']) == pending_selection['arguments']
        pending_key = f'{RUN_ID}:{pending["episode_id"]}:{pending["decision_index"]}'
        assert operations[2]['operation_key'] == pending_key
        copied_store = _clone_checkpoint(original, checkpoint, tmp_path / 'owned-continuation')
        assert original.db.total_changes == 0
    finally:
        original.close()

    monkeypatch.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    monkeypatch.setattr(ordinary, 'run_selected_flux_balance_native', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.flux_balance_model_execution.run_selected_flux_balance_model', _forbidden)
    worker_calls, actual_worker = [], ordinary.run_selected_flux_balance_result_worker
    def selected_saved_worker(store, *, plan, software, policy):
        assert plan['mode'] == 'saved_sheet_recalculation'
        worker_calls.append({'plan': deepcopy(plan), 'software_sha256': digest(software)})
        return actual_worker(store, plan=plan, software=software, policy=policy)
    monkeypatch.setattr(ordinary, 'run_selected_flux_balance_result_worker', selected_saved_worker)
    with Store(copied_store) as store:
        assert _tables(store) == before_tables
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, flux_balance_environments=environments)
        factory.configure_tool_registry(tools)
        case = SimpleNamespace(store=store, directory=copied_store.parent / 'run',
            source=copied_store.parent / 'source', descriptors=descriptors, scope=deepcopy(scope))
        application = factory(store, run_id=RUN_ID, directory=case.directory, tool_registry=tools)
        state = {'visible_outcomes': []}
        def previous(context, mode):
            outcome = context['last_local_outcome']
            assert outcome['status'] in {'completed', 'partial'} and outcome['result']['mode'] == mode
            state['visible_outcomes'].append(deepcopy(outcome))
            return outcome['result']
        def choose_read_one(context):
            solved = previous(context, 'solve')
            state['solve_source'] = solved['source_ref']
            state['saved_sheet'], = deepcopy(solved['saved_sheets'])
            return {**action(ordinary.FBA_TOOL, {**_arguments('read_stored'), 'result_ref': solved['source_ref'],
                'view': {'kind': 'measurement', 'selector': _projection('bounds')}}),
                'report_update': {'solve_source': solved['source_ref']}}
        def choose_read_two(context):
            actual = previous(context, 'read_stored')
            assert actual['source_ref'] == state['solve_source']
            return action(ordinary.FBA_TOOL, {**_arguments('read_stored'), 'result_ref': actual['source_ref'],
                'view': {'kind': 'measurement', 'selector': _projection('population')}})
        def choose_saved_calculation(context):
            actual = previous(context, 'read_stored')
            assert actual['source_ref'] == state['solve_source']
            return action(ordinary.FBA_TOOL, {**_arguments('calculate_saved'),
                'sheet': _file_selection(state['saved_sheet']),
                'calculation_parameters': deepcopy(pending_selection['arguments']['calculation_parameters']),
                'projection': _projection('native_values'), 'return_saved_sheet': False})
        provider = ScriptedProvider([choose_read_one, choose_read_two, choose_saved_calculation])
        workflow = _workflow(case, tools, provider, application, original_file)
        assert _tables(store) == before_tables
        root = workflow.build('annotation', 'root', QUESTION, case.scope)
        record = asyncio.run(root.run_async(workflow.context))
        final_result = asyncio.run(root.build_result(record)).as_record()
        assert len(provider.contexts) == 3 and len(worker_calls) == 1
        episodes = list(store.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2 and all(row['state'] == 'yielded' for row in episodes)
        parent_id, science_id = (row['episode_id'] for row in episodes)
        rows = list(store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? ORDER BY decision_index', (science_id,)))
        selections, outcomes = [json.loads(row['action']) for row in rows], [json.loads(row['result']) for row in rows]
        assert len(rows) == 6 and all(value['tool'] == ordinary.FBA_TOOL for value in selections)
        assert [value['arguments']['mode'] for value in selections] == ['inspect', 'edit', 'solve', 'read_stored', 'read_stored', 'calculate_saved']
        assert all(value['status'] in {'completed', 'partial'} for value in outcomes)
        assert [{k: v for k, v in value.items() if k != 'pending_work_after_action'}
            for value in outcomes[:3]] == prefix_outcomes
        assert [dict(row) for row in store.db.execute('SELECT * FROM tool_operations ORDER BY operation_key')][:3] == [dict(row) for row in operations]
        counts = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in prefix_counts}
        assert counts == dict(runtime_episodes=2, runtime_actions=7, runtime_observations=7,
            runtime_model_calls=7, tool_operations=6, runtime_forms=1, runtime_report_attempts=1)
        assert not store.list('native_execution')
        assert outcomes[3]['result']['source_ref'] == outcomes[4]['result']['source_ref'] == outcomes[2]['result']['source_ref']
        assert outcomes[3]['result']['measurements'][0]['selector'] != outcomes[4]['result']['measurements'][0]['selector']
        published = {mode: store.get(outcomes[index]['result']['source_ref'])
            for mode, index in [('inspect', 0), ('edit', 1), ('solve', 2), ('calculate_saved', 5)]}
        capsules = {mode: _json(store, source['request_ref']) for mode, source in published.items()}
        assert [capsules[mode] for mode in ('inspect', 'edit', 'solve')] == prefix_capsules
        assert len({source['id'] for source in published.values()}) == 4
        software = resources['ordinary-selected']['native_flux_balance'][0]['software']
        units = []
        for mode in ('inspect', 'edit'):
            model = capsules[mode]['prepared']['model']
            assert model['result']['model_optimize_call_count'] == 0
            assert model['execution']['returncode'] == 0 and model['execution']['failure'] is None
            assert model['execution']['observation']['terminal'] is model['execution']['observation']['quiescent'] is True
            assert model['execution']['metadata']['policy'] == POLICY
            assert model['handle']['command'][0] == software['python']['path']
            units.append(model['handle']['unit'])
        native = capsules['solve']['prepared']['native']
        assert native['terminal'] is native['quiescent'] is True and native['returncode'] == 0 and native['failure'] is None
        assert native['plan']['requested_job']['native_flux_balance']['objective'] == {'kind': 'single_reaction', 'reaction_id': 'BC'}
        assert native['plan']['requested_job']['native_flux_balance']['software'] == software
        assert native['metadata']['policy'] == POLICY and native['handle']['command'][0] == software['python']['path']
        units.append(native['handle']['unit'])
        for mode in ('solve', 'calculate_saved'):
            selected = capsules[mode]['prepared']['selected']
            assert selected == prefix_capsules[2]['prepared']['selected']
            worker = capsules[mode]['prepared']['worker']
            assert worker['execution']['terminal'] is worker['execution']['quiescent'] is True
            assert worker['execution']['returncode'] == 0 and worker['execution']['failure'] is None
            assert worker['execution']['metadata']['policy'] == POLICY
            worker_python = Path(worker['execution']['handle']['command'][0])
            assert worker_python.stat().st_size == software['python']['size_bytes']
            assert hashlib.sha256(worker_python.read_bytes()).hexdigest() == software['python']['sha256']
            units.append(worker['execution']['handle']['unit'])
        assert len(units) == len(set(units)) == 5
        assert worker_calls[0]['plan'] == capsules['calculate_saved']['prepared']['worker']['plan']
        assert worker_calls[0]['software_sha256'] == digest(software)
        assert Path(worker_calls[0]['plan']['directory']).is_relative_to(copied_store)
        assert units[-1] not in units[:-1]
        sheet, calculations = capsules['solve']['sheet'], capsules['solve']['calculations']
        assert sheet['native']['solve_call_count'] == sheet['native_solution']['native']['model_optimize_call_count'] == 1
        assert calculations['objective']['native_cobra']['state'] == 'present' and calculations['objective']['native_cobra']['value'] == 0
        assert capsules['calculate_saved']['sheet'] == sheet
        assert capsules['calculate_saved']['prepared']['worker']['plan']['mode'] == 'saved_sheet_recalculation'
        original_raw = store.get_artifact(original_file['artifact_ref'])
        assert hashlib.sha256(original_raw).hexdigest() == original_file['sha256']
        edited, = outcomes[1]['result']['edited_models']
        edited_native = json.loads(store.get_artifact(edited['artifact_ref']))
        edited_reactions = {row['id']: row for row in edited_native['reactions']}
        assert edited_reactions['AB']['lower_bound'] == edited_reactions['AB']['upper_bound'] == 0
        assert edited_reactions['BC']['objective_coefficient'] == 1
        assert [row['id'] for row in edited_native['metabolites']] == ['A', 'B', 'C']
        returned = json.loads(store.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?', (science_id,)).fetchone()[0])
        assert returned['solve_source'] == state['solve_source']
        assert len(returned['model_views']) == 2 and len(returned['measurements']) == 4
        assert returned['edited_models'] == [edited] and returned['saved_sheets'] == [state['saved_sheet']]
        for outcome in outcomes:
            for field in ('measurements', 'model_views'):
                assert all(value in returned[field] for value in outcome['result'][field])
        reaction_view = outcomes[3]['result']['measurements'][0]
        assert [row['reaction_id'] for row in reaction_view['rows']] == ['AB', 'BC']
        for row in reaction_view['rows']:
            assert row['values']['flux']['flux']['state'] == 'present' and row['values']['flux']['flux']['value'] == 0
            assert row['values']['flux']['unit'] == {'native_text': None, 'basis': 'unknown'}
        assert reaction_view['rows'][0]['values']['bounds']['lower']['value'] == reaction_view['rows'][0]['values']['bounds']['upper']['value'] == 0
        contexts = EpisodeReturnRecords(store, RUN_ID, failure_prefix='ordinary_fba_retained_')
        parent, science = contexts.context(parent_id), contexts.context(science_id)
        receiving = workflow.episode_bindings.received_report_facts(parent)
        for field, source in FIELDS.items():
            assert receiving[source] == returned[field]
        known = set(workflow.receipts.known(parent_id))
        assert {state['solve_source'], edited['artifact_ref'], state['saved_sheet']['artifact_ref']} <= known
        for source in published.values():
            assert source['request_ref'] not in known and source['artifact_ref'] not in known
            denied, path = workflow.services.read_received_molecular_input(parent, source['request_ref'], 'artifact',
                file_format=ordinary.CAPSULE_VERSION)
            assert path is None and denied['failure'] is not None
        worker = capsules['solve']['prepared']['worker']
        private_files = {name: worker['files'][name] for name in ('calculations', 'projection')}
        private_files.update(worker_plan=worker['capture']['plan_file'], worker_execution=worker['capture']['execution_receipt_file'])
        private_refs = {name: (file['artifact_ref'], file['format']) for name, file in private_files.items()}
        private_refs['solve_capsule'] = (published['solve']['request_ref'], ordinary.CAPSULE_VERSION)
        allowed_files = {'original_input': original_file, 'edited_model': edited, 'saved_sheet': state['saved_sheet']}
        private_wrappers = {name: _byte_probe_source(store, ref, 'private_' + name) for name, (ref, _) in private_refs.items()}
        public_wrappers = {name: _byte_probe_source(store, file['artifact_ref'], 'received_' + name) for name, file in allowed_files.items()}
        receipt_prefixes = {context.episode_id: set(workflow.receipts.known(context.episode_id)) for context in (parent, science)}
        permission_counts = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in counts}
        for context in (parent, science):
            scope = plain(context.scope)
            resolve = workflow.resolver(scope, context=context)
            for name, (reference, format_) in private_refs.items():
                assert reference not in receipt_prefixes[context.episode_id]
                assert resolve(reference, 'artifact') is False
                assert workflow.services.reference_in_scope(reference, scope, 'artifact') is False
                assert workflow.services.reference_in_context(context, reference, 'artifact') is False
                denied, path = workflow.services.read_received_molecular_input(context, reference, 'artifact', file_format=format_)
                assert path is None and denied['failure'] is not None
                arguments = {'source_ref': private_wrappers[name], 'representation': 'original'}
                with pytest.raises(ContractError, match='molecular_source_artifact_not_granted'):
                    workflow.services.authenticate_source_byte_operands(context, 'source.read', arguments)
                with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                        tool_name='source.read', arguments=arguments, operation_key=None):
                    with pytest.raises(ContractError, match='molecular_source_artifact_not_granted'):
                        tools._check_molecular_source_bytes('source.read', arguments)
            for name, file in allowed_files.items():
                reference = file['artifact_ref']
                assert reference in receipt_prefixes[context.episode_id]
                assert resolve(reference, 'artifact') is True
                assert workflow.services.reference_in_scope(reference, scope, 'artifact') is True
                assert workflow.services.reference_in_context(context, reference, 'artifact') is True
                received, path = workflow.services.read_received_molecular_input(context, reference, 'artifact', file_format=file['format'])
                assert path is not None and received['failure'] is None and received['input']['byte_verification'] == 'verified'
                assert hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256']
                arguments = {'source_ref': public_wrappers[name], 'representation': 'original'}
                workflow.services.authenticate_source_byte_operands(context, 'source.read', arguments)
                with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                        tool_name='source.read', arguments=arguments, operation_key=None):
                    tools._check_molecular_source_bytes('source.read', arguments)
            assert set(workflow.receipts.known(context.episode_id)) == receipt_prefixes[context.episode_id]
            assert not set((*private_wrappers.values(), *public_wrappers.values())).intersection(receipt_prefixes[context.episode_id])
        assert permission_counts == {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in counts}
        attempt, = list(store.db.execute('SELECT * FROM runtime_report_attempts WHERE parent_episode_id=?', (parent_id,)))
        assert attempt['failure'] is None and json.loads(attempt['form']) == returned
        # Withdraw only the owned original-model copy. Original355 producer
        # paths remain untouched; the artifact guard supplies the closed test.
        (store.path / 'artifacts' / original_file['sha256'][:2] / original_file['sha256']).unlink()
        before_closed_tables, before_closed_artifacts = _tables(store), _inventory(store.path / 'artifacts')
        changes_before = store.db.total_changes
        guarded_refs = {source[field] for source in published.values() for field in ('request_ref', 'artifact_ref')}
        guarded_refs.update(_retained_file_refs(capsules))
        guarded_refs.update(file['artifact_ref'] for file in allowed_files.values())
        assert {source['request_ref'] for source in published.values()} <= guarded_refs
        blocked_reads, actual_get_artifact = [], Store.get_artifact
        def guarded_get_artifact(current_store, reference):
            if reference in guarded_refs:
                blocked_reads.append(reference)
                raise AssertionError('closed retained FBA replay reopened a publication or scientific File')
            return actual_get_artifact(current_store, reference)
        trace = {'cached_actions': [], 'closed_scientific_requests': [], 'restored_scientific_processes': []}
        actual_action, actual_restore = DecisionSource.execute, ScientificProcessEpisodes.restore_closed_process
        async def traced_action(source, selection, index):
            row = source.workflow.journal.row('runtime_actions', source.episode_id, index)
            trace['cached_actions'].append({'role': source.path[-1][0], 'episode_id': source.episode_id,
                'decision_index': index, 'result_already_saved': row is not None and row['result'] is not None})
            return await actual_action(source, selection, index)
        def traced_restore(binding, context):
            result = actual_restore(binding, context)
            if result is not None:
                trace['restored_scientific_processes'].append(context.episode_id)
            return result
        replay_provider = ScriptedProvider([])
        with monkeypatch.context() as frozen:
            frozen.setattr(Store, 'get_artifact', guarded_get_artifact)
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect'):
                frozen.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
            for name in ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker',
                    'capture_flux_balance_native_files', 'project_fba_result', 'project_flux_balance_model_result'):
                frozen.setattr(ordinary, name, _forbidden)
            for name in ('parse_cobra_glpk_model_capture', 'parse_cobra_glpk_problem_capture',
                    'parse_cobra_glpk_solution_capture', 'parse_biomni_fba_csv', 'parse_fba_capture'):
                frozen.setattr('gene_annotation_episode.flux_balance_readers.' + name, _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_result_worker.calculate_flux_balance_sheet', _forbidden)
            frozen.setattr(DecisionSource, 'execute', traced_action)
            frozen.setattr(ScientificProcessEpisodes, 'restore_closed_process', traced_restore)
            replay = _workflow(case, tools, replay_provider, application, original_file)
            actual_closed = replay.services.scientific_closed_request
            def traced_closed(context):
                result = actual_closed(context)
                if result is not None:
                    trace['closed_scientific_requests'].append(context.episode_id)
                return result
            frozen.setattr(replay.services, 'scientific_closed_request', traced_closed)
            replay_root = replay.build('annotation', 'root', QUESTION, case.scope)
            replay_record = asyncio.run(replay_root.run_async(replay.context))
            replay_final = asyncio.run(replay_root.build_result(replay_record)).as_record()
            assert replay_provider.contexts == [] and replay_final == final_result
            # Reconstruct the actual closed scientific child too; the root's
            # cached commission result alone cannot establish that restoration.
            commission = replay.journal.row('runtime_actions', parent_id, 0)
            replay_child = replay.selected(replay_root.source, json.loads(commission['action']), 0).child
            assert replay_child.source.episode_id == science_id
            assert plain(replay_child.request.as_record()) == science_request
            assert replay_child.goal.parent_goal_id == replay_root.goal.goal_id
            root_context = replay.context
            boundary = type(root_context).from_commission(tree=root_context.tree, run_id=RUN_ID,
                parent_path=replay_root.source.path, parent_goal_id=replay_root.goal.goal_id,
                child_goal_id=replay_child.goal.goal_id, grain=replay_child.grain.name, key=replay_child.key)
            try:
                replay.context = boundary
                replay_child_record = asyncio.run(replay_child.run_async(boundary))
                replay_child_result = asyncio.run(replay_child.build_result(replay_child_record)).as_record()
            finally:
                replay.context = root_context
            assert replay_child_result == {'form': returned}
            assert science_id in trace['closed_scientific_requests']
            assert science_id in trace['restored_scientific_processes']
            assert replay_provider.contexts == []
        assert _tables(store) == before_closed_tables and _inventory(store.path / 'artifacts') == before_closed_artifacts
        assert blocked_reads == [] and all(row['result_already_saved'] for row in trace['cached_actions'])
        assert len(worker_calls) == 1
        reclosure_changes = store.db.total_changes - changes_before
    assert _inventory(checkpoint) == checkpoint_before and _inventory(original_root) == original_before
    (tmp_path / 'FLUX_BALANCE_ORDINARY_RETAINED_CONTINUATION.json').write_text(json.dumps({
        'qualification': 'Genuine355 pending checkpoint cloned without SQL edits; original selected paths preserved; one new saved-sheet worker only.',
        'checkpoint': str(checkpoint), 'checkpoint_database': checkpoint_before['store/state.sqlite3'],
        'owned_store': str(copied_store), 'question': QUESTION, 'prefix_counts': prefix_counts,
        'final_counts': counts, 'new_scripted_decisions': len(provider.contexts), 'new_saved_worker_count': len(worker_calls),
        'new_solve_or_model_worker_count': 0, 'pending_operation_key': pending_key,
        'original_saved_solve_recovered': True, 'prefix_tool_operations_and_capsules_unchanged': True,
        'native_units': units, 'new_worker_unit': units[-1], 'selected_software_sha256': digest(software),
        'objective_native_cobra': calculations['objective']['native_cobra'], 'observed_BC_flux': reaction_view['rows'][1]['values']['flux'],
        'published_source_refs': {mode: source['id'] for mode, source in published.items()},
        'typed_return_sha256': digest(returned), 'typed_return_fields': sorted(returned),
        'same_source_distinct_read_selectors': [outcomes[index]['result']['measurements'][0]['selector'] for index in (3, 4)],
        'explicit_edited_model': edited, 'explicit_saved_sheet': state['saved_sheet'], 'parent_known_refs': sorted(known),
        'private_refs_denied': {name: reference for name, (reference, _) in private_refs.items()},
        'genuinely_received_files_allowed': {name: file['artifact_ref'] for name, file in allowed_files.items()},
        'permission_checks_added_no_receipts_or_actions': True, 'root_final_result': final_result,
        'closed_replay_trace': trace, 'closed_guarded_refs': sorted(guarded_refs), 'closed_blocked_reads': blocked_reads,
        'closed_scientific_child_form_replayed': replay_child_result == {'form': returned},
        'closed_reclosure_SQL_changes': reclosure_changes, 'closed_table_and_artifact_values_unchanged': True,
        'original_checkpoint_and355test_directory_unchanged': True,
        'limits': 'The original355 testcase remains failed. This continues its actual earlier pending prefix. '
            'Only the owned input File copy is withdrawn before closed replay; original producer directories remain untouched. '
            'Store.get_artifact guards actual publication/native/worker/model/sheet refs, not global filesystem access. '
            'No relocation, new optimize, biological conclusion or NativeExecution statistics receipt is claimed.'
    }, indent=2) + '\n')
