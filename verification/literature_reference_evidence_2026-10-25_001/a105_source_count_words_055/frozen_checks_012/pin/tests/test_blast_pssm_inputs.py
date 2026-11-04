"""Supplied upstream inputs and explicitly synthetic format counterexamples."""
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode.blast_pssm_inputs import read_blast_msa_master, read_blast_pssm


SOURCES = Path(__file__).resolve().parents[1] / "verification/tool_graders_blast_pssm_2026-10-26_306/sources"


def pssm(text, **kw):
    return read_blast_pssm(text.encode(), format=kw.pop("format", "scoremat_asn_text"),
                           artifact_key=kw.pop("artifact_key", "supplied:synthetic"), source_ref="synthetic:test", **kw)


def msa(text, master=0, ignore=False, **kw):
    return read_blast_msa_master(text.encode(), format=kw.pop("format", "clustal"),
        artifact_key="supplied:synthetic", source_ref="synthetic:test", master_record_ordinal=master,
        ignore_master_for_profile=ignore, **kw)


def test_retained_primary_source_hashes_match_both_immutable_manifests():
    for filename in ("MANIFEST.json", "MANIFEST_002.json"):
        manifest = json.loads((SOURCES / filename).read_text())
        for entry in manifest["sources"]:
            raw = (SOURCES / Path(entry["file"]).name).read_bytes()
            assert len(raw) == entry["bytes"]
            assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


@pytest.mark.parametrize("filename,rows", [("pssm_freq_ratios.asn", 26), ("pssm_zero_fratios.asn", 28)])
def test_upstream_checkpoint_retains_full_text_and_native_cardinality(filename, rows):
    raw = (SOURCES / filename).read_bytes()
    sheet = read_blast_pssm(raw, format="scoremat_asn_text", artifact_key="upstream:" + filename,
                            source_ref="pinned-primary-source")
    assert sheet["status"] == "complete"
    assert sheet["native_text"] == raw.decode()
    assert sheet["input_identity"] == {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    assert set(sheet) == {"schema", "artifact_key", "source_ref", "format", "input_identity", "status", "native_text", "pssms", "issues"}
    row, = sheet["pssms"]
    assert row["native_type"] == "PssmWithParameters"
    assert row["native_pssm"]["numRows"] == rows
    assert row["native_pssm"]["numColumns"] == 232
    assert len(row["native_pssm"]["intermediateData"]["freqRatios"]) == rows * 232
    assert row["character_span"] == [0, raw.decode().rfind("}") + 1]
    assert json.loads(json.dumps(sheet, allow_nan=False)) == sheet


def test_upstream_seq_entry_repeated_descriptors_and_parameters_survive():
    row = read_blast_pssm((SOURCES / "pssm_freq_ratios.asn").read_bytes(), format="scoremat_asn_text",
        artifact_key="upstream:ratios", source_ref="pinned-primary-source")["pssms"][0]
    query_fields = row["native_pssm"]["query"]["seq"]
    descriptors = next(v["descr"] for v in query_fields if "descr" in v)
    assert len([v for v in descriptors if "source" in v]) == 2
    assert [next(iter(v)) for v in descriptors] == ["title", "user", "source", "source"]
    assert row["native_params"] == {"pseudocount": 9, "rpsdbparams": {"matrixName": "BLOSUM62"}}
    assert row["issues"] == []


def test_unknown_fields_real_representation_and_all_parameter_families_retained():
    sheet = pssm('''PssmWithParameters ::= { pssm { numRows 2, numColumns 1,
        future-field { seq { name "é" }, seq { name "β" } },
        finalData { scores { -32768, 0 }, lambda { 4, 2, -3 }, kappa 0.1, h 2 } },
        params { pseudocount 5, rpsdbparams { matrixName "test", gapOpen 11, gapExtend 1 },
        constraints { nblocks 1, blocks { { start 0, stop 1, property { { type 10, textvalue "x" } } } },
                      loops { { minlength 0, maxlength 2 }, { minlength 1 } } },
        bitScoreThresh { 1, 10, 1 }, bitScoreReportingThresh 1.25,
        annotatedSites { { startPosition 0, stopPosition 0, aliases { "a", "b" } } } } }''')
    row, = sheet["pssms"]
    assert sheet["status"] == "complete"
    assert row["native_pssm"]["future-field"] == [{"seq": [{"name": "é"}]}, {"seq": [{"name": "β"}]}]
    assert row["native_pssm"]["finalData"]["lambda"] == [4, 2, -3]
    assert row["native_pssm"]["finalData"]["kappa"] == {"real_token": "0.1"}
    assert row["native_params"]["bitScoreReportingThresh"] == {"real_token": "1.25"}
    assert row["native_params"]["annotatedSites"][0]["aliases"] == ["a", "b"]
    assert row["character_span"][1] < len(sheet["native_text"].encode())


@pytest.mark.parametrize("body,path", [
    ("numRows 2, numRows 3, numColumns 1", "pssm.numRows"),
    ("numRows 2, numColumns 1, finalData { scores { 1, 2 }, scores { 3, 4 } }", "pssm.finalData.scores"),
    ("numRows 2, numColumns 1, query seq { inst { length 1, length 2 } }", "pssm.query.seq.inst.length"),
])
def test_duplicate_typed_fields_are_retained_and_explicitly_rejected(body, path):
    sheet = pssm("Pssm ::= { " + body + " }")
    assert sheet["status"] != "complete"
    problem = next(i for i in sheet["issues"] if i["code"] == "asn_duplicate_field")
    assert problem["field"] == path
    assert problem["record_ordinal"] == 0
    assert problem["character_span"][0] < problem["character_span"][1]


def test_repeated_seq_entry_choices_in_compound_master_are_not_duplicate_fields():
    sheet = pssm('''Pssm ::= { numRows 2, numColumns 1, intermediateData { freqRatios { 0, 0 } },
       query set { seq-set { seq { inst { length 1, seq-data iupacaa "A" } },
                             seq { inst { length 1, seq-data iupacaa "C" } } } } }''')
    assert sheet["status"] == "complete"
    seqs = sheet["pssms"][0]["native_pssm"]["query"]["set"][0]["seq-set"]
    assert len(seqs) == 2
    assert all("seq" in v for v in seqs)


def test_multiple_records_original_ordinals_unicode_spans_and_truncated_tail():
    one = 'Pssm ::= { numRows 1, numColumns 1, rowLabels { "é" }, intermediateData { freqRatios { 1 } } }'
    text = '-- prologue é\n' + one + '\n' + one + '\nPssm ::= { numRows 2, numColumns 1, intermediateData { freqRatios { 2,'
    sheet = pssm(text, artifact_key="artifact:é")
    assert sheet["status"] == "partial"
    assert [r["record_ordinal"] for r in sheet["pssms"]] == [0, 1, 2]
    assert sheet["pssms"][1]["pssm_key"] == '["artifact:é",1]'
    for row in sheet["pssms"][:2]:
        assert text[slice(*row["character_span"])] == one
    assert any(i["code"] == "asn_truncated" and i["record_ordinal"] == 2 for i in sheet["issues"])
    assert sheet["pssms"][2]["native_pssm"]["intermediateData"]["freqRatios"] == [2]


@pytest.mark.parametrize("text", ["", "not an ASN record", "Pssm ::=", "Pssm ::= {", "Pssm ::= { numRows 2 numColumns 1 }"])
def test_empty_or_malformed_input_is_not_empty_success(text):
    sheet = pssm(text)
    assert sheet["status"] != "complete"
    assert sheet["issues"]
    assert sheet["native_text"] == text


@pytest.mark.parametrize("format,raw", [("scoremat_asn_binary", b"\x30\x80\xff"),
    ("ascii_pssm", b"Last position-specific scoring matrix computed\n"),
    ("ascii_pssm", (SOURCES / "aa.129295.pssm.txt").read_bytes())])
def test_unsupported_pssm_formats_remain_explicitly_unavailable(format, raw):
    sheet = read_blast_pssm(raw, format=format, artifact_key="supplied", source_ref="supplied")
    assert sheet["status"] == "unavailable" and sheet["pssms"] == []
    assert any(i["code"] == "unsupported_format" for i in sheet["issues"])
    assert sheet["input_identity"]["sha256"] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("filename,count,length", [("msa.clustalw.txt", 25, 151), ("sample_msa.txt", 14, 176)])
def test_upstream_complete_clustal_membership_lengths_and_map(filename, count, length):
    raw = (SOURCES / filename).read_bytes()
    sheet = read_blast_msa_master(raw, format="clustal", artifact_key="upstream:" + filename,
        source_ref="pinned-primary-source", master_record_ordinal=0, ignore_master_for_profile=False)
    assert sheet["status"] == "complete"
    assert sheet["native_text"] == raw.decode()
    assert len(sheet["records"]) == count
    assert len(sheet["records"][0]["ungapped_sequence"]) == length
    assert len(sheet["master_column_map"]) == sheet["alignment_columns"]
    mapped = [c for c in sheet["master_column_map"] if c["master_position"] is not None]
    assert [c["master_position"] for c in mapped] == list(range(length))
    assert "".join(c["symbol"] for c in mapped) == sheet["records"][0]["ungapped_sequence"]
    if filename == "sample_msa.txt":
        assert mapped[22]["uppercase_selected"] is True
        assert mapped[23]["symbol"] == "d" and mapped[23]["uppercase_selected"] is False
        assert mapped[92]["symbol"].islower()
        assert mapped[93]["symbol"] == "R" and mapped[93]["uppercase_selected"] is True
        assert mapped[94]["uppercase_selected"] is True


def test_selected_master_original_ordinal_case_gaps_and_ignore_do_not_drop_rows():
    text = 'CLUSTAL W\n\nfirst   A-Cd\nsecond  -eFG\n\nfirst   E-\nsecond  hI\n'
    sheet = msa(text, master=1, ignore=True)
    assert sheet["status"] == "complete"
    assert [r["identifier"] for r in sheet["records"]] == ["first", "second"]
    assert sheet["records"][1] == {"record_ordinal": 1, "identifier": "second", "aligned_sequence": "-eFGhI", "ungapped_sequence": "eFGhI"}
    assert sheet["master_column_map"] == [
        {"alignment_column": 0, "master_position": None, "symbol": "-", "uppercase_selected": False},
        {"alignment_column": 1, "master_position": 0, "symbol": "e", "uppercase_selected": False},
        {"alignment_column": 2, "master_position": 1, "symbol": "F", "uppercase_selected": True},
        {"alignment_column": 3, "master_position": 2, "symbol": "G", "uppercase_selected": True},
        {"alignment_column": 4, "master_position": 3, "symbol": "h", "uppercase_selected": False},
        {"alignment_column": 5, "master_position": 4, "symbol": "I", "uppercase_selected": True}]
    assert sheet["master_column_map"] == msa(text, master=1, ignore=False)["master_column_map"]


def test_duplicate_msa_identifiers_remain_separate_original_records():
    sheet = msa("CLUSTAL W\n\nsame  A-C\nsame  DEF\n\nsame  gH\nsame  IJ\n", master=1)
    assert sheet["status"] == "incompatible"
    assert [r["aligned_sequence"] for r in sheet["records"]] == ["A-CgH", "DEFIJ"]
    assert [i["record_ordinal"] for i in sheet["issues"] if i["code"] == "msa_duplicate_identifier"] == [0, 1]
    assert sheet["master_column_map"][0]["symbol"] == "D"


@pytest.mark.parametrize("text,code", [
    ("CLUSTAL W\n\n", "msa_alignment_missing"),
    ("CLUSTAL W\n\na  AC\nb  A\n", "msa_inconsistent_widths"),
    ("CLUSTAL W\n\na  AC\nb  DE\n\na  F\n", "msa_block_membership_invalid"),
    ("CLUSTAL W\n\na  AC\nb  DE\n\nCLUSTAL W\n\na  F\n", "msa_multiple_alignments"),
    (">a\nAC\n", "msa_header_invalid"),
])
def test_invalid_msa_retains_text_and_specific_failure(text, code):
    sheet = msa(text)
    assert sheet["status"] == "incompatible"
    assert sheet["native_text"] == text
    assert any(i["code"] == code for i in sheet["issues"])


def test_master_selection_validation_and_unsupported_alignment_format():
    text = "CLUSTAL W\n\na  AC\n"
    assert msa(text, master=9)["issues"][0]["code"] == "msa_master_out_of_range"
    assert msa(text, format="aligned_fasta")["status"] == "unavailable"
    with pytest.raises(ValueError):
        msa(text, master=True)
    with pytest.raises(ValueError):
        msa(text, ignore=1)
