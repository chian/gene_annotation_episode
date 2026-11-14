"""Synthetic input fixtures; real pinned bedtools and retained-byte G1 joins."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import sys

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.native_genomic_overlap_contracts import (
    POLICY, ATTEMPT_DIRECTORY_NAME, RUN_PLAN_FILENAME, genomic_overlap_output_files,
    requested_job_from_genomic_overlap,
)
from gene_annotation_episode.native_genomic_overlap_driver import _immutable
from gene_annotation_episode.native_file_capture import capture_declared_native_files, capture_native_file
from gene_annotation_episode.state import Store

REPO = Path('/home/chia/repos/gene_annotation_episode')
BEDTOOLS = REPO / 'software/bedtools/ubuntu-2.31.1+dfsg-2/installation/usr/bin/bedtools'
BEDTOOLS_SHA = 'b6c6e44b79180f0c9f64f916010c71bcd44baf81e5abe71b63f19aa9d4bc9fb6'
DEFAULT_DATA = [b'chr1\t0\t10\nchr1\t5\t15\n', b'chr1\t7\t12\n', b'chr1\t10\t20\n']


def software():
    import gene_annotation_episode.native_genomic_overlap_driver as driver
    root = Path(driver.__file__).parents[1]
    modules = ['gene_annotation_episode.' + suffix for suffix in (
        'native_genomic_overlap_driver', 'native_genomic_overlap_contracts',
        'genomic_overlap_contracts', 'genomic_overlap_inputs')]
    return {'python_executable': sys.executable,
        'python_sha256': hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        'python_version': platform.python_version(), 'module_root': str(root),
        'driver_module': 'gene_annotation_episode.native_genomic_overlap_driver',
        'implementation_files': [{'module': module, 'sha256': hashlib.sha256(
            (root / (module.replace('.', '/') + '.py')).read_bytes()).hexdigest()} for module in modules],
        'bedtools_executable': str(BEDTOOLS), 'bedtools_sha256': BEDTOOLS_SHA,
        'bedtools_version': 'bedtools v2.31.1'}


def make_assignment(directory, data=None, formats=None, *, software_change=None):
    directory.mkdir(parents=True, exist_ok=True)
    data = DEFAULT_DATA if data is None else data
    formats = formats or ['bed_outer_span_v1'] * len(data)
    inputs = directory / 'inputs'
    inputs.mkdir()
    regions, bindings = [], []
    with Store(directory / 'source-store') as store:
        for i, (raw, format) in enumerate(zip(data, formats)):
            key = chr(65 + i)
            path = inputs / f'{i}.data'
            path.write_bytes(raw)
            identity = capture_native_file(store, directory=str(inputs), relative_path=path.name, format=format)
            regions.append({'set_key': key, 'display_label': None,
                'source': {'kind': 'bed_artifact' if format == 'bed_outer_span_v1' else 'coordinate_rows_artifact',
                    'source_ref': 'component-fixture-source-' + key, 'file': identity},
                'reference': None, 'format': format})
            bindings.append({'set_key': key, 'path': str(path)})
    comparisons = [{'comparison_key': a['set_key'] + b['set_key'], 'ordinal': n,
        'a_set_key': a['set_key'], 'b_set_key': b['set_key']} for n, (a, b) in enumerate(
        (a, b) for i, a in enumerate(regions) for b in regions[i+1:])]
    request = {'version': 'genomic_overlap_request_v1', 'operation': 'analyze_genomic_region_overlap',
        'mode': 'unstranded_outer_span', 'region_sets': regions, 'comparisons': comparisons, 'output_prefix': 'overlap'}
    selected_software = software()
    if software_change:
        software_change(selected_software)
    job = {'version': 'native_genomic_overlap_job_v1', 'program': 'bedtools_intersect_all_pairs',
        'request': request, 'software': selected_software, 'inputs': bindings,
        'outputs': genomic_overlap_output_files(request), 'environment': {'LC_ALL': 'C'}}
    return {'version': 'practical_assignment_v1', 'assignment_id': 'overlap-component-fixture',
        'resource_kind': 'local', 'resource_id': 'selected-local', 'workspace': str(directory),
        'endpoint': 'usable_handoff', 'requested_job': requested_job_from_genomic_overlap(job),
        'progress_requirements': [{'key': 'handoff', 'credit': 1,
            'predicate': {'kind': 'requested_job_handoff'}}], 'completion_keys': ['handoff'],
        'initial_context': {'revision': 0, 'cwd': str(directory), 'environment': {}},
        'inventory_snapshot': {}, 'constraints': {'allocation': deepcopy(POLICY)}}


def plan_for(assignment, *, operation='selected-start', run='component-run', episode='local-child'):
    root = Path(assignment['workspace']) / '.episode-operations' / digest({'run': run, 'episode': episode}) / digest(operation)
    return {'version': 'native_genomic_overlap_run_plan_v1', 'identity': {
        'run_id': run, 'episode_id': episode, 'resource_id': assignment['resource_id'],
        'execution_id': str(root / 'native.json'), 'attempt_id': digest(operation), 'operation_key': operation,
        'requested_job_sha256': digest(assignment['requested_job']), 'assignment_sha256': digest(assignment)},
        'requested_job': deepcopy(assignment['requested_job']),
        'attempt_directory': str(root / ATTEMPT_DIRECTORY_NAME), 'policy': deepcopy(POLICY)}


def make_plan(directory, **kwargs):
    assignment = make_assignment(directory, **kwargs)
    plan = plan_for(assignment)
    root = Path(plan['identity']['execution_id']).parent
    root.mkdir(parents=True)
    _immutable(root / RUN_PLAN_FILENAME, plan)
    return plan


def parameters(minimum=1):
    return {'version': 'genomic_overlap_calculation_parameters_v1', 'minimum_overlap_bp': minimum,
        'minimum_a_fraction': {'numerator': 0, 'denominator': 1},
        'minimum_b_fraction': {'numerator': 0, 'denominator': 1}}


def g1_result(plan, bundle, *, minimum=1):
    """Test-only real Store capture, then the unchanged G1 reader/calculator."""
    from gene_annotation_episode.genomic_overlap_inputs import (
        parse_bedtools_intersect_wo, extract_overlap_reference_metadata, build_genomic_overlap_sheet)
    from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
    directory = Path(plan['attempt_directory'])
    request = plan['requested_job']['native_genomic_overlap']['request']
    with Store(directory.parent / 'captured-store') as store:
        captures = capture_declared_native_files(store, directory=str(directory),
            declarations=[row['declaration'] for row in bundle['files']])
    captured = {row['specification']['file_key']: capture['observed'] for row, capture in zip(bundle['files'], captures)}
    files = {row['specification']['file_key']: directory / row['declaration']['relative_path'] for row in bundle['files']}
    sets = [json.loads(files[row['parsed_file_key']].read_bytes()) for row in bundle['sets']]
    by_key = {row['set_key']: row for row in sets}
    set_outputs = {row['set_key']: row for row in bundle['sets']}
    parsed_pairs = []
    for pair_output in bundle['pairs']:
        comparison, manifest = pair_output['comparison'], pair_output['manifest']
        ordinal = comparison['ordinal']
        if manifest is None:
            invalid = pair_output['disposition'] == 'input_unavailable'
            derivation = 'not_executed_invalid_input' if invalid else 'bedtools_intersect'
            outcome, argv, environment, native_software = 'not_executed', [], {}, None
            rc = began = ended = closed = stdout = stderr = None
            extent = 'unavailable'
            basis = 'unavailable'
        else:
            derivation, outcome = manifest['derivation'], manifest['outcome']
            argv, environment, native_software = manifest['realized_argv'], manifest['environment'], manifest['software']
            rc, began, ended, closed = (manifest[k] for k in ('returncode', 'started_at', 'finished_at', 'writer_closed'))
            stdout, stderr = captured[f'p{ordinal}:stdout'], captured[f'p{ordinal}:stderr']
            extent = 'complete' if outcome == 'succeeded' or derivation == 'validated_empty_input' else (
                'partial' if outcome == 'failed' else 'unavailable')
            basis = ('validated_empty_input' if derivation == 'validated_empty_input' else
                'closed_successful_native_attempt' if outcome == 'succeeded' else
                'partial_native_result' if outcome == 'failed' else 'unavailable')
        receipt = {'version': 'genomic_overlap_native_pair_receipt_v1',
            'comparison_key': comparison['comparison_key'], 'identity': bundle['identity'],
            'derivation': derivation, 'outcome': outcome, 'software': native_software,
            **{side: {'set_key': comparison[side + '_set_key'],
                'original_file': by_key[comparison[side + '_set_key']]['source_file'],
                'canonical_file': captured[set_outputs[comparison[side + '_set_key']]['canonical_file_key']]}
                for side in ('a', 'b')}, 'realized_argv': argv, 'environment': environment,
            'returncode': rc, 'started_at': began, 'finished_at': ended, 'stdout': stdout, 'stderr': stderr,
            'writer_closed': closed, 'capture_extent': 'complete' if manifest else 'unavailable',
            'native_result_extent': extent, 'completeness_basis': basis,
            'completeness_source_refs': ['component-fixture-actual-pair-seal'], 'issues': []}
        raw = files[f'p{ordinal}:stdout'].read_bytes() if stdout is not None else None
        parsed_pairs.append(parse_bedtools_intersect_wo(raw, pair=comparison, sets=by_key, native=receipt))
    references = extract_overlap_reference_metadata(specifications=request['region_sets'], sets=by_key,
        comparisons=request['comparisons'])
    sheet = build_genomic_overlap_sheet(request=request, sets=sets, native_pairs=parsed_pairs, reference_relations=references)
    return sheet, calculate_genomic_overlap_components(sheet, parameters=parameters(minimum))
