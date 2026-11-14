"""Engineering custody controls using real API hosts, Store and typed receipts.

HTTP responses and commission choices are explicit fixtures. No biological
service request, model, workflow continuation, native job or statistic is run.
"""
import asyncio
import base64
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.communication import (ReportBoundaryError, form_with_facts,
    plain, validate_form)
from gene_annotation_episode.enrichr_contracts import enrichr_fact_sources, TABLE_SOURCE, ROW_SOURCE
from gene_annotation_episode.enrichr_returns import (EnrichrReturns, OWN_WITNESSES,
    CLOSURE_PREFIX, requested_enrichr_fields)
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def form_schema(*sources):
    sources = sources or (TABLE_SOURCE, ROW_SOURCE)
    definitions = enrichr_fact_sources()
    fields = {"tables" if source == TABLE_SOURCE else "rows": deepcopy(definitions[source]["report_schema"])
        for source in sources}
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def source_only_schema():
    return {"type": "object", "properties": {
        "sources": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"},
            "x-source": "execution_result_refs"},
        "completed": {"type": "boolean", "x-source": "execution_completed"}},
        "required": ["sources", "completed"], "additionalProperties": False}


class EngineeringHTTP:
    def __init__(self):
        self.calls = []
        self.content = canonical({"Literal library": [
            [1, "literal first term", 0, 2.5, 8, ["A", "A"], 0.25, 0, 0],
            None, [3, "literal last term", 0.02, -1.7, 3, ["a", None, True], 0.5]]}).encode()

    def _http(self, service, url, params, media_type, *, body, content_type,
              accept, max_bytes, timeout_seconds, follow_redirects):
        self.calls.append((service, url, params, body, content_type, max_bytes, timeout_seconds, follow_redirects))
        assert service == "enrichr" and params == {} and follow_redirects is False
        content = b'{"userListId":731,"shortId":"engineering"}' if url.endswith("/addList") else self.content
        headers = {"Accept": accept}
        if content_type is not None:
            headers["Content-Type"] = content_type
        wire = {"method": "POST" if body is not None else "GET", "url": url, "headers": headers}
        if body is not None:
            wire.update(body_base64=base64.b64encode(body).decode(), body_sha256=hashlib.sha256(body).hexdigest())
        return SourceSnapshot("enrichr", url, {}, "2026-10-30T00:00:00+00:00", content,
            "application/json", {"status": 200, "body_complete": True,
                "headers": {"content-type": "application/json"}, "effective_url": url,
                "request": wire, "request_policy": {"timeout_seconds": timeout_seconds,
                    "automatic_redirects": False}, "representation": "http_response_bytes"})


class Harness:
    """Actual configured host; journal commissions are engineering fixtures."""
    def __init__(self, store, directory, *, run_id="enrichr-return-engineering", scope=None, launch=True):
        self.store, self.run_id, self.client = store, run_id, EngineeringHTTP()
        if scope is None:
            subject, = store.create_problem(raw_sequence="MACDEFGHIK", molecule="protein")["subject_refs"]
            self.scope = {"subject_refs": [subject]}
        else:
            self.scope = deepcopy(scope)
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.api = APIServiceExecution(store, run_id=self.run_id, directory=directory,
            configuration={"enrichr": {"kind": "api", "service": "enrichr",
                "protocol_profile": "standard_enrichr_v1", "base_url": "https://enrichr.invalid/Enrichr",
                "timeout": 2, "response_byte_limit": 65536}},
            tool_registry=ToolRegistry(store, clients=self.client), handoff_unit=3, acquired_record_unit=2)
        self.host = EnrichrReturns(self.api)
        self.root = self.context((("annotation", "root"),), {}, None)
        self.request = {"version": "enrichr_request_v1", "protocol_profile": "standard_enrichr_v1",
            "library": "Literal library", "genes": ["A", "a", "A"], "identifier_policy": "literal_no_mapping",
            "species_context": "engineering context", "description": "no biological query",
            "background": {"policy": "service_native", "genes": None}, "native_statistic_profile": "gget_z_label_v1"}
        self.handoff = None
        if launch:
            source = self.context((("launch_api", "fixture"),), {"version": "api_service_assignment_v1",
                "resource_id": "enrichr", "service": "enrichr", "request": self.request,
                "endpoint": "usable_handoff", "constraints": {}}, None)
            outcome = self.action(source, "api.enrichr.query")
            self.handoff = outcome["result"]["handoff_ref"]

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inheritance = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective="Verify actual Enrichr native-return custody", result_contract={"role": path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                objective="Verify actual Enrichr native-return custody", result_contract=contract.schema))
        request = EpisodeRequest(goal, Record({"scope": deepcopy(self.scope), "initial_report": {},
            "episode_assignment": deepcopy(assignment), "knowledge_inheritance": inheritance}), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path), "request": canonical(request),
            "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, parent, *, index=0, role="results", schema=None, offset=0, limit=3):
        schema = form_schema() if schema is None else schema
        contract = TypedReportContract("Return the selected original native Enrichr facts", schema, lambda *_: True)
        assignment = ({"version": "execution_results_assignment_v1", "handoff_ref": self.handoff,
            "selector": {"version": "enrichr_selector_v1", "offset": offset, "limit": limit}}
            if role == "results" else {})
        child = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent)
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical({"kind": "episode_child", "role": role, "assignment": assignment,
                "scope": self.scope, "purpose": contract.decision, "schema_json": canonical(schema)}),
            "result": None, "credit": None})
        return child

    def action(self, context, name="api.enrichr.result", index=0):
        key = f"{self.run_id}:{context.episode_id}:{index}"
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": name, "arguments": {}}), "result": None, "credit": None})
        value = asyncio.run(self.api.execute(context, name, {}, key))
        assert value["status"] in {"completed", "partial"}, value
        self.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(value), self.run_id, context.episode_id, index))
        self.receipts.receive(context.episode_id, value["record_refs"], kind="own_action", source_index=index)
        return value

    def returned(self, parent, child):
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        facts = self.host.facts_for_closure(child, schema)
        form = form_with_facts({}, schema, facts)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        self.host.validate_received_report(child, form, schema)
        index = int(child.path[-1][1].removeprefix("child_"))
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24], "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        references = self.host.record_admission(parent, form, schema, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        self.receipts.receive(parent.episode_id, references, kind="child_form", source_index=index)
        return form


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path / "state") as store:
        yield Harness(store, tmp_path / "run")


@pytest.mark.parametrize("sources", [(TABLE_SOURCE,), (ROW_SOURCE,), (TABLE_SOURCE, ROW_SOURCE)])
def test_original_api_publication_and_actual_source_resolver_preserve_selected_native_cells(case, sources):
    schema = form_schema(*sources)
    child = case.child(case.root, schema=schema)
    outcome = case.action(child)
    facts = case.host.facts(child, schema)
    form = form_with_facts({}, schema, facts)
    assert validate_form(form, schema, lambda ref, namespace: case.host.resolve_own(child, ref, namespace)) == form
    case.host.validate_received_report(child, form, schema)
    reference = outcome["result"]["source_ref"]
    assert case.host.read_own(reference, context=child)["enrichr_values"] == {
        name: outcome["result"][name] for name in (TABLE_SOURCE, ROW_SOURCE)}
    returned = case.returned(case.root, child)
    if TABLE_SOURCE in sources:
        assert returned["tables"][0]["captured_returned_row_count"] == 3
        assert returned["tables"][0]["population"]["effective_universe"] == {"state": "unknown", "value": None}
    if ROW_SOURCE in sources:
        assert [row["ordinal"] for row in returned["rows"]] == [0, 1, 2]
        assert returned["rows"][0]["statistics"]["p_value"]["value"] == 0
        assert returned["rows"][1]["native_kind"] == "null"
        assert returned["rows"][2]["overlap"]["entries"][2]["state"] == "invalid"
        assert returned["rows"][0]["statistic_3_interpretation"]["meaning"] == "unknown"
    assert case.host.resolve_received(case.root, reference, "source") is True
    assert len(case.client.calls) == 2


def test_real_receipts_deliver_source_only_and_explicit_native_file_is_separate(case):
    child = case.child(case.root)
    outcome = case.action(child)
    reference = outcome["result"]["source_ref"]
    source = case.store.get(reference)
    protected = [source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]]
    assert set(case.receipts.known(child.episode_id)) == {reference}
    form = case.returned(case.root, child)
    assert set(case.receipts.known(case.root.episode_id)) == {reference}
    assert all(case.host.resolve_received(case.root, ref, "artifact") is False for ref in protected)
    # Exercise the actual shared receive traversal, not an owner-only verdict.
    case.receipts.receive(case.root.episode_id, [reference], kind="decision_input", source_index=1)
    assert set(case.receipts.known(case.root.episode_id)) == {reference}
    case.receipts.receive(case.root.episode_id, [source["artifact_ref"]], kind="decision_input", source_index=2)
    assert set(case.receipts.known(case.root.episode_id)) == {reference, source["artifact_ref"]}
    assert case.host.resolve_received(case.root, source["artifact_ref"], "artifact") is True
    assert case.host.resolve_received(case.root, source["request_ref"], "artifact") is False
    assert case.host.resolve_received(case.root, source["auxiliary_artifact_refs"][0], "artifact") is False
    assert validate_form(form, form_schema(), lambda ref, namespace: case.host.resolve_received(case.root, ref, namespace)) == form


def test_protocol_stage_artifacts_stay_private_and_unrelated_artifacts_are_unclaimed(case):
    child = case.child(case.root)
    outcome = case.action(child)
    reference = outcome["result"]["source_ref"]
    source = case.store.get(reference)
    witness = case.host.read_own(reference, context=child)["enrichr_witness"]
    stage_refs = [item["artifact_ref"] for item in witness["protocol_artifacts"]]
    assert len(stage_refs) == 2 and stage_refs[-1] == source["artifact_ref"]
    case.returned(case.root, child)
    assert all(ref not in set(case.receipts.known(case.root.episode_id)) for ref in stage_refs)
    for reference in stage_refs:
        assert case.host.resolve_own(child, reference, "artifact") is False
        assert case.host.resolve_received(case.root, reference, "artifact") is False
    unrelated = case.store.artifact(b"independent engineering File")
    assert case.host.resolve_own(child, unrelated, "artifact") is None
    assert case.host.resolve_received(case.root, unrelated, "artifact") is None
    # A source-shaped record without the original API operation cannot taint it.
    payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    payload["auxiliary_artifact_refs"] = [unrelated]
    case.store.put("source", payload, origin="external")
    assert case.host.resolve_received(case.root, unrelated, "artifact") is None
    case.receipts.receive(case.root.episode_id, [source["artifact_ref"]], kind="decision_input", source_index=3)
    assert case.host.resolve_received(case.root, stage_refs[-1], "artifact") is True
    assert case.host.resolve_received(case.root, stage_refs[0], "artifact") is False


def test_foreign_run_source_receipt_never_grants_private_files_in_same_store(case, tmp_path, monkeypatch):
    child = case.child(case.root)
    outcome = case.action(child)
    source = case.store.get(outcome["result"]["source_ref"])
    case.returned(case.root, child)
    control = json.loads(case.store.get_artifact(source["request_ref"]))
    upload_ref = control["transport"]["enrichr_protocol"]["stages"][0]["snapshot"]["content_ref"]
    other = Harness(case.store, tmp_path / "run-b", run_id="enrichr-return-run-b", scope=case.scope, launch=False)
    other.receipts.receive(other.root.episode_id, [source["id"]], kind="initial")
    # The shared Store attachment projection is global; callback None is unsafe.
    for reference in [source["request_ref"], source["auxiliary_artifact_refs"][0]]:
        assert case.store.reference_subset([reference], other.scope) == [reference]
    attached = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    attached.update(provider="engineering_attachment", artifact_ref=upload_ref, request_ref=None,
        auxiliary_artifact_refs=[])
    case.store.put("source", attached, origin="external")
    assert case.store.reference_subset([upload_ref], other.scope) == [upload_ref]
    unrelated = case.store.artifact(b"unrelated run-b File")
    fake = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    fake["auxiliary_artifact_refs"] = [unrelated]
    case.store.put("source", fake, origin="external")
    assert case.store.reference_subset([unrelated], other.scope) == [unrelated]
    def forbidden(*args, **kwargs):
        pytest.fail("foreign privacy classification acquired data or guessed a foreign API path")
    monkeypatch.setattr(other.client, "_http", forbidden)
    monkeypatch.setattr(other.api, "read_result", forbidden)
    monkeypatch.setattr(other.api, "_context", forbidden)
    monkeypatch.setattr(other.api, "_episode_directory", forbidden)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    assert set(other.receipts.known(other.root.episode_id)) == {source["id"]}
    assert other.host.resolve_received(other.root, source["id"], "source") is True
    for reference in [source["request_ref"], source["auxiliary_artifact_refs"][0], upload_ref, source["artifact_ref"]]:
        assert other.host.resolve_received(other.root, reference, "artifact") is False
    assert other.host.resolve_received(other.root, unrelated, "artifact") is None
    assert other.host.received_context(other.root) == {TABLE_SOURCE: [], ROW_SOURCE: []}
    other.receipts.receive(other.root.episode_id, [source["artifact_ref"]], kind="decision_input", source_index=1)
    assert other.host.resolve_received(other.root, source["artifact_ref"], "artifact") is True
    assert other.host.resolve_received(other.root, upload_ref, "artifact") is False
    assert other.client.calls == [] and len(case.client.calls) == 2
    assert not case.store.db.execute("SELECT 1 FROM runtime_actions WHERE run_id=?", (other.run_id,)).fetchall()


def test_unrelated_candidate_does_not_authenticate_damaged_managed_publication(case):
    child = case.child(case.root)
    outcome = case.action(child)
    source = case.store.get(outcome["result"]["source_ref"])
    case.store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (source["auxiliary_artifact_refs"][0],))
    unrelated = case.store.artifact(b"another independent File")
    fake = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    fake["auxiliary_artifact_refs"] = [unrelated]
    case.store.put("source", fake, origin="external")
    assert case.store.reference_subset([unrelated], case.scope) == [unrelated]
    assert case.host.resolve_own(child, unrelated, "artifact") is None
    assert case.host.resolve_received(case.root, unrelated, "artifact") is None


@pytest.mark.parametrize("change", ["row_ordinal_float", "window_offset_float", "p_value_float", "p_value_boolean", "source", "literal"])
def test_changed_saved_values_and_scalar_type_substitutions_are_rejected(case, change):
    child = case.child(case.root)
    case.action(child)
    form = case.returned(case.root, child)
    changed = deepcopy(form)
    if change == "row_ordinal_float":
        changed["rows"][0]["ordinal"] = 0.0
    elif change == "window_offset_float":
        changed["tables"][0]["window"]["offset"] = 0.0
    elif change == "p_value_float":
        changed["rows"][0]["statistics"]["p_value"]["value"] = 0.0
    elif change == "p_value_boolean":
        changed["rows"][0]["statistics"]["p_value"]["value"] = False
    elif change == "source":
        changed["rows"][0]["source_ref"] = "source_" + "0" * 24
    else:
        changed["rows"][0]["term"]["value"] = "invented biology"
    if change in {"row_ordinal_float", "window_offset_float", "p_value_float"}:
        assert Draft202012Validator(form_schema()).is_valid(changed)
    with pytest.raises(ReportBoundaryError):
        case.host.validate_received_report(child, changed, form_schema())


@pytest.mark.parametrize("change", ["schema", "context", "tool_name", "tool_arguments", "runtime_result", "raw_bytes", "request_bytes", "grade_bytes",
    "raw_metadata", "request_metadata", "grade_metadata"])
def test_original_commission_publication_and_files_are_authenticated(case, change):
    child = case.child(case.root)
    outcome = case.action(child)
    reference = outcome["result"]["source_ref"]
    source = case.store.get(reference)
    if change == "schema":
        schema = form_schema(); schema["properties"]["rows"]["items"]["properties"]["ordinal"]["minimum"] = 1
        with pytest.raises(ReportBoundaryError, match="original_schema_conflict"):
            case.host.facts(child, schema)
        return
    if change == "context":
        changed = replace(child, assignment={**plain(child.assignment), "selector": {"version": "enrichr_selector_v1", "offset": 1, "limit": 1}})
        with pytest.raises(ReportBoundaryError, match="original_context_conflict"):
            case.host.read_own(reference, context=changed)
        return
    key = outcome["result"]["acquisition_receipt"]["operation_key"]
    if change in {"tool_name", "tool_arguments"}:
        column, value = ("name", "internal.api_service.other") if change == "tool_name" else ("arguments", canonical({}))
        case.store.db.execute("UPDATE tool_operations SET " + column + "=? WHERE operation_key=?", (value, key + ":publication"))
    elif change == "runtime_result":
        modified = deepcopy(outcome); modified["record_refs"] = []
        case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(modified), case.run_id, child.episode_id))
    elif change.endswith("_metadata"):
        ref = {"raw_metadata": source["artifact_ref"], "request_metadata": source["request_ref"],
            "grade_metadata": source["auxiliary_artifact_refs"][0]}[change]
        case.store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (ref,))
    else:
        ref = {"raw_bytes": source["artifact_ref"], "request_bytes": source["request_ref"],
            "grade_bytes": source["auxiliary_artifact_refs"][0]}[change]
        sha = ref.removeprefix("artifact_")
        (case.store.path / "artifacts" / sha[:2] / sha).write_bytes(b"mutated")
    with pytest.raises((ReportBoundaryError, ValueError)):
        case.host.read_own(reference, context=child)


def test_raw_source_resemblance_without_original_api_publication_is_not_authority(case):
    child = case.child(case.root)
    outcome = case.action(child)
    source = case.store.get(outcome["result"]["source_ref"])
    payload = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
    payload["uri"] += "&forged=true"
    forged = case.store.put("source", payload, origin="external")
    with pytest.raises(ReportBoundaryError):
        case.host.read_own(forged["id"], context=child)
    assert case.host.resolve_received(case.root, forged["id"], "source") is None


def test_saved_unadmitted_form_cannot_bypass_raw_verification(case):
    child = case.child(case.root)
    outcome = case.action(child)
    facts = case.host.facts(child, form_schema())
    case.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts),
        "form": canonical(form_with_facts({}, form_schema(), facts))})
    with pytest.raises(ReportBoundaryError, match="frozen_prefix_conflict"):
        case.host.read_own(outcome["result"]["source_ref"], context=child, verify_artifacts=False)


def test_runtime_pending_wrapper_is_validated_before_exact_outcome_comparison(case):
    child = case.child(case.root)
    outcome = case.action(child)
    wrapped = deepcopy(outcome)
    wrapped["pending_work_after_action"] = {"version": "pending_work_v1",
        "captured_at": "2026-10-30T00:00:00+00:00", "items": []}
    case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(wrapped), case.run_id, child.episode_id))
    assert case.host.read_own(outcome["result"]["source_ref"], context=child)["source_ref"] == outcome["result"]["source_ref"]
    wrapped["pending_work_after_action"]["captured_at"] = "not a timestamp"
    case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(wrapped), case.run_id, child.episode_id))
    with pytest.raises(ReportBoundaryError):
        case.host.read_own(outcome["result"]["source_ref"], context=child)


def test_closed_native_and_grade_withdrawal_uses_original_witness_without_parsing_or_work(case, monkeypatch):
    child = case.child(case.root)
    outcome = case.action(child)
    form = case.returned(case.root, child)
    source = case.store.get(outcome["result"]["source_ref"])
    forbidden_refs = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
    witness = json.loads(case.journal.row("runtime_forms", child.episode_id)["facts"])[OWN_WITNESSES]["publications"][0]
    forbidden_refs.update(item["artifact_ref"] for item in witness["protocol_artifacts"])
    for reference in forbidden_refs:
        sha = reference.removeprefix("artifact_")
        (case.store.path / "artifacts" / sha[:2] / sha).unlink()
    original_reader = case.store.get_artifact
    def read_control_only(reference):
        assert reference not in forbidden_refs, "closed return consumed scientific bytes"
        return original_reader(reference)
    def no_work(*args, **kwargs):
        pytest.fail("closed return parsed native data or acquired/calculated again")
    monkeypatch.setattr(case.store, "get_artifact", read_control_only)
    monkeypatch.setattr("gene_annotation_episode.enrichr_returns.project_enrichr_return", no_work)
    monkeypatch.setattr("gene_annotation_episode.enrichr_returns.validate_enrichr_sheet", no_work)
    monkeypatch.setattr(case.client, "_http", no_work)
    before = [tuple(row) for row in case.store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id,decision_index")]
    assert case.host.facts(child, form_schema())[TABLE_SOURCE] == form["tables"]
    assert case.host.facts(child, form_schema())[ROW_SOURCE] == form["rows"]
    case.host.validate_received_report(child, form, form_schema())
    assert case.host.received_context(case.root)[ROW_SOURCE] == form["rows"]
    for item in witness["protocol_artifacts"]:
        assert case.host.resolve_received(case.root, item["artifact_ref"], "artifact") is False
    assert before == [tuple(row) for row in case.store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id,decision_index")]
    assert len(case.client.calls) == 2


def test_historical_preproof_is_nonrecursive_and_reads_no_artifact_bytes(case, monkeypatch):
    child = case.child(case.root)
    outcome = case.action(child)
    case.returned(case.root, child)
    reference = outcome["result"]["source_ref"]
    key = outcome["result"]["acquisition_receipt"]["operation_key"]
    expected = json.loads(case.journal.row("runtime_forms", child.episode_id)["facts"])[OWN_WITNESSES]["publications"][0]
    def forbidden(*args, **kwargs):
        pytest.fail("historical preproof recursed into API/handoff or read scientific bytes")
    monkeypatch.setattr(case.api, "read_result", forbidden)
    monkeypatch.setattr(case.api, "_context", forbidden)
    monkeypatch.setattr(case.host, "read_own", forbidden)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    monkeypatch.setattr("gene_annotation_episode.enrichr_returns.project_enrichr_return", forbidden)
    monkeypatch.setattr("gene_annotation_episode.enrichr_returns.validate_enrichr_sheet", forbidden)
    assert case.host.historical_result_witness(reference, context=child, operation_key=key) == expected


@pytest.mark.parametrize("saved_form", [False, True])
def test_unadmitted_historical_preproof_fails_before_artifact_or_api_access(case, monkeypatch, saved_form):
    child = case.child(case.root)
    outcome = case.action(child)
    if saved_form:
        facts = case.host.facts(child, form_schema())
        case.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts),
            "form": canonical(form_with_facts({}, form_schema(), facts))})
    def forbidden(*args, **kwargs):
        pytest.fail("unadmitted historical request reached API or scientific bytes")
    monkeypatch.setattr(case.api, "read_result", forbidden)
    monkeypatch.setattr(case.api, "_context", forbidden)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    with pytest.raises(ReportBoundaryError, match="frozen_prefix_conflict"):
        case.host.historical_result_witness(outcome["result"]["source_ref"], context=child,
            operation_key=outcome["result"]["acquisition_receipt"]["operation_key"])


@pytest.mark.parametrize("change", ["source", "key", "context", "frozen_scalar"])
def test_historical_preproof_rejects_substituted_original_identity_and_saved_values(case, change):
    child = case.child(case.root)
    outcome = case.action(child)
    case.returned(case.root, child)
    reference = outcome["result"]["source_ref"]
    key = outcome["result"]["acquisition_receipt"]["operation_key"]
    if change == "source":
        reference = "source_" + "0" * 24
    elif change == "key":
        key = f"{case.run_id}:{child.episode_id}:99"
    elif change == "context":
        child = replace(child, assignment={**plain(child.assignment), "selector": {
            "version": "enrichr_selector_v1", "offset": 1, "limit": 1}})
    else:
        row = case.journal.row("runtime_forms", child.episode_id)
        facts, form = json.loads(row["facts"]), json.loads(row["form"])
        facts[ROW_SOURCE][0]["statistics"]["p_value"]["value"] = 0.0
        form["rows"][0]["statistics"]["p_value"]["value"] = 0.0
        case.store.db.execute("UPDATE runtime_forms SET facts=?,form=? WHERE run_id=? AND episode_id=?",
            (canonical(facts), canonical(form), case.run_id, child.episode_id))
    with pytest.raises(ReportBoundaryError):
        case.host.historical_result_witness(reference, context=child, operation_key=key)


def test_closed_parent_prefix_excludes_later_delivery_and_detects_attempt_tampering(case):
    parent = case.child(case.root, role="scientific_process")
    first = case.child(parent)
    case.action(first)
    first_form = case.returned(parent, first)
    late = case.child(parent, index=1, offset=2, limit=1)
    case.action(late)
    closed = case.returned(case.root, parent)
    saved = case.journal.row("runtime_forms", parent.episode_id)["facts"]
    case.returned(parent, late)
    assert case.host.facts_for_closure(parent, form_schema())[ROW_SOURCE] == first_form["rows"] == closed["rows"]
    assert case.journal.row("runtime_forms", parent.episode_id)["facts"] == saved
    assert [x["decision_index"] for x in json.loads(saved)[CLOSURE_PREFIX]["attempts"]] == [0]
    case.store.db.execute("UPDATE runtime_report_attempts SET delivery_ref='substituted' WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
        (case.run_id, parent.episode_id))
    with pytest.raises(ReportBoundaryError, match="frozen_prefix_conflict"):
        case.host.facts_for_closure(parent, form_schema())
    assert len(case.client.calls) == 2


def test_child_inherits_only_received_report_prefix_at_its_actual_creation(case):
    earlier = case.child(case.root, role="scientific_process", index=0)
    results = case.child(case.root, index=1)
    case.action(results)
    form = case.returned(case.root, results)
    later = case.child(case.root, role="scientific_process", index=2)
    assert case.host.received_context(earlier)[ROW_SOURCE] == []
    assert case.host.received_context(later)[ROW_SOURCE] == form["rows"]
    source_ref = form["rows"][0]["source_ref"]
    assert case.host.resolve_received(earlier, source_ref, "source") is False
    assert case.host.resolve_received(later, source_ref, "source") is True


@pytest.mark.parametrize("key", ["tool_operation_sha256", "snapshot_metadata_sha256", "projected_sha256"])
def test_closed_original_witness_tampering_is_rejected(case, key):
    child = case.child(case.root)
    case.action(child)
    case.returned(case.root, child)
    row = case.journal.row("runtime_forms", child.episode_id)
    facts = json.loads(row["facts"])
    facts[OWN_WITNESSES]["publications"][0][key] = "0" * 64
    case.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
        (canonical(facts), case.run_id, child.episode_id))
    with pytest.raises(ReportBoundaryError, match="frozen_prefix_conflict"):
        case.host.facts(child, form_schema())


def test_only_exact_full_source_schemas_are_recognized():
    assert requested_enrichr_fields(form_schema()) == {"tables": TABLE_SOURCE, "rows": ROW_SOURCE}
    assert requested_enrichr_fields({"type": "object", "properties": {}, "required": [], "additionalProperties": False}) == {}
    changed = form_schema(); changed["properties"]["rows"]["items"]["properties"]["term"]["properties"]["value"]["format"] = "reference"
    with pytest.raises(ReportBoundaryError, match="original_schema_conflict"):
        requested_enrichr_fields(changed)


def test_source_only_partial_return_captures_actual_api_witness_and_closed_preproof(case, monkeypatch):
    schema = source_only_schema()
    child = case.child(case.root, schema=schema)
    outcome = case.action(child)
    assert outcome["status"] == "partial"
    reference = outcome["result"]["source_ref"]
    key = outcome["result"]["acquisition_receipt"]["operation_key"]
    facts = case.api.facts(child, {})
    assert facts["execution_result_refs"] == [reference] and facts["execution_completed"] is False
    assert not any(source in facts for source in (TABLE_SOURCE, ROW_SOURCE))
    witness = facts[OWN_WITNESSES]["publications"][0]
    assert witness["source_ref"] == reference and witness["operation_key"] == key
    assert case.host.facts_for_closure(child, schema) == {OWN_WITNESSES: facts[OWN_WITNESSES]}
    form = form_with_facts({}, schema, facts)
    assert form == {"sources": [reference], "completed": False}
    assert validate_form(form, schema, lambda ref, namespace: case.host.resolve_own(child, ref, namespace)) == form
    case.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
    contract = plain(child.request)["report_contract"]
    case.journal.save("runtime_report_attempts", {"parent_episode_id": case.root.episode_id, "decision_index": 0,
        "delivery_ref": "delivery_" + digest([case.root.episode_id, 0])[:24], "child_episode_id": child.episode_id,
        "contract": canonical(contract), "form": canonical(form), "failure": None})
    assert case.host._successful_closed(child) is True
    assert reference not in case.receipts.known(case.root.episode_id)
    admitted = case.host.record_admission(case.root, form, schema, f"{case.run_id}:{case.root.episode_id}:0:typed_form")
    assert admitted == [reference]  # Proved before a parent receipt exists.
    case.receipts.receive(case.root.episode_id, admitted, kind="child_form", source_index=0)
    assert set(case.receipts.known(case.root.episode_id)) == {reference}
    private_refs = {witness[name] for name in ("native_artifact_ref", "request_artifact_ref", "grading_artifact_ref")}
    private_refs.update(item["artifact_ref"] for item in witness["protocol_artifacts"])
    for ref in private_refs:
        sha = ref.removeprefix("artifact_")
        (case.store.path / "artifacts" / sha[:2] / sha).unlink()
    before = {table: [tuple(row) for row in case.store.db.execute("SELECT * FROM " + table + " ORDER BY rowid")]
        for table in ("runtime_actions", "runtime_forms", "runtime_report_attempts", "tool_operations")}
    def forbidden(*args, **kwargs):
        pytest.fail("Source-only closed preproof read bytes, recursed or performed new work")
    monkeypatch.setattr(case.api, "read_result", forbidden)
    monkeypatch.setattr(case.api, "_context", forbidden)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    monkeypatch.setattr(case.client, "_http", forbidden)
    monkeypatch.setattr("gene_annotation_episode.enrichr_returns.project_enrichr_return", forbidden)
    monkeypatch.setattr("gene_annotation_episode.enrichr_returns.validate_enrichr_sheet", forbidden)
    assert case.host.historical_result_witness(reference, context=child, operation_key=key) == witness
    assert case.host.record_admission(case.root, form, schema,
        f"{case.run_id}:{case.root.episode_id}:0:typed_form") == [reference]
    assert before == {table: [tuple(row) for row in case.store.db.execute("SELECT * FROM " + table + " ORDER BY rowid")]
        for table in before}
    assert len(case.client.calls) == 2


@pytest.mark.parametrize("empty_witness", [False, True])
def test_source_only_empty_publication_cannot_manufacture_a_closed_proof(case, empty_witness):
    schema = source_only_schema()
    child = case.child(case.root, schema=schema)
    assert case.host.facts(child, schema) == {}
    facts = case.api.facts(child, {})
    assert facts["execution_result_refs"] == [] and OWN_WITNESSES not in facts
    if empty_witness:
        facts[OWN_WITNESSES] = {"version": OWN_WITNESSES, "publications": []}
    form = form_with_facts({}, schema, facts)
    case.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
    contract = plain(child.request)["report_contract"]
    case.journal.save("runtime_report_attempts", {"parent_episode_id": case.root.episode_id, "decision_index": 0,
        "delivery_ref": "delivery_" + digest([case.root.episode_id, 0])[:24], "child_episode_id": child.episode_id,
        "contract": canonical(contract), "form": canonical(form), "failure": None})
    assert case.host._successful_closed(child) is False
    assert case.host.record_admission(case.root, form, schema,
        f"{case.run_id}:{case.root.episode_id}:0:typed_form") == []
    with pytest.raises(ReportBoundaryError, match="frozen_prefix_conflict"):
        case.host.historical_result_witness("source_" + "0" * 24, context=child,
            operation_key=f"{case.run_id}:{child.episode_id}:0")


def test_standard_source_reference_field_requires_actual_execution_result_namespace(case):
    schema = source_only_schema()
    schema["properties"]["sources"]["items"]["x-reference-namespace"] = "artifact"
    with pytest.raises(ReportBoundaryError, match="original_schema_conflict"):
        case.host.record_admission(case.root, {"sources": [], "completed": False}, schema,
            f"{case.run_id}:{case.root.episode_id}:0:typed_form")
