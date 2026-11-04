"""One actual ordinary FBA Workflow path and genuine pending-publication recovery.

Tiny caller-authored model bytes exercise the selected Cobra/GLPK closure.
Scripted decisions select actual prior returned identities; they calculate no
scientific values. This is an engineering control, not biological evidence.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pytest

from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.flux_balance_return_views import fba_fact_sources
from gene_annotation_episode.flux_balance_tools import ARGUMENT_VERSION, FBA_TOOL
from gene_annotation_episode import flux_balance_tools as ordinary
from gene_annotation_episode.native_flux_balance_contracts import POLICY
from gene_annotation_episode.runtime import DecisionSource, Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_flux_balance_model_tools import addition
from test_flux_balance_ordinary import explicit_request
from test_flux_balance_tools import parameters
from test_native_flux_balance_producer_688 import _json_model, _software
from test_runtime import FixtureController
from test_scientific_process_runtime import Scenario, action


QUESTION = ('What objective value and BC reaction flux does the supplied model support after adding C and BC, '
    'fixing AB bounds to zero, and selecting BC as objective; what changed in its reaction inventory?')
FIELDS = {'measurements': 'flux_balance_measurements', 'model_views': 'flux_balance_model_views',
    'saved_sheets': 'flux_balance_saved_sheets', 'edited_models': 'flux_balance_edited_models',
    'failures': 'flux_balance_failures'}
RUN_ID = 'ordinary-fba-workflow-regression'


class ScriptedProvider:
    """Record actual dispatches without asserting any episode instruction text."""
    def __init__(self, script):
        self.script, self.contexts, self.released = iter(script), [], []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == 'REASONING'
        self.contexts.append(deepcopy(context))
        response = next(self.script)
        if isinstance(response, BaseException):
            raise response
        return response(context) if callable(response) else deepcopy(response)

    async def release(self, episode_id):
        self.released.append(episode_id)


def _forbidden(*args, **kwargs):
    raise AssertionError('closed ordinary FBA replay attempted fresh work')


def _credit(*args, **kwargs):
    return 0


def _controller(path, initial):
    return FixtureController(str(path), initial, 1 if len(path) == 1 else 6)


def _file_selection(file):
    return {'witness_ref': file['artifact_ref'], 'artifact_field': None,
        'version': None, 'format': file['format']}


def _model_view(phase='loaded_original', *, ordinals=None):
    return {'snapshot_phase': phase, 'collection': 'reactions', 'ordinals': ordinals,
        'row_window': {'offset': 0, 'limit': 10}}


def _projection(kind):
    base = {'version': 'flux_balance_projection_selector_v1', 'row_window': {'offset': 0, 'limit': 10}}
    if kind == 'solve':
        return {**base, 'view': 'run_diagnostics', 'fields': ['native_run', 'objective']}
    if kind == 'population':
        return {**base, 'view': 'run_diagnostics', 'fields': ['reaction_population', 'candidate_feasibility']}
    return {**base, 'view': 'reaction_fluxes', 'snapshot_phase': 'effective',
        'reaction_positions': [1, 3] if kind == 'bounds' else [3], 'filter': None,
        'fields': ['flux', 'bounds'] if kind == 'bounds' else ['flux', 'native_values']}


def _arguments(mode):
    return {'version': ARGUMENT_VERSION, 'mode': mode,
        **({} if mode == 'read_stored' else {'resource_id': 'ordinary-selected', 'binding_ordinal_0based': 0})}


def _configuration(tmp_path, software):
    workspace = tmp_path / 'native-workspace'
    workspace.mkdir()
    resources = {'ordinary-selected': {'kind': 'local', 'workspace': str(workspace),
        'policy': deepcopy(POLICY), 'native_flux_balance': [{'version': 'flux_balance_local_binding_v1',
            'operation': FBA_TOOL, 'mode': 'steady_state_linear_fba', 'software': software,
            'model_formats': ['cobra_json', 'sbml']}]}}
    environments = [{'resource_id': 'ordinary-selected', 'binding_ordinal_0based': 0,
        'environment': deepcopy(ordinary.ENVIRONMENT_SELECTION)}]
    return resources, environments


def _workflow(case, tools, provider, application, original):
    return Workflow(case.store, tools, provider, case.directory, RUN_ID, _controller, _credit,
        project_child_credit=_credit, episode_binding_descriptors=[*case.descriptors,
            *application.episode_binding_descriptors], role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider, episode_record_receipts=True,
        initial_known_record_refs=[original['artifact_ref']])


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: sorted((tuple((type(value).__name__, value) for value in row)
        for row in store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')), key=repr) for name in names}


def _inventory(root):
    return {str(path.relative_to(root)): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'byte_length': path.stat().st_size} for path in sorted(root.rglob('*')) if path.is_file()}


def _json(store, reference):
    return json.loads(store.get_artifact(reference))


def _retained_file_refs(value):
    """Read actual retained File identities already present in the audit data."""
    result = set()
    if isinstance(value, dict):
        if {'artifact_ref', 'sha256', 'format'} <= value.keys() and (
                'size_bytes' in value or 'byte_length' in value):
            result.add(value['artifact_ref'])
        for child in value.values():
            result.update(_retained_file_refs(child))
    elif isinstance(value, list):
        for child in value:
            result.update(_retained_file_refs(child))
    return result


def _byte_probe_source(store, reference, label):
    """Caller-origin wrapper tests byte gates; it supplies no producer/receipt."""
    return store.put('source', {'provider': 'engineering_fba_byte_gate_probe',
        'accession': label, 'uri': None, 'artifact_ref': reference, 'text_ref': None,
        'request_ref': None, 'version': 'caller_fixture_v1', 'retrieved_at': None}, origin='caller')['id']


def _checkpoint(store, case, workspace, destination, key, outcome):
    """Preserve the real pending prefix; do not rewrite original absolute paths."""
    assert not store.db.in_transaction
    destination.mkdir()
    copied_store = destination / 'store'
    copied_store.mkdir()
    database = copied_store / 'state.sqlite3'
    connection = sqlite3.connect(database)
    try:
        store.db.backup(connection)
    finally:
        connection.close()
    for name in ('artifacts', 'cache'):
        if (store.path / name).exists(): shutil.copytree(store.path / name, copied_store / name)
    shutil.copytree(case.directory, destination / 'run')
    shutil.copytree(case.source, destination / 'source')
    shutil.copytree(workspace, destination / 'native-workspace')
    connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        run_id, episode_id, index = key.rsplit(':', 2)
        pending = connection.execute('SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?',
            (run_id, episode_id, int(index))).fetchone()
        assert pending['result'] is None and pending['credit'] is None
        selected = json.loads(pending['action'])
        assert selected['tool'] == FBA_TOOL and selected['arguments']['mode'] == 'solve'
        operation = connection.execute('SELECT * FROM tool_operations WHERE operation_key=?', (key,)).fetchone()
        assert json.loads(operation['result']) == outcome and outcome['status'] in {'completed', 'partial'}
        counts = {name: connection.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
            ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_model_calls',
                'tool_operations', 'runtime_forms', 'runtime_report_attempts')}
        assert counts == dict(runtime_episodes=2, runtime_actions=4, runtime_observations=2,
            runtime_model_calls=4, tool_operations=3, runtime_forms=0, runtime_report_attempts=0)
    finally:
        connection.close()
    return {'directory': str(destination), 'operation_key': key, 'counts': counts,
        'action_result': None, 'action_credit': None, 'saved_operation_status': outcome['status'],
        'database': {'sha256': hashlib.sha256(database.read_bytes()).hexdigest(), 'byte_length': database.stat().st_size},
        'copied_files': _inventory(destination), 'original_store_path': str(store.path),
        'portability_limit': 'This is a genuine pending prefix with copied artifacts, libraries and native controls. '
            'Stored native/worker/capsule paths retain their original absolute identities; relocation alone is not a replay proof.'}


class PublicationResponseLost(RuntimeError):
    pass


def test_actual_ordinary_fba_model_edit_solve_saved_reads_and_recovery(tmp_path, monkeypatch):
    if 'HMMER529_ATTEMPT' not in os.environ:
        pytest.skip('actual selected FBA execution requires the bounded runtime closure')
    software = _software()
    resources, environments = _configuration(tmp_path, software)
    monkeypatch.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
    monkeypatch.setattr('socket.create_connection', _forbidden)
    with Store(tmp_path / 'store') as store:
        document = _json_model()
        document['compartments'] = {'c': 'cytosol'}  # same supported caller control as348
        raw = canonical(document).encode()
        original_ref = store.artifact(raw, 'application/json')
        original = {'artifact_ref': original_ref, 'sha256': original_ref[9:], 'size_bytes': len(raw), 'format': 'cobra_json'}
        tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, flux_balance_environments=environments)
        factory.configure_tool_registry(tools)
        case = Scenario(tmp_path, store, tools=tools)
        application = factory(store, run_id=RUN_ID, directory=case.directory, tool_registry=tools)
        sources = fba_fact_sources()
        schema = obj({**{field: sources[source]['report_schema'] for field, source in FIELDS.items()},
            'solve_source': {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': 'source'}})
        commission = case.commission()
        commission['selection'].update(goal=QUESTION, purpose='Return the requested literal FBA values, model views and selected model/sheet Files.',
            schema_json=json.dumps(schema), initial_report_json='{"solve_source":null}')
        commission['selection']['assignment']['selection'] = case.selection(tools=[FBA_TOOL])
        inspect = {**_arguments('inspect'), 'model': _file_selection(original), 'edits': None,
            'view': _model_view(), 'return_edited_model': False}
        edit = addition()
        edit['add_metabolites'][0]['source_refs'] = []  # caller hypothesis, no invented annotation evidence
        state = {'visible_outcomes': []}
        def previous(context, mode):
            outcome = context['last_local_outcome']
            assert outcome['status'] in {'completed', 'partial'} and outcome['result']['mode'] == mode
            state['visible_outcomes'].append(deepcopy(outcome))
            return outcome['result']
        def choose_edit(context):
            previous(context, 'inspect')
            return action(FBA_TOOL, {**_arguments('edit'), 'model': _file_selection(original), 'edits': edit,
                'view': _model_view('effective', ordinals=[3, 1, 3, 0]), 'return_edited_model': True})
        calculation_parameters = parameters()
        calculation_parameters['objective_absolute_tolerance'] = 1e-8
        def choose_solve(context):
            actual = previous(context, 'edit')
            edited, = actual['edited_models']
            state['edited_model'] = deepcopy(edited)
            request = explicit_request()
            request['model_input']['file'] = _file_selection(edited)
            request['objective'] = {'kind': 'single_reaction', 'reaction_id': 'BC'}
            return action(FBA_TOOL, {**_arguments('solve'), 'request': request,
                'calculation_parameters': calculation_parameters, 'projection': _projection('solve'), 'return_saved_sheet': True})
        provider = ScriptedProvider([commission, action(FBA_TOOL, inspect), choose_edit, choose_solve])
        workflow = _workflow(case, tools, provider, application, original)
        root = workflow.build('annotation', 'root', QUESTION, case.scope)
        original_execute, lost, checkpoints = ToolRegistry.execute_async, [], []
        workspace = Path(resources['ordinary-selected']['workspace'])
        async def lose_after_saved_solve(registry, name, arguments, **kwargs):
            outcome = await original_execute(registry, name, arguments, **kwargs)
            if name == FBA_TOOL and arguments['mode'] == 'solve' and not lost:
                checkpoints.append(_checkpoint(store, case, workspace, tmp_path / 'pending-publication-checkpoint',
                    kwargs['operation_key'], outcome))
                lost.append({'operation_key': kwargs['operation_key'], 'outcome': deepcopy(outcome)})
                raise PublicationResponseLost('committed solve ToolOperation before its actual RuntimeAction response')
            return outcome
        with monkeypatch.context() as patch:
            patch.setattr(ToolRegistry, 'execute_async', lose_after_saved_solve)
            with pytest.raises(PublicationResponseLost): asyncio.run(root.run_async(workflow.context))
        assert len(provider.contexts) == 4 and len(lost) == len(checkpoints) == 1
        def choose_read_one(context):
            solved = previous(context, 'solve')
            state['solve_source'] = solved['source_ref']
            state['saved_sheet'], = deepcopy(solved['saved_sheets'])
            return {**action(FBA_TOOL, {**_arguments('read_stored'), 'result_ref': solved['source_ref'],
                'view': {'kind': 'measurement', 'selector': _projection('bounds')}}),
                'report_update': {'solve_source': solved['source_ref']}}
        def choose_read_two(context):
            actual = previous(context, 'read_stored')
            assert actual['source_ref'] == state['solve_source']
            return action(FBA_TOOL, {**_arguments('read_stored'), 'result_ref': actual['source_ref'],
                'view': {'kind': 'measurement', 'selector': _projection('population')}})
        def choose_saved_calculation(context):
            actual = previous(context, 'read_stored')
            assert actual['source_ref'] == state['solve_source']
            return action(FBA_TOOL, {**_arguments('calculate_saved'), 'sheet': _file_selection(state['saved_sheet']),
                'calculation_parameters': calculation_parameters, 'projection': _projection('native_values'), 'return_saved_sheet': False})
        monkeypatch.setattr(ordinary, 'run_selected_flux_balance_native', _forbidden)
        monkeypatch.setattr('gene_annotation_episode.flux_balance_model_execution.run_selected_flux_balance_model', _forbidden)
        restored_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        factory.configure_tool_registry(restored_tools)
        restored_provider = ScriptedProvider([choose_read_one, choose_read_two, choose_saved_calculation])
        restored = _workflow(case, restored_tools, restored_provider, application, original)
        restored_root = restored.build('annotation', 'root', QUESTION, case.scope)
        record = asyncio.run(restored_root.run_async(restored.context))
        final_result = asyncio.run(restored_root.build_result(record)).as_record()
        assert len(restored_provider.contexts) == 3
        episodes = list(store.db.execute('SELECT * FROM runtime_episodes ORDER BY json_array_length(path)'))
        assert len(episodes) == 2 and [json.loads(row['path'])[-1][0] for row in episodes] == ['annotation', 'scientific_process']
        assert all(row['state'] == 'yielded' for row in episodes)
        parent_id, science_id = (row['episode_id'] for row in episodes)
        rows = list(store.db.execute('SELECT * FROM runtime_actions WHERE episode_id=? ORDER BY decision_index', (science_id,)))
        assert len(rows) == 6
        selections = [json.loads(row['action']) for row in rows]
        assert all(row['tool'] == FBA_TOOL for row in selections)
        assert [row['arguments']['mode'] for row in selections] == ['inspect', 'edit', 'solve', 'read_stored', 'read_stored', 'calculate_saved']
        outcomes = [json.loads(row['result']) for row in rows]
        assert all(row['status'] in {'completed', 'partial'} for row in outcomes)
        recovered = {key: value for key, value in outcomes[2].items() if key != 'pending_work_after_action'}
        assert recovered == lost[0]['outcome']
        assert {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0] for name in
            ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'tool_operations')} == {
                'runtime_actions': 7, 'runtime_observations': 7, 'runtime_model_calls': 7, 'tool_operations': 6}
        assert not store.list('native_execution')
        assert outcomes[3]['result']['source_ref'] == outcomes[4]['result']['source_ref'] == outcomes[2]['result']['source_ref']
        assert outcomes[3]['result']['measurements'][0]['selector'] != outcomes[4]['result']['measurements'][0]['selector']
        published = {mode: store.get(outcomes[index]['result']['source_ref'])
            for mode, index in [('inspect', 0), ('edit', 1), ('solve', 2), ('calculate_saved', 5)]}
        capsules = {mode: _json(store, source['request_ref']) for mode, source in published.items()}
        assert len({source['id'] for source in published.values()}) == 4
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
            assert selected['binding']['software'] == software and selected['environment'] == environments[0]['environment']
            worker = capsules[mode]['prepared']['worker']
            assert worker['execution']['terminal'] is worker['execution']['quiescent'] is True
            assert worker['execution']['returncode'] == 0 and worker['execution']['failure'] is None
            assert worker['execution']['metadata']['policy'] == POLICY
            worker_python = Path(worker['execution']['handle']['command'][0])
            assert worker_python.stat().st_size == software['python']['size_bytes']
            assert hashlib.sha256(worker_python.read_bytes()).hexdigest() == software['python']['sha256']
            units.append(worker['execution']['handle']['unit'])
        assert len(units) == len(set(units)) == 5
        sheet, calculations = capsules['solve']['sheet'], capsules['solve']['calculations']
        assert sheet['native']['solve_call_count'] == sheet['native_solution']['native']['model_optimize_call_count'] == 1
        assert calculations['objective']['native_cobra']['state'] == 'present' and calculations['objective']['native_cobra']['value'] == 0
        assert capsules['calculate_saved']['sheet'] == sheet
        assert capsules['calculate_saved']['prepared']['worker']['plan']['mode'] == 'saved_sheet_recalculation'
        assert store.get_artifact(original_ref) == raw
        edited = state['edited_model']
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
        contexts = EpisodeReturnRecords(store, RUN_ID, failure_prefix='ordinary_fba_workflow_')
        parent, science = contexts.context(parent_id), contexts.context(science_id)
        receiving = restored.episode_bindings.received_report_facts(parent)
        for field, source in FIELDS.items(): assert receiving[source] == returned[field]
        known = set(restored.receipts.known(parent_id))
        assert {state['solve_source'], edited['artifact_ref'], state['saved_sheet']['artifact_ref']} <= known
        for mode, source in published.items():
            assert source['request_ref'] not in known and source['artifact_ref'] not in known
            denied, path = restored.services.read_received_molecular_input(parent, source['request_ref'], 'artifact',
                file_format=ordinary.CAPSULE_VERSION)
            assert path is None and denied['failure'] is not None
        for name in ('calculations', 'projection'):
            file = capsules['solve']['prepared']['worker']['files'][name]
            assert file is not None and file['artifact_ref'] not in known
        worker = capsules['solve']['prepared']['worker']
        private_files = {name: worker['files'][name] for name in ('calculations', 'projection')}
        private_files.update(worker_plan=worker['capture']['plan_file'],
            worker_execution=worker['capture']['execution_receipt_file'])
        private_refs = {name: (file['artifact_ref'], file['format']) for name, file in private_files.items()}
        private_refs['solve_capsule'] = (published['solve']['request_ref'], ordinary.CAPSULE_VERSION)
        allowed_files = {'original_input': original, 'edited_model': edited, 'saved_sheet': state['saved_sheet']}
        private_wrappers = {name: _byte_probe_source(store, reference, 'private_' + name)
            for name, (reference, _) in private_refs.items()}
        public_wrappers = {name: _byte_probe_source(store, file['artifact_ref'], 'received_' + name)
            for name, file in allowed_files.items()}
        receipt_prefixes = {context.episode_id: set(restored.receipts.known(context.episode_id))
            for context in (parent, science)}
        permission_counts = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('runtime_actions', 'runtime_observations', 'runtime_model_calls', 'tool_operations')}
        for context in (parent, science):
            scope = plain(context.scope)
            resolve = restored.resolver(scope, context=context)
            for name, (reference, format_) in private_refs.items():
                assert reference not in receipt_prefixes[context.episode_id]
                assert resolve(reference, 'artifact') is False
                assert restored.services.reference_in_scope(reference, scope, 'artifact') is False
                assert restored.services.reference_in_context(context, reference, 'artifact') is False
                denied, path = restored.services.read_received_molecular_input(context, reference, 'artifact', file_format=format_)
                assert path is None and denied['failure'] is not None
                arguments = {'source_ref': private_wrappers[name], 'representation': 'original'}
                with pytest.raises(ContractError, match='molecular_source_artifact_not_granted'):
                    restored.services.authenticate_source_byte_operands(context, 'source.read', arguments)
                # This is only the existing byte-permission port with an actual
                # receiver context. No selected action/key or tool dispatch is
                # invented, and the wrapper itself is never received.
                with restored_tools.current_invocation(context,
                        read_received=restored.services.read_received_molecular_input,
                        tool_name='source.read', arguments=arguments, operation_key=None):
                    with pytest.raises(ContractError, match='molecular_source_artifact_not_granted'):
                        restored_tools._check_molecular_source_bytes('source.read', arguments)
            for name, file in allowed_files.items():
                reference = file['artifact_ref']
                assert reference in receipt_prefixes[context.episode_id]
                assert resolve(reference, 'artifact') is True
                assert restored.services.reference_in_scope(reference, scope, 'artifact') is True
                assert restored.services.reference_in_context(context, reference, 'artifact') is True
                received, path = restored.services.read_received_molecular_input(context, reference, 'artifact',
                    file_format=file['format'])
                assert path is not None and received['failure'] is None
                assert received['input']['byte_verification'] == 'verified'
                assert hashlib.sha256(path.read_bytes()).hexdigest() == file['sha256']
                arguments = {'source_ref': public_wrappers[name], 'representation': 'original'}
                restored.services.authenticate_source_byte_operands(context, 'source.read', arguments)
                with restored_tools.current_invocation(context,
                        read_received=restored.services.read_received_molecular_input,
                        tool_name='source.read', arguments=arguments, operation_key=None):
                    restored_tools._check_molecular_source_bytes('source.read', arguments)
            assert set(restored.receipts.known(context.episode_id)) == receipt_prefixes[context.episode_id]
            assert not set((*private_wrappers.values(), *public_wrappers.values())).intersection(receipt_prefixes[context.episode_id])
        assert permission_counts == {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in permission_counts}
        attempt = store.db.execute('SELECT * FROM runtime_report_attempts WHERE parent_episode_id=?', (parent_id,)).fetchone()
        assert attempt['failure'] is None and json.loads(attempt['form']) == returned
        # The remaining proof uses frozen selected values, after the original
        # producer bytes/directories are withdrawn. No native operation repeats.
        (store.path / 'artifacts' / original['sha256'][:2] / original['sha256']).unlink()
        shutil.rmtree(workspace)
        before_tables, before_artifacts = _tables(store), _inventory(store.path / 'artifacts')
        calls_before = store.db.total_changes
        trace = {'cached_actions': [], 'closed_scientific_requests': [], 'restored_scientific_processes': []}
        guarded_refs = {source[field] for source in published.values() for field in ('request_ref', 'artifact_ref')}
        guarded_refs.update(_retained_file_refs(capsules))
        guarded_refs.update(file['artifact_ref'] for file in allowed_files.values())
        assert {source['request_ref'] for source in published.values()} <= guarded_refs
        blocked_reads, original_get_artifact = [], Store.get_artifact
        def guarded_get_artifact(current_store, reference):
            if reference in guarded_refs:
                blocked_reads.append(reference)
                raise AssertionError('closed FBA replay reopened a publication or retained scientific File')
            return original_get_artifact(current_store, reference)
        original_action, original_restore = DecisionSource.execute, ScientificProcessEpisodes.restore_closed_process
        async def traced_action(source, selection, index):
            row = source.workflow.journal.row('runtime_actions', source.episode_id, index)
            trace['cached_actions'].append({'role': source.path[-1][0], 'episode_id': source.episode_id,
                'decision_index': index, 'result_already_saved': row is not None and row['result'] is not None})
            return await original_action(source, selection, index)
        def traced_restore(binding, context):
            result = original_restore(binding, context)
            if result is not None: trace['restored_scientific_processes'].append(context.episode_id)
            return result
        replay_provider = ScriptedProvider([])
        with monkeypatch.context() as frozen:
            frozen.setattr(Store, 'get_artifact', guarded_get_artifact)
            for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect'):
                frozen.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
            for name in ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker',
                    'capture_flux_balance_native_files', 'project_fba_result', 'project_flux_balance_model_result'):
                frozen.setattr(ordinary, name, _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_readers.parse_cobra_glpk_model_capture', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_readers.parse_cobra_glpk_problem_capture', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_readers.parse_cobra_glpk_solution_capture', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_readers.parse_biomni_fba_csv', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_readers.parse_fba_capture', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_calculations.calculate_flux_balance_sheet', _forbidden)
            frozen.setattr('gene_annotation_episode.flux_balance_result_worker.calculate_flux_balance_sheet', _forbidden)
            frozen.setattr(DecisionSource, 'execute', traced_action)
            frozen.setattr(ScientificProcessEpisodes, 'restore_closed_process', traced_restore)
            replay = _workflow(case, restored_tools, replay_provider, application, original)
            actual_closed = replay.services.scientific_closed_request
            def traced_closed(context):
                result = actual_closed(context)
                if result is not None: trace['closed_scientific_requests'].append(context.episode_id)
                return result
            frozen.setattr(replay.services, 'scientific_closed_request', traced_closed)
            replay_root = replay.build('annotation', 'root', QUESTION, case.scope)
            replay_record = asyncio.run(replay_root.run_async(replay.context))
            replay_final = asyncio.run(replay_root.build_result(replay_record)).as_record()
            assert replay_provider.contexts == []
            assert replay_final == final_result
        assert _tables(store) == before_tables and _inventory(store.path / 'artifacts') == before_artifacts
        assert blocked_reads == []
        assert all(row['result_already_saved'] for row in trace['cached_actions'])
        assert not workspace.exists()
        (tmp_path / 'FLUX_BALANCE_ORDINARY_WORKFLOW.json').write_text(json.dumps({
            'qualification': 'Caller-authored tiny model; real selected native model workers, one solve and finite result workers; scripted decisions, no model RPC.',
            'question': QUESTION, 'run_id': RUN_ID, 'store_path': str(store.path),
            'episodes': [{'episode_id': row['episode_id'], 'path': json.loads(row['path']),
                'completion': json.loads(row['completion'])} for row in episodes],
            'counts': {'episodes': 2, 'actions': 7, 'observations': 7, 'scripted_calls': 7, 'tool_operations': 6},
            'native_units': units, 'selected_software_sha256': digest(software), 'solve_call_count': 1,
            'observed_BC_flux': reaction_view['rows'][1]['values']['flux'],
            'objective_native_cobra': calculations['objective']['native_cobra'],
            'published_source_refs': {mode: source['id'] for mode, source in published.items()},
            'edited_model': edited, 'saved_sheet': state['saved_sheet'], 'typed_return_sha256': digest(returned),
            'typed_return_fields': sorted(returned), 'same_source_distinct_read_selectors': [outcomes[index]['result']['measurements'][0]['selector'] for index in (3, 4)],
            'pending_checkpoint': checkpoints[0], 'saved_solve_recovered_without_native': True,
            'parent_known_refs': sorted(known), 'closed_replay_trace': trace,
            'reference_and_byte_gate_controls': {'actual_contexts': [parent_id, science_id],
                'private_file_refs_denied': {name: reference for name, (reference, _) in private_refs.items()},
                'genuinely_received_files_allowed': {name: file['artifact_ref'] for name, file in allowed_files.items()},
                'caller_origin_wrapper_refs': [*private_wrappers.values(), *public_wrappers.values()],
                'receipts_and_action_counts_unchanged': True},
            'root_final_result': final_result,
            'closed_guarded_artifact_refs': sorted(guarded_refs), 'closed_blocked_artifact_reads': blocked_reads,
            'closed_artifact_guard_scope': 'Store.get_artifact is guarded for the actual four FBA capsules/public packets '
                'and retained native/worker/model/sheet Files; unrelated artifact reads delegate to the real Store. '
                'This is not global filesystem interception or withdrawal of every retained byte.',
            'reclosure_sql_change_count': store.db.total_changes - calls_before,
            'closed_replay_tables_and_artifacts_unchanged': True,
            'closed_replay_scope': ('root and cached scientific action paths' if any(row['role'] == 'scientific_process' for row in trace['cached_actions'])
                else 'root closed return; descendant frozen/restore callbacks are recorded separately'),
            'limits': 'The original raw model and native workspace were removed only after genuine recovery completed. '
                'Original absolute Store/worker paths are preserved; no relocation claim or biological conclusion. '
                'Missing per-entity tolerances remain unknown; native execution statistics receipts are not claimed.'
        }, indent=2) + '\n')


_FBA_REACTION_QUESTION = (
    'For the supplied five-metabolite control, what reaction correspondence and conditional '
    'SINK_GSSG objective and RHEA11740_ADDITION/UPTAKE_GSH fluxes are supported under the '
    'parent-supplied participant mapping and left-to-right orientation? Retain the database\'s '
    'undefined direction, unknown flux units, cofactor accounting and the limits on physiological '
    'growth or gene-function inference.')
_FBA_REACTION_QUALIFICATION = (
    'One new ordinary model-edit/solve integration control. The HTTP fixture replays authentic '
    'Rhea210 bytes, request, retrieval time and transport; it is not a live lookup. Participant '
    'correspondence, compartment, direction and bounds are explicit parent-owned numerical '
    'hypotheses. No gene correspondence, measured growth or physiological flux is inferred. '
    'The historical baseline/clamped calculations are not repeated.')


def _fba_reaction_inputs():
    """Load the three byte-exact scientific inputs; never follow their old host paths."""
    root = Path(__file__).parent / 'retained_workflow_fixtures/data/rhea11740'
    selected = {
        'rhea-live-reaction.json': ('a8f987d37abf10904d30b235eaf2cee8481307b8e4ea1105f0dbfabac484e641', 10960),
        'rhea-native.json': ('e6e0533ec0df9f0d7b9920cdc64bb3efb30038ab4c21bd4b7b85ce835c14a0df', 1010),
        'metabolic-addition-case.json': ('a4f34e8a80ff774d1e2786c240517bb12ea7d52433df3a50bbc30c569f301075', 5587),
    }
    bodies, pins = {}, {}
    for name, (sha, size) in selected.items():
        path = root / name
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == size and hashlib.sha256(raw).hexdigest() == sha
        bodies[name], pins[name] = raw, {'sha256': sha, 'size_bytes': size}
    capture = json.loads(bodies['rhea-live-reaction.json'])
    case = json.loads(bodies['metabolic-addition-case.json'])
    assert capture['schema'] == 'rhea_live_reaction_acquisition_v1' and capture['replay_verified'] is True
    assert case['schema'] == 'metabolic_reaction_addition_case_v1'
    assert case['acquisition_sha256'] == pins['rhea-live-reaction.json']['sha256']
    assert capture['native_body']['sha256'] == pins['rhea-native.json']['sha256']
    assert capture['native_body']['size_bytes'] == pins['rhea-native.json']['size_bytes']
    assert capture['request'] == {'operation': 'public.rhea.reaction', 'arguments': {'accession': 'RHEA:11740'}}
    assert case['mapping_basis'] == case['orientation_basis'] == 'caller_selected_numerical_control'
    assert case['source_qualifications']['source_direction'] == 'undefined'
    assert case['source_qualifications']['gene_correspondence'] == 'not_inferred'
    assert case['expected_stoichiometry'] == {'gsh_c': -2, 'nadp_c': -1, 'gssg_c': 1, 'nadph_c': 1, 'h_c': 1}
    return capture, bodies['rhea-native.json'], case, pins


def _fba_reaction_controller(path, initial):
    from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
    horizon = 1 if path[-1][0] == 'annotation' else 4
    def estimate(raw, parameters, contexts):
        return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1),
            parameters, {'fixture': 'one_database_cited_ordinary_fba_control'})
    return YieldController(str(path), initial, 0, YieldParameters(100, 50), estimate_with_context=estimate)


def test_actual_rhea_source_cited_edit_one_solve_and_requested_parent_return(tmp_path, monkeypatch):
    """Exercise the missing ordinary lookup→edit citation→selected numerical return join."""
    if os.environ.get('HMMER_NATIVE_ORACLE_FBA_REACTION_ADDITION') != '1':
        pytest.skip('requires explicit selection of one new ordinary Rhea-cited FBA solve')
    assert os.environ.get('HMMER529_ATTEMPT'), 'requires the selected bounded current runtime closure'
    from gene_annotation_episode.acquisition import SourceSnapshot
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.providers import _SessionConnection
    from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    from tests.test_flux_balance_model_tools import bound, edits
    from tests.test_homer_motif_saved_workflow import _archive_value, _encode
    from tests.test_molecular_sequence_n_glycosylation_native import JOURNALS, _checkpoint as checkpoint, _files, _history, _sqlite_pins
    import gene_annotation_episode.flux_balance_model_execution as model_execution
    import gene_annotation_episode.flux_balance_calculations as calculations_module
    import gene_annotation_episode.flux_balance_result_worker as result_worker_module

    capture, body, selected_case, fixture_pins = _fba_reaction_inputs()
    software = _software()  # This run's actual source/runtime/dependency declarations.
    resources, environments = _configuration(tmp_path, software)
    directory = tmp_path / 'rhea-cited-ordinary-fba'
    directory.mkdir()
    run_id = 'rhea-cited-ordinary-fba-positive'
    output = directory / 'FBA_REACTION_ADDITION_WORKFLOW.json'
    proof = {'version': 'ordinary_fba_reaction_addition_workflow_v1', 'run_id': run_id,
        'qualification': _FBA_REACTION_QUALIFICATION, 'question': _FBA_REACTION_QUESTION,
        'case_directory': str(directory), 'store_directory': str(directory / 'store'),
        'workflow_directory': str(directory / 'run'), 'fixture_pins': fixture_pins,
        'native_attempts': [], 'model_attempts': [], 'result_worker_attempts': [],
        'calls': [], 'phase': 'prepared', 'passed': False,
        'parent_post_return_model_call_claimed': False}
    state = {}

    class RetainedRheaHTTP:
        def __init__(self):
            self.calls = []
        def rhea_reaction(self, accession):
            assert accession == 'RHEA:11740'
            self.calls.append({'operation': 'public.rhea.reaction', 'arguments': {'accession': accession}})
            original = capture['source_record']
            metadata = capture['request_metadata']
            return SourceSnapshot('rhea', original['uri'], deepcopy(metadata['request']),
                original['retrieved_at'], body, 'application/json', deepcopy(metadata['transport']))
        _http = staticmethod(_forbidden)

    client = RetainedRheaHTTP()
    monkeypatch.setattr('socket.create_connection', _forbidden)
    native_run = ordinary.run_selected_flux_balance_native
    model_run = model_execution.run_selected_flux_balance_model
    worker_run = ordinary.run_selected_flux_balance_result_worker
    def selected_native(*args, **kwargs):
        assert not proof['native_attempts'], 'one new selected native solve only'
        proof['native_attempts'].append({'state': 'started'})
        result = native_run(*args, **kwargs)
        proof['native_attempts'][0] = {'state': 'returned', 'result': result}
        return result
    def selected_model(*args, **kwargs):
        assert not proof['model_attempts'], 'one selected model edit only'
        proof['model_attempts'].append({'state': 'started'})
        result = model_run(*args, **kwargs)
        proof['model_attempts'][0] = {'state': 'returned', 'result': result}
        return result
    def selected_worker(*args, **kwargs):
        assert not proof['result_worker_attempts'], 'one selected result calculation only'
        proof['result_worker_attempts'].append({'state': 'started'})
        result = worker_run(*args, **kwargs)
        proof['result_worker_attempts'][0] = {'state': 'returned', 'result': result}
        return result
    monkeypatch.setattr(ordinary, 'run_selected_flux_balance_native', selected_native)
    monkeypatch.setattr(model_execution, 'run_selected_flux_balance_model', selected_model)
    monkeypatch.setattr(ordinary, 'run_selected_flux_balance_result_worker', selected_worker)

    try:
        with Store(directory / 'store') as store:
            try:
                # The sequence supplies an engineering scope only, never a reaction/gene mapping.
                store.create_problem(raw_sequence='MKWAA', molecule='protein')
                scope = store.validate_scope()
                model_raw = canonical(selected_case['model']).encode()
                material = store.register_material(data=model_raw, name='parent-supplied Rhea11740 numerical control',
                    format='auto', use='evidence')
                model_source = store.get(material['source_ref'])
                original = {'artifact_ref': model_source['artifact_ref'], 'sha256': model_source['artifact_ref'][9:],
                    'size_bytes': len(model_raw), 'format': 'cobra_json'}
                assert store.get_artifact(original['artifact_ref']) == model_raw
                tools = ToolRegistry(store, clients=client, job_limits=deepcopy(POLICY))
                factory = ExecutionServiceFactory(resources, {}, 2, .25, .5, flux_balance_environments=environments)
                factory.configure_tool_registry(tools)
                publication = Path(__file__).resolve().parents[1] / 'research/slotted_process_library/publications/2026-10-24-001'
                binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=publication,
                    tool_catalog=tools.catalog(), child_roles=['scientific_process'])
                library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
                axis, pattern = library.reference('A110'), library.reference('P10')
                assert library.resolve(axis)['name'] == 'Biochemical feasibility and chemical/resource accounting'
                assert library.resolve(pattern)['name'] == 'Account for the coupled chemical system'
                selectors = [{'name': 'public.rhea.reaction', 'resources': 'api'}, {'name': FBA_TOOL, 'resources': 'local'}]
                selected_info = ScientificToolLibrary(directory / 'run/scientific-tool-library').resolve_tool_info(selectors, tools.catalog())
                sources = fba_fact_sources()
                fields = {'measurements': 'flux_balance_measurements', 'model_views': 'flux_balance_model_views',
                    'edited_models': 'flux_balance_edited_models', 'failures': 'flux_balance_failures'}
                schema = obj({**{field: sources[source]['report_schema'] for field, source in fields.items()},
                    'records': {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
                        'x-source': 'committed_record_refs'}})
                assignment = {'selection': {'version': 'scientific_process_selection_v3', 'evidence_axis': axis,
                    'thought_pattern': pattern, 'child_tool_info': selectors}, 'evidence_refs': scope['subject_refs'],
                    'constraints': {}, 'context': {'parent_model_file': original,
                        'participant_mapping': deepcopy(selected_case['participant_mapping']),
                        'expected_stoichiometry': deepcopy(selected_case['expected_stoichiometry']),
                        'mapping_basis': selected_case['mapping_basis'], 'orientation_basis': selected_case['orientation_basis'],
                        'bounds': deepcopy(selected_case['bounds']), 'source_qualifications': deepcopy(selected_case['source_qualifications']),
                        'qualification': _FBA_REACTION_QUALIFICATION}}
                proof.update(scope=deepcopy(scope), factory=factory.as_record(), scientific_binding=deepcopy(binding),
                    initial_known_record_refs=[material['id']], selected_tool_info=deepcopy(selected_info),
                    original_model_file=original, original_model_material=material, original_model_source=model_source,
                    parent_owned_mapping=deepcopy(assignment['context']))

                class Choices:
                    def __init__(self):
                        self.turns, self.cleanup_callbacks = {}, []
                    async def complete(self, episode_id, role, instructions, context, response_schema):
                        assert role == 'REASONING' and not context.get('feedback'), context.get('feedback')
                        self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                        turn = self.turns[episode_id]
                        scientific = context.get('scientific_process')
                        owner = 'scientific_process' if scientific is not None else 'annotation'
                        connection = object.__new__(_SessionConnection)
                        connection.scientific_prompt_states = {}
                        wire, wire_instructions = connection._presentation(episode_id, role, instructions, state_frame(plain(context)))
                        assert wire.startswith('TASK\n') and '\n\nSTEERING\n' in wire and _FBA_REACTION_QUESTION in wire
                        proof['calls'].append({'episode_id': episode_id, 'role': owner, 'turn': turn,
                            'context': plain(context), 'instructions': plain(instructions), 'wire': wire,
                            'wire_instructions': plain(wire_instructions)})
                        checkpoint(store, proof, output)
                        if owner == 'annotation':
                            assert turn == 1
                            state['parent_id'] = episode_id
                            answer = {'selection': {'kind': 'episode_child', 'role': 'scientific_process',
                                'goal': _FBA_REACTION_QUESTION, 'scope': scope, 'assignment': assignment,
                                'purpose': 'Return the actual source correspondence, conditional model values and qualifications.',
                                'schema_json': json.dumps(schema), 'initial_report_json': '{}'}, 'report_update': {}}
                        elif turn == 1:
                            state['science_id'] = episode_id
                            assert scientific['child_tool_info'] == selected_info
                            assert original['artifact_ref'] in wire and str(Path(os.environ['HMMER529_ATTEMPT'])) not in wire
                            assert all(item['name'] in wire for item in selected_info)
                            assert 'Biochemical feasibility and chemical/resource accounting' in wire
                            assert 'Account for the coupled chemical system' in wire
                            assert all(item['model_metabolite_id'] in wire for item in selected_case['participant_mapping'])
                            assert set((material['id'], model_source['id'], original['artifact_ref'])) <= set(flow.receipts.known(episode_id))
                            assert not store.list('reaction_record')
                            assert capture['source_record']['id'] not in flow.receipts.known(episode_id)
                            answer = action('public.rhea.reaction', {'accession': 'RHEA:11740'})
                        elif turn == 2:
                            lookup = context['last_local_outcome']
                            assert lookup['status'] == 'completed'
                            expected = {row['id']: row for row in [capture['source_record'], *capture['reaction_records'],
                                *capture['reaction_references'], *capture['chemical_references']]}
                            assert {ref: store.get(ref) for ref in lookup['record_refs']} == expected
                            reaction, = capture['reaction_records']
                            assert reaction['source_direction'] == 'undefined' and reaction['source_arrow'] == '='
                            state['database_source'] = store.get(reaction['source_ref'])
                            state['mapping_refs'] = list(lookup['record_refs'])
                            assert set(state['mapping_refs']) <= set(flow.receipts.known(episode_id))
                            assert store.get_artifact(state['database_source']['artifact_ref']) == body
                            assert _json(store, state['database_source']['request_ref']) == capture['request_metadata']
                            participants = {item['ordinal']: item for item in reaction['participants']}
                            assert len(participants) == len(selected_case['participant_mapping']) == 5
                            assert [item['side'] for item in reaction['participants']] == ['left', 'left', 'right', 'right', 'right']
                            assert [item['coefficient_expression'] for item in reaction['participants']] == ['2', '1', '1', '1', '1']
                            for item in selected_case['participant_mapping']:
                                actual = participants[item['ordinal']]
                                assert (actual['chemical_ref'], actual['source_accession']) == (item['chemical_ref'], item['source_accession'])
                                assert actual['source_location'] == '' and item['compartment'] == 'c'
                            receiver = EpisodeReturnRecords(store, run_id, failure_prefix='fba_reaction_addition_').context(episode_id)
                            admitted = flow.services.read_received_molecular_input(receiver, state['database_source']['id'],
                                'source', source_metadata_only=True)
                            assert admitted['failure'] is None and admitted['input']['witness']['record'] == state['database_source']
                            selected_edit = edits()
                            selected_edit['add_reactions'] = [{'id': selected_case['reaction_id'],
                                'name': reaction['source_equation'], 'lower': bound(selected_case['bounds'][0]),
                                'upper': bound(selected_case['bounds'][1]), 'stoichiometry': [
                                    {'metabolite_id': item['model_metabolite_id'],
                                        'coefficient': selected_case['expected_stoichiometry'][item['model_metabolite_id']]}
                                    for item in selected_case['participant_mapping']],
                                'source_refs': [state['database_source']['id']]}]
                            state['edits'] = deepcopy(selected_edit)
                            answer = action(FBA_TOOL, {**_arguments('edit'), 'model': _file_selection(original),
                                'edits': selected_edit, 'view': {**_model_view('effective'), 'collection': 'stoichiometry',
                                    'row_window': {'offset': 0, 'limit': 20}}, 'return_edited_model': True})
                        elif turn == 3:
                            edited = context['last_local_outcome']
                            assert edited['status'] in {'completed', 'partial'} and edited['result']['mode'] == 'edit'
                            state['edit_outcome'] = deepcopy(edited)
                            state['edited_file'], = deepcopy(edited['result']['edited_models'])
                            edit_source = store.get(edited['result']['source_ref'])
                            assert edit_source['parent_source_refs'] == [state['database_source']['id']]
                            request = explicit_request()
                            request['model_input']['file'] = _file_selection(state['edited_file'])
                            request['objective'] = {'kind': 'model_default', 'reaction_id': None}
                            state['solve_request'] = deepcopy(request)
                            answer = action(FBA_TOOL, {**_arguments('solve'), 'request': request,
                                'calculation_parameters': parameters(), 'projection': _projection('solve'), 'return_saved_sheet': False})
                        else:
                            assert turn == 4
                            solved = context['last_local_outcome']
                            assert solved['status'] in {'completed', 'partial'} and solved['result']['mode'] == 'solve'
                            state['solve_outcome'] = deepcopy(solved)
                            proof['phase'] = 'one_native_solve_returned'
                            checkpoint(store, proof, output)
                            for module, names in ((ordinary, ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker')),
                                    (model_execution, ('run_selected_flux_balance_model',)),
                                    (calculations_module, ('calculate_flux_balance_sheet',)),
                                    (result_worker_module, ('calculate_flux_balance_sheet',))):
                                for name in names: monkeypatch.setattr(module, name, _forbidden)
                            selector = {**_projection('native_values'), 'reaction_positions': [5, 0, 2]}
                            state['read_selector'] = deepcopy(selector)
                            answer = action(FBA_TOOL, {**_arguments('read_stored'), 'result_ref': solved['result']['source_ref'],
                                'view': {'kind': 'measurement', 'selector': selector}})
                        return _encode(answer, response_schema)
                    async def release(self, episode_id):
                        self.cleanup_callbacks.append(episode_id)

                provider = Choices()
                def assemble(registry, selected_provider):
                    actual_application = factory(store, run_id=run_id, directory=directory / 'run', tool_registry=registry)
                    return Workflow(store, registry, selected_provider, directory / 'run', run_id, _fba_reaction_controller,
                        _credit, project_child_credit=_credit, annotation_child_roles=('scientific_process',),
                        episode_record_receipts=True, initial_known_record_refs=[material['id']],
                        episode_binding_descriptors=[binding, *actual_application.episode_binding_descriptors],
                        role_credit_bindings=actual_application.role_credit_bindings,
                        job_progress_provider=actual_application.job_progress_provider)
                flow = assemble(tools, provider)
                root = flow.build('annotation', 'root', _FBA_REACTION_QUESTION, scope)
                record = asyncio.run(root.run_async(flow.context))
                final = _archive_value(asyncio.run(root.build_result(record)))
                proof.update(phase='workflow_returned', archive=_archive_value(record), final=final)
                checkpoint(store, proof, output)
                assert client.calls == [capture['request']]
                assert all(len(proof[name]) == 1 and proof[name][0]['state'] == 'returned' for name in
                    ('native_attempts', 'model_attempts', 'result_worker_attempts'))
                history = _history(store, run_id)
                episodes = sorted(history['runtime_episodes'], key=lambda row: len(json.loads(row['path'])))
                assert len(episodes) == 2 and all(row['state'] == 'yielded' for row in episodes)
                contexts = EpisodeReturnRecords(store, run_id, failure_prefix='fba_reaction_addition_')
                parent, science = [contexts.context(row['episode_id']) for row in episodes]
                assert [parent.episode_id, science.episode_id] == [state['parent_id'], state['science_id']]
                actions = [row for row in history['runtime_actions'] if row['episode_id'] == science.episode_id]
                assert [json.loads(row['action'])['tool'] for row in actions] == ['public.rhea.reaction', FBA_TOOL, FBA_TOOL, FBA_TOOL]
                assert [json.loads(row['action'])['arguments']['mode'] for row in actions[1:]] == ['edit', 'solve', 'read_stored']
                edit_capsule = _json(store, store.get(state['edit_outcome']['result']['source_ref'])['request_ref'])
                solve_source = store.get(state['solve_outcome']['result']['source_ref'])
                solve_capsule = _json(store, solve_source['request_ref'])
                assert edit_capsule['prepared']['model']['result']['model_optimize_call_count'] == 0
                assert edit_capsule['prepared']['model']['result']['edit_state'] == 'exact'
                assert edit_capsule['prepared']['model']['execution']['returncode'] == 0
                assert edit_capsule['prepared']['model']['execution']['failure'] is None
                assert edit_capsule['prepared']['arguments']['edits'] == state['edits']
                assert solve_capsule['prepared']['resolved_inputs'][0]['file'] == state['edited_file']
                native_execution = solve_capsule['prepared']['native']
                assert native_execution['terminal'] is native_execution['quiescent'] is True
                assert native_execution['returncode'] == 0 and native_execution['failure'] is None
                assert native_execution['plan']['requested_job']['native_flux_balance']['software'] == software
                assert native_execution['handle']['command'][0] == software['python']['path']
                worker_execution = solve_capsule['prepared']['worker']['execution']
                assert worker_execution['terminal'] is worker_execution['quiescent'] is True
                assert worker_execution['returncode'] == 0 and worker_execution['failure'] is None
                edited_document = _json(store, state['edited_file']['artifact_ref'])
                added, = [row for row in edited_document['reactions'] if row['id'] == selected_case['reaction_id']]
                assert added['metabolites'] == selected_case['expected_stoichiometry']
                assert (added['lower_bound'], added['upper_bound']) == tuple(selected_case['bounds'])
                assert store.get_artifact(original['artifact_ref']) == model_raw
                sheet, calculated = solve_capsule['sheet'], solve_capsule['calculations']
                assert sheet['native']['solve_call_count'] == sheet['native_solution']['native']['model_optimize_call_count'] == 1
                assert calculated['objective']['native_cobra']['value'] == calculated['objective']['full_calculated']['value'] == 5
                fluxes = {row['reaction_id']: row['flux']['value'] for row in sheet['native_solution']['native']['reaction_values']}
                assert fluxes == selected_case['expected']['added']['fluxes']
                read_outcome = json.loads(actions[3]['result'])
                assert read_outcome['status'] in {'completed', 'partial'} and read_outcome['result']['source_ref'] == solve_source['id']
                read_view, = read_outcome['result']['measurements']
                assert read_view['selector'] == state['read_selector']
                assert [row['reaction_id'] for row in read_view['rows']] == ['RHEA11740_ADDITION', 'UPTAKE_GSH', 'SINK_GSSG']
                assert [row['values']['flux']['flux']['value'] for row in read_view['rows']] == [5, 10, 5]
                assert all(row['values']['flux']['unit'] == {'native_text': None, 'basis': 'unknown'} for row in read_view['rows'])
                returned = json.loads(history['runtime_forms'][0]['form'])
                attempt, = history['runtime_report_attempts']
                assert attempt['failure'] is None and json.loads(attempt['form']) == returned
                assert flow.episode_bindings.received_report_facts(parent) == {}
                received = _archive_value(record)['units'][0]['child_result']['form']
                assert received == returned
                assert set(state['mapping_refs']) <= set(returned['records'])
                for outcome in (state['edit_outcome'], state['solve_outcome'], read_outcome):
                    for field in fields: assert all(value in returned[field] for value in outcome['result'][field])
                known = set(flow.receipts.known(parent.episode_id))
                assert {material['id'], model_source['id'], original['artifact_ref'], state['edited_file']['artifact_ref']} <= known
                assert set(state['mapping_refs']) <= known
                for source_ref in (state['edit_outcome']['result']['source_ref'], solve_source['id']):
                    source = store.get(source_ref)
                    assert source['artifact_ref'] not in known and source['request_ref'] not in known
                    for reference in (source['artifact_ref'], source['request_ref']):
                        assert flow.resolver(plain(parent.scope), context=parent)(reference, 'artifact') is False
                assert not returned.get('saved_sheets')
                assert final == {'credit': 0, 'pending_handles': []}
                proof.update(phase='typed_parent_verified', database_source=state['database_source'],
                    original_model_file=original, parent_owned_mapping=assignment['context'],
                    edited_file=state['edited_file'], edit_source=store.get(state['edit_outcome']['result']['source_ref']),
                    solve_source=solve_source, returned=returned, native_fluxes=fluxes,
                    objective=calculated['objective'], provider_cleanup_callbacks=provider.cleanup_callbacks)
                checkpoint(store, proof, output)
                before_tables, before_files = _tables(store), _files(directory / 'run')
                before_artifacts = _files(store.path / 'artifacts')
                class NoNewDecisions:
                    def __init__(self): self.cleanup_callbacks = []
                    async def complete(self, *args, **kwargs): _forbidden()
                    async def release(self, episode_id): self.cleanup_callbacks.append(episode_id)
                replay_provider = NoNewDecisions()
                with monkeypatch.context() as frozen:
                    frozen.setattr(Store, 'get_artifact', _forbidden)
                    frozen.setattr(ToolRegistry, 'execute_async', _forbidden)
                    for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel', 'release'):
                        frozen.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
                    frozen.setattr(client, 'rhea_reaction', _forbidden)
                    replay_tools = ToolRegistry(store, clients=client, job_limits=deepcopy(POLICY))
                    replay = assemble(replay_tools, replay_provider)
                    replay_root = replay.build('annotation', 'root', _FBA_REACTION_QUESTION, scope)
                    replay_record = asyncio.run(replay_root.run_async(replay.context))
                    assert _archive_value(replay_record) == _archive_value(record)
                    assert _archive_value(asyncio.run(replay_root.build_result(replay_record))) == final
                assert _tables(store) == before_tables and _files(directory / 'run') == before_files
                assert _files(store.path / 'artifacts') == before_artifacts
                assert client.calls == [capture['request']]
                proof.update(passed=True, phase='verified', closed_replay={'new_provider_decisions': 0,
                    'new_native_calls': 0, 'new_calculations': 0, 'new_tool_actions': 0,
                    'all_tables_and_artifacts_unchanged': True, 'provider_cleanup_callbacks': replay_provider.cleanup_callbacks})
            except BaseException as error:
                proof['passed'] = False
                proof['failure'] = {'exception_type': type(error).__name__, 'message': str(error)}
                raise
            finally:
                tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if set(JOURNALS) <= tables:
                    checkpoint(store, proof, output)
                else:
                    proof['available_tables_before_initialization_failure'] = sorted(tables)
                    output.write_text(json.dumps(proof, allow_nan=False, indent=2) + '\n')
    finally:
        proof['sqlite_pins'] = _sqlite_pins(directory / 'store')
        proof['sqlite_pins_sha256'] = digest(proof['sqlite_pins'])
        output.write_text(json.dumps(proof, allow_nan=False, indent=2) + '\n')


def _fba_retained550_input():
    """Authenticate the interrupted prefix before opening its owned copy."""
    selected = os.environ.get('HMMER_NATIVE_ORACLE_FBA_RETAINED550_PROOF')
    if not selected:
        pytest.skip('requires the explicitly pinned interrupted550 ordinary FBA prefix')
    path = Path(selected)
    assert path.is_absolute() and path.is_file() and not path.is_symlink()
    expected = 'b0ce33acf571eb2d4d1377249423af70bf397fa1ab31815c33a1ebfa66223706'
    assert os.environ['HMMER_NATIVE_ORACLE_FBA_RETAINED550_PROOF_SHA256'] == expected
    raw = path.read_bytes()
    assert len(raw) == 101979982 and hashlib.sha256(raw).hexdigest() == expected
    original = json.loads(raw)
    assert original['version'] == 'ordinary_fba_reaction_addition_workflow_v1'
    assert original['phase'] == 'one_native_solve_returned' and original['passed'] is False
    assert original['question'] == _FBA_REACTION_QUESTION
    assert original['run_id'] == 'rhea-cited-ordinary-fba-positive'
    assert original['failure']['exception_type'] == 'AssertionError'
    assert 'uniqueItems' in original['failure']['message']
    assert path.parent == Path(original['case_directory'])
    assert Path(original['store_directory']) == path.parent / 'store'
    assert Path(original['workflow_directory']) == path.parent / 'run'
    assert original['counts'] == dict(runtime_episodes=2, runtime_actions=4,
        runtime_observations=3, runtime_model_calls=6, runtime_forms=0,
        runtime_report_attempts=0, tool_operations=3)
    for name in ('native_attempts', 'model_attempts', 'result_worker_attempts'):
        assert len(original[name]) == 1 and original[name][0]['state'] == 'returned'
    database = path.parent / 'store/state.sqlite3'
    assert sorted(item.name for item in database.parent.glob('state.sqlite3*')) == ['state.sqlite3']
    pin = dict(name='state.sqlite3', sha256='aa88bc0ec6ed71573ebd6b7d84a994650a6efc02ef6159343f84a657a9ddb45a',
        size_bytes=24272896)
    assert original['sqlite_pins'] == [pin]
    assert database.stat().st_size == pin['size_bytes']
    assert hashlib.sha256(database.read_bytes()).hexdigest() == pin['sha256']
    return path, original


def _fba_retained_assemble(store, directory, proof, provider):
    """Reconstruct the actual factory and frozen binding without new selection."""
    factory = ExecutionServiceFactory.from_record(proof['factory'])
    assert factory.as_record() == proof['factory']
    registry = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=proof['run_id'], directory=directory, tool_registry=registry)
    workflow = Workflow(store, registry, provider, directory, proof['run_id'], _fba_reaction_controller,
        _credit, project_child_credit=_credit, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=proof['initial_known_record_refs'],
        episode_binding_descriptors=[proof['scientific_binding'], *application.episode_binding_descriptors],
        role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider)
    return workflow, registry


def _fba_retained550_journal_changes(before, after):
    """Distinguish ordinary pending completion from immutable completed history."""
    assert len(after['runtime_episodes']) == 2
    assert len(after['runtime_actions']) == len(after['runtime_observations']) == 5
    assert len(after['runtime_model_calls']) == 6
    assert len(after['tool_operations']) == 4
    assert len(after['runtime_forms']) == len(after['runtime_report_attempts']) == 1
    changes = []
    for old in before['runtime_episodes']:
        new, = [row for row in after['runtime_episodes'] if row['episode_id'] == old['episode_id']]
        assert {key: value for key, value in new.items() if key not in {'state', 'completion', 'archive'}} == {
            key: value for key, value in old.items() if key not in {'state', 'completion', 'archive'}}
        assert old['state'] == 'active' and old['completion'] is old['archive'] is None
        assert new['state'] == 'yielded' and new['completion'] is not None and new['archive'] is not None
        changes.append(dict(table='runtime_episodes', episode_id=old['episode_id'],
            fields=['state', 'completion', 'archive']))
    for table, key_fields in (('runtime_actions', ('episode_id', 'decision_index')),
            ('runtime_model_calls', ('episode_id', 'call_index'))):
        for old in before[table]:
            new, = [row for row in after[table] if all(row[key] == old[key] for key in key_fields)]
            pending = old['result'] is None if table == 'runtime_actions' else old['response'] is None
            if not pending:
                assert new == old
                continue
            allowed = {'result', 'credit', 'timing'} if table == 'runtime_actions' else {'response', 'timing'}
            assert {key: value for key, value in new.items() if key not in allowed} == {
                key: value for key, value in old.items() if key not in allowed}
            assert new['result' if table == 'runtime_actions' else 'response'] is not None
            if table == 'runtime_actions':
                assert new['credit'] == 0
            old_timing, new_timing = json.loads(old['timing']), json.loads(new['timing'])
            assert new_timing['version'] == old_timing['version']
            assert new_timing['intervals'][:len(old_timing['intervals'])] == old_timing['intervals']
            changes.append(dict(table=table, identity={key: old[key] for key in key_fields},
                fields=sorted(allowed)))
    assert all(row in after['runtime_observations'] for row in before['runtime_observations'])
    assert all(row in after['tool_operations'] for row in before['tool_operations'])
    return changes


def _fba_retained550_closed_receiver(store, directory, proof, returned, monkeypatch):
    """Replay the newly completed history, then inspect its actual received view."""
    from method_loop.episode import EpisodeView
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.providers import _SessionConnection
    from gene_annotation_episode.runtime import ReturnedActionUnit
    from tests.test_homer_motif_saved_workflow import _archive, _archive_value
    from tests.test_molecular_sequence_n_glycosylation_native import _files, _history
    before, run_files, artifacts = _tables(store), _files(directory), _files(store.path / 'artifacts')
    history = _history(store, proof['run_id'])
    episodes = sorted(history['runtime_episodes'], key=lambda row: len(json.loads(row['path'])))
    parent_archive, science_archive = [_archive(row, directory) for row in episodes]
    class NoDecisions:
        def __init__(self): self.cleanup_callbacks = []
        async def complete(self, *args, **kwargs): _forbidden()
        async def release(self, episode_id): self.cleanup_callbacks.append(episode_id)
    provider, closed_units, receiver = NoDecisions(), [], {}
    with monkeypatch.context() as guarded:
        guarded.setattr(Store, 'get_artifact', _forbidden)
        guarded.setattr(ToolRegistry, 'execute_async', _forbidden)
        workflow, registry = _fba_retained_assemble(store, directory, proof, provider)
        guarded.setattr(registry.clients, '_http', _forbidden)
        closed = workflow._closed_child_commission
        def authenticate_closed(*args, **kwargs):
            unit = closed(*args, **kwargs)
            assert isinstance(unit, ReturnedActionUnit)
            assert plain(unit.request.as_record()) == json.loads(episodes[1]['request'])
            assert _archive_value(unit.record) == science_archive
            assert plain(unit.result.as_record()) == dict(form=returned)
            closed_units.append(unit)
            return unit
        guarded.setattr(workflow, '_closed_child_commission', authenticate_closed)
        root = workflow.build('annotation', 'root', _FBA_REACTION_QUESTION, proof['scope'])
        record = asyncio.run(root.run_async(workflow.context))
        assert _archive_value(record) == parent_archive and len(closed_units) == 1
        assert _archive_value(asyncio.run(root.build_result(record))) == dict(credit=0, pending_handles=[])
        # This is a current read-side receiver reconstruction, not a historical
        # post-return model call or a new reasoning/action journal entry.
        receiver_scope = workflow.context.enter(root.grain, root.key)
        try:
            assert receiver_scope == root.source.path == record.path
            view = EpisodeView(grain=root.grain, key=root.key, path=receiver_scope,
                units_consumed=record.units_consumed,
                updates=tuple(workflow.context._child_updates.get(receiver_scope, ())),
                controller_state=record.controller_state, episode_ref=record.episode_ref, request=record.request)
            assert _archive_value(view.controller_state) == parent_archive['controller_state']
            assert [plain(report.as_record()) for report in view.child_reports] == [returned]
            class ReceiverCaptured(BaseException): pass
            async def capture_call(source, context, schema):
                assert source is root.source and context['child_reports'] == [returned]
                instructions = source.instructions(context)
                connection = object.__new__(_SessionConnection)
                connection.scientific_prompt_states = {}
                wire, wire_instructions = connection._presentation(source.episode_id, 'REASONING',
                    instructions, state_frame(plain(context)))
                assert wire.startswith('TASK\n') and '\n\nSTEERING\n' in wire
                assert _FBA_REACTION_QUESTION in wire
                for literal in ('RHEA11740_ADDITION', 'UPTAKE_GSH', 'SINK_GSSG', 'unknown', '5.0', '10.0'):
                    assert literal in wire
                assert proof['original_case_directory'] not in wire and str(directory) not in wire
                receiver.update(context=plain(context), schema=deepcopy(schema), instructions=plain(instructions),
                    wire=wire, wire_instructions=plain(wire_instructions),
                    current_receiver_builder_verified=True, historical_post_return_model_call_claimed=False)
                raise ReceiverCaptured()
            guarded.setattr(DecisionSource, 'call', capture_call)
            previous_calls = root.source.calls
            with pytest.raises(ReceiverCaptured): asyncio.run(root.source.next(view))
            assert root.source.calls == previous_calls and receiver
        finally:
            workflow.context.leave(receiver_scope)
    assert _tables(store) == before and _history(store, proof['run_id']) == history
    assert _files(directory) == run_files and _files(store.path / 'artifacts') == artifacts
    return dict(new_provider_decisions=0, new_tool_actions=0, new_native_calls=0, new_calculations=0,
        no_Store_get_artifact_calls=True, integrity_inventory_reads_performed=True,
        all_tables_and_files_unchanged=True,
        provider_cleanup_callbacks=provider.cleanup_callbacks, receiver_reconstruction=receiver)


def test_retained550_rhea_cited_fba_pending_read_typed_parent_and_closed_replay(tmp_path, monkeypatch):
    """Continue only the rejected stored-read callback; preserve the one550 solve."""
    from gene_annotation_episode.decision_context import state_frame
    from gene_annotation_episode.providers import _SessionConnection
    from tests.test_homer_motif_saved_workflow import _archive_value, _encode
    from tests.test_molecular_sequence_n_glycosylation_native import _checkpoint as checkpoint, _files, _history, _sqlite_pins
    import gene_annotation_episode.flux_balance_model_execution as model_execution
    import gene_annotation_episode.flux_balance_calculations as calculations_module
    import gene_annotation_episode.flux_balance_result_worker as result_worker_module
    import gene_annotation_episode.flux_balance_ordinary as selected_execution
    original_path, original = _fba_retained550_input()
    original_case = original_path.parent
    workspace = Path(original['factory']['resources']['ordinary-selected']['workspace'])
    inventories = {str(path): _files(path) for path in (original_case, workspace)}
    case = tmp_path / 'retained550-rhea-cited-fba'
    shutil.copytree(original_case, case, copy_function=shutil.copy2, symlinks=True)
    assert _files(case) == inventories[str(original_case)]
    output = case / 'FBA_RETAINED550_CONTINUATION.json'
    proof = {key: deepcopy(original[key]) for key in ('run_id', 'question', 'scope', 'factory',
        'scientific_binding', 'initial_known_record_refs', 'selected_tool_info', 'parent_owned_mapping')}
    proof.update(version='ordinary_fba_retained550_continuation_v1', phase='copied', passed=False,
        case_directory=str(case), store_directory=str(case / 'store'), workflow_directory=str(case / 'run'),
        original_case_directory=str(original_case), original_test_passed=False,
        original_failure=deepcopy(original['failure']), original_proof=dict(path=str(original_path),
            sha256=hashlib.sha256(original_path.read_bytes()).hexdigest(), size_bytes=original_path.stat().st_size),
        calls=[], body_reads=[], new_native_calls=0, new_model_edit_calls=0, new_calculations=0,
        new_result_worker_calls=0, new_sources=0,
        qualification='Continue the actual unanswered550 callback with a valid unique selector. '
            'The original rejected selection and failed test remain recorded; no edit, solve, result calculation or lookup repeats.')
    actual_get = Store.get_artifact
    try:
        with Store(case / 'store') as store:
            assert _history(store, proof['run_id']) == original['history']
            before_tables, before_artifacts = _tables(store), _files(store.path / 'artifacts')
            sources_before = deepcopy(store.list('source'))
            old_actions = original['history']['runtime_actions']
            science_actions = [row for row in old_actions if json.loads(row['action'])['kind'] == 'tool']
            assert [json.loads(row['action'])['tool'] for row in science_actions] == ['public.rhea.reaction', FBA_TOOL, FBA_TOOL]
            lookup, edited, solved = [json.loads(row['result']) for row in science_actions]
            assert [edited['result']['mode'], solved['result']['mode']] == ['edit', 'solve']
            science_id = science_actions[0]['episode_id']
            source_records = [store.get(outcome['result']['source_ref']) for outcome in (edited, solved)]
            allowed = {reference for source in source_records for reference in (source['artifact_ref'], source['request_ref'])}
            capsules = [_json(store, source['request_ref']) for source in source_records]
            edit_capsule, solve_capsule = capsules
            assert edit_capsule['prepared']['model'] == original['model_attempts'][0]['result']
            assert solve_capsule['prepared']['native'] == original['native_attempts'][0]['result']
            assert solve_capsule['prepared']['worker']['capture'] == original['result_worker_attempts'][0]['result']
            assert edit_capsule['prepared']['model']['result']['model_optimize_call_count'] == 0
            assert edit_capsule['prepared']['arguments']['edits']['add_reactions'][0]['source_refs'] == [
                'source_c42c3814aa3399b57f480502']
            assert source_records[0]['parent_source_refs'] == ['source_c42c3814aa3399b57f480502']
            edited_file, = edited['result']['edited_models']
            assert solve_capsule['prepared']['resolved_inputs'][0]['file'] == edited_file
            sheet, calculated = solve_capsule['sheet'], solve_capsule['calculations']
            assert sheet['native']['solve_call_count'] == sheet['native_solution']['native']['model_optimize_call_count'] == 1
            assert calculated['objective']['native_cobra']['value'] == calculated['objective']['full_calculated']['value'] == 5
            fluxes = {row['reaction_id']: row['flux']['value'] for row in sheet['native_solution']['native']['reaction_values']}
            assert fluxes == {'UPTAKE_GSH': 10, 'UPTAKE_NADP': 5, 'SINK_GSSG': 5,
                'SINK_NADPH': 5, 'SINK_H': 5, 'RHEA11740_ADDITION': 5}
            selector = {**_projection('native_values'), 'reaction_positions': [5, 0, 2]}
            arguments = {**_arguments('read_stored'), 'result_ref': solved['result']['source_ref'],
                'view': {'kind': 'measurement', 'selector': selector}}
            pending, = [row for row in original['history']['runtime_model_calls'] if row['response'] is None]
            expected_feedback = json.loads(pending['request'])['context']['feedback']
            assert pending['episode_id'] == science_id and pending['call_index'] == 4
            assert expected_feedback == {'category': 'action_contract', 'status': 'invalid',
                'detail': {'code': 'schema_validation', 'issues': [{'expected': True,
                    'path': ['arguments', 'view', 'selector', 'reaction_positions'], 'rule': 'uniqueItems'}], 'more_issues': False}}
            def retained_only(current, reference):
                assert reference in allowed, 'original input/native/software body forbidden: ' + reference
                proof['body_reads'].append(reference)
                return actual_get(current, reference)
            class PendingRead:
                def __init__(self): self.cleanup_callbacks = []
                async def complete(self, episode_id, role, instructions, context, response_schema):
                    assert not proof['calls'], 'only the original unanswered callback may run'
                    assert episode_id == science_id and role == 'REASONING'
                    assert context.get('feedback') == expected_feedback
                    assert context['last_local_outcome']['result'] == solved['result']
                    assert context['scientific_process']['child_tool_info'] == original['selected_tool_info']
                    connection = object.__new__(_SessionConnection)
                    connection.scientific_prompt_states = {}
                    wire, wire_instructions = connection._presentation(episode_id, role, instructions, state_frame(plain(context)))
                    assert wire.startswith('TASK\n') and '\n\nSTEERING\n' in wire and _FBA_REACTION_QUESTION in wire
                    for literal in ('RHEA11740_ADDITION', 'gsh_c', 'nadp_c', 'undefined', 'unknown'):
                        assert literal in wire
                    assert all(item['name'] in wire for item in original['selected_tool_info'])
                    proof['calls'].append(dict(episode_id=episode_id, context=plain(context),
                        instructions=plain(instructions), wire=wire, wire_instructions=plain(wire_instructions)))
                    checkpoint(store, proof, output)
                    return _encode(action(FBA_TOOL, arguments), response_schema)
                async def release(self, episode_id): self.cleanup_callbacks.append(episode_id)
            with monkeypatch.context() as guarded:
                for module, names in ((ordinary, ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker')),
                        (selected_execution, ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker')),
                        (model_execution, ('run_selected_flux_balance_model',)),
                        (calculations_module, ('calculate_flux_balance_sheet',)),
                        (result_worker_module, ('execute_flux_balance_worker', 'calculate_flux_balance_sheet'))):
                    for name in names: guarded.setattr(module, name, _forbidden)
                for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel', 'release'):
                    guarded.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
                guarded.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
                guarded.setattr('socket.create_connection', _forbidden)
                guarded.setattr(Store, 'put', _forbidden)
                guarded.setattr(Store, 'artifact', _forbidden)
                guarded.setattr(Store, 'get_artifact', retained_only)
                provider = PendingRead()
                workflow, registry = _fba_retained_assemble(store, case / 'run', proof, provider)
                execute = registry.execute_async
                dispatched = []
                async def literal_read(name, selected_arguments, **kwargs):
                    assert name == FBA_TOOL and selected_arguments == arguments and not dispatched
                    dispatched.append(deepcopy(selected_arguments))
                    return await execute(name, selected_arguments, **kwargs)
                guarded.setattr(registry, 'execute_async', literal_read)
                root = workflow.build('annotation', 'root', _FBA_REACTION_QUESTION, proof['scope'])
                record = asyncio.run(root.run_async(workflow.context))
                final = _archive_value(asyncio.run(root.build_result(record)))
                proof.update(phase='workflow_returned', archive=_archive_value(record), final=final)
                checkpoint(store, proof, output)
                assert len(proof['calls']) == len(dispatched) == 1 and final == dict(credit=0, pending_handles=[])
                history = _history(store, proof['run_id'])
                proof['allowed_original_pending_changes'] = _fba_retained550_journal_changes(original['history'], history)
                records = EpisodeReturnRecords(store, proof['run_id'], failure_prefix='retained_fba_')
                episodes = sorted(history['runtime_episodes'], key=lambda row: len(json.loads(row['path'])))
                parent, science = [records.context(row['episode_id']) for row in episodes]
                read_action, = [row for row in history['runtime_actions'] if row not in old_actions
                    and row['episode_id'] == science_id]
                assert read_action['decision_index'] == 4 and json.loads(read_action['action']) == {
                    'kind': 'tool', 'tool': FBA_TOOL, 'arguments': arguments}
                read = json.loads(read_action['result'])
                assert read['status'] == 'completed' and read['result']['source_ref'] == source_records[1]['id']
                assert read['changed_record_refs'] == [] and read['record_refs'] == [source_records[1]['id']]
                view, = read['result']['measurements']
                assert view['selector'] == selector
                assert [row['reaction_position'] for row in view['rows']] == [5, 0, 2]
                assert [row['reaction_id'] for row in view['rows']] == ['RHEA11740_ADDITION', 'UPTAKE_GSH', 'SINK_GSSG']
                assert [row['values']['flux']['flux']['value'] for row in view['rows']] == [5, 10, 5]
                assert all(row['values']['flux']['unit'] == {'native_text': None, 'basis': 'unknown'} for row in view['rows'])
                assert view['population']['expected_count'] == view['population']['retained_count'] == 6
                assert view['population']['expected_count_basis'] == 'model_population'
                assert view['page']['selected_row_count'] == view['page']['returned_row_count'] == 3
                assert view['page']['row_offset'] == 0 and view['page']['has_more'] is False
                returned = json.loads(history['runtime_forms'][0]['form'])
                attempt, = history['runtime_report_attempts']
                assert attempt['failure'] is None and json.loads(attempt['form']) == returned
                fields = {'measurements': 'flux_balance_measurements', 'model_views': 'flux_balance_model_views',
                    'edited_models': 'flux_balance_edited_models', 'failures': 'flux_balance_failures'}
                assert workflow.episode_bindings.received_report_facts(parent) == {}
                received = _archive_value(record)['units'][0]['child_result']['form']
                assert received == returned
                for field, source in fields.items():
                    for outcome in (edited, solved, read):
                        assert all(value in returned[field] for value in outcome['result'][field])
                assert set(lookup['record_refs']) <= set(returned['records'])
                known = set(workflow.receipts.known(parent.episode_id))
                assert {original['original_model_material']['id'], original['original_model_source']['id'],
                    original['original_model_file']['artifact_ref'], edited_file['artifact_ref']} <= known
                assert set(lookup['record_refs']) <= known
                for source in source_records:
                    for reference in (source['artifact_ref'], source['request_ref']):
                        assert reference not in known
                        assert workflow.resolver(plain(parent.scope), context=parent)(reference, 'artifact') is False
                assert not returned.get('saved_sheets')
                assert store.list('source') == sources_before and _files(store.path / 'artifacts') == before_artifacts
                after_tables = _tables(store)
                for name in ('records', 'artifacts', 'record_roots', 'tool_operations'):
                    if name == 'tool_operations':
                        assert set(before_tables[name]) <= set(after_tables[name]) and len(after_tables[name]) == len(before_tables[name]) + 1
                    else:
                        assert after_tables[name] == before_tables[name]
                proof.update(phase='typed_parent_verified', returned=returned, native_fluxes=fluxes,
                    objective=calculated['objective'], selected_read=view, no_new_sources=True,
                    original_completed_science_rows_unchanged=True,
                    answered_original_pending_callbacks=1, new_model_call_rows=0, new_stored_read_actions=1,
                    provider_cleanup_callbacks=provider.cleanup_callbacks)
                checkpoint(store, proof, output)
                proof['closed_replay'] = _fba_retained550_closed_receiver(store, case / 'run', proof, returned, guarded)
                proof.update(passed=True, phase='verified')
    except BaseException as error:
        proof['passed'] = False
        proof['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        proof['original_inventories_before'] = inventories
        proof['original_inventories_after'] = {path: _files(Path(path)) for path in inventories}
        proof['original_case_and_native_files_and_modes_unchanged'] = proof['original_inventories_after'] == inventories
        proof['sqlite_pins'] = _sqlite_pins(case / 'store')
        proof['sqlite_pins_sha256'] = digest(proof['sqlite_pins'])
        output.write_text(json.dumps(proof, allow_nan=False, indent=2) + '\n')
        assert proof['original_case_and_native_files_and_modes_unchanged']


def _fba_completed551_input():
    """Authenticate the completed delivery whose later root checker failed."""
    selected = os.environ.get('HMMER_NATIVE_ORACLE_FBA_COMPLETED551_PROOF')
    if not selected:
        pytest.skip('requires the explicitly pinned completed551 ordinary FBA delivery')
    path = Path(selected)
    assert path.is_absolute() and path.is_file() and not path.is_symlink()
    expected = 'dc66b73d26f988370ec763538189424be32dd64ef13a88a373c77e1724bf0f2c'
    assert os.environ['HMMER_NATIVE_ORACLE_FBA_COMPLETED551_PROOF_SHA256'] == expected
    raw = path.read_bytes()
    assert len(raw) == 50266198 and hashlib.sha256(raw).hexdigest() == expected
    recorded = json.loads(raw)
    assert recorded['version'] == 'ordinary_fba_retained550_continuation_v1'
    assert recorded['passed'] is False and recorded['phase'] == 'workflow_returned'
    assert recorded['failure'] == dict(exception_type='KeyError', message="'flux_balance_measurements'")
    assert recorded['question'] == _FBA_REACTION_QUESTION
    assert recorded['run_id'] == 'rhea-cited-ordinary-fba-positive'
    assert path.parent == Path(recorded['case_directory'])
    assert Path(recorded['store_directory']) == path.parent / 'store'
    assert Path(recorded['workflow_directory']) == path.parent / 'run'
    assert recorded['counts'] == dict(runtime_episodes=2, runtime_actions=5,
        runtime_observations=5, runtime_model_calls=6, runtime_forms=1,
        runtime_report_attempts=1, tool_operations=4)
    assert recorded['final'] == dict(credit=0, pending_handles=[])
    assert len(recorded['calls']) == 1
    assert all(row['state'] == 'yielded' for row in recorded['history']['runtime_episodes'])
    assert all(row['response'] is not None for row in recorded['history']['runtime_model_calls'])
    pin = dict(name='state.sqlite3', sha256='efa9bfcb66fdb1dd1e4ca17f0d27021ede7c255f51bcfeb7225544c31562d33b',
        size_bytes=24272896)
    assert recorded['sqlite_pins'] == [pin]
    database = path.parent / 'store/state.sqlite3'
    assert sorted(item.name for item in database.parent.glob('state.sqlite3*')) == ['state.sqlite3']
    assert database.stat().st_size == pin['size_bytes']
    assert hashlib.sha256(database.read_bytes()).hexdigest() == pin['sha256']
    return path, recorded


def test_completed551_fba_typed_parent_and_closed_replay_without_new_actions(tmp_path, monkeypatch):
    """Verify actual551 receiving and replay; do not repeat its valid stored read."""
    from tests.test_homer_motif_saved_workflow import _archive_value
    from tests.test_molecular_sequence_n_glycosylation_native import _checkpoint as checkpoint, _files, _history, _sqlite_pins
    import gene_annotation_episode.flux_balance_model_execution as model_execution
    import gene_annotation_episode.flux_balance_calculations as calculations_module
    import gene_annotation_episode.flux_balance_result_worker as result_worker_module
    import gene_annotation_episode.flux_balance_ordinary as selected_execution

    completed_path, completed = _fba_completed551_input()
    original_path, original = _fba_retained550_input()
    assert completed['original_proof'] == dict(path=str(original_path),
        sha256=hashlib.sha256(original_path.read_bytes()).hexdigest(), size_bytes=original_path.stat().st_size)
    assert completed['original_case_directory'] == str(original_path.parent)
    workspace = Path(original['factory']['resources']['ordinary-selected']['workspace'])
    protected_directories = (original_path.parent, completed_path.parent, workspace)
    inventories = {str(path): _files(path) for path in protected_directories}
    case = tmp_path / 'completed551-fba-postcheck'
    shutil.copytree(completed_path.parent, case, copy_function=shutil.copy2, symlinks=True)
    assert _files(case) == inventories[str(completed_path.parent)]
    output = case / 'FBA_COMPLETED551_POSTCHECK.json'
    proof = {key: deepcopy(completed[key]) for key in ('run_id', 'question', 'scope', 'factory',
        'scientific_binding', 'initial_known_record_refs', 'selected_tool_info', 'parent_owned_mapping',
        'original_case_directory')}
    proof.update(version='ordinary_fba_completed551_postcheck_v1', phase='copied', passed=False,
        case_directory=str(case), store_directory=str(case / 'store'), workflow_directory=str(case / 'run'),
        completed551_proof=dict(path=str(completed_path), sha256=hashlib.sha256(completed_path.read_bytes()).hexdigest(),
            size_bytes=completed_path.stat().st_size), original551_test_passed=False,
        original551_test_failure=deepcopy(completed['failure']),
        new_provider_decisions=0, new_model_call_rows=0, new_tool_actions=0,
        new_native_calls=0, new_model_edits=0, new_calculations=0, new_result_workers=0,
        new_sources=0, calls=[], private_retained_capsule_reads=[],
        qualification='Actual551 typed delivery completed before a checker used the SCI-only fact API on '
            'the uncontracted annotation root. Verify the actual parent child_result and current receiver '
            'without another decision, stored-read action, edit, solve or result calculation.')
    try:
        with Store(case / 'store') as store:
            before_history = _history(store, proof['run_id'])
            assert before_history == completed['history']
            before_tables, before_artifacts = _tables(store), _files(store.path / 'artifacts')
            sources_before = deepcopy(store.list('source'))
            changes = _fba_retained550_journal_changes(original['history'], before_history)
            assert changes == completed['allowed_original_pending_changes']
            episodes = sorted(before_history['runtime_episodes'], key=lambda row: len(json.loads(row['path'])))
            parent_id, science_id = [row['episode_id'] for row in episodes]
            actions = [row for row in before_history['runtime_actions'] if row['episode_id'] == science_id]
            assert [json.loads(row['action'])['tool'] for row in actions] == ['public.rhea.reaction', FBA_TOOL, FBA_TOOL, FBA_TOOL]
            lookup, edited, solved, read = [json.loads(row['result']) for row in actions]
            assert [outcome['result']['mode'] for outcome in (edited, solved, read)] == ['edit', 'solve', 'read_stored']
            assert len(before_history['tool_operations']) == 4
            form, = before_history['runtime_forms']
            returned = json.loads(form['form'])
            attempt, = before_history['runtime_report_attempts']
            assert attempt['failure'] is None and json.loads(attempt['form']) == returned
            unit, = completed['archive']['units']
            assert unit['child_result'] == dict(form=returned)
            assert completed['archive']['episode_id'] == parent_id
            fields = ('measurements', 'model_views', 'edited_models', 'failures')
            for outcome in (edited, solved, read):
                for field in fields:
                    assert all(value in returned[field] for value in outcome['result'][field])
            assert set(lookup['record_refs']) <= set(returned['records'])
            source_records = [store.get(outcome['result']['source_ref']) for outcome in (edited, solved)]
            edit_capsule, solve_capsule = [_json(store, source['request_ref']) for source in source_records]
            proof['private_retained_capsule_reads'] = [source['request_ref'] for source in source_records]
            assert edit_capsule['prepared']['model'] == original['model_attempts'][0]['result']
            assert solve_capsule['prepared']['native'] == original['native_attempts'][0]['result']
            assert solve_capsule['prepared']['worker']['capture'] == original['result_worker_attempts'][0]['result']
            assert edit_capsule['prepared']['model']['result']['model_optimize_call_count'] == 0
            database_source = lookup['result']['source_ref']
            assert source_records[0]['parent_source_refs'] == [database_source]
            assert edit_capsule['prepared']['arguments']['edits']['add_reactions'][0]['source_refs'] == [database_source]
            edited_file, = edited['result']['edited_models']
            assert solve_capsule['prepared']['resolved_inputs'][0]['file'] == edited_file
            sheet, calculated = solve_capsule['sheet'], solve_capsule['calculations']
            assert sheet['native']['solve_call_count'] == sheet['native_solution']['native']['model_optimize_call_count'] == 1
            assert calculated['objective']['native_cobra']['value'] == calculated['objective']['full_calculated']['value'] == 5
            fluxes = {row['reaction_id']: row['flux']['value'] for row in sheet['native_solution']['native']['reaction_values']}
            assert fluxes == dict(UPTAKE_GSH=10, UPTAKE_NADP=5, SINK_GSSG=5,
                SINK_NADPH=5, SINK_H=5, RHEA11740_ADDITION=5)
            view, = read['result']['measurements']
            assert view['selector'] == {**_projection('native_values'), 'reaction_positions': [5, 0, 2]}
            assert [row['reaction_id'] for row in view['rows']] == ['RHEA11740_ADDITION', 'UPTAKE_GSH', 'SINK_GSSG']
            assert [row['values']['flux']['flux']['value'] for row in view['rows']] == [5, 10, 5]
            assert all(row['values']['flux']['unit'] == {'native_text': None, 'basis': 'unknown'} for row in view['rows'])
            assert view['population']['expected_count'] == view['population']['retained_count'] == 6
            assert view['population']['expected_count_basis'] == 'model_population'
            assert view['page']['selected_row_count'] == view['page']['returned_row_count'] == 3
            assert view['page']['row_offset'] == 0 and view['page']['has_more'] is False
            assert read['changed_record_refs'] == [] and read['record_refs'] == [source_records[1]['id']]
            proof.update(phase='actual_parent_delivery_verified', returned=returned, selected_read=view,
                native_fluxes=fluxes, objective=calculated['objective'],
                original_pending_completion_changes_verified=changes)
            checkpoint(store, proof, output)
            with monkeypatch.context() as guarded:
                for module, names in ((ordinary, ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker')),
                        (selected_execution, ('run_selected_flux_balance_native', 'run_selected_flux_balance_result_worker')),
                        (model_execution, ('run_selected_flux_balance_model',)),
                        (calculations_module, ('calculate_flux_balance_sheet',)),
                        (result_worker_module, ('execute_flux_balance_worker', 'calculate_flux_balance_sheet'))):
                    for name in names: guarded.setattr(module, name, _forbidden)
                for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect', 'cancel', 'release'):
                    guarded.setattr('gene_annotation_episode.native_lifecycle.' + name, _forbidden)
                guarded.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
                guarded.setattr('socket.create_connection', _forbidden)
                guarded.setattr(Store, 'put', _forbidden)
                guarded.setattr(Store, 'artifact', _forbidden)
                proof['closed_replay'] = _fba_retained550_closed_receiver(store, case / 'run', proof, returned, guarded)
            assert _history(store, proof['run_id']) == before_history and _tables(store) == before_tables
            assert _files(store.path / 'artifacts') == before_artifacts and store.list('source') == sources_before
            proof.update(passed=True, phase='verified', all_completed551_rows_unchanged=True,
                no_new_sources=True, no_new_native_calls=True, no_new_calculations=True,
                no_new_stored_read_actions=True)
            checkpoint(store, proof, output)
    except BaseException as error:
        proof['passed'] = False
        proof['failure'] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        proof['original_inventories_before'] = inventories
        proof['original_inventories_after'] = {path: _files(Path(path)) for path in inventories}
        proof['original550_and_completed551_and_native_workspace_unchanged'] = proof['original_inventories_after'] == inventories
        proof['sqlite_pins'] = _sqlite_pins(case / 'store')
        proof['sqlite_pins_sha256'] = digest(proof['sqlite_pins'])
        output.write_text(json.dumps(proof, allow_nan=False, indent=2) + '\n')
        assert proof['original550_and_completed551_and_native_workspace_unchanged']
