"""Synthetic native-format fixtures; no BLAST job, API call or HPC run.

JSON field shapes follow NCBI blastxml2.asn; tabular headers/fields follow NCBI's
BLAST+ manual. These fixtures test extraction, not biological accuracy.
"""
from copy import deepcopy
import io
import json
import zipfile
from pathlib import Path

import pytest

from gene_annotation_episode.blast_grading_inputs import (
    parse_blast_json, parse_blast_tabular, STANDARD_TABULAR_FIELDS,
)


def native(*, pairwise=False):
    search = {"query_id": "Query_1", "query_title": "supplied_fragment", "query_len": 8,
        "hits": [{"num": 1, "len": 10, "description": [
            {"id": "ref|A.1|", "accession": "A.1", "title": "reported function A",
             "taxid": 562, "sciname": "Escherichia coli"},
            {"id": "ref|B.1|", "accession": "B.1", "title": "reported function B",
             "taxid": 620, "sciname": "Shigella"}],
            "hsps": [{"num": 1, "bit_score": 30.5, "score": 70, "evalue": 0.0,
                "identity": 5, "positive": 6, "gaps": 1, "align_len": 7,
                "query_from": 2, "query_to": 7, "hit_from": 1, "hit_to": 7,
                "qseq": "ACD-EFG", "hseq": "ACDWEYG", "midline": "ACD E+G"}]}],
        "stat": {"db_num": 1000, "db_len": 300000, "hsp_len": 1, "eff_space": 500000,
                 "kappa": 0.04, "lambda": 0.267, "entropy": 0.14}}
    return {"BlastOutput2": [{"report": {"program": "blastp", "version": "BLASTP 2.17.0+",
        "search_target": {"subjects": ["reference"]} if pairwise else {"db": "swissprot"},
        "params": {"matrix": "BLOSUM62", "expect": 10, "gap_open": 11, "gap_extend": 1},
        "results": {"bl2seq": [search]} if pairwise else {"search": search}}}]}


def encode(body):
    return json.dumps(body).encode()


def search(body):
    results = body["BlastOutput2"][0]["report"]["results"]
    return results.get("search", (results.get("bl2seq") or [None])[0])


def codes(result):
    return {row["code"] for row in result["issues"]}


def test_json_api_and_hpc_preserve_all_associations_and_native_measurements():
    source = native()
    raw = encode(source)
    api = parse_blast_json(raw, mode="database", resource="api")
    hpc = parse_blast_json(raw, mode="database", resource="hpc")
    assert api["hits"] == hpc["hits"]
    assert api["search"] == hpc["search"]
    assert api["resource"] != hpc["resource"]
    hit, = api["hits"]
    assert [(x["accession"], x["taxid"], x["title"]) for x in hit["descriptions"]] == [
        ("A.1", 562, "reported function A"), ("B.1", 620, "reported function B")]
    assert hit["hsps"][0]["evalue"] == 0
    assert hit["hsps"][0]["qseq"] == "ACD-EFG"
    assert api["search"]["statistics"]["db_len"] == 300000
    assert api["native"]["document"] == source
    assert api["issues"] == []


def test_zip_manifest_selects_original_payload_and_preserves_locator():
    payload = encode(native())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"BlastJSON": [{"File": "job_1.json"}]}))
        archive.writestr("job_1.json", payload)
    result = parse_blast_json(buffer.getvalue(), mode="database", resource="api")
    assert result["native"]["archive_member"] == {"ordinal": 1, "name": "job_1.json"}
    assert result["hits"][0]["descriptions"][1]["taxid"] == 620


def test_zip_without_manifest_accepts_only_one_report_payload():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("one.json", encode(native()))
        archive.writestr("other.json", json.dumps({"unrelated": True}))
    assert parse_blast_json(buffer.getvalue(), mode="database", resource="api")["search"]["reported_hit_count"] == 1


def test_pairwise_native_bl2seq_is_supported_and_has_no_database():
    result = parse_blast_json(encode(native(pairwise=True)), mode="pairwise", resource="local")
    assert result["mode"] == "pairwise" and result["search"]["database"] is None
    assert len(result["hits"]) == 1 and len(result["hits"][0]["descriptions"]) == 2


@pytest.mark.parametrize("as_pairwise,mode", [(True, "database"), (False, "pairwise")])
def test_wrong_pairwise_database_interpretation_is_rejected(as_pairwise, mode):
    with pytest.raises(ValueError, match="blast_pairwise_database_mode_conflict"):
        parse_blast_json(encode(native(pairwise=as_pairwise)), mode=mode, resource="hpc")


def test_multiple_queries_and_pairwise_subjects_are_not_silently_selected():
    body = native()
    body["BlastOutput2"].append(deepcopy(body["BlastOutput2"][0]))
    with pytest.raises(ValueError, match="blast_single_query_report_required"):
        parse_blast_json(encode(body), mode="database", resource="api")
    body = native(pairwise=True)
    search(body)["hits"].append(deepcopy(search(body)["hits"][0]))
    with pytest.raises(ValueError, match="blast_single_pairwise_subject_required"):
        parse_blast_json(encode(body), mode="pairwise", resource="local")
    body = native(pairwise=True)
    body["BlastOutput2"][0]["report"]["results"]["bl2seq"].append(deepcopy(search(body)))
    with pytest.raises(ValueError, match="blast_single_pairwise_search_required"):
        parse_blast_json(encode(body), mode="pairwise", resource="local")


def test_explicit_empty_missing_and_invalid_hits_are_distinct():
    body = native()
    search(body)["hits"] = []
    empty = parse_blast_json(encode(body), mode="database", resource="api")
    assert empty["search"]["hit_array_present"] and empty["search"]["reported_hit_count"] == 0
    del search(body)["hits"]
    missing = parse_blast_json(encode(body), mode="database", resource="api")
    assert not missing["search"]["hit_array_present"] and missing["search"]["reported_hit_count"] is None
    assert "blast_hit_array_not_reported" in codes(missing)
    search(body)["hits"] = "malformed"
    invalid = parse_blast_json(encode(body), mode="database", resource="api")
    assert "blast_hit_array_invalid" in codes(invalid)
    assert invalid["native"]["document"] == body


def test_malformed_independent_rows_preserve_valid_parts_and_originals():
    body = native()
    hit = search(body)["hits"][0]
    hit["description"] += ["bad", {"accession": "C", "taxid": 0}]
    hit["hsps"] += ["bad", {"bit_score": 10, "evalue": -1, "query_from": "one"}]
    search(body)["hits"].append(None)
    result = parse_blast_json(encode(body), mode="database", resource="api")
    assert result["search"]["reported_hit_count"] == 2
    assert len(result["hits"]) == 1 and len(result["hits"][0]["hsps"]) == 2
    assert result["hits"][0]["hsps"][0]["bit_score"] == 30.5
    assert result["hits"][0]["hsps"][1] == {"bit_score": 10}
    assert result["hits"][0]["descriptions"][-1] == {"accession": "C"}
    assert result["native"]["document"] == body
    assert {"blast_hit_object_required", "blast_description_object_required", "blast_hsp_field_invalid"} <= codes(result)


def test_request_lengths_program_and_fresh_copies_are_checked():
    request = {"program": "blastp", "query_length": 8, "hitlist_size": 50, "nested": {"x": 1}}
    saved = deepcopy(request)
    result = parse_blast_json(encode(native()), mode="database", resource="api", request=request)
    result["search"]["request"]["nested"]["x"] = 10
    assert request == saved
    with pytest.raises(ValueError, match="blast_query_length_request_conflict"):
        parse_blast_json(encode(native()), mode="database", resource="api", request={"query_length": 9})
    with pytest.raises(ValueError, match="blast_program_request_conflict"):
        parse_blast_json(encode(native()), mode="database", resource="api", request={"program": "blastn"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_json_never_reaches_numeric_sheet(value):
    body = native()
    search(body)["hits"][0]["hsps"][0]["bit_score"] = value
    with pytest.raises(ValueError, match="blast_finite_json_value_required"):
        parse_blast_json(encode(body), mode="database", resource="api")


TAB_FIELDS = ["qseqid", "saccver", "qlen", "slen", "qstart", "qend", "sstart", "send",
              "qseq", "sseq", "bitscore", "score", "evalue", "length", "nident", "gaps",
              "staxids", "sscinames", "stitle"]
TAB_VALUES = ["q1", "A.1", "8", "10", "2", "7", "1", "7", "ACD-EFG", "ACDWEYG",
              "30.5", "70", "0", "7", "5", "1", "562", "Escherichia coli", "reported function A"]


def tabular(values=TAB_VALUES, fields=TAB_FIELDS, *, header=True):
    prefix = "# BLASTP 2.17.0+\n# Query: q1 supplied_fragment\n# Database: swissprot\n"
    if header:
        prefix += "# Fields: " + ", ".join(fields) + "\n# 1 hits found\n"
    return prefix + "\t".join(values) + "\n# BLAST processed 1 queries\n"


def test_hpc_tabular_and_json_hsp_fields_agree():
    table = parse_blast_tabular(tabular(), mode="database", resource="hpc")
    output = parse_blast_json(encode(native()), mode="database", resource="api")
    assert table["query"]["length"] == output["query"]["length"] == 8
    for key in ("bit_score", "score", "evalue", "identity", "gaps", "align_len", "qseq", "hseq",
                "query_from", "query_to", "hit_from", "hit_to"):
        assert table["hits"][0]["hsps"][0][key] == output["hits"][0]["hsps"][0][key]
    assert table["hits"][0]["descriptions"][0]["taxid"] == 562
    assert table["search"]["statistics"] == {}
    assert table["native"]["rows"][0]["fields"]["evalue"] == "0"


def test_real_ncbi_display_header_names_are_recognized():
    text = ("# BLASTN 2.17.0+\n# Query: q1\n# Database: refseq_rna\n"
        "# Fields: query id, subject id, % identity, alignment length, mismatches, gap opens, "
        "q. start, q. end, s. start, s. end, evalue, bit score\n# 1 hits found\n"
        "q1\ts1\t95.000\t20\t1\t0\t1\t20\t30\t11\t1e-9\t40.1\n")
    result = parse_blast_tabular(text, mode="database", resource="hpc")
    assert result["native"]["fields"] == STANDARD_TABULAR_FIELDS
    hsp, = result["hits"][0]["hsps"]
    assert hsp["hit_from"] == 30 and hsp["hit_to"] == 11
    assert "identity" not in hsp  # Rounded percent is not an integer count.
    assert result["query"]["length"] is None


def test_headerless_tabular_requires_explicit_fields_even_for_twelve_columns():
    line = "q1\ts1\t95.000\t20\t1\t0\t1\t20\t30\t11\t1e-9\t40.1"
    with pytest.raises(ValueError, match="blast_tabular_fields_required"):
        parse_blast_tabular(line, mode="database", resource="hpc", request={"program": "blastn"})
    result = parse_blast_tabular(line, mode="database", resource="hpc", fields=["std"], request={"program": "blastn"})
    assert result["search"]["reported_hit_count"] == 1


def test_tabular_taxon_and_accession_sets_are_not_zipped():
    fields = ["qseqid", "sacc", "sallacc", "staxids", "sscinames", "salltitles", "bitscore"]
    values = ["q1", "B", "B;A", "2157;562", "Archaea;Escherichia coli", "title B<>title A", "100"]
    result = parse_blast_tabular("\t".join(values), mode="database", resource="hpc",
                                fields=fields, request={"program": "blastp"})
    hit, = result["hits"]
    assert hit["descriptions"] == [{"accession": "B"}, {"accession": "A"}]
    assert hit["unpaired_metadata"]["staxids"] == [2157, 562]
    assert hit["unpaired_metadata"]["salltitles"] == ["title B", "title A"]
    assert "blast_tabular_reference_metadata_unpaired" in codes(result)


def test_invalid_taxon_does_not_turn_a_multiple_taxon_row_into_a_single_association():
    values = list(TAB_VALUES)
    values[16] = "0;562"
    result = parse_blast_tabular(tabular(values), mode="database", resource="hpc")
    hit, = result["hits"]
    assert "taxid" not in hit["descriptions"][0]
    assert hit["unpaired_metadata"]["staxids"] == [562]
    assert hit["unpaired_metadata"]["invalid_staxids"] == ["0"]


def test_wrong_optional_json_types_are_retained_as_native_not_typed_facts():
    body = native()
    report = body["BlastOutput2"][0]["report"]
    report["version"] = 123
    report["search_target"]["db"] = {"bad": "type"}
    search(body)["hits"][0]["hsps"][0]["hit_strand"] = []
    result = parse_blast_json(encode(body), mode="database", resource="api")
    assert result["search"]["version"] is None and result["search"]["database"] is None
    assert "hit_strand" not in result["hits"][0]["hsps"][0]
    assert result["native"]["document"] == body


def test_multiple_hsps_are_one_subject_and_declared_row_count_is_not_hit_count():
    first = "\t".join(TAB_VALUES)
    second = "\t".join(TAB_VALUES[:10] + ["5", "10", "0.8"] + TAB_VALUES[13:])
    text = tabular().replace("# 1 hits found", "# 2 hits found").replace(first, first + "\n" + second)
    result = parse_blast_tabular(text, mode="database", resource="hpc")
    assert result["search"]["reported_hit_count"] == 1
    assert result["native"]["declared_alignment_row_count"] == 2
    assert len(result["hits"][0]["hsps"]) == 2


def test_bad_tabular_row_does_not_discard_a_valid_row_or_claim_complete_count():
    text = tabular().replace("# 1 hits found", "# 2 hits found") + "missing\tcolumns\n"
    result = parse_blast_tabular(text, mode="database", resource="hpc")
    assert len(result["hits"]) == 1 and len(result["hits"][0]["hsps"]) == 1
    assert result["search"]["reported_hit_count"] is None
    assert "blast_tabular_column_count_invalid" in codes(result)
    assert result["native"]["rows"][-1]["values"] == ["missing", "columns"]


def test_bad_tabular_number_keeps_native_text_and_other_numbers():
    values = list(TAB_VALUES)
    values[10], values[12] = "NaN", "-1"
    result = parse_blast_tabular(tabular(values), mode="database", resource="hpc")
    hsp = result["hits"][0]["hsps"][0]
    assert "bit_score" not in hsp and "evalue" not in hsp
    assert hsp["score"] == 70 and result["native"]["rows"][0]["fields"]["bitscore"] == "NaN"
    json.dumps(result, allow_nan=False)


def test_explicit_tabular_zero_hits_differs_from_bare_empty_file():
    text = "# BLASTP 2.17.0+\n# Query: q1\n# Database: swissprot\n# 0 hits found\n# BLAST processed 1 queries\n"
    zero = parse_blast_tabular(text, mode="database", resource="hpc")
    missing = parse_blast_tabular("", mode="database", resource="hpc", request={"program": "blastp"})
    assert zero["search"]["reported_hit_count"] == 0 and zero["search"]["hit_array_present"]
    assert missing["search"]["reported_hit_count"] is None and not missing["search"]["hit_array_present"]


def test_tabular_multiquery_and_conflicting_columns_are_rejected():
    text = tabular() + "# Query: q2\n# 0 hits found\n"
    with pytest.raises(ValueError, match="blast_single_query_report_required"):
        parse_blast_tabular(text, mode="database", resource="hpc")
    with pytest.raises(ValueError, match="blast_tabular_declared_fields_conflict"):
        parse_blast_tabular(tabular(), mode="database", resource="hpc", fields=["std"])
    changed = list(TAB_VALUES)
    changed[0] = "q2"
    with pytest.raises(ValueError, match="blast_single_query_report_required"):
        parse_blast_tabular(tabular() + "\t".join(changed), mode="database", resource="hpc")


def test_conflicting_reference_lengths_remain_unknown():
    second, third = list(TAB_VALUES), list(TAB_VALUES)
    second[3], third[3] = "20", "10"
    text = tabular() + "\t".join(second) + "\n" + "\t".join(third)
    result = parse_blast_tabular(text, mode="database", resource="hpc")
    assert result["hits"][0]["length"] is None
    assert "blast_tabular_reference_length_conflict" in codes(result)


def test_translated_native_frames_and_endpoints_are_not_converted_by_parser():
    body = native()
    report = body["BlastOutput2"][0]["report"]
    report["program"] = "blastx"
    search(body)["query_len"] = 30
    hsp = search(body)["hits"][0]["hsps"][0]
    hsp.update(query_from=20, query_to=3, query_frame=-2)
    parsed = parse_blast_json(encode(body), mode="database", resource="api")
    retained = parsed["hits"][0]["hsps"][0]
    assert (retained["query_from"], retained["query_to"], retained["query_frame"]) == (20, 3, -2)


@pytest.mark.parametrize("mode,resource", [("unknown", "api"), ("database", "invented")])
def test_invalid_context_is_rejected(mode, resource):
    with pytest.raises(ValueError):
        parse_blast_json(encode(native()), mode=mode, resource=resource)


def test_actual_blast_2_17_pairwise_json_and_tabular_outputs():
    fixtures = Path(__file__).parent / "fixtures" / "blast_grading_inputs"
    json_result = parse_blast_json((fixtures / "native_pair_result.json").read_bytes(),
                                   mode="pairwise", resource="local")
    table_result = parse_blast_tabular((fixtures / "native_pair_result.tsv").read_bytes(),
                                      mode="pairwise", resource="local")
    for result in (json_result, table_result):
        assert result["query"]["length"] == 253
        assert result["search"]["database"] is None
        assert result["search"]["version"] == "BLASTP 2.17.0+"
        assert result["issues"] == []
        hit, = result["hits"]
        assert hit["length"] == 243
        assert len(hit["hsps"]) == 1
        hsp, = hit["hsps"]
        assert (hsp["identity"], hsp["gaps"], hsp["align_len"]) == (238, 10, 253)
    for key in ("query_from", "query_to", "hit_from", "hit_to", "qseq", "hseq",
                "score", "evalue", "align_len", "identity", "positive", "gaps"):
        assert json_result["hits"][0]["hsps"][0][key] == table_result["hits"][0]["hsps"][0][key]
    with pytest.raises(ValueError, match="blast_pairwise_database_mode_conflict"):
        parse_blast_tabular((fixtures / "native_pair_result.tsv").read_bytes(),
                            mode="database", resource="local")
