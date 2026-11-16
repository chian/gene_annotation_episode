"""Closed result requests, independent of episode authority or science execution."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import issue
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_views import protein_structure_fact_sources
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_selection import protein_structure_result_selector_schema

FIXTURES = Path(__file__).resolve().parents[1] / "gene_annotation_episode/episodic_workflow/root/a102/tests/fixtures/protein_structure_result_worker_393/fixtures"


def native(name="held_out"):
    return json.loads((FIXTURES / (name + ".json")).read_bytes())


def test_schema_contains_exact_reachable_definitions_only():
    schema = protein_structure_result_selector_schema()
    Draft202012Validator.check_schema(schema)
    original = protein_structure_fact_sources()["execution_protein_structure_projections"]["report_schema"]["$defs"]
    assert len(schema["$defs"]) < len(original)
    assert all(value == original[name] for name, value in schema["$defs"].items())
    assert "ProteinStructureComponents" not in schema["$defs"]
    assert schema["$id"] == "urn:gene-annotation:protein-structure:schema:" + digest({k:v for k,v in schema.items() if k != "$id"})
    schema["$defs"]["ProteinResultSelector"]["additionalProperties"] = True
    assert protein_structure_result_selector_schema()["$defs"]["ProteinResultSelector"]["additionalProperties"] is False


def test_structured_operand_error_preserves_exact_issue_and_detached_detail():
    problem = issue("sequence_not_received", stage="authority", field="descriptor")
    error = ProteinStructureOperandError(problem)
    assert str(error) == "sequence_not_received"
    assert error.issue == problem and error.detail == {"protein_structure_issue": problem}
    problem["code"] = "invalid_schema"
    assert error.issue["code"] == "sequence_not_received"
    error.issue["code"] = "invalid_schema"
    assert error.detail["protein_structure_issue"]["code"] == "sequence_not_received"
    with pytest.raises(ValueError, match="invalid_schema"):
        ProteinStructureOperandError({"code": "made_up"})
