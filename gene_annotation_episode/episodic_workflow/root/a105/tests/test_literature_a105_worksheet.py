"""Mechanical worksheet checks using explicit fixtures."""
from copy import deepcopy
import json
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_a105_worksheet as worksheet
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_a105_worksheet_render as render
from gene_annotation_episode.episodic_workflow.root.a105.communication import validate_closed_schema, validate_form
from gene_annotation_episode.episodic_workflow.root.a105.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a105.episode_contract_information import expand_fact_form


def expand(template):
    facts = {source: {'type': 'array', 'meaning': 'Existing selected numerical format.', 'report_schema': worksheet._schema(source)} for source in worksheet.FAMILIES}
    return expand_fact_form(json.dumps(template['submitted_form']), child_role='experimental', facts_by_role={'experimental': facts}, permitted_child_roles=['experimental'])['expanded_schema']


def test_original_nine_formats_preserve_exact_schemas_and_component_order():
    requests = [{'field': 'section_' + str(i), 'source': source, 'components': list(reversed(worksheet._components(source)))} for i, source in enumerate(tuple(worksheet.FAMILIES)[:9])]
    original = deepcopy(requests)
    result = worksheet.a105_worksheet_template(requests)
    schema = expand(result)
    assert requests == original
    assert len(result['section_roles']) == 9
    for request in requests:
        source, field = (request['source'], request['field'])
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
    worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: pytest.fail('no link needs public records'))
    node = schema['properties']['assessment_context']['properties']
    assert node['quantity_links']['maxItems'] == node['assertion_links']['maxItems'] == 0

@pytest.mark.parametrize('specification', [[], [{'field': 'bad field', 'source': worksheet.NATIVE, 'components': []}], [{'field': 'assessment_context', 'source': worksheet.NATIVE, 'components': []}], [{'field': 'a', 'source': worksheet.NATIVE, 'components': ['invented']}], [{'field': 'a', 'source': worksheet.NATIVE, 'components': ['numerator_parameter', 'numerator_parameter']}], [{'field': 'a', 'source': worksheet.NATIVE, 'components': []}, {'field': 'b', 'source': worksheet.NATIVE, 'components': []}], [{'field': 'a', 'source': worksheet.NATIVE, 'components': []}, {'field': 'a', 'source': worksheet.SUMMARY, 'components': []}]])
def test_invalid_construction_has_declared_error(specification):
    with pytest.raises(ContractError, match='a105_worksheet_request_invalid'):
        worksheet.a105_worksheet_template(specification)

def test_unregistered_format_is_unimplemented_here():
    with pytest.raises(ContractError, match='a105_worksheet_section_unimplemented'):
        worksheet.a105_worksheet_template([{'field': 'future', 'source': 'literature_unregistered_format_cells', 'components': []}])

def test_empty_roster_sibling_and_independent_output_mutation():
    requests = [{'field': 'native', 'source': worksheet.NATIVE, 'components': []}, {'field': 'summary', 'source': worksheet.SUMMARY, 'components': ['source_reported_sd']}]
    result = worksheet.a105_worksheet_template(requests, context_field='interpretation')
    assert result['assignment_rosters']['requested_kinetic_components'] == []
    result['section_roles'][1]['components'].append('source_reported_parameter')
    assert requests[1]['components'] == result['assignment_rosters']['requested_kinetic_summary_precision_components'] == ['source_reported_sd']
    assert 'maxItems' not in result['submitted_form']['properties']['interpretation']['properties']['quantity_links']


def test_unsupported_other_family_positive_join_stays_unresolved():
    template = worksheet.a105_worksheet_template([{'field': 'signal', 'source': 'literature_endpoint_signal_cells', 'components': ['retained_fraction']}])
    schema = expand(template)
    row = {'sheet_ref': 'source_' + 'd' * 24, 'component': 'retained_fraction', 'evaluation_scope': 'source_endpoint_signal_contribution'}
    selected = {'field': 'signal', 'sheet_ref': row['sheet_ref'], 'component': row['component'], 'quantity': 'cell_value'}
    context = {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [{'left': selected, 'right': deepcopy(selected), 'relation': 'unresolved', 'support_record_refs': []}], 'assertion_links': []}
    form = {'signal': [row], 'assessment_context': context}
    worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: pytest.fail('no support fetched'))
    context['quantity_links'][0]['relation'] = 'same_reported_parameter'
    with pytest.raises(ContractError, match='link_not_supported'):
        worksheet.validate_a105_worksheet_links(form, schema, template['assignment_rosters'], read_public_record=lambda *_: None)


def test_nonworksheet_forms_remain_untouched():
    worksheet.validate_a105_worksheet_links({'value': 3}, {'type': 'object', 'properties': {'value': {'type': 'number'}}}, {}, read_public_record=lambda *_: pytest.fail('unrelated form read'))

def render_text(form, records):
    parts = []

    def table(headers, rows):
        return '\n'.join((' | '.join(map(str, row)) for row in [headers, *rows]))

    def section(parts, title, content):
        parts.extend([title, content])
    render.render_a105_worksheet(parts, form, section=section, table=table, public_records=records)
    return '\n'.join(parts)


@pytest.mark.parametrize(('scope', 'target'), [('source_kinetic_summary_precision', 'summary'), ('source_endpoint_signal_contribution', 'endpoint'), ('source_measurement_comparison', 'comparison'), ('source_product_coupling', 'coupling'), ('source_calibration_recovery', 'recovery'), ('compiled_source_endpoint', 'compiled'), ('common_assertion_contrast', 'compiled')])
def test_renderer_routes_each_existing_family_without_scientific_io(scope, target, monkeypatch):
    captured = []
    monkeypatch.setattr(getattr(render, target), 'render_received', lambda parts, rows, **kw: captured.extend(rows))
    row = {'sheet_ref': 'source_' + 'a' * 24, 'component': 'selected', 'evaluation_scope': scope}
    form = {'selected': [row], 'context': {'version': worksheet.VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}}
    render_text(form, {})
    assert captured == [row]
