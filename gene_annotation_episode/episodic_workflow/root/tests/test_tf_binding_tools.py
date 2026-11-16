"""Ordinary TF integration and retained recovery, selected explicitly by the runner.

The choices are deterministic engineering fixtures. Native scoring, journals,
Source custody and typed delivery use the actual application ports.
"""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import tf_binding_measurements as core
from gene_annotation_episode import tf_binding_result_contracts as contracts
from gene_annotation_episode import tf_binding_tools as host
from gene_annotation_episode.domain import obj
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry


ROOT = Path(__file__).resolve().parents[4]
PUBLICATION = 'research/slotted_process_library/publications/2026-10-24-001'
POLICY = dict(memory_bytes=ENVIRONMENT_BOUNDS['memory_bytes'], scratch_bytes=4294967296)
ENVIRONMENT = dict(version='tf_binding_execution_selection_v1',
    environment_realization='operation_scoped_tmp_and_cache_v1')
QUESTION = ('Which positions and strands in the supplied GATC DNA meet raw log2-odds thresholds '
    '2 and 0 for the supplied count matrix, using the declared background and zero pseudocounts? '
    'Retain both selected strand score arrays. Return candidate sites at raw log2-odds '
    'threshold 2, read that fixed result, then use the same saved scores '
    'at threshold 0 and select that exact saved view again. Preserve original coordinates, '
    'qualifications and the distinction between candidates and measured binding or regulation. '
    'The extra binary input is an explicitly unselected invalid DNA slot, not measured DNA; '
    'these fragments establish no gene or neighborhood context.')
JOURNALS = ('runtime_episodes', 'runtime_actions', 'runtime_observations',
    'runtime_model_calls', 'runtime_forms', 'runtime_report_attempts')


def _write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _inventory(directory):
    root = Path(directory)
    return [dict(relative_path=str(path.relative_to(root)), mode=stat.S_IMODE(path.stat().st_mode),
        sha256=value['sha256'], size_bytes=value['size_bytes'])
        for path in sorted(root.rglob('*')) if path.is_file() for value in [_pin(path)]]


def _form():
    return obj(dict(sites=contracts.tf_binding_fact_sources()[contracts.FACT_SOURCE]['report_schema']))


def _assert_tf_display(text, packet):
    """Independent display boundary: literal scientific operands and values."""
    for heading in ('Selected scans in caller order', 'Declared input parameters before native normalization',
            'Original sequence occurrences', 'Original matrix occurrences',
            'Retained scans available for saved selection', 'Retained counts for the selected scans',
            'Returned raw-threshold rows; coordinates are zero-based forward-sequence intervals',
            'Retained relative normalization', 'Result qualifications'):
        assert heading in text
    assert '| Raw log2-odds threshold | ' + str(packet['selection']['raw_threshold']) + ' |' in text
    assert packet['source_ref'] in text
    for scan in packet['selection']['scan_ids']:
        assert scan in text
    for base in 'ACGT':
        assert '| ' + base + ' | ' + str(packet['parameters']['background'][base]) + ' | ' + str(packet['parameters']['pseudocounts'][base]) + ' |' in text
    for key in ('possible_strand_windows', 'model_eligible_candidate_sites', 'nan_scores', 'negative_infinity_scores'):
        cell = packet['totals'][key]
        value = 'null' if cell['value'] is None else str(cell['value'])
        assert '| ' + key.replace('_', ' ') + ' | ' + value + ' | ' + cell['state'] + ' | ' + cell['unit'] + ' |' in text
    assert 'forward_pssm_bounds_for_both_strands' in text
    # These keys belong to the controlled DTO, not the finite literal display.
    for field in ('raw_threshold_matches', 'relative_normalizations', 'numeric_authority', 'available_scans'):
        assert '"' + field + '":' not in text


def _dispatch_fixture(tmp_path):
    directory = tmp_path / 'worker'; directory.mkdir()
    resource = dict(resource_id='tf', resource=dict(kind='local', workspace=str(tmp_path), policy=deepcopy(POLICY)),
        environment=deepcopy(ENVIRONMENT))
    registry = SimpleNamespace(local_job_policy=LocalJobPolicy(**POLICY))
    owner = SimpleNamespace(resources={'tf': deepcopy(resource['resource'])})
    request = dict(engineered_metadata_only=True)
    selected = dict(version='ordinary_molecular_execution_v1', command=['/selected/python', '-m',
        'gene_annotation_episode.tf_binding_driver', str(directory / 'worker-request.json'), str(directory / 'worker-result.json')],
        cwd=str(directory), environment={}, policy=deepcopy(POLICY), request=dict(operation='tf_binding_native', arguments=dict(request=deepcopy(request))),
        python=dict(path='/selected/python'), implementation_files=[])
    return directory, resource, registry, owner, request, selected


@pytest.mark.parametrize('field', ['request', 'command', 'cwd', 'policy'])
def test_tf_dispatch_rejects_changed_original_selection_before_work(tmp_path, field):
    directory, resource, registry, owner, request, selected = _dispatch_fixture(tmp_path)
    if field == 'request': selected['request']['arguments']['request']['changed'] = True
    elif field == 'command': selected['command'][2] = 'gene_annotation_episode.tf_binding_result_worker'
    elif field == 'cwd': selected['cwd'] += '-other'
    else: selected['policy']['scratch_bytes'] += 1
    _write(directory / 'execution-selection.json', selected)
    before = _inventory(tmp_path)
    with pytest.raises(ValueError, match='tf_binding_original_worker_selection_conflict'):
        host._worker_dispatch(registry, owner, request, directory, 'tf_binding_native', POLICY, resource)
    assert _inventory(tmp_path) == before


def test_tf_dispatch_preserves_original_policy_without_repricing(tmp_path):
    directory, resource, registry, owner, request, selected = _dispatch_fixture(tmp_path)
    _write(directory / 'execution-selection.json', selected)
    registry.local_job_policy = LocalJobPolicy(**dict(POLICY, scratch_bytes=POLICY['scratch_bytes'] * 2))
    owner.resources = {}
    before = _inventory(tmp_path)
    host._worker_dispatch(registry, owner, request, directory, 'tf_binding_native', POLICY, resource)
    assert _inventory(tmp_path) == before


@pytest.mark.parametrize('fault', ['current_policy', 'resource'])
def test_tf_dispatch_authenticates_first_allocation_before_work(tmp_path, fault):
    directory, resource, registry, owner, request, _ = _dispatch_fixture(tmp_path)
    if fault == 'current_policy':
        registry.local_job_policy = LocalJobPolicy(**dict(POLICY, scratch_bytes=POLICY['scratch_bytes'] * 2))
    else:
        owner.resources['tf']['workspace'] += '-other'
    before = _inventory(tmp_path)
    with pytest.raises(ValueError, match='tf_binding_run_resource_selection_conflict'):
        host._worker_dispatch(registry, owner, request, directory, 'tf_binding_native', POLICY, resource)
    assert _inventory(tmp_path) == before


def _render_tf_without_work(packet, monkeypatch):
    """Engineered display control, not an actual Source or native observation."""
    from Bio.motifs.matrix import PositionSpecificScoringMatrix
    from gene_annotation_episode import scientific_process_prompt as prompt
    from gene_annotation_episode import tf_binding_driver as driver
    from gene_annotation_episode import tf_binding_result_worker as result_worker
    import builtins
    import urllib.request
    def forbidden(*args, **kwargs):
        raise AssertionError('TF display attempted I/O, scoring, calculation or publication')
    with monkeypatch.context() as guard:
        for name in ('decode_tf_binding_inputs', 'populate_tf_binding_sheet',
                'calculate_tf_binding_components', 'project_tf_binding_return'):
            guard.setattr(core, name, forbidden)
        guard.setattr(PositionSpecificScoringMatrix, 'calculate', forbidden)
        guard.setattr(driver, 'run_tf_binding_native', forbidden)
        guard.setattr(result_worker, 'run_tf_binding_result', forbidden)
        guard.setattr(Store, '__init__', forbidden)
        guard.setattr(Store, 'get_artifact', forbidden)
        guard.setattr(Store, 'artifact', forbidden)
        guard.setattr(ToolRegistry, '_source', forbidden)
        guard.setattr(Path, 'open', forbidden)
        guard.setattr(Path, 'read_bytes', forbidden)
        guard.setattr(builtins, 'open', forbidden)
        guard.setattr(urllib.request, 'urlopen', forbidden)
        for name in ('prepare_job', 'start', 'resume_start', 'status', 'collect', 'cancel', 'release', 'wait_job'):
            if hasattr(native_lifecycle, name): guard.setattr(native_lifecycle, name, forbidden)
        return prompt._values(dict(result=packet, status='completed', record_refs=[packet['source_ref']],
            changed_record_refs=[packet['source_ref']], same_fixed_result=deepcopy(packet)))


@pytest.mark.parametrize('threshold,expected_candidates', [(2., 2), (0., 4)])
def test_tf_display_uses_fixed_values_without_io_or_calculation(monkeypatch, threshold, expected_candidates):
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet()
    components = core.calculate_tf_binding_components(sheet, selection(sheet, threshold))
    packet = core.project_tf_binding_return(components, 'source_' + 'c' * 24)
    before = deepcopy(packet)
    text = _render_tf_without_work(packet, monkeypatch)
    _assert_tf_display(text, packet)
    assert packet['totals']['model_eligible_candidate_sites']['value'] == expected_candidates
    assert text.count('Declared input parameters before native normalization') == 1
    assert text.count(packet['source_ref']) == 1
    assert '| - | 0 | 2 | GA | TC | 2.0 | finite |' in text
    assert '| + | 2 | 4 | TC | TC | 2.0 | finite |' in text
    assert all(row['sha256'] not in text for row in packet['inputs'])
    assert packet == before


def test_tf_display_keeps_nonfinite_counts_and_undefined_relative_meaning(monkeypatch):
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet(dna=b'ANC', counts=dict(A=[1], C=[0], G=[0], T=[0]),
        pwm=[[1], [0], [0], [0]], pssm=[[2], [-float('inf')], [-float('inf')], [-float('inf')]],
        rc=[[-float('inf')], [-float('inf')], [-float('inf')], [2]],
        background=dict.fromkeys('ACGT', .25), bounds=(-float('inf'), 2),
        scores={'+': [2, float('nan'), -float('inf')]}, strands=('+',))
    packet = core.project_tf_binding_return(core.calculate_tf_binding_components(sheet, selection(sheet)),
        'source_' + 'd' * 24)
    before = deepcopy(packet)
    text = _render_tf_without_work(packet, monkeypatch)
    _assert_tf_display(text, packet)
    assert '| nan scores | 1 | available | count |' in text
    assert '| negative infinity scores | 1 | available | count |' in text
    assert '| scientific_state | undefined |' in text
    assert '| reason_code | nonfinite_relative_bounds |' in text
    assert '| minimum | null | negative_infinity | available | bits |' in text
    assert 'undefined' in text and 'nonfinite_relative_bounds' in text
    assert packet == before


@pytest.mark.parametrize('fault', ['version', 'parameters'])
def test_tf_display_requires_exact_validated_packet(monkeypatch, fault):
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet()
    packet = core.project_tf_binding_return(core.calculate_tf_binding_components(sheet, selection(sheet)),
        'source_' + 'e' * 24)
    if fault == 'version': packet['version'] = 'tf_binding_return_v999'
    else: packet['parameters']['background']['A'] = -1
    before = deepcopy(packet)
    text = _render_tf_without_work(packet, monkeypatch)
    assert 'Declared input parameters before native normalization' not in text
    assert 'Raw log2-odds threshold' not in text
    assert packet['source_ref'] in text
    assert packet == before


def _engineered_tf_form():
    from test_tf_binding_measurements import engineered_sheet, selection
    sheet = engineered_sheet()
    returned = core.project_tf_binding_return(core.calculate_tf_binding_components(sheet, selection(sheet)),
        'source_' + 'c' * 24)
    # Deliberately identifier-shaped opaque metadata. It is not another grant.
    returned['inputs'][0]['upstream_source_id'] = 'source_' + 'f' * 24
    return _form(), dict(sites=[returned])


def _validate_tf_form_without_work(schema, payload, resolver, monkeypatch, *, compile_only=False):
    from Bio.motifs.matrix import PositionSpecificScoringMatrix
    from gene_annotation_episode.episodic_workflow.root import communication
    from gene_annotation_episode import tf_binding_driver as driver
    from gene_annotation_episode import tf_binding_result_worker as result_worker
    import builtins
    import urllib.request
    def forbidden(*args, **kwargs):
        raise AssertionError('TF form validation attempted I/O, scoring, calculation or publication')
    with monkeypatch.context() as guard:
        for name in ('decode_tf_binding_inputs', 'populate_tf_binding_sheet',
                'calculate_tf_binding_components', 'project_tf_binding_return'):
            guard.setattr(core, name, forbidden)
        guard.setattr(PositionSpecificScoringMatrix, 'calculate', forbidden)
        guard.setattr(driver, 'run_tf_binding_native', forbidden)
        guard.setattr(result_worker, 'run_tf_binding_result', forbidden)
        guard.setattr(Store, '__init__', forbidden)
        guard.setattr(Store, 'get_artifact', forbidden)
        guard.setattr(Store, 'artifact', forbidden)
        guard.setattr(ToolRegistry, '_source', forbidden)
        guard.setattr(Path, 'open', forbidden)
        guard.setattr(Path, 'read_bytes', forbidden)
        guard.setattr(builtins, 'open', forbidden)
        guard.setattr(urllib.request, 'urlopen', forbidden)
        guard.setattr(urllib.request.OpenerDirector, 'open', forbidden)
        if compile_only:
            return communication.validate_closed_schema(schema)
        return communication.validate_form(payload, schema, resolver)


def test_tf_registered_form_compiles_without_work(monkeypatch):
    schema = _form()
    before = deepcopy(schema)
    compiled = _validate_tf_form_without_work(schema, None, None, monkeypatch, compile_only=True)
    assert compiled == before and schema == before


def test_tf_form_resolves_only_top_source_and_keeps_input_ids_opaque(monkeypatch):
    schema, payload = _engineered_tf_form()
    before = deepcopy((schema, payload))
    returned = payload['sites'][0]
    seen = []
    def resolver(reference, namespace):
        seen.append((reference, namespace))
        return reference == returned['source_ref'] and namespace == 'source'
    admitted = _validate_tf_form_without_work(schema, payload, resolver, monkeypatch)
    assert admitted == payload
    assert seen == [(returned['source_ref'], 'source')]
    assert returned['inputs'][0]['artifact_id'].startswith('artifact_')
    assert returned['inputs'][0]['upstream_source_id'] == 'source_' + 'f' * 24
    assert (schema, payload) == before


@pytest.mark.parametrize('fault', ['modified', 'widened', 'nested', 'unregistered'])
def test_tf_form_rejects_changed_or_nested_registered_contract(monkeypatch, fault):
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    schema = _form()
    field = schema['properties']['sites']
    if fault == 'modified': field['description'] = field.get('description', '') + ' changed'
    elif fault == 'widened': field['$defs']['Return']['additionalProperties'] = True
    elif fault == 'nested': schema = obj(dict(wrapper=obj(dict(sites=field))))
    else: del field['x-source']
    before = deepcopy(schema)
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(schema, None, None, monkeypatch, compile_only=True)
    assert error.value.diagnostic['code'] == 'invalid_schema'
    assert schema == before


@pytest.mark.parametrize('fault', ['negative_parameter', 'crossfield_count', 'score_bits', 'float_integer'])
def test_tf_form_rejects_invalid_parameters_and_crossfield_values(monkeypatch, fault):
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    schema, payload = _engineered_tf_form()
    value = payload['sites'][0]
    if fault == 'negative_parameter': value['parameters']['background']['A'] = -1
    elif fault == 'crossfield_count': value['totals']['returned_candidate_rows']['value'] = 0
    elif fault == 'score_bits': value['raw_threshold_matches'][0]['score']['bits_hex'] = '00000000'
    else: value['inputs'][0]['size_bytes'] = float(value['inputs'][0]['size_bytes'])
    before = deepcopy((schema, payload))
    seen = []
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(schema, payload, lambda *args: seen.append(args) or True, monkeypatch)
    assert error.value.diagnostic['field'] == 'sites'
    assert seen == [] and (schema, payload) == before


def test_tf_form_revalidates_source_permission_after_cached_schema(monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    schema, payload = _engineered_tf_form()
    source = payload['sites'][0]['source_ref']
    assert _validate_tf_form_without_work(schema, payload, lambda ref, ns: (ref, ns) == (source, 'source'), monkeypatch) == payload
    seen = []
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(schema, payload, lambda *args: seen.append(args) or False, monkeypatch)
    assert seen == [(source, 'source')]
    assert error.value.diagnostic == dict(category='report_format', code='unknown_reference', field='report.sites[0].source_ref')


def test_tf_registration_does_not_widen_generic_string_forms(monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    with pytest.raises(ReportBoundaryError) as error:
        _validate_tf_form_without_work(obj(dict(unrestricted=dict(type='string'))), None, None,
            monkeypatch, compile_only=True)
    assert error.value.diagnostic['code'] == 'unrestricted_string'
