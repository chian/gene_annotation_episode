"""Actual provider turn inputs with a controlled wire, without model inference.

Synthetic source snippets and state exercise presentation and reconstruction.
These checks do not validate papers, scientific grading or live-model choices.
"""
import asyncio
from copy import deepcopy
import json

from gene_annotation_episode.decision_context import INSTRUCTIONS, state_frame
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.providers import _SessionConnection, load_config


class LiteratureWire(_SessionConnection):
    """Run the real provider's complete/presentation path over scripted RPC."""

    def __init__(self, directory):
        super().__init__(load_config(), directory, directory.parent)
        self.sent = []
        self.turns = 0

    async def _rpc(self, method, params):
        self.sent.append((method, deepcopy(params)))
        if method == "thread/start":
            return {"thread": {"id": "controlled-literature-thread"},
                    "model": params["model"], "reasoningEffort": params["config"]["model_reasoning_effort"]}
        assert method == "turn/start"
        self.turns += 1
        turn = "controlled-literature-turn-" + str(self.turns)
        self.pending.extend([
            {"method": "item/completed", "params": {"threadId": "controlled-literature-thread",
                "item": {"type": "agentMessage", "text": '{"fixture":true}'}}},
            {"method": "turn/completed", "params": {"threadId": "controlled-literature-thread",
                "turn": {"id": turn, "status": "completed"}}},
        ])
        return {"turn": {"id": turn}}

    def turns_sent(self):
        return [params for method, params in self.sent if method == "turn/start"]


OBJECTIVE = "Determine whether the reference preparation oxygen-rate comparison establishes product formation."
QUALIFICATION = "The preparation consumed oxygen; productive coupling to a chemical product remains unquantified."
SOURCE_TEXT = "Reference: 0.16 µmol/min; 5 mM inhibitor: 0.10 µmol/min. No-enzyme blank was not reported."
LOOKUP_TEXT = "Selected source methods: errors are SD across three measurements; independent preparations were not identified."
OUTPUT_SCHEMA = {"type": "object", "properties": {"fixture": {"const": True}},
                 "required": ["fixture"], "additionalProperties": False}
INSTRUCTION_TEXT = "Evaluate the reference experiment iteratively within its assigned source scope.\n" + INSTRUCTIONS


def snapshot():
    """Finite synthetic state using the actual ordinary decision field shapes."""
    return {
        "goal": {"goal_id": "PRIVATE_GOAL", "parent_goal_id": "PRIVATE_PARENT_GOAL",
                 "objective": OBJECTIVE,
                 "task_context": {"constraint": "Use the retained original source and preserve its actual assayed subject."}},
        "scope": {"subject_refs": ["input_scoped_material"]},
        "literature_experimental_work": {"version": "literature_experimental_task_v1",
                                           "aspect": "source_rate_comparison"},
        "literature_assignment": {"version": "literature_assignment_v1",
            "question_context_refs": [], "source_refs": ["source_selected"],
            "requested_rate_components": ["rate_difference", "difference_se", "source_signed_index"]},
        "literature_source_custody": [{"source_ref": "source_selected",
            "artifact_ref": "artifact_selected", "version": "retained source representation"}],
        "working_state": {"problem_ref": "PRIVATE_PROBLEM", "subjects": [{
            "id": "input_scoped_material", "molecule": "protein", "length": 5,
            "sequence_ref": "artifact_supplied", "source_ref": "source_supplied",
            "record_type": "input", "name": "local reference material"}],
            "sources": [{"id": "source_unrequested", "uri": "UNREQUESTED_SOURCE_INVENTORY"}],
            "observations": [{"id": "observation_unrequested", "value": "UNREQUESTED_OBSERVATION"}]},
        "tools": [{"name": "source.read", "description": "Read the selected retained source byte window.",
            "input_schema": {"type": "object", "properties": {
                "source_ref": {"type": "string", "format": "reference"},
                "representation": {"type": "string", "enum": ["original", "text"]},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1}},
                "required": ["source_ref", "representation", "offset", "limit"],
                "additionalProperties": False}}],
        "child_options": "literature_strategy can compare search approaches for this assigned experimental question.",
        "requested_report_purpose": "Return the requested source-rate cells and necessary qualifications.",
        "requested_form": {"type": "object", "properties": {
            "measurements": {"type": "array", "items": {"type": "object", "properties": {
                "component": {"type": "string", "enum": ["rate_difference", "difference_se", "source_signed_index"]},
                "value": {"type": ["number", "null"]},
                "unit": {"type": ["string", "null"], "enum": ["umol/min", "dimensionless", None]}},
                "required": ["component", "value", "unit"], "additionalProperties": False},
                "x-source": "literature_rate_cells", "description": "Recorded source-preparation measurements; unavailable inputs remain null."}},
            "required": ["measurements"], "additionalProperties": False},
        "available_report_facts": {"literature_rate_cells": {"meaning": "Source endpoint statistics, not an annotation probability or transfer score."},
                                   "unused_fact": {"meaning": "UNREQUESTED_FACT_DEFINITION"}},
        "current_report_update": {}, "current_report_basis_refs": [],
        "last_local_outcome": None, "feedback": None,
        "current_credit": 0,
        "controller": {"scores": [999], "epoch": "PRIVATE_EPOCH",
            "estimate": {"turns": 2, "expected_next_gain": {
                "value": .5, "lower": -.1, "upper": .9, "status_code": 0,
                "uncertainty_code": 2, "alpha": .05}, "diagnostics": {"fit": "PRIVATE_FIT"}},
            "decision": {"continuation_cost": .001}},
        "action_yields": {"version": "own_decision_yield_table_v1", "before": 5,
            "rows": [{"category": "tool/source.read", "completed_actions": 2,
                "total_yield": -.25, "attempted_uncompleted": 1,
                "expected_yield": {"status": "unavailable", "unavailable_reason": "parameters_unbound", "band": None}}]},
        "own_literature_outcomes": {"records": []},
        "waiting_support": {"own_completed_action_history": ["PRIVATE_OWN_HISTORY"],
                            "local_return_history": {"samples": ["PRIVATE_CHILD_HISTORY"]}},
        "restored_episode_history": {"entries": ["PRIVATE_RESTORE_HISTORY"]},
        "child_reports": [], "pending_work": {"items": []},
    }


def complete(wire, state, *, episode="literature-episode"):
    return wire.complete(episode, "REASONING", INSTRUCTION_TEXT, state, OUTPUT_SCHEMA)


def assert_task(text):
    assert text.startswith("TASK\n\n")
    assert text.count("\n\nSTEERING\n") == 1
    task = text.split("\n\nSTEERING\n", 1)[0]
    for item in (OBJECTIVE, "source_selected", "source.read", "representation", "offset", "limit",
                 "rate_difference", "difference_se", "source_signed_index",
                 "Return the requested source-rate cells and necessary qualifications.",
                 "Recorded source-preparation measurements; unavailable inputs remain null."):
        assert item in task
    # Experimental meanings matter more than an exact sentence or heading.
    for item in ("subject", "condition", "endpoint", "control", "uncertainty"):
        assert item in task.lower()
    assert "no-enzyme" in task.lower()
    assert "product" in task.lower()
    assert "independen" in task.lower()
    assert "transfer" in task.lower()
    return task


def assert_no_bookkeeping(text):
    for item in ("PRIVATE_GOAL", "PRIVATE_PARENT_GOAL", "PRIVATE_PROBLEM", "PRIVATE_EPOCH",
                 "PRIVATE_FIT", "PRIVATE_OWN_HISTORY", "PRIVATE_CHILD_HISTORY", "PRIVATE_RESTORE_HISTORY",
                 "UNREQUESTED_SOURCE_INVENTORY", "UNREQUESTED_OBSERVATION", "UNREQUESTED_FACT_DEFINITION",
                 "PRIVATE_OPERATION", "PRIVATE_PIN", "base_revision", "removed_fields",
                 "decision_bootstrap supplies", "restored_pending_decision_index",
                 "DO_NOT_RENDER_RESPONSE_TRANSCRIPT"):
        assert item not in text


def test_native_turns_repeat_full_task_after_delta_and_same_decision_lookup(tmp_path):
    wire = LiteratureWire(tmp_path / "wire")
    first = snapshot()
    second = deepcopy(first)
    second["last_local_outcome"] = {"status": "completed", "operation_ref": "PRIVATE_OPERATION",
        "record_refs": [], "changed_record_refs": [], "result": {
            "source_ref": "source_selected", "artifact_ref": "artifact_selected",
            "representation": "original", "start": 0, "end": len(SOURCE_TEXT.encode()),
            "text": SOURCE_TEXT, "qualification": QUALIFICATION}}
    second["feedback"] = {"category": "arguments_or_reference", "code": "condition_mismatch", "field": "test_condition"}
    second["controller"]["estimate"]["expected_next_gain"]["value"] = .25
    delta = state_frame(second, first)
    assert "literature_experimental_work" not in delta["fields"]
    lookup = {"version": "decision_context_v1", "kind": "decision_lookup_result",
              "decision_index": 8, "exchange_index": 2,
              "result": {"status": "completed", "text": LOOKUP_TEXT, "content_sha256": "PRIVATE_PIN"}}
    original = deepcopy((first, second, delta, lookup))

    async def exercise():
        assert await complete(wire, state_frame(first)) == {"fixture": True}
        await complete(wire, delta)
        await complete(wire, lookup)
    asyncio.run(exercise())
    turns = wire.turns_sent()
    assert len(turns) == 3
    tasks = []
    for turn in turns:
        text = turn["input"][0]["text"]
        tasks.append(assert_task(text))
        assert_no_bookkeeping(text)
        assert "tool/source.read" in text and "-0.25" in text
        assert "parameters_unbound" in text
        assert turn["outputSchema"] == OUTPUT_SCHEMA
    assert tasks[0] == tasks[1] == tasks[2]
    assert "| 2 | 0.5 |" in turns[0]["input"][0]["text"]
    assert SOURCE_TEXT not in turns[0]["input"][0]["text"]
    for turn in turns[1:]:
        text = turn["input"][0]["text"]
        assert SOURCE_TEXT in text
        assert QUALIFICATION in text
        assert "condition_mismatch" in text and "test_condition" in text
        assert "| 2 | 0.25 |" in text
        assert "lower=-0.1; upper=0.9" in text
    assert LOOKUP_TEXT in turns[2]["input"][0]["text"]
    assert (first, second, delta, lookup) == original
    developer = next(params["developerInstructions"] for method, params in wire.sent if method == "thread/start")
    assert "decision_bootstrap supplies" not in developer
    assert "request_context" in developer and "select_action" in developer
    saved = json.loads((tmp_path / "wire/call-00002/request.json").read_text())
    assert saved["context"] == delta
    assert saved["instructions"] == INSTRUCTION_TEXT
    assert saved["input"] == turns[1]["input"]


def test_restart_bootstrap_repeats_task_and_restores_only_answered_lookup_result(tmp_path):
    state = snapshot()
    frame = state_frame(state)
    frame.update(restored_pending_decision_index=9, restored_public_exchanges=[{
        "exchange_index": 3,
        "response": {"response": {"response_type": "request_context",
            "lookup": {"view": "own_history", "decision_index": 1},
            "private_extra": "DO_NOT_RENDER_RESPONSE_TRANSCRIPT"}},
        "lookup_result": {"status": "completed", "text": LOOKUP_TEXT,
                          "content_sha256": "PRIVATE_PIN"}}])
    original = deepcopy(frame)
    first = LiteratureWire(tmp_path / "first-process")
    restarted = LiteratureWire(tmp_path / "restarted-process")
    asyncio.run(complete(first, state_frame(state)))
    asyncio.run(complete(restarted, frame))
    before = first.turns_sent()[0]["input"][0]["text"]
    after = restarted.turns_sent()[0]["input"][0]["text"]
    assert assert_task(before) == assert_task(after)
    assert LOOKUP_TEXT in after
    assert_no_bookkeeping(after)
    assert restarted.turns_sent()[0]["outputSchema"] == OUTPUT_SCHEMA
    assert frame == original


def test_legacy_full_literature_state_renders_but_unmarked_state_keeps_original_path(tmp_path):
    marked = snapshot()
    marked_wire = LiteratureWire(tmp_path / "marked")
    asyncio.run(complete(marked_wire, marked))
    assert_task(marked_wire.turns_sent()[0]["input"][0]["text"])

    unmarked = snapshot()
    unmarked.pop("literature_experimental_work")
    unmarked_wire = LiteratureWire(tmp_path / "unmarked")
    asyncio.run(complete(unmarked_wire, unmarked))
    assert json.loads(unmarked_wire.turns_sent()[0]["input"][0]["text"]) == unmarked
    developer = next(params["developerInstructions"] for method, params in unmarked_wire.sent if method == "thread/start")
    assert developer == INSTRUCTION_TEXT


def test_only_enabled_literature_binding_supplies_experimental_marker():
    class EmptyServices:
        def own_outcomes(self, *_args, **_kwargs):
            return {"records": [], "offset": 0, "limit": 8, "next_offset": None}

    assignment = {"version": "literature_assignment_v1", "question_context_refs": [], "source_refs": []}
    context = BindingContext("run", "episode", "literature", (("literature", "case"),),
        {"subject_refs": ["input_fixture"]}, assignment, {})
    enabled = LiteratureEpisodes(EmptyServices(), rate_population=True)
    disabled = LiteratureEpisodes(EmptyServices())
    assert enabled.decision_context(context, None)["literature_experimental_work"] == {
        "version": "literature_experimental_task_v1", "aspect": "source_experimental_evidence"}
    assert "literature_experimental_work" not in disabled.decision_context(context, None)


def test_existing_published_scientific_context_keeps_its_own_task(tmp_path):
    from test_scientific_process_prompt_delivery import snapshot as scientific_snapshot
    state = scientific_snapshot()
    wire = LiteratureWire(tmp_path / "scientific")
    asyncio.run(complete(wire, state_frame(state), episode="scientific-episode"))
    text = wire.turns_sent()[0]["input"][0]["text"]
    assert text.startswith("TASK\n\n") and "\n\nSTEERING\n" in text
    assert "Determine what the supplied unnamed protein does." in text
    assert "Candidate functions may emerge" in text
    assert OBJECTIVE not in text
    assert wire.turns_sent()[0]["outputSchema"] == OUTPUT_SCHEMA


def test_native_turn_retains_cell_units_missingness_and_selected_experimental_identities(tmp_path):
    state = snapshot()
    state["last_local_outcome"] = {"status": "completed", "operation_ref": "PRIVATE_OPERATION",
        "record_refs": ["reference_assayed"], "changed_record_refs": [], "result": {
            "sheet_ref": "source_saved_sheet", "subject": "His-tagged reference preparation",
            "experiment": "inhibitor comparison", "scope": "source_preparation_endpoint",
            "source_uncertainty": {"reference": {"kind": "sd", "magnitude": .01, "count": 3,
                                                     "sampling_basis": "unspecified"}},
            "cells": {
                "rate_difference": {"value": -.12, "unit": "umol/min", "status": "populated",
                    "unavailable_reason": None, "conditional_on": [], "origin": "derived"},
                "source_signed_index": {"value": None, "unit": "dimensionless", "status": "unavailable",
                    "unavailable_reason": "observation_model_unspecified",
                    "conditional_on": ["independent_normal_groups"], "origin": "proposed"}}}}
    state["child_reports"] = [{"measurements": [{"component": "difference_se", "value": None,
        "unit": "umol/min", "unavailable_reason": "dependence_unknown",
        "assayed_subject_ref": "reference_assayed", "reference_condition_ref": "context_reference"}]}]
    state["working_state"]["references"] = [{"id": "reference_assayed", "record_type": "reference",
        "label": "His-tagged reference preparation", "source_ref": "source_selected"},
        {"id": "reference_unrequested", "label": "UNREQUESTED_REFERENCE_INVENTORY"}]
    state["working_state"]["contexts"] = [{"id": "context_reference", "record_type": "context",
        "name": "30 C, no inhibitor", "source_ref": "source_selected"}]
    original = deepcopy(state)
    wire = LiteratureWire(tmp_path / "cells")
    asyncio.run(complete(wire, state_frame(state)))
    text = wire.turns_sent()[0]["input"][0]["text"]
    assert_task(text)
    assert_no_bookkeeping(text)
    for item in ("-0.12", "umol/min", "unknown", "observation_model_unspecified",
                 "dependence_unknown", "independent_normal_groups", "His-tagged reference preparation",
                 "30 C, no inhibitor", "sd", "0.01", "unspecified"):
        assert item in text
    assert "UNREQUESTED_REFERENCE_INVENTORY" not in text
    assert '"cells":' not in text and '"child_reports":' not in text
    assert state == original
