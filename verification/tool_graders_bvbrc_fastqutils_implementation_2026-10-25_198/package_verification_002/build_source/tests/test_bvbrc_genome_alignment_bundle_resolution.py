"""Public E facade using upstream native bytes and synthetic receipt custody."""
from copy import deepcopy
import hashlib

import pytest

from gene_annotation_episode import bvbrc_genome_alignment_bundle_adapter as facade
from gene_annotation_episode import bvbrc_genome_alignment_bundle_resolution as resolution
from test_bvbrc_genome_alignment_associations import native_case
from test_bvbrc_genome_alignment_retained_records import content
from test_bvbrc_genome_alignment_sheet import all_requests, plan, slot


def member(index=0, namespace='mauve_v4_member_0based'):
    return {'namespace': namespace, 'index': index}


def measurement(request_id='anchors', family='v4_coverage', field='known_union_bases', **location):
    if not location:
        location = {'member': member()}
    return {'kind': 'measurement', 'request_id': request_id, 'metric': {'family': family, 'field': field, **location}}


def arguments(fmt='mauve_v4', fields=None):
    case = native_case(fmt)
    artifact = case['artifacts'][0]
    slots = [slot({'mauve_v4': 'v4', 'mauve1_xmfa': 'xmfa', 'mauve_backbone': 'backbone', 'mauve_bbcols': 'bbcols'}[fmt],
                  fmt, case['parsed_artifacts'][0]['document'])]
    requests = [r for r in all_requests() if r['document_slot_id'] == slots[0]['slot_id']]
    if fmt == 'mauve_bbcols':
        slots.append(slot('xmfa', 'mauve1_xmfa'))
    if fields is None:
        fields = {'native': {'mauve_v4': measurement(),
            'mauve_backbone': measurement('backbone', 'backbone_coverage', member=member(0, 'mauve_sidecar_member_0based')),
            'mauve_bbcols': measurement('columns', 'bbcols_interval', 'union_columns', native_interval_index_0based=0),
            'mauve1_xmfa': measurement('pairs', 'xmfa_pair', 'identity_fraction', block_index=0, member_a=1, member_b=2)}[fmt]}
    # The full bundle includes the acquisition helper; C2 receives scientific
    # roles only and proves the manifest through unchanged retained_records.
    artifacts = [deepcopy(r['record']['value']['artifact']) for r in case['retained_records'] if r['record']['contract'] == 'AcquisitionReceipt']
    bundle = {'version': 'bvbrc_appservice_artifact_bundle_v1', 'original_task': case['original_task'],
        'artifacts': artifacts, 'input_bindings': [], 'query_bindings': [], 'supplied_scientific_metadata': [],
        'supplied_contents': [], 'acquisition_receipt_refs': [a['transfer']['receipt_ref'] for a in artifacts],
        'requested_selector_sha256': 'a' * 64, 'status': 'ok', 'missing_requirements': [], 'diagnostics': []}
    params = {'schema_version': 'bvbrc_genome_alignment_parameters_v1', 'analysis_id': 'E-offline-native',
        'document_slots': slots, 'calculation_plan': plan(requests)}
    return {'bundle': bundle, 'artifact_bytes': case['supplied_bytes'], 'supplied_values': [],
        'retained_records': case['retained_records'], 'requested_form': facade.requested_form_schema(fields), 'parameters': params}


def scientific_artifact(args):
    return next(a for a in args['bundle']['artifacts'] if a['role'] != 'task_manifest')


def replace_native(args, raw):
    """Change test bytes without forging corresponding positive C custody."""
    artifact = scientific_artifact(args)
    artifact['sha256'] = hashlib.sha256(raw).hexdigest()
    artifact['byte_count'] = artifact['transfer']['total_size'] = len(raw)
    args['artifact_bytes'][artifact['raw_artifact_ref']] = raw


@pytest.mark.parametrize('fmt,expected', [('mauve_v4', 690), ('mauve_backbone', 50), ('mauve_bbcols', 52), ('mauve1_xmfa', 40 / 48)])
def test_actual_public_facade_native_numbers_with_all_missing_reports(fmt, expected):
    args = arguments(fmt); before = deepcopy(args)
    result = facade.consume_bundle(**args)
    assert result['status'] == 'ok'
    assert result['facts']['native']['value']['value'] == expected
    assert result['missing_requirements'] and result['diagnostics']
    assert result['sheet']['components'] == result['components']
    assert result['sheet']['data']['associations']['artifacts'][0]['state'] == 'bound'
    assert args == before


@pytest.mark.parametrize('problem,code,state', [
    ('no_artifact', 'artifact_bytes_missing', 'missing'), ('bytes', 'artifact_bytes_missing', 'missing'),
    ('digest', 'artifact_digest_conflict', 'incompatible'), ('size', 'artifact_size_conflict', 'incompatible'),
    ('body', 'artifact_transfer_incomplete', 'missing'), ('object', 'artifact_transfer_incomplete', 'missing'),
    ('format', 'artifact_format_conflict', 'incompatible'), ('version', 'artifact_format_conflict', 'incompatible'),
    ('mode', 'artifact_format_conflict', 'incompatible'), ('ambiguous', 'artifact_selection_ambiguous', 'missing')])
def test_local_resolution_failure_and_original_request_identity(problem, code, state):
    args = arguments(); artifact = scientific_artifact(args)
    if problem == 'no_artifact': args['bundle']['artifacts'].remove(artifact)
    elif problem == 'bytes': del args['artifact_bytes'][artifact['raw_artifact_ref']]
    elif problem == 'digest': args['artifact_bytes'][artifact['raw_artifact_ref']] = b'x' * artifact['byte_count']
    elif problem == 'size': artifact['byte_count'] += 1; artifact['transfer']['total_size'] += 1
    elif problem == 'body': artifact['transfer'].update(body_complete=False, object_complete='no')
    elif problem == 'object': artifact['transfer']['object_complete'] = 'unknown'
    elif problem == 'format': artifact['declared_format']['format'] = 'mauve1_xmfa'
    elif problem == 'version': artifact['declared_format']['version'] = 'Mauve1'
    elif problem == 'mode': artifact['declared_format']['mode'] = 'mauveAligner'
    else:
        other = deepcopy(artifact); other['source_ref'] += ':other'; other['raw_artifact_ref'] += ':other'
        args['bundle']['artifacts'].append(other)
        args['parameters']['document_slots'][0].update(source_ref=None, raw_artifact_ref=None)
    result = facade.consume_bundle(**args)
    assert result['status'] == 'partial' and result['sheet'] is not None
    assert result['facts']['native']['state'] == state and result['facts']['native']['value'] is None
    assert result['components']['outcomes'][0]['request_id'] == 'anchors'
    assert 'bvbrc_genome_alignment_bundle_' + code in {r['reason_code'] for r in result['missing_requirements']}


@pytest.mark.parametrize('missing_position', [0, 1, 2])
def test_missing_request_first_middle_last_and_parse_once(monkeypatch, missing_position):
    args = arguments(); parameters = args['parameters']; request = parameters['calculation_plan']['requests'][0]
    parameters['document_slots'].append(slot('absent', 'mauve_v4'))
    parameters['document_slots'][-1]['source_ref'] = 'absent-source'
    requests = [dict(deepcopy(request), request_id=f'r{i}') for i in range(3)]
    requests[missing_position]['document_slot_id'] = 'absent'
    parameters['calculation_plan'] = plan(requests)
    args['requested_form'] = facade.requested_form_schema({f'f{i}': measurement(f'r{i}') for i in range(3)})
    calls = []; real = resolution.parse_mauve_v4
    def counted(*a, **k):
        calls.append(k); return real(*a, **k)
    monkeypatch.setattr(resolution, 'parse_mauve_v4', counted)
    result = facade.consume_bundle(**args)
    assert len(calls) == 1
    assert [o['request_id'] for o in result['components']['outcomes']] == ['r0', 'r1', 'r2']
    for i in range(3):
        fact = result['facts'][f'f{i}']; assert fact['request_ref'].endswith(f'/r{i}')
        assert (fact['value'] is None) == (i == missing_position)
        if i != missing_position: assert fact['value']['value'] == 690


def test_exact_c_forwarding_and_local_bad_neighbor_survival(monkeypatch):
    args = arguments(); calls = []
    bad = deepcopy(args['retained_records'][1]); bad['record']['source_ref'] = bad['receipt_content']['source_ref'] = 'synthetic:bad-neighbor'
    args['retained_records'] += (bad,)
    # Unknown finite retained JSON must reach both C readers unchanged.
    raw = b'{"example":17}'; binding = content(raw, 'other-json')
    args['artifact_bytes'][binding['artifact_ref']] = raw
    args['supplied_values'] = [{'evidence': {'content': binding, 'pointer': ''}, 'value': {'example': 17}}]
    for name in ('extract_genome_alignment_inputs', 'bind_genome_alignment_artifacts'):
        real = getattr(resolution, name)
        def capture(*a, _real=real, _name=name, **k):
            assert k['retained_records'] is args['retained_records']
            assert k['supplied_bytes'] is args['artifact_bytes']
            assert k['supplied_values'] == tuple(args['supplied_values'])
            calls.append((_name, k)); return _real(*a, **k)
        monkeypatch.setattr(resolution, name, capture)
    result = facade.consume_bundle(**args)
    assert len(calls) == 2 and result['status'] == 'ok'
    assert [a['role'] for a in calls[1][1]['artifacts']] == ['genome_alignment_primary']
    codes = {r['reason_code'] for r in result['missing_requirements']}
    assert 'bvbrc_genome_alignment_metadata_type_unsupported' in codes
    assert 'bvbrc_genome_alignment_metadata_record_unverified' in codes


def test_source_denominator_partial_and_native_denominator_usable():
    args = arguments(fields={'fraction': measurement(field='coverage_fraction')})
    native = facade.consume_bundle(**args)
    assert native['status'] == 'ok' and native['facts']['fraction']['value']['value'] == 690 / 693
    request = args['parameters']['calculation_plan']['requests'][0]
    request['use_inputs'] = True; request['selection']['denominator'] = 'validated_staged_length'
    source = facade.consume_bundle(**args)
    assert source['status'] == 'partial' and source['facts']['fraction']['value']['value'] is None
    assert source['facts']['fraction']['state'] == 'resolved'
    assert source['components']['outcomes'][0]['measurement']['value']['coverage'][0]['known_union_bases']['value'] == 690


def test_measured_zero_missing_and_not_measured_are_distinct_saved_cells():
    location = dict(interval_index=0, segment_index=0, member=member())
    args = arguments(fields={'zero': measurement('anchors', 'v4_member', 'selected_gap_count', **location),
                             'missing': measurement('anchors', 'v4_member', 'selected_canonical_count', **location)})
    result = facade.consume_bundle(**args)
    assert (result['facts']['zero']['value']['value'], result['facts']['zero']['value']['state']) == (0, 'available')
    assert (result['facts']['missing']['value']['value'], result['facts']['missing']['value']['state']) == (None, 'missing')
    args = arguments('mauve1_xmfa', {'not_measured': measurement('pairs', 'xmfa_pair', 'identity_fraction',
        block_index=1, member_a=1, member_b=2)})
    result = facade.consume_bundle(**args)
    assert result['facts']['not_measured']['state'] == 'resolved'
    assert (result['facts']['not_measured']['value']['value'], result['facts']['not_measured']['value']['state']) == (None, 'not_measured')


def test_truncated_selected_population_preserves_independent_native_measurement():
    args = arguments('mauve1_xmfa', {'truncated': measurement('pairs', 'xmfa_site', 'canonical_count', block_index=1, column_0based=0),
        'independent': measurement('pairs', 'xmfa_pair', 'identity_fraction', block_index=0, member_a=1, member_b=2)})
    artifact = scientific_artifact(args)
    replace_native(args, args['artifact_bytes'][artifact['raw_artifact_ref']].rstrip()[:-1])
    result = facade.consume_bundle(**args)
    assert (result['facts']['truncated']['value']['value'], result['facts']['truncated']['value']['state']) == (None, 'truncated')
    assert result['facts']['independent']['value']['value'] == 40 / 48


@pytest.mark.parametrize('status', ['partial', 'invalid', 'failed'])
def test_bundle_status_does_not_discard_independent_native_measurement(status):
    args = arguments(); args['bundle']['status'] = status
    result = facade.consume_bundle(**args)
    assert result['facts']['native']['value']['value'] == 690 and result['status'] == 'ok'


def test_original_bundle_reports_survive_alongside_usable_native_counts():
    from gene_annotation_episode.bvbrc_alignment_values import diagnostic, requirement
    args = arguments(); code = 'bvbrc_genome_alignment_bundle_artifact_bytes_missing'
    req = requirement('original-bundle-gap', kind='output_bytes', role=None, reason_code=code)
    diag = diagnostic(code, phase='publication', path='/original-required-output')
    args['bundle'].update(status='partial', missing_requirements=[req], diagnostics=[diag])
    result = facade.consume_bundle(**args)
    assert result['status'] == 'ok' and result['facts']['native']['value']['value'] == 690
    assert result['missing_requirements'][0] == result['sheet']['requirements'][0] == req
    assert result['diagnostics'][0] == result['sheet']['diagnostics'][0] == diag


def test_valid_other_application_is_invalid_and_malformed_arguments_raise():
    args = arguments(); args['bundle']['original_task']['required_application_id'] = 'MSA'
    args['bundle']['original_task']['native_application_id'] = 'MSA'
    args['retained_records'] = ()
    result = facade.consume_bundle(**args)
    assert result['status'] == 'invalid' and result['facts'] == {} and result['sheet'] is result['components'] is None
    args = arguments(); args['retained_records'] = []
    with pytest.raises(ValueError, match='argument_invalid'): facade.consume_bundle(**args)
    args = arguments(); args['bundle']['unexpected'] = True
    with pytest.raises(ValueError): facade.consume_bundle(**args)


@pytest.mark.parametrize('fmt,version', [('mauve_v4', '4'), ('mauve1_xmfa', 'Mauve1'), ('mauve_backbone', None), ('mauve_bbcols', None)])
def test_accepted_declared_versions_and_no_fallback(fmt, version, monkeypatch):
    args = arguments(fmt); scientific_artifact(args)['declared_format']['version'] = version
    result = facade.consume_bundle(**args)
    assert result['sheet']['data']['slot_resolutions'][0]['state'] == 'resolved'
    scientific_artifact(args)['declared_format']['version'] = 'unsupported'
    def fail(*a, **k): raise AssertionError('must not try a parser')
    for name in ('parse_mauve_v4', 'parse_mauve_xmfa', 'parse_mauve_backbone', 'parse_mauve_bbcols'):
        monkeypatch.setattr(resolution, name, fail)
    result = facade.consume_bundle(**args)
    assert result['sheet']['data']['slot_resolutions'][0]['state'] == 'incompatible'


def test_complete_transfer_but_syntactically_partial_native_preserves_selected_counts():
    args = arguments('mauve1_xmfa'); artifact = scientific_artifact(args)
    raw = args['artifact_bytes'][artifact['raw_artifact_ref']].rstrip()[:-1]
    artifact['sha256'] = hashlib.sha256(raw).hexdigest(); artifact['byte_count'] = len(raw); artifact['transfer']['total_size'] = len(raw)
    args['artifact_bytes'][artifact['raw_artifact_ref']] = raw
    result = facade.consume_bundle(**args)
    assert result['sheet']['data']['parsed_artifacts'][0]['parse_status'] == 'partial'
    assert result['facts']['native']['value']['value'] == 40 / 48
    assert result['status'] == 'partial'  # altered synthetic acquisition no longer proves object custody


def test_conflicting_selected_readers_are_contract_error_before_any_parse(monkeypatch):
    args = arguments(); other = deepcopy(args['parameters']['document_slots'][0])
    other['slot_id'] = 'same-other-reader'; other['reader']['encoding'] = 'utf-8'
    args['parameters']['document_slots'].append(other)
    monkeypatch.setattr(resolution, 'parse_mauve_v4', lambda *a, **k: pytest.fail('unexpected parse'))
    with pytest.raises(ValueError, match='slot_reader_conflict'): facade.consume_bundle(**args)


def test_multiple_explicit_slots_share_exactly_one_selected_artifact_parse(monkeypatch):
    args = arguments(); parameters = args['parameters']; first = parameters['document_slots'][0]
    parameters['document_slots'].append(dict(deepcopy(first), slot_id='alias'))
    parameters['calculation_plan']['requests'].append(dict(deepcopy(parameters['calculation_plan']['requests'][0]),
                                                          request_id='alias-request', document_slot_id='alias'))
    args['requested_form'] = facade.requested_form_schema({'first': measurement(), 'second': measurement('alias-request')})
    actual = resolution.parse_mauve_v4; calls = []
    def counted(*a, **k):
        calls.append(k); return actual(*a, **k)
    monkeypatch.setattr(resolution, 'parse_mauve_v4', counted)
    result = facade.consume_bundle(**args)
    assert len(calls) == len(result['sheet']['data']['parsed_artifacts']) == 1
    assert len(result['sheet']['data']['slot_resolutions']) == 2
    assert [o['request_id'] for o in result['components']['outcomes']] == ['anchors', 'alias-request']
    assert result['facts']['first']['value']['value'] == result['facts']['second']['value']['value'] == 690


@pytest.mark.parametrize('fmt', ['mauve_v4', 'mauve1_xmfa', 'mauve_backbone', 'mauve_bbcols'])
def test_declared_null_version_and_null_mode_are_supported_but_nonnull_modes_are_not(fmt):
    args = arguments(fmt); declaration = scientific_artifact(args)['declared_format']
    declaration.update(version=None, mode=None)
    assert facade.consume_bundle(**args)['sheet']['data']['slot_resolutions'][0]['state'] == 'resolved'
    declaration['mode'] = args['parameters']['document_slots'][0]['reader'].get('dialect', 'mauveAligner')
    result = facade.consume_bundle(**args)
    assert result['sheet']['data']['slot_resolutions'][0]['state'] == 'incompatible'
    assert any(r['reason_code'].endswith('artifact_format_conflict') for r in result['missing_requirements'])


@pytest.mark.parametrize('fmt', ['mauve_v4', 'mauve1_xmfa'])
@pytest.mark.parametrize('problem', ['unsupported', 'missing', 'conflicting'])
def test_actual_native_version_never_inferred_and_independent_slot_survives(fmt, problem):
    args = arguments(fmt); artifact = scientific_artifact(args)
    raw = args['artifact_bytes'][artifact['raw_artifact_ref']]
    first, rest = raw.split(b'\n', 1)
    unsupported = b'FormatVersion 5' if fmt == 'mauve_v4' else b'#FormatVersion Mauve2'
    changed = unsupported + b'\n' + rest if problem == 'unsupported' else rest if problem == 'missing' else first + b'\n' + unsupported + b'\n' + rest
    # Independent bytes use a distinct identity. No new C custody is invented.
    other = deepcopy(artifact)
    for key in ('raw_artifact_ref', 'source_ref'):
        other[key] += ':independent'
    args['bundle']['artifacts'].append(other); args['artifact_bytes'][other['raw_artifact_ref']] = raw
    other_slot = deepcopy(args['parameters']['document_slots'][0])
    other_slot.update(slot_id='independent', source_ref=other['source_ref'], raw_artifact_ref=other['raw_artifact_ref'])
    args['parameters']['document_slots'].append(other_slot)
    other_request = deepcopy(args['parameters']['calculation_plan']['requests'][0])
    other_request.update(request_id='independent', document_slot_id='independent')
    args['parameters']['calculation_plan']['requests'].append(other_request)
    selected = measurement() if fmt == 'mauve_v4' else measurement('pairs', 'xmfa_block', 'selected_column_count', block_index=0)
    args['requested_form'] = facade.requested_form_schema({'bad': selected, 'good': dict(deepcopy(selected), request_id='independent')})
    artifact['declared_format']['version'] = None
    replace_native(args, changed)
    result = facade.consume_bundle(**args)
    native = result['sheet']['data']['parsed_artifacts'][0]
    assert len(result['sheet']['data']['parsed_artifacts']) == 2
    if fmt == 'mauve1_xmfa' or problem == 'conflicting':
        assert native['document'] is not None and native['parse_status'] == 'partial'
    else:
        assert native['document'] is None and native['parse_status'] == 'invalid'
    assert result['sheet']['data']['slot_resolutions'][0]['state'] == 'incompatible'
    assert result['sheet']['data']['slot_resolutions'][0]['document_id'] is None
    assert result['facts']['bad']['state'] == 'incompatible' and result['facts']['bad']['value'] is None
    assert result['facts']['good']['value']['value'] == (690 if fmt == 'mauve_v4' else 52)
    assert result['status'] == 'partial'
    assert any(r['reason_code'].endswith('artifact_format_conflict') for r in result['missing_requirements'])


@pytest.mark.parametrize('mode', ['full_observed', 'partial_observed', 'partial_total', 'ignored_requested_range'])
def test_exact_transfer_ranges_and_totals(mode):
    args = arguments(); artifact = scientific_artifact(args); size = artifact['byte_count']; transfer = artifact['transfer']
    if mode == 'full_observed': transfer['observed_range'] = {'start': 0, 'end_inclusive': size - 1, 'total_size': size}
    elif mode == 'partial_observed':
        transfer.update(object_complete='no', total_size=size + 1,
                        observed_range={'start': 1, 'end_inclusive': size, 'total_size': size + 1})
    elif mode == 'partial_total': transfer.update(object_complete='unknown', total_size=size + 1)
    else: transfer['requested_range'] = [0, 1]
    result = facade.consume_bundle(**args)
    incomplete = mode in ('partial_observed', 'partial_total')
    assert result['sheet']['data']['slot_resolutions'][0]['state'] == ('missing' if incomplete else 'resolved')
    if incomplete: assert any(r['reason_code'].endswith('artifact_transfer_incomplete') for r in result['missing_requirements'])
