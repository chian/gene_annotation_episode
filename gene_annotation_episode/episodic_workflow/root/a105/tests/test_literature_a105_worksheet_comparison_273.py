"""Mechanical composition of already interpreted comparison268 evidence.

No new paper interpretation, new assay, numerical rule or configured-model claim.
"""
from gene_annotation_episode.episodic_workflow.root.a105.library import literature_a105_worksheet as worksheet
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_measurement_comparison_storage import COMPONENTS, NAMESPACE, REQUESTED, OPERATION, measurement_comparison_cells_schema, LiteratureMeasurementComparisonRepository
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_a105_worksheet import expand, render_text
SELECTED = ['protocol_ratio', 'protocol_difference', 'required_nuisance_equivalent_scenario', 'combined_estimate']


def comparison_template(components=SELECTED):
    return worksheet.a105_worksheet_template([{'field': 'comparison', 'source': NAMESPACE, 'components': list(components)}])


def test_exact_existing_v2_schema_roster_and_order_without_new_format_version():
    requested = list(reversed(COMPONENTS))
    template = comparison_template(requested)
    assert len(COMPONENTS) == 26
    assert template['submitted_form']['properties']['comparison'] == {'$ref': 'episode-fact:' + NAMESPACE}
    assert expand(template)['properties']['comparison'] == measurement_comparison_cells_schema()
    assert template['assignment_rosters'] == {REQUESTED: requested}
    assert template['section_roles'] == [{'field': 'comparison', 'source': NAMESPACE, 'components': requested, 'numerical_role': 'measurement_comparison_validity'}]
    assert worksheet.VERSION == 'a105_source_evidence_worksheet_v1'




