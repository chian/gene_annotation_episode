"""Real BLAST work through Workflow, selected local children and typed forms.

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
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.blast_pairwise_result_views import (
    FAMILY_SOURCES, NATIVE_BLAST_METRICS,
    native_blast_fact_sources,
)
from gene_annotation_episode.native_blast_contracts import (
    compile_native_blast_job, requested_job_from_native,
)
from gene_annotation_episode.native_blast_local import local_blast_plan
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
INPUTS = ROOT / 'verification/tool_graders_blast_pairwise_2026-10-26_294'
LABELS = {'blastn': 'blastn_range_forward_json15', 'blastp': 'blastp_gaps_json15',
    'blastx': 'blastx_range_reverse_json15', 'tblastn': 'tblastn_reverse_json15',
    'tblastx': 'tblastx_frames_json15'}
PUBLICATION = ROOT / 'research/slotted_process_library/publications/2026-10-24-001'
POLICY = {'memory_bytes': 20 * 1024**3, 'scratch_bytes': 4 * 1024**3, 'wall_seconds': None}
RUN_ID = 'native-blast-episode-298'


def selected(name, arguments=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}}, 'report_update': {}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Measure native paired BLAST correspondence for the supplied sequences.',
        'scope': scope, 'purpose': 'Return exactly the requested native numerical measurements and associations.',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'},
        'report_update': {}}


def selector(family, *, rows=None, metrics=None):
    return {'version': 'native_blast_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'family': family, 'rows': rows or {'offset': 0, 'limit': 50},
            'metrics': list(metrics or NATIVE_BLAST_METRICS[family])}}


def results_form(family, *, include_rows=True, include_refs=False, include_origin=False):
    fields = {'completed': {'type': 'boolean', 'x-source': 'execution_completed'}}
    if include_rows:
        fields['rows'] = native_blast_fact_sources()[FAMILY_SOURCES[family]]['report_schema']
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


def retained_request(program, *, no_hits=False):
    label = 'blastn_no_hits_json15' if no_hits else LABELS[program]
    paths = [INPUTS / directory / label / 'plan.json' for directory in ('native_examples', 'native_ranges')]
    return deepcopy(json.loads(next(path for path in paths if path.exists()).read_bytes())['requested_job'])


def bound_request(store, program, *, bind=True, wrong_sequence=False, native_failure=False, no_hits=False):
    request = retained_request(program, no_hits=no_hits)
    job = request['native_blast']
    query = next(row for row in job['operands'] if row['role'] == 'query_sequence')
    reference = next(row for row in job['operands'] if row['role'] == 'subject_sequence')
    name, sequence = fasta_records(query['path'])[0]
    if wrong_sequence:
        sequence = ('C' if sequence[0] != 'C' else 'A') + sequence[1:]
    query_file = store.path.parent / 'supplied-query.fa'
    query_file.write_text('>' + name + '\n' + sequence + '\n')
    molecule = 'protein' if program in ('blastp', 'tblastn') else 'dna'
    subject, = store.create_problem(query_file, molecule=molecule, format='fasta')['subject_refs']
    job['operand_bindings'] = []
    if bind:
        job['operand_bindings'].append({'operand_role': 'query_sequence', 'record_ordinal': 0,
            'native_name': name, 'native_accession': None, 'subject_ref': subject, 'reference_ref': None})
    job['operand_bindings'].append({'operand_role': 'subject_sequence', 'record_ordinal': 0,
        'native_name': fasta_records(reference['path'])[0][0], 'native_accession': None,
        'subject_ref': None, 'reference_ref': None})
    if native_failure:
        job['options'] += ['-matrix', 'MISSING_MATRIX_298']
    return requested_job_from_native(job), store.validate_scope()


def practical_assignment(workspace, request):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'native-blast-results',
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
    selectors = selectors or [selector('pairwise_hsp')]
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_blast': [{key: request['native_blast'][key] for key in ('program', 'mode', 'software')}]}}
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
                next(row['path'] for row in request['native_blast']['operands'] if row['role'] == 'query_sequence'))],
                'molecule': 'protein' if program in ('blastp', 'tblastn') else 'dna', 'candidate_function_required': False}}
        families = list(dict.fromkeys(s['projection']['family'] for s in selectors if not callable(s)))
        fields = ({family: native_blast_fact_sources()[FAMILY_SOURCES[family]]['report_schema'] for family in families}
            if include_rows else {'references': owner.received_report_sources('scientific_process')[
                'execution_blast_pairwise_result_refs']['report_schema']})
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
                self.plan = local_blast_plan(assignment, self.target['execution_id'])
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
    root = flow.build('annotation', 'root', 'Measure native paired BLAST correspondence in the supplied sequences.', scope)
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


def values(row):
    return {value['name']: value['value'] for value in row['measurements']}


def assert_counts(case):
    actions = case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0]
    observations = case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
    assert actions == observations == len(case.provider.calls)
    for record in case.records:
        own = case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE episode_id=?',
            (record['episode_id'],)).fetchone()[0]
        observed = case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE episode_id=?',
            (record['episode_id'],)).fetchone()[0]
        assert own == observed == record['units_consumed']


@pytest.fixture(scope='module')
def native_case(tmp_path_factory):
    choices = [selector('pairwise_hsp', metrics=['paired_positions', 'query_aligned_positions']),
        selector('pairwise_union', metrics=['query_length', 'query_paired_coverage',
            'query_selected_length', 'query_selected_paired_positions', 'query_selected_paired_coverage']),
        selector('pairwise_hsp', metrics=['native_score_bits'])]
    case = run_case(tmp_path_factory.mktemp('translated-reverse'), 'blastx', selectors=choices,
        nested=True, status_first=True)
    yield case
    case.store.close()


def test_real_selected_translated_reverse_path_and_filled_parent_forms(native_case):
    case = native_case
    first, union, repeated = [form['rows'][0] for form in case.returned]
    assert values(first) == {'paired_positions': 62, 'query_aligned_positions': 186}
    assert values(union) == {'query_length': 244, 'query_paired_coverage': 186 / 244,
        'query_selected_length': 186, 'query_selected_paired_positions': 186,
        'query_selected_paired_coverage': 1}
    assert first['observation_ref'] == repeated['observation_ref']
    assert first['record_key'] == repeated['record_key']
    assert len({out['result']['source_ref'] for out in case.outcomes}) == 1
    assert union['observation_ref'] is None and case.store.count('observation') == 1
    observation = case.store.get(first['observation_ref'])
    assert observation['native_blast_pairwise'] == {
        'version': 'native_blast_pairwise_observation_v1', 'program': 'blastx',
        'record_key': first['record_key'], 'search_key': first['search_key'],
        'hit_ordinal': first['hit_ordinal'], 'hsp_ordinal': first['hsp_ordinal'],
        'bundle_artifact_ref': case.outcomes[0]['result']['capture']['bundle_artifact_ref']}
    assert observation['operand_intervals'][0] == {'role': 'query', 'subject_ref': first['subject_ref'],
        'start': 29, 'end': 215, 'unit': 'nt', 'model_unit': 'aa'}
    assert len(observation['measurements']) > len(first['measurements'])
    science = next(record for record in case.records if case.owner.native_blast_returns.context(
        record['episode_id']).role == 'scientific_process')
    form = json.loads(case.flow.journal.row('runtime_forms', science['episode_id'])['form'])
    assert form == {'pairwise_hsp': [first, repeated], 'pairwise_union': [union]}
    context = case.owner.native_blast_returns.context(case.record.episode_id)
    assert {group['fact_source']: group['facts'] for group in
        case.owner.native_blast_returns.received_context(context)} == {
        FAMILY_SOURCES[key]: rows for key, rows in form.items()}
    assert case.record.units_consumed == 1 and science['units_consumed'] == 4
    assert case.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 13
    assert_counts(case)


def test_complete_custody_and_original_output_geometry(native_case):
    case = native_case
    assert len(list(case.workspace.rglob('blast-plan.json'))) == 1
    assert case.plan['policy'] == POLICY
    handle = native.NativeJobHandle(Path(case.plan['identity']['execution_id'])).read()
    assert handle['metadata']['verified_cgroup']['memory_max'] == POLICY['memory_bytes']
    assert handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert handle['metadata']['verified_cgroup']['runtime_max'] == 'infinity'
    for context, outcome in zip(case.contexts, case.outcomes):
        body = outcome['result']
        assert outcome['status'] == 'completed' and body['complete'], body['failures']
        bundle = json.loads(case.store.get_artifact(body['capture']['bundle_artifact_ref']))
        assert bundle['identity'] == case.plan['identity'] and bundle['requested_job'] == case.request
        assert len(body['capture']['artifacts']) == len(bundle['inputs']) + len(bundle['artifacts'])
        source = case.store.get(body['source_ref'])
        assert {row['artifact_ref'] for row in body['capture']['artifacts']} <= set(source['auxiliary_artifact_refs'])
        sheet = json.loads(case.store.get_artifact(body['prepared']['sheet_artifact_ref']))
        search = sheet['collection']['searches'][0]
        hsp = search['normalized']['hits'][0]['hsps'][0]
        assert (hsp['query_from'], hsp['query_to'], hsp['query_frame']) == (30, 215, -3)
        assert search['normalized']['query']['length'] == 186
        scores = json.loads(case.store.get_artifact(body['prepared']['scores_artifact_ref']))
        assert len(scores['rows']['pairwise_hsp']) == 1
        case.owner.validate_report(context, case.returned[case.contexts.index(context)],
            case.forms[case.contexts.index(context)])
        description = case.owner.job_progress_provider.targets.describe_target(
            case.provider.handoff, case.scope, selector=plain(context.assignment)['selector'])
        assert description['service_or_program'] == 'blastx'
        assert description['mode'] == 'pairwise' and description['output_format'] == 'native_blast_bundle_v1'
        assert description['selected_outputs'] == case.request['native_blast']['outputs']
        assert description['status_meanings']['process_liveness_establishes_productive_work'] is False
        assert description['acquisition_operations'] == ['execution.results.status', 'execution.results.collect']
        assert description['extractors'][1]['implementation'].endswith('NativeBLASTResults.execute')
        assert description['result_selector_schema']['properties']['version']['const'] == 'native_blast_result_selector_v1'


def test_exact_zero_completion_and_stable_credit(native_case):
    case = native_case
    for index, (context, record, outcome) in enumerate(zip(case.contexts, case.child_records, case.outcomes)):
        assert record['units_consumed'] == 2
        assert history(record)[0] == 0
        assert history(record)[1] == (6 if index == 0 else 0)
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        proof = case.owner.completion_for_action(context, outcome['result']['operation_key'])
        assert proof and case.owner.verify_completion(context, proof)
    for role, gain in [('launch_local', 7), ('launch', 3)]:
        record = next(record for record in case.records if case.owner.native_blast_returns.context(
            record['episode_id']).role == role)
        assert history(record) == [gain] and record['units_consumed'] == 1
        assert record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    assert_counts(case)


def test_replay_redelivery_and_closed_return_never_recompute(native_case, monkeypatch):
    case = native_case
    context = case.owner.native_blast_returns.context(case.record.episode_id)
    expected = case.owner.native_blast_returns.received_context(context)
    before = list(case.store.db.iterdump())
    def forbidden(*args, **kwargs):
        raise AssertionError('Closed BLAST return performed new work')
    with unavailable_native_attempt(case.plan), monkeypatch.context() as isolated:
        for name in ('capture_local_bundle', 'prepare_native_blast_grading', 'publish_selected_native_blast_rows'):
            isolated.setattr('gene_annotation_episode.native_blast_results.' + name, forbidden)
        isolated.setattr('gene_annotation_episode.native_blast_result_worker.run', forbidden)
        for name in ('populate_blast_pairwise_sheet', 'calculate_blast_pairwise_components'):
            isolated.setattr('gene_annotation_episode.blast_pairwise_results.' + name, forbidden)
        isolated.setattr(subprocess, 'Popen', forbidden)
        isolated.setattr(case.owner.job_progress_provider.targets, 'observe_target', forbidden)
        for child_context, original in zip(case.contexts, case.outcomes):
            replay = asyncio.run(case.owner.execute(child_context, 'execution.results.collect', {},
                original['result']['operation_key']))
            assert replay == {key: value for key, value in original.items() if key != 'pending_work_after_action'}
        assert case.owner.native_blast_returns.received_context(context) == expected
        science = next(record for record in case.records if case.owner.native_blast_returns.context(
            record['episode_id']).role == 'scientific_process')
        form = json.loads(case.flow.journal.row('runtime_forms', science['episode_id'])['form'])
        case.flow.receive_form(case.root.source, form, case.scientific_form, 0, redelivery=True)
    assert list(case.store.db.iterdump()) == before
    assert_counts(case)


def test_three_slots_and_receiver_presentation_keep_only_requested_numbers(native_case):
    case = native_case
    entry, = [row for row in case.owner.resource_tool_contracts() if row['name'] == 'native.blastx']
    assert entry['invocation_route'] == {'kind': 'commission', 'routes': [
        {'entry_role': 'launch', 'resource_id': 'here', 'resource_role': 'launch_local'}]}
    science_calls = [row for row in case.provider.calls if 'scientific_process' in row[2]]
    for _, _, current, _ in science_calls:
        info, = current['scientific_process']['child_tool_info']
        assert info == {key: entry[key] for key in ('name', 'description', 'resources', 'instructions')}
    assert case.flow.catalog(case.scope, source=case.root.source) == []
    received_call = next(row for row in science_calls if any('rows' in form for form in row[2]['child_reports']))
    current, instructions = received_call[2:]
    rendered = render_scientific_process_prompt(current, instructions).split('\n\nSTEERING', 1)[1]
    assert 'paired_positions' in rendered and 'query_aligned_positions' in rendered
    assert 'native_evalue' not in rendered and 'native_raw_score' not in rendered
    # Child input uses its original assignment and task; no ancestor yield history.
    for row in case.store.db.execute('SELECT path,request FROM runtime_episodes'):
        if len(json.loads(row['path'])) > 1:
            message = json.loads(row['request'])['message']
            assert not any('history' in key or 'yield' in key for key in message)


@pytest.mark.parametrize('program', ['blastn', 'blastp', 'blastx', 'tblastn', 'tblastx'])
def test_all_five_bound_schema_and_software_constraints(tmp_path, program):
    from jsonschema import Draft202012Validator
    with Store(tmp_path / 'state') as store:
        request, scope = bound_request(store, program)
        workspace = tmp_path / 'workspace'
        workspace.mkdir()
        configuration = {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY,
            'native_blast': [{key: request['native_blast'][key] for key in ('program', 'mode', 'software')}]}
        owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=RUN_ID,
            resources={'here': configuration}, initial_information={}, tool_registry=ToolRegistry(store),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
        assignment = practical_assignment(workspace, request)
        schema = owner._request_schema('here', selected=True)
        assert Draft202012Validator(schema).is_valid(assignment)
        assert owner._validate_request(assignment) == assignment
        changed = deepcopy(assignment)
        changed['requested_job']['native_blast']['software']['sha256'] = 'f' * 64
        assert not Draft202012Validator(schema).is_valid(changed)
        with pytest.raises(ValueError):
            owner._validate_request(changed)
        changed = deepcopy(assignment)
        changed['constraints']['allocation']['memory_bytes'] -= 1
        with pytest.raises(ValueError, match='allocation'):
            owner._validate_request(changed)
        changed = deepcopy(assignment)
        changed['requested_job']['native_blast']['mode'] = 'database'
        assert not Draft202012Validator(schema).is_valid(changed)
        with pytest.raises(ValueError):
            owner._validate_request(changed)
        for kind in ('api', 'pbs_ssh'):
            unsupported = {**configuration, 'kind': kind}
            with pytest.raises(ValueError, match='native_blast_resource_execution_binding_unfinished'):
                ExecutionEpisodes(None, store=store, directory=tmp_path / kind, run_id=RUN_ID,
                    resources={'here': unsupported}, initial_information={}, tool_registry=ToolRegistry(store),
                    handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))


@pytest.mark.parametrize('kind', ['zero_hits', 'missing_report', 'changed_stdout', 'native_failure',
    'source_only', 'completion_only'])
def test_partial_failure_zero_hits_and_unrequested_data(tmp_path, kind):
    def alter(store, plan):
        root = Path(plan['attempt_directory'])
        job = plan['requested_job']['native_blast']
        role = 'primary_report' if kind == 'missing_report' else 'stdout'
        path = root / next(row['relative_path'] for row in job['outputs'] if row['role'] == role)
        (tmp_path / 'preserved-original-output').write_bytes(path.read_bytes())
        if kind == 'missing_report':
            path.unlink()
        else:
            path.write_bytes(b'changed post-seal output\n')
    failure = kind in {'missing_report', 'changed_stdout', 'native_failure'}
    case = run_case(tmp_path, 'blastp' if kind == 'native_failure' else 'blastn',
        no_hits=kind == 'zero_hits', native_failure=kind == 'native_failure',
        before_collection=alter if kind in {'missing_report', 'changed_stdout'} else None,
        include_rows=kind not in {'source_only', 'completion_only'}, include_refs=kind != 'completion_only',
        include_origin=True, incomplete=failure)
    try:
        result, body = case.returned[0], case.outcomes[0]['result']
        assert result['completed'] is (not failure)
        assert body['complete'] is (not failure)
        if failure:
            assert body['failures'] and not case.owner.completion_for_action(case.contexts[0], body['operation_key'])
            if kind == 'changed_stdout':
                assert result['rows'][0]['status'] == 'published'
                assert body['capture']['invalid_artifacts'][0]['role'] == 'stdout'
            elif kind == 'native_failure':
                assert result['origin'] is None and body['observation']['state'] == 'failed'
                assert any(row['code'] == 'native_blast_nonzero_returncode' for row in body['failures'])
            else:
                assert not body['capture']['complete']
        elif kind == 'zero_hits':
            assert result['rows'] == [] and len(result['references']) == 1
            assert case.store.count('observation') == 0 and history(case.child_records[0]) == [2]
        else:
            root = case.owner.native_blast_returns.context(case.record.episode_id)
            assert case.owner.native_blast_returns.received_context(root) == []
            assert not case.owner.resolve_received_reference(root, body['rows'][0]['record_key'],
                'native_blast_pairwise_row')
            assert case.owner.facts(case.contexts[0], {})[FAMILY_SOURCES['pairwise_hsp']] == []
            if kind == 'completion_only':
                assert list(case.flow.receipts.known(case.record.episode_id, record_type='observation')) == []
        assert len(list(case.workspace.rglob('blast-plan.json'))) == 1
        assert_counts(case)
    finally:
        case.store.close()


@pytest.mark.parametrize('change', ['number', 'source', 'ordinal', 'union'])
def test_forged_form_rejected_at_original_and_scientific_boundary(native_case, change):
    case = native_case
    index = 1 if change == 'union' else 0
    changed = deepcopy(case.returned[index])
    row = changed['rows'][0]
    if change in {'number', 'union'}:
        row['measurements'][0]['value'] += 1
    elif change == 'source':
        row['source_ref'] = case.provider.handoff
    else:
        row['hsp_ordinal'] += 1
    with pytest.raises(ValueError):
        case.owner.validate_report(case.contexts[index], changed, case.forms[index])
    with pytest.raises(ValueError):
        case.owner.validate_received_report(case.contexts[index], changed, case.forms[index])


@pytest.mark.parametrize('change', ['interval', 'unrequested_measurement', 'marker', 'reference'])
def test_frozen_observation_tamper_is_rejected(native_case, change):
    case = native_case
    reference = case.returned[0]['rows'][0]['observation_ref']
    saved = case.store.db.execute('SELECT data FROM records WHERE id=?', (reference,)).fetchone()
    # Use the Store's exact persisted record representation; restore every byte.
    if saved is None:
        raise AssertionError('Published observation missing')
    changed = json.loads(saved['data'])
    if change == 'interval':
        changed['operand_intervals'][0]['start'] += 1
    elif change == 'unrequested_measurement':
        next(value for value in changed['measurements'] if value['name'] == 'native_raw_score')['value']['value'] += 1
    elif change == 'marker':
        changed['native_blast_pairwise']['hsp_ordinal'] += 1
    else:
        changed['source_subject_refs'] = []
    try:
        case.store.db.execute('UPDATE records SET data=? WHERE id=?', (json.dumps(changed), reference))
        with pytest.raises(ValueError, match='frozen_publication'):
            case.owner.native_blast_results.facts(case.contexts[0])
    finally:
        case.store.db.execute('UPDATE records SET data=? WHERE id=?', (saved['data'], reference))


def test_matching_forged_form_and_facts_still_fail_original_receipt(native_case):
    case = native_case
    context = case.contexts[0]
    saved = case.flow.journal.row('runtime_forms', context.episode_id)
    original = {key: saved[key] for key in ('form', 'facts')}
    attempts = [dict(row) for row in case.store.db.execute(
        'SELECT * FROM runtime_report_attempts WHERE child_episode_id=?', (context.episode_id,))]
    changed = deepcopy(case.returned[0])
    changed['rows'][0]['measurements'][0]['value'] += 1
    facts = json.loads(original['facts'])
    facts[FAMILY_SOURCES['pairwise_hsp']] = changed['rows']
    try:
        case.store.db.execute('UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?',
            (json.dumps(changed), json.dumps(facts), RUN_ID, context.episode_id))
        case.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND child_episode_id=?',
            (json.dumps(changed), RUN_ID, context.episode_id))
        root_context = case.owner.native_blast_returns.context(case.record.episode_id)
        with pytest.raises(ValueError, match='returned_facts_conflict'):
            case.owner.native_blast_returns.received_context(root_context)
    finally:
        case.store.db.execute('UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?',
            (original['form'], original['facts'], RUN_ID, context.episode_id))
        for attempt in attempts:
            case.store.db.execute('UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=?',
                (attempt['form'], RUN_ID, attempt['parent_episode_id'], attempt['decision_index']))


@pytest.mark.parametrize('change', ['intent', 'observation', 'capture_plan', 'capture_intent', 'assignment'])
def test_immutable_action_sidecars_qualify_the_original_owner(native_case, change):
    case = native_case
    body = case.outcomes[0]['result']
    from gene_annotation_episode.execution_contracts import digest
    directory = case.owner.directory / 'execution-results' / digest([RUN_ID, body['episode_id']]) / 'native-blast-actions' / digest(body['operation_key'])
    filename = {'intent': 'intent.json', 'observation': 'observation.json',
        'capture_plan': 'capture/capture-plan.json', 'capture_intent': 'capture/capture-intent.json',
        'assignment': '../../assignment.json'}[change]
    path = directory / filename
    saved = path.read_bytes()
    changed = json.loads(saved)
    if change == 'intent':
        changed['operation_key'] += ':forged'
    elif change == 'observation':
        changed['observed_at'] = '2000-01-01T00:00:00+00:00'
    elif change == 'capture_intent':
        changed['target']['origin_episode_id'] = case.record.episode_id
    elif change == 'assignment':
        changed['episode_id'] = case.record.episode_id
    else:
        changed['identity']['episode_id'] = case.record.episode_id
    try:
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError):
            case.owner.native_blast_results.facts(case.contexts[0])
    finally:
        path.write_bytes(saved)


