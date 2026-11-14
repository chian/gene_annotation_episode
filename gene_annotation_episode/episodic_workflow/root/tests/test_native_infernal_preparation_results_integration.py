"""Real preparation commands, deterministic grading and typed Workflow returns.

Scientific choices and their verification horizon are explicit test fixtures.
Practical operations, original native identities, retained data, numerical
grading, typed returns and practical terminal estimation use production code.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

from method_loop.archive import iter_json
from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.infernal_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.native_infernal_preparation_contracts import requested_job_from_infernal_preparation
from gene_annotation_episode.native_infernal_preparation_local import local_infernal_preparation_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_infernal_preparation_driver import CASES, POLICY, native_job


RUN_ID = 'infernal-preparation-workflow247'
PREFIX = 'execution_infernal_preparation_'


def selected(name):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': {}}, 'report_update': {}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Prepare the selected covariance-model inputs and return the requested measurements and artifacts.',
        'scope': scope, 'purpose': 'Return the selected native preparation facts without an annotation score.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}


def result_form(*, rows=True, artifacts=True, population=True, references=False, failures=False):
    descriptors = preparation_fact_sources()
    fields = {'completed': {'type': 'boolean', 'x-source': 'execution_completed'}}
    for name, include in [('rows', rows), ('artifacts', artifacts), ('population', population), ('failures', failures)]:
        if include:
            fields[name] = descriptors[PREFIX + name]['report_schema']
    if references:
        fields['references'] = {'type': 'array', 'uniqueItems': True,
            'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
            'x-source': 'execution_result_refs'}
    return validate_closed_schema({'type': 'object', 'properties': fields,
        'required': list(fields), 'additionalProperties': False})


def choice_for(job):
    program = job['program']
    if program == 'cmemit':
        quantities = ['components.residue_count', 'components.gc_count', 'components.gc_fraction_canonical']
        checks = ['cmemit_sequence_count_matches']
    elif program in {'cmbuild', 'cmcalibrate', 'cmstat'}:
        quantities = ['components.paired_consensus_fraction', 'components.actual_calibration_nt']
        checks = ['paired_topology_coherent']
    else:
        quantities = ['components.input_model_count', 'components.output_artifact_count', 'components.missing_key_count']
        checks = ['artifact_payload_identity']
    return {'version': 'native_infernal_preparation_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'collection': 'calculations', 'rows': {'offset': 0, 'limit': 50},
            'quantities': quantities, 'checks': checks},
        'artifacts': [{'direction': 'output', 'role': row['role'], 'ordinal': 0} for row in job['outputs']]}


def run_case(tmp_path, program='cmemit', mode='consensus', *, selectors=None, form_options=None,
             partial=False, status_first=False, before_collection=None):
    store = Store(tmp_path / 'state')
    supplied = tmp_path / 'supplied-sequence.fa'
    supplied.write_text('>internal_sample\nGCGCAAAAGCGC\n')
    store.create_problem(supplied, molecule='dna', format='fasta')
    scope = store.validate_scope()
    job = native_job(program, mode)
    request = requested_job_from_infernal_preparation(job)
    selectors = selectors or [choice_for(job)]
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY.to_dict(),
        'native_infernal_preparation': [{key: job[key] for key in ('program', 'mode', 'software')}]}}
    assignment = {'version': 'practical_assignment_v1', 'assignment_id': 'native-preparation',
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
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    tools = ToolRegistry(store)
    owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= 1 + len(selectors) else 1),
                parameters, {'fixture': 'selected_engineering_cases'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] == 'annotation' else None)

    class Choices:
        def __init__(self):
            self.root_calls, self.calls, self.result_calls = 0, [], {}
            self.handoff, self.target, self.plan = None, None, None
            self.forms = []

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append((episode_id, role, deepcopy(current)))
            assert not current.get('feedback'), current.get('feedback')
            if 'practical_assignment' in current:
                assert current['practical_assignment'] == assignment
                return selected('practical.job.start')
            execution = current.get('execution_assignment', {})
            if execution.get('version') == 'execution_launch_assignment_v1':
                return child('launch_local', assignment, scope, handoff_form)
            if execution.get('version') == RESULTS_VERSION:
                count = self.result_calls.get(episode_id, 0)
                assert count < 1 + int(status_first), current.get('last_local_outcome')
                self.result_calls[episode_id] = count + 1
                return selected('execution.results.status' if status_first and count == 0 else 'execution.results.collect')
            self.root_calls += 1
            if self.root_calls == 1:
                return child('launch', launch, scope, handoff_form)
            if self.handoff is None:
                self.handoff, = current['child_reports'][-1]['references']
                self.target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                native_result = await asyncio.to_thread(native.wait_job, native.NativeJobHandle(Path(self.target['execution_id'])))
                assert native_result.returncode == 0
                self.plan = local_infernal_preparation_plan(assignment, self.target['execution_id'])
                if before_collection is not None:
                    before_collection(store, self.plan)
            choice = selectors[self.root_calls - 2]
            if callable(choice):
                choice = choice(current['child_reports'][-1])
            form = result_form(**(form_options or {}))
            self.forms.append(form)
            return child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                'selector': choice}, scope, form)

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, tmp_path / 'run', RUN_ID, controller_factory=controller,
        project_credit=lambda *args, **kwargs: 0, annotation_child_roles=('launch', 'results'),
        episode_record_receipts=True, initial_known_record_refs=[], episode_service_factory=factory,
        episode_service_binding=factory.as_record(), episode_service_inputs='actual_tool_registry_v1')
    if partial:
        binding = flow.episode_bindings.for_role('results')
        previous = binding.practical_estimator
        def partial_estimator(context):
            if context.role != 'results':
                return previous(context)
            def base(raw, parameters):
                return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= 1 + int(status_first) else 1),
                    parameters, {'fixture': 'explicit_partial_result_horizon'})
            return PracticalYieldEstimator(lambda proof: binding.verify_completion(context, proof), base_estimate=base)
        binding.practical_estimator = partial_estimator
    root = flow.build('annotation', 'root', 'Prepare the selected model inputs for this gene investigation.', scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(execute())
    archive = json.loads(''.join(iter_json(record.as_record())))
    def walk(row):
        yield row
        for unit in row['units']:
            if unit.get('child'):
                yield from walk(unit['child'])
    records = list(walk(archive))
    contexts, returned, outcomes, result_records = [], [], [], []
    for row in records:
        saved = flow.journal.row('runtime_episodes', row['episode_id'])
        path, request_record = json.loads(saved['path']), json.loads(saved['request'])
        if path[-1][0] != 'results':
            continue
        message = request_record['message']
        contexts.append(BindingContext(RUN_ID, row['episode_id'], 'results', tuple(map(tuple, path)),
            message['scope'], message['episode_assignment'], request_record))
        returned.append(json.loads(flow.journal.row('runtime_forms', row['episode_id'])['form']))
        outcomes.append(json.loads(flow.journal.row('runtime_actions', row['episode_id'], row['units_consumed'] - 1)['result']))
        result_records.append(row)
    result = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root, record=record,
        records=records, result_records=result_records, contexts=contexts, returned=returned, outcomes=outcomes,
        scope=scope, request=request, workspace=workspace, plan=provider.plan, forms=provider.forms, job=job)
    (tmp_path / 'CASE.json').write_text(json.dumps({'program': program, 'mode': mode,
        'scripted_decisions': True, 'root_gains': list(record.controller_state.history), 'forms': returned,
        'result_histories': [r['controller_state'] for r in result_records],
        'native_plan': provider.plan, 'outcomes': outcomes}, indent=2) + '\n')
    return result


def assert_accounting(case):
    assert case.store.count('observation') == 0
    actions = case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
    observations = case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
    assert actions == observations == len(case.provider.calls)
    assert len(list(case.workspace.rglob('infernal-preparation-plan.json'))) == 1
    for context, form, schema in zip(case.contexts, case.returned, case.forms):
        case.owner.validate_report(context, form, schema)
    parent = case.owner.native_infernal_preparation_returns.context(case.record.episode_id)
    received = case.owner.native_infernal_preparation_returns.received_context(parent)
    assert all(row['fact_source'].startswith(PREFIX) for row in received)
    return parent, received


def test_consensus_through_launch_local_grade_typed_return_and_exact_terminal(tmp_path):
    case = run_case(tmp_path, status_first=True)
    try:
        parent, received = assert_accounting(case)
        form, body = case.returned[0], case.outcomes[0]['result']
        assert body['complete'] and form['completed'], body['failures']
        values = [{q['path']: q['value'] for q in row['quantities']} for row in form['rows']]
        assert any(row['components.residue_count'] == 12 and row['components.gc_count'] == 8
            and row['components.gc_fraction_canonical'] == pytest.approx(8 / 12) for row in values)
        assert form['population'][0]['source_ref'] == body['source_ref']
        assert all(row['source_ref'] == body['source_ref'] for row in form['artifacts'])
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key'])
        history = [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']]
        assert history == [0, 2]
        assert case.result_records[0]['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert case.record.controller_state.history == (0, 0)
        described = case.owner.job_progress_provider.targets.describe_target(case.provider.handoff,
            case.scope, selector=case.contexts[0].assignment['selector'])
        assert described['service_or_program'] == 'cmemit' and described['operation'] == 'consensus'
        assert described['acquisition_operations'] == ['execution.results.status', 'execution.results.collect']
        assert 'execution.results.read' not in {row['name'] for row in case.owner.catalog(case.contexts[0])}
        assert len(list(case.flow.receipts.known(case.record.episode_id, record_type='observation'))) == 0
        assert all(case.owner.resolve_received_reference(parent, row['artifact_ref'], 'artifact') for row in form['artifacts'])
    finally:
        case.store.close()


@pytest.mark.parametrize('program,mode', [('cmbuild', 'build'), ('cmcalibrate', 'calibrate'),
    ('cmconvert', 'ascii'), ('cmfetch', 'single_key'), ('cmpress', 'press'), ('cmstat', 'summary')])
def test_each_preparation_program_reaches_requested_parent_form(tmp_path, program, mode):
    case = run_case(tmp_path, program, mode)
    try:
        assert_accounting(case)
        body = case.outcomes[0]['result']
        assert body['complete'], body['failures']
        assert body['prepared']['graded'] and case.returned[0]['artifacts']
        assert body['population']['returned_artifact_count'] == len(case.job['outputs'])
        assert body['population']['missing_artifacts'] == []
        assert case.returned[0]['population'] == [body['population']]
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == [2]
        assert case.result_records[0]['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    finally:
        case.store.close()


def test_artifact_only_and_repeated_projection_do_not_manufacture_scientific_progress(tmp_path):
    job = native_job('cmemit', 'consensus')
    one = choice_for(job)
    one['projection'] = None
    case = run_case(tmp_path, selectors=[one, deepcopy(one)],
        form_options={'rows': False, 'references': True})
    try:
        parent, received = assert_accounting(case)
        assert case.outcomes[0]['result']['source_ref'] == case.outcomes[1]['result']['source_ref']
        assert case.returned[0] == case.returned[1]
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[1]['units']] == [0]
        assert all(row['fact_source'] != PREFIX + 'rows' for row in received)
        assert case.returned[0]['population'][0]['collection'] is None
        assert case.returned[0]['population'][0]['total_records'] == 0
        assert case.owner.native_infernal_preparation_returns.received_facts(parent, result_form())[
            PREFIX + 'rows'] == []
    finally:
        case.store.close()


@pytest.mark.parametrize('fault', ['missing_key', 'changed_output'])
def test_partial_acquisition_returns_diagnostic_information_without_false_completion(tmp_path, fault):
    selection = choice_for(native_job('cmemit', 'consensus'))
    if fault == 'missing_key':
        selection['projection']['rows'] = {'record_keys': ['explicitly_absent_record']}
    def change(store, plan):
        output = next(row for row in plan['requested_job']['native_infernal_preparation']['outputs']
            if row['role'] == 'stdout')
        path = Path(plan['attempt_directory']) / output['relative_path']
        path.write_bytes(b'changed after sealed producer bundle\n')
    case = run_case(tmp_path, selectors=[selection], partial=True, form_options={'failures': True},
        before_collection=change if fault == 'changed_output' else None)
    try:
        parent, received = assert_accounting(case)
        body = case.outcomes[0]['result']
        assert not body['complete'] and not case.returned[0]['completed']
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
        if fault == 'missing_key':
            assert case.returned[0]['rows'] == []
            assert case.returned[0]['population'][0]['missing_record_keys'] == ['explicitly_absent_record']
            assert case.owner.resolve_received_reference(parent, 'explicitly_absent_record', 'native_infernal_preparation_row')
        else:
            assert not body['capture']['complete']
            assert any('digest_mismatch' in f['code'] for f in body['failures'])
            assert case.returned[0]['artifacts']
            failures = case.returned[0]['failures']
            assert any(row['code'] == 'native_infernal_preparation_sealed_artifact_digest_mismatch'
                and row['affected'] == {'direction': 'output', 'role': 'stdout', 'ordinal': 0}
                and row['handoff_ref'] == case.provider.handoff for row in failures)
            assert case.owner.resolve_received_reference(parent, failures[0]['code'],
                'native_infernal_preparation_failure_code')
    finally:
        case.store.close()


def test_saved_result_replay_never_reopens_native_paths_or_recalculates(tmp_path, monkeypatch):
    case = run_case(tmp_path)
    attempt = Path(case.plan['attempt_directory'])
    relocated = attempt.with_name('temporarily-unavailable-original')
    try:
        assert_accounting(case)
        original = deepcopy(case.outcomes[0])
        body = original['result']
        attempt.rename(relocated)
        def forbidden(*args, **kwargs):
            raise AssertionError('replay performed new native, acquisition or grading work')
        original_socket = socket.socket
        def local_socket_only(*args, **kwargs):
            family = args[0] if args else kwargs.get('family', socket.AF_INET)
            if family != socket.AF_UNIX:
                forbidden(*args, **kwargs)
            return original_socket(*args, **kwargs)
        monkeypatch.setattr(native, 'start_job', forbidden)
        monkeypatch.setattr(native, 'status', forbidden)
        # asyncio's wakeup socket is local plumbing, not result acquisition.
        monkeypatch.setattr(socket, 'socket', local_socket_only)
        monkeypatch.setattr(subprocess, 'Popen', forbidden)
        monkeypatch.setattr('gene_annotation_episode.native_infernal_preparation_worker.grade_infernal_preparation', forbidden)
        replay = asyncio.run(case.owner.execute(case.contexts[0], 'execution.results.collect', {}, body['operation_key']))
        # Runtime adds its own pending-work snapshot after the operation returns.
        assert replay == {key: value for key, value in original.items() if key != 'pending_work_after_action'}
        saved = json.loads(case.flow.journal.row('runtime_actions', case.contexts[0].episode_id, 0)['result'])
        assert saved == original
        case.owner.validate_report(case.contexts[0], case.returned[0], case.forms[0])
        assert_accounting(case)
    finally:
        if relocated.exists():
            relocated.rename(attempt)
        case.store.close()


@pytest.mark.parametrize('fault', ['bundle_unavailable', 'grading_unavailable'])
def test_failed_acquisition_returns_requested_failure_without_inventing_numerical_population(tmp_path, monkeypatch, fault):
    def fail(store, plan):
        if fault == 'bundle_unavailable':
            path = Path(plan['attempt_directory']) / 'bundle.json'
            path.rename(path.with_suffix('.unavailable'))
        else:
            def unavailable(*args, **kwargs):
                raise ValueError('Synthetic unexpected grading error with diagnostic prose.')
            monkeypatch.setattr('gene_annotation_episode.native_infernal_preparation_results.'
                'prepare_native_infernal_preparation_grading', unavailable)
    case = run_case(tmp_path, partial=True, before_collection=fail, form_options={'failures': True})
    try:
        parent, received = assert_accounting(case)
        body, form = case.outcomes[0]['result'], case.returned[0]
        assert body['population'] is None and form['population'] == []
        assert form['rows'] == [] and not form['completed'] and form['failures']
        expected = ('native_infernal_preparation_sealed_bundle_unavailable' if fault == 'bundle_unavailable'
            else 'native_infernal_preparation_unclassified_error')
        failure, = form['failures']
        assert failure['code'] == expected and failure['handoff_ref'] == case.provider.handoff
        assert failure['source_ref'] == body['source_ref']
        assert case.owner.resolve_received_reference(parent, failure['code'], 'native_infernal_preparation_failure_code')
        assert case.owner.resolve_received_reference(parent, failure['handoff_ref'], 'execution_handoff')
        assert case.owner.resolve_received_reference(parent, failure['handoff_ref'], 'execution_result') is False
        received_refs = case.owner.native_infernal_preparation_returns.received_facts(parent, {
            'properties': {'references': {'x-source': PREFIX + 'result_refs'}}})[PREFIX + 'result_refs']
        assert failure['handoff_ref'] not in received_refs
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == (
            [0] if fault == 'bundle_unavailable' else [2])
        assert case.record.controller_state.history == (0, 0)
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
    finally:
        case.store.close()


@pytest.mark.parametrize('case', CASES, ids=[r['program'] + '-' + r['mode'] for r in CASES])
def test_configured_modes_are_callable_through_actual_launch_contract(tmp_path, case):
    job = native_job(case['program'], case['mode'])
    resources = {'here': {'kind': 'local', 'workspace': str(tmp_path), 'policy': POLICY.to_dict(),
        'native_infernal_preparation': [{key: job[key] for key in ('program', 'mode', 'software')}]}}
    store = Store(tmp_path / 'store')
    try:
        factory = ExecutionServiceFactory(resources, {}, 3, 2, 1)
        application = factory(store, run_id=RUN_ID, directory=tmp_path / 'run', tool_registry=ToolRegistry(store))
        entry, = [r for r in application.resource_tool_catalogs['local'] if r['name'].startswith('native.')]
        assert entry['name'] == 'native.' + job['program'] + '.' + job['mode']
        Draft202012Validator(entry['input_schema']).validate(requested_job_from_infernal_preparation(job))
        assert set(entry) >= {'name', 'description', 'resources', 'instructions', 'input_schema', 'invocation_route'}
        assert ExecutionServiceFactory.from_record(factory.as_record()).as_record() == factory.as_record()
    finally:
        store.close()
