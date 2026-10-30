"""Native provenance, exact uncertainty joins, and directed QA values."""
from copy import deepcopy
from importlib import import_module
import pytest
from gene_annotation_episode.protein_structure_contracts import canonical
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure
from gene_annotation_episode.protein_structure_sequences import extract_structure_sequence
from gene_annotation_episode.protein_structure_metadata import extract_native_structure_metadata
f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")


def declared_metadata(parsed, seq, semantics):
    selected = deepcopy(seq["selection"])
    document = {"version": "protein_structure_metadata_v1", "semantics_declarations": [{"declaration_id": "producer_semantics",
        "scope": {"structure_file": selected["file_identity"], "data_block": selected["data_block"], "model_key": selected["model_key"], "chain_key": selected["chain_key"]},
        "bfactor_semantics": semantics, "producer_name": "Synthetic documented producer", "producer_version": "1",
        "evidence_artifact_ref": parsed["file_identity"]["artifact_ref"], "evidence_span": None}], "metric_unit_declarations": []}
    file = f.identity(canonical(document).encode(), "protein_structure_metadata_v1")
    selected.update(bfactor_semantics=semantics, semantics_evidence={"file_identity": file, "declaration_id": "producer_semantics"})
    seq = extract_structure_sequence(parsed, selection=selected)
    return seq, [{"file_identity": file, "document": document}]


def test_bfactor_never_becomes_confidence_without_provenance():
    _, _, _, metadata = f.fixture_pdb(b="92.00")
    row = metadata["atom_uncertainty"][0]
    assert row["b_factor_native"]["value"] == 92.0
    assert row["plddt"]["value"] is None and row["physical_b_A2"]["value"] is None
    _, parsed, seq, _ = f.fixture_pdb(b="92.00")
    seq, supplied = declared_metadata(parsed, seq, "declared_plddt")
    meta = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=supplied)
    assert meta["atom_uncertainty"][0]["plddt"]["value"] == 92.0
    assert meta["atom_uncertainty"][0]["physical_b_A2"]["state"] == "not_applicable"
    with pytest.raises(ValueError, match="metadata_join_conflict"):
        extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=[])


def test_displacement_blank_and_measured_zero_are_distinct():
    _, parsed, seq, _ = f.fixture_pdb(b="20.00")
    seq, supplied = declared_metadata(parsed, seq, "native_atomic_displacement")
    row = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=supplied)["atom_uncertainty"][0]
    assert row["physical_b_A2"]["value"] == 20.0 and row["physical_b_A2"]["unit"] == "angstrom_squared"
    assert row["plddt"]["value"] is None
    _, _, _, blank = f.fixture_pdb(b="")
    _, _, _, zero = f.fixture_pdb(b="0.00")
    assert blank["atom_uncertainty"][0]["b_factor_native"]["state"] == "missing"
    assert zero["atom_uncertainty"][0]["b_factor_native"]["value"] == 0.0
    assert "native_zero_b_not_proof_of_measured_uncertainty" in zero["atom_uncertainty"][0]["qualifications"]


def test_pdb_anisou_siguiij_sigatm_join_full_atom_identity(tmp_path):
    atom = f.atom_line(alt="A")
    anisou = "ANISOU" + atom[6:28] + "".join(f"{v:7d}" for v in [10000, 20000, 30000, -4000, 5000, 6000]) + atom[70:]
    siguij = "SIGUIJ" + atom[6:28] + "".join(f"{v:7d}" for v in [10, 20, 30, 40, 50, 60]) + atom[70:]
    sigatm = "SIGATM" + atom[6:30] + "".join(f"{v:8.3f}" for v in [0.1, 0.2, 0.3]) + atom[54:]
    unmatched = anisou[:16] + "B" + anisou[17:]
    data = (atom + anisou + siguij + sigatm + unmatched).encode()
    parsed = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
    seq = extract_structure_sequence(parsed, selection=f.selection(parsed))
    meta = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=[])
    row = meta["atom_uncertainty"][0]
    assert [x["value"] for x in row["anisotropic_U_A2"]] == pytest.approx([1, 2, 3, -0.4, 0.5, 0.6])
    assert [x["value"] for x in row["anisotropic_U_standard_uncertainty_A2"]] == pytest.approx([0.001, 0.002, 0.003, 0.004, 0.005, 0.006])
    assert [x["value"] for x in row["coordinate_standard_uncertainty_xyz_A"]] == [0.1, 0.2, 0.3]
    assert meta["unjoined_rows"][0]["row_key"] == "pdb_line_5"
    (tmp_path / "uncertainty.pdb").write_bytes(data)
    (tmp_path / "native_uncertainty.json").write_text(canonical({"parsed": parsed, "sequence": seq, "metadata": meta}) + "\n", encoding="utf-8")


def test_modelcif_local_plddt_and_ordered_pae_retain_native_meaning(tmp_path):
    extra = """
loop_
_ma_qa_metric.id
_ma_qa_metric.name
_ma_qa_metric.type
_ma_qa_metric.mode
_ma_qa_metric.software_group_id
q confidence pLDDT local 1
p error PAE local-pairwise 1
loop_
_ma_qa_metric_local.ordinal_id
_ma_qa_metric_local.model_id
_ma_qa_metric_local.label_asym_id
_ma_qa_metric_local.label_seq_id
_ma_qa_metric_local.label_comp_id
_ma_qa_metric_local.metric_id
_ma_qa_metric_local.metric_value
1 5 X 2 ALA q 91
2 5 X 7 SER q 80
loop_
_ma_qa_metric_local_pairwise.ordinal_id
_ma_qa_metric_local_pairwise.model_id
_ma_qa_metric_local_pairwise.label_asym_id_1
_ma_qa_metric_local_pairwise.label_seq_id_1
_ma_qa_metric_local_pairwise.label_comp_id_1
_ma_qa_metric_local_pairwise.label_asym_id_2
_ma_qa_metric_local_pairwise.label_seq_id_2
_ma_qa_metric_local_pairwise.label_comp_id_2
_ma_qa_metric_local_pairwise.metric_id
_ma_qa_metric_local_pairwise.metric_value
3 5 X 2 ALA X 7 SER p 3
4 5 X 7 SER X 2 ALA p 8
"""
    data, parsed, sequence, meta = f.fixture_cif(extra=extra)
    ordered = [r for r in meta["qa_rows"] if r["scope"] == "ordered_pair"]
    assert [(r["endpoint_1"]["label_seq_id"], r["endpoint_2"]["label_seq_id"], r["value"]["value"]) for r in ordered] == [(2, 7, 3.0), (7, 2, 8.0)]
    assert ordered[0]["value"]["unit"] == "angstrom"
    assert [r["plddt"]["value"] for r in meta["atom_uncertainty"]] == [80.0, 91.0]
    (tmp_path / "ordered_qa.cif").write_bytes(data)
    (tmp_path / "native_qa.json").write_text(canonical({"parsed": parsed, "sequence": sequence, "metadata": meta}) + "\n", encoding="utf-8")


def test_embedded_coordinate_esd_and_anisotrop_join_by_id_not_row_order():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"0.123456789012345 1.0 0.0", b"1.234(5)e2 1.0 0.0")
    extra = """
loop_
_atom_site_anisotrop.id
_atom_site_anisotrop.pdbx_label_asym_id
_atom_site_anisotrop.pdbx_label_seq_id
_atom_site_anisotrop.U[1][1]
_atom_site_anisotrop.U[2][2]
_atom_site_anisotrop.U[3][3]
_atom_site_anisotrop.U[1][2]
_atom_site_anisotrop.U[1][3]
_atom_site_anisotrop.U[2][3]
q2 X 2 1 2 3 4 5 6
q7 X 7 10 20 30 40 50 60
"""
    _, _, _, meta = f.fixture_cif(data=data, extra=extra)
    assert meta["atom_uncertainty"][0]["coordinate_standard_uncertainty_xyz_A"][0]["value"] == 0.5
    assert [c["value"] for c in meta["atom_uncertainty"][0]["anisotropic_U_A2"]] == [10, 20, 30, 40, 50, 60]
    assert [c["value"] for c in meta["atom_uncertainty"][1]["anisotropic_U_A2"]] == [1, 2, 3, 4, 5, 6]


def test_conflicting_anisotrop_qualifier_stays_unjoined():
    extra = """
loop_
_atom_site_anisotrop.id
_atom_site_anisotrop.pdbx_label_asym_id
_atom_site_anisotrop.U[1][1]
q2 Y 1
"""
    _, _, _, meta = f.fixture_cif(extra=extra)
    assert meta["unjoined_rows"] and meta["atom_uncertainty"][1]["anisotropic_U_A2"][0]["value"] is None


def test_conflicting_explicit_and_embedded_esds_are_not_averaged():
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"_atom_site.Cartn_x\n", b"_atom_site.Cartn_x\n_atom_site.Cartn_x_esd\n")
    data = data.replace(b"0.123456789012345 1.0 0.0", b"1.234(5)e2 0.7 1.0 0.0")
    data = data.replace(b"? 0.0 0.0 0.0 1.0 20.0 5", b"? 0.0 ? 0.0 0.0 1.0 20.0 5")
    _, _, _, meta = f.fixture_cif(data=data)
    cell = meta["atom_uncertainty"][0]["coordinate_standard_uncertainty_xyz_A"][0]
    assert cell["state"] == "invalid" and cell["value"] is None
    assert any(i["code"] == "metadata_join_conflict" for i in meta["issues"])


def test_unknown_qa_type_keeps_native_value_and_unknown_units():
    extra = """
_ma_qa_metric.id q
_ma_qa_metric.name pLDDT
_ma_qa_metric.type other
_ma_qa_metric.mode global
_ma_qa_metric.software_group_id 1
_ma_qa_metric_global.ordinal_id 1
_ma_qa_metric_global.model_id 5
_ma_qa_metric_global.metric_id q
_ma_qa_metric_global.metric_value 92
"""
    _, _, _, meta = f.fixture_cif(extra=extra)
    assert meta["metric_definitions"][0]["meaning"] == "unknown"
    assert meta["qa_rows"][0]["value"]["unit"] == "unknown" and meta["qa_rows"][0]["value"]["value"] == 92
    assert "native_qa_unit_unknown" in meta["qualifications"]
    assert all(r["plddt"]["value"] is None for r in meta["atom_uncertainty"])


def test_out_of_range_declared_plddt_preserves_raw_native_b():
    _, parsed, seq, _ = f.fixture_pdb(b="101.00")
    seq, supplied = declared_metadata(parsed, seq, "declared_plddt")
    meta = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=supplied)
    assert meta["atom_uncertainty"][0]["b_factor_native"]["value"] == 101
    assert meta["atom_uncertainty"][0]["plddt"]["state"] == "invalid"


def test_invalid_declared_plddt_is_not_repaired_by_another_qa_source():
    extra = """
_ma_qa_metric.id q
_ma_qa_metric.name confidence
_ma_qa_metric.type pLDDT
_ma_qa_metric.mode local
_ma_qa_metric.software_group_id 1
_ma_qa_metric_local.ordinal_id 1
_ma_qa_metric_local.model_id 5
_ma_qa_metric_local.label_asym_id X
_ma_qa_metric_local.label_seq_id 7
_ma_qa_metric_local.label_comp_id SER
_ma_qa_metric_local.metric_id q
_ma_qa_metric_local.metric_value 80
"""
    data, _, _, _ = f.fixture_cif()
    data = data.replace(b"? 92.0 5", b"? 101.0 5")
    _, parsed, seq, _ = f.fixture_cif(data=data, extra=extra)
    seq, supplied = declared_metadata(parsed, seq, "declared_plddt")
    result = extract_native_structure_metadata(parsed, selected_sequence=seq, supplied_metadata=supplied)
    assert result["qa_rows"][0]["value"]["value"] == 80
    assert result["atom_uncertainty"][0]["b_factor_native"]["value"] == 101
    assert result["atom_uncertainty"][0]["plddt"]["state"] == "invalid"
    assert any(i["code"] == "metadata_join_conflict" for i in result["issues"])


def test_metadata_does_not_match_an_uninventoried_model_by_serial_alone():
    _, parsed, seq, _ = f.fixture_cif()
    selected = deepcopy(seq["selection"])
    selected["model_key"]["ordinal_0based"] += 1
    wrong = extract_structure_sequence(parsed, selection=selected)
    result = extract_native_structure_metadata(parsed, selected_sequence=wrong, supplied_metadata=[])
    assert result["state"] == "unavailable" and result["atom_uncertainty"] == []
    assert result["issues"][0]["code"] == "model_not_found"
