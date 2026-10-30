"""Runtime contract tests with explicitly synthetic providers/state/controllers.

These fixtures exercise accounting and communication, not biological accuracy
and not the production numerical estimator's stopping behavior.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.runtime import (
    Journal, Record, WorkflowError, _action_generation_schema,
    _decode_action_response, run_workflow,
)
from gene_annotation_episode.state import Store


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


class FixtureStore:
    """Synthetic semantic state: no external or biological evidence is claimed."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self._savepoint = 0
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE synthetic_records(id TEXT PRIMARY KEY, payload TEXT);
        CREATE TABLE synthetic_operations(id TEXT PRIMARY KEY, result TEXT);
        """)
        for name in ("subject_A", "subject_B"):
            self.add({"id": name, "record_type": "subject", "subject_refs": [name]})

    def add(self, row):
        self.db.execute("INSERT OR REPLACE INTO synthetic_records VALUES(?,?)", (row["id"], json.dumps(row)))
        self.db.commit()

    # This fixture supplies the same transaction port as the authoritative
    # Store so journal helpers can participate in caller-owned transactions.
    transaction = Store.transaction

    @contextmanager
    def read_snapshot(self):
        yield

    def problem(self):
        return {"id": "synthetic_problem", "subject_refs": ["subject_A", "subject_B"]}

    def validate_scope(self, scope, parent_scope=None):
        if set(scope) != {"subject_refs"} or not scope["subject_refs"]:
            raise ValueError("invalid_scope")
        allowed = set((parent_scope or self.problem())["subject_refs"])
        if not set(scope["subject_refs"]) <= allowed:
            raise ValueError("scope_outside_parent")
        return deepcopy(scope)

    def get(self, ref):
        row = self.db.execute("SELECT payload FROM synthetic_records WHERE id=?", (ref,)).fetchone()
        if row is None:
            raise KeyError(ref)
        return json.loads(row[0])

    def references(self, scope):
        rows = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM synthetic_records")]
        rows = [row for row in rows if set(row["subject_refs"]) <= set(scope["subject_refs"])]
        return {kind: [row["id"] for row in rows if row["record_type"] == kind]
                for kind in ("subject", "assessment", "observation")}

    def reference_subset(self, candidates, scope):
        # Fixture implementation of the Store's candidate-resolution seam.
        # Synthetic subject IDs are not a production scientific namespace.
        accepted = []
        for ref in candidates:
            try:
                row = self.get(ref)
            except KeyError:
                continue
            if (row["record_type"] in {"subject", "assessment", "observation"}
                    and set(row["subject_refs"]) <= set(scope["subject_refs"])):
                accepted.append(ref)
        return accepted

    def reasoning_view(self, scope, limit=24):
        refs = self.references(scope)
        return {"records": [self.get(ref) for values in refs.values() for ref in values][:limit]}

    def reasoning_schema(self):
        return obj({"fixture_value": {"type": "number"}})

    def commit_reasoning(self, payload, scope, operation_key):
        old = self.db.execute("SELECT result FROM synthetic_operations WHERE id=?", (operation_key,)).fetchone()
        if old:
            return json.loads(old[0])
        ref = "assessment_" + str(self.db.execute("SELECT COUNT(*) FROM synthetic_records").fetchone()[0])
        self.add({"id": ref, "record_type": "assessment", "subject_refs": scope["subject_refs"],
                  "fixture_value": payload["fixture_value"]})
        result = {"status": "completed", "record_refs": [ref], "changed_record_refs": [ref]}
        self.db.execute("INSERT INTO synthetic_operations VALUES (?,?)", (operation_key, json.dumps(result)))
        self.db.commit()
        return result


def fixture_credit(store, scope):
    return sum(row.get("fixture_value", 0) for row in store.reasoning_view(scope, limit=1000)["records"])


class FixtureTools:
    def __init__(self, store):
        self.store, self.executions, self.commits = store, 0, 0

    def catalog(self, scope=None):
        return [{"name": "fixture.measure", "input_schema": obj({"result": {"type": "string",
                    "enum": ["completed", "unavailable"]}, "page": {"type": "integer"}})}]

    def execute(self, name, args, scope=None, operation_key=None):
        self.executions += 1
        old = self.store.db.execute("SELECT result FROM synthetic_operations WHERE id=?", (operation_key,)).fetchone()
        if old:
            return json.loads(old[0])
        if args["result"] == "unavailable":
            return {"status": "unavailable", "record_refs": [], "feedback": {"code": "fixture_unavailable"}}
        self.commits += 1
        refs = []
        for index in range(15):
            ref = f"observation_{self.commits}_{args['page']}_{index}"
            refs.append(ref)
            self.store.add({"id": ref, "record_type": "observation", "subject_refs": scope["subject_refs"]})
        result = {"status": "completed", "record_refs": refs,
                  "changed_record_refs": refs, "result": {"page": args["page"], "records": refs}}
        self.store.db.execute("INSERT INTO synthetic_operations VALUES (?,?)", (operation_key, json.dumps(result)))
        self.store.db.commit()
        return result


class FixtureController:
    """Test-only continuation seam, not an application action limit."""
    def __init__(self, epoch, initial, stop_after):
        self.epoch, self.initial, self.current, self.stop_after = epoch, initial, initial, stop_after
        self.scores = []

    def observe(self, label, value, *, is_root):
        value = value.as_record()["credit"]
        self.scores.append(value-self.current)
        self.current = value
        stop = len(self.scores) >= self.stop_after
        return FixtureStep(stop, self.scores[-1])

    def state(self):
        return FixtureState(self.scores, self.current, len(self.scores) >= self.stop_after)

    def transitioned(self, epoch):
        raise AssertionError("no runtime-owned epoch transition")


class FixtureStep:
    requests_transition = False
    def __init__(self, stop, delta):
        self.stop, self.delta = stop, delta
    def as_record(self):
        return {"stop": self.stop, "requests_transition": False, "delta": self.delta}


class FixtureState:
    def __init__(self, scores, value, stop):
        self.scores, self.value, self.decision = list(scores), value, SimpleNamespace(stop=stop)
    def as_record(self):
        return {"scores": self.scores, "credit": self.value, "decision": {"stop": self.decision.stop}}


class ScriptedProvider:
    """Explicit fixture responses; never a claim of live model behavior."""
    def __init__(self, script):
        self.script, self.contexts, self.released = iter(script), [], []
    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == "REASONING"
        assert "competing explanations" in instructions
        self.contexts.append(deepcopy(context))
        response = next(self.script)
        if isinstance(response, BaseException):
            raise response
        return response(context) if callable(response) else deepcopy(response)
    async def release(self, episode_id):
        self.released.append(episode_id)


def reason(value, report=None):
    return {"selection": {"kind": "reason", "commit": {"fixture_value": value}}, "report_update": report or {}}


def tool(status="completed", page=0, report=None):
    return {"selection": {"kind": "tool", "tool": "fixture.measure",
            "arguments": {"result": status, "page": page}}, "report_update": report or {}}


def commission(schema, initial):
    return {"selection": {"kind": "child", "goal": "Iteratively investigate the synthetic comparison",
        "scope": {"subject_refs": ["subject_A"]}, "purpose": "Choose the next synthetic comparison",
        "schema_json": json.dumps(schema), "initial_report_json": json.dumps(initial)}, "report_update": {}}


def setup(tmp_path):
    store = FixtureStore(tmp_path / "state.db")
    return store, FixtureTools(store)


def run(store, tools, provider, path, counts=(2, 2), **kwargs):
    import asyncio
    factory = lambda episode_path, initial: FixtureController(str(episode_path), initial,
        counts[0] if len(episode_path) == 1 else counts[1])
    return asyncio.run(run_workflow(store, tools, provider=provider, run_dir=path,
        controller_factory=factory, project_credit=fixture_credit, **kwargs))


def test_reasoning_uses_existing_state_and_signed_corrections(tmp_path):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([reason(3), reason(-1)])
    result = run(store, tools, provider, tmp_path / "run")
    assert result["completed_actions"] == 2
    assert tools.executions == 0
    assert provider.contexts[1]["current_credit"] == 3
    assert provider.contexts[1]["current_evidence_vector"] is None
    rows = store.db.execute("SELECT observation FROM runtime_observations ORDER BY unit_index").fetchall()
    assert [json.loads(row[0])["step"]["delta"] for row in rows] == [3, -1]
    assert result["scientific_completion"] == "not_established_by_termination"
    assert provider.released


def test_child_iterates_and_returns_only_parent_form_without_composer(tmp_path):
    store, tools = setup(tmp_path)
    schema = obj({"interpretation": {"type": "string", "enum": ["unresolved", "supported"]},
                  "assessment_refs": {"type": "array", "items": {"type": "string", "format": "reference",
                                      "x-reference-namespace": "assessment"}, "x-source": "changed_assessment_refs"},
                  "latest_refs": {"type": "array", "items": {"type": "string", "format": "reference"},
                                  "x-source": "last_outcome_refs"},
                  "uninterpreted": {"type": "array", "items": {"type": "string", "format": "reference"},
                                  "x-source": "observations_after_report_basis"}})
    provider = ScriptedProvider([commission(schema, {"interpretation": "unresolved"}),
        reason(2, {"interpretation": "unresolved"}), tool(report={"interpretation": "supported"}), reason(1)])
    result = run(store, tools, provider, tmp_path / "run")
    assert len(provider.contexts) == 4  # no final report/composer call
    assert provider.contexts[2]["current_credit"] == 2
    parent = provider.contexts[3]
    assert len(parent["child_reports"]) == 1
    form = parent["child_reports"][0]
    assert set(form) == set(schema["properties"])
    assert form["interpretation"] == "supported"
    assert len(form["assessment_refs"]) == 1
    assert len(form["latest_refs"]) == len(form["uninterpreted"]) == 15
    assert parent["current_credit"] == 2
    counts = store.db.execute("SELECT episode_id,COUNT(*) FROM runtime_observations GROUP BY episode_id").fetchall()
    assert sorted(row[1] for row in counts) == [2, 2]  # child is one of two parent units
    assert result["episode_count"] == 2
    assert store.db.execute("SELECT COUNT(*) FROM runtime_episodes WHERE state='yielded' AND archive IS NOT NULL").fetchone()[0] == 2


def test_bad_report_preserves_science_and_exact_tool_page(tmp_path):
    store, tools = setup(tmp_path)
    schema = obj({"interpretation": {"type": "string", "enum": ["unresolved", "supported"]}})
    provider = ScriptedProvider([commission(schema, {"interpretation": "unresolved"}),
        reason(2, {"interpretation": "unrestricted explanation"}),
        tool(page=13, report={"interpretation": "supported"}), reason(1)])
    run(store, tools, provider, tmp_path / "run")
    child_next = provider.contexts[2]
    assert child_next["feedback"]["category"] == "report_format"
    assert child_next["current_credit"] == 2
    assert provider.contexts[3]["child_reports"] == [{"interpretation": "supported"}]
    stored = store.db.execute("SELECT result FROM runtime_actions WHERE action LIKE '%fixture.measure%'").fetchone()[0]
    assert len(json.loads(stored)["result"]["records"]) == 15
    assert json.loads(stored)["result"]["page"] == 13


def test_child_receives_actual_parent_purpose_and_current_admitted_form_values(tmp_path):
    """Actual commissioning/context path; no model call or biological claim."""
    class CapturingProvider(ScriptedProvider):
        def __init__(self, script):
            super().__init__(script)
            self.schemas = []

        async def complete(self, episode_id, role, instructions, context, output_schema):
            self.schemas.append(deepcopy(output_schema))
            return await super().complete(episode_id, role, instructions, context, output_schema)

    store, tools = setup(tmp_path)
    schema = obj({"interpretation": {"type": "string", "enum": ["unresolved", "supported"]},
                  "scoped_credit": {"type": "number", "x-source": "credit"}})
    initial = {"interpretation": "unresolved"}
    updated = {"interpretation": "supported"}
    purpose = "PARENT_PURPOSE_SENTINEL: distinguish the alternatives before choosing my next comparison."
    selected_child = commission(schema, initial)
    selected_child["selection"]["purpose"] = purpose
    provider = CapturingProvider([
        selected_child,
        reason(1, updated),
        reason(0, {"interpretation": "unrestricted prose is not an allowed form value"}),
        reason(0, initial),
        reason(0),
    ])
    result = run(store, tools, provider, tmp_path / "purpose-run", counts=(2, 3))
    assert len(provider.contexts) == 5  # no commissioning/report composer call
    first, second, after_invalid = provider.contexts[1:4]
    assert first["current_report_update"] == initial
    assert second["current_report_update"] == updated
    assert after_invalid["current_report_update"] == updated
    assert after_invalid["feedback"]["category"] == "report_format"
    for index, context in enumerate(provider.contexts):
        if index in (0, 4):
            assert context["requested_report_purpose"] is None
            assert context["current_report_update"] == {}
            assert context["requested_form"] is None
            assert provider.schemas[index]["properties"]["report_update"]["properties"] == {}
        else:
            assert context["requested_report_purpose"] == purpose
            assert context["requested_form"] == schema
            report_schema = provider.schemas[index]["properties"]["report_update"]
            assert report_schema == obj({"interpretation": schema["properties"]["interpretation"]})
    assert provider.contexts[-1]["child_reports"] == [{"interpretation": "unresolved", "scoped_credit": 1}]
    assert result["completed_actions"] == 2 and result["episode_count"] == 2
    observations = store.db.execute("SELECT episode_id,count(*) FROM runtime_observations GROUP BY episode_id").fetchall()
    assert sorted(row[1] for row in observations) == [2, 3]
    stored_child = store.db.execute("SELECT request FROM runtime_episodes WHERE path LIKE '%improvement%'").fetchone()
    assert json.loads(stored_child[0])["report_contract"]["decision"] == purpose


def test_unavailable_work_is_feedback_not_zero_observation(tmp_path):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([tool("unavailable"), reason(1), reason(2)])
    result = run(store, tools, provider, tmp_path / "run")
    assert result["completed_actions"] == 2
    assert provider.contexts[1]["feedback"] == {"code": "fixture_unavailable"}
    assert provider.contexts[1]["controller"]["scores"] == []
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 2


def test_resume_reuses_selected_work_and_controller_observations(tmp_path):
    store, tools = setup(tmp_path)
    interrupted = ScriptedProvider([reason(1), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, interrupted, tmp_path / "run")
    pending_context = json.loads(store.db.execute("SELECT request FROM runtime_model_calls "
        "WHERE response IS NULL").fetchone()[0])["context"]
    assert pending_context == interrupted.contexts[-1]
    resumed = ScriptedProvider([reason(2)])
    result = run(store, tools, resumed, None, resume=True)
    assert result["credit"] == 3
    assert len(resumed.contexts) == 1
    assert resumed.contexts[0]["current_credit"] == 1
    assert resumed.contexts[0] == pending_context
    assert "restored_visible_conversation" not in resumed.contexts[0]
    assert resumed.contexts[0]["restored_episode_history"]["entries"] == [
        {"decision_index": 0, "kind": "reason", "tool": None, "status": "completed", "credit": 1}]
    assert store.db.execute("SELECT COUNT(*) FROM synthetic_operations").fetchone()[0] == 2
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 2


def test_resume_reuses_closed_child_archives_without_duplicate_files(tmp_path):
    store, tools = setup(tmp_path)
    schema = obj({'credit': {'type': 'number', 'x-source': 'credit'}})
    first = ScriptedProvider([commission(schema, {}), reason(1), tool(), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, first, tmp_path/'run')
    row = store.db.execute("SELECT episode_id,archive FROM runtime_episodes WHERE state='yielded'").fetchone()
    original = dict(row)
    directory = tmp_path/'run/archive'
    files_before = {file.name for file in directory.iterdir()}
    # One child trace and one child result; the parent references the same trace
    # that the child already archived on closure.
    assert len(files_before) == 4
    observations_before = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
    resumed = ScriptedProvider([reason(0)])
    summary = run(store, tools, resumed, None, resume=True)
    after = store.db.execute('SELECT episode_id,archive FROM runtime_episodes WHERE episode_id=?',
        (original['episode_id'],)).fetchone()
    assert dict(after) == original
    # Only the newly closed parent adds an archive and its byte-offset index.
    files_after = {file.name for file in directory.iterdir()}
    root = next(row for row in store.db.execute('SELECT path,archive FROM runtime_episodes')
        if len(json.loads(row['path'])) == 1)
    descriptor = json.loads(root['archive'])
    root_file = descriptor['file']
    assert files_after-files_before == {root_file, root_file.removesuffix('.json')+'.index.json'}
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == observations_before+1
    assert len(resumed.contexts) == 1 and tools.executions == tools.commits == 1
    from method_loop.archive import ArchivedRecord
    expanded = ArchivedRecord(directory/root_file, descriptor['sha256'], descriptor['index_sha256']).load()
    assert expanded['units'][0]['child']['units_consumed'] == 2
    assert expanded['units'][0]['child_result']['form']['credit'] == 1
    assert run(store, tools, ScriptedProvider([]), None, resume=True) == summary
    assert {file.name for file in directory.iterdir()} == files_after


def test_resume_recovers_published_operation_before_runtime_response(tmp_path, monkeypatch):
    store, tools = setup(tmp_path)
    original = Journal.save
    crashed = False
    def crash_once(self, table, values):
        nonlocal crashed
        if table == "runtime_actions" and values.get("result") and not crashed:
            crashed = True
            raise RuntimeError("synthetic crash after semantic publication")
        return original(self, table, values)
    monkeypatch.setattr(Journal, "save", crash_once)
    with pytest.raises(RuntimeError, match="synthetic crash"):
        run(store, tools, ScriptedProvider([tool()]), tmp_path / "run", counts=(1, 1))
    result = run(store, tools, ScriptedProvider([]), tmp_path / "run", counts=(1, 1), resume=True)
    assert result["completed_actions"] == 1
    assert tools.executions == 2 and tools.commits == 1
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 1


def test_child_scoped_reference_error_does_not_discard_work(tmp_path):
    store, tools = setup(tmp_path)
    schema = obj({"target": {"type": "string", "format": "reference", "x-reference-namespace": "subject"}})
    provider = ScriptedProvider([commission(schema, {"target": "subject_A"}),
        reason(2, {"target": "subject_B"}), reason(1, {"target": "subject_A"}), reason(0)])
    run(store, tools, provider, tmp_path / "run")
    assert provider.contexts[2]["feedback"]["category"] == "report_format"
    assert provider.contexts[2]["current_credit"] == 2
    assert provider.contexts[3]["child_reports"] == [{"target": "subject_A"}]


def test_strict_transport_optional_null_roundtrip():
    schema = obj({"arguments": {"type": "object", "properties": {"required": {"type": "number"},
                 "optional": {"enum": ["one", "two"]}}, "required": ["required"], "additionalProperties": False}})
    transport = _action_generation_schema(schema)
    args = transport["properties"]["arguments"]
    assert set(args["required"]) == set(args["properties"])
    assert args["properties"]["optional"]["anyOf"][0]["type"] == "string"
    assert _decode_action_response({"arguments": {"required": 1, "optional": None}}, schema) == {"arguments": {"required": 1}}
    assert _decode_action_response({"arguments": {"required": None, "optional": None}}, schema) == {"arguments": {"required": None}}


def test_resume_rejects_configuration_replacement(tmp_path):
    store, tools = setup(tmp_path)
    run(store, tools, ScriptedProvider([reason(0)]), tmp_path / "run", counts=(1, 1))
    with pytest.raises(ValueError, match="custom_controller_owns_its_configuration"):
        run(store, tools, ScriptedProvider([]), tmp_path / "run", resume=True,
            controller_settings={"cost": .2})


def test_resume_keeps_unmentioned_caller_settings(tmp_path):
    store, tools = setup(tmp_path)
    run(store, tools, ScriptedProvider([reason(0)]), tmp_path / "run", counts=(1, 1),
        binding_definitions={"controller": {"kind": "fixture", "root_actions": 1, "child_actions": 1}})
    resumed = ScriptedProvider([])
    result = run(store, tools, resumed, None, counts=(1, 1), resume=True)
    assert result["completed_actions"] == 1
    assert not resumed.contexts
    settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert settings['controller'] is None and settings['credit_policy'] is None
    assert settings['binding_definitions']['controller'] == {'kind': 'fixture', 'root_actions': 1, 'child_actions': 1}


def test_custom_binding_definitions_are_actual_model_context_and_immutable_on_resume(tmp_path):
    store, tools = setup(tmp_path)
    definitions = {'credit': {'kind': 'fixture_assessment_sum', 'scale': 1},
                   'controller': {'kind': 'fixture', 'root_actions': 2, 'child_actions': 2}}
    provider = ScriptedProvider([reason(1), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, provider, tmp_path/'run', binding_definitions=definitions)
    saved = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert saved['credit_policy'] is saved['controller'] is None
    assert provider.contexts[0]['credit_binding']['definition'] == definitions['credit']
    assert provider.contexts[0]['controller_binding']['definition'] == definitions['controller']
    changed = deepcopy(definitions)
    changed['credit']['scale'] = 2
    with pytest.raises(WorkflowError, match='custom binding definitions'):
        run(store, tools, ScriptedProvider([]), tmp_path/'run', resume=True, binding_definitions=changed)
    resumed = ScriptedProvider([reason(1)])
    run(store, tools, resumed, None, resume=True)
    assert resumed.contexts[0]['credit_binding']['definition'] == definitions['credit']


def test_custom_callbacks_do_not_silently_ignore_default_policy_settings(tmp_path):
    store, tools = setup(tmp_path)
    for supplied in ({'credit_policy': {'scale': 10}}, {'provider_config': {'credit': {'scale': 10}}}):
        with pytest.raises(ValueError, match='custom_projector_owns_its_configuration'):
            run(store, tools, ScriptedProvider([]), tmp_path/'run', **supplied)


def test_actual_default_controller_resume_keeps_unspecified_caller_cost(tmp_path):
    import asyncio
    store, tools = setup(tmp_path)
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(run_workflow(store, tools, provider=ScriptedProvider([reason(0), KeyboardInterrupt()]),
            run_dir=tmp_path/'run', project_credit=fixture_credit, controller_settings={'cost': .02}))
    settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
    assert settings['controller']['cost'] == .02 and settings['credit_policy'] is None
    provider = ScriptedProvider([KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(run_workflow(store, tools, provider=provider, run_dir=None,
            resume=True, project_credit=fixture_credit, controller_settings={'window_size': 8}))
    assert provider.contexts[0]['controller_binding']['definition']['cost'] == .02
    assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1


def test_actual_schema_transport_is_closed_required_and_roundtrips(tmp_path):
    from gene_annotation_episode.domain import REASONING_SCHEMA
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.state import Store
    with Store(tmp_path / "schema-store") as store:
        store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein", role="protein")
        schemas = [REASONING_SCHEMA] + [definition["input_schema"]
                    for definition in ToolRegistry(store).catalog().values()]
        def visit(node):
            if not isinstance(node, dict):
                return
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                if isinstance(value, dict):
                    visit(value)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
        for schema in schemas:
            visit(_action_generation_schema(schema))


def test_empty_reasoning_is_feedback_without_fake_observation(tmp_path):
    store, tools = setup(tmp_path)
    empty = {"selection": {"kind": "reason", "commit": {"fixture_value": []}}, "report_update": {}}
    provider = ScriptedProvider([empty, reason(1)])
    result = run(store, tools, provider, tmp_path / "run", counts=(1, 1))
    assert result["completed_actions"] == 1
    assert provider.contexts[1]["feedback"]["category"] == "action_contract"
    assert "empty_reasoning_commit" in provider.contexts[1]["feedback"]["detail"]
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 1


def test_incompatible_fact_type_is_feedback_before_commission(tmp_path):
    store, tools = setup(tmp_path)
    schema = obj({"score": {"type": "boolean", "x-source": "credit"}})
    provider = ScriptedProvider([commission(schema, {}), reason(1)])
    result = run(store, tools, provider, tmp_path / "run", counts=(1, 1))
    assert result["episode_count"] == 1
    assert provider.contexts[1]["feedback"]["category"] == "action_contract"
    assert "different declared value type" in provider.contexts[1]["feedback"]["detail"]


def test_actual_store_partial_reasoning_retains_independent_rows(tmp_path):
    import asyncio
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    with Store(tmp_path / "partial") as store:
        problem = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein", role="protein")
        subject = problem["subject_refs"][0]
        payload = {name: [] for name in store.reasoning_schema()["properties"]}
        valid = {"alias": "valid", "subject_refs": [subject], "predicate": "sequence_integrity",
                 "value": {"type": "enum", "value": "unknown"}, "context_refs": []}
        payload["hypotheses"] = [valid, {**valid, "alias": "invalid", "predicate": "invalid_fixture_predicate"}]
        provider = ScriptedProvider([{"selection": {"kind": "reason", "commit": payload}, "report_update": {}}])
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "partial-run",
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 1)))
        assert result["completed_actions"] == 1
        assert len(store.list("hypothesis")) == 1
        recorded = json.loads(store.db.execute("SELECT result FROM runtime_actions").fetchone()[0])
        assert recorded["status"] == "partial"
        assert len(recorded["record_refs"]) == len(recorded["errors"]) == 1


def test_omitted_optional_contexts_does_not_make_empty_request_a_completed_action(tmp_path):
    import asyncio
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    with Store(tmp_path / "empty-actual") as store:
        problem = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")
        empty = {key: [] for key in store.reasoning_schema()["required"]}
        provider = ScriptedProvider([
            {"selection": {"kind": "reason", "commit": empty}, "report_update": {}},
            {"selection": {"kind": "tool", "tool": "sequence.inspect",
             "arguments": {"subject_ref": problem["subject_refs"][0]}}, "report_update": {}},
        ])
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "empty-run",
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 1)))
        assert result["completed_actions"] == 1
        assert "empty_reasoning_commit" in provider.contexts[1]["feedback"]["detail"]
        assert store.db.execute("SELECT COUNT(*) FROM runtime_actions").fetchone()[0] == 1
        assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 1


def test_transport_optional_null_is_decoded_even_when_another_reasoning_row_is_invalid(tmp_path):
    import asyncio
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    with Store(tmp_path / "transport-partial") as store:
        problem = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")
        text = "Synthetic construct A"
        artifact = store.artifact(text, "text/plain")
        source = store.put("source", {"provider": "synthetic_transport_fixture", "accession": None,
            "uri": None, "artifact_ref": artifact, "text_ref": None, "request_ref": None,
            "version": None, "retrieved_at": None}, origin="external")
        payload = {key: [] for key in store.reasoning_schema()["properties"]}
        payload["contexts"] = None  # strict provider representation of omission
        payload["source_subjects"] = [{"alias": "construct", "reference_type": "construct",
            "source_ref": source["id"], "label": "construct A", "anchor": {
                "source_ref": source["id"], "artifact_ref": artifact, "start": 0,
                "end": len(text.encode()), "quote": text}}]
        payload["hypotheses"] = [{"alias": "@bad", "subject_refs": problem["subject_refs"],
            "predicate": "sequence_integrity", "value": {"type": "enum", "value": "unknown"},
            "context_refs": []}]
        provider = ScriptedProvider([{"selection": {"kind": "reason", "commit": payload}, "report_update": {}}])
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "transport-partial-run",
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 1)))
        assert result["completed_actions"] == 1
        assert len(store.list("reference")) == 1 and not store.list("hypothesis")
        recorded = json.loads(store.db.execute("SELECT result FROM runtime_actions").fetchone()[0])
        assert recorded["status"] == "partial" and set(recorded["aliases"]) == {"construct"}
        assert recorded["errors"][0]["field_path"] == ["alias"]
        assert recorded["errors"][0]["schema_keyword"] == "pattern"
        assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 1


def test_transport_decoder_does_not_guess_ambiguous_or_missing_discriminators():
    first = {"type": "object", "properties": {"kind": {"const": "a"},
        "optional": {"type": "string"}, "required": {"type": "integer"}},
        "required": ["kind", "required"], "additionalProperties": False}
    value = {"kind": "a", "optional": None, "required": None}
    assert _decode_action_response(value, {"anyOf": [first]}) == {"kind": "a", "required": None}
    assert _decode_action_response(value, {"anyOf": [first, deepcopy(first)]}) == value
    untagged = {"optional": None, "required": None}
    assert _decode_action_response(untagged, {"anyOf": [first]}) == untagged


def delivery_schema():
    return obj({"interpretation": {"type": "string", "enum": ["unresolved", "supported"]},
        "outcome_refs": {"type": "array", "items": {"type": "string", "format": "reference"},
                         "maxItems": 0, "x-source": "last_outcome_refs"}})


def redeliver(schema):
    def response(context):
        return {"selection": {"kind": "redeliver_report", "delivery_ref": context["feedback"]["delivery_ref"],
            "purpose": "Read the actual saved outcome references", "schema_json": json.dumps(schema)},
            "report_update": {}}
    return response


def test_failed_child_delivery_parent_repairs_without_new_science_or_yield(tmp_path):
    from method_loop.archive import ArchivedRecord
    store, tools = setup(tmp_path)
    original = delivery_schema()
    repaired = deepcopy(original)
    del repaired["properties"]["outcome_refs"]["maxItems"]
    unavailable = deepcopy(repaired)
    unavailable["properties"]["new_judgment"] = {"type": "string", "enum": ["novel"]}
    unavailable["required"].append("new_judgment")
    provider = ScriptedProvider([commission(original, {"interpretation": "unresolved"}),
        reason(2, {"interpretation": "unresolved"}), tool(report={"interpretation": "supported"}),
        redeliver(unavailable), redeliver(repaired), reason(1)])
    result = run(store, tools, provider, tmp_path / "run")
    failed, rejected_meaning, repaired_parent = provider.contexts[3:]
    assert failed["feedback"]["kind"] == "report_delivery_failure"
    assert failed["feedback"]["reason"] == "maxItems"
    assert failed["child_reports"] == []
    assert rejected_meaning["feedback"]["reason"] == "recorded_interpretation_unavailable"
    assert rejected_meaning["child_reports"] == []
    assert repaired_parent["child_reports"][0]["interpretation"] == "supported"
    assert len(repaired_parent["child_reports"][0]["outcome_refs"]) == 15
    assert [context["controller"]["scores"] for context in (failed, rejected_meaning, repaired_parent)] == [[2], [2], [2]]
    assert tools.commits == tools.executions == 1
    assert result["completed_actions"] == 2 and result["credit"] == 3
    assert result["pending_report_deliveries"] == 0
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 4
    assert store.db.execute("SELECT COUNT(*) FROM runtime_report_attempts").fetchone()[0] == 3
    root_row = next(row for row in store.db.execute("SELECT path,archive FROM runtime_episodes")
                    if len(json.loads(row["path"])) == 1)
    descriptor = json.loads(root_row["archive"])
    archived = ArchivedRecord(tmp_path / "run" / "archive" / descriptor["file"],
                              descriptor["sha256"], descriptor["index_sha256"]).load()
    edge = archived["units"][0]
    assert edge["child"]["units_consumed"] == 2
    assert len(edge["episode_update"]["delivery_failures"]) == 2
    assert len(edge["episode_update"]["report"]["outcome_refs"]) == 15
    assert "maxItems" not in edge["episode_update"]["report_contract"]["measurements"]["schema"]["properties"]["outcome_refs"]


@pytest.mark.parametrize("after_redelivery", [False, True])
def test_report_repair_resume_preserves_child_science_and_observations(tmp_path, after_redelivery):
    store, tools = setup(tmp_path)
    original = delivery_schema()
    repaired = deepcopy(original)
    del repaired["properties"]["outcome_refs"]["maxItems"]
    script = [commission(original, {"interpretation": "unresolved"}),
              reason(2, {"interpretation": "unresolved"}), tool(report={"interpretation": "supported"})]
    if after_redelivery:
        script.append(redeliver(repaired))
    script.append(KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider(script), tmp_path / "run")
    before_operations = store.db.execute("SELECT COUNT(*) FROM synthetic_operations").fetchone()[0]
    before_observations = store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0]
    resumed = ScriptedProvider(([redeliver(repaired)] if not after_redelivery else []) + [reason(1)])
    result = run(store, tools, resumed, None, resume=True)
    assert before_operations == 2 and before_observations == 3
    assert result["completed_actions"] == 2 and result["credit"] == 3
    assert result["pending_report_deliveries"] == 0
    assert tools.commits == tools.executions == 1
    assert store.db.execute("SELECT COUNT(*) FROM synthetic_operations").fetchone()[0] == 3
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 4
    assert store.db.execute("SELECT COUNT(*) FROM runtime_report_attempts").fetchone()[0] == 2
    assert len(resumed.contexts[-1]["child_reports"][0]["outcome_refs"]) == 15


def test_numerical_yield_with_pending_delivery_is_explicit(tmp_path):
    store, tools = setup(tmp_path)
    provider = ScriptedProvider([commission(delivery_schema(), {"interpretation": "unresolved"}),
        reason(2, {"interpretation": "unresolved"}), tool(report={"interpretation": "supported"})])
    result = run(store, tools, provider, tmp_path / "run", counts=(1, 2))
    assert result["ended_by"] == "yield_stop"
    assert result["completed_actions"] == 1
    assert result["pending_report_deliveries"] == 1
    assert len(provider.contexts) == 3


def test_async_tool_protocol_runs_on_owning_loop_with_sync_fallback_available(tmp_path):
    import asyncio
    store, _ = setup(tmp_path)
    class AsyncTools(FixtureTools):
        async_calls = 0
        def execute(self, *args, **kwargs):
            raise AssertionError("sync protocol must not replace execute_async")
        async def execute_async(self, *args, **kwargs):
            self.async_calls += 1
            await asyncio.sleep(0)
            return FixtureTools.execute(self, *args, **kwargs)
    tools = AsyncTools(store)
    result = run(store, tools, ScriptedProvider([tool(), reason(1)]), tmp_path / "run")
    assert result["completed_actions"] == 2
    assert tools.async_calls == tools.commits == 1


def test_shared_kernel_sync_delivery_repair_preserves_declarative_child_trace():
    from method_loop import (Context, Episode, EpisodeGoal, EpisodeRequest, EpisodeTree,
        Grain, Leaf, ChildEpisodeUnit, ReportDeliveryError, ReportRedelivery)
    from gene_annotation_episode.runtime import TypedReportContract
    factory = lambda path: FixtureController(str(path), 0, 2)
    root_grain = Grain("fixture_root", "Fixture work", "Fixture result", factory)
    child_grain = Grain("fixture_child", "Fixture work", "Fixture result", factory)
    context = Context(tree=EpisodeTree(root_grain, {root_grain: (child_grain,)}), run_id="fixture")
    root_goal = EpisodeGoal.root(objective="Fixture integration", result_contract={"result": "fixture"})
    original = TypedReportContract("Read actual fixture value", obj({"value": {"type": "integer", "maximum": 0}}), None)
    child_goal = EpisodeGoal.child(root_goal, objective="Iteratively improve fixture", result_contract=original.schema)
    child_request = EpisodeRequest(child_goal, Record({}), original)
    class Source:
        def __init__(self, values):
            self.values = iter(values)
        def next(self, view):
            return next(self.values)
    child = Episode(child_grain, "child", Source([
        Leaf(1, lambda value: value, lambda value, result: Record({"credit": result}), label="one"),
        Leaf(2, lambda value: value, lambda value, result: Record({"credit": result}), label="two")]),
        child_request, lambda record: Record({"value": 1}))
    def failed_projection(result, completion, request):
        raise ReportDeliveryError(Record({"kind": "report_delivery_failure", "reason": "maximum"}))
    edge = ChildEpisodeUnit(child, lambda *args: Record({"credit": 2}), failed_projection)
    fixed = TypedReportContract("Read actual fixture value", obj({"value": {"type": "integer"}}), None)
    child_id = Episode.identity(context, child_grain, "child", parent_path=(("fixture_root", "root"),)).episode_id
    message = ReportRedelivery(child_id, report=fixed.admit({"value": 1}, audit_identifiers=()))
    root = Episode(root_grain, "root", Source([edge, message,
        Leaf(3, lambda value: value, lambda value, result: Record({"credit": result}), label="next")]),
        EpisodeRequest(root_goal, Record({})), lambda record: Record({"credit": 3}))
    result = root.run(context)
    assert result.units_consumed == 2
    assert len(result.unit_records[0].child.unit_records) == 2
    assert result.unit_records[0].episode_update.report.as_record() == {"value": 1}
    assert len(result.unit_records[0].episode_update.delivery_failures) == 1
    assert result.controller_state.scores == [2, 1]


def test_selected_record_page_remains_part_of_actual_report_basis(tmp_path):
    store, _ = setup(tmp_path)
    for index in range(40):
        store.add({"id": f"observation_fixture_{index}", "record_type": "observation", "subject_refs": ["subject_A"]})
    target = "observation_fixture_29"
    class PageTools(FixtureTools):
        def execute(self, name, args, scope=None, operation_key=None):
            return {"status": "completed", "record_refs": [target],
                    "result": {"records": [store.get(target)]}}
    tools = PageTools(store)
    schema = obj({"basis": {"type": "array", "items": {"type": "string", "format": "reference"},
                            "x-source": "interpretation_basis_refs"}})
    provider = ScriptedProvider([commission(schema, {}), tool(page=29), reason(0)])
    run(store, tools, provider, tmp_path / "run", counts=(1, 2))
    last_child = provider.contexts[2]
    assert target not in [row["id"] for row in last_child["working_state"]["records"]]
    assert target in last_child["visible_record_refs"]
    delivered = json.loads(store.db.execute("SELECT form FROM runtime_report_attempts").fetchone()[0])
    assert target in delivered["basis"]


def test_form_facts_stream_only_reference_arrays_without_archived_tool_text(tmp_path, monkeypatch):
    """Guard both SQLite-to-Python rows and JSON decoding, not just query text."""
    import gene_annotation_episode.runtime as runtime
    store, tools = setup(tmp_path)
    rows = [("observation_A", "observation"), ("annotation_B", "annotation"),
            ("assessment_A", "assessment"), ("assessment_C", "assessment")]
    extra = [f"observation_extra_{index}" for index in range(14)]
    for ref, kind in rows + [(ref, "observation") for ref in extra]:
        store.add({"id": ref, "record_type": kind, "subject_refs": ["subject_A"]})
    workflow = runtime.Workflow(store, tools, ScriptedProvider([]), tmp_path / "run", "fixture-memory",
        lambda path, initial: FixtureController(str(path), initial, 2), lambda bound_store, scope: 7.5)
    marker = "ARCHIVED_BODY_MUST_NOT_REACH_PYTHON"
    body = marker + ("x" * 1024 * 1024)
    # Deliberately insert out of action order and include overlapping references.
    for index, refs, changed in [
            (20, ["observation_A", "assessment_C"], ["annotation_B", "assessment_C"]),
            (3, ["annotation_B", "observation_A", *extra], ["assessment_A", "annotation_B"]),
            (10, ["assessment_C", "observation_A"], None)]:
        result = {"status": "completed", "record_refs": refs, "result": {"text": body}}
        if changed is not None:
            result["changed_record_refs"] = changed
        workflow.journal.save("runtime_actions", {"episode_id": "fixture-episode", "decision_index": index,
            "action": json.dumps({"kind": "tool", "tool": "source.read"}), "result": json.dumps(result), "credit": 7.5})
    source = SimpleNamespace(episode_id="fixture-episode", scope={"subject_refs": ["subject_A"]},
        last_outcome={"record_refs": ["observation_A"]}, report_basis=["assessment_A"])
    original_db, original_loads = store.db, json.loads
    class GuardCursor:
        def __init__(self, cursor):
            self.cursor = cursor
        @staticmethod
        def check(row):
            if row is not None:
                assert all(not isinstance(value, str) or marker not in value for value in row), \
                    "archived source text crossed the SQLite row boundary"
            return row
        def __iter__(self):
            for row in self.cursor:
                yield self.check(row)
        def fetchone(self):
            return self.check(self.cursor.fetchone())
        def fetchall(self):
            return [self.check(row) for row in self.cursor]
    class GuardConnection:
        def execute(self, query, parameters=()):
            return GuardCursor(original_db.execute(query, parameters))
    def guarded_loads(value, *args, **kwargs):
        assert marker not in value, "archived source text reached the Python JSON decoder"
        return original_loads(value, *args, **kwargs)
    store.db = GuardConnection()
    monkeypatch.setattr(runtime.json, "loads", guarded_loads)
    facts = workflow.facts(source)
    assert facts["committed_record_refs"] == ["annotation_B", "observation_A", *extra, "assessment_C"]
    assert facts["changed_record_refs"] == ["assessment_A", "annotation_B", "assessment_C"]
    assert facts["changed_annotation_refs"] == ["annotation_B"]
    assert facts["changed_assessment_refs"] == ["assessment_A", "assessment_C"]
    assert facts["observations_after_report_basis"] == ["observation_A"]
    assert facts["credit"] == 7.5
    assert not workflow.context.runtime._controllers
    assert original_db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 0


def test_effective_credit_binding_in_context_is_persisted_and_restored(tmp_path):
    import asyncio
    from gene_annotation_episode.credit import AXES, CreditPolicy
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.runtime import _credit_binding_from_settings
    policy = CreditPolicy(epsilon=.37, scale=42,
        axis_weights=tuple((axis, 2. if axis == "comparative" else 1.) for axis in AXES))
    factory = lambda path, baseline: FixtureController(str(path), baseline, 2)
    with Store(tmp_path / "actual") as store:
        problem = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein", role="protein")
        subject = problem["subject_refs"][0]
        tools = ToolRegistry(store)
        provider = ScriptedProvider([{"selection": {"kind": "tool", "tool": "sequence.inspect",
            "arguments": {"subject_ref": subject}}, "report_update": {}}, KeyboardInterrupt()])
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "run",
                controller_factory=factory, credit_policy=policy))
        settings = json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
        binding = provider.contexts[0]["credit_binding"]
        assert binding == _credit_binding_from_settings(settings)
        assert binding['definition']['kind'] == 'received_scientific_finding_progress'
        assert settings['credit_policy'] is None
        annotation_binding = provider.contexts[0]['annotation_score_binding']
        assert annotation_binding['definition']['policy'] == policy.as_record()
        assert settings['binding_definitions']['annotation_score'] == annotation_binding['definition']
        assert binding["versions"] == settings["binding_versions"]["credit"]
        assert binding["scope_source"] == "context.scope"
        assert "source_contributions" not in binding and "history" not in binding
        resumed = ScriptedProvider([{"selection": {"kind": "tool", "tool": "state.query",
            "arguments": {"kind": "observation", "limit": 1}}, "report_update": {}}])
        asyncio.run(run_workflow(store, tools, provider=resumed, resume=True, controller_factory=factory))
        assert resumed.contexts[0]["credit_binding"] == binding
        assert resumed.contexts[0]['annotation_score_binding'] == annotation_binding
        for row in store.db.execute("SELECT request FROM runtime_model_calls"):
            assert json.loads(row[0])["context"]["credit_binding"] == binding
        # A caller-injected score must expose only its declared meaning.
        custom_settings = deepcopy(settings)
        custom_settings["bindings"]["credit"] = "fixtures.custom_score"
        custom_settings["binding_versions"]["credit"] = {"requirement": "same_caller_injected_executable"}
        custom_settings['binding_definitions']['credit'] = {'kind': 'synthetic_custom_score'}
        custom = _credit_binding_from_settings(custom_settings)
        assert custom["kind"] == "custom"
        assert custom["projector"] == "fixtures.custom_score"
        assert not ({"policy", "axes", "denominator"} & custom.keys())


def test_caller_native_resource_changes_preserve_original_history_on_resume(tmp_path):
    store, tools = setup(tmp_path)
    binding = {"cmsearch": {"executable": "/fixture/cmsearch", "cpu": 2,
        "executable_sha256": "fixture-hash", "adapter_version": "fixture-adapter"}}
    tools.resource_binding = lambda: deepcopy(binding)
    provider = ScriptedProvider([tool(), KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, provider, tmp_path / "run")
    settings = json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
    original_binding = deepcopy(binding)
    assert settings["initial_tool_resources"] == original_binding
    manifest = json.loads((tmp_path / "run/run.json").read_text())
    assert manifest["initial_tool_resources"] == original_binding
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 1
    binding["cmsearch"]["cpu"] = 3
    binding["cmsearch"]["executable_sha256"] = "changed-resource-fixture"
    result = run(store, tools, ScriptedProvider([tool(page=1)]), tmp_path / "run", resume=True)
    assert result["completed_actions"] == 2 and tools.executions == 2
    assert store.db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0] == 2
    assert json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])["initial_tool_resources"] == original_binding
    assert [json.loads(row[0])["step"]["delta"] for row in store.db.execute(
        "SELECT observation FROM runtime_observations ORDER BY unit_index")] == [0, 0]


def test_resource_only_run_config_uses_canonical_models_and_resume_keeps_custom_models(tmp_path):
    import tomllib
    from gene_annotation_episode.runtime import _effective_configuration
    from gene_annotation_episode.providers import default_config_path
    defaults = tomllib.loads(default_config_path().read_text())
    local_only = {"local_tools": {"cmsearch_executable": "/fixture/cmsearch", "cmsearch_cpu": 2}}
    models, control = _effective_configuration(local_only)
    assert models == defaults["models"] and control == defaults["controller"]
    models, control = _effective_configuration({**local_only, "controller": {"cost": .002}})
    assert models == defaults["models"] and control["cost"] == .002
    store, tools = setup(tmp_path)
    custom_models = deepcopy(defaults["models"])
    custom_models["REASONING"]["model"] = "explicit-test-fixture-model"
    with pytest.raises(KeyboardInterrupt):
        run(store, tools, ScriptedProvider([tool(), KeyboardInterrupt()]), tmp_path / "run",
            provider_config={"models": custom_models})
    result = run(store, tools, ScriptedProvider([tool(page=1)]), tmp_path / "run", resume=True,
                 provider_config=local_only)
    assert result["completed_actions"] == 2
    settings = json.loads(store.db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
    assert settings["models"] == custom_models


def test_actual_store_tools_and_credit_reasoning_commit_existing_evidence(tmp_path):
    """Actual local adapters/semantic state, with labelled scripted reasoning."""
    import asyncio
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.credit import project_credit
    with Store(tmp_path / "actual") as store:
        problem = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein", role="protein")
        subject = problem["subject_refs"][0]
        tools = ToolRegistry(store)
        first = {"selection": {"kind": "tool", "tool": "sequence.inspect",
                 "arguments": {"subject_ref": subject}}, "report_update": {}}
        def interpretation(context):
            observation = context["working_state"]["observations"][0]["id"]
            payload = {name: [] for name in store.reasoning_schema()["properties"]}
            payload["hypotheses"] = [{"alias": "h", "subject_refs": [subject],
                "predicate": "sequence_integrity", "value": {"type": "enum", "value": "unknown"},
                "context_refs": []}]
            payload["assessments"] = [{"extent_basis": "observed_extent", "alias": "a", "hypothesis_ref": "@h", "observation_ref": observation,
                "relation": "mixed", "applicability": "scope_limited", "condition_refs": [],
                "assumption_refs": [], "expected_revision": 0}]
            payload["annotation_updates"] = [{"alias": "n", "subject_ref": subject,
                "footprint_kind": "localized", "coherent_sets": [{"interpretations": [{
                    "hypothesis_ref": "@h", "disposition": "unresolved", "assessment_refs": ["@a"]}],
                    "context_refs": []}], "alternative_refs": [], "resolution": "unresolved", "expected_revision": 0}]
            return {"selection": {"kind": "reason", "commit": payload}, "report_update": {}}
        def use_returned_progress(context):
            current = project_credit(store)
            assert context['current_credit'] == 0  # No typed finding was committed.
            assert context['annotation_score'] == current.credit > 0
            assert context['annotation_evidence_vector'] == dict(current.axis_components)
            assert context['annotation_evidence_vector']['biological_context'] > 0
            assert context['credit_binding']['definition']['kind'] == 'received_scientific_finding_progress'
            return {"selection": {"kind": "tool", "tool": "state.query",
                "arguments": {"kind": "annotation", "limit": 1}}, "report_update": {}}
        provider = ScriptedProvider([first, interpretation, use_returned_progress])
        result = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "actual-run",
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 3)))
        assert result["completed_actions"] == 3
        assert len(store.current_annotations()) == len(store.current_assessments()) == 1
        assert result['credit'] == 0
        assert project_credit(store).credit == result['annotation_score'] > 0
        rows = store.db.execute("SELECT observation FROM runtime_observations ORDER BY unit_index").fetchall()
        assert json.loads(rows[0][0])["step"]["delta"] == 0
        assert json.loads(rows[1][0])["step"]["delta"] == 0
        assert json.loads(rows[2][0])["step"]["delta"] == 0


def test_missing_inferred_extent_notice_reaches_owner_then_bounded_revision_gains_once(tmp_path):
    """Informational feedback shares the ordinary outcome; it is not a gate."""
    import asyncio
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from gene_annotation_episode.credit import project_credit

    with Store(tmp_path / 'extent-feedback') as store:
        target = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs'][0]
        tools = ToolRegistry(store)
        first = {'selection': {'kind': 'tool', 'tool': 'sequence.inspect',
            'arguments': {'subject_ref': target}}, 'report_update': {}}
        def no_extent(context):
            observation = context['working_state']['observations'][0]['id']
            payload = {name: [] for name in store.reasoning_schema()['required']}
            payload['hypotheses'] = [{'alias': 'h', 'subject_refs': [target],
                'predicate': 'sequence_integrity', 'value': {'type': 'enum', 'value': 'unknown'}, 'context_refs': []}]
            payload['assessments'] = [{'alias': 'a', 'hypothesis_ref': '@h', 'observation_ref': observation,
                'relation': 'mixed', 'applicability': 'scope_limited', 'extent_basis': 'inferred_extent',
                'condition_refs': [], 'assumption_refs': [], 'expected_revision': 0}]
            payload['annotation_updates'] = [{'alias': 'n', 'subject_ref': target,
                'footprint_kind': 'localized', 'coherent_sets': [{'interpretations': [{'hypothesis_ref': '@h',
                    'disposition': 'unresolved', 'assessment_refs': ['@a']}], 'context_refs': []}],
                'alternative_refs': [], 'resolution': 'unresolved', 'expected_revision': 0}]
            return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}
        def bounded(context):
            outcome = context['last_local_outcome']
            assert outcome['status'] == 'completed' and outcome['errors'] == []
            assert context['current_credit'] == 0
            assert outcome['notices'] == [{'section': 'assessments', 'row_index': 0,
                'record_ref': outcome['aliases']['a'], 'field_path': ['target_footprint'],
                'code': 'inferred_extent_requires_target_footprint'}]
            a = store.get(outcome['aliases']['a'])
            n = store.get(outcome['aliases']['n'])
            payload = {name: [] for name in store.reasoning_schema()['required']}
            payload['assessments'] = [{key: value for key, value in a.items()
                if key not in {'id', 'origin', 'record_type', 'revision'}} | {
                    'alias': 'bounded', 'target_footprint': store.coverage(target), 'expected_revision': a['revision']}]
            payload['annotation_updates'] = [{key: value for key, value in n.items()
                if key not in {'id', 'origin', 'record_type', 'revision', 'footprint'}} | {
                    'alias': 'n', 'expected_revision': n['revision'], 'coherent_sets': [{'interpretations': [{
                        'hypothesis_ref': a['hypothesis_ref'], 'disposition': 'unresolved', 'assessment_refs': ['@bounded']}],
                        'context_refs': []}]}]
            return {'selection': {'kind': 'reason', 'commit': payload}, 'report_update': {}}
        def inspect_current(context):
            assert context['last_local_outcome']['notices'] == []
            assert context['current_credit'] == 0  # Extent attribution is not a typed scientific finding.
            assert context['annotation_score'] == project_credit(store).credit > 0
            return {'selection': {'kind': 'tool', 'tool': 'state.query',
                'arguments': {'kind': 'assessment', 'current_only': True}}, 'report_update': {}}
        result = asyncio.run(run_workflow(store, tools,
            provider=ScriptedProvider([first, no_extent, bounded, inspect_current]), run_dir=tmp_path / 'extent-run',
            controller_factory=lambda path, baseline: FixtureController(str(path), baseline, 4)))
        assert result['completed_actions'] == 4
        observations = [json.loads(row[0]) for row in store.db.execute(
            'SELECT observation FROM runtime_observations ORDER BY unit_index')]
        assert len(observations) == 4
        deltas = [row['step']['delta'] for row in observations]
        assert deltas[0] == deltas[1] == deltas[3] == 0
        assert deltas[2] == result['credit'] == 0
        assert result['annotation_score'] > 0
        assert store.count('observation') == 1
