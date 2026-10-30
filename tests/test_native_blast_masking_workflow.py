"""Four tiny native masking jobs through the actual nested episode boundaries.

Choices and scientific horizons are explicit engineering fixtures. The resource
execution, retained originals, result workers, typed returns, receipt grants and
practical terminal estimator are production paths. No biological annotation,
model decision, API/HPC deployment or database-scale operation is claimed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain, validate_closed_schema, validate_form
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_blast_masking_contracts import requested_job_from_native_blast_masking
from gene_annotation_episode.native_blast_masking_local import local_blast_masking_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.sequence_masking_result_views import masking_fact_sources
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_blast_masking_invocation import POLICY, job_for
from test_native_hmmer_preparation_nested_workflow import provider_value, walk, history

ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'masking-workflow619'
MODES = [('dustmasker', 'mask'), ('segmasker', 'mask'),
         ('windowmasker', 'mask'), ('windowmasker', 'create_counts')]


def form_for(fields, *, completed=False):
    descriptors = masking_fact_sources()
    properties = {field: deepcopy(descriptors['execution.masking_' + field]['report_schema']) for field in fields}
    if completed:
        properties['completed'] = {'type': 'boolean', 'x-source': 'execution_completed'}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Prepare the supplied sequences and return the requested masking measurements or reference statistics.',
        'scope': scope, 'purpose': 'Return only the requested native preparation facts and selected artifacts.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}


def selected(tool):
    return {'selection': {'kind': 'tool', 'tool': tool, 'arguments': {}}, 'report_update': {}}


def nested_case(tmp_path, program, mode, *, supplied_job=None, result_selector=None,
                subject_sequence='GCGCAAAAGCGC', subject_molecule='dna'):
    store = Store(tmp_path / 'state')
    store.create_problem(raw_sequence=subject_sequence, molecule=subject_molecule)
    scope = store.validate_scope()
    job = (job_for(tmp_path / 'supplied', program, mode, actual=True)
           if supplied_job is None else deepcopy(supplied_job))
    assert (job['operation']['program'], job['operation']['mode']) == (program, mode)
    if program == 'windowmasker':
        params = job['operation']['requested_parameters']
        if mode == 'create_counts':
            params.update(unit=3, mem=16, t_low=1, t_high=64, checkdup=False)
        else:
            params.update(window=7, t_low=1, t_high=64, t_extend=4, t_thres=8,
                set_t_low=1, set_t_high=64, dust=False)
    request = requested_job_from_native_blast_masking(job)
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    binding = {'program': program, 'mode': mode, 'software': job['software'],
        'output_formats': [job['operation']['output_format']], 'masking_styles': [job['operation']['masking_style']]}
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY,
        'native_blast_masking': [binding]}}
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'masking-workflow619',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'handoff', 'credit': 7, 'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': POLICY}}
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': assignment},
        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
            'allowed_kinds': ['local'], 'allocation': POLICY}}
    handoff_form = {'type': 'object', 'additionalProperties': False, 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
            'x-source': 'execution_handoff_refs'}}, 'required': ['completed', 'references']}
    selector = {'version': 'native_blast_masking_result_selector_v1', 'mode': 'native_result',
        'records': {'mode': 'all'}, 'quantities': [] if mode == 'create_counts' else
            ['input_length', 'masked_positions', 'masked_fraction'],
        'statistics_fields': ['unit_length', 'thresholds'] if program == 'windowmasker' else [],
        'statistics_unit_codes': [], 'include_checks': True,
        'artifacts': [{'direction': 'output', 'role': 'statistics' if mode == 'create_counts' else 'mask', 'ordinal': 0}],
        'saved_data': ['parsed_statistics'] if mode == 'create_counts' else ['sheet', 'calculations'],
        'saved_sheet_ref': None}
    if result_selector is not None:
        selector = deepcopy(result_selector)
    results_fields = ('status', 'quantities', 'statistics', 'artifacts', 'saved_data', 'checks', 'failures')
    results_form = form_for(results_fields, completed=True)
    science_form = form_for(('status', 'quantities', 'statistics'))
    tools = ToolRegistry(store)
    application = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)(
        store, run_id=RUN_ID, directory=tmp_path / 'run', tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=tmp_path / 'run', source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(tmp_path / 'run/scientific-process-library')
    science_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': 'native.' + program + '.' + mode, 'resources': 'local'}]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True, 'allocation': POLICY},
        'context': {'supplied_sequence': subject_sequence, 'molecule': subject_molecule, 'candidate_annotation_required': False}}
    owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' else 2
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {'fixture': 'explicit_scientific_boundary_horizon_not_production_stop_rule'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    class Choices:
        def __init__(self):
            self.calls, self.science_calls = [], 0
            self.handoff = self.target = self.plan = None

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({'episode_id': episode_id, 'role': role,
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
                self.science_calls += 1
                if self.science_calls == 1:
                    answer = child('launch', launch, scope, handoff_form)
                else:
                    assert self.science_calls == 2
                    self.handoff, = current['child_reports'][-1]['references']
                    self.target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                    # Fixture synchronization observes this exact selected handle.
                    # It adds no episode action and never submits a replacement.
                    result = await asyncio.to_thread(native.wait_job,
                        native.NativeJobHandle(Path(self.target['execution_id'])))
                    assert result.returncode == 0
                    self.plan = local_blast_masking_plan(assignment, self.target['execution_id'])
                    answer = child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                        'selector': selector}, scope, results_form)
            answer = provider_value(plain(answer), plain(schema))
            try:
                Draft202012Validator(plain(schema)).validate(answer)
            except Exception:
                (tmp_path / 'schema-failure.json').write_text(json.dumps({'answer': answer, 'schema': plain(schema)}, indent=2))
                raise
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, tmp_path / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=[],
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    root = flow.build('annotation', 'root', 'Prepare supplied sequence material and inspect selected masking measurements.', scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(execute())
    records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
    contexts = {r['episode_id']: owner.native_blast_masking_returns.context(r['episode_id']) for r in records}
    by_role = {contexts[r['episode_id']].role: r for r in records}
    science_context = contexts[by_role['scientific_process']['episode_id']]
    results_context = contexts[by_role['results']['episode_id']]
    returned = json.loads(flow.journal.row('runtime_forms', results_context.episode_id)['form'])
    forwarded = json.loads(flow.journal.row('runtime_forms', science_context.episode_id)['form'])
    outcome = json.loads(flow.journal.row('runtime_actions', results_context.episode_id, 0)['result'])
    case = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root, record=record,
        records=records, contexts=contexts, by_role=by_role, root_context=contexts[record.episode_id],
        science_context=science_context, results_context=results_context, returned=returned, forwarded=forwarded,
        outcome=outcome, results_form=results_form, science_form=science_form, job=job, request=request,
        scope=scope, selector=selector, workspace=workspace, plan=provider.plan, directory=tmp_path)
    (tmp_path / 'CASE.json').write_text(json.dumps({'program': program, 'mode': mode,
        'scope': 'actual bounded native + scripted shared Workflow; no biological annotation',
        'native_plan': provider.plan, 'result': outcome, 'returned': returned, 'forwarded': forwarded,
        'histories': {role: r['controller_state'] for role, r in by_role.items()}}, indent=2) + '\n')
    return case


@pytest.fixture(scope='module', params=MODES, ids=['-'.join(r) for r in MODES])
def native_case(tmp_path_factory, request):
    case = nested_case(tmp_path_factory.mktemp('-'.join(request.param)), *request.param)
    yield case
    case.store.close()


def assert_selected_numbers(job, body, returned, read_artifact):
    bundle = json.loads(read_artifact(body['capture']['bundle_artifact_ref']))
    prepared = body['prepared']
    if job['operation']['mode'] == 'mask':
        sheet = json.loads(read_artifact(prepared['sheet_artifact_ref']))
        calculated = json.loads(read_artifact(prepared['calculations_artifact_ref']))
        assert sheet['operation'] == bundle['operation']
        rows = {r['record_key']: r for r in calculated['records']}
        assert all(r['value'] == rows[r['record_key']][r['quantity']] for r in returned['quantities'])
        expected = {'dustmasker': [80, 0, 72], 'segmasker': [64, 0, 32], 'windowmasker': [80, 0, 0]}
        assert [r['value']['value'] for r in returned['quantities'] if r['quantity'] == 'masked_positions'] == expected[job['operation']['program']]
    else:
        assert prepared['sheet_artifact_ref'] is None and prepared['calculations_artifact_ref'] is None
        assert not returned['quantities'] and returned['statistics']
        stats = json.loads(read_artifact(prepared['statistics_artifact_ref']))
        assert returned['statistics'][0]['fields'] == {key: stats[key] for key in ('unit_length', 'thresholds')}
        assert returned['saved_data'][0]['schema'] == 'windowmasker_statistics_v1'


def test_actual_nested_masking_returns_share_retained_calculations(native_case):
    case, body = native_case, native_case.outcome['result']
    assert case.outcome['status'] == 'completed' and body['complete'], body['failures']
    assert case.returned['completed'] and case.returned['status'] == [body['status']]
    assert body['status']['state'] == 'complete' and body['status']['native_state'] == 'succeeded'
    assert case.forwarded == {k: case.returned[k] for k in ('status', 'quantities', 'statistics')}
    case.owner.validate_report(case.results_context, case.returned, case.results_form)
    case.owner.validate_received_report(case.root_context, case.forwarded, case.science_form)
    bundle = json.loads(case.store.get_artifact(body['capture']['bundle_artifact_ref']))
    assert bundle['requested_job'] == case.request and bundle['identity'] == case.plan['identity']
    assert bundle['operation'] == case.job['operation'] and bundle['returncode'] == 0
    assert bundle['software']['actual_sha256'] == hashlib.sha256(Path(case.job['software']['executable']).read_bytes()).hexdigest()
    assert_selected_numbers(case.job, body, case.returned, case.store.get_artifact)
    assert case.store.count('annotation') == case.store.count('observation') == 0


def test_selected_contracts_grants_and_practical_accounting(native_case):
    case, body = native_case, native_case.outcome['result']
    entry, = [r for r in case.owner.resource_tool_contracts() if r['name'] == 'native.' + case.job['operation']['program'] + '.' + case.job['operation']['mode']]
    Draft202012Validator(entry['input_schema']).validate(case.request)
    assert entry['invocation_route']['routes'] == [{'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]
    for call in case.provider.calls:
        if 'scientific_process' in call['context']:
            info, = call['context']['scientific_process']['child_tool_info']
            assert info == {key: entry[key] for key in ('name', 'description', 'resources', 'instructions')}
            assert set(call['context']['scientific_process']['selection']) == {'version', 'evidence_axis', 'thought_pattern', 'child_tool_info'}
    assert case.flow.catalog(case.scope, source=case.root.source) == []
    assert len(case.provider.calls) == 6
    assert history(case.by_role['annotation']) == [0] and history(case.by_role['scientific_process']) == [0, 0]
    assert history(case.by_role['launch_local']) == [7]
    assert history(case.by_role['launch']) == [3] and history(case.by_role['results']) == [2]
    for role, row in case.by_role.items():
        episode = row['episode_id']
        for table in ('runtime_actions', 'runtime_observations'):
            assert case.store.db.execute('SELECT count(*) FROM ' + table + ' WHERE episode_id=?', (episode,)).fetchone()[0] == row['units_consumed']
        if role in ('launch_local', 'launch', 'results'):
            assert row['units_consumed'] == 1
            assert row['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    proof = case.owner.completion_for_action(case.results_context, body['operation_key'])
    assert proof and case.owner.verify_completion(case.results_context, proof)
    handle = native.NativeJobHandle(Path(case.plan['identity']['execution_id'])).read()
    assert handle['metadata']['policy'] == POLICY
    assert handle['metadata']['verified_cgroup']['memory_max'] == 20 * 1024**3
    assert handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert handle['metadata']['verified_cgroup']['runtime_max'] == 'infinity'
    root_known = set(case.flow.receipts.known(case.root_context.episode_id))
    science_known = set(case.flow.receipts.known(case.science_context.episode_id))
    resolver = case.flow.resolver(case.scope, context=case.root_context)
    assert body['source_ref'] in root_known
    for row in (*body['saved_data'], *body['artifacts']):
        assert row['artifact_ref'] in science_known
        assert row['artifact_ref'] not in root_known and not resolver(row['artifact_ref'], 'artifact')
    hidden = body['prepared']['source_grading_artifact_ref']
    assert hidden not in root_known and hidden not in science_known
    assert not resolver(hidden, 'artifact')


def test_closed_native_result_and_received_forms_replay_without_work(native_case, monkeypatch):
    case, body = native_case, native_case.outcome['result']
    original = deepcopy(case.owner.native_blast_masking_returns.received_context(case.root_context))
    shutil.rmtree(case.workspace)
    shutil.rmtree(case.directory / 'supplied')
    def forbidden(*args, **kwargs):
        raise AssertionError('closed replay attempted new acquisition, execution, parsing or calculation')
    for module, name in (
        ('gene_annotation_episode.native_blast_masking_result_publication', 'run_local_job'),
        ('gene_annotation_episode.native_blast_masking_acquisition', '_capture_file'),
        ('gene_annotation_episode.native_blast_masking_acquisition', 'local_blast_masking_plan'),
        ('gene_annotation_episode.native_blast_masking_results', 'prepare_native_blast_masking_result'),
        ('gene_annotation_episode.native_blast_masking_results', 'publish_selected_masking_result'),
        ('gene_annotation_episode.sequence_masking_calculations', 'calculate_sequence_masking_components'),
        ('gene_annotation_episode.sequence_masking_inputs', 'parse_sequence_masking_output')):
        monkeypatch.setattr(module + '.' + name, forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
    before = list(case.store.db.iterdump())
    replay = asyncio.run(case.owner.execute(case.results_context, 'execution.results.collect', {}, body['operation_key']))
    assert replay == {k: v for k, v in case.outcome.items() if k != 'pending_work_after_action'}
    assert case.owner.native_blast_masking_returns.received_context(case.root_context) == original
    case.flow.receive_form(case.root.source, case.forwarded, case.science_form, 0, redelivery=True)
    assert case.owner.native_blast_masking_returns.received_context(case.root_context) == original
    assert list(case.store.db.iterdump()) == before
    assert case.store.count('annotation') == case.store.count('observation') == 0
