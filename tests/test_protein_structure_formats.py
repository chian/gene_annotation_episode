"""Hand-auditable native lexical/identity behavior, without SMCRA or float32."""
from importlib import import_module
from pathlib import Path
import pytest
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure, parse_mmcif_structure, category_rows, native_number
f = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")


def test_fixed_columns_insertions_order_blank_fields_and_raw_lines():
    data = f.pdb_bytes(b="", occupancy="")
    parsed = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
    assert "".join(r["text"] for r in parsed["pdb_records"]).encode() == data
    atoms = parsed["atoms"]
    assert [a["identity"]["residue"]["position_key"]["insertion_code"] for a in atoms] == [" ", "A", " ", " "]
    assert atoms[0]["b_iso"]["state"] == "missing" and atoms[0]["b_iso"]["value"] is None
    assert atoms[0]["identity"]["atom_name"]["text"] == " CA "
    assert parsed["models"][0]["model_key"]["serial_state"] == "implicit"
    assert parsed["models"][0]["model_key"]["native_serial_token"]["text"] is None


def test_pdb_models_ter_and_duplicate_atoms_preserve_all_rows():
    a = f.atom_line()
    data = ("MODEL        7\n" + a + "TER                  A\n" + a + "ENDMDL\nMODEL        2\n" + a + a + "ENDMDL\n").encode()
    p = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
    assert [m["model_key"]["native_serial_token"]["text"].strip() for m in p["models"]] == ["7", "2"]
    assert [r["chain_key"]["ter_segment_ordinal_0based"] for r in p["chains"]] == [0, 1, 0]
    assert len(p["atoms"]) == 4 and p["atoms"][-1]["state"] == "invalid"


def test_cif_preserves_every_token_quote_missing_distinction_and_precision():
    data, p, _, _ = f.fixture_cif()
    assert len(p["atoms"]) == 2
    assert p["atoms"][0]["xyz_A"][0]["value"] == 0.123456789012345
    note = category_rows(p, 0, "_note")[0][1]
    assert note["literal_question"]["lexical_state"] == "value"
    assert note["unknown"]["lexical_state"] == "cif_unknown"
    assert note["literal_dot"]["lexical_state"] == "value"
    assert note["not_applicable"]["lexical_state"] == "cif_not_applicable"
    assert "second 'line' # literal text" in note["multiline"]["text"]
    for block in p["cif_blocks"]:
        for table in block["tables"]:
            for token in table["tags"] + [t for row in table["rows"] for t in row]:
                span = token["span"]
                assert data[span["start_0based"]:span["end_exclusive"]].decode() == token["lexeme"]
    assert native_number(note["literal_dot"])["state"] == "invalid"
    assert native_number(note["not_applicable"])["state"] == "missing"


@pytest.mark.parametrize("spelling,value,uncertainty", [("1.234(5)e2", 123.4, 0.5), ("1.234e2(5)", 123.4, 0.5), ("0", 0.0, None)])
def test_cif_numeric_uncertainty_rule(spelling, value, uncertainty):
    data = ("data_x\n_x.value " + spelling + "\n").encode()
    p = parse_mmcif_structure(data, file_identity=f.identity(data, "pdbx_mmcif_text"), data_block=None)
    token = category_rows(p, 0, "_x")[0][1]["value"]
    number = native_number(token)
    assert number["value"] == value and number["embedded_standard_uncertainty"] == uncertainty


def test_malformed_loop_and_duplicate_tags_do_not_repair_or_drop_valid_blocks():
    data = b"data_bad\nloop_\n_x.a\n_x.b\n1 2 3\ndata_good\n_x.a 4\n"
    p = parse_mmcif_structure(data, file_identity=f.identity(data, "pdbx_mmcif_text"), data_block=None)
    assert p["cif_blocks"][0]["state"] == "invalid"
    assert p["cif_blocks"][0]["tables"][0]["rows"][0][0]["text"] == "1"
    span = p["cif_blocks"][0]["unparsed_spans"][0]
    assert data[span["start_0based"]:span["end_exclusive"]] == b"3"
    assert p["cif_blocks"][1]["state"] == "complete"
    data = b"data_x\n_x.a 1\n_x.a 2\n"
    p = parse_mmcif_structure(data, file_identity=f.identity(data, "pdbx_mmcif_text"), data_block=None)
    assert len(p["cif_blocks"][0]["tables"]) == 2 and p["cif_blocks"][0]["state"] == "invalid"


def test_nonfinite_coordinate_token_and_wrong_byte_identity_are_not_zero():
    data = f.atom_line(xyz=("nan", 0.0, 0.0)).encode()
    p = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
    assert p["atoms"][0]["xyz_A"][0]["state"] == "invalid"
    assert p["atoms"][0]["xyz_A"][0]["token"]["text"].strip() == "nan"
    assert p["atoms"][0]["xyz_A"][0]["value"] is None
    with pytest.raises(ValueError, match="input_digest_mismatch"):
        parse_pdb_structure(data + b"x", file_identity=f.identity(data, "pdb_3x_text"))


def test_compressed_and_wrong_format_content_are_explicit_invalid():
    for data in (b"\x1f\x8bcompressed", b"data_x\n_tag.name 5\n"):
        p = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
        assert p["state"] == "invalid" and p["atoms"] == []


def test_lexical_failure_does_not_taint_other_blocks_comments_or_utf8_spans():
    data = "data_good\n# comment\n_x.a 'β'\ndata_bad\n_x.a 'unterminated\n".encode()
    p = parse_mmcif_structure(data, file_identity=f.identity(data, "pdbx_mmcif_text"), data_block=None)
    assert [b["state"] for b in p["cif_blocks"]] == ["complete", "invalid"]
    token = p["cif_blocks"][0]["tables"][0]["rows"][0][0]
    assert data[token["span"]["start_0based"]:token["span"]["end_exclusive"]] == "'β'".encode()


def test_unselected_blocks_all_raw_tables_survive_a_selected_parse():
    data = b"data_one\n_x.a 1\ndata_two\n_x.a 2\n"
    p = parse_mmcif_structure(data, file_identity=f.identity(data, "pdbx_mmcif_text"), data_block={"ordinal_0based": 1, "name": "two"})
    assert len(p["cif_blocks"]) == 2
    assert category_rows(p, 0, "_x")[0][1]["a"]["text"] == "1"


@pytest.mark.parametrize("spelling", ["1e999999999", "1e-999999999", "1e-400", "1e400", "1.0(1)e-400"])
def test_unrepresentable_native_numbers_remain_invalid_tokens_not_zero(spelling):
    data = ("data_x\n_x.value " + spelling + "\n").encode()
    p = parse_mmcif_structure(data, file_identity=f.identity(data, "pdbx_mmcif_text"), data_block=None)
    token = category_rows(p, 0, "_x")[0][1]["value"]
    result = native_number(token)
    assert result["state"] == "invalid" and result["value"] is None
    assert result["token"]["lexeme"] == spelling


def test_explicitly_declared_pqr_is_rejected_before_numeric_interpretation():
    data = b"ATOM      1  N   MET     1      12.399  16.604  14.457 -0.3000 1.8500\n"
    with pytest.raises(ValueError, match="invalid_schema|unsupported_format"):
        parse_pdb_structure(data, file_identity=f.identity(data, "pqr_text"))


def test_pdb_coordinate_fields_do_not_accept_cif_embedded_standard_uncertainty():
    data = f.atom_line(xyz=("1.2(3)", 0.0, 0.0)).encode()
    parsed = parse_pdb_structure(data, file_identity=f.identity(data, "pdb_3x_text"))
    number = parsed["atoms"][0]["xyz_A"][0]
    assert number["state"] == "invalid" and number["value"] is None
    assert number["embedded_standard_uncertainty"] is None
    assert number["token"]["lexeme"].strip() == "1.2(3)"
