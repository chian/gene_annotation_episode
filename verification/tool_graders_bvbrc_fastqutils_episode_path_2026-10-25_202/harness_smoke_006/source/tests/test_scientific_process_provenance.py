"""Provenance reads original operations and admitted forms, without execution."""
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3

import pytest

from method_loop import EpisodeGoal
from method_loop.identities import EpisodeRef
from gene_annotation_episode.domain import identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_provenance import ScientificProcessProvenance
from gene_annotation_episode.scientific_process_records import scientific_digest, scientific_invocation_ref
from gene_annotation_episode.scientific_process_reports import credit_binding_ref
from gene_annotation_episode.state import Store
from test_scientific_process_library import independent_source


def encoded(value):
    return json.dumps(value, allow_nan=False)


class Case:
    def __init__(self, tmp_path):
        self.store = Store(tmp_path / "state")
        self.journal = Journal(self.store, "provenance-fixture")
        independent_source(tmp_path / "source", extra=True)
        self.library = ScientificProcessLibrary.freeze(tmp_path / "library", source=tmp_path / "source")
        problem = self.store.create_problem(raw_sequence="MKWAA", molecule="protein")
        self.scope = {"subject_refs": problem["subject_refs"]}
        self.provenance = ScientificProcessProvenance(self.store, self.journal, library=self.library)
        self.root = self.context("annotation", "root")
        self.owner = self.context("scientific_process", "child_0", parent=self.root)

    def selection(self, thought="P01"):
        return {"version": "scientific_process_selection_v2",
            "annotation_ref": self.library.reference("A01"),
            "thought_ref": self.library.reference(thought), "tools": ["fixture.inspect"]}

    def context(self, role, key, *, parent=None, saved=True, origin=None):
        path = (() if parent is None else parent.path) + ((role, key),)
        parent_goal = None if parent is None else EpisodeGoal.from_record(parent.as_record()["request"]["goal"])
        goal = (EpisodeGoal.root(objective="Fixture target", result_contract={"role": role})
            if parent is None else EpisodeGoal.child(parent_goal,
                objective="Fixture child", result_contract={"required": []}))
        assignment = {} if role == "annotation" else {"selection": self.selection(),
            "evidence_refs": [], "constraints": {}, "context": {}}
        if origin is not None:
            assignment["revision_origin"] = origin
        message = {"scope": self.scope, "initial_report": {},
            "scientific_invocation_ref": scientific_invocation_ref(self.journal.run_id, path)}
        if assignment:
            message["episode_assignment"] = assignment
            message["scientific_process"] = {"selection": assignment["selection"]}
        request = {"goal": goal.as_record(), "message": message, "report_contract": None}
        context = BindingContext(self.journal.run_id, EpisodeRef(self.journal.run_id, path).episode_id,
            role, path, self.scope, assignment, request)
        if saved:
            self.save(context)
        return context

    def save(self, context):
        self.journal.save("runtime_episodes", {"episode_id": context.episode_id,
            "path": encoded(context.as_record()["path"]), "request": encoded(context.as_record()["request"]),
            "initial_credit": 3, "state": "active", "completion": None, "archive": None})

    def prepare(self, owner=None, *, index=2, thought="P77", mutation=None):
        owner = self.owner if owner is None else owner
        arguments = {"thought_ref": self.library.reference(thought), "tools": ["fixture.inspect"]}
        reference = identity("operation", {"key": f"{owner.run_id}:{owner.episode_id}:{index}",
            "name": "process.revise", "arguments": arguments})
        action = {"kind": "tool", "tool": "process.revise", "arguments": arguments}
        outcome = {"status": "completed", "operation_ref": reference, "record_refs": [],
            "changed_record_refs": [], "result": {"version": "scientific_process_child_selection_v1",
                "parent_selection_sha256": scientific_digest(self.selection()),
                "selection": self.selection(thought)}, "feedback": None,
            "revision_origin": {"version": "scientific_process_revision_origin_v1",
                "parent_invocation_ref": scientific_invocation_ref(owner.run_id, owner.path),
                "preparation_operation_ref": reference}}
        if mutation:
            mutation(action, outcome)
        self.journal.save("runtime_actions", {"episode_id": owner.episode_id, "decision_index": index,
            "action": encoded(action), "result": encoded(outcome), "credit": None})
        return reference, outcome

    def result(self, context=None, *, origin=None):
        context = self.owner if context is None else context
        return {"version": "scientific_process_result_v1",
            "invocation_ref": scientific_invocation_ref(context.run_id, context.path),
            "parent_invocation_ref": (None if len(context.path) == 1 else
                scientific_invocation_ref(context.run_id, context.path[:-1])),
            "origin_kind": "ordinary_child" if origin is None else "approach_revision",
            "preparation_operation_ref": origin, "selection": self.selection(),
            "initial_credit": 3, "credit": 1.5, "credit_kind": None,
            "credit_binding_ref": None, "completed_actions": 2, "episode_yield": None}

    def attempt(self, fields, form, *, parent=None, child=None, index=0, failure=None):
        parent = self.root if parent is None else parent
        child = self.owner if child is None else child
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "child_episode_id": child.episode_id, "decision_index": index,
            "delivery_ref": identity("delivery", {"index": index}),
            "contract": encoded({"measurements": {"schema": {"properties": fields}}}),
            "form": encoded(form), "failure": None if failure is None else encoded(failure)})


@pytest.fixture
def case(tmp_path):
    result = Case(tmp_path)
    try:
        yield result
    finally:
        result.store.close()


def test_exact_preparation_does_not_fold_latest_selection_and_returns_detached(case):
    first, outcome = case.prepare()
    case.prepare(index=4, thought="P01")
    value = case.provenance.preparation(case.owner, first)
    assert set(value) == {"operation_ref", "owner_invocation_ref", "owner_selection",
        "arguments", "proposal", "revision_origin"}
    assert value["proposal"] == outcome["result"]
    assert value["owner_selection"] == case.selection()
    assert value["revision_origin"] == outcome["revision_origin"]
    value["proposal"]["selection"]["thought_ref"]["option_id"] = "P999"
    assert case.provenance.preparation(case.owner, first)["proposal"] == outcome["result"]


def test_parent_preparation_for_new_unsaved_child_uses_immediate_saved_parent(case):
    reference, _ = case.prepare()
    child = case.context("scientific_process", "new", parent=case.owner, saved=False)
    assert case.provenance.parent_invocation(child) == scientific_invocation_ref(case.owner.run_id, case.owner.path)
    assert case.provenance.preparation(child, reference, owner="parent")["operation_ref"] == reference
    with pytest.raises(ValueError, match="saved_owner_required"):
        case.provenance.preparation(child, reference)
    with pytest.raises(ValueError, match="owner_invalid"):
        case.provenance.preparation(child, reference, owner=case.owner.episode_id)
    grandchild = case.context("scientific_process", "deeper", parent=child, saved=True)
    with pytest.raises(ValueError, match="saved_parent_required"):
        case.provenance.preparation(grandchild, reference, owner="parent")


@pytest.mark.parametrize("mutation", [
    lambda a, o: o.update(status="failed"),
    lambda a, o: o.update(record_refs=["source_" + "a" * 24]),
    lambda a, o: o.update(changed_record_refs=["source_" + "a" * 24]),
    lambda a, o: a.update(tool="fixture.other"),
    lambda a, o: a.update(kind="reason"),
    lambda a, o: a["arguments"].update(extra=True),
    lambda a, o: o["result"].update(parent_selection_sha256="0" * 64),
    lambda a, o: o["result"]["selection"].update(thought_ref=deepcopy(o["result"]["selection"]["annotation_ref"])),
    lambda a, o: o["revision_origin"].update(parent_invocation_ref="scientific_invocation_" + "0" * 24),
    lambda a, o: o["revision_origin"].update(preparation_operation_ref="operation_" + "0" * 24),
    lambda a, o: o.update(feedback={"code": "failed"}),
])
def test_failed_or_mismatched_original_preparation_is_not_usable(case, mutation):
    reference, _ = case.prepare(mutation=mutation)
    with pytest.raises(ValueError):
        case.provenance.preparation(case.owner, reference)
    assert not case.provenance.resolve(case.owner, reference, "scientific_preparation")


def test_foreign_operation_and_wrong_original_operation_key_are_rejected(case):
    sibling = case.context("scientific_process", "sibling", parent=case.root)
    foreign, _ = case.prepare(sibling)
    with pytest.raises(ValueError, match="unavailable"):
        case.provenance.preparation(case.owner, foreign)
    reference, _ = case.prepare()
    case.store.db.execute("UPDATE runtime_actions SET decision_index=7 WHERE episode_id=?", (case.owner.episode_id,))
    with pytest.raises(ValueError, match="identity_mismatch"):
        case.provenance.preparation(case.owner, reference)


@pytest.mark.parametrize("index", [-1, "forged", 2.5])
def test_saved_operation_requires_nonnegative_integer_decision_index(case, index):
    reference, _ = case.prepare()
    case.store.db.execute("UPDATE runtime_actions SET decision_index=? WHERE episode_id=?",
        (index, case.owner.episode_id))
    with pytest.raises(ValueError, match="operation_key_invalid"):
        case.provenance.preparation(case.owner, reference)


def test_preparation_rejects_tampered_saved_original_selection_and_duplicate_operation(case):
    reference, _ = case.prepare()
    original = case.owner.as_record()["request"]
    original["message"]["scientific_process"]["selection"] = case.selection("P77")
    context = replace(case.owner, request=original)
    case.save(context)
    with pytest.raises(ValueError, match="original_selection_mismatch"):
        case.provenance.preparation(context, reference)
    case.save(case.owner)
    row = case.store.db.execute("SELECT action,result FROM runtime_actions WHERE episode_id=?",
        (case.owner.episode_id,)).fetchone()
    case.journal.save("runtime_actions", {"episode_id": case.owner.episode_id,
        "decision_index": 9, "action": row["action"], "result": row["result"], "credit": None})
    with pytest.raises(ValueError, match="unavailable"):
        case.provenance.preparation(case.owner, reference)


@pytest.mark.parametrize("change", ["run", "role", "episode", "path", "request", "assignment", "goal", "scope"])
def test_context_identity_and_exact_original_request_are_authenticated(case, change):
    reference, _ = case.prepare()
    context = case.owner
    request = context.as_record()["request"]
    if change == "run":
        context = replace(context, run_id="foreign")
    elif change == "role":
        context = replace(context, role="annotation", path=case.root.path)
    elif change == "episode":
        context = replace(context, episode_id=case.root.episode_id)
    elif change == "path":
        context = replace(context, path=case.root.path + (("scientific_process", "other"),))
    elif change == "request":
        request["message"]["unrequested_context"] = "forged"
        context = replace(context, request=request)
    elif change == "assignment":
        context = replace(context, assignment={**context.as_record()["assignment"], "context": {"forged": True}})
    elif change == "goal":
        request["goal"]["goal_id"] = "goal_" + "0" * 24
        context = replace(context, request=request)
    else:
        context = replace(context, scope={"subject_refs": []})
    with pytest.raises(ValueError):
        case.provenance.preparation(context, reference)


def test_unsaved_child_must_preserve_actual_parent_goal_scope_and_marker(case):
    reference, _ = case.prepare()
    child = case.context("scientific_process", "new", parent=case.owner, saved=False)
    request = child.as_record()["request"]
    wrong_goal = EpisodeGoal.child(EpisodeGoal.from_record(case.root.as_record()["request"]["goal"]),
        objective="Fixture child", result_contract={"required": []})
    request["goal"] = wrong_goal.as_record()
    with pytest.raises(ValueError, match="parent_mismatch"):
        case.provenance.preparation(replace(child, request=request), reference, owner="parent")
    request = child.as_record()["request"]
    request["message"]["scientific_invocation_ref"] = "scientific_invocation_" + "0" * 24
    with pytest.raises(ValueError, match="invocation_mismatch"):
        case.provenance.parent_invocation(replace(child, request=request))


def test_unsaved_child_cannot_widen_saved_immediate_parent_scope(case):
    target = case.scope["subject_refs"][0]
    scope = case.store.validate_scope({**case.scope, "segments": [{"target_ref": target,
        "start": 0, "end": 3, "unit": "aa"}]})
    request = case.owner.as_record()["request"]
    request["message"]["scope"] = scope
    owner = replace(case.owner, scope=scope, request=request)
    case.save(owner)
    reference, _ = case.prepare(owner)
    child = case.context("scientific_process", "wider", parent=owner, saved=False)
    with pytest.raises(ValueError, match="outside_parent"):
        case.provenance.preparation(child, reference, owner="parent")


def test_received_only_successful_explicit_source_fields_flatten_and_deduplicate(case):
    row = case.result()
    grandchild = case.context("scientific_process", "private", parent=case.owner)
    private = case.result(grandchild)
    declared = {"type": "array", "x-source": "scientific_process_results"}
    case.attempt({"parent.chosen": declared, "other": {"type": "array"}},
        {"parent.chosen": [row], "other": [private]})
    case.attempt({"scientific_process_results": {"type": "array"}},
        {"scientific_process_results": [private]}, index=1)
    case.attempt({"failed": declared}, {"failed": [private]}, index=2, failure={"code": "invalid_form"})
    case.attempt({"again": declared}, {"again": [row]}, index=3)
    # Private child facts and even malformed archives are not a read source.
    case.journal.save("runtime_forms", {"episode_id": case.owner.episode_id,
        "facts": "not JSON and must not be read", "form": None})
    assert case.provenance.received_results(case.root) == [row]
    case.attempt({"requested": declared}, {"requested": [row, private]}, index=4)
    assert case.provenance.received_results(case.root) == [row, private]
    assert case.provenance.received_results(case.owner) == []


def test_closed_receiver_reads_only_previously_admitted_rows_without_child_facts(case):
    received = case.result()
    case.attempt({"selected": {"x-source": "scientific_process_results"}}, {"selected": [received]})
    private_child = case.context("scientific_process", "private", parent=case.root)
    case.journal.save("runtime_forms", {"episode_id": private_child.episode_id,
        "facts": encoded({"scientific_process_results": [case.result(private_child)]}), "form": None})
    case.store.db.execute("UPDATE runtime_episodes SET state='yielded',archive='not an archive' "
        "WHERE episode_id=?", (case.root.episode_id,))
    assert case.provenance.received_results(case.root) == [received]
    assert not case.provenance.resolve(case.root,
        scientific_invocation_ref(private_child.run_id, private_child.path), "scientific_invocation")


def test_received_snapshot_conflicts_and_invalid_bodies_fail(case):
    declared = {"chosen": {"type": "array", "x-source": "scientific_process_results"}}
    row = case.result()
    case.attempt(declared, {"chosen": [row]})
    changed = {**row, "credit": 99}
    case.attempt(declared, {"chosen": [changed]}, index=1)
    with pytest.raises(ValueError, match="conflict"):
        case.provenance.received_results(case.root)
    case.store.db.execute("DELETE FROM runtime_report_attempts WHERE decision_index=1")
    case.attempt(declared, {"chosen": [{**row, "unexpected": "forged"}]}, index=1)
    with pytest.raises(ValueError):
        case.provenance.received_results(case.root)


def test_received_conflicts_use_canonical_body_identity(case):
    declared = {"chosen": {"type": "array", "x-source": "scientific_process_results"}}
    row = case.result()
    case.attempt(declared, {"chosen": [row]})
    case.attempt(declared, {"chosen": [{**row, "initial_credit": 3.0}]}, index=1)
    with pytest.raises(ValueError, match="conflict"):
        case.provenance.received_results(case.root)


def test_namespace_resolution_uses_original_preparation_received_rows_and_actual_binding(case):
    reference, _ = case.prepare()
    other = case.context("scientific_process", "unreceived", parent=case.root)
    foreign, _ = case.prepare(other)
    resolve = lambda ref, ns: case.provenance.resolve(case.owner, ref, ns)
    assert resolve(scientific_invocation_ref(case.owner.run_id, case.owner.path), "scientific_invocation")
    assert resolve(scientific_invocation_ref(case.root.run_id, case.root.path), "scientific_invocation")
    assert resolve(reference, "scientific_preparation")
    assert not resolve(foreign, "scientific_preparation")
    assert not resolve(scientific_invocation_ref(other.run_id, other.path), "scientific_invocation")
    assert resolve(case.library.as_record()["library_id"], "scientific_process_library")
    assert resolve(case.library.reference("P77")["entry_sha256"], "scientific_option_digest")
    assert not resolve("0" * 64, "scientific_option_digest")
    assert not resolve(reference, "source")
    metadata = {"credit_kind": "scientific", "credit_binding": {"version": "fixture_credit_v1"}}
    binding = credit_binding_ref(metadata)
    assert case.provenance.resolve(case.owner, binding, "scientific_credit_binding", credit_metadata=metadata)
    assert not resolve(binding, "scientific_credit_binding")
    row = case.result(other, origin=foreign)
    row.update(credit_kind="scientific", credit_binding_ref=binding)
    case.attempt({"selected": {"x-source": "scientific_process_results"}}, {"selected": [row]}, parent=case.owner)
    assert resolve(scientific_invocation_ref(other.run_id, other.path), "scientific_invocation")
    assert resolve(foreign, "scientific_preparation")
    assert resolve(binding, "scientific_credit_binding")


def test_origin_reference_visible_to_new_child_only_when_exact_parent_preparation_matches(case):
    reference, outcome = case.prepare(thought="P01")
    child = case.context("scientific_process", "new", parent=case.owner,
        saved=False, origin=outcome["revision_origin"])
    assert case.provenance.resolve(child, reference, "scientific_preparation")
    forged = child.as_record()["assignment"]
    forged["revision_origin"]["parent_invocation_ref"] = "scientific_invocation_" + "0" * 24
    request = child.as_record()["request"]
    request["message"]["episode_assignment"] = forged
    with pytest.raises(ValueError, match="identity_mismatch"):
        case.provenance.resolve(replace(child, assignment=forged, request=request), reference, "scientific_preparation")


def test_construction_and_reads_issue_queries_only_and_never_read_private_history(case):
    reference, _ = case.prepare()
    case.attempt({"selected": {"x-source": "scientific_process_results"}}, {"selected": [case.result()]})
    statements = []
    denied = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_PRAGMA, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}
    def authorize(action, table, column, database, trigger):
        if action in denied:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_READ and table in {
                "runtime_forms", "runtime_model_calls", "runtime_observations", "runtime_return_admissions"}:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    case.store.db.execute("PRAGMA query_only=ON")
    case.store.db.set_authorizer(authorize)
    case.store.db.set_trace_callback(statements.append)
    producer = ScientificProcessProvenance(case.store, case.journal, library=case.library)
    assert statements == []
    producer.preparation(case.owner, reference)
    producer.received_results(case.root)
    assert producer.parent_invocation(case.root) is None
    assert producer.resolve(case.owner, reference, "scientific_preparation")
    assert statements and all(statement.lstrip().upper().startswith(("SELECT", "BEGIN", "COMMIT"))
        for statement in statements)
    assert not any("SELECT *" in statement.upper() for statement in statements)
