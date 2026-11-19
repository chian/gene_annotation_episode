"""Worksheet composition resolves the same native scientific component schemas."""
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence import literature_worksheet as literature_a105_worksheet
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_assay_grading_storage import assay_grading_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_aggregation_storage import aggregation_cells_schema

@pytest.mark.parametrize('source,factory', [('literature_assay_grading_cells', assay_grading_cells_schema), ('literature_a105_aggregation_cells', aggregation_cells_schema)])
def test_worksheet_uses_actual_original_component_schema(source, factory):
    assert literature_a105_worksheet._schema(source) == factory()
