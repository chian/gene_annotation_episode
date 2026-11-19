"""Generation-bound kinetics and authentic original-release reconstruction.

All sources are synthetic. The original-v2 states were selected with intact
archived production code before this repair, never relabelled from new results.
"""
import hashlib
import sqlite3
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_kinetic_storage import LiteratureKineticRepository
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_kinetic_model_storage import LiteratureKineticModelRepository
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_kinetic_inputs import fixture
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_kinetic_storage import setup

@pytest.mark.parametrize('token', ['-8', '18', '8e3', 'between 8 and 9', 'SD 8', '8/2'])
def test_called_scalar_contract_rejects_clipping_and_wrong_scientific_role(token):
    source, selection = fixture(n=token)
    number = selection['numerator']['measurement']['number']
    number.update(witness=source.witness('8'), number_start=0, number_end=1)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)

@pytest.mark.parametrize('unit', ['M^-1</td><td>s^-1', 'uM^-1min^-1/mg'])
def test_selected_compound_unit_cannot_cross_cells_or_omit_factor(unit):
    source, selection = fixture(unit=unit)
    if '/mg' in unit:
        selection['numerator']['measurement']['unit'] = source.witness('uM^-1min^-1')
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


