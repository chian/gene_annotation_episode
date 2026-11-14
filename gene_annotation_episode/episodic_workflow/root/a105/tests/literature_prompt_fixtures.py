"""Actual provider turn inputs with a controlled wire, without model inference.

Synthetic source snippets and state exercise presentation and reconstruction.
These checks do not validate papers, scientific grading or live-model choices.
"""
import asyncio
from copy import deepcopy
import json

from ..decision_context import INSTRUCTIONS, state_frame
from ..providers import _SessionConnection, load_config


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
    from types import MethodType, SimpleNamespace
    from ..providers import ModelConnection
    from ..published_evidence_assessment.episode import LiteratureEpisode
    # Keep the real ModelConnection.complete and presentation methods. Only the
    # serial I/O boundary forwards to the original scripted SessionConnection.
    if not hasattr(wire, '_private_model_connection'):
        provider = object.__new__(ModelConnection)
        provider.worker_lock = asyncio.Lock()
        async def serial(self, episode_id, role, instructions, context, output_schema, *, prompt_renderer=None):
            if prompt_renderer is None:
                return await wire.complete(episode_id, role, instructions, context, output_schema)
            return await wire.complete(episode_id, role, instructions, context, output_schema,
                prompt_renderer=prompt_renderer)
        provider._complete_serial = MethodType(serial, provider)
        wire._private_model_connection = provider
    source = SimpleNamespace(episode_id=episode, workflow=SimpleNamespace(
        provider=wire._private_model_connection, specialist=lambda source: LiteratureEpisode))
    return LiteratureEpisode.decision_source_type.decision_completion(source)(
        episode, 'REASONING', INSTRUCTION_TEXT, state, OUTPUT_SCHEMA)


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

