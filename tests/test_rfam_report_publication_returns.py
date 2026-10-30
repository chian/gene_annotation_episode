"""Selected API receipts and both Rfam report return boundaries, without HTTP.

The six retained report displays are adapted only to the service's generated
query headers and marked synthetic. Empty/foreign/malformed variants below are
also synthetic. Store, API selections/receipts, publication, authentication and
parent admission are real; commission/form journal records are controlled
fixtures, not a configured-model Workflow demonstration.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import json
import re

import pytest

from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.form_reference_validation import form_reference_validation
from gene_annotation_episode.rfam_batch_contracts import RFAM_CALCULATION_PARAMETERS
from gene_annotation_episode.rfam_batch_publication import publish_rfam_batch_result
from gene_annotation_episode.rfam_batch_report_contracts import (
    REPORT_FORMAT, REPORT_PARSE_VERSION, RFAM_REPORT_METRICS)
from gene_annotation_episode.rfam_batch_returns import RfamBatchReturns, rfam_fact_sources
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_rfam_batch_returns import (Harness, SavedClient, LIVE, forbid_read_work,
    schema_for, snapshot)


REPORT_ROWS = "rfam_report_rows"
POPULATIONS = "rfam_result_populations"
REPORT_SOURCES = (REPORT_ROWS, POPULATIONS)


def report_selector(*metrics, family="hit", rows=None, projection=True, version=3):
    return {"version": "rfam_batch_result_selector_v" + str(version),
        "representation": "out", "model_metadata_ref": None,
        "projection": {"family": family, "rows": rows or {"offset": 0, "limit": 20},
            "metrics": list(metrics or ("native_score_bits", "native_evalue", "query_span_fraction",
                "model_consensus_equal_count", "model_consensus_compared_count", "query_insert_count",
                "model_delete_count", "model_length_positions", "model_coverage_fraction"))}
        if projection else None}


class ReportClient(SavedClient):
    """No live transport: adapt captured report names without moving tracks."""
    def __init__(self):
        super().__init__()
        value = snapshot("multi", "005-fetch-out")
        self.original_report = value.content
        records = json.loads((LIVE / "multi/input-manifest.json").read_text())["records"]
        content = value.content
        for index, record in enumerate(records):
            old, new = record["original_header"], f"rfam_query_{index:08d}"
            assert len(new) <= len(old)
            content = content.replace(old.encode(), new.ljust(len(old)).encode())
        self.result_snapshot = replace(value, content=content,
            transport={**value.transport, "evidence_kind": "synthetic_fixture"})

    def change_report(self, transform=None, *, content=None, complete=True):
        value = self.result_snapshot
        content = value.content if content is None else content
        if transform is not None:
            content = transform(content)
        self.result_snapshot = replace(value, content=content,
            transport={**value.transport, "evidence_kind": "synthetic_fixture", "body_complete": complete})

    def empty_report(self):
        value = self.result_snapshot.content.decode()
        header = value[:value.index("Query:")]
        queries = re.findall(r"^Query:.*$", value, re.MULTILINE)
        self.change_report(content=(header + "".join(query + "\nHit scores:\n"
            "   [No hits detected that satisfy reporting thresholds]\n\nHit alignments:\n"
            "   [No hits detected that satisfy reporting thresholds]\n\n"
            "Internal CM pipeline statistics summary:\nTotal CM hits reported: 0\n//\n"
            for query in queries) + "[ok]\n").encode())


class ReportHarness(Harness):
    def __init__(self, store, directory):
        self.store, self.run_id = store, "rfam-report-return-fixture"
        self.client = ReportClient()
        subjects = store.create_problem(LIVE / "multi/input.seq", molecule="dna")["subject_refs"]
        assert len(subjects) == 6
        self.scope = {"subject_refs": subjects}
        self.request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch", "subject_refs": subjects}
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.tools = ToolRegistry(store, clients=self.client)
        self.api = APIServiceExecution(store, run_id=self.run_id, directory=directory,
            configuration={"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90}},
            tool_registry=self.tools, handoff_unit=3, acquired_record_unit=2)
        self.api.services["rfam"].client = self.client
        self.boundary = RfamBatchReturns(self.api)
        self.root = self.context((("annotation", "root"),), {}, None)

    def acquired(self, parent=None, schema=None, selected=None, *, index=0):
        return super().acquired(parent, schema if schema is not None else schema_for(*REPORT_SOURCES),
            selected or report_selector(), index=index)


@pytest.fixture(autouse=True)
def no_external_work(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline report verification attempted external/model execution")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("time.sleep", forbidden)
    monkeypatch.setattr("gene_annotation_episode.runtime.DecisionSource.call", forbidden)


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / "state") as store:
        yield ReportHarness(store, tmp_path / "run")


def retained(h, result):
    grading = h.store.get(result["grading_source_ref"])
    manifest = json.loads(h.store.get_artifact(grading["artifact_ref"]))
    return manifest, *(None if manifest[key] is None else json.loads(h.store.get_artifact(manifest[key]))
        for key in ("parse_ref", "sheet_ref", "calculation_ref"))


def measured(row):
    return {cell["name"]: cell["value"] for cell in row["measured"]}


def forbid_report_read_work(monkeypatch, h):
    forbid_read_work(monkeypatch, h)
    def forbidden(*args, **kwargs):
        raise AssertionError("Return/replay attempted report parsing, calculation or transport")
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_report_grader.calculate_rfam_batch_report_components", forbidden)
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_table.parse_rfam_report_membership", forbidden)


def publication_inputs(h, child, outcome):
    result = outcome["result"]
    key = result["acquisition_receipt"]["operation_key"]
    path = h.api._episode_directory(child.episode_id) / "actions" / digest(key)
    response = h.api._load_snapshot(json.loads((path / "snapshot.json").read_text()))
    handoff = h.api._read_handoff(child.assignment["handoff_ref"], h.scope)
    submission = h.api._load_snapshot(handoff["snapshot"])
    return dict(request=h.request, selector=plain(child.assignment)["selector"], snapshot=response,
        scope=h.scope, operation_key=key + ":publication", submission_snapshot=submission,
        handle=handoff["event"]["native_handle"])


def test_selected_report_keeps_native_arithmetic_full_artifacts_and_separate_model_identity(saved, monkeypatch):
    h = saved
    def forbidden(*args, **kwargs):
        raise AssertionError("Report publication entered the JSON scientific parser")
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_publication._json_parse", forbidden)
    child, outcome = h.acquired(selected=report_selector(*RFAM_REPORT_METRICS["hit"]))
    assert outcome["status"] == "completed", outcome
    result = outcome["result"]
    manifest, parsed, sheet, calculation = retained(h, result)
    assert manifest["format"] == REPORT_FORMAT and parsed["version"] == "rfam_batch_parse_result_v2"
    assert parsed["sheet"] == sheet and parsed["status"] == "partial"
    assert sheet["source_context"]["population_complete"]  # Explicit truncation shorthand is not missing hit membership.
    assert sheet["source_context"]["input_identity"] == manifest["input_identity"]
    assert sheet["source_context"]["capture"]["evidence_kind"] == "synthetic_fixture"
    assert calculation["parameters"] == {"hit_scope": "reported"}
    assert h.store.get_artifact(result["artifact_ref"]) == h.client.result_snapshot.content
    assert len(sheet["hits"]) == len(calculation["hits"]) == 6
    assert outcome["record_refs"] == [result["submission_source_ref"], result["source_ref"], result["grading_source_ref"]]
    assert h.store.get(result["grading_source_ref"])["parent_source_refs"] == outcome["record_refs"][:2]
    rows = result["projection"]["rows"]
    assert [measured(row)["native_score_bits"] for row in rows] == [104.6, 104.6, 104.6, 51.3, 95.5, 95.2]
    assert [measured(row)["query_span_nt"] for row in rows] == [119, 119, 119, 70, 120, 118]
    assert [measured(row)["query_insert_count"] for row in rows] == [1, 1, 1, 0, 2, 1]
    assert [measured(row)["model_delete_count"] for row in rows] == [2, 2, 2, 1, 2, 3]
    assert [measured(row)["model_consensus_compared_count"] for row in rows] == [118, 118, 118, 70, 118, 117]
    # Independently checked from the retained native consensus/query strings.
    assert [measured(row)["model_consensus_equal_count"] for row in rows] == [75, 75, 75, 43, 75, 75]
    for row, native in zip(rows, sheet["hits"]):
        values = measured(row)
        pairs = native["correspondence"]["paired_positions"]
        equal = sum(pair["consensus_symbol"].upper().replace("T", "U") ==
            pair["query_symbol"].upper().replace("T", "U") for pair in pairs)
        assert values["model_consensus_equal_count"] == equal
        assert values["model_consensus_equal_fraction"] == equal / values["model_consensus_compared_count"]
        assert values["query_span_fraction"] == 1 and values["native_bias_bits"] == 0
        assert row["family_accession"] is None and row["model_name"] == "5S_rRNA"
        assert row["unavailable"] == [
            {"name": "model_length_positions", "reason": "model_length_unavailable"},
            {"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
    assert measured(rows[3])["native_model_span_positions"] == measured(rows[3])["represented_model_positions"] == 71
    assert measured(rows[3])["display_model_to"] == 120 and measured(rows[3])["truncated_model_count_3p"] == 49
    assert rows[0]["query_occurrence_key"] != rows[1]["query_occurrence_key"]
    assert rows[2]["strand"] == "-" and measured(rows[2])["native_start_1i"] == 119
    forbid_report_read_work(monkeypatch, h)
    before = list(h.store.db.iterdump())
    for ref in outcome["record_refs"]:
        assert h.boundary.read(ref, h.scope, episode_id=child.episode_id)["projection"] == result["projection"]
    facts = h.api.facts(child, {})
    assert len(facts[REPORT_ROWS]) == 6 and "rfam_result_rows" not in facts
    assert h.api.resolve(child, "5S_rRNA", "rfam_model") is True
    assert h.api.resolve(child, "RF00001", "rfam_family") is False
    assert h.store.count("observation") == h.store.count("reference") == 0
    assert list(h.store.db.iterdump()) == before


def test_report_both_parent_boundaries_and_exact_replay_do_no_new_work(saved, monkeypatch):
    h, schema = saved, schema_for(*REPORT_SOURCES)
    science = h.child(h.root, schema)
    child, outcome = h.acquired(science, schema)
    form = h.returned(science, child)
    forwarded = h.returned(h.root, science)
    assert form == forwarded
    original = publication_inputs(h, child, outcome)
    forbid_report_read_work(monkeypatch, h)
    before = list(h.store.db.iterdump())
    for parent, returned, owner in ((science, form, child), (h.root, forwarded, science)):
        h.boundary.validate_received_report(owner, returned, schema)
        assert h.boundary.record_admission(parent, returned, schema, h.operation(parent)) == [outcome["result"]["source_ref"]]
        with form_reference_validation():
            assert validate_form(returned, schema, lambda ref, namespace: h.api.resolve(parent, ref, namespace)) == returned
        assert h.boundary.received_facts(parent, schema) == h.boundary.facts(child, schema)
    assert asyncio.run(h.api.execute(child, "api.rfam.fetch", {}, outcome["result"]["acquisition_receipt"]["operation_key"])) == outcome
    replay = publish_rfam_batch_result(h.tools, **original)
    assert replay["result"] == {key: value for key, value in outcome["result"].items()
        if key not in {"handoff_ref", "acquisition_receipt"}}
    assert h.client.calls == ["submit_synthetic_batch", "fetch_saved:out"]
    assert h.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    assert list(h.store.db.iterdump()) == before
    changed = deepcopy(original)
    changed["selector"]["projection"]["metrics"] = ["native_score_bits"]
    with pytest.raises(ValueError, match="operation_key_reused_for_different_work"):
        publish_rfam_batch_result(h.tools, **changed)


@pytest.mark.parametrize("family", ["hit", "query_strand"])
def test_complete_empty_report_has_zero_population_without_fake_hit(saved, family):
    h = saved
    h.client.empty_report()
    selected = report_selector("query_length_nt", "selected_row_count", "query_strand_union_span_nt",
        "query_strand_union_fraction", family=family) if family == "query_strand" else report_selector()
    child, outcome = h.acquired(selected=selected)
    assert outcome["status"] == "completed", outcome
    form = h.returned(h.root, child)
    h.boundary.record_admission(h.root, form, schema_for(*REPORT_SOURCES), h.operation(h.root))
    facts = h.boundary.received_facts(h.root, schema_for(*REPORT_SOURCES))
    population, = facts[POPULATIONS]
    assert population["population_complete"] and not population["more_rows"]
    if family == "hit":
        assert facts[REPORT_ROWS] == [] and population["available_row_count"] == population["selected_row_count"] == 0
    else:
        assert len(facts[REPORT_ROWS]) == population["selected_row_count"] == 12
        for row in facts[REPORT_ROWS]:
            assert row["model_name"] is row["family_accession"] is None
            assert measured(row)["selected_row_count"] == measured(row)["query_strand_union_span_nt"] == 0
            assert measured(row)["query_strand_union_fraction"] == 0


@pytest.mark.parametrize("mutation", ["incomplete_body", "missing_end", "invalid_cell", "foreign_query", "wrong_length", "malformed", "wrong_file", "unsupported_profile"])
def test_report_partial_and_rejected_data_keep_specific_facts_and_bytes(saved, mutation):
    h = saved
    if mutation == "incomplete_body":
        h.client.change_report(complete=False)
    elif mutation == "missing_end":
        h.client.change_report(lambda raw: raw.replace(b"[ok]\n", b""))
    elif mutation == "invalid_cell":
        h.client.change_report(lambda raw: raw.replace(b"104.6", b"wrong", 1))
    elif mutation == "foreign_query":
        h.client.change_report(lambda raw: raw.replace(b"rfam_query_00000000", b"foreign_query_00000"))
    elif mutation == "wrong_length":
        h.client.change_report(lambda raw: raw.replace(b"[L=119]", b"[L=120]", 1))
    elif mutation == "malformed":
        h.client.change_report(content=b"deliberately malformed report\n")
    elif mutation == "wrong_file":
        job = h.client.result_snapshot.request["job_id"].encode()
        h.client.change_report(lambda raw: raw.replace(job, b"infernal_cmscan-FOREIGN"))
    else:
        h.client.change_report(lambda raw: raw.replace(b"INFERNAL 1.1.5", b"INFERNAL 9.9.9"))
    child, outcome = h.acquired()
    result = outcome["result"]
    manifest, parsed, sheet, _ = retained(h, result)
    assert h.store.get_artifact(result["artifact_ref"]) == h.client.result_snapshot.content
    form = h.returned(h.root, child)
    h.boundary.validate_received_report(child, form, schema_for(*REPORT_SOURCES))
    facts = h.boundary.received_facts(h.root, schema_for(*REPORT_SOURCES))
    if mutation in {"malformed", "wrong_file", "unsupported_profile"}:
        assert outcome["status"] == "partial" and sheet is result["projection"] is None
        assert facts == {name: [] for name in REPORT_SOURCES}
        assert result["projection_errors"] and parsed["status"] in {"rejected", "unsupported"}
        assert all(item["source_pointer"] is None or item["source_pointer"].startswith("line:")
            for item in result["projection_errors"])
        if mutation == "wrong_file":
            assert "rfam_batch_report_query_file_conflict" in {item["code"] for item in result["projection_errors"]}
    else:
        assert len(facts[REPORT_ROWS]) == 6
        assert measured(facts[REPORT_ROWS][1])["native_score_bits"] == 104.6
        if mutation in {"foreign_query", "wrong_length"}:
            assert outcome["status"] == "partial"
            assert facts[REPORT_ROWS][0]["query_occurrence_key"] is None
            assert facts[REPORT_ROWS][0]["measured"] == []
            assert {cell["reason"] for cell in facts[REPORT_ROWS][0]["unavailable"]} == {"identity_rejected"}
        elif mutation == "invalid_cell":
            assert outcome["status"] == "completed"
            assert "native_score_bits" not in measured(facts[REPORT_ROWS][0])
            assert measured(facts[REPORT_ROWS][0])["native_evalue"] == 1.4e-24
        else:
            assert not facts[POPULATIONS][0]["population_complete"]
            assert outcome["status"] == ("partial" if mutation == "incomplete_body" else "completed")


def test_only_original_selected_report_rows_are_resolvable(saved):
    h = saved
    child, outcome = h.acquired(selected=report_selector(rows={"offset": 2, "limit": 1}))
    facts = h.boundary.facts(child, schema_for(*REPORT_SOURCES, "rfam_result_rows"))
    assert facts["rfam_result_rows"] == [] and len(facts[REPORT_ROWS]) == 1
    assert facts[POPULATIONS][0]["available_row_count"] == 6 and facts[POPULATIONS][0]["more_rows"]
    _, _, sheet, _ = retained(h, outcome["result"])
    hidden = sheet["hits"][0]
    selected = sheet["hits"][2]
    h.returned(h.root, child)
    for context in (child, h.root):
        assert h.api.resolve(context, selected["hit_id"], "rfam_record") is True
        assert h.api.resolve(context, hidden["hit_id"], "rfam_record") is False
        assert h.api.resolve(context, hidden["query_occurrence_key"], "rfam_query") is False
        assert h.api.resolve(context, "5S_rRNA", "rfam_model") is True


def test_explicit_report_record_keys_and_unavailable_projection_preserve_full_saved_data(saved):
    h = saved
    child, outcome = h.acquired()
    inputs = publication_inputs(h, child, outcome)
    _, _, sheet, _ = retained(h, outcome["result"])
    keys = [sheet["hits"][index]["hit_id"] for index in (5, 0)]
    reordered = publish_rfam_batch_result(h.tools, **{**inputs,
        "operation_key": inputs["operation_key"] + ":ordered-keys",
        "selector": report_selector("native_score_bits", rows={"record_keys": keys})})
    assert reordered["status"] == "completed"
    assert [row["record_key"] for row in reordered["result"]["projection"]["rows"]] == keys
    assert [measured(row)["native_score_bits"] for row in reordered["result"]["projection"]["rows"]] == [95.2, 104.6]
    wrong = publish_rfam_batch_result(h.tools, **{**inputs,
        "operation_key": inputs["operation_key"] + ":wrong-key",
        "selector": report_selector(rows={"record_keys": ["foreign-record"]})})
    assert wrong["status"] == "partial" and wrong["result"]["projection"] is None
    assert wrong["result"]["projection_errors"] == [{"code": "rfam_projection_reference_conflict",
        "scope": "projection", "hit_key": None, "field": "projection", "source_pointer": None}]
    assert wrong["result"]["sheet_ref"] == outcome["result"]["sheet_ref"]
    assert wrong["result"]["calculation_ref"] == outcome["result"]["calculation_ref"]


@pytest.mark.parametrize("mutation", ["response_job", "submitted_file"])
def test_original_report_request_and_submission_identity_reject_before_new_publication(saved, mutation):
    h = saved
    child, outcome = h.acquired()
    inputs = publication_inputs(h, child, outcome)
    inputs["operation_key"] += ":invalid-original"
    if mutation == "response_job":
        value = inputs["snapshot"]
        inputs["snapshot"] = replace(value, request={**value.request, "job_id": value.request["job_id"] + "OTHER"})
    else:
        value = inputs["submission_snapshot"]
        inputs["submission_snapshot"] = replace(value, request={**value.request,
            "file_base64": base64.b64encode(b">unselected\nACGT\n").decode()})
    before = list(h.store.db.iterdump())
    with pytest.raises(ValueError, match="rfam_result_(job|sequence)_identity_conflict"):
        publish_rfam_batch_result(h.tools, **inputs)
    assert list(h.store.db.iterdump()) == before


@pytest.mark.parametrize("original_source", ["execution_result_refs", "execution_completed", POPULATIONS, "rfam_result_rows"])
def test_report_source_only_or_other_row_family_does_not_grant_model_or_report_rows(saved, original_source):
    h, schema = saved, schema_for(original_source)
    child, outcome = h.acquired(schema=schema)
    facts = h.boundary.facts(child, schema)
    facts.update(execution_result_refs=outcome["record_refs"], execution_completed=True)
    h.returned(h.root, child, facts)
    h.receipts.receive(h.root.episode_id, outcome["record_refs"], kind="child_form", source_index=0)
    for context, resolver in ((child, h.boundary.resolve_own), (h.root, h.boundary.resolve_received)):
        assert resolver(context, "5S_rRNA", "rfam_model") is False
        assert resolver(context, outcome["result"]["projection"]["rows"][0]["record_key"], "rfam_record") is False
    assert h.boundary.received_facts(h.root, schema_for(REPORT_ROWS)) == {REPORT_ROWS: []}
    assert h.boundary.facts(child, schema_for(REPORT_ROWS)) == {REPORT_ROWS: []}


def test_scientific_population_only_form_does_not_forward_received_report_identity(saved):
    h = saved
    science = h.child(h.root, schema_for(POPULATIONS))
    child, _ = h.acquired(science)
    h.returned(science, child)
    h.returned(h.root, science)
    assert h.api.resolve(science, "5S_rRNA", "rfam_model") is True
    assert h.api.resolve(h.root, "5S_rRNA", "rfam_model") is False
    assert h.boundary.received_facts(h.root, schema_for(REPORT_ROWS)) == {REPORT_ROWS: []}


@pytest.mark.parametrize("field", ["model_name", "family_accession", "query_occurrence_key", "metric", "value", "omit", "expand"])
def test_forged_report_cells_cannot_cross_frozen_parent_boundary(saved, field):
    h, schema = saved, schema_for(*REPORT_SOURCES)
    child, _ = h.acquired()
    facts = h.boundary.facts(child, schema)
    row = facts[REPORT_ROWS][0]
    if field in {"model_name", "family_accession", "query_occurrence_key"}:
        row[field] = "RF00001" if field == "family_accession" else "foreign"
    elif field == "metric":
        row["measured"][0]["name"] = "query_insert_count"
    elif field == "value":
        row["measured"][0]["value"] += 1
    elif field == "omit":
        facts[REPORT_ROWS].pop()
    else:
        facts[REPORT_ROWS].append(deepcopy(row))
    form = h.returned(h.root, child, facts)
    with pytest.raises(ValueError, match="rfam_return_returned_facts_conflict"):
        h.boundary.record_admission(h.root, form, schema, h.operation(h.root))


@pytest.mark.parametrize("mutation", ["native", "submission", "manifest", "parse", "sheet", "calculation", "selector", "projection"])
def test_report_custody_and_original_projection_tampering_rejected(saved, mutation):
    h = saved
    child, outcome = h.acquired()
    result = outcome["result"]
    manifest, _, _, _ = retained(h, result)
    if mutation == "selector":
        path = h.api._episode_directory(child.episode_id) / "assignment.json"
        value = json.loads(path.read_text())
        value["assignment"]["selector"]["projection"]["rows"]["limit"] = 1
        path.write_text(canonical(value))
    elif mutation == "projection":
        outcome["result"]["projection"]["rows"][0]["model_name"] = "other_model"
        h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(outcome), h.run_id, child.episode_id))
    else:
        reference = (result["artifact_ref"] if mutation == "native" else
            h.store.get(result["submission_source_ref"])["request_ref"] if mutation == "submission" else
            h.store.get(result["grading_source_ref"])["artifact_ref"] if mutation == "manifest" else manifest[mutation + "_ref"])
        sha = h.store.get(reference)["sha256"]
        (h.store.path / "artifacts" / sha[:2] / sha).write_bytes(b"{}")
    with pytest.raises(ValueError):
        h.boundary.read(result["source_ref"], h.scope, episode_id=child.episode_id)


def test_report_redelivery_is_exact_and_cannot_expand_original_families(saved, monkeypatch):
    h = saved
    child, outcome = h.acquired()
    h.returned(h.root, child)
    schema = schema_for(*REPORT_SOURCES)
    form = h.redeliver(h.root, child, schema)
    forbid_report_read_work(monkeypatch, h)
    before = list(h.store.db.iterdump())
    assert h.boundary.record_admission(h.root, form, schema, h.operation(h.root, 1)) == [outcome["result"]["source_ref"]]
    assert len(h.boundary.received_facts(h.root, schema)[REPORT_ROWS]) == 6
    assert h.journal.row("runtime_actions", h.root.episode_id, 1) is None
    assert list(h.store.db.iterdump()) == before


@pytest.mark.parametrize("version", [1, 2])
def test_old_report_selector_still_has_artifact_only_semantics(saved, monkeypatch, version):
    h = saved
    def forbidden(*args, **kwargs):
        raise AssertionError("Old report selection entered new numerical parser")
    monkeypatch.setattr("gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet", forbidden)
    child, outcome = h.acquired(selected=report_selector(version=version, projection=False))
    assert outcome["status"] == "completed"
    result = outcome["result"]
    assert result["sheet_ref"] is result["calculation_ref"] is result["projection"] is None
    assert h.boundary.facts(child, schema_for(*REPORT_SOURCES)) == {source: [] for source in REPORT_SOURCES}
    assert h.store.get_artifact(result["artifact_ref"]) == h.client.result_snapshot.content


def test_report_fact_form_does_not_broaden_old_rows():
    descriptors = rfam_fact_sources()
    old = descriptors["rfam_result_rows"]["report_schema"]["items"]
    report = descriptors[REPORT_ROWS]["report_schema"]["items"]
    assert "model_name" not in old["properties"] and "model_name" in report["properties"]
    assert "query_insert_count" not in old["properties"]["measured"]["items"]["properties"]["name"]["enum"]
    assert "query_insert_count" in report["properties"]["measured"]["items"]["properties"]["name"]["enum"]
    assert report["additionalProperties"] is False
    assert report["properties"]["model_name"]["x-reference-namespace"] == "rfam_model"
