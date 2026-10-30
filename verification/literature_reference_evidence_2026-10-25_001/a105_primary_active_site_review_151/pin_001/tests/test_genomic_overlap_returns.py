"""Real Store/runtime/form records with a labeled strict results-host double.

The numerical fixtures are retained worker432 outputs over native427 bytes.
This suite verifies the communication/operand authority boundary only. It does
not claim native execution, production result-host binding or full Workflow.
Run through packet435's bounded local_jobs runner, retaining every attempt.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef
import pytest

from gene_annotation_episode.communication import form_with_facts, plain, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.genomic_overlap_return_views import (
    FACT_SOURCES, FAILURE_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE,
    genomic_overlap_fact_sources,
)
from gene_annotation_episode.genomic_overlap_returns import GenomicOverlapReturns
from gene_annotation_episode.native_file_capture import retained_native_file
from gene_annotation_episode.runtime import Record, TypedReportContract
from gene_annotation_episode.state import Store


PACKET = Path(__file__).resolve().parents[1] / "verification/tool_graders_genomic_overlap_return_authority_2026-10-27_435"


def schema_for(*sources):
    descriptors = genomic_overlap_fact_sources()
    fields = {"requested_" + str(index): deepcopy(descriptors[source]["report_schema"])
        for index, source in enumerate(sources)}
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def values(form, schema):
    return {node["x-source"]: form[name] for name, node in schema["properties"].items()}


def failure(artifact):
    # Explicit synthetic failure fact for access-control verification, not a
    # newly measured native failure or scientific result.
    return {"code": "native_output_unavailable", "stage": "capture", "set_key": None,
        "comparison_key": "AB", "artifact_ref": artifact, "locator": None,
        "field_path": "/stdout", "expected_value": None, "observed_value": None,
        "partial_artifact_refs": [artifact], "requirement": "complete_native_output"}


class StrictResultsHostDouble:
    """Only root014's two ports; no producer/capture/store-source authority.

    The double verifies exact registered contexts, selected actions and committed
    outcomes against real runtime rows. Its own facts are explicit test operands.
    It is not the production host and cannot establish a full episode path.
    """
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id
        self.originals, self.calls = {}, []

    @staticmethod
    def applies(context):
        return context.role == "results" and context.assignment.get("selector", {}).get(
            "version") == "genomic_overlap_result_selector_v1"

    def register(self, context, facts):
        action = {"kind": "tool", "tool": "execution.results.collect", "arguments": {}}
        outcome = {"status": "completed", "strict_host_fixture_facts": deepcopy(facts)}
        self.originals[context.episode_id] = (plain(context.as_record()), action, outcome)
        Journal(self.store, self.run_id).save("runtime_actions", {"episode_id": context.episode_id,
            "decision_index": 0, "action": canonical(action), "result": canonical(outcome), "credit": None})

    def own_fact_groups(self, context, *, verify_artifacts):
        self.calls.append((context.episode_id, verify_artifacts))
        original = self.originals.get(context.episode_id)
        if original is None or plain(context.as_record()) != original[0]:
            raise ValueError("strict_host_original_context_required")
        row = self.store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? "
            "AND episode_id=? AND decision_index=0", (self.run_id, context.episode_id)).fetchone()
        if row is None or row["result"] is None:
            raise ValueError("strict_host_completed_result_required")
        if json.loads(row["action"]) != original[1] or json.loads(row["result"]) != original[2]:
            raise ValueError("strict_host_original_completed_action_conflict")
        facts = deepcopy(original[2]["strict_host_fixture_facts"])
        if verify_artifacts:
            for file in facts[SAVED_SOURCE]:
                retained_native_file(self.store, file)
        return facts


class RuntimeFixture:
    def __init__(self, store):
        self.store, self.run_id = store, "genomic-overlap-return435"
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.scope = {"subject_refs": store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"]}
        self.host = StrictResultsHostDouble(store, self.run_id)
        self.boundary = GenomicOverlapReturns(SimpleNamespace(store=store, run_id=self.run_id,
            native_genomic_overlap_results=self.host))
        self.root = self.context((("annotation", "root"),), {}, None)
        pins = json.loads((PACKET / "FIXTURE_PINS.json").read_bytes())["files"]
        for pin in pins:
            raw = (PACKET / pin["path"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == pin["sha256"]
            assert len(raw) == pin["size_bytes"]
        sheet_raw = (PACKET / "fixtures/sheet.json").read_bytes()
        sha = hashlib.sha256(sheet_raw).hexdigest()
        self.sheet = {"artifact_ref": store.artifact(sheet_raw, "application/json"),
            "sha256": sha, "size_bytes": len(sheet_raw), "format": "genomic_region_overlap_sheet_v1"}
        self.projection = json.loads((PACKET / "fixtures/projection.json").read_bytes())
        self.recalculated = json.loads((PACKET / "fixtures/recalculated_projection.json").read_bytes())
        assert self.projection["source_sheet_sha256"] == self.recalculated["source_sheet_sha256"] == sha

    def context(self, path, assignment, contract, parent=None, *, scope=None, persist=True):
        scope = plain(self.scope if scope is None else scope)
        episode_id = EpisodeRef(self.run_id, path).episode_id
        inheritance = self.receipts.bind(episode_id, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective="Verify retained overlap returns", result_contract={"role": path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                objective="Verify retained overlap returns", result_contract=contract.schema))
        message = {"scope": scope, "initial_report": {}, "episode_assignment": deepcopy(assignment),
            "knowledge_inheritance": inheritance}
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, scope, assignment, request)
        if persist:
            self.persist(context)
        return context

    def persist(self, context):
        self.journal.save("runtime_episodes", {"episode_id": context.episode_id, "path": canonical(context.path),
            "request": canonical(plain(context.request)), "initial_credit": 0, "state": "active",
            "completion": None, "archive": None})

    def selector(self, saved=None):
        return {"version": "genomic_overlap_result_selector_v1", "mode": "native_result" if saved is None else "saved_sheet_recalculation",
            "comparison_keys": ["AB", "AC", "BC"], "saved_sheet_file": deepcopy(saved),
            "parameters": deepcopy(self.projection["parameters"]),
            "projection": {"kind": "pair_metrics", "offset": 0, "limit": 100,
                "measurement_fields": ["unfiltered.jaccard_bp"], "occurrence_keys": []}}

    def child(self, parent, schema, *, index=0, role="results", kind="episode_child", saved=None,
            scope=None, persist=True):
        contract = TypedReportContract("Return original requested overlap facts", schema, lambda *_: True)
        assignment = {"handoff_ref": "strict-fixture-handoff", "selector": self.selector(saved)} if role == "results" else {}
        child = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent,
            scope=parent.scope if scope is None else scope, persist=persist)
        if persist:
            self.commission(parent, child, kind=kind)
        return child

    def commission(self, parent, child, *, kind="episode_child"):
        contract = plain(child.request)["report_contract"]
        selection = {"kind": kind, "role": child.role, "assignment": plain(child.assignment),
            "scope": plain(child.scope), "purpose": contract["decision"],
            "schema_json": canonical(contract["measurements"]["schema"])}
        if kind == "tool":
            selection = {"kind": "tool", "tool": "process.revise", "arguments": {}}
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id,
            "decision_index": int(child.path[-1][1][6:]), "action": canonical(selection), "result": None, "credit": None})

    def own(self, child, *, projections=None, sheets=None, failures=None):
        facts = {PROJECTION_SOURCE: [self.projection] if projections is None else projections,
            SAVED_SOURCE: [self.sheet] if sheets is None else sheets,
            FAILURE_SOURCE: [] if failures is None else failures}
        self.host.register(child, facts)
        return deepcopy(facts)

    def returned(self, parent, child, facts=None, *, successful=True):
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        if facts is None:
            facts = (self.host.own_fact_groups(child, verify_artifacts=True) if child.role == "results"
                else self.boundary.facts_for_closure(child, schema_for(*FACT_SOURCES)))
        form = form_with_facts({}, schema, facts)
        self.boundary.validate_received_report(child, form, schema)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        typed = TypedReportContract(contract["decision"], schema, lambda *_: True,
            lambda value: self.boundary.validate_received_report(child, value, schema))
        admitted = typed.admit(form, audit_identifiers=(child.episode_id, plain(child.request)["goal"]["goal_id"])).as_record()
        index = int(child.path[-1][1][6:])
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "delivery_" + digest([parent.episode_id, index]),
            "child_episode_id": child.episode_id, "contract": canonical(contract),
            "form": canonical(admitted) if successful else None,
            "failure": None if successful else canonical({"kind": "synthetic_delivery_failure"})})
        if successful:
            self.receive(parent, admitted, schema, index)
        return admitted

    def receive(self, parent, form, schema, index, *, redelivery=False):
        references = self.boundary.record_admission(parent, form, schema, self.operation(parent, index))
        self.receipts.receive(parent.episode_id, references,
            kind="report_redelivery" if redelivery else "child_form", source_index=index)
        return references

    def redeliver(self, parent, child, schema, *, index=1):
        original_index = int(child.path[-1][1][6:])
        original = self.store.db.execute("SELECT delivery_ref FROM runtime_report_attempts WHERE run_id=? "
            "AND parent_episode_id=? AND decision_index=?", (self.run_id, parent.episode_id, original_index)).fetchone()
        contract = TypedReportContract("Return separately requested frozen overlap facts", schema, lambda *_: True,
            lambda value: self.boundary.validate_received_report(child, value, schema))
        facts = json.loads(self.journal.row("runtime_forms", child.episode_id)["facts"])
        form = contract.admit(form_with_facts({}, schema, facts),
            audit_identifiers=(child.episode_id, plain(child.request)["goal"]["goal_id"])).as_record()
        selection = {"kind": "redeliver_report", "delivery_ref": original["delivery_ref"],
            "purpose": contract.decision, "schema_json": canonical(schema)}
        self.journal.save("runtime_model_calls", {"episode_id": parent.episode_id, "call_index": index,
            "purpose": "decision", "request": "{}", "response": canonical({"selection": selection})})
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": original["delivery_ref"], "child_episode_id": child.episode_id,
            "contract": canonical(contract.as_record()), "form": canonical(form), "failure": None})
        self.receive(parent, form, schema, index, redelivery=True)
        return form

    def operation(self, parent, index=0):
        return f"{self.run_id}:{parent.episode_id}:{index}:typed_form"

    def change_action(self, context, index, update):
        row = self.journal.row("runtime_actions", context.episode_id, index)
        action = json.loads(row["action"])
        update(action)
        self.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(action), self.run_id, context.episode_id, index))


@pytest.fixture(autouse=True)
def no_acquisition_calculation_or_model(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Return authority attempted acquisition, native work or numerical calculation")
    for path in ("socket.create_connection", "socket.socket", "subprocess.Popen",
        "gene_annotation_episode.genomic_overlap_inputs.parse_region_set",
        "gene_annotation_episode.genomic_overlap_inputs.parse_bedtools_intersect_wo",
        "gene_annotation_episode.genomic_overlap_calculations.calculate_genomic_overlap_components",
        "gene_annotation_episode.genomic_overlap_result_views.project_genomic_overlap_result"):
        monkeypatch.setattr(path, forbidden)


@pytest.fixture
def f(tmp_path):
    with Store(tmp_path / "store") as store:
        fixture = RuntimeFixture(store)
        yield fixture
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM records WHERE record_type='observation'").fetchone()[0] == 0


@pytest.mark.parametrize("sources", [(PROJECTION_SOURCE,), (SAVED_SOURCE,), (FAILURE_SOURCE,), FACT_SOURCES])
def test_requested_immediate_returns_through_science_to_annotation(f, sources, tmp_path):
    schema = schema_for(*sources)
    science = f.child(f.root, schema, role="scientific_process")
    result = f.child(science, schema)
    own = f.own(result, failures=[failure(f.sheet["artifact_ref"])])
    first = f.returned(science, result)
    forwarded = f.returned(f.root, science)
    received = f.boundary.received_facts(f.root, schema_for(*FACT_SOURCES))
    assert first == forwarded
    assert received == {source: own[source] if source in sources else [] for source in FACT_SOURCES}
    references = f.boundary.record_admission(f.root, forwarded, schema, f.operation(f.root))
    assert references == ([f.sheet["artifact_ref"]] if SAVED_SOURCE in sources else [])
    assert f.boundary.resolve_received(f.root, f.sheet["artifact_ref"], "artifact") == (SAVED_SOURCE in sources)
    if SAVED_SOURCE in sources:
        assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (result.episode_id,)
    else:
        with pytest.raises(ValueError, match="saved_sheet_not_received"):
            f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)
    if PROJECTION_SOURCE in sources:
        row = received[PROJECTION_SOURCE][0]["pair_rows"][0]
        assert row["measurements"]["unfiltered.jaccard_bp"] == {
            "numerator": 5, "denominator": 15, "value": 1 / 3, "missing_reason": None}
        (tmp_path / "ACTUAL_TYPED_RETURN.json").write_text(canonical({
            "evidence": "retained_worker432_values_strict_host_double_real_runtime_forms",
            "received_sources": list(sources), "form": forwarded, "references": references}))


def test_projection_hash_and_failure_artifacts_never_grant_hidden_sheet(f):
    schema = schema_for(PROJECTION_SOURCE, FAILURE_SOURCE)
    child = f.child(f.root, schema)
    f.own(child, failures=[failure(f.sheet["artifact_ref"])])
    f.returned(f.root, child)
    for namespace in (None, "artifact", "source", "execution_result"):
        assert not f.boundary.resolve_received(f.root, f.sheet["artifact_ref"], namespace)
    assert list(f.receipts.known(f.root.episode_id)) == []
    with pytest.raises(ValueError, match="saved_sheet_not_received"):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def test_unrequested_grandchild_and_private_sibling_do_not_leak(f):
    science = f.child(f.root, schema_for(PROJECTION_SOURCE), role="scientific_process")
    grandchild = f.child(science, schema_for(*FACT_SOURCES))
    f.own(grandchild)
    f.returned(science, grandchild)
    f.returned(f.root, science)
    private = f.child(f.root, schema_for(SAVED_SOURCE), index=1)
    f.own(private)
    assert f.boundary.received_facts(f.root, schema_for(SAVED_SOURCE)) == {SAVED_SOURCE: []}
    with pytest.raises(ValueError, match="saved_sheet_not_received"):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)
    assert all(episode != private.episode_id for episode, _ in f.host.calls)


@pytest.mark.parametrize("change", ["scalar", "denominator", "parameter", "hash", "qualification", "page"])
def test_fabricated_values_reject_even_with_valid_schema(f, change):
    schema = schema_for(PROJECTION_SOURCE)
    child = f.child(f.root, schema)
    facts = f.own(child)
    form = form_with_facts({}, schema, facts)
    projection = form["requested_0"]
    row = projection[0]
    if change == "scalar":
        row["pair_rows"][0]["measurements"]["unfiltered.jaccard_bp"]["value"] = 0.5
    elif change == "denominator":
        row["pair_rows"][0]["measurements"]["unfiltered.jaccard_bp"]["denominator"] = 10
    elif change == "parameter":
        row["parameters"]["minimum_overlap_bp"] = 4
    elif change == "hash":
        row["source_sheet_sha256"] = "0" * 64
    elif change == "qualification":
        row["pair_rows"][0]["reference_relation"] = "same_supplied_reference"
    else:
        row["page"]["total_rows"] = 4
    validate_form(form, schema, lambda *_: True)
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        f.boundary.validate_received_report(child, form, schema)


def test_aliases_must_agree_and_equal_representations_deduplicate(f):
    schema = schema_for(PROJECTION_SOURCE, PROJECTION_SOURCE, SAVED_SOURCE)
    child = f.child(f.root, schema)
    facts = f.own(child, projections=[f.projection, f.projection, f.recalculated])
    form = form_with_facts({}, schema, facts)
    form["requested_1"] = [f.recalculated]
    with pytest.raises(ValueError, match="conflicting_fields"):
        f.boundary.validate_received_report(child, form, schema)
    f.returned(f.root, child)
    received = f.boundary.received_facts(f.root, schema)
    assert received[PROJECTION_SOURCE] == [f.projection, f.recalculated]
    received[PROJECTION_SOURCE][0]["parameters"]["minimum_overlap_bp"] = 200
    assert f.boundary.received_facts(f.root, schema)[PROJECTION_SOURCE] == [f.projection, f.recalculated]


@pytest.mark.parametrize("alter", ["missing", "uncommitted", "action", "outcome"])
def test_original_completed_host_action_required(f, alter):
    schema = schema_for(*FACT_SOURCES)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child)
    if alter == "missing":
        f.store.db.execute("DELETE FROM runtime_actions WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
    elif alter == "uncommitted":
        f.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
    elif alter == "action":
        f.change_action(child, 0, lambda action: action.update(tool="unrelated.tool"))
    else:
        f.store.db.execute("UPDATE runtime_actions SET result='{}' WHERE run_id=? AND episode_id=?", (f.run_id, child.episode_id))
    with pytest.raises(ValueError, match="strict_host_"):
        f.boundary.record_admission(f.root, form, schema, f.operation(f.root))


@pytest.mark.parametrize("change", ["scope", "schema", "purpose", "assignment", "role", "kind"])
def test_original_commission_cannot_change(f, change):
    schema = schema_for(*FACT_SOURCES)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child)
    replacements = {"scope": {"subject_refs": []}, "schema_json": canonical(schema_for()),
        "purpose": "Changed purpose", "assignment": {}, "role": "launch", "kind": "unselected"}
    field = "schema_json" if change == "schema" else change
    f.change_action(f.root, 0, lambda action: action.update({field: replacements[field]}))
    with pytest.raises(ValueError, match="commission|original_commission"):
        f.boundary.record_admission(f.root, form, schema, f.operation(f.root))


def test_context_run_scope_and_original_request_are_bound(f):
    schema = schema_for(PROJECTION_SOURCE)
    child = f.child(f.root, schema)
    form = form_with_facts({}, schema, f.own(child))
    for context in (replace(child, run_id="another-run"), replace(child, scope={"subject_refs": []})):
        with pytest.raises(ValueError, match="context_conflict"):
            f.boundary.validate_received_report(context, form, schema)
    request = plain(child.request)
    request["message"]["initial_report"] = {"altered": True}
    with pytest.raises(ValueError, match="original_context_conflict"):
        f.boundary.validate_received_report(replace(child, request=request), form, schema)


def test_foreign_scope_and_non_immediate_child_attempt_reject(f):
    schema = schema_for(PROJECTION_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    result = f.child(science, schema)
    f.own(result)
    f.returned(science, result)
    form = f.returned(f.root, science)
    f.store.db.execute("UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=? AND parent_episode_id=?",
        (result.episode_id, f.run_id, f.root.episode_id))
    with pytest.raises(ValueError, match="return_child_contract_conflict"):
        f.boundary.record_admission(f.root, form, schema, f.operation(f.root))
    unrelated = {"subject_refs": ["input_not_in_this_store_or_scope"]}
    foreign = f.child(f.root, schema, index=1, scope=unrelated)
    f.own(foreign)
    with pytest.raises(ValueError, match="commission_scope_conflict"):
        f.returned(f.root, foreign)


@pytest.mark.parametrize("change", ["form", "facts", "both"])
def test_frozen_form_and_facts_cannot_be_rewritten(f, change):
    schema = schema_for(PROJECTION_SOURCE)
    child = f.child(f.root, schema)
    f.own(child)
    original = f.returned(f.root, child)
    altered = deepcopy(original)
    altered["requested_0"][0]["parameters"]["minimum_overlap_bp"] = 2
    if change in {"form", "both"}:
        f.store.db.execute("UPDATE runtime_forms SET form=? WHERE run_id=? AND episode_id=?",
            (canonical(altered), f.run_id, child.episode_id))
    if change in {"facts", "both"}:
        facts = json.loads(f.journal.row("runtime_forms", child.episode_id)["facts"])
        facts[PROJECTION_SOURCE] = altered["requested_0"]
        f.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
            (canonical(facts), f.run_id, child.episode_id))
    if change == "both":
        f.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=?",
            (canonical(altered), f.run_id, f.root.episode_id))
    with pytest.raises(ValueError, match="frozen_.*conflict|returned_facts_conflict"):
        f.boundary.received_facts(f.root, schema)


def test_frozen_scientific_form_remains_ordered_subset_after_later_return(f):
    schema = schema_for(PROJECTION_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    first = f.child(science, schema)
    f.own(first)
    f.returned(science, first)
    frozen = f.returned(f.root, science)
    later = f.child(science, schema, index=1)
    f.own(later, projections=[f.recalculated])
    f.returned(science, later)
    assert f.boundary.received_facts(science, schema)[PROJECTION_SOURCE] == [f.projection, f.recalculated]
    f.boundary.validate_received_report(science, frozen, schema)
    assert f.boundary.received_facts(f.root, schema)[PROJECTION_SOURCE] == [f.projection]
    assert json.loads(f.journal.row("runtime_forms", science.episode_id)["form"]) == frozen


@pytest.mark.parametrize("alter", ["reverse", "duplicate"])
def test_frozen_subset_cannot_reorder_or_invent_duplicates(f, alter):
    schema = schema_for(PROJECTION_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    result = f.child(science, schema)
    f.own(result, projections=[f.projection, f.recalculated])
    f.returned(science, result)
    original = f.returned(f.root, science)
    original["requested_0"] = list(reversed(original["requested_0"])) if alter == "reverse" else [f.projection, f.projection]
    facts = {**json.loads(f.journal.row("runtime_forms", science.episode_id)["facts"]), **values(original, schema)}
    f.store.db.execute("UPDATE runtime_forms SET form=?,facts=? WHERE run_id=? AND episode_id=?",
        (canonical(original), canonical(facts), f.run_id, science.episode_id))
    f.store.db.execute("UPDATE runtime_report_attempts SET form=? WHERE run_id=? AND parent_episode_id=?",
        (canonical(original), f.run_id, f.root.episode_id))
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        f.boundary.received_facts(f.root, schema)


@pytest.mark.parametrize("original_success", [True, False])
def test_explicit_redelivery_grants_only_newly_requested_frozen_sheet(f, original_success):
    child = f.child(f.root, schema_for(PROJECTION_SOURCE))
    f.own(child)
    f.returned(f.root, child, successful=original_success)
    assert not f.boundary.resolve_received(f.root, f.sheet["artifact_ref"], "artifact")
    action_count = f.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    f.redeliver(f.root, child, schema_for(SAVED_SOURCE))
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    assert f.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == action_count


def test_redelivery_preserves_original_assignment_proof(f):
    child = f.child(f.root, schema_for(PROJECTION_SOURCE))
    f.own(child)
    f.returned(f.root, child)
    form = f.redeliver(f.root, child, schema_for(SAVED_SOURCE))
    f.change_action(f.root, 0, lambda action: action.update(assignment={}))
    with pytest.raises(ValueError, match="commission_assignment_conflict"):
        f.boundary.record_admission(f.root, form, schema_for(SAVED_SOURCE), f.operation(f.root, 1))


def test_multiple_original_results_origins_survive_representation_deduplication(f):
    schema = schema_for(*FACT_SOURCES)
    science = f.child(f.root, schema, role="scientific_process")
    results = [f.child(science, schema, index=index) for index in (0, 1)]
    for child in results:
        f.own(child)
        f.returned(science, child)
    f.returned(f.root, science)
    received = f.boundary.received_facts(f.root, schema)
    assert len(received[SAVED_SOURCE]) == len(received[PROJECTION_SOURCE]) == 1
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == tuple(child.episode_id for child in results)


def test_later_identical_sheet_origin_does_not_expand_frozen_forwarded_authority(f):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    original = f.child(science, schema)
    f.own(original)
    f.returned(science, original)
    original_form = f.returned(f.root, science)
    frozen_before = f.journal.row("runtime_forms", science.episode_id)["facts"]
    later = f.child(science, schema, index=1)
    f.own(later)
    f.returned(science, later)
    assert f.boundary.authenticate_received_saved_sheet(science, f.sheet) == (original.episode_id, later.episode_id)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (original.episode_id,)
    assert f.boundary.received_facts(f.root, schema) == {SAVED_SOURCE: [f.sheet]}
    f.boundary.validate_received_report(science, original_form, schema)
    repeat = f.boundary.facts_for_closure(science, schema_for(*FACT_SOURCES))
    assert canonical(repeat) == frozen_before


@pytest.mark.parametrize("alter", ["missing", "digest", "child", "deleted_attempt", "order"])
def test_historical_scientific_forwarding_requires_exact_closure_witnesses(f, alter):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process")
    for index in (0, 1):
        result = f.child(science, schema, index=index)
        f.own(result)
        f.returned(science, result)
    f.returned(f.root, science)
    facts = json.loads(f.journal.row("runtime_forms", science.episode_id)["facts"])
    key = "genomic_overlap_received_report_prefix"
    if alter == "missing":
        del facts[key]
    elif alter == "digest":
        facts[key]["attempts"][0]["form_sha256"] = "0" * 64
    elif alter == "child":
        facts[key]["attempts"][0]["child_episode_id"] = science.episode_id
    elif alter == "order":
        facts[key]["attempts"].reverse()
    else:
        f.store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND decision_index=0",
            (f.run_id, science.episode_id))
    f.store.db.execute("UPDATE runtime_forms SET facts=? WHERE run_id=? AND episode_id=?",
        (canonical(facts), f.run_id, science.episode_id))
    with pytest.raises(ValueError, match="closure_prefix_required|return_prefix_conflict|invalid_received_report_prefix"):
        f.boundary.authenticate_received_saved_sheet(f.root, f.sheet)


def test_closure_prefix_is_private_requested_only_and_captured_inside_read_snapshot(f, monkeypatch):
    schema = schema_for(PROJECTION_SOURCE)
    result = f.child(f.root, schema)
    f.own(result)
    f.returned(f.root, result)
    original = f.host.own_fact_groups
    def inside_snapshot(context, *, verify_artifacts):
        assert f.store.db.in_transaction
        return original(context, verify_artifacts=verify_artifacts)
    monkeypatch.setattr(f.host, "own_fact_groups", inside_snapshot)
    closure = f.boundary.facts_for_closure(f.root, schema)
    assert set(closure) == {PROJECTION_SOURCE, "genomic_overlap_received_report_prefix"}
    assert closure["genomic_overlap_received_report_prefix"]["attempts"][0]["child_episode_id"] == result.episode_id
    assert form_with_facts({}, schema, closure) == {"requested_0": [f.projection]}
    assert "genomic_overlap_received_report_prefix" not in genomic_overlap_fact_sources()
    monkeypatch.setattr(f.host, "own_fact_groups", original)
    assert f.boundary.received_facts(f.root, schema) == {PROJECTION_SOURCE: [f.projection]}


def test_historical_authority_survives_scientific_byte_loss(f, monkeypatch):
    schema = schema_for(*FACT_SOURCES)
    child = f.child(f.root, schema)
    f.own(child)
    form = f.returned(f.root, child)
    path = retained_native_file(f.store, f.sheet)
    path.unlink()
    f.host.calls.clear()
    monkeypatch.setattr(f.store, "get_artifact", lambda *a: pytest.fail("historical authority opened bytes"))
    assert f.boundary.received_facts(f.root, schema)[SAVED_SOURCE] == [f.sheet]
    f.boundary.validate_received_report(child, form, schema)
    assert f.boundary.resolve_received(f.root, f.sheet["artifact_ref"], None)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (child.episode_id,)
    assert f.host.calls and not any(verify for _, verify in f.host.calls)
    with pytest.raises((ValueError, OSError)):
        retained_native_file(f.store, f.sheet)


def test_saved_results_selection_sees_only_frozen_received_prefix(f):
    original = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(original)
    f.returned(f.root, original)
    delayed = f.child(f.root, schema_for(SAVED_SOURCE), index=1)
    f.own(delayed)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=2, saved=f.sheet)
    f.returned(f.root, delayed)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (original.episode_id, delayed.episode_id)
    assert f.boundary.authenticate_received_saved_sheet(selected, f.sheet) == (original.episode_id,)
    assert f.boundary.received_facts(f.root, schema_for(SAVED_SOURCE)) == {SAVED_SOURCE: [f.sheet]}
    assert not f.boundary.resolve_received(selected, f.sheet["artifact_ref"], "artifact")


def test_late_lower_index_delivery_does_not_enter_selected_child(f):
    delayed = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(delayed)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1, saved=f.sheet)
    f.returned(f.root, delayed)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (delayed.episode_id,)
    with pytest.raises(ValueError, match="saved_sheet_not_received"):
        f.boundary.authenticate_received_saved_sheet(selected, f.sheet)


def test_unsaved_construction_requires_exact_manifest_and_no_prior_work(f):
    original = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(original)
    f.returned(f.root, original)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1, saved=f.sheet, persist=False)
    assert f.boundary.authenticate_received_saved_sheet(selected, f.sheet) == (original.episode_id,)
    f.persist(selected)
    with pytest.raises(ValueError, match="original_commission_required"):
        f.boundary.authenticate_received_saved_sheet(selected, f.sheet)
    f.commission(f.root, selected)
    assert f.boundary.authenticate_received_saved_sheet(selected, f.sheet) == (original.episode_id,)


@pytest.mark.parametrize("alter", ["unselected", "size", "format", "hash", "prefix", "missing_prefix"])
def test_exact_selected_sheet_and_frozen_inheritance_are_required(f, alter):
    original = f.child(f.root, schema_for(SAVED_SOURCE))
    f.own(original)
    f.returned(f.root, original)
    selected = f.child(f.root, schema_for(PROJECTION_SOURCE), index=1, saved=None if alter == "unselected" else f.sheet)
    file = deepcopy(f.sheet)
    if alter == "size":
        file["size_bytes"] += 1
    elif alter == "format":
        file["format"] = "other_format"
    elif alter == "hash":
        file["sha256"] = "0" * 64
        file["artifact_ref"] = "artifact_" + file["sha256"]
    elif alter in {"prefix", "missing_prefix"}:
        prefix = None if alter == "missing_prefix" else canonical({"version": "frozen_received_report_prefix_v1", "attempts": []})
        f.store.db.execute("UPDATE runtime_receipt_inheritance SET received_report_prefix=? WHERE run_id=? AND episode_id=?",
            (prefix, f.run_id, selected.episode_id))
    with pytest.raises(ValueError, match="saved_|saved_sheet_identity"):
        f.boundary.authenticate_received_saved_sheet(selected, file)


@pytest.mark.parametrize("kind", ["child", "episode_child", "tool"])
def test_ordinary_scientific_and_existing_process_revision_relationships(f, kind):
    schema = schema_for(SAVED_SOURCE)
    science = f.child(f.root, schema, role="scientific_process", kind=kind)
    result = f.child(science, schema)
    f.own(result)
    f.returned(science, result)
    f.returned(f.root, science)
    assert f.boundary.authenticate_received_saved_sheet(f.root, f.sheet) == (result.episode_id,)


def test_unsupported_owner_empty_results_and_admission_operation_checks(f):
    schema = schema_for(*FACT_SOURCES)
    launch = f.child(f.root, schema, role="launch")
    empty = {source: [] for source in FACT_SOURCES}
    with pytest.raises(ValueError, match="unsupported_return_owner"):
        f.boundary.validate_received_report(launch, form_with_facts({}, schema, empty), schema)
    result = f.child(f.root, schema, index=1)
    f.own(result, projections=[], sheets=[])
    form = f.returned(f.root, result)
    assert f.boundary.received_facts(f.root, schema) == empty
    for operation in (f.operation(launch, 1), f.operation(f.root, 1).replace(":1:", ":01:"), "foreign:typed_form"):
        with pytest.raises(ValueError, match="admission_operation_required"):
            f.boundary.record_admission(f.root, form, schema, operation)


def test_unsupported_fact_source_and_mutated_admission_shape_reject(f):
    schema = schema_for(SAVED_SOURCE)
    result = f.child(f.root, schema)
    f.own(result)
    form = f.returned(f.root, result)
    unknown = schema_for(SAVED_SOURCE)
    unknown["properties"]["requested_0"]["x-source"] = "genomic_overlap_unknown"
    with pytest.raises(ValueError, match="unknown_source"):
        f.boundary.received_facts(f.root, unknown)
    changed = deepcopy(form)
    changed["requested_0"][0]["size_bytes"] += 1
    with pytest.raises(ValueError, match="admitted_form_conflict"):
        f.boundary.record_admission(f.root, changed, schema, f.operation(f.root))
