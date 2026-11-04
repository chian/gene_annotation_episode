"""Original-location, partial-data and retained-native BLAST collection checks."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import zipfile

import pytest

from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_grading_inputs import parse_blast_json


ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "verification/tool_graders_blast_collection_2026-10-26_293"
NATIVE = json.loads((PACKET / "native_fixtures/manifest.json").read_text())


def operand(name="q", length=12, **changes):
    row = dict(role="query", artifact_key="query.fa", record_ordinal=0, native_id=name,
               native_title=name, subject_ref="actual-query", molecule="protein", length=length,
               selected_interval=None, identity=None)
    row.update(changes)
    return row


def invocation(**changes):
    row = dict(execution_program="blastp", scientific_mode="database", resource_kind="hpc",
               query_kind="sequence", reference_kind="sequence", request={"exact_request": [1, None]},
               effective_options={"requested_hit_limit": 5, "requested_hsp_limit": 3, "matrix": "BLOSUM62"},
               operands=[operand()], completion={"native_returncode": 0, "producer_complete": True})
    row.update(changes)
    return row


def descriptor(key="report", format="json15", **changes):
    row = dict(artifact_key=key, role="primary_report", format=format, fields=None, delimiter=None)
    row.update(changes)
    return row


def search(name="q", **changes):
    row = {"query_id": name, "query_title": name, "query_len": 12,
           "hits": [{"num": 1, "len": 12,
                "description": [{"id": "s", "accession": "A.1", "title": "subject", "taxid": 1}],
                "hsps": [{"num": 1, "query_from": 1, "query_to": 4, "hit_from": 2, "hit_to": 5,
                          "score": 7, "bit_score": 5.5, "evalue": 0, "qseq": "AAAA", "hseq": "AAAA",
                          "align_len": 4, "identity": 4, "gaps": 0}]}]}
    row.update(changes)
    return row


def report(value=None, **changes):
    row = {"program": "blastp", "version": "BLASTP 2.17.0+", "search_target": {"db": "actualdb"},
           "params": {"expect": 10}, "results": {"search": search() if value is None else value}}
    row.update(changes)
    return {"report": row}


def collect(body=None, *, inv=None, artifact=None, raw=None):
    artifact = descriptor() if artifact is None else artifact
    return parse_blast_report_collection({artifact["artifact_key"]: raw if raw is not None else
        json.dumps(body if body is not None else {"BlastOutput2": [report()]}, allow_nan=False).encode()},
        artifacts=[artifact], invocation=invocation() if inv is None else inv)


def codes(rows):
    return {row["code"] for row in rows}


def test_exact_envelopes_original_identity_and_copied_finite_json():
    body, inv = {"BlastOutput2": [report()]}, invocation()
    row = collect(body, inv=inv)
    assert set(row) == {"schema", "invocation", "artifacts", "searches", "issues"}
    item = row["searches"][0]
    assert set(item) == {"search_key", "program_context", "stage", "iteration", "normalized", "row_map",
                         "operand_binding", "reporting", "native", "issues"}
    assert item["search_key"] == {"artifact_key": "report", "member_ordinal": None, "report_index": 0,
                                  "search_pointer": "/BlastOutput2/0/report/results/search"}
    assert item["native"]["report"] == body["BlastOutput2"][0]["report"]
    assert item["normalized"]["search"]["request"] == inv["request"]
    assert item["reporting"] == {"native_hit_array_present": True, "native_hit_count": 1,
        "requested_hit_limit": 5, "requested_hsp_limit": 3, "native_returncode": 0, "producer_complete": True}
    assert item["operand_binding"] == operand()
    body["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["score"] = 900
    inv["operands"][0]["length"] = 900
    assert item["normalized"]["hits"][0]["hsps"][0]["score"] == 7
    assert item["operand_binding"]["length"] == 12
    json.dumps(row, allow_nan=False)


def test_native_ordinals_survive_malformed_siblings_and_fields():
    native = search()
    good_hit = native["hits"][0]
    good_hit["description"] = ["bad", {"id": 5}, {"id": "real", "accession": "R.7"}]
    good_hit["hsps"] = [None, {"query_from": "bad", "score": 9}, good_hit["hsps"][0]]
    native["hits"] = [False, good_hit, "bad tail"]
    row = collect({"BlastOutput2": [report(native)]})["searches"][0]
    assert row["row_map"] == [{"hit_index": 1, "description_ordinals": [1, 2], "hsp_ordinals": [1, 2]}]
    hit = row["normalized"]["hits"][0]
    assert hit["hit_index"] == 1 and hit["descriptions"] == [{}, {"id": "real", "accession": "R.7"}]
    assert hit["hsps"][0] == {"score": 9}
    assert row["native"]["search"] == native
    assert row["reporting"]["native_hit_count"] == 3
    bad = next(issue for issue in row["issues"] if issue["code"] == "blast_hsp_field_invalid")
    assert bad["pointer"].endswith("/hits/1/hsps/1")


def test_all_original_reports_rounds_bl2seq_and_bad_search_objects_remain_located():
    iterative = report(results={"iterations": [
        {"iter_num": 1, "search": search()}, None,
        {"iter_num": 3, "search": search("q2")}, {"iter_num": 3, "search": False}]})
    second = report(results={"bl2seq": [search(), search("q2")]})
    row = collect({"BlastOutput2": [None, iterative, second]}, inv=invocation(operands=[operand(), operand("q2")]))
    keys = [item["search_key"] for item in row["searches"]]
    assert [x["report_index"] for x in keys] == [1, 1, 1, 2, 2]
    assert [x["search_pointer"] for x in keys] == [
        "/BlastOutput2/1/report/results/iterations/0/search", "/BlastOutput2/1/report/results/iterations/2/search",
        "/BlastOutput2/1/report/results/iterations/3/search", "/BlastOutput2/2/report/results/bl2seq/0",
        "/BlastOutput2/2/report/results/bl2seq/1"]
    assert [x["iteration"] for x in row["searches"]] == [1, 3, 3, None, None]
    assert "blast_iteration_number_duplicate" in codes(row["searches"][2]["issues"])
    assert "blast_search_object_required" in codes(row["searches"][2]["issues"])
    assert row["searches"][2]["native"]["report"]["results"]["iterations"][3]["search"] is False
    assert "blast_iteration_object_required" in codes(row["issues"])
    assert row["searches"][1]["operand_binding"]["native_id"] == "q2"


@pytest.mark.parametrize("program,reference,reported,geometry", [
    ("psiblast", "sequence", "psiblast", "blastp"),
    ("deltablast", "sequence", "deltablast", "blastp"),
    ("rpsblast", "profile", "rpsblast", "blastp"),
    ("rpstblastn", "profile", "rpstblastn", "blastx"),
    ("blastn_vdb", "vdb_read", "blastn", "blastn"),
    ("tblastn_vdb", "vdb_mixed", "tblastn", "tblastn"),
])
def test_source_qualified_schema_synthetic_variants_keep_identity(program, reference, reported, geometry):
    # Synthetic format-contract examples; not native variant execution claims.
    row = collect({"BlastOutput2": report(program=reported, version=reported.upper() + " 2.17.0+")},
                  inv=invocation(execution_program=program, reference_kind=reference))["searches"][0]
    assert row["normalized"]["search"]["program"] == program
    assert row["program_context"]["geometry_program"] == geometry
    assert row["native"]["report"]["program"] == reported
    assert row["search_key"]["search_pointer"].startswith("/BlastOutput2/report/")


@pytest.mark.parametrize("changes,code", [
    ({"program": "blastn"}, "blast_reported_program_conflict"),
    ({"program": ["blastp"]}, "blast_native_program_invalid"),
    ({"version": 7}, "blast_native_version_invalid"),
    ({"version": "BLASTN 2.17.0+"}, "blast_native_version_program_conflict"),
    ({"search_target": {"subjects": ["s"]}}, "blast_pairwise_database_mode_conflict"),
    ({"search_target": None}, "blast_search_target_object_invalid"),
])
def test_bad_native_context_stays_native_and_only_its_geometry_is_unresolved(changes, code):
    body = {"BlastOutput2": [report(**changes), report()]}
    items = collect(body)["searches"]
    assert items[0]["program_context"]["geometry_program"] is None
    assert code in codes(items[0]["issues"])
    assert items[0]["native"]["report"] == body["BlastOutput2"][0]["report"]
    assert items[1]["program_context"]["geometry_program"] == "blastp"
    if isinstance(changes.get("program"), str):
        assert items[0]["program_context"]["reported_program"] == changes["program"]


def test_missing_hits_zero_hits_and_failed_partial_completion_are_distinct():
    missing = search(); del missing["hits"]
    inv = invocation(completion={"native_returncode": 2, "producer_complete": False})
    items = collect({"BlastOutput2": [report(missing), report(search(hits=[])), report()]}, inv=inv)["searches"]
    assert [x["reporting"]["native_hit_count"] for x in items] == [None, 0, 1]
    assert [x["reporting"]["native_hit_array_present"] for x in items] == [False, True, True]
    assert all(x["reporting"]["native_returncode"] == 2 for x in items)
    assert all(x["reporting"]["producer_complete"] is False for x in items)


@pytest.mark.parametrize("query,operands,bound,code", [
    (search("wrong"), [operand()], False, "blast_query_binding_unavailable"),
    (search(query_id="wrong", query_title="q"), [operand()], False, "blast_query_binding_conflict"),
    (search(query_id="Query_1"), [operand()], True, None),
    (search(query_id="Query_1"), [operand(native_id="Query_2")], False, "blast_query_binding_conflict"),
    (search(query_len=11), [operand()], False, "blast_query_binding_conflict"),
    (search(), [operand(), operand(artifact_key="different.fa")], False, "blast_query_binding_ambiguous"),
    (search(), [operand(molecule="dna")], False, "blast_query_binding_conflict"),
    (search(query_len=6), [operand(selected_interval=[3, 9])], True, None),
    (search(query_id=None, query_title=None), [operand()], False, "blast_query_binding_unavailable"),
])
def test_only_actual_exact_query_names_and_compatible_lengths_bind(query, operands, bound, code):
    item = collect({"BlastOutput2": [report(query)]}, inv=invocation(operands=operands))["searches"][0]
    assert (item["operand_binding"] is not None) is bound
    if code:
        assert code in codes(item["issues"])


def archive(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, value in members:
            z.writestr(name, value if isinstance(value, bytes) else json.dumps(value).encode())
    return buffer.getvalue()


def test_archive_all_members_duplicates_malformed_siblings_and_manifest_pointers():
    raw = archive([("manifest.json", {"BlastJSON": [{"File": "one.json"}, {"File": "missing.json"}]}),
                   ("one.json", {"BlastOutput2": [report()]}), ("bad.json", b"{truncated"),
                   ("../one.json", {"BlastOutput2": [report(), report()]}), ("notes.txt", b"retained"),
                   ("one.json", {"BlastOutput2": [report()]})])
    row = collect(raw=raw, artifact=descriptor(format="json2_archive"))
    assert len(row["artifacts"][0]["members"]) == 6
    assert [s["search_key"]["member_ordinal"] for s in row["searches"]] == [1, 3, 3, 5]
    assert {"blast_native_json_invalid", "blast_archive_member_name_duplicate", "blast_archive_manifest_member_missing"} <= codes(row["issues"])
    assert all("blast_archive_member_name_duplicate" in codes(s["issues"]) for s in (row["searches"][0], row["searches"][-1]))
    assert row["artifacts"][0]["members"][4]["sha256"] == hashlib.sha256(b"retained").hexdigest()
    assert row["artifacts"][0]["members"][3]["name"] == "../one.json"


def test_unparseable_artifact_does_not_erase_another_report_or_decode_auxiliary_roles():
    descriptors = [descriptor("bad"), descriptor("good"), descriptor("pssm", role="query_pssm", format="asn1")]
    row = parse_blast_report_collection({"bad": b'{"truncated"', "good": json.dumps({"BlastOutput2": [report()]}).encode(),
                                        "pssm": b"not a JSON report"}, artifacts=descriptors, invocation=invocation())
    assert len(row["searches"]) == 1
    assert row["searches"][0]["search_key"]["artifact_key"] == "good"
    assert len(row["artifacts"]) == 3
    assert row["issues"][0]["artifact_key"] == "bad"


@pytest.mark.parametrize("raw,code", [(b'{"BlastOutput2": NaN}', "blast_collection_finite_json_required"),
    (b'{"BlastOutput2": [], "BlastOutput2": []}', "blast_native_duplicate_json_key"),
    (b'{"BlastOutput2": []}', "blast_report_collection_empty"),
    (b'{"different": {}}', "blast_report_document_layout_unsupported")])
def test_fatal_native_defects_remain_explicit_and_bytes_remain_identified(raw, code):
    result = collect(raw=raw)
    assert code in codes(result["issues"])
    assert result["artifacts"][0]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert not result["searches"]


def test_unknown_layout_and_stage_do_not_acquire_invented_semantics():
    result = collect({"BlastOutput2": [report(results={"domain_search": search()}), report(stage="made-up-stage")]})
    assert "blast_results_layout_unsupported" in codes(result["issues"])
    assert result["searches"][0]["stage"] is None
    assert "blast_native_stage_semantics_unestablished" in codes(result["searches"][0]["issues"])


FIELDS = ["qseqid", "sseqid", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq"]


def trow(query="q", subject="s", **changes):
    values = dict(zip(FIELDS, [query, subject, "12", "12", "1", "4", "1", "4", "AAAA", "AAAA"]))
    values.update(changes)
    return "\t".join(values[field] for field in FIELDS) + "\n"


def test_multisection_tabular6_custom_delimiter_and_noncontiguous_queries():
    raw = (trow() + trow("q2") + trow()).replace("\t", "@").encode()
    result = collect(raw=raw, artifact=descriptor(format="tabular6", fields=FIELDS, delimiter="@"),
                     inv=invocation(operands=[operand(), operand("q2")]))
    assert [x["search_key"]["search_pointer"] for x in result["searches"]] == ["/sections/0", "/sections/1", "/sections/2"]
    assert [x["native"]["line_numbers"] for x in result["searches"]] == [[1], [2], [3]]
    assert all(x["operand_binding"] is not None for x in result["searches"])


def test_tabular_native_row_ordinals_include_every_malformed_row():
    raw = (trow() + "malformed\n" + trow(subject="s2") + trow()).encode()
    item = collect(raw=raw, artifact=descriptor(format="tabular6", fields=FIELDS))["searches"][0]
    assert item["row_map"] == [
        {"hit_index": 0, "description_ordinals": [0], "hsp_ordinals": [0, 3]},
        {"hit_index": 1, "description_ordinals": [0], "hsp_ordinals": [2]}]
    assert item["native"]["line_numbers"] == [1, 2, 3, 4]
    assert item["reporting"]["native_hit_count"] is None
    assert item["native"]["search"]["rows"][1]["values"] == ["malformed"]


def test_tabular_rounds_zero_sections_and_original_program_case():
    header = "# PSIBLAST 2.17.0+\n# Iteration: {round}\n# Query: q\n# Database: nr\n"
    text = header.format(round=1) + "# 0 hits found\n" + header.format(round=2) + "# 1 hits found\n" + trow()
    result = collect(raw=text.encode(), artifact=descriptor(format="tabular7", fields=FIELDS),
                     inv=invocation(execution_program="psiblast"))
    assert [x["iteration"] for x in result["searches"]] == [1, 2]
    assert [x["reporting"]["native_hit_count"] for x in result["searches"]] == [0, 1]
    assert result["searches"][1]["program_context"]["reported_program"] == "PSIBLAST"
    assert result["searches"][1]["normalized"]["search"]["program"] == "psiblast"


def test_tabular_empty_is_not_a_zero_result_even_when_process_succeeded():
    empty = collect(raw=b"", artifact=descriptor(format="tabular6", fields=FIELDS))["searches"][0]
    zero = collect(raw=b"# BLASTP 2.17.0+\n# Query: q\n# 0 hits found\n",
                   artifact=descriptor(format="tabular7"))["searches"][0]
    assert empty["reporting"]["native_hit_array_present"] is False
    assert empty["reporting"]["native_hit_count"] is None and empty["operand_binding"] is None
    assert zero["reporting"]["native_hit_count"] == 0 and zero["operand_binding"] == operand()


def test_tabular_conflicting_declared_fields_do_not_reinterpret_columns():
    raw = ("# Query: q\n# Fields: subject id, query id\nq\ts\n").encode()
    item = collect(raw=raw, artifact=descriptor(format="tabular7", fields=["qseqid", "sseqid"]))["searches"][0]
    assert "blast_tabular_declared_fields_conflict" in codes(item["issues"])
    assert item["normalized"]["hits"] == []
    assert item["native"]["search"]["rows"][0]["values"] == ["q", "s"]


def test_tabular_conflicting_lengths_and_query_ids_remain_unbound():
    raw = ("# BLASTP 2.17.0+\n# Query: q\n" + trow() + trow("q2", qlen="10", slen="10")).encode()
    item = collect(raw=raw, artifact=descriptor(format="tabular7", fields=FIELDS))["searches"][0]
    assert item["operand_binding"] is None
    assert item["normalized"]["query"]["length"] is None
    assert item["normalized"]["hits"][0]["length"] is None
    assert {"blast_tabular_query_identity_conflict", "blast_tabular_query_length_conflict",
            "blast_tabular_reference_length_conflict"} <= codes(item["issues"])


@pytest.mark.parametrize("change,code", [
    (lambda a,i: a.update(fields=None, format="tabular6"), "blast_tabular_fields_required"),
    (lambda a,i: a.update(delimiter="xx"), "blast_collection_delimiter_invalid"),
    (lambda a,i: a.update(role=[]), "blast_collection_artifact_role_or_format_invalid"),
    (lambda a,i: i.update(unexpected=True), "blast_collection_invocation_fields_invalid"),
    (lambda a,i: i["effective_options"].update(requested_hit_limit=True), "blast_collection_requested_limit_invalid"),
    (lambda a,i: i["completion"].update(native_returncode=False), "blast_collection_completion_invalid"),
    (lambda a,i: i["operands"][0].update(selected_interval=[0,13]), "blast_collection_operand_interval_invalid"),
    (lambda a,i: i["operands"][0].update(identity={"namespace":"n", "value":"v"}), "blast_collection_identity_fields_invalid"),
    (lambda a,i: i["request"].update(nonfinite=float("inf")), "blast_collection_finite_json_required"),
])
def test_structural_caller_contract_failures_raise_codes(change, code):
    artifact, inv = descriptor(), invocation(); change(artifact, inv)
    with pytest.raises(ValueError, match=code):
        collect(artifact=artifact, inv=inv)


def test_artifact_custody_requires_unique_descriptors_and_exact_bytes():
    for contents, artifacts, code in [
        ({"report": b"{}"}, [descriptor(), descriptor()], "artifact_key_invalid_or_duplicate"),
        ({"report": "{}"}, [descriptor()], "artifact_bytes_required"),
        ({"other": b"{}"}, [descriptor()], "contents_descriptor_keys_conflict"),
    ]:
        with pytest.raises(ValueError, match=code):
            parse_blast_report_collection(contents, artifacts=artifacts, invocation=invocation())


@pytest.mark.parametrize("native", NATIVE, ids=[row["name"] for row in NATIVE])
def test_complete_retained_native_pair_reports(native):
    raw = (ROOT / native["path"]).read_bytes()
    result = collect(raw=raw, artifact=native["artifact"], inv=native["invocation"])
    assert not result["issues"]
    assert result["artifacts"][0]["sha256"] == native["sha256"]
    assert len(result["searches"]) == 1
    item = result["searches"][0]
    assert item["program_context"]["geometry_program"] == native["invocation"]["execution_program"]
    if raw:
        assert item["operand_binding"] == native["invocation"]["operands"][0]
        assert not item["issues"]
    else:
        assert item["reporting"]["native_hit_count"] is None
    if "blastp_multiple_hsps" in native["name"]:
        assert item["reporting"]["native_hit_count"] == 1
        assert len(item["normalized"]["hits"][0]["hsps"]) == 2
    if "blastp_gaps" in native["name"]:
        hsp = item["normalized"]["hits"][0]["hsps"][0]
        assert (hsp["align_len"], hsp["identity"], hsp["gaps"]) == (253, 238, 10)
    if "range_forward" in native["name"]:
        assert item["normalized"]["query"]["length"] == 180
        assert item["operand_binding"]["length"] == 240


def test_retained_ncbi_archive_and_existing_public_single_query_parser_unchanged():
    path = ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api/result.body"
    raw = path.read_bytes()
    old = parse_blast_json(raw, mode="database", resource="api")
    inv = invocation(resource_kind="api", operands=[operand("gene_001", old["query"]["length"])])
    result = collect(raw=raw, artifact=descriptor(format="json2_archive"), inv=inv)
    item = result["searches"][0]
    assert not result["issues"] and not item["issues"]
    assert item["normalized"]["hits"] == old["hits"]
    assert item["search_key"]["member_ordinal"] == 1
    assert item["normalized"]["native"]["archive_member"]["name"] == "DTKE1D4G016_1.json"
    assert item["operand_binding"]["native_id"] == "gene_001"
    with pytest.raises(ValueError, match="blast_single_query_report_required"):
        parse_blast_json(json.dumps({"BlastOutput2": [report(), report()]}).encode(), mode="database", resource="api")


def test_parser_has_no_execution_network_or_filesystem_access(monkeypatch):
    raw = json.dumps({"BlastOutput2": [report()]}).encode()
    def forbidden(*args, **kwargs):
        raise AssertionError("pure parser attempted external access")
    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert len(collect(raw=raw)["searches"]) == 1


def test_empty_native_collections_do_not_become_a_zero_search():
    empty = collect({"BlastOutput2": [report(results={"iterations": []})]})
    assert not empty["searches"]
    assert "blast_search_collection_empty" in codes(empty["issues"])
    empty_zip = collect(raw=archive([("notes.txt", b"only a log")]), artifact=descriptor(format="json2_archive"))
    assert not empty_zip["searches"]
    assert "blast_archive_report_missing" in codes(empty_zip["issues"])


def test_invalid_query_fields_cannot_be_repaired_by_a_matching_title():
    row = collect({"BlastOutput2": [report(search(query_id=["q"]))]})["searches"][0]
    assert row["operand_binding"] is None
    assert row["native"]["search"]["query_id"] == ["q"]
    assert "blast_query_binding_incompatible_native_identity" in codes(row["issues"])


def test_malformed_subject_row_cannot_hide_conflicting_query_length():
    raw = ("# Query: q\n" + trow() + trow(subject="", qlen="10")).encode()
    row = collect(raw=raw, artifact=descriptor(format="tabular7", fields=FIELDS))["searches"][0]
    assert row["operand_binding"] is None
    assert "blast_tabular_query_length_conflict" in codes(row["issues"])


def test_malformed_overflow_score_preserves_native_integer_and_valid_sibling():
    body = {"BlastOutput2": [report(), report()]}
    huge = 10**400
    body["BlastOutput2"][0]["report"]["results"]["search"]["hits"][0]["hsps"][0]["score"] = huge
    rows = collect(body)["searches"]
    assert "score" not in rows[0]["normalized"]["hits"][0]["hsps"][0]
    assert rows[0]["native"]["search"]["hits"][0]["hsps"][0]["score"] == huge
    assert rows[1]["normalized"]["hits"][0]["hsps"][0]["score"] == 7
    assert "blast_hsp_field_invalid" in codes(rows[0]["issues"])


def test_native_nesting_decoder_failure_does_not_abort_other_artifacts():
    artifacts = [descriptor("bad"), descriptor("good")]
    result = parse_blast_report_collection({"bad": b"[" * 10000 + b"]" * 10000,
        "good": json.dumps({"BlastOutput2": [report()]}).encode()}, artifacts=artifacts, invocation=invocation())
    assert len(result["searches"]) == 1
    assert "blast_native_json_invalid" in codes(result["issues"])
