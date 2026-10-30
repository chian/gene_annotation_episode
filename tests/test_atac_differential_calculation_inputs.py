"""Bridge010/011 checks using retained native bytes and explicit counterexamples."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.atac_differential_calculation_inputs import prepare_atac_calculation_inputs
from gene_annotation_episode.atac_differential_calculations import (
    iter_atac_track_segments, iter_atac_interval_components, iter_atac_differential_regions,
)
from gene_annotation_episode.atac_differential_contracts import AtacTableReadError
from gene_annotation_episode.atac_differential_inputs import (
    iter_atac_track_table_rows, parse_atac_bedgraph, parse_macs2_peaks_xls,
)
from gene_annotation_episode.atac_differential_sheet import build_atac_differential_sheet, select_atac_depth_counts
from gene_annotation_episode.atac_reference_observations import parse_atac_bam_reference
from test_atac_differential_inputs import NATIVE, artifact, codes, table_bytes
from test_atac_differential_sheet import explicit_inputs, native_inputs


ROLES = ('signal1', 'background1', 'signal2', 'background2')
LIKELIHOODS = ('condition1_vs_background', 'condition2_vs_background', 'condition1_vs_condition2')
HEADERS = Path(__file__).resolve().parents[1] / 'verification/tool_graders_atac_calculation_bridge_2026-10-27_467/native_headers'


def population(start=0, end=500, chromosome='chrToy'):
    return [dict(chromosome=chromosome, start=start, end=end)]


def sheet(native=False):
    return build_atac_differential_sheet(**(native_inputs_with_headers() if native else explicit_inputs()))


def header_report(raw, run, ordinal=0, **artifact_changes):
    # Full header bytes are retained468 observations in the baseline case.
    # Modified text in counterexamples is explicitly synthetic test data.
    descriptor = artifact(raw, 'header-' + hashlib.sha256(raw).hexdigest(),
                          'sam_header_text', 'retained-header-inspection')
    descriptor.update(producer_name='pysam', producer_version='0.23.3',
                      producer_source_ref='retained468-input-inspection')
    descriptor.update(artifact_changes)
    return parse_atac_bam_reference(raw, artifact=descriptor, callpeak_run_key=run['run_key'],
                                    input_ordinal=ordinal, input_artifact_ref=run['treatment_input_refs'][ordinal])


def native_inputs_with_headers():
    inputs = native_inputs()
    inputs['bam_references'] = [header_report((HEADERS / f'condition{i}.sam').read_bytes(), run)
                                for i, run in enumerate(inputs['callpeak_bindings'], 1)]
    return inputs


def track(saved, role):
    key = saved['comparison']['track_keys'][role]
    return next(t for t in saved['tracks'] if t['binding_key'] == key)


def replace_track(saved, role, raw, **changes):
    old = track(saved, role)
    descriptor = deepcopy(old['artifact'])
    descriptor.update(expected_sha256=hashlib.sha256(raw).hexdigest() if raw is not None else None,
                      expected_size_bytes=len(raw) if raw is not None else None)
    descriptor.update(changes)
    replacement = parse_atac_bedgraph(raw, artifact=descriptor, binding=old['binding'])
    saved['tracks'][saved['tracks'].index(old)] = replacement
    return replacement


def externalize(saved, roles=ROLES, *, bad_hash=(), failing=(), observed=None):
    streams = {}
    for role in roles:
        table = track(saved, role)
        rows = table['rows']
        raw, manifest = table_bytes(rows, order='chromosome_start_end_source_ordinal')
        manifest.update(artifact_ref='numeric-' + role, source_artifact_ref=table['artifact']['artifact_ref'])
        if role in bad_hash:
            manifest['sha256'] = '0' * 64
        table['rows'], table['ordered_row_index'] = manifest, None

        def chunks(raw=raw, role=role):
            for line in raw.splitlines(keepends=True):
                if observed is not None:
                    observed.append(role)
                yield line
            if role in failing:
                raise OSError('synthetic late read failure')

        streams[table['binding_key']] = iter_atac_track_table_rows(chunks(), table=manifest)
    return streams


def components(prepared, pseudocount=0.01):
    return list(iter_atac_interval_components(
        iter_atac_track_segments(prepared['tracks'], intervals=prepared['intervals']),
        depth1=prepared['depth1'], depth2=prepared['depth2'], depth_unit=prepared['depth_unit'],
        pseudocount=pseudocount))


def region_rows(records, cutoff=3):
    return list(iter_atac_differential_regions(records, cutoff=cutoff, min_length_bp=50, max_gap_bp=0))


def likelihoods(record):
    return [record['scores']['likelihoods'][name]['native_float32']['value'] for name in LIKELIHOODS]


@pytest.mark.parametrize('external', [False, True])
def test_retained_native_tracks_actual_parsers_sheet_bridge_all_fifteen_scores_and_three_regions(external):
    saved = sheet()
    streams = externalize(saved) if external else None
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(), ordered_track_rows=streams)
    records = components(prepared)
    assert [(r['start'], r['end']) for r in records] == [(i, i + 100) for i in range(0, 500, 100)]
    assert (prepared['depth1'], prepared['depth2'], prepared['depth_unit']) == (1, 2, 'million_tags')
    assert prepared['eligibility'] == dict(population='usable', tracks={r: 'usable' for r in ROLES}, depths='usable')
    oracle = json.loads((NATIVE / 'explicit_tracks/NATIVE_DIAGNOSTIC.json').read_text())['arrays'][0]
    expected = list(zip(*(oracle['native_' + name] for name in LIKELIHOODS), strict=True))
    assert [tuple(likelihoods(record)) for record in records] == expected
    regions = region_rows(records)
    by_category = {r['category']: r for r in regions}
    assert len(regions) == 3
    for category, start, end, score in (
        ('condition1', 100, 200, 17.7408447265625),
        ('common', 200, 300, 5.425064273367752e-7),
        ('condition2', 300, 400, 12.148710250854492),
    ):
        r = by_category[category]
        assert (r['start'], r['end'], r['native_float32_mean_score']) == (start, end, score)
    assert saved == before
    assert saved['native_differential'][0]['rows'][0]['reported_start0'] == 0
    assert saved['native_differential'][0]['rows'][0]['reported_score'] == 17.7408
    output = os.environ.get('ATAC467_NATIVE_EXAMPLE_PATH')
    if output and not external:
        Path(output).write_text(json.dumps(dict(
            provenance='retained MACS2 2.2.9.1 output from synthetic engineering tracks',
            native_sheet=saved, intervals=records, regions=regions,
            depth_operands=[prepared['depth1'], prepared['depth2']], depth_unit=prepared['depth_unit'],
            eligibility=prepared['eligibility']), indent=2, allow_nan=False) + '\n')


def test_retained_bam_outputs_use_postfilter_counts_not_totals_and_preserve_unknown_tails():
    saved = sheet(native=True)
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(end=12000))
    records = components(prepared)
    assert (prepared['depth1'], prepared['depth2'], prepared['depth_unit']) == (100, 200, 'tags')
    assert [r['reported_numbers']['treatment_total_tags']['value'] for r in saved['peaks_xls']] == [105, 200]
    tail = next(r for r in records if r['start'] == 10060)
    assert tail['end'] == 12000
    assert set(tail['states'].values()) == {'missing'}
    assert likelihoods(tail) == [None, None, None]
    assert any(r['start'] >= 8060 and r['states']['signal1'] == 'missing'
               and r['states']['signal2'] == 'observed' for r in records)
    assert records[0]['states']['signal1'] == 'observed' and records[0]['values']['signal1'] == 0
    assert saved['native_differential'][2]['data_row_count'] == 0
    assert [[(r['chromosome'], r['length_bp'], r['sequence_md5']) for r in report['rows']]
            for report in saved['bam_references']] == [[('chrToy', 12000, None)]] * 2
    assert any(i['code'] == 'sequence_identity_unknown' for i in prepared['issues'])
    assert saved == before
    output = os.environ.get('ATAC467_BAM_EXAMPLE_PATH')
    if output:
        Path(output).write_text(json.dumps(dict(
            provenance='retained MACS2 BAM outputs plus actual retained pysam header observations',
            native_sheet=saved, intervals=records, regions=region_rows(records),
            depth_operands=[prepared['depth1'], prepared['depth2']], depth_unit=prepared['depth_unit'],
            eligibility=prepared['eligibility'], issues=prepared['issues']), indent=2, allow_nan=False) + '\n')


def test_historical_native_sheet_without_actual_bam_dictionary_is_readable_but_not_verified():
    saved = build_atac_differential_sheet(**native_inputs())
    saved.pop('bam_references', None)
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert set(prepared['eligibility']['tracks'].values()) == {'unavailable'}
    assert (prepared['depth1'], prepared['depth2']) == (100, 200)
    assert all(set(r['states'].values()) == {'missing'} for r in components(prepared))
    assert 'metadata_missing' in codes(prepared)
    assert saved == before


@pytest.mark.parametrize('case', ['length', 'missing_sq', 'duplicate_sq', 'duplicate_sn', 'invalid_ln',
                                   'invalid_m5', 'bare_m5', 'partial', 'wrong_format', 'unverified', 'unlocated'])
def test_native_bam_dictionary_defect_disables_only_affected_run(case):
    inputs = native_inputs_with_headers()
    raw = (HEADERS / 'condition1.sam').read_bytes()
    changes = {}
    if case == 'length':
        raw = raw.replace(b'LN:12000', b'LN:12001')
    elif case == 'missing_sq':
        raw = raw.splitlines(keepends=True)[0]
    elif case == 'duplicate_sq':
        raw += raw.splitlines(keepends=True)[1]
    elif case == 'duplicate_sn':
        raw = raw.replace(b'SN:chrToy', b'SN:chrToy\tSN:chrToy')
    elif case == 'invalid_ln':
        raw = raw.replace(b'LN:12000', b'LN:-1')
    elif case == 'invalid_m5':
        raw = raw.rstrip(b'\n') + b'\tM5:bad\n'
    elif case == 'bare_m5':
        raw = raw.rstrip(b'\n') + b'\tM5\n'
    elif case == 'partial':
        changes['supplied_extent'] = 'partial'
    elif case == 'wrong_format':
        changes['format'] = 'not_sam_header'
    elif case == 'unverified':
        changes['expected_sha256'] = None
        changes['expected_size_bytes'] = None
    else:
        raw += b'@SQ\tLN:10\n'
    inputs['bam_references'][0] = header_report(raw, inputs['callpeak_bindings'][0], **changes)
    saved = build_atac_differential_sheet(**inputs)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert prepared['eligibility']['tracks'] == dict(signal1='unavailable', background1='unavailable',
                                                     signal2='usable', background2='usable')
    assert (prepared['depth1'], prepared['depth2']) == (100, 200)
    records = components(prepared)
    assert all(r['states']['signal1'] == 'missing' for r in records)
    assert all(r['states']['signal2'] == 'observed' for r in records)
    assert likelihoods(records[0])[1] is not None


@pytest.mark.parametrize('field', ['callpeak_run_key', 'input_ordinal', 'input_artifact_ref'])
def test_actual_bam_header_must_match_the_exact_selected_input_occurrence(field):
    saved = sheet(native=True)
    report = saved['bam_references'][0]
    report[field] = 1 if field == 'input_ordinal' else 'wrong'
    if field in ('callpeak_run_key', 'input_ordinal'):
        report['binding_key'] = f"{report['callpeak_run_key']}:input:{report['input_ordinal']}"
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert prepared['eligibility']['tracks']['signal1'] == 'unavailable'
    assert prepared['eligibility']['tracks']['signal2'] == 'usable'


@pytest.mark.parametrize('extra', [b'@SQ\tSN:extra\tLN:500\n', b'@SQ\tSN:extra\tLN:not-a-number\n',
                                  b'@CO\tretained irrelevant header comment\n'])
def test_unselected_extra_dictionary_rows_and_comments_do_not_invalidate_selected_population(extra):
    inputs = native_inputs_with_headers()
    raw = (HEADERS / 'condition1.sam').read_bytes() + extra
    inputs['bam_references'][0] = header_report(raw, inputs['callpeak_bindings'][0])
    saved = build_atac_differential_sheet(**inputs)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(100, 200))
    assert set(prepared['eligibility']['tracks'].values()) == {'usable'}
    assert len(components(prepared)) == 1
    assert len(saved['bam_references'][0]['rows']) == (1 if extra.startswith(b'@CO') else 2)


def test_actual_bam_alias_mapping_requires_explicit_reference_alias():
    inputs = native_inputs_with_headers()
    raw = (HEADERS / 'condition1.sam').read_bytes().replace(b'SN:chrToy', b'SN:Toy')
    inputs['bam_references'][0] = header_report(raw, inputs['callpeak_bindings'][0])
    saved = build_atac_differential_sheet(**inputs)
    assert prepare_atac_calculation_inputs(saved, intervals=population())['eligibility']['tracks']['signal1'] == 'unavailable'
    saved['reference']['aliases'] = [dict(source_chromosome='Toy', target_chromosome='chrToy',
                                         reference_id='toy', source_refs=['explicit'])]
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert set(prepared['eligibility']['tracks'].values()) == {'usable'}
    assert saved['bam_references'][0]['rows'][0]['chromosome'] == 'Toy'


@pytest.mark.parametrize('second_digest,usable', [('a' * 32, True), ('b' * 32, False), (None, True)])
def test_present_bam_sequence_md5_conflicts_are_reference_conflicts_unknown_stays_unknown(second_digest, usable):
    inputs = native_inputs_with_headers()
    for i, digest in enumerate(('a' * 32, second_digest)):
        raw = (HEADERS / f'condition{i + 1}.sam').read_bytes()
        if digest is not None:
            raw = raw.rstrip(b'\n') + b'\tM5:' + digest.encode() + b'\n'
        inputs['bam_references'][i] = header_report(raw, inputs['callpeak_bindings'][i])
    # Reference SHA256 is a distinct quantity, never compared against M5.
    inputs['reference']['contigs'][0]['sequence_sha256'] = 'c' * 64
    saved = build_atac_differential_sheet(**inputs)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert set(prepared['eligibility']['tracks'].values()) == {'usable' if usable else 'unavailable'}
    if not usable:
        assert any(i['code'] == 'reference_conflict' and i['field'] == 'sequence_md5' for i in prepared['issues'])
    if second_digest is None:
        assert 'sequence_identity_unknown' in codes(prepared)


def test_actual_same_header_content_remains_two_bound_input_occurrences_and_saved_only_recalculates(monkeypatch):
    saved = json.loads(json.dumps(sheet(native=True)))
    first, second = saved['bam_references']
    assert first['artifact']['artifact_ref'] == second['artifact']['artifact_ref']
    assert first['input_artifact_ref'] != second['input_artifact_ref']
    assert first['callpeak_run_key'] != second['callpeak_run_key']
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError('original BAM and acquisition unavailable during saved recalculation')
    monkeypatch.setattr('builtins.open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert prepared['eligibility']['tracks']['signal1'] == 'usable'
    assert components(prepared)
    assert saved == before


@pytest.mark.parametrize('defect', ['missing', 'reference', 'normalization', 'role', 'sample', 'condition', 'unit', 'background', 'format', 'identity'])
def test_independent_background2_defects_keep_other_two_likelihood_components(defect):
    saved = sheet()
    t = track(saved, 'background2')
    if defect == 'missing':
        replace_track(saved, 'background2', None)
    elif defect == 'reference':
        t['binding']['reference_id'] = 'different-reference'
    elif defect == 'normalization':
        t['binding']['normalization'] = 'spmr'
    elif defect == 'role':
        t['binding']['role'] = 'signal'
    elif defect == 'sample':
        t['binding']['sample_ids'] = ['fixture-s1']
    elif defect == 'condition':
        t['binding']['condition_id'] = 'fixture-c1'
    elif defect == 'unit':
        t['binding']['value_unit'] = 'supplied_signal'
    elif defect == 'background':
        t['binding']['background_origin'] = 'self_model'
    elif defect == 'format':
        replace_track(saved, 'background2', b'chrToy\t0\t500\t2\nbad\n', format='unrelated_format')
    elif defect == 'identity':
        replace_track(saved, 'background2', b'chrToy\t0\t500\t2\n', expected_sha256='0' * 64)
    # Copied summary claims cannot override the actual operands above.
    saved['reference_relation'] = 'same_supplied_reference'
    saved['normalization_compatibility'] = 'raw_compatible'
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    records = components(prepared)
    assert prepared['eligibility']['tracks']['background2'] == ('missing' if defect == 'missing' else 'unavailable')
    assert prepared['tracks']['background2']['extent'] == ('missing' if defect == 'missing' else 'failed')
    scores = likelihoods(records[1])
    assert scores[0] is not None and scores[1] is None and scores[2] == 17.7408447265625
    assert records[1]['states']['background2'] == 'missing'
    assert saved == before


@pytest.mark.parametrize('defect', ['swapped_artifact_role', 'wrong_producer', 'wrong_run', 'wrong_run_condition',
                                   'wrong_run_input', 'wrong_sample_reference', 'spmr', 'downsample', 'control', 'paired'])
def test_native_role_run_and_original_input_relationships_are_checked(defect):
    saved = sheet(native=True)
    run = saved['callpeak_bindings'][1]
    t = track(saved, 'background2')
    if defect == 'swapped_artifact_role':
        run['artifact_roles']['background_track'] = run['artifact_roles']['signal_track']
    elif defect == 'wrong_producer':
        t['artifact']['producer_run_ref'] = 'other-producer'
    elif defect == 'wrong_run':
        t['binding']['callpeak_run_key'] = saved['callpeak_bindings'][0]['run_key']
    elif defect == 'wrong_run_condition':
        run['condition_id'] = 'c1'
    elif defect == 'wrong_run_input':
        run['treatment_input_refs'] = ['condition1.bam']
    elif defect == 'wrong_sample_reference':
        saved['samples'][1]['reference_id'] = 'other-reference'
    elif defect in ('spmr', 'downsample'):
        run['selected_parameters'][defect] = True
    elif defect == 'control':
        run['supplied_control_input_refs'] = ['matched-control']
    else:
        run['paired_end'] = True
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(end=12000))
    assert prepared['eligibility']['tracks']['background2'] == 'unavailable'
    assert prepared['eligibility']['tracks']['signal1'] == 'usable'
    assert list(prepared['tracks']['background2']['rows']) == []


@pytest.mark.parametrize('case', ['missing_length', 'unknown_contig', 'outside', 'wrong_reference', 'duplicate_contig', 'conflicting_alias', 'duplicate_alias'])
def test_reference_population_conflicts_do_not_invent_bounds(case):
    saved = sheet()
    selected = population()
    reference = saved['reference']
    if case == 'missing_length':
        reference['contigs'][0]['length_bp'] = None
    elif case == 'unknown_contig':
        selected = population(chromosome='Toy')
    elif case == 'outside':
        selected = population(end=501)
    elif case == 'wrong_reference':
        saved['comparison']['reference_id'] = 'wrong'
    elif case == 'duplicate_contig':
        reference['contigs'].append(deepcopy(reference['contigs'][0]))
    else:
        alias = dict(source_chromosome='Toy', target_chromosome='chrToy', reference_id='fixture-toy', source_refs=['declared'])
        reference['aliases'] = [alias, deepcopy(alias)]
        if case == 'conflicting_alias':
            reference['aliases'][1]['target_chromosome'] = 'unlisted'
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=selected)
    assert prepared['eligibility']['population'] == 'unavailable'
    assert prepared['intervals'] == []
    assert list(iter_atac_track_segments(prepared['tracks'], intervals=prepared['intervals'])) == []
    assert {'reference_conflict', 'unknown_chromosome', 'metadata_missing', 'coordinate_outside_reference'} & codes(prepared)
    assert saved == before


def test_narrow_selected_population_clips_valid_row_but_reference_violation_retains_overlap():
    saved = sheet()
    replace_track(saved, 'signal1', b'chrToy\t0\t500\t7\n')
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(50, 150))
    records = components(prepared)
    assert [(r['start'], r['end']) for r in records] == [(50, 100), (100, 150)]
    assert all(r['states']['signal1'] == 'observed' and r['values']['signal1'] == 7 for r in records)
    replace_track(saved, 'signal1', b'chrToy\t0\t600\t7\nchrToy\t0\t500\t2\n')
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    records = components(prepared)
    assert all(r['states']['signal1'] == 'ambiguous' and r['source_rows']['signal1'] == [0, 1] for r in records)
    assert 'coordinate_outside_reference' in codes(prepared)
    assert saved == before


def test_unique_outside_reference_row_has_null_operand_but_exact_source_geometry_and_lexeme():
    saved = sheet()
    raw = replace_track(saved, 'signal1', b'chrToy\t400\t600\t7.50\n')['rows'][0]
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    projected = list(prepared['tracks']['signal1']['rows'])
    assert projected == [(*raw[:7], None, raw[8])]
    assert track(saved, 'signal1')['rows'][0][7] == 7.5
    problem = next(i for i in prepared['issues'] if i['code'] == 'coordinate_outside_reference')
    assert problem['row_ordinals'] == [0]
    assert problem['locations'] == [dict(line_number=1, byte_start=0, byte_end=len(b'chrToy\t400\t600\t7.50\n'))]


@pytest.mark.parametrize('token,value,state', [('0', 0, 'observed'), ('-2.50', -2.5, 'invalid'), ('NaN', None, 'invalid')])
def test_zero_negative_and_unavailable_values_reach_existing_state_classifier(token, value, state):
    saved = sheet()
    replace_track(saved, 'signal1', f'chrToy\t0\t500\t{token}\n'.encode())
    records = components(prepare_atac_calculation_inputs(saved, intervals=population()))
    assert all(r['values']['signal1'] == value and r['states']['signal1'] == state for r in records)
    assert track(saved, 'signal1')['rows'][0][8] == token


def test_unlocated_corruption_and_duplicate_occurrences_preserve_ambiguity_and_count():
    saved = sheet()
    replace_track(saved, 'signal1', b'chrToy\t0\t100\t7\nbroken\nchrToy\t0\t100\t7\nchrToy\t100\t500\t2\n')
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    records = components(prepared)
    assert records[0]['states']['signal1'] == 'ambiguous'
    assert records[0]['source_rows']['signal1'] == [0, 2]
    assert records[1]['states']['signal1'] == 'invalid'
    assert all(r['unlocated_invalid_rows']['signal1'] == 1 for r in records)


def test_unknown_chromosome_is_qualified_and_never_guessed_by_chr_prefix():
    saved = sheet()
    replace_track(saved, 'signal1', b'Toy\t0\t500\t7\n')
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert all(r['states']['signal1'] == 'missing' for r in components(prepared))
    assert 'unknown_chromosome' in codes(prepared)
    saved['reference']['aliases'] = [dict(source_chromosome='Toy', target_chromosome='chrToy',
                                           reference_id='fixture-toy', source_refs=['explicit'])]
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert all(r['states']['signal1'] == 'observed' for r in components(prepared))
    assert track(saved, 'signal1')['rows'][0][4] == 'Toy'


def alias_reorder_sheet():
    saved = sheet()
    template = saved['reference']['contigs'][0]
    saved['reference']['contigs'] = [dict(template, chromosome=name) for name in ('A', 'B')]
    saved['reference']['aliases'] = [dict(source_chromosome=source, target_chromosome=target,
        reference_id='fixture-toy', source_refs=['explicit']) for source, target in (('x', 'B'), ('y', 'A'))]
    for role in ROLES:
        replace_track(saved, role, b'x\t0\t500\t1\ny\t0\t500\t2\n')
    return saved


def test_in_memory_alias_projection_derives_order_without_reordering_native_rows():
    saved = alias_reorder_sheet()
    before = deepcopy(saved)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(chromosome='A') + population(chromosome='B'))
    records = components(prepared)
    assert [r['chromosome'] for r in records] == ['A', 'B']
    assert [r['source_rows']['signal1'] for r in records] == [[1], [0]]
    assert saved == before


def test_external_alias_reorder_is_specific_partial_failure_not_materialization():
    saved = alias_reorder_sheet()
    seen = []
    streams = externalize(saved, ('signal1',), observed=seen)
    prepared = prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows=streams)
    assert seen == []
    port = prepared['tracks']['signal1']
    assert next(port['rows'])[4] == 'B'
    with pytest.raises(AtacTableReadError, match='atac_projected_track_order_required'):
        next(port['rows'])
    assert port['extent'] == 'partial'
    assert prepared['eligibility']['tracks']['signal1'] == 'unavailable'


@pytest.mark.parametrize('case', ['empty', 'missing', 'failed_producer', 'unverified'])
def test_output_extents_do_not_turn_empty_missing_failed_or_unverified_into_zero(case):
    saved = sheet(native=case == 'failed_producer')
    if case == 'empty':
        replace_track(saved, 'signal1', b'')
    elif case == 'missing':
        replace_track(saved, 'signal1', None)
    elif case == 'failed_producer':
        replace_track(saved, 'signal1', b'chrToy\t0\t500\t7\n', producer_outcome='failed')
    else:
        replace_track(saved, 'signal1', b'chrToy\t0\t500\t7\n', expected_sha256=None, expected_size_bytes=None)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert prepared['tracks']['signal1']['extent'] == dict(empty='complete', missing='missing', failed_producer='failed', unverified='partial')[case]
    records = components(prepared)
    assert records[0]['states']['signal1'] == ('missing' if case in ('empty', 'missing') else 'observed')
    assert records[0]['values']['signal1'] == (None if case in ('empty', 'missing') else 7)


@pytest.mark.parametrize('failure', ['checksum', 'read'])
def test_external_streams_remain_lazy_late_failure_preserves_emitted_prefix(failure):
    saved = sheet()
    seen = []
    streams = externalize(saved, ('signal1',), bad_hash=('signal1',) if failure == 'checksum' else (),
                          failing=('signal1',) if failure == 'read' else (), observed=seen)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(end=100), ordered_track_rows=streams)
    assert seen == []
    iterator = iter_atac_track_segments(prepared['tracks'], intervals=prepared['intervals'])
    first = next(iterator)
    assert (first['start'], first['end']) == (0, 100)
    assert len(seen) < 5
    with pytest.raises(AtacTableReadError, match='identity_mismatch' if failure == 'checksum' else 'stream_read_failed'):
        list(iterator)
    assert len(seen) == 5
    assert prepared['tracks']['signal1']['extent'] == 'partial'
    assert first['values']['signal1'] == 0


def test_disabled_track_still_drains_and_validates_its_supplied_table():
    saved = sheet()
    track(saved, 'background2')['binding']['reference_id'] = 'wrong-reference'
    seen = []
    streams = externalize(saved, ('background2',), bad_hash=('background2',), observed=seen)
    prepared = prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows=streams)
    assert seen == []
    with pytest.raises(AtacTableReadError, match='identity_mismatch'):
        list(prepared['tracks']['background2']['rows'])
    assert seen == ['background2'] * 5
    assert prepared['tracks']['background2']['extent'] == 'failed'


def test_caller_finalization_observes_failures_in_two_streams_without_bridge_recovery():
    saved = sheet()
    seen = []
    streams = externalize(saved, bad_hash=('signal1', 'background2'), observed=seen)
    prepared = prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows=streams)
    failures = []
    try:
        list(iter_atac_track_segments(prepared['tracks'], intervals=[]))
    except AtacTableReadError as error:
        failures.append(error.issue)
        assert seen == ['signal1'] * 5
    finally:
        # Worker-owned finalization of already supplied streams, no acquisition.
        for port in prepared['tracks'].values():
            try:
                list(port['rows'])
            except AtacTableReadError as error:
                failures.append(error.issue)
    assert [i['artifact_ref'] for i in failures] == ['numeric-signal1', 'numeric-background2']
    assert all(seen.count(role) == 5 for role in ROLES)


def test_explicit_empty_population_drains_all_streams_and_does_not_select_whole_genome():
    saved = sheet()
    seen = []
    prepared = prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows=externalize(saved, observed=seen))
    assert components(prepared) == []
    assert prepared['eligibility']['population'] == 'usable'
    assert all(seen.count(role) == 5 for role in ROLES)


def test_huge_coordinate_span_stays_a_single_interval():
    saved = sheet()
    saved['reference']['contigs'][0]['length_bp'] = 10**12
    for role in ROLES:
        replace_track(saved, role, b'chrToy\t0\t1000000000000\t2\n')
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(end=10**12), ordered_track_rows=externalize(saved))
    records = components(prepared)
    assert len(records) == 1 and records[0]['end'] == 10**12


def test_retained_native_order_table_keeps_unlocated_invalid_geometry_separate():
    saved = sheet()
    t = replace_track(saved, 'signal1', b'chrToy\t0.0\t100\t1\nchrToy\t100\t500\t7\n')
    raw, manifest = table_bytes(t['rows'], order='native_file_order')
    manifest['source_artifact_ref'] = t['artifact']['artifact_ref']
    t['rows'], t['ordered_row_index'] = manifest, None
    prepared = prepare_atac_calculation_inputs(saved, intervals=population(), ordered_track_rows={
        t['binding_key']: iter_atac_track_table_rows([raw], table=manifest)})
    records = components(prepared)
    assert records[0]['states']['signal1'] == 'missing'
    assert all(r['states']['signal1'] == 'invalid' for r in records[1:])
    assert all(r['unlocated_invalid_rows']['signal1'] == 1 for r in records)


def test_external_native_order_table_with_late_reversed_geometry_preserves_first_row():
    saved = sheet()
    t = replace_track(saved, 'signal1', b'chrToy\t100\t200\t1\nchrToy\t0\t100\t2\n')
    raw, manifest = table_bytes(t['rows'], order='native_file_order')
    manifest['source_artifact_ref'] = t['artifact']['artifact_ref']
    t['rows'], t['ordered_row_index'] = manifest, None
    prepared = prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows={
        t['binding_key']: iter_atac_track_table_rows([raw], table=manifest)})
    stream = prepared['tracks']['signal1']['rows']
    assert next(stream)[5:8] == (100, 200, 1)
    with pytest.raises(AtacTableReadError, match='atac_projected_track_order_required'):
        next(stream)


def test_external_unknown_contigs_and_outside_reference_rows_retain_null_projection():
    saved = sheet()
    replace_track(saved, 'signal1', b'Unknown\t0\t10\t7\nchrToy\t400\t600\t8\n')
    prepared = prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows=externalize(saved, ('signal1',)))
    rows = list(prepared['tracks']['signal1']['rows'])
    assert [(r[0], r[4], r[5], r[6], r[7], r[8]) for r in rows] == [
        (0, 'Unknown', 0, 10, None, '7'), (1, 'chrToy', 400, 600, None, '8')]
    assert {'unknown_chromosome', 'coordinate_outside_reference'} <= codes(prepared)


@pytest.mark.parametrize('case', ['missing', 'zero', 'partial'])
def test_native_missing_zero_and_partial_header_depths_keep_the_actual_other_operand(case):
    inputs = native_inputs_with_headers()
    cp = inputs['callpeak_bindings'][0]
    raw = (NATIVE / 'bam_outputs/condition1_peaks.xls').read_bytes()
    if case == 'missing':
        raw = raw.replace(b'# tags after filtering in treatment: 100\n', b'')
    elif case == 'zero':
        raw = raw.replace(b'# tags after filtering in treatment: 100\n', b'# tags after filtering in treatment: 0\n')
    else:
        raw = raw[:-12]
    descriptor = artifact(raw, cp['artifact_roles']['peaks_xls'], 'macs2_peaks_xls_narrow', cp['producer_ref'])
    if case == 'partial':
        descriptor['supplied_extent'] = 'partial'
    inputs['peaks_xls'][0] = parse_macs2_peaks_xls(raw, artifact=descriptor, callpeak=cp)
    inputs['depth_selection'] = select_atac_depth_counts(inputs['peaks_xls'], conditions=('c1', 'c2'),
                                                       callpeak_bindings=inputs['callpeak_bindings'])
    saved = build_atac_differential_sheet(**inputs)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert prepared['depth1'] == dict(missing=None, zero=0, partial=100)[case]
    assert prepared['depth2'] == 200 and prepared['depth_unit'] == 'tags'
    assert prepared['eligibility']['depths'] == ('unavailable' if case == 'missing' else 'usable')
    if case == 'zero':
        records = components(prepared)
        assert records[0]['scores']['depth_factors']['condition1']['reason'] == 'zero_depth'


@pytest.mark.parametrize('field', ['count', 'source_locations', 'source_artifact_ref', 'sample_ids', 'callpeak_run_key'])
def test_changed_saved_native_depth_selection_is_not_authenticated_by_summary_boolean(field):
    saved = sheet(native=True)
    depth = saved['depth_selection']['conditions'][0]
    if field == 'count':
        depth.update(count=105, count_lexeme='105')
    elif field == 'source_locations':
        depth['source_locations'][0]['line_number'] += 1
    elif field == 'sample_ids':
        depth[field] = ['s2']
    else:
        depth[field] = 'wrong-identity'
    saved['depth_selection']['compatible_population'] = True
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert (prepared['depth1'], prepared['depth2']) == (None, None)
    assert prepared['eligibility']['depths'] == 'unavailable'
    assert 'depth_population_conflict' in codes(prepared)


@pytest.mark.parametrize('field', ['unit', 'population', 'condition_id', 'sample_ids'])
def test_declared_depth_mismatch_is_not_rescaled_or_given_a_fake_unit(field):
    saved = sheet()
    depth = saved['depth_selection']['conditions'][1]
    depth[field] = ['fixture-s1'] if field == 'sample_ids' else 'tags' if field == 'unit' else 'different'
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert (prepared['depth1'], prepared['depth2']) == (None, None)
    assert prepared['depth_unit'] == (None if field == 'unit' else 'million_tags')
    assert prepared['eligibility']['depths'] == 'unavailable'
    assert len(list(iter_atac_track_segments(prepared['tracks'], intervals=prepared['intervals']))) == 5


def test_declared_missing_depth_preserves_other_value_and_inconsistent_lexeme_is_unbound():
    saved = sheet()
    depth = saved['depth_selection']['conditions'][0]
    depth.update(state='missing', value=None, value_lexeme=None)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert (prepared['depth1'], prepared['depth2'], prepared['depth_unit']) == (None, 2, 'million_tags')
    assert prepared['eligibility']['depths'] == 'unavailable'
    depth.update(state='declared', value=1, value_lexeme='2')
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert (prepared['depth1'], prepared['depth2']) == (None, None)
    assert 'depth_population_conflict' in codes(prepared)


def test_invalid_copied_compatibility_labels_cannot_disable_valid_actual_operands():
    saved = sheet(native=True)
    saved['reference_relation'] = 'conflicting'
    saved['normalization_compatibility'] = 'incompatible'
    saved['depth_selection']['compatible_population'] = False
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert all(v == 'usable' for v in prepared['eligibility']['tracks'].values())
    assert prepared['eligibility']['depths'] == 'usable'
    assert (prepared['depth1'], prepared['depth2']) == (100, 200)


def test_same_content_and_shared_samples_are_dependence_not_fabricated_replicates_or_conflicts():
    inputs = explicit_inputs()
    first, second = inputs['conditions']
    second['sample_ids'] = first['sample_ids'].copy()
    inputs['depth_selection']['conditions'][1]['sample_ids'] = first['sample_ids'].copy()
    for t in inputs['tracks']:
        if t['binding']['condition_id'] == second['condition_id']:
            t['binding']['sample_ids'] = first['sample_ids'].copy()
    # Equal background content has distinct selected roles and conditions.
    for role in ('background1', 'background2'):
        t = next(t for t in inputs['tracks'] if t['binding_key'] == role)
        raw = b'chrToy\t0\t500\t1\n'
        t['binding']['source_artifact_ref'] = 'shared-content'
        replacement = parse_atac_bedgraph(raw, artifact=artifact(raw, 'shared-content'), binding=t['binding'])
        inputs['tracks'][inputs['tracks'].index(t)] = replacement
    saved = build_atac_differential_sheet(**inputs)
    prepared = prepare_atac_calculation_inputs(saved, intervals=population())
    assert all(v == 'usable' for v in prepared['eligibility']['tracks'].values())
    assert prepared['eligibility']['depths'] == 'usable'
    assert len(components(prepared)) == 5
    assert any(i['code'] == 'duplicate_record' and i['field'] == 'shared_artifact_content' for i in prepared['issues'])
    assert any(i['code'] == 'duplicate_record' and i['field'] == 'shared_samples' for i in prepared['issues'])
    assert all(s['replicate_id'] is None for s in saved['samples'])


@pytest.mark.parametrize('case,code', [('duplicate_sample', 'duplicate_atac_sample_id'),
    ('duplicate_condition', 'duplicate_atac_condition_id'), ('duplicate_run', 'duplicate_atac_callpeak_run_key'),
    ('duplicate_track', 'duplicate_atac_track_key'), ('duplicate_selected_track', 'duplicate_atac_comparison_track_key'),
    ('index', 'invalid_atac_ordered_row_index'), ('coordinate_declaration', 'invalid_atac_track_order_or_coordinate_declaration'),
    ('cutoff', 'invalid_atac_comparison_cutoff_log10_lr'), ('pseudocount', 'invalid_atac_comparison_native_pseudocount'),
    ('gap', 'invalid_atac_comparison_maximum_gap_bp')])
def test_structural_inputs_fail_specifically_before_consuming_streams(case, code):
    saved = sheet(native=True)
    if case.startswith('duplicate_') and case != 'duplicate_selected_track':
        field = {'sample': 'samples', 'condition': 'conditions', 'run': 'callpeak_bindings', 'track': 'tracks'}[case.removeprefix('duplicate_')]
        if field == 'conditions':
            saved[field][1] = deepcopy(saved[field][0])
        else:
            saved[field].append(deepcopy(saved[field][0]))
    elif case == 'duplicate_selected_track':
        saved['comparison']['track_keys']['background2'] = 'signal2'
    elif case == 'index':
        track(saved, 'signal1')['ordered_row_index'] = []
    elif case == 'coordinate_declaration':
        track(saved, 'signal1')['coordinate_convention'] = 'one_based'
    else:
        saved['comparison']['selected_parameters'][{'cutoff': 'cutoff_log10_lr', 'pseudocount': 'native_pseudocount', 'gap': 'maximum_gap_bp'}[case]] = {'cutoff': -1, 'pseudocount': 0, 'gap': 50}[case]
    with pytest.raises(ValueError, match=code):
        prepare_atac_calculation_inputs(saved, intervals=[])


@pytest.mark.parametrize('selected', [[dict(chromosome='chrToy', start=True, end=10)],
    population(0, 100) + population(50, 150), population(100, 200) + population(0, 50),
    [dict(chromosome='chrToy', start=0, end=0)]])
def test_malformed_or_unordered_population_is_a_programming_error(selected):
    with pytest.raises(ValueError):
        prepare_atac_calculation_inputs(sheet(), intervals=selected)


def test_external_stream_binding_keys_cannot_override_memory_or_omit_a_required_table():
    saved = sheet()
    with pytest.raises(ValueError, match='atac_unselected_or_in_memory_track_stream'):
        prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows={'signal1': iter(())})
    externalize(saved, ('signal1',))
    with pytest.raises(ValueError, match='atac_retained_track_stream_required'):
        prepare_atac_calculation_inputs(saved, intervals=[])
    with pytest.raises(ValueError, match='atac_unselected_or_in_memory_track_stream'):
        prepare_atac_calculation_inputs(saved, intervals=[], ordered_track_rows={'filename.bdg': iter(())})


def test_saved_sheet_recalculation_forbids_files_acquisition_native_work_and_preserves_native_results(monkeypatch):
    saved = json.loads(json.dumps(sheet(), allow_nan=False))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError('bridge/recalculation cannot open paths, acquire inputs or execute native work')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('builtins.open', forbidden)
    first = components(prepare_atac_calculation_inputs(saved, intervals=population()))
    changed = components(prepare_atac_calculation_inputs(saved, intervals=population()), pseudocount=1)
    assert likelihoods(first[1]) != likelihoods(changed[1])
    assert len(region_rows(first, cutoff=100)) == 0
    assert len(region_rows(first, cutoff=3)) == 3
    assert saved == before
