"""Structured presentation for an episode's own continuing decision conversation.

The full saved calculation context is never changed. These frames carry the
model's view, not parent-to-child assignments or estimator training operands.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from method_loop.durable import canonical

from .infernal_result_presentation import infernal_receiver_context

VERSION = "decision_context_v1"
PROTOCOL = "decision_exchange_v1"

INSTRUCTIONS = """
Your internal decision may take several model exchanges. Return the required
closed response object. Use response_type=request_context to request your own
prior attempts through the declared lookup form. This only retrieves information
you already received; it does not perform new scientific work or complete an
action. After its decision_lookup_result arrives, continue the SAME decision.
For this protocol, use request_context for own history; episode.history is not
an available action. This replaces the older history-tool instruction.
Use response_type=select_action with selection and report_update when ready to
dispatch an actual action. Only that action's actual completion supplies an
observation to your configured continuation controller.

decision_bootstrap supplies an authoritative scoped model state. decision_update
replaces the listed top-level fields and removes exactly removed_fields; omitted
fields keep their previous values. base_revision identifies the previous state
and revision identifies the resulting state. Newer state replaces older values,
including yield expectations; older estimates remain historical. A bootstrap
after conversation loss or compaction replaces earlier presentation state.
decision_lookup_result supplies only the requested own historical information.
Restored public exchanges preserve the requests and results of an unfinished
decision; do not repeat their already answered lookups merely to restore memory.

action_yields describes your OWN completed action categories. total_yield is
observed signed gain, excluding inherited credit. Expected category yield is
conditional on choosing and completing that category again; unavailable is not
zero. Approximate model bands are not calibrated next-outcome guarantees. Useful
evidence acquisition can have zero immediate credit when a later interpretation
earns the credit. Failed or unexecuted attempts have no completed-action gain.
Use recorded inputs and result references to distinguish specific prior attempts.
""".strip()

# Text-rendered scientific decisions preserve this protocol's action/lookup and
# yield meanings. Frame identities remain host reconstruction details, so the
# provider uses this variant only for published investigation instructions.
_FRAME_INSTRUCTIONS = INSTRUCTIONS[INSTRUCTIONS.index('decision_bootstrap supplies'):
    INSTRUCTIONS.index('action_yields describes')]
TEXT_INSTRUCTIONS = INSTRUCTIONS.replace(_FRAME_INSTRUCTIONS,
    'Each request supplies the complete task and current decision-relevant information. '
    'Current values replace earlier values, including yield expectations; prior estimates '
    'remain historical. A requested own-history lookup continues this same pending decision. '
    'Previously answered lookups remain answered after reconstruction; do not repeat them '
    'merely to restore memory.\n\n')


def _copy(value):
    return json.loads(canonical(value))


def _object(value, name):
    if not isinstance(value, Mapping):
        raise TypeError(name + "_requires_object")
    return _copy(value)


def revision(snapshot):
    """A stable identity for exactly the state reconstructed by the model."""
    return hashlib.sha256(canonical(snapshot).encode("utf-8")).hexdigest()


def instructional_model_context(value):
    """Expose only investigation guidance in axis copies supplied to a model.

    Lookup replies, saved action outcomes and restored exchanges can contain an
    older full process.entry result. Preserve that record on disk and project
    only its limited investigation guidance here. Published instruction records
    likewise retain their provenance on disk rather than in their task view.
    This is not a general filter of scientific evidence, caller forms or
    numerical estimator operands.
    """
    from .evidence_axis_contracts import VERSION as EVIDENCE_AXIS_VERSION
    from .evidence_axis_instructions import VERSION as INSTRUCTION_VERSION, instruction_view
    from .scientific_process_library import evidence_axis_instruction_view

    def project(node):
        if isinstance(node, dict):
            if node.get('entry_version') == INSTRUCTION_VERSION:
                return instruction_view(node)
            if (node.get('entry_version') == EVIDENCE_AXIS_VERSION
                    or {'native_measurements', 'judgment_criteria', 'qualitative_grading',
                        'name', 'id'} <= node.keys()):
                return evidence_axis_instruction_view(node)
            result = {key: project(item) for key, item in node.items()}
            process = result.get('scientific_process')
            if isinstance(process, dict):
                # This was a detached draft-sheet descriptor, never the
                # parent's actual typed return or response contract.
                process.pop('axis_judgment_contract', None)
            return result
        if isinstance(node, list):
            return [project(item) for item in node]
        return node

    return project(_copy(value))


def model_snapshot(raw_context, table):
    """Purely replace repeated own history with the decision-category table.

    Current controller estimates and their meaning stay visible. Raw waiting
    histories and local-return training samples remain in the saved calculation
    context for their numerical consumers and scoped lookup; no observation is
    truncated, repriced or copied to a child.
    """
    state = infernal_receiver_context(
        instructional_model_context(_object(raw_context, "decision_context")))
    state["action_yields"] = _object(table, "action_yield_table")
    support = state.get("waiting_support")
    if isinstance(support, dict):
        support.pop("own_completed_action_history", None)
        support.pop("local_return_history", None)
        source_version = support.pop("version", None)
        support["version"] = "decision_waiting_view_v1"
        support["source_version"] = source_version
    controller = state.get("controller")
    if isinstance(controller, dict):
        controller.pop("scores", None)
    return state


def state_frame(current, previous=None):
    """Create an initial snapshot or an exact top-level replacement delta."""
    current = _object(current, "current_model_state")
    if previous is None:
        return {"version": VERSION, "kind": "decision_bootstrap",
            "base_revision": None, "revision": revision(current),
            "fields": current, "removed_fields": []}
    previous = _object(previous, "previous_model_state")
    return {"version": VERSION, "kind": "decision_update",
        "base_revision": revision(previous), "revision": revision(current),
        "fields": {key: value for key, value in current.items()
                   if key not in previous or canonical(value) != canonical(previous[key])},
        "removed_fields": sorted(set(previous) - set(current))}


def apply_state_frame(previous, frame):
    """Validate frame identity and reconstruct its authoritative model state."""
    frame = _object(frame, "decision_frame")
    required = {"version", "kind", "base_revision", "revision", "fields", "removed_fields"}
    restoration = {"restored_public_exchanges", "restored_pending_decision_index"}
    if (not required <= set(frame) or set(frame) - required - restoration
            or frame["version"] != VERSION or not isinstance(frame["fields"], dict)
            or not isinstance(frame["removed_fields"], list)
            or any(not isinstance(key, str) for key in frame["removed_fields"])
            or len(set(frame["removed_fields"])) != len(frame["removed_fields"])
            or set(frame["removed_fields"]).intersection(frame["fields"])):
        raise ValueError("invalid_decision_frame")
    if set(frame).intersection(restoration):
        if (frame["kind"] != "decision_bootstrap" or not restoration <= set(frame)
                or not isinstance(frame["restored_public_exchanges"], list)
                or any(not isinstance(item, dict) for item in frame["restored_public_exchanges"])
                or type(frame["restored_pending_decision_index"]) is not int
                or frame["restored_pending_decision_index"] < 0):
            raise ValueError("invalid_decision_restoration")
    if frame["kind"] == "decision_bootstrap":
        if frame["base_revision"] is not None or frame["removed_fields"]:
            raise ValueError("invalid_decision_bootstrap")
        result = frame["fields"]
    elif frame["kind"] == "decision_update":
        previous = _object(previous, "previous_model_state")
        if frame["base_revision"] != revision(previous):
            raise ValueError("decision_frame_base_conflict")
        if not set(frame["removed_fields"]) <= set(previous):
            raise ValueError("decision_frame_removes_unknown_field")
        result = {key: value for key, value in previous.items()
                  if key not in frame["removed_fields"]}
        result.update(frame["fields"])
    else:
        raise ValueError("unknown_decision_frame_kind")
    if frame["revision"] != revision(result):
        raise ValueError("decision_frame_revision_conflict")
    return _copy(result)
