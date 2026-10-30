"""Native associations/count selection plus independent saved-sheet examples."""
from copy import deepcopy
import hashlib
import json
import socket
import subprocess

import pytest

from gene_annotation_episode.atac_differential_contracts import atac_track_extent
from gene_annotation_episode.atac_differential_inputs import parse_atac_bedgraph, parse_macs2_peaks_xls, parse_macs2_bdgdiff_bed
from gene_annotation_episode.atac_differential_sheet import build_atac_differential_sheet, select_atac_depth_counts
from gene_annotation_episode.atac_differential_scores import calculate_atac_interval_scores
from test_atac_differential_inputs import (NATIVE, artifact, callpeak, comparison, native_report,
                                           track_binding, codes, table_bytes)


def reference(length=12000):
    return dict(reference_id='toy', assembly_accession_version=None, source_refs=['supplied-sq'],
                contigs=[dict(chromosome='chrToy', length_bp=length, sequence_accession_version=None,
                              sequence_sha256=None, source_refs=['supplied-sq'])], aliases=[])


def samples(native=True):
    return [dict(sample_id=f's{i}', input_artifact_refs=[f'condition{i}.bam'] if native else [f'supplied-{i}'],
                 reference_id='toy', biospecimen_id=None, replicate_id=None, origin='synthetic_engineering_fixture') for i in (1, 2)]


def conditions():
    return [dict(condition_id=f'c{i}', label=f'condition {i}', sample_ids=[f's{i}']) for i in (1, 2)]


def native_inputs():
    bindings = [callpeak(1), callpeak(2)]
    tracks = []
    for role in ('signal1', 'background1', 'signal2', 'background2'):
        cp = bindings[int(role[-1]) - 1]
        filename = cp['artifact_roles']['signal_track' if role.startswith('signal') else 'background_track']
        raw = (NATIVE / 'bam_outputs' / filename).read_bytes()
        tracks.append(parse_atac_bedgraph(raw, artifact=artifact(raw, filename, producer=cp['producer_ref']),
                                         binding=track_binding(role, filename, native=True)))
    cp = comparison()
    differential = []
    for category, filename in cp['artifact_roles'].items():
        raw = (NATIVE / 'bam_outputs' / filename).read_bytes()
        differential.append(parse_macs2_bdgdiff_bed(raw, artifact=artifact(raw, filename, 'macs2_bdgdiff_bed5', cp['producer_ref']),
                                                  comparison=cp, category=category))
    xls = [native_report(1), native_report(2)]
    return dict(reference=reference(), samples=samples(), conditions=conditions(), callpeak_bindings=bindings,
                comparison=cp, tracks=tracks, peaks_xls=xls,
                narrowpeaks=[native_report(1, 'narrowpeak'), native_report(2, 'narrowpeak')],
                summits=[native_report(1, 'summits'), native_report(2, 'summits')], native_differential=differential,
                depth_selection=select_atac_depth_counts(xls, conditions=('c1', 'c2'), callpeak_bindings=bindings))


def explicit_inputs():
    tracks = []
    for role, filename in zip(('signal1', 'background1', 'signal2', 'background2'), ('t1.bdg', 'c1.bdg', 't2.bdg', 'c2.bdg'), strict=True):
        raw = (NATIVE / 'explicit_tracks' / filename).read_bytes()
        binding = track_binding(role, filename)
        binding.update(condition_id='fixture-c' + role[-1], sample_ids=['fixture-s' + role[-1]], reference_id='fixture-toy')
        tracks.append(parse_atac_bedgraph(raw, artifact=artifact(raw, filename), binding=binding))
    cp = comparison()
    cp.update(comparison_key='fixture-comparison', condition1_id='fixture-c1', condition2_id='fixture-c2',
              reference_id='fixture-toy', producer_ref='fixture-native-bdgdiff')
    cp['artifact_roles'].update(condition1='condition1.bed', condition2='condition2.bed')
    cp['selected_parameters'].update(depth1_lexeme='1', depth2_lexeme='2')
    differential = []
    for category, filename in cp['artifact_roles'].items():
        raw = (NATIVE / 'explicit_tracks' / filename).read_bytes()
        differential.append(parse_macs2_bdgdiff_bed(raw, artifact=artifact(raw, filename, 'macs2_bdgdiff_bed5', cp['producer_ref']),
                                                  comparison=cp, category=category))
    depths = dict(kind='explicit_declared_depths', conditions=[dict(condition_id=f'fixture-c{i}', sample_ids=[f'fixture-s{i}'],
        value=i, value_lexeme=str(i), unit='million_tags', population='synthetic_declared_treatment_depth',
        source_ref='supplied-depths', origin='synthetic_engineering_fixture', state='declared') for i in (1, 2)],
        compatible_population=True, issues=[])
    fixture_reference = reference(500)
    fixture_reference['reference_id'] = 'fixture-toy'
    fixture_samples = samples(False)
    fixture_conditions = conditions()
    for i, (sample, condition) in enumerate(zip(fixture_samples, fixture_conditions, strict=True), 1):
        sample.update(sample_id=f'fixture-s{i}', reference_id='fixture-toy')
        condition.update(condition_id=f'fixture-c{i}', sample_ids=[f'fixture-s{i}'])
    return dict(reference=fixture_reference, samples=fixture_samples, conditions=fixture_conditions, callpeak_bindings=[],
                comparison=cp, tracks=tracks, peaks_xls=[], narrowpeaks=[], summits=[], native_differential=differential,
                depth_selection=depths)


def test_actual_native_sheet_contains_all_numerical_rows_counts_and_original_bed_geometry(tmp_path):
    inputs = native_inputs()
    original = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == original
    assert [t['data_row_count'] for t in sheet['tracks']] == [110, 35, 210, 69]
    assert [d['count'] for d in sheet['depth_selection']['conditions']] == [100, 200]
    assert [r['reported_numbers']['treatment_total_tags']['value'] for r in sheet['peaks_xls']] == [105, 200]
    assert sheet['depth_selection']['compatible_population'] is True
    assert sheet['reference_relation'] == 'same_supplied_reference'
    assert sheet['normalization_compatibility'] == 'raw_compatible'
    assert sheet['coverage_completeness'] == 'partial_declared_domain'
    assert sheet['data_status'] == 'complete_reported_data'
    assert all(t['chromosome_extents'][0]['has_unreported_tail'] for t in sheet['tracks'])
    assert [link['status'] for link in sheet['peak_links']] == ['matched', 'matched']
    assert sheet['narrowpeaks'][1]['rows'][0]['display_score'] == 1045
    assert sheet['native_differential'][0]['rows'][0]['reported_start0'] == 907
    assert sheet['native_differential'][0]['rows'][0]['reported_end0'] == 1140
    assert sheet['native_differential'][0]['rows'][0]['reported_score'] == 147.378
    assert sheet['native_differential'][2]['data_row_count'] == 0
    assert not ({'condition_binding_conflict', 'reference_conflict', 'depth_population_conflict', 'metadata_conflict'} & codes(sheet))
    (tmp_path / 'filled_bam_native_sheet.json').write_text(json.dumps(sheet, indent=2, allow_nan=False) + '\n')


def test_explicit_synthetic_depths_never_become_observed_million_counts():
    sheet = build_atac_differential_sheet(**explicit_inputs())
    assert sheet['coverage_completeness'] == 'complete_declared_domain'
    assert sheet['data_status'] == 'complete_reported_data'
    assert sheet['depth_selection']['kind'] == 'explicit_declared_depths'
    assert [d['value'] for d in sheet['depth_selection']['conditions']] == [1, 2]
    assert all('count' not in d for d in sheet['depth_selection']['conditions'])
    assert sheet['peak_links'] == []
    assert sheet['tracks'][1]['binding']['role'] == 'model_background'


@pytest.mark.parametrize('case,expected', [('missing', 'missing'), ('conflict', 'conflicting'), ('zero', 'zero'), ('keep_all', 'missing')])
def test_depth_headers_zero_missing_conflicting_and_keep_all(case, expected):
    cp = callpeak(1)
    raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes()
    if case in ('missing', 'keep_all'):
        raw = raw.replace(b'# tags after filtering in treatment: 100\n', b'')
    if case == 'keep_all':
        cp['selected_parameters']['keep_duplicates'] = 'all'
    if case == 'conflict':
        raw = raw.replace(b'# tags after filtering in treatment: 100\n', b'# tags after filtering in treatment: 100\n# tags after filtering in treatment: 99\n')
    if case == 'zero':
        raw = raw.replace(b'# tags after filtering in treatment: 100\n', b'# tags after filtering in treatment: 0\n')
    report = parse_macs2_peaks_xls(raw, artifact=artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref']), callpeak=cp)
    selected = select_atac_depth_counts([report, native_report(2)], conditions=('c1', 'c2'), callpeak_bindings=[cp, callpeak(2)])
    assert selected['conditions'][0]['state'] == expected
    assert selected['conditions'][0]['count'] == (0 if case == 'zero' else None)
    assert report['reported_numbers']['treatment_total_tags']['value'] == 105
    assert selected['conditions'][1]['count'] == 200


def test_count_in_identity_bound_partial_report_is_still_an_actual_count():
    cp = callpeak()
    raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes()[:-12]
    a = artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref'])
    a['supplied_extent'] = 'partial'
    report = parse_macs2_peaks_xls(raw, artifact=a, callpeak=cp)
    selected = select_atac_depth_counts([report, native_report(2)], conditions=('c1', 'c2'), callpeak_bindings=[cp, callpeak(2)])
    assert report['state']['output_extent'] == 'partial'
    assert selected['conditions'][0]['state'] == 'observed'
    assert selected['conditions'][0]['count'] == 100


@pytest.mark.parametrize('field,value', [('paired_end', True), ('selected_format', 'BAMPE'), ('spmr', True), ('downsample', True), ('control', ['control.bam'])])
def test_unsupported_population_and_normalization_never_supply_raw_se_depth(field, value):
    bindings = [callpeak(), callpeak(2)]
    if field in ('spmr', 'downsample'):
        bindings[0]['selected_parameters'][field] = value
    elif field == 'control':
        bindings[0]['supplied_control_input_refs'] = value
    else:
        bindings[0][field] = value
    selected = select_atac_depth_counts([native_report(), native_report(2)], conditions=('c1', 'c2'), callpeak_bindings=bindings)
    assert selected['conditions'][0]['state'] == 'incompatible_mode'
    assert selected['conditions'][0]['count'] is None
    assert selected['compatible_population'] is False


def test_missing_or_ambiguous_run_never_selects_first_or_fabricates_identity():
    selected = select_atac_depth_counts([native_report()], conditions=('c1', 'c2'), callpeak_bindings=[callpeak()])
    assert selected['conditions'][1]['callpeak_run_key'] is None
    assert selected['conditions'][1]['source_artifact_ref'] is None
    assert selected['conditions'][1]['sample_ids'] == []
    same_condition = callpeak(2)
    same_condition['condition_id'] = 'c1'
    selected = select_atac_depth_counts([native_report(), native_report(2)], conditions=('c1', 'c2'), callpeak_bindings=[callpeak(), same_condition])
    assert selected['conditions'][0]['state'] == 'conflicting'
    assert selected['conditions'][0]['callpeak_run_key'] is None
    assert selected['conditions'][0]['count'] is None


def test_duplicate_report_and_identity_mismatch_do_not_supply_depth():
    bindings = [callpeak(), callpeak(2)]
    report = native_report()
    selected = select_atac_depth_counts([report, deepcopy(report), native_report(2)], conditions=('c1', 'c2'), callpeak_bindings=bindings)
    assert selected['conditions'][0]['state'] == 'conflicting'
    report['state']['identity'] = 'mismatch'
    report['state']['output_extent'] = 'unknown'
    selected = select_atac_depth_counts([report, native_report(2)], conditions=('c1', 'c2'), callpeak_bindings=bindings)
    assert selected['conditions'][0]['state'] == 'conflicting'


def test_reference_mismatch_bounds_and_aliases_require_explicit_mapping():
    inputs = explicit_inputs()
    inputs['tracks'][2]['binding']['reference_id'] = 'other-assembly'
    sheet = build_atac_differential_sheet(**inputs)
    assert sheet['reference_relation'] == 'conflicting'
    assert 'reference_conflict' in codes(sheet)
    inputs = explicit_inputs()
    inputs['reference']['contigs'][0]['length_bp'] = 400
    sheet = build_atac_differential_sheet(**inputs)
    assert 'coordinate_outside_reference' in codes(sheet)
    assert sheet['tracks'][0]['rows'][-1][6] == 500
    inputs = explicit_inputs()
    inputs['reference']['contigs'][0]['chromosome'] = 'Toy'
    assert 'unknown_chromosome' in codes(build_atac_differential_sheet(**inputs))
    inputs['reference']['aliases'] = [dict(source_chromosome='chrToy', target_chromosome='Toy', reference_id='fixture-toy', source_refs=['explicit-alias'])]
    mapped = build_atac_differential_sheet(**inputs)
    assert 'unknown_chromosome' not in codes(mapped)
    assert mapped['tracks'][0]['rows'][0][4] == 'chrToy'
    assert mapped['coverage_completeness'] == 'complete_declared_domain'


def test_unknown_reference_lengths_do_not_come_from_last_endpoint():
    inputs = explicit_inputs()
    inputs['reference']['contigs'][0]['length_bp'] = None
    sheet = build_atac_differential_sheet(**inputs)
    assert sheet['coverage_completeness'] == 'unknown'
    assert sheet['tracks'][0]['chromosome_extents'][0]['reference_length_bp'] is None
    assert sheet['tracks'][0]['chromosome_extents'][0]['has_unreported_tail'] is None


def test_missing_roles_preserve_exact_slots_with_no_invented_artifact():
    inputs = explicit_inputs()
    inputs['tracks'].pop(1)
    inputs['native_differential'].pop()
    inputs['comparison']['artifact_roles']['common'] = None
    sheet = build_atac_differential_sheet(**inputs)
    assert len(sheet['tracks']) == 4
    missing = sheet['tracks'][1]
    assert missing['binding']['track_key'] == 'background1'
    assert missing['binding']['source_artifact_ref'] is None
    assert missing['artifact']['artifact_ref'] is None
    assert missing['binding']['value_unit'] is None
    assert missing['native_writer_precision'] == 'unknown'
    assert missing['rows'] == []
    assert missing['data_row_count'] is None
    assert len(sheet['native_differential']) == 3
    assert sheet['native_differential'][-1]['artifact']['artifact_ref'] is None
    assert sheet['data_status'] == 'partial_reported_data'


def test_duplicate_track_key_is_invalid_assembly_without_mutation():
    inputs = explicit_inputs()
    inputs['tracks'].append(deepcopy(inputs['tracks'][0]))
    before = deepcopy(inputs)
    with pytest.raises(ValueError, match='duplicate_atac_track_key'):
        build_atac_differential_sheet(**inputs)
    assert inputs == before


@pytest.mark.parametrize('raw', [b'', b'chrToy\t0\t12000\t0.00000\n'])
def test_content_addressed_equal_backgrounds_preserve_both_producers_and_roles(raw):
    inputs = native_inputs()
    shared_ref = 'sha256:' + hashlib.sha256(raw).hexdigest()
    for index, role in ((1, 'background1'), (3, 'background2')):
        cp = inputs['callpeak_bindings'][int(role[-1]) - 1]
        cp['artifact_roles']['background_track'] = shared_ref
        inputs['tracks'][index] = parse_atac_bedgraph(raw,
            artifact=artifact(raw, shared_ref, producer=cp['producer_ref']),
            binding=track_binding(role, shared_ref, native=True))
    before = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == before
    backgrounds = [sheet['tracks'][1], sheet['tracks'][3]]
    assert [t['binding_key'] for t in backgrounds] == ['background1', 'background2']
    assert [t['artifact']['producer_run_ref'] for t in backgrounds] == ['native-callpeak-1', 'native-callpeak-2']
    assert [t['artifact']['artifact_ref'] for t in backgrounds] == [shared_ref, shared_ref]
    assert [t['data_row_count'] for t in backgrounds] == [int(bool(raw)), int(bool(raw))]
    assert all(t['state']['output_extent'] == 'complete' for t in backgrounds)
    sharing = [i for i in sheet['issues'] if i['field'] == 'shared_artifact_content']
    assert len(sharing) == 1
    assert sharing[0]['code'] == 'duplicate_record' and sharing[0]['requirement'] == 'none'
    assert sheet['depth_selection']['compatible_population'] is True
    assert not ({'condition_binding_conflict', 'depth_population_conflict', 'metadata_conflict'} & codes(sheet))


@pytest.mark.parametrize('same_sample', [False, True])
def test_explicit_shared_native_inputs_retain_counts_without_independent_replication(same_sample):
    # Engineering fixture: two separately declared occurrences of the same
    # native source bytes. Each occurrence retains its own producer/run binding.
    inputs = native_inputs()
    cp1 = inputs['callpeak_bindings'][0]
    cp2 = deepcopy(cp1)
    cp2.update(run_key='callpeak-2', condition_id='c2', producer_ref='native-callpeak-2',
               sample_ids=['s1'] if same_sample else ['s2'])
    inputs['callpeak_bindings'][1] = cp2
    inputs['conditions'][1]['sample_ids'] = deepcopy(cp2['sample_ids'])
    inputs['samples'][1]['input_artifact_refs'] = ['condition1.bam']
    for index, source_index, role in ((2, 0, 'signal2'), (3, 1, 'background2')):
        track = deepcopy(inputs['tracks'][source_index])
        track['binding_key'] = role
        track['binding'].update(track_key=role, condition_id='c2', sample_ids=deepcopy(cp2['sample_ids']),
                                callpeak_run_key='callpeak-2')
        track['artifact']['producer_run_ref'] = cp2['producer_ref']
        inputs['tracks'][index] = track
    for reports in ('peaks_xls', 'narrowpeaks', 'summits'):
        report = deepcopy(inputs[reports][0])
        report.update(binding_key='callpeak-2', callpeak_run_key='callpeak-2')
        report['artifact']['producer_run_ref'] = cp2['producer_ref']
        inputs[reports][1] = report
    inputs['native_differential'] = []
    inputs['comparison']['selected_parameters']['depth2_lexeme'] = '0.0001'
    inputs['depth_selection'] = select_atac_depth_counts(inputs['peaks_xls'], conditions=('c1', 'c2'),
                                                       callpeak_bindings=inputs['callpeak_bindings'])
    before = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == before
    depths = sheet['depth_selection']
    assert depths['compatible_population'] is True
    assert [d['count'] for d in depths['conditions']] == [100, 100]
    assert [d['callpeak_run_key'] for d in depths['conditions']] == ['callpeak-1', 'callpeak-2']
    assert [d['source_artifact_ref'] for d in depths['conditions']] == ['condition1_peaks.xls'] * 2
    for issues in (depths['issues'], sheet['issues']):
        shared = [i for i in issues if i['field'] in ('shared_samples', 'shared_treatment_inputs', 'shared_artifact_content')]
        assert {i['field'] for i in shared} == ({'shared_treatment_inputs', 'shared_artifact_content', 'shared_samples'}
                                               if same_sample else {'shared_treatment_inputs', 'shared_artifact_content'})
        assert all(i['code'] == 'duplicate_record' and i['requirement'] == 'none' for i in shared)
    assert len(sheet['tracks']) == 4
    assert all(s['replicate_id'] is None for s in sheet['samples'])
    assert not ({'condition_binding_conflict', 'depth_population_conflict', 'metadata_conflict'} & codes(sheet))


@pytest.mark.parametrize('mismatch', ['producer', 'role', 'run'])
def test_true_swapped_track_producer_or_role_still_conflicts(mismatch):
    inputs = native_inputs()
    track = inputs['tracks'][2]
    if mismatch == 'producer':
        track['artifact']['producer_run_ref'] = 'native-callpeak-1'
    elif mismatch == 'role':
        track['binding']['role'] = 'model_background'
    else:
        track['binding']['callpeak_run_key'] = 'callpeak-1'
    before = deepcopy(inputs)
    sheet = build_atac_differential_sheet(**inputs)
    assert inputs == before
    conflicts = [i for i in sheet['issues'] if i['code'] == 'condition_binding_conflict']
    assert any(i['binding_key'] == 'signal2' for i in conflicts)
    assert sheet['tracks'][2]['rows'] == track['rows']


@pytest.mark.parametrize('normalization,expected', [('spmr', 'incompatible'), ('unknown', 'unknown')])
def test_normalization_does_not_change_native_track_values(normalization, expected):
    inputs = explicit_inputs()
    inputs['tracks'][0]['binding']['normalization'] = normalization
    original = deepcopy(inputs['tracks'][0]['rows'])
    sheet = build_atac_differential_sheet(**inputs)
    assert sheet['normalization_compatibility'] == expected
    assert sheet['tracks'][0]['rows'] == original


def test_peak_links_reject_duplicate_names_disagreements_but_not_display_rounding():
    inputs = native_inputs()
    inputs['narrowpeaks'][0]['rows'][0]['display_score'] = 517
    assert build_atac_differential_sheet(**inputs)['peak_links'][0]['status'] == 'matched'
    inputs['narrowpeaks'][0]['rows'][0]['end0'] += 1
    assert build_atac_differential_sheet(**inputs)['peak_links'][0]['status'] == 'conflicting'
    inputs = native_inputs()
    duplicate = deepcopy(inputs['narrowpeaks'][0]['rows'][0])
    duplicate['row_ordinal'] = 1
    inputs['narrowpeaks'][0]['rows'].append(duplicate)
    inputs['narrowpeaks'][0]['readable_data_row_count'] = 2
    inputs['narrowpeaks'][0]['data_row_count'] = 2
    sheet = build_atac_differential_sheet(**inputs)
    assert sheet['peak_links'][0]['status'] == 'ambiguous'
    assert sheet['peak_links'][0]['narrowpeak_row_ordinals'] == [0, 1]


def test_retained_numeric_table_manifest_carries_actual_sheet_population():
    inputs = explicit_inputs()
    for track in inputs['tracks']:
        _, manifest = table_bytes(track['rows'])
        manifest['source_artifact_ref'] = track['artifact']['artifact_ref']
        track['rows'] = manifest
        track['ordered_row_index'] = None
    sheet = build_atac_differential_sheet(**inputs)
    assert all(t['rows']['row_count'] == 5 for t in sheet['tracks'])
    assert sheet['coverage_completeness'] == 'complete_declared_domain'
    assert sheet['tracks'][0]['rows']['columns'][-2:] == ['value_numeric', 'value_lexeme']


def test_forged_native_depth_or_incompatible_declared_population_is_qualified():
    inputs = native_inputs()
    inputs['depth_selection']['conditions'][0].update(count=105, count_lexeme='105')
    sheet = build_atac_differential_sheet(**inputs)
    assert sheet['depth_selection']['compatible_population'] is False
    assert 'depth_population_conflict' in codes(sheet)
    assert sheet['depth_selection']['conditions'][0]['count'] == 105
    inputs = explicit_inputs()
    inputs['depth_selection']['conditions'][1]['unit'] = 'tags'
    assert build_atac_differential_sheet(**inputs)['depth_selection']['compatible_population'] is False


def test_saved_sheet_json_recalculation_without_acquisition_or_input_mutation(monkeypatch, tmp_path):
    saved_path = tmp_path / 'saved_atac_native_sheet.json'
    saved_path.write_text(json.dumps(build_atac_differential_sheet(**explicit_inputs()), indent=2, allow_nan=False) + '\n')
    saved = json.loads(saved_path.read_text())
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError('acquisition or native execution forbidden during recalculation')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    rows = {track['binding_key']: track['rows'][1] for track in saved['tracks']}
    depths = saved['depth_selection']['conditions']
    arguments = dict(signal1=rows['signal1'][7], background1=rows['background1'][7],
                     signal2=rows['signal2'][7], background2=rows['background2'][7],
                     depth1=depths[0]['value'], depth2=depths[1]['value'], depth_unit=depths[0]['unit'])
    baseline = calculate_atac_interval_scores(**arguments, pseudocount=0.01)
    changed = calculate_atac_interval_scores(**arguments, pseudocount=1)
    assert baseline['likelihoods']['condition1_vs_condition2']['native_float32']['value'] == 17.7408447265625
    assert baseline['likelihoods']['condition1_vs_condition2'] != changed['likelihoods']['condition1_vs_condition2']
    assert saved == before
    assert saved['native_differential'][0]['rows'][0]['reported_score'] == 17.7408


def test_extent_adapter_preserves_failed_missing_unverified_and_complete_states():
    track = explicit_inputs()['tracks'][0]
    assert atac_track_extent(track) == 'complete'
    track['state']['identity'] = 'unverified'
    assert atac_track_extent(track) == 'partial'
    track['artifact']['producer_outcome'] = 'failed'
    assert atac_track_extent(track) == 'failed'
    track['state']['availability'] = 'missing'
    assert atac_track_extent(track) == 'missing'


def test_native_sheet_to_retained_stream_to_separate_interval_calculator():
    from gene_annotation_episode.atac_differential_inputs import iter_atac_track_rows, iter_atac_track_table_rows
    from gene_annotation_episode.atac_differential_calculations import (
        iter_atac_track_segments, iter_atac_interval_components, iter_atac_differential_regions,
    )
    sheet = build_atac_differential_sheet(**explicit_inputs())
    ports = {}
    for track in sheet['tracks']:
        raw, manifest = table_bytes(track['rows'], order='chromosome_start_end_source_ordinal')
        manifest['source_artifact_ref'] = track['artifact']['artifact_ref']
        rows = iter_atac_track_table_rows([raw], table=manifest)
        ports[track['binding_key']] = dict(rows=iter_atac_track_rows(track, chromosome='chrToy', ordered_rows=rows),
                                          extent=atac_track_extent(track), unlocated_invalid_row_count=track['unlocated_invalid_row_count'])
    segments = iter_atac_track_segments(ports, intervals=[dict(chromosome='chrToy', start=0, end=500)])
    components = list(iter_atac_interval_components(segments, depth1=1, depth2=2, depth_unit='million_tags', pseudocount=0.01))
    assert len(components) == 5
    assert [(r['start'], r['end']) for r in components] == [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500)]
    regions = list(iter_atac_differential_regions(components, cutoff=3, min_length_bp=50, max_gap_bp=0))
    by_category = {r['category']: r for r in regions}
    assert (by_category['condition1']['start'], by_category['condition1']['end']) == (100, 200)
    assert by_category['condition1']['native_float32_mean_score'] == 17.7408447265625
    assert (by_category['condition2']['start'], by_category['condition2']['end']) == (300, 400)
    assert by_category['condition2']['native_float32_mean_score'] == 12.148710250854492
    assert (by_category['common']['start'], by_category['common']['end']) == (200, 300)
    assert sheet['native_differential'][0]['rows'][0]['reported_start0'] == 0
    assert sheet['native_differential'][0]['rows'][0]['reported_score'] == 17.7408


def test_outside_reference_row_stays_exact_with_source_located_issue():
    inputs = explicit_inputs()
    inputs['reference']['contigs'][0]['length_bp'] = 450
    original = deepcopy(inputs['tracks'][0])
    sheet = build_atac_differential_sheet(**inputs)
    track = sheet['tracks'][0]
    assert track['rows'] == original['rows']
    assert track['ordered_row_index'] == original['ordered_row_index']
    outside = next(i for i in track['issues'] if i['code'] == 'coordinate_outside_reference')
    assert outside['row_ordinals'] == [4]
    assert outside['locations'] == [dict(line_number=5, byte_start=68, byte_end=85)]


def test_unsupported_callpeak_scale_cannot_leave_sheet_raw_compatible():
    inputs = native_inputs()
    inputs['callpeak_bindings'][0]['selected_parameters']['spmr'] = True
    sheet = build_atac_differential_sheet(**inputs)
    assert sheet['normalization_compatibility'] == 'incompatible'
    assert sheet['tracks'][0]['rows'][50][7] == 50
