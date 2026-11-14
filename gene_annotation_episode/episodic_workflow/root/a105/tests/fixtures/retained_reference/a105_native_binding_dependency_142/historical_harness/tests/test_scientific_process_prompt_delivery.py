"""Actual native turn inputs with a controlled wire; no model/network work."""
import asyncio
from copy import deepcopy
import json

import pytest

from gene_annotation_episode.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.providers import _SessionConnection, load_config


class ScientificWire(_SessionConnection):
    def __init__(self, directory, *, image_resolver=None):
        super().__init__(load_config(), directory, directory.parent, image_resolver=image_resolver)
        self.sent = []
        self.turns = 0

    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        if method == "thread/start":
            return {"thread": {"id": "controlled-thread"}, "model": params["model"],
                "reasoningEffort": "medium"}
        assert method == "turn/start"
        self.turns += 1
        turn = "controlled-turn-" + str(self.turns)
        self.pending.extend([
            {"method": "item/completed", "params": {"threadId": "controlled-thread",
                "item": {"type": "agentMessage", "text": '{"fixture":true}'}}},
            {"method": "turn/completed", "params": {"threadId": "controlled-thread",
                "turn": {"id": turn, "status": "completed"}}}])
        return {"turn": {"id": turn}}

    def turns_sent(self):
        return [params for method, params in self.sent if method == "turn/start"]


def snapshot():
    """Synthetic projection with the same field shapes as DecisionSource.next."""
    reference = {"version": "scientific_process_option_ref_v1", "library_id": "a" * 64,
        "slot": "evidence_axis", "option_id": "A105", "entry_sha256": "b" * 64}
    selection = {"version": "scientific_process_selection_v3", "evidence_axis": reference,
        "thought_pattern": {**reference, "slot": "thought_pattern", "option_id": "P01"},
        "child_tool_info": [{"name": "source.read", "resources": "local"}]}
    return {
        "goal": {"goal_id": "private-goal", "parent_goal_id": "private-parent-goal",
            "objective": "Determine what the supplied unnamed protein does.",
            "task_context": {"assignment": "Use only the selected supplied region."}},
        "scope": {"subject_refs": ["input_target"], "segments": [{"subject_ref": "input_target",
            "start": 2, "end": 5}]},
        "working_state": {"problem_ref": "private-problem", "subjects": [{"id": "input_target",
            "molecule": "protein", "length": 5, "unit": "aa", "sequence_ref": "artifact_target",
            "source_ref": "source_supplied", "name": "private label only", "record_type": "input"}],
            "materials": [{"id": "material_target", "name": "selected.faa", "use": "target",
                "source_ref": "source_supplied", "record_type": "material"}],
            "sources": [{"id": "source_unrequested", "uri": "UNREQUESTED_SOURCE_INVENTORY"}],
            "observations": [{"id": "observation_received", "value": 7, "unit": "nmol/min",
                "qualification": "Measured on a reference protein, not this target."},
                {"id": "observation_unrequested", "value": "UNREQUESTED_OBSERVATION"}],
            "annotations": [], "interpretation_accounts": []},
        "scientific_process": {"selection": selection, "initial_selection_sha256": "PRIVATE_PIN",
            "evidence_axis": {"id": "A105", "name": "Experimental results",
                "instruction_status": "published_investigation_instructions",
                "investigation_instructions": "Read the supplied sequence or selected file contents.\n"
                    "Separate the measured activity, assayed subject, conditions and controls.\n"
                    "Candidate functions may emerge from these findings."},
            "thought_pattern": {"id": "P01", "name": "Compare informative alternatives",
                "description": "Choose a comparison that distinguishes the functional explanations.",
                "use_when": "The reference is informative but the function remains uncertain.",
                "live_alternatives": ["Shared activity", "Different recognition"],
                "decision_guidance": ["Inspect the measured comparison before transferring function."],
                "outcome_contingencies": [{"if_observed": "Different specificity",
                    "then_consider": "Retain only the supported relationship."}],
                "boundary": "A tool score is not the transfer conclusion."},
            "child_tool_info": [{"name": "source.read", "description": "Read the selected source window.",
                "resources": "local", "instructions": "Use source_ref with exact offset and limit.\n"
                    "Retain source coordinates and report partial windows."}],
            "assignment": {"selection": selection, "evidence_refs": [],
                "constraints": {"target_only": True}, "context": {"snippet": "MKWAA", "complete": False}},
            "permitted_children": ["scientific_process", "literature"]},
        "tools": [{"name": "source.read", "description": "Read an exact source byte window.",
            "input_schema": {"type": "object", "properties": {"source_ref": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0}, "limit": {"type": "integer", "minimum": 1}},
                "required": ["source_ref", "offset", "limit"], "additionalProperties": False}}],
        "requested_report_purpose": "Return supported interpretations and their retained qualifications.",
        "requested_form": {"type": "object", "properties": {
            "conclusion": {"type": "string", "enum": ["unresolved", "qualified"],
                "description": "Whether the evidence supports a qualified functional interpretation."},
            "sources": {"type": "array", "items": {"type": "string", "format": "reference"},
                "x-source": "changed_record_refs"}}, "required": ["conclusion", "sources"],
            "additionalProperties": False},
        "available_report_facts": {"changed_record_refs": {"meaning": "Actual records changed by own completed work."},
            "unrequested_fact": {"meaning": "UNREQUESTED_FACT_DEFINITION"}},
        "current_report_update": {"conclusion": "unresolved"}, "current_report_basis_refs": [],
        "last_local_outcome": None, "feedback": None,
        "current_credit": 4, "annotation_score": 2,
        "controller": {"scores": [999], "epoch": "PRIVATE_EPOCH", "estimate": {"turns": 2,
            "expected_next_gain": {"value": .5, "lower": -.1, "upper": .9,
                "status_code": 0, "uncertainty_code": 2, "alpha": .05},
            "diagnostics": {"private_fit": "PRIVATE_FIT"}}, "decision": {"continuation_cost": .001}},
        "action_yields": {"version": "own_decision_yield_table_v1", "before": 5,
            "rows": [{"category": "tool/source.read", "completed_actions": 2, "total_yield": -.25,
                "attempted_uncompleted": 1, "expected_yield": {"status": "unavailable",
                    "unavailable_reason": "parameters_unbound", "band": None}}]},
        "waiting_support": {"own_completed_action_history": ["PRIVATE_HISTORY"],
            "local_return_history": {"samples": ["PRIVATE_CHILD_HISTORY"]}},
        "restored_episode_history": {"entries": ["PRIVATE_RESTORE_HISTORY"]},
        "child_reports": [], "pending_work": {"items": []},
    }


INSTRUCTION_TEXT = "Investigate the parent's supplied target iteratively; use the actual scoped evidence.\n" + INSTRUCTIONS
OUTPUT_SCHEMA = {"type": "object", "properties": {"fixture": {"const": True}},
    "required": ["fixture"], "additionalProperties": False}


def complete(wire, context, *, episode="episode", instructions=INSTRUCTION_TEXT):
    return wire.complete(episode, "REASONING", instructions, context, OUTPUT_SCHEMA)


def assert_task(text):
    assert text.startswith("TASK\n\n")
    assert text.count("\n\nSTEERING\n") == 1
    for content in ("Determine what the supplied unnamed protein does.", "MKWAA", "target_only",
            "Separate the measured activity, assayed subject, conditions and controls.",
            "Candidate functions may emerge", "Shared activity", "Different recognition",
            "Different specificity", "Retain only the supported relationship.",
            "Retain source coordinates and report partial windows.",
            "Return supported interpretations and their retained qualifications.",
            "Whether the evidence supports a qualified functional interpretation.",
            "Actual records changed by own completed work.", "source_supplied", "selected.faa"):
        assert content in text


def assert_no_bookkeeping(text):
    for value in ("private-goal", "private-parent-goal", "private-problem", "PRIVATE_PIN", "PRIVATE_EPOCH",
            "PRIVATE_FIT", "PRIVATE_HISTORY", "PRIVATE_CHILD_HISTORY", "PRIVATE_RESTORE_HISTORY",
            "UNREQUESTED_SOURCE_INVENTORY", "UNREQUESTED_OBSERVATION", "UNREQUESTED_FACT_DEFINITION",
            "base_revision", "removed_fields", "decision_bootstrap supplies", "restored_pending_decision_index"):
        assert value not in text


def test_actual_turns_repeat_task_across_update_and_same_decision_lookup(tmp_path):
    wire = ScientificWire(tmp_path / "wire")
    first = snapshot()
    second = deepcopy(first)
    second["last_local_outcome"] = {"status": "partial", "operation_ref": "PRIVATE_OPERATION",
        "record_refs": ["observation_received"], "changed_record_refs": ["observation_received"],
        "result": {"count": 1, "qualification": "Below the measured detection limit."},
        "feedback": {"code": "one_source_unavailable"}}
    second["controller"]["estimate"]["expected_next_gain"]["value"] = .25
    second.pop("annotation_score")
    update = state_frame(second, first)
    assert "scientific_process" not in update["fields"]
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result",
        "decision_index": 8, "exchange_index": 2, "result": {"status": "completed", "text": "Selected child role details."}}
    original = deepcopy((first, second, update, lookup))

    async def exercise():
        assert await complete(wire, state_frame(first)) == {"fixture": True}
        await complete(wire, update)
        await complete(wire, lookup)
    asyncio.run(exercise())
    turns = wire.turns_sent()
    assert len(turns) == 3
    for turn in turns:
        text = turn["input"][0]["text"]
        assert_task(text)
        assert_no_bookkeeping(text)
        assert turn["outputSchema"] == OUTPUT_SCHEMA
        assert "| tool/source.read | 2 | -0.25 | unavailable | parameters_unbound | 1 |" in text
        assert "request_context" in text and "select_action" in text
    assert "observation_received" not in turns[0]["input"][0]["text"]
    for turn in turns[1:]:
        text = turn["input"][0]["text"]
        assert "Below the measured detection limit." in text
        assert "Measured on a reference protein, not this target." in text
        assert "one_source_unavailable" in text
        assert "PRIVATE_OPERATION" not in text
        assert "| 2 | 0.25 |" in text
        assert "| annotation_score |" not in text
    assert "Selected child role details." in turns[2]["input"][0]["text"]
    assert (first, second, update, lookup) == original
    developer = next(params["developerInstructions"] for method, params in wire.sent if method == "thread/start")
    assert "decision_bootstrap supplies" not in developer
    assert "request_context" in developer and "select_action" in developer
    saved = json.loads((tmp_path / "wire/call-00002/request.json").read_text())
    assert saved["context"] == update
    assert saved["instructions"] == INSTRUCTION_TEXT
    assert saved["model_instructions"] == developer
    assert saved["input"] == turns[1]["input"]


def test_reconstruction_restores_answered_lookup_values_without_exchange_transcript(tmp_path):
    state = snapshot()
    frame = state_frame(state)
    frame.update(restored_pending_decision_index=9, restored_public_exchanges=[{
        "exchange_index": 3,
        "response": {"response": {"response_type": "request_context", "lookup": {
            "view": "composition_information", "operation": "process.entry", "arguments": {"option_id": "P08"}},
            "private_extra": "DO_NOT_RENDER_RESPONSE_TRANSCRIPT"}},
        "lookup_result": {"status": "completed", "result": {"option_ref": {
            "version": "scientific_process_option_ref_v1", "library_id": "c" * 64,
            "slot": "thought_pattern", "option_id": "P08", "entry_sha256": "d" * 64},
            "entry": {"slot": "thought_pattern", "id": "P08", "name": "Alternative strategy",
                "decision_guidance": ["Use the requested comparison."],
                "evidence": [{"observation": "PRIVATE_INSTRUCTION_PROVENANCE"}]}}}}])
    wire = ScientificWire(tmp_path / "reopened")
    asyncio.run(complete(wire, frame))
    text = wire.turns_sent()[0]["input"][0]["text"]
    assert_task(text)
    assert_no_bookkeeping(text)
    assert "Use the requested comparison." in text
    assert "DO_NOT_RENDER_RESPONSE_TRANSCRIPT" not in text
    assert "PRIVATE_INSTRUCTION_PROVENANCE" not in text
    # Pins are explicit callable operands, not an excuse to hide identities
    # needed by the unchanged child-assignment/option lookup contracts.
    assert "c" * 64 in text and "d" * 64 in text
    assert "Previously answered lookups remain answered" in text
    saved = json.loads((tmp_path / "reopened/call-00001/request.json").read_text())
    assert saved["context"] == frame


def test_own_attempt_lookup_is_a_factual_page_with_actionable_detail_operands(tmp_path):
    wire = ScientificWire(tmp_path / "wire")
    query = {"view": "own_attempt_detail", "decision_index": 2, "pointer": "/arguments/query",
        "offset": 0, "limit": 32}
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result", "result": {
        "view": "own_attempts", "run_id": "PRIVATE_RUN", "episode_id": "PRIVATE_EPISODE",
        "records": [{"decision_index": 2, "category": "tool/source.read", "status": "failed",
            "completed_gain": None, "completion": {"unit_ref": "PRIVATE_UNIT"},
            "inputs": {"arguments": {"query": {"representation": "bounded_selected_input_v1",
                "value_type": "string", "bytes": 12345, "sha256": "PRIVATE_INPUT_HASH",
                "total": 12345, "detail_query": query}}},
            "published_references": {"values": [], "total": 0, "included": 0, "complete": True,
                "saved_value": {"sha256": "PRIVATE_RESULT_HASH"}},
            "input_fields": {"complete": True}, "outcome_summary": {"sha256": "PRIVATE_OUTCOME_HASH"}}],
        "offset": 0, "total": 1, "returned_count": 1, "next_query": None, "unavailable_reasons": []}}
    async def exercise():
        await complete(wire, state_frame(snapshot()))
        await complete(wire, lookup)
    asyncio.run(exercise())
    text = wire.turns_sent()[1]["input"][0]["text"]
    assert_task(text)
    assert "| 2 | tool/source.read | failed | null |" in text
    assert "/arguments/query" in text and "own_attempt_detail" in text
    assert "PRIVATE_" not in text


def test_frame_validation_and_episode_isolation_precede_dispatch(tmp_path):
    wire = ScientificWire(tmp_path / "wire")
    state = snapshot()
    changed = deepcopy(state)
    changed["current_credit"] = 9
    damaged = state_frame(changed, state)
    damaged["fields"]["current_credit"] = 99
    async def exercise():
        await complete(wire, state_frame(state))
        with pytest.raises(ValueError, match="revision_conflict"):
            await complete(wire, damaged)
        with pytest.raises(TypeError, match="previous_model_state_requires_object"):
            await complete(wire, state_frame(changed, {}), episode="another")
    asyncio.run(exercise())
    assert len(wire.turns_sent()) == 1
    assert wire.scientific_prompt_states[("episode", "REASONING")]["current_credit"] == 4


def test_selected_manual_lookup_retains_text_and_page_operands(tmp_path):
    wire = ScientificWire(tmp_path / "wire")
    state = snapshot()
    state["selected_launch_instructions"] = {"selection": {"library_id": "PRIVATE_MANUAL_LIBRARY"},
        "sections": [{"entry_id": "selected_service", "section_id": "inputs",
            "text": "Use the parent's selected input records and selected compute allocation.",
            "section_sha256": "PRIVATE_MANUAL_HASH"}]}
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result", "result": {
        "status": "completed", "operation_ref": "PRIVATE_LOOKUP_OPERATION", "result": {
            "text": "Exact returned manual window.\nContinue with the selected record.",
            "entry_id": "selected_service", "section_id": "inputs", "coordinate_unit": "zero_based_lines",
            "offset": 0, "returned_lines": 2, "total_lines": 5, "section_sha256": "PRIVATE_WINDOW_HASH",
            "next_query": {"entry_id": "selected_service", "section_id": "inputs", "offset": 2, "limit": 3}}}}
    async def exercise():
        await complete(wire, state_frame(state))
        await complete(wire, lookup)
    asyncio.run(exercise())
    text = wire.turns_sent()[1]["input"][0]["text"]
    assert_task(text)
    assert "Use the parent's selected input records and selected compute allocation." in text
    assert "Exact returned manual window.\nContinue with the selected record." in text
    assert "next_query.offset | 2" in text
    assert "PRIVATE_" not in text


def test_pending_progress_is_the_selected_latest_observation_with_original_units(tmp_path):
    wire = ScientificWire(tmp_path / "wire")
    state = snapshot()
    state["pending_work"] = {"items": [{"handle": "child_selected", "role": "scientific_process",
        "lifecycle_state": "executing", "latest_progress_ref": "progress_current", "return_available": False,
        "resource_selection": {"resource_id": "resource_local", "kind": "local", "allocation": {"cpu": 2},
            "capability_binding_ref": "PRIVATE_CAPABILITY_PIN"}}]}
    progress = {"progress_ref": "progress_current", "target_handle": "child_selected",
        "observed_at": "2026-10-24T10:00:00+00:00", "provenance_refs": ["PRIVATE_PROGRESS_HASH"],
        "execution_status": {"handle": "child_selected", "lifecycle_state": "executing", "liveness": "live",
            "execution_identity": {"pid": 42, "boot_id": "PRIVATE_BOOT_ID"}},
        "measurements": [{"name": "completed_rows", "value": 18, "unit": "rows",
            "measured_at": "2026-10-24T09:59:00+00:00", "provenance_ref": "source_measurement"}],
        "log_windows": [{"source_ref": "source_progress_log", "artifact_ref": "artifact_log",
            "start_byte": 0, "end_byte": 50, "content_sha256": "PRIVATE_LOG_HASH"}],
        "dependencies": [], "result_available": False}
    state["waiting_support"]["progress_records"] = [
        {**deepcopy(progress), "progress_ref": "progress_old", "measurements": ["UNREQUESTED_OLD_PROGRESS"]}, progress]
    state["report_deliveries"] = [{"delivery_ref": "PRIVATE_CLOSED_DELIVERY", "status": "delivered"},
        {"delivery_ref": "delivery_repair", "status": "pending"}]
    asyncio.run(complete(wire, state_frame(state)))
    text = wire.turns_sent()[0]["input"][0]["text"]
    assert_task(text)
    assert "completed_rows" in text and "| [0].measurements[0].unit | rows |" in text
    assert "source_progress_log" in text and "source_measurement" in text
    assert "2026-10-24T09:59:00+00:00" in text
    assert "delivery_repair" in text
    assert "PRIVATE_" not in text and "UNREQUESTED_OLD_PROGRESS" not in text


@pytest.mark.parametrize("published", [False, True])
def test_scope_is_published_instructions_and_original_pixel_delivery_is_unchanged(tmp_path, published):
    calls = []
    def resolve(image):
        calls.append(image)
        return {"type": "localImage", "path": "/fixture/image.png"}
    wire = ScientificWire(tmp_path / "wire", image_resolver=resolve)
    state = snapshot()
    if not published:
        state["scientific_process"]["evidence_axis"]["instruction_status"] = "limited_existing_measurement_guidance"
    state["visual_evidence"] = [{"id": "selected-image"}]
    frame = state_frame(state)
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result", "result": {"records": []}}
    async def exercise():
        await complete(wire, frame)
        await complete(wire, lookup)
    asyncio.run(exercise())
    turns = wire.turns_sent()
    assert len(turns[0]["input"]) == 2 and len(turns[1]["input"]) == 1
    assert calls == [{"id": "selected-image"}]
    if published:
        assert_task(turns[0]["input"][0]["text"])
        assert_task(turns[1]["input"][0]["text"])
    else:
        assert json.loads(turns[0]["input"][0]["text"]) == frame
        assert json.loads(turns[1]["input"][0]["text"]) == lookup
        assert not wire.scientific_prompt_states
