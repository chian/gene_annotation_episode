"""Actual UniProt API/publication custody and shared Workflow selected returns.

Transport is retained P0AAW1 or explicitly controlled malformed JSON; choices and
scientific continuation are fixtures. No model, network, native job or HPC runs.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
from method_loop.archive import iter_json
import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts, interpretation_schema, plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from gene_annotation_episode.uniprot_return_contracts import uniprot_selected_return_schema
from gene_annotation_episode.uniprot_returns import UniProtReturns, select_received_uniprot_pages


FIXTURE = Path(__file__).parent / "fixtures" / "uniprot_native"
SOURCE = "uniprot_selected_returns"


def selection(*, source=False, sequence=False, fields=None, records=None):
    fields = fields if fields is not None else [
        {"kind": "integer", "field": "taxon_id"},
        {"kind": "text", "field": "protein_name", "pointer": "/proteinDescription/recommendedName/fullName/value",
         "offset": 2, "limit": 7},
        {"kind": "sequence_window", "start": 9, "end": 19},
        {"kind": "evidence", "selection": {"mode": "all_at_owner", "owner_pointer": "/uniProtKBCrossReferences/31"}}]
    return {"version": "uniprot_return_selection_v1", "pages": [{"publication": {"mode": "assigned_page"},
        "page_fields": [{"kind": "page_token", "field": "release"}],
        "records": records if records is not None else [{"record": {"mode": "all_native_records"},
            "fields": fields, "grant_sequence_artifact": sequence}], "grant_source": source}]}


def schema(selected, name="arbitrary_scientific_cells", *, legacy=False):
    fields = {name: uniprot_selected_return_schema(selected)}
    if legacy:
        fields["legacy_records"] = {"type": "array", "items": {"type": "string", "format": "reference",
            "x-reference-namespace": "execution_result"}, "x-source": "execution_result_refs"}
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def forwarding(selected, value):
    result = deepcopy(selected)
    witness = value["pages"][0]["witness"]
    result["pages"][0]["publication"] = {"mode": "received_publication",
        "source_id": witness["source_id"], "publication_sha256": witness["publication_sha256"]}
    return result


class RetainedClient:
    def __init__(self, body=None, *, search=False):
        self.calls = []
        content = (FIXTURE / "P0AAW1.json").read_bytes() if body is None else canonical(body).encode()
        self.native = SourceSnapshot("uniprot", "https://rest.uniprot.org/uniprotkb/" + ("search" if search else "P0AAW1"),
            {"query": "fixture", "size": 10} if search else {"accession": "P0AAW1"},
            "2026-10-28T00:00:00+00:00", content, "application/json",
            {"response": {"status": 200, "headers": {"x-uniprot-release": "2025_01"}},
             "evidence_kind": "retained_native" if body is None else "controlled_native_fixture"})

    def uniprot_record(self, accession):
        self.calls.append(("record", accession))
        assert accession == "P0AAW1"
        return self.native

    def uniprot_search(self, **arguments):
        self.calls.append(("search", arguments))
        return replace(self.native, request=arguments)


class Harness:
    """Real hosts and journals; controlled commission rows for adversarial tests."""
    def __init__(self, store, directory, client=None):
        self.store, self.run_id, self.client = store, "uniprot-selected-host", client or RetainedClient()
        subject, = store.create_problem(raw_sequence="MACDEFGHIKLMNPQRSTVWY", molecule="protein")["subject_refs"]
        self.scope = {"subject_refs": [subject]}
        self.journal, self.receipts = Journal(store, self.run_id), EpisodeReceipts(store, self.run_id)
        self.api = APIServiceExecution(store, run_id=self.run_id, directory=directory,
            configuration={"uniprot": {"kind": "api", "service": "uniprot"}},
            tool_registry=ToolRegistry(store, clients=self.client), handoff_unit=3, acquired_record_unit=2)
        self.host = self.api.uniprot_returns
        self.root = self.context((("annotation", "root"),), {}, None)
        request = ({"operation": "search", "query": "fixture", "size": 10}
                   if "query" in self.client.native.request else {"operation": "record", "accession": "P0AAW1"})
        launch = self.context((("launch_api", "fixture"),), {"version": "api_service_assignment_v1",
            "resource_id": "uniprot", "service": "uniprot", "request": request,
            "endpoint": "usable_handoff", "constraints": {}}, None)
        launched = self.action(launch, "api.uniprot." + request["operation"])
        self.assignment = {"version": "execution_results_assignment_v1",
            "handoff_ref": launched["result"]["handoff_ref"], "selector": {}}

    def context(self, path, assignment, contract, parent=None):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inheritance = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective="Verify UniProt selected custody", result_contract={"role": path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                objective="Verify UniProt selected custody", result_contract=contract.schema))
        request = EpisodeRequest(goal, Record({"scope": deepcopy(self.scope), "initial_report": {},
            "episode_assignment": deepcopy(assignment), "knowledge_inheritance": inheritance}), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, parent, form_schema, *, role="results", index=0):
        contract = TypedReportContract("Return selected original source facts", form_schema, lambda *_: True)
        assignment = self.assignment if role == "results" else {}
        context = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent)
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical({"kind": "episode_child", "role": role, "assignment": assignment,
                "scope": self.scope, "purpose": contract.decision, "schema_json": canonical(form_schema)}),
            "result": None, "credit": None})
        return context

    def action(self, context, name="api.uniprot.collect", index=0):
        key = f"{self.run_id}:{context.episode_id}:{index}"
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": name, "arguments": {}}), "result": None, "credit": None})
        outcome = asyncio.run(self.api.execute(context, name, {}, key))
        assert outcome["status"] in {"completed", "partial"}, outcome
        self.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(outcome), self.run_id, context.episode_id, index))
        self.receipts.receive(context.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
        return outcome

    def returned(self, parent, child):
        contract = plain(child.request)["report_contract"]
        form_schema = contract["measurements"]["schema"]
        facts = self.host.facts_for_closure(child, form_schema)
        if "legacy_records" in form_schema["properties"]:
            facts["execution_result_refs"] = list(next(self.api._own_outcomes(child))[1]["record_refs"])
        value = form_with_facts({}, form_schema, facts)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(value)})
        self.host.validate_received_report(child, value, form_schema)
        index = int(child.path[-1][1].removeprefix("child_"))
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24], "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(value), "failure": None})
        refs = self.host.record_admission(parent, value, form_schema, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        refs.extend(value.get("legacy_records", []))
        self.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        return value


@pytest.fixture
def run(tmp_path):
    with Store(tmp_path / "state") as store:
        yield Harness(store, tmp_path / "run")


@pytest.mark.parametrize("source,sequence,legacy", [(False, False, False), (True, False, False),
    (False, True, False), (True, True, False), (False, False, True)])
def test_real_acquisition_requested_grants_and_independent_legacy_fields(run, source, sequence, legacy):
    chosen = selection(source=source, sequence=sequence)
    form_schema = schema(chosen, legacy=legacy)
    child = run.child(run.root, form_schema)
    result = run.action(child)
    before = set(run.receipts.known(run.root.episode_id))
    returned = run.returned(run.root, child)["arbitrary_scientific_cells"]
    page, = returned["pages"]
    row, = page["records"]
    assert row["fields"][0]["value"]["value"] == 83333
    assert row["fields"][2]["value"]["value"] == json.loads(run.client.native.content)["sequence"]["value"][9:19]
    assert len(row["fields"][2]["value"]["value"]) == 10
    received = set(run.receipts.known(run.root.episode_id)) - before
    native_source, native_artifact = page["witness"]["source_id"], page["witness"]["native_artifact_id"]
    sequence_artifact = row["witness"]["sequence_artifact_id"]
    assert (native_source in received) == (source or legacy)
    assert (native_artifact in received) == (source or legacy)
    assert (sequence_artifact in received) == (sequence or legacy)
    assert (row["witness"]["record_id"] in received) == legacy
    assert run.host.resolve_received(run.root, native_source, "source") == (source or legacy)
    assert run.host.resolve_received(run.root, sequence_artifact, "artifact") == (sequence or legacy)
    assert run.host.resolve_own(child, row["witness"]["record_id"], "reference") is True
    if sequence:
        assert run.host.authenticate_sequence_artifact(run.root, row["sequence_grant"]) == (child.episode_id,)
    assert len(run.client.calls) == 1
    assert result["result"]["uniprot_publication"]["content_sha256"] == page["witness"]["content_sha256"]


def test_exact_received_selectors_and_changed_windows_have_no_implicit_native_read(run, monkeypatch):
    chosen = selection()
    child = run.child(run.root, schema(chosen))
    run.action(child)
    returned = run.returned(run.root, child)
    wrappers = run.host._received(run.root)
    forwarded = forwarding(chosen, returned["arbitrary_scientific_cells"])
    def prohibited(*args, **kwargs):
        pytest.fail("pure forwarding read native material")
    monkeypatch.setattr(run.store, "get_artifact", prohibited)
    value = select_received_uniprot_pages(wrappers, selection=forwarded)
    assert value == returned["arbitrary_scientific_cells"]
    forwarded["pages"][0]["records"][0]["fields"][1]["limit"] = 6
    value = select_received_uniprot_pages(wrappers, selection=forwarded)
    field = value["pages"][0]["records"][0]["fields"][1]
    assert field["status"] == "unavailable" and field["value"] is None
    assert field["failures"][0]["code"] == "field_not_received"


def test_missing_new_sequence_material_preserves_other_selected_facts(run):
    chosen = selection(sequence=True)
    child = run.child(run.root, schema(chosen))
    outcome = run.action(child)
    sequence_ref = outcome["result"]["uniprot_publication"]["records"][0]["sequence_ref"]
    sha = sequence_ref.removeprefix("artifact_")
    (run.store.path / "artifacts" / sha[:2] / sha).unlink()
    value = run.returned(run.root, child)["arbitrary_scientific_cells"]
    row, = value["pages"][0]["records"]
    assert row["fields"][0]["value"]["value"] == 83333
    assert row["fields"][1]["status"] == row["fields"][3]["status"] == "available"
    assert row["fields"][2]["status"] == "unavailable" and row["fields"][2]["value"] is None
    assert row["fields"][2]["failures"][0]["code"] == "sequence_unavailable"
    assert row["sequence_grant_status"] == "unavailable" and row["sequence_grant"] is None
    assert sequence_ref not in run.receipts.known(run.root.episode_id)
    assert len(run.client.calls) == 1


@pytest.mark.parametrize('material', ['native', 'sequence'])
def test_changed_material_bytes_are_rejected_before_first_projection(run, material):
    child = run.child(run.root, schema(selection(sequence=True)))
    outcome = run.action(child)
    publication = outcome["result"]["uniprot_publication"]
    reference = (publication['native_artifact_ref'] if material == 'native'
                 else publication['records'][0]['sequence_ref'])
    sha = reference.removeprefix("artifact_")
    (run.store.path / "artifacts" / sha[:2] / sha).write_bytes(b"MUTATED")
    with pytest.raises(ReportBoundaryError, match="uniprot_artifact_content_conflict"):
        run.host.facts(child, schema(selection(sequence=True)))
    assert run.journal.row("runtime_forms", child.episode_id) is None
    assert not set(run.receipts.known(run.root.episode_id))


def test_unreceived_publication_fields_and_grants_do_not_read_native_material(run, monkeypatch):
    chosen = selection()
    child = run.child(run.root, schema(chosen))
    run.action(child)
    form = run.returned(run.root, child)
    wrappers = run.host._received(run.root)
    forwarded = forwarding(chosen, form["arbitrary_scientific_cells"])
    forwarded["pages"][0]["grant_source"] = True
    forwarded["pages"][0]["records"][0]["grant_sequence_artifact"] = True
    forwarded["pages"][0]["records"][0]["fields"][3]["selection"]["owner_pointer"] = "/sequence"
    def prohibited(*args, **kwargs):
        pytest.fail("unreceived selector inspected native material")
    monkeypatch.setattr(run.store, "get_artifact", prohibited)
    value = select_received_uniprot_pages(wrappers, selection=forwarded)
    page, = value["pages"]
    row, = page["records"]
    assert page["source_grant_status"] == row["sequence_grant_status"] == "unavailable"
    assert page["source_grant"] is row["sequence_grant"] is None
    assert page["failures"][0]["code"] == "source_not_received"
    assert row["failures"][0]["code"] == "sequence_artifact_not_received"
    assert row["fields"][3]["failures"][0]["code"] == "field_not_received"
    forwarded["pages"][0]["publication"]["publication_sha256"] = "0" * 64
    value = select_received_uniprot_pages(wrappers, selection=forwarded)
    assert value["pages"] == [] and value["failures"][0]["code"] == "publication_not_received"


def test_saved_unadmitted_form_cannot_skip_material_authentication(run):
    chosen = selection()
    child = run.child(run.root, schema(chosen))
    outcome = run.action(child)
    facts = run.host.facts(child, schema(chosen))
    form = form_with_facts({}, schema(chosen), facts)
    run.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
    with pytest.raises(ReportBoundaryError, match="uniprot_frozen_prefix_conflict"):
        run.host.read_own(outcome["result"]["source_ref"], context=child,
            operation_key=outcome["result"]["acquisition_receipt"]["operation_key"], verify_artifacts=False)
    with pytest.raises(ValueError, match="uniprot_frozen_prefix_conflict"):
        run.api.read_result(outcome["result"]["source_ref"], child.scope, episode_id=child.episode_id,
            operation_key=outcome["result"]["acquisition_receipt"]["operation_key"], verify_artifacts=False)
    assert not set(run.receipts.known(run.root.episode_id))


def test_empty_selection_returns_no_page_or_material(run, monkeypatch):
    chosen = {"version": "uniprot_return_selection_v1", "pages": []}
    child = run.child(run.root, schema(chosen))
    run.action(child)
    def prohibited(*args, **kwargs):
        pytest.fail("empty selection read native material")
    monkeypatch.setattr(run.store, "get_artifact", prohibited)
    value = run.returned(run.root, child)["arbitrary_scientific_cells"]
    assert value == {"version": "uniprot_selected_returns_v1", "pages": [], "failures": []}
    assert not set(run.receipts.known(run.root.episode_id))


def test_episode_mode_fails_before_dispatch_and_initial_form_bypass(run):
    chosen = selection()
    chosen['pages'][0]['publication'] = {'mode': 'received_publication',
        'source_id': 'source_' + '0' * 24, 'publication_sha256': '0' * 64}
    results = run.child(run.root, schema(chosen))
    with pytest.raises(ReportBoundaryError, match='uniprot_selection_mode_conflict') as error:
        run.api.initialize(results)
    assert error.value.diagnostic['field'].endswith('.pages[0].publication.mode')
    assert not (run.api._episode_directory(results.episode_id) / 'assignment.json').exists()
    scientist = run.child(run.root, schema(selection()), role='scientific_process', index=1)
    with pytest.raises(ReportBoundaryError, match='uniprot_selection_mode_conflict'):
        run.host.validate_received_report(scientist, {}, interpretation_schema(schema(selection())))
    for context in (results, scientist):
        assert not run.store.db.execute('SELECT 1 FROM runtime_actions WHERE run_id=? AND episode_id=?',
            (run.run_id, context.episode_id)).fetchall()
    assert len(run.client.calls) == 1


def test_sequence_grant_inheritance_keeps_original_received_prefix(run):
    empty = schema({"version": "uniprot_return_selection_v1", "pages": []})
    earlier = run.child(run.root, empty, role="scientific_process", index=0)
    child = run.child(run.root, schema(selection(sequence=True)), index=1)
    run.action(child)
    form = run.returned(run.root, child)
    descriptor = form["arbitrary_scientific_cells"]["pages"][0]["records"][0]["sequence_grant"]
    later = run.child(run.root, empty, role="scientific_process", index=2)
    assert run.host.authenticate_sequence_artifact(later, descriptor) == (child.episode_id,)
    with pytest.raises(ReportBoundaryError, match="uniprot_original_receipt_conflict"):
        run.host.authenticate_sequence_artifact(earlier, descriptor)


def test_partial_bindings_keep_original_native_rows_and_outer_counts(tmp_path):
    native = json.loads((FIXTURE / "P0AAW1.json").read_bytes())
    omitted = deepcopy(native)
    omitted["primaryAccession"] = "Z" * 500
    with Store(tmp_path / "state") as store:
        run = Harness(store, tmp_path / "run", RetainedClient({"results": [native, None, omitted, native]}, search=True))
        child = run.child(run.root, schema(selection()))
        result = run.action(child)
        assert result["status"] == "partial"
        value = run.returned(run.root, child)["arbitrary_scientific_cells"]
        page, = value["pages"]
        assert [r["requested_record_ordinal"] for r in page["records"]] == [0, 1, 2, 3]
        assert [r["state"] for r in page["records"]] == ["bound", "parser_unpublishable", "binding_omitted", "bound"]
        assert page["status"]["native_record_count"] == 4
        assert page["status"]["parser_eligible_record_count"] == 3
        assert page["status"]["bound_record_count"] == result["result"]["count"] == 2
        assert not set(run.receipts.known(run.root.episode_id))


@pytest.mark.parametrize("change", ["source", "witness", "field", "evidence_owner", "schema"])
def test_original_form_and_selected_associations_reject_tampering(run, change):
    chosen = selection()
    child = run.child(run.root, schema(chosen))
    run.action(child)
    returned = run.returned(run.root, child)
    changed, form_schema = deepcopy(returned), deepcopy(plain(child.request)["report_contract"]["measurements"]["schema"])
    page = changed["arbitrary_scientific_cells"]["pages"][0]
    row = page["records"][0]
    if change == "source":
        page["witness"]["source_id"] = "source_" + "0" * 24
    elif change == "witness":
        row["witness"]["record_id"] = "reference_" + "0" * 24
    elif change == "field":
        row["fields"][0]["value"]["value"] += 1
    elif change == "evidence_owner":
        members = row["fields"][3]["value"]["members"]
        assert members
        members[0]["value"]["owner_pointer"] = "/sequence"
    else:
        different = deepcopy(chosen)
        different["pages"][0]["records"][0]["fields"][1]["limit"] += 1
        form_schema = schema(different)
    with pytest.raises(ReportBoundaryError) as failure:
        run.host.validate_received_report(child, changed, form_schema)
    assert failure.value.diagnostic["code"].startswith("uniprot_")


def test_closed_native_withdrawal_replays_forms_and_rejects_new_material_read(run, monkeypatch):
    chosen = selection(sequence=True)
    child = run.child(run.root, schema(chosen))
    outcome = run.action(child)
    returned = run.returned(run.root, child)
    page = returned["arbitrary_scientific_cells"]["pages"][0]
    for ref in [page["witness"]["native_artifact_id"], page["records"][0]["sequence_grant"]["artifact_ref"]]:
        sha = ref.removeprefix("artifact_")
        (run.store.path / "artifacts" / sha[:2] / sha).unlink()
    def prohibited(*args, **kwargs):
        pytest.fail("closed history reprojected native content")
    monkeypatch.setattr("gene_annotation_episode.uniprot_returns.project_uniprot_page", prohibited)
    before = [tuple(row) for row in run.store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id,decision_index")]
    assert run.host.facts(child, schema(chosen))[SOURCE] == returned["arbitrary_scientific_cells"]
    run.host.validate_received_report(child, returned, schema(chosen))
    assert run.host._received(run.root)[0]["form"] == returned
    assert before == [tuple(row) for row in run.store.db.execute("SELECT * FROM runtime_actions ORDER BY episode_id,decision_index")]
    with pytest.raises(FileNotFoundError):
        run.host.read_own(outcome["result"]["source_ref"], context=child,
            operation_key=outcome["result"]["acquisition_receipt"]["operation_key"])
    historical = run.api.read_result(outcome["result"]["source_ref"], child.scope,
        episode_id=child.episode_id, operation_key=outcome["result"]["acquisition_receipt"]["operation_key"],
        verify_artifacts=False)
    assert historical["publication_result"] == outcome["result"]
    assert len(run.client.calls) == 1


def test_original_operation_key_disambiguates_repeated_partial_acquisitions(tmp_path):
    native = json.loads((FIXTURE / "P0AAW1.json").read_bytes())
    native["sequence"]["length"] = 999
    with Store(tmp_path / "state") as store:
        run = Harness(store, tmp_path / "run", RetainedClient(native))
        child = run.child(run.root, schema(selection()))
        first, second = run.action(child), run.action(child, index=1)
        assert first["status"] == second["status"] == "partial"
        reference = first["result"]["source_ref"]
        assert reference == second["result"]["source_ref"]
        for outcome in (first, second):
            key = outcome["result"]["acquisition_receipt"]["operation_key"]
            assert run.host.read_own(reference, context=child, operation_key=key)["publication_result"] == outcome["result"]
        with pytest.raises(ReportBoundaryError, match="uniprot_original_receipt_conflict"):
            run.host.read_own(reference, context=child, operation_key=f"{run.run_id}:{child.episode_id}:9")
        value = run.returned(run.root, child)["arbitrary_scientific_cells"]
        assert len(value["pages"]) == 1


def test_forwarding_closed_prefix_excludes_later_child_and_rejects_forged_attempt(run):
    chosen = selection()
    # An actual earlier returned witness supplies an explicit forwarding selector.
    first = run.child(run.root, schema(chosen))
    run.action(first)
    first_form = run.returned(run.root, first)
    forward = forwarding(chosen, first_form["arbitrary_scientific_cells"])
    parent = run.child(run.root, schema(forward, "parent_cells"), role="scientific_process", index=1)
    owned = run.child(parent, schema(chosen, "results_cells"))
    run.action(owned)
    run.returned(parent, owned)
    # This second child was already commissioned when its parent closed.
    later = run.child(parent, schema(chosen), index=1)
    run.action(later)
    closed = run.returned(run.root, parent)
    saved = run.journal.row("runtime_forms", parent.episode_id)["facts"]
    run.returned(parent, later)
    assert run.host.facts_for_closure(parent, schema(forward, "parent_cells"))[SOURCE] == closed["parent_cells"]
    assert run.journal.row("runtime_forms", parent.episode_id)["facts"] == saved
    prefix = json.loads(saved)["uniprot_received_report_prefix_v1"]
    assert [row["decision_index"] for row in prefix["attempts"]] == [0]
    run.store.db.execute("UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
        (later.episode_id, run.run_id, parent.episode_id))
    with pytest.raises(ReportBoundaryError, match="uniprot_frozen_prefix_conflict"):
        run.host.facts_for_closure(parent, schema(forward, "parent_cells"))


@pytest.mark.parametrize("source,sequence", [(False, False), (True, False), (False, True), (True, True)])
def test_shared_workflow_results_scientific_parent_ancestor_and_closed_replay(tmp_path, monkeypatch, source, sequence):
    from gene_annotation_episode.decision_context import apply_state_frame
    from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
    from gene_annotation_episode.runtime import Workflow
    from test_resource_tool_selection import ResourceCase
    from test_execution_episodes_family import launch_assignment
    from test_execution_wiring import child as commission, form as reference_form
    from test_published_axis_workflow import select

    client = RetainedClient()
    chosen = selection(source=source, sequence=sequence)
    result_schema = schema(chosen, "selected_by_results")
    discovery_schema = schema(selection(), "selected_by_results")
    with Store(tmp_path / "state") as store:
        case = ResourceCase(tmp_path, store, resources={"uniprot": {"kind": "api", "service": "uniprot"}},
            sequence="MACDEFGHIKLMNPQRSTVWY", client=client)
        assignment = {"version": "api_service_assignment_v1", "resource_id": "uniprot", "service": "uniprot",
            "request": {"operation": "record", "accession": "P0AAW1"}, "endpoint": "usable_handoff", "constraints": {}}
        handoff_schema = reference_form("execution_handoff_refs")
        selected_tools = [{"name": "api.uniprot.collect", "resources": "api"}]

        class Choices:
            def __init__(self):
                self.states, self.calls, self.root_count = {}, [], 0
                self.handoff, self.forward_schema = None, None
            async def complete(self, episode_id, role, instructions, current, output_schema):
                self.states[episode_id] = apply_state_frame(self.states.get(episode_id), current)
                state = self.states[episode_id]
                self.calls.append(episode_id)
                assert state.get("feedback") is None, state.get("feedback")
                execution = state.get("execution_assignment", {})
                if not execution:
                    assert state["working_state"]["record_view"] == "received_immutable_versions"
                if execution.get("version") == "execution_launch_assignment_v1":
                    return select(commission("launch_api", assignment, case.scope, handoff_schema)["selection"])
                if execution.get("version") == "api_service_assignment_v1":
                    return select({"kind": "tool", "tool": "api.uniprot.record", "arguments": {}})
                if execution.get("version") == "execution_results_assignment_v1":
                    return select({"kind": "tool", "tool": "api.uniprot.collect", "arguments": {}})
                if "scientific_process" in state:
                    return select(commission("results", {"version": "execution_results_assignment_v1",
                        "handoff_ref": self.handoff, "selector": {}}, case.scope, result_schema)["selection"])
                self.root_count += 1
                if self.root_count == 1:
                    return select(commission("launch", launch_assignment({"uniprot": assignment}), case.scope, handoff_schema)["selection"])
                if self.root_count == 2:
                    self.handoff, = state["child_reports"][-1]["references"]
                    return select(commission("results", {"version": "execution_results_assignment_v1",
                        "handoff_ref": self.handoff, "selector": {}}, case.scope, discovery_schema)["selection"])
                assert self.root_count == 3
                value = state["child_reports"][-1]["selected_by_results"]
                self.forward_schema = schema(forwarding(chosen, value), "ancestor_requested_cells")
                work = case.commission(selected_tools)
                work["schema_json"] = canonical(self.forward_schema)
                return select(work)
            async def release(self, episode_id):
                pass

        def controller(path, initial):
            def estimate(history, parameters, contexts):
                count = 3 if path[-1][0] == "annotation" else 1
                return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= count else 1), parameters,
                                     {"fixture": "scientific_continuation_only"})
            return YieldController(str(path), initial, 0, YieldParameters(100, 50),
                estimate_with_context=estimate if path[-1][0] in {"annotation", "scientific_process"} else None)
        application, provider = case.assemble(), Choices()
        def zero_scientific_fixture_credit(store, scope, **arguments):
            return 0
        workflow = Workflow(store, case.tools, provider, case.directory, case.run_id,
            controller_factory=controller, project_credit=zero_scientific_fixture_credit,
            episode_binding_descriptors=application.episode_binding_descriptors,
            role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
            episode_record_receipts=True, initial_known_record_refs=[], decision_protocol="decision_exchange_v1",
            annotation_child_roles=("launch", "results", "scientific_process"))
        root = workflow.build("annotation", "root", "Obtain selected UniProt entry measurements", case.scope)
        async def run_work():
            closed = await root.run_async(workflow.context)
            await root.build_result(closed)
            return closed
        closed = asyncio.run(run_work())
        tree = json.loads("".join(iter_json(closed.as_record())))
        science = tree["units"][2]["child"]
        results = science["units"][0]["child"]
        assert tree["units_consumed"] == 3 and science["units_consumed"] == results["units_consumed"] == 1
        assert results["controller_state"]["estimate"]["expected_next_gain"] == NumericBand.exact(0).as_record()
        parent_form = json.loads(workflow.journal.row("runtime_forms", science["episode_id"])["form"])
        child_form = json.loads(workflow.journal.row("runtime_forms", results["episode_id"])["form"])
        assert parent_form["ancestor_requested_cells"] == child_form["selected_by_results"]
        page = parent_form["ancestor_requested_cells"]["pages"][0]
        assert page["records"][0]["fields"][0]["value"]["value"] == 83333
        assert len(client.calls) == 1
        native_source, native_artifact = page["witness"]["source_id"], page["witness"]["native_artifact_id"]
        record_id = page["records"][0]["witness"]["record_id"]
        sequence_artifact = page["records"][0]["witness"]["sequence_artifact_id"]
        for receiver in (root.source.episode_id, science["episode_id"]):
            known = set(workflow.receipts.known(receiver))
            assert (native_source in known) == source
            assert (native_artifact in known) == source
            assert (sequence_artifact in known) == sequence
            assert record_id not in known
        host = workflow.episode_bindings.for_role("results").api_execution.uniprot_returns
        context = host.context(science["episode_id"])
        if sequence:
            assert host.authenticate_sequence_artifact(host.context(root.source.episode_id),
                page["records"][0]["sequence_grant"]) == (results["episode_id"],)
        rows_before = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id,unit_index")]
        calls_before = len(provider.calls)
        sha = page["witness"]["content_sha256"]
        (store.path / "artifacts" / sha[:2] / sha).unlink()
        def prohibited(*args, **kwargs):
            pytest.fail("closed workflow reprojected a source")
        monkeypatch.setattr("gene_annotation_episode.uniprot_returns.project_uniprot_page", prohibited)
        host.validate_received_report(context, parent_form, provider.forward_schema)
        assert host.facts_for_closure(context, provider.forward_schema)[SOURCE] == parent_form["ancestor_requested_cells"]
        attempt = store.db.execute("SELECT decision_index FROM runtime_report_attempts WHERE child_episode_id=?",
                                  (science["episode_id"],)).fetchone()
        workflow.receive_form(root.source, parent_form, provider.forward_schema, attempt[0], redelivery=True)
        assert rows_before == [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id,unit_index")]
        assert len(provider.calls) == calls_before and len(client.calls) == 1
