"""Resolve every original registered A106 scientific schema without acquisition."""
from copy import deepcopy
import pytest
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_numerical_contracts as numerical
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_a105_worksheet as worksheet
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_assay_grading_inputs as grading
from gene_annotation_episode.episodic_workflow.root.a106.library import literature_task_families as tasks


@pytest.mark.parametrize('source',numerical.registered_sources())
def test_original_numerical_schema_registry_resolves_detached_schema(source):
    schema=numerical.registered_schema(source)
    assert isinstance(schema,dict) and schema
    expected=deepcopy(schema)
    schema['fixture-only-mutation']=True
    assert numerical.registered_schema(source)==expected


@pytest.mark.parametrize('source',tuple(worksheet.FAMILIES))
def test_original_worksheet_schema_registry_resolves_original_components(source):
    schema=worksheet._schema(source)
    assert schema['type']=='array'
    assert worksheet._components(source)==schema['items']['properties']['component']['enum']


@pytest.mark.parametrize('source',tuple(grading.SOURCE_SCHEMAS))
def test_original_assessment_source_registry_resolves_original_schema(source):
    schema=grading.source_schema(source)
    assert isinstance(schema,dict) and schema
    assert schema['type']=='array'


def test_original_task_metadata_keeps_all_three_intervention_families():
    values=list(tasks.population_task_metadata_specs())
    assert len(values)==3
    assert set(tasks._ROWS)=={'literature_perturbation_cells',
        'literature_intervention_grading_cells','literature_a106_subscore_cells'}
