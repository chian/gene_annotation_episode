"""Mechanical worksheet checks using explicit fixtures."""
from copy import deepcopy
import json
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence import literature_worksheet as worksheet
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence import literature_worksheet_render as render
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError






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
