"""Real Store/API receipts and frozen form records with retained or marked data.

The selected API executor, publisher and typed-return machinery are real. HTTP
responses come from retained captures or explicit synthetic variants. Runtime
commissions/forms are controlled fixtures, not an actual Workflow/model run.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.rfam_batch_returns import (FACT_SOURCES, IDENTIFIER_NAMESPACES,
    RfamBatchReturns, rfam_fact_sources)
from gene_annotation_episode.rfam_discovery import result_url
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live"


def snapshot(mode, action):
    path = LIVE / mode / action
    value = json.loads((path / "snapshot.json").read_text())
    content = (path / "response.body").read_bytes()
    assert hashlib.sha256(content).hexdigest() == value.pop("content_sha256")
    return SourceSnapshot(**value, content=content)


def schema_for(*sources):
    descriptors, fields = rfam_fact_sources(), {}
    for index, source in enumerate(sources):
        if source in FACT_SOURCES:
            node = deepcopy(descriptors[source]["report_schema"])
        elif source == "execution_completed":
            node = {"type": "boolean", "x-source": source}
        else:
            node = {"type": "array", "items": {"type": "string", "format": "reference",
                "x-reference-namespace": "execution_result"}, "x-source": source}
        fields["selected_" + str(index)] = node
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def selector(*metrics, family="hit", rows=None, table=False, projection=True):
    return {"version": "rfam_batch_result_selector_v2" if table else "rfam_batch_result_selector_v1",
        "representation": "tblout" if table else "json", "model_metadata_ref": None,
        "projection": {"family": family, "rows": rows or {"offset": 0, "limit": 12},
            "metrics": list(metrics or ("native_score_bits", "native_evalue", "query_span_fraction", "model_coverage_fraction"))}
        if projection else None}


class SavedClient:
    """Captured single bytes unchanged; table name variants are marked synthetic."""
    timeout = 90

    def __init__(self):
        self.calls = []
        self.native = snapshot("single", "003-fetch-json")
        self.result_snapshot = self.native

    def submit(self, sequence):
        self.calls.append("submit_saved_single")
        value = snapshot("single", "001-submit")
        assert value.request["sequence_sha256"] == hashlib.sha256(sequence.encode()).hexdigest()
        return value

    def submit_file(self, content, *, filename):
        self.calls.append("submit_synthetic_batch")
        value = snapshot("multi", "001-submit")
        return replace(value, request={**value.request, "filename": filename,
            "file_base64": base64.b64encode(content).decode(),
            "file_sha256": hashlib.sha256(content).hexdigest(), "file_bytes": len(content)},
            transport={"status": 200, "body_complete": True, "evidence_kind": "synthetic_fixture"})

    def result(self, job_id, *, representation):
        self.calls.append("fetch_saved:" + representation)
        value = self.result_snapshot
        assert job_id == value.request["job_id"] and representation == value.request["representation"]
        return value

    def synthetic_json(self, transform=None, *, content=None, complete=True):
        value = json.loads(self.native.content)
        if transform is not None:
            transform(value)
        self.result_snapshot = replace(self.native,
            content=content if content is not None else canonical(value).encode(),
            transport={**self.native.transport, "evidence_kind": "synthetic_fixture", "body_complete": complete})

    def synthetic_table(self, *, foreign=False, empty=False, complete=True):
        value = snapshot("multi", "004-fetch-tblout")
        lines = value.content.decode().splitlines()
        header = [line for line in lines if line.startswith("#")]
        row = next(line for line in lines if not line.startswith("#")).split()
        row[2] = "foreign" if foreign else "rfam_query_00000000"
        rows = [] if empty else [" ".join(row)]
        # Retain the observed native header/footer profile, with a declared
        # synthetic one-row query-name substitution for the generated request.
        text = "\n".join(header[:2] + rows + header[2:]) + "\n"
        if not complete:
            text = text.replace("# [ok]\n", "")
        self.result_snapshot = replace(value, content=text.encode(),
            transport={**value.transport, "evidence_kind": "synthetic_fixture", "body_complete": True})


class Harness:
    def __init__(self, store, directory):
        self.store, self.run_id = store, "rfam-return-fixture"
        self.client = SavedClient()
        subject, = store.create_problem(raw_sequence=json.loads(self.client.native.content)["searchSequence"],
            molecule="dna")["subject_refs"]
        self.scope = {"subject_refs": [subject]}
        self.request = {"version": "rfam_batch_request_v1", "mode": "single_sequence", "subject_ref": subject}
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.tools = ToolRegistry(store, clients=self.client)
        self.api = APIServiceExecution(store, run_id=self.run_id, directory=directory,
            configuration={"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90}},
            tool_registry=self.tools, handoff_unit=3, acquired_record_unit=2)
        self.api.services["rfam"].client = self.client
        self.boundary = RfamBatchReturns(self.api)
        self.root = self.context((("annotation", "root"),), {}, None)

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective="Verify typed Rfam returns", result_contract={"role": path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                objective="Verify typed Rfam returns", result_contract=contract.schema))
        request = EpisodeRequest(goal, Record({"scope": deepcopy(self.scope), "initial_report": {},
            "episode_assignment": deepcopy(assignment)}), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, parent, schema, *, index=0, role="scientific_process", assignment=None):
        contract = TypedReportContract("Return original requested Rfam values", schema, lambda *_: True)
        assignment = assignment or {}
        child = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent)
        selection = {"kind": "episode_child", "role": role, "assignment": deepcopy(assignment),
            "scope": deepcopy(self.scope), "purpose": contract.decision, "schema_json": canonical(schema)}
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical(selection), "result": None, "credit": None})
        return child

    def action(self, context, name, *, index=0):
        key = f"{self.run_id}:{context.episode_id}:{index}"
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": name, "arguments": {}}), "result": None, "credit": None})
        outcome = asyncio.run(self.api.execute(context, name, {}, key))
        assert outcome["status"] in {"completed", "partial"}, outcome
        self.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(outcome), self.run_id, context.episode_id, index))
        self.receipts.receive(context.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
        return outcome

    def acquired(self, parent=None, schema=None, selected=None, *, index=0, batch=False):
        parent = parent or self.root
        schema = schema if schema is not None else schema_for(*FACT_SOURCES)
        if batch:
            subject = self.scope["subject_refs"][0]
            self.request = {"version": "rfam_batch_request_v2", "mode": "sequence_batch", "subject_refs": [subject, subject]}
        assignment = {"version": "api_service_assignment_v1", "resource_id": "rfam", "service": "rfam_batch",
            "request": self.request, "endpoint": "usable_handoff", "constraints": {}}
        launch = self.context((("launch_api", "native_fixture"),), assignment, None)
        submission = self.action(launch, "api.rfam.submit")
        assignment = {"version": "execution_results_assignment_v1", "handoff_ref": submission["result"]["handoff_ref"],
            "selector": selected or selector(table=batch)}
        child = self.child(parent, schema, index=index, role="results", assignment=assignment)
        outcome = self.action(child, "api.rfam.fetch")
        return child, outcome

    def returned(self, parent, child, facts=None):
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        if facts is None:
            facts = (self.boundary.facts(child, schema) if child.role == "results"
                else self.boundary.received_facts(child, schema))
        form = form_with_facts({}, schema, facts)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        index = int(child.path[-1][1].removeprefix("child_"))
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24],
            "child_episode_id": child.episode_id, "contract": canonical(contract),
            "form": canonical(form), "failure": None})
        return form

    def operation(self, context, index=0):
        return f"{self.run_id}:{context.episode_id}:{index}:typed_form"

    def redeliver(self, parent, child, schema, *, index=1, facts=None):
        original = self.store.db.execute("SELECT delivery_ref FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND child_episode_id=? ORDER BY decision_index LIMIT 1",
            (self.run_id, parent.episode_id, child.episode_id)).fetchone()
        if facts is None:
            facts = json.loads(self.journal.row("runtime_forms", child.episode_id)["facts"])
        form = form_with_facts({}, schema, facts)
        contract = TypedReportContract("Return exact saved Rfam facts", schema, lambda *_: True).as_record()
        selection = {"kind": "redeliver_report", "delivery_ref": original[0], "schema_json": canonical(schema),
            "purpose": contract["decision"]}
        self.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": index,
            "purpose": "decision", "request": "{}", "response": canonical({"selection": selection})})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": original[0], "child_episode_id": child.episode_id, "contract": canonical(contract),
            "form": canonical(form), "failure": None})
        return form


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Rfam return verification attempted external execution")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)


@pytest.fixture
def saved(tmp_path):
    with Store(tmp_path / "state") as store:
        yield Harness(store, tmp_path / "run")


def forbid_read_work(monkeypatch, h):
    def forbidden(*args, **kwargs):
        raise AssertionError("Return attempted acquisition, parsing or calculation")
    monkeypatch.setattr(h.api.services["rfam"], "invoke", forbidden)
    for module, names in {
        "rfam_batch_publication": ["populate_rfam_batch_json_sheet", "calculate_rfam_batch_components", "parse_rfam_alignment_display"],
        "rfam_batch_inputs": ["populate_rfam_batch_json_sheet"],
        "rfam_batch_table": ["populate_rfam_batch_tblout_sheet", "populate_infernal_search_sheet"],
        "rfam_batch_grader": ["calculate_rfam_batch_components"],
        "rfam_batch_table_grader": ["calculate_rfam_batch_table_components", "calculate_infernal_search_scores"],
        "infernal_search_grader": ["calculate_infernal_search_scores"],
        "infernal_search_inputs": ["populate_infernal_search_sheet"],
        "infernal_search_cells": ["populate_infernal_search_cells", "upgrade_saved_infernal_search_sheet"],
        "rfam_batch_infernal": ["populate_infernal_search_cells", "populate_rfam_json_cells",
            "populate_rfam_table_cells", "populate_rfam_report_cells", "upgrade_saved_rfam_search_sheet"],
        "rfam_batch_report": ["populate_rfam_batch_report_sheet"],
        "rfam_batch_report_grader": ["calculate_rfam_batch_report_components"],
    }.items():
        for name in names:
            monkeypatch.setattr("gene_annotation_episode." + module + "." + name, forbidden)


def test_native_read_uses_actual_api_receipt_and_three_original_sources(saved, monkeypatch):
    h = saved
    child, outcome = h.acquired()
    forbid_read_work(monkeypatch, h)
    before = list(h.store.db.iterdump())
    result = outcome["result"]
    for reference in outcome["record_refs"]:
        body = h.boundary.read(reference, h.scope, episode_id=child.episode_id)
        assert body["publication_result"] == result
        assert body["projection"] == result["projection"]
        assert not {"sheet", "calculation", "parse", "content"} & set(body)
    values = h.boundary.facts(child, schema_for(*FACT_SOURCES))
    row, = values[FACT_SOURCES[0]]
    assert {cell["name"]: cell["value"] for cell in row["measured"]} == {
        "native_score_bits": 104.6, "native_evalue": 1.4e-24, "query_span_fraction": 1.0}
    assert row["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_length_unavailable"}]
    assert row["population_complete"] is True
    assert h.boundary.resolve_own(child, row["record_key"], "rfam_record") is True
    assert h.boundary.resolve_own(child, "unselected", "rfam_record") is False
    assert h.client.calls == ["submit_saved_single", "fetch_saved:json"]
    assert h.store.count("observation") == 0
    assert list(h.store.db.iterdump()) == before


def test_results_science_annotation_exact_requested_rows_and_replay(saved, monkeypatch):
    h, schema = saved, schema_for(*FACT_SOURCES)
    science = h.child(h.root, schema)
    child, outcome = h.acquired(science, schema)
    returned = h.returned(science, child)
    forwarded = h.returned(h.root, science)
    forbid_read_work(monkeypatch, h)
    before = list(h.store.db.iterdump())
    assert forwarded == returned
    h.boundary.validate_received_report(child, returned, schema)
    h.boundary.validate_received_report(science, forwarded, schema)
    assert validate_form(forwarded, schema, lambda ref, namespace:
        h.boundary.resolve_received(h.root, ref, namespace)) == forwarded
    for _ in range(2):
        assert h.boundary.record_admission(h.root, forwarded, schema, h.operation(h.root)) == [outcome["result"]["source_ref"]]
        assert h.boundary.received_facts(h.root, schema) == h.boundary.facts(child, schema)
    assert list(h.store.db.iterdump()) == before
    assert h.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("original_source", ["execution_result_refs", "execution_completed", FACT_SOURCES[1]])
def test_reference_or_population_form_does_not_grant_parent_numerical_rows(saved, original_source):
    h = saved
    schema = schema_for(original_source)
    child, outcome = h.acquired(schema=schema)
    facts = h.boundary.facts(child, schema)
    facts.update(execution_result_refs=outcome["record_refs"], execution_completed=True)
    form = h.returned(h.root, child, facts)
    h.receipts.receive(h.root.episode_id, outcome["record_refs"], kind="child_form", source_index=0)
    assert h.boundary.received_facts(h.root, schema_for(FACT_SOURCES[0])) == {FACT_SOURCES[0]: []}
    row = outcome["result"]["projection"]["rows"][0]
    assert h.boundary.resolve_received(h.root, row["record_key"], "rfam_record") is False
    assert h.boundary.record_admission(h.root, form, schema, h.operation(h.root)) == (
        [outcome["result"]["source_ref"]] if original_source == FACT_SOURCES[1] else [])


def test_scientific_original_population_form_does_not_forward_received_rows(saved):
    h = saved
    science = h.child(h.root, schema_for(FACT_SOURCES[1]))
    child, _ = h.acquired(science)
    h.returned(science, child)
    h.returned(h.root, science)
    assert h.boundary.received_facts(science, schema_for(FACT_SOURCES[0]))[FACT_SOURCES[0]]
    assert h.boundary.received_facts(h.root, schema_for(FACT_SOURCES[0])) == {FACT_SOURCES[0]: []}


@pytest.mark.parametrize("table", [False, True])
def test_complete_empty_population_is_returned_without_a_hit(saved, table):
    h = saved
    if table:
        h.client.synthetic_table(empty=True)
    else:
        h.client.synthetic_json(lambda body: body.update(numHits=0, hits={}))
    child, outcome = h.acquired(batch=table)
    form = h.returned(h.root, child)
    h.boundary.record_admission(h.root, form, schema_for(*FACT_SOURCES), h.operation(h.root))
    facts = h.boundary.received_facts(h.root, schema_for(*FACT_SOURCES))
    assert facts[FACT_SOURCES[0]] == []
    assert facts[FACT_SOURCES[1]] == [{"source_ref": outcome["result"]["source_ref"], "family": "hit",
        "available_row_count": 0, "selected_row_count": 0, "more_rows": False, "population_complete": True}]


@pytest.mark.parametrize("mutation", ["partial", "invalid_optional", "invalid_family", "rejected", "malformed"])
def test_missing_partial_and_unavailable_cells_are_preserved(saved, mutation):
    h = saved
    if mutation == "partial":
        h.client.synthetic_json(lambda body: body.update(numHits=2))
    elif mutation == "invalid_optional":
        h.client.synthetic_json(lambda body: body["hits"]["5S_rRNA"][0].update(score="invalid"))
    elif mutation == "invalid_family":
        h.client.synthetic_json(lambda body: body["hits"]["5S_rRNA"][0].update(acc="invalid"))
    elif mutation == "rejected":
        h.client.synthetic_json(lambda body: body.update(searchSequence=""))
    else:
        h.client.synthetic_json(content=b"invalid JSON")
    child, outcome = h.acquired()
    form = h.returned(h.root, child)
    h.boundary.validate_received_report(child, form, schema_for(*FACT_SOURCES))
    facts = h.boundary.received_facts(h.root, schema_for(*FACT_SOURCES))
    if mutation in {"rejected", "malformed"}:
        assert outcome["status"] == "partial" and all(not value for value in facts.values())
    else:
        assert outcome["status"] == "completed"
        row, = facts[FACT_SOURCES[0]]
        if mutation == "partial":
            assert not row["population_complete"]
        elif mutation == "invalid_family":
            assert row["family_accession"] is None and row["measured"] == []
            assert {cell["reason"] for cell in row["unavailable"]} == {"identity_rejected"}
        else:
            assert {"name": "native_score_bits", "reason": "invalid_native_value"} in row["unavailable"]
            assert any(cell["value"] == 1.4e-24 for cell in row["measured"])


@pytest.mark.parametrize("foreign,complete", [(False, True), (True, True), (False, False)])
def test_table_wrapper_query_bindings_and_incomplete_populations(saved, monkeypatch, foreign, complete):
    h = saved
    h.client.synthetic_table(foreign=foreign, complete=complete)
    child, outcome = h.acquired(batch=True)
    assert outcome["result"].get("projection") is not None, outcome
    forbid_read_work(monkeypatch, h)
    facts = h.boundary.facts(child, schema_for(*FACT_SOURCES))
    row, = facts[FACT_SOURCES[0]]
    if foreign:
        assert row["query_occurrence_key"] is None and row["measured"] == []
        assert {cell["reason"] for cell in row["unavailable"]} == {"identity_rejected"}
    else:
        assert row["query_occurrence_key"].startswith("rfam_query_")
        assert any(cell == {"name": "native_score_bits", "value": 104.6, "unit": "bits"} for cell in row["measured"])
    if not complete or foreign:
        assert not row["population_complete"]


def test_original_row_selector_cannot_widen_to_full_saved_sheet(saved):
    h = saved
    def duplicate(body):
        body["hits"]["5S_rRNA"] *= 3
        body["numHits"] = 3
    h.client.synthetic_json(duplicate)
    child, outcome = h.acquired(selected=selector(rows={"offset": 1, "limit": 1}))
    facts = h.boundary.facts(child, schema_for(*FACT_SOURCES))
    assert len(facts[FACT_SOURCES[0]]) == 1
    assert facts[FACT_SOURCES[1]][0]["available_row_count"] == 3
    assert facts[FACT_SOURCES[1]][0]["more_rows"]
    sheet = json.loads(h.store.get_artifact(outcome["result"]["sheet_ref"]))
    assert len(sheet["hits"]) == 3
    assert h.boundary.resolve_own(child, sheet["hits"][0]["hit_id"], "rfam_record") is False
    h.returned(h.root, child)
    assert h.boundary.resolve_received(h.root, sheet["hits"][0]["hit_id"], "rfam_record") is False


@pytest.mark.parametrize("table,complete", [(False, True), (True, True), (True, False)])
def test_query_strand_population_keeps_zero_separate_from_unknown(saved, table, complete):
    h = saved
    if table:
        h.client.synthetic_table(empty=True, complete=complete)
    else:
        h.client.synthetic_json(lambda body: body.update(numHits=0, hits={}))
    child, outcome = h.acquired(batch=table, selected=selector("query_length_nt", "query_strand_union_span_nt",
        "query_strand_union_fraction", family="query_strand", table=table))
    assert outcome["result"]["projection"] is not None
    h.returned(h.root, child)
    rows = h.boundary.received_facts(h.root, schema_for(FACT_SOURCES[0]))[FACT_SOURCES[0]]
    assert len(rows) == (4 if table else 2)
    assert [row["strand"] for row in rows] == (["+", "-"] * (2 if table else 1))
    for row in rows:
        assert json.loads(row["record_key"]) == [row["query_occurrence_key"], row["strand"]]
        measured = {cell["name"]: cell["value"] for cell in row["measured"]}
        assert measured["query_length_nt"] == 119
        assert row["family_accession"] is None and row["population_complete"] is complete
        if complete:
            assert measured["query_strand_union_span_nt"] == measured["query_strand_union_fraction"] == 0
        else:
            assert set(measured) == {"query_length_nt"}
            assert {cell["reason"] for cell in row["unavailable"]} == {"partial_body"}


@pytest.mark.parametrize("table", [False, True])
@pytest.mark.parametrize("metadata", ["missing", "invalid_bundle"])
def test_invalid_optional_metadata_preserves_returnable_native_values(saved, monkeypatch, table, metadata):
    h = saved
    if table:
        h.client.synthetic_table()
    selected = selector(table=table)
    if metadata == "missing":
        selected["model_metadata_ref"] = "source_missing"
    else:
        artifact = h.store.artifact(b"invalid metadata", "application/json")
        selected["model_metadata_ref"] = h.store.put("source", {"provider": "controlled_metadata", "accession": None,
            "uri": None, "artifact_ref": artifact, "text_ref": None, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="caller")["id"]
    child, outcome = h.acquired(selected=selected, batch=table)
    assert outcome["status"] == "completed", outcome
    forbid_read_work(monkeypatch, h)
    facts = h.boundary.facts(child, schema_for(*FACT_SOURCES))
    row, = facts[FACT_SOURCES[0]]
    assert any(cell == {"name": "native_score_bits", "value": 104.6, "unit": "bits"} for cell in row["measured"])
    assert row["unavailable"] == [{"name": "model_coverage_fraction", "reason": "model_metadata_conflict"}]
    grading = h.store.get(outcome["result"]["grading_source_ref"])
    assert (selected["model_metadata_ref"] in grading["parent_source_refs"]) is (metadata == "invalid_bundle")


@pytest.mark.parametrize("field", ["source", "query", "record", "family", "value", "metric", "unit", "reason", "omit", "expand", "population"])
def test_forged_values_reject_even_with_matching_frozen_form_and_attempt(saved, field):
    h, schema = saved, schema_for(*FACT_SOURCES)
    child, _ = h.acquired()
    facts = h.boundary.facts(child, schema)
    row = facts[FACT_SOURCES[0]][0]
    if field in {"source", "query", "record", "family"}:
        row[{"source": "source_ref", "query": "query_occurrence_key", "record": "record_key", "family": "family_accession"}[field]] = "forged"
    elif field == "value":
        row["measured"][0]["value"] += 1
    elif field == "metric":
        row["measured"][0]["name"] = "native_evalue"
    elif field == "unit":
        row["measured"][0]["unit"] = "nt"
    elif field == "reason":
        row["unavailable"][0]["reason"] = "not_reported"
    elif field == "omit":
        facts[FACT_SOURCES[0]] = []
    elif field == "expand":
        facts[FACT_SOURCES[0]].append(deepcopy(row))
    else:
        facts[FACT_SOURCES[1]][0]["available_row_count"] += 1
    form = h.returned(h.root, child, facts)
    with pytest.raises(ValueError, match="rfam_return_returned_facts_conflict"):
        h.boundary.record_admission(h.root, form, schema, h.operation(h.root))
    with pytest.raises(ValueError, match="rfam_return_returned_facts_conflict"):
        h.boundary.received_facts(h.root, schema)


@pytest.mark.parametrize("field", ["scope", "assignment", "role", "purpose", "schema"])
def test_original_selected_commission_is_authoritative(saved, field):
    h, schema = saved, schema_for(*FACT_SOURCES)
    child, _ = h.acquired()
    form = h.returned(h.root, child)
    action = json.loads(h.journal.row("runtime_actions", h.root.episode_id, 0)["action"])
    action[{"schema": "schema_json"}.get(field, field)] = {
        "scope": {"subject_refs": []}, "assignment": {}, "role": "annotation", "purpose": "changed",
        "schema": canonical(schema_for("execution_completed"))}[field]
    h.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(action), h.run_id, h.root.episode_id))
    with pytest.raises(ValueError, match="rfam_return_.*conflict"):
        h.boundary.record_admission(h.root, form, schema, h.operation(h.root))


def test_wrong_child_and_unsupported_owner_cannot_return_received_values(saved):
    h, schema = saved, schema_for(*FACT_SOURCES)
    science = h.child(h.root, schema)
    sibling, outcome = h.acquired(h.root, index=1)
    h.returned(h.root, sibling)
    facts = h.boundary.facts(sibling, schema)
    h.receipts.receive(science.episode_id, outcome["record_refs"], kind="own_action", source_index=0)
    form = form_with_facts({}, schema, facts)
    with pytest.raises(ValueError, match="rfam_return_returned_facts_conflict"):
        h.boundary.validate_received_report(science, form, schema)
    wrong = h.child(h.root, schema, index=2, role="monitor")
    with pytest.raises(ValueError, match="rfam_return_unsupported_return_owner"):
        h.boundary.validate_received_report(wrong, form, schema)
    h.store.db.execute("UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=? AND parent_episode_id=?",
        (science.episode_id, h.run_id, h.root.episode_id))
    with pytest.raises(ValueError, match="rfam_return_"):
        h.boundary.received_facts(h.root, schema)


def test_monitor_parent_cannot_admit_scientific_rfam_rows(saved):
    h, schema = saved, schema_for(*FACT_SOURCES)
    monitor = h.child(h.root, schema, role="monitor")
    child, _ = h.acquired(monitor)
    form = h.returned(monitor, child)
    with pytest.raises(ValueError, match="rfam_return_unsupported_return_owner"):
        h.boundary.record_admission(monitor, form, schema, h.operation(monitor))
    with pytest.raises(ValueError, match="rfam_return_unsupported_return_owner"):
        h.boundary.received_facts(monitor, schema)


def test_exact_redelivery_has_no_new_action_observation_or_fact(saved):
    h, schema = saved, schema_for(*FACT_SOURCES)
    child, outcome = h.acquired()
    h.returned(h.root, child)
    renamed = deepcopy(schema)
    renamed["properties"] = {"forwarded_" + key: value for key, value in renamed["properties"].items()}
    renamed["required"] = list(renamed["properties"])
    form = h.redeliver(h.root, child, renamed)
    before = list(h.store.db.iterdump())
    for _ in range(2):
        assert h.boundary.record_admission(h.root, form, renamed, h.operation(h.root, 1)) == [outcome["result"]["source_ref"]]
    assert len(h.boundary.received_facts(h.root, schema)[FACT_SOURCES[0]]) == 1
    assert h.journal.row("runtime_actions", h.root.episode_id, 1) is None
    assert list(h.store.db.iterdump()) == before


def test_original_form_source_cannot_be_expanded_on_redelivery(saved):
    h = saved
    original = schema_for(FACT_SOURCES[1])
    child, _ = h.acquired(schema=original)
    h.returned(h.root, child)
    schema = schema_for(FACT_SOURCES[0])
    form = h.redeliver(h.root, child, schema, facts={FACT_SOURCES[0]: []})
    with pytest.raises(ValueError, match="rfam_return_(frozen_return_conflict|original_form_source_conflict)"):
        h.boundary.record_admission(h.root, form, schema, h.operation(h.root, 1))


@pytest.mark.parametrize("mutation", ["source_provider", "grading_parent", "submission_request", "manifest", "parse", "sheet", "calculation", "selector", "runtime_value", "publication_value"])
def test_saved_custody_corruption_is_rejected(saved, mutation):
    h = saved
    child, outcome = h.acquired()
    result = outcome["result"]
    grading = h.store.get(result["grading_source_ref"])
    manifest = json.loads(h.store.get_artifact(grading["artifact_ref"]))
    if mutation in {"source_provider", "grading_parent"}:
        value = h.store.get(result["source_ref"] if mutation == "source_provider" else result["grading_source_ref"])
        value["provider" if mutation == "source_provider" else "parent_source_refs"] = "forged" if mutation == "source_provider" else []
        h.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(value), value["id"]))
    elif mutation in {"submission_request", "manifest", "parse", "sheet", "calculation"}:
        reference = (h.store.get(result["submission_source_ref"])["request_ref"] if mutation == "submission_request"
            else grading["artifact_ref"] if mutation == "manifest" else manifest[mutation + "_ref"])
        artifact = h.store.get(reference)
        path = h.store.path / "artifacts" / artifact["sha256"][:2] / artifact["sha256"]
        path.write_bytes(b"{}")
    elif mutation == "selector":
        path = h.api._episode_directory(child.episode_id)/"assignment.json"
        value = json.loads(path.read_text())
        value["assignment"]["selector"]["projection"]["metrics"] = ["native_evalue"]
        path.write_text(canonical(value))
    elif mutation == "runtime_value":
        outcome["result"]["projection"]["rows"][0]["measured"][0]["value"] += 1
        h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(outcome), h.run_id, child.episode_id))
    else:
        key = result["acquisition_receipt"]["operation_key"] + ":publication"
        value = json.loads(h.store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (key,)).fetchone()[0])
        value["result"]["projection"]["rows"][0]["measured"][0]["value"] += 1
        h.store.db.execute("UPDATE tool_operations SET result=? WHERE operation_key=?", (canonical(value), key))
    with pytest.raises(ValueError):
        h.boundary.read(result["source_ref"], h.scope, episode_id=child.episode_id)


def test_wrong_episode_scope_and_unindexed_source_are_not_custody(saved):
    h = saved
    child, outcome = h.acquired()
    for scope, episode in [(h.scope, h.root.episode_id), ({"subject_refs": []}, child.episode_id)]:
        with pytest.raises(ValueError):
            h.boundary.read(outcome["result"]["source_ref"], scope, episode_id=episode)
    artifact = h.store.artifact(b"unacquired", "text/plain")
    source = h.store.put("source", {"provider": "rfam_batch", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": None, "request_ref": None, "version": None, "retrieved_at": None}, origin="external")
    with pytest.raises(ValueError, match="not_an_api_acquired_result"):
        h.boundary.read(source["id"], h.scope)


def test_fact_schemas_are_closed_and_identifier_resolution_is_namespace_specific(saved):
    h = saved
    child, _ = h.acquired()
    h.returned(h.root, child)
    row = h.boundary.received_facts(h.root, schema_for(*FACT_SOURCES))[FACT_SOURCES[0]][0]
    for namespace, key in zip(IDENTIFIER_NAMESPACES, ("record_key", "query_occurrence_key", "family_accession")):
        assert h.boundary.resolve_received(h.root, row[key], namespace) is True
        assert h.boundary.resolve_received(h.root, "unreceived", namespace) is False
    assert h.boundary.resolve_received(h.root, row["source_ref"], "unrelated") is None
    invalid = deepcopy(row)
    invalid["findings"] = "unrestricted text"
    with pytest.raises(ValueError):
        validate_form({"selected_0": [invalid]}, schema_for(FACT_SOURCES[0]), lambda *_: True)
    descriptors = rfam_fact_sources()
    descriptors[FACT_SOURCES[0]]["report_schema"]["items"]["properties"].clear()
    assert rfam_fact_sources()[FACT_SOURCES[0]]["report_schema"]["items"]["properties"]
