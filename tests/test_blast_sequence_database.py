"""Synthetic PSI/DELTA contexts, exact source identities, retained native bytes.

These are pure adapter tests, not database searches or six-mode deployments.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import zipfile

import pytest

from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_sequence_database import (
    populate_blast_sequence_database_sheet as populate,
    calculate_blast_sequence_database_components as calculate,
)


ROOT = Path(__file__).resolve().parents[1]


def operand(**changes):
    row = dict(role="query", artifact_key="query.fa", record_ordinal=0, native_id="q",
        native_title="q", subject_ref="query", molecule="protein", length=12,
        selected_interval=[2, 10], identity=None)
    row.update(changes)
    return row


def hsp(score=20, **changes):
    row = dict(num=1, query_from=3, query_to=6, hit_from=2, hit_to=5, score=40,
        bit_score=score, evalue=0.0, qseq="ACDE", hseq="ACDE", align_len=4, identity=4, gaps=0)
    row.update(changes)
    return row


def native_search(**changes):
    row = dict(query_id="q", query_title="q", query_len=8, hits=[
        dict(num=1, len=10, description=[dict(id="A", accession="A.1", title="synthetic A", taxid=1)], hsps=[hsp()]),
        dict(num=2, len=10, description=[dict(id="B", accession="B.1", title="synthetic B", taxid=2)], hsps=[hsp(18)])])
    row.update(changes)
    return row


def document(program="psiblast", search=None, iterations=None):
    results = {"search": native_search() if search is None else search} if iterations is None else {"iterations": iterations}
    return {"BlastOutput2": [{"report": dict(program=program, version=program.upper()+" 2.17.0+",
        search_target={"db": "synthetic_db"}, params={"expect": 10}, results=results)}]}


def invocation(program="psiblast", query_kind="sequence", query=None, **changes):
    row = dict(execution_program=program, scientific_mode="database", resource_kind="hpc", query_kind=query_kind,
        reference_kind="sequence", request={"selected": "synthetic-only"},
        effective_options={"requested_hit_limit": 2, "requested_hsp_limit": 4},
        operands=[operand() if query is None else query], completion={"native_returncode": 0, "producer_complete": True})
    row.update(changes)
    return row


def collect(doc=None, inv=None, raw=None, format_name="json15", fields=None, delimiter=None):
    descriptor = dict(artifact_key="synthetic-report", role="primary_report", format=format_name, fields=fields, delimiter=delimiter)
    return parse_blast_report_collection({descriptor["artifact_key"]: raw if raw is not None else json.dumps(document() if doc is None else doc).encode()},
        artifacts=[descriptor], invocation=invocation() if inv is None else inv)


def inputs(search=None, *, collection=None):
    search = collect()["searches"][0] if search is None else search
    key = search["search_key"]
    metadata, descriptions, sequences = [], [], []
    for hit, row_map in zip(search["normalized"]["hits"], search["row_map"]):
        h = hit["hit_index"]
        for description, d in zip(hit["descriptions"], row_map["description_ordinals"]):
            index = len(metadata)
            metadata.append(dict(accession="reference-"+str(h), identifier_namespace="synthetic", source="metadata",
                native_pointer=f"/records/{index}", taxid=description.get("taxid"),
                functions=[dict(function="F" if h == 0 else "G", evidence=["supplied"])]))
            descriptions.append(dict(search_key=deepcopy(key), binding=dict(report_index=key["report_index"], hit_index=h,
                description_index=d, metadata_index=index,
                native_description={field: description.get(field) for field in ("id", "accession", "title", "taxid")},
                metadata_identifier={"namespace": "synthetic", "value": metadata[-1]["accession"]},
                metadata_source_ref="metadata", metadata_pointer=f"/records/{index}", linkage_source_ref="links", linkage_pointer=f"/links/{index}")))
        digest = hashlib.sha256(("ACDEFGHIKL" if h == 0 else "ACDEPQRSTV").encode()).hexdigest()
        sequences.append(dict(search_key=deepcopy(key), binding=dict(report_index=key["report_index"], hit_index=h,
            kind="full_sequence_digest", sequence_group="sha256:"+digest, algorithm="sha256", digest=digest,
            molecule="aa", sequence_length=10, source_ref="sequences", pointer=f"/records/{h}",
            linkage_source_ref="links", linkage_pointer=f"/sequences/{h}")))
    member = search["normalized"]["native"].get("archive_member")
    kind = search["program_context"]["query_kind"]
    query = search["operand_binding"]
    query_binding = None if query is None else dict(operand=deepcopy(query), axis_kind={"sequence":"sequence","pssm":"pssm_master","msa":"msa_master"}[kind],
        full_length=query["length"], coordinate_unit="aa", sequence_sha256="a"*64 if kind == "sequence" else None,
        pssm_key="checkpoint" if kind == "pssm" else None,
        master_mapping_ref={"source_ref":"master-input", "pointer":"/master"} if kind != "sequence" else None)
    return dict(search=search, report_source=dict(artifact_key=key["artifact_key"], artifact_ref="retained:synthetic-report",
        member_ordinal=key["member_ordinal"], member_sha256=member["sha256"] if member else None),
        search_binding=dict(search_key=deepcopy(key), stage="sequence_database", biological_round=None,
            database_identity=dict(namespace="native", value="synthetic_db", version="1", release="r1", scope="selected_sequences",
                preparation_type="sequence_database", source={"source_ref":"manifest", "pointer":"/database"}),
            input_pssm_key="checkpoint" if kind == "pssm" else None, provenance={"source_ref":"producer", "pointer":"/stage"}),
        query_binding=query_binding, reference_metadata=metadata, description_bindings=descriptions,
        sequence_identity_bindings=sequences, database_profile=dict(database="synthetic_db", release="r1", scope="selected_sequences",
            source="census", count_unit="unique_sequences", total_count=1000, function_counts={"F":200,"G":50}))


def codes(out):
    return {row["code"] for row in out["issues"]}


def test_exact_shapes_filled_numerics_and_saved_native_inputs():
    arguments = inputs()
    before = deepcopy(arguments)
    sheet = populate(**arguments)
    out = calculate(sheet)
    assert arguments == before and sheet["search"] == before["search"]
    assert set(sheet) == {"schema", "search", "report_source", "search_binding", "query_binding", "reference_metadata",
        "description_bindings", "sequence_identity_bindings", "target_context", "database_profile"}
    assert set(out) == {"schema", "search_key", "status", "components", "issues"}
    assert set(out["components"]) == {"database_sheet", "function_weights", "coordinate_context", "selected_query_coverage", "row_keys"}
    assert out["status"] == "complete"
    measured = out["components"]["database_sheet"]["hits"][0]["measurements"]
    assert measured["maximum_bit_score"] == 20 and measured["minimum_evalue"] == 0
    assert measured["observed_paired_query_positions"] == 4
    assert measured["query_paired_coverage"] == 4/12 and measured["reference_paired_coverage"] == 4/10
    assert out["components"]["coordinate_context"]["query"] == dict(axis_kind="sequence", reported_length=8, full_length=12,
        selected_interval=[2,10], coordinate_unit="aa")
    selected = out["components"]["selected_query_coverage"][0]
    assert selected == dict(row_key=out["components"]["row_keys"]["hits"][0]["row_key"], numerator=4, denominator=8,
        value=.5, unit="fraction", complete_for_reported_hsps=True, unavailable_reason=None)
    weights = out["components"]["function_weights"]
    assert weights["function_masses"] == {"F":1,"G":.25}
    assert weights["unadjusted_probabilities"] == {"F":.8,"G":.2}
    assert weights["representation_adjusted_probabilities"] == {"F":.5,"G":.5}
    assert out["components"]["database_sheet"]["normalized_result"]["search"]["program"] == "psiblast"
    assert sheet["search"]["normalized"]["query"]["length"] == 8


def test_overlaps_union_once_and_native_precision_preserved():
    native = native_search()
    native["hits"][0]["hsps"] += [hsp(19.1234567890123, query_from=5, query_to=8)]
    out = calculate(populate(**inputs(collect(document(search=native))["searches"][0])))
    assert out["components"]["database_sheet"]["hits"][0]["measurements"]["observed_paired_query_positions"] == 6
    assert out["components"]["selected_query_coverage"][0]["value"] == .75
    assert out["components"]["database_sheet"]["hits"][0]["hsp_components"][1]["native_scores"]["bit_score"] == 19.1234567890123


def test_malformed_first_hsp_and_description_leave_original_ordinals_and_partial_union():
    native = native_search()
    native["hits"][0]["description"].insert(0, False)
    native["hits"][0]["hsps"].insert(0, None)
    native["hits"].append(False)
    item = collect(document(search=native))["searches"][0]
    out = calculate(populate(**inputs(item)))
    row = out["components"]["row_keys"]["hits"][0]
    assert row["hsps"][0]["component_index"] == 0 and row["hsps"][0]["row_key"]["hsp_ordinal"] == 1
    assert row["hsps"][0]["source_locator"]["pointer"].endswith("/hits/0/hsps/1")
    assert row["descriptions"][0]["row_key"]["description_ordinal"] == 1
    assert row["descriptions"][0]["source_locator"]["pointer"].endswith("/hits/0/description/1")
    first, second, invalid = out["components"]["selected_query_coverage"]
    assert first["numerator"] == 4 and first["value"] is None and first["complete_for_reported_hsps"] is False
    assert second["value"] == .5 and invalid["unavailable_reason"] == "invalid_native_row"
    assert out["components"]["database_sheet"]["hits"][0]["measurements"]["query_paired_coverage"] is None
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"F":.8,"G":.2}


@pytest.mark.parametrize("key,value", [("artifact_key", "other"), ("member_ordinal", 7),
    ("report_index", 1), ("search_pointer", "/different/round")])
def test_every_outer_link_key_is_checked_before_legacy_linking(key, value):
    arguments = inputs()
    arguments["description_bindings"][0]["search_key"][key] = value
    arguments["sequence_identity_bindings"][0]["search_key"][key] = value
    out = calculate(populate(**arguments))
    assert "blast_sequence_database_link_search_key_mismatch" in codes(out)
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"G":1.0}
    assert out["components"]["database_sheet"]["hits"][0]["associations"][0]["functions"] == []


def test_same_report_and_hit_in_two_rounds_do_not_crosslink():
    data = collect(document(iterations=[dict(iter_num=7, search=native_search()), dict(iter_num=12, search=native_search())]))
    first, second = (inputs(search) for search in data["searches"])
    second["description_bindings"] = first["description_bindings"]
    out = calculate(populate(**second))
    assert out["components"]["function_weights"]["unadjusted_probabilities"] is None
    assert "blast_sequence_database_link_search_key_mismatch" in codes(out)
    assert second["search_binding"]["biological_round"] is None
    assert second["search"]["iteration"] == 12


def archive_collection():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("first.json", json.dumps(document()))
        archive.writestr("second.json", json.dumps(document(), indent=2))
    return collect(raw=stream.getvalue(), format_name="json2_archive")


def test_same_indices_in_different_archive_members_never_crosslink():
    data = archive_collection()
    first, second = [inputs(row) for row in data["searches"]]
    assert first["report_source"]["member_sha256"] != second["report_source"]["member_sha256"]
    second["description_bindings"] = first["description_bindings"]
    second["sequence_identity_bindings"] = first["sequence_identity_bindings"]
    out = calculate(populate(**second))
    assert out["components"]["function_weights"]["unadjusted_probabilities"] is None
    assert "blast_sequence_database_link_search_key_mismatch" in codes(out)
    row = out["components"]["row_keys"]["hits"][0]["source_locator"]
    assert row["member_ordinal"] == 1 and row["member_sha256"] == second["report_source"]["member_sha256"]


@pytest.mark.parametrize("change,code", [("absent", "blast_sequence_database_member_digest_unverifiable"),
    ("mismatch", "blast_sequence_database_member_digest_mismatch"),
    ("container", "blast_sequence_database_member_digest_mismatch")])
def test_archive_member_digest_absent_mismatch_and_container_are_distinct(change, code):
    arguments = inputs(archive_collection()["searches"][0])
    if change == "absent":
        arguments["search"]["normalized"]["native"]["archive_member"].pop("sha256")
    else:
        arguments["report_source"]["member_sha256"] = "b"*64 if change == "mismatch" else arguments["search"]["normalized"]["native"]["sha256"]
    out = calculate(populate(**arguments))
    assert code in codes(out) and out["components"]["database_sheet"] is None


@pytest.mark.parametrize("kind", ["sequence", "pssm", "msa"])
def test_query_kinds_have_exact_full_and_selected_axis_with_no_offset(kind):
    arguments = inputs(collect(inv=invocation(query_kind=kind))["searches"][0])
    out = calculate(populate(**arguments))
    assert out["components"]["coordinate_context"]["query"]["full_length"] == 12
    pair = out["components"]["database_sheet"]["hits"][0]["hsp_components"][0]["pairs"][0]
    assert pair["query_start"] == 2 and pair["query_end"] == 3
    assert out["components"]["selected_query_coverage"][0]["value"] == .5
    if kind != "sequence":
        assert "blast_sequence_database_master_biological_identity_unestablished" in codes(out)
        assert out["status"] == "partial"
    if kind == "msa":
        assert arguments["query_binding"]["pssm_key"] is None


@pytest.mark.parametrize("change", ["absent", "unbound", "same_length_other_operand", "wrong_unit", "missing_digest", "wrong_length"])
def test_missing_or_incompatible_query_preserves_native_weights_without_biological_claim(change):
    arguments = inputs()
    if change == "absent":
        arguments["query_binding"] = None
    elif change == "unbound":
        arguments["search"]["operand_binding"] = None
    elif change == "same_length_other_operand":
        arguments["query_binding"]["operand"]["artifact_key"] = "different-sequence.fa"
    elif change == "wrong_unit":
        arguments["query_binding"]["coordinate_unit"] = "nt"
    elif change == "missing_digest":
        arguments["query_binding"]["sequence_sha256"] = None
    else:
        arguments["query_binding"]["full_length"] = 13
    out = calculate(populate(**arguments))
    assert out["status"] == "partial"
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"F":.8,"G":.2}
    if change != "missing_digest":
        assert out["components"]["coordinate_context"]["query"]["full_length"] is None
        assert out["components"]["database_sheet"]["hits"][0]["measurements"]["query_paired_coverage"] is None


@pytest.mark.parametrize("kind", ["pssm", "msa"])
def test_missing_master_mapping_disables_full_denominator(kind):
    arguments = inputs(collect(inv=invocation(query_kind=kind))["searches"][0])
    arguments["query_binding"]["master_mapping_ref"] = None
    out = calculate(populate(**arguments))
    assert out["components"]["coordinate_context"]["query"]["full_length"] is None
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"F":.8,"G":.2}


def test_coordinates_outside_selection_are_not_rescued_by_offset():
    native = native_search()
    native["hits"][0]["hsps"] = [hsp(query_from=1, query_to=4)]
    out = calculate(populate(**inputs(collect(document(search=native))["searches"][0])))
    assert "blast_sequence_database_coordinates_outside_selection" in codes(out)
    assert out["components"]["selected_query_coverage"][0]["value"] is None
    assert out["components"]["database_sheet"]["hits"][0]["hsp_components"][0]["native_scores"]["bit_score"] == 20


@pytest.mark.parametrize("stage", [None, "domain_database"])
def test_delta_stage_is_not_inferred_from_execution_or_iteration(stage):
    arguments = inputs(collect(document("deltablast"), invocation("deltablast"))["searches"][0])
    arguments["search_binding"]["stage"] = stage
    sheet = populate(**arguments)
    out = calculate(sheet)
    assert out["components"]["function_weights"] is None
    assert sheet["search"]["stage"] is None
    assert sheet["search"]["normalized"]["hits"][0]["hsps"][0]["bit_score"] == 20


def test_unresolved_native_token_cannot_be_rescued_by_known_executable():
    data = document()
    data["BlastOutput2"][0]["report"]["program"] = "wrong-native-program"
    arguments = inputs(collect(data)["searches"][0])
    assert arguments["search"]["program_context"]["geometry_program"] is None
    out = calculate(populate(**arguments))
    assert out["components"]["database_sheet"] is None
    assert "blast_sequence_database_program_context_incompatible" in codes(out)


@pytest.mark.parametrize("program,reference", [("rpsblast","profile"), ("rpstblastn","profile"),
    ("blastn_vdb","vdb_read"), ("tblastn_vdb","vdb_reference")])
def test_rps_and_vdb_populations_are_incompatible(program, reference):
    reported = program.removesuffix("_vdb")
    data = collect(document(reported), invocation(program, reference_kind=reference))
    out = calculate(populate(**inputs(data["searches"][0])))
    assert out["components"]["function_weights"] is None
    assert "blast_sequence_database_target_population_incompatible" in codes(out)


def test_tabular_original_data_row_ordinals_and_description_memberships():
    fields = ["qseqid","sseqid","saccver","stitle","qlen","slen","qstart","qend","sstart","send","bitscore","qseq","sseq"]
    raw = ("# PSIBLAST 2.17.0+\n# Query: q\n# Database: synthetic_db\n"
           "malformed\nq\tA\tA.1\tfirst\t8\t10\t3\t6\t2\t5\t20\tACDE\tACDE\n"
           "q\tA\tA.1\tsecond\t8\t10\t5\t8\t2\t5\t18\tACDE\tACDE\n").encode()
    item = collect(raw=raw, format_name="tabular7", fields=fields)["searches"][0]
    out = calculate(populate(**inputs(item)))
    row = out["components"]["row_keys"]["hits"][0]
    assert row["source_locator"]["pointer"] == "/sections/0"
    assert row["source_locator"]["data_row_ordinals"] == [1,2]
    assert row["source_locator"]["line_numbers"] == [5,6]
    assert row["hsps"][0]["row_key"]["hsp_ordinal"] == 1
    assert row["hsps"][0]["component_index"] == 0
    assert row["descriptions"][0]["source_locator"]["data_row_ordinals"] == [1]
    assert row["descriptions"][1]["source_locator"]["data_row_ordinals"] == [2]
    selected = out["components"]["selected_query_coverage"][0]
    assert selected["numerator"] == 6 and selected["value"] is None
    assert selected["complete_for_reported_hsps"] is False


@pytest.mark.parametrize("change", ["no_map", "reordered_hsps", "changed_native_value", "wrong_pointer"])
def test_changed_or_absent_row_mapping_never_fabricates_a_locator(change):
    arguments = inputs()
    if change == "no_map":
        arguments["search"]["row_map"] = None
    elif change == "reordered_hsps":
        arguments["search"]["row_map"][0]["hsp_ordinals"] = [1]
    elif change == "changed_native_value":
        arguments["search"]["normalized"]["hits"][0]["hsps"][0]["bit_score"] = 999
    else:
        key = arguments["search"]["search_key"]
        key["search_pointer"] += "/wrong"
        arguments["search_binding"]["search_key"] = deepcopy(key)
    out = calculate(populate(**arguments))
    assert out["components"]["database_sheet"] is None and out["components"]["row_keys"]["hits"] == []


def test_missing_reference_length_can_use_exact_binding_but_conflict_cannot():
    data = native_search()
    data["hits"][0].pop("len")
    out = calculate(populate(**inputs(collect(document(search=data))["searches"][0])))
    reference = out["components"]["coordinate_context"]["references"][0]
    assert reference["reported_length"] is None and reference["full_length"] == 10
    arguments = inputs()
    arguments["sequence_identity_bindings"][0]["binding"]["sequence_length"] = 11
    out = calculate(populate(**arguments))
    assert out["components"]["coordinate_context"]["references"][0]["full_length"] is None
    assert out["components"]["database_sheet"]["hits"][0]["measurements"]["reference_paired_coverage"] is None
    assert "blast_sequence_binding_reference_length_mismatch" in codes(out)


@pytest.mark.parametrize("completion,expected", [({"native_returncode":0,"producer_complete":True},"no_reported_hits"),
    ({"native_returncode":1,"producer_complete":False},"unavailable"),
    ({"native_returncode":None,"producer_complete":None},"unavailable")])
def test_zero_hits_requires_actual_successful_report(completion, expected):
    item = collect(document(search=native_search(hits=[])), invocation(completion=completion))["searches"][0]
    arguments = inputs(item)
    out = calculate(populate(**arguments))
    assert out["status"] == expected
    assert out["components"]["function_weights"]["unadjusted_probabilities"] is None


def test_saved_sheet_calculation_and_population_make_no_io_or_execution(monkeypatch):
    arguments = inputs()
    saved = json.loads(json.dumps(populate(**arguments)))
    original = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("pure sheet functions cannot acquire or execute")
    with monkeypatch.context() as patch:
        for target, name in ((builtins,"open"), (io,"open"), (socket,"socket"), (socket,"create_connection"),
                (subprocess,"Popen"), (subprocess,"run"), (Path,"read_bytes"), (Path,"read_text")):
            patch.setattr(target, name, forbidden)
        assert populate(**arguments) == saved
        first = calculate(saved)
        second = calculate(saved, model={"temperature_bits":2})
    assert first["components"]["function_weights"]["unadjusted_probabilities"] == {"F":.8,"G":.2}
    assert second["components"]["function_weights"]["unadjusted_probabilities"] == {"F":2/3,"G":1/3}
    assert saved == original


@pytest.mark.parametrize("change,code", [("duplicate", "duplicate_source_binding"), ("nonfinite", "finite_json_required"),
    ("missing_key", "search_key_fields_invalid"), ("wrong_mode", "mode_required"), ("tuple", "finite_json_required")])
def test_structural_contract_failures_are_explicit(change, code):
    arguments = inputs()
    if change == "duplicate":
        arguments["description_bindings"].append(deepcopy(arguments["description_bindings"][0]))
    elif change == "nonfinite":
        arguments["reference_metadata"][0]["bad"] = float("nan")
    elif change == "missing_key":
        arguments["description_bindings"][0]["search_key"].pop("member_ordinal")
    elif change == "wrong_mode":
        arguments["search"]["program_context"]["scientific_mode"] = "pairwise"
    else:
        arguments["reference_metadata"] = tuple(arguments["reference_metadata"])
    with pytest.raises(ValueError, match=code):
        populate(**arguments)


def retained_api_inputs():
    """Actual retained database bytes; no invented query, function or census."""
    directory = ROOT / "verification/w04_blast_graders_2026-10-24_001/live_api"
    raw = (directory / "result.body").read_bytes()
    actual_request = json.loads((directory / "request.json").read_text())
    collection = parse_blast_report_collection({"retained-api-result": raw},
        artifacts=[dict(artifact_key="retained-api-result", role="primary_report", format="json2_archive", fields=None, delimiter=None)],
        invocation=dict(execution_program="blastp", scientific_mode="database", resource_kind="api", query_kind="sequence",
            reference_kind="sequence", request=actual_request, effective_options={"requested_hit_limit":50,"requested_hsp_limit":None},
            operands=[], completion={"native_returncode":None,"producer_complete":True}))
    search, = collection["searches"]
    key, member = search["search_key"], search["normalized"]["native"]["archive_member"]
    return dict(search=search, report_source=dict(artifact_key=key["artifact_key"], artifact_ref=str(directory / "result.body"),
        member_ordinal=member["ordinal"], member_sha256=member["sha256"]),
        search_binding=dict(search_key=deepcopy(key), stage="sequence_database", biological_round=None,
            database_identity=dict(namespace="ncbi_blast_database", value="swissprot", version=None, release=None, scope=None,
                preparation_type="sequence_database", source={"source_ref":str(directory / "request.json"), "pointer":"/database"}),
            input_pssm_key=None, provenance={"source_ref":str(directory / "request.json"), "pointer":""}),
        query_binding=None, reference_metadata=[], description_bindings=[], sequence_identity_bindings=[])


def test_authentic_retained_api_archive_all_hits_native_precision_and_missing_biology():
    arguments = retained_api_inputs()
    before = deepcopy(arguments)
    sheet, = [populate(**arguments)]
    out = calculate(sheet)
    assert arguments == before
    database = out["components"]["database_sheet"]
    assert len(database["hits"]) == 7
    assert [row["measurements"]["maximum_bit_score"] for row in database["hits"]] == [527.709,38.1206,32.3426,31.9574,31.5722,31.187,31.187]
    first = database["hits"][0]
    assert first["hsp_components"][0]["counts"]["identical_pairs"] == 253
    assert first["measurements"]["reference_paired_coverage"] == 1
    assert first["measurements"]["query_paired_coverage"] is None
    assert out["components"]["function_weights"]["unadjusted_probabilities"] is None
    assert out["components"]["function_weights"]["representation_adjusted_probabilities"] is None
    assert out["status"] == "partial"
    locator = out["components"]["row_keys"]["hits"][0]["source_locator"]
    assert locator["member_ordinal"] == 1
    assert locator["member_sha256"] == "e343568a2833a49ce7667779b8e9763cf9cb0229d3f24893a26cbb643e40bbe0"
    assert arguments["search"]["normalized"]["native"]["sha256"] == "38908947ffab7a09a8260c6c6933b53cd35c066a3630e5e072c61be0a51c771f"


@pytest.mark.parametrize("preparation", ["rps", "delta"])
def test_explicit_profile_database_identity_cannot_get_sequence_weights(preparation):
    arguments = inputs()
    arguments["search_binding"]["database_identity"]["preparation_type"] = preparation
    out = calculate(populate(**arguments))
    assert "blast_sequence_database_target_population_incompatible" in codes(out)
    assert out["components"]["function_weights"] is None


@pytest.mark.parametrize("field", ["query", "database"])
def test_detached_normalization_cannot_rewrite_native_context(field):
    arguments = inputs()
    if field == "query":
        arguments["search"]["normalized"]["query"]["length"] = 12
    else:
        arguments["search"]["normalized"]["search"]["database"] = "other"
    out = calculate(populate(**arguments))
    assert out["components"]["database_sheet"] is None


def test_explicit_zero_hit_table_with_title_and_no_id_is_not_missing_report():
    raw = b"# PSIBLAST 2.17.0+\n# Query: q\n# Database: synthetic_db\n# 0 hits found\n"
    item = collect(raw=raw, format_name="tabular7")["searches"][0]
    out = calculate(populate(**inputs(item)))
    assert out["status"] == "no_reported_hits"
    assert out["components"]["selected_query_coverage"] == []


def test_saved_table_calculation_needs_no_io_or_process(monkeypatch):
    fields = ["qseqid","sseqid","qlen","slen","qstart","qend","sstart","send","bitscore","qseq","sseq"]
    raw = b"q\tA\t8\t10\t3\t6\t2\t5\t20\tACDE\tACDE\n"
    sheet = populate(**inputs(collect(raw=raw, format_name="tabular6", fields=fields)["searches"][0]))
    def forbidden(*args, **kwargs):
        raise AssertionError("saved table must be pure")
    with monkeypatch.context() as patch:
        for obj, field in ((builtins,"open"),(io,"open"),(socket,"socket"),(subprocess,"Popen")):
            patch.setattr(obj,field,forbidden)
        out = calculate(sheet)
    assert out["components"]["selected_query_coverage"][0]["value"] == .5


def test_conflicting_reference_binding_does_not_remove_native_bounds_validation():
    native = native_search()
    native["hits"][0]["hsps"] = [hsp(hit_from=9, hit_to=12)]
    arguments = inputs(collect(document(search=native))["searches"][0])
    arguments["sequence_identity_bindings"][0]["binding"]["sequence_length"] = 12
    out = calculate(populate(**arguments))
    first = out["components"]["database_sheet"]["hits"][0]
    assert first["measurements"]["maximum_bit_score"] == 20
    assert first["hsp_components"][0]["geometry_available"] is False
    assert first["hsp_components"][0]["pairs"] == []
    assert "coordinates_outside_operand" in codes(out)


@pytest.mark.parametrize("layout,code,status", [
    (None,"blast_sequence_database_table_layout_unavailable","unavailable"),
    ({},"blast_sequence_database_table_layout_invalid","incompatible"),
    ({"format":"tabular6","declared_fields":None,"delimiter":"\t"},"blast_sequence_database_table_layout_invalid","incompatible"),
    ({"format":"tabular7","declared_fields":[],"delimiter":"\t"},"blast_sequence_database_table_layout_invalid","incompatible"),
    ({"format":"tabular7","declared_fields":None,"delimiter":"\n"},"blast_sequence_database_table_layout_invalid","incompatible"),
])
def test_missing_invalid_table_layout_never_guessed(layout, code, status):
    fields = ["qseqid","sseqid","qlen","slen","qstart","qend","sstart","send","bitscore","qseq","sseq"]
    raw = b"q\tA\t8\t10\t3\t6\t2\t5\t20\tACDE\tACDE\n"
    arguments = inputs(collect(raw=raw, format_name="tabular6", fields=fields)["searches"][0])
    if layout is None:
        arguments["search"]["normalized"]["native"].pop("table_layout")
    else:
        arguments["search"]["normalized"]["native"]["table_layout"] = layout
    out = calculate(populate(**arguments))
    assert code in codes(out) and out["status"] == status
    assert out["components"]["database_sheet"] is None


def test_exact_custom_delimiter_and_literal_hash_preserve_table6_sections():
    fields = ["qseqid","sseqid","stitle","qlen","slen","qstart","qend","sstart","send","bitscore","qseq","sseq"]
    raw = b"q@A@literal # title@8@10@3@6@2@5@20@ACDE@ACDE\nq2@B@other title@8@10@3@6@2@5@18@ACDE@ACDE\n"
    inv = invocation(operands=[operand(),operand(native_id="q2",native_title="q2",record_ordinal=1)])
    data = collect(raw=raw, inv=inv, format_name="tabular6", fields=fields, delimiter="@")
    assert len(data["searches"]) == 2
    for section, search in enumerate(data["searches"]):
        out = calculate(populate(**inputs(search)))
        assert out["components"]["selected_query_coverage"][0]["value"] == .5
        locator = out["components"]["row_keys"]["hits"][0]["descriptions"][0]["source_locator"]
        assert locator["pointer"] == f"/sections/{section}"
        assert locator["line_numbers"] == [section+1]


def test_conflicting_table_delimiter_cannot_make_a_new_field_mapping():
    fields = ["qseqid","sseqid","qlen","slen","qstart","qend","sstart","send","bitscore","qseq","sseq"]
    raw = b"q@A@8@10@3@6@2@5@20@ACDE@ACDE\n"
    arguments = inputs(collect(raw=raw, format_name="tabular6", fields=fields, delimiter="@")["searches"][0])
    arguments["search"]["normalized"]["native"]["table_layout"]["delimiter"] = "\t"
    out = calculate(populate(**arguments))
    assert out["components"]["database_sheet"] is None
    assert "blast_sequence_database_native_table_conflict" in codes(out)


@pytest.mark.parametrize("outer_kind", ["list", "object"])
def test_report_index_must_identify_the_report_selected_by_the_native_pointer(outer_kind):
    doc = document()
    if outer_kind == "list":
        # Identical report contents cannot make their original indices interchangeable.
        doc["BlastOutput2"].append(deepcopy(doc["BlastOutput2"][0]))
    else:
        doc["BlastOutput2"] = doc["BlastOutput2"][0]
    search = collect(doc)["searches"][0]
    search["search_key"]["report_index"] = 1
    sheet = populate(**inputs(search))
    out = calculate(sheet)
    assert out["status"] == "incompatible"
    assert "blast_sequence_database_native_report_index_conflict" in codes(out)
    assert out["components"]["database_sheet"] is None
    assert out["components"]["row_keys"]["hits"] == []
    assert sheet["search"] == search


@pytest.mark.parametrize("outer_kind,index", [("list", 1), ("object", 0)])
def test_exact_native_report_index_and_pointer_remain_usable(outer_kind, index):
    doc = document()
    if outer_kind == "list":
        doc["BlastOutput2"].append(deepcopy(doc["BlastOutput2"][0]))
    else:
        doc["BlastOutput2"] = doc["BlastOutput2"][0]
    out = calculate(populate(**inputs(collect(doc)["searches"][index])))
    assert out["status"] == "complete"
    locator = out["components"]["row_keys"]["hits"][0]["source_locator"]
    assert locator["report_index"] == index
    assert locator["search_key"] == out["search_key"]
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"F": .8, "G": .2}


@pytest.mark.parametrize("key,value", [("report_index", 1), ("member_ordinal", 0)])
def test_table_search_key_cannot_gain_a_report_or_archive_member(key, value):
    fields = ["qseqid","sseqid","qlen","slen","qstart","qend","sstart","send","bitscore","qseq","sseq"]
    raw = b"q\tA\t8\t10\t3\t6\t2\t5\t20\tACDE\tACDE\n"
    search = collect(raw=raw, format_name="tabular6", fields=fields)["searches"][0]
    search["search_key"][key] = value
    if key == "member_ordinal":
        # Even a mutually matching supplied member descriptor cannot invent a
        # table archive path that the original collector did not produce.
        search["normalized"]["native"]["archive_member"] = dict(ordinal=value, name="table.tsv", sha256="b" * 64)
    sheet = populate(**inputs(search))
    out = calculate(sheet)
    assert out["status"] == "incompatible"
    assert "blast_sequence_database_table_search_key_conflict" in codes(out)
    assert out["components"]["database_sheet"] is None
    assert out["components"]["row_keys"]["hits"] == []
    assert sheet["search"] == search


@pytest.mark.parametrize("index", ["00", "+0", "-1"])
def test_native_iteration_array_index_stays_canonical(index):
    search = collect(document(iterations=[dict(iter_num=1, search=native_search())]))["searches"][0]
    search["search_key"]["search_pointer"] = f"/BlastOutput2/0/report/results/iterations/{index}/search"
    out = calculate(populate(**inputs(search)))
    assert out["components"]["database_sheet"] is None
    assert out["components"]["row_keys"]["hits"] == []
    assert "blast_sequence_database_native_row_validation_unavailable" in codes(out)


def fasta_inputs(program="blastp"):
    """Direct already-qualified rows; no claim to M's byte/proof qualification."""
    from gene_annotation_episode.blast_search import PROGRAM_UNITS
    geometry = "blastp" if program in ("psiblast", "deltablast") else program
    qunit, runit, aligned_unit = PROGRAM_UNITS[geometry]
    qstep = 3 if qunit == "nt" and aligned_unit == "aa" else 1
    rstep = 3 if runit == "nt" and aligned_unit == "aa" else 1
    native = native_search(query_len=8*qstep)
    for row in native["hits"]:
        row["len"] = 10*rstep
        for h in row["hsps"]:
            h.update(query_from=2*qstep+1, query_to=6*qstep, hit_from=rstep+1, hit_to=5*rstep)
            if qstep == 3:
                h["query_frame"] = 1
            if rstep == 3:
                h["hit_frame"] = 1
            if aligned_unit == "nt":
                h.update(qseq="ACGT", hseq="ACGT")
    query = operand(molecule="protein" if qunit == "aa" else "dna", length=12*qstep,
                    selected_interval=[2*qstep, 10*qstep])
    search = collect(document(program, search=native), invocation(program, query=query))["searches"][0]
    arguments = inputs(search)
    arguments["query_binding"]["coordinate_unit"] = qunit
    arguments["database_profile"]["function_counts"] = {"F":100, "G":10}
    for i, row in enumerate(arguments["reference_metadata"]):
        row.update(source="original-full-fasta", native_pointer="",
                   record_locator={"kind":"fasta_record", "record_ordinal":i})
        row["functions"][0]["source"] = "separate-explicit-functions-json"
        description = arguments["description_bindings"][i]["binding"]
        description.update(metadata_source_ref=row["source"], metadata_pointer="",
                           metadata_record_locator=deepcopy(row["record_locator"]))
        sequence = arguments["sequence_identity_bindings"][i]["binding"]
        symbols = ("ACDEFGHIKL" if i == 0 else "ACDEPQRSTV") if runit == "aa" else (
            "ACGTACGTAA" if i == 0 else "ACGTCCGTAA") * rstep
        digest = hashlib.sha256(symbols.encode()).hexdigest()
        sequence.update(source_ref=row["source"], pointer="", record_locator=deepcopy(row["record_locator"]),
                        molecule=runit, sequence_length=len(symbols), digest=digest, sequence_group="sha256:"+digest)
    return arguments


@pytest.mark.parametrize("program", ["blastn", "blastp", "blastx", "tblastn", "tblastx", "psiblast", "deltablast"])
def test_v2_all_sequence_modes_preserve_geometry_reference_units_and_kernel(program):
    arguments = fasta_inputs(program)
    sheet = populate(**arguments)
    out = calculate(sheet)
    assert sheet["schema"] == "blast_sequence_database_result_sheet_v2"
    assert out["schema"] == "blast_sequence_database_result_components_v1"
    assert out["status"] == "complete"
    database = out["components"]["database_sheet"]
    assert database["schema"] == "blast_database_sheet_v2" and database["association_mode"] == "explicit_bindings_v2"
    assert database["coverage"]["matched_metadata_row_count"] == 2
    for hit in database["hits"]:
        assert hit["hsp_components"][0]["geometry_available"]
        assert hit["measurements"]["query_paired_coverage"] == 4/12
        assert hit["measurements"]["reference_paired_coverage"] == 4/10
    reference = out["components"]["coordinate_context"]["references"][0]
    expected = arguments["sequence_identity_bindings"][0]["binding"]
    assert reference["coordinate_unit"] == expected["molecule"]
    assert reference["full_length"] == expected["sequence_length"]
    assert out["components"]["selected_query_coverage"][0]["value"] == .5
    weights = out["components"]["function_weights"]
    assert weights["unadjusted_probabilities"] == {"F":.8, "G":.2}
    assert weights["representation_adjusted_probabilities"] == {"F":pytest.approx(2/7), "G":pytest.approx(5/7)}
    assert calculate(sheet, model={"temperature_bits":2})["components"]["function_weights"]["unadjusted_probabilities"] == {"F":2/3, "G":1/3}


@pytest.mark.parametrize("program", ["tblastn", "tblastx"])
def test_translated_reference_traceback_never_supplies_nt_full_identity(program):
    arguments = fasta_inputs(program)
    arguments["sequence_identity_bindings"][0]["binding"].update(molecule="aa", sequence_length=10)
    out = calculate(populate(**arguments))
    assert "blast_sequence_binding_reference_molecule_mismatch" in codes(out)
    first = out["components"]["coordinate_context"]["references"][0]
    assert first["coordinate_unit"] == "nt" and first["reported_length"] == 30 and first["full_length"] is None
    assert out["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20


def test_v2_mixed_original_rows_keep_partial_metadata_and_original_positions():
    arguments = fasta_inputs()
    for field in ("reference_metadata", "description_bindings", "sequence_identity_bindings"):
        arguments[field][0] = inputs(arguments["search"])[field][0]
    before = deepcopy(arguments)
    sheet = populate(**arguments)
    out = calculate(sheet)
    assert arguments == before and sheet["reference_metadata"] == before["reference_metadata"]
    assert "record_locator" not in sheet["reference_metadata"][0]
    assert "native_record" not in sheet["reference_metadata"][1]
    assert out["components"]["database_sheet"]["coverage"]["matched_metadata_row_count"] == 2
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"F":.8, "G":.2}


def test_explicit_null_locator_opts_in_without_rewriting_v1_rows():
    arguments = inputs()
    arguments["reference_metadata"][0]["record_locator"] = None
    sheet = populate(**arguments)
    assert sheet["schema"] == "blast_sequence_database_result_sheet_v2"
    assert "metadata_record_locator" not in sheet["description_bindings"][0]["binding"]
    assert calculate(sheet)["components"]["function_weights"]["unadjusted_probabilities"] == {"F":.8, "G":.2}


@pytest.mark.parametrize("field", ["reference_metadata", "description_bindings", "sequence_identity_bindings"])
def test_saved_v1_rejects_new_association_fields_instead_of_upgrading(field):
    sheet = populate(**inputs())
    row = sheet[field][0] if field == "reference_metadata" else sheet[field][0]["binding"]
    row["metadata_record_locator" if field == "description_bindings" else "record_locator"] = None
    with pytest.raises(ValueError, match="record_locator_requires_v2_sheet|inner_binding_fields_invalid"):
        calculate(sheet)


def test_declared_saved_v2_is_not_downgraded_after_filtering_or_missing_extended_rows():
    sheet = populate(**inputs())
    sheet["schema"] = "blast_sequence_database_result_sheet_v2"
    out = calculate(sheet)
    assert out["components"]["database_sheet"]["schema"] == "blast_database_sheet_v2"
    arguments = inputs()
    arguments["sequence_identity_bindings"][0]["binding"].update(record_locator=None, molecule="nt")
    filtered = calculate(populate(**arguments))
    assert filtered["components"]["database_sheet"]["schema"] == "blast_database_sheet_v2"


@pytest.mark.parametrize("field", ["reference_metadata", "description_bindings", "sequence_identity_bindings"])
@pytest.mark.parametrize("locator", [{}, {"kind":"fasta_record", "record_ordinal":True},
    {"kind":"fasta_record", "record_ordinal":-1}, {"kind":"fasta_record", "record_ordinal":0, "extra":None}])
def test_v2_locators_are_closed_at_all_declared_locations(field, locator):
    arguments = fasta_inputs()
    row = arguments[field][0] if field == "reference_metadata" else arguments[field][0]["binding"]
    row["metadata_record_locator" if field == "description_bindings" else "record_locator"] = locator
    with pytest.raises(ValueError, match="^blast_record_locator_invalid$"):
        populate(**arguments)


@pytest.mark.parametrize("field,pointer", [("reference_metadata","native_pointer"),
    ("description_bindings","metadata_pointer"), ("sequence_identity_bindings","pointer")])
def test_v2_fasta_records_cannot_use_json_pointers(field, pointer):
    arguments = fasta_inputs()
    row = arguments[field][0] if field == "reference_metadata" else arguments[field][0]["binding"]
    row[pointer] = "/records/0"
    with pytest.raises(ValueError, match="^record_locator_pointer_conflict$"):
        populate(**arguments)


@pytest.mark.parametrize("field", ["description_bindings", "sequence_identity_bindings"])
def test_v2_binding_extensions_remain_exact_shapes_and_exact_duplicates_fail(field):
    arguments = fasta_inputs()
    arguments[field][0]["binding"]["unexpected"] = None
    with pytest.raises(ValueError, match="^blast_sequence_database_inner_binding_fields_invalid$"):
        populate(**arguments)
    arguments = fasta_inputs()
    arguments[field].append(deepcopy(arguments[field][0]))
    with pytest.raises(ValueError, match="^blast_sequence_database_duplicate_source_binding$"):
        populate(**arguments)


def test_v2_wrong_cross_record_description_is_local_with_original_native_measurements():
    arguments = fasta_inputs()
    # Keep the second hit valid while making only the first metadata locator
    # disagree with its explicit description binding.
    arguments["description_bindings"][0]["binding"]["metadata_record_locator"]["record_ordinal"] = 1
    out = calculate(populate(**arguments))
    assert "blast_description_binding_metadata_provenance_mismatch" in codes(out)
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"G":1.0}
    assert out["components"]["database_sheet"]["hits"][0]["measurements"]["maximum_bit_score"] == 20
    assert out["components"]["selected_query_coverage"][0]["value"] == .5


def test_v2_population_and_parameter_recalculation_are_pure_and_do_not_reprove_fasta(monkeypatch):
    arguments = fasta_inputs()
    saved = json.loads(json.dumps(populate(**arguments)))
    before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("scientific functions cannot acquire or reprove a source file")
    with monkeypatch.context() as patch:
        for target, name in ((builtins,"open"), (io,"open"), (socket,"socket"), (socket,"create_connection"),
                (subprocess,"Popen"), (subprocess,"run"), (Path,"read_bytes"), (Path,"read_text")):
            patch.setattr(target,name,forbidden)
        patch.setattr("gene_annotation_episode.blast_fasta_record_identity.parse_blast_fasta_source_records", forbidden)
        patch.setattr("gene_annotation_episode.domain.parse_sequences", forbidden)
        patch.setattr("gene_annotation_episode.blast_grading_inputs.parse_blast_json", forbidden)
        patch.setattr("gene_annotation_episode.blast_report_collection.parse_blast_report_collection", forbidden)
        assert populate(**arguments) == saved
        out = calculate(saved, model={"temperature_bits":2})
    assert saved == before
    assert out["components"]["function_weights"]["unadjusted_probabilities"] == {"F":2/3, "G":1/3}


def test_native_payload_locator_text_never_dispatches_a_sheet_version():
    arguments = inputs()
    arguments["reference_metadata"][0]["native_record"] = {"record_locator":False}
    arguments["reference_metadata"][0]["functions"][0]["evidence"] = [{"record_locator":False}]
    assert populate(**arguments)["schema"] == "blast_sequence_database_result_sheet_v1"


@pytest.mark.parametrize("program", ["psiblast", "deltablast"])
def test_iteration_dependency_keeps_v2_fields_and_calls_the_public_calculator_once(program, monkeypatch):
    """Existing saved-data dependency only; no M/worker/episode-path claim."""
    from gene_annotation_episode import blast_sequence_database as public
    from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
    from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components

    arguments = fasta_inputs(program)
    key = arguments["search"]["search_key"]
    collection = collect(document(program), invocation(program))
    collection["searches"] = [deepcopy(arguments["search"])]
    metadata = dict(search_key=deepcopy(key), **{k:deepcopy(arguments[k]) for k in
        ("reference_metadata", "description_bindings", "sequence_identity_bindings", "database_profile")})
    sheet = populate_blast_iteration_sheet(collection,
        report_sources=[dict(search_key=deepcopy(key), report_source=arguments["report_source"])],
        query_bindings=[dict(search_key=deepcopy(key), query_binding=arguments["query_binding"])],
        search_bindings=[arguments["search_binding"]], pssm_sheets=[], checkpoint_bindings=[],
        sequence_metadata=[metadata], profile_metadata=[], comparison_pairs=[], inclusion_records=[],
        convergence_records=[], invocation_source={"source_ref":"explicit-invocation", "pointer":""})
    calls = []
    original = public.calculate_blast_sequence_database_components
    def counted(child_sheet, *, model=None):
        calls.append(deepcopy(child_sheet))
        return original(child_sheet, model=model)
    monkeypatch.setattr(public, "calculate_blast_sequence_database_components", counted)
    out = calculate_blast_iteration_components(sheet, sequence_model={"temperature_bits":2})
    assert len(calls) == 1 and calls[0]["schema"] == "blast_sequence_database_result_sheet_v2"
    assert sheet["sequence_metadata"] == [metadata]
    result = out["searches"][0]["sequence_components"]
    assert result["components"]["database_sheet"]["schema"] == "blast_database_sheet_v2"
    assert result["components"]["function_weights"]["unadjusted_probabilities"] == {"F":2/3,"G":1/3}


@pytest.mark.parametrize("returncode,producer,execution_state,producer_state,success", [
    (0, True, "completed", "complete", .5),
    (None, None, "unknown", "unknown", None),
])
def test_common_population_forwards_only_supplied_reporting_facts(returncode, producer, execution_state, producer_state, success):
    arguments = inputs()
    arguments["search"]["reporting"].update(native_returncode=returncode, producer_complete=producer)
    sheet = populate(**arguments)
    before = deepcopy(sheet)
    output = calculate(sheet, _retain_correspondence=True)
    companion = output.pop("correspondence")
    assert output == calculate(sheet)
    assert sheet == before
    instance = companion["instances"][0]
    assert instance["sheet"]["population"]["execution_state"] == execution_state
    assert instance["sheet"]["population"]["producer_state"] == producer_state
    assert instance["components"]["selected"]["query"]["execution_success_value"] == success
    database = output["components"]["database_sheet"]
    assert database["calculation_context"]["reporting"] == before["search"]["reporting"]
    assert output["components"]["selected_query_coverage"][0]["value"] == .5
    assert database["hits"][0]["measurements"]["maximum_bit_score"] == 20
