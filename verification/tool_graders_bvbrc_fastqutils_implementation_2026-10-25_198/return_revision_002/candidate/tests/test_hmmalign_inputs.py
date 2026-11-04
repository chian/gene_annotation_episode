from copy import deepcopy
from io import StringIO
from pathlib import Path

import pytest

from gene_annotation_episode.hmmalign_inputs import (
    build_hmmalign_sheet, iter_hmmalign_stockholm_events, iter_hmmalign_stockholm_records,
    iter_hmmalign_stockholm_rows, parse_hmmalign_stockholm, stockholm_digital_checksum,
)


FIXTURES = Path(__file__).resolve().parents[1]/"verification/tool_graders_hmmalign_2026-10-24/native"


def parse(text):
    return parse_hmmalign_stockholm(text, artifact_ref="native:stockholm", engine_version="3.4")


def native_inputs(mode="ordinary"):
    sequences = []
    for record in (FIXTURES/"sequences.fa").read_text().split(">")[1:]:
        name, *lines = record.splitlines()
        sequence = "".join(lines)
        sequences.append({"name": name, "occurrence": 0, "length": len(sequence), "sequence": sequence, "origin": "new"})
    inputs = {"profile": {"name": "test", "length": 20, "alphabet": "amino",
                          "map": list(range(1, 21)), "checksum": 1166427327},
              "sequences": sequences, "trim": mode == "trim", "acquisition": {"output_complete": True}}
    if mode == "mapali":
        inputs["mapali"] = {"artifact_ref": "native:seed", "stockholm": (FIXTURES/"seed.sto").read_text()}
    return inputs


def codes(value):
    return {issue["code"] for issue in value["issues"]}


def test_interleaved_stockholm_original_annotations_utf8_and_exact_locators():
    text = ("# STOCKHOLM 1.0\r\n#=GF ID α\r\n#=GF XX full original value\r\n"
            "#=GS seq AC accession.1\r\n# comment\r\nseq ACd\r\n#=GR seq PP *90\r\n#=GR seq SS HH.\r\n"
            "#=GC RF xx.\r\n#=GC PP_cons *9.\r\n\r\nseq E-\r\n#=GR seq PP 5.\r\n"
            "#=GR seq SS E.\r\n#=GC RF xx\r\n#=GC PP_cons 5.\r\n//\r\n")
    native = parse(text)
    record = native["alignments"][0]
    row = record["rows"][0]
    assert native["artifacts"]["stockholm"] == text
    assert record["column_count"] == 5 and record["block_count"] == 2
    assert row["aligned_sequence"] == "ACdE-"
    assert row["column_annotations"]["PP"]["text"] == "*905."
    assert row["column_annotations"]["SS"]["text"] == "HH.E."
    assert record["column_annotations"]["RF"]["text"] == "xx.xx"
    assert row["sequence_annotations"][0]["value"] == "accession.1"
    assert row["locator"]["line"] == 6
    start = text.encode().index(b"seq ACd")
    assert row["locator"]["byte_start"] == start
    assert text.encode()[start:row["locator"]["byte_end"]] == b"seq ACd\r\n"
    events = list(iter_hmmalign_stockholm_events(StringIO(text), artifact_ref="native:stockholm"))
    assert "".join(e["raw"] for e in events) == text
    assert events[-1]["locator"]["byte_end"] == len(text.encode())
    assert codes(record) == set() and codes(row) == set()


def test_streaming_does_not_read_next_record_before_yielding_and_rows_retain_occurrences():
    consumed = []
    def stream():
        for line in ["# STOCKHOLM 1.0\n", "q AC\n", "#=GC RF xx\n", "//\n", "# STOCKHOLM 1.0\n", "q DE\n", "#=GC RF xx\n", "//\n"]:
            consumed.append(line)
            yield line
    records = iter_hmmalign_stockholm_records(stream(), artifact_ref="x", engine_version="3.4")
    assert next(records)["rows"][0]["aligned_sequence"] == "AC"
    assert len(consumed) == 4
    assert next(records)["alignment_index"] == 1
    rows = list(iter_hmmalign_stockholm_rows("".join(consumed), artifact_ref="x", engine_version="3.4"))
    assert [r["record_key"] for r in rows] == ["alignment:0/sequence:0", "alignment:1/sequence:0"]
    assert rows[1]["locator"]["line"] == 6


def test_duplicate_names_interleaved_keep_original_occurrences_and_annotations():
    native = parse("# STOCKHOLM 1.0\nx AC\n#=GR x PP *9\nx DE\n#=GR x PP 01\n#=GC RF xx\n\nx FG\n#=GR x PP 88\nx HI\n#=GR x PP **\n#=GC RF xx\n//\n")
    rows = native["alignments"][0]["rows"]
    assert [(r["occurrence"], r["aligned_sequence"], r["column_annotations"]["PP"]["text"]) for r in rows] == [(0, "ACFG", "*988"), (1, "DEHI", "01**")]
    inputs = {"trim": False, "sequences": [
        {"name": "x", "occurrence": 1, "sequence": "DEHI", "origin": "new"},
        {"name": "x", "occurrence": 0, "sequence": "ACFG", "origin": "new"}]}
    sheet = build_hmmalign_sheet(native, inputs=inputs)
    assert [r["metadata_join"]["input_index"] for r in sheet["sequences"]] == [1, 0]
    assert [r["mapping"]["original_length"] for r in sheet["sequences"]] == [4, 4]


def test_duplicate_metadata_without_occurrence_is_not_arbitrarily_joined():
    native = parse("# STOCKHOLM 1.0\nx AC\nx DE\n#=GC RF xx\n//\n")
    sheet = build_hmmalign_sheet(native, inputs={"sequences": [{"name": "x", "length": 2}]})
    assert all(r["metadata_join"] is None for r in sheet["sequences"])
    assert "hmmalign_sequence_metadata_join_ambiguous" in codes(sheet)


def test_unequal_duplicate_block_multiplicities_preserve_ambiguous_partial_rows():
    native = parse("# STOCKHOLM 1.0\nx AC\nx DE\n#=GC RF xx\n\nx FG\n#=GC RF xx\n//\n")
    first, second = native["alignments"][0]["rows"]
    assert not first["identity_unambiguous"] and not second["identity_unambiguous"]
    assert first["aligned_sequence"] == "ACFG" and second["aligned_sequence"] == "DE"
    assert first["geometry_valid"] and not second["geometry_valid"]
    assert "hmmalign_interleaved_occurrence_ambiguous" in codes(first)


def test_duplicate_name_partial_pp_cannot_be_attached_to_arbitrary_occurrence():
    native = parse("# STOCKHOLM 1.0\nx AC\nx DE\n#=GR x PP **\n#=GC RF xx\n//\n")
    alignment = native["alignments"][0]
    assert "hmmalign_row_annotation_join_ambiguous" in codes(alignment)
    assert all("PP" not in r["column_annotations"] for r in alignment["rows"])
    assert any(e.get("tag") == "PP" for e in alignment["original_events"])


def test_valid_siblings_survive_malformed_rows_bad_geometry_and_truncation():
    text = "# STOCKHOLM 1.0\ngood ACDE\nbad AC\nsymbols A?DE\nmalformed\n#=GC RF xxxx\n"
    native = parse(text)
    sheet = build_hmmalign_sheet(native, inputs={"acquisition": {"output_complete": True}})
    assert native["status"] == "truncated"
    assert sheet["sequences"][0]["measurements"]["match_state_residues"] == 4
    assert sheet["sequences"][1]["measurements"]["match_state_residues"] is None
    assert sheet["sequences"][2]["measurements"]["retained_residues"] is None
    assert "hmmalign_malformed_sequence" in codes(sheet)
    assert "hmmalign_acquisition_native_completeness_conflict" in codes(sheet)
    assert sheet["native_result"]["artifacts"]["stockholm"] == text


@pytest.mark.parametrize("text,status", [("", "missing"), ("\n", "missing"),
    ("# STOCKHOLM 1.0\n//\n", "completed_empty"), ("# STOCKHOLM 1.0\n", "truncated"),
    ("# STOCKHOLM 2.0\nq AC\n//\n", "invalid")])
def test_missing_empty_truncated_and_wrong_format_are_distinct(text, status):
    assert parse(text)["status"] == status


@pytest.mark.parametrize("text", [None, b"# STOCKHOLM 1.0\n", {}, 4])
def test_invalid_native_top_level_type_has_specific_error(text):
    with pytest.raises(ValueError, match="hmmalign_text_required"):
        parse(text)


@pytest.mark.parametrize("inputs,code", [([], "hmmalign_inputs_object_required"),
    ({"profile": []}, "hmmalign_profile_object_required"),
    ({"trim": 0}, "hmmalign_trim_boolean_required"),
    ({"sequences": {}}, "hmmalign_sequences_array_required"),
    ({"anything": float("nan")}, "hmmalign_inputs_finite_json_required")])
def test_input_validation(inputs, code):
    with pytest.raises(ValueError, match=code):
        build_hmmalign_sheet(parse("# STOCKHOLM 1.0\nq AC\n#=GC RF xx\n//\n"), inputs=inputs)


def test_native_ordinary_trim_mapali_metadata_checksums_and_no_input_mutation():
    for mode in ("ordinary", "trim", "mapali"):
        inputs = native_inputs(mode)
        native = parse((FIXTURES/mode/"stdout.txt").read_text())
        original_native, original_inputs = deepcopy(native), deepcopy(inputs)
        sheet = build_hmmalign_sheet(native, inputs=inputs)
        assert native == original_native and inputs == original_inputs
        assert sheet["issues"] == []
        assert sheet["operation"]["mode"] == mode
        if mode == "mapali":
            assert sheet["mapali"]["computed_checksum"] == 1166427327
            assert sheet["mapali"]["status"] == "compatible"
            assert all(r["origin"] == "inherited" and r["inherited_join"]["status"] == "verified" for r in sheet["sequences"][:10])
            assert all(r["origin"] == "newly_aligned" for r in sheet["sequences"][10:])


@pytest.mark.parametrize("change,code", [
    ("checksum", "hmmalign_mapali_checksum_mismatch"),
    ("map", "hmmalign_mapali_profile_map_invalid_or_missing"),
    ("missing_seed", "hmmalign_mapali_actual_alignment_required"),
    ("bad_seed", "hmmalign_mapali_checksum_mismatch"),
    ("wrong_claim", "hmmalign_mapali_supplied_checksum_mismatch")])
def test_mapali_requires_actual_seed_map_and_checksum(change, code):
    inputs = native_inputs("mapali")
    if change == "checksum":
        inputs["profile"]["checksum"] += 1
    elif change == "map":
        inputs["profile"]["map"][-1] = 19
    elif change == "missing_seed":
        del inputs["mapali"]["stockholm"]
    elif change == "bad_seed":
        inputs["mapali"]["stockholm"] = inputs["mapali"]["stockholm"].replace("ACDEFGHIKLMNPQRSTVWY", "CCDEFGHIKLMNPQRSTVWY", 1)
    else:
        inputs["mapali"]["checksum"] = 3
    sheet = build_hmmalign_sheet(parse((FIXTURES/"mapali/stdout.txt").read_text()), inputs=inputs)
    assert code in codes(sheet)
    assert sheet["mapali"]["status"] != "compatible"
    assert all(r["origin"] != "newly_aligned" for r in sheet["sequences"][:10])


def test_mapali_verifies_mapped_symbols_and_does_not_trust_equal_row_names():
    text = (FIXTURES/"mapali/stdout.txt").read_text().replace("ACDEFGHIKLMN", "CCDEFGHIKLMN", 1)
    sheet = build_hmmalign_sheet(parse(text), inputs=native_inputs("mapali"))
    assert sheet["mapali"]["status"] == "compatible"
    assert sheet["sequences"][0]["inherited_join"]["status"] == "unverified"
    assert sheet["sequences"][0]["mapping"]["original_length"] is None
    assert "hmmalign_inherited_model_columns_unverified" in codes(sheet)


def test_mapali_does_not_verify_changed_inherited_insert_symbols():
    inputs = {"profile": {"length": 20, "alphabet": "amino", "map": [*range(3, 9), *range(11, 25)], "checksum": 1589892361},
              "mapali": {"artifact_ref": "seed", "stockholm": (FIXTURES/"fragment_seed.sto").read_text()}, "trim": False}
    text = (FIXTURES/"fragment_mapali/stdout.txt").read_text().replace("ACDEFGaaHIK", "ACDEFGccHIK", 1)
    populated = build_hmmalign_sheet(parse(text), inputs=inputs)
    assert populated["sequences"][0]["inherited_join"]["status"] == "unverified"
    assert populated["sequences"][1]["inherited_join"]["status"] == "verified"


def test_mapali_rejects_conflicting_new_input_metadata_on_an_inherited_row():
    inputs = native_inputs("mapali")
    inputs["sequences"].append({"name": "seq1", "occurrence": 0, "sequence": "ACDEFGHIKLMNPQRSTVWY", "origin": "new", "function_assignments": ["wrong join"]})
    populated = build_hmmalign_sheet(parse((FIXTURES/"mapali/stdout.txt").read_text()), inputs=inputs)
    row = populated["sequences"][0]
    assert row["origin"] == "inherited"
    assert row["metadata_join"]["mapali_row_index"] == 0
    assert "function_assignments" not in row["metadata_join"]["supplied"]
    assert "hmmalign_sequence_origin_conflict" in codes(row)


def test_easel_checksum_digital_alphabet_normalization_and_geometry():
    seed = parse((FIXTURES/"seed.sto").read_text())["alignments"][0]
    assert stockholm_digital_checksum([r["aligned_sequence"] for r in seed["rows"]], alphabet="amino") == 1166427327
    assert stockholm_digital_checksum(["ac.tuX"], alphabet="dna") == stockholm_digital_checksum(["AC-TTN"], alphabet="dna")
    assert stockholm_digital_checksum(["ac.tuX"], alphabet="rna") == stockholm_digital_checksum(["AC-UUN"], alphabet="rna")
    with pytest.raises(ValueError, match="hmmalign_checksum_row_geometry_invalid"):
        stockholm_digital_checksum(["AC", "A"], alphabet="amino")


def test_stream_rejects_multiple_physical_lines_in_one_supplied_line():
    with pytest.raises(ValueError, match="hmmalign_stream_complete_text_lines_required"):
        list(iter_hmmalign_stockholm_events(["q AC\n\n"], artifact_ref="x"))


def test_invalid_origin_and_alphabet_component_preserve_sibling_rows():
    populated = build_hmmalign_sheet(parse("# STOCKHOLM 1.0\nvalid AC\nbad AE\n#=GC RF xx\n//\n"),
        inputs={"profile": {"alphabet": "DNA"}, "sequences": [{"name": "valid", "origin": []}]})
    assert populated["sequences"][0]["measurements"]["match_state_residues"] == 2
    assert populated["sequences"][1]["measurements"]["retained_residues"] is None
    assert "hmmalign_sequence_origin_invalid" in codes(populated)
    assert "hmmalign_sequence_profile_alphabet_mismatch" in codes(populated)


def test_invalid_supplied_parsed_row_or_alignment_preserves_valid_siblings():
    native = parse("# STOCKHOLM 1.0\na AC\nb DE\n#=GC RF xx\n//\n")
    del native["alignments"][0]["rows"][0]["name"]
    native["alignments"].append({"rows": []})
    populated = build_hmmalign_sheet(native, inputs={})
    assert len(populated["sequences"]) == 1 and populated["sequences"][0]["name"] == "b"
    assert populated["sequences"][0]["record_key"] == "alignment:0/sequence:1"
    assert {"hmmalign_native_sequence_row_invalid", "hmmalign_native_alignment_invalid"} <= codes(populated)


def test_trim_repeated_subsequence_keeps_all_offsets_and_count_not_unique_offset():
    native = parse("# STOCKHOLM 1.0\nq AC\n#=GC RF xx\n//\n")
    sheet = build_hmmalign_sheet(native, inputs={"trim": True,
        "sequences": [{"name": "q", "occurrence": 0, "sequence": "ACAC", "length": 4}]})
    row = sheet["sequences"][0]
    assert row["mapping"]["status"] == "ambiguous"
    assert row["mapping"]["candidate_intervals"] == [[0, 2], [2, 4]]
    assert row["mapping"]["original_interval"] is None
    assert row["mapping"]["trimmed_residues"] == 2
    assert all(c["original_sequence_position"] is None for c in row["correspondence"])


def test_wrong_sequence_or_length_does_not_keep_denominators():
    native = parse("# STOCKHOLM 1.0\nq AC\n#=GC RF xx\n//\n")
    for metadata in ({"sequence": "DE", "length": 2}, {"sequence": "AC", "length": 4}, {"length": 1}, {"length": True}):
        sheet = build_hmmalign_sheet(native, inputs={"trim": False, "sequences": [{"name": "q", **metadata}]})
        assert sheet["sequences"][0]["mapping"]["original_length"] is None
        assert sheet["sequences"][0]["metadata_join"]["status"] == "incompatible"
        assert sheet["sequences"][0]["measurements"]["match_state_residues"] == 2


def test_profile_length_conflict_and_missing_rf_do_not_invent_model_correspondence():
    native = parse("# STOCKHOLM 1.0\nq AC\n#=GC RF xx\n//\n")
    sheet = build_hmmalign_sheet(native, inputs={"profile": {"length": 20}})
    assert sheet["sequences"][0]["model_length"] is None
    assert sheet["sequences"][0]["rf_model_positions"] == 2
    sheet = build_hmmalign_sheet(parse("# STOCKHOLM 1.0\nq AC\n//\n"), inputs={"profile": {"length": 2}})
    assert sheet["sequences"][0]["measurements"]["match_state_residues"] is None
    assert sheet["sequences"][0]["measurements"]["retained_residues"] == 2
    assert sheet["sequences"][0]["correspondence"] == []


def test_repeated_alignment_names_require_alignment_occurrence_to_join():
    text = "# STOCKHOLM 1.0\nq AC\n#=GC RF xx\n//\n"*2
    sheet = build_hmmalign_sheet(parse(text), inputs={"sequences": [{"name": "q", "occurrence": 0, "length": 2}]})
    assert all(r["metadata_join"] is None for r in sheet["sequences"])
    sheet = build_hmmalign_sheet(parse(text), inputs={"sequences": [{"name": "q", "occurrence": 0, "alignment_index": 1, "length": 2}]})
    assert sheet["sequences"][0]["metadata_join"] is None
    assert sheet["sequences"][1]["mapping"]["original_length"] == 2
