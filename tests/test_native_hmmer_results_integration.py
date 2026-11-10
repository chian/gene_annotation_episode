"""Selected original HMMER results through the shared Workflow and typed return.

Tiny source sequences are synthetic; HMMER programs, local cgroups, native
outputs, acquisition, numerical workers, observations and admission are real.
Decisions and the annotation parent's continuation/projection are fixture
settings. Successful resource/results roles use production operational credit
and terminal estimation; incomplete fault cases disclose a fixture base
estimator while retaining actual proof validation. This suite does not test an
LLM, remote service, HPC, or W05.
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

from method_loop.archive import iter_json
import pytest

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.hmmer_native_result_views import (
    FAMILY_SOURCES, NATIVE_HMMER_METRICS, family_for_program, native_hmmer_fact_sources,
)
from gene_annotation_episode.native_hmmer_contracts import requested_job_from_native
from gene_annotation_episode.native_hmmer_local import local_hmmer_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / 'verification/tool_graders_native_hmmer_producer_2026-10-24/runs'
POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
LABELS = (
    'hmmscan_search_ordinary', 'hmmsearch_search_ordinary', 'jackhmmer_search_ordinary',
    'nhmmer_sequence_ordinary', 'nhmmer_profile_ordinary', 'nhmmer_alignment_ordinary',
    'nhmmer_profile_watson', 'nhmmscan_search_ordinary', 'hmmalign_align_ordinary',
    'hmmalign_align_trim', 'hmmalign_align_mapali', 'hmmsearch_search_empty',
)
METRICS = {
    'protein_domain': ['paired_positions', 'paired_model_coverage', 'native_domain_score_bits',
                       'native_independent_evalue', 'sequence_identity_fraction'],
    'nucleotide_locus': ['paired_positions', 'paired_model_coverage', 'sequence_span_coverage',
                         'native_score_bits', 'native_evalue'],
    'alignment_sequence': ['original_length', 'model_length', 'match_state_residues',
                           'trimmed_residues', 'model_occupancy', 'sequence_match_coverage'],
}
COLLECTIONS = {'protein_domain': 'domains', 'nucleotide_locus': 'loci', 'alignment_sequence': 'sequences'}


def selected(name, arguments=None):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': arguments or {}}, 'report_update': {}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Acquire the selected HMMER native measurements with original attempt custody',
        'scope': scope, 'purpose': 'Receive the explicitly requested original numerical rows',
        'assignment': assignment, 'schema_json': json.dumps(form), 'initial_report_json': '{}'},
        'report_update': {}}


def fasta_records(path):
    records = []
    for line in Path(path).read_text().splitlines():
        if line.startswith('>'):
            records.append([line[1:].split()[0], ''])
        elif line.strip():
            records[-1][1] += ''.join(line.split()).upper()
    return records


def bound_request(store, label, *, bind=True, wrong_sequence=False):
    job = deepcopy(json.loads((PRODUCER / label / 'plan.json').read_text())['requested_job']['native_hmmer'])
    # B003/064 retained metadata has known length/alphabet conflicts. A new
    # request explicitly omits those optional declarations and uses actual input
    # bytes. This does not alter the original retained fixture or its evidence.
    job['metadata'] = {}
    job['operand_bindings'] = []
    role = ('sequences' if job['program'] == 'hmmalign' else 'query_sequence'
            if job['program'] in {'hmmscan', 'nhmmscan'} else 'sequence_database')
    operand = next(row for row in job['operands'] if row['role'] == role)
    molecule = 'dna' if job['program'] in {'nhmmer', 'nhmmscan'} else 'protein'
    records = fasta_records(operand['path'])
    subject_path = store.path.parent / 'biological-subjects.fa'
    supplied = []
    for ordinal, (name, sequence) in enumerate(records):
        if wrong_sequence and ordinal == 0:
            sequence = ('C' if sequence[0] != 'C' else 'A') + sequence[1:]
        supplied.append('>' + name + '\n' + sequence + '\n')
    subject_path.write_text(''.join(supplied))
    subjects = store.create_problem(subject_path, molecule=molecule, format='fasta')['subject_refs']
    assert len(subjects) == len(records)
    for ordinal, ((name, sequence), subject) in enumerate(zip(records, subjects)):
        if bind:
            job['operand_bindings'].append({'operand_role': role, 'record_ordinal': ordinal,
                'native_name': name, 'native_accession': None, 'subject_ref': subject, 'reference_ref': None})
    return requested_job_from_native(job), store.validate_scope()


def selector(program, *, rows=None, metrics=None):
    family = family_for_program(program)
    return {'version': 'native_hmmer_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'family': family, 'rows': rows or {'offset': 0, 'limit': 50},
                       'metrics': list(metrics or METRICS[family])}}


def practical_assignment(workspace, request):
    return {'version': 'practical_assignment_v1', 'assignment_id': 'native-hmmer-results',
        'resource_id': 'here', 'resource_kind': 'local', 'workspace': str(workspace),
        'endpoint': 'usable_handoff', 'requested_job': request,
        'progress_requirements': [{'key': 'handoff', 'credit': 7,
                                  'predicate': {'kind': 'requested_job_handoff'}}],
        'completion_keys': ['handoff'], 'initial_context': {'revision': 0, 'cwd': str(workspace),
                                                          'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def results_form(family, *, include_rows=True, include_refs=False):
    fields = {'completed': {'type': 'boolean', 'x-source': 'execution_completed'}}
    if include_rows:
        fields['rows'] = native_hmmer_fact_sources()[FAMILY_SOURCES[family]]['report_schema']
    if include_refs:
        fields['references'] = {'type': 'array', 'uniqueItems': True, 'items': {
            'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_result'},
            'x-source': 'execution_result_refs'}
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def run_case(tmp_path, label, *, selectors=None, bind=True, wrong_sequence=False,
             include_rows=True, include_refs=False, status_first=False, before_collection=None,
             incomplete=False):
    store = Store(tmp_path / 'state')
    request, scope = bound_request(store, label, bind=bind, wrong_sequence=wrong_sequence)
    program = request['native_hmmer']['program']
    family = family_for_program(program)
    selectors = selectors or [selector(program)]
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': deepcopy(POLICY),
        'native_hmmer': [{key: request['native_hmmer'][key] for key in ('program', 'mode', 'software')}]}}
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
    form = results_form(family, include_rows=include_rows, include_refs=include_refs)

    def controller(path, initial):
        # Only the annotation parent and explicitly incomplete fault cases use
        # a finite scripted verification horizon. Production results completion
        # supplies its own estimator and is tested independently below.
        def estimate(history, parameters, contexts):
            count = 1 + len(selectors) if path[-1][0] == 'annotation' else 1 + int(status_first)
            return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1),
                parameters, {'fixture': 'explicit_verification_horizon'})
        use = path[-1][0] == 'annotation' or incomplete and path[-1][0] == 'results'
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                               estimate_with_context=estimate if use else None)

    def received_observation_count(actual_store, actual_scope):
        # Engineering parent projection counts only delivered observations.
        # It is intentionally not an annotation-confidence or W05 formula.
        rows = actual_store.db.execute('SELECT episode_id,path FROM runtime_episodes WHERE run_id=?',
                                      ('native-hmmer-results',)).fetchall()
        roots = [row['episode_id'] for row in rows if json.loads(row['path']) == [['annotation', 'root']]]
        if not roots:
            return 0
        receipts = EpisodeReceipts(actual_store, 'native-hmmer-results')
        return len(list(receipts.known(roots[0], record_type='observation')))

    class Choices:
        def __init__(self):
            self.calls = []
            self.root_calls = 0
            self.result_calls = {}
            self.handoff = None
            self.target = None
            self.plan = None

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
                assert count < 1 + int(status_first), current.get('last_local_outcome', current)
                self.result_calls[episode_id] = count + 1
                return selected('execution.results.status' if status_first and count == 0 else 'execution.results.collect')
            self.root_calls += 1
            if self.root_calls == 1:
                return child('launch', launch, scope, handoff_form)
            if self.handoff is None:
                self.handoff, = current['child_reports'][-1]['references']
                self.target = flow.progress_provider.job_provider.targets.read_target(self.handoff, scope)
                handle = native.NativeJobHandle(Path(self.target['execution_id']))
                # Test synchronization is not a production polling rule.
                assert (await asyncio.to_thread(native.wait_job, handle)).returncode == 0
                self.plan = local_hmmer_plan(assignment, self.target['execution_id'])
                if before_collection is not None:
                    before_collection(store, self.plan)
            selection = selectors[self.root_calls - 2]
            if callable(selection):
                selection = selection(current['child_reports'][-1])
            return child('results', {'version': RESULTS_VERSION, 'handoff_ref': self.handoff,
                'selector': selection}, scope, form)

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, ToolRegistry(store), provider, tmp_path / 'run', 'native-hmmer-results',
        controller_factory=controller, project_credit=received_observation_count,
        episode_service_factory=factory, episode_service_binding=factory.as_record(),
        episode_service_inputs='actual_tool_registry_v1', annotation_child_roles=('launch', 'results'),
        episode_record_receipts=True, initial_known_record_refs=[])
    if incomplete:
        # Fault cases deliberately close with partial data after the selected
        # collection. Bind a disclosed fixture base estimator; retain the real
        # practical proof verifier, credit projector and method_loop. This is
        # not evidence for production continuation of an unfinished assignment.
        binding = flow.episode_bindings.for_role('results')
        original_estimator = binding.practical_estimator
        def partial_estimator(context):
            if context.role != 'results':
                return original_estimator(context)
            def base(raw, parameters):
                return YieldEstimate(len(raw), NumericBand.exact(0 if raw else 1), parameters,
                    {'fixture': 'explicit_partial_result_verification_horizon'})
            return PracticalYieldEstimator(lambda proof: binding.verify_completion(context, proof), base_estimate=base)
        binding.practical_estimator = partial_estimator
    root = flow.build('annotation', 'root', 'Acquire the selected native HMMER numerical measurements', scope)

    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record

    record = asyncio.run(execute())
    archive = json.loads(''.join(iter_json(record.as_record())))
    owner = ExecutionEpisodes(None, store=store, directory=tmp_path / 'run', run_id=flow.run_id,
        resources=resources, initial_information={}, tool_registry=flow.tools, handoff_unit=3,
        acquired_record_unit=2, log_window_bytes=128, log_roles=('stdout', 'stderr'))
    contexts, returned, outcomes = [], [], []
    for unit in archive['units'][1:]:
        child_record = unit['child']
        row = flow.journal.row('runtime_episodes', child_record['episode_id'])
        saved_request = json.loads(row['request'])
        contexts.append(BindingContext(flow.run_id, row['episode_id'], 'results',
            tuple(tuple(part) for part in json.loads(row['path'])), saved_request['message']['scope'],
            saved_request['message']['episode_assignment'], saved_request))
        returned.append(json.loads(flow.journal.row('runtime_forms', row['episode_id'])['form']))
        index = child_record['units_consumed'] - 1
        outcomes.append(json.loads(flow.journal.row('runtime_actions', row['episode_id'], index)['result']))
    summary = {'label': label, 'program': program, 'mode': request['native_hmmer']['mode'],
        'native_execution': 'fresh tiny selected practical.job.start',
        'decisions': 'scripted; production execution/results credit and terminal estimator',
        'root_projection': 'fixture count of actually received numerical observations; not W05',
        'partial_result_fixture_estimator': incomplete,
        'parent_units': record.units_consumed, 'parent_gains': list(record.controller_state.history),
        'selected_actions': store.db.execute('SELECT count(*) FROM runtime_actions WHERE run_id=?',
                                           (flow.run_id,)).fetchone()[0],
        'controller_observations': store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?',
                                                   (flow.run_id,)).fetchone()[0],
        'scripted_decision_calls': len(provider.calls), 'native_plan': provider.plan,
        'returned_forms': returned, 'results': [{'gains': history(unit['child']),
            'units': unit['child']['units_consumed'],
            'future_expectation': unit['child']['controller_state']['estimate']['expected_next_gain'],
            'original_action': outcome['result']['operation_key'],
            'capture': outcome['result']['capture'], 'prepared': outcome['result']['prepared'],
            'failures': outcome['result']['failures'], 'complete': outcome['result']['complete']}
            for unit, outcome in zip(archive['units'][1:], outcomes)]}
    (tmp_path / 'CASE.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    return SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, record=record,
        archive=archive, contexts=contexts, returned=returned, outcomes=outcomes, scope=scope,
        plan=provider.plan, form=form, request=request, workspace=workspace, tmp_path=tmp_path)


def history(record):
    return [unit['controller_step']['marginal_credit'] for unit in record['units']]


@pytest.mark.parametrize('label', [label for label in LABELS if 'empty' not in label])
def test_selected_native_results_reach_requested_parent_form_and_real_credit(tmp_path, monkeypatch, label):
    case = run_case(tmp_path, label)
    try:
        body = case.outcomes[0]['result']
        assert case.outcomes[0]['status'] == 'completed', case.outcomes[0]
        assert body['complete'], body['failures']
        assert case.returned[0]['completed']
        rows = case.returned[0]['rows']
        assert rows and any(row['status'] == 'published' for row in rows)
        case.owner.validate_report(case.contexts[0], case.returned[0], case.form)
        parent_known = set(case.flow.receipts.known(case.record.episode_id))
        assert {row['observation_ref'] for row in rows if row['observation_ref']} <= parent_known
        assert case.owner.received_form_references(case.contexts[0], case.returned[0], case.form, 'verify')
        count = len(body['record_refs'])
        child_record = case.archive['units'][1]['child']
        assert child_record['units_consumed'] == 1
        assert history(child_record) == [2 * count]
        assert child_record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert case.record.units_consumed == 2
        assert case.record.controller_state.history == (0, len({row['observation_ref'] for row in rows if row['observation_ref']}))
        actions = case.store.db.execute('SELECT count(*) FROM runtime_actions WHERE run_id=?', (case.flow.run_id,)).fetchone()[0]
        observations = case.store.db.execute('SELECT count(*) FROM runtime_observations WHERE run_id=?', (case.flow.run_id,)).fetchone()[0]
        assert actions == observations == len(case.provider.calls) == 5
        source = case.store.get(body['source_ref'])
        captured = body['capture']
        manifest = json.loads(case.store.get_artifact(captured['bundle_artifact_ref']))
        assert manifest['requested_job'] == case.request
        assert manifest['identity'] == case.plan['identity']
        assert case.plan['policy'] == POLICY
        native_handle = native.NativeJobHandle(Path(case.plan['identity']['execution_id'])).read()
        assert native_handle['metadata']['policy'] == POLICY
        assert native_handle['metadata']['verified_cgroup']['memory_max'] == POLICY['memory_bytes']
        assert native_handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
        assert 'runtime_max' not in native_handle['metadata']['verified_cgroup']
        assert len(captured['artifacts']) == len(manifest['inputs']) + len(manifest['artifacts'])
        assert {row['artifact_ref'] for row in captured['artifacts']} <= set(source['auxiliary_artifact_refs'])
        prepared = body['prepared']
        sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
        scores = json.loads(case.store.get_artifact(prepared['scores_artifact_ref']))
        family = family_for_program(manifest['program'])
        assert len(sheet[COLLECTIONS[family]]) >= len(rows)
        by_key = {row['record_key']: row for row in scores[COLLECTIONS[family]]}
        for row in rows:
            assert {v['name'] for v in row['measurements'] + row['unavailable']} == set(METRICS[family])
            assert {v['name']: v['value'] for v in row['measurements']} == {
                v['name']: by_key[row['record_key']][v['name']] for v in row['measurements']}
        assert len(list(case.workspace.rglob('hmmer-plan.json'))) == 1
        compare_b003(label, family, scores[COLLECTIONS[family]])
        from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
        from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores
        from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores
        calculator = {'protein_domain': calculate_hmmer_search_scores,
            'nucleotide_locus': calculate_nhmmer_scores,
            'alignment_sequence': calculate_hmmalign_scores}[family]
        before = deepcopy(sheet)
        def prohibited(*args, **kwargs):
            raise AssertionError('saved-sheet recalculation attempted acquisition/execution')
        with monkeypatch.context() as isolated:
            isolated.setattr(socket, 'socket', prohibited)
            isolated.setattr(subprocess, 'Popen', prohibited)
            isolated.setattr('builtins.open', prohibited)
            assert calculator(sheet, parameters={}) == scores
            assert sheet == before
        if label == 'nhmmer_profile_ordinary':
            reverse = next(row for row in rows if row['strand'] == 'minus')
            observation = case.store.get(reverse['observation_ref'])
            assert observation['operand_intervals'][0]['start'] == 10
            assert observation['operand_intervals'][0]['end'] == 110
        if label == 'hmmalign_align_trim':
            trimmed = next(row for row in rows if next(v['value'] for v in row['measurements']
                if v['name'] == 'original_length') == 26)
            assert {v['name']: v['value'] for v in trimmed['measurements']} == {
                'original_length': 26, 'model_length': 20, 'match_state_residues': 20,
                'trimmed_residues': 6, 'model_occupancy': 1, 'sequence_match_coverage': 20 / 26}
            assert case.store.get(trimmed['observation_ref'])['operand_intervals'][0]['start'] == 3
    finally:
        case.store.close()


def compare_b003(label, family, actual):
    if label.startswith(('hmmscan_', 'hmmsearch_', 'jackhmmer_')):
        path = ROOT / 'verification/tool_graders_hmmer_search_2026-10-24' / (label.split('_')[0] + '.scores.json')
    elif label.startswith('hmmalign_'):
        mode = label.removeprefix('hmmalign_align_')
        path = ROOT / 'verification/tool_graders_hmmalign_2026-10-24/saved' / mode / 'scores.json'
    else:
        name = {'nhmmer_sequence_ordinary': 'nhmmer_sequence', 'nhmmer_profile_ordinary': 'nhmmer_profile',
            'nhmmer_alignment_ordinary': 'nhmmer_msa', 'nhmmer_profile_watson': 'nhmmer_z_watson',
            'nhmmscan_search_ordinary': 'nhmmscan'}[label]
        path = ROOT / 'verification/tool_graders_nhmmer_2026-10-24' / name / 'scores.json'
    expected = json.loads(path.read_text())[COLLECTIONS[family]]
    def association(row):
        fields = ('query_name', 'target_name', 'name', 'iteration', 'strand', 'identities', 'intervals', 'coordinates', 'origin')
        return {field: row.get(field) for field in fields}
    for current in actual:
        # B003 hmmscan used four queries; the original 064 producer selected
        # only test1. Match actual names/axes/intervals, never independently
        # sorted rows or a shared taxon. Artifact identities necessarily differ.
        matches = [row for row in expected if association(row) == association(current)]
        assert len(matches) == 1, (label, association(current))
        retained, = matches
        for field in ('query_name', 'target_name', 'name', 'iteration', 'strand', 'identities'):
            assert current.get(field) == retained.get(field)
        for metric in NATIVE_HMMER_METRICS[family]:
            if retained.get(metric) is not None:
                assert current.get(metric) == pytest.approx(retained[metric]), (label, metric, current, retained)


def test_original_completed_result_replay_does_not_read_files_grade_or_launch(tmp_path, monkeypatch):
    case = run_case(tmp_path, 'hmmscan_search_ordinary')
    try:
        original = deepcopy(case.outcomes[0])
        context = case.contexts[0]
        body = original['result']
        before = [tuple(row) for row in case.store.db.execute('SELECT * FROM runtime_observations')]
        shutil.rmtree(case.plan['attempt_directory'])
        def prohibited(*args, **kwargs):
            raise AssertionError('completed action replay acquired or executed work')
        with monkeypatch.context() as isolated:
            isolated.setattr('gene_annotation_episode.native_hmmer_results.capture_local_bundle', prohibited)
            isolated.setattr('gene_annotation_episode.native_hmmer_results.prepare_native_hmmer_grading', prohibited)
            isolated.setattr(case.owner.job_progress_provider.targets, 'observe_target', prohibited)
            isolated.setattr(subprocess, 'Popen', prohibited)
            replay = asyncio.run(case.owner.execute(context, 'execution.results.collect', {}, body['operation_key']))
            # Workflow adds its pending-work snapshot after the binding returns.
            # The original operation receipt and all binding-owned outputs must
            # replay exactly; this direct binding call adds no runtime snapshot.
            assert replay == {key: value for key, value in original.items()
                              if key != 'pending_work_after_action'}
            assert case.owner.native_hmmer_results.read_result(body['source_ref'], case.scope) == body
            assert case.owner.verify_completion(context, case.owner.completion_for_action(context, body['operation_key']))
        assert [tuple(row) for row in case.store.db.execute('SELECT * FROM runtime_observations')] == before
    finally:
        case.store.close()


def test_row_and_source_identity_stay_fixed_across_metrics_and_new_pages(tmp_path):
    one = selector('hmmsearch', rows={'offset': 0, 'limit': 1}, metrics=['paired_positions'])
    def again(received):
        return selector('hmmsearch', rows={'record_keys': [received['rows'][0]['record_key']]},
                        metrics=['native_domain_score_bits'])
    sibling = selector('hmmsearch', rows={'offset': 1, 'limit': 1}, metrics=['paired_positions'])
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', selectors=[one, again, sibling])
    try:
        first, duplicate, second = [result['rows'][0] for result in case.returned]
        assert first['source_ref'] == duplicate['source_ref'] == second['source_ref']
        assert first['record_key'] == duplicate['record_key']
        assert first['observation_ref'] == duplicate['observation_ref'] != second['observation_ref']
        assert first['measurements'] != duplicate['measurements']
        histories = [history(unit['child']) for unit in case.archive['units'][1:]]
        assert histories == [[6], [0], [2]]
        assert case.record.controller_state.history == (0, 1, 0, 1)
        assert case.store.count('observation') == 2
        first_body = case.outcomes[0]['result']
        full_scores = json.loads(case.store.get_artifact(first_body['prepared']['scores_artifact_ref']))
        assert len(full_scores['domains']) > 2
        parent_observations = list(case.flow.receipts.known(case.record.episode_id, record_type='observation'))
        assert len(parent_observations) == 2
        # Three selected collections + resource start, three child deliveries
        # + launch child delivery: exactly nine completed own actions.
        assert case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 9
    finally:
        case.store.close()


def test_status_is_separate_zero_gain_action_then_completion_without_extra_turn(tmp_path):
    case = run_case(tmp_path, 'hmmscan_search_ordinary', status_first=True)
    try:
        child_record = case.archive['units'][1]['child']
        assert child_record['units_consumed'] == 2
        assert history(child_record) == [0, 6]
        assert child_record['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        first = json.loads(case.flow.journal.row('runtime_actions', case.contexts[0].episode_id, 0)['result'])
        assert first['result']['capture'] is None and first['result']['prepared'] is None
        assert first['record_refs'] == [] and first['result']['rows'] == []
        assert len(case.provider.calls) == 6
        assert case.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 6
    finally:
        case.store.close()


def test_completion_only_form_does_not_deliver_unrequested_numerical_rows(tmp_path):
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', include_rows=False, include_refs=False)
    try:
        assert case.returned[0] == {'completed': True}
        assert case.store.count('observation') == 4
        assert list(case.flow.receipts.known(case.record.episode_id, record_type='observation')) == []
        assert case.record.controller_state.history == (0, 0)
        facts = case.owner.facts(case.contexts[0], {})
        assert facts['execution_hmmer_domain_rows'] == []
    finally:
        case.store.close()


def test_zero_hit_completed_search_returns_empty_rows_not_missing_measurements(tmp_path):
    case = run_case(tmp_path, 'hmmsearch_search_empty', include_refs=True)
    try:
        returned = case.returned[0]
        assert returned['completed'] and returned['rows'] == []
        assert len(returned['references']) == 1
        assert case.store.count('observation') == 0
        assert history(case.archive['units'][1]['child']) == [2]
        assert case.archive['units'][1]['child']['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
    finally:
        case.store.close()


def test_unbound_profile_query_is_explicit_without_invented_subject(tmp_path):
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', bind=False)
    try:
        rows = case.returned[0]['rows']
        assert rows and all(row['status'] == 'unbound' and row['subject_ref'] is None
                            and row['observation_ref'] is None for row in rows)
        assert all(row['measurements'] for row in rows)
        assert case.store.count('observation') == 0
        assert case.returned[0]['completed']
        assert history(case.archive['units'][1]['child']) == [2]
    finally:
        case.store.close()


def test_wrong_biological_binding_is_invalid_and_does_not_close_endpoint(tmp_path):
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', wrong_sequence=True, incomplete=True)
    try:
        rows = case.returned[0]['rows']
        assert any(row['status'] == 'published' for row in rows)
        wrong = rows[0]
        assert wrong['status'] == 'invalid' and wrong['observation_ref'] is None
        assert not case.returned[0]['completed']
        assert any(failure['code'] == 'native_hmmer_subject_sequence_mismatch'
                   for failure in case.outcomes[0]['result']['failures'])
        assert case.owner.completion_for_action(case.contexts[0], case.outcomes[0]['result']['operation_key']) is None
    finally:
        case.store.close()


def test_missing_exact_requested_row_preserves_failure_and_prevents_completion(tmp_path):
    selection = selector('hmmsearch', rows={'record_keys': ['unavailable-native-row']})
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', selectors=[selection], incomplete=True, include_refs=True)
    try:
        assert case.returned[0]['rows'] == [] and not case.returned[0]['completed']
        body = case.outcomes[0]['result']
        assert {'stage': 'selection', 'code': 'native_hmmer_selected_record_missing',
                'record_key': 'unavailable-native-row'} in body['failures']
        assert case.store.count('observation') == 0
        assert body['prepared']['sheet_artifact_ref']
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
    finally:
        case.store.close()


def test_changed_native_bytes_preserve_valid_partial_custody_without_original_row_reassignment(tmp_path):
    def corrupt(store, plan):
        root = Path(plan['attempt_directory'])
        bundle = json.loads((root / 'bundle.json').read_text())
        path = root / next(row['relative_path'] for row in bundle['artifacts'] if row['role'] == 'stdout')
        path.write_bytes(b'changed and truncated original native output\n')
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', before_collection=corrupt,
                    incomplete=True, include_refs=True)
    try:
        body = case.outcomes[0]['result']
        assert not body['complete'] and not body['capture']['complete']
        assert any(row['role'] == 'stdout' for row in body['capture']['invalid_artifacts'])
        assert any(row['role'] == 'domtblout' for row in body['capture']['artifacts'])
        assert any('digest_mismatch' in failure['code'] for failure in body['failures'])
        assert body['prepared']['sheet_artifact_ref'] and body['source_ref']
        # Native tables are still usable partial measurements; missing stdout
        # alignment is unavailable instead of a fabricated zero count.
        for row in case.returned[0]['rows']:
            assert 'paired_positions' not in {v['name'] for v in row['measurements']}
            assert 'paired_positions' in {v['name'] for v in row['unavailable']}
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
    finally:
        case.store.close()


def test_original_action_receipt_and_requested_return_are_qualified(tmp_path):
    selection = selector('hmmsearch', rows={'offset': 0, 'limit': 1})
    case = run_case(tmp_path, 'hmmsearch_search_ordinary', selectors=[selection])
    try:
        context = case.contexts[0]
        body = case.outcomes[0]['result']
        results = case.owner.native_hmmer_results
        source_ref = body['source_ref']
        source = case.store.get(source_ref)
        payload = {key: deepcopy(value) for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
        payload['accession'] += '-unrelated'
        unrelated = case.store.put('source', payload, origin='tool')['id']
        assert not case.owner.resolve(context, unrelated, 'execution_result')
        with pytest.raises(ValueError, match='not_a_native_hmmer_acquired_result'):
            results.read_result(unrelated, case.scope)
        assert not case.owner.resolve(context, case.scope['subject_refs'][0], 'execution_result')
        assert case.owner.resolve(context, body['rows'][0]['record_key'], 'native_hmmer_row')
        sheet = json.loads(case.store.get_artifact(body['prepared']['sheet_artifact_ref']))
        unselected = sheet['domains'][1]['record_key']
        assert not case.owner.resolve(context, unselected, 'native_hmmer_row')
        changed = deepcopy(case.returned[0])
        changed['rows'][0]['measurements'][0]['value'] += 1
        with pytest.raises(ValueError, match='recorded_facts'):
            case.owner.validate_report(context, changed, case.form)
        changed = deepcopy(case.returned[0])
        changed['rows'][0]['source_ref'] = unrelated
        with pytest.raises(ValueError):
            case.owner.validate_report(context, changed, case.form)

        path = results._action_directory(context, body['operation_key']) / 'receipt.json'
        original = path.read_bytes()
        for field, replacement in [('run_id', 'wrong-run'), ('operation_key', body['operation_key'] + 'x'),
                                   ('complete', False), ('rows', []), ('record_refs', [unrelated])]:
            damaged = deepcopy(body)
            damaged[field] = replacement
            path.write_text(canonical(damaged))
            with pytest.raises(ValueError):
                results.read_result(source_ref, case.scope)
            assert not case.owner.resolve(context, source_ref, 'execution_result')
            path.write_bytes(original)
        assert results.read_result(source_ref, case.scope) == body
        directory = path.parent
        for journal, field, replacement, message in [
                (directory / 'capture/capture.json', 'complete', False, 'capture_receipt_conflict'),
                (directory / 'grading/native-hmmer-grading/prepared.json', 'numerical_complete', False,
                 'prepared_receipt_conflict'),
                (directory / 'publication.json', 'rows', [], 'publication_receipt_conflict')]:
            saved = journal.read_bytes()
            damaged = json.loads(saved)
            damaged[field] = replacement
            try:
                journal.write_text(canonical(damaged))
                # The immutable byte seal may reject the mutation before the
                # cross-journal semantic equality check is reached.
                with pytest.raises(ValueError, match='practical_record_bytes_changed|' + message):
                    results.read_result(source_ref, case.scope)
                assert not case.owner.resolve(context, source_ref, 'execution_result')
            finally:
                journal.write_bytes(saved)
        assert results.read_result(source_ref, case.scope) == body
        selected_row = case.flow.journal.row('runtime_actions', context.episode_id, 0)
        original_action = selected_row['action']
        altered = json.loads(original_action)
        altered['tool'] = 'execution.results.status'
        case.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (canonical(altered), case.flow.run_id, context.episode_id))
        with pytest.raises(ValueError, match='selected_action_conflict'):
            results.read_result(source_ref, case.scope)
        case.store.db.execute('UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0',
            (original_action, case.flow.run_id, context.episode_id))
        assert results.read_result(source_ref, case.scope) == body
    finally:
        case.store.close()
