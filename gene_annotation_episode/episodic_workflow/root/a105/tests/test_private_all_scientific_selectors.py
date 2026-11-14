"""Actual dynamically selected A105 contracts, including private pilot factories."""
from importlib import import_module
from pathlib import Path

import pytest

AXIS = 'gene_annotation_episode.episodic_workflow.root.a105'
PILOT = AXIS + '.scientific_process.published_evidence_assessment.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination'


def axis_module(name):
    path = import_module(AXIS + '.literature_implementation_sources').source_file(name + '.py')
    root = Path(import_module(AXIS).__file__).parent
    return import_module(AXIS + '.' + '.'.join(path.resolve().relative_to(root.resolve()).with_suffix('').parts))


def test_axis_received_partner_contract_retains_source_qualification():
    schema = axis_module('literature_assay_grading_inputs').source_schema('literature_partner_cells')
    props = schema['items']['properties']
    assert schema['x-source'] == 'literature_partner_cells'
    assert props['target_correspondence']['enum'] == ['not_evaluated']
    assert props['partner_necessity']['enum'] == ['not_inferred']
    assert 'unavailable' in props['status']['enum']
    assert 'subject_mismatch' in props['unavailable_reason']['enum']
    assert props['experiment_ref']['x-reference-namespace'] == 'reference'


@pytest.mark.parametrize('kind', ('grading', 'numerical', 'worksheet', 'population_metadata'))
def test_pilot_actual_scientific_selectors_resolve_owned_factories(kind):
    if kind == 'grading':
        module = import_module(PILOT + '.grading.literature_assay_grading_inputs')
        outputs = {name: module.source_schema(name) for name in module.SOURCE_SCHEMAS}
    elif kind == 'numerical':
        module = import_module(PILOT + '.tools.literature_numerical_contracts')
        outputs = {name: module.registered_schema(name) for name in module.registered_sources()}
    elif kind == 'worksheet':
        module = import_module(PILOT + '.tools.literature_a105_worksheet')
        outputs = {name: module._schema(name) for name in module.FAMILIES}
    else:
        module = import_module(PILOT + '.prompts.literature_task_selection')
        outputs = list(module.population_task_metadata_specs())
        assert len(outputs) == len(module._FAMILIES)
        assert len({row[0] for row in outputs}) == len(outputs)
        assert all(row[2] and row[3] and row[4] for row in outputs)
        return
    assert outputs
    for name, schema in outputs.items():
        assert schema['type'] == 'array', name
        assert schema['items']['type'] == 'object', name
        assert schema['items']['properties'], name
