"""Actual A106 exception boundaries, without changing scientific contracts."""
import pytest
from gene_annotation_episode.domain import ContractError as CanonicalContractError
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence import domain



def test_own_schema_validator_raises_original_catch_identity_and_detail():
    with pytest.raises(CanonicalContractError) as caught:
        domain.validate_schema({"effect": "invalid"}, domain.obj({"effect": {"type": "number"}}))
    assert str(caught.value) == "representation_error"
    assert caught.value.detail == {"field_path": ["effect"], "schema_keyword": "type"}


def test_comparison_rejects_wrong_role_before_reading_any_cells():
    from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_intervention_inputs import read_comparison_operand
    def forbidden(*args, **kwargs):
        pytest.fail("An inadmissible comparison role acquired scientific cells")
    with pytest.raises(CanonicalContractError, match="^intervention_comparison_quantity_role_mismatch$"):
        read_comparison_operand({"component": "required_interference_scenario"}, role="effect", quantity_kind="endpoint_difference", read_cells=forbidden)


