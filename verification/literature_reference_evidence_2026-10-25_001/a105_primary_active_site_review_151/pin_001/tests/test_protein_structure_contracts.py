"""Closed-shape, relationship and detached-copy checks for shared contract 380."""
from copy import deepcopy
from importlib import import_module
import math
import pytest
from jsonschema import Draft202012Validator
from gene_annotation_episode import protein_structure_contracts as c
f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")


def test_every_public_type_has_detached_resolvable_schema():
    definitions = c.protein_structure_schema_definitions()
    for name in c.PUBLIC_TYPE_NAMES:
        assert c.protein_structure_schema_ref(name) == {"$ref": "#/$defs/" + name}
        Draft202012Validator.check_schema({"$defs": definitions, **c.protein_structure_schema_ref(name)})
    definitions["FileIdentity"]["properties"].clear()
    assert c.protein_structure_schema_definitions()["FileIdentity"]["properties"]
    with pytest.raises(ValueError, match="invalid_schema"):
        c.protein_structure_schema_ref("NotAContract")


@pytest.mark.parametrize("mutation", [lambda x: x.update(byte_length=True), lambda x: x.update(byte_length=1.0), lambda x: x.update(extra=1), lambda x: x.update(sha256="f" * 64)])
def test_file_identity_rejects_wrong_types_extra_fields_and_mismatched_digest(mutation):
    value = f.identity(b"abc", "pdb_3x_text")
    mutation(value)
    with pytest.raises(ValueError):
        c.validate_file_identity(value)


def test_selection_and_map_validation_is_detached_and_role_specific():
    _, parsed, seq, _ = f.fixture_pdb()
    result = c.validate_structure_sequence(seq)
    result["selection"]["chain_key"]["chain_id"] = "B"
    assert seq["selection"]["chain_key"]["chain_id"] == "A"
    bad = deepcopy(seq); bad["residues"][1]["sequence_position_0based"] = 0
    with pytest.raises(ValueError, match="conflicting_identity"):
        c.validate_structure_sequence(bad)
    bad = deepcopy(seq); bad["residues"][0]["position_key"]["file_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="conflicting_identity"):
        c.validate_structure_sequence(bad)
    bad = deepcopy(parsed); bad["atoms"][0]["xyz_A"][0]["value"] = math.inf
    with pytest.raises(ValueError, match="invalid_schema"):
        c.validate_parsed_structure(bad)


def test_fixed_selection_requirements_and_count_cells():
    _, _, seq, _ = f.fixture_pdb()
    value = deepcopy(seq["selection"]); value["bfactor_semantics"] = "declared_plddt"
    with pytest.raises(ValueError, match="metadata_join_conflict"):
        c.validate_structure_selection(value)
    value = f.fit_parameters(); value["numerical"]["svd_relative_tolerance"] = -1.0
    with pytest.raises(ValueError, match="invalid_schema"):
        c.validate_calculation_parameters(value)
    value = f.fit_parameters(); value["fit_selection"] = None
    with pytest.raises(ValueError, match="invalid_schema"):
        c.validate_calculation_parameters(value)


def test_descriptor_formats_receipt_identity_and_real_store_identifier_grammar():
    _, _, seq, _ = f.fixture_pdb()
    desc = f.sequence_descriptor(seq)
    assert c.validate_structure_sequence_descriptor(desc) == desc
    bad = deepcopy(desc); bad["custody"]["result_receipt_key"] += "x"
    with pytest.raises(ValueError, match="conflicting_identity"):
        c.validate_structure_sequence_descriptor(bad)
    bad = deepcopy(desc); bad["allowed_uses"] *= 2
    with pytest.raises(ValueError, match="duplicate_selection"):
        c.validate_structure_sequence_descriptor(bad)


def test_declared_transform_record_validates_shape_not_rotation_math():
    _, _, fixed, _ = f.fixture_pdb()
    _, _, moving, _ = f.fixture_pdb(role="moving", chain="B")
    transform = {"version": "protein_structure_transform_v1", "direction": "moving_to_fixed", "convention": "row_vector_y_R_plus_t",
        "rotation": [[2.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 2.0]], "translation_A": [0.0, 0.0, 0.0],
        "fixed_selection": fixed["selection"], "moving_selection": moving["selection"], "origin": "supplied", "received_from": None}
    assert c.validate_declared_transform_record(transform) == transform  # Proper rotation is B's separate check.


def test_structural_correspondence_rejects_impossible_unmapped_relationship():
    fixed = f.fixture_pdb()[2]
    moving = f.fixture_pdb(role="moving", chain="B")[2]
    _, _, value = f.explicit_map(fixed, moving, [(0, 0)])
    bad = deepcopy(value)
    bad["unmapped_fixed"][0]["sequence_position_0based"] = 0
    bad["unmapped_fixed"][0]["position_key"] = fixed["residues"][0]["position_key"]
    with pytest.raises(ValueError, match="conflicting_identity"):
        c.validate_correspondence(bad)
    bad = deepcopy(value); bad["population_available"] = False; bad["state"] = "complete"
    with pytest.raises(ValueError, match="conflicting_identity"):
        c.validate_correspondence(bad)


def test_structural_metadata_rejects_a_foreign_model_identity():
    _, _, _, value = f.fixture_cif()
    bad = deepcopy(value)
    bad["atom_uncertainty"][0]["residue_identity"]["model_key"]["ordinal_0based"] += 1
    with pytest.raises(ValueError, match="conflicting_identity"):
        c.validate_structure_metadata(bad)


def test_correspondence_input_orientation_authenticates_exact_reference_pair():
    fixed = f.fixture_pdb()[2]
    moving = f.fixture_pdb(role="moving", chain="B")[2]
    _, kwargs, _ = f.retained_alignment(fixed, moving)
    value = {"kind": "retained_alignment", "alignment": kwargs["alignment"], "fixed_sequence_descriptor": kwargs["fixed_descriptor"],
        "moving_sequence_descriptor": kwargs["moving_descriptor"], "orientation": kwargs["orientation"]}
    assert c.validate_correspondence_input(value) == value
    value["orientation"] = "fixed_is_reference"
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        c.validate_correspondence_input(value)
