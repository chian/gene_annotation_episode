"""R1 shared HSP publication/read regressions; synthetic native inputs, no search.

The actual NCBIBlastService publisher and requested facts are used. Selected
column analysis is distinct; it must reuse the retained whole-HSP component.
"""
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import zipfile

import pytest

from gene_annotation_episode import blast_graders, blast_pairwise_grader, blast_search
from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.blast_database_grader import build_database_sheet, calculate_database_probabilities
from gene_annotation_episode.blast_hsp_site_calculators import calculate_blast_hsp_column_components
from gene_annotation_episode.blast_result_views import BLAST_HSP_FACT_SCHEMA, blast_hsp_facts, read_blast_hsp
from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry


def hsp(**changes):
    return {"query_from": 1, "query_to": 4, "hit_from": 1, "hit_to": 4,
        "qseq": "ACGT", "hseq": "AGGT", "identity": 4, "align_len": 4,
        "bit_score": 12.5, "score": 25, "evalue": 0, **changes}


def snapshot(content, request=None):
    return SourceSnapshot("ncbi_blast", "https://example.invalid/retained-only",
        request or {}, "2026-10-27T00:00:00Z", content, "application/json", {})


def publish(store, native=None, *, hits=None, query="ACGT", program="blastn",
            reference_length=4, archive=False, missing_hits=False):
    target, = store.create_problem(raw_sequence=query,
        molecule="protein" if program in ("blastp", "tblastn") else "dna")["subject_refs"]
    search = {"query_title": target, "query_len": len(query), "hits": hits if hits is not None else [
        {"len": reference_length, "description": [{"accession": "REFERENCE.1"}],
         "hsps": [native if native is not None else hsp()]}]}
    if missing_hits:
        search.pop("hits")
    body = {"BlastOutput2": [{"report": {"program": program,
        "search_target": {"db": "synthetic_database"}, "results": {"search": search}}}]}
    content = json.dumps(body).encode()
    if archive:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as bundle:
            bundle.writestr("manifest.json", json.dumps({"BlastJSON": [{"File": "one.json"}]}))
            bundle.writestr("one.json", content)
        content = output.getvalue()
    tools = ToolRegistry(store)
    outcome = NCBIBlastService(tools).publish({"subject_ref": target, "program": program,
        "database": "synthetic_database"}, {}, snapshot(content), None, "selected-publish",
        submission_snapshot=snapshot(b"RID = ORIGINAL_502\nRTOE = 0\n"),
        handle={"rid": "ORIGINAL_502", "rtoe_seconds": 0})
    return tools, outcome


def numeric(observation):
    return {item["name"]: item["value"]["value"] for item in observation["measurements"]
            if item["value"]["type"] == "number"}


def retained(store, outcome):
    grading, = source_tool_gradings(store, outcome["result"]["source_ref"])
    return grading


def blocked(*args, **kwargs):
    raise AssertionError("unexpected recalculation, acquisition or execution")


@pytest.mark.parametrize("archive", [False, True])
def test_mismatch_actual_publisher_reader_requested_return_and_saved_recalculation(tmp_path, monkeypatch, archive):
    count = []
    original = blast_pairwise_grader.alignment_components
    def counted(*args, **kwargs):
        count.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(blast_pairwise_grader, "alignment_components", counted)
    with Store(tmp_path / "store") as store:
        _, outcome = publish(store, archive=archive)
        assert outcome["status"] == "completed", outcome
        assert len(count) == 1
        observation = store.get(outcome["result"]["records"][0]["observation_ref"])
        grading = retained(store, outcome)
        component = grading["sheet"]["hits"][0]["hsp_components"][0]
        assert component["reported_counts"]["identity"] == 4
        assert component["counts"]["identical_pairs"] == 3
        assert numeric(observation)["identity_fraction"] == component["fractions"]["alignment_identity"] == .75
        conflict = {"code": "reported_count_traceback_conflict", "field": "identity", "reported": 4, "calculated": 3}
        assert conflict in component["issues"]
        assert observation["native_blast"]["shared_projection"]["native_artifact_ref"] == store.get(observation["source_ref"])["artifact_ref"]
        with monkeypatch.context() as patch:
            patch.setattr(blast_pairwise_grader, "alignment_components", blocked)
            patch.setattr(blast_graders, "grade_blast_result", blocked)
            patch.setattr(socket, "socket", blocked)
            patch.setattr(subprocess, "Popen", blocked)
            view = read_blast_hsp(store, observation["id"], 0, 4, permitted_inputs=[observation["id"]], scope=None)
            facts = blast_hsp_facts(store, outcome["record_refs"])
            assert numeric(view)["identity_fraction"] == facts[0]["identity_fraction"] == .75
            assert view["reported_counts"]["identity"] == 4 and conflict in view["hsp_component_issues"]
            site = json.loads(store.get_artifact(view["site_grading_artifact_ref"]))["grading"]
            assert site["sheet"]["whole_hsp_input"]["component"] == component
            assert calculate_blast_hsp_column_components(site["sheet"]) == site["scores"]
            assert calculate_database_probabilities(grading["sheet"]) == grading["probabilities"]
        schema = {"type": "object", "additionalProperties": False, "required": ["matches"],
            "properties": {"matches": {**deepcopy(BLAST_HSP_FACT_SCHEMA), "x-source": "execution_blast_hsps"}}}
        form = form_with_facts({}, schema, {"execution_blast_hsps": facts})
        validate_form(form, schema, lambda ref, ns: ns == "execution_result" and ref in outcome["record_refs"])
        assert build_database_sheet(json.loads(json.dumps(grading["sheet"]["normalized_result"]))) == grading["sheet"]
        if directory := os.environ.get("BLAST502_ATTEMPT"):
            (Path(directory) / ("mismatch_zip.json" if archive else "mismatch_direct.json")).write_text(json.dumps({
                "source_ref": observation["source_ref"], "binding": observation["native_blast"]["shared_projection"],
                "reported_identity": 4, "calculated_identical_pairs": 3, "published": numeric(observation),
                "reader": numeric(view), "requested_return": form, "issues": component["issues"],
                "whole_hsp_calculator_calls_during_publication": 1,
                "whole_hsp_calculator_calls_during_read": 0}, indent=2) + "\n")


def test_span_and_paired_denominators_are_distinct(tmp_path):
    with Store(tmp_path / "store") as store:
        _, result = publish(store, hsp(qseq="AC-GT", hseq="ACAGT", align_len=5, hit_to=5), reference_length=5)
        component = retained(store, result)["sheet"]["hits"][0]["hsp_components"][0]
        fractions = component["fractions"]
        assert fractions["query_span_coverage"] == fractions["reference_span_coverage"] == 1
        assert fractions["query_paired_coverage"] == fractions["paired_identity"] == 1
        assert fractions["reference_paired_coverage"] == fractions["alignment_identity"] == .8
        fact, = blast_hsp_facts(store, result["record_refs"])
        assert fact["query_coverage"] == fact["target_coverage"] == 1 and fact["identity_fraction"] == .8


def test_original_addresses_survive_malformed_predecessors_and_equal_siblings(tmp_path):
    hits = ["malformed_hit", {"len": 4, "description": [{"accession": "REFERENCE.1"}],
        "hsps": ["malformed_hsp", hsp(), hsp(qseq="TGCA", hseq="TCCA")]}]
    with Store(tmp_path / "store") as store:
        _, outcome = publish(store, hits=hits)
        assert outcome["status"] == "partial" and outcome["result"]["projected_hsp_count"] == 2
        grading = retained(store, outcome)
        assert grading["sheet"]["hits"][0]["hsp_source_map"] == [
            {"hit_index": 1, "hsp_index": 1}, {"hit_index": 1, "hsp_index": 2}]
        for row, expected, compact in zip(outcome["result"]["records"], ("ACGT", "TGCA"), (0, 1)):
            marker = row["native_blast"]
            assert marker["hit_ordinal"] == 1 and marker["hsp_ordinal"] == compact + 1
            assert marker["shared_projection"]["hit_row"] == 0
            assert marker["shared_projection"]["hsp_row"] == compact
            view = read_blast_hsp(store, row["observation_ref"], 0, 4, permitted_inputs=[row["observation_ref"]], scope=None)
            assert view["alignment"]["query"] == expected
        assert [row["identity_fraction"] for row in blast_hsp_facts(store, outcome["record_refs"])] == [.75, .75]
        original = store.get(outcome["result"]["records"][0]["observation_ref"])
        changed = {key: deepcopy(value) for key, value in original.items() if key not in ("id", "record_type", "origin")}
        changed["native_blast"]["hsp_ordinal"] = 2  # Same scores, different original HSP.
        forged = store.put("observation", changed, origin="tool")
        with pytest.raises(ContractError, match="component_address_conflict"):
            blast_hsp_facts(store, [forged["id"]])


def test_missing_traceback_scores_and_conflicting_string_spans_preserve_partial_cells(tmp_path):
    native = hsp()
    for field in ("qseq", "hseq", "identity", "score", "align_len"):
        native.pop(field)
    with Store(tmp_path / "missing") as store:
        _, result = publish(store, native)
        assert result["status"] == "partial" and result["result"]["projected_hsp_count"] == 1
        component = retained(store, result)["sheet"]["hits"][0]["hsp_components"][0]
        assert component["fractions"]["query_span_coverage"] == 1
        assert component["fractions"]["query_paired_coverage"] is None
        fact, = blast_hsp_facts(store, result["record_refs"])
        assert fact["alignment_score"] is fact["identity_fraction"] is None
        assert fact["bitscore"] == 12.5 and fact["query_coverage"] == 1
        assert result["result"]["projection_errors"][0]["code"] == "blast_hsp_shared_measurements_unavailable"
    with Store(tmp_path / "span") as store:
        _, result = publish(store, hsp(query_to=3))
        component = retained(store, result)["sheet"]["hits"][0]["hsp_components"][0]
        assert component["counts"]["identical_pairs"] == 3
        assert component["fractions"]["query_span_coverage"] == .75
        assert component["fractions"]["query_paired_coverage"] is None
        assert "traceback_coordinate_span_conflict" in {row["code"] for row in component["issues"]}


@pytest.mark.parametrize("native,reference_length", [(hsp(query_from=0), 4), (hsp(), 0)])
def test_invalid_native_coordinates_or_length_preserve_native_without_fake_projection(tmp_path, native, reference_length):
    with Store(tmp_path / "store") as store:
        _, result = publish(store, native, reference_length=reference_length)
        assert result["status"] == "partial" and result["result"]["projected_hsp_count"] == 0
        component = retained(store, result)["sheet"]["hits"][0]["hsp_components"][0]
        assert component["native_scores"]["bit_score"] == 12.5
        assert component["counts"]["identical_pairs"] == 3


def test_grading_failure_does_not_invoke_independent_fallback(tmp_path, monkeypatch):
    def failed(*args, **kwargs):
        raise ValueError("explicit_grader_failure")
    monkeypatch.setattr(blast_graders, "grade_blast_result", failed)
    monkeypatch.setattr(blast_search, "hsp_row", blocked)
    with Store(tmp_path / "store") as store:
        _, result = publish(store)
        assert result["status"] == "partial" and result["result"]["projected_hsp_count"] == 0
        assert retained(store, result)["failure"]["code"] == "explicit_grader_failure"
        assert result["result"]["projection_errors"][0]["code"] == "blast_shared_grading_unavailable"


@pytest.mark.parametrize("missing", [False, True])
def test_zero_hits_are_distinct_from_missing_hit_array(tmp_path, missing):
    with Store(tmp_path / "store") as store:
        _, result = publish(store, hits=[], missing_hits=missing)
        assert result["result"]["projected_hsp_count"] == 0
        assert result["result"]["reported_hit_array_empty"] is (not missing)
        assert result["result"]["native_hit_count"] == (None if missing else 0)
        assert (result["result"]["no_hit_meaning"] is None) is missing


@pytest.mark.parametrize("kind", ["hit_row", "hsp_row", "wrong_artifact", "wrong_native", "wrong_ordinal", "forged_value", "downgrade"])
def test_new_record_binding_rejects_forged_records_even_with_fresh_record_digest(tmp_path, kind):
    with Store(tmp_path / "store") as store:
        _, outcome = publish(store)
        original = store.get(outcome["result"]["records"][0]["observation_ref"])
        forged = {key: deepcopy(value) for key, value in original.items() if key not in ("id", "record_type", "origin")}
        binding = forged["native_blast"]["shared_projection"]
        if kind in ("hit_row", "hsp_row"):
            binding[kind] = 1
        elif kind == "wrong_artifact":
            binding["grading_artifact_ref"] = store.artifact(b"{}", "application/json")
        elif kind == "wrong_native":
            binding["native_artifact_ref"] = store.artifact(b"{}", "application/json")
        elif kind == "wrong_ordinal":
            forged["native_blast"]["hsp_ordinal"] = 1
        elif kind == "downgrade":
            forged["native_blast"].pop("shared_projection")
        else:
            next(row for row in forged["measurements"] if row["name"] == "identity_fraction")["value"]["value"] = 1
        record = store.put("observation", forged, origin="tool")
        for read in (lambda: read_blast_hsp(store, record["id"], 0, 4, permitted_inputs=[record["id"]], scope=None),
                     lambda: blast_hsp_facts(store, [record["id"]])):
            with pytest.raises(ContractError):
                read()


def test_historical_saved_reported_count_meaning_is_not_repriced(tmp_path):
    with Store(tmp_path / "store") as store:
        _, outcome = publish(store)
        new = store.get(outcome["result"]["records"][0]["observation_ref"])
        source = store.get(new["source_ref"])
        metadata = json.loads(store.get_artifact(source["request_ref"]))
        source_payload = {key: deepcopy(value) for key, value in source.items()
            if key not in ("id", "record_type", "origin", "auxiliary_artifact_refs")}
        source_payload["request_ref"] = store.artifact(json.dumps(
            {"request": metadata["request"], "transport": {}}), "application/json")
        legacy_source = store.put("source", source_payload, origin="external")
        original_reference = store.get(new["source_subject_refs"][0])
        reference_payload = {key: value for key, value in original_reference.items() if key not in ("id", "record_type", "origin")}
        legacy_reference = store.put("reference", {**reference_payload, "source_ref": legacy_source["id"]}, origin="external")
        payload = json.loads(json.dumps({key: value for key, value in new.items() if key not in ("id", "record_type", "origin")})
            .replace(source["id"], legacy_source["id"]).replace(original_reference["id"], legacy_reference["id"]))
        payload["native_blast"].pop("shared_projection")
        next(row for row in payload["measurements"] if row["name"] == "identity_fraction")["value"]["value"] = 1
        legacy = store.put("observation", payload, origin="tool")
        saved = deepcopy(legacy)
        read = read_blast_hsp(store, legacy["id"], 0, 4, permitted_inputs=[legacy["id"]], scope=None)
        assert numeric(read)["identity_fraction"] == 1
        assert read["measurement_semantics"] == "legacy_saved_native_reported"
        assert blast_hsp_facts(store, [legacy["id"]])[0]["identity_fraction"] == 1
        assert store.get(legacy["id"]) == saved


def test_original_retained_legacy_store_remains_readable_without_changing_its_records(tmp_path):
    original = Path(__file__).resolve().parents[1] / (
        "verification/tool_graders_blast_regressions_2026-10-26_299/checks_003/temporary/pytest/"
        "test_recorded_hsp_facts_fill_c0/store")
    copied = tmp_path / "historical"
    shutil.copytree(original, copied, copy_function=shutil.copyfile)
    for path in copied.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)
    copied.chmod(0o755)
    with Store(copied) as store:
        old_records = list(store.db.execute("SELECT id,data FROM records ORDER BY id"))
        observations = [json.loads(row["data"]) for row in old_records
            if json.loads(row["data"]).get("native_blast")]
        assert observations and all("shared_projection" not in row["native_blast"] for row in observations)
        for observation in observations:
            view = read_blast_hsp(store, observation["id"], 0, 2,
                permitted_inputs=[observation["id"]], scope=None)
            assert numeric(view) == numeric(observation)
            assert view["measurement_semantics"] == "legacy_saved_native_reported"
            fact, = blast_hsp_facts(store, [observation["id"]])
            assert fact["identity_fraction"] == numeric(observation).get("identity_fraction")
        assert [tuple(row) for row in store.db.execute("SELECT id,data FROM records ORDER BY id")] == [tuple(row) for row in old_records]


def test_union_and_database_dependence_survive_projection(tmp_path):
    first = hsp(hseq="ACGT", identity=4)
    overlap = hsp(qseq="GTAC", hseq="GTAC", query_from=3, query_to=6, hit_from=3, hit_to=6)
    with Store(tmp_path / "store") as store:
        _, result = publish(store, query="ACGTAC", hits=[{"len": 6,
            "description": [{"accession": "REFERENCE.1"}, {"accession": "ALIAS.1"}],
            "hsps": [first, deepcopy(first), overlap]}])
        sheet = retained(store, result)["sheet"]
        assert sheet["hits"][0]["measurements"]["observed_paired_query_positions"] == 6
        assert len(sheet["sequence_groups"]) == 1
        assert len(retained(store, result)["probabilities"]["sequence_group_contributions"]) == 1
        pair_input = deepcopy(sheet["normalized_result"])
        pair_input["mode"] = "pairwise"
        pair = blast_pairwise_grader.build_pairwise_sheet(pair_input)
        assert pair["union"]["counts"]["paired_query_positions"] == 6
        assert pair["union"]["identical_mapping_hsp_groups"] == [[0, 1]]
