"""Real Infernal work through Workflow, selected local children and typed forms.

Decisions and scientific continuation/projection are explicit engineering
fixtures. Native execution, resource limits, capture, bounded grading, Store,
practical endpoint estimation and both communication boundaries are production.
No model, external service, HPC, literature or annotation-credit claim is made.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.infernal_native_result_views import (
    COLLECTIONS, FAMILY_SOURCES, NATIVE_INFERNAL_METRICS, measurement_values,
    native_infernal_fact_sources,
)
from gene_annotation_episode.native_infernal_contracts import (
    compile_native_infernal_job, requested_job_from_infernal,
)
from gene_annotation_episode.native_infernal_local import local_infernal_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / 'tests/fixtures/native_infernal_result_worker'
BIN = ROOT / 'resources/software/infernal-1.1.5-install/bin'
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
RUN_ID = 'native-infernal-episode-226'


def selected(name, arguments=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}}, 'report_update': {}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Measure covariance-model correspondence for the supplied nucleotide sequences.',
        'scope': scope, 'purpose': 'Return exactly the requested native numerical measurements and associations.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'},
        'report_update': {}}


def selector(family, *, rows=None, metrics=None):
    return {'version': 'native_infernal_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'family': family, 'rows': rows or {'offset': 0, 'limit': 50},
            'metrics': list(metrics or NATIVE_INFERNAL_METRICS[family])}}


def results_form(family, *, include_rows=True, include_refs=False, include_origin=False):
    fields = {'completed': {'type': 'boolean', 'x-source': 'execution_completed'}}
    if include_rows:
        fields['rows'] = native_infernal_fact_sources()[FAMILY_SOURCES[family]]['report_schema']
    if include_refs:
        fields['references'] = {'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
            'x-source': 'execution_result_refs'}
    if include_origin:
        # Use the production descriptor when constructing this optional form.
        raise AssertionError('origin form must use the actual owner descriptor')
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def fasta_records(path):
    rows = []
    for line in Path(path).read_text().splitlines():
        if line.startswith('>'):
            rows.append([line[1:].split()[0], ''])
        elif line.strip():
            rows[-1][1] += ''.join(line.split()).upper()
    return rows


def bound_request(store, program, *, bind=True, wrong_sequence=False, native_failure=False, no_hits=False):
    """Use retained actual inputs, not an old attempt or a placeholder result."""
    label = 'cmalign_native_failure' if native_failure else program
    bundle = json.loads((INPUTS / label / 'bundle.json').read_text())
    job = deepcopy(bundle['requested_job']['native_infernal'])
    executable = BIN / program
    job['software']['executable'] = str(executable)
    job['software']['sha256'] = hashlib.sha256(executable.read_bytes()).hexdigest()
    for operand in job['operands']:
        retained = next(row for row in bundle['inputs'] if row['role'] == operand['role'])
        path = INPUTS / label / retained['relative_path']
        if no_hits and operand['role'] == 'sequences':
            path = store.path.parent / 'no-hit-input.fa'
            path.write_text('>explicit_no_hit_sequence\n' + 'A' * 72 + '\n')
        raw = path.read_bytes()
        operand.update(path=str(path), sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw), artifact_ref=None)
    # Model names remain native identities; no invented Store references are
    # carried over from the producer's isolated engineering workspace.
    job['operand_bindings'] = []
    sequences = next(row for row in job['operands'] if row['role'] == 'sequences')
    records = fasta_records(sequences['path'])
    subject_file = store.path.parent / 'supplied-biological-subjects.fa'
    original = []
    for ordinal, (name, sequence) in enumerate(records):
        if wrong_sequence and ordinal == 0:
            sequence = ('C' if sequence[0] != 'C' else 'A') + sequence[1:]
        original.append('>' + name + '\n' + sequence + '\n')
    subject_file.write_text(''.join(original))
    molecule = 'rna' if any('U' in sequence for _, sequence in records) else 'dna'
    subjects = store.create_problem(subject_file, molecule=molecule, format='fasta')['subject_refs']
    assert len(subjects) == len(records)
    if bind:
        job['operand_bindings'] = [{'operand_role': 'sequences', 'record_ordinal': ordinal,
            'native_name': name, 'native_accession': None, 'subject_ref': subject, 'reference_ref': None}
            for ordinal, ((name, _), subject) in enumerate(zip(records, subjects))]
    return requested_job_from_infernal(job), store.validate_scope()


def practical_assignment(workspace, request):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'native-infernal-results',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'handoff', 'credit': 7,
            'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace),
            'environment': {}}, 'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def history(record):
    return [unit['controller_step']['marginal_credit'] for unit in record['units']]


def walk_records(record):
    yield record
    for unit in record['units']:
        if unit.get('child') is not None:
            yield from walk_records(unit['child'])


@contextmanager
def unavailable_native_attempt(plan):
    """Temporarily remove original file locations, preserving every native byte."""
    original = Path(plan['attempt_directory'])
    retained = original.with_name('retained-original-attempt-unavailable')
    original.rename(retained)
    try:
        yield
    finally:
        retained.rename(original)


def run_case(tmp_path, program, *, selectors=None, bind=True, wrong_sequence=False,
        native_failure=False, no_hits=False, include_rows=True, include_refs=False,
        include_origin=False, status_first=False, before_collection=None, incomplete=False, nested=False,
        root_read_after_return=False):
    store = Store(tmp_path / 'state')
    request, scope = bound_request(store, program, bind=bind, wrong_sequence=wrong_sequence,
        native_failure=native_failure, no_hits=no_hits)
    selectors = selectors or [selector('alignment_sequence' if program == 'cmalign' else 'search_hit')]
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_infernal': [{key: request['native_infernal'][key] for key in ('program', 'software')}]}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    assignment = practical_assignment(workspace, request)
    launch = {'version': 'execution_launch_assignment_v1', 'requests': {'here': assignment},
        'immutable_input_versions': [], 'constraints': {'allowed_resource_ids': ['here'],
            'allowed_kinds': ['local'], 'allocation': deepcopy(POLICY)}}
    handoff_form = {'type': 'object', 'properties': {
        'completed': {'type': 'boolean', 'x-source': 'execution_completed'},
        'references': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string',
            'format': 'reference', 'x-reference-namespace': 'execution_handoff'},
            'x-source': 'execution_handoff_refs'}}, 'required': ['completed', 'references'],
        'additionalProperties': False}
    tools = ToolRegistry(store)
    owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=RUN_ID,
        resources=resources, initial_information={}, tool_registry=tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
    descriptors, scientific_assignment, scientific_form = [], None, None
    service_arguments = {'episode_service_factory': factory, 'episode_service_binding': factory.as_record(),
        'episode_service_inputs': 'actual_tool_registry_v1'}
    if nested:
        application = factory(store, run_id=RUN_ID, directory=tmp_path / 'run', tool_registry=tools)
        descriptor = prepare_scientific_binding(run_directory=tmp_path / 'run',
            source_directory=PUBLICATION, tool_catalog=tools.catalog(),
            child_roles=('scientific_process', 'launch', 'results'),
            resource_catalogs=application.resource_tool_catalogs)
        descriptors.append(descriptor)
        service_arguments = {'episode_binding_descriptors': (descriptor, *application.episode_binding_descriptors),
            'role_credit_bindings': application.role_credit_bindings,
            'job_progress_provider': application.job_progress_provider}
        library = ScientificProcessLibrary(tmp_path / 'run/scientific-process-library')
        scientific_assignment = {'selection': {'version': 'scientific_process_selection_v3',
            'evidence_axis': library.reference('A101'), 'thought_pattern': library.reference('P01'),
            'child_tool_info': [{'name': 'native.' + program, 'resources': 'local'}]},
            'evidence_refs': scope['subject_refs'],
            'constraints': {'no_external_acquisition': True, 'allocation': deepcopy(POLICY)},
            'context': {'supplied_sequence_records': [name for name, _ in fasta_records(
                next(row['path'] for row in request['native_infernal']['operands'] if row['role'] == 'sequences'))],
                'molecule': 'rna', 'candidate_function_required': False}}
        families = list(dict.fromkeys(s['projection']['family'] for s in selectors if not callable(s)))
        fields = ({family: native_infernal_fact_sources()[FAMILY_SOURCES[family]]['report_schema'] for family in families}
            if include_rows else {'references': owner.received_report_sources('scientific_process')[
                'execution_infernal_result_refs']['report_schema']})
        if root_read_after_return:
            fields['handoff_and_result_references'] = {'type': 'array', 'uniqueItems': True,
                'items': {'type': 'string', 'format': 'reference'}, 'x-source': 'committed_record_refs'}
        scientific_form = {'type': 'object', 'properties': fields, 'required': list(fields),
            'additionalProperties': False}

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            count = ((2 if root_read_after_return else 1) if nested and path[-1][0] == 'annotation'
                else 1 + len(selectors))
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= count else 1), parameters,
                {'fixture': 'explicit_scientific_verification_horizon'})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {'annotation', 'scientific_process'} else None)

    def received_observations(actual_store, actual_scope, **kwargs):
        # Engineering count of facts actually delivered to the root, never an
        # annotation confidence or W05 formula. Scientific decisions are scripted.
        rows = actual_store.db.execute('SELECT episode_id,path FROM runtime_episodes WHERE run_id=?', (RUN_ID,))
        roots = [r['episode_id'] for r in rows if json.loads(r['path']) == [['annotation', 'root']]]
        return 0 if not roots else len(list(EpisodeReceipts(actual_store, RUN_ID).known(
            roots[0], record_type='observation')))

    received_observations.requires_episode_receipts = True

    class Choices:
        def __init__(self):
            self.calls, self.result_calls = [], {}
            self.science_calls, self.handoff, self.target, self.plan = 0, None, None, None
            self.root_calls = 0
            self.actual_forms = []

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append((episode_id, role, deepcopy(current), instructions))
            assert not current.get('feedback'), current.get('feedback')
            if 'practical_assignment' in current:
                assert current['practical_assignment'] == assignment
                return selected('practical.job.start')
            execution = current.get('execution_assignment', {})
            if execution.get('version') == 'execution_launch_assignment_v1':
                return child('launch_local', assignment, scope, handoff_form)
            if execution.get('version') == RESULTS_VERSION:
                count = self.result_calls.get(episode_id, 0)
                assert count < 1 + int(status_first), current.get('last_local_outcome', current)
                self.result_calls[episode_id] = count + 1
                return selected('execution.results.status' if status_first and count == 0 else 'execution.results.collect')
            if nested and 'scientific_process' not in current:
                self.root_calls += 1
                if self.root_calls == 1:
                    return child('scientific_process', scientific_assignment, scope, scientific_form)
                assert root_read_after_return and self.root_calls == 2
                assert self.handoff in current['child_reports'][-1]['handoff_and_result_references']
                form = results_form(selectors[0]['projection']['family'], include_rows=include_rows,
                    include_refs=include_refs)
                self.actual_forms.append(form)
                return child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                    'selector': selectors[0]}, scope, form)
            self.science_calls += 1
            if self.science_calls == 1:
                return child('launch', launch, scope, handoff_form)
            if self.handoff is None:
                self.handoff, = current['child_reports'][-1]['references']
                self.target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                result = await asyncio.to_thread(native.wait_job, native.NativeJobHandle(Path(self.target['execution_id'])))
                assert result.returncode != 0 if native_failure else result.returncode == 0
                self.plan = local_infernal_plan(assignment, self.target['execution_id'])
                if before_collection is not None:
                    before_collection(store, self.plan)
            choice = selectors[self.science_calls - 2]
            if callable(choice):
                choice = choice(current['child_reports'][-1])
            form = results_form(choice['projection']['family'], include_rows=include_rows, include_refs=include_refs)
            if include_origin:
                form['properties']['origin'] = owner.fact_sources('results')['execution_result_origin']['report_schema']
                form['required'].append('origin')
            self.actual_forms.append(form)
            return child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                'selector': choice}, scope, form)

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, tmp_path / 'run', RUN_ID,
        controller_factory=controller, project_credit=received_observations,
        annotation_child_roles=(('scientific_process', 'results') if root_read_after_return else
            ('scientific_process',)) if nested else ('launch', 'results'),
        episode_record_receipts=True, initial_known_record_refs=[], **service_arguments)
    if incomplete:
        # A fault fixture explicitly yields partial data after its chosen reads.
        # Production completion proof validation remains installed and false.
        binding = flow.episode_bindings.for_role('results')
        original_estimator = binding.practical_estimator
        def partial_estimator(context):
            if context.role != 'results':
                return original_estimator(context)
            def base(raw, parameters):
                return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= 1 + int(status_first) else 1),
                    parameters, {'fixture': 'explicit_partial_result_verification_horizon'})
            return PracticalYieldEstimator(lambda proof: binding.verify_completion(context, proof), base_estimate=base)
        binding.practical_estimator = partial_estimator
    root = flow.build('annotation', 'root', 'Measure covariance-model correspondence in the supplied sequences.', scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    record = asyncio.run(execute())
    archive = json.loads(''.join(iter_json(record.as_record())))
    records = list(walk_records(archive))
    contexts, returned, outcomes, child_records = [], [], [], []
    for row_record in records:
        row = flow.journal.row('runtime_episodes', row_record['episode_id'])
        path, saved_request = json.loads(row['path']), json.loads(row['request'])
        if path[-1][0] != 'results':
            continue
        contexts.append(BindingContext(RUN_ID, row['episode_id'], 'results', tuple(map(tuple, path)),
            saved_request['message']['scope'], saved_request['message']['episode_assignment'], saved_request))
        returned.append(json.loads(flow.journal.row('runtime_forms', row['episode_id'])['form']))
        outcomes.append(json.loads(flow.journal.row('runtime_actions', row['episode_id'],
            row_record['units_consumed'] - 1)['result']))
        child_records.append(row_record)
    cases = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, record=record,
        archive=archive, records=records, child_records=child_records, contexts=contexts,
        returned=returned, outcomes=outcomes, scope=scope, plan=provider.plan, forms=provider.actual_forms,
        request=request, workspace=workspace, tmp_path=tmp_path, scientific_form=scientific_form,
        root=root, nested=nested)
    summary = {'program': program, 'native_execution': 'fresh practical.job.start through Workflow',
        'decisions': 'scripted; scientific horizon and root received-observation count are fixtures',
        'operational_units': {'practical_handoff': 7, 'launch_handoff': 3, 'acquired_record': 2},
        'partial_result_fixture_estimator': incomplete, 'nested_scientific_return': nested,
        'parent_units': record.units_consumed, 'parent_gains': list(record.controller_state.history),
        'selected_actions': store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0],
        'controller_observations': store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0],
        'scripted_decision_calls': len(provider.calls), 'native_plan': provider.plan,
        'returned_forms': returned, 'results': [{'gains': history(cr), 'units': cr['units_consumed'],
            'future_expectation': cr['controller_state']['estimate']['expected_next_gain'],
            'original_action': out['result']['operation_key'], 'capture': out['result']['capture'],
            'prepared': out['result']['prepared'], 'failures': out['result']['failures'],
            'complete': out['result']['complete']} for cr, out in zip(child_records, outcomes)]}
    (tmp_path / 'CASE.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    for index, (episode_id, role, current, instructions) in enumerate(provider.calls):
        scientific = 'scientific_process' in current
        if not scientific and episode_id != root.source.episode_id:
            continue
        label = 'scientific' if scientific else 'root'
        (tmp_path / f'{label}-decision-{index}.json').write_text(json.dumps({
            'episode_id': episode_id, 'role': role, 'context': current, 'instructions': instructions},
            indent=2, sort_keys=True) + '\n')
        connection = object.__new__(_SessionConnection)
        connection.scientific_prompt_states = {}
        rendered, _ = connection._presentation(episode_id, role, instructions, current)
        (tmp_path / f'{label}-presentation-{index}.txt').write_text(rendered)
    return cases


@pytest.fixture(scope='module', params=['cmsearch', 'cmscan', 'cmalign'])
def native_case(tmp_path_factory, request):
    program = request.param
    families = {'cmsearch': ['search_hit', 'search_sequence'], 'cmscan': ['search_hit'],
        'cmalign': ['alignment_sequence', 'alignment_column', 'alignment_pair']}[program]
    choices = [selector(family, rows={'offset': 0, 'limit': 2} if family in {
        'alignment_column', 'alignment_pair'} else None) for family in families]
    case = run_case(tmp_path_factory.mktemp(program), program, selectors=choices,
        nested=True, status_first=program == 'cmsearch')
    yield case
    case.store.close()


def values(row):
    return {m['name']: m['value'] for m in row['measurements']}


def presented_root_after_return(case):
    decision = next(call for call in case.provider.calls
        if call[0] == case.record.episode_id and call[2].get('child_reports'))
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    text, _ = connection._presentation(decision[0], decision[1], decision[3], decision[2])
    presented = json.loads(text)
    assert presented['child_reports'] == decision[2]['child_reports']
    return presented


def assert_counts(case):
    actions = case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
    observations = case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
    assert actions == observations == len(case.provider.calls)
    for record in case.records:
        episode = record['episode_id']
        own = case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?', (episode,)).fetchone()[0]
        observed = case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?', (episode,)).fetchone()[0]
        assert own == observed == record['units_consumed']


def test_real_selected_program_retained_results_and_two_form_boundaries(native_case):
    case = native_case
    job = case.request['native_infernal']
    assert len(list(case.workspace.rglob('infernal-plan.json'))) == 1
    assert case.plan['policy'] == POLICY
    handle = native.NativeJobHandle(Path(case.plan['identity']['execution_id'])).read()
    assert handle['metadata']['policy'] == POLICY
    assert handle['metadata']['verified_cgroup']['memory_max'] == POLICY['memory_bytes']
    assert handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert 'runtime_max' not in handle['metadata']['verified_cgroup']
    root_context = case.owner.native_infernal_returns.context(case.record.episode_id)
    science_record = next(r for r in case.records if case.owner.native_infernal_returns.context(r['episode_id']).role == 'scientific_process')
    science_context = case.owner.native_infernal_returns.context(science_record['episode_id'])
    forwarded = json.loads(case.flow.journal.row('runtime_forms', science_context.episode_id)['form'])
    assert science_record['units_consumed'] == 1 + len(case.outcomes)
    assert case.record.units_consumed == 1
    assert len({outcome['result']['source_ref'] for outcome in case.outcomes}) == 1
    for context, result, outcome, form in zip(case.contexts, case.returned, case.outcomes, case.forms):
        body = outcome['result']
        assert outcome['status'] == 'completed' and body['complete'], body['failures']
        assert result['completed'] and result['rows']
        case.owner.validate_report(context, result, form)
        capture, prepared = body['capture'], body['prepared']
        bundle = json.loads(case.store.get_artifact(capture['bundle_artifact_ref']))
        assert bundle['requested_job'] == case.request and bundle['identity'] == case.plan['identity']
        assert bundle['software']['actual_sha256'] == bundle['software']['expected_sha256'] == hashlib.sha256(
            Path(job['software']['executable']).read_bytes()).hexdigest()
        assert bundle['realized_argv'] == compile_native_infernal_job(job,
            input_paths={r['role']: str(Path(case.plan['attempt_directory']) / r['relative_path']) for r in bundle['inputs']},
            output_directory=case.plan['attempt_directory'])['argv']
        assert len(capture['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        source = case.store.get(body['source_ref'])
        assert {r['artifact_ref'] for r in capture['artifacts']} <= set(source['auxiliary_artifact_refs'])
        sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
        scores = json.loads(case.store.get_artifact(prepared['scores_artifact_ref']))
        family = context.assignment['selector']['projection']['family']
        collection = scores[COLLECTIONS[family]]
        key = {'search_hit': 'hit_id', 'search_sequence': 'aggregate_id'}.get(family, 'record_key')
        by_key = {r[key]: r for r in collection}
        assert len(collection) >= len(result['rows'])
        assert sheet['publication_inputs']['operand_bindings'] == job['operand_bindings']
        for row in result['rows']:
            assert set(values(row)) | {v['name'] for v in row['unavailable']} == set(NATIVE_INFERNAL_METRICS[family])
            assert values(row) == {name: measurement_values(by_key[row['record_key']], family=family)[name]
                for name in values(row)}
            if row['observation_ref']:
                observation = case.store.get(row['observation_ref'])
                assert observation['subject_refs'] == [row['subject_ref']]
                assert observation['native_infernal']['record_key'] == row['record_key']
                assert observation['operand_intervals'] and all(r['model_unit'] == 'nt' for r in observation['operand_intervals'])
        assert forwarded[family] == result['rows']
    groups = {g['fact_source']: g['facts'] for g in case.owner.native_infernal_returns.received_context(root_context)}
    assert groups == {FAMILY_SOURCES[f]: rows for f, rows in forwarded.items()}
    case.owner.validate_received_report(science_context, forwarded, case.scientific_form)
    delivered = {r['observation_ref'] for rows in forwarded.values() for r in rows if r['observation_ref']}
    assert delivered <= set(case.flow.receipts.known(case.record.episode_id, record_type='observation'))
    assert case.store.count('annotation') == 0
    assert_counts(case)


def test_native_numbers_zero_unknown_and_population_meanings(native_case):
    for context, returned in zip(native_case.contexts, native_case.returned):
        family = context.assignment['selector']['projection']['family']
        rows, first = returned['rows'], returned['rows'][0]
        measured = values(first)
        if family == 'search_hit':
            assert measured == {'bitscore': 71.4, 'evalue': 3.6e-22 if native_case.request['native_infernal']['program'] == 'cmsearch' else 1e-22,
                'bias_bits': 0.0, 'gc_fraction': .5, 'model_span_length': 72, 'model_span_fraction': 1,
                'sequence_span_length': 72, 'sequence_span_fraction': 1, 'consensus_length': 72, 'sequence_length': 72}
            assert first['sequence_name'] == 'mrum-tRNA.1' and first['model_name'] == 'tRNA5'
            assert first['status'] == 'published' and 'aligned_residue_coverage' not in measured
        elif family == 'search_sequence':
            assert measured == {'hit_count': 1, 'union_numerator': 72, 'union_denominator': 72,
                'union_span_fraction': 1, 'unselected_hit_count': 0, 'unknown_selection_count': 0, 'invalid_geometry_count': 0}
        elif family == 'alignment_sequence':
            assert measured['native_bit_score'] == 60.03 and measured['native_avg_pp'] == 1
            assert measured['model_match_nucleotides'] == 72 and measured['posterior_lower_mean'] == .95
            assert measured['posterior_upper_mean'] == 1
            assert measured['retained_insert_nucleotides'] == 0
            assert 'deleted_model_positions' not in measured
            assert {'name': 'deleted_model_positions', 'reason': 'not_measured'} in first['unavailable']
            assert values(rows[8])['retained_local_end_nucleotides'] == 40
        elif family == 'alignment_column':
            assert measured['row_count'] == measured['occupancy_denominator'] == 10
            assert measured['occupancy'] == 1
            assert first['status'] == 'unbound' and first['subject_ref'] is None and first['observation_ref'] is None
        elif family == 'alignment_pair':
            assert measured['canonical_pairs'] == measured['unambiguous_pair_denominator'] == 10
            assert measured['canonical_pair_fraction'] == 1 and len(first['pair_columns']) == 2
            assert first['status'] == 'unbound' and first['subject_ref'] is None and first['observation_ref'] is None


def test_completed_action_accounting_and_exact_zero_without_extra_turn(native_case):
    case = native_case
    for context, record, outcome in zip(case.contexts, case.child_records, case.outcomes):
        expected_count = 2 if case.request['native_infernal']['program'] == 'cmsearch' else 1
        assert record['units_consumed'] == expected_count
        gains = history(record)
        assert gains[-1] >= 0
        if expected_count == 2:
            assert gains[0] == 0
            status = json.loads(case.flow.journal.row('runtime_actions', context.episode_id, 0)['result'])['result']
            assert status['capture'] is status['prepared'] is None and status['rows'] == []
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        proof = case.owner.completion_for_action(context, outcome['result']['operation_key'])
        assert proof and case.owner.verify_completion(context, proof)
    assert history(case.child_records[0])[-1] > 0
    practical = next(r for r in case.records if case.owner.native_infernal_returns.context(r['episode_id']).role == 'launch_local')
    launch = next(r for r in case.records if case.owner.native_infernal_returns.context(r['episode_id']).role == 'launch')
    assert history(practical) == [7] and history(launch) == [3]
    for record in (practical, launch):
        assert record['units_consumed'] == 1
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    assert_counts(case)


def test_saved_calculator_replay_without_native_execution_or_acquisition(native_case, monkeypatch):
    case = native_case
    from gene_annotation_episode.cmalign_grader import calculate_cmalign_scores
    from gene_annotation_episode.infernal_search_grader import calculate_infernal_search_scores
    calculator = calculate_cmalign_scores if case.request['native_infernal']['program'] == 'cmalign' else calculate_infernal_search_scores
    body = case.outcomes[0]['result']
    sheet = json.loads(case.store.get_artifact(body['prepared']['sheet_artifact_ref']))
    scores = json.loads(case.store.get_artifact(body['prepared']['scores_artifact_ref']))
    saved = deepcopy(sheet)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved calculator attempted acquisition/native execution')
    with monkeypatch.context() as isolated:
        isolated.setattr(socket, 'socket', forbidden)
        isolated.setattr(subprocess, 'Popen', forbidden)
        isolated.setattr('builtins.open', forbidden)
        assert calculator(sheet, parameters=case.request['native_infernal']['grading_parameters']) == scores
    assert sheet == saved


def test_original_result_and_return_replay_have_no_new_contribution(native_case, monkeypatch):
    case = native_case
    before = [tuple(r) for r in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')]
    receipt_count = case.store.db.execute('SELECT count(*) FROM runtime_record_receipts').fetchone()[0]
    root_context = case.owner.native_infernal_returns.context(case.record.episode_id)
    expected = case.owner.native_infernal_returns.received_context(root_context)
    def forbidden(*args, **kwargs):
        raise AssertionError('saved result replay attempted new work')
    with unavailable_native_attempt(case.plan), monkeypatch.context() as isolated:
        isolated.setattr('gene_annotation_episode.native_infernal_results.capture_local_bundle', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_results.prepare_native_infernal_grading', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_results.publish_selected_native_infernal_rows', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.run', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.populate_cmalign_sheet', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.populate_infernal_search_sheet', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.calculate_cmalign_scores', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.calculate_infernal_search_scores', forbidden)
        isolated.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
        isolated.setattr(subprocess, 'Popen', forbidden)
        for context, original in zip(case.contexts, case.outcomes):
            body = original['result']
            replay = asyncio.run(case.owner.execute(context, 'execution.results.collect', {}, body['operation_key']))
            assert replay == {k: v for k, v in original.items() if k != 'pending_work_after_action'}
        assert case.owner.native_infernal_returns.received_context(root_context) == expected
        assert case.owner.native_infernal_returns.received_context(root_context) == expected
        science = next(r for r in case.records if case.owner.native_infernal_returns.context(r['episode_id']).role == 'scientific_process')
        form = json.loads(case.flow.journal.row('runtime_forms', science['episode_id'])['form'])
        case.flow.receive_form(case.root.source, form, case.scientific_form, 0, redelivery=True)
    assert case.store.db.execute('SELECT count(*) FROM runtime_record_receipts').fetchone()[0] == receipt_count
    assert [tuple(r) for r in case.store.db.execute('SELECT * FROM runtime_observations ORDER BY episode_id,unit_index')] == before


def test_actual_selected_tool_information_and_child_ownership(native_case):
    case = native_case
    program = case.request['native_infernal']['program']
    entry, = [r for r in case.owner.resource_tool_contracts() if r['name'] == 'native.' + program]
    assert entry['description'] and entry['instructions'] and entry['resources'] == 'local'
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    schema = entry['input_schema']['properties']['native_infernal']['properties']
    assert schema['program'] == {'const': program}
    assert schema['software'] == {'const': case.request['native_infernal']['software']}
    scientific_calls = [call for call in case.provider.calls if 'scientific_process' in call[2]]
    assert len(scientific_calls) == 1 + len(case.contexts)
    for _, _, state, _ in scientific_calls:
        information, = state['scientific_process']['child_tool_info']
        assert information == {k: entry[k] for k in ('name', 'description', 'resources', 'instructions')}
    assert case.flow.catalog(case.scope, source=case.root.source) == []
    actions = [json.loads(r[0]) for r in case.store.db.execute('SELECT action FROM runtime_actions')]
    assert sum(a.get('tool') == 'practical.job.start' for a in actions) == 1
    assert sum(a.get('tool') == 'execution.results.collect' for a in actions) == len(case.contexts)


@pytest.mark.parametrize('forgery', ['number', 'name', 'relationship'])
def test_forged_native_values_rejected_by_owner_and_higher_receiver(native_case, forgery):
    case = native_case
    context, result, form = case.contexts[0], case.returned[0], case.forms[0]
    changed = deepcopy(result)
    row = changed['rows'][0]
    if forgery == 'number':
        row['measurements'][0]['value'] += 1
    elif forgery == 'name':
        row['sequence_name'] = changed['rows'][1]['sequence_name']
    else:
        row['subject_ref'] = changed['rows'][1]['subject_ref']
    with pytest.raises(ValueError):
        case.owner.validate_report(context, changed, form)
    science = next(r for r in case.records if case.owner.native_infernal_returns.context(r['episode_id']).role == 'scientific_process')
    science_context = case.owner.native_infernal_returns.context(science['episode_id'])
    forwarded = json.loads(case.flow.journal.row('runtime_forms', science['episode_id'])['form'])
    family = context.assignment['selector']['projection']['family']
    forwarded[family] = changed['rows']
    with pytest.raises(ValueError):
        case.owner.validate_received_report(science_context, forwarded, case.scientific_form)
    assert_counts(case)


def test_matching_forged_frozen_return_still_fails_original_native_facts(native_case):
    case = native_case
    context, form = case.contexts[0], case.forms[0]
    row = case.flow.journal.row('runtime_forms', context.episode_id)
    saved = {key: row[key] for key in ('form', 'facts')}
    attempts = [dict(r) for r in case.store.db.execute('SELECT * FROM runtime_report_attempts WHERE child_episode_id=?',
        (context.episode_id,))]
    changed = deepcopy(case.returned[0])
    changed['rows'][0]['measurements'][0]['value'] += 1
    facts = json.loads(saved['facts'])
    family = context.assignment['selector']['projection']['family']
    facts[FAMILY_SOURCES[family]] = changed['rows']
    try:
        case.store.db.execute('UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?',
            (json.dumps(changed), json.dumps(facts), RUN_ID, context.episode_id))
        case.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND child_episode_id=?',
            (json.dumps(changed), RUN_ID, context.episode_id))
        root_context = case.owner.native_infernal_returns.context(case.record.episode_id)
        with pytest.raises(ValueError, match='returned_facts_conflict'):
            case.owner.native_infernal_returns.received_context(root_context)
    finally:
        case.store.db.execute('UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?',
            (saved['form'], saved['facts'], RUN_ID, context.episode_id))
        for attempt in attempts:
            case.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (attempt['form'], RUN_ID, attempt['parent_episode_id'], attempt['decision_index']))
    case.owner.validate_report(context, case.returned[0], form)
    assert_counts(case)


def test_same_native_row_source_and_observation_survive_metrics_and_pages(tmp_path):
    first = selector('search_hit', rows={'offset': 0, 'limit': 1}, metrics=['bitscore'])
    def duplicate(previous):
        return selector('search_hit', rows={'record_keys': [previous['rows'][0]['record_key']]}, metrics=['evalue'])
    second = selector('search_hit', rows={'offset': 1, 'limit': 1}, metrics=['bitscore'])
    case = run_case(tmp_path, 'cmsearch', selectors=[first, duplicate, second], nested=True,
        root_read_after_return=True)
    try:
        one, again, two, redelivered = [form['rows'][0] for form in case.returned]
        assert redelivered == one
        assert one['source_ref'] == again['source_ref'] == two['source_ref']
        assert one['record_key'] == again['record_key'] != two['record_key']
        assert one['observation_ref'] == again['observation_ref'] != two['observation_ref']
        assert values(one) == {'bitscore': 71.4} and values(again) == {'evalue': 3.6e-22}
        assert history(case.child_records[1]) == [0]
        assert history(case.child_records[3]) == [0]
        assert case.record.controller_state.history == (2, 0)
        assert case.record.units_consumed == 2
        assert case.store.count('observation') == 2
        full = json.loads(case.store.get_artifact(case.outcomes[0]['result']['prepared']['scores_artifact_ref']))
        assert len(full['hits']) == 10
        retained = case.store.get(one['observation_ref'])
        assert len(retained['measurements']) > 1
        first_receipt = next((current, instructions) for _, _, current, instructions in case.provider.calls
            if 'scientific_process' in current and current.get('child_reports')
            and current['child_reports'][-1].get('rows') == [one])
        steering = render_scientific_process_prompt(*first_receipt).split('\n\nSTEERING', 1)[1]
        assert 'bitscore' in steering
        assert all(metric not in steering for metric in NATIVE_INFERNAL_METRICS['search_hit']
            if metric != 'bitscore'), 'unrequested saved native measurements reintroduced into scientific STEERING'
        presented = presented_root_after_return(case)
        requested = {one['observation_ref']: {'bitscore', 'evalue'}, two['observation_ref']: {'bitscore'}}
        for observation in presented['working_state']['observations']:
            if observation.get('native_infernal'):
                assert {m['name'] for m in observation['measurements']} <= requested[observation['id']]
        assert_counts(case)
    finally:
        case.store.close()


@pytest.mark.parametrize('decision,allowed', [(6, {'bitscore'}), (8, {'bitscore', 'evalue'})])
def test_saved_actual_scientific_prompt_keeps_requested_native_metrics(decision, allowed, monkeypatch):
    saved = json.loads((ROOT / 'tests/fixtures/native_infernal_episode' /
        f'scientific-decision-{decision}.json').read_text())
    original = deepcopy(saved)
    assert len(saved['context']['working_state']['observations'][0]['measurements']) > len(allowed)
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    def forbidden(*args, **kwargs):
        raise AssertionError('saved receiver presentation attempted acquisition or native work')
    with monkeypatch.context() as isolated:
        isolated.setattr(socket, 'socket', forbidden)
        isolated.setattr(subprocess, 'Popen', forbidden)
        isolated.setattr(Store, 'get', forbidden)
        isolated.setattr(Store, 'get_artifact', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.run', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.populate_infernal_search_sheet', forbidden)
        isolated.setattr('gene_annotation_episode.native_infernal_result_worker.calculate_infernal_search_scores', forbidden)
        text, _ = connection._presentation(saved['episode_id'], saved['role'],
            saved['instructions'], saved['context'])
        assert text == render_scientific_process_prompt(saved['context'], saved['instructions'])
    steering = text.split('\n\nSTEERING', 1)[1]
    assert all(metric in steering for metric in allowed)
    assert all(metric not in steering for metric in NATIVE_INFERNAL_METRICS['search_hit'] if metric not in allowed)
    assert saved == original


@pytest.mark.parametrize('kind', ['unbound', 'wrong_sequence', 'completion_only', 'source_only',
    'nested_source_only', 'zero_hits'])
def test_subject_binding_and_requested_information_distinctions(tmp_path, kind):
    case = run_case(tmp_path, 'cmsearch', bind=kind != 'unbound', wrong_sequence=kind == 'wrong_sequence',
        incomplete=kind == 'wrong_sequence', include_rows=kind not in {'completion_only', 'source_only', 'nested_source_only'},
        include_refs=kind in {'zero_hits', 'source_only', 'nested_source_only'}, no_hits=kind == 'zero_hits',
        nested=kind == 'nested_source_only', root_read_after_return=kind == 'nested_source_only')
    try:
        result, body = case.returned[0], case.outcomes[0]['result']
        if kind == 'unbound':
            assert result['completed'] and result['rows']
            assert all(r['status'] == 'unbound' and r['subject_ref'] is None and r['observation_ref'] is None
                and r['measurements'] for r in result['rows'])
            assert case.store.count('observation') == 0
        elif kind == 'wrong_sequence':
            assert not result['completed'] and result['rows'][0]['status'] == 'invalid'
            assert result['rows'][0]['observation_ref'] is None
            assert any(r['status'] == 'published' for r in result['rows'][1:])
            assert any('subject_sequence' in f['code'] for f in body['failures'])
            assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
        elif kind == 'completion_only':
            assert result == {'completed': True}
            assert case.store.count('observation') == 10
            assert list(case.flow.receipts.known(case.record.episode_id, record_type='observation')) == []
            assert case.owner.facts(case.contexts[0], {})[FAMILY_SOURCES['search_hit']] == []
            assert case.record.controller_state.history == (0, 0)
            assert case.flow.working_state(case.root.source)['observations'] == []
        elif kind in {'source_only', 'nested_source_only'}:
            assert result['completed'] and result['references']
            root_context = case.owner.native_infernal_returns.context(case.record.episode_id)
            assert body['source_ref'] in result['references']
            assert set(result['references']) <= set(case.flow.receipts.known(case.record.episode_id))
            assert case.owner.resolve_received_reference(root_context, body['source_ref'], 'execution_result')
            groups = case.owner.native_infernal_returns.received_context(root_context)
            assert not any(g['fact_source'] in FAMILY_SOURCES.values() for g in groups)
            numeric_form = results_form('search_hit')
            assert case.owner.native_infernal_returns.received_facts(root_context, numeric_form) == {
                FAMILY_SOURCES['search_hit']: []}
            assert not case.owner.resolve_received_reference(root_context, body['rows'][0]['record_key'], 'native_infernal_row')
            if kind == 'nested_source_only':
                science = next(r for r in case.records if case.owner.native_infernal_returns.context(r['episode_id']).role == 'scientific_process')
                forwarded = json.loads(case.flow.journal.row('runtime_forms', science['episode_id'])['form'])
                assert forwarded['references'] == result['references']
                assert case.provider.handoff in forwarded['handoff_and_result_references']
                assert case.scientific_form['properties']['references']['x-source'] == 'execution_infernal_result_refs'
                presented = presented_root_after_return(case)
                assert all(not r.get('native_infernal') or not r.get('measurements')
                    for r in presented['working_state']['observations'])
                assert history(case.child_records[1]) == [0]
        else:
            assert result['completed'] and result['rows'] == [] and len(result['references']) == 1
            assert case.store.count('observation') == 0
            assert history(case.child_records[0]) == [2]
            assert case.child_records[0]['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert_counts(case)
    finally:
        case.store.close()


@pytest.mark.parametrize('fault', ['missing_row', 'changed_byte', 'native_failure'])
def test_specific_failures_preserve_partial_native_work_without_false_completion(tmp_path, fault):
    def corrupt(store, plan):
        path = Path(plan['attempt_directory']) / 'stdout.log'
        (tmp_path / 'original-native-stdout.log').write_bytes(path.read_bytes())
        path.write_bytes(b'changed original native output\n')
    choices = [selector('search_hit', rows={'record_keys': ['missing-native-row']})] if fault == 'missing_row' else None
    case = run_case(tmp_path, 'cmalign' if fault == 'native_failure' else 'cmsearch', selectors=choices,
        native_failure=fault == 'native_failure', before_collection=corrupt if fault == 'changed_byte' else None,
        incomplete=True, include_refs=True, include_origin=True)
    try:
        body = case.outcomes[0]['result']
        assert not body['complete'] and not case.returned[0]['completed']
        assert body['source_ref'] and body['prepared']['sheet_artifact_ref']
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
        if fault == 'missing_row':
            assert case.returned[0]['rows'] == [] and case.store.count('observation') == 0
            assert {'stage': 'selection', 'code': 'native_infernal_requested_record_key_missing',
                'record_key': 'missing-native-row'} in body['failures']
        elif fault == 'changed_byte':
            assert not body['capture']['complete']
            assert any(r['role'] == 'stdout' for r in body['capture']['invalid_artifacts'])
            assert any(r['role'] == 'tblout' for r in body['capture']['artifacts'])
            assert any('digest_mismatch' in f['code'] for f in body['failures'])
            assert case.returned[0]['rows'] and values(case.returned[0]['rows'][0])['bitscore'] == 71.4
        else:
            bundle = json.loads(case.store.get_artifact(body['capture']['bundle_artifact_ref']))
            assert bundle['returncode'] != 0 and body['capture']['bundle_validated']
            assert any(f['code'] == 'native_infernal_nonzero_returncode' for f in body['failures'])
            assert case.returned[0]['origin'] is None
            assert body['observation']['state'] == 'failed'
            assert bundle['requested_job']['native_infernal']['options'] == ['--cpu', '1', '--sample', '--seed', '42']
        assert len(list(case.workspace.rglob('infernal-plan.json'))) == 1
        assert_counts(case)
    finally:
        case.store.close()
