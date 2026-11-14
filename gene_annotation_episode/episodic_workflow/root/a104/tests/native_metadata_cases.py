"""Metadata projection controls, explicitly separate from native admission.

The actual private Results reader, Store source, original describe method and
real selector validators are exercised. A named read_target projection port
supplies operation operands; this does NOT establish a valid native handoff,
saved scientific sheet or producer result for those seven profiles. Native
receipt/progress authentication has its separate NativeProgressCase controls.
"""
from copy import deepcopy
import ast
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from .api_cases import canonical, module, outcome, rows
from .native_progress_cases import HOMES, NativeProgressCase

FAMILIES = (('native_hmmer_results', 'NativeHMMERResults', 'NativeHMMERResultRecords', 'NativeHMMERResultAcquisition', ('_action_directory', '_index', 'execute'), ()), ('native_blast_results', 'NativeBLASTResults', 'NativeBLASTResultRecords', 'NativeBLASTResultAcquisition', ('_action_directory', '_index', 'execute'), ()), ('native_blast_masking_results', 'NativeBLASTMaskingResults', 'NativeBLASTMaskingResultRecords', 'NativeBLASTMaskingResultAcquisition', ('_index', '_prior', 'execute'), ('_failure',)), ('native_blast_utility_results', 'NativeBLASTUtilityResults', 'NativeBLASTUtilityResultRecords', 'NativeBLASTUtilityResultAcquisition', ('_index', '_prior', 'execute'), ('_failure',)), ('native_blast_standard_database_results', 'StandardBLASTDatabaseResults', 'StandardBLASTDatabaseResultRecords', 'StandardBLASTDatabaseResultAcquisition', ('_index', 'execute'), ()), ('native_blast_database_results', 'NativeBLASTDatabaseResults', 'NativeBLASTDatabaseResultRecords', 'NativeBLASTDatabaseResultAcquisition', ('_index', 'execute'), ('_saved_failure',)), ('native_hmmer_preparation_results', 'NativeHmmerPreparationResults', 'NativeHmmerPreparationResultRecords', 'NativeHmmerPreparationResultAcquisition', ('_index', 'execute'), ()))
ORIGINAL_PROGRESS_SHA256 = '15789862b1868a0aba54c03783f9c530e45c362f44414ce2c3432728d07b5a14'


def original_describe():
    path = Path(__file__).parent / 'fixtures/native_result_validation/execution_progress.py.txt'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ORIGINAL_PROGRESS_SHA256
    source = ast.parse(raw)
    owner, = [node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'ExecutionTargetReader']
    method, = [node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == 'describe_target']
    # Complete original function; no calls, operands, decorators or branches
    # are specialized. Current shared globals are explicit external dependencies.
    namespace = dict(vars(module('execution_progress')))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
        str(path), 'exec', dont_inherit=True), namespace)
    return namespace['describe_target']


def projection_operands(family):
    """Only the fields read by metadata, never passed as a native job contract."""
    name = family[0]
    if name == 'native_hmmer_results':
        return 'native_hmmer', {'program': 'hmmsearch', 'mode': 'search'}, {'original_ignored_selector': True}
    if name == 'native_blast_results':
        return 'native_blast', {'program': 'blastp', 'mode': 'pairwise', 'outputs': []}, {
            'version': 'native_blast_result_selector_v1', 'acquisition': 'complete_bound_bundle',
            'projection': {'family': 'pairwise_hsp', 'rows': {'record_keys': ['explicit-original-row']},
                'metrics': ['native_score_bits']}}
    if name == 'native_blast_masking_results':
        # Original job_for operation construction, without creating an executable
        # or presenting this metadata operand as its complete native job.
        schema = module('sequence_masking_contracts').sequence_masking_operation_schema(program='dustmasker', mode='mask')
        operation = {'version': 'sequence_masking_operation_v1', 'program': 'dustmasker',
            'mode': 'mask', 'engine_version': 'synthetic', 'input_format': 'fasta',
            'output_format': 'interval', 'masking_style': 'interval', 'parse_seqids': False,
            'requested_parameters': {key: None for key in schema['properties']['requested_parameters']['properties']}}
        selected = {'version': 'native_blast_masking_result_selector_v1', 'mode': 'native_result',
            'records': {'mode': 'all'}, 'quantities': ['masked_positions', 'masked_fraction'],
            'statistics_fields': [], 'statistics_unit_codes': [], 'include_checks': True,
            'artifacts': [], 'saved_sheet_ref': None, 'saved_data': []}
        return 'native_blast_masking', {'operation': operation, 'outputs': []}, selected
    if name == 'native_blast_utility_results':
        # test_blast_utility_contracts_625.operation('info') original operands.
        operation = {'version': 'blast_utility_operation_v1', 'program': 'blastdbcmd',
            'mode': 'info', 'input_occurrence_ids': [], 'database_key': 'tiny',
            'molecule': 'dna', 'parameters': {'exact_length': True}}
        return 'native_blast_utility', {'version': 'native_blast_utility_job_v1',
            'operation': operation, 'outputs': []}, {
            'version': 'native_blast_utility_result_selector_v1', 'sequences': None,
            'database_fields': ['database_sequence_count'], 'integrity': None,
            'preparation': None, 'prepared_database': False, 'include_checks': True,
            'artifacts': [], 'saved_data': []}
    if name in {'native_blast_standard_database_results', 'native_blast_database_results'}:
        standard = name == 'native_blast_standard_database_results'
        key = 'native_blast_standard_database' if standard else 'native_blast_database'
        return key, {'program': 'blastp' if standard else 'psiblast', 'mode': 'database',
            'outputs': [], 'databases': []}, {
            'version': 'native_blast_standard_database_selector_v1' if standard else 'native_blast_database_result_selector_v1',
            'acquisition': 'complete_bound_bundle', 'metadata_inputs': [], 'retained_sources': [],
            'projections': [{'family': 'hsp', 'rows': {'offset': 0, 'limit': 5},
                'metrics': ['native_score_bits', 'native_evalue'], 'booleans': []}]}
    assert name == 'native_hmmer_preparation_results'
    return 'native_hmmer_preparation', {'program': 'hmmemit', 'mode': 'consensus_simple'}, {
        'version': 'native_hmmer_preparation_result_selector_v1', 'acquisition': 'complete_bound_bundle',
        'artifacts': [], 'projection': {'collection': 'calculations',
            'rows': {'record_keys': ['explicit-original-row']}, 'quantities': ['length'], 'checks': []}}


def expected_implementation(home, family):
    leaf = family[0].removesuffix('_results') + '_result_acquisition'
    return 'gene_annotation_episode.episodic_workflow.root.a104.' + home.replace('/', '.') + '.' + leaf + '.' + family[3] + '.execute'


def check_metadata(directory, home, family, *, phase, bound):
    from types import SimpleNamespace
    from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources as hpc_resources
    assert phase in {'baseline', 'connected'} and type(bound) is bool
    case = NativeProgressCase(directory, home)
    try:
        resources = {**case.resources, **hpc_resources()}
        owner = module(home + '/episode').ExecutionEpisode(
            SimpleNamespace(annotation_task_required=lambda: False), store=case.store,
            directory=case.directory / 'results', run_id=case.run_id, resources=resources,
            initial_information={}, tool_registry=None, handoff_unit=1., acquired_record_unit=1.,
            log_window_bytes=8, log_roles=('stdout', 'stderr'))
        reader = owner.job_progress_provider.targets
        if not bound:
            reader = module('execution_progress').ExecutionTargetReader(case.store, run_id=case.run_id,
                directory=case.directory / 'unbound', resources=resources, api_execution=owner.api_execution)
        key, job, selected = projection_operands(family)
        target = deepcopy(case.target)
        target['assignment']['requested_job'][key] = job
        if key in {'native_blast_standard_database', 'native_blast_database'}:
            target['resource_id'], target['resource_kind'] = 'aurora', 'hpc'
            target['assignment'].update(resource_id='aurora', resource_kind='hpc',
                workspace=resources['aurora']['workspace'])
        projection_calls = []
        def selected_projection(handle, scope):
            assert handle == case.reference
            case.store.validate_scope(case.scope, parent_scope=canonical(scope))
            projection_calls.append((handle, canonical(scope)))
            return deepcopy(target)
        selectors = [None, selected, {'deliberately_invalid_selector': True}]
        if family[0] == 'native_blast_masking_results':
            saved_selector = deepcopy(selected)
            saved_selector.update(mode='saved_recalculation',
                saved_sheet_ref=case.store.artifact(b'{"controlled_metadata_only":true}', 'application/json'))
            selectors.append(saved_selector)
        before = rows(case.store)
        observations = []
        old_name = 'gene_annotation_episode.episodic_workflow.root.a104.' + family[0] + '.' + family[1] + '.execute'
        original = original_describe()
        with patch.object(reader, 'read_target', selected_projection):
            for selector in selectors:
                preserved = outcome(lambda: original(reader, case.reference, case.scope, selector=deepcopy(selector)))
                actual = outcome(lambda: reader.describe_target(case.reference, case.scope, selector=deepcopy(selector)))
                expected = deepcopy(preserved)
                if phase == 'connected' and 'returned' in expected:
                    selected_count = 0
                    for extractor in expected['returned']['extractors']:
                        if extractor.get('implementation') == old_name:
                            selected_count += 1
                            extractor['implementation'] = expected_implementation(home, family) if bound else None
                            if not bound:
                                extractor['implementation_status'] = 'private_results_counterpart_unbound'
                    assert selected_count == (2 if isinstance(selector, dict)
                        and selector.get('mode') == 'saved_recalculation' else 1)
                assert actual == expected
                observations.append({'selector': selector, 'original': preserved, 'actual': actual})
        assert len(projection_calls) == 2 * len(selectors) and rows(case.store) == before
        assert all('returned' in row['actual'] for row in observations[:2])
        if family[0] != 'native_hmmer_results':
            assert 'raised' in observations[2]['actual']
        else:
            assert observations[2]['actual'] == observations[0]['actual']
        if len(selectors) == 4:
            saved_view = observations[3]['actual']['returned']
            assert saved_view['status_operations'] == ['execution.results.status']
            assert saved_view['extractors'][0]['fresh_native_observation'] is False
            assert 'parsers' not in saved_view['extractors'][1]
        return {'home': home, 'family': family[0], 'bound': bound, 'observations': observations,
            'all_store_rows_unchanged': True, 'controlled_port': 'metadata_only_read_target_projection',
            'scientific_native_handoff_or_producer_acceptance_claimed': False,
            'saved_workflow_restoration_claimed': False}
    finally:
        case.close()
