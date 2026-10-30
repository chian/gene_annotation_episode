"""Offline custody/read boundaries, not biological results or live calls."""
from copy import deepcopy
import json

import pytest

from gene_annotation_episode import runtime
from test_runtime import FixtureController, ScriptedProvider, obj, setup, tool


def workflow_source(tmp_path, *, preview=0):
    store, tools = setup(tmp_path)
    workflow = runtime.Workflow(store, tools, ScriptedProvider([]), tmp_path / "run", "batch-read",
        lambda path, initial: FixtureController(str(path), initial, 2), lambda *_: 0,
        restoration_settings={"preview_size": preview})
    source = workflow.build("annotation", "root", "Synthetic publication custody", {"subject_refs": ["subject_A"]}).source
    return store, workflow, source


def saved_decision(workflow, source, index, outcome, *, action=True):
    workflow.journal.save("runtime_model_calls", {"episode_id": source.episode_id,
        "call_index": index, "purpose": "decision", "request": json.dumps({"context": {}, "schema": obj({})}),
        "response": json.dumps(tool()["selection"])})
    if action:
        workflow.journal.save("runtime_actions", {"episode_id": source.episode_id,
            "decision_index": index, "action": json.dumps(tool()["selection"]),
            "result": json.dumps(outcome) if outcome is not None else None, "credit": None})


def test_publication_page_preserves_duplicates_status_and_reads_no_archived_body(tmp_path, monkeypatch):
    store, workflow, source = workflow_source(tmp_path)
    marker = "LARGE_ARCHIVED_RESULT_NOT_A_PUBLICATION_PAGE"
    refs = ["observation_a", "observation_b", "observation_a"]
    saved_decision(workflow, source, 0, {"status": "partial", "record_refs": refs,
        "result": {"text": marker + "x" * 100000}})
    original_db = store.db
    class Cursor:
        def __init__(self, cursor): self.cursor = cursor
        @staticmethod
        def check(row):
            assert row is None or all(not isinstance(v, str) or marker not in v for v in row)
            return row
        def fetchone(self): return self.check(self.cursor.fetchone())
        def __iter__(self): return (self.check(row) for row in self.cursor)
    class Database:
        def execute(self, *a, **k): return Cursor(original_db.execute(*a, **k))
        def __getattr__(self, name): return getattr(original_db, name)
    store.db = workflow.journal.db = Database()
    original_loads = runtime.json.loads
    def no_body(text, *args, **kwargs):
        assert marker not in text
        return original_loads(text, *args, **kwargs)
    monkeypatch.setattr(runtime.json, "loads", no_body)
    # preview zero reuses the ordinary positive page default, not a new limit.
    args = {"view": "publications", "decision_index": 0}
    pages = []
    while args is not None:
        result = workflow.history_read(source, args, before=1)
        assert result["status"] == "completed" and result["record_refs"] == result["changed_record_refs"] == []
        page = result["result"]
        assert page["total"] == 3 and page["limit"] == 1 and page["result_recorded"]
        assert page["action_status"] == "partial"
        pages += page["records"]
        args = page["next_query"]
    assert pages == [{"publication_index": i, "record_ref": ref} for i, ref in enumerate(refs)]
    assert original_db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 1
    assert original_db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_publication_pending_unknown_completed_empty_and_prior_owner_boundary(tmp_path):
    store, workflow, source = workflow_source(tmp_path)
    saved_decision(workflow, source, 0, {"status": "completed", "record_refs": []})
    saved_decision(workflow, source, 1, None)
    saved_decision(workflow, source, 2, None, action=False)
    for index, status, total, recorded in [(0, "completed", 0, True), (1, "pending", None, False),
                                          (2, "unexecuted", None, False)]:
        page = workflow.history_read(source, {"view": "publications", "decision_index": index}, before=3)["result"]
        assert (page["action_status"], page["total"], page["result_recorded"]) == (status, total, recorded)
        assert page["records"] == [] and page["next_query"] is None
    other = workflow.build("annotation", "other", "Synthetic other owner", {"subject_refs": ["subject_A"]}).source
    assert workflow.history_read(other, {"view": "publications", "decision_index": 0}, before=3)["feedback"]["code"] == "history_decision_not_available"
    for index in (3, 100):
        assert workflow.history_read(source, {"view": "publications", "decision_index": index}, before=3)["status"] == "invalid"
    assert workflow.history_read(source, {"view": "publications", "decision_index": 0, "episode_id": "another"}, before=3)["status"] == "invalid"


@pytest.mark.parametrize("preview_size", [0, 2])
def test_declared_partial_preview_is_nonmutating_and_never_recursive(preview_size):
    workflow = runtime.Workflow.__new__(runtime.Workflow)
    workflow.restoration_settings = {"preview_size": preview_size}
    refs = ["one", "two", "three"]
    failed = {"status": "partial", "record_refs": refs, "result": {"retained_record_refs": refs},
        "published_batch": {"representation": "native_publications_v1", "published_rows_total": 1,
            "failure_rows_total": None, "observation_query": None}, "feedback": {"code": "synthetic_late_failure"}}
    before = deepcopy(failed)
    shown = workflow.local_outcome_preview(failed, decision_index=7)
    assert failed == before and shown["record_refs"] == shown["result"]["retained_record_refs"] == refs[:preview_size]
    assert shown["automatic_preview"]["record_refs"]["total"] == 3
    assert shown["automatic_preview"]["rows"] == {"total": 1, "included": 0, "truncated": True}
    assert shown["automatic_preview"]["publication_query"] == {
        "view": "publications", "decision_index": 7, "offset": 0, "limit": max(1, preview_size)}
    exact = {"status": "completed", "record_refs": [], "result": {"records": [{"outcome": failed}]}}
    assert workflow.local_outcome_preview(exact) is exact
    form = {"child_reports": [{"actual_refs": refs, "published_batch": failed["published_batch"]}]}
    assert workflow.local_outcome_preview(form) is form
    selected = {"status": "completed", "record_refs": refs, "result": {"records": refs}}
    assert workflow.local_outcome_preview(selected) is selected


def test_actual_read_batches_keep_sources_partial_rows_and_exact_selected_reads(tmp_path):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from test_library_targets import library, members
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        tools = ToolRegistry(store)
        workflow = runtime.Workflow.__new__(runtime.Workflow)
        workflow.restoration_settings = {"preview_size": 1}
        inspected = tools.execute("reads.inspect", {"subject_refs": [a["id"], b["id"]]})
        assert inspected["published_batch"]["published_rows_total"] == 2
        query = inspected["published_batch"]["observation_query"]
        observed = tools.execute("state.query", {**query, "limit": 10})
        assert "published_batch" not in observed
        assert observed["result"]["total"] == 2
        assert {r["subject_refs"][0] for r in observed["result"]["records"]} == {a["id"], b["id"]}
        shown = workflow.local_outcome_preview(inspected, decision_index=0)
        assert len(shown["record_refs"]) == len(shown["result"]["records"]) == 1
        assert workflow.local_outcome_preview(observed) is observed
        args = {"subject_refs": [a["id"], b["id"], target["id"], a["member_ref"], b["member_ref"]],
            "reference_ref": a["id"], "molecule": "dna", "mode": "local"}
        aligned = tools.execute("reads.align", args, operation_key="actual-partial-alignments")
        assert aligned["status"] == "partial"
        assert aligned["published_batch"]["published_rows_total"] == 2
        assert aligned["published_batch"]["failure_rows_total"] == 3
        assert aligned["published_batch"]["observation_query"] is None  # separate actual sources
        shown = workflow.local_outcome_preview(aligned, decision_index=1)
        assert shown["automatic_preview"]["failures"] == {"total": 3, "included": 1, "truncated": True}
        assert len(shown["result"]["errors"]) == len(shown["feedback"]["rows"]) == 1
        assert len(aligned["result"]["errors"]) == len(aligned["feedback"]["rows"]) == 3
        replay = tools.execute("reads.align", args, operation_key="actual-partial-alignments")
        assert replay == aligned
        assert not store.current_annotations()


@pytest.mark.parametrize("name,arguments", [
    ("sequence.view", {"molecule": "dna", "segments": [{"start": 2, "end": 8}]}),
    ("sequence.translate", {"code": 11}),
])
def test_actual_small_derivations_share_generated_publication_contract(tmp_path, name, arguments):
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from test_library_targets import library, members
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, _ = members(store, target)
        outcome = ToolRegistry(store).execute(name, {"subject_ref": a["id"], **arguments})
        assert outcome["status"] == "completed"
        assert outcome["published_batch"]["published_rows_total"] == 1
        assert len(outcome["record_refs"]) == 5
        assert outcome["published_batch"]["observation_query"]["references"] == [outcome["result"]["source_ref"]]


def test_actual_all_failed_read_batch_bounds_repeated_feedback_but_observes_only_next_read(tmp_path):
    import asyncio
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from test_library_targets import library, members
    with Store(tmp_path / "state") as store:
        _, target = library(store, tmp_path, molecule="dna")
        a, b = members(store, target)
        args = {"subject_refs": [target["id"], a["member_ref"], b["member_ref"]],
            "reference_ref": a["id"], "molecule": "dna", "mode": "local"}
        responses = [{"selection": {"kind": "tool", "tool": "reads.align", "arguments": args}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "state.query", "arguments": {"refs": [a["id"]]}}, "report_update": {}}]
        provider = ScriptedProvider(responses)
        summary = asyncio.run(runtime.run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", restoration_settings={"preview_size": 1},
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        context = provider.contexts[1]
        assert context["last_local_outcome"]["status"] == "invalid"
        assert len(context["feedback"]["rows"]) == len(context["last_local_outcome"]["feedback"]["rows"]) == 1
        assert context["last_local_outcome"]["automatic_preview"]["failures"]["total"] == 3
        full = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0])
        assert len(full["feedback"]["rows"]) == 3
        assert summary["completed_actions"] == 1
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
