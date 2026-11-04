"""Finish permission and closed-replay proof from genuine completed360 records.

This optional follow-up executes no model, solve, saved calculation or model
decision. Original355/360 failures remain failures; original absolute paths are
evidence controls, and copied worker interpreter bytes establish selection.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode import flux_balance_tools as ordinary
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.runtime import DecisionSource
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.waiting import validate_pending
from test_flux_balance_ordinary_retained import _clone_checkpoint, _readonly_store
from test_flux_balance_ordinary_workflow import (FIELDS, QUESTION, RUN_ID, ScriptedProvider,
    _byte_probe_source, _forbidden, _inventory, _json, _retained_file_refs, _tables, _workflow)


COMPLETED_DATABASE_SHA256 = '7a3e9d961da978a8bc382539dcf21f6e224f26d4ac786d571fd4d60edfae18ae'
PENDING_DATABASE_SHA256 = '0713c47d65ccf4be757c5ec14864585a9c7905209a0dacf1fea7c9f17e6b2978'


def _counts(store):
    return {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
        ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls',
            'tool_operations', 'runtime_forms', 'runtime_report_attempts')}


def _permission_checks(store, workflow, tools, contexts, published, capsules, allowed_files):
    worker = capsules['solve']['prepared']['worker']
    private_files = {name: worker['files'][name] for name in ('calculations', 'projection')}
    private_files.update(worker_plan=worker['capture']['plan_file'],
        worker_execution=worker['capture']['execution_receipt_file'])
    private_refs = {name: (file['artifact_ref'], file['format']) for name, file in private_files.items()}
    private_refs.update({mode + '_capsule': (source['request_ref'], ordinary.CAPSULE_VERSION)
        for mode, source in published.items()})
    packets = {mode + '_public_packet': (source['artifact_ref'], 'text')
        for mode, source in published.items()}
    private_refs.update(packets)
    private_wrappers = {name: _byte_probe_source(store, reference, 'private_' + name)
        for name, (reference, _) in private_refs.items()}
    public_wrappers = {name: _byte_probe_source(store, file['artifact_ref'], 'received_' + name)
        for name, file in allowed_files.items()}
    before = _counts(store)
    receipts = {context.episode_id: set(workflow.receipts.known(context.episode_id)) for context in contexts}
    packet_scope = {}
    for context in contexts:
        scope = plain(context.scope)
        resolve = workflow.resolver(scope, context=context)
        for name, (reference, format_) in private_refs.items():
            assert reference not in receipts[context.episode_id]
            assert resolve(reference, 'artifact') is False
            in_scope = workflow.services.reference_in_scope(reference, scope, 'artifact')
            if name in packets:
                # Source ownership is a coarse scope fact. It grants no File;
                # all actual reader/context checks below still require receipt.
                packet_scope.setdefault(context.episode_id, {})[reference] = in_scope
            else:
                assert in_scope is False
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
            assert reference in receipts[context.episode_id]
            assert resolve(reference, 'artifact') is True
            assert workflow.services.reference_in_scope(reference, scope, 'artifact') is True
            assert workflow.services.reference_in_context(context, reference, 'artifact') is True
            received, path = workflow.services.read_received_molecular_input(context, reference, 'artifact', file_format=file['format'])
            assert path is not None and received['failure'] is None
            assert received['input']['byte_verification'] == 'verified'
            assert hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256']
            arguments = {'source_ref': public_wrappers[name], 'representation': 'original'}
            workflow.services.authenticate_source_byte_operands(context, 'source.read', arguments)
            with tools.current_invocation(context, read_received=workflow.services.read_received_molecular_input,
                    tool_name='source.read', arguments=arguments, operation_key=None):
                tools._check_molecular_source_bytes('source.read', arguments)
        assert set(workflow.receipts.known(context.episode_id)) == receipts[context.episode_id]
        assert not set((*private_wrappers.values(), *public_wrappers.values())).intersection(receipts[context.episode_id])
    assert _counts(store) == before
    return {'contexts': [context.episode_id for context in contexts],
        'private_refs_denied': {name: ref for name, (ref, _) in private_refs.items() if name not in packets},
        'unreceived_packet_refs_denied': {name: ref for name, (ref, _) in packets.items()},
        'packet_contextless_scope_verdicts': packet_scope,
        'received_files_allowed': {name: file['artifact_ref'] for name, file in allowed_files.items()},
        'wrapper_refs': [*private_wrappers.values(), *public_wrappers.values()],
        'receipts_and_runtime_counts_unchanged': True}


def test_completed_ordinary_fba_permissions_and_direct_closed_replay(tmp_path, monkeypatch):
    supplied = os.environ.get('HMMER_NATIVE_ORACLE_FBA_COMPLETED_STORE')
    if not supplied:
        pytest.skip('requires the explicitly supplied original completed360 Store')
    directory = Path(supplied).expanduser().resolve(strict=True)
    assert hashlib.sha256((directory / 'state.sqlite3').read_bytes()).hexdigest() == COMPLETED_DATABASE_SHA256
    original360_root = directory.parent
    before360 = _inventory(original360_root)
    original = _readonly_store(directory)
    try:
        original_tables = _tables(original)
        episodes = list(original.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2 and all(row['state'] == 'yielded' for row in episodes)
        assert {row['run_id'] for row in episodes} == {RUN_ID}
        parent_request, science_request = [json.loads(row['request']) for row in episodes]
        assert parent_request['goal']['objective'] == science_request['goal']['objective'] == QUESTION
        parent_id, science_id = (row['episode_id'] for row in episodes)
        actions = list(original.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? ORDER BY decision_index', (science_id,)))
        selections, outcomes = [json.loads(row['action']) for row in actions], [json.loads(row['result']) for row in actions]
        assert len(actions) == 6 and all(value['tool'] == ordinary.FBA_TOOL for value in selections)
        assert [value['arguments']['mode'] for value in selections] == ['inspect', 'edit', 'solve', 'read_stored', 'read_stored', 'calculate_saved']
        assert all(value['status'] == 'completed' for value in outcomes)
        operations = list(original.db.execute('SELECT * FROM tool_operations ORDER BY operation_key'))
        assert len(operations) == 6
        for index, operation in enumerate(operations):
            assert operation['operation_key'] == f'{RUN_ID}:{science_id}:{index}'
            assert operation['name'] == ordinary.FBA_TOOL
            assert json.loads(operation['arguments']) == selections[index]['arguments']
            actual_outcome = deepcopy(outcomes[index])
            if 'pending_work_after_action' in actual_outcome:
                validate_pending(actual_outcome.pop('pending_work_after_action'))
            assert json.loads(operation['result']) == actual_outcome
        counts = _counts(original)
        assert counts == dict(runtime_episodes=2, runtime_actions=7, runtime_observations=7,
            runtime_model_calls=7, tool_operations=6, runtime_forms=1, runtime_report_attempts=1)
        published = {mode: original.get(outcomes[index]['result']['source_ref'])
            for mode, index in [('inspect', 0), ('edit', 1), ('solve', 2), ('calculate_saved', 5)]}
        capsules = {mode: _json(original, source['request_ref']) for mode, source in published.items()}
        selected = capsules['solve']['prepared']['selected']
        assert all(capsule['prepared']['selected'] == selected for capsule in capsules.values())
        resources = {selected['resource_id']: {'kind': 'local', 'workspace': selected['workspace'],
            'policy': deepcopy(POLICY), 'native_flux_balance': [deepcopy(selected['binding'])]}}
        environments = [{'resource_id': selected['resource_id'], 'binding_ordinal_0based': selected['binding_ordinal_0based'],
            'environment': deepcopy(selected['environment'])}]
        original_file, = [value['file'] for value in capsules['inspect']['prepared']['resolved_inputs']]
        returned = json.loads(original.db.execute('SELECT form FROM runtime_forms WHERE episode_id=?', (science_id,)).fetchone()[0])
        attempt, = list(original.db.execute('SELECT * FROM runtime_report_attempts WHERE parent_episode_id=?', (parent_id,)))
        assert attempt['failure'] is None and json.loads(attempt['form']) == returned
        original355_root = Path(selected['workspace']).parent
        before355 = _inventory(original355_root)
        for original_store in (original355_root / 'store', original355_root / 'pending-publication-checkpoint' / 'store'):
            retained = _readonly_store(original_store)
            try:
                assert retained.db.total_changes == 0
                if original_store.parent.name == 'pending-publication-checkpoint':
                    assert hashlib.sha256((original_store / 'state.sqlite3').read_bytes()).hexdigest() == PENDING_DATABASE_SHA256
            finally:
                retained.close()
        copied_store = _clone_checkpoint(original, original360_root, tmp_path / 'owned-completed')
        assert original.db.total_changes == 0
    finally:
        original.close()

    monkeypatch.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.flux_balance_model_execution.run_selected_flux_balance_model', _forbidden)
    for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status'):
        monkeypatch.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
    for name in ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker',
            'capture_flux_balance_native_files', 'project_fba_result', 'project_flux_balance_model_result'):
        monkeypatch.setattr(ordinary, name, _forbidden)
    for name in ('parse_cobra_glpk_model_capture', 'parse_cobra_glpk_problem_capture',
            'parse_cobra_glpk_solution_capture', 'parse_biomni_fba_csv', 'parse_fba_capture'):
        monkeypatch.setattr('gene_annotation_episode.flux_balance_readers.' + name, _forbidden)
    monkeypatch.setattr('gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet', _forbidden)
    monkeypatch.setattr('gene_annotation_episode.flux_balance_result_worker.calculate_flux_balance_sheet', _forbidden)
    with Store(copied_store) as store:
        assert _tables(store) == original_tables
        assert not store.list('native_execution')
        software = selected['binding']['software']
        units, interpreter_proofs = [], []
        for mode in ('inspect', 'edit'):
            model = capsules[mode]['prepared']['model']
            assert model['result']['model_optimize_call_count'] == 0
            assert model['execution']['returncode'] == 0 and model['execution']['failure'] is None
            assert model['handle']['command'][0] == software['python']['path']
            units.append(model['handle']['unit'])
        native = capsules['solve']['prepared']['native']
        assert native['terminal'] is native['quiescent'] is True and native['returncode'] == 0 and native['failure'] is None
        assert native['metadata']['policy'] == POLICY
        assert native['plan']['requested_job']['native_flux_balance']['software'] == software
        assert native['plan']['requested_job']['native_flux_balance']['objective'] == {'kind': 'single_reaction', 'reaction_id': 'BC'}
        units.append(native['handle']['unit'])
        for mode in ('solve', 'calculate_saved'):
            worker = capsules[mode]['prepared']['worker']
            execution = worker['execution']
            assert execution['terminal'] is execution['quiescent'] is True
            assert execution['returncode'] == 0 and execution['failure'] is None and execution['metadata']['policy'] == POLICY
            copied_python = Path(execution['handle']['command'][0])
            pin = {'sha256': hashlib.sha256(copied_python.read_bytes()).hexdigest(), 'size_bytes': copied_python.stat().st_size}
            assert pin == {key: software['python'][key] for key in ('sha256', 'size_bytes')}
            interpreter_proofs.append({'mode': mode, 'recorded_path': str(copied_python), **pin})
            units.append(execution['handle']['unit'])
        assert len(units) == len(set(units)) == 5
        assert units[-1] == 'gene-local-job-f8566677935c49019e9a93d00ab4a6d9.service'
        sheet, calculations = capsules['solve']['sheet'], capsules['solve']['calculations']
        assert sheet['native']['solve_call_count'] == sheet['native_solution']['native']['model_optimize_call_count'] == 1
        assert calculations['objective']['native_cobra']['state'] == 'present' and calculations['objective']['native_cobra']['value'] == 0
        assert capsules['calculate_saved']['sheet'] == sheet
        assert capsules['calculate_saved']['prepared']['worker']['plan']['mode'] == 'saved_sheet_recalculation'
        captured_stdout = capsules['calculate_saved']['prepared']['worker']['execution']['stdout_file']
        assert captured_stdout['size_bytes'] == 0 and captured_stdout['sha256'] == hashlib.sha256(b'').hexdigest()
        assert store.get_artifact(captured_stdout['artifact_ref']) == b''
        solve_source = outcomes[2]['result']['source_ref']
        assert outcomes[3]['result']['source_ref'] == outcomes[4]['result']['source_ref'] == solve_source
        assert outcomes[3]['result']['measurements'][0]['selector'] != outcomes[4]['result']['measurements'][0]['selector']
        edited, = outcomes[1]['result']['edited_models']
        saved_sheet, = outcomes[2]['result']['saved_sheets']
        assert returned['solve_source'] == solve_source and returned['edited_models'] == [edited] and returned['saved_sheets'] == [saved_sheet]
        assert len(returned['model_views']) == 2 and len(returned['measurements']) == 4
        for value in outcomes:
            for field in ('measurements', 'model_views'):
                assert all(item in returned[field] for item in value['result'][field])
        reaction_view = outcomes[3]['result']['measurements'][0]
        assert [row['reaction_id'] for row in reaction_view['rows']] == ['AB', 'BC']
        for row in reaction_view['rows']:
            assert row['values']['flux']['flux']['state'] == 'present' and row['values']['flux']['flux']['value'] == 0
            assert row['values']['flux']['unit'] == {'native_text': None, 'basis': 'unknown'}
        assert reaction_view['rows'][0]['values']['bounds']['lower']['value'] == reaction_view['rows'][0]['values']['bounds']['upper']['value'] == 0
        edited_native = json.loads(store.get_artifact(edited['artifact_ref']))
        reactions = {row['id']: row for row in edited_native['reactions']}
        assert reactions['AB']['lower_bound'] == reactions['AB']['upper_bound'] == 0
        assert reactions['BC']['objective_coefficient'] == 1
        assert [row['id'] for row in edited_native['metabolites']] == ['A', 'B', 'C']
        assert hashlib.sha256(store.get_artifact(original_file['artifact_ref'])).hexdigest() == original_file['sha256']
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, flux_balance_environments=environments)
        factory.configure_tool_registry(tools)
        case = SimpleNamespace(store=store, directory=copied_store.parent / 'run', source=copied_store.parent / 'source',
            descriptors=[deepcopy(science_request['message']['scientific_process']['mechanics_binding']), LiteratureEpisodes(None).as_record()],
            scope=deepcopy(parent_request['message']['scope']))
        application = factory(store, run_id=RUN_ID, directory=case.directory, tool_registry=tools)
        workflow = _workflow(case, tools, ScriptedProvider([]), application, original_file)
        contexts = EpisodeReturnRecords(store, RUN_ID, failure_prefix='ordinary_fba_completed_')
        parent, science = contexts.context(parent_id), contexts.context(science_id)
        # The root requests no onward report. Its received child report is
        # authenticated independently against that child's original contract.
        assert workflow.episode_bindings.received_report_facts(parent) == {}
        execution = workflow.episode_bindings.for_role('results')
        receiving = execution.native_flux_balance_returns.received_facts(parent,
            science_request['report_contract']['measurements']['schema'])
        for field, source in FIELDS.items():
            assert receiving[source] == returned[field]
        assert {solve_source, edited['artifact_ref'], saved_sheet['artifact_ref']} <= set(workflow.receipts.known(parent_id))
        allowed_files = {'original_input': original_file, 'edited_model': edited, 'saved_sheet': saved_sheet}
        permissions = _permission_checks(store, workflow, tools, (parent, science), published, capsules, allowed_files)
        (store.path / 'artifacts' / original_file['sha256'][:2] / original_file['sha256']).unlink()
        before_tables, before_files, before_run = _tables(store), _inventory(store.path / 'artifacts'), _inventory(case.directory)
        changes_before = store.db.total_changes
        guarded = {source[field] for source in published.values() for field in ('request_ref', 'artifact_ref')}
        for source in published.values(): guarded.update(source.get('auxiliary_artifact_refs', []))
        guarded.update(_retained_file_refs(capsules))
        guarded.update(file['artifact_ref'] for file in allowed_files.values())
        blocked, actual_get = [], Store.get_artifact
        def get_artifact(current, reference):
            if reference in guarded:
                blocked.append(reference); raise AssertionError('closed completed FBA replay reopened a scientific payload')
            return actual_get(current, reference)
        traces = {'cached_actions': [], 'closed_requests': [], 'restored_science': [], 'finished': []}
        actual_execute, actual_restore, actual_closed, actual_finish = (DecisionSource.execute,
            ScientificProcessEpisodes.restore_closed_process, WorkflowServices.scientific_closed_request, DecisionSource.finish)
        async def execute(source, selection, index):
            row = source.workflow.journal.row('runtime_actions', source.episode_id, index)
            assert row is not None and row['result'] is not None
            traces['cached_actions'].append({'role': source.path[-1][0], 'episode_id': source.episode_id, 'index': index})
            return await actual_execute(source, selection, index)
        def restore(binding, context):
            result = actual_restore(binding, context)
            if result is not None: traces['restored_science'].append(context.episode_id)
            return result
        def closed(services, context):
            result = actual_closed(services, context)
            if result is not None: traces['closed_requests'].append(context.episode_id)
            return result
        async def finish(source, record):
            result = await actual_finish(source, record)
            traces['finished'].append({'role': source.path[-1][0], 'episode_id': source.episode_id, 'result': plain(result.as_record())})
            return result
        replay_provider = ScriptedProvider([])
        with monkeypatch.context() as frozen:
            frozen.setattr(Store, 'get_artifact', get_artifact)
            frozen.setattr(replay_provider, 'complete', _forbidden)
            frozen.setattr(ToolRegistry, 'execute_async', _forbidden)
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status'):
                frozen.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
            for name in ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker',
                    'capture_flux_balance_native_files', 'project_fba_result', 'project_flux_balance_model_result'):
                frozen.setattr(ordinary, name, _forbidden)
            for name in ('parse_cobra_glpk_model_capture', 'parse_cobra_glpk_problem_capture',
                    'parse_cobra_glpk_solution_capture', 'parse_biomni_fba_csv', 'parse_fba_capture'):
                frozen.setattr('gene_annotation_episode.flux_balance_readers.' + name, _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_result_worker.calculate_flux_balance_sheet', _forbidden)
            frozen.setattr(DecisionSource, 'execute', execute)
            frozen.setattr(DecisionSource, 'finish', finish)
            frozen.setattr(ScientificProcessEpisodes, 'restore_closed_process', restore)
            frozen.setattr(WorkflowServices, 'scientific_closed_request', closed)
            replay = _workflow(case, tools, replay_provider, application, original_file)
            root = replay.build('annotation', 'root', QUESTION, case.scope)
            record = asyncio.run(root.run_async(replay.context))
            parent_result = plain(asyncio.run(root.build_result(record)).as_record())
            assert parent_result == {'credit': 0, 'pending_handles': []}
            commission = replay.journal.row('runtime_actions', parent_id, 0)
            child = replay.selected(root.source, json.loads(commission['action']), 0).child
            assert child.source.episode_id == science_id and plain(child.request.as_record()) == science_request
            root_context = replay.context
            boundary = type(root_context).from_commission(tree=root_context.tree, run_id=RUN_ID,
                parent_path=root.source.path, parent_goal_id=root.goal.goal_id,
                child_goal_id=child.goal.goal_id, grain=child.grain.name, key=child.key)
            try:
                replay.context = boundary
                child_record = asyncio.run(child.run_async(boundary))
                child_result = plain(asyncio.run(child.build_result(child_record)).as_record())
            finally:
                replay.context = root_context
            assert child_result == {'form': returned}
            assert science_id in traces['closed_requests'] and science_id in traces['restored_science']
            assert any(value['role'] == 'annotation' and value['result'] == parent_result for value in traces['finished'])
            assert any(value['episode_id'] == science_id and value['result'] == child_result for value in traces['finished'])
            assert replay_provider.contexts == []
        assert _counts(store) == counts and _tables(store) == before_tables
        assert _inventory(store.path / 'artifacts') == before_files and _inventory(case.directory) == before_run
        assert blocked == [] and not (store.path / 'artifacts' / original_file['sha256'][:2] / original_file['sha256']).exists()
        reclosure_changes = store.db.total_changes - changes_before
    after360, after355 = _inventory(original360_root), _inventory(original355_root)
    assert after360 == before360 and after355 == before355
    (tmp_path / 'FLUX_BALANCE_ORDINARY_COMPLETED_PROOF.json').write_text(json.dumps({
        'qualification': 'Retained-only actual completed360 proof; no new decisions, workers, solves or calculations.',
        'source_store': str(directory), 'owned_store': str(copied_store), 'counts': counts,
        'source_database_sha256': COMPLETED_DATABASE_SHA256, 'original355_checkpoint_database_sha256': PENDING_DATABASE_SHA256,
        'worker_interpreter_byte_proofs': interpreter_proofs, 'recorded_native_units': units,
        'saved_worker_captured_empty_stdout': captured_stdout,
        'objective_native_cobra': calculations['objective']['native_cobra'], 'observed_BC_flux': reaction_view['rows'][1]['values']['flux'],
        'same_source_distinct_selectors': [outcomes[index]['result']['measurements'][0]['selector'] for index in (3, 4)],
        'received_child_fact_groups_sha256': digest(receiving),
        'uncontracted_root_onward_facts': {},
        'typed_return_sha256': digest(returned), 'permission_checks': permissions,
        'parent_final_result': parent_result, 'direct_scientific_result': child_result, 'closed_traces': traces,
        'closed_guarded_refs': sorted(guarded), 'closed_blocked_reads': blocked,
        'new_decisions_workers_observations': 0, 'same_value_reclosure_SQL_changes': reclosure_changes,
        'closed_all_table_artifact_and_run_values_unchanged': True,
        'original360_inventory_before': before360, 'original360_inventory_after': after360,
        'original355_inventory_before': before355, 'original355_inventory_after': after355,
        'limits': 'Original355 and360 testcases remain failed. The360 failure occurred after actual Workflow completion, '
            'before its permission and replay assertions. This follow-up compares original trees only against its own current baseline; '
            'the unexecuted original360 whole-tree check is not retroactively claimed. The original355 checkpoint and completed360 '
            'database pins are independently checked. Only the owned input copy is withdrawn. Stored original absolute paths remain '
            'literal and available as historical controls; relocation portability, new biology and NativeExecution statistics receipts '
            'are not established. Scientific File payloads are guarded; operational journal/archive/library reads remain real.'
    }, indent=2) + '\n')
