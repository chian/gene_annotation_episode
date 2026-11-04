"""Controlled host/journal fixtures with real API acquisition/publication code.

These are not Workflow, controller or communication-compiler tests. Commissions
and closure callbacks are supplied explicitly here because shared integration
is a later slice. The public retained page is replayed without network; inline
bases are engineering input, not authenticated Addgene acquisition.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import socket

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode import addgene_sequence_returns as returns
from gene_annotation_episode import addgene_sequence_native as native
from gene_annotation_episode.acquisition import PublicClients, SourceSnapshot
from gene_annotation_episode.addgene_sequence_facts import FACT_SOURCE, ADDGENE_SEQUENCE_FACTS_SCHEMA
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.api_sequence_support import COLLECT
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.form_reference_validation import form_reference_validation
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


pytestmark = pytest.mark.skipif("HMMER529_ATTEMPT" not in os.environ, reason="requires bounded529")
FIXTURES = Path(__file__).parent / "fixtures/addgene_sequence_page"
ENTITY_SHA = "deb0393a4b1c71ae21e438a7dd2a6f410defbc83c3e939c2ce10faf0b4b30c4d"
METADATA_SHA = "ae1e05538cb541d5e1ad6a6610e690204e8d426066ba6432494c72ef62aa0e06"


def schema():
    return {"type": "object", "additionalProperties": False, "required": ["metadata"],
        "properties": {"metadata": deepcopy(ADDGENE_SEQUENCE_FACTS_SCHEMA)}}


def forbidden(*args, **kwargs):
    raise AssertionError("closed Addgene return reopened native/private data or acquisition")


def engineering_source(store, *, provider, uri, body, media_type="text/html"):
    """Caller fixture with stored provenance; no API producer or tool publication."""
    provenance = store.artifact(canonical({"fixture_version": "uncommissioned_source_fixture_v1",
        "origin": "caller", "purpose": "engineering Source resemblance without acquisition authority",
        "api_producer": None, "tool_operation": None}), "application/json")
    return store.put("source", {"provider": provider, "accession": "engineering-uncommissioned",
        "uri": uri, "artifact_ref": store.artifact(body, media_type), "text_ref": None,
        "request_ref": provenance, "version": "engineering-source-fixture-v1", "retrieved_at": None}, origin="caller")


class RetainedClient(PublicClients):
    """Synthetic transport envelope over retained bytes; no HTTP is performed."""
    def __init__(self, body):
        super().__init__(ncbi_email=None)
        self.body, self.calls = body, []

    def _http(self, service, url, params, media_type, *, max_bytes):
        assert not self.calls, "collection or return unexpectedly reacquired the page"
        assert (service, url, params, media_type) == (
            "addgene", "https://www.addgene.org/50005/sequences/", {}, "text/html")
        self.calls.append((service, url, deepcopy(params), max_bytes))
        return SourceSnapshot(service, url, params, "2026-10-29T00:00:00+00:00", self.body, media_type,
            {"status": 200, "body_complete": True, "response_byte_limit": max_bytes,
             "request": {"method": "GET", "url": url}})


class HostCase:
    """Real API host; parent decisions and runtime journal closure are controlled."""
    def __init__(self, directory, *, body=None):
        self.store = Store(directory / "store")
        self.run_id = "addgene-return-host-engineering"
        self.scope = {"subject_refs": self.store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        self.journal = Journal(self.store, self.run_id)
        self.receipts = EpisodeReceipts(self.store, self.run_id)
        if body is None:
            body = (FIXTURES / "addgene50005.entity").read_bytes()
        self.client = RetainedClient(body)
        self.tools = ToolRegistry(self.store, clients=self.client)
        self.api = APIServiceExecution(self.store, run_id=self.run_id, directory=directory,
            configuration={"addgene": {"kind": "api", "service": "sequence_support"}},
            tool_registry=self.tools, handoff_unit=3, acquired_record_unit=2)
        self.host = returns.AddgeneSequenceReturns(self.api)
        self.root = self.context((("annotation", "root"),), {}, schema())
        request = {"operation": "get_plasmid_sequence", "provider": "addgene",
            "plasmid_id": "50005", "max_bytes": 4194304}
        launch = self.context((("launch_api", "engineering-launch"),), {
            "version": "api_service_assignment_v1", "resource_id": "addgene", "service": "sequence_support",
            "request": request, "endpoint": "usable_handoff", "constraints": {}}, None)
        self.handoff = self.action(launch, name="get_plasmid_sequence")["result"]["handoff_ref"]
        self.parent = self.child(self.root, role="scientific_process")

    def context(self, path, assignment, form, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inheritance = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        contract = None if form is None else {"decision": "Return the assigned original Addgene metadata",
            "measurements": {"schema": deepcopy(form)}}
        request = {"message": {"scope": deepcopy(self.scope), "episode_assignment": deepcopy(assignment),
            "initial_report": {}, "knowledge_inheritance": inheritance}, "report_contract": contract}
        context = BindingContext(self.run_id, episode_id, path[-1][0], path,
            deepcopy(self.scope), deepcopy(assignment), request)
        self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, parent, *, index=0, role="results", choices=(2, 0, 99), form=None):
        form = schema() if form is None else form
        assignment = ({"version": "execution_results_assignment_v1", "handoff_ref": self.handoff,
            "selector": {"view": "sequences", "record_ordinals": list(choices)}} if role == "results" else {})
        context = self.context((*parent.path, (role, "child_" + str(index))), assignment, form, parent)
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical({"kind": "episode_child", "role": role, "assignment": assignment,
                "scope": deepcopy(self.scope), "purpose": context.request["report_contract"]["decision"],
                "schema_json": canonical(form)}), "result": None, "credit": None})
        return context

    def action(self, context, *, index=0, name=COLLECT):
        key = f"{self.run_id}:{context.episode_id}:{index}"
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": name, "arguments": {}}), "result": None, "credit": None})
        outcome = asyncio.run(self.api.execute(context, name, {}, key))
        assert outcome["status"] in {"completed", "partial"}, outcome
        self.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(outcome), self.run_id, context.episode_id, index))
        self.receipts.receive(context.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
        return outcome

    def freeze(self, context):
        form_schema = context.request["report_contract"]["measurements"]["schema"]
        facts = self.host.facts_for_closure(context, form_schema)
        form = {name: deepcopy(facts[node["x-source"]]) for name, node in form_schema["properties"].items()}
        self.journal.save("runtime_forms", {"episode_id": context.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        self.store.db.execute("UPDATE runtime_episodes SET state='yielded',completion=? WHERE run_id=? AND episode_id=?",
            (canonical({"ended_by": "yield", "actions": 1}), self.run_id, context.episode_id))
        self.host.validate_report(context, form, form_schema)
        return facts, form

    def returned(self, parent, child):
        facts, form = self.freeze(child)
        contract = child.request["report_contract"]
        form_schema = contract["measurements"]["schema"]
        index = int(child.path[-1][1].removeprefix("child_"))
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "child_episode_id": child.episode_id,
            "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24],
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        refs = self.host.record_admission(parent, form, form_schema,
            f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        self.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        self.store.db.execute("UPDATE runtime_actions SET result=?,credit=0 WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical({"status": "completed", "record_refs": refs, "changed_record_refs": refs}),
             self.run_id, parent.episode_id, index))
        return facts, form, refs

    def saved(self, context):
        return self.journal.row("runtime_forms", context.episode_id)


@pytest.fixture
def case(tmp_path):
    value = HostCase(tmp_path)
    yield value
    value.store.db.close()


def test_original_selected_partial_metadata_and_closure_are_separate_from_completion(case):
    assert hashlib.sha256((FIXTURES / "addgene50005.entity").read_bytes()).hexdigest() == ENTITY_SHA
    assert hashlib.sha256((FIXTURES / "addgene50005.json").read_bytes()).hexdigest() == METADATA_SHA
    child = case.child(case.parent)
    outcome = case.action(child)
    public = case.host.facts(child, schema())
    assert set(public) == {FACT_SOURCE}, "private closure witnesses must not enter execution_progress"
    fact, = public[FACT_SOURCE]
    assert [row["record_ordinal"] for row in fact["selected_rows"]] == [2, 0, 99]
    assert [row["status"] for row in fact["selected_rows"]] == ["authentication_required", "authentication_required", "unavailable"]
    assert fact["authentication_required"] is True and all(row["symbol_count"] is None for row in fact["selected_rows"])
    assert outcome["status"] == "partial" and case.api._completion(child) is None
    assert case.api.facts(child, {})["execution_completed"] is False
    frozen, form, refs = case.returned(case.parent, child)
    assert set(frozen) == {FACT_SOURCE, returns.OWN_BINDINGS} and refs == [fact["source_ref"]]
    assert case.host.received_facts(case.parent, schema()) == public
    assert set(case.host.received_context(case.parent)) == {FACT_SOURCE}
    assert len(case.client.calls) == 1
    assert case.host.resolve_own(child, fact["source_ref"], "source") is True
    assert case.host.resolve_received(case.parent, fact["source_ref"], "execution_result") is True
    assert case.host.resolve_received(case.parent, fact["source_ref"], "artifact") is False
    assert form == {"metadata": public[FACT_SOURCE]}


def test_exact_selected_views_survive_one_native_acquisition_identity(case):
    first = case.child(case.parent)
    first_outcome = case.action(first)
    _, first_form, _ = case.returned(case.parent, first)
    second = case.child(case.parent, index=1, choices=(0,))
    second_outcome = case.action(second)
    _, second_form, _ = case.returned(case.parent, second)
    assert first_outcome["result"]["source_ref"] == second_outcome["result"]["source_ref"]
    assert first_form != second_form
    rows = case.host.received_facts(case.parent, schema())[FACT_SOURCE]
    assert [[row["record_ordinal"] for row in view["selected_rows"]] for view in rows] == [[2, 0, 99], [0]]
    source = rows[0]["source_ref"]
    assert case.api.result_identity(source, case.scope) == case.api.result_identity(rows[1]["source_ref"], case.scope)
    selection = {"known_record_refs": [source], "initial_known_record_refs": []}
    assert case.api.credit_view(first, selection)["new_acquired_record_count"] == 1
    assert case.api.credit_view(second, {**selection, "initial_known_record_refs": [source]})["new_acquired_record_count"] == 0
    assert len(case.client.calls) == 1
    third = case.child(case.parent, index=2)
    case.action(third)
    case.returned(case.parent, third)
    assert case.host.received_facts(case.parent, schema())[FACT_SOURCE] == rows


@pytest.mark.parametrize("fault", ["source", "view", "bool_ordinal", "status", "count", "extra", "native_label"])
def test_candidate_typed_metadata_cannot_replace_original_selected_facts(case, fault):
    child = case.child(case.parent)
    case.action(child)
    form = {"metadata": deepcopy(case.host.facts(child, schema())[FACT_SOURCE])}
    fact = form["metadata"][0]
    if fault == "source": fact["source_ref"] = "source_" + "f" * 24
    elif fault == "view": fact["selected_rows"].pop()
    elif fault == "bool_ordinal": fact["selected_rows"][0]["selection_ordinal"] = False
    elif fault == "status": fact["selected_rows"][0]["status"] = "available"
    elif fault == "count": fact["selected_rows"][0]["symbol_count"] = 0
    elif fault == "native_label": fact["selected_rows"][0]["native_record"]["section_id"] = "forged-section"
    else: fact["unit"] = "bases"
    before = case.store.db.total_changes
    with pytest.raises(ValueError):
        case.host.validate_report(child, form, schema())
    assert case.store.db.total_changes == before


@pytest.mark.parametrize("fault", ["items", "source_alias", "extra_schema", "field_alias"])
def test_only_the_exact_declared_source_schema_is_accepted(case, fault):
    child = case.child(case.parent)
    selected = schema()
    if fault == "items": selected["properties"]["metadata"]["items"] = {"type": "object"}
    elif fault == "source_alias": selected["properties"]["metadata"]["x-source"] = "execution_addgene_alternative"
    elif fault == "extra_schema": selected["properties"]["metadata"]["description"] = "changed contract"
    else: selected["properties"]["alias"] = selected["properties"].pop("metadata")
    with pytest.raises(ValueError):
        case.host.facts(child, selected)


@pytest.mark.parametrize("fault", ["handoff", "selector", "operation", "snapshot", "source", "publication"])
def test_live_original_acquisition_and_publication_cannot_be_substituted(case, fault):
    child = case.child(case.parent)
    outcome = case.action(child)
    changed = deepcopy(outcome)
    receipt = changed["result"]["acquisition_receipt"]
    if fault == "handoff": receipt["handoff_ref"] = "source_" + "a" * 24
    elif fault == "selector": receipt["selector"]["record_ordinals"] = [0]
    elif fault == "operation": receipt["operation_key"] += ":forged"
    elif fault == "snapshot": receipt["snapshot_sha256"] = "0" * 64
    elif fault == "source": receipt["source_ref"] = "source_" + "a" * 24
    else: changed["result"]["sequence_support_ref"] = case.store.artifact("{}", "application/json")
    case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
        (canonical(changed), case.run_id, child.episode_id))
    with pytest.raises(ValueError):
        case.host.facts(child, schema())


@pytest.mark.parametrize("fault", ["fact", "view", "binding", "ordinal_bool", "outcome", "commission", "form"])
def test_frozen_original_facts_action_and_commission_bindings_reject_tampering(case, fault):
    child = case.child(case.parent)
    case.action(child)
    frozen, form, _ = case.returned(case.parent, child)
    if fault in {"fact", "view", "binding", "ordinal_bool"}:
        if fault == "fact": frozen[FACT_SOURCE][0]["requested_id"] = "50006"
        elif fault == "view": frozen[FACT_SOURCE][0]["selected_rows"].pop()
        elif fault == "binding": frozen[returns.OWN_BINDINGS]["acquisitions"][0]["outcome_sha256"] = "0" * 64
        else: frozen[returns.OWN_BINDINGS]["acquisitions"][0]["decision_index"] = False
        if fault in {"fact", "view"}: form["metadata"] = deepcopy(frozen[FACT_SOURCE])
        case.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(frozen), "form": canonical(form)})
    elif fault == "outcome":
        outcome = json.loads(case.journal.row("runtime_actions", child.episode_id, 0)["result"])
        outcome["result"]["acquisition_receipt"]["finished_at"] += "forged"
        case.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(outcome), case.run_id, child.episode_id))
    elif fault == "commission":
        action = json.loads(case.journal.row("runtime_actions", case.parent.episode_id, 0)["action"])
        action["assignment"]["selector"]["record_ordinals"] = [0]
        case.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(action), case.run_id, case.parent.episode_id))
    else:
        form["metadata"][0]["requested_id"] = "50006"
        case.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
            (canonical(form), case.run_id, case.parent.episode_id))
    with pytest.raises(ValueError):
        case.host.received_facts(case.parent, schema())


def test_closed_reads_need_no_raw_artifact_publication_parser_or_reprojection(case, monkeypatch):
    child = case.child(case.parent)
    case.action(child)
    _, form, refs = case.returned(case.parent, child)
    case.returned(case.root, case.parent)
    expected = {FACT_SOURCE: form["metadata"]}
    before = case.store.db.total_changes
    for owner, name in ((case.api, "read_result"), (case.store, "get_artifact"),
            (returns, "read_sequence_support_publication"), (returns, "build_addgene_sequence_fact"),
            (native, "read_addgene_sequences"), (native, "validate_addgene_sequence_page"),
            (Path, "read_bytes"), (Path, "read_text"), (PublicClients, "_http"), (socket, "create_connection")):
        monkeypatch.setattr(owner, name, forbidden)
    assert case.host.facts(child, schema()) == expected
    assert case.host.received_facts(case.parent, schema()) == expected
    assert case.host.received_facts(case.root, schema()) == expected
    assert case.host.recorded_admission_references(case.parent, form, schema(), 0) == refs
    assert case.host.resolve_received(case.root, refs[0], "source") is True
    assert case.store.db.total_changes == before


def test_receiver_closure_and_onward_inheritance_keep_the_original_received_prefix(case):
    first = case.child(case.parent)
    case.action(first)
    _, first_form, _ = case.returned(case.parent, first)
    case.returned(case.root, case.parent)
    onward = case.child(case.root, index=1, role="scientific_process")
    initial = case.host.received_context(onward)
    assert initial[FACT_SOURCE] == first_form["metadata"]
    other = case.child(case.root, index=2, role="scientific_process")
    second = case.child(other, choices=(0,))
    case.action(second)
    case.returned(other, second)
    case.returned(case.root, other)
    assert len(case.host.received_context(case.root)[FACT_SOURCE]) == 2
    assert case.host.received_context(onward) == initial
    case.freeze(onward)
    assert case.host.facts(onward, schema()) == initial
    row = case.store.db.execute("SELECT form FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
        (case.run_id, case.root.episode_id)).fetchone()
    tampered = json.loads(row[0]); tampered["metadata"][0]["requested_id"] = "50006"
    case.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
        (canonical(tampered), case.run_id, case.root.episode_id))
    with pytest.raises(ValueError):
        case.host.received_context(onward)


def test_inline_sequence_file_requires_the_explicit_selected_return_and_keeps_legacy_expansion(tmp_path):
    body = (b'<section id="depositor-full"><div data-sequence-id="17"><textarea class="copy-from">'
        b'&gt; engineering inline\nAaCGTN</textarea></div></section>')
    case = HostCase(tmp_path, body=body)
    try:
        child = case.child(case.parent, choices=(0,))
        outcome = case.action(child)
        fact, = case.host.facts(child, schema())[FACT_SOURCE]
        file_ref = fact["selected_rows"][0]["sequence_file_ref"]
        source = case.store.get(fact["source_ref"])
        assert outcome["status"] == "completed" and case.store.get_artifact(file_ref) == b"AaCGTN"
        assert file_ref not in set(case.receipts.known(case.parent.episode_id))
        assert case.host.resolve_own(child, file_ref, "artifact") is True
        assert case.host.resolve_received(case.parent, file_ref, "artifact") is None
        _, _, references = case.returned(case.parent, child)
        assert references == [source["id"], file_ref]
        known = set(case.receipts.known(case.parent.episode_id))
        assert {source["id"], file_ref, source["artifact_ref"], source["request_ref"]} <= known
        assert case.host.resolve_received(case.parent, file_ref, "artifact") is True
        assert case.host.resolve_received(case.parent, file_ref, "source") is False
        assert case.host.resolve_received(case.parent, source["artifact_ref"], "artifact") is None
        assert fact["selected_rows"][0]["symbol_count"] is None
        assert len(case.client.calls) == 1
    finally:
        case.store.db.close()


def test_a_successful_saved_candidate_without_actual_receipt_grants_is_not_received(case):
    child = case.child(case.parent)
    case.action(child)
    _, form = case.freeze(child)
    case.journal.save("runtime_report_attempts", {"parent_episode_id": case.parent.episode_id,
        "decision_index": 0, "delivery_ref": "delivery_" + "1" * 24, "child_episode_id": child.episode_id,
        "contract": canonical(child.request["report_contract"]), "form": canonical(form), "failure": None})
    with pytest.raises(ValueError, match="received_reference_ungranted"):
        case.host.received_facts(case.parent, schema())


def test_validation_frame_reuses_only_one_original_context_and_invalidates_after_exit(case, monkeypatch):
    child = case.child(case.parent)
    case.action(child)
    fact, = case.host.facts(child, schema())[FACT_SOURCE]
    form = {"metadata": [fact]}
    original, calls = case.host.facts, []
    def counted(context, selected):
        calls.append(context.episode_id)
        return original(context, selected)
    monkeypatch.setattr(case.host, "facts", counted)
    with form_reference_validation():
        case.host.validate_report(child, form, schema())
        assert case.host.resolve_own(child, fact["source_ref"], "source") is True
        assert len(calls) == 1
        forged = replace(child, run_id="foreign-run")
        with pytest.raises(ValueError):
            case.host.validate_report(forged, form, schema())
    case.host.validate_report(child, form, schema())
    assert len(calls) == 3


def test_uncommissioned_source_resemblance_and_inconsistent_same_view_have_no_authority(case):
    child = case.child(case.parent)
    case.action(child)
    original = case.host.facts(child, schema())[FACT_SOURCE]
    forged = deepcopy(original)
    forged[0]["requested_id"] = "50006"
    with pytest.raises(ValueError, match="selected_value_conflict"):
        returns._merge([original, forged])
    altered = replace(child, assignment={**child.assignment, "selector": {"view": "sequences", "record_ordinals": [0]}})
    with pytest.raises(ValueError):
        case.host.facts(altered, schema())
    raw_source = engineering_source(case.store, provider="addgene",
        uri="https://www.addgene.org/50006/sequences/", body=b"<html></html>")
    assert case.host.resolve_own(child, raw_source["id"], "source") is False
    assert set(returns.addgene_sequence_fact_sources()) == {FACT_SOURCE}
    assert returns.addgene_sequence_fact_sources()[FACT_SOURCE]["report_schema"] == ADDGENE_SEQUENCE_FACTS_SCHEMA


def test_unrelated_sources_files_and_namespaces_decline_without_addgene_or_receipt_context(case, monkeypatch):
    path = (("annotation", "unrelated-legacy-context"),)
    episode_id = EpisodeRef(case.run_id, path).episode_id
    request = {"message": {"scope": case.scope, "episode_assignment": {}}, "report_contract": None}
    context = BindingContext(case.run_id, episode_id, "annotation", path, case.scope, {}, request)
    case.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
        "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
    assert case.store.db.execute("SELECT 1 FROM runtime_receipt_inheritance WHERE run_id=? AND episode_id=?",
        (case.run_id, episode_id)).fetchone() is None
    unrelated = engineering_source(case.store, provider="ncbi_entrez",
        uri="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        body=b"<Id>1</Id>", media_type="application/xml")
    ordinary_file = case.store.artifact("ordinary caller data", "text/plain")
    for name in ("authenticate", "_received"):
        monkeypatch.setattr(case.host, name, forbidden)
    monkeypatch.setattr(case.store, "reference_subset", forbidden)
    assert case.host.resolve_received(context, unrelated["id"], "source") is None
    assert case.host.resolve_received(context, unrelated["artifact_ref"], "artifact") is None
    assert case.host.resolve_received(context, ordinary_file, "artifact") is None
    assert case.host.resolve_received(context, ordinary_file, "unrelated_file_namespace") is None


def test_actual_legacy_result_source_and_expanded_raw_files_keep_generic_resolution(case, monkeypatch):
    legacy = {"type": "object", "additionalProperties": False, "required": ["references"],
        "properties": {"references": {"type": "array", "items": {"type": "string", "format": "reference",
            "x-reference-namespace": "execution_result"}, "x-source": "execution_result_refs"}}}
    child = case.child(case.parent, form=legacy)
    outcome = case.action(child)
    source = case.store.get(outcome["result"]["source_ref"])
    facts = case.api.facts(child, {"completion": {"ended_by": "yield"}})
    form = {"references": facts["execution_result_refs"]}
    assert returns.OWN_BINDINGS not in facts and facts["execution_completed"] is False
    assert case.api.resolve(child, source["id"], "execution_result") is True
    case.journal.save("runtime_forms", {"episode_id": child.episode_id,
        "facts": canonical(facts), "form": canonical(form)})
    case.journal.save("runtime_report_attempts", {"parent_episode_id": case.parent.episode_id,
        "decision_index": 0, "delivery_ref": "delivery_" + "2" * 24, "child_episode_id": child.episode_id,
        "contract": canonical(child.request["report_contract"]), "form": canonical(form), "failure": None})
    case.receipts.receive(case.parent.episode_id, [source["id"]], kind="child_form", source_index=0)
    known = set(case.receipts.known(case.parent.episode_id))
    assert {source["id"], source["artifact_ref"], source["request_ref"]} <= known
    for name in ("authenticate", "_received"):
        monkeypatch.setattr(case.host, name, forbidden)
    monkeypatch.setattr(case.store, "reference_subset", forbidden)
    assert case.host.resolve_received(case.parent, source["id"], "source") is None
    assert case.host.resolve_received(case.parent, source["id"], "execution_result") is None
    assert case.host.resolve_received(case.parent, source["artifact_ref"], "artifact") is None
    assert case.host.resolve_received(case.parent, source["request_ref"], "artifact") is None


def test_explicit_rich_file_inherits_into_receiver_without_an_outgoing_addgene_field(tmp_path):
    body = (b'<section id="depositor-full"><div data-sequence-id="17"><textarea class="copy-from">'
        b'&gt; engineering inline\nAaCGTN</textarea></div></section>')
    case = HostCase(tmp_path, body=body)
    try:
        child = case.child(case.parent, choices=(0,))
        case.action(child)
        _, form, _ = case.returned(case.parent, child)
        file_ref = form["metadata"][0]["selected_rows"][0]["sequence_file_ref"]
        empty = {"type": "object", "additionalProperties": False, "required": [], "properties": {}}
        onward = case.child(case.parent, index=1, role="scientific_process", form=empty)
        assert returns.requested_addgene_fields(onward.request["report_contract"]["measurements"]["schema"]) == {}
        assert file_ref in set(case.receipts.known(onward.episode_id))
        assert case.host.resolve_received(onward, file_ref, "artifact") is True
        assert case.host.resolve_received(onward, file_ref, "source") is False
        assert case.host.resolve_received(onward, form["metadata"][0]["source_ref"], "artifact") is False
        assert len(case.client.calls) == 1
    finally:
        case.store.db.close()


def test_unreceived_managed_source_is_denied_at_an_active_rich_receiver(case, monkeypatch):
    source = engineering_source(case.store, provider="addgene",
        uri="https://www.addgene.org/50006/sequences/", body=b"<html></html>")
    assert source["id"] not in set(case.receipts.known(case.parent.episode_id))
    monkeypatch.setattr(case.host, "_received", forbidden)
    monkeypatch.setattr(case.store, "reference_subset", forbidden)
    assert case.host.resolve_received(case.parent, source["id"], "source") is False


def test_later_explicit_file_grant_is_outside_an_existing_receiver_cutoff(tmp_path, monkeypatch):
    body = (b'<section id="depositor-full"><div data-sequence-id="17"><textarea class="copy-from">'
        b'&gt; first\nAaCGTN</textarea></div><div data-sequence-id="18"><textarea class="copy-from">'
        b'&gt; later\nTTGGCC</textarea></div></section>')
    case = HostCase(tmp_path, body=body)
    try:
        first = case.child(case.parent, choices=(0,))
        case.action(first)
        _, first_form, _ = case.returned(case.parent, first)
        empty = {"type": "object", "additionalProperties": False, "required": [], "properties": {}}
        onward = case.child(case.parent, index=1, role="scientific_process", form=empty)
        first_file = first_form["metadata"][0]["selected_rows"][0]["sequence_file_ref"]
        assert case.host.resolve_received(onward, first_file, "artifact") is True
        later = case.child(case.parent, index=2, choices=(1,))
        case.action(later)
        _, later_form, _ = case.returned(case.parent, later)
        later_file = later_form["metadata"][0]["selected_rows"][0]["sequence_file_ref"]
        assert later_file != first_file and later_file in set(case.receipts.known(case.parent.episode_id))
        assert later_file not in set(case.receipts.known(onward.episode_id))
        monkeypatch.setattr(case.host, "_received", forbidden)
        assert case.host.resolve_received(onward, later_file, "artifact") is None
        assert len(case.client.calls) == 1
    finally:
        case.store.db.close()
