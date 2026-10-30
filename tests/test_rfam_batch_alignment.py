"""Native display correspondence and explicitly synthetic counterexamples."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.rfam_batch_alignment import parse_rfam_alignment_display
from gene_annotation_episode.rfam_batch_contracts import (
    RFAM_ALIGNMENT_COUNT_FIELDS, RFAM_ALIGNMENT_RESULT_FIELDS,
    validate_rfam_alignment_result,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "verification/tool_graders_rfam_alignment_2026-10-26_236"
DOCS = ROOT / "verification/tool_graders_rfam_contract_2026-10-26_232/examples/official-single-result.json"
LIVE = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/single/003-fetch-json/response.body"
IDENTITY = {"artifact_ref": "fixture:synthetic-display", "hit_key": "fixture:synthetic-display/hits/test/0",
            "query_occurrence_key": "fixture:original-occurrence-0", "family_accession": "RF00001"}


def native_json(path):
    doc = json.loads(path.read_bytes())
    row = doc["hits"]["5S_rRNA"][0]
    ref = "fixture:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return parse_rfam_alignment_display(row["alignment"],
        hit_identity=dict(IDENTITY, artifact_ref=ref, hit_key=ref + "/hits/5S_rRNA/0"),
        query_sequence=doc["searchSequence"], native_start=row["start"], native_end=row["end"], native_strand=row["strand"])


def report_fixture(name):
    data = json.loads((EVIDENCE / "fixtures" / (name + ".json")).read_text())
    assert hashlib.sha256((ROOT / data["source"]["path"]).read_bytes()).hexdigest() == data["source"]["sha256"]
    return data


def parse_fixture(data):
    return parse_rfam_alignment_display(data["alignment"], **{key: data[key] for key in
        ("hit_identity", "query_sequence", "native_start", "native_end", "native_strand")})


def synthetic(model, query, *, mstart=1, mend=None, qstart=1, qend=None, pp=None):
    """Clearly synthetic six-string display; never a claimed native response."""
    assert len(model) == len(query)
    if mend is None:
        mend = mstart + len(model.replace(".", "")) - 1
    if qend is None:
        qend = qstart + len(query.replace("-", "")) - 1
    if pp is None:
        pp = "".join("." if c == "-" else "*" for c in query)
    return {"nc": "#NC " + " " * len(model), "ss": "#SS " + ":" * len(model),
            "hit_seq": f"#CM {mstart} {model} {mend}", "match": "#MATCH " + "+" * len(model),
            "user_seq": f"#SEQ {qstart} {query} {qend}", "pp": "#PP " + pp}


def parse(alignment, sequence, *, start=1, end=None, strand="+"):
    return parse_rfam_alignment_display(alignment, hit_identity=IDENTITY,
        query_sequence=sequence, native_start=start, native_end=len(sequence) if end is None else end,
        native_strand=strand)


def codes(result):
    return {issue["code"] for issue in result["issues"]}


def test_documentation_example_has_exact_119_comparisons_79_equal():
    result = native_json(DOCS)
    assert result["status"] == "complete"
    assert result["model_consensus_compared_count"] == 119
    assert result["model_consensus_equal_count"] == 79
    assert result["aligned_model_intervals"] == [[0, 119]]
    assert result["aligned_query_intervals"] == [[0, 119]]
    assert len(result["posterior_segments"]) == 119
    assert all(p["lower_bound"] == .95 and p["upper_bound"] == 1 for p in result["posterior_segments"])
    assert result["query_insert_count"] == result["model_delete_count"] == 0
    assert "model_length_positions" not in result


def test_actual_current_json_retains_gap_and_insertion_geometry():
    result = native_json(LIVE)
    assert result["status"] == "complete"
    assert result["display_model_to"] == 120
    assert result["display_query_to"] == 119
    assert result["model_consensus_compared_count"] == 118
    assert result["model_consensus_equal_count"] == 75
    assert result["query_insert_count"] == 1
    assert result["model_delete_count"] == 2
    assert result["aligned_model_intervals"] == [[0, 120]]
    assert result["aligned_query_intervals"] == [[0, 119]]
    assert len(result["paired_positions"]) == 118
    assert len(result["posterior_segments"]) == 119
    assert set(result) == RFAM_ALIGNMENT_RESULT_FIELDS
    deletions = [s for s in result["segments"] if s["kind"] == "model_deletion"]
    assert [s["model_interval"] for s in deletions] == [[40, 41], [109, 110]]
    insertion = [s for s in result["segments"] if s["kind"] == "query_insertion"]
    assert insertion[0]["query_interval"] == [101, 102]
    assert insertion[0]["query_text"] == "u"


@pytest.mark.parametrize("name,query_length,paired,inserted,deleted", [
    ("original", 119, 118, 1, 2), ("repeat", 119, 118, 1, 2),
    ("reverse_complement", 119, 118, 1, 2), ("insertion", 120, 118, 2, 2),
    ("deletion", 118, 117, 1, 3),
])
def test_actual_report_displays_are_labelled_extractions(name, query_length, paired, inserted, deleted):
    fixture = report_fixture("native-rfam_example_" + name)
    assert fixture["fixture_kind"] == "derived_native_report_display"
    result = parse_fixture(fixture)
    assert result["status"] == "complete"
    assert result["aligned_model_intervals"] == [[0, 120]]
    assert result["aligned_query_intervals"] == [[0, query_length]]
    assert result["model_consensus_compared_count"] == paired
    assert result["query_insert_count"] == inserted
    assert result["model_delete_count"] == deleted
    if name == "reverse_complement":
        assert result["query_strand"] == "-"
        assert result["paired_positions"][0]["query_position"] == 118
        assert result["paired_positions"][-1]["query_position"] == 0
        assert result["paired_positions"][0]["query_symbol"] == "A"
        assert fixture["query_sequence"][118] == "T"


def test_actual_report_truncation_does_not_create_a_model_length_or_alignment():
    result = parse_fixture(report_fixture("native-rfam_example_prefix70"))
    assert result["status"] == "partial"
    assert codes(result) == {"rfam_alignment_correspondence_unrepresented"}
    assert result["display_model_to"] == 120
    assert result["aligned_model_intervals"] == [[0, 71]]
    assert result["aligned_query_intervals"] == [[0, 70]]
    assert result["truncated_model_count_3p"] == 49
    assert result["model_consensus_compared_count"] == 70
    assert result["model_delete_count"] == 1
    assert result["query_insert_count"] == 0
    segment = result["segments"][-1]
    assert segment == {"kind": "truncated_model", "model_interval": [71, 120], "query_interval": None,
        "model_text": "*[49]>", "query_text": "*[ 0]>", "model_count": 49, "query_count": 0,
        "correspondence_represented": False}


def test_upstream_native_wrapped_reverse_local_end_preserves_unrepresented_positions():
    fixture = report_fixture("upstream-cobalamin-wrapped-local-end")
    result = parse_fixture(fixture)
    assert result["status"] == "partial"
    assert codes(result) == {"rfam_alignment_correspondence_unrepresented"}
    assert result["display_model_from"] == 1
    assert result["display_model_to"] == 191
    assert result["display_query_from"] == 934
    assert result["display_query_to"] == 832
    assert result["truncated_model_count_5p"] == 31
    assert result["local_end_model_omitted_count"] == 61
    assert result["local_end_query_count"] == 4
    assert result["query_insert_count"] == result["model_delete_count"] == 1
    assert len(result["paired_positions"]) == 98
    assert sum(b - a for a, b in result["aligned_model_intervals"]) == 99
    assert sum(b - a for a, b in result["aligned_query_intervals"]) == 99
    omitted = next(s for s in result["segments"] if s["kind"] == "local_end")
    assert omitted["correspondence_represented"] is False
    assert not any(omitted["query_interval"][0] <= p["query_position"] < omitted["query_interval"][1]
                   for p in result["paired_positions"])
    means = [p for p in result["posterior_segments"] if p["meaning"] == "span_mean_placement_bin"]
    assert means == [{"query_interval": omitted["query_interval"], "code": "7", "lower_bound": .65,
                      "upper_bound": .75, "meaning": "span_mean_placement_bin"}]


def test_synthetic_both_truncations_and_local_end_have_explicit_native_counts():
    model, query = "<[2]*AC*[3]*GU*[4]>", "<[0]*AC*[2]*GU*[0]>"
    alignment = synthetic(model, query, mend=13, qend=6, pp=".....**..7..**.....")
    result = parse(alignment, "ACUUGU")
    assert result["status"] == "partial"
    assert result["truncated_model_count_5p"] == 2
    assert result["truncated_model_count_3p"] == 4
    assert result["local_end_model_omitted_count"] == 3
    assert result["local_end_query_count"] == 2
    assert result["aligned_model_intervals"] == [[2, 4], [7, 9]]
    assert result["aligned_query_intervals"] == [[0, 2], [4, 6]]
    assert result["model_consensus_compared_count"] == result["model_consensus_equal_count"] == 4


def test_synthetic_empty_local_end_query_has_no_posterior_residues():
    result = parse(synthetic("A*[3]*U", "A*[0]*U", mend=5, qend=2, pp="*.....*"), "AU")
    assert result["status"] == "partial"
    assert result["local_end_query_count"] == 0
    assert result["segments"][1]["query_interval"] is None
    assert len(result["posterior_segments"]) == 2


def test_synthetic_large_shorthand_is_not_expanded():
    model, query = "<[1000000000]*A", "<[         0]*A"
    result = parse(synthetic(model, query, mend=1000000001, qend=1, pp="." * (len(model) - 1) + "*"), "A")
    assert result["status"] == "partial"
    assert result["truncated_model_count_5p"] == 1000000000
    assert result["aligned_model_intervals"] == [[1000000000, 1000000001]]
    assert len(result["segments"]) == 2


@pytest.mark.parametrize("code,bounds", [("0", (0, .05)), ("1", (.05, .15)), ("2", (.15, .25)),
    ("3", (.25, .35)), ("4", (.35, .45)), ("5", (.45, .55)), ("6", (.55, .65)),
    ("7", (.65, .75)), ("8", (.75, .85)), ("9", (.85, .95)), ("*", (.95, 1))])
def test_all_posterior_bins_are_intervals_not_point_estimates(code, bounds):
    result = parse(synthetic("A", "A", pp=code), "A")
    assert result["status"] == "complete"
    p = result["posterior_segments"][0]
    assert (p["lower_bound"], p["upper_bound"]) == bounds
    assert p["meaning"] == "residue_placement_bin"


def test_synthetic_ambiguity_and_tu_equivalence_have_conditional_denominator():
    result = parse(synthetic("aCGUNRY", "ACUTNRY"), "acutnry")
    assert result["status"] == "complete"
    assert len(result["paired_positions"]) == 7
    assert result["model_consensus_compared_count"] == 4
    assert result["model_consensus_equal_count"] == 3


def test_synthetic_all_ambiguous_pairs_are_unknown_not_equal_observations():
    result = parse(synthetic("NRYSWKMBDHV", "NRYSWKMBDHV"), "NRYSWKMBDHV")
    assert result["model_consensus_compared_count"] == 0
    assert result["model_consensus_equal_count"] == 0
    assert len(result["paired_positions"]) == 11


def test_synthetic_reverse_all_iupac_symbols_use_explicit_complement():
    sequence = "ACGTURYSWKMBDHVN"
    oriented = "NBDHVKMWSRYAACGU"
    result = parse(synthetic(oriented, oriented, qstart=16, qend=1), sequence, start=16, end=1, strand="-")
    assert result["status"] == "complete"
    assert [p["query_position"] for p in result["paired_positions"]] == list(range(15, -1, -1))
    assert result["model_consensus_compared_count"] == 5


def test_reverse_synthetic_hit_cannot_reuse_forward_display():
    alignment = synthetic("ACGU", "ACGU")
    result = parse(alignment, "ACGU", start=4, end=1, strand="-")
    assert result["status"] == "invalid"
    assert "rfam_alignment_coordinate_conflict" in codes(result)
    assert all(result[field] is None for field in RFAM_ALIGNMENT_COUNT_FIELDS)


@pytest.mark.parametrize("alteration,code", [
    (lambda a: a.update(user_seq="#SEQ 1 AGGU 4"), "rfam_alignment_query_conflict"),
    (lambda a: a.update(hit_seq="#CM 1 ACGU 5"), "rfam_alignment_coordinate_conflict"),
    (lambda a: a.update(user_seq="#SEQ 1 ACGU 5"), "rfam_alignment_coordinate_conflict"),
    (lambda a: a.update(hit_seq="#CM 0 ACGU 3"), "rfam_alignment_coordinate_conflict"),
    (lambda a: a.update(hit_seq="#CM 1 AC~U 4"), "rfam_alignment_unsupported"),
    (lambda a: a.update(hit_seq="#ALT 1 ACGU 4"), "rfam_alignment_unsupported"),
    (lambda a: a.update(hit_seq="#CM 1 AC*U 4"), "rfam_alignment_invalid"),
    (lambda a: a.update(hit_seq="#CM 1 AC.GU 4"), "rfam_alignment_coordinate_conflict"),
    (lambda a: a.update(user_seq=None), "rfam_alignment_missing"),
])
def test_malformed_and_unimplemented_display_grammar_are_explicit(alteration, code):
    alignment = synthetic("ACGU", "ACGU")
    alteration(alignment)
    result = parse(alignment, "ACGU")
    assert code in codes(result)
    assert result["status"] == ("unsupported" if code == "rfam_alignment_unsupported" else "invalid")
    assert result["paired_positions"] == []
    assert result["model_consensus_compared_count"] is None


@pytest.mark.parametrize("field,value", [("pp", None), ("pp", ""), ("pp", "#PP ****extra"),
    ("pp", "#PP **?*"), ("ss", None), ("nc", "#NC malformed"), ("match", None)])
def test_invalid_optional_tracks_preserve_valid_geometry(field, value):
    alignment = synthetic("ACGU", "ACGU")
    if value is None:
        alignment.pop(field)
    else:
        alignment[field] = value
    result = parse(alignment, "ACGU")
    assert result["status"] == "partial"
    assert result["model_consensus_compared_count"] == 4
    assert result["aligned_model_intervals"] == [[0, 4]]
    assert result["paired_positions"][0]["query_position"] == 0
    assert any(i["field"] == field for i in result["issues"])
    if field == "pp" and value != "#PP **?*":
        assert result["posterior_segments"] == []


def test_bad_pp_at_deleted_column_preserves_other_bins_and_geometry():
    result = parse(synthetic("ACGU", "A-GU", pp="****"), "AGU")
    assert result["status"] == "partial"
    assert result["model_delete_count"] == 1
    assert len(result["posterior_segments"]) == 3
    assert result["model_consensus_compared_count"] == 3


def test_double_gap_column_is_not_a_real_position():
    result = parse(synthetic("A.G", "A-G"), "AG")
    assert result["status"] == "invalid"
    assert "rfam_alignment_invalid" in codes(result)


@pytest.mark.parametrize("model,query,mend,qend", [
    ("A<[2]*U", "A<[0]*U", 4, 2),
    ("A*[2]>U", "A*[0]>U", 4, 2),
    ("<[2]*AU", "<[1]*AU", 4, 3),
    ("A*[0]*U", "A*[0]*U", 2, 2),
    ("A*[2]*U", "A*[2]>U", 4, 4),
])
def test_malformed_shorthand_boundaries_counts_and_kind_are_not_accepted(model, query, mend, qend):
    result = parse(synthetic(model, query, mend=mend, qend=qend, pp="." * len(model)), "AAAU", end=qend)
    assert result["status"] == "invalid"
    assert result["model_consensus_compared_count"] is None


def test_oversized_decimal_native_tokens_return_structured_failure():
    # Larger than Python's configured decimal conversion limit; no new parser
    # scientific size threshold is introduced by this check.
    import sys
    size = max(sys.get_int_max_str_digits(), 4300) + 1
    alignment = synthetic("A", "A")
    alignment["hit_seq"] = "#CM 1 A " + "9" * size
    result = parse(alignment, "A")
    assert result["status"] == "invalid"
    assert "rfam_alignment_invalid" in codes(result)


def test_wrapped_display_per_block_continuity_and_all_deletion_block():
    parts = [synthetic("AC", "AC", mstart=1, qstart=1),
             synthetic("GU", "--", mstart=3, qstart="-", qend="-", pp=".."),
             synthetic("AC", "AC", mstart=5, qstart=3)]
    display = {k: "\n".join(p[k] for p in parts) for k in parts[0]}
    result = parse(display, "ACAC")
    assert result["status"] == "complete"
    assert result["model_delete_count"] == 2
    assert result["aligned_model_intervals"] == [[0, 6]]
    display["hit_seq"] = display["hit_seq"].replace("#CM 5", "#CM 6")
    assert parse(display, "ACAC")["status"] == "invalid"


def test_wrapped_display_all_insertion_block_has_zero_model_span():
    parts = [synthetic("AC", "AC"), synthetic("..", "aa", mstart=3, mend=2, qstart=3),
             synthetic("GU", "GU", mstart=3, qstart=5)]
    display = {k: "\n".join(p[k] for p in parts) for k in parts[0]}
    result = parse(display, "ACAAGU")
    assert result["status"] == "complete"
    assert result["query_insert_count"] == 2
    assert result["aligned_model_intervals"] == [[0, 4]]
    assert result["aligned_query_intervals"] == [[0, 6]]


@pytest.mark.parametrize("start,end,strand", [(True, 4, "+"), (0, 4, "+"), (1, 5, "+"), (4, 1, "+"), (1, 4, "-")])
def test_hit_endpoint_validation_preserves_no_false_geometry(start, end, strand):
    result = parse(synthetic("ACGU", "ACGU"), "ACGU", start=start, end=end, strand=strand)
    assert result["status"] == "invalid"
    assert codes(result) == {"rfam_alignment_coordinate_conflict"}


@pytest.mark.parametrize("key,value,code", [("hit_identity", dict(IDENTITY, unexpected=True), "rfam_alignment_binding_conflict"),
    ("hit_identity", dict(IDENTITY, hit_key="foreign/hits/test/0"), "rfam_alignment_binding_conflict"),
    ("query_sequence", "AAZ", "rfam_sequence_invalid"), ("native_strand", "?", "rfam_hit_strand_invalid")])
def test_invalid_caller_contracts_raise_before_an_unbound_result(key, value, code):
    kwargs = dict(hit_identity=IDENTITY, query_sequence="ACGU", native_start=1, native_end=4, native_strand="+")
    kwargs[key] = value
    with pytest.raises(ContractError, match=code):
        parse_rfam_alignment_display(synthetic("ACGU", "ACGU"), **kwargs)


def test_no_network_process_file_access_or_input_mutation(monkeypatch):
    alignment = synthetic("ACGU", "ACGU")
    original = deepcopy(alignment)
    def forbidden(*args, **kwargs):
        raise AssertionError("parser attempted acquisition or execution")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    result = parse(alignment, "ACGU")
    assert result["status"] == "complete"
    assert alignment == original
    assert validate_rfam_alignment_result(json.loads(json.dumps(result, allow_nan=False))) == result


def test_exact_original_row_pointer_and_occurrence_are_retained():
    identity = dict(IDENTITY, hit_key=IDENTITY["artifact_ref"] + "/hits/family~1with~0escapes/7",
                    query_occurrence_key="same-sequence-distinct-occurrence-9")
    result = parse_rfam_alignment_display(synthetic("A", "A"), hit_identity=identity,
        query_sequence="A", native_start=1, native_end=1, native_strand="+")
    assert result["hit_identity"] == identity
    assert result["raw_alignment_ref"] == {"artifact_ref": identity["artifact_ref"],
        "json_pointer": "/hits/family~1with~0escapes/7/alignment"}
