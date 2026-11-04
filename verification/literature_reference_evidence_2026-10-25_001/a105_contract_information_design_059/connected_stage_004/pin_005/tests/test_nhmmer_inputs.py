"""Pure-reader checks; retained native execution is labelled separately."""
from copy import deepcopy
import io
import json
from pathlib import Path

import pytest

from gene_annotation_episode.nhmmer_inputs import (
    build_nhmmer_sheet, iter_nhmmer_stdout_queries, iter_nhmmer_stdout_records,
    iter_nhmmer_tblout_rows, parse_nhmmer_artifacts,
)

FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_nhmmer_2026-10-24"


def native_fixture(name):
    directory = FIXTURES / name
    return parse_nhmmer_artifacts(program="nhmmscan" if name == "nhmmscan" else "nhmmer",
        artifacts={"stdout": (directory / "stdout.txt").read_text(), "tblout": (directory / "hits.tbl").read_text()},
        artifact_refs={"stdout": name + "/stdout", "tblout": name + "/tblout"}, engine_version="3.4")


def table_native(text, program="nhmmer"):
    return parse_nhmmer_artifacts(program=program, artifacts={"tblout": text},
        artifact_refs={"tblout": "supplied-table"}, engine_version="3.4")


def synthetic_stdout(*, name="q", length=10, target="t", program="nhmmer", strand="+", pp="09**", terminated=True):
    left, right = (1, 4) if strand == "+" else (4, 1)
    model_label, sequence_label = (name, target) if program == "nhmmer" else (target, name)
    return (f"# {program} :: synthetic\nQuery: {name} [{'M' if program == 'nhmmer' else 'L'}={length}]\n"
        f">> {target}\n ! 3.0 0.0 0 1 4 .. {left} {right} .. {left} {right} .. 10 0.77\n"
        f"  Alignment:\n  score: 3 bits\n  {model_label} 1 acgt 4\n"
        f"    acgt\n  {sequence_label} {left} ACGT {right}\n    {pp} PP\n"
        + ("//\n[ok]\n" if terminated else ""))


def test_tblout_rows_preserve_reverse_coordinates_original_occurrences_and_bytes():
    text = "# unicode λ\n" + "t - q - 2 5 9 6 10 5 20 - 0 -3.2 1.4 unicode α\n" * 2
    rows = list(iter_nhmmer_tblout_rows(io.BytesIO(text.encode()), program="nhmmer", artifact_ref="a"))
    assert rows[0]["native"]["score_bits"] == -3.2
    assert rows[0]["native"]["evalue"] == 0
    assert rows[0]["native"]["length_field_meaning"] == "sequence_length"
    assert rows[0]["coordinates"]["sequence_interval"] == [5, 9]
    assert rows[0]["coordinates"]["sequence_envelope_interval"] == [4, 10]
    assert rows[0]["locator"]["byte_start"] == len("# unicode λ\n".encode())
    assert rows[0]["locator"]["row_occurrence"] == 1
    assert rows[1]["locator"]["row_occurrence"] == 2
    assert rows[0]["record_key"] != rows[1]["record_key"]
    assert rows[0]["native"]["included"] is None


def test_invalid_rows_and_native_fields_do_not_remove_valid_siblings():
    rows = list(iter_nhmmer_tblout_rows(io.StringIO(
        "t - q - 1 2 1 2 1 2 10 + nan -1 0 x\n"
        "t - q - 1 2\n"
        "t - q - 1 2 1 2 1 2 10 + 0 0 0 x\n"), program="nhmmer", artifact_ref="a"))
    assert len(rows) == 3
    assert [row["status"] for row in rows] == ["partial", "invalid", "valid"]
    assert rows[0]["native"]["evalue"] is None
    assert rows[0]["native"]["score_bits"] == -1
    assert rows[2]["native"]["evalue"] == 0
    assert rows[1]["raw_fields"]["hmm_from"] == "1"
    assert any(issue["code"] == "nhmmer_truncated_tblout_row" for issue in rows[1]["issues"])


@pytest.mark.parametrize("name", ["nhmmer_sequence", "nhmmer_profile", "nhmmer_msa", "nhmmer_z_watson", "nhmmer_z_both", "nhmmscan"])
def test_real_native_artifacts_have_matching_loci_and_no_invented_lengths(name):
    native = native_fixture(name)
    inputs = json.loads((FIXTURES / name / "inputs.json").read_text())
    sheet = build_nhmmer_sheet(native, inputs=inputs)
    assert sheet["schema"] == "nhmmer_sheet_v1"
    assert len(sheet["loci"]) == len(native["table_rows"])
    assert all(row["joins"]["stdout"] for row in sheet["loci"])
    assert all(row["status"] == "valid" for row in sheet["loci"])
    assert all(row["model_length"] == 100 for row in sheet["loci"])
    assert {row["sequence_length"] for row in sheet["loci"]} <= {120, 121}
    assert all(row["native"]["length_field_meaning"] == ("model_length" if name == "nhmmscan" else "sequence_length") for row in sheet["loci"])
    assert sheet["completeness"]["status"] == "complete"
    assert sheet["operation"]["query_construction_mode"] == inputs["native_parameters"].get("query_construction_mode")


def test_scan_model_length_never_becomes_sequence_length_without_query_metadata():
    native = table_native("model - query - 1 80 121 200 120 201 80 + 0 3 0 x\n# [ok]\n", "nhmmscan")
    sheet = build_nhmmer_sheet(native, inputs={})
    row = sheet["loci"][0]
    assert row["model_length"] == 80
    assert row["sequence_length"] is None
    assert row["coordinates"]["sequence_interval"] == [120, 200]


def test_sequence_query_length_is_not_constructed_model_length():
    native = table_native("t - q - 1 5 1 5 1 5 20 + 1 3 0 x\n")
    row = build_nhmmer_sheet(native, inputs={"query": {"name": "q", "kind": "nucleotide_sequence", "length": 10}})["loci"][0]
    assert row["model_length"] is None
    assert row["sequence_length"] == 20


def test_exact_metadata_mismatch_and_duplicate_metadata_remain_unjoined():
    native = table_native("t A q Q 1 5 1 5 1 5 20 + 1 3 0 x\n")
    supplied = {"query": {"name": "q", "accession": "wrong", "kind": "profile", "length": 10},
        "targets": [{"name": "t", "accession": "A", "length": 20}] * 2}
    row = build_nhmmer_sheet(native, inputs=supplied)["loci"][0]
    assert row["model_length"] is None
    assert row["model_metadata"] is None
    assert row["sequence_metadata"] is None
    assert row["union_identity"] is None
    assert any(issue["code"] == "nhmmer_ambiguous_target_metadata" for issue in row["issues"])


def test_conflicting_lengths_do_not_destroy_independent_axis():
    native = table_native("t - q - 1 5 1 5 1 5 20 + 1 3 0 x\n")
    row = build_nhmmer_sheet(native, inputs={"query": {"name": "q", "kind": "profile", "length": 10},
        "targets": [{"name": "t", "kind": "nucleotide_sequence", "length": 19}]} )["loci"][0]
    assert row["model_length"] == 10 and row["sequence_length"] is None
    assert len(row["length_sources"]["sequence_length"]) == 2


def test_repeated_identical_queries_make_table_stdout_join_ambiguous():
    stdout = synthetic_stdout() + synthetic_stdout()
    native = parse_nhmmer_artifacts(program="nhmmer", artifacts={"stdout": stdout,
        "tblout": "t - q - 1 4 1 4 1 4 10 + 0 3 0 x\n" * 2},
        artifact_refs={"stdout": "s", "tblout": "t"}, engine_version="3.4")
    sheet = build_nhmmer_sheet(native, inputs={})
    assert [q["occurrence"] for q in sheet["queries"]] == [1, 2]
    assert len(sheet["loci"]) == 4  # Original representations remain distinct.
    assert sheet["loci"][0]["joins"]["stdout"] is None
    assert sheet["loci"][0]["query_occurrence"] is None
    assert any(i["code"] == "nhmmer_ambiguous_stdout_join" for i in sheet["loci"][0]["issues"])
    assert sheet["loci"][2]["query_occurrence"] == 1
    assert sheet["loci"][3]["query_occurrence"] == 2


def test_invalid_geometry_retains_native_coordinates_and_valid_model_axis():
    row = list(iter_nhmmer_tblout_rows("t - q - 1 5 8 4 7 5 10 + 1 3 0\n",
        program="nhmmer", artifact_ref="t"))[0]
    assert row["native"]["ali_from"] == 8
    assert row["coordinates"]["sequence_interval"] is None
    assert row["coordinates"]["model_interval"] == [0, 5]


def test_stdout_iterator_keeps_queries_occurrences_and_truncation():
    text = synthetic_stdout() + synthetic_stdout(name="second", terminated=False)
    records = list(iter_nhmmer_stdout_records(io.StringIO(text), program="nhmmer", artifact_ref="s"))
    queries = list(iter_nhmmer_stdout_queries(io.BytesIO(text.encode()), program="nhmmer", artifact_ref="s"))
    assert [q["terminated"] for q in queries] == [True, False]
    assert [q["name"] for q in queries] == ["q", "second"]
    assert len([r for r in records if r["kind"] == "locus"]) == 2
    assert queries[1]["locator"]["byte_end"] == len(text.encode())
    assert not any("loci" in q for q in queries)


def test_locus_stream_does_not_consume_following_query_before_yield():
    class Guarded:
        def __iter__(self):
            yield from synthetic_stdout().splitlines(keepends=True)
            raise AssertionError("iterator read beyond selected query")
    stream = iter_nhmmer_stdout_queries(Guarded(), program="nhmmer", artifact_ref="s")
    assert next(stream)["name"] == "q"


def test_empty_completed_partial_and_missing_are_different():
    complete = build_nhmmer_sheet(table_native("# [ok]\n"), inputs={})
    partial = build_nhmmer_sheet(table_native("# header\n"), inputs={})
    missing = build_nhmmer_sheet(parse_nhmmer_artifacts(program="nhmmer", artifacts={}, artifact_refs={}, engine_version="3.4"), inputs={})
    assert [s["completeness"]["status"] for s in (complete, partial, missing)] == ["complete", "partial", "missing"]
    assert not complete["loci"] and not partial["loci"] and not missing["loci"]


def test_native_completion_is_not_population_or_page_completion():
    sheet = build_nhmmer_sheet(table_native("# [ok]\n"), inputs={"acquisition": {
        "output_complete": True, "hit_population_complete": False, "page_start": 1, "page_count": 3}})
    assert sheet["completeness"]["status"] == "complete"
    assert sheet["completeness"]["hit_population_complete"] is False
    contradicted = build_nhmmer_sheet(table_native("# [ok]\n"), inputs={"acquisition": {"output_complete": False}})
    assert any(i["code"] == "nhmmer_completeness_contradiction" for i in contradicted["issues"])


def test_wrong_format_is_retained_but_not_parsed_as_tblout():
    native = parse_nhmmer_artifacts(program="nhmmer", artifacts={"dfamtblout": "native Dfam text", "aliscoresout": "positions"},
        artifact_refs={"dfamtblout": "d", "aliscoresout": "p"}, engine_version="3.4")
    assert native["artifacts"]["dfamtblout"]["text"] == "native Dfam text"
    assert not native["table_rows"]
    assert [issue["code"] for issue in native["issues"]] == ["nhmmer_unsupported_artifact_format"] * 2


def test_declared_other_program_or_scan_length_header_is_incompatible():
    native = table_native("t - q - 1 5 1 5 1 5 20 + 1 3 0 x\n# Program: nhmmscan\n# [ok]\n")
    assert native["table_rows"][0]["status"] == "invalid"
    rows = list(iter_nhmmer_tblout_rows("# target name accession query name accession hmmfrom hmm to modlen strand\n"
        "t - q - 1 5 1 5 1 5 20 + 1 3 0 x\n", program="nhmmer", artifact_ref="t"))
    assert rows[0]["status"] == "invalid"


def test_metadata_sequence_mismatch_does_not_establish_union_identity():
    native = native_fixture("nhmmer_sequence")
    inputs = json.loads((FIXTURES / "nhmmer_sequence/inputs.json").read_text())
    inputs["targets"][0]["sequence"] = "A" * 120
    row = build_nhmmer_sheet(native, inputs=inputs)["loci"][0]
    assert row["sequence_metadata_alignment_validated"] is False
    assert row["union_identity"] is None


def test_native_z_declaration_and_actual_searched_population_are_distinct():
    both, watson = native_fixture("nhmmer_z_both"), native_fixture("nhmmer_z_watson")
    assert next(v for v in both["native_settings"] if v["name"] == "Z")["value"] == 0.1
    assert next(v for v in both["native_settings"] if v["name"] == "Z")["unit"] == "million_nucleotides"
    assert next(v for v in watson["native_settings"] if v["name"] == "strands")["value"] == "watson"
    assert next(v for v in both["queries"][0]["statistics"] if v["name"] == "Target sequences")["positions"] == 722
    assert next(v for v in watson["queries"][0]["statistics"] if v["name"] == "Target sequences")["positions"] == 361


def test_top_level_types_and_nonfinite_values_have_specific_errors():
    with pytest.raises(ValueError, match="nhmmer_invalid_artifacts_type"):
        parse_nhmmer_artifacts(program="nhmmer", artifacts=[], artifact_refs={}, engine_version="3.4")
    with pytest.raises(ValueError, match="nhmmer_nonfinite_json"):
        build_nhmmer_sheet(table_native("# [ok]\n"), inputs={"extra": float("nan")})
    with pytest.raises(ValueError, match="nhmmer_unsupported_program"):
        table_native("", "phmmer")
    with pytest.raises(ValueError, match="nhmmer_artifact_text_required"):
        parse_nhmmer_artifacts(program="nhmmer", artifacts={"tblout": 0}, artifact_refs={}, engine_version="3.4")


def test_inputs_and_native_are_not_mutated():
    native, inputs = native_fixture("nhmmer_profile"), {"query": {"name": "model", "kind": "profile", "length": 100}, "custom": {"keep": [1, 2]}}
    before = deepcopy((native, inputs))
    sheet = build_nhmmer_sheet(native, inputs=inputs)
    assert (native, inputs) == before
    sheet["inputs"]["custom"]["keep"].append(3)
    assert inputs["custom"]["keep"] == [1, 2]


def test_completion_marker_before_truncated_query_is_not_completion():
    text = synthetic_stdout() + synthetic_stdout(name="truncated", terminated=False)
    native = parse_nhmmer_artifacts(program="nhmmer", artifacts={"stdout": text}, artifact_refs={"stdout": "s"}, engine_version="3.4")
    assert native["artifacts"]["stdout"]["completion_marker_observed"] is True
    assert native["artifacts"]["stdout"]["native_complete"] is False
    assert len(native["stdout_loci"]) == 2


def test_invalid_alignment_chunk_preserves_prior_locus_and_native_spans():
    text = synthetic_stdout() + synthetic_stdout(name="broken").replace("t 1 ACGT 4", "t 2 ACGT 5")
    native = parse_nhmmer_artifacts(program="nhmmer", artifacts={"stdout": text}, artifact_refs={"stdout": "s"}, engine_version="3.4")
    first, second = native["stdout_loci"]
    assert first["alignment"]["valid"] is True
    assert second["alignment"]["valid"] is False
    assert second["coordinates"]["sequence_interval"] == [0, 4]
    assert any(issue["code"] == "nhmmer_alignment_chunk_coordinates" for issue in second["issues"])


def test_engine_version_conflict_is_explicit():
    native = table_native("# Version: 3.3.2\n# [ok]\n")
    assert native["observed_engine_versions"] == [{"artifact_role": "tblout", "version": "3.3.2"}]
    assert any(issue["code"] == "nhmmer_engine_version_mismatch" for issue in native["issues"])


def test_wrong_saved_native_row_does_not_destroy_siblings():
    native = table_native("t - q - 1 4 1 4 1 4 10 + 1 3 0\n")
    native["table_rows"].insert(0, {"bad": "row"})
    sheet = build_nhmmer_sheet(native, inputs={})
    assert len(sheet["loci"]) == 1
    assert sheet["native"]["table_rows"][0] == {"bad": "row"}
    assert any(issue["code"] == "nhmmer_invalid_native_row" for issue in sheet["issues"])


def test_absent_query_kind_does_not_identify_sequence_length_as_model_length():
    native = table_native("t - q - 1 4 1 4 1 4 10 + 1 3 0\n")
    row = build_nhmmer_sheet(native, inputs={"query": {"name": "q", "length": 100}})["loci"][0]
    assert row["model_length"] is None


def test_invalid_utf8_rows_have_exact_bytes_and_keep_following_valid_rows():
    text = b"bad\xff\n" + b"t - q - 1 4 1 4 1 4 10 + 1 3 0\n"
    first, second = iter_nhmmer_tblout_rows(io.BytesIO(text), program="nhmmer", artifact_ref="t")
    assert first["raw_bytes_hex"] == b"bad\xff\n".hex()
    assert second["locator"]["byte_start"] == 5
    assert second["status"] == "valid"
