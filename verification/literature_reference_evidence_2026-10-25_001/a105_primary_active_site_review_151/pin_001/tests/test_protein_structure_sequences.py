"""Sequence populations and full native residue identity are independent of CA use."""
from copy import deepcopy
from importlib import import_module
import pytest
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure
from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence, rebind_structure_sequence, inspect_structure
f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")


def from_pdb(data, **changes):
    parsed = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
    selected = f.selection(parsed)
    selected.update(changes)
    return parsed, extract_structure_sequence(parsed, selection=selected)


def test_insertion_codes_and_disjoint_numbering_are_distinct_positions():
    _, _, fixed, _ = f.fixture_pdb()
    _, _, moving, _ = f.fixture_pdb(role="moving", chain="B")
    assert fixed["alignment_sequence"] == moving["alignment_sequence"] == "AGST"
    assert [r["position_key"]["residue_number"] for r in fixed["residues"]] == [10, 10, 11, 15]
    assert [r["position_key"]["residue_number"] for r in moving["residues"]] == [101, 102, 103, 104]
    assert fixed["declared_polymer_length"] is None


def test_declared_labels_are_not_filled_and_author_numbers_are_not_order():
    _, _, seq, _ = f.fixture_cif()
    assert seq["alignment_sequence"] == "AGS"
    assert [r["position_key"]["label_seq_id"] for r in seq["residues"]] == [2, 4, 7]
    assert seq["sequence_length"] == seq["declared_polymer_length"] == 3
    gap = seq["residues"][1]
    assert gap["selected_residue_identity"] is None and gap["ca"]["state"] == "missing"
    assert gap["no_coordinate_identity"]["auth_seq_id"]["lexical_state"] == "cif_unknown"
    _, _, observed, _ = f.fixture_cif(sequence_basis="observed_polymer")
    assert observed["alignment_sequence"] == "AS" and observed["declared_polymer_length"] == 3


def test_ca_alternatives_and_explicit_choice_keep_both_raw_atoms():
    data = (f.atom_line(alt="A", occupancy="0.60") + f.atom_line(serial=2, alt="B", xyz=(0, 0, 2), occupancy="0.40")).encode()
    p, seq = from_pdb(data)
    assert seq["sequence_available"] and seq["residues"][0]["ca"]["state"] == "ambiguous"
    selected = deepcopy(seq["selection"])
    selected["ca_selection"] = {"policy": "explicit_atom_rows", "choices": [{"position_key": seq["residues"][0]["position_key"], "atom_row_key": "pdb_line_2"}]}
    seq = extract_structure_sequence(p, selection=selected)
    assert seq["residues"][0]["ca"]["selected_atom_row_key"] == "pdb_line_2"
    assert len(p["atoms"]) == 2


@pytest.mark.parametrize("occupancy,policy,state", [("", "exclude", "available"), ("0.00", "exclude", "excluded"), ("0.00", "include", "available"), ("1.01", "include", "invalid"), ("-0.10", "exclude", "invalid")])
def test_occupancy_is_unknown_zero_or_invalid_independently(occupancy, policy, state):
    _, seq = from_pdb(f.atom_line(occupancy=occupancy).encode(), zero_occupancy_policy=policy)
    assert seq["residues"][0]["ca"]["state"] == state
    assert seq["sequence_length"] == 1 and seq["sequence_available"]
    if occupancy == "":
        assert "occupancy_not_reported" in seq["residues"][0]["ca"]["qualifications"]


def test_missing_ca_and_calcium_ligand_do_not_destroy_or_extend_sequence():
    data = (f.atom_line(atom=" N  ", element="N") + f.atom_line(serial=2, component="CA", atom="CA  ", element="CA", record="HETATM", number=99)).encode()
    _, seq = from_pdb(data)
    assert seq["alignment_sequence"] == "A" and len(seq["residues"]) == 1
    assert seq["residues"][0]["ca"]["primary_reason"] == "ca_missing"


def test_unknown_symbols_require_policy_and_do_not_convert_ligands():
    data = (f.atom_line(component="SEC") + f.atom_line(serial=2, component="LIG", number=99, record="HETATM")).encode()
    p, seq = from_pdb(data)
    assert not seq["sequence_available"] and seq["native_symbols"] == ["U"]
    selected = deepcopy(seq["selection"]); selected["symbol_policy"]["unknown"] = "explicit_X"
    x = extract_structure_sequence(p, selection=selected)
    assert x["alignment_sequence"] == "X" and x["sequence_length"] == 1
    selected["symbol_policy"]["explicit_component_overrides"] = [{"component_id": "SEC", "alignment_symbol": "C"}]
    override = extract_structure_sequence(p, selection=selected)
    assert override["alignment_sequence"] == "C" and override["native_symbols"] == ["U"]


def test_explicit_role_rebinding_changes_only_declared_role_fields():
    _, _, seq, _ = f.fixture_pdb(role="single", occupancy="")
    rebound = rebind_structure_sequence(seq, structure_role="moving")
    expected = deepcopy(seq); expected["selection"]["structure_role"] = "moving"
    for issue in expected["issues"]:
        if issue["structure_role"] is not None:
            issue["structure_role"] = "moving"
    assert rebound == expected
    assert seq["selection"]["structure_role"] == "single"


def test_inventory_selects_information_without_selecting_a_model():
    _, parsed, _, _ = f.fixture_pdb()
    inventory = inspect_structure(parsed, inventory_selection={"blocks": {"kind": "all"}, "include": ["models"]})
    assert len(inventory["models"]) == 1
    assert inventory["chains"] == inventory["positions"] == inventory["metadata"] == []
    inventory = inspect_structure(parsed, inventory_selection={"blocks": {"kind": "all"}, "include": ["residue_variants", "ca_candidates", "sequence_bases"]})
    assert len(inventory["positions"]) == 4 and inventory["chains"][0]["observed_polymer_position_count"] == 4


def test_missing_polymer_join_is_unknown_population_not_empty_sequence():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"_struct_asym.entity_id 1", b"_struct_asym.entity_id 9")
    _, _, seq, _ = f.fixture_cif(data=data)
    assert seq["sequence_length"] is None and seq["sequence_available"] is False
    assert any(i["code"] == "polymer_mapping_unavailable" for i in seq["issues"])


def test_mmcif_author_namespace_conflicts_disqualify_population_without_losing_rows():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"X 1 2 100 ALA A CA", b"X 1 2 999 ALA A CA")
    _, p, seq, _ = f.fixture_cif(data=data)
    assert len(p["atoms"]) == 2 and len(seq["residues"]) == 3
    assert seq["sequence_length"] is None and not seq["sequence_available"]


def test_pdb_modres_parent_admits_modified_polymer_but_not_same_named_ligand():
    line = list(" " * 80)
    for start, text in [(0, "MODRES"), (12, "MSE"), (16, "A"), (18, "  10"), (22, " "), (24, "MET")]:
        line[start:start + len(text)] = text
    data = ("".join(line) + "\n" + f.atom_line(component="MSE", record="HETATM") + f.atom_line(serial=2, component="MSE", record="HETATM", number=11)).encode()
    _, seq = from_pdb(data)
    assert seq["alignment_sequence"] == "M" and seq["sequence_length"] == 1
    assert seq["residues"][0]["symbol_mapping_origin"] == "pdb_modres_parent"


def test_microheterogeneous_components_need_explicit_variant_not_first_row():
    data = (f.atom_line(component="ALA", alt="A") + f.atom_line(serial=2, component="GLY", alt="B")).encode()
    p, unresolved = from_pdb(data)
    assert not unresolved["sequence_available"] and unresolved["residues"][0]["selected_component_id"] is None
    selection = deepcopy(unresolved["selection"])
    selection["residue_variant_choices"] = [{"position_key": unresolved["residues"][0]["position_key"], "selected_native_component_id": "GLY"}]
    resolved = extract_structure_sequence(p, selection=selection)
    assert resolved["alignment_sequence"] == "G" and resolved["residues"][0]["ca"]["selected_atom_row_key"] == "pdb_line_2"


def test_no_coordinate_declared_chain_can_be_selected_in_an_existing_model():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"ATOM q7 C CA . SER X 1 7 500 SER A CA . 0.123456789012345 1.0 0.0 ? 92.0 5\n", b"")
    _, p, _, _ = f.fixture_cif(data=data)
    selection = f.selection(p, sequence_basis="mmcif_declared_polymer")
    seq = extract_structure_sequence(p, selection=selection)
    assert seq["sequence_available"] and seq["sequence_length"] == 3
    assert sum(r["ca"]["state"] == "missing" for r in seq["residues"]) == 2


def test_native_one_letter_maps_established_nonstandard_polymer_with_exact_evidence():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"ALA", b"MSE").replace(b"MSE A ?", b"MSE M ?")
    _, parsed, seq, _ = f.fixture_cif(data=data)
    row = seq["residues"][0]
    assert seq["alignment_sequence"] == "MGS"
    assert row["native_one_letter"] == "M" and row["symbol_mapping_origin"] == "mmcif_native_one_letter"
    address = row["symbol_evidence"][0]
    assert address["file_sha256"] == parsed["file_identity"]["sha256"]
    assert address["field_name"] == "_chem_comp.one_letter_code"
    table = next(t for t in parsed["cif_blocks"][0]["tables"] if address["record_key"] in t["row_keys"])
    native = table["rows"][table["row_keys"].index(address["record_key"])][1]
    assert native["lexeme"] == native["text"] == "M"
    assert data[native["span"]["start_0based"]:native["span"]["end_exclusive"]] == b"M"


@pytest.mark.parametrize("component,code,parent", [("MSE", "A", "MET"), ("ALA", "G", "?"), ("MSE", "M", "MET,ALA"), ("MSE", "X", "MET"), ("MSE", "MG", "?"), ("MSE", "U", "?")])
def test_conflicting_or_unsupported_native_mappings_need_explicit_policy(component, code, parent):
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"ALA", component.encode()).replace((component + " A ?").encode(), f"{component} {code} {parent}".encode())
    _, parsed, seq, _ = f.fixture_cif(data=data)
    assert not seq["sequence_available"] and seq["residues"][0]["alignment_symbol"] is None
    assert seq["residues"][0]["native_one_letter"] == code
    selected = deepcopy(seq["selection"])
    selected["symbol_policy"]["explicit_component_overrides"] = [{"component_id": component, "alignment_symbol": "M"}]
    override = extract_structure_sequence(parsed, selection=selected)
    assert override["alignment_sequence"] == "MGS"
    assert override["residues"][0]["symbol_mapping_origin"] == "explicit_override"


def test_agreeing_native_parent_is_distinct_from_native_one_letter_origin():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"ALA", b"MSE").replace(b"MSE A ?", b"MSE M MET")
    _, _, seq, _ = f.fixture_cif(data=data)
    assert seq["alignment_sequence"] == "MGS"
    assert seq["residues"][0]["symbol_mapping_origin"] == "mmcif_chemical_parent"


def test_physical_residue_helpers_preserve_ca_identity_without_equating_atom_spans():
    from gene_annotation_episode.protein_structure_sequences import residue_component_id, residue_position_key
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"ATOM q2 C CA . ALA", b"ATOM q3 N N . ALA X 1 2 100 ALA A N ? 1.0 0.0 0.0 1.0 20.0 5\nATOM q2 C CA . ALA")
    _, p, seq, _ = f.fixture_cif(data=data)
    ca = p["atoms"][2]["identity"]["residue"]
    nitrogen = p["atoms"][1]["identity"]["residue"]
    assert seq["residues"][0]["selected_residue_identity"] == ca
    assert ca != nitrogen
    assert residue_position_key(ca) == residue_position_key(nitrogen) == seq["residues"][0]["position_key"]
    assert residue_component_id(ca) == residue_component_id(nitrogen) == "ALA"


def test_inventory_includes_declared_positions_and_an_empty_declared_chain():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"_struct_asym.id X\n_struct_asym.entity_id 1", b"loop_\n_struct_asym.id\n_struct_asym.entity_id\nX 1\nY 1")
    data = data.replace(b"X 1 4 GLY A ? .", b"X 1 4 GLY A ? .\nY 1 7 SER B 900 .\nY 1 2 ALA B 800 .\nY 1 4 GLY B ? .")
    _, parsed, _, _ = f.fixture_cif(data=data)
    inventory = inspect_structure(parsed, inventory_selection={"blocks": {"kind": "all"}, "include": ["models", "chains", "sequence_bases", "residue_variants", "ca_candidates"]})
    assert len(inventory["models"]) == 1 and len(inventory["positions"]) == 6
    by_chain = {r["chain_key"]["label_asym_id"]: r for r in inventory["chains"]}
    assert by_chain["X"]["observed_polymer_position_count"] == 2
    assert by_chain["X"]["declared_polymer_position_count"] == 3
    assert by_chain["Y"]["atom_count"] == by_chain["Y"]["observed_polymer_position_count"] == 0
    assert by_chain["Y"]["declared_polymer_position_count"] == 3
    selected = f.selection(parsed, sequence_basis="mmcif_declared_polymer")
    selected["chain_key"]["label_asym_id"] = "Y"
    seq = extract_structure_sequence(parsed, selection=selected)
    assert seq["alignment_sequence"] == "AGS" and all(r["ca"]["state"] == "missing" for r in seq["residues"])


def test_invalid_pdb_atom_in_another_chain_preserves_selected_valid_population():
    malformed = f.atom_line(serial=2, chain="B")
    malformed = malformed[:22] + "oops" + malformed[26:]
    parsed, seq = from_pdb((f.atom_line(chain="A") + malformed).encode())
    assert seq["alignment_sequence"] == "A" and seq["sequence_length"] == 1
    assert parsed["atoms"][1]["identity"]["residue"] is None
    assert parsed["atoms"][1]["issues"][0]["code"] == "invalid_coordinate_identity"
    selected = deepcopy(seq["selection"]); selected["chain_key"]["chain_id"] = "B"
    assert extract_structure_sequence(parsed, selection=selected)["sequence_length"] is None


def test_invalid_pdb_atom_in_another_model_preserves_selected_valid_population():
    malformed = f.atom_line(serial=2)
    malformed = malformed[:22] + "oops" + malformed[26:]
    data = ("MODEL        1\n" + f.atom_line() + "ENDMDL\nMODEL        2\n" + malformed + "ENDMDL\n").encode()
    parsed, seq = from_pdb(data)
    assert len(parsed["models"]) == 2 and seq["alignment_sequence"] == "A"
    assert parsed["atoms"][1]["identity"]["residue"] is None


def test_invalid_cif_atom_in_another_chain_preserves_selected_valid_population():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"_note.literal_question", b"ATOM bad C CA . ? Y 1 2 100 ? B CA ? 2.0 0.0 0.0 1.0 20.0 5\n_note.literal_question")
    _, parsed, seq, _ = f.fixture_cif(data=data)
    assert seq["alignment_sequence"] == "AGS" and seq["sequence_length"] == 3
    assert parsed["atoms"][2]["identity"]["residue"] is None
    assert any(r["chain_key"]["label_asym_id"] == "Y" and parsed["atoms"][2]["identity"]["atom_row_key"] in r["atom_row_keys"] for r in parsed["chains"])


def test_unassigned_invalid_atom_keeps_raw_diagnostic_and_unknown_population():
    parsed, seq = from_pdb((f.atom_line() + "ATOM      9\n").encode())
    assert len(parsed["atoms"]) == 2 and parsed["atoms"][1]["issues"]
    assert seq["sequence_length"] is None and not seq["sequence_available"]
