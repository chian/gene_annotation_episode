"""Actual selected RNA tools through Workflow, local execution and typed results.

Episode choices and scientific horizons are engineering fixtures. Native calls,
the original launch/local commission, bounded result worker, deterministic
numbers, typed form admission and practical terminal estimator are real paths.
No configured-model scientific judgment or annotation credit is claimed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_rna_structure_contracts import POLICY, requested_job_from_rna_structure
from gene_annotation_episode.native_rna_structure_local import local_rna_structure_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.rna_structure_result_views import FAMILY_SOURCES, REFERENCE_SOURCE, SAVED_SOURCE, rna_structure_fact_sources
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_rna_structure_contracts import job as native_job, rna_input


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'rna-structure-integration360'
SOURCES = {**FAMILY_SOURCES, 'references': REFERENCE_SOURCE, 'saved': SAVED_SOURCE}


def result_form(fields=('summary', 'references', 'saved'), *, completed=True):
    descriptors = rna_structure_fact_sources()
    properties = {name: descriptors[SOURCES[name]]['report_schema'] for name in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def selector(*, family='summary', metrics=None):
    return {'version': 'native_rna_structure_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'family': family, 'rows': {'offset': 0, 'limit': 20},
            'metrics': metrics if metrics is not None else ['pair_count', 'paired_fraction', 'stack_count',
                'long_stem_fraction', 'accepted_pair_fraction', 'loop_mean_unpaired_nt']}}


def selected(name):
    return {'selection': {'kind': 'tool', 'name': name, 'arguments': {}}, 'report_update': {}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Investigate the supplied RNA sequence and structure using the selected numerical measurements.',
        'scope': scope, 'purpose': 'Return exactly the requested original quantities and their qualifications.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}


def provider_value(value, schema):
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            candidate = provider_value(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get('type') == 'string' and isinstance(value, dict) and schema.get('description', '').startswith('JSON encoding'):
        return json.dumps(value)
    if schema.get('type') == 'object' and isinstance(value, dict):
        result = dict(value)
        for name, field in schema.get('properties', {}).items():
            if name in result:
                result[name] = provider_value(result[name], field)
            elif name in schema.get('required', []) and Draft202012Validator(field).is_valid(None):
                result[name] = None
        return result
    if isinstance(value, list) and 'items' in schema:
        return [provider_value(item, schema['items']) for item in value]
    return value


def walk(record):
    yield record
    for unit in record['units']:
        if unit.get('child') is not None:
            yield from walk(unit['child'])


def history(record):
    return [unit['controller_step']['marginal_credit'] for unit in record['units']]


def values(row):
    return {cell['name']: cell['value'] for cell in row['measurements']}


def workflow_case(tmp_path, *, prediction=True, energy=False, failed=False, selection=None,
        results_fields=('summary', 'references', 'saved'), parent_fields=('summary',),
        nested=False, saved=False, before_saved=None, before_collect=None):
    store = Store(tmp_path / 'state')
    supplied = tmp_path / 'supplied-sequence.fa'
    supplied.write_text('>supplied_sequence_without_candidate_annotation\n' + ('GAC' if failed else 'GGGAAACCC') + '\n')
    store.create_problem(supplied, molecule='rna', format='fasta')
    scope = store.validate_scope()
    raw = None
    if failed:
        original = rna_input(energy=True)
        original.update(sequence='GAC', dot_bracket='(.)')
        raw = (canonical(original) + '\n').encode()
    job = native_job(tmp_path, prediction=prediction, energy=energy, native=prediction or energy, raw=raw)
    for output in job['outputs']:
        output['relative_path'] = 'selected/' + output['relative_path']
    request = requested_job_from_rna_structure(job)
    chosen = deepcopy(selection if selection is not None else selector())
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_rna_structure': [{key: deepcopy(job[key]) for key in ('operation', 'mode', 'software')}]}}
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'rna-structure360',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'handoff', 'credit': 7,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': assignment},
        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
            'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}
    handoff_form = {'type': 'object', 'additionalProperties': False, 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
            'x-source': 'execution_handoff_refs'}}, 'required': ['completed', 'references']}
    results_form = result_form(results_fields)
    science_form = result_form(parent_fields, completed=False)
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    tools = ToolRegistry(store)
    application = factory(store, run_id=RUN_ID, directory=tmp_path / 'run', tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=tmp_path / 'run', source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(tmp_path / 'run/scientific-process-library')
    science_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': job['operation'], 'resources': 'local'}]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True,
            'allocation': deepcopy(POLICY)}, 'context': {'supplied_sequence': 'GAC' if failed else 'GGGAAACCC',
            'molecule': 'rna', 'candidate_annotation_required': False}}
    owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' or nested and len(path) == 2 else 3 if saved else 2
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {'fixture': 'explicit_scientific_boundary_verification_horizon'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    class Choices:
        def __init__(self):
            self.calls, self.science_calls = [], {}
            self.handoff = self.plan = self.first_return = self.saved_selector = None

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({'episode_id': episode_id, 'role': role, 'instructions': instructions,
                'context': deepcopy(current), 'schema': plain(schema)})
            assert not current.get('feedback'), current.get('feedback')
            if 'practical_assignment' in current:
                assert current['practical_assignment'] == assignment
                answer = selected('practical.job.start')
            elif current.get('execution_assignment', {}).get('version') == 'execution_launch_assignment_v1':
                answer = child('launch_local', assignment, scope, handoff_form)
            elif current.get('execution_assignment', {}).get('version') == RESULTS_VERSION:
                answer = selected('execution.results.collect')
            elif 'scientific_process' not in current:
                answer = child('scientific_process', science_assignment, scope, science_form)
            else:
                self.science_calls[episode_id] = self.science_calls.get(episode_id, 0) + 1
                turn = self.science_calls[episode_id]
                if nested and len(self.science_calls) == 1:
                    assert turn == 1
                    answer = child('scientific_process', science_assignment, scope, science_form)
                elif turn == 1:
                    answer = child('launch', launch, scope, handoff_form)
                elif turn == 2:
                    self.handoff, = current['child_reports'][-1]['references']
                    target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                    # Engineering synchronization observes only the already
                    # selected handle; it adds no episode action or credit.
                    observed = await asyncio.to_thread(native.wait_job,
                        native.NativeJobHandle(Path(target['execution_id'])))
                    assert observed.returncode == (1 if failed else 0)
                    self.plan = local_rna_structure_plan(assignment, target['execution_id'])
                    if before_collect:
                        before_collect(SimpleNamespace(store=store, owner=owner, flow=flow,
                            target=target, plan=self.plan, assignment=assignment))
                    answer = child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                        'selector': chosen}, scope, results_form)
                else:
                    assert saved and turn == 3
                    self.first_return = deepcopy(current['child_reports'][-1])
                    descriptor, = self.first_return['saved']
                    changed = deepcopy(job['grading_parameters'])
                    changed['topology']['long_stem_min_pairs'] = 4
                    changed['pair_composition']['accepted_ordered_pair_types'] = ['AU', 'UA']
                    self.saved_selector = {'version': 'native_rna_structure_saved_sheet_selector_v1',
                        'acquisition': 'retained_sheet_only', 'saved_input': descriptor,
                        'parameters': changed, 'projection': deepcopy(chosen['projection'])}
                    if before_saved:
                        before_saved(SimpleNamespace(store=store, owner=owner, flow=flow,
                            plan=self.plan, returned=self.first_return, descriptor=descriptor,
                            assignment=assignment, workspace=workspace, job=job))
                    answer = child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                        'selector': self.saved_selector}, scope, results_form)
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, tmp_path / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=[],
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build('annotation', 'root', 'Investigate the exact supplied RNA sequence and structure.', scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(execute())
    records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
    contexts = {row['episode_id']: owner.native_rna_structure_returns.context(row['episode_id']) for row in records}
    by_role = {}
    for row in records:
        by_role.setdefault(contexts[row['episode_id']].role, []).append(row)
    result_contexts = [contexts[row['episode_id']] for row in by_role['results']]
    science_contexts = [contexts[row['episode_id']] for row in by_role['scientific_process']]
    returned = [json.loads(flow.journal.row('runtime_forms', ctx.episode_id)['form']) for ctx in result_contexts]
    forwarded = [json.loads(flow.journal.row('runtime_forms', ctx.episode_id)['form']) for ctx in science_contexts]
    outcomes = [json.loads(flow.journal.row('runtime_actions', ctx.episode_id, 0)['result']) for ctx in result_contexts]
    case = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root,
        record=record, records=records, by_role=by_role, contexts=contexts, root_context=contexts[record.episode_id],
        science_contexts=science_contexts, result_contexts=result_contexts, returned=returned, forwarded=forwarded,
        outcomes=outcomes, results_form=results_form, science_form=science_form, scientific_assignment=science_assignment,
        assignment=assignment, resources=resources, job=job, request=request, scope=scope, selector=chosen,
        plan=provider.plan, workspace=workspace, saved=saved, nested=nested)
    (tmp_path / 'CASE.json').write_text(json.dumps({'operation': job['operation'], 'mode': job['mode'],
        'scope': 'scripted engineering choices; actual native execution and Workflow; no model science',
        'native_plan': provider.plan, 'outcomes': outcomes, 'results_form': results_form, 'science_form': science_form,
        'returned': returned, 'forwarded': forwarded, 'histories': {role: [row['controller_state'] for row in rows]
            for role, rows in by_role.items()}}, indent=2) + '\n')
    for index, call in enumerate(provider.calls):
        (tmp_path / f'decision-{index}.json').write_text(json.dumps(call, indent=2) + '\n')
    return case


def assert_accounting(case):
    assert case.store.count('observation') == case.store.count('annotation') == 0
    for row in case.records:
        episode = row['episode_id']
        actions = case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?', (episode,)).fetchone()[0]
        observations = case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (episode,)).fetchone()[0]
        assert actions == observations == row['units_consumed']
    assert history(case.by_role['annotation'][0]) == [0]
    assert history(case.by_role['scientific_process'][-1]) == ([0, 0, 0] if case.saved else [0, 0])
    assert history(case.by_role['launch_local'][0]) == [7]
    assert history(case.by_role['launch'][0]) == [3]
    assert [history(row) for row in case.by_role['results']] == ([[2], [0]] if case.saved else [[2]])
    assert len(list(case.workspace.rglob('rna-structure-plan.json'))) == 1
    for role in ('launch_local', 'launch', 'results'):
        for row in case.by_role[role]:
            assert row['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()


@pytest.mark.parametrize('prediction,energy', [(True, False), (False, True), (False, False)],
    ids=['mfe_prediction', 'supplied_native_evaluation', 'supplied_topology_only'])
def test_real_selected_tool_to_native_sheet_and_requested_typed_return(tmp_path, prediction, energy):
    energy_metric = 'mfe_kcal_mol' if prediction else 'evaluated_energy_kcal_mol'
    chosen = selector(metrics=['pair_count', 'paired_fraction', 'stack_count', 'loop_mean_unpaired_nt', energy_metric])
    case = workflow_case(tmp_path, prediction=prediction, energy=energy, selection=chosen)
    try:
        body = case.outcomes[0]['result']
        assert body['native_success'] and body['capture_complete'] and body['delivery_complete']
        returned, = case.returned
        assert returned['completed']
        row, = returned['summary']
        assert values(row) | {} == {**{'pair_count': 3, 'paired_fraction': 2 / 3,
            'stack_count': 2, 'loop_mean_unpaired_nt': 3}, **({energy_metric: -1.2000000476837158}
                if prediction or energy else {})}
        if not prediction and not energy:
            assert row['unavailable'][0]['name'] == energy_metric
        assert [cell['name'] for cell in row['measurements'] + row['unavailable']] == chosen['projection']['metrics']
        assert case.forwarded == [{'summary': returned['summary']}]
        case.owner.validate_report(case.result_contexts[0], returned, case.results_form)
        case.owner.validate_received_report(case.science_contexts[0], case.forwarded[0], case.science_form)
        received = {group['fact_source']: group['facts'] for group in
            case.owner.native_rna_structure_returns.received_context(case.root_context)}
        assert received == {FAMILY_SOURCES['summary']: returned['summary']}
        prepared = body['prepared']
        sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
        components = json.loads(case.store.get_artifact(prepared['components_artifact_ref']))
        assert sheet['mode'] == components['mode'] == case.job['mode']
        assert prepared['sheet_artifact_ref'] != prepared['components_artifact_ref']
        bundle = json.loads(case.store.get_artifact(body['capture']['bundle_artifact_ref']))
        assert bundle['identity'] == case.plan['identity'] and bundle['requested_job'] == case.request
        assert bundle['native_status'] == 'complete' and bundle['returncode'] == 0
        assert all(item['state'] == 'present' for item in bundle['files'])
        assert bundle['software'] == case.job['software']
        entry, = [entry for entry in case.owner.resource_tool_contracts() if entry['name'] == case.job['operation']]
        Draft202012Validator(entry['input_schema']).validate(case.request)
        assert entry['invocation_route']['routes'] == [{'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]
        assert entry['instructions'] and entry['description'] and entry['resources'] == 'local'
        target = case.owner.job_progress_provider.targets.describe_target(case.provider.handoff, case.scope, selector=case.selector)
        assert target['result_selector_schema'] and target['output_format'] == 'native_rna_structure_bundle_v1'
        assert target['acquisition_operations'] == ['execution.results.status', 'execution.results.collect']
        assert_accounting(case)
    finally:
        case.store.close()
