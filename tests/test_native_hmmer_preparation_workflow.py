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
from gene_annotation_episode.hmmer_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.native_hmmer_preparation_contracts import requested_job_from_hmmer_preparation
from gene_annotation_episode.native_hmmer_preparation_local import local_hmmer_preparation_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_native_hmmer_preparation_driver import POLICY
from test_native_hmmer_preparation_contracts import CASES, EVIDENCE, NATIVE, job as fixture_job, operand
from gene_annotation_episode.native_hmmer_preparation_worker import recalculate_hmmer_preparation
from gene_annotation_episode.hmmer_statistics_calculations import native_hmmstat_parameters
from gene_annotation_episode.native_hmmer_preparation_contracts import compile_native_hmmer_preparation_job
import hashlib
import math
import struct


RUN_ID = 'hmmer-preparation-workflow277'
PREFIX = 'execution_hmmer_preparation_'


def native_job(program='hmmemit', mode='consensus_simple'):
    """Explicit tiny native selections, including requested diagnostic outputs."""
    job = fixture_job(program, mode)
    if (program, mode) == ('alimask', 'mask_alignment'):
        job['options'][-1] = '2-4,4-6'
    if program == 'hmmbuild':
        job['outputs'] += [
            {'role': 'resaved_alignment', 'format': 'stockholm', 'relative_path': 'outputs/resaved'},
            {'role': 'summary', 'format': 'hmmbuild_summary', 'relative_path': 'outputs/summary'}]
    if program == 'hmmstat':
        job['operands'] = [operand('models', NATIVE / 'hmmbuild_dna/profile.hmm', 'hmmer3_ascii')]
        job['grading_parameters'] = native_hmmstat_parameters('3.4', 'DNA')
    if program == 'hmmsim':
        job['options'] += ['--fs', '--tmin', '.1', '--tmax', '.1', '--pthresh', '.1']
        job['outputs'] += [{'role': role, 'format': fmt, 'relative_path': 'outputs/' + role}
            for role, fmt in [('filter', 'hmmsim_filter'), ('survival', 'hmmsim_xy'),
                ('expected_counts', 'hmmsim_xy')]]
        if mode == 'viterbi':
            job['options'].append('-a')
            job['outputs'].append({'role': 'alignments', 'format': 'hmmsim_alignments',
                'relative_path': 'outputs/alignments'})
    if program == 'hmmerfm-exactmatch':
        job['grading_parameters'] = {'exhaustive_literal_check': True}
    return job


def choice_for(job):
    """Each mode requests its own numerical meaning, without a universal score."""
    program, mode = job['program'], job['mode']
    if program == 'hmmemit':
        quantities = ['length', 'canonical_residue_count', 'ambiguous_residue_count',
            'captured_sample_count', 'expected_output_count', 'total_length', 'mean_length']
        if mode.startswith('consensus_'):
            quantities += ['mismatch_count', 'certain_mismatch_count', 'ambiguous_position_count']
        if mode == 'sample_core_aligned':
            quantities += ['alignment_width', 'rf_match_column_count', 'captured_row_count']
        checks = ['sample_population_count', 'consensus_agreement']
    elif program == 'hmmbuild':
        quantities = ['components.' + name for name in ['input_sequence_count', 'input_column_count',
            'model_length', 'model_alignment_fraction', 'effective_input_sequence_ratio',
            'resaved_sequence_count', 'resaved_column_count', 'native_relative_entropy']]
        checks = ['summary_counts', 'sequence_membership', 'model_map']
    elif program == 'alimask':
        quantities = ['components.' + name for name in ['input_sequence_count', 'input_column_count',
            'rf_consensus_count', 'requested_interval_count', 'native_mapping_row_count',
            'requested_union_count']]
        if mode.startswith('mask_'):
            quantities += ['components.actual_masked_count', 'components.masked_fraction']
        checks = ['requested_ranges', 'native_mapping', 'mask_annotation']
    elif program == 'hmmconvert':
        quantities = ['decoded_model_count', 'model_artifact_bytes', 'source_length', 'output_length',
            'compared_cell_count', 'max_absolute_probability_difference']
        checks = ['conversion_stdout_equal', 'model_probability_equivalence', 'model_population_complete']
    elif program == 'hmmfetch':
        quantities = (['native_model_count', 'native_primary_name_count', 'native_accession_count',
            'decoded_input_model_count', 'size_bytes'] if mode == 'index' else
            ['requested_key_count', 'resolved_key_count', 'missing_key_count', 'selected_source_occurrence_count',
             'returned_model_occurrence_count', 'duplicate_representation_count', 'compared_cell_count'])
        checks = ['all_requested_keys_returned', 'fetch_output_population', 'binary_internal_content']
    elif program == 'hmmpress':
        quantities = ['native_model_count', 'decoded_input_model_count', 'native_primary_name_count',
            'native_accession_count', 'bundle_byte_sum', 'member_count']
        checks = ['required_member_present', 'supplied_artifact_binding', 'binary_internal_content']
    elif program == 'hmmsim':
        quantities = ['components.' + name for name in ['observed_count', 'declared_population', 'mean',
            'sample_variance', 'x10', 'mu', 'lambda', 'E10', 'tail_count', 'tail_mass',
            'count', 'fraction', 'pmu']]
        if mode == 'viterbi':
            quantities += ['components.alignment_mean', 'components.alignment_sample_sd']
        checks = ['native_filter_count', 'native_filter_fraction', 'native_rounding.E10']
    elif program == 'hmmstat':
        quantities = ['components.' + name for name in ['sequence_count', 'mean_match_entropy',
            'mean_match_relative_entropy', 'mean_match_information', 'position_relative_entropy',
            'composition_relative_entropy', 'occupancy_sum']]
        checks = ['native_rounding_agreement']
    else:
        quantities = ['components.' + name for name in ['source_occurrence_count', 'source_symbol_total',
            'actual_database_bytes', 'indexed_symbols', 'ambiguity_fraction']]
        if program == 'hmmerfm-exactmatch':
            quantities += ['components.' + name for name in ['query_occurrence_count', 'native_Q', 'native_H',
                'native_R', 'emitted_location_count', 'valid_location_count', 'invalid_location_count',
                'valid_location_fraction', 'expected_literal_location_count', 'missing_literal_location_count',
                'extra_literal_location_count']]
        checks = ['source_custody', 'source_symbols_outside_ambiguities', 'exhaustive_literal_agreement']
    return {'version': 'native_hmmer_preparation_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'projection': {'collection': 'calculations', 'rows': {'offset': 0, 'limit': 100},
            'quantities': quantities, 'checks': checks},
        'artifacts': [{'direction': 'output', 'role': row['role'], 'ordinal': 0} for row in job['outputs']]}


def selected(name):
    return {'selection': {'kind': 'tool', 'tool': name, 'arguments': {}}, 'report_update': {}}


def child(role, assignment, scope, form):
    return {'selection': {'kind': 'episode_child', 'role': role,
        'goal': 'Prepare the selected profile-model inputs and return the requested measurements and artifacts.',
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



def run_case(tmp_path, program='hmmemit', mode='consensus_simple', *, selectors=None, form_options=None,
             partial=False, status_first=False, before_collection=None, job_override=None, expected_returncode=0,
             job_factory=None):
    store = Store(tmp_path / 'state')
    supplied = tmp_path / 'supplied-sequence.fa'
    supplied.write_text('>internal_sample\nGCGCAAAAGCGC\n')
    store.create_problem(supplied, molecule='dna', format='fasta')
    scope = store.validate_scope()
    if job_factory is None:
        job = deepcopy(job_override) if job_override is not None else native_job(program, mode)
        initial_refs = []
    else:
        if job_override is not None:
            raise ValueError('job_factory_and_override_are_exclusive')
        job, initial_refs = job_factory(store)
    request = requested_job_from_hmmer_preparation(job)
    selectors = selectors or [choice_for(job)]
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    resources = {'here': {'kind': 'local', 'workspace': str(workspace), 'policy': POLICY.to_dict(),
        'native_hmmer_preparation': [{key: job[key] for key in ('program', 'mode', 'software')}]}}
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
                assert native_result.returncode == expected_returncode
                self.plan = local_hmmer_preparation_plan(assignment, self.target['execution_id'])
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
        episode_record_receipts=True, initial_known_record_refs=initial_refs, episode_service_factory=factory,
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
    assert len(list(case.workspace.rglob('hmmer-preparation-plan.json'))) == 1
    for context, form, schema in zip(case.contexts, case.returned, case.forms):
        case.owner.validate_report(context, form, schema)
    parent = case.owner.native_hmmer_preparation_returns.context(case.record.episode_id)
    received = case.owner.native_hmmer_preparation_returns.received_context(parent)
    assert all(row['fact_source'].startswith(PREFIX) for row in received)
    return parent, received


def read_retained(case):
    body = case.outcomes[0]['result']
    prepared = body['prepared']
    assert prepared is not None and prepared['graded'], body['failures']
    bundle = json.loads(case.store.get_artifact(prepared['bundle_artifact_ref']))
    grading = json.loads(case.store.get_artifact(prepared['grading_artifact_ref']))
    sheet = json.loads(case.store.get_artifact(prepared['sheet_artifact_ref']))
    calculations = json.loads(case.store.get_artifact(prepared['calculations_artifact_ref']))
    assert grading['sheet'] == sheet and grading['calculations'] == calculations
    assert grading['operation'] == sheet['operation'] == calculations['operation'] == bundle['operation']
    return body, bundle, sheet, calculations


def present(cell, expected, *, unit=None, tolerance=1e-12):
    assert cell['state'] == 'present' and type(cell['value']) in (int, float), cell
    assert cell['value'] == pytest.approx(expected, abs=tolerance), cell
    if unit is not None:
        assert cell['unit'] == unit, cell
    assert cell['inputs'], cell


def kind_row(calculations, kind):
    row, = [row for row in calculations['rows'] if row.get('kind') == kind]
    return row


def assert_native_custody(case, bundle):
    assert bundle['requested_job'] == case.request == case.plan['requested_job']
    assert (bundle['program'], bundle['mode']) == (case.job['program'], case.job['mode'])
    assert bundle['identity'] == case.plan['identity']
    assert bundle['returncode'] == 0 and bundle['failures'] == []
    assert case.plan['policy'] == POLICY.to_dict()
    root = Path(case.plan['attempt_directory'])
    inputs = {}
    for row, original in zip(bundle['inputs'], case.job['operands'], strict=True):
        inputs.setdefault(row['role'], []).append(str(root / row['relative_path']))
        raw = (root / row['relative_path']).read_bytes()
        assert raw == Path(original['path']).read_bytes()
        assert len(raw) == row['expected_size_bytes'] == row['staged_size_bytes'] == row['final_size_bytes']
        assert hashlib.sha256(raw).hexdigest() == row['expected_sha256'] == row['staged_sha256'] == row['final_sha256']
    compiled = compile_native_hmmer_preparation_job(case.job, input_paths=inputs, output_directory=str(root))
    assert bundle['realized_argv'] == compiled['argv']
    assert bundle['operation'] == compiled['operation']
    assert bundle['realized_argv'][1:1 + len(case.job['options'])] == case.job['options']
    assert bundle['software']['actual_sha256'] == case.job['software']['sha256']
    for row in case.outcomes[0]['result']['prepared']['occurrences']:
        raw = case.store.get_artifact(row['artifact_ref'])
        assert raw == (root / row['relative_path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        assert len(raw) == row['size_bytes'] and row['completeness'] == 'complete'
    handle = native.NativeJobHandle(Path(bundle['identity']['execution_id'])).read()
    assert handle['metadata']['policy'] == POLICY.to_dict()
    assert handle['metadata']['verified_cgroup']['memory_max'] == 20 * 1024**3
    assert handle['metadata']['verified_cgroup']['memory_swap_max'] == 0
    assert handle['metadata']['verified_cgroup']['runtime_max'] == 'infinity'


def assert_projected_values(form, selector, calculations):
    saved = {}
    for row in calculations['rows']:
        key = row.get('record_key', row.get('row_key'))
        if key is None and 'model_record_key' in row:
            key = row['model_record_key'] + '#' + row['kind']
        if key is None and row['kind'] in {'database_summary', 'exactmatch_summary'}:
            key = 'aggregate/' + row['kind']
        assert key is not None and key not in saved
        saved[key] = row
    for row in form['rows']:
        assert [q['path'] for q in row['quantities']] == list(selector['projection']['quantities'])
        assert {check['name'] for check in row['checks']} == set(selector['projection']['checks'])
        for quantity in row['quantities']:
            value = saved[row['record_key']]
            for name in quantity['path'].split('.'):
                value = value.get(name) if isinstance(value, dict) else None
            if value is None:
                assert quantity['value'] is None and quantity['state'] == 'missing'
            else:
                assert {key: quantity[key] for key in ('value', 'state', 'unit')} == {
                    key: value[key] for key in ('value', 'state', 'unit')}


def requested_input_dependencies(job):
    # These selected S1 quantities/checks depend on the retained score vectors,
    # trace lengths and native summary/filter files. They do not request model
    # body quantities; a model association alone grants no artifact disclosure.
    if job['program'] == 'hmmsim':
        return set()
    return {('input', row['role'], row['ordinal']) for row in job['operands']}


def assert_mode_numbers(job, bundle, sheet, calculations):
    """Independent arithmetic and retained native facts, never expected=calculator."""
    program, mode = job['program'], job['mode']
    rows = calculations['rows']
    if program == 'hmmemit':
        generated = [r for r in rows if r['kind'] == 'generated_record']
        lengths = [len(r['sequence'].replace('-', '').replace('.', '')) for r in generated]
        expected = [15, 72, 39] if mode == 'sample_profile' else [12] * (3 if mode.startswith('sample_') else 1)
        assert lengths == expected
        for row, length in zip(generated, lengths):
            assert row['basis'] == ('model_derived' if mode.startswith('consensus') else 'generated')
            present(row['length'], length, unit='residue_count')
        model = kind_row(calculations, 'model')
        present(model['input_model_length'], 12)
        present(model['captured_sample_count'], len(expected))
        present(model['total_length'], sum(expected))
        present(model['mean_length'], sum(expected) / len(expected))
        if mode.startswith('consensus'):
            assert generated[0]['sequence'] == ('ACDEFGHIKLMN' if mode == 'consensus_simple' else 'ACDExGHIKLMN')
            consensus = kind_row(calculations, 'consensus')
            present(consensus['mismatch_count'], 0)
            present(generated[0]['ambiguous_residue_count'], int(mode == 'consensus_thresholded'))
        elif mode == 'sample_core_aligned':
            alignment = kind_row(calculations, 'alignment')
            present(alignment['alignment_width'], 12)
            present(alignment['captured_row_count'], 3)
    elif program == 'hmmbuild':
        row = kind_row(calculations, 'build')
        c = row['components']
        n, columns = (1, 12) if mode == 'build_single_sequence_matrix' else (3, 14)
        present(c['input_sequence_count'], n)
        present(c['input_column_count'], columns)
        present(c['model_length'], 12)
        present(c['model_alignment_fraction'], 12 / columns)
        present(c['effective_input_sequence_ratio'], 1)
        output, = [r for r in bundle['artifacts'] if r['role'] == 'resaved_alignment']
        if mode == 'build_single_sequence_matrix':
            assert output['size_bytes'] == 0
            assert c['resaved_column_count']['value'] is None
        else:
            present(c['resaved_sequence_count'], 3)
            present(c['resaved_column_count'], 12)
    elif program == 'alimask':
        row, = rows
        c = row['components']
        present(c['input_sequence_count'], 3)
        present(c['input_column_count'], 14)
        present(c['rf_consensus_count'], 12)
        if mode.startswith('mask_'):
            count = 5 if mode == 'mask_alignment' else 3
            present(c['actual_masked_count'], count)
            present(c['requested_union_count'], count)
            present(c['masked_fraction'], count / 14)
            assert sum(char == 'm' for char in row['output_mm']) == count
        else:
            present(c['native_mapping_row_count'], 1)
            present(c['mapped_model_position_count'], 12)
            assert c['requested_union_count']['value'] is None
            assert row['native_mappings']
    elif program in {'hmmconvert', 'hmmfetch', 'hmmpress'}:
        inputs, = [r for r in rows if r['kind'] == 'population' and r['direction'] == 'input']
        outputs, = [r for r in rows if r['kind'] == 'population' and r['direction'] == 'output']
        present(inputs['decoded_model_count'], 1)
        if program == 'hmmconvert':
            aliases = [r for r in bundle['artifacts'] if r['role'] in {'stdout', 'converted_models'}]
            assert len(aliases) == 2 and aliases[0]['sha256'] == aliases[1]['sha256']
            present(outputs['decoded_model_count'], 1)
            compare = kind_row(calculations, 'model_comparison')
            present(compare['source_length'], 12)
            present(compare['output_length'], 12)
            if mode == 'ascii':
                present(compare['compared_cell_count'], 611)
                present(compare['max_absolute_probability_difference'], 0)
            elif mode == 'binary':
                present(compare['compared_cell_count'], 611)
                difference = compare['max_absolute_probability_difference']
                assert difference['state'] == 'present'
                assert 0 <= difference['value'] <= 1e-4
            else:
                assert mode == 'legacy_hmmer2'
                assert compare['output_record_key'] is not None
                assert compare['compared_cell_count']['value'] > 0
                assert any(check['code'] == 'model_probability_equivalence'
                    and check['state'] != 'pass' for check in calculations['checks'])
        elif program == 'hmmfetch' and mode != 'index':
            c = kind_row(calculations, 'key_population')
            present(c['requested_key_count'], 2 if mode == 'key_file' else 1)
            present(c['resolved_key_count'], 2 if mode == 'key_file' else 1)
            present(c['selected_source_occurrence_count'], 1)
            present(c['returned_model_occurrence_count'], 1)
            present(c['duplicate_representation_count'], 0)
            present(c['missing_key_count'], 0)
        else:
            summary = kind_row(calculations, 'index_summary')
            for field in ['native_model_count', 'decoded_input_model_count', 'native_primary_name_count', 'native_accession_count']:
                present(summary[field], 1)
            # Easel SSI allocates its filename field using the full invocation
            # path length, even though it writes only the basename (esl_ssi.c,
            # esl_newssi_AddFile/Write). The original relative-path fixture is
            # 165 bytes; this private absolute path changes only that padding.
            ssi_bytes = 165 + len(bundle['realized_argv'][-1].encode()) - len(b'models.hmm')
            if program == 'hmmpress':
                members = [r for r in bundle['artifacts'] if r['role'] in {
                    'binary_models', 'ssi_index', 'msv_profiles', 'remaining_profiles'}]
                sizes = sorted(r['size_bytes'] for r in members)
                assert sizes == sorted([2725, ssi_bytes, 9918, 3216])
                press = kind_row(calculations, 'bundle')
                present(press['bundle_byte_sum'], 2725 + ssi_bytes + 9918 + 3216, unit='byte')
                present(press['member_count'], 4)
            else:
                ssi, = [r for r in bundle['artifacts'] if r['role'] == 'ssi']
                assert ssi['size_bytes'] == ssi_bytes
    elif program == 'hmmstat':
        c = rows[0]['components']
        assert calculations['parameters']['background'] == native_hmmstat_parameters('3.4', 'DNA')['background']
        for name, value in [('mean_match_entropy', .9925134248800135),
                ('mean_match_information', 1.0074865751199864),
                ('mean_match_relative_entropy', 1.0074921672642938),
                ('position_relative_entropy', .8906422345697793),
                ('composition_relative_entropy', .006355823477963574)]:
            present(c[name], value)
        # Direct independent KL from retained ASCII costs and supplied q=.25.
        model = Path(job['operands'][0]['path']).read_text().splitlines()
        costs = [list(map(float, line.split()[1:5])) for line in model
            if line.split() and line.split()[0].isdigit()]
        manual = math.fsum(math.fsum(math.exp(-x) * math.log2(math.exp(-x) / .25)
            for x in values) for values in costs) / len(costs)
        present(c['mean_match_relative_entropy'], manual)
    elif program == 'hmmsim':
        vector, = [r['payload'] for r in sheet['native_rows'] if r['kind'] == 'scores']
        data = bytes.fromhex(vector['original_bytes_hex'])
        values = struct.unpack('<1000d', data)
        assert len(data) == 8000 and list(values) == vector['values']
        c = kind_row(calculations, 'score_statistics')['components']
        mean = math.fsum(values) / 1000
        present(c['observed_count'], 1000)
        present(c['mean'], mean, unit='bit')
        present(c['sample_variance'], math.fsum((v - mean)**2 for v in values) / 999)
        present(c['x10'], sorted(values, reverse=True)[9])
        if mode == 'viterbi':
            present(c['mean'], -5.619071923450204)
            present(c['x10'], -.6476082390605439)
            fit = next(r for r in rows if r['kind'] == 'fit' and
                abs(r['components']['lambda']['value'] - .7137499186051701) < 1e-10)
            present(fit['components']['mu'], -6.414576359999045)
            present(fit['components']['lambda'], .7137499186051701)
            # The independent fit stops at a declared 1e-10 residual; its E10
            # agrees with the reference fit to better than 1e-9 sequences.
            present(fit['components']['E10'], 16.174564750739254, tolerance=1e-9)
            independent_e10 = 1000 * -math.expm1(-math.exp(-fit['components']['lambda']['value'] *
                (c['x10']['value'] - fit['components']['mu']['value'])))
            present(fit['components']['E10'], independent_e10)
            filtered = kind_row(calculations, 'native_filter')['components']
            present(filtered['count'], 368)
            present(filtered['fraction'], 368 / 1000)
            alignment = kind_row(calculations, 'alignment_statistics')['components']
            present(alignment['alignment_mean'], 4.439)
            present(alignment['alignment_sample_sd'], 1.8616510802899517)
        if mode == 'forward':
            filtered, = [r for r in bundle['artifacts'] if r['role'] == 'filter']
            assert filtered['size_bytes'] == 0
            assert not [r for r in sheet['native_rows'] if r['kind'] == 'filter']
            fit = next(r for r in rows if r['kind'] == 'fit' and
                abs(r['components']['lambda']['value'] - .8836442251850544) < 1e-10)
            present(fit['components']['tail_count'], 100)
            present(fit['components']['mu'], 1.2244937724332836)
            present(fit['components']['E10'], 12.511194245467216)
        if mode == 'hybrid':
            summary = kind_row(calculations, 'native_summary')
            assert summary['components']['pmu']['state'] == 'incompatible'
            assert summary['components']['pmu']['value'] is None
    else:
        c = kind_row(calculations, 'database_summary')['components']
        present(c['source_occurrence_count'], 2)
        present(c['source_symbol_total'], 28, unit='source_symbols')
        present(c['actual_database_bytes'], 314, unit='bytes')
        present(c['indexed_symbols'], 28)
        present(c['ambiguity_fraction'], 0)
        if program == 'hmmerfm-exactmatch':
            c = kind_row(calculations, 'exactmatch_summary')['components']
            present(c['query_occurrence_count'], 7)
            present(c['native_Q'], 5)
            present(c['native_R'], 2)
            present(c['native_H'], 17 if mode == 'locations' else 19)
            if mode == 'locations':
                present(c['emitted_location_count'], 17)
                present(c['valid_location_count'], 16)
                present(c['invalid_location_count'], 1)
                present(c['valid_location_fraction'], 16 / 17)
                present(c['expected_literal_location_count'], 17)
            else:
                assert c['valid_location_count']['value'] is None
                assert c['valid_location_count']['state'] == 'missing'


def forbid_work(monkeypatch, *, calculations=False):
    from gene_annotation_episode import native_hmmer_preparation_worker as worker
    def forbidden(*args, **kwargs):
        raise AssertionError('retained-data verification performed native work, acquisition, or parsing')
    for target, name in [(native, 'start_job'), (native, 'status'), (socket, 'socket'),
            (subprocess, 'Popen'), (worker, 'grade_hmmer_preparation')]:
        monkeypatch.setattr(target, name, forbidden)
    for module in (worker.model_data, worker.artifact_data, worker.alignment_data, worker.emission_data,
            worker.simulation_data, worker.statistics_data, worker.fm_data):
        for name, value in vars(module).items():
            if callable(value) and name.startswith(('populate_', 'parse_', 'extract_', 'iter_')):
                monkeypatch.setattr(module, name, forbidden)
    if calculations:
        monkeypatch.setattr(worker, 'recalculate_hmmer_preparation', forbidden)
    return forbidden


@pytest.mark.parametrize('program,mode', CASES, ids=['-'.join(r) for r in CASES])
def test_all_native_modes_through_workflow_and_requested_typed_form(tmp_path, monkeypatch, program, mode):
    assert len(CASES) == len(set(CASES)) == 26
    case = run_case(tmp_path, program, mode)
    try:
        parent, received = assert_accounting(case)
        body, bundle, sheet, calculations = read_retained(case)
        assert body['complete'] and case.returned[0]['completed'], body['failures']
        assert_native_custody(case, bundle)
        assert_projected_values(case.returned[0], case.contexts[0].assignment['selector'], calculations)
        assert_mode_numbers(case.job, bundle, sheet, calculations)
        assert case.returned[0]['population'] == [body['population']]
        assert body['population']['total_records'] == len(calculations['rows'])
        assert body['population']['requested_artifact_count'] == len(case.job['outputs'])
        # Selected measurements/checks also deliver their actual input operands.
        # Custody-only bundle, sheet and calculation artifacts stay withheld.
        expected = {('output', row['role'], 0) for row in case.job['outputs']} | requested_input_dependencies(case.job)
        assert {(r['direction'], r['role'], r['ordinal']) for r in case.returned[0]['artifacts']} == expected
        assert body['population']['returned_artifact_count'] == len(expected)
        assert body['population']['missing_record_keys'] == body['population']['missing_artifacts'] == []
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == [2]
        assert case.result_records[0]['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert tuple(case.record.controller_state.history) == (0, 0)
        proof = case.owner.completion_for_action(case.contexts[0], body['operation_key'])
        assert proof and case.owner.verify_completion(case.contexts[0], proof)
        for key in ('run_id', 'episode_id', 'operation_key', 'assignment_sha256', 'receipt_sha256'):
            invalid = deepcopy(proof)
            invalid[key] = ('0' * 64 if key.endswith('sha256') else 'different-original-identity')
            assert not case.owner.verify_completion(case.contexts[0], invalid)
        expected = {PREFIX + name: case.returned[0][name] for name in ('rows', 'artifacts', 'population')}
        assert case.owner.native_hmmer_preparation_returns.received_facts(parent, case.forms[0]) == expected
        known = set(case.flow.receipts.known(parent.episode_id))
        for name in ('sheet_artifact_ref', 'calculations_artifact_ref'):
            withheld = body['prepared'][name]
            assert withheld not in known
            assert not case.flow.resolver(case.scope, context=parent)(withheld, 'artifact')
        original = deepcopy(sheet)
        with monkeypatch.context() as guard:
            forbidden = forbid_work(guard)
            guard.setattr('builtins.open', forbidden)
            guard.setattr(Path, 'open', forbidden)
            assert recalculate_hmmer_preparation(sheet, parameters=case.job['grading_parameters']) == calculations
            if program == 'hmmstat':
                altered = recalculate_hmmer_preparation(sheet, parameters={})
                assert altered['rows'][0]['components']['mean_match_relative_entropy']['value'] is None
                present(altered['rows'][0]['components']['mean_match_entropy'], .9925134248800135)
        assert sheet == original and case.store.count('observation') == 0
        (tmp_path / 'NUMERICAL_EXAMPLE.json').write_text(json.dumps({
            'program': program, 'mode': mode, 'original_job': case.job,
            'native_argv': bundle['realized_argv'], 'returncode': bundle['returncode'],
            'sheet_artifact_ref': body['prepared']['sheet_artifact_ref'],
            'calculations_artifact_ref': body['prepared']['calculations_artifact_ref'],
            'sheet_issues': sheet['issues'], 'calculation_issues': calculations['issues'],
            'typed_return': case.returned[0], 'failures': body['failures'],
            'completion_proof': proof, 'scientific_observation_count': 0}, indent=2) + '\n')
    finally:
        case.store.close()



def test_artifact_only_and_repeated_projection_do_not_manufacture_scientific_progress(tmp_path):
    job = native_job('hmmemit', 'consensus_simple')
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
        assert case.owner.native_hmmer_preparation_returns.received_facts(parent, result_form())[
            PREFIX + 'rows'] == []
    finally:
        case.store.close()


@pytest.mark.parametrize('fault', ['missing_key', 'changed_output'])
def test_partial_acquisition_returns_diagnostic_information_without_false_completion(tmp_path, fault):
    selection = choice_for(native_job('hmmemit', 'consensus_simple'))
    if fault == 'missing_key':
        selection['projection']['rows'] = {'record_keys': ['explicitly_absent_record']}
    def change(store, plan):
        output = next(row for row in plan['requested_job']['native_hmmer_preparation']['outputs']
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
            assert case.owner.resolve_received_reference(parent, 'explicitly_absent_record', 'native_hmmer_preparation_row')
        else:
            assert not body['capture']['complete']
            assert any('digest_mismatch' in f['code'] for f in body['failures'])
            assert case.returned[0]['artifacts']
            failures = case.returned[0]['failures']
            assert any(row['code'] == 'native_hmmer_preparation_sealed_artifact_digest_mismatch'
                and row['affected'] == {'direction': 'output', 'role': 'stdout', 'ordinal': 0}
                and row['handoff_ref'] == case.provider.handoff for row in failures)
            assert case.owner.resolve_received_reference(parent, failures[0]['code'],
                'native_hmmer_preparation_failure_code')
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
        monkeypatch.setattr('gene_annotation_episode.native_hmmer_preparation_worker.grade_hmmer_preparation', forbidden)
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
            monkeypatch.setattr('gene_annotation_episode.native_hmmer_preparation_results.'
                'prepare_native_hmmer_preparation_grading', unavailable)
    case = run_case(tmp_path, partial=True, before_collection=fail, form_options={'failures': True})
    try:
        parent, received = assert_accounting(case)
        body, form = case.outcomes[0]['result'], case.returned[0]
        assert body['population'] is None and form['population'] == []
        assert form['rows'] == [] and not form['completed'] and form['failures']
        expected = ('native_hmmer_preparation_sealed_bundle_unavailable' if fault == 'bundle_unavailable'
            else 'native_hmmer_preparation_retained_grading_unavailable')
        failure, = form['failures']
        assert failure['code'] == expected and failure['handoff_ref'] == case.provider.handoff
        assert 'Synthetic unexpected grading error' not in json.dumps(form)
        assert failure['source_ref'] == body['source_ref']
        assert case.owner.resolve_received_reference(parent, failure['code'], 'native_hmmer_preparation_failure_code')
        assert case.owner.resolve_received_reference(parent, failure['handoff_ref'], 'execution_handoff')
        assert case.owner.resolve_received_reference(parent, failure['handoff_ref'], 'execution_result') is False
        received_refs = case.owner.native_hmmer_preparation_returns.received_facts(parent, {
            'properties': {'references': {'x-source': PREFIX + 'result_refs'}}})[PREFIX + 'result_refs']
        assert failure['handoff_ref'] not in received_refs
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == (
            [0] if fault == 'bundle_unavailable' else [2])
        assert case.record.controller_state.history == (0, 0)
        assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
    finally:
        case.store.close()


def test_status_then_collect_preserves_final_gain_and_has_no_extra_zero_turn(tmp_path):
    case = run_case(tmp_path, status_first=True)
    try:
        assert_accounting(case)
        body = case.outcomes[0]['result']
        assert body['complete'] and case.returned[0]['completed']
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == [0, 2]
        assert case.result_records[0]['units_consumed'] == 2
        assert case.result_records[0]['controller_state']['estimate']['expected_next_gain'] == NumericBand.exact(0).as_record()
        assert {row['name'] for row in case.owner.catalog(case.contexts[0])} == {
            'execution.results.status', 'execution.results.collect'}
        described = case.owner.job_progress_provider.targets.describe_target(case.provider.handoff,
            case.scope, selector=case.contexts[0].assignment['selector'])
        assert described['service_or_program'] == 'hmmemit' and described['operation'] == 'consensus_simple'
    finally:
        case.store.close()


@pytest.mark.parametrize('scenario', ['indexed_aliases', 'unindexed_missing_key', 'indexed_partial_failure'])
def test_actual_fetch_key_populations_and_partial_native_prefix(tmp_path, scenario):
    job = native_job('hmmfetch', 'key_file')
    if scenario != 'unindexed_missing_key':
        job['operands'] = [operand('models', NATIVE / 'hmmfetch_index/models.hmm', 'hmmer3_ascii'),
            operand('ssi', NATIVE / 'hmmfetch_index/models.hmm.ssi', 'hmmer_ssi'), job['operands'][1]]
    if scenario != 'indexed_aliases':
        job['operands'][-1] = operand('keys', EVIDENCE / 'inputs/keys_missing.txt', 'key_file')
    partial = scenario == 'indexed_partial_failure'
    case = run_case(tmp_path, 'hmmfetch', 'key_file', job_override=job,
        partial=partial, expected_returncode=1 if partial else 0, form_options={'failures': True})
    try:
        assert_accounting(case)
        body, bundle, sheet, calculations = read_retained(case)
        keys = kind_row(calculations, 'key_population')
        present(keys['requested_key_count'], 2)
        present(keys['selected_source_occurrence_count'], 1)
        if partial:
            assert keys['returned_model_occurrence_count']['value'] == 1
            assert keys['returned_model_occurrence_count']['state'] == 'incomplete'
        else:
            present(keys['returned_model_occurrence_count'], 2 if scenario == 'indexed_aliases' else 1)
        present(keys['missing_key_count'], 0 if scenario == 'indexed_aliases' else 1)
        present(keys['resolved_key_count'], 2 if scenario == 'indexed_aliases' else 1)
        present(keys['duplicate_representation_count'], int(scenario == 'indexed_aliases'))
        assert body['complete'] is (not partial)
        assert case.returned[0]['completed'] is (not partial)
        if partial:
            assert bundle['returncode'] != 0 and bundle['failures']
            assert case.returned[0]['rows'] and case.returned[0]['artifacts']
            assert any(row['code'].endswith('nonzero_returncode') for row in case.returned[0]['failures'])
            assert case.owner.completion_for_action(case.contexts[0], body['operation_key']) is None
        else:
            assert bundle['returncode'] == 0
            # Acquired negative validation is valid practical information.
            assert case.owner.completion_for_action(case.contexts[0], body['operation_key'])
        assert [u['controller_step']['marginal_credit'] for u in case.result_records[0]['units']] == [2]
    finally:
        case.store.close()


