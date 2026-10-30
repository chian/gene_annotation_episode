"""Mechanical worksheet checks using retained admitted rows and explicit fixtures.

The original rows were already produced in controlled261 execution. These tests
do not reopen a paper, rerun a population operation or claim a new selected run.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

import pytest

from gene_annotation_episode import literature_a105_worksheet as worksheet
from gene_annotation_episode import literature_a105_worksheet_render as render
from gene_annotation_episode.communication import validate_closed_schema, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_contract_information import expand_fact_form

PACKET = Path(__file__).resolve().parents[1] / 'verification/a105_worksheet_pure_266'


def load(name):
    return json.loads((PACKET / name).read_text())


def expand(template):
    facts = {source: {'type': 'array', 'meaning': 'Existing selected numerical format.',
        'report_schema': worksheet._schema(source)} for source in worksheet.FAMILIES}
    return expand_fact_form(json.dumps(template['submitted_form']), child_role='experimental',
        facts_by_role={'experimental': facts}, permitted_child_roles=['experimental'])['expanded_schema']


@pytest.fixture
def example():
    form = load('RETAINED_JOINT_NUMERICAL_ROWS_001.json')
    requests = [{'field': field, 'source': source, 'components': [row['component'] for row in form[field]]}
        for field, source in (('native_parameter', worksheet.NATIVE), ('precision', worksheet.SUMMARY))]
    template = worksheet.a105_worksheet_template(requests)
    schema = expand(template)
    form['assessment_context'] = {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}
    records = load('RETAINED_PUBLIC_REFERENCES_001.json')
    return form, schema, template['assignment_rosters'], records


def selector(form, field, component, quantity='cell_value'):
    row = next(row for row in form[field] if row['component'] == component)
    return {'field': field, 'sheet_ref': row['sheet_ref'], 'component': component, 'quantity': quantity}


def link(form, relation, component='source_reported_parameter', quantity='cell_value'):
    value = {'left': selector(form, 'native_parameter', 'numerator_parameter', quantity),
        'right': selector(form, 'precision', component), 'relation': relation, 'support_record_refs': []}
    form['assessment_context']['quantity_links'].append(value)
    return value


def verify(example):
    form, schema, assignment, records = example
    # Ordinary native schemas validate separately in their original resource;
    # host reference possession is covered by original261, not fabricated here.
    validate_form(form, schema, lambda reference, namespace: True)
    worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_original_nine_formats_preserve_exact_schemas_and_component_order():
    requests = [{'field': 'section_' + str(i), 'source': source,
        'components': list(reversed(worksheet._components(source)))}
        for i, source in enumerate(tuple(worksheet.FAMILIES)[:9])]
    original = deepcopy(requests)
    result = worksheet.a105_worksheet_template(requests)
    schema = expand(result)
    assert requests == original
    assert len(result['section_roles']) == 9
    for request in requests:
        source, field = request['source'], request['field']
        assert schema['properties'][field] == worksheet._schema(source)
        assert result['assignment_rosters'][worksheet.FAMILIES[source][0]] == request['components']
    validate_closed_schema(schema)


@pytest.mark.parametrize('source', list(worksheet.FAMILIES))
def test_each_existing_format_accepts_empty_partial_without_record_reads(source):
    template = worksheet.a105_worksheet_template([{'field': 'selected', 'source': source, 'components': []}])
    schema = expand(template)
    context = {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}
    form = {'selected': [], 'assessment_context': context}
    validate_form(form, schema, lambda *_: pytest.fail('empty partial has no references'))
    worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'],
        read_public_record=lambda *_: pytest.fail('no link needs public records'))
    node = schema['properties']['assessment_context']['properties']
    assert node['quantity_links']['maxItems'] == node['assertion_links']['maxItems'] == 0


@pytest.mark.parametrize('specification', [[], [{'field': 'bad field', 'source': worksheet.NATIVE, 'components': []}],
    [{'field': 'assessment_context', 'source': worksheet.NATIVE, 'components': []}],
    [{'field': 'a', 'source': worksheet.NATIVE, 'components': ['invented']}],
    [{'field': 'a', 'source': worksheet.NATIVE, 'components': ['numerator_parameter', 'numerator_parameter']}],
    [{'field': 'a', 'source': worksheet.NATIVE, 'components': []}, {'field': 'b', 'source': worksheet.NATIVE, 'components': []}],
    [{'field': 'a', 'source': worksheet.NATIVE, 'components': []}, {'field': 'a', 'source': worksheet.SUMMARY, 'components': []}]])
def test_invalid_construction_has_declared_error(specification):
    with pytest.raises(ContractError, match='a105_worksheet_request_invalid'):
        worksheet.a105_worksheet_template(specification)


def test_unregistered_format_is_unimplemented_here():
    with pytest.raises(ContractError, match='a105_worksheet_section_unimplemented'):
        worksheet.a105_worksheet_template([{'field': 'future', 'source': 'literature_unregistered_format_cells', 'components': []}])


def test_empty_roster_sibling_and_independent_output_mutation():
    requests = [{'field': 'native', 'source': worksheet.NATIVE, 'components': []},
        {'field': 'summary', 'source': worksheet.SUMMARY, 'components': ['source_reported_sd']}]
    result = worksheet.a105_worksheet_template(requests, context_field='interpretation')
    assert result['assignment_rosters']['requested_kinetic_components'] == []
    result['section_roles'][1]['components'].append('source_reported_parameter')
    assert requests[1]['components'] == result['assignment_rosters']['requested_kinetic_summary_precision_components'] == ['source_reported_sd']
    assert 'maxItems' not in result['submitted_form']['properties']['interpretation']['properties']['quantity_links']


@pytest.mark.parametrize(('relation', 'component', 'quantity'), [
    ('same_reported_parameter', 'source_reported_parameter', 'cell_value'),
    ('same_reported_spread', 'source_reported_sd', 'reported_spread'),
    ('same_count_report', 'source_independent_preparation_count', 'reported_count')])
def test_retained_admitted_anchors_establish_narrow_same_report_links(example, relation, component, quantity):
    form = example[0]
    value = link(form, relation, component, quantity)
    before = deepcopy(form)
    verify(example)
    value['left'], value['right'] = value['right'], value['left']
    verify(example)
    value['left'], value['right'] = value['right'], value['left']
    assert form == before


@pytest.mark.parametrize('component', ['scenario_mean_variance', 'scenario_mean_standard_error'])
@pytest.mark.parametrize('report', ['source_reported_sd', 'source_independent_preparation_count'])
def test_conditional_precision_is_bound_to_same_summary_and_retains_unknown_source_se(example, component, report):
    form = example[0]
    form['assessment_context']['quantity_links'].append({'left': selector(form, 'precision', report),
        'right': selector(form, 'precision', component), 'relation': 'conditional_precision_of_report', 'support_record_refs': []})
    verify(example)
    assert next(row for row in form['precision'] if row['component'] == 'source_mean_standard_error')['cell']['value'] is None


@pytest.mark.parametrize('change', ['equal_other_anchor', 'wrong_subject', 'missing_subject', 'withheld_spread',
    'sem', 'physical_to_statistical', 'wrong_source', 'wrong_unit', 'count_technical'])
def test_positive_links_do_not_follow_equal_numbers_or_incompatible_meanings(example, change):
    form, schema, assignment, records = example
    relation, component, quantity = ('same_reported_parameter', 'source_reported_parameter', 'cell_value')
    n = form['native_parameter'][0]['numerator']
    if change in ('withheld_spread', 'sem'):
        relation, component, quantity = 'same_reported_spread', 'source_reported_sd', 'reported_spread'
    if change in ('physical_to_statistical', 'count_technical'):
        relation, component, quantity = 'same_count_report', 'source_independent_preparation_count', 'reported_count'
    value = link(form, relation, component, quantity)
    if change == 'equal_other_anchor':
        records[n['measurement_ref']]['anchor']['start'] += 10
        records[n['measurement_ref']]['anchor']['end'] += 10
    elif change == 'wrong_subject':
        records[n['subject']['construct']]['anchor']['quote'] = 'other-variant'
        records[n['subject']['construct']]['anchor']['end'] = records[n['subject']['construct']]['anchor']['start'] + len('other-variant')
    elif change == 'missing_subject':
        for r in form['precision']:
            for name in ('molecule', 'construct'):
                r['source_context'][name] = {'status': 'not_selected', 'fragments': []}
    elif change == 'withheld_spread':
        n['uncertainty_values']['delivery_status'] = 'not_requested'
    elif change == 'sem':
        n['uncertainty']['statistic'] = 'sem'
    elif change == 'physical_to_statistical':
        value['right']['component'] = 'source_statistical_estimator_count'
    elif change == 'wrong_source':
        form['native_parameter'][0]['evidence_source_ref'] = 'source_' + 'a' * 24
    elif change == 'wrong_unit':
        form['native_parameter'][0]['unit'] = 'min^-1'
    elif change == 'count_technical':
        n['uncertainty']['repetition_basis'] = 'technical_measurements'
    with pytest.raises(ContractError, match='a105_worksheet_(link_not_supported|subquantity_not_delivered)'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_source_unit_location_is_required_beside_matching_parameter_anchor(example):
    form, schema, assignment, records = example
    link(form, 'same_reported_parameter')
    summary_row = next(row for row in form['precision'] if row['component'] == 'source_reported_parameter')
    summary_row['dependency_locations'] = summary_row['dependency_locations'][:1]
    with pytest.raises(ContractError, match='link_not_supported'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


@pytest.mark.parametrize('change', ['different_sheet', 'no_stipulations', 'source_promotion', 'wrong_dependencies'])
def test_scenario_precision_cannot_be_promoted_or_detached(example, change):
    form, schema, assignment, records = example
    form['assessment_context']['quantity_links'].append({'left': selector(form, 'precision', 'source_reported_sd'),
        'right': selector(form, 'precision', 'scenario_mean_variance'), 'relation': 'conditional_precision_of_report', 'support_record_refs': []})
    scenario = next(row for row in form['precision'] if row['component'] == 'scenario_mean_variance')
    if change == 'different_sheet':
        scenario['sheet_ref'] = 'source_' + 'b' * 24
        form['assessment_context']['quantity_links'][0]['right']['sheet_ref'] = scenario['sheet_ref']
    elif change == 'no_stipulations':
        scenario['cell']['stipulated_assumptions'] = []
    elif change == 'source_promotion':
        scenario['cell']['qualification'] = 'source_reported'
    elif change == 'wrong_dependencies':
        scenario['dependency_locations'] = []
    with pytest.raises(ContractError, match='a105_worksheet_(link_not_supported|scenario_source_promotion)'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_unresolved_partial_and_conflicting_support_are_preserved(example):
    form, schema, assignment, records = example
    value = link(form, 'unresolved', 'source_mean_standard_error')
    verify(example)
    value['relation'] = 'conflicting'
    with pytest.raises(ContractError, match='link_not_supported'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)
    refs = list(records)[:2]
    value['support_record_refs'] = refs
    verify(example)


def test_duplicate_and_hidden_selectors_cannot_expand_the_return(example):
    form, schema, assignment, records = example
    value = link(form, 'same_reported_parameter')
    duplicate = deepcopy(value)
    duplicate['support_record_refs'] = list(records)[:1]
    form['assessment_context']['quantity_links'].append(duplicate)
    with pytest.raises(ContractError, match='duplicate_link'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)
    form['assessment_context']['quantity_links'].pop()
    value['right']['sheet_ref'] = 'source_' + 'c' * 24
    with pytest.raises(ContractError, match='selector_not_delivered'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_unsupported_other_family_positive_join_stays_unresolved():
    template = worksheet.a105_worksheet_template([{'field': 'signal', 'source': 'literature_endpoint_signal_cells', 'components': ['retained_fraction']}])
    schema = expand(template)
    row = {'sheet_ref': 'source_' + 'd' * 24, 'component': 'retained_fraction', 'evaluation_scope': 'source_endpoint_signal_contribution'}
    selected = {'field': 'signal', 'sheet_ref': row['sheet_ref'], 'component': row['component'], 'quantity': 'cell_value'}
    context = {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [{'left': selected, 'right': deepcopy(selected),
        'relation': 'unresolved', 'support_record_refs': []}], 'assertion_links': []}
    form = {'signal': [row], 'assessment_context': context}
    # Explicit minimal routing fixture; no claim to a valid scientific endpoint
    # row. The ordinary schema check is separately exercised on retained rows.
    worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: pytest.fail('no support fetched'))
    context['quantity_links'][0]['relation'] = 'same_reported_parameter'
    with pytest.raises(ContractError, match='link_not_supported'):
        worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: None)


def test_forged_context_schema_and_orphan_forwarded_link_are_rejected(example):
    form, schema, assignment, records = example
    link(form, 'same_reported_parameter')
    original = deepcopy(form['precision'])
    form['native_parameter'] = []
    with pytest.raises(ContractError, match='selector_not_delivered'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)
    form['assessment_context']['quantity_links'] = []
    verify(example)
    assert form['precision'] == original
    schema['properties']['assessment_context']['properties']['assertion_refs']['uniqueItems'] = False
    with pytest.raises(ContractError, match='schema_invalid'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_assertion_interpretation_has_exact_requested_reference_and_record_support(example):
    form, schema, assignment, records = example
    hypothesis = 'hypothesis_' + 'e' * 24
    records[hypothesis] = {'id': hypothesis, 'record_type': 'hypothesis'}  # explicit engineering fixture
    context = form['assessment_context']
    context['assertion_refs'] = [hypothesis]
    context['assertion_links'] = [{'selector': selector(form, 'native_parameter', 'numerator_parameter'),
        'assertion_ref': hypothesis, 'relation': 'measures_asserted_endpoint', 'support_record_refs': list(records)[:1]}]
    verify(example)
    context['assertion_links'][0]['assertion_ref'] = 'hypothesis_' + 'f' * 24
    with pytest.raises(ContractError, match='assertion_reference_invalid'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_cold_link_validation_uses_only_retained_rows_and_public_references(example, monkeypatch):
    form, schema, assignment, records = example
    link(form, 'same_reported_parameter')
    monkeypatch.setattr(worksheet, '_schema', lambda *_: pytest.fail('cold path consulted current native factory'))
    monkeypatch.setattr(worksheet, 'import_module', lambda *_: pytest.fail('cold path imported scientific implementation'))
    before = deepcopy(form)
    worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)
    assert form == before


def test_canonical_storage_key_order_preserves_original_declared_section_order(example):
    form, schema, assignment, records = example
    link(form, 'same_reported_parameter')
    # Reverse the chosen field order without sorting enum arrays. On disk,
    # object keys are then sorted by canonical serialization, independently.
    schema['properties'] = dict(reversed(list(schema['properties'].items())))
    context = schema['properties']['assessment_context']['properties']
    for node in (context['quantity_links']['items']['properties']['left'],
            context['quantity_links']['items']['properties']['right'], context['assertion_links']['items']['properties']['selector']):
        node['properties']['field']['enum'].reverse()
        # Component union order also follows the selected sections.
        node['properties']['component']['enum'] = [*assignment['requested_kinetic_summary_precision_components'],
            *assignment['requested_kinetic_components']]
    stored_schema = json.loads(json.dumps(schema, sort_keys=True))
    stored_form = json.loads(json.dumps(form, sort_keys=True))
    worksheet.validate_a105_worksheet_links(stored_form, stored_schema, assignment, read_public_record=records.get)


def test_inconsistent_approximation_is_not_certified_as_same_parameter(example):
    form, schema, assignment, records = example
    link(form, 'same_reported_parameter')
    form['native_parameter'][0]['approximate'] = True
    with pytest.raises(ContractError, match='link_not_supported'):
        worksheet.validate_a105_worksheet_links(form, schema, assignment, read_public_record=records.get)


def test_nonworksheet_forms_remain_untouched():
    worksheet.validate_a105_worksheet_links({'value': 3}, {'type': 'object', 'properties': {'value': {'type': 'number'}}}, {},
        read_public_record=lambda *_: pytest.fail('unrelated form read'))


def render_text(form, records):
    parts = []
    def table(headers, rows):
        return '\n'.join(' | '.join(map(str, row)) for row in [headers, *rows])
    def section(parts, title, content):
        parts.extend([title, content])
    render.render_a105_worksheet(parts, form, section=section, table=table, public_records=records)
    return '\n'.join(parts)


def test_render_joint_requested_cells_qualifications_and_dependence_without_host_ids(example):
    form, _, _, records = example
    link(form, 'same_reported_parameter')
    text = render_text(form, records)
    assert '0.000186' in text and '4.242640687119285e-06' in text
    assert 'statistical_estimator_count_unknown' in text
    assert 'dependent views' in text and 'same original parameter report' in text
    assert worksheet.VERSION not in text
    assert re.search(r'(?:source|artifact|reference)_[a-f0-9]{24,64}', text) is None


def test_native_render_hides_unrequested_other_side_and_overlapping_public_label(example):
    form, _, _, records = example
    row = form['native_parameter'][0]
    row['denominator']['uncertainty_values']['magnitude'] = 987654321
    record = records[row['numerator']['context']['conditions']]
    record['anchor'] = deepcopy(records[row['numerator']['measurement_ref']]['anchor'])
    record['label'] = 'LEAKED_NUMERIC_PRIVATE_QUOTE'
    text = render_text(form, records)
    assert '987654321' not in text and 'LEAKED_NUMERIC_PRIVATE_QUOTE' not in text


@pytest.mark.parametrize(('scope', 'target'), [
    ('source_kinetic_summary_precision', 'summary'), ('source_endpoint_signal_contribution', 'endpoint'),
    ('source_measurement_comparison', 'comparison'),
    ('source_product_coupling', 'coupling'), ('source_calibration_recovery', 'recovery'),
    ('compiled_source_endpoint', 'compiled'), ('common_assertion_contrast', 'compiled')])
def test_renderer_routes_each_existing_family_without_scientific_io(scope, target, monkeypatch):
    captured = []
    monkeypatch.setattr(getattr(render, target), 'render_received', lambda parts, rows, **kw: captured.extend(rows))
    row = {'sheet_ref': 'source_' + 'a' * 24, 'component': 'selected', 'evaluation_scope': scope}
    form = {'selected': [row], 'context': {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}}
    render_text(form, {})
    assert captured == [row]
