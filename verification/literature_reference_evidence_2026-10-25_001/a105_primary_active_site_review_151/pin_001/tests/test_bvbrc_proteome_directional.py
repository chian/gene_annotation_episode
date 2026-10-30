"""Retained public native reports and explicitly constructed error cases.

The fixtures establish text decoding, never BV-BRC deployment/task custody.
"""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.bvbrc_proteome_directional import (
    ProteomeDirectionalError, parse_genome_comparison_directional_report,
)
from gene_annotation_episode.bvbrc_proteome_directional_contracts import validate_directional_report


FIXTURES = Path(__file__).parent / "fixtures" / "bvbrc_proteome_directional"
FORMAT = "ncbi_blastall_blastp_pairwise_text_v1"
NATIVE_FILES = {
    "2011": ("biopython_text_2011L_blastp_002.txt", "c122ef42cd2d2da7ae5318045aa88a73c84713572a2c14d15c562117f3eec62d"),
    "2202": ("biopython_text_2202L_blastp_001.txt", "c0f5e5d3541500aef1ac93957fe35fbd4481f5788314e3e12ed1ea5f9d16510a"),
    "2221": ("biopython_text_2221L_blastp_001.txt", "e8bcff01bf827d936c36f00e4bbb73f2b5b1dd99b4d37af4cb9a6b0de44e25f8"),
}


def native(key="2221"):
    name, digest = NATIVE_FILES[key]
    data = (FIXTURES / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest
    return data


def source(data, **flags):
    return {"content": {"source_ref": "supplied-report", "artifact_field": "stdout_ref", "artifact_ref": "retained-test-bytes",
                        "sha256": hashlib.sha256(data).hexdigest(), "byte_count": len(data)},
            "body_complete": flags.get("body_complete", True), "object_complete": flags.get("object_complete", "yes")}


def parse(data, **flags):
    return parse_genome_comparison_directional_report(data, source=source(data, **flags), declared_format=FORMAT, report_key="test-report")


def all_issues(node):
    if isinstance(node, dict):
        yield from node.get("issues", [])
        for key, value in node.items():
            if key != "issues":
                yield from all_issues(value)
    elif isinstance(node, list):
        for value in node:
            yield from all_issues(value)


def codes(result):
    return {i["code"] for i in all_issues(result)}


def cells(node):
    if isinstance(node, dict):
        if set(node) == {"state", "value", "native_text", "locations"}:
            yield node
        else:
            for value in node.values():
                yield from cells(value)
    elif isinstance(node, list):
        for value in node:
            yield from cells(value)


def hsp(result, q=1, s=0, h=0):
    return result["queries"][q]["subjects"][s]["hsps"][h]


def test_native_fixture_provenance_hashes():
    receipts = json.loads((FIXTURES / "ACQUISITION_RECEIPTS_002.json").read_text())
    receipts += json.loads((FIXTURES / "ACQUISITION_RECEIPTS_003.json").read_text())
    for receipt in receipts:
        data = (FIXTURES / receipt["file"]).read_bytes()
        assert len(data) == receipt["byte_count"]
        assert hashlib.sha256(data).hexdigest() == receipt["sha256"]
        assert receipt["http_status"] == 200


@pytest.mark.parametrize("key,queries,descriptions,subjects,hsps", [
    ("2011", 1, [0], [0], [0]),
    ("2202", 2, [15, 8], [15, 8], [16, 9]),
    ("2221", 3, [10, 10, 10], [1, 1, 1], [1, 2, 1]),
])
def test_native_independent_populations(key, queries, descriptions, subjects, hsps):
    result = parse(native(key))
    assert result["parse_state"] == "ok"
    assert codes(result) == set()
    assert len(result["queries"]) == queries
    assert [len(q["descriptions"]) for q in result["queries"]] == descriptions
    assert [len(q["subjects"]) for q in result["queries"]] == subjects
    assert [sum(len(s["hsps"]) for s in q["subjects"]) for q in result["queries"]] == hsps


def test_native_2221_multiple_hsps_and_actual_numerators():
    result = parse(native())
    q = result["queries"][1]
    assert q["length"]["value"] == q["subjects"][0]["length"]["value"] == 600
    first, second = q["subjects"][0]["hsps"]
    assert [first[k]["value"] for k in ("bit_score", "raw_score", "expect", "identity_count", "identity_denominator")] == ["684", 1765, "0.0", 353, 414]
    assert [second[k]["value"] for k in ("bit_score", "raw_score", "expect", "identity_count", "identity_denominator")] == ["258", 658, "2e-66", 115, 115]
    for side in ("query", "subject"):
        assert (first["traceback_blocks"][0][side + "_start"]["value"], first["traceback_blocks"][-1][side + "_end"]["value"]) == (1, 414)
        assert (second["traceback_blocks"][0][side + "_start"]["value"], second["traceback_blocks"][-1][side + "_end"]["value"]) == (486, 600)
        positions = {position for h in (first, second) for b in h["traceback_blocks"] for position in range(b[side + "_start"]["value"], b[side + "_end"]["value"] + 1)}
        assert len(positions) == 529
    assert sum(h["identity_count"]["value"] for h in (first, second)) == 468
    assert first["gap_count"]["state"] == second["gap_count"]["state"] == "missing"
    assert first["expect_group_count"]["state"] == "missing"
    assert first["method_text"]["value"] == "Compositional matrix adjust."
    assert [q["boundary"] for q in result["queries"]] == ["next_banner", "next_banner", "eof_complete"]
    assert result["queries"][0]["statistics"] == q["statistics"] == []
    better = next(s for s in result["queries"][2]["statistics"] if s["kind"] == "sequences_better_than")
    assert better["integer_value"]["value"] == 30452
    assert better["threshold"]["value"] == "1.0e-05"


def test_native_2202_overlap_missing_gap_and_historical_percent():
    result = parse(native("2202"))
    q = result["queries"][0]
    s = q["subjects"][0]
    assert q["length"]["value"] == 1922 and s["length"]["value"] == 249
    first, second = s["hsps"]
    assert [first[k]["value"] for k in ("bit_score", "raw_score", "expect", "identity_count", "identity_denominator", "positive_count", "gap_count")] == ["68.9", 167, "3e-12", 53, 176, 83, 36]
    assert [second[k]["value"] for k in ("bit_score", "raw_score", "expect", "identity_count", "identity_denominator", "positive_count")] == ["37.7", 86, "0.007", 20, 47, 28]
    assert second["gap_count"] == {"state": "missing", "value": None, "native_text": None, "locations": []}
    for side, expected in (("query", 219), ("subject", 144)):
        union = {position for h in (first, second) for b in h["traceback_blocks"] for position in range(b[side + "_start"]["value"], b[side + "_end"]["value"] + 1)}
        assert len(union) == expected
    historical = result["queries"][1]["subjects"][6]["hsps"][0]
    assert [historical[k]["value"] for k in ("positive_count", "positive_denominator", "positive_printed_percent")] == [16, 29, "54"]


def test_native_no_hit_statistics_and_zero():
    result = parse(native("2011"))
    q = result["queries"][0]
    assert q["no_hits_marker"]["value"] == " ***** No hits found ******"
    assert q["subjects"] == q["descriptions"] == []
    header = q["database_headers"][0]
    assert (header["sequence_count"]["value"], header["letter_count"]["value"]) == (6999, 1461753)
    assert header["letter_count"]["native_text"] == "1,461,753"
    stats = {s["kind"]: s for s in q["statistics"]}
    assert stats["sequences_better_than"]["integer_value"]["value"] == 0
    assert stats["sequences_better_than"]["threshold"]["value"] == "10.0"
    assert stats["effective_search_space_used"]["integer_value"]["value"] == 62304000
    assert stats["ka_gapped"]["lambda"]["value"] == "0.270"
    assert stats["ka_ungapped"]["k"]["value"] == "0.126"
    assert stats["database_posted_date"]["text_value"]["value"] == "Feb 11, 2000  2:32 PM"
    assert stats["gap_open"]["integer_value"]["value"] == 11
    assert stats["gap_extend"]["integer_value"]["value"] == 1


@pytest.mark.parametrize("key", NATIVE_FILES)
@pytest.mark.parametrize("crlf", [False, True])
def test_every_native_cell_slices_original_bytes(key, crlf):
    # CRLF variants are constructed layout cases; original fixture bytes stay unchanged.
    data = native(key)
    if crlf:
        data = data.replace(b"\n", b"\r\n")
    result = parse(data)
    assert result["parse_state"] == "ok"
    for cell in cells(result):
        if cell["state"] != "missing":
            assert len(cell["locations"]) == 1
            loc = cell["locations"][0]
            a, b = loc["span"]["byte_start"], loc["span"]["byte_end"]
            assert data[a:b].decode("utf-8") == cell["native_text"]
            assert loc["sha256"] == hashlib.sha256(data).hexdigest()


def test_multiline_headers_and_exact_midline_spaces():
    result = parse(native())
    first_subject = result["queries"][0]["subjects"][0]
    assert "pdb|1JLX|B" in first_subject["defline_text"]["value"]
    assert "pdb|1JLY|B" in first_subject["defline_text"]["value"]
    assert first_subject["identifier_token"]["value"] == "pdb|1JLX|A"
    assert len(first_subject["hsps"]) == 1
    blocks = hsp(result)["traceback_blocks"]
    assert blocks[2]["midline"]["value"].endswith("     ")
    assert blocks[3]["midline"]["value"].startswith(" " * 14)
    assert len(blocks[3]["midline"]["value"]) == 60
    assert result["queries"][0]["descriptions"][0]["ellipsis_suffix"] is True
    assert result["queries"][0]["descriptions"][1]["ellipsis_suffix"] is False
    exponent = result["queries"][0]["descriptions"][1]["evalue"]
    assert exponent["native_text"] == "e-179" and exponent["value"] == "1e-179"


def test_constructed_underflow_zero_and_expect_group():
    data = native().replace(b"Expect = 2e-66", b"Expect(2) = e-900", 1)
    result = parse(data)
    assert hsp(result, h=1)["expect"]["value"] == "1e-900"
    assert Decimal(hsp(result, h=1)["expect"]["value"]) > 0
    assert hsp(result, h=1)["expect"]["native_text"] == "e-900"
    assert hsp(result, h=1)["expect_group_count"]["value"] == 2
    assert hsp(result)["expect"]["value"] == "0.0"


@pytest.mark.parametrize("token", [b"NaN", b"Infinity", b"oops", b"1,23"])
def test_constructed_invalid_decimal_preserves_good_neighbors(token):
    result = parse(native().replace(b"Expect = 2e-66", b"Expect = " + token))
    assert result["parse_state"] == "partial"
    assert hsp(result, h=1)["expect"]["state"] == "invalid"
    assert hsp(result, h=1)["expect"]["native_text"] == token.decode()
    assert hsp(result)["identity_count"]["value"] == 353
    assert result["queries"][2]["subjects"][0]["hsps"][0]["identity_count"]["value"] == 458
    assert "invalid_native_number" in codes(result)


def test_constructed_optional_missing_positives_midline_and_gaps():
    data = native().replace(b", Positives = 115/115 (100%)", b"")
    data = data.replace(b"           KDGRHRAPVTFDESGSLPFFSLAQFFLLNEDDEDQPRGLTKEQIDNLAMRSFGENDALKT\n", b"")
    result = parse(data)
    second = hsp(result, h=1)
    assert second["positive_count"]["state"] == second["gap_count"]["state"] == "missing"
    assert second["traceback_blocks"][0]["midline"]["state"] == "missing"
    assert second["identity_count"]["value"] == 115


def test_constructed_explicit_zero_gap_is_distinct_from_missing_gap():
    data = native().replace(b"Identities = 115/115 (100%), Positives = 115/115 (100%)", b"Identities = 115/115 (100%), Positives = 115/115 (100%), Gaps = 0/115 (0%)")
    result = parse(data)
    assert hsp(result)["gap_count"]["state"] == "missing"
    gap = hsp(result, h=1)["gap_count"]
    assert gap["state"] == "present" and gap["value"] == 0 and gap["native_text"] == "0"


def test_constructed_malformed_later_score_and_count_keep_native_tokens():
    data = native().replace(b"Score =  258 bits (658)", b"Score = BAD bits (raw?)")
    data = data.replace(b"Identities = 115/115 (100%)", b"Identities = bad/115 (100%)")
    result = parse(data)
    second = hsp(result, h=1)
    assert result["parse_state"] == "partial"
    for field, text in (("bit_score", "BAD"), ("raw_score", "raw?"), ("identity_count", "bad")):
        assert second[field]["state"] == "invalid" and second[field]["native_text"] == text
    assert second["identity_denominator"]["value"] == 115
    assert hsp(result)["identity_count"]["value"] == 353
    assert hsp(result, q=2)["identity_count"]["value"] == 458


def test_constructed_no_hit_words_in_description_are_not_a_marker():
    data = native().replace(b"gb|AAQ03084.1|AF401479_1 agglutinin [Amaranthus caudatus]", b"gb|AAQ03084.1|AF401479_1 No hits found protein title   ")
    result = parse(data)
    assert result["queries"][0]["no_hits_marker"]["state"] == "missing"
    assert len(result["queries"][0]["descriptions"]) == 10


def test_constructed_truncated_second_hsp_keeps_earlier_work():
    data = native()
    cut = data.index(b"Sbjct: 546") + len(b"Sbjct: 546 CSVCITEY")
    result = parse(data[:cut])
    assert result["parse_state"] == "partial"
    assert len(result["queries"]) == 2
    assert len(result["queries"][1]["subjects"][0]["hsps"]) == 2
    assert hsp(result, q=0)["identity_count"]["value"] == 303
    assert hsp(result)["identity_count"]["value"] == 353
    assert hsp(result, h=1)["identity_count"]["value"] == 115
    assert hsp(result, h=1)["traceback_blocks"][-1]["subject_end"]["state"] == "missing"
    assert {"incomplete_traceback_block", "unterminated_native_block"} <= codes(result)


def test_constructed_missing_later_score_retains_separate_hsp():
    data = native().replace(b" Score =  258 bits (658), Expect = 2e-66,   Method: Compositional matrix adjust.\n", b"")
    result = parse(data)
    assert len(result["queries"][1]["subjects"][0]["hsps"]) == 2
    assert hsp(result, h=1)["identity_count"]["value"] == 115
    assert hsp(result, h=1)["bit_score"]["state"] == "missing"
    assert "missing_hsp_score" in codes(result)


def test_constructed_duplicates_are_occurrences_not_unique_keys():
    original = native()
    initial = parse(original)
    span = initial["queries"][1]["subjects"][0]["span"]
    duplicated = original[:span["byte_end"]] + original[span["byte_start"]:span["byte_end"]] + original[span["byte_end"]:]
    result = parse(duplicated + duplicated)
    assert len(result["queries"]) == 6
    q = result["queries"][1]
    assert len(q["subjects"]) == 2
    assert [s["ordinal"] for s in q["subjects"]] == [0, 1]
    assert q["subjects"][0]["identifier_token"]["value"] == q["subjects"][1]["identifier_token"]["value"]
    assert [len(s["hsps"]) for s in q["subjects"]] == [2, 2]
    assert len(q["descriptions"]) == 10


@pytest.mark.parametrize("old,new,expected", [
    (b"Identities = 353/414", b"Identities = 415/414", "count_out_of_bounds"),
    (b"Positives = 353/414", b"Positives = 353/413", "alignment_denominator_mismatch"),
    (b"Query: 1   MENS", b"Query: 0   MENS", "coordinate_out_of_bounds"),
    (b"MENSDSNDKGSDQSAAQRRSQMDRLDREEAFYQFVNNLSEEDYRLMRDNNLLGTPGESTE 60", b"MENSDSNDKGSDQSAAQRRSQMDRLDREEAFYQFVNNLSEEDYRLMRDNNLLGTPGESTE 61", "coordinate_symbol_count_mismatch"),
    (b"(600 letters)", b"(400 letters)", "coordinate_out_of_bounds"),
    (b"Query: 486 KDGR", b"Query: 550 KDGR", "nonprotein_coordinate_order"),
    (b"Sbjct: 486 KDGRHR", b"Sbjct: 486 DGRHR", "traceback_width_mismatch"),
])
def test_constructed_contradictions_stay_present_with_required_issue(old, new, expected):
    result = parse(native().replace(old, new, 1))
    assert result["parse_state"] == "partial"
    assert expected in codes(result)
    assert validate_directional_report(result) == result
    assert all(c["state"] != "invalid" for c in cells(result))


def test_constructed_unknown_footer_and_repeated_statistic_retained():
    data = native("2011").replace(b"S2: 47 (22.7 bits)", b"Number of Sequences: 7000\nUnreviewed counter: 17\nS2: 47 (22.7 bits)")
    result = parse(data)
    assert result["parse_state"] == "partial"
    stats = result["queries"][0]["statistics"]
    assert [s["integer_value"]["value"] for s in stats if s["kind"] == "sequence_counter"] == [6999, 7000]
    assert any(r["kind"] == "unknown_footer" for r in result["raw_records"])
    assert "unparsed_scientific_record" in codes(result)


@pytest.mark.parametrize("data,expected", [
    (b"BLASTP 2.2.2\nQuery=   \n (12 letters)\n", "missing_query_header"),
    (b"BLASTP 2.2.2\nQuery= q\n (bad letters)\n", "invalid_native_number"),
    (b"BLASTP 2.2.2\nQuery= q\n\n> s\n Score = BAD bits (x), Expect = NaN\n", "missing_query_length"),
    (b"BLASTP 2.2.2\nQuery= q\n (10 letters)\n> s\n Score = 2 bits (3), Expect = 0\nQuery: -1 AA 2\nSbjct: 1 AA 2\n", "invalid_native_number"),
])
def test_constructed_malformed_blocks_return_partial_without_throwing(data, expected):
    result = parse(data)
    assert result["parse_state"] == "partial"
    assert expected in codes(result)
    assert validate_directional_report(result) == result


def test_constructed_no_hit_marker_with_alignments_is_qualified():
    data = native().replace(b">sp|Q9WTV7.1|RNF12_MOUSE", b" ***** No hits found ******\n>sp|Q9WTV7.1|RNF12_MOUSE", 1)
    result = parse(data)
    assert "no_hits_with_alignments" in codes(result)
    assert len(result["queries"][1]["subjects"][0]["hsps"]) == 2


def test_constructed_unicode_header_and_extra_traceback_tokens_keep_byte_locations():
    data = native().replace(b"Query= gi|3298468|dbj|BAA31520.1| SAMIPF", "Query= gi|3298468|dbj|BAA31520.1| SAMIPF α".encode())
    data = data.replace(b"Sbjct: 301 QNN 303", b"Sbjct: 301 QNN 303 unexpected", 1)
    result = parse(data)
    assert "unparsed_scientific_record" in codes(result)
    assert hsp(result, q=0)["traceback_blocks"][-1]["subject_end"]["value"] == 303
    for cell in cells(result):
        if cell["state"] != "missing":
            span = cell["locations"][0]["span"]
            assert data[span["byte_start"]:span["byte_end"]].decode() == cell["native_text"]


@pytest.mark.parametrize("flags,expected", [
    ({"body_complete": False}, "source_body_incomplete"),
    ({"object_complete": "no"}, "source_object_incomplete"),
    ({"object_complete": "unknown"}, "source_object_completeness_unknown"),
])
def test_source_completeness_is_not_execution_completeness(flags, expected):
    result = parse(native(), **flags)
    assert result["parse_state"] == "partial"
    assert expected in codes(result)
    assert len(result["queries"]) == 3


@pytest.mark.parametrize("data,expected", [
    (b'{"BlastOutput2": []}', "missing_banner"),
    (b"BLASTP 2.17.0+\nQuery= x\n (10 letters)\n", "unsupported_banner_version"),
    (b"BLASTN 2.2.2\nQuery= x\n (10 letters)\n", "unsupported_program"),
    (b"\xff\xfe\x80", "unsupported_encoding"),
])
def test_incompatible_native_input_is_failure(data, expected):
    result = parse(data)
    assert result["parse_state"] == "failure"
    assert expected in codes(result)


def test_unsupported_section_does_not_erase_supported_neighbors():
    result = parse(native("2011") + b"BLASTP 2.17.0+\nQuery= unreviewed\n (10 letters)\n" + native("2011"))
    assert result["parse_state"] == "partial"
    assert len(result["queries"]) == 2
    assert [q["banner_ordinal"] for q in result["queries"]] == [0, 2]
    assert "unsupported_banner_version" in codes(result)


def test_constructed_wrong_declared_format_and_source_errors():
    data = native("2011")
    result = parse_genome_comparison_directional_report(data, source=source(data), declared_format="json2", report_key="wrong-format")
    assert result["parse_state"] == "failure" and "unsupported_format" in codes(result)
    for mutate, expected, path in (
        (lambda s: s["content"].update(sha256="0" * 64), "directional_digest_mismatch", "/source/content/sha256"),
        (lambda s: s["content"].update(byte_count=len(data) + 1), "directional_byte_count_mismatch", "/source/content/byte_count"),
        (lambda s: s.update(validated=True), "directional_source_invalid", "/source"),
        (lambda s: s["content"].update(byte_count=True), "directional_source_invalid", "/source/content/byte_count"),
    ):
        supplied = source(data)
        mutate(supplied)
        with pytest.raises(ProteomeDirectionalError) as caught:
            parse_genome_comparison_directional_report(data, source=supplied, declared_format=FORMAT, report_key="caller-key")
        assert caught.value.code == expected and caught.value.path == path
        assert str(caught.value) == expected


@pytest.mark.parametrize("key", ["", "   ", None, 5, True])
def test_invalid_caller_report_keys(key):
    data = native("2011")
    with pytest.raises(ProteomeDirectionalError, match="directional_argument_invalid"):
        parse_genome_comparison_directional_report(data, source=source(data), declared_format=FORMAT, report_key=key)


def test_data_only_parse_and_revalidation_and_detached_copies(monkeypatch):
    data = native()
    supplied = source(data)
    def prohibited(*args, **kwargs):
        raise AssertionError("unexpected IO")
    monkeypatch.setattr("builtins.open", prohibited)
    monkeypatch.setattr(Path, "open", prohibited)
    monkeypatch.setattr("socket.socket", prohibited)
    monkeypatch.setattr("subprocess.Popen", prohibited)
    result = parse_genome_comparison_directional_report(data, source=supplied, declared_format=FORMAT, report_key="io-test")
    saved = json.loads(json.dumps(result))
    copied = validate_directional_report(saved)
    assert copied == result
    supplied["body_complete"] = False
    copied["queries"][0]["header_text"]["value"] = "changed"
    assert result["source"]["body_complete"] is True
    assert result["queries"][0]["header_text"]["value"] == saved["queries"][0]["header_text"]["value"]
