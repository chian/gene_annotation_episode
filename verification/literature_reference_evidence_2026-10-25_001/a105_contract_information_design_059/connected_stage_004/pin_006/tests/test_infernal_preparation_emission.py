"""Native retained cmemit format tests and explicitly synthetic counterexamples."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.infernal_preparation_emission import (
    ISSUE_CODES, ROW_FIELDS, populate_cmemit_sheet,
)
from gene_annotation_episode.infernal_preparation_models import extract_infernal_models


ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / "verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"
NATIVE = ROOT / "verification/tool_graders_infernal_preparation_emission_2026-10-26_250/native"


def artifact(content, role, fmt, *, complete="complete", ref=None):
    raw = content.encode() if isinstance(content, str) else content
    return {"role": role, "format": fmt, "artifact_ref": ref or role,
            "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "completeness": complete}


def build_sheet(content, *, mode="sample_unaligned", fmt="fasta", settings=None, model_content=None,
                complete="complete", model_complete="complete", model_extraction=None, trace=None):
    model_content = model_content if model_content is not None else (PRIOR / "cmemit_fasta/model.cm").read_bytes()
    ma = artifact(model_content, "models", "infernal_cm_ascii", complete=model_complete)
    models = model_extraction or extract_infernal_models(model_content, artifact=ma, format=ma["format"], engine_version="1.1.5")
    role = "generated_alignment" if mode == "sample_aligned" else "generated_sequences"
    oa = artifact(content, role, fmt, complete=complete)
    operation = {"program": "cmemit", "mode": mode, "engine_version": "1.1.5",
                 "settings": {"-N": 2, "--idx": 1, "--seed": 181, "--rna": True} if settings is None else settings}
    artifacts = [models["artifact"], oa]
    tp = None
    if trace is not None:
        ta = artifact(trace, "trace", "infernal_trace")
        artifacts.append(ta)
        tp = {"artifact": ta, "content": trace}
    return populate_cmemit_sheet(operation=operation, artifacts=artifacts, models=models,
        output={"artifact": oa, "content": content}, trace=tp)


def rows(sheet, kind="generated_sequence"):
    return [r for r in sheet["output_records"] if r["kind"] == kind]


def codes(sheet):
    return {i["code"] for i in sheet["issues"]}


def test_native_fasta_and_actual_model_parser():
    sheet = build_sheet((PRIOR / "cmemit_fasta/emitted.out").read_bytes())
    seqs = rows(sheet)
    assert sheet["input_records"][0]["topology"]["base_pair_nodes"]["value"] == 4
    assert [r["sequence"] for r in seqs] == ["GCGCUAAGCGC", "GCGCUAAAGCGC"]
    assert [r["values"]["residue_count"]["value"] for r in seqs] == [11, 12]
    assert [r["values"]["gc_count"]["value"] for r in seqs] == [8, 8]
    assert [r["sample_index"] for r in seqs] == [1, 2]
    assert all(a["status"] == "validated" for a in sheet["associations"])
    assert not sheet["issues"]
    assert all(set(r) == ROW_FIELDS[r["kind"]] for r in sheet["output_records"])
    assert "subject_ref" not in str(sheet)


def test_consensus_preserves_native_case_and_distinct_origin():
    sheet = build_sheet((PRIOR / "cmemit_consensus/emitted.out").read_bytes(), mode="consensus")
    row = rows(sheet)[0]
    assert row["sequence"] == "GCGCaaAAGCGC"
    assert row["origin"] == "generated_consensus"
    assert row["sample_index"] is None
    assert row["residue_sha256"] == hashlib.sha256(b"GCGCAAAAGCGC").hexdigest()


@pytest.mark.parametrize("name,fmt", [("aligned_pfam", "pfam"), ("aligned_afa", "afa"),
    ("aligned_a2m", "a2m"), ("aligned_clustal", "clustal"), ("aligned_phylip", "phylip")])
def test_actual_native_formats(name, fmt):
    sheet = build_sheet((NATIVE/name/"emitted.out").read_bytes(), mode="sample_aligned", fmt=fmt,
        settings={"-N": 3, "--idx": 1, "--rna": True, "--outformat": fmt})
    assert len(rows(sheet)) == 3
    assert rows(sheet, "generated_alignment")[0]["values"]["column_count"]["value"] == 12
    assert [r["values"]["residue_count"]["value"] for r in rows(sheet)] == [11, 12, 12]
    assert all(a["status"] == "validated" for a in sheet["associations"])
    assert not [i for i in sheet["issues"] if i["severity"] == "error"]
    if fmt == "phylip":
        assert [r["name"] for r in rows(sheet)] == ["fixture246"] * 3
        assert [r["sample_index"] for r in rows(sheet)] == [1, 2, 3]


def test_native_a2m_insertion_columns_remain_unavailable():
    sheet = build_sheet((NATIVE/"a2m_insertions/emitted.out").read_bytes(), mode="sample_aligned", fmt="a2m",
        settings={"-N": 5, "--idx": 1, "--rna": True, "--exp": .5, "--outformat": "A2M"})
    seqs = rows(sheet)
    assert seqs[0]["sequence"] == "GCGC-uUAAGCGC"
    assert seqs[0]["values"]["residue_count"]["value"] == 12
    assert seqs[0]["values"]["gap_count"]["value"] == 1
    assert all(r["values"]["column_count"]["state"] == "not_measured" for r in seqs)
    assert rows(sheet, "generated_alignment")[0]["values"]["column_count"]["state"] == "not_measured"
    assert "cmemit_a2m_insert_columns_not_retained" in codes(sheet)


def test_full_stockholm_annotations_and_locators():
    text = ("# STOCKHOLM 1.0\n#=GF ID fixture246\n#=GF CC first\n#=GF CC second\n"
            "#=GS fixture246-sample1 DE case test\n\nfixture246-sample1 Gc-\nfixture246-sample2 AcU\n"
            "#=GR fixture246-sample1 PP 98.\n#=GC RF xxx\n#=GC SS_cons <._\n\n"
            "fixture246-sample1 AaG\nfixture246-sample2 C-G\n#=GR fixture246-sample1 PP 877\n"
            "#=GC RF xxx\n#=GC SS_cons __>\n//\n")
    sheet = build_sheet(text, mode="sample_aligned", fmt="stockholm")
    al = rows(sheet, "generated_alignment")[0]
    seqs = rows(sheet)
    assert [r["sequence"] for r in seqs] == ["Gc-AaG", "AcUC-G"]
    assert [(a["tag"], a["value"]) for a in al["annotations"]["gf"]] == [
        ("ID", "fixture246"), ("CC", "first"), ("CC", "second")]
    assert al["annotations"]["gs"][0]["sequence_key"] == seqs[0]["record_key"]
    assert [a["block_index"] for a in al["annotations"]["gr"]] == [0, 1]
    for family in al["annotations"].values():
        for ann in family:
            loc = ann["locator"]
            native_line = text.encode()[loc["byte_start"]:loc["byte_end"]].decode()
            assert ann["value"] in native_line
            assert loc["line_start"] == loc["line_end"]


def test_duplicate_sequence_name_annotations_not_arbitrarily_joined():
    text = "# STOCKHOLM 1.0\n#=GS fixture246-sample1 DE ambiguous\nfixture246-sample1 AC\nfixture246-sample1 GU\n#=GR fixture246-sample1 PP 99\n#=GC RF xx\n//\n"
    sheet = build_sheet(text, mode="sample_aligned", fmt="stockholm")
    al = rows(sheet, "generated_alignment")[0]
    assert al["annotations"]["gs"][0]["sequence_key"] is None
    assert al["annotations"]["gr"][0]["sequence_key"] is None
    assert "cmemit_annotation_association_ambiguous" in codes(sheet)


def test_duplicate_models_resolve_only_with_complete_order_and_boundaries():
    native = NATIVE/"duplicate_models"
    sheet = build_sheet((native/"emitted.out").read_bytes(), mode="sample_aligned", fmt="stockholm",
                        model_content=(native/"model.cm").read_bytes())
    seqs = rows(sheet)
    assert [r["model_keys"] for r in seqs] == [["models#model/0"], ["models#model/0"], ["models#model/1"], ["models#model/1"]]
    assert all(a["status"] == "validated" for a in sheet["associations"])
    partial = build_sheet((native/"emitted.out").read_bytes().split(b"//")[0]+b"//\n", mode="sample_aligned", fmt="stockholm",
                         model_content=(native/"model.cm").read_bytes(), complete="partial")
    assert all(a["status"] != "validated" for a in partial["associations"])


def test_hyphenated_model_and_nondefault_sample_index():
    model = (PRIOR/"cmemit_fasta/model.cm").read_bytes().replace(b"fixture246", b"model-with-hyphen")
    sheet = build_sheet(">model-with-hyphen-sample7\nACGU\n>model-with-hyphen-sample8\nCCGU\n", model_content=model,
                        settings={"-N": 2, "--idx": 7, "--rna": True})
    assert [r["sample_index"] for r in rows(sheet)] == [7, 8]
    assert all(a["status"] == "validated" for a in sheet["associations"])


@pytest.mark.parametrize("name,flags", [("consensus_hmm", {"--hmmonly": True}), ("unaligned_auto_hmm", {})])
def test_actual_hmm_emission(name, flags):
    mode = "consensus" if name.startswith("consensus") else "sample_unaligned"
    sheet = build_sheet((NATIVE/name/"emitted.out").read_bytes(), mode=mode,
        model_content=(NATIVE/name/"model.cm").read_bytes(), settings={"-N": 2, "--idx": 1, "--rna": True, **flags})
    assert all(a["status"] == "validated" for a in sheet["associations"])
    assert rows(sheet)[0]["origin"] == ("generated_consensus" if mode == "consensus" else "generated_sample")


@pytest.mark.parametrize("name,settings", [("unaligned_trunc_5p", {"--u5p": True}),
    ("unaligned_trunc_3p", {"--u3p": True}), ("unaligned_trunc_both", {"--u5p": True, "--u3p": True}),
    ("unaligned_local_exp", {"-l": True, "--exp": .8})])
def test_native_truncation_and_local_settings_preserved(name, settings):
    settings = {"-N": 2, "--idx": 1, "--rna": True, **settings}
    sheet = build_sheet((NATIVE/name/"emitted.out").read_bytes(), settings=settings)
    assert sheet["operation"]["settings"] == settings
    assert all(r["embedded_interval"] is None for r in rows(sheet))
    assert all(a["status"] == "validated" for a in sheet["associations"])


@pytest.mark.parametrize("name,endpoints,columns", [("aligned_trunc_fixed", (3,9),7), ("aligned_trunc_random", (0,0),8)])
def test_native_aligned_truncation(name, endpoints, columns):
    sheet = build_sheet((NATIVE/name/"emitted.out").read_bytes(), mode="sample_aligned", fmt="stockholm",
        settings={"-N": 2, "--idx": 1, "--rna": True, "--a5p": endpoints[0], "--a3p": endpoints[1]})
    assert rows(sheet, "generated_alignment")[0]["values"]["column_count"]["value"] == columns
    assert all(r["embedded_interval"] is None for r in rows(sheet))


def test_native_embedding_preserves_actual_symbols_and_interval():
    sheet = build_sheet((NATIVE/"embedded_3p/emitted.out").read_bytes(),
        settings={"-N": 2, "--idx": 1, "--rna": True, "-e": 40, "--iid": True, "--u3p": True})
    row = rows(sheet)[0]
    assert row["embedded_interval"] == {"start": 37, "end": 40}
    assert row["values"]["residue_count"]["value"] == 40
    assert not {"cmemit_embedding_length_mismatch", "cmemit_embedding_interval_invalid"} & codes(sheet)


def test_synthetic_embedding_mismatch_and_out_of_bounds_are_reported():
    sheet = build_sheet(">fixture246-sample1/38-40\nACGU\n", settings={"-N": 1, "--idx": 1, "--rna": True, "-e": 40})
    row = rows(sheet)[0]
    assert row["embedded_interval"] == {"start": 37, "end": 40}
    assert row["values"]["residue_count"]["value"] == 4
    assert {"cmemit_embedding_length_mismatch", "cmemit_embedding_interval_invalid"} <= codes(sheet)


@pytest.mark.parametrize("name", ["trace_unaligned_cm", "trace_unaligned_hmm", "trace_aligned_cm", "trace_aligned_hmm"])
def test_actual_trace_headers_and_retained_bodies(name):
    aligned = "trace_aligned" in name
    sheet = build_sheet((NATIVE/name/"emitted.out").read_bytes(),
        mode="sample_aligned" if aligned else "sample_unaligned", fmt="stockholm" if aligned else "fasta",
        settings={"-N": 2, "--idx": 1, "--rna": True, **({"--hmmonly": True} if name.endswith("hmm") else {})},
        trace=(NATIVE/name/"traces.txt").read_bytes())
    if name == "trace_aligned_hmm":
        assert "cmemit_trace_empty" in codes(sheet)
        assert not sheet["native_rows"]
        return
    assert "cmemit_trace_body_not_decoded" in codes(sheet)
    assert len(sheet["native_rows"]) == 2
    first, second = sheet["native_rows"]
    assert all(set(r) == ROW_FIELDS["generated_trace"] for r in sheet["native_rows"])
    assert first["sequence_keys"] == [rows(sheet)[0]["record_key"]]
    if name == "trace_unaligned_cm":
        assert first["values"]["score_bits"]["value"] == 11.17
        assert second["values"]["score_bits"]["value"] == 19.73
        assert first["values"]["structure_score_bits"]["value"] == .71
        assert first["values"]["score_bits"]["native_token"] == "11.17"
    elif name == "trace_unaligned_hmm":
        assert first["values"]["score_bits"]["value"] == 9.94
        assert second["values"]["score_bits"]["value"] == 6.14
        assert first["values"]["structure_score_bits"]["state"] == "not_measured"
        assert first["values"]["structure_score_bits"]["native_token"] == "0.00"
    else:
        assert all(v["state"] == "not_measured" for v in first["values"].values())


def test_trace_partial_and_malformed_headers_preserve_valid_sibling():
    trace=(NATIVE/"trace_unaligned_cm/traces.txt").read_text()
    first,second=trace.split("//",1)
    altered=first+"//"+second.replace("19.73", "nan").rsplit("//",1)[0]
    sheet=build_sheet((NATIVE/"trace_unaligned_cm/emitted.out").read_bytes(),trace=altered)
    assert sheet["native_rows"][0]["values"]["score_bits"]["value"] == 11.17
    assert sheet["native_rows"][1]["values"]["score_bits"]["state"] == "invalid"
    assert sheet["native_rows"][1]["values"]["score_bits"]["native_token"] == "nan"
    assert "cmemit_trace_terminator_missing" in codes(sheet)
    assert all(not r["sequence_keys"] for r in sheet["native_rows"])


def test_wrong_trace_family_is_never_linked_to_cm_generation():
    sheet=build_sheet((NATIVE/"trace_unaligned_cm/emitted.out").read_bytes(),
                     trace=(NATIVE/"trace_unaligned_hmm/traces.txt").read_bytes())
    assert "cmemit_trace_family_conflict" in codes(sheet)
    assert all(not r["sequence_keys"] for r in sheet["native_rows"])


def test_partial_fasta_preserves_finished_sibling_and_missing_population():
    sheet = build_sheet(">fixture246-sample1\nACGU\n>fixture246-sample2\nAC", complete="partial", model_complete="partial")
    assert rows(sheet)[0]["values"]["residue_count"]["value"] == 4
    assert rows(sheet)[1]["values"]["residue_count"]["state"] == "truncated"
    assert "cmemit_model_population_incomplete" in codes(sheet)


def test_partial_stockholm_and_malformed_sibling():
    first = (PRIOR/"cmemit_stockholm/emitted.out").read_text()
    second = "# STOCKHOLM 1.0\nfixture246-sample1 ACGU\nfixture246-sample2 A$\n#=GC RF xxxx\n"
    sheet = build_sheet(first + second, mode="sample_aligned", fmt="stockholm")
    assert rows(sheet)[0]["values"]["residue_count"]["value"] == 11
    assert "cmemit_stockholm_terminator_missing" in codes(sheet)
    assert "cmemit_sequence_symbols_invalid" in codes(sheet)
    assert rows(sheet)[-1]["values"]["residue_count"]["state"] == "truncated"


def test_unknown_defaults_are_not_guessed():
    sheet = build_sheet(">fixture246-sample1\nACG\n", settings={})
    assert rows(sheet)[0]["sample_index"] is None
    assert rows(sheet)[0]["alphabet"] is None
    assert "cmemit_setting_missing" in codes(sheet)


def test_invalid_payload_digest_does_not_validate_model_associations():
    content = ">fixture246-sample1\nACGU\n"
    ma_data = (PRIOR/"cmemit_fasta/model.cm").read_bytes()
    ma = artifact(ma_data,"models","infernal_cm_ascii")
    models = extract_infernal_models(ma_data, artifact=ma, format=ma["format"], engine_version="1.1.5")
    oa = artifact(content,"generated_sequences","fasta"); oa["sha256"] = "0"*64
    sheet = populate_cmemit_sheet(operation={"program":"cmemit","mode":"sample_unaligned","engine_version":"1.1.5",
        "settings":{"-N":1,"--idx":1,"--rna":True}},artifacts=[ma,oa],models=models,output={"artifact":oa,"content":content})
    assert "cmemit_payload_digest_mismatch" in codes(sheet)
    assert all(a["status"] != "validated" for a in sheet["associations"])


@pytest.mark.parametrize("settings", [{"-N": True}, {"--idx": 0}, {"--a5p": -1}, {"--dna": "yes"}])
def test_invalid_api_settings_rejected(settings):
    with pytest.raises(ValueError):
        build_sheet("", settings=settings)


def test_native_hmm_aligned_dna_discrepancy_is_not_normalized():
    sheet = build_sheet((NATIVE/"aligned_dna_hmm/emitted.out").read_bytes(), mode="sample_aligned", fmt="stockholm",
        settings={"-N": 2, "--idx": 1, "--dna": True, "--hmmonly": True})
    assert rows(sheet)[0]["sequence"] == "GCGC-UAAGCGC"
    assert rows(sheet)[0]["alphabet"] == "RNA"
    assert "cmemit_alphabet_conflict" in codes(sheet)


def test_reordered_names_do_not_use_independently_sorted_join():
    sheet = build_sheet(">fixture246-sample2\nACGU\n>fixture246-sample1\nACGU\n")
    assert all(a["status"] == "conflicting" for a in sheet["associations"])


def test_all_emission_issues_are_declared():
    sheet = build_sheet("# STOCKHOLM 2.0\nfixture246-sample1 A$\n#=GC RF x\n", mode="sample_aligned", fmt="stockholm")
    assert codes(sheet) <= ISSUE_CODES


@pytest.mark.parametrize("fmt", ["phylip","clustal","stockholm"])
def test_actual_long_interleaved_native_formats(fmt):
    folder=NATIVE/(fmt+"_long_interleaved")
    sheet=build_sheet((folder/"emitted.out").read_bytes(),mode="sample_aligned",fmt=fmt,
        model_content=(folder/"model.cm").read_bytes(),settings={"-N":2,"--idx":1,"--rna":True,"--outformat":fmt})
    assert rows(sheet,"generated_alignment")[0]["values"]["column_count"]["value"] == 74
    assert [r["values"]["residue_count"]["value"] for r in rows(sheet)] == [71,73]
    assert [r["values"]["gc_count"]["value"] for r in rows(sheet)] == [38,33]
    assert [r["values"]["gap_count"]["value"] for r in rows(sheet)] == [3,1]
    assert all(a["status"]=="validated" for a in sheet["associations"])
    assert sheet["input_records"][0]["writer_version"] == "1.1.4 | Dec 2020"


def test_alignment_native_hmm_marker_checked_against_selected_family():
    sheet=build_sheet((PRIOR/"cmemit_hmm/emitted.out").read_bytes(),mode="sample_aligned",fmt="stockholm")
    assert "cmemit_model_family_conflict" in codes(sheet)
    al=rows(sheet,"generated_alignment")[0]
    assert next(a for a in sheet["associations"] if a["output_keys"]==[al["record_key"]])["status"] == "unresolved"


@pytest.mark.parametrize("fmt,text", [("fasta","orphan sequence\n>fixture246-sample1\nACGU\n"),
    ("stockholm","# STOCKHOLM 1.0\n#=GR missing malformed\n//\n"),
    ("clustal","unrelated file\nnot a row now\n"), ("phylip","2 80\nshort\n"),
    ("phylip","2 80\nfixture246 AC\nfixture246 GU\n"), ("a2m",">fixture246-sample1\nACgu--\n>fixture246-sample2\nACG\n")])
def test_malformed_native_content_returns_structured_issues(fmt,text):
    sheet=build_sheet(text,mode="sample_unaligned" if fmt=="fasta" else "sample_aligned",fmt=fmt)
    assert any(i["severity"]=="error" for i in sheet["issues"])


def test_invalid_utf8_is_explicit_and_not_lossily_decoded():
    sheet=build_sheet(b">fixture246-sample1\nAC\xffGU\n")
    assert not rows(sheet)
    assert "cmemit_text_encoding_invalid" in codes(sheet)
