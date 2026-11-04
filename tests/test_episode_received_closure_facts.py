"""Finite closure plumbing with engineering bindings and a synthetic Workflow.

The callbacks retain no scientific provenance. The actual Workflow cases use
one synthetic reasoning action, with no scientific/API/native work.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from tests.test_runtime import (FixtureController, ScriptedProvider, fixture_credit,
    obj, reason, setup)


PUBLIC = {"execution_completed": False, "literal_public": {"values": [0, None]}}
PRIVATE = {"_closure_probe": {"version": "engineering_closure_v1", "literal": 0}}
COMPLETION = {"ended_by": "controller", "end_reason": "fixture_stop", "units_consumed": 1}


class _LegacyBinding:
    """Complete engineering binding whose received callback takes ONE argument."""
    entry_roles = ()

    def __init__(self, role="probe", *, public=None):
        self.roles = (role,)
        self.public = deepcopy(PUBLIC if public is None else public)
        self.public_calls = []

    def child_roles(self, role):
        return ()

    def as_record(self):
        return {"kind": "engineering_received_closure_probe_v1", "roles": list(self.roles)}

    def credit_kind(self, role):
        return "scientific"

    def assignment_schema(self, role):
        return obj({})

    def permitted_common_actions(self, context):
        return ()

    def allowed_children(self, parent, caller_capabilities):
        return ()

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        raise AssertionError("the closure fixture commissions no child")

    def instructions(self, context):
        return "Engineering closure fixture."

    def decision_context(self, context, current_view):
        return {}

    def catalog(self, context):
        return []

    def execute(self, context, tool_name, arguments, operation_key):
        raise AssertionError("the closure fixture executes no specialist tool")

    def fact_sources(self, role):
        return {}

    def facts(self, context, completion_snapshot):
        return {}

    def resolve(self, context, reference, namespace):
        return False

    def validate_report(self, context, form, original_schema):
        return None

    def credit_view(self, context, receiver_selection):
        return {"credit": 0}

    def received_report_facts(self, context):
        self.public_calls.append(context)
        return self.public


class _ClosureBinding(_LegacyBinding):
    def __init__(self, role="probe", *, public=None, private=None):
        super().__init__(role, public=public)
        self.private = deepcopy(PRIVATE if private is None else private)
        self.closure_calls = []

    def received_report_closure_facts(self, context):
        self.closure_calls.append(context)
        return self.private


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def test_legacy_received_callback_keeps_one_argument_and_exact_public_facts():
    context, binding = object(), _LegacyBinding()
    registry = EpisodeBindingRegistry([binding])
    result = registry.received_report_facts(context)
    assert _canonical(result) == _canonical(PUBLIC)
    assert binding.public_calls == [context]
    result["literal_public"]["values"].append(1)
    assert _canonical(binding.public) == _canonical(PUBLIC)
    assert registry.received_report_facts(context,
        completion_snapshot={"completion": deepcopy(COMPLETION)}) == PUBLIC
    assert binding.public_calls == [context, context]


@pytest.mark.parametrize("snapshot", [None, {}, {"completion": None, "execution_completed": True}])
def test_nonclosing_snapshot_exposes_only_unchanged_public_facts(snapshot):
    context, binding = object(), _ClosureBinding()
    result = EpisodeBindingRegistry([binding]).received_report_facts(context,
        completion_snapshot=snapshot)
    assert _canonical(result) == _canonical(PUBLIC)
    assert binding.public_calls == [context]
    assert binding.closure_calls == []


def test_actual_completion_adds_private_facts_despite_execution_completed_false():
    context, binding = object(), _ClosureBinding()
    snapshot = {"completion": deepcopy(COMPLETION), "execution_completed": False}
    result = EpisodeBindingRegistry([binding]).received_report_facts(context,
        completion_snapshot=snapshot)
    assert _canonical(result) == _canonical({**PUBLIC, **PRIVATE})
    assert result["execution_completed"] is False
    assert binding.public_calls == binding.closure_calls == [context]
    result["_closure_probe"]["literal"] = 7
    assert _canonical(binding.private) == _canonical(PRIVATE)
    assert snapshot == {"completion": COMPLETION, "execution_completed": False}


@pytest.mark.parametrize("collision", ["public", "closure", "public_closure"])
def test_duplicate_fields_retain_existing_mapping_rejection(collision):
    if collision == "public":
        bindings = [_LegacyBinding("one", public={"same": 0}),
            _LegacyBinding("two", public={"same": 0})]
        suffix = "received_report_facts"
    elif collision == "closure":
        bindings = [_ClosureBinding("one", public={}, private={"same": 0}),
            _ClosureBinding("two", public={}, private={"same": 0})]
        suffix = "received_report_closure_facts"
    else:
        bindings = [_ClosureBinding(public={"same": 0}, private={"same": 0})]
        suffix = "received_report_closure_facts"
    with pytest.raises(ValueError, match="^received_report_field_conflict:" + suffix + "$"):
        EpisodeBindingRegistry(bindings).received_report_facts(object(),
            completion_snapshot={"completion": deepcopy(COMPLETION)})


@pytest.mark.parametrize("invalid_callback", ["public", "closure"])
def test_nonmapping_callbacks_retain_existing_mapping_rejection(invalid_callback):
    binding = (_ClosureBinding(public=[]) if invalid_callback == "public" else
        _ClosureBinding(private=[]))
    suffix = "received_report_facts" if invalid_callback == "public" else "received_report_closure_facts"
    with pytest.raises(ValueError, match="^received_report_field_conflict:" + suffix + "$"):
        EpisodeBindingRegistry([binding]).received_report_facts(object(),
            completion_snapshot={"completion": deepcopy(COMPLETION)})


@pytest.mark.parametrize("typed", [False, True])
def test_actual_annotation_closure_passes_snapshot_and_keeps_uncontracted_root_formless(
        tmp_path, monkeypatch, typed):
    """Actual shared loop, synthetic action/controller; no provider acquisition."""
    store, tools = setup(tmp_path)
    provider, binding = ScriptedProvider([reason(3)]), _ClosureBinding("improvement")
    workflow = Workflow(store, tools, provider, tmp_path / "run", "received-closure-fixture",
        lambda path, initial: FixtureController(str(path), initial, 1), fixture_credit,
        episode_binding_factories=(lambda services: binding,))
    snapshots, received = [], workflow.episode_bindings.received_report_facts

    def capture(context, *, completion_snapshot=None):
        snapshots.append(deepcopy(completion_snapshot))
        return received(context, completion_snapshot=completion_snapshot)

    monkeypatch.setattr(workflow.episode_bindings, "received_report_facts", capture)
    scope = {"subject_refs": ["subject_A"]}
    contract = (TypedReportContract("Read the literal synthetic fixture credit",
        obj({"credit": {"type": "number", "x-source": "credit"}}),
        workflow.resolver(scope)) if typed else None)
    root = workflow.build("annotation", "root", "Close the synthetic fixture", scope,
        contract=contract)
    assert workflow.specialist(root.source) is None
    normal = workflow.facts(root.source)
    assert normal["execution_completed"] is False
    assert _canonical(normal["literal_public"]) == _canonical(PUBLIC["literal_public"])
    assert "_closure_probe" not in normal and binding.closure_calls == []

    async def close():
        record = await root.run_async(workflow.context)
        result = await root.build_result(record)
        return record, result

    record, result = asyncio.run(close())
    assert record.units_consumed == 1
    assert len(provider.contexts) == len(provider.released) == 1
    assert tools.executions == 0
    for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
        assert store.db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 1
    episode = workflow.journal.row("runtime_episodes", root.source.episode_id)
    assert episode["state"] == "yielded" and episode["archive"] is not None
    saved = workflow.journal.row("runtime_forms", root.source.episode_id)
    closing = [item for item in snapshots if item["completion"] is not None]
    if typed:
        assert len(closing) == len(binding.closure_calls) == 1
        assert closing[0] == {"completion": {"ended_by": record.ended_by,
            "end_reason": record.end_reason, "units_consumed": 1}, "own_action_count": 1,
            "last_outcome_refs": root.source.last_outcome["record_refs"],
            "committed_record_refs": root.source.last_outcome["record_refs"],
            "changed_record_refs": root.source.last_outcome["changed_record_refs"],
            "report_basis_refs": root.source.report_basis}
        facts = json.loads(saved["facts"])
        assert facts["execution_completed"] is False
        assert _canonical({key: facts[key] for key in PUBLIC}) == _canonical(PUBLIC)
        assert facts["_closure_probe"] == PRIVATE["_closure_probe"]
        assert json.loads(saved["form"]) == result.as_record()["form"] == {"credit": 3}
    else:
        assert saved is None and closing == [] and binding.closure_calls == []
        assert result.as_record() == {"credit": 3, "pending_handles": []}
