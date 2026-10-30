"""One selected FBA Workflow case; choices are verification inputs only.

This module neither supplies tool information nor changes episode policy. Its
catalog assertion requires the real production entry. Native execution is an
explicit later bounded check, not a side effect of importing this helper.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.flux_balance_result_selection import validate_flux_balance_result_selector
from gene_annotation_episode.flux_balance_return_views import fba_fact_sources
from gene_annotation_episode.native_flux_balance_contracts import POLICY, validate_flux_balance_software
from gene_annotation_episode.native_flux_balance_local import local_flux_balance_plan
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


# Only generic compatible helpers are reused;490's globals and NMF case stay
# untouched. In particular its workflow_case/selector/result_form are not used.
G = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')
action, commission, provider_value = G.action, G.commission, G.provider_value
walk, history, rows, write = G.walk, G.history, G.rows, G.write
controller_factory = G.controller_factory

ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'flux-balance-workflow716'
OPERATION, MODE = 'perform_flux_balance_analysis', 'steady_state_linear_fba'
SOURCE_BASE = ROOT / 'verification/tool_graders_hmmer_map_verification_2026-10-28_529/check151c_producer688/producer-emissions/cobra_json'
MODEL_INPUT = SOURCE_BASE / 'input.json'
PARAMETERS_INPUT = SOURCE_BASE / 'calculated.json'
MODEL_SHA256 = '7fea0ee00e2ede8c67750c51cc5c23f1da6e9d9acb4fc575a030a50ca2f6b655'
SOFTWARE_SHA256 = '9a35a5c56d9672957322865f4f105b279b432a3f22ea8a96f0ef8f0ced2e05e5'
SOFTWARE_SIZE = 3540474
SOFTWARE_ENV = 'HMMER_NATIVE_ORACLE_FBA716_SOFTWARE'
TASK = ('Test the supplied candidate reaction hypothesis in the synthetic IN/AB/OUT model '
    'by setting both bounds of the parent-corresponding AB reaction to zero, retaining the model objective. '
    'Return the requested native and calculated '
    'model quantities, their unavailable units and qualifications; these predictions are '
    'conditional on the supplied model and are not observed fluxes or annotation probabilities.')
SOURCES = {'measurements': 'flux_balance_measurements', 'saved': 'flux_balance_saved_sheets',
    'failures': 'flux_balance_failures'}
TABLES = G.TABLES
HANDOFF_FORM = deepcopy(G.HANDOFF_FORM)
EXECUTION_SELECTION = {'version': 'flux_balance_execution_selection_v1',
    'environment_realization': 'operation_scoped_tmp_and_cache_v1'}
RUN_FIELDS = ['native_run', 'objective', 'reaction_population', 'variable_population',
    'constraint_population', 'reaction_bound_counts', 'variable_bound_counts',
    'active_population', 'balance_residual']


def selected_software():
    """Read only the explicitly supplied, collected714 descriptor identity."""
    path = Path(os.environ[SOFTWARE_ENV])
    assert path.is_absolute(), 'the selected software path must be explicit'
    raw = path.read_bytes()
    assert len(raw) == SOFTWARE_SIZE and hashlib.sha256(raw).hexdigest() == SOFTWARE_SHA256
    return validate_flux_balance_software(json.loads(raw))


def result_form(*fields, completed=False):
    definitions = fba_fact_sources()
    properties = {field: deepcopy(definitions[SOURCES[field]]['report_schema']) for field in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def selector(parameters, *, saved=None):
    projection = ({'version': 'flux_balance_projection_selector_v1', 'view': 'run_diagnostics',
        'fields': list(RUN_FIELDS), 'row_window': {'offset': 0, 'limit': len(RUN_FIELDS)}} if saved is None else {
        'version': 'flux_balance_projection_selector_v1', 'view': 'reaction_fluxes',
        'fields': ['flux', 'bound_check', 'active', 'csv_comparison', 'gpr'],
        'snapshot_phase': 'effective', 'reaction_positions': [2, 0, 1],
        'row_window': {'offset': 0, 'limit': 2}})
    return validate_flux_balance_result_selector({'version': 'flux_balance_result_selector_v1',
        'mode': 'native_result' if saved is None else 'saved_sheet_recalculation',
        'saved_sheet_file': deepcopy(saved), 'calculation_parameters': deepcopy(parameters),
        'projection': projection})


def assemble(store, directory, provider, configuration):
    factory = ExecutionServiceFactory.from_record(configuration['factory'])
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=tools)
    flow = Workflow(store, tools, provider, directory / 'run', RUN_ID,
        controller_factory=controller_factory, project_credit=lambda *_args, **_kwargs: 0,
        annotation_child_roles=('scientific_process',), episode_record_receipts=True,
        initial_known_record_refs=configuration['initial_refs'],
        episode_binding_descriptors=(configuration['scientific_binding'], *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return flow, tools


async def run_root(flow, configuration):
    root = flow.build('annotation', 'root', configuration['goal'], configuration['scope'])
    record = await root.run_async(flow.context)
    await root.build_result(record)
    return root, record, json.loads(''.join(iter_json(record.as_record())))


def worker_runs(directory):
    result = []
    for path in sorted((Path(directory) / 'run/execution-results').rglob('worker-plan.json')):
        plan = json.loads(path.read_bytes())
        if plan.get('version') != 'flux_balance_worker_plan_v1':
            continue
        root = path.parent
        capture = json.loads((root / 'worker-capture.json').read_bytes())
        execution = json.loads((root / 'worker-execution.json').read_bytes())
        result.append({'action_directory': str(root), 'directory': plan['directory'],
            'execution_directory': plan['directory'] + '.execution', 'plan': plan,
            'capture': capture, 'execution': execution})
    return result


def completed_fba_outcomes(store, *, result_contexts=None, receipt_reader=None):
    result, by_action = [], {}
    for row in rows(store, 'runtime_actions'):
        if row['result'] is None:
            continue
        outcome = json.loads(row['result'])
        version = outcome.get('result', {}).get('version')
        if version == 'native_flux_balance_acquired_result_v1':
            retained = outcome
        elif version == 'flux_balance_public_result_v1':
            key = f'{RUN_ID}:{row["episode_id"]}:{row["decision_index"]}'
            path = (store.path.parent / 'run/execution-results' / digest([RUN_ID, row['episode_id']])
                / 'native-flux-balance-actions' / digest(key) / 'receipt.json')
            retained = {**outcome, 'result': json.loads(path.read_bytes())}
        else:
            continue
        operation_key = f'{RUN_ID}:{row["episode_id"]}:{row["decision_index"]}'
        identity = (row['episode_id'], operation_key)
        intent = retained['result']['intent']
        assert (row['run_id'] == intent['run_id'] == RUN_ID
            and intent['episode_id'] == row['episode_id'] and intent['operation_key'] == operation_key), \
            'retained FBA outcome action identity conflict'
        assert identity not in by_action, 'duplicate retained FBA outcome action'
        by_action[identity] = retained
        result.append(retained)
    if result_contexts is None:
        assert receipt_reader is None
        return result
    assert receipt_reader is not None
    contexts = list(result_contexts)
    assert contexts and all(context.run_id == RUN_ID and context.role == 'results' for context in contexts)
    # This fixture selects exactly one original collect at index0 per results
    # child. General SQL/canonical row order does not establish that association.
    expected = [(context.episode_id, f'{RUN_ID}:{context.episode_id}:0') for context in contexts]
    assert len(set(expected)) == len(expected), 'duplicate requested FBA result context'
    assert set(by_action) == set(expected), 'retained FBA result action set differs'
    for context, identity in zip(contexts, expected):
        assert receipt_reader.read_completed(episode_id=context.episode_id,
            operation_key=identity[1], scope=context.scope) == by_action[identity]['result'], \
            'retained FBA outcome custody conflict'
    return [by_action[identity] for identity in expected]


def workflow_case(directory, software, *, before_saved=None):
    """Execute one later explicitly selected bounded case through real owners.

    Existing directories are refused to preserve any prior original run. This
    is a verification helper, not a production retry/continuation policy.
    """
    assert os.environ.get('HMMER529_ATTEMPT'), 'this case requires the bounded529 runtime'
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    store = Store(directory / 'state')
    try:
        store.create_problem(raw_sequence='ACGTACGT', molecule='dna')
        caller_sources = [json.loads(row['data']) for row in store.db.execute(
            "SELECT data FROM records WHERE record_type='source'")]
        assert len(caller_sources) == 1 and caller_sources[0]['origin'] == caller_sources[0]['provider'] == 'caller'
        scope = store.validate_scope()
        raw = MODEL_INPUT.read_bytes()
        assert len(raw) == 714 and hashlib.sha256(raw).hexdigest() == MODEL_SHA256
        model_ref = store.artifact(raw, 'application/json')
        model_source = store.put('source', {'provider': 'supplied716_model', 'accession': 'synthetic-model',
            'artifact_ref': model_ref, 'text_ref': None, 'request_ref': None, 'uri': None,
            'version': None, 'retrieved_at': None}, origin='tool', scope=scope)['id']
        mapping_artifact = store.artifact(canonical({'basis': 'supplied_synthetic_fixture',
            'model_reaction_id': 'AB', 'equation': 'A -> B', 'database_lookup_performed': False}), 'application/json')
        mapping_source = store.put('source', {'provider': 'supplied716_mapping', 'accession': 'synthetic-AB',
            'artifact_ref': mapping_artifact, 'text_ref': None, 'request_ref': None, 'uri': None,
            'version': None, 'retrieved_at': None}, origin='tool', scope=scope)['id']
        reaction_ref = store.put('reference', {'reference_type': 'reaction', 'source_ref': mapping_source,
            'accession': 'AB', 'label': 'Supplied synthetic AB reaction', 'sequence_ref': None,
            'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}, origin='tool', scope=scope)['id']
        hypothesis_ref = store.put('hypothesis', {'subject_refs': scope['subject_refs'], 'predicate': 'catalyzes',
            'value': {'type': 'reference', 'ref': reaction_ref}, 'context_refs': []}, origin='reasoning', scope=scope)['id']
        parameters = json.loads(PARAMETERS_INPUT.read_bytes())['parameters']
        assert [r['subject_id'] for r in parameters['reaction_bound_tolerances']] == ['IN', 'AB', 'OUT']
        assert [r['subject_id'] for r in parameters['constraint_tolerances']] == ['A', 'B']
        assert len(parameters['variable_bound_tolerances']) == 6
        software = validate_flux_balance_software(software)
        workspace = directory / 'workspace'
        workspace.mkdir()
        request = {'version': 'flux_balance_scientific_request_v1', 'operation': OPERATION, 'mode': MODE,
            'model_input': {'file': {'witness_ref': model_source, 'version': None,
                'artifact_field': 'artifact_ref', 'format': 'cobra_json'}, 'original_loader_selection': 'json_file',
                'repository_identifier': None, 'acquisition_receipt_file': None},
            'constraints': [{'reaction_id': 'AB', 'lower': {'kind': 'finite', 'value': 0},
                'upper': {'kind': 'finite', 'value': 0}}],
            'objective': {'kind': 'model_default', 'reaction_id': None},
            'solver_options': {'feasibility_tolerance': None, 'optimality_tolerance': None,
                'integrality_tolerance': None}}
        practical = {'version': 'flux_balance_scientific_assignment_v1',
            'resource_id': 'here', 'resource_kind': 'local', 'endpoint': 'completed_job_outputs', 'request': request,
            'progress_requirements': [
                {'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}},
                {'key': 'selected_outputs', 'credit': 0, 'predicate': {
                    'kind': 'requested_job_outputs', 'output_roles': ['solution', 'flux_csv']}}],
            'completion_keys': ['selected_outputs'], 'constraints': {'allocation': deepcopy(POLICY)}}
        launch = {'version': 'flux_balance_scientific_launch_v1', 'requests': {'here': practical},
            'constraints': {'allowed_resource_ids': ['here'], 'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}
        resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
            'native_flux_balance': [{'version': 'flux_balance_local_binding_v1', 'operation': OPERATION,
                'mode': MODE, 'software': deepcopy(software), 'model_formats': ['cobra_json']}]}}
        factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128,
            log_roles=('stdout', 'stderr', 'native_log'))
        preliminary_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
        application = factory(store, run_id=RUN_ID, directory=directory / 'run', tool_registry=preliminary_tools)
        actual_info = [row for row in application.resource_tool_catalogs.get('local', []) if row['name'] == OPERATION]
        # Tool information must come from the actual configured resource owner.
        assert len(actual_info) == 1 and actual_info[0]['description'] and actual_info[0]['instructions'], \
            'actual reviewed FBA resource_tool_contracts entry is required'
        binding = prepare_scientific_binding(run_directory=directory / 'run', source_directory=PUBLICATION,
            tool_catalog=preliminary_tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        library = ScientificProcessLibrary(directory / 'run/scientific-process-library')
        scientific_assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': library.reference('A110'), 'thought_pattern': library.reference('P10'),
            'child_tool_info': [{'name': OPERATION, 'resources': 'local'}]},
            'evidence_refs': [*scope['subject_refs'], model_source, mapping_source, reaction_ref, hypothesis_ref],
            'constraints': {'no_external_acquisition': True,
                'allocation': deepcopy(POLICY)}, 'context': {'supplied_sequence': 'ACGTACGT', 'molecule': 'dna',
                'supplied_model_file': deepcopy(request['model_input']), 'hypothesis_ref': hypothesis_ref,
                'reaction_correspondence': {'reaction_ref': reaction_ref, 'model_reaction_id': 'AB',
                    'source_ref': mapping_source, 'basis': 'supplied_synthetic_fixture'},
                'candidate_annotation_required': False}}
        configuration = {'factory': factory.as_record(), 'scientific_binding': binding, 'goal': TASK,
            'scope': scope, 'initial_refs': [model_source, mapping_source, reaction_ref, hypothesis_ref]}
        write(directory / 'fixture-configuration.json', configuration)
        write(directory / 'SELECTED_INPUTS.json', {'model_file': request['model_input'], 'parameters': parameters,
            'parameters_reused_from': str(PARAMETERS_INPUT), 'historical_outputs_reused_as_new_results': False,
            'software_sha256': digest(software), 'actual_tool_information': actual_info})
        full_form = result_form('measurements', 'saved', 'failures', completed=True)
        parent_form = result_form('measurements')

        class Choices:
            def __init__(self):
                self.calls, self.turns, self.native_bytes = [], {}, {}
                self.plan = self.target = self.handoff = self.original_return = None
                # Use the production presentation boundary without starting a
                # model transport or constructing another formatter.
                self.presentation = _SessionConnection.__new__(_SessionConnection)
                self.presentation.scientific_prompt_states = {}

            async def complete(self, episode_id, role, instructions, current, schema):
                model_text, model_instructions = self.presentation._presentation(
                    episode_id, role, instructions, plain(current))
                shown = canonical({'instructions': plain(instructions),
                    'context': plain(current), 'schema': plain(schema),
                    'model_text': model_text, 'model_instructions': model_instructions})
                for private in ('implementation_files', 'runtime_files', 'solver_runtime_files',
                        'source_function_sha256', 'fba_software_v1', 'PYTHONPATH'):
                    assert private not in shown, 'host FBA execution bookkeeping entered a model request'
                self.calls.append({'episode_id': episode_id, 'role': role,
                    'instructions': deepcopy(instructions),
                    'context': deepcopy(current), 'schema': deepcopy(schema),
                    'model_text': model_text, 'model_instructions': model_instructions})
                write(directory / f'decision-{len(self.calls) - 1}.json', self.calls[-1])
                assert not current.get('feedback'), current.get('feedback')
                self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
                turn = self.turns[episode_id]
                if 'practical_assignment' in current:
                    assert current['practical_assignment']['constraints']['allocation'] == POLICY
                    if turn == 1:
                        answer = action('practical.job.start')
                    else:
                        assert turn == 2, 'only the same original start and its terminal collection are selected'
                        reader = PracticalReceiptInformation(store, RUN_ID)
                        start, = [ref for ref in current['last_local_outcome']['record_refs']
                            if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                        target = owner.job_progress_provider.targets.read_target(start, scope)
                        assert target['origin_episode_id'] == episode_id
                        result = await asyncio.to_thread(native_lifecycle.wait_job,
                            native_lifecycle.NativeJobHandle(Path(target['execution_id'])))
                        assert result.returncode == 0, 'preserve this original native attempt; do not regenerate the case'
                        answer = action('practical.job.collect')
                elif current.get('execution_assignment', {}).get('version') == 'flux_balance_scientific_launch_v1':
                    assert turn == 1
                    answer = commission('launch_local', current['execution_assignment']['requests']['here'], scope,
                        HANDOFF_FORM, objective='Execute the assigned reaction-bound perturbation with its selected allocation.')
                elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                    assert turn == 1
                    answer = action('execution.results.collect')
                elif 'scientific_process' not in current:
                    assert turn == 1
                    answer = commission('scientific_process', scientific_assignment, scope, parent_form, objective=TASK)
                elif turn == 1:
                    answer = commission('launch', launch, scope, HANDOFF_FORM,
                        objective='Test the parent-supplied reaction hypothesis by clamping corresponding model reaction AB to zero.')
                elif turn == 2:
                    reader = PracticalReceiptInformation(store, RUN_ID)
                    self.handoff, = [ref for ref in current['child_reports'][-1]['references']
                        if reader.read(ref, scope)['receipt']['tool_name'] == 'practical.job.start']
                    self.target = owner.job_progress_provider.targets.read_target(self.handoff, scope)
                    result = await asyncio.to_thread(native_lifecycle.wait_job,
                        native_lifecycle.NativeJobHandle(Path(self.target['execution_id'])))
                    self.plan = local_flux_balance_plan(self.target['assignment'], self.target['execution_id'])
                    write(directory / 'original-native-plan.json', self.plan)
                    write(directory / 'native-lifecycle.json', {'returncode': result.returncode, 'metadata': result.metadata})
                    for spec in self.plan['outputs']:
                        path = Path(self.plan['attempt_directory']) / spec['relative_path']
                        if path.is_file():
                            self.native_bytes[spec['role']] = path.read_bytes()
                    assert result.returncode == 0, 'preserve this original native attempt; do not regenerate the case'
                    assert store.get_artifact(model_ref) == raw, 'selected perturbation changed the supplied input model'
                    answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                        'selector': selector(parameters)}, scope, full_form,
                        objective='Return the selected original FBA run diagnostics, saved numerical sheet and located qualifications.')
                elif turn == 3:
                    self.original_return = deepcopy(current['child_reports'][-1])
                    assert self.original_return['completed'], self.original_return
                    sheet_file, = self.original_return['saved']
                    if before_saved:
                        before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                            workspace=workspace, sheet_file=sheet_file, original_return=self.original_return,
                            provider=self, science_context=owner.native_flux_balance_returns.context(episode_id)))
                    prior = store.db.execute('SELECT delivery_ref FROM runtime_report_attempts WHERE '
                        'parent_episode_id=? AND decision_index=1', (episode_id,)).fetchone()
                    assert prior is not None
                    answer = {'selection': {'kind': 'redeliver_report', 'delivery_ref': prior['delivery_ref'],
                        'purpose': 'Redeliver the exact original requested FBA facts without another calculation.',
                        'schema_json': json.dumps(full_form)}, 'report_update': {}}
                else:
                    assert turn == 4 and current['child_reports'][-1] == self.original_return
                    sheet_file, = self.original_return['saved']
                    answer = commission('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                        'selector': selector(parameters, saved=sheet_file)}, scope, full_form,
                        objective='Recalculate the selected reaction quantities from the received sheet with explicit parameters and positions.')
                answer = provider_value(plain(answer), plain(schema))
                Draft202012Validator(plain(schema)).validate(answer)
                return answer

            async def release(self, episode_id):
                pass

        provider = Choices()
        flow, tools = assemble(store, directory, provider, configuration)
        owner = flow.episode_bindings.for_role('results')
        root, record, archive = asyncio.run(run_root(flow, configuration))
        records = list(walk(archive))
        contexts = {row['episode_id']: owner.native_flux_balance_returns.context(row['episode_id']) for row in records}
        by_role = {}
        for row in records:
            by_role.setdefault(contexts[row['episode_id']].role, []).append(row)
        result_contexts = [contexts[row['episode_id']] for row in by_role['results']]
        returned = [json.loads(flow.journal.row('runtime_forms', c.episode_id)['form']) for c in result_contexts]
        outcomes = [json.loads(flow.journal.row('runtime_actions', c.episode_id, 0)['result']) for c in result_contexts]
        retained = completed_fba_outcomes(store, result_contexts=result_contexts,
            receipt_reader=owner.native_flux_balance_results.receipts)
        assert len(retained) == len(outcomes) == 2
        scientific_context, = [contexts[row['episode_id']] for row in by_role['scientific_process']]
        forwarded = json.loads(flow.journal.row('runtime_forms', scientific_context.episode_id)['form'])
        case = SimpleNamespace(store=store, directory=directory, flow=flow, tools=tools, owner=owner,
            provider=provider, configuration=configuration, root=root, record=record, archive=archive,
            records=records, contexts=contexts, by_role=by_role, result_contexts=result_contexts,
            returned=returned, outcomes=retained, public_outcomes=outcomes, scientific_context=scientific_context,
            root_context=contexts[record.episode_id], forwarded=forwarded, parent_form=parent_form,
            full_form=full_form, scope=scope, workspace=workspace,
            job=deepcopy(provider.plan['requested_job']['native_flux_balance']), parameters=parameters,
            hypothesis_ref=hypothesis_ref, reaction_ref=reaction_ref, mapping_source=mapping_source,
            model_source=model_source, compact_assignment=practical)
        write(directory / 'CASE.json', {'scope': 'scripted choices, supplied synthetic molecular model, actual Workflow and local Cobra/GLPK',
            'returned': returned, 'forwarded': forwarded, 'archive': archive,
            'histories': {role: [r['controller_state'] for r in group] for role, group in by_role.items()}})
        return case
    except BaseException as error:
        write(directory / 'FAILURE_STATE.json', {'exception': type(error).__name__, 'message': str(error),
            'native_plan_saved': (directory / 'original-native-plan.json').exists(),
            'original_run_must_be_preserved': True, 'automatic_retry': False})
        store.close()
        raise
