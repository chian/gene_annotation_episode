"""Statistical premise custody; no arithmetic changes or primary-paper inference."""

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import (
    ReportBoundaryError, validate_closed_schema,
)
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.perturbation_evidence.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.perturbation_evidence.literature_perturbation_summary_storage import perturbation_summary_cells_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.tests.test_literature_perturbation_summary import extract
from .library_data import data_with_basis
from .library_world import run_scenarios, world  # noqa: F401 - ``world`` is the fixture





@pytest.mark.parametrize('mutation', [
    lambda b: b.pop('summary_scale'),
    lambda b: b.update(extra='source_reported'),
    lambda b: b.update(summary_scale='probably_reported'),
    lambda b: b.update(count_n=None),
    lambda b: b.update(spread_kind=True),
])
def test_basis_is_closed_without_changing_selected_numerical_meanings(mutation):
    data = data_with_basis()
    mutation(data['measurements']['W']['interpretation_basis'])
    with pytest.raises(ExperimentalContractError):
        extract(data)



@pytest.mark.parametrize('kind', ['changed_enum', 'unknown_field', 'unknown_source', 'nested', 'generic_optional'])
def test_registered_schema_exception_is_exact_and_does_not_relax_generic_forms(kind):
    node = perturbation_summary_cells_schema()
    if kind == 'changed_enum':
        node['items']['properties']['statistical_interpretation_basis']['properties']['W']['properties']['summary_scale']['enum'].append('guessed')
    elif kind == 'unknown_field':
        node['items']['properties']['extra'] = {'type': 'number'}
    elif kind == 'unknown_source':
        node['x-source'] = 'unregistered_perturbation_cells'
    if kind == 'nested':
        schema = obj({'nested': obj({'measurements': node})})
    elif kind == 'generic_optional':
        schema = obj({'metadata': {'type': 'object', 'properties': {'optional': {'type': 'number'}},
            'required': [], 'additionalProperties': False}})
    else:
        schema = obj({'measurements': node})
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)


def test_exact_contributing_roles_and_qualification_survive_typed_receipt(world):
    outcome, = run_scenarios(world, 'basis', ('basis_receipt', {}))
    assert outcome == {'rows': 8}
