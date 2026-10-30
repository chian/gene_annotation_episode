"""Common-cell publication and authenticated saved v1/v2 receiver regressions.

New executions use retained source bytes and the existing explicitly synthetic
request seams. Historical replay uses isolated copies of actual old receipts;
it does not regenerate a v1 result with current code or change old evidence.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.rfam_batch_contracts import rfam_digest
from gene_annotation_episode.rfam_batch_infernal import HIT_ALIASES
from gene_annotation_episode.rfam_batch_views import project_rfam_batch_result
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_rfam_batch_returns import Harness, forbid_read_work, schema_for, selector
from test_rfam_report_publication_returns import ReportHarness


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Shared Rfam verification attempted external or model work")
    for path in ("socket.create_connection", "subprocess.Popen",
                 "gene_annotation_episode.runtime.DecisionSource.call"):
        monkeypatch.setattr(path, forbidden)


def _saved(h, outcome):
    result = outcome["result"]
    manifest_ref = h.store.get(result["grading_source_ref"])["artifact_ref"]
    manifest = json.loads(h.store.get_artifact(manifest_ref))
    parsed, sheet, scores = [json.loads(h.store.get_artifact(manifest[key]))
        for key in ("parse_ref", "sheet_ref", "calculation_ref")]
    return manifest_ref, manifest, parsed, sheet, scores


@pytest.mark.parametrize("representation", ["json", "tblout", "out"])
def test_selected_child_publication_and_both_returns_use_one_common_calculation(tmp_path, monkeypatch, representation):
    from gene_annotation_episode import infernal_search_grader
    calls = []
    original = infernal_search_grader.calculate_infernal_search_scores
    def tracked(sheet, *, parameters=None):
        calls.append((deepcopy(sheet), deepcopy(parameters)))
        return original(sheet, parameters=parameters)
    monkeypatch.setattr(infernal_search_grader, "calculate_infernal_search_scores", tracked)
    with Store(tmp_path / "state") as store:
        h = (ReportHarness if representation == "out" else Harness)(store, tmp_path / "run")
        if representation == "tblout":
            h.client.synthetic_table()
        rows = "rfam_report_rows" if representation == "out" else "rfam_result_rows"
        schema = schema_for(rows, "rfam_result_populations")
        parent = h.child(h.root, schema)
        child, outcome = (h.acquired(parent, schema) if representation == "out" else
            h.acquired(parent, schema, batch=representation == "tblout"))
        assert outcome["status"] == "completed", outcome
        _, manifest, parsed, sheet, scores = _saved(h, outcome)
        assert manifest["version"] == "rfam_batch_retained_grading_v2"
        assert parsed["version"] == "rfam_batch_parse_result_v2" and parsed["representation"] == representation
        assert manifest["sheet_schema"] == sheet["schema"] == "infernal_search_sheet_v2"
        assert manifest["calculation_schema"] == scores["schema"] == "infernal_search_scores_v2"
        assert manifest["parse_digest"] == rfam_digest(parsed)
        assert manifest["sheet_digest"] == scores["sheet_digest"] == rfam_digest(sheet)
        assert manifest["calculation_digest"] == rfam_digest(scores)
        assert calls == [(sheet, {"hit_scope": "reported"})]
        assert sheet["source_context"] == scores["source_context"]
        assert sheet["source_context"]["input_identity"] == manifest["input_identity"]
        assert sheet["artifacts"][0]["source_descriptor"]["artifact_ref"] == outcome["result"]["artifact_ref"]
        assert sheet["lineage"] is None and "native_calculation" not in scores
        by_id = {row["hit_id"]: row for row in scores["hits"]}
        for row in outcome["result"]["projection"]["rows"]:
            for cell in row["measured"]:
                assert cell["value"] == by_id[row["record_key"]]["attributed_components"][HIT_ALIASES[cell["name"]]]
        returned = h.returned(parent, child)
        forwarded = h.returned(h.root, parent)
        forbid_read_work(monkeypatch, h)
        before = list(store.db.iterdump())
        assert returned == forwarded
        assert h.boundary.read(outcome["result"]["source_ref"], h.scope)["projection"] == outcome["result"]["projection"]
        h.boundary.validate_received_report(child, returned, schema)
        h.boundary.validate_received_report(parent, forwarded, schema)
        assert h.boundary.received_facts(h.root, schema) == h.boundary.facts(child, schema)
        assert list(store.db.iterdump()) == before


def test_new_partial_json_keeps_observed_union_and_unavailable_fraction(tmp_path, monkeypatch):
    with Store(tmp_path / "state") as store:
        h = Harness(store, tmp_path / "run")
        h.client.synthetic_json(lambda body: body.update(numHits=2))
        child, outcome = h.acquired(selected=selector("query_length_nt", "selected_row_count",
            "query_strand_sum_span_nt", "query_strand_union_span_nt", "query_strand_union_fraction",
            family="query_strand"))
        _, _, _, sheet, scores = _saved(h, outcome)
        assert scores["hits"][0]["components"]["sequence_span_fraction"] == 1
        plus = scores["sequence_strand_aggregates"][0]
        assert plus["span_sum"] == plus["union_numerator"] == 119
        assert plus["union_span_fraction"] is None and not plus["complete_for_selected_population"]
        forbid_read_work(monkeypatch, h)
        body = h.boundary.read(outcome["result"]["source_ref"], h.scope, episode_id=child.episode_id)
        row = body["projection"]["rows"][0]
        assert {v["name"]: v["value"] for v in row["measured"]} == {
            "query_length_nt": 119, "selected_row_count": 1,
            "query_strand_sum_span_nt": 119, "query_strand_union_span_nt": 119}
        assert row["unavailable"] == [{"name": "query_strand_union_fraction", "reason": "partial_body"}]
        assert not body["projection"]["population_complete"]
        assert sheet["source_context"]["capture"]["evidence_kind"] == "synthetic_fixture"


@pytest.mark.parametrize("field", ["parse_digest", "sheet_digest", "calculation_digest", "sheet_schema",
    "input_identity", "capture", "source_descriptor", "parameters", "hit_id", "occurrence", "saved_value"])
def test_v2_receiver_rejects_forged_saved_bindings_even_with_resealed_component_digests(tmp_path, monkeypatch, field):
    with Store(tmp_path / "state") as store:
        h = Harness(store, tmp_path / "run")
        child, outcome = h.acquired()
        manifest_ref, manifest, parsed, sheet, scores = deepcopy(_saved(h, outcome))
        if field in {"parse_digest", "sheet_digest", "calculation_digest", "sheet_schema"}:
            manifest[field] = "forged"
        else:
            if field == "input_identity":
                sheet["source_context"]["input_identity"]["subject_ref"] = "unselected_subject"
            elif field == "capture":
                sheet["source_context"]["capture"]["request_job_id"] = "another_job"
            elif field == "source_descriptor":
                sheet["artifacts"][0]["source_descriptor"]["source_sha256"] = "0" * 64
            elif field == "parameters":
                scores["parameters"] = {"hit_scope": "included"}
            elif field == "hit_id":
                scores["hits"][0]["hit_id"] = "unselected_hit"
            elif field == "occurrence":
                scores["hits"][0]["query_occurrence_key"] = "unselected_occurrence"
            else:
                scores["hits"][0]["components"]["bitscore"] = 999
                scores["hits"][0]["attributed_components"]["bitscore"] = 999
            scores["sheet_digest"] = rfam_digest(sheet)
            scores["source_context"] = deepcopy(sheet["source_context"])
            parsed["sheet"] = deepcopy(sheet)
            manifest.update(parse_digest=rfam_digest(parsed), sheet_digest=rfam_digest(sheet),
                calculation_digest=rfam_digest(scores))
        replacements = {manifest_ref: manifest, manifest["parse_ref"]: parsed,
            manifest["sheet_ref"]: sheet, manifest["calculation_ref"]: scores}
        real_read = h.api._artifact_json
        def substituted(reference):
            return deepcopy(replacements[reference]) if reference in replacements else real_read(reference)
        monkeypatch.setattr(h.api, "_artifact_json", substituted)
        forbid_read_work(monkeypatch, h)
        with pytest.raises(ValueError):
            h.boundary.read(outcome["result"]["source_ref"], h.scope, episode_id=child.episode_id)


LEGACY_RECEIPTS = {
    "json": "tool_graders_rfam_returns_2026-10-26_240/tests_004/temporary/pytest/test_native_read_uses_actual_a0",
    "json_partial": "tool_graders_rfam_returns_2026-10-26_240/tests_004/temporary/pytest/test_missing_partial_and_unava0",
    "tblout": "tool_graders_rfam_returns_2026-10-26_240/tests_004/temporary/pytest/test_query_strand_population_k1",
    "out": "tool_graders_rfam_report_returns_2026-10-26_244/tests_002/temporary/pytest/test_selected_report_keeps_nat0",
}


def _hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in directory.rglob("*") if p.is_file()}


@pytest.mark.parametrize("representation", LEGACY_RECEIPTS)
def test_actual_saved_v1_receivers_copy_exact_old_projection_without_upgrade(tmp_path, monkeypatch, representation):
    original = ROOT / "verification" / LEGACY_RECEIPTS[representation]
    evidence_before = _hashes(original)
    working = tmp_path / "historical_replay"
    shutil.copytree(original, working)
    # Store recovery may write local bookkeeping in this temporary copy. The
    # frozen historical receipt tree itself must remain byte-for-byte intact.
    working.chmod(0o700)
    for path in working.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
    acquisition, = working.glob("run/api-service-execution/*/episodes/*/actions/*/acquisition.json")
    receipt = json.loads(acquisition.read_text())
    expected = json.loads(acquisition.with_name("outcome.json").read_text())
    assignment = json.loads((acquisition.parents[2] / "assignment.json").read_text())
    with Store(working / "state") as store:
        api = APIServiceExecution(store, run_id=receipt["run_id"], directory=working / "run",
            configuration={"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90}},
            tool_registry=ToolRegistry(store), handoff_unit=3, acquired_record_unit=2)
        forbid_read_work(monkeypatch, SimpleNamespace(api=api))
        before = list(store.db.iterdump())
        body = api.rfam_returns.read(receipt["source_ref"], assignment["scope"], episode_id=receipt["episode_id"])
        assert body["publication_result"] == expected["result"]
        assert body["projection"] == expected["result"]["projection"]
        grading = store.get(body["grading_source_ref"])
        manifest = json.loads(store.get_artifact(grading["artifact_ref"]))
        assert manifest["version"] == "rfam_batch_retained_grading_v1"
        if representation == "json_partial":
            sheet = json.loads(store.get_artifact(manifest["sheet_ref"]))
            scores = json.loads(store.get_artifact(manifest["calculation_ref"]))
            saved_plus = scores["query_strands"][0]
            assert saved_plus["query_strand_union_fraction"] == 1 and not saved_plus["population_complete"]
            projection = project_rfam_batch_result(sheet, scores,
                projection={"family": "query_strand", "rows": {"offset": 0, "limit": 1},
                    "metrics": ["query_strand_union_span_nt", "query_strand_union_fraction"]},
                artifact_bindings={"source_ref": manifest["source_ref"], "sheet_ref": manifest["sheet_ref"],
                    "calculation_ref": manifest["calculation_ref"], "sheet_digest": rfam_digest(sheet),
                    "calculation_digest": rfam_digest(scores)})
            assert {v["name"]: v["value"] for v in projection["rows"][0]["measured"]} == {
                "query_strand_union_span_nt": 119, "query_strand_union_fraction": 1}
            assert not projection["population_complete"]
        assert list(store.db.iterdump()) == before
    assert _hashes(original) == evidence_before
