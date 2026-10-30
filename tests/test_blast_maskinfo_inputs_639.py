"""Reuse retained 636 native bytes; no native execution or acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_maskinfo_inputs import parse_blast_maskinfo, _signature
from gene_annotation_episode.domain import ContractError

PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_mask_conversion_2026-10-28_636"


def occurrence(content, oid="mask", role="mask", completeness="complete"):
    digest = hashlib.sha256(content).hexdigest()
    return {"occurrence_id": oid, "direction": "output" if role == "mask" else "input", "role": role,
            "ordinal": 0, "artifact_ref": "artifact_" + digest, "sha256": digest,
            "size_bytes": len(content), "completeness": completeness}


def retained(case_id):
    data = json.loads((PACKET / "CAPTURE_001.json").read_text())
    row = next(r for r in data["cases"] if r["case_id"] == case_id)
    # Read the original captured bytes from the frozen support tree, not a
    # regenerated fixture; receipt text is a separate equality check.
    path = Path(row["native_output"]["path"])
    relative = path.relative_to("/home/chia/repos/gene_annotation_episode")
    content = (PACKET.parents[1] / relative).read_bytes()
    assert hashlib.sha256(content).hexdigest() == row["native_output"]["sha256"]
    assert len(content) == row["native_output"]["size_bytes"]
    source = data["inputs"][row["input_name"]]["content"].encode()
    assert hashlib.sha256(source).hexdigest() == data["inputs"][row["input_name"]]["artifact"]["sha256"]
    return row, source, content


def read(case_id):
    row, source, data = retained(case_id)
    return row, source, data, parse_blast_maskinfo(data, occurrence=occurrence(data), native_format=row["native_format"])


def test_authentic_xml_text_complete_native_ids_metadata_and_spans():
    observations = []
    for name in ("nucleotide_xml_parsed", "nucleotide_text_parsed"):
        case, _, data, parsed = read(name)
        assert parsed["parse_state"] == "complete", parsed["failures"]
        root = parsed["roots"][0]
        assert root["algorithm_id"] == 0
        assert root["algorithm_program_name"] == "dust"
        assert root["algorithm_options"] == case["declared_upstream_options"]
        assert root["mask_lists"][0]["more"] is False
        assert root["mask_lists"][0]["record_ordinals"] == [0, 1, 2]
        if name.endswith("xml_parsed"):
            assert (root["algorithm_program_code"], root["algorithm_program_code_presence"]) == (10, "serialized")
        else:
            assert (root["algorithm_program_code"], root["algorithm_program_code_presence"]) == (None, "not_serialized")
        signature = []
        for ordinal, record in enumerate(parsed["records"]):
            assert record["native_record_ordinal"] == ordinal
            assert record["record_ref"] == "mask#/native_mask_records/" + str(ordinal)
            loc = record["native_locator"]
            assert data[loc["byte_start"]:loc["byte_end"]].startswith(b"<Seq-loc>" if name.endswith("xml_parsed") else b"packed-int")
            assert loc["line_start"] == data[:loc["byte_start"]].count(b"\n") + 1
            signature.append([(r["start"], r["end_inclusive"], _signature(r["seq_id"])) for r in record["intervals"]])
        observations.append(signature)
    assert observations[0] == observations[1]
    assert observations[0][0][0][2] == ("local", "string", "mask_a")
    assert observations[0][1][0][2] == ("other", (("accession", "NM_999999999"), ("version", 7)))
    assert observations[0][2][0][2] == ("general", "fixture636", "string", "mask_general")


def test_authentic_single_packed_duplicate_and_generated_ids():
    *_, parsed = read("duplicate_headers_xml")
    assert [r["native_location_kind"] for r in parsed["records"]] == ["int", "packed_int"]
    assert [_signature(r["intervals"][0]["seq_id"]) for r in parsed["records"]] == [("local", "string", "duplicate")] * 2
    *_, parsed = read("nucleotide_xml_unparsed")
    assert [_signature(r["intervals"][0]["seq_id"]) for r in parsed["records"]] == [("local", "integer", n) for n in (1, 3, 4)]


def test_authentic_binary_is_explicitly_unsupported_and_exact_occurrence_checked():
    row, _, data, parsed = read("nucleotide_binary_parsed")
    assert parsed["parse_state"] == "unsupported"
    assert parsed["records"] == parsed["roots"] == []
    assert parsed["unparsed_spans"] == [{"byte_start": 0, "byte_end": len(data), "line_start": None, "line_end": None}]
    assert parsed["failures"][0]["code"] == "maskinfo_binary_reader_unimplemented"
    bad = occurrence(data); bad["sha256"] = "0" * 64
    with pytest.raises(ContractError, match="content_occurrence_mismatch"):
        parse_blast_maskinfo(data, occurrence=bad, native_format=row["native_format"])


def test_authentic_success_and_failed_empty_documents_are_identical():
    success, _, a, pa = read("uppercase_only_xml")
    failure, _, b, pb = read("malformed_xml")
    assert success["returncode"] == 0 and failure["returncode"] == 1
    assert a == b and pa == pb
    assert pa["parse_state"] == "complete" and pa["records"] == []


def test_synthetic_asn1_single_and_doubled_quote_escape_retains_lexemes():
    data = b'Blast-db-mask-info ::= { algo-id 0, algo-program other, algo-options "a ""quoted"" b", masks { masks { int { from 2, to 3, id local str "x" } }, more FALSE } }\n'
    parsed = parse_blast_maskinfo(data, occurrence=occurrence(data), native_format="maskinfo_asn1_text")
    assert parsed["parse_state"] == "complete", parsed["failures"]
    assert parsed["roots"][0]["algorithm_options"] == 'a "quoted" b'
    assert parsed["records"][0]["native_location_kind"] == "int"
    assert parsed["records"][0]["intervals"][0]["start"] == 2


@pytest.mark.parametrize("change,code", [
    (lambda s: s.replace(b">2</Seq-interval_from>", b">-2</Seq-interval_from>", 1), "maskinfo_interval_invalid"),
    (lambda s: s.replace(b">3</Seq-interval_to>", b">1</Seq-interval_to>", 1), "maskinfo_interval_invalid"),
    (lambda s: s.replace(b">mask_a</Object-id_str>", b">other</Object-id_str>", 1), "maskinfo_seq_id_conflict"),
    (lambda s: s.replace(b'value="false"', b'value="true"'), "maskinfo_more_unresolved"),
    (lambda s: s.replace(b"<Blast-db-mask-info_algo-id>0", b"<Blast-db-mask-info_algo-id>bad"), "maskinfo_metadata_invalid"),
    (lambda s: s.replace(b"</Blast-db-mask-info>", b""), "maskinfo_syntax_invalid"),
    (lambda s: s + b"extra", "maskinfo_syntax_invalid"),
])
def test_synthetic_malformed_native_fields_are_retained_without_renumbering(change, code):
    _, _, original = retained("nucleotide_xml_parsed")
    data = change(original)
    parsed = parse_blast_maskinfo(data, occurrence=occurrence(data), native_format="maskinfo_xml")
    assert parsed["parse_state"] == "partial"
    assert code in {r["code"] for r in parsed["failures"]}
    assert [r["native_record_ordinal"] for r in parsed["records"]] == [0, 1, 2]
    assert parsed["roots"][0]["native_tree"]


def test_synthetic_extra_roots_and_unknown_location_preserve_native_syntax():
    _, _, data = retained("duplicate_headers_xml")
    twice = data + data
    parsed = parse_blast_maskinfo(twice, occurrence=occurrence(twice), native_format="maskinfo_xml")
    assert len(parsed["roots"]) == 2 and len(parsed["records"]) == 4
    assert "maskinfo_stream_framing_unverified" in {r["code"] for r in parsed["failures"]}
    altered = data.replace(b"Seq-loc_int", b"Seq-loc_whole")
    parsed = parse_blast_maskinfo(altered, occurrence=occurrence(altered), native_format="maskinfo_xml")
    assert parsed["records"][0]["native_location_kind"] == "unsupported"
    assert parsed["records"][1]["native_record_ordinal"] == 1


def test_synthetic_truncated_text_retains_valid_closed_prior_member():
    _, _, original = retained("nucleotide_text_parsed")
    data = original[:original.index(b'      packed-int {', original.index(b'      packed-int {') + 1)]
    parsed = parse_blast_maskinfo(data, occurrence=occurrence(data, completeness="partial"), native_format="maskinfo_asn1_text")
    assert parsed["parse_state"] == "partial"
    assert parsed["records"][0]["completeness"] == "complete"
    assert parsed["unparsed_spans"]
