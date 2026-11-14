"""Closed supplied-data masking jobs and one-command compilation.

The pure core owns Operation and every native parameter definition. These
contracts add custody and paths, never masking calculations or native defaults.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator

from .domain import ContractError
from .native_blast_contracts import finite_json_copy, native_blast_digest
from .sequence_masking_contracts import (
    sequence_masking_operation_schema, validate_sequence_masking_record,
)

MODES = (("dustmasker", "mask"), ("segmasker", "mask"),
         ("windowmasker", "mask"), ("windowmasker", "create_counts"),
         ("convert2blastmask", "convert_mask"))
PREFIX = "native_blast_masking_"
JOB_VERSION = PREFIX + "job_v1"
PLAN_VERSION = PREFIX + "run_plan_v1"
BUNDLE_VERSION = PREFIX + "bundle_v1"
OWNER_NAME = ".native-blast-masking-owner.json"
ATTEMPT_NAME = "blast-masking-attempt"
PLAN_NAME = "blast-masking-plan.json"
RESERVED_ENVIRONMENT = frozenset({"TMPDIR", "TMP", "TEMP", "XDG_CACHE_HOME"})
_STR = {"type": "string", "minLength": 1, "pattern": r"^[^\u0000]+$"}
_NULL_STR = {"anyOf": [_STR, {"type": "null"}]}
_SHA = {"type": "string", "pattern": r"^[0-9a-f]{64}$"}
_ABS = {"type": "string", "pattern": r"^/[^\u0000\r\n]+$"}
_UINT = {"type": "integer", "minimum": 0}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


SOFTWARE_SCHEMA = _object({"executable": _ABS, "sha256": _SHA, "engine_version": _NULL_STR})
_STATISTICS_BINDING_SCHEMA = _object({
    "kind": {"enum": ["generated", "supplied"]}, "statistics_occurrence_id": _STR,
    "reference_occurrence_ids": {"type": "array", "uniqueItems": True, "items": _STR},
    "producer_source_ref": _NULL_STR, "producer_attempt_id": _NULL_STR,
    "provenance": {"enum": ["authenticated_generation", "caller_declared", "unknown"]}})


def native_blast_masking_job_schema(*, program, mode):
    operation = sequence_masking_operation_schema(program=program, mode=mode)
    output_formats = ([*operation["properties"]["output_format"]["enum"], "text"]
        if mode == "convert_mask" else ["interval", "fasta", "ascii_statistics", "text"])
    return _object({"version": {"const": JOB_VERSION},
        "operation": operation,
        "software": SOFTWARE_SCHEMA,
        "environment": {"type": "object", "additionalProperties": {"type": "string"}},
        "operands": {"type": "array", "minItems": 1, "maxItems": 2, "items": _object({
            "role": {"enum": ["sequences", "reference_sequences", "statistics"]},
            "ordinal": {"type": "integer", "const": 0}, "path": _ABS,
            "format": {"enum": ["fasta", "ascii_statistics"]}, "sha256": _SHA,
            "size_bytes": _UINT, "artifact_ref": _NULL_STR})},
        "operand_bindings": {"type": "array", "items": _object({
            "operand_role": {"enum": ["sequences", "reference_sequences"]},
            "operand_ordinal": {"type": "integer", "const": 0},
            "record_ordinal": _UINT, "source_record_ref": _NULL_STR})},
        "statistics_binding": {"anyOf": [_STATISTICS_BINDING_SCHEMA, {"type": "null"}]},
        "outputs": {"type": "array", "minItems": 3, "maxItems": 3, "items": _object({
            "role": {"enum": ["mask", "statistics", "stdout", "stderr"]},
            "format": {"enum": output_formats},
            "relative_path": _STR})}})


NATIVE_BLAST_MASKING_JOB_SCHEMA = {"oneOf": [native_blast_masking_job_schema(
    program=p, mode=m) for p, m in MODES]}
NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA = _object({
    "argv": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": r"^[^\u0000]*$"}},
    "environment": {"type": "object", "additionalProperties": {"type": "string"}},
    "native_blast_masking": NATIVE_BLAST_MASKING_JOB_SCHEMA})


def _error(code):
    raise ContractError(PREFIX + code)


def _schema(value, schema):
    if next(Draft202012Validator(schema).iter_errors(value), None) is not None:
        _error("schema_mismatch")


def _path(value, *, absolute=False):
    if (type(value) is not str or not value or any(c in value for c in "\0\r\n\\")
            or value.startswith("//") or ".." in value.split("/") or value in {".", "/"}):
        _error("normalized_path_required")
    path = PurePosixPath(value)
    if path.is_absolute() != absolute or str(path) != value:
        _error("normalized_path_required")
    return path


def _output_path(value):
    path = _path(value)
    if path.parts[0] in {"inputs", "tmp", "cache", "bundle.json", OWNER_NAME, PLAN_NAME,
            "native.json", "invoke.json"} or path.parts[0].startswith("."):
        _error("reserved_output_path")
    return path


def _sha(value, *, nullable=False):
    if value is None and nullable:
        return
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _error("digest_invalid")


def _pair(row, prefix=""):
    size, sha = row[prefix + "size_bytes"], row[prefix + "sha256"]
    if size is None and sha is None:
        return None, None
    if type(size) is not int or size < 0:
        _error("measurement_pair_invalid")
    _sha(sha)
    return size, sha


def validate_native_blast_masking_job(value):
    job = finite_json_copy(value)
    _schema(job, NATIVE_BLAST_MASKING_JOB_SCHEMA)
    op = validate_sequence_masking_record("Operation", job["operation"])
    _path(job["software"]["executable"], absolute=True)
    if op["engine_version"] != job["software"]["engine_version"]:
        _error("software_version_conflict")
    for key, value in job["environment"].items():
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is None or "\0" in value:
            _error("environment_invalid")
        if key in RESERVED_ENVIRONMENT:
            _error("reserved_environment")
    expected = ({"reference_sequences"} if op["mode"] == "create_counts" else
        {"sequences", "statistics"} if op["program"] == "windowmasker" else {"sequences"})
    operands = {}
    for row in job["operands"]:
        if (row["role"] in operands or type(row["ordinal"]) is not int
                or type(row["size_bytes"]) is not int):
            _error("operand_identity_invalid")
        operands[row["role"]] = row
        _path(row["path"], absolute=True)
        if row["format"] != ("ascii_statistics" if row["role"] == "statistics" else "fasta"):
            _error("operand_format_conflict")
    if set(operands) != expected:
        _error("operand_roles_conflict")
    seen = set()
    for row in job["operand_bindings"]:
        key = row["operand_role"], row["record_ordinal"]
        if (key in seen or row["operand_role"] not in expected or row["operand_role"] == "statistics"
                or type(row["operand_ordinal"]) is not int or type(row["record_ordinal"]) is not int):
            _error("operand_record_binding_conflict")
        seen.add(key)
    binding = job["statistics_binding"]
    if (binding is not None) != ("statistics" in operands):
        _error("statistics_binding_required_or_forbidden")
    if binding is not None:
        validate_sequence_masking_record("StatisticsBinding", binding)
    primary = "statistics" if op["mode"] == "create_counts" else "mask"
    roles, paths = set(), []
    for row in job["outputs"]:
        if row["role"] in roles:
            _error("duplicate_output_role")
        roles.add(row["role"])
        paths.append(_output_path(row["relative_path"]))
        if row["format"] != ("text" if row["role"] in {"stdout", "stderr"} else op["output_format"]):
            _error("output_format_conflict")
    if roles != {primary, "stdout", "stderr"}:
        _error("one_selected_output_required")
    for i, path in enumerate(paths):
        if any(path == other or path in other.parents or other in path.parents for other in paths[i + 1:]):
            _error("output_path_overlap")
    return job


def compile_native_blast_masking_job(job, *, input_paths, output_directory):
    job = validate_native_blast_masking_job(job)
    roles = {r["role"] for r in job["operands"]}
    if type(input_paths) is not dict or set(input_paths) != roles:
        _error("complete_input_path_mapping_required")
    for path in input_paths.values():
        _path(path, absolute=True)
    root = PurePosixPath(".") if output_directory == "." else _path(output_directory, absolute=True)
    for row in job["outputs"]:
        output = root / row["relative_path"]
        if str(output) in set(input_paths.values()) | {r["path"] for r in job["operands"]} | {job["software"]["executable"]}:
            _error("output_aliases_input_or_software")
    op = job["operation"]
    argv = [job["software"]["executable"]]
    if op["mode"] == "create_counts":
        argv += ["-mk_counts", "-in", input_paths["reference_sequences"], "-infmt", "fasta",
                 "-sformat", "ascii", "-fa_list", "false"]
    elif op["mode"] == "convert_mask":
        # Conversion reads the supplied lowercase mask; it runs no detector
        # and accepts neither the maskers' -infmt nor a molecule flag.
        argv += ["-in", input_paths["sequences"], "-outfmt", op["output_format"]]
        if op["parse_seqids"]:
            argv.append("-parse_seqids")
    else:
        if op["program"] == "windowmasker":
            argv += ["-ustat", input_paths["statistics"]]
        argv += ["-in", input_paths["sequences"], "-infmt", "fasta", "-outfmt", op["output_format"]]
        if op["parse_seqids"]:
            argv.append("-parse_seqids")
        if op["masking_style"] == "hard":
            argv.append("-hard_masking")
    # Iterate the shared parameter schema, not JSON insertion order or a second table.
    schema = sequence_masking_operation_schema(program=op["program"], mode=op["mode"])
    for key in schema["properties"]["requested_parameters"]["properties"]:
        value = op["requested_parameters"][key]
        if value is not None:
            argv.extend(["-" + key, str(value).lower() if type(value) is bool else
                         repr(value) if type(value) is float else str(value)])
    output = next(r for r in job["outputs"] if r["role"] not in {"stdout", "stderr"})
    argv += ["-out", str(root / output["relative_path"])]
    return argv


def requested_job_from_native_blast_masking(job):
    job = validate_native_blast_masking_job(job)
    return {"argv": compile_native_blast_masking_job(job,
        input_paths={r["role"]: r["path"] for r in job["operands"]}, output_directory="."),
        "environment": job["environment"], "native_blast_masking": job}


def validate_native_blast_masking_requested_job(value):
    request = finite_json_copy(value)
    _schema(request, NATIVE_BLAST_MASKING_REQUESTED_JOB_SCHEMA)
    if native_blast_digest(request) != native_blast_digest(requested_job_from_native_blast_masking(request["native_blast_masking"])):
        _error("requested_job_compiler_mismatch")
    return request


def staged_relative(operand):
    return "inputs/" + operand["role"] + (".ascii" if operand["role"] == "statistics" else ".fa")


def masking_occurrence_id(identity, direction, role, ordinal=0):
    if direction not in {"input", "output"} or type(ordinal) is not int or ordinal != 0:
        _error("occurrence_identity_invalid")
    return "native_blast_masking:" + native_blast_digest(identity) + ":" + direction + ":" + role + ":" + str(ordinal)


def native_environment(job, directory):
    root = PurePosixPath(directory)
    return {**job["environment"], **{key: str(root / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
            "XDG_CACHE_HOME": str(root / "cache")}


def validate_native_blast_masking_plan(value):
    """Pure validation; current filesystem qualification belongs to the adapter."""
    plan = finite_json_copy(value)
    if type(plan) is not dict or set(plan) != {"version", "identity", "requested_job", "attempt_directory", "policy"} or plan["version"] != PLAN_VERSION:
        _error("run_plan_required")
    request = validate_native_blast_masking_requested_job(plan["requested_job"])
    identity = plan["identity"]
    if (type(identity) is not dict or set(identity) != {"run_id", "episode_id", "resource_id", "execution_id",
            "attempt_id", "operation_key", "requested_job_sha256"}
            or any(type(v) is not str or not v or "\0" in v for v in identity.values())
            or identity["requested_job_sha256"] != native_blast_digest(request)
            or identity["attempt_id"] != native_blast_digest(identity["operation_key"])):
        _error("plan_identity_conflict")
    root, execution = _path(plan["attempt_directory"], absolute=True), _path(identity["execution_id"], absolute=True)
    if execution.name != "native.json" or root != execution.parent / ATTEMPT_NAME:
        _error("plan_directory_conflict")
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {'memory_bytes', 'scratch_bytes'}:
        _error("explicit_policy_required")
    from .local_jobs import LocalJobPolicy
    LocalJobPolicy(**policy)
    job = request["native_blast_masking"]
    if any(_path(r["path"], absolute=True).is_relative_to(root) for r in job["operands"]) or _path(job["software"]["executable"], absolute=True).is_relative_to(root):
        _error("supplied_material_inside_attempt")
    compile_native_blast_masking_job(job, input_paths={r["role"]: str(root / staged_relative(r)) for r in job["operands"]}, output_directory=str(root))
    return plan


FAILURE_STAGES = {
    "software_unavailable": "software", "software_digest_mismatch": "software", "software_not_executable": "software",
    "input_unavailable": "inputs", "input_identity_mismatch": "inputs", "staging_scratch_limit": "inputs",
    "invalid_fasta": "preflight", "invalid_statistics": "preflight", "record_binding_outside_input": "preflight",
    "command_unavailable": "execution", "nonzero_returncode": "execution", "execution_scratch_limit": "execution",
    "immutable_input_changed": "execution", "input_final_unavailable": "execution",
    "missing_output": "outputs", "invalid_output": "outputs"}
FAILURE_CODES = frozenset(PREFIX + k for k in FAILURE_STAGES)


def producer_failure(code, role=None, input_failures=None):
    return {"stage": FAILURE_STAGES[code], "code": PREFIX + code, "role": role,
            "ordinal": 0 if role is not None else None, "diagnostic_artifact_ref": None,
            "input_failures": finite_json_copy(input_failures or [])}


def validate_preflight_failures(rows):
    if type(rows) is not list:
        _error("input_failure_rows_required")
    for row in rows:
        if (type(row) is not dict or set(row) != {"code", "record_ordinal", "line_number"}
                or type(row["code"]) is not str or re.fullmatch(r"[a-z][a-z0-9_]*", row["code"]) is None
                or row["record_ordinal"] is not None and (type(row["record_ordinal"]) is not int or row["record_ordinal"] < 0)
                or row["line_number"] is not None and (type(row["line_number"]) is not int or row["line_number"] < 1)):
            _error("input_failure_row_invalid")


def generated_statistics_binding(bundle):
    return {"kind": "generated", "statistics_occurrence_id": masking_occurrence_id(bundle["identity"], "output", "statistics"),
        "reference_occurrence_ids": [masking_occurrence_id(bundle["identity"], "input", "reference_sequences")],
        "producer_source_ref": None, "producer_attempt_id": bundle["identity"]["attempt_id"],
        "provenance": "authenticated_generation"}


def validate_original_bundle(bundle, plan):
    """One pure authority for the producer and retained-result consumers."""
    plan, bundle = validate_native_blast_masking_plan(plan), finite_json_copy(bundle)
    fields = {"version", "identity", "requested_job", "operation", "software", "realized_argv", "environment",
        "inputs", "operand_bindings", "statistics_binding", "returncode", "artifacts", "failures", "started_at", "finished_at"}
    if (type(bundle) is not dict or set(bundle) != fields or bundle["version"] != BUNDLE_VERSION
            or native_blast_digest(bundle["identity"]) != native_blast_digest(plan["identity"])
            or native_blast_digest(bundle["requested_job"]) != native_blast_digest(plan["requested_job"])):
        _error("original_bundle_identity_conflict")
    job, root = plan["requested_job"]["native_blast_masking"], PurePosixPath(plan["attempt_directory"])
    if (native_blast_digest(bundle["operation"]) != native_blast_digest(job["operation"])
            or native_blast_digest(bundle["operand_bindings"]) != native_blast_digest(job["operand_bindings"])):
        _error("original_bundle_request_conflict")
    expected_argv = compile_native_blast_masking_job(job,
        input_paths={r["role"]: str(root / staged_relative(r)) for r in job["operands"]}, output_directory=str(root))
    if bundle["realized_argv"] != expected_argv or bundle["environment"] != native_environment(job, root):
        _error("original_realized_command_conflict")
    sw = bundle["software"]
    if (type(sw) is not dict or set(sw) != {"executable", "expected_sha256", "actual_sha256", "declared_engine_version"}
            or any(sw[a] != job["software"][b] for a, b in (("executable", "executable"),
                ("expected_sha256", "sha256"), ("declared_engine_version", "engine_version")))):
        _error("bundle_software_conflict")
    _sha(sw["actual_sha256"], nullable=True)
    rc = bundle["returncode"]
    if rc is not None and type(rc) is not int:
        _error("bundle_returncode_invalid")
    try:
        dates = [datetime.fromisoformat(bundle[k]) for k in ("started_at", "finished_at")]
        if any(d.utcoffset() is None for d in dates) or dates[1] < dates[0]:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        _error("bundle_timestamp_invalid")
    input_roles, output_roles = {r["role"] for r in job["operands"]}, {r["role"] for r in job["outputs"]}
    if type(bundle["failures"]) is not list:
        _error("bundle_failures_invalid")
    for f in bundle["failures"]:
        if (type(f) is not dict or set(f) != {"stage", "code", "role", "ordinal", "diagnostic_artifact_ref", "input_failures"}
                or type(f["code"]) is not str or f["code"] not in FAILURE_CODES
                or f["stage"] != FAILURE_STAGES[f["code"][len(PREFIX):]]
                or f["diagnostic_artifact_ref"] is not None
                or f["role"] is not None and (type(f["role"]) is not str or f["role"] not in input_roles | output_roles
                    or type(f["ordinal"]) is not int or f["ordinal"] != 0)
                or f["role"] is None and f["ordinal"] is not None):
            _error("bundle_failure_shape")
        validate_preflight_failures(f["input_failures"])
        if bool(f["input_failures"]) != (f["code"] == PREFIX + "invalid_fasta"):
            _error("bundle_input_failure_context")
        if (f["stage"] in {"inputs", "preflight"} and f["role"] not in input_roles
                or f["stage"] == "outputs" and f["role"] not in output_roles
                or f["stage"] == "software" and f["role"] is not None):
            _error("bundle_failure_role")
    def has(code, role=None):
        return producer_failure(code, role) in bundle["failures"]
    prevented = any(f["stage"] in {"software", "inputs", "preflight"} for f in bundle["failures"])
    if ((rc is None and not (prevented or has("command_unavailable") or has("execution_scratch_limit")))
            or rc is not None and prevented or rc not in (0, None) and not has("nonzero_returncode")
            or has("nonzero_returncode") and rc in (0, None)
            or has("command_unavailable") and rc is not None):
        _error("bundle_execution_conflict")
    if (sw["actual_sha256"] is None and not has("software_unavailable")
            or sw["actual_sha256"] not in {None, sw["expected_sha256"]} and not has("software_digest_mismatch")
            or rc is not None and sw["actual_sha256"] != sw["expected_sha256"]):
        _error("bundle_software_measurement_conflict")
    if type(bundle["inputs"]) is not list or len(bundle["inputs"]) != len(job["operands"]):
        _error("bundle_inputs_conflict")
    for row, operand in zip(bundle["inputs"], job["operands"]):
        expected = {"role": operand["role"], "ordinal": 0, "format": operand["format"], "original_path": operand["path"],
            "relative_path": staged_relative(operand), "artifact_ref": operand["artifact_ref"],
            "expected_sha256": operand["sha256"], "expected_size_bytes": operand["size_bytes"]}
        if (type(row) is not dict or set(row) != set(expected) | {"staged_sha256", "staged_size_bytes", "final_sha256", "final_size_bytes"}
                or any(type(row[k]) is not type(v) or row[k] != v for k, v in expected.items())):
            _error("bundle_input_identity_conflict")
        staged, final = _pair(row, "staged_"), _pair(row, "final_")
        role = row["role"]
        if staged != (operand["size_bytes"], operand["sha256"]) and (rc is not None or not any(has(c, role) for c in ("input_unavailable", "input_identity_mismatch", "staging_scratch_limit"))):
            _error("bundle_input_measurement_conflict")
        if staged != final and not has("immutable_input_changed", role):
            _error("bundle_input_change_failure_required")
        if staged[0] is not None and final[0] is None and not has("input_final_unavailable", role):
            _error("bundle_input_unavailable_failure_required")
    if type(bundle["artifacts"]) is not list or len(bundle["artifacts"]) != len(job["outputs"]):
        _error("bundle_outputs_conflict")
    for row, selected in zip(bundle["artifacts"], job["outputs"]):
        if (type(row) is not dict or set(row) != set(selected) | {"ordinal", "sha256", "size_bytes"}
                or type(row["ordinal"]) is not int or row["ordinal"] != 0
                or any(row[k] != v for k, v in selected.items())):
            _error("bundle_output_identity_conflict")
        pair = _pair(row)
        if pair[0] is None and not (has("missing_output", row["role"]) or has("invalid_output", row["role"])):
            _error("bundle_output_failure_required")
        if pair[0] is not None and (has("missing_output", row["role"]) or has("invalid_output", row["role"])):
            _error("bundle_output_failure_conflict")
    expected_binding = job["statistics_binding"]
    if job["operation"]["mode"] == "create_counts" and rc == 0 and not bundle["failures"]:
        expected_binding = generated_statistics_binding(bundle)
    if native_blast_digest(bundle["statistics_binding"]) != native_blast_digest(expected_binding):
        _error("bundle_statistics_binding_conflict")
    return bundle
