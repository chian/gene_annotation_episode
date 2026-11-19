"""The restored genomic-overlap calculator (97308b94c text, imports repointed) reproduces the hand-worked components
of the contract's worked example: occurrence counts and union quantities apart, ratios with integer operands, no
invented uncertainty. Fixture: ``root/a103/tests/fixtures/genomic_overlap/contract/WORKED_EXAMPLE.json`` at
``97308b94c``."""
from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.calculations.sequence_and_context_sources.genomic_overlap_calculations import (
    calculate_genomic_overlap_components)

EXAMPLE = json.loads((Path(__file__).parent / 'fixtures' / 'genomic_overlap' / 'WORKED_EXAMPLE.json').read_text())


def test_the_worked_sheet_calculates_to_the_worked_components():
    sheet, components = EXAMPLE['sheet'], EXAMPLE['components']
    before = deepcopy(sheet)
    assert calculate_genomic_overlap_components(sheet, parameters=components['parameters']) == components
    assert sheet == before
