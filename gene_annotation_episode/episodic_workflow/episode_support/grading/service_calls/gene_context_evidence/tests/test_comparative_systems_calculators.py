"""The restored BV-BRC ComparativeSystems sheet calculator (97308b94c text, imports repointed) recalculates the
numerical values of the reviewed sheets' saved components exactly: counts of assignment records, ratios with their
operands and named populations. Fixture: ``fixtures/bvbrc_comparative_systems_calculators/
saved_examples.json`` at ``97308b94c``; the examples were assembled before the calculator began recording each cell's
input pointers (``input_refs``, ``qualification_codes``), so the values, quantities and sheet digest are compared."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.grading.service_calls.gene_context_evidence.bvbrc_comparative_systems_calculators import (
    calculate_comparative_systems_components)

EXAMPLES = json.loads((Path(__file__).parent / 'fixtures' / 'comparative_systems_saved_examples.json').read_text())['examples']


def values(components):
    return {row['component_id']: (row['quantity'], *(row['value'].get(key) for key in ('state', 'value', 'unit')))
            for row in components['components']}


@pytest.mark.parametrize('sheet_name,components_name', [
    ('pathway_subsystem_sheet', 'pathway_subsystem_components'), ('families_sheet', 'families_components'),
    ('hex_256_sheet', 'hex_256_components'), ('pathway_subsystem_sheet', 'saved_sheet_recalculation')])
def test_the_saved_sheet_recalculates_to_its_saved_component_values(sheet_name, components_name):
    sheet, saved = EXAMPLES[sheet_name], EXAMPLES[components_name]
    before = deepcopy(sheet)
    actual = calculate_comparative_systems_components(sheet, parameters=saved['parameters'])
    assert (actual['sheet_sha256'], actual['formula_version']) == (saved['sheet_sha256'], saved['formula_version'])
    assert values(actual) == values(saved)
    assert sheet == before
