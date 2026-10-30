"""Private selected molecular execution records, without execution authority.

The selected argv independently commits the scientific/private request payload.
These pure checks establish record relationships only. The future result owner
must compare them with the actual original practical assignment and lifecycle.
"""
from __future__ import annotations

from copy import deepcopy
import re
from pathlib import PurePosixPath

from .execution_contracts import canonical, digest
from . import molecular_sequence_driver as private


PAYLOAD_VERSION = "molecular_sequence_selected_payload_v1"
PLAN_VERSION = "molecular_sequence_selected_plan_v1"
BUNDLE_VERSION = "molecular_sequence_attempt_bundle_v1"
SOFTWARE_VERSION = "molecular_sequence_adapter_software_v1"
ADAPTER_MODULE = "gene_annotation_episode.molecular_sequence_execution_driver"
PLAN_FILENAME = "molecular-sequence-plan.json"
ATTEMPT_DIRECTORY = "molecular-sequence-attempt"
OWNER_FILENAME = ".molecular-sequence-owner.json"
STARTED_FILENAME = ".molecular-sequence-started.json"
BUNDLE_FILENAME = "attempt-bundle.json"
REQUEST_RELATIVE = "inputs/driver-request.json"
MANIFEST_RELATIVE = "inputs/software-files.json"
OUTPUT_DIRECTORY = "driver-output"
OPERATIONS = ("annotate_open_reading_frames", "align_sequences", "find_n_glycosylation_motifs",
    "predict_o_glycosylation_hotspots", "analyze_protease_kinetics")
BASE_ROLES = ("private_stdout", "private_stderr", "declaration", "capture", "sheet", "components")
NATIVE_ROLES = ("native_results", "native_plot")
STAGES = ("plan", "request", "software_before", "launch", "process", "software_after",
    "output_observation", "declaration_validation", "replay")
FAILURE_CODES = ("invalid_plan", "request_unavailable", "request_identity_conflict", "request_document_conflict",
    "software_unavailable", "software_identity_conflict", "software_import_conflict", "original_owner_conflict",
    "original_invocation_uncertain", "inner_launch_failed", "inner_nonzero_exit", "output_unavailable",
    "output_not_regular", "output_identity_conflict", "declaration_missing", "declaration_malformed",
    "declaration_input_conflict", "replay_artifact_conflict", "adapter_io_failure")
IDENTITY_FIELDS = {"run_id", "episode_id", "resource_id", "execution_id", "attempt_id", "operation_key",
    "assignment_sha256", "requested_job_sha256"}
PLAN_FIELDS = {"version", "identity", "requested_job", "selection", "software", "policy", "selected_environment",
    "selected_payload_sha256", "attempt_directory"}
BUNDLE_FIELDS = {"version", "plan_sha256", "identity", "selected_payload_sha256", "retained_inputs",
    "selected_request_file", "observed_request_file", "private_asserted_attempt_identity", "adapter_argv",
    "private_driver_argv", "cwd", "selected_environment", "realized_environment", "software_verification",
    "invocation", "files", "failures", "sealed"}


class MolecularSequenceExecutionError(ValueError):
    def __init__(self, code, field=""):
        self.code, self.field = code, field
        super().__init__(code + (":" + field if field else ""))


def require(condition, code="invalid_plan", field=""):
    if not condition:
        raise MolecularSequenceExecutionError(code, field)


def closed(value, fields, field=""):
    require(type(value) is dict and set(value) == set(fields), field=field)


def _text(value):
    return type(value) is str and bool(value) and not any(c in value for c in "\0\n\r")


def _sha(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def environment(value):
    require(type(value) is dict and all(type(k) is str and re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", k)
        and type(v) is str and "\0" not in v for k, v in value.items()), field="/environment")
    return deepcopy(value)


def file_pin(value):
    # Exact existing private three-field pin contract; this performs no I/O.
    return private._file_pin(value)


def absolute_path(value):
    return PurePosixPath(str(private._path(value)))


def _software(value):
    closed(value, {"version", "python", "python_home", "python_version", "import_roots",
        "software_files_file", "software_files_ref"}, "/software")
    require(value["version"] == SOFTWARE_VERSION and _text(value["python_version"]), field="/software")
    file_pin(value["python"])
    file_pin(value["software_files_file"])
    absolute_path(value["python_home"])
    require(value["software_files_ref"] == "artifact_" + value["software_files_file"]["sha256"], field="/software/software_files_ref")
    roots = value["import_roots"]
    require(type(roots) is list and bool(roots) and len(set(roots)) == len(roots), field="/software/import_roots")
    for root in roots:
        absolute_path(root)


def _policy(value):
    closed(value, {"memory_bytes", "scratch_bytes", "wall_seconds"}, "/policy")
    require(all(type(value[k]) is int and value[k] > 0 for k in ("memory_bytes", "scratch_bytes")), field="/policy")
    wall = value["wall_seconds"]
    require(wall is None or type(wall) in (int, float) and wall > 0, field="/policy/wall_seconds")


def _selection(value):
    closed(value, {"operation", "mode", "driver_request", "request_file"}, "/selection")
    require(value["operation"] in OPERATIONS and value["mode"] in ("native", "saved_sheet"), field="/selection")
    file_pin(value["request_file"])
    request = value["driver_request"]
    operation = private._request(request)
    require(operation == value["operation"] and request["mode"] == value["mode"], field="/selection/driver_request")
    if value["mode"] == "native":
        version = request["selection"]["version"]
        allowed = (("molecular_sequence_request_v3",) if operation == "analyze_protease_kinetics" else
            ("molecular_sequence_request_v2",) if operation in OPERATIONS[2:4] else
            ("molecular_sequence_request_v1", "molecular_sequence_request_v2"))
        require(version in allowed, field="/selection/driver_request/selection/version")


def selected_payload_sha256(*, selection, software, policy, selected_environment):
    """Hash independent selected data, never its enclosing job/identity hashes."""
    _selection(selection)
    _software(software)
    _policy(policy)
    environment(selected_environment)
    return digest({"version": PAYLOAD_VERSION, "selection": selection, "software": software,
        "policy": policy, "selected_environment": selected_environment})


def _requested_argv(software, payload_sha256):
    return [software["python"]["path"], "-B", "-m", ADAPTER_MODULE, "--plan", PLAN_FILENAME,
        "--selected-payload-sha256", payload_sha256]


def build_molecular_sequence_selected_plan(*, identity, requested_job, selection, software, policy, selected_environment):
    payload = selected_payload_sha256(selection=selection, software=software, policy=policy,
        selected_environment=selected_environment)
    value = {"version": PLAN_VERSION, "identity": deepcopy(identity), "requested_job": deepcopy(requested_job),
        "selection": deepcopy(selection), "software": deepcopy(software), "policy": deepcopy(policy),
        "selected_environment": deepcopy(selected_environment), "selected_payload_sha256": payload,
        "attempt_directory": str(absolute_path(identity["execution_id"]).parent / ATTEMPT_DIRECTORY)}
    return validate_molecular_sequence_selected_plan(value, expected_payload_sha256=payload)


def validate_molecular_sequence_selected_plan(value, *, expected_payload_sha256):
    canonical(value)
    closed(value, PLAN_FIELDS)
    require(value["version"] == PLAN_VERSION and _sha(expected_payload_sha256), field="/version")
    payload = selected_payload_sha256(**{k: value[k] for k in
        ("selection", "software", "policy", "selected_environment")})
    require(payload == expected_payload_sha256 == value["selected_payload_sha256"], field="/selected_payload_sha256")
    identity, job = value["identity"], value["requested_job"]
    closed(identity, IDENTITY_FIELDS, "/identity")
    require(all(_text(v) for v in identity.values()) and all(_sha(identity[k]) for k in
        ("assignment_sha256", "requested_job_sha256", "attempt_id")), field="/identity")
    closed(job, {"argv", "environment"}, "/requested_job")
    environment(job["environment"])
    require(job["argv"] == _requested_argv(value["software"], payload)
        and job["environment"] == value["selected_environment"] and identity["requested_job_sha256"] == digest(job), field="/requested_job")
    execution = absolute_path(identity["execution_id"])
    require(execution.name == "native.json" and execution.parent.name == digest(identity["operation_key"])
        == identity["attempt_id"] and execution.parent.parent.name == digest({"run": identity["run_id"], "episode": identity["episode_id"]})
        and execution.parent.parent.parent.name == ".episode-operations", field="/identity/execution_id")
    attempt = absolute_path(value["attempt_directory"])
    require(attempt == execution.parent / ATTEMPT_DIRECTORY, field="/attempt_directory")
    require(value["selected_environment"].get("PYTHONHOME") == value["software"]["python_home"]
        and value["selected_environment"].get("PYTHONPATH") == ":".join(value["software"]["import_roots"])
        and value["selected_environment"].get("PYTHONDONTWRITEBYTECODE") == "1"
        and value["selected_environment"].get("PYTHONNOUSERSITE") == "1", field="/selected_environment")
    request = value["selection"]["driver_request"]
    if request["mode"] == "native":
        deployment = request["selection"]["deployment"]
        require(deployment["runtime"]["executable"] == value["software"]["python"]
            and deployment["runtime"]["home"] == value["software"]["python_home"], field="/selection/driver_request/selection/deployment/runtime")
        if value["selection"]["operation"] == "analyze_protease_kinetics":
            selected = request["selection"]
            output = attempt / OUTPUT_DIRECTORY
            require(absolute_path(selected["output_workspace"]) == output
                and absolute_path(selected["arguments"]["output_dir"]).is_relative_to(output), field="/selection/driver_request/selection/output_workspace")
            prefix = selected["arguments"]["output_prefix"]
            require(type(prefix) is str and prefix and prefix not in (".", "..")
                and not any(c in prefix for c in "/\\\0\n\r"), field="/selection/driver_request/selection/arguments/output_prefix")
            for key, item in selected["environment"].items():
                require(value["selected_environment"].get(key) == item, field="/selected_environment/" + key)
    return deepcopy(value)


def molecular_sequence_adapter_argv(plan):
    plan = validate_molecular_sequence_selected_plan(plan, expected_payload_sha256=plan["selected_payload_sha256"])
    args = deepcopy(plan["requested_job"]["argv"])
    args[args.index("--plan") + 1] = str(absolute_path(plan["identity"]["execution_id"]).parent / PLAN_FILENAME)
    return args


def molecular_sequence_private_driver_argv(plan, *, retained_request_file):
    file_pin(retained_request_file)
    selected = plan["selection"]["request_file"]
    require(all(retained_request_file[k] == selected[k] for k in ("sha256", "size_bytes")), field="/retained_request_file")
    return [plan["software"]["python"]["path"], "-B", "-m", "gene_annotation_episode.molecular_sequence_driver",
        "--request-file", retained_request_file["path"], "--request-sha256", selected["sha256"],
        "--request-size-bytes", str(selected["size_bytes"]), "--output-directory", str(absolute_path(plan["attempt_directory"]) / OUTPUT_DIRECTORY)]


def expected_output_roles(plan):
    return (*BASE_ROLES, *NATIVE_ROLES) if plan["selection"]["operation"] == "analyze_protease_kinetics" \
        and plan["selection"]["mode"] == "native" else BASE_ROLES


def output_specifications(plan):
    """One exact path/format mapping; no native prose supplies a destination."""
    root = absolute_path(plan["attempt_directory"])
    specifications = {"private_stdout": ("private.stdout", "text"), "private_stderr": ("private.stderr", "text"),
        **{role: (str(PurePosixPath(OUTPUT_DIRECTORY) / (role + ".json")), "json")
            for role in ("declaration", "capture", "sheet", "components")}}
    if "native_results" in expected_output_roles(plan):
        arguments = plan["selection"]["driver_request"]["selection"]["arguments"]
        native_output = absolute_path(arguments["output_dir"])
        require(native_output.is_relative_to(root / OUTPUT_DIRECTORY), field="/native_output")
        prefix = arguments["output_prefix"]
        specifications.update(native_results=(str((native_output / (prefix + "_results.txt")).relative_to(root)), "text"),
            native_plot=(str((native_output / (prefix + "_mm_plot.png")).relative_to(root)), "png"))
    return specifications


def output_comparison(observed_state, observed, declared):
    if declared is None:
        return "not_declared"
    if observed is None:
        return "matches" if declared["state"] == "absent" and observed_state == "absent" else "unavailable"
    return "matches" if declared["state"] == "present" and all(
        observed[key] == declared[key] for key in ("sha256", "size_bytes")) else "mismatch"


def failure(code, stage, *, role=None, error=None):
    value = {"stage": stage, "code": code, "file_role": role,
        "exception_type": None if error is None else type(error).__module__ + "." + type(error).__name__,
        "message": None if error is None else str(error)}
    return validate_failure(value)


def validate_failure(value):
    closed(value, {"stage", "code", "file_role", "exception_type", "message"})
    require(value["stage"] in STAGES and value["code"] in FAILURE_CODES)
    require(value["file_role"] is None or value["file_role"] in (*BASE_ROLES, *NATIVE_ROLES))
    require(all(value[k] is None or type(value[k]) is str for k in ("exception_type", "message")))
    return deepcopy(value)


def _realization(value, *, selected, relative, use, root):
    if value is None:
        return
    closed(value, {"selected", "retained_relative_path", "observed", "byte_identity_matches_selected", "content_changed", "use"})
    require(value["selected"] == selected and value["retained_relative_path"] == relative
        and value["content_changed"] is False and value["use"] == use)
    observed = file_pin(value["observed"])
    require(observed["path"] == str(root / relative) and type(value["byte_identity_matches_selected"]) is bool
        and value["byte_identity_matches_selected"] == all(observed[k] == selected[k] for k in ("sha256", "size_bytes")))


def validate_molecular_sequence_attempt_bundle(value, *, plan):
    canonical(value)
    closed(value, BUNDLE_FIELDS)
    require(value["version"] == BUNDLE_VERSION and value["sealed"] is True and value["plan_sha256"] == digest(plan)
        and value["identity"] == plan["identity"] and value["selected_payload_sha256"] == plan["selected_payload_sha256"])
    root = absolute_path(plan["attempt_directory"])
    retained = value["retained_inputs"]
    closed(retained, {"plan_file", "request", "software_manifest"})
    require(file_pin(retained["plan_file"])["path"] == str(root / OWNER_FILENAME))
    _realization(retained["request"], selected=plan["selection"]["request_file"], relative=REQUEST_RELATIVE,
        use="private_cli_request", root=root)
    _realization(retained["software_manifest"], selected=plan["software"]["software_files_file"], relative=MANIFEST_RELATIVE,
        use="software_manifest_evidence", root=root)
    require(value["selected_request_file"] == plan["selection"]["request_file"])
    expected_observed = None if retained["request"] is None else {
        **retained["request"]["observed"], "path": plan["selection"]["request_file"]["path"]}
    require(value["observed_request_file"] == expected_observed)
    require(value["private_asserted_attempt_identity"] == plan["selection"]["driver_request"]["attempt_identity"])
    require(value["adapter_argv"] == molecular_sequence_adapter_argv(plan) and value["cwd"] == str(root.parent)
        and value["selected_environment"] == value["realized_environment"] == plan["selected_environment"])
    invocation = value["invocation"]
    closed(invocation, {"launch_attempt_count", "invocation_count", "pid", "returncode", "started_at", "finished_at", "process_exit_observed"})
    require(all(type(invocation[k]) is int and invocation[k] in (0, 1) for k in ("launch_attempt_count", "invocation_count"))
        and invocation["invocation_count"] <= invocation["launch_attempt_count"] and type(invocation["process_exit_observed"]) is bool)
    require((invocation["pid"] is None) == (invocation["invocation_count"] == 0))
    require(invocation["pid"] is None or type(invocation["pid"]) is int and invocation["pid"] > 0)
    require((invocation["returncode"] is not None) == invocation["process_exit_observed"]
        and (invocation["returncode"] is None or type(invocation["returncode"]) is int))
    require(not invocation["process_exit_observed"] or invocation["invocation_count"] == 1)
    require(all(invocation[k] is None or _text(invocation[k]) for k in ("started_at", "finished_at")))
    require((invocation["started_at"] is not None) == bool(invocation["launch_attempt_count"])
        and (invocation["finished_at"] is not None) == invocation["process_exit_observed"])
    if invocation["launch_attempt_count"]:
        require(retained["request"] is not None and retained["request"]["byte_identity_matches_selected"] is True
            and retained["software_manifest"] is not None and retained["software_manifest"]["byte_identity_matches_selected"] is True)
        require(value["private_driver_argv"] == molecular_sequence_private_driver_argv(plan, retained_request_file=retained["request"]["observed"]))
    else:
        require(value["private_driver_argv"] is None)
    verification = value["software_verification"]
    closed(verification, {"before", "after", "adapter_imported_files", "inner_complete_import_closure_observed", "failures"})
    require(verification["before"] in ("not_checked", "verified", "conflict")
        and verification["after"] in ("not_checked", "verified", "conflict")
        and verification["inner_complete_import_closure_observed"] is False and type(verification["adapter_imported_files"]) is list)
    require(not invocation["launch_attempt_count"] or verification["before"] == "verified")
    for row in verification["adapter_imported_files"]:
        closed(row, {"module", "file"})
        require(_text(row["module"]))
        file_pin(row["file"])
    for item in verification["failures"]:
        validate_failure(item)
    rows = value["files"]
    require(type(rows) is list and [row.get("role") for row in rows] == list(expected_output_roles(plan)))
    specifications = output_specifications(plan)
    for row in rows:
        closed(row, {"role", "relative_path", "format", "observed_state", "observed", "declared", "comparison", "failure"})
        require(row["format"] in ("json", "text", "png") and row["observed_state"] in ("present", "absent", "unavailable")
            and row["comparison"] in ("matches", "mismatch", "unavailable", "not_declared"))
        require((row["relative_path"], row["format"]) == specifications[row["role"]])
        relative = PurePosixPath(row["relative_path"])
        require(not relative.is_absolute() and ".." not in relative.parts and str(relative) == row["relative_path"])
        require((row["observed"] is not None) == (row["observed_state"] == "present"))
        if row["observed"] is not None:
            require(file_pin(row["observed"])["path"] == str(root / relative))
        if row["declared"] is not None:
            declaration = row["declared"]
            closed(declaration, {"relative_path", "format", "state", "sha256", "size_bytes"})
            require(declaration["state"] in ("present", "absent") and declaration["format"] == row["format"]
                and str(PurePosixPath(OUTPUT_DIRECTORY) / declaration["relative_path"]) == row["relative_path"])
            if declaration["state"] == "present":
                require(_sha(declaration["sha256"]) and type(declaration["size_bytes"]) is int and declaration["size_bytes"] >= 0)
            else:
                require(declaration["sha256"] is None and declaration["size_bytes"] is None)
        require(row["comparison"] == output_comparison(row["observed_state"], row["observed"], row["declared"]))
        if row["failure"] is not None:
            validate_failure(row["failure"])
    require(type(value["failures"]) is list)
    for item in value["failures"]:
        validate_failure(item)
    return deepcopy(value)
