"""Four-field information and separate child-owned AppService contracts.

These entries describe actual individual native operations. They neither enable
a service in an unbound receiver nor claim a deployed scientific adapter.
"""
from copy import deepcopy

from .bvbrc_appservice_contracts import contract_schema


PREFIX = "api.bvbrc_appservice."
_DETAILS = {
    "enumerate_apps": (
        "Acquire the configured AppService's ordered application definitions.",
        "Select no arguments. Issue AppService.enumerate_apps with native params []. Preserve the complete "
        "correlated response, definition order and malformed members. A definition can later be selected by "
        "its actual record index; enumeration neither prepares nor submits a job."),
    "prepare": (
        "Validate the assigned application and unchanged native operands using one selected definition.",
        "Select a packaged, originally supplied, or previously acquired indexed definition. The host supplies "
        "its actual source-backed envelope to prepare_application. Validate the original application, parameters, "
        "start parameters and output destination locally. Preserve C3 errors and qualifications; preparation "
        "inserts no defaults, submits nothing and does not establish current deployment or input availability."),
    "workspace_metadata": (
        "Acquire metadata for the explicitly selected Workspace objects in one native call.",
        "Select exact original input/target, receipt-row, task-info object or manifest-member references. "
        "Workspace.get uses metadata_only=1 and only the selected options. Retain native metadata tuples, "
        "their original positions, all valid rows and individual failures. Metadata does not acquire file bytes; "
        "object size and Workspace UUID remain distinct from a Shock node or immutable producer-byte identity."),
    "workspace_create": (
        "Create the explicitly assigned Workspace targets in one selected native call.",
        "Select assigned target IDs, exact data bindings, creation times and native options. Workspace.create "
        "retains all targets, returned ancestors, partial failures and overwrite effects. createUploadNodes=1 "
        "creates empty nodes for a separately selected upload; a zero size is not upload completion. "
        "downloadFromLinks=1 requires exact originally supplied links and records the server-side fetch. "
        "downloadLinks=1 is source-declared but unused and is rejected. The native call cannot enforce a "
        "constraint forbidding ancestor creation. Creating support objects does not submit the scientific job."),
    "upload": (
        "Upload one retained original input to its selected created Shock node.",
        "Select an exact create receipt row, original retained-byte input binding and filename. One multipart "
        "PUT sends field upload with the complete authenticated bytes. Preserve original digest/length, "
        "Workspace and Shock identities, native reply and returned checksums. Compare only observed matching "
        "checksum algorithms. An accepted identity alone does not establish byte identity. No task is submitted."),
    "submit": (
        "Submit the original prepared scientific job through one start_app2 request.",
        "Select the exact successful preparation receipt and supplied input evidence. AppService.start_app2 "
        "receives exactly the prepared native application, parameters and start parameters. Preserve the actual "
        "correlated scheduler response and task ID. Compare every returned original parameter/app field; retain "
        "native _preflight additions separately and missing echoes as unknown. A receipt is a usable job handoff, "
        "not scientific output. An uncertain issued submission remains unresolved; this operation never retries."),
    "status": (
        "Observe the original possessed AppService task's native status once.",
        "Select the original handoff. AppService.query_tasks receives exactly [[original_task_id]]. Retain the "
        "native map, exact selected member, native state and timing strings. Missing sentinels, unknown timezone "
        "and SQL TIMEDIFF values retain their meanings; HTTP turnaround is not scientific execution duration. "
        "No task search, log acquisition, polling schedule or throughput/stall inference is performed."),
    "task_info": (
        "Acquire one selected original task-info file or complete returned log.",
        "Select the original handoff and exactly stdout, stderr, job_result_id or job_result_folder. One "
        "authenticated GET retains the full signature-redacted representation. A UUID file must contain the "
        "actual UUID, not a substring guessed from a log. Log observations do not refresh status, declare "
        "completion or infer a stall. Local excerpt offsets refer only to the retained returned representation."),
    "list_outputs": (
        "List the explicitly selected output containers or original output path once.",
        "Workspace.ls receives the exact selected paths and native flags, including the source spelling "
        "fullHierachicalOutput. Retain all groups, rows and order. There is no inspected cursor/offset contract; "
        "an absent empty-directory group is retained as absence. Container membership alone does not establish "
        "that a file was produced by the original task, and no basename search chooses a file."),
    "download_capability": (
        "Acquire download capabilities for the exact selected output objects.",
        "Workspace.get_download_url receives one explicit ordered object array. Preserve each URL or null at "
        "its original index. This creates remote capability keys and may change Shock ACLs, so it owns an "
        "effect slot for the exact object and selected generation. Later generations cite prior evidence and "
        "are separately selected work. Expiry is unknown unless actually observed. Capability strings remain "
        "internal; this operation downloads no bytes and never refreshes a capability automatically."),
    "download": (
        "Acquire one exact capability's output bytes and enable same-action deterministic publication.",
        "Select the possessed capability entry, exact object, positive integer max_bytes, inclusive byte range "
        "or null, requirement IDs, role and declared format. One GET retains the exact response prefix within "
        "that byte cap, with observed-versus-retained counts, HTTP 200/206, Content-Range, Content-Length "
        "and separate body/object completeness. A 200 response ignoring Range keeps its actual prefix; "
        "hitting the cap leaves the object incomplete. "
        "Do not follow redirects, refresh capabilities or fetch another file. The host publishes from frozen "
        "dependencies; an explicitly bound scientific adapter may parse and calculate without acquisition. "
        "Missing sidecars, unknown producer-byte version and unavailable adapters remain qualified partials."),
}

OPERATIONS = tuple(PREFIX + suffix for suffix in _DETAILS)
LAUNCH_OPERATIONS = tuple(PREFIX + suffix for suffix in (
    "enumerate_apps", "prepare", "workspace_metadata", "workspace_create", "upload", "submit", "status", "task_info"))
RESULT_OPERATIONS = tuple(PREFIX + suffix for suffix in (
    "workspace_metadata", "status", "task_info", "list_outputs", "download_capability", "download"))


def _schema(suffix):
    schema = contract_schema("Arguments_" + suffix)
    if suffix == "download":
        # Retained contracts accept the exact old shape. Current selections
        # always name their cap; no default or historical rewrite is supplied.
        schema["$defs"]["Arguments_download"]["required"].append("max_bytes")
    # An explicit resource boundary keeps local refs correct when the common
    # episode embeds this schema inside its operation-selection schema.
    schema["$id"] = "urn:gene-annotation:bvbrc-appservice:arguments:" + suffix
    return schema


def operation_catalog(role):
    if role not in ("launch_api", "results"):
        raise ValueError("bvbrc_appservice_operation_role_invalid")
    names = LAUNCH_OPERATIONS if role == "launch_api" else RESULT_OPERATIONS
    return [{"name": name, "description": _DETAILS[name.removeprefix(PREFIX)][0],
             "input_schema": _schema(name.removeprefix(PREFIX))} for name in names]


def bvbrc_appservice_tool_information():
    return [{"name": PREFIX + suffix, "description": description, "resources": "api",
             "instructions": instructions + " Use the separately supplied closed operation contract within "
             "the assigned API execution or results episode. Episode choices own additional work; this "
             "support operation supplies no invented annotation-confidence score."}
            for suffix, (description, instructions) in _DETAILS.items()]


def bvbrc_appservice_tool_contracts(*, resource_id):
    if type(resource_id) is not str or not resource_id or "\x00" in resource_id:
        raise ValueError("bvbrc_appservice_resource_id_required")
    result = []
    for info in bvbrc_appservice_tool_information():
        name = info["name"]
        routes = []
        if name in LAUNCH_OPERATIONS:
            routes.append({"entry_role": "launch", "resource_id": resource_id, "resource_role": "launch_api"})
        if name in RESULT_OPERATIONS:
            routes.append({"entry_role": "results", "resource_id": resource_id, "resource_role": "results"})
        result.append({**deepcopy(info), "input_schema": _schema(name.removeprefix(PREFIX)),
                       "invocation_route": {"kind": "commission", "routes": routes}})
    return result


__all__ = ["PREFIX", "OPERATIONS", "LAUNCH_OPERATIONS", "RESULT_OPERATIONS", "operation_catalog",
           "bvbrc_appservice_tool_information", "bvbrc_appservice_tool_contracts"]
