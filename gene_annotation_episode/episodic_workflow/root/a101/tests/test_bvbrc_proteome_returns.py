"""Real provider outputs through Store/Journal and the typed return boundary.

Inputs are retained synthetic native-format bytes. ControlledPublications is an
explicit test publication envelope, not an AppService transport or full Workflow.
The parsers, input/joins/sheet constructors, calculators, custody and typed
communication classes are real; no live GenomeComparison service is claimed.
"""

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library import bvbrc_proteome_fact_contracts as facts
from gene_annotation_episode.episodic_workflow.root.a101.bvbrc_proteome_returns import BVBRCProteomeReturns
from gene_annotation_episode.episodic_workflow.root.a101.library.bvbrc_proteome_return_values import FACT_SOURCES as ALL_FACT_SOURCES, IDENTIFIER_NAMESPACES, ProteomeReturnError, proteome_fact_sources, requested_sources, project_proteome_facts, _report_node
from gene_annotation_episode.episodic_workflow.root.a101.communication import validate_closed_schema


# This retained fixture exercises the eight original v1 fact families. The
# production descriptor catalog additionally supplies the fourteen v2 families.
FACT_SOURCES = (
    'bvbrc_proteome_measurements', 'bvbrc_proteome_ratios', 'bvbrc_proteome_populations',
    'bvbrc_proteome_associations', 'bvbrc_proteome_selections', 'bvbrc_proteome_requirements',
    'bvbrc_proteome_qualifications', 'bvbrc_proteome_request_status')
MEASUREMENTS, RATIOS, POPULATIONS, ASSOCIATIONS, SELECTIONS, REQUIREMENTS, QUALIFICATIONS, STATUS = FACT_SOURCES


def fact_form(*sources):
    descriptors = proteome_fact_sources()
    properties = {f'f{i}': descriptors[source]['report_schema'] for i, source in enumerate(sources)}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def test_eight_exact_families_and_explicit_closed_semantic_namespaces():
    descriptors = proteome_fact_sources()
    assert FACT_SOURCES == (
        'bvbrc_proteome_measurements', 'bvbrc_proteome_ratios', 'bvbrc_proteome_populations',
        'bvbrc_proteome_associations', 'bvbrc_proteome_selections', 'bvbrc_proteome_requirements',
        'bvbrc_proteome_qualifications', 'bvbrc_proteome_request_status')
    assert tuple(descriptors) == ALL_FACT_SOURCES == FACT_SOURCES + tuple(
        'bvbrc_proteome_' + suffix for suffix in (
            'directional_counts', 'directional_fractions', 'directional_coverages',
            'directional_native_integers', 'directional_native_decimals', 'directional_states',
            'directional_extrema', 'directional_intervals', 'directional_columns',
            'directional_edges', 'directional_conflicts', 'directional_support',
            'directional_issues', 'directional_requirements'))
    assert set(IDENTIFIER_NAMESPACES) == {'bvbrc_proteome_' + kind for kind in (
        *facts.REFERENCE_KINDS, 'track', 'association', 'inventory', 'native_identifier', 'protein', 'report',
        'requested_field', 'native_category', 'document')}
    schema = fact_form(*FACT_SOURCES)
    assert validate_closed_schema(schema) == schema
    assert requested_sources(fact_form(STATUS, MEASUREMENTS, STATUS)) == (STATUS, MEASUREMENTS)
    assert BVBRCProteomeReturns.fact_sources() == descriptors
    for descriptor in descriptors.values():
        assert descriptor['report_schema']['items']['properties']['source_ref']['x-reference-namespace'] == 'execution_result'
    descriptors[MEASUREMENTS]['report_schema']['items']['properties'].clear()
    assert proteome_fact_sources()[MEASUREMENTS]['report_schema']['items']['properties']


@pytest.mark.parametrize('schema', [
    {'oneOf': [{'type': 'number'}, {'type': 'null'}]}, {'type': 'string'},
    {'anyOf': [{'type': 'number'}, {'type': 'integer'}]},
    {'type': 'string', 'pattern': '.*'},
])
def test_unreviewed_schema_unions_and_free_strings_are_rejected(schema):
    with pytest.raises(ProteomeReturnError, match='fact_schema_unsupported'):
        _report_node(schema)


@pytest.mark.parametrize('sources', [[], (MEASUREMENTS, MEASUREMENTS), ('unknown',), None, {MEASUREMENTS}])
def test_requested_source_selection_is_finite_unique_tuple(sources):
    with pytest.raises(ProteomeReturnError, match='requested_sources_invalid'):
        project_proteome_facts({}, requested_sources=sources, sheet=None, components=None)

