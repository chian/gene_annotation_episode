"""Actual A106 exception boundaries, without changing scientific contracts."""
import pytest
from gene_annotation_episode.domain import ContractError as CanonicalContractError
from gene_annotation_episode.episodic_workflow.root.a106 import domain


def test_contract_error_is_original_canonical_type_and_keeps_detail():
    assert domain.ContractError is CanonicalContractError
    detail = {"field_path": ["effect"], "schema_keyword": "type"}
    error = domain.ContractError("representation_error", detail=detail)
    assert type(error) is CanonicalContractError
    assert isinstance(error, ValueError)
    assert error.args == ("representation_error",)
    assert error.detail is detail
    assert domain.ContractError("a").detail == {}
    assert domain.ContractError("a").detail is not domain.ContractError("a").detail


def test_own_schema_validator_raises_original_catch_identity_and_detail():
    with pytest.raises(CanonicalContractError) as caught:
        domain.validate_schema({"effect": "invalid"}, domain.obj({"effect": {"type": "number"}}))
    assert str(caught.value) == "representation_error"
    assert caught.value.detail == {"field_path": ["effect"], "schema_keyword": "type"}


def test_comparison_rejects_wrong_role_before_reading_any_cells():
    from gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_inputs import read_comparison_operand
    def forbidden(*args, **kwargs):
        pytest.fail("An inadmissible comparison role acquired scientific cells")
    with pytest.raises(CanonicalContractError, match="^intervention_comparison_quantity_role_mismatch$"):
        read_comparison_operand({"component": "required_interference_scenario"}, role="effect", quantity_kind="endpoint_difference", read_cells=forbidden)


def test_revision_conflict_remains_own_subclass_with_original_fields():
    from gene_annotation_episode.episodic_workflow.root.a106.state import RevisionConflict
    assert RevisionConflict is not CanonicalContractError
    assert RevisionConflict.__module__ == "gene_annotation_episode.episodic_workflow.root.a106.state"
    with pytest.raises(CanonicalContractError) as caught:
        raise RevisionConflict("sequence", "sequence_ref", 3, "proposal_ref")
    assert type(caught.value) is RevisionConflict
    assert caught.value.args == ("revision_conflict",)
    assert caught.value.detail == {"kind": "sequence", "key_ref": "sequence_ref", "current_revision": 3, "proposal_ref": "proposal_ref"}


