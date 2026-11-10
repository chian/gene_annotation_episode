"""Selected preparation tools through both actual immediate-parent boundaries.

The seven native commands, catalog materialization, shared Workflow, typed
returns and practical terminal estimator are production paths. Decisions and
scientific horizons are explicit engineering fixtures, with zero scientific
credit. No configured-model investigation or biological evidence is claimed.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
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
from gene_annotation_episode.infernal_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
from gene_annotation_episode.native_infernal_preparation_local import local_infernal_preparation_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_infernal_preparation_driver import POLICY, native_job
from test_native_infernal_preparation_results_integration import choice_for, result_form, selected


ROOT = Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
RUN_ID = 'infernal-preparation-nested257'
PREFIX = 'execution_infernal_preparation_'
MODES = [('cmbuild', 'build'), ('cmcalibrate', 'calibrate'), ('cmconvert', 'ascii'),
    ('cmemit', 'consensus'), ('cmfetch', 'single_key'), ('cmpress', 'press'), ('cmstat', 'summary')]


def forwarded_form(fields):
    descriptors = preparation_fact_sources()
    properties = {name: descriptors[PREFIX + ('result_refs' if name == 'references' else name)]['report_schema']
        for name in fields}
    return validate_closed_schema({'type': 'object', 'properties': properties,
        'required': list(properties), 'additionalProperties': False})


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Prepare the supplied RNA model inputs and inspect the requested native preparation measurements.',
        'scope': scope, 'purpose': 'Return only the requested preparation quantities, validation facts and artifacts.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}


def walk(record):
    yield record
    for unit in record['units']:
        if unit.get('child') is not None:
            yield from walk(unit['child'])


def history(record):
    return [unit['controller_step']['marginal_credit'] for unit in record['units']]


def provider_value(value, schema):
    """Express fixture choices in the actual provider's strict transport."""
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


def nested_case(tmp_path, program='cmemit', mode='consensus', *, selector=None,
        results_fields=('rows', 'artifacts', 'population', 'references'),
        parent_fields=('rows', 'population'), partial=False, before_collection=None):
    """A scripted selected itinerary, never a production route requirement."""
    store = Store(tmp_path / 'state')
    supplied = tmp_path / 'supplied-sequence.fa'
    supplied.write_text('>supplied_sequence_without_candidate_annotation\nGCGCAAAAGCGC\n')
    store.create_problem(supplied, molecule='dna', format='fasta')
    scope = store.validate_scope()
    job = native_job(program, mode)
    request = requested_job_from_infernal_preparation(job)
    selector = deepcopy(selector if selector is not None else choice_for(job))
    if program == 'cmpress':
        selector['projection']['checks'].extend(['model_calibration_present', 'index_content_decoded'])
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY.to_dict(),
        'native_infernal_preparation': [{key: job[key] for key in ('program', 'mode', 'software')}]}}
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'preparation-nested257',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'handoff', 'credit': 7,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(workspace), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': POLICY.to_dict()}}
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': assignment},
        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
            'allowed_kinds': ['local'], 'allocation': POLICY.to_dict()}}
    handoff_form = {'type': 'object', 'additionalProperties': False, 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
            'x-source': 'execution_handoff_refs'}}, 'required': ['completed', 'references']}
    results_form = result_form(**{name: name in results_fields
        for name in ('rows', 'artifacts', 'population', 'references')})
    if 'failures' in results_fields:
        results_form['properties']['failures'] = preparation_fact_sources()[PREFIX + 'failures']['report_schema']
        results_form['required'].append('failures')
        validate_closed_schema(results_form)
    science_form = forwarded_form(parent_fields)
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    tools = ToolRegistry(store)
    application = factory(store, run_id=RUN_ID, directory=tmp_path / 'run', tool_registry=tools)
    descriptor = prepare_scientific_binding(run_directory=tmp_path / 'run', source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=('scientific_process', 'launch', 'results'),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(tmp_path / 'run/scientific-process-library')
    science_assignment = {'selection': {'version': 'scientific_process_selection_v3',
        'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
        'child_tool_info': [{'name': 'native.' + program + '.' + mode, 'resources': 'local'}]},
        'evidence_refs': scope['subject_refs'], 'constraints': {'no_external_acquisition': True,
            'allocation': POLICY.to_dict()}, 'context': {'supplied_sequence': 'GCGCAAAAGCGC',
            'molecule': 'dna', 'candidate_annotation_required': False}}
    owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == 'annotation' else 2
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1),
                parameters, {'fixture': 'explicit_scientific_boundary_verification_horizon'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    class Choices:
        def __init__(self):
            self.calls, self.science_calls = [], 0
            self.handoff = self.plan = None

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
                self.science_calls += 1
                if self.science_calls == 1:
                    answer = child('launch', launch, scope, handoff_form)
                else:
                    assert self.science_calls == 2
                    self.handoff, = current['child_reports'][-1]['references']
                    target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                    # Engineering synchronization polls this original handle;
                    # it neither submits a second job nor adds episode credit.
                    result = await asyncio.to_thread(native.wait_job,
                        native.NativeJobHandle(Path(target['execution_id'])))
                    assert result.returncode == 0
                    self.plan = local_infernal_preparation_plan(assignment, target['execution_id'])
                    if before_collection is not None:
                        before_collection(self.plan)
                    answer = child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                        'selector': selector}, scope, results_form)
            answer = provider_value(plain(answer), plain(schema))
            errors = list(Draft202012Validator(plain(schema)).iter_errors(answer))
            if errors:
                (tmp_path / 'schema-failure.json').write_text(json.dumps({
                    'answer': answer, 'schema': plain(schema)}, indent=2) + '\n')
                leaves = []
                def explain(error):
                    if error.context:
                        for nested in error.context:
                            explain(nested)
                    else:
                        leaves.append({'path': list(error.absolute_path), 'message': error.message[:500]})
                for error in errors:
                    explain(error)
                raise AssertionError(leaves)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, tmp_path / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=('scientific_process',),
        episode_record_receipts=True, initial_known_record_refs=[],
        episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings,
        job_progress_provider=application.job_progress_provider)
    if partial:
        # This deliberate missing-row case has no practical completion proof.
        # A test-only base horizon lets the incomplete original form close.
        binding = flow.episode_bindings.for_role('results')
        original = binding.practical_estimator
        def partial_estimator(context):
            if context.role != 'results':
                return original(context)
            def base(raw, parameters):
                return YieldEstimate(len(raw), NumericBand.exact(0 if raw else 1), parameters,
                    {'fixture': 'explicit_missing_row_partial_return_horizon'})
            return PracticalYieldEstimator(lambda proof: binding.verify_completion(context, proof), base_estimate=base)
        binding.practical_estimator = partial_estimator
    root = flow.build('annotation', 'root', 'Inspect preparation of supplied RNA model inputs.', scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(execute())
    records = list(walk(json.loads(''.join(iter_json(record.as_record())))))
    contexts = {row['episode_id']: owner.native_infernal_preparation_returns.context(row['episode_id'])
        for row in records}
    by_role = {contexts[row['episode_id']].role: row for row in records}
    science_context = contexts[by_role['scientific_process']['episode_id']]
    results_context = contexts[by_role['results']['episode_id']]
    returned = json.loads(flow.journal.row('runtime_forms', results_context.episode_id)['form'])
    forwarded = json.loads(flow.journal.row('runtime_forms', science_context.episode_id)['form'])
    outcome = json.loads(flow.journal.row('runtime_actions', results_context.episode_id, 0)['result'])
    case = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root,
        record=record, records=records, by_role=by_role, contexts=contexts,
        root_context=contexts[record.episode_id], science_context=science_context,
        results_context=results_context, returned=returned, forwarded=forwarded, outcome=outcome,
        results_form=results_form, science_form=science_form, scientific_assignment=science_assignment,
        job=job, request=request, scope=scope, selector=selector, plan=provider.plan, workspace=workspace)
    (tmp_path / 'CASE.json').write_text(json.dumps({'program': program, 'mode': mode,
        'scope': 'scripted engineering decisions; actual native and Workflow boundaries; no model science',
        'partial_horizon_fixture': partial, 'native_plan': provider.plan, 'result': outcome,
        'results_form': results_form, 'science_form': science_form,
        'returned': returned, 'forwarded': forwarded,
        'histories': {role: row['controller_state'] for role, row in by_role.items()}}, indent=2) + '\n')
    for index, call in enumerate(provider.calls):
        (tmp_path / f'decision-{index}.json').write_text(json.dumps(call, indent=2) + '\n')
        if 'scientific_process' in call['context']:
            (tmp_path / f'presentation-{index}.txt').write_text(
                render_scientific_process_prompt(call['context'], call['instructions']))
    return case


@pytest.fixture(scope='module', params=MODES, ids=['-'.join(mode) for mode in MODES])
def native_case(tmp_path_factory, request):
    case = nested_case(tmp_path_factory.mktemp('-'.join(request.param)), *request.param)
    yield case
    case.store.close()


def assert_accounting(case, *, acquisition_gain=2):
    assert case.store.count('observation') == case.store.count('annotation') == 0
    assert len(case.provider.calls) == 6
    for row in case.records:
        episode = row['episode_id']
        actions = case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?', (episode,)).fetchone()[0]
        observations = case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (episode,)).fetchone()[0]
        assert actions == observations == row['units_consumed']
    assert history(case.by_role['annotation']) == [0]
    assert history(case.by_role['scientific_process']) == [0, 0]
    assert history(case.by_role['launch_local']) == [7]
    assert history(case.by_role['launch']) == [3]
    assert history(case.by_role['results']) == [acquisition_gain]
    assert len(list(case.workspace.rglob('infernal-preparation-plan.json'))) == 1


def values(row):
    return {quantity['path']: quantity['value'] for quantity in row['quantities']}


def test_selected_native_preparation_and_both_original_typed_forms(native_case):
    case = native_case
    body = case.outcome['result']
    assert case.outcome['status'] == 'completed' and body['complete'], body['failures']
    assert case.returned['completed'] and case.returned['rows']
    case.owner.validate_report(case.results_context, case.returned, case.results_form)
    case.owner.validate_received_report(case.science_context, case.forwarded, case.science_form)
    assert case.forwarded == {name: case.returned[name] for name in ('rows', 'population')}
    assert case.returned['population'] == [body['population']]
    assert all(row['source_ref'] == body['source_ref'] for rows in (
        case.returned['rows'], case.returned['artifacts'], case.returned['population']) for row in rows)
    received = {row['fact_source']: row['facts'] for row in
        case.owner.native_infernal_preparation_returns.received_context(case.root_context)}
    assert received == {PREFIX + name: case.forwarded[name] for name in ('rows', 'population')}
    capture, prepared = body['capture'], body['prepared']
    bundle = json.loads(case.store.get_artifact(capture['bundle_artifact_ref']))
    assert bundle['requested_job'] == case.request and bundle['identity'] == case.plan['identity']
    assert bundle['returncode'] == 0 and bundle['failures'] == []
    assert bundle['program'] == case.job['program'] and bundle['mode'] == case.job['mode']
    assert bundle['software']['actual_sha256'] == hashlib.sha256(
        Path(case.job['software']['executable']).read_bytes()).hexdigest()
    sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
    calculations = json.loads(case.store.get_artifact(prepared['calculations_artifact_ref']))
    assert sheet['schema'] == 'infernal_preparation_sheet_v1'
    assert calculations['schema'] == 'infernal_preparation_calculations_v1'
    assert prepared['sheet_artifact_ref'] != prepared['calculations_artifact_ref']
    assert sheet['operation'] == calculations['operation'] == bundle['operation']
    by_key = {row['record_key']: row for row in calculations['rows']}
    originals = {row['record_key']: row for collection in ('input_records', 'output_records', 'native_rows')
        for row in sheet[collection]}
    occurrences = {row['occurrence_ref']: row for row in prepared['occurrences']}
    for row in case.returned['rows']:
        assert [quantity['path'] for quantity in row['quantities']] == case.selector['projection']['quantities']
        for quantity in row['quantities']:
            field = quantity['path'].split('.')[1]
            if field in by_key[row['record_key']]['components']:
                original = by_key[row['record_key']]['components'][field]
                assert {key: quantity[key] for key in ('value', 'state', 'basis', 'unit')} == {
                    key: original[key] for key in ('value', 'state', 'basis', 'unit')}
        expected_checks = []
        for check in by_key[row['record_key']]['checks']:
            if check['check'] not in case.selector['projection']['checks']:
                continue
            refs = list(dict.fromkeys(item['locator']['artifact_ref'] for item in check['inputs']))
            expected_checks.append({'name': check['check'], 'outcome': check['outcome'],
                'occurrences': [{key: occurrences[reference][key] for key in
                    ('direction', 'role', 'ordinal', 'artifact_ref')} for reference in refs]})
        present = {check['name'] for check in expected_checks}
        expected_checks.extend({'name': name, 'outcome': 'unknown', 'occurrences': []}
            for name in case.selector['projection']['checks'] if name not in present)
        assert row['checks'] == expected_checks
        original = originals.get(row['record_key'])
        aggregate = 'input_model_count' in by_key[row['record_key']]['components']
        expected_artifact = None if original is None or aggregate else occurrences[
            original['locator']['artifact_ref']]['artifact_ref']
        assert row['artifact_ref'] == expected_artifact
    selected_artifacts = [(row['direction'], row['role'], row['ordinal']) for row in case.returned['artifacts']]
    assert selected_artifacts == [(row['direction'], row['role'], row['ordinal']) for row in case.selector['artifacts']]
    for row in case.returned['artifacts']:
        raw = case.store.get_artifact(row['artifact_ref'])
        assert len(raw) == row['size_bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
    assert_accounting(case)


def test_actual_catalog_instructions_callable_contract_and_all_three_slots(native_case):
    case = native_case
    name = 'native.' + case.job['program'] + '.' + case.job['mode']
    entry, = [row for row in case.owner.resource_tool_contracts() if row['name'] == name]
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    Draft202012Validator(entry['input_schema']).validate(case.request)
    calls = [call for call in case.provider.calls if 'scientific_process' in call['context']]
    assert len(calls) == 2
    for call in calls:
        current = call['context']
        information, = current['scientific_process']['child_tool_info']
        assert information == {key: entry[key] for key in ('name', 'description', 'resources', 'instructions')}
        selection = current['scientific_process']['selection']
        assert set(selection) == {'version', 'evidence_axis', 'thought_pattern', 'child_tool_info'}
        assert selection['evidence_axis']['option_id'] == 'A101'
        assert selection['thought_pattern']['option_id'] == 'P01'
        assert selection['child_tool_info'] == [{'name': name, 'resources': 'local'}]
        prompt = render_scientific_process_prompt(current, call['instructions'])
        task, steering = prompt.split('\n\nSTEERING', 1)
        assert task.startswith('TASK\n') and entry['instructions'] in task
        assert 'GCGCAAAAGCGC' in task and entry['instructions'] not in steering
        assert 'candidate_annotation_required' in task
        assert name not in {tool['name'] for tool in current['tools']}
        # A valid selected child request must fit the actual delivered response
        # schema, including the configured program/mode/software contract.
        launch_assignment = next(json.loads(row['action'])['assignment']
            for row in case.store.db.execute('SELECT action FROM runtime_actions WHERE episode_id=?',
                (case.science_context.episode_id,)) if json.loads(row['action']).get('role') == 'launch')
        launch_branch = next(branch for branch in call['schema']['properties']['selection']['anyOf']
            if branch.get('properties', {}).get('role', {}).get('enum') == ['launch'])
        transport = launch_branch['properties']['assignment']
        assert transport['type'] == 'string'
        delivered_contract = json.loads(transport['description'].split('schema: ', 1)[1])
        Draft202012Validator(delivered_contract).validate(launch_assignment)
        bad = deepcopy(launch_assignment)
        bad['requests']['here']['requested_job']['native_infernal_preparation']['mode'] = 'unbound_mode'
        assert not Draft202012Validator(delivered_contract).is_valid(bad)
    assert case.flow.catalog(case.scope, source=case.root.source) == []


def test_independent_numeric_examples_and_practical_exact_zero(native_case):
    case = native_case
    rows = [values(row) for row in case.returned['rows']]
    program = case.job['program']
    if program == 'cmemit':
        assert any(row['components.residue_count'] == 12 and row['components.gc_count'] == 8
            and row['components.gc_fraction_canonical'] == pytest.approx(8 / 12) for row in rows)
        sheet = json.loads(case.store.get_artifact(case.outcome['result']['prepared']['sheet_artifact_ref']))
        sequence, = [row for row in sheet['output_records'] if row['kind'] == 'generated_sequence']
        assert sequence['origin'] == 'generated_consensus' and sequence['model_keys']
    elif program in {'cmbuild', 'cmstat'}:
        assert any(row['components.paired_consensus_fraction'] == pytest.approx(8 / 12) for row in rows)
    elif program == 'cmcalibrate':
        assert any(row['components.actual_calibration_nt'] == 10000 for row in rows)
    else:
        assert any(row['components.input_model_count'] == 1 for row in rows)
        if program == 'cmpress':
            checks = [check for row in case.forwarded['rows'] for check in row['checks']]
            assert any(check['name'] == 'model_calibration_present' and check['outcome'] == 'fail' for check in checks)
            assert any(check['name'] == 'index_content_decoded' and check['outcome'] == 'unknown' for check in checks)
    for role in ('launch_local', 'launch', 'results'):
        row = case.by_role[role]
        assert row['units_consumed'] == 1
        assert row['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    proof = case.owner.completion_for_action(case.results_context, case.outcome['result']['operation_key'])
    assert proof and case.owner.verify_completion(case.results_context, proof)
    handle = native.NativeJobHandle(Path(case.plan['identity']['execution_id'])).read()
    assert case.plan['policy'] == handle['metadata']['policy'] == POLICY.to_dict()
    assert handle['metadata']['verified_cgroup']['memory_max'] == 20 * 1024**3
    assert handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert 'runtime_max' not in handle['metadata']['verified_cgroup']
    assert_accounting(case)


@pytest.mark.parametrize('fields', [('rows',), ('artifacts',), ('references',)])
def test_requested_only_subsets_at_each_boundary(tmp_path, fields):
    selector = choice_for(native_job('cmemit', 'consensus'))
    selector['projection']['rows'] = {'offset': 0, 'limit': 1}
    selector['projection']['quantities'] = ['components.gc_fraction_canonical']
    selector['projection']['checks'] = []
    selector['artifacts'] = [{'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0}]
    case = nested_case(tmp_path, selector=selector, results_fields=fields, parent_fields=fields)
    try:
        assert set(case.returned) == {'completed', *fields} and set(case.forwarded) == set(fields)
        assert case.forwarded == {field: case.returned[field] for field in fields}
        for context in (case.science_context, case.root_context):
            facts = case.owner.native_infernal_preparation_returns.received_facts(context,
                forwarded_form(('rows', 'artifacts', 'population', 'references')))
            for name in ('rows', 'artifacts', 'population'):
                assert facts[PREFIX + name] == (case.forwarded[name] if name in fields else [])
        if fields == ('rows',):
            assert [q['path'] for q in case.forwarded['rows'][0]['quantities']] == ['components.gc_fraction_canonical']
        # A source reference never grants auxiliary sheet/calculation files.
        prepared = case.outcome['result']['prepared']
        source = case.store.get(case.outcome['result']['source_ref'])
        probes = []
        for context in (case.science_context, case.root_context):
            resolve = case.flow.resolver(case.scope, context=context)
            for reference in source['auxiliary_artifact_refs']:
                probes.append({'recipient': context.role, 'reference': reference,
                    'source_ref': source['id'], 'relationship': 'auxiliary_artifact_refs',
                    'known_references': sorted(case.flow.receipts.known(context.episode_id)),
                    'workflow_resolver': resolve(reference, 'artifact'),
                    'owner_without_services_resolver': case.owner.resolve(context, reference, 'artifact'),
                    'received_preparation_resolver': case.owner.native_infernal_preparation_returns.resolve_received(
                        context, reference, 'artifact')})
        (tmp_path / 'resolver-probe.json').write_text(json.dumps(probes, indent=2) + '\n')
        reference_form = validate_closed_schema({'type': 'object', 'additionalProperties': False,
            'properties': {'artifact': {'type': 'string', 'format': 'reference',
                'x-reference-namespace': 'artifact'}}, 'required': ['artifact']})
        for context in (case.science_context, case.root_context):
            known = set(case.flow.receipts.known(context.episode_id))
            resolve = case.flow.resolver(case.scope, context=context)
            for key in ('sheet_artifact_ref', 'calculations_artifact_ref'):
                assert prepared[key] not in known
                assert not case.owner.native_infernal_preparation_returns.resolve_received(context, prepared[key], 'artifact')
                assert not resolve(prepared[key], 'artifact'), (context.role, key, prepared[key], sorted(known))
                assert not case.owner.resolve(context, prepared[key], 'artifact')
                with pytest.raises(ValueError):
                    validate_form({'artifact': prepared[key]}, reference_form, resolve)
            unrequested = next(row for row in case.outcome['result']['capture']['artifacts'] if row['role'] == 'stdout')
            assert unrequested['artifact_ref'] not in known, (context.role, unrequested, sorted(known))
            assert not resolve(unrequested['artifact_ref'], 'artifact'), (context.role, unrequested, sorted(known))
            assert not case.owner.resolve(context, unrequested['artifact_ref'], 'artifact')
            with pytest.raises(ValueError):
                validate_form({'artifact': unrequested['artifact_ref']}, reference_form, resolve)
        assert_accounting(case)
    finally:
        case.store.close()


def test_missing_key_diagnostic_survives_both_boundaries_without_invented_row(tmp_path):
    selector = choice_for(native_job('cmemit', 'consensus'))
    selector['projection']['rows'] = {'record_keys': ['requested_but_absent_preparation_row']}
    selector['artifacts'] = []
    case = nested_case(tmp_path, selector=selector, results_fields=('rows', 'population'),
        parent_fields=('population',), partial=True)
    try:
        assert not case.returned['completed'] and not case.outcome['result']['complete']
        assert case.returned['rows'] == []
        population, = case.forwarded['population']
        assert population['missing_record_keys'] == ['requested_but_absent_preparation_row']
        assert population['returned_records'] == 0 and population['source_ref'] == case.outcome['result']['source_ref']
        for context in (case.science_context, case.root_context):
            assert case.owner.native_infernal_preparation_returns.resolve_received(context,
                'requested_but_absent_preparation_row', 'native_infernal_preparation_row')
            assert case.owner.native_infernal_preparation_returns.received_facts(context,
                forwarded_form(('rows',)))[PREFIX + 'rows'] == []
        assert case.owner.completion_for_action(case.results_context, case.outcome['result']['operation_key']) is None
        assert_accounting(case)
    finally:
        case.store.close()


@pytest.mark.parametrize('fault', ['digest_mismatch', 'missing_bundle'])
def test_requested_capture_failure_facts_and_narrower_forwarding(tmp_path, fault, monkeypatch):
    def damage(plan):
        attempt = Path(plan['attempt_directory'])
        if fault == 'missing_bundle':
            (attempt / 'bundle.json').rename(attempt / 'retained-original-bundle.json')
        else:
            output = next(row for row in plan['requested_job']['native_infernal_preparation']['outputs']
                if row['role'] == 'generated_sequences')
            path = attempt / output['relative_path']
            path.rename(attempt / 'retained-original-generated-sequences.fa')
            path.write_text('>explicit_capture_corruption\nA\n')
    case = nested_case(tmp_path, results_fields=('rows', 'artifacts', 'population', 'failures'),
        parent_fields=('failures',), partial=True, before_collection=damage)
    try:
        assert not case.returned['completed'] and not case.outcome['result']['complete']
        assert case.forwarded == {'failures': case.returned['failures']}
        assert case.returned['failures']
        source = case.outcome['result']['source_ref']
        for failure in case.forwarded['failures']:
            assert failure['handoff_ref'] == case.provider.handoff
            assert failure['source_ref'] == source
            for context in (case.science_context, case.root_context):
                assert case.owner.native_infernal_preparation_returns.resolve_received(context,
                    failure['code'], 'native_infernal_preparation_failure_code')
        if fault == 'digest_mismatch':
            failed = [row for row in case.forwarded['failures'] if 'digest_mismatch' in row['code']]
            assert failed and all(row['affected'] == {
                'direction': 'output', 'role': 'generated_sequences', 'ordinal': 0} for row in failed)
            assert case.returned['artifacts']
        else:
            assert source is None
            assert case.returned['rows'] == case.returned['population'] == case.returned['artifacts'] == []
        root_facts = case.owner.native_infernal_preparation_returns.received_context(case.root_context)
        assert root_facts == [{'fact_source': PREFIX + 'failures', 'facts': case.forwarded['failures']}]
        forged = deepcopy(case.forwarded)
        forged['failures'][0]['code'] = 'native_infernal_preparation_forged_failure'
        with pytest.raises(ValueError):
            case.owner.validate_received_report(case.science_context, forged, case.science_form)
        assert case.owner.completion_for_action(case.results_context, case.outcome['result']['operation_key']) is None
        assert_accounting(case, acquisition_gain=0 if source is None else 2)
        assert_return_replay(case, monkeypatch, acquisition_gain=0 if source is None else 2)
    finally:
        case.store.close()


def test_forged_numbers_population_and_artifacts_rejected_across_boundaries(native_case):
    case = native_case
    for field in ('rows', 'population', 'artifacts'):
        changed = deepcopy(case.returned)
        if field == 'rows':
            quantity = next(q for row in changed['rows'] for q in row['quantities'] if q['value'] is not None)
            quantity['value'] += 1
        elif field == 'population':
            changed[field][0]['returned_records'] += 1
        else:
            changed[field][0]['source_ref'] = case.provider.handoff
        with pytest.raises(ValueError):
            case.owner.validate_report(case.results_context, changed, case.results_form)
        if field in case.forwarded:
            forwarded = deepcopy(case.forwarded)
            forwarded[field] = changed[field]
            with pytest.raises(ValueError):
                case.owner.validate_received_report(case.science_context, forwarded, case.science_form)
    expanded = deepcopy(case.forwarded)
    expanded['artifacts'] = case.returned['artifacts']
    with pytest.raises(ValueError):
        case.owner.validate_received_report(case.root_context, expanded,
            forwarded_form(('rows', 'population', 'artifacts')))
    assert_accounting(case)


def forbid_acquisition_and_parsing(monkeypatch, *, calculations):
    def forbidden(*args, **kwargs):
        raise AssertionError('retained-data verification performed forbidden acquisition, native work or parsing')
    monkeypatch.setattr(native, 'start_job', forbidden)
    monkeypatch.setattr(native, 'status', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    functions = {
        'native_infernal_preparation_worker': ['grade_infernal_preparation'],
        'infernal_preparation_artifacts': ['populate_infernal_artifact_sheet'],
        'infernal_preparation_statistics': ['populate_infernal_statistics_sheet'],
        'infernal_preparation_emission': ['populate_cmemit_sheet'],
        'infernal_preparation_models': ['extract_infernal_models'],
    }
    if calculations:
        functions['native_infernal_preparation_worker'].append('recalculate_infernal_preparation')
        functions['infernal_preparation_artifacts'].append('validate_infernal_artifact_sheet')
        functions['infernal_preparation_calculations'] = ['calculate_infernal_statistics']
        functions['infernal_preparation_emission_calculations'] = ['calculate_cmemit_components']
    for module, names in functions.items():
        for name in names:
            monkeypatch.setattr('gene_annotation_episode.' + module + '.' + name, forbidden)


def assert_return_replay(case, monkeypatch, *, acquisition_gain=2):
    before = [tuple(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    receipt_count = case.store.db.execute('SELECT count(*) FROM runtime_record_receipts').fetchone()[0]
    reader = case.owner.native_infernal_preparation_returns
    original = reader.received_context(case.root_context)
    with monkeypatch.context() as isolated:
        forbid_acquisition_and_parsing(isolated, calculations=True)
        assert reader.received_context(case.root_context) == original
        case.flow.receive_form(case.root.source, case.forwarded, case.science_form, 0, redelivery=True)
        assert reader.received_context(case.root_context) == original
    assert case.store.db.execute('SELECT count(*) FROM runtime_record_receipts').fetchone()[0] == receipt_count
    assert [tuple(row) for row in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == before
    assert_accounting(case, acquisition_gain=acquisition_gain)


def test_received_returns_replay_without_native_work_or_extra_observations(native_case, monkeypatch):
    assert_return_replay(native_case, monkeypatch)


def test_saved_sheet_recalculation_keeps_native_work_and_prior_facts_unchanged(native_case, monkeypatch):
    from gene_annotation_episode.native_infernal_preparation_worker import recalculate_infernal_preparation
    case = native_case
    prepared = case.outcome['result']['prepared']
    sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
    calculations = json.loads(case.store.get_artifact(prepared['calculations_artifact_ref']))
    saved = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved-sheet recalculation acquired, parsed or executed native data')
    with monkeypatch.context() as isolated:
        forbid_acquisition_and_parsing(isolated, calculations=False)
        isolated.setattr('builtins.open', forbidden)
        isolated.setattr(Path, 'open', forbidden)
        assert recalculate_infernal_preparation(sheet, parameters=calculations['parameters']) == calculations
    assert sheet == saved
    assert case.forwarded['rows'] == case.returned['rows']
    assert_accounting(case)
