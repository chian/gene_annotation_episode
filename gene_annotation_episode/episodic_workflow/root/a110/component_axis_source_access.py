"""Source access feedback for A110's private reaction literature work."""

import json

from .communication import plain
from .domain import identity
from .episode_return_records import EpisodeReturnRecords


VERSION = "component_axis_source_access_v1"
ERROR = "literature_reading_outside_assigned_source"
RECOVERY = (
    "This reader can use its assigned source and derived sources. "
    "A received sibling dataset needs an assignment that includes it. "
    "Report the missing source access to the parent; a rejected read does not "
    "establish scientific absence or opposition."
)


def source_received_inputs(tools, name, arguments, scope, operation_key, selected):
    """Use the current reader's exact authenticated source receipts."""
    if selected is not None or name not in {
            "source.locate", "source.sequence.scan",
            "source.sequence.references", "source.experimental.records"}:
        return selected
    invocation = tools._current_invocation.get()
    if invocation is None or operation_key is None or invocation[2:] != (
            name, arguments, operation_key):
        return None
    context = invocation[0]
    try:
        if tools.store.validate_scope(scope) != plain(context.scope):
            return None
        if tools.store.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='runtime_episodes'").fetchone() is None:
            return ()
        EpisodeReturnRecords(tools.store, context.run_id,
            failure_prefix="component_source_").authenticate(context)
    except (ValueError, KeyError, TypeError):
        return ()
    return tuple(context.received_record_refs)


def rejection_detail(workflow, context, root, blocked):
    if workflow is None or not hasattr(getattr(workflow, "store", None), "db"):
        return None
    return {"version": VERSION, "assigned_source_ref": root,
        "blocked_source_refs": sorted(set(blocked)),
        "scientific_inference_authorized": False, "recovery": RECOVERY}


def decision_context(workflow, context):
    if (workflow.receipts is None or not hasattr(workflow.store, "db")
            or not (context.role.startswith("literature") or context.role == 'biochemical_feasibility_evidence')):
        return None
    EpisodeReturnRecords(workflow.store, workflow.run_id,
        failure_prefix="component_source_access_").authenticate(context)
    known = set(context.received_record_refs)
    assignment = plain(context.assignment)
    page = assignment if context.role == "literature_page" else assignment.get("page")
    result = {"version": VERSION, "operational_metadata_only": True,
        "permission_and_receipt_changes": False, "recovery": RECOVERY}
    from .component_axis_inspection import inspection_index
    inspected = inspection_index(workflow.store, run_id=workflow.run_id,
        episode_id=context.episode_id, known_source_refs=known)
    if inspected is not None:
        result['own_source_inspection'] = inspected
        result['operational_metadata_only'] = False
        result['already_received_information_only'] = True
    if page is not None:
        result["own_assigned_source_ref"] = page["source_ref"]
    notices, seen = [], set()
    rows = workflow.store.db.execute(
        "SELECT episode_id,path,state,"
        "json_extract(request,'$.message.episode_assignment.page.source_ref') page_source,"
        "json_extract(request,'$.message.episode_assignment.source_ref') source "
        "FROM runtime_episodes WHERE run_id=? ORDER BY episode_id",
        (workflow.run_id,)).fetchall()
    for row in rows:
        path = tuple(map(tuple, json.loads(row["path"])))
        if len(path) < len(context.path) or path[:len(context.path)] != context.path:
            continue
        failures = workflow.store.db.execute(
            "SELECT decision_index,"
            "json_extract(action,'$.tool') tool,"
            "json_extract(action,'$.arguments.source_ref') source_ref,"
            "json_extract(action,'$.arguments.data_source_ref') data_source_ref,"
            "json_extract(result,'$.feedback.detail.blocked_source_refs') blocked "
            "FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND json_extract(result,'$.feedback.code')=? ORDER BY decision_index DESC",
            (workflow.run_id, row["episode_id"], ERROR))
        for failure in failures:
            assigned = row["source"] if path[-1][0] == "literature_page" else row["page_source"]
            blocked = (json.loads(failure["blocked"]) if failure["blocked"] is not None else
                [value for value in (failure["source_ref"], failure["data_source_ref"])
                    if value is not None and value != assigned])
            key = (row["episode_id"], failure["tool"], tuple(sorted(blocked)))
            if key in seen:
                continue
            seen.add(key)
            branch = path[len(context.path)] if len(path) > len(context.path) else None
            notices.append({"handle": identity("source_access_need", {
                    "run_id": workflow.run_id, "receiver": context.episode_id,
                    "requester": row["episode_id"], "decision_index": failure["decision_index"]}),
                "own_attempt": branch is None,
                "child_role": None if branch is None else branch[0],
                "child_label": None if branch is None else branch[1],
                "requesting_role": path[-1][0], "requester_state": row["state"],
                "rejected_operation": failure["tool"], "code": ERROR,
                "assigned_source_ref": assigned if assigned in known else None,
                "blocked_received_source_refs": sorted(set(blocked) & known),
                "other_rejected_input_count": len(set(blocked) - known),
                "status": "retained_access_rejection",
                "meaning": "No scientific contents delivered; no absence or opposition inferred."})
    if not notices and not {"own_assigned_source_ref", "own_source_inspection"}.intersection(result):
        return None
    result.update(notices=notices[:12], total_distinct_notices=len(notices),
        omitted_notices=max(0, len(notices) - 12))
    return result
