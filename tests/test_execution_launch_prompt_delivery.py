"""Retained/scripted launch data at the actual provider's controlled wire.

No Codex process, network request, service operation or Store reconstruction is
performed. Engineered updates exercise display mechanics, not original work.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.execution_prompt import is_api_launch_context
from gene_annotation_episode.providers import _SessionConnection, load_config


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


def retained_launch():
    selected = os.environ.get("HMMER_NATIVE_ORACLE_EXECUTION_LAUNCH_SQLITE")
    if selected is None:
        pytest.skip("the original276 retained launch SQLite was not selected")
    path = Path(selected)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "d943fda9203fa869524f4714227a7455abe91cc1004b94c7c85cad3610f99fd1"
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    try:
        row = connection.execute("SELECT request,response FROM runtime_model_calls WHERE run_id=? AND episode_id=? "
            "AND call_index=? AND purpose=?", ("bvbrc-selected-process-fixture",
                "episode_7ad49f8fc11f280fe03f0dfe1d5ef95985cafb35046adbf0c619da6847cfddb7", 0, "decision")).fetchone()
    finally:
        connection.close()
    assert hashlib.sha256(row[0].encode()).hexdigest() == "be02b5dae87a57b7bbcaeea0c0e0c79622bd6b0675e65c32c85023502b709ee3"
    assert hashlib.sha256(row[1].encode()).hexdigest() == "6ba56912ace718480a1de6298538c86f753722d3473307f36a0b94629089b058"
    request = json.loads(row[0])
    return request["context"], request["schema"], json.loads(row[1])


def test_retained_api_launch_reaches_actual_turn_start_with_original_response_contract(tmp_path):
    context, schema, response = retained_launch()
    original = deepcopy((context, schema, response))
    wire = LaunchWire(tmp_path / "wire"); wire.reply = response
    assert asyncio.run(complete(wire, context, schema=schema)) == response
    turn, = wire.inputs(); text = turn["input"][0]["text"]
    assert_task(text)
    assert "input_d14dec7a2167972e3147cee9" not in text
    assert "goal_23131464985693a64ea6e2bf" not in text
    cost = context["controller"]["decision"]["continuation_cost"]
    assert "| 0 | 0 | unavailable | insufficient completed actions | " + str(cost) + " | continue |" in text
    assert "-1.0" not in text.split("\n\nSTEERING\n", 1)[1]
    assert encoded(turn["outputSchema"]) == encoded(schema)
    saved = json.loads((tmp_path / "wire/call-00001/request.json").read_text())
    assert encoded(saved["context"]) == encoded(context) and encoded(saved["output_schema"]) == encoded(schema)
    assert encoded(saved["input"]) == encoded(turn["input"]) and saved["instructions"] == INSTRUCTION_TEXT
    assert encoded((context, schema, response)) == encoded(original)
    assert hashlib.sha256(Path(os.environ["HMMER_NATIVE_ORACLE_EXECUTION_LAUNCH_SQLITE"]).read_bytes()).hexdigest() == "d943fda9203fa869524f4714227a7455abe91cc1004b94c7c85cad3610f99fd1"
    assert wire.process is None and len([method for method, _ in wire.sent if method == "thread/start"]) == 1


def test_task_repeats_across_bootstrap_delta_and_same_decision_lookup_without_state_changes(tmp_path):
    first = snapshot(); second = deepcopy(first)
    second["current_credit"] = 0
    second["controller"]["estimate"]["expected_next_gain"]["value"] = .25
    second["last_local_outcome"] = {"status": "partial", "operation_ref": "PRIVATE_OPERATION",
        "record_refs": ["PRIVATE_SOURCE"], "result": {"response_complete": False, "reported_total": None,
            "native_job_id": "PRIVATE_NATIVE_JOB", "handoff_ref": "PRIVATE_HANDOFF"},
        "feedback": {"code": "reply_incomplete"}}
    update = state_frame(second, first)
    assert "goal" not in update["fields"] and "execution_assignment" not in update["fields"]
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result", "result": {
        "view": "own_attempts", "run_id": "PRIVATE_RUN", "episode_id": "PRIVATE_EPISODE",
        "records": [{"decision_index": 1, "category": "tool/api.bvbrc.data.query", "status": "partial",
            "completed_gain": 0, "inputs": {"request": {"native_id": "selected-native-id"}}}],
        "next_query": None, "unavailable_reasons": []}}
    detail = {"version": "decision_context_v1", "kind": "decision_lookup_result", "result": {
        "view": "own_attempt_detail", "decision_index": 1, "pointer": "/arguments/source_ref",
        "slice_unit": "scalar_values", "offset": 0, "total": 1, "included": 1,
        "values": "source_explicitly_selected_operand", "has_more": False, "next_query": None,
        "value_sha256": "PRIVATE_DETAIL_HASH", "value_bytes": 34}}
    before = deepcopy((first, second, update, lookup, detail))
    wire = LaunchWire(tmp_path / "wire")
    async def exercise():
        await complete(wire, state_frame(first)); await complete(wire, update)
        await complete(wire, lookup); await complete(wire, detail)
    asyncio.run(exercise())
    tasks = []
    for turn in wire.inputs():
        text = turn["input"][0]["text"]; tasks.append(assert_task(text)); assert_private_absent(text)
        assert "| tool/api.bvbrc.data.query | 2 | -0.25 | unavailable | parameters_unbound | 1 |" in text
        assert encoded(turn["outputSchema"]) == encoded(OUTPUT_SCHEMA)
    assert tasks[0] == tasks[1] == tasks[2] == tasks[3]
    for turn in wire.inputs()[1:]:
        text = turn["input"][0]["text"]
        assert "reported_total | null" in text and "response_complete | false" in text
        assert "native_job_id" not in text and "reply_incomplete" in text
        assert "| 2 | 0 | 0.25 |" in text
    assert "selected-native-id" in wire.inputs()[2]["input"][0]["text"]
    assert "source_explicitly_selected_operand" in wire.inputs()[3]["input"][0]["text"]
    assert encoded((first, second, update, lookup, detail)) == encoded(before)
    saved = json.loads((tmp_path / "wire/call-00002/request.json").read_text())
    assert encoded(saved["context"]) == encoded(update) and encoded(saved["input"]) == encoded(wire.inputs()[1]["input"])
    developer = next(params["developerInstructions"] for method, params in wire.sent if method == "thread/start")
    assert "decision_bootstrap supplies" not in developer and "request_context" in developer


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


@pytest.mark.parametrize("kind", ["results", "local", "hpc", "legacy_hmmer", "scientific", "wrong_service", "plain"])
def test_unapproved_roles_and_legacy_assignments_preserve_existing_json_presentation(tmp_path, kind):
    context = snapshot()
    if kind == "results": context["execution_assignment"] = {"version": "execution_results_assignment_v1", "selector": {}}
    elif kind in {"local", "hpc"}: context["execution_assignment"] = {"version": "practical_assignment_v1", "resource_kind": kind}
    elif kind == "legacy_hmmer": context["execution_assignment"]["version"] = "api_execution_assignment_v1"
    elif kind == "scientific":
        context.pop("execution_assignment"); context["scientific_process"] = {"evidence_axis": {
            "instruction_status": "limited_existing_measurement_guidance"}}
    elif kind == "wrong_service": context["api_service"] = "unselected_service"
    else: context = {"goal": {"objective": "plain input"}}
    assert not is_api_launch_context(context)
    frame = state_frame(context); original = deepcopy(frame)
    wire = LaunchWire(tmp_path / "wire")
    asyncio.run(complete(wire, frame))
    assert json.loads(wire.inputs()[0]["input"][0]["text"]) == frame == original
    assert not wire.scientific_prompt_states


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


def test_steering_preserves_attributable_own_failure_and_submission_uncertainty_without_controls(tmp_path):
    context = snapshot()
    context["api_received_progress"] = {"api.example.submit": {"state": "failed", "kind": "service_error",
        "facts": {"submission_outcome": "unknown", "http_status": None, "native_job_id": "retained-native-id",
            "source_ref": "PRIVATE_SOURCE", "request_ref": "PRIVATE_REQUEST", "sha256": "PRIVATE_HASH"}}}
    context["last_local_outcome"] = {"status": "failed", "result": {"returned_count": 0, "reported_total": None,
        "request_ref": "PRIVATE_CONTROL"}, "feedback": {"code": "transport_failed", "retry_selected": False,
            "diagnostic_ref": "PRIVATE_DIAGNOSTIC"}}
    context["feedback"] = deepcopy(context["last_local_outcome"]["feedback"])
    wire = LaunchWire(tmp_path / "wire"); before = deepcopy(context)
    asyncio.run(complete(wire, state_frame(context)))
    text = wire.inputs()[0]["input"][0]["text"]
    assert "submission_outcome | unknown" in text and "http_status | null" in text
    assert "retained-native-id" not in text and "returned_count | 0" in text and "reported_total | null" in text
    assert "transport_failed" in text and "retry_selected | false" in text
    assert_private_absent(text); assert encoded(context) == encoded(before)


@pytest.mark.parametrize("kind", ["native_tracking", "diagnostics", "large_controls"])
def test_operational_steering_excludes_handles_and_arbitrary_control_subtrees(tmp_path, kind):
    context = snapshot()
    context["api_received_progress"] = {"api.example.submit": {"state": "failed", "kind": "service_error",
        "facts": {"submission_outcome": "unknown", "http_status": None, "response_complete": False,
            "page": {"returned_count": 0, "reported_total": None, "count_exactness": "unknown"},
            "progress": {"completed_rows": 2},
            "measurements": [{"name": "captured_bytes", "value": 0, "unit": "bytes"}],
            "qualification": {"population_coverage": "unknown"},
            "failure": {"code": "provider_request_timeout"}}}}
    context["last_local_outcome"] = {"status": "failed", "result": {"returned_count": 0},
        "feedback": {"code": "transport_failed", "category": "communication"}}
    changed = deepcopy(context)
    facts = changed["api_received_progress"]["api.example.submit"]["facts"]
    feedback = changed["last_local_outcome"]["feedback"]
    if kind == "native_tracking":
        facts.update(native_job_id="PRIVATE_NATIVE_JOB", native_handle={"handle": "PRIVATE_NATIVE_HANDLE", "pid": 42},
            execution_id="PRIVATE_EXECUTION_ID", task_id="PRIVATE_TASK_ID")
        feedback["original_job_ref"] = "PRIVATE_ORIGINAL_JOB"
    elif kind == "diagnostics":
        feedback["diagnostic_ref"] = "PRIVATE_DIAGNOSTIC"
        feedback["details"] = {"traceback": "PRIVATE_TRACEBACK", "status": "PRIVATE_NESTED_STATUS"}
        facts["failure"]["diagnostic_ref"] = "PRIVATE_FAILURE_DIAGNOSTIC"
        facts["qualification"]["evidence_ref"] = "PRIVATE_QUALIFICATION_CONTROL"
    else:
        payload = "PRIVATE_IRRELEVANT_CONTROL" * 50000
        facts["unrelated_control_payload"] = {"result": {"http_status": 200, "payload": payload}}
        changed["last_local_outcome"]["result"]["rows"] = [{"body": payload}]
        facts["page"]["control"] = {"completed_rows": 99999, "payload": payload}
        assert len(encoded(changed)) > 1000000
    wire = LaunchWire(tmp_path / "wire"); before = deepcopy(changed)
    async def exercise():
        await complete(wire, state_frame(context)); await complete(wire, state_frame(changed, context))
    asyncio.run(exercise())
    first, second = [turn["input"][0]["text"] for turn in wire.inputs()]
    assert first == second
    assert_task(second); assert_private_absent(second)
    for value in ("submission_outcome | unknown", "returned_count | 0", "reported_total | null",
            "completed_rows | 2", "population_coverage | unknown", "provider_request_timeout",
            "captured_bytes", "unit | bytes", "value | 0"):
        assert value in second
    assert encoded(changed) == encoded(before)
