"""Retained/scripted launch data at the actual provider's controlled wire.

No Codex process, network request, service operation or Store reconstruction is
performed. Engineered updates exercise display mechanics, not original work.
"""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.episodic_workflow.root.providers import _SessionConnection, load_config


QUESTION = "For these two supplied feature IDs, how many matching feature records carry each annotation label?"
FEATURE_IDS = ["PATRIC.511145.12.NC_000913.CDS.822959.823720.rev",
    "RefSeq.511145.12.NC_000913.CDS.822959.823720.rev"]
INSTRUCTION_TEXT = "Use one selected operation each turn; preserve the original request and parent constraints.\n" + INSTRUCTIONS
OUTPUT_SCHEMA = {"type": "object", "properties": {"fixture": {"const": True}},
    "required": ["fixture"], "additionalProperties": False}


class LaunchWire(_SessionConnection):
    """Only the existing transport port is simulated; complete remains real."""

    def __init__(self, directory):
        super().__init__(load_config(), directory, directory.parent)
        self.sent = []
        self.turns = 0
        self.reply = {"fixture": True}

    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        if method == "thread/start":
            return {"thread": {"id": "controlled-launch-thread"}, "model": params["model"],
                "reasoningEffort": params["config"]["model_reasoning_effort"]}
        assert method == "turn/start"
        self.turns += 1
        turn = "controlled-launch-turn-" + str(self.turns)
        self.pending.extend([
            {"method": "item/completed", "params": {"threadId": "controlled-launch-thread",
                "item": {"type": "agentMessage", "text": json.dumps(self.reply)}}},
            {"method": "turn/completed", "params": {"threadId": "controlled-launch-thread",
                "turn": {"id": turn, "status": "completed"}}}])
        return {"turn": {"id": turn}}

    def inputs(self):
        return [params for method, params in self.sent if method == "turn/start"]


def snapshot():
    request = {"version": "bvbrc_data_request_v2", "collection": "genome_feature", "mode": "facet",
        "filters": [{"field": "feature_id", "operator": "in", "value": list(FEATURE_IDS)}],
        "facet": {"field": "annotation", "offset": 0, "limit": 2, "min_count": 1,
            "sort": "index", "include_missing": True}}
    return {"goal": {"goal_id": "PRIVATE_GOAL", "parent_goal_id": "PRIVATE_PARENT_GOAL",
            "objective": "Acquire the explicitly assigned BV-BRC native values",
            "task_context": {"root_objective": QUESTION}},
        "scope": {"subject_refs": ["PRIVATE_SUBJECT"], "segments": [
            {"target_ref": "PRIVATE_SUBJECT", "start": 2, "end": 8, "unit": "aa"}]},
        "execution_assignment": {"version": "api_service_assignment_v1", "resource_id": "bvbrc",
            "service": "bvbrc_data", "request": request, "endpoint": "usable_handoff",
            "constraints": {"allowed_resource_ids": ["bvbrc"], "allowed_kinds": ["api"]}},
        "api_service": "bvbrc_data", "api_request": deepcopy(request), "api_received_progress": {},
        "api_execution_completed": False,
        "execution_resource_capabilities": [{"resource_id": "bvbrc", "resource_kind": "api",
            "service": "bvbrc_data", "base_url": "https://www.bv-brc.org/api", "availability": "unknown",
            "inventory_snapshot": {"private": "PRIVATE_INVENTORY"}}],
        "tools": [{"name": "api.bvbrc.data.query", "description": "Execute the one assigned page, count or facet GET.",
            "input_schema": {"type": "object", "properties": {}, "required": [], "additionalProperties": False}}],
        "requested_report_purpose": "Return the requested typed usable original handoff.",
        "requested_form": {"type": "object", "properties": {
            "completed": {"type": "boolean", "x-source": "execution_completed"},
            "references": {"type": "array", "items": {"type": "string", "format": "reference",
                "x-reference-namespace": "execution_handoff"}, "x-source": "execution_handoff_refs"}},
            "required": ["completed", "references"], "additionalProperties": False},
        "available_report_facts": {"execution_completed": {"meaning": "Original usable handoff established."},
            "execution_handoff_refs": {"meaning": "Actual original handoff references."},
            "not_requested": {"meaning": "PRIVATE_UNREQUESTED_SCHEMA"}},
        "controller": {"epoch": "PRIVATE_EPOCH", "scores": [999], "estimate": {"turns": 2,
            "expected_next_gain": {"value": .5, "lower": .1, "upper": .9,
                "status_code": 0, "uncertainty_code": 2, "alpha": .05}},
            "decision": {"continuation_cost": .01, "stop": False}},
        "current_credit": 1,
        "action_yields": {"rows": [{"category": "tool/api.bvbrc.data.query", "completed_actions": 2,
            "total_yield": -.25, "attempted_uncompleted": 1,
            "expected_yield": {"status": "unavailable", "band": None, "unavailable_reason": "parameters_unbound"}}]},
        "last_local_outcome": None, "feedback": None, "pending_work": {"items": []},
        "working_state": {"sources": [{"id": "PRIVATE_SOURCE_INVENTORY"}]},
        "waiting_support": {"own_completed_action_history": ["PRIVATE_RAW_HISTORY"],
            "local_return_history": {"samples": ["PRIVATE_PARENT_HISTORY"]}},
        "restored_episode_history": {"entries": ["PRIVATE_OLD_CONTEXT"]},
        "child_reports": [{"private": "PRIVATE_CHILD_HISTORY"}]}


def complete(wire, context, *, episode="launch", schema=OUTPUT_SCHEMA):
    return wire.complete(episode, "REASONING", INSTRUCTION_TEXT, context, schema)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def assert_task(text):
    assert text.startswith("TASK\n") and text.count("\n\nSTEERING\n") == 1
    task = text.split("\n\nSTEERING\n", 1)[0]
    assert QUESTION in task and "Acquire the explicitly assigned BV-BRC native values" in task
    assert all(identifier in task for identifier in FEATURE_IDS)
    for value in ("genome_feature", "annotation", "include_missing", "min_count", "index",
            "allowed_resource_ids", "usable_handoff", "https://www.bv-brc.org/api",
            "api.bvbrc.data.query", "Requested controlled JSON return", "execution_handoff"):
        assert value in task
    assert "one selected operation each turn" in task
    return task


def assert_private_absent(text):
    assert "PRIVATE_" not in text
    for key in ("base_revision", "removed_fields", "admission_key", "operation_key", "sha256",
            "own_completed_action_history", "local_return_history"):
        assert key not in text


def test_fresh_bootstrap_replaces_task_without_replaying_parent_or_exchange_transcripts(tmp_path):
    first = snapshot(); replacement = deepcopy(first)
    replacement["goal"]["task_context"]["root_objective"] = "A newly supplied scientific question."
    frame = state_frame(replacement)
    frame.update(restored_pending_decision_index=4, restored_public_exchanges=[{
        "response": {"private": "PRIVATE_TRANSCRIPT"},
        "lookup_result": {"status": "completed", "result": {"text": "Already requested manual content.",
            "entry_id": "selected_resource", "section_id": "inputs", "offset": 0, "returned_lines": 1,
            "total_lines": 1, "section_sha256": "PRIVATE_MANUAL_HASH"}}}])
    wire = LaunchWire(tmp_path / "wire")
    async def exercise():
        await complete(wire, state_frame(first)); await complete(wire, frame)
    asyncio.run(exercise())
    text = wire.inputs()[1]["input"][0]["text"]
    assert "A newly supplied scientific question." in text and QUESTION not in text
    assert "Already requested manual content." in text
    assert_private_absent(text)


def test_bad_delta_and_foreign_episode_state_fail_before_turn_dispatch(tmp_path):
    first = snapshot(); second = deepcopy(first); second["current_credit"] = 4
    broken = state_frame(second, first); broken["fields"]["current_credit"] = 99
    wire = LaunchWire(tmp_path / "wire")
    async def exercise():
        await complete(wire, state_frame(first))
        with pytest.raises(ValueError, match="revision_conflict"):
            await complete(wire, broken)
        with pytest.raises(TypeError, match="previous_model_state_requires_object"):
            await complete(wire, state_frame(second, {}), episode="other-episode")
    asyncio.run(exercise())
    assert len(wire.inputs()) == 1
    assert wire.scientific_prompt_states[("launch", "REASONING")]["current_credit"] == 1


def test_task_uses_only_bound_callables_selected_manuals_and_exact_native_operands(tmp_path):
    context = snapshot()
    context["tools"][0]["instructions"] = "Retain the original input; use only the selected service."
    context["tools"][0]["description"] = "Literal operation | description.\nPreserve both lines."
    # An engineered operand tests literal presentation, not BV request admission.
    context["execution_assignment"]["request"]["native_operand"] = "source_actual_selected_operand"
    context["selected_launch_instructions"] = {"selection": {"library_id": "PRIVATE_LIBRARY"},
        "sections": [{"entry_id": "selected_api", "section_id": "inputs",
            "text": "Use the original assigned public feature identifiers.", "section_sha256": "PRIVATE_PIN"}]}
    wire = LaunchWire(tmp_path / "wire"); before = deepcopy(context)
    asyncio.run(complete(wire, context))
    text = wire.inputs()[0]["input"][0]["text"]
    assert_task(text); assert_private_absent(text)
    assert "Retain the original input; use only the selected service." in text
    assert "Use the original assigned public feature identifiers." in text
    assert "Literal operation | description.\nPreserve both lines." in text
    assert "source_actual_selected_operand" in text
    assert "| Region 1 start | 2 |" in text and "| Region 1 end | 8 |" in text and "| Region 1 unit | aa |" in text
    assert encoded(context) == encoded(before)


@pytest.mark.parametrize("band,expected,limitation", [
    ({"value": 0, "lower": 0, "upper": 0, "status_code": 0, "uncertainty_code": 0, "alpha": 0}, "0", "exact; lower=0; upper=0"),
    ({"value": -.5, "lower": -.7, "upper": -.2, "status_code": 0, "uncertainty_code": 2, "alpha": .05}, "-0.5", "approximate Laplace model band"),
    ({"value": -1, "lower": -1, "upper": -1, "status_code": -1, "uncertainty_code": -1, "alpha": -1}, "unavailable", "insufficient completed actions"),
    ({"value": -2, "lower": -2, "upper": -2, "status_code": -2, "uncertainty_code": -1, "alpha": -1}, "unavailable", "unidentifiable"),
    ({"value": 0, "lower": -1, "upper": -1, "status_code": 0, "uncertainty_code": -1, "alpha": -1}, "0", "unavailable"),
], ids=["zero", "negative", "insufficient", "unidentifiable", "unknown_uncertainty"])
def test_steering_preserves_recorded_signed_zero_and_unavailable_band_meanings(tmp_path, band, expected, limitation):
    context = snapshot(); context["controller"]["estimate"]["expected_next_gain"] = band
    context["action_yields"]["rows"][0]["expected_yield"] = {"status": "available", "band": band}
    wire = LaunchWire(tmp_path / "wire")
    asyncio.run(complete(wire, state_frame(context)))
    text = wire.inputs()[0]["input"][0]["text"].split("\n\nSTEERING\n", 1)[1]
    assert "| tool/api.bvbrc.data.query | 2 | -0.25 | " + expected + " | " + limitation in text
    if band["status_code"] != 0 or band["uncertainty_code"] == -1:
        assert "lower=-1" not in text and "lower=-2" not in text and "alpha=-1" not in text
    assert_private_absent(text)
