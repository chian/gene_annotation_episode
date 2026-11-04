"""Offline fixtures for bounded recovery and actual own-Episode history reads.

No native model/network calls. Fixture continuation counts are test boundaries,
not production budgets, estimator behavior, or biological success evidence.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode import runtime
from test_runtime import (FixtureController, FixtureTools, ScriptedProvider,
    commission, obj, reason, run, setup, tool)


def history(indices=None, *, view="records", report=None, **arguments):
    args = {"view": view, **arguments}
    if indices is not None:
        args["decision_indices"] = indices
    return {"selection": {"kind": "tool", "tool": "episode.history", "arguments": args},
            "report_update": report or {}}


def call_hashes(store, before):
    return [(row[0], hashlib.sha256(row[1].encode()).hexdigest(),
             hashlib.sha256(row[2].encode()).hexdigest()) for row in store.db.execute(
        "SELECT call_index,request,response FROM runtime_model_calls WHERE call_index<? "
        "AND response IS NOT NULL ORDER BY episode_id,call_index", (before,))]


def test_long_active_resume_adds_bounded_metadata_without_rewriting_or_reexecuting(tmp_path):
    store, _ = setup(tmp_path)
    marker = "ARCHIVED_SOURCE_BODY_EXCLUDED_FROM_AUTOMATIC_RESTORATION"
    body = marker + "x" * 128000

    class BodyTools(FixtureTools):
        def execute(self, name, args, scope=None, operation_key=None):
            self.executions += 1
            if args["result"] == "unavailable":
                return {"status": "failed", "record_refs": [],
                        "feedback": {"code": "synthetic_original_failure"}, "result": {"text": body}}
            old = self.store.db.execute("SELECT result FROM synthetic_operations WHERE id=?",
                                        (operation_key,)).fetchone()
            if old:
                return json.loads(old[0])
            self.commits += 1
            result = {"status": "completed", "record_refs": [], "changed_record_refs": [],
                      "result": {"text": body, "page": args["page"]}}
            self.store.db.execute("INSERT INTO synthetic_operations VALUES (?,?)",
                                  (operation_key, json.dumps(result)))
            self.store.db.commit()
            return result

    tools = BodyTools(store)
    first = ScriptedProvider([tool("unavailable"), *[tool(page=index) for index in range(40)],
                              reason(1), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, first, tmp_path / "run", counts=(42, 42),
            restoration_settings={"preview_size": 3})
    before = call_hashes(store, 42)
    observations = store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]
    assert len(before) == 42 and observations == 41
    assert tools.executions == 41 and tools.commits == 40
    resumed = ScriptedProvider([reason(2)])
    result = run(store, tools, resumed, None, counts=(42, 42), resume=True)
    assert len(resumed.contexts) == 1
    context = resumed.contexts[0]
    preview = context["restored_episode_history"]
    assert preview["total_prior_decisions"] == 42
    assert preview["preview_size"] == 3 and preview["omitted_prior_decisions"] == 39
    assert [row["decision_index"] for row in preview["entries"]] == [39, 40, 41]
    assert set(preview["entries"][0]) == {"decision_index", "kind", "tool", "status", "credit"}
    assert len(json.dumps(preview)) < 1000
    assert "restored_visible_conversation" not in context and marker not in json.dumps(context)
    assert context["current_credit"] == 1
    assert context["controller"]["scores"] == [0] * 40 + [1]
    assert context["current_report_update"] == {} and context["requested_report_purpose"] is None
    assert context["credit_binding"]["kind"] == "custom"
    assert context["current_report_basis_refs"]
    assert result["credit"] == 3 and result["completed_actions"] == 42
    assert tools.executions == 41  # no old tool is repeated during recovery
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == observations+1
    assert call_hashes(store, 42) == before
    saved_context = json.loads(store.db.execute("SELECT request FROM runtime_model_calls "
        "WHERE call_index=42").fetchone()[0])["context"]
    assert saved_context == context
    assert "restored_visible_conversation" not in saved_context


def test_automatic_preview_never_decodes_or_returns_archived_contexts_and_outcomes(tmp_path, monkeypatch):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([reason(0)])
    workflow = runtime.Workflow(store, tools, provider, tmp_path / "run", "metadata-only",
        lambda path, initial: FixtureController(str(path), initial, 2),
        lambda *_: 0, restoration_settings={"preview_size": 2})
    scope = {"subject_refs": ["subject_A"]}
    source = workflow.build("annotation", "root", "Synthetic metadata audit", scope).source
    marker = "FULL_ARCHIVED_PAYLOAD_MUST_NOT_ENTER_PYTHON"
    for index in range(8):
        workflow.journal.save("runtime_model_calls", {"episode_id": source.episode_id,
            "call_index": index, "purpose": "decision", "request": json.dumps({
                "context": {"text": marker + "x" * 100000}, "schema": obj({})}),
            "response": json.dumps({"selection": {"kind": "tool", "tool":
                                     "fixture.measure" if index != 6 else marker + "invalid" * 10000,
                                     "arguments": {"text": marker + "y" * 100000}}})})
        workflow.journal.save("runtime_actions", {"episode_id": source.episode_id, "decision_index": index,
            "action": json.dumps(tool()["selection"]),
            "result": (json.dumps({"status": "completed", "result": {"text": marker + "z" * 100000}})
                       if index != 7 else None),
            "credit": 0 if index != 7 else None})
    source.calls = 8
    original_db, original_loads = store.db, json.loads

    class GuardCursor:
        def __init__(self, cursor):
            self.cursor = cursor
        @staticmethod
        def check(row):
            if row is not None:
                assert all(not isinstance(value, str) or marker not in value for value in row)
            return row
        def __iter__(self):
            return (self.check(row) for row in self.cursor)
        def fetchone(self):
            return self.check(self.cursor.fetchone())
        def fetchall(self):
            return [self.check(row) for row in self.cursor.fetchall()]

    class GuardDB:
        def execute(self, *args, **kwargs):
            return GuardCursor(original_db.execute(*args, **kwargs))
        def __getattr__(self, name):
            return getattr(original_db, name)

    def guard_loads(text, *args, **kwargs):
        assert not isinstance(text, str) or marker not in text
        return original_loads(text, *args, **kwargs)

    store.db = workflow.journal.db = GuardDB()
    monkeypatch.setattr(runtime.json, "loads", guard_loads)
    import asyncio
    asyncio.run(source.call({"visible_record_refs": [], "current_report_update": {}}, obj({})))
    assert [row["decision_index"] for row in provider.contexts[0]["restored_episode_history"]["entries"]] == [6, 7]
    assert [row["status"] for row in provider.contexts[0]["restored_episode_history"]["entries"]] == ["completed", "pending"]
    assert provider.contexts[0]["restored_episode_history"]["entries"][0]["tool"] is None
    assert provider.contexts[0]["restored_episode_history"]["entries"][-1]["credit"] is None
    assert original_db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 8
    assert original_db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_selected_exact_recall_preserves_failure_and_is_one_zero_gain_read_even_on_resume(tmp_path, monkeypatch):
    store, tools = setup(tmp_path)
    calls = []
    original = runtime.Workflow.history_read
    def observed(self, source, arguments, **kwargs):
        calls.append(deepcopy(arguments))
        return original(self, source, arguments, **kwargs)
    monkeypatch.setattr(runtime.Workflow, "history_read", observed)
    first = ScriptedProvider([tool("unavailable"), reason(1), history([0, 1]), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, first, tmp_path / "run", counts=(3, 3))
    saved = first.contexts[-1]["last_local_outcome"]
    records = saved["result"]["records"]
    assert saved["status"] == "completed" and saved["record_refs"] == []
    assert records[0]["outcome"]["status"] == "unavailable"
    assert records[0]["outcome"]["feedback"] == {"code": "fixture_unavailable"}
    assert records[0]["status"] == "unavailable" and records[0]["credit"] is None
    assert records[0]["selection"] == tool("unavailable")["selection"]
    assert records[1]["selection"] == reason(1)["selection"]
    assert first.contexts[-1]["controller"]["scores"] == [1, 0]
    resumed = ScriptedProvider([reason(2)])
    result = run(store, tools, resumed, None, counts=(3, 3), resume=True)
    assert resumed.contexts[0]["last_local_outcome"] == saved
    assert len(calls) == tools.executions == 1  # selected read cached, old failure never rerun
    assert result["completed_actions"] == 3 and result["credit"] == 3
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
    assert [json.loads(row[0])["step"]["delta"] for row in store.db.execute(
        "SELECT observation FROM runtime_observations ORDER BY unit_index")] == [1, 0, 2]


def test_history_is_bound_to_owner_and_parent_gets_only_admitted_child_form(tmp_path):
    store, tools = setup(tmp_path)
    schema = obj({"interpretation": {"type": "string", "enum": ["unresolved", "supported"]}})
    forbidden = history([0], episode_id="another_episode")
    forbidden["report_update"] = {"interpretation": "supported"}
    provider = ScriptedProvider([commission(schema, {"interpretation": "unresolved"}),
        reason(2, {"interpretation": "supported"}), forbidden,
        history([0], report={"interpretation": "supported"}), history([0]), reason(1)])
    result = run(store, tools, provider, tmp_path / "run", counts=(3, 2))
    assert provider.contexts[3]["feedback"]["category"] == "action_contract"
    child_recall = provider.contexts[4]["working_state"]  # shared science is still legitimately available
    assert child_recall
    parent_recall = provider.contexts[5]["last_local_outcome"]["result"]["records"][0]
    assert parent_recall["selection"]["kind"] == "child"
    assert parent_recall["admitted_report"] == {"interpretation": "supported"}
    assert "fixture_value" not in json.dumps(parent_recall)
    # Child index zero was its own reason action, not the parent's commission.
    child_id = next(row[0] for row in store.db.execute("SELECT episode_id FROM runtime_episodes WHERE path LIKE '%improvement%'"))
    child_read = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE episode_id=? "
        "AND action LIKE '%episode.history%'", (child_id,)).fetchone()[0])
    assert child_read["result"]["records"][0]["selection"] == reason(2)["selection"]
    assert child_read["result"]["records"][0]["admitted_report"] is None
    assert result["completed_actions"] == 3 and tools.executions == 0
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 5


def test_recall_does_not_deliver_rejected_child_form(tmp_path):
    from test_runtime import delivery_schema
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([commission(delivery_schema(), {"interpretation": "unresolved"}),
        reason(2, {"interpretation": "unresolved"}), tool(report={"interpretation": "supported"}), history([0])])
    result = run(store, tools, provider, tmp_path / "run", counts=(2, 2))
    parent_id = next(row[0] for row in store.db.execute("SELECT episode_id FROM runtime_episodes WHERE path NOT LIKE '%improvement%'"))
    read = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE episode_id=? "
        "AND action LIKE '%episode.history%'", (parent_id,)).fetchone()[0])
    record = read["result"]["records"][0]
    assert record["admitted_report"] is None
    assert record["report_delivery_failure"]["kind"] == "report_delivery_failure"
    assert "form" not in record and result["pending_report_deliveries"] == 1
    assert result["completed_actions"] == 2  # recall does not pretend to repair delivery


@pytest.mark.parametrize("index", [0, 5])
def test_current_or_future_decision_cannot_be_recalled(tmp_path, index):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([history([index]), reason(1)])
    result = run(store, tools, provider, tmp_path / "run", counts=(1, 1))
    assert provider.contexts[1]["feedback"]["code"] == "history_decision_not_available"
    assert result["completed_actions"] == 1 and tools.executions == 0
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1


def test_restoration_config_is_canonical_persisted_and_immutable_on_resume(tmp_path, monkeypatch):
    from gene_annotation_episode.providers import default_config_path
    import tomllib
    store, tools = setup(tmp_path)
    config = tomllib.loads(default_config_path().read_text())
    # This test supplies fixture credit and continuation functions. Their
    # configuration is not the application's unused default numeric policy.
    config.pop("controller", None)
    config.pop("credit", None)
    assert config["restoration"] == {"preview_size": 24}
    config["restoration"] = {"preview_size": 5}
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([reason(1), KeyboardInterrupt()]), tmp_path / "run",
            provider_config=config, restoration_settings={"preview_size": 2})
    persisted = json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
    assert persisted["restoration"] == {"preview_size": 2}
    assert json.loads((tmp_path / "run/run.json").read_text())["restoration"] == {"preview_size": 2}
    # A changed package default cannot silently replace the recorded caller choice.
    changed_default = tmp_path / "new-defaults.toml"
    changed_default.write_text(default_config_path().read_text().replace("preview_size = 24", "preview_size = 99"))
    monkeypatch.setattr("gene_annotation_episode.providers.default_config_path", lambda: changed_default)
    resumed = ScriptedProvider([reason(1)])
    run(store, tools, resumed, None, resume=True)
    assert resumed.contexts[0]["restored_episode_history"]["preview_size"] == 2
    with pytest.raises(runtime.WorkflowError, match="restoration settings"):
        run(store, tools, ScriptedProvider([]), None, resume=True, restoration_settings={"preview_size": 3})
    assert persisted["models"] == json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])["models"]


def test_index_paging_unexecuted_decision_and_zero_preview_are_exact(tmp_path):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([{"selection": "invalid_selection_fixture", "report_update": {}},
        reason(1), history(view="index", offset=0, limit=1), history([0])])
    result = run(store, tools, provider, tmp_path / "run", counts=(3, 3),
                 restoration_settings={"preview_size": 0})
    assert provider.contexts[1]["restored_episode_history"]["entries"] == []
    assert provider.contexts[1]["restored_episode_history"]["total_prior_decisions"] == 1
    index = provider.contexts[3]["last_local_outcome"]["result"]
    assert index["entries"] == [{"decision_index": 0, "kind": "unrecognized", "tool": None,
                                  "status": "unexecuted", "credit": None}]
    assert index["next_offset"] == 1
    root_id = store.db.execute("SELECT episode_id FROM runtime_episodes").fetchone()[0]
    exact = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE episode_id=? "
        "AND decision_index=3", (root_id,)).fetchone()[0])
    assert exact["result"]["records"][0]["selection"] == "invalid_selection_fixture"
    assert exact["result"]["records"][0]["outcome"] is None
    assert result["completed_actions"] == 3


@pytest.mark.parametrize("view", ["index", "records"])
def test_disabled_automatic_preview_keeps_default_ordinary_page_advancing(tmp_path, view):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([reason(1), reason(2), history(view=view)])
    result = run(store, tools, provider, tmp_path / "run", counts=(3, 3),
                 restoration_settings={"preview_size": 0})
    assert provider.contexts[-1]["restored_episode_history"]["entries"] == []
    read = json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=2").fetchone()[0])
    page = read["result"]
    assert page["offset"] == 0 and page["limit"] == 1 and page["next_offset"] == 1
    assert page["total_prior_decisions"] == 2
    values = page["entries"] if view == "index" else page["records"]
    assert len(values) == 1 and values[0]["decision_index"] == 0
    if view == "records":
        assert values[0]["selection"] == reason(1)["selection"]
    assert result["completed_actions"] == 3 and result["credit"] == 3
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
