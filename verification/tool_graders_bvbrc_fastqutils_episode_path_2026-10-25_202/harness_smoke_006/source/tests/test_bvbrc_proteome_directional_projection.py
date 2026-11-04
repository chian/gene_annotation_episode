"""Retained native scientific quantities via the real composed v2 facade."""
from copy import deepcopy
from decimal import localcontext
import importlib
import json

import pytest

from gene_annotation_episode import bvbrc_proteome_bundle_adapter_v2 as adapter
from gene_annotation_episode import bvbrc_proteome_directional_fact_contracts as c
from gene_annotation_episode.bvbrc_proteome_directional_projection import validate_saved_projection_v2, _at
from gene_annotation_episode.bvbrc_proteome_fact_contracts import decode_reference
from gene_annotation_episode.execution_contracts import digest
from test_bvbrc_proteome_bundle_v2_resolution import fixture
from test_bvbrc_proteome_bundle_resolution import member
from test_bvbrc_proteome_directional_fact_contracts import all_selections


def selector(kind, scope, metric=None, **values):
    result = dict(kind=kind, scope=scope, document_id='d', **{k: {'query_ordinal': 1, 'hsp_ordinal': 1}.get(k, 0) for k in c.KEYS[scope]})
    if metric is not None: result['metric'] = metric
    return {**result, **values}


def case_with(fields, key='2221', **kwargs):
    case = fixture(key, **kwargs)
    case['requested_form'] = c.requested_form_schema_v2(fields)
    return case


@pytest.fixture(scope='module')
def native_projection():
    fields = all_selections()
    for value in fields.values():
        if value['kind'] == 'directional_issues': value['limit'] = 100
    fields['status'] = {'kind': 'request_status', 'field': 'directional_native_integer_hsp_gap_count'}
    case = case_with(fields)
    return case, adapter.consume_bundle(**case)


def saved_check(case, result):
    return validate_saved_projection_v2(result['sheet'], result['components'], facts=result['facts'], status=result['status'],
        missing_requirements=tuple(result['missing_requirements']), diagnostics=tuple(result['diagnostics']),
        requested_form=case['requested_form'], parameters=case['parameters'], original_task=case['bundle']['original_task'],
        bundle_sha256=digest(case['bundle']), bundle=case['bundle'])


def test_all_finite_metrics_and_families_project_real_saved_fields(native_projection):
    case, result = native_projection
    assert set(result['facts']) == set(case['requested_form']['properties'])
    assert {node['x-bvbrc-proteome']['kind'] for node in case['requested_form']['properties'].values()} >= set(c.FAMILIES)
    assert result['status'] == 'partial'
    root = {key: result[key] for key in ('sheet', 'components', 'facts', 'missing_requirements', 'diagnostics')}
    def inspect(value):
        if isinstance(value, dict):
            for child in value.values(): inspect(child)
        elif isinstance(value, list):
            for child in value: inspect(child)
        elif isinstance(value, str) and value.startswith('bvbrc_proteome_') and ':' in value:
            _, analysis, pointer = decode_reference(value)
            assert analysis == case['parameters']['analysis_id']
            assert _at(root, pointer) is not None, pointer
    inspect(result['facts'])
    assert saved_check(case, result)['facts'] == result['facts']


def test_report_issue_pages_preserve_distinct_saved_locations_in_reviewed_order(native_projection):
    _, result = native_projection
    value = result['facts']['directional_issues_report_reader_numerical']
    report = result['components']['directional']['components']['reports'][0]['diagnostics']
    assert len(report) == 11
    # The accepted contract retains distinct saved locations even where the
    # producer propagated an equal issue. No independent evidence is inferred.
    assert value['total_count'] == value['returned_count'] == 22
    paths = [decode_reference(row['issue_ref'])[2] for row in value['items']]
    assert paths == [f'/components/directional/components/reports/0/diagnostics/{i}' for i in range(11)] + [
        f'/components/directional/components/diagnostics/{i}' for i in range(11)]
    assert len(set(paths)) == 22


def test_exact_native_decimal_ratio_populations_and_missing_gap_are_distinct(native_projection):
    _, result = native_projection
    facts = result['facts']
    expectation = facts['directional_native_decimal_hsp_expect']
    assert expectation['cell'] == {'state': 'present', 'value': {'sign': 0, 'digits': [2], 'exponent': -66}}
    assert expectation['expect_group_count'] == {'state': 'missing', 'value': None}
    assert expectation['context']['parameter_ref'] is None
    coverage = facts['directional_coverage_query_any_displayed_subject_query_paired_union']
    assert coverage['coverage']['value'] == dict(numerator=529, denominator=600,
        rendered_decimal={'sign': 0, 'digits': [int(x) for x in '881666666666666667'], 'exponent': -18})
    resolved = facts['directional_fraction_subject_compatible_unique_pair_resolved_identity']
    assert resolved['cell']['value'] == dict(numerator=468, denominator=468,
        rendered_decimal={'sign': 0, 'digits': [1], 'exponent': 0})
    assert resolved['pair_population'] == dict(total_pairs=529, resolved_pairs=468, unresolved_pairs=61, stop_containing_pairs=0)
    assert resolved['context']['supports'][0]['included_block_count'] == 9
    assert facts['directional_native_integer_hsp_gap_count']['cell'] == dict(state='missing', value=None)
    assert facts['directional_count_hsp_query_gap_columns']['cell']['value'] == 0
    assert facts['status']['state'] == 'unavailable' and facts['status']['requirement_refs']
    assert facts['status']['requirement_refs'] == facts['directional_native_integer_hsp_gap_count']['context']['requirement_refs']
    minimum = facts['directional_extremum_subject_minimum_reported_hsp_expectation']
    assert minimum['native_decimal']['value'] == dict(sign=0, digits=[0], exponent=0)
    assert minimum['expectation_display'] == 'printed_zero_precision_unknown'
    assert facts['directional_count_hsp_stop_containing_pairs']['cell']['unit'] == 'paired_column'
    assert facts['directional_count_compatible_pairs_stop_containing_pairs']['cell']['unit'] == 'coordinate_pair'


def test_synthetic_tiny_native_expectation_survives_real_provider_saved_and_json_paths():
    # This altered measurement is synthetic; retained 2221 remains unchanged.
    case = case_with({'expect': selector('directional_native_decimal', 'hsp', 'expect')})
    raw = case['artifact_bytes']['directional']
    assert raw.count(b'2e-66') == 1
    raw = raw.replace(b'2e-66', b'1e-900')
    original = case['bundle']['artifacts'][0]
    changed = member(raw, name='directional', role=original['role'])
    changed.update(declared_format=deepcopy(original['declared_format']), requirement_ids=['directional'])
    case['bundle']['artifacts'] = [changed]
    case['artifact_bytes']['directional'] = raw
    with localcontext() as context:
        context.prec, context.Emin, context.Emax = 2, -2, 2
        for signal in context.traps: context.traps[signal] = True
        result = adapter.consume_bundle(**case)
        returned = json.loads(json.dumps(result['facts']['expect']))
        assert returned['cell']['value'] == dict(sign=0, digits=[1], exponent=-900)
        assert returned['expectation_display'] == 'positive_reported_decimal'
        assert saved_check(case, result)['facts']['expect'] == returned


@pytest.mark.parametrize('offset,items,next_offset', [(0, [{'start': 0, 'end': 414}], 1),
    (1, [{'start': 485, 'end': 600}], None), (2, [], None), (90, [], None)])
def test_page_counts_preserve_actual_full_membership(offset, items, next_offset):
    case = case_with({'page': selector('directional_intervals', 'query', 'any_displayed_subject_query_paired_union', offset=offset, limit=1)})
    fact = adapter.consume_bundle(**case)['facts']['page']
    assert fact['availability'] == 'available' and fact['total_count'] == 2
    assert fact['returned_count'] == len(items) and fact['items'] == items and fact['next_offset'] == next_offset


def test_retained_no_hit_zero_and_absent_pair_identity_keep_different_states():
    case = case_with({'coverage': selector('directional_coverage', 'query', 'any_displayed_subject_query_paired_union', query_ordinal=0),
        'count': selector('directional_count', 'query', 'displayed_hsp_count', query_ordinal=0),
        'state': selector('directional_state', 'query', 'display_state', query_ordinal=0),
        'identity': selector('directional_fraction', 'subject', 'compatible_unique_pair_resolved_identity', query_ordinal=0)}, key='2011')
    result = adapter.consume_bundle(**case)
    facts = result['facts']
    assert facts['coverage']['coverage']['value'] == dict(numerator=0, denominator=102,
        rendered_decimal=dict(sign=0, digits=[0], exponent=0))
    assert facts['coverage']['availability'] == facts['count']['availability'] == 'available'
    assert facts['count']['cell']['value'] == 0
    assert facts['state']['value_code'] == 'native_no_hit_claim'
    assert facts['identity']['availability'] == 'unavailable'
    assert facts['identity']['cell']['state'] is facts['identity']['cell']['value'] is None
    assert saved_check(case, result)['facts'] == facts
    # Remove the claim in a separate synthetic specimen. An empty display then
    # does not establish measured zero coverage.
    raw = case['artifact_bytes']['directional']
    assert raw.count(b' ***** No hits found ******') == 1
    raw = raw.replace(b' ***** No hits found ******', b'')
    original = case['bundle']['artifacts'][0]
    changed = member(raw, name='directional', role=original['role'])
    changed.update(declared_format=deepcopy(original['declared_format']), requirement_ids=['directional'])
    case['bundle']['artifacts'] = [changed]
    case['artifact_bytes']['directional'] = raw
    missing = adapter.consume_bundle(**case)['facts']['coverage']
    assert missing['availability'] == 'unavailable'
    assert missing['coverage']['state'] == 'missing' and missing['coverage']['value'] is None


def test_retained_conflicts_keep_independent_available_coverage_and_conflict_page():
    case = case_with({'coverage': selector('directional_coverage', 'subject', 'query_trace_paired_union', query_ordinal=0),
        'identity': selector('directional_fraction', 'subject', 'compatible_unique_pair_resolved_identity', query_ordinal=0),
        'conflicts': selector('directional_conflicts', 'subject', query_ordinal=0, offset=0, limit=100),
        'mapping': selector('directional_state', 'subject', 'mapping_state', query_ordinal=0)}, key='2202')
    result = adapter.consume_bundle(**case)
    facts = result['facts']
    assert facts['coverage']['count']['value'] == 187
    assert facts['coverage']['availability'] == 'available'
    assert facts['identity']['cell']['state'] == 'conflict'
    assert facts['identity']['availability'] == 'incompatible'
    assert facts['mapping']['value_code'] == 'observed_conflict'
    assert facts['conflicts']['total_count'] == len(facts['conflicts']['items']) > 0
    assert saved_check(case, result)['facts'] == facts


def test_missing_first_document_and_out_of_range_native_ordinal_never_shift_target():
    case = case_with({'present': selector('directional_native_decimal', 'hsp', 'expect'),
        'out_of_range': selector('directional_native_integer', 'hsp', 'gap_count', hsp_ordinal=99),
        'absent': selector('directional_native_integer', 'query', 'length', document_id='absent')})
    absent = deepcopy(case['parameters']['directional_documents'][0])
    absent.update(document_id='absent', requirement_id='absent', report_key='absent')
    case['parameters']['directional_documents'].insert(0, absent)
    facts = adapter.consume_bundle(**case)['facts']
    assert facts['present']['context']['target']['report_ordinal'] == 0
    assert facts['present']['cell']['value'] == dict(sign=0, digits=[2], exponent=-66)
    assert facts['absent']['context']['target']['report_ordinal'] is None
    assert facts['absent']['context']['target']['query_ordinal'] == 1
    assert facts['absent']['cell'] == facts['out_of_range']['cell'] == dict(state=None, value=None)
    assert facts['out_of_range']['context']['target']['hsp_ordinal'] == 99


def test_mixed_form_preserves_legacy_numerical_meaning_and_maps_original_references():
    case = case_with({'mean': {'kind': 'measurement', 'target': 'summary', 'track_key': 'comp_genome_2',
        'summary': 'first_hsp_identity_summary', 'metric': 'mean'},
        'legacy_requirements': {'kind': 'requirements', 'scope': 'all'},
        'expect': selector('directional_native_decimal', 'hsp', 'expect'),
        'status': {'kind': 'request_status', 'field': 'expect'}}, mixed=True, supplementary=True)
    result = adapter.consume_bundle(**case)
    assert result['facts']['mean']['cell']['value'] == .4375
    assert decode_reference(result['facts']['mean']['population_ref'])[2].startswith('/components/legacy/')
    assert result['facts']['expect']['cell']['value'] == dict(sign=0, digits=[2], exponent=-66)
    assert all(not row['code'].startswith('proteome_directional_') for row in result['facts']['legacy_requirements']['requirements'])
    assert saved_check(case, result)['facts'] == result['facts']


@pytest.mark.parametrize('change', ['decimal', 'denominator', 'state', 'target', 'page', 'requirement'])
def test_saved_projection_rejects_changes_in_original_requested_values(native_projection, change):
    case, result = deepcopy(native_projection)
    facts = result['facts']
    if change == 'decimal': facts['directional_native_decimal_hsp_expect']['cell']['value']['exponent'] = -65
    elif change == 'denominator': facts['directional_fraction_subject_compatible_unique_pair_resolved_identity']['cell']['value']['denominator'] = 529
    elif change == 'state': facts['directional_state_report_parse_state']['value_code'] = 'unknown'
    elif change == 'target': facts['directional_native_decimal_hsp_expect']['context']['target']['hsp_ordinal'] = 0
    elif change == 'page': facts['directional_columns_block']['total_count'] += 1
    else: result['missing_requirements'].append({**result['missing_requirements'][-1], 'requirement_id': 'foreign'})
    with pytest.raises(ValueError): saved_check(case, result)


def forbid_construction(monkeypatch):
    def fail(*args, **kwargs): raise AssertionError('saved return performed scientific construction or I/O')
    for module, names in {
        'bvbrc_proteome_directional': ('parse_genome_comparison_directional_report',),
        'bvbrc_proteome_directional_sheet': ('build_directional_sheet',),
        'bvbrc_proteome_directional_calculators': ('calculate_directional_components',),
        'bvbrc_proteome_directional_geometry': ('calculate_protein_block', 'inspect_protein_correspondence', 'union_position_intervals'),
        'bvbrc_proteome_bundle_v2_resolution': ('parse_genome_comparison_directional_report', 'build_directional_sheet', 'calculate_directional_components'),
    }.items():
        for name in names: monkeypatch.setattr(importlib.import_module('gene_annotation_episode.' + module), name, fail)
    monkeypatch.setattr('socket.create_connection', fail)
    monkeypatch.setattr('subprocess.run', fail)
    monkeypatch.setattr('subprocess.Popen', fail)
    return fail


def test_saved_projection_uses_no_native_parsing_builders_geometry_or_calculation(native_projection, monkeypatch):
    case, result = native_projection
    forbid_construction(monkeypatch)
    assert saved_check(case, result)['facts'] == result['facts']
