"""One selected ordinary HOMER reservation and non-cancelling observation.

The authenticated caller owns the action lease and received-input authority.
This module owns no Source, receipt, grant, episode or scientific calculator.
Closed metadata validators do not inspect a current deployment or workspace.
"""
from copy import deepcopy
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys
import time

from . import native_lifecycle as native
from .acquisition import AcquisitionError
from .communication import plain
from .episode_bindings import BindingContext
from .execution_contracts import canonical, digest
from .local_jobs import LocalJobPolicy
from .molecular_measurement_tools import MolecularOperationUnpublished
from .native_file_capture import _identity
from .native_flux_balance_storage import (
    confined_file, decode_json, directory, file_pin, immutable_bytes, read_bytes,
)


OPERATION = "find_enriched_motifs_with_homer"
VARIANT = "supplied_fasta_explicit_background_old_v1"
BINDING_VERSION = "ordinary_homer_attempt_binding_v1"
PREPARED_VERSION = "ordinary_homer_prepared_v1"
EXECUTION_VERSION = "ordinary_homer_execution_v1"
PLAN_VERSION = "homer_native_plan_v1"
COMPLETION_VERSION = "homer_native_completion_v1"
MANIFEST_VERSION = "homer_native_output_manifest_v1"
BINDING_FILENAME = "homer-binding.json"
REQUEST_FILENAME = "homer-request.json"
PLAN_FILENAME = "homer-plan.json"
ATTEMPT_DIRECTORY = "homer-attempt"
STARTED_FILENAME = "homer-wrapper-started.json"
REALIZATION_FILENAME = "homer-realization.json"
COMPLETION_FILENAME = "homer-completion.json"
OUTPUT_MANIFEST_FILENAME = "homer-output-manifest.json"
WORKER_MODULE = "gene_annotation_episode.native_homer_worker"
ENVIRONMENT_SELECTION = {"version": "homer_execution_selection_v1",
    "environment_realization": "operation_scoped_tmp_and_cache_v1"}
POLICY = {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}
INPUT_ROLES = ("target_bed", "reference_fasta", "background_bed")
ROLES = ("known_results", "known_pwm", "denovo_pwm", "denovo_combined_pwm",
    "denovo_nonredundant_pwm", "sequence_table", "group_weights", "normalization_table", "native_log")
PATCH_NAMES = ("findMotifsGenome.pl", "findKnownMotifs.pl", "compareMotifs.pl", "HomerConfig.pm")
_NATIVE_PATHS = ("request", "ready", "release", "status", "result", "launcher")
_SHA = re.compile(r"[0-9a-f]{64}")
_SAFE = re.compile(r"[A-Za-z0-9_./-]+")


class HomerPreflightRejected(ValueError):
    """Fresh selected files failed verification before any reservation existed."""


def _require(condition, code):
    if not condition:
        raise ValueError("ordinary_homer_" + code)


def _closed(value, fields, code):
    _require(type(value) is dict and set(value) == set(fields), code)


def _copy(value):
    return decode_json(canonical(value).encode("utf-8"))


def _same(left, right):
    return canonical(left) == canonical(right)


def _text(value):
    return type(value) is str and bool(value) and not any(ord(c) < 32 for c in value)


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _path(value, *, absolute=True):
    _require(_text(value) and "\\" not in value, "path_invalid")
    path = PurePosixPath(value)
    _require(str(path) == value and value not in (".", "/") and ".." not in path.parts
        and path.is_absolute() == absolute, "path_invalid")
    return Path(value)


def _relative(value):
    path = _path(value, absolute=False)
    _require(_SAFE.fullmatch(value) is not None, "native_relative_path_invalid")
    return path


def _deployment_member(value):
    """A copied member name is distinct from an interpolated command path.

    The selected ELF closure contains the literal libstdc++ names. These
    members are opened/copied through confined file descriptors, not inserted
    into shell commands. Keep command/workspace/output path policy unchanged.
    """
    path = _path(value, absolute=False)
    _require(re.fullmatch(r"[A-Za-z0-9_./+\-]+", value) is not None,
        "deployment_member_path_invalid")
    return path


def _pin(value):
    _closed(value, ("path", "sha256", "size_bytes"), "file_pin_invalid")
    _path(value["path"])
    _require(_sha(value["sha256"]) and _integer(value["size_bytes"]), "file_pin_invalid")
    return value


def _raw_pin(path, raw):
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _bytes(value):
    return (canonical(value) + "\n").encode("utf-8")


def _failure(value):
    if value is not None:
        _closed(value, ("code", "phase", "diagnostic", "operational"), "failure_invalid")
        _require(_text(value["code"]) and _text(value["phase"]), "failure_invalid")
        canonical(value)
    return value


def failure_record(code, phase, error=None):
    return dict(code=code, phase=phase, diagnostic=None if error is None else
        dict(exception_type=type(error).__name__, message=str(error)), operational=None)


def validate_homer_arguments(value):
    value = _copy(value)
    _closed(value, ("window_bp", "motif_lengths", "num_motifs", "threads", "strand",
        "statistic", "normalization", "motif_set"), "arguments_fields_invalid")
    lengths = value["motif_lengths"]
    _require(_integer(value["window_bp"], 1) and type(lengths) is list and bool(lengths)
        and all(_integer(n, 1) for n in lengths) and len(set(lengths)) == len(lengths)
        and _integer(value["num_motifs"]) and _integer(value["threads"], 1)
        and value["strand"] in ("both", "forward")
        and value["statistic"] in ("binomial", "hypergeometric"), "arguments_invalid")
    norm = value["normalization"]
    _closed(norm, ("composition", "oligo_length", "max_iterations", "neutral"), "normalization_invalid")
    _require(norm["composition"] in ("gc", "cpg", "none") and _integer(norm["oligo_length"])
        and _integer(norm["max_iterations"], 1) and type(norm["neutral"]) is bool,
        "normalization_invalid")
    # A native motif-set name is a selected packaged dataset, never a path.
    _require(type(value["motif_set"]) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value["motif_set"]) is not None,
        "motif_set_invalid")
    return value


def validate_homer_software(value):
    value = _copy(value)
    _closed(value, ("version", "python", "python_home", "python_version", "import_roots",
        "software_files_file"), "software_fields_invalid")
    _require(value["version"] == "homer_native_software_v1" and _text(value["python_version"]),
        "software_invalid")
    _pin(value["python"]); _pin(value["software_files_file"]); _path(value["python_home"])
    roots = value["import_roots"]
    _require(type(roots) is list and bool(roots) and len(set(roots)) == len(roots), "import_roots_invalid")
    for path in roots:
        _path(path)
    return value


def _deployment(value):
    _closed(value, ("version", "root", "files", "system_files", "corrections"), "deployment_fields_invalid")
    _require(value["version"] == "homer_native_deployment_v1", "deployment_version_invalid")
    _path(value["root"])
    _require(type(value["files"]) is list and bool(value["files"])
        and type(value["system_files"]) is list, "deployment_files_invalid")
    paths = []
    for row in value["files"]:
        _closed(row, ("relative_path", "sha256", "size_bytes", "mode"), "deployment_file_invalid")
        path = _deployment_member(row["relative_path"])
        _require(path.parts[0] in ("deployment", "selected_runtime") and _sha(row["sha256"])
            and _integer(row["size_bytes"]) and _integer(row["mode"]) and row["mode"] <= 0o777,
            "deployment_file_invalid")
        paths.append(str(path))
    _require(len(set(paths)) == len(paths), "deployment_path_duplicate")
    required = {"deployment/bin/" + n for n in (*PATCH_NAMES, "homerTools", "homer2", "mergePeaks", "HomerSVGLogo.pm")}
    required.update(("deployment/config.txt", "selected_runtime/perl/bin/perl",
        "selected_runtime/elf/ld-linux-x86-64.so.2"))
    _require(required <= set(paths), "deployment_required_file_missing")
    for row in value["system_files"]:
        _pin(row)
    _require(len({row["path"] for row in value["system_files"]}) == len(value["system_files"]),
        "system_path_duplicate")
    _closed(value["corrections"], ("extractor_build_report", "svg_repair_record"), "correction_records_invalid")
    for row in value["corrections"].values():
        _pin(row)
    return value


def validate_homer_bindings(bindings):
    """Validate configured metadata only; never discover or select a binding."""
    bindings = _copy(bindings)
    _require(type(bindings) is list, "bindings_invalid")
    for value in bindings:
        _closed(value, ("version", "operation", "variant", "deployment", "software", "input_staging"),
            "binding_fields_invalid")
        _require(value["version"] == "homer_native_binding_v1" and value["operation"] == OPERATION
            and value["variant"] == VARIANT, "binding_variant_unsupported")
        _deployment(value["deployment"]); validate_homer_software(value["software"])
        _closed(value["input_staging"], ("mode", "max_total_bytes"), "input_staging_invalid")
        _require(value["input_staging"]["mode"] == "verified_copy"
            and _integer(value["input_staging"]["max_total_bytes"])
            and value["input_staging"]["max_total_bytes"] <= POLICY["scratch_bytes"], "input_staging_invalid")
    return bindings


def homer_motif_sets(binding):
    """Actual selected inventory names; no current directory discovery."""
    binding = validate_homer_bindings([binding])[0]
    names = []
    for row in binding["deployment"]["files"]:
        match = re.fullmatch(r"deployment/data/knownTFs/([A-Za-z0-9][A-Za-z0-9_-]*)/known\.motifs",
            row["relative_path"])
        if match and match[1] not in names:
            names.append(match[1])
    # The source's custom-FASTA auto mode explicitly resolves to all.
    if "all" in names:
        names.append("auto")
    return names


def homer_execution_schema(kind, *, binding=None):
    """The explicit scientific selection, separate from all private controls."""
    _require(kind == "Arguments", "schema_kind_invalid")
    def obj(properties):
        return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)
    integer = lambda minimum: dict(type="integer", minimum=minimum)
    motif_set = dict(type="string", pattern="^[A-Za-z0-9][A-Za-z0-9_-]*$")
    if binding is not None:
        motif_set = dict(type="string", enum=homer_motif_sets(binding))
    return obj(dict(window_bp=integer(1), motif_lengths=dict(type="array", minItems=1,
        uniqueItems=True, items=integer(1)), num_motifs=integer(0), threads=integer(1),
        strand=dict(type="string", enum=["both", "forward"]),
        statistic=dict(type="string", enum=["binomial", "hypergeometric"]),
        normalization=obj(dict(composition=dict(type="string", enum=["gc", "cpg", "none"]),
            oligo_length=integer(0), max_iterations=integer(1), neutral=dict(type="boolean"))),
        motif_set=motif_set))


def _selected(value):
    _closed(value, ("resource_id", "binding_ordinal_0based", "workspace", "binding", "environment"),
        "selection_fields_invalid")
    _require(_text(value["resource_id"]) and _integer(value["binding_ordinal_0based"])
        and _same(value["environment"], ENVIRONMENT_SELECTION), "selection_invalid")
    workspace = _path(value["workspace"])
    # HOMER's retained Perl wrappers contain unquoted internal shell operands.
    _require(_SAFE.fullmatch(str(workspace)) is not None, "native_workspace_not_shell_safe")
    validate_homer_bindings([value["binding"]])
    return value


def validate_homer_frozen_inputs(value):
    value = _copy(value)
    _closed(value, ("version", "inputs"), "frozen_inputs_fields_invalid")
    _require(value["version"] == "ordinary_homer_frozen_inputs_v1" and type(value["inputs"]) is list
        and len(value["inputs"]) == 3, "frozen_inputs_invalid")
    for row, role, fmt in zip(value["inputs"], INPUT_ROLES, ("bed", "fasta", "bed")):
        _closed(row, ("role", "selection", "file", "path"), "frozen_input_invalid")
        _closed(row["selection"], ("namespace", "reference"), "frozen_selection_invalid")
        _require(row["role"] == role and row["selection"]["namespace"] in ("artifact", "source")
            and _text(row["selection"]["reference"]), "frozen_input_invalid")
        identity = _identity(row["file"])
        _require(identity["format"] == fmt, "frozen_format_conflict")
        _path(row["path"])
    return value


def _request(value):
    _closed(value, ("version", "operation", "variant", "arguments", "frozen_inputs", "deployment", "input_staging"),
        "request_fields_invalid")
    _require(value["version"] == "homer_native_request_v1" and value["operation"] == OPERATION
        and value["variant"] == VARIANT, "request_invalid")
    validate_homer_arguments(value["arguments"]); validate_homer_frozen_inputs(value["frozen_inputs"])
    _deployment(value["deployment"])
    staging = value["input_staging"]
    _closed(staging, ("mode", "max_total_bytes"), "input_staging_invalid")
    size = sum(row["file"]["size_bytes"] for row in value["frozen_inputs"]["inputs"])
    _require(staging["mode"] == "verified_copy" and _integer(staging["max_total_bytes"])
        and size <= staging["max_total_bytes"] <= POLICY["scratch_bytes"], "input_copy_budget_exceeded")
    motif_set = value["arguments"]["motif_set"]
    motif_set = "all" if motif_set == "auto" else motif_set
    _require("deployment/data/knownTFs/" + motif_set + "/known.motifs" in
        {row["relative_path"] for row in value["deployment"]["files"]}, "selected_motif_set_unavailable")
    return value


def _environment(software, root):
    return {"PYTHONHOME": software["python_home"], "PYTHONPATH": ":".join(software["import_roots"]),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        "PYTHONPYCACHEPREFIX": str(root / "cache" / "pycache"), "TMPDIR": str(root),
        "TMP": str(root), "TEMP": str(root), "HOME": str(root / "home"),
        "XDG_CACHE_HOME": str(root / "cache")}


def _payload(plan):
    identity = {key: value for key, value in plan["identity"].items() if key != "requested_job_sha256"}
    return digest(dict(identity=identity, request=plan["request"], request_file=plan["request_file"],
        software=plan["software"], policy=plan["policy"], selected_environment=plan["selected_environment"],
        operation_directory=plan["operation_directory"], attempt_directory=plan["attempt_directory"]))


def homer_adapter_argv(plan):
    return [plan["software"]["python"]["path"], "-B", "-S", "-m", WORKER_MODULE,
        "--native-plan", PLAN_FILENAME, "--selected-payload-sha256", plan["selected_payload_sha256"]]


def validate_homer_plan(value):
    value = _copy(value)
    _closed(value, ("version", "identity", "request", "request_file", "software", "policy",
        "selected_environment", "selected_payload_sha256", "requested_job", "operation_directory", "attempt_directory"),
        "plan_fields_invalid")
    _require(value["version"] == PLAN_VERSION and _same(value["policy"], POLICY), "plan_invalid")
    _request(value["request"]); validate_homer_software(value["software"]); _pin(value["request_file"])
    identity = value["identity"]
    _closed(identity, ("run_id", "episode_id", "resource_id", "binding_ordinal_0based", "operation_key",
        "execution_id", "attempt_id", "request_sha256", "assignment_sha256", "requested_job_sha256"), "identity_fields_invalid")
    _require(all(_text(identity[k]) for k in ("run_id", "episode_id", "resource_id", "operation_key"))
        and _integer(identity["binding_ordinal_0based"])
        and all(_sha(identity[k]) for k in ("attempt_id", "request_sha256", "assignment_sha256", "requested_job_sha256")),
        "identity_invalid")
    root = _path(value["operation_directory"])
    _require(_SAFE.fullmatch(str(root)) is not None and value["attempt_directory"] == str(root / ATTEMPT_DIRECTORY)
        and identity["execution_id"] == str(root / "native.json")
        and identity["attempt_id"] == digest(identity["operation_key"])
        and value["request_file"] == _raw_pin(root / REQUEST_FILENAME, _bytes(value["request"]))
        and _same(value["selected_environment"], _environment(value["software"], root))
        and value["selected_payload_sha256"] == _payload(value), "plan_selection_conflict")
    expected = dict(argv=homer_adapter_argv(value), environment=value["selected_environment"])
    _require(_same(value["requested_job"], expected) and identity["requested_job_sha256"] == digest(expected),
        "plan_job_conflict")
    # The budget includes runtime copies and private controls, not just BED/FASTA.
    staged = sum(row["size_bytes"] for row in value["request"]["deployment"]["files"])
    staged += sum(row["file"]["size_bytes"] for row in value["request"]["frozen_inputs"]["inputs"])
    _require(staged + len(_bytes(value)) + len(_bytes(value["request"])) < POLICY["scratch_bytes"],
        "staged_runtime_and_inputs_exceed_scratch")
    return value


def homer_native_invocation(plan):
    """Literal wrapper argv/environment; no input resolution or filesystem work."""
    root = Path(plan["attempt_directory"])
    dep, runtime = root / "deployment", root / "selected_runtime"
    args = plan["request"]["arguments"]
    environment = dict(PATH=":".join(str(p) for p in (runtime / "perl/bin", dep / "bin", runtime / "coreutils/bin")),
        LC_ALL="C.UTF-8", LD_LIBRARY_PATH=str(runtime / "elf"), LD_BIND_NOW="1",
        PERL5LIB=str(root / "runtime_control"), PERL5OPT="-MHomerSelectedRuntime",
        HOME=str(root / "home"), TMPDIR=str(root / "tmp"), TMP=str(root / "tmp"), TEMP=str(root / "tmp"),
        XDG_CACHE_HOME=str(root / "cache"))
    argv = [str(runtime / "elf/ld-linux-x86-64.so.2"), str(runtime / "perl/bin/perl"),
        str(dep / "bin/findMotifsGenome.pl"), str(root / "inputs/target.bed"),
        str(root / "inputs/reference.fa"), str(root / "native"), "-bg", str(root / "inputs/background.bed"),
        "-size", str(args["window_bp"]), "-len", ",".join(map(str, args["motif_lengths"])),
        "-S", str(args["num_motifs"]), "-p", str(args["threads"]), "-useOldBg",
        {"gc": "-gc", "cpg": "-cpg", "none": "-noweight"}[args["normalization"]["composition"]],
        "-nlen", str(args["normalization"]["oligo_length"]), "-nmax", str(args["normalization"]["max_iterations"]),
        "-homer2", "-mset", args["motif_set"], "-keepFiles", "-preparsedDir", str(root / "preparsed")]
    if args["strand"] == "forward": argv.append("-norevopp")
    if args["statistic"] == "hypergeometric": argv.append("-h")
    if args["normalization"]["neutral"]: argv.append("-neutral")
    return dict(argv=argv, cwd=str(root / "work"), environment=environment)


def _execution(value):
    _closed(value, ("wrapper_returncode", "wrapper_outcome", "known_outcome", "denovo_outcome"), "execution_outcomes_invalid")
    _require(value["wrapper_returncode"] is None or type(value["wrapper_returncode"]) is int,
        "wrapper_returncode_invalid")
    _require(all(value[k] in ("succeeded", "failed", "not_run", "unknown")
        for k in ("wrapper_outcome", "known_outcome", "denovo_outcome")), "execution_outcomes_invalid")
    return value


def _metadata_execution(completion, manifest):
    if manifest is not None:
        return deepcopy(manifest["execution"])
    value = dict(wrapper_returncode=None, wrapper_outcome="unknown", known_outcome="unknown", denovo_outcome="unknown")
    if completion is not None:
        wrapper = completion["wrapper"]
        value.update(wrapper_returncode=wrapper["returncode"], wrapper_outcome=
            "succeeded" if wrapper["outcome"] == "returned" and wrapper["returncode"] == 0 else
            "failed" if wrapper["outcome"] == "returned" else "not_run" if wrapper["outcome"] == "not_started" else "unknown")
    return value


def validate_homer_completion(value, *, plan):
    value = _copy(value)
    _closed(value, ("version", "identity", "request_file", "selected_payload_sha256", "wrapper_started_file",
        "realization_file", "wrapper", "stdout", "stderr", "failure"), "completion_fields_invalid")
    _require(value["version"] == COMPLETION_VERSION and _same(value["identity"], plan["identity"])
        and _same(value["request_file"], plan["request_file"])
        and value["selected_payload_sha256"] == plan["selected_payload_sha256"], "completion_plan_conflict")
    root = Path(plan["attempt_directory"])
    for key, name in (("wrapper_started_file", STARTED_FILENAME), ("realization_file", REALIZATION_FILENAME),
            ("stdout", "stdout.log"), ("stderr", "stderr.log")):
        if value[key] is not None:
            _pin(value[key]); _require(value[key]["path"] == str(root / name), "completion_path_conflict")
    wrapper = value["wrapper"]
    _closed(wrapper, ("argv", "cwd", "environment", "started_at", "finished_at", "returncode", "outcome"),
        "wrapper_fields_invalid")
    selected = homer_native_invocation(plan)
    _require(all(_same(wrapper[k], selected[k]) for k in selected)
        and wrapper["outcome"] in ("returned", "not_started", "unconfirmed")
        and (wrapper["returncode"] is None or type(wrapper["returncode"]) is int)
        and all(wrapper[k] is None or _text(wrapper[k]) for k in ("started_at", "finished_at")), "wrapper_invalid")
    if wrapper["outcome"] == "returned":
        _require(type(wrapper["returncode"]) is int and value["wrapper_started_file"] is not None
            and value["realization_file"] is not None
            and wrapper["started_at"] is not None and wrapper["finished_at"] is not None, "returned_completion_incomplete")
    else:
        _require(wrapper["returncode"] is None, "unconfirmed_returncode_conflict")
    _failure(value["failure"])
    return value


def homer_output_specifications(plan):
    rows = [("known_results", "native/knownResults.txt", "homer_known_results_tsv")]
    rows += [("denovo_pwm", "native/homerMotifs.motifs" + str(n), "homer_native_pwm")
        for n in plan["request"]["arguments"]["motif_lengths"]]
    rows += [("denovo_combined_pwm", "native/homerMotifs.all.motifs", "homer_native_pwm"),
        ("sequence_table", "native/seq.tsv", "homer_sequence_tsv"),
        ("group_weights", "native/group.adj", "homer_group_weights_tsv"),
        ("normalization_table", "native/seq.autonorm.tsv", "homer_normalization_tsv"),
        ("native_log", "stdout.log", "native_stdout"), ("native_log", "stderr.log", "native_stderr")]
    return [dict(role=role, native_relative_path=path, format=fmt) for role, path, fmt in rows]


def validate_homer_output_manifest(value, *, plan, completion=None):
    value = _copy(value)
    _closed(value, ("version", "identity", "selected_payload_sha256", "completion_file", "files", "other_files",
        "failures", "execution"), "manifest_fields_invalid")
    _require(value["version"] == MANIFEST_VERSION and _same(value["identity"], plan["identity"])
        and value["selected_payload_sha256"] == plan["selected_payload_sha256"], "manifest_plan_conflict")
    _pin(value["completion_file"])
    root = Path(plan["attempt_directory"])
    _require(value["completion_file"]["path"] == str(root / COMPLETION_FILENAME), "manifest_completion_path_conflict")
    if completion is not None:
        _require(value["completion_file"] == _raw_pin(root / COMPLETION_FILENAME, _bytes(completion)),
            "manifest_completion_identity_conflict")
    _require(type(value["files"]) is list and type(value["other_files"]) is list
        and type(value["failures"]) is list, "manifest_lists_invalid")
    expected = {r["native_relative_path"]: r for r in homer_output_specifications(plan)}
    paths = []
    for row in value["files"]:
        _closed(row, ("role", "native_relative_path", "format", "observed_state", "sha256", "size_bytes", "failure"),
            "output_record_fields_invalid")
        path = row["native_relative_path"]; _relative(path)
        _require(row["role"] in ROLES and _text(row["format"]), "output_role_invalid")
        if row["role"] == "known_pwm":
            _require(re.fullmatch(r"native/knownResults/known[1-9][0-9]*\.motif", path) is not None
                and row["format"] == "homer_native_pwm", "known_pwm_path_invalid")
        elif row["role"] == "denovo_nonredundant_pwm":
            _require(re.fullmatch(r"native/homerResults/motif[1-9][0-9]*\.motif", path) is not None
                and row["format"] == "homer_native_pwm", "final_pwm_path_invalid")
        else:
            _require(path in expected and all(row[k] == expected[path][k] for k in ("role", "format")),
                "output_path_role_conflict")
        _require(row["observed_state"] in ("present", "absent", "unavailable"), "output_state_invalid")
        if row["observed_state"] == "present":
            _require(_sha(row["sha256"]) and _integer(row["size_bytes"]) and row["failure"] is None,
                "present_output_identity_invalid")
        else:
            _require(row["sha256"] is None and row["size_bytes"] is None, "missing_output_identity_conflict")
            _require(row["observed_state"] != "unavailable" or row["failure"] is not None,
                "unavailable_output_failure_required")
        _failure(row["failure"]); paths.append(path)
    _require(set(expected) <= set(paths), "expected_output_record_missing")
    for role, expression in (("known_pwm", r"known([1-9][0-9]*)\.motif"),
            ("denovo_nonredundant_pwm", r"motif([1-9][0-9]*)\.motif")):
        ranks = [int(re.fullmatch(expression, Path(row["native_relative_path"]).name)[1])
            for row in value["files"] if row["role"] == role]
        _require(ranks == sorted(ranks), "native_output_rank_order_conflict")
    for row in value["other_files"]:
        _closed(row, ("native_relative_path", "sha256", "size_bytes"), "other_output_invalid")
        _relative(row["native_relative_path"])
        _require(_sha(row["sha256"]) and _integer(row["size_bytes"]), "other_output_invalid")
        paths.append(row["native_relative_path"])
    _require(len(paths) == len(set(paths)), "output_path_duplicate")
    for failure in value["failures"]: _failure(failure)
    _execution(value["execution"])
    if completion is not None:
        wrapper = completion["wrapper"]
        outcome = "succeeded" if wrapper["outcome"] == "returned" and wrapper["returncode"] == 0 else \
            "failed" if wrapper["outcome"] == "returned" else "not_run" if wrapper["outcome"] == "not_started" else "unknown"
        _require(value["execution"]["wrapper_returncode"] == wrapper["returncode"]
            and value["execution"]["wrapper_outcome"] == outcome, "manifest_wrapper_conflict")
    return value


def read_homer_attempt_metadata(plan, *, read_bytes=None):
    """One original-raw metadata parser, also usable over retained private bytes.

    The optional reader takes an absolute Path and returns the exact raw bytes.
    This validates metadata independently and does not open scientific outputs.
    """
    plan = validate_homer_plan(plan)
    read = globals()["read_bytes"] if read_bytes is None else read_bytes
    root, values, pins, issues = Path(plan["attempt_directory"]), {}, {}, []
    for role, name in (("completion", COMPLETION_FILENAME), ("output_manifest", OUTPUT_MANIFEST_FILENAME)):
        try:
            raw = read(root / name)
            _require(type(raw) is bytes, "metadata_bytes_required")
            parsed = decode_json(raw)
            parsed = validate_homer_completion(parsed, plan=plan) if role == "completion" else \
                validate_homer_output_manifest(parsed, plan=plan, completion=values.get("completion"))
            values[role], pins[role] = parsed, _raw_pin(root / name, raw)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
            values[role], pins[role] = None, None
            issues.append(dict(code=role + ("_unavailable" if isinstance(error, FileNotFoundError) else "_invalid"),
                role=role, diagnostic=dict(exception_type=type(error).__name__, message=str(error))))
    if values["output_manifest"] is not None:
        # Raw completion bytes, rather than canonical reserialization, own this join.
        if pins["completion"] is not None and values["output_manifest"]["completion_file"] != pins["completion"]:
            values["output_manifest"], pins["output_manifest"] = None, None
            issues.append(dict(code="output_manifest_completion_identity_conflict", role="output_manifest", diagnostic=None))
    execution = _metadata_execution(values["completion"], values["output_manifest"])
    return dict(completion=values["completion"], completion_file=pins["completion"],
        output_manifest=values["output_manifest"], output_manifest_file=pins["output_manifest"],
        metadata_failures=issues, execution=execution)


def validate_homer_execution(value):
    value = _copy(value)
    _closed(value, ("version", "plan", "handle", "plan_file", "binding_file", "request_file", "terminal", "quiescent",
        "returncode", "metadata", "failure", "completion", "completion_file", "output_manifest", "output_manifest_file",
        "metadata_failures", "execution", "output_byte_validation"), "execution_fields_invalid")
    plan = validate_homer_plan(value["plan"])
    _require(value["version"] == EXECUTION_VERSION and value["terminal"] is True and value["quiescent"] is True
        and value["output_byte_validation"] == "deferred_to_result_owner"
        and (value["returncode"] is None or type(value["returncode"]) is int)
        and type(value["handle"]) is dict and type(value["metadata"]) is dict
        and _same(value["metadata"].get("policy"), plan["policy"]), "execution_invalid")
    root = Path(plan["operation_directory"])
    _handle_metadata(plan, value["handle"])
    for key, name in (("plan_file", PLAN_FILENAME), ("binding_file", BINDING_FILENAME), ("request_file", REQUEST_FILENAME)):
        _pin(value[key]); _require(value[key]["path"] == str(root / name), "execution_control_path_conflict")
    _require(value["plan_file"] == _raw_pin(root / PLAN_FILENAME, _bytes(plan))
        and value["request_file"] == plan["request_file"], "execution_control_identity_conflict")
    for role, validator in (("completion", validate_homer_completion), ("output_manifest", validate_homer_output_manifest)):
        pin = value[role + "_file"]
        _require((value[role] is None) == (pin is None), "execution_metadata_identity_missing")
        if pin is not None:
            _pin(pin)
            if role == "completion": validator(value[role], plan=plan)
            else: validator(value[role], plan=plan, completion=value["completion"])
            filename = COMPLETION_FILENAME if role == "completion" else OUTPUT_MANIFEST_FILENAME
            _require(pin["path"] == str(Path(plan["attempt_directory"]) / filename), "execution_metadata_path_conflict")
    _failure(value["failure"]); _execution(value["execution"])
    _require(_same(value["execution"], _metadata_execution(value["completion"], value["output_manifest"])),
        "execution_outcomes_metadata_conflict")
    _require(type(value["metadata_failures"]) is list, "metadata_failures_invalid")
    for row in value["metadata_failures"]:
        _closed(row, ("code", "role", "diagnostic"), "metadata_failure_invalid")
        _require(_text(row["code"]) and (row["role"] is None or _text(row["role"])), "metadata_failure_invalid")
    return value


def _same_or_write(path, raw):
    if path.exists() or path.is_symlink():
        _require(read_bytes(path) == raw, "original_control_conflict")
    else:
        try: immutable_bytes(path, raw)
        except FileExistsError: _require(read_bytes(path) == raw, "original_control_conflict")


def verify_homer_start_inputs(plan, *, verify_loaded=False):
    """Verify selected software/runtime identities only before original release."""
    _require(type(verify_loaded) is bool, "verify_loaded_flag_invalid")
    software = plan["software"]
    _require(file_pin(software["python"]["path"]) == software["python"], "python_identity_conflict")
    inventory = software["software_files_file"]
    raw = read_bytes(inventory["path"])
    _require(_raw_pin(inventory["path"], raw) == inventory, "software_inventory_identity_conflict")
    records = decode_json(raw)
    _closed(records, ("version", "files"), "software_inventory_invalid")
    _require(records["version"] == "homer_native_software_files_v1" and type(records["files"]) is list
        and bool(records["files"]), "software_inventory_invalid")
    paths = []
    for row in records["files"]:
        _pin(row); paths.append(row["path"])
        _require(file_pin(row["path"]) == row, "software_file_identity_conflict")
    _require(len(set(paths)) == len(paths) and inventory["path"] not in paths, "software_inventory_path_conflict")
    required = {software["python"]["path"], str(Path(__file__).absolute()),
        str(Path(__file__).with_name("native_homer_worker.py").absolute())}
    _require(required <= set(paths), "software_inventory_entry_closure_missing")
    # The original worker checks its actually imported modules after loading
    # this validator. Host dispatch need not import a scientific implementation.
    if verify_loaded:
        _require(Path(sys.executable).absolute() == Path(software["python"]["path"]), "selected_python_identity_conflict")
        for module in tuple(sys.modules.values()):
            selected_path = getattr(module, "__file__", None)
            if type(selected_path) is str and Path(selected_path).is_absolute():
                selected_path = str(Path(selected_path).absolute())
                _require(selected_path in paths, "software_inventory_loaded_module_missing")
    deployment = plan["request"]["deployment"]
    for row in deployment["files"]:
        path = Path(deployment["root"]) / row["relative_path"]
        _require(file_pin(path) == dict(path=str(path), sha256=row["sha256"], size_bytes=row["size_bytes"]),
            "deployment_file_identity_conflict")
        _require(path.stat().st_mode & 0o777 == row["mode"], "deployment_file_mode_conflict")
    for row in [*deployment["system_files"], *deployment["corrections"].values()]:
        _require(file_pin(row["path"]) == row, "system_or_correction_identity_conflict")


def _verify_controls(prepared):
    _closed(prepared, ("version", "binding", "binding_file", "plan", "plan_file", "request_file", "handle_path"),
        "prepared_fields_invalid")
    _require(prepared["version"] == PREPARED_VERSION, "prepared_version_invalid")
    plan = validate_homer_plan(prepared["plan"])
    binding = prepared["binding"]
    _closed(binding, ("version", "context", "operation_key", "arguments", "frozen_inputs", "selected", "policy"),
        "attempt_binding_fields_invalid")
    _require(binding["version"] == BINDING_VERSION and _same(binding["policy"], POLICY), "attempt_binding_invalid")
    selected = _selected(binding["selected"])
    context, identity = binding["context"], plan["identity"]
    root = Path(selected["workspace"]) / ".episode-operations" / digest({"run": context["run_id"],
        "episode": context["episode_id"]}) / digest(binding["operation_key"])
    _require(plan["operation_directory"] == str(root) and prepared["handle_path"] == identity["execution_id"]
        and all(identity[k] == context[k] for k in ("run_id", "episode_id"))
        and identity["request_sha256"] == digest(context["request"])
        and identity["assignment_sha256"] == digest(context["assignment"])
        and identity["operation_key"] == binding["operation_key"]
        and identity["resource_id"] == selected["resource_id"]
        and identity["binding_ordinal_0based"] == selected["binding_ordinal_0based"]
        and _same(plan["software"], selected["binding"]["software"])
        and _same(plan["request"], dict(version="homer_native_request_v1", operation=OPERATION, variant=VARIANT,
            arguments=binding["arguments"], frozen_inputs=binding["frozen_inputs"],
            deployment=selected["binding"]["deployment"], input_staging=selected["binding"]["input_staging"])),
        "attempt_binding_plan_conflict")
    directory(root)
    for key, name, value in (("binding_file", BINDING_FILENAME, binding), ("plan_file", PLAN_FILENAME, plan),
            ("request_file", REQUEST_FILENAME, plan["request"])):
        raw = read_bytes(confined_file(root, name))
        _require(prepared[key] == _raw_pin(root / name, raw) and raw == _bytes(value), "original_control_conflict")
    return plan, root


def _native_request(plan, paths):
    return dict(command=homer_adapter_argv(plan), cwd=plan["operation_directory"], file_bytes=plan["policy"]["scratch_bytes"],
        ready_path=paths["ready"], release_path=paths["release"], result_path=paths["result"], stdin_path=None,
        env=plan["selected_environment"])


def _handle_metadata(plan, body):
    """Pure original lifecycle shape; the live reader also verifies raw sidecar."""
    root = Path(plan["operation_directory"])
    _require(type(body) is dict and body.get("version") == native.VERSION
        and body.get("stage") in ("prepared", "submitting", "released")
        and _same(body.get("command"), homer_adapter_argv(plan)) and body.get("cwd") == str(root)
        and body.get("stdout") == str(root / "stdout.log") and body.get("stderr") == str(root / "stderr.log")
        and type(body.get("metadata")) is dict and _same(body["metadata"].get("policy"), plan["policy"]),
        "original_handle_conflict")
    paths = body.get("paths")
    _closed(paths, _NATIVE_PATHS, "original_native_paths_invalid")
    _require(all(type(p) is str for p in paths.values()), "original_native_paths_invalid")
    match = re.fullmatch(r"(\.local-job-[0-9a-f]{32})\.request", Path(paths["request"]).name)
    _require(match is not None and paths == {k: str(root / (match[1] + "." + k)) for k in _NATIVE_PATHS},
        "original_native_paths_conflict")
    _require(_sha(body.get("request_sha256")), "original_native_request_identity_invalid")
    return paths


def _verify_handle(prepared):
    plan, root = _verify_controls(prepared)
    body = decode_json(read_bytes(confined_file(root, "native.json")))
    paths = _handle_metadata(plan, body)
    for path in paths.values(): confined_file(root, Path(path).name)
    raw = read_bytes(paths["request"])
    _require(hashlib.sha256(raw).hexdigest() == body.get("request_sha256")
        and _same(decode_json(raw), _native_request(plan, paths)), "original_native_request_conflict")
    return native.NativeJobHandle(root / "native.json"), body


def prepare_ordinary_homer_attempt(*, context, operation_key, arguments, frozen_inputs, selected, policy):
    """Freeze one caller-selected reservation; do not release native work."""
    _require(type(context) is BindingContext, "binding_context_required")
    prefix = context.run_id + ":" + context.episode_id + ":"
    suffix = operation_key[len(prefix):] if type(operation_key) is str and operation_key.startswith(prefix) else ""
    _require(bool(suffix) and suffix.isdecimal() and str(int(suffix)) == suffix, "operation_key_invalid")
    _require(type(policy) is LocalJobPolicy and _same(policy.to_dict(), POLICY), "registry_allocation_required")
    arguments, frozen_inputs = validate_homer_arguments(arguments), validate_homer_frozen_inputs(frozen_inputs)
    selected = _selected(_copy(selected))
    root = Path(selected["workspace"]) / ".episode-operations" / digest({"run": context.run_id,
        "episode": context.episode_id}) / digest(operation_key)
    binding = dict(version=BINDING_VERSION, context=context.as_record(), operation_key=operation_key,
        arguments=arguments, frozen_inputs=frozen_inputs, selected=selected, policy=policy.to_dict())
    request = dict(version="homer_native_request_v1", operation=OPERATION, variant=VARIANT, arguments=arguments,
        frozen_inputs=frozen_inputs, deployment=selected["binding"]["deployment"], input_staging=selected["binding"]["input_staging"])
    identity = dict(run_id=context.run_id, episode_id=context.episode_id, resource_id=selected["resource_id"],
        binding_ordinal_0based=selected["binding_ordinal_0based"], operation_key=operation_key,
        execution_id=str(root / "native.json"), attempt_id=digest(operation_key),
        request_sha256=digest(plain(context.request)), assignment_sha256=digest(plain(context.assignment)))
    plan = dict(version=PLAN_VERSION, identity=identity, request=request, request_file=_raw_pin(root / REQUEST_FILENAME, _bytes(request)),
        software=selected["binding"]["software"], policy=policy.to_dict(), selected_environment=_environment(selected["binding"]["software"], root),
        operation_directory=str(root), attempt_directory=str(root / ATTEMPT_DIRECTORY))
    plan["selected_payload_sha256"] = _payload(plan)
    plan["requested_job"] = dict(argv=homer_adapter_argv(plan), environment=plan["selected_environment"])
    identity["requested_job_sha256"] = digest(plan["requested_job"])
    plan = validate_homer_plan(plan)
    staged_size = sum(row["size_bytes"] for row in request["deployment"]["files"])
    staged_size += sum(row["file"]["size_bytes"] for row in frozen_inputs["inputs"])
    control_size = sum(len(_bytes(value)) for value in (binding, request, plan))
    _require(staged_size + control_size < policy.scratch_bytes, "selected_staging_and_controls_exceed_scratch")
    prepared = dict(version=PREPARED_VERSION, binding=binding, binding_file=_raw_pin(root / BINDING_FILENAME, _bytes(binding)),
        plan=plan, plan_file=_raw_pin(root / PLAN_FILENAME, _bytes(plan)), request_file=plan["request_file"], handle_path=identity["execution_id"])
    directory(root, create=True)
    for name in (BINDING_FILENAME, REQUEST_FILENAME, PLAN_FILENAME, "native.json", "stdout.log", "stderr.log"):
        confined_file(root, name)
    if (root / "native.json").exists():
        _verify_handle(prepared)
        return _copy(prepared)
    # No replacement unit after an incomplete publication or uncertain writer.
    allowed = {BINDING_FILENAME, REQUEST_FILENAME, PLAN_FILENAME}
    if any(path.name not in allowed for path in root.iterdir()):
        raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed")
    try:
        verify_homer_start_inputs(plan)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        raise HomerPreflightRejected("ordinary_homer_preflight_rejected") from error
    for name, value in ((BINDING_FILENAME, binding), (REQUEST_FILENAME, request), (PLAN_FILENAME, plan)):
        _same_or_write(root / name, _bytes(value))
    for child in ("cache", "cache/pycache", "home"):
        directory(root / child, create=True)
    native.prepare_job(homer_adapter_argv(plan), cwd=root, policy=policy, handle_path=root / "native.json",
        stdout_path=root / "stdout.log", stderr_path=root / "stderr.log", env=plan["selected_environment"])
    _verify_handle(prepared)
    return _copy(prepared)


def _observe(handle, policy):
    view = native.status(handle)
    _require(type(view) is dict and type(view.get("terminal")) is bool and type(view.get("quiescent")) is bool
        and type(view.get("metadata")) is dict and _same(view["metadata"].get("policy"), policy), "lifecycle_observation_invalid")
    return view


def run_ordinary_homer_attempt(prepared, *, cancel_event=None):
    """Observe the original unit; caller cancellation never cancels that unit."""
    prepared = _copy(prepared)
    try:
        handle, body = _verify_handle(prepared)
        plan = prepared["plan"]
    except Exception as error:
        raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed") from error
    result, failure = None, None
    try:
        view = _observe(handle, plan["policy"])
        if not (view["terminal"] and view["quiescent"]):
            if cancel_event is not None and cancel_event.is_set():
                raise MolecularOperationUnpublished("ordinary_homer_observation_stopped")
            if view.get("state") == "execution_unknown":
                raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed")
            if body["stage"] == "prepared" or not Path(body["paths"]["release"]).exists():
                verify_homer_start_inputs(plan)
                if cancel_event is not None and cancel_event.is_set():
                    raise MolecularOperationUnpublished("ordinary_homer_observation_stopped")
                native.resume_start(handle)
            while True:
                view = _observe(handle, plan["policy"])
                if view["terminal"] and view["quiescent"]: break
                if cancel_event is not None and cancel_event.is_set():
                    raise MolecularOperationUnpublished("ordinary_homer_observation_stopped")
                if view.get("state") == "execution_unknown":
                    raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed")
                time.sleep(0.05)
        result = native.collect(handle)
    except MolecularOperationUnpublished:
        raise
    except Exception as error:
        try: view = _observe(handle, plan["policy"])
        except Exception as observation_error:
            raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed") from observation_error
        if not (view["terminal"] and view["quiescent"]):
            raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed") from error
        failure = dict(code=error.code, phase=error.phase, diagnostic=deepcopy(error.diagnostic),
            operational=deepcopy(error.operational)) if isinstance(error, AcquisitionError) else \
            failure_record("ordinary_homer_lifecycle_error", "local_execution", error)
    try:
        view = _observe(handle, plan["policy"])
        _require(view["terminal"] and view["quiescent"], "original_unit_not_quiescent")
        _handle, body = _verify_handle(prepared)
    except Exception as error:
        raise MolecularOperationUnpublished("ordinary_homer_original_attempt_unconfirmed") from error
    code = result.returncode if result is not None else view["metadata"].get("native_returncode")
    _require(code is None or type(code) is int, "native_returncode_invalid")
    metadata = read_homer_attempt_metadata(plan)
    return validate_homer_execution(dict(version=EXECUTION_VERSION, plan=plan, handle=body,
        **{key: prepared[key] for key in ("plan_file", "binding_file", "request_file")},
        terminal=True, quiescent=True, returncode=code, metadata=deepcopy(view["metadata"]),
        failure=failure, **metadata, output_byte_validation="deferred_to_result_owner"))


__all__ = ["validate_homer_bindings", "validate_homer_arguments", "validate_homer_plan",
    "validate_homer_completion", "validate_homer_output_manifest", "validate_homer_execution",
    "read_homer_attempt_metadata", "prepare_ordinary_homer_attempt", "run_ordinary_homer_attempt",
    "homer_execution_schema", "homer_motif_sets", "HomerPreflightRejected"]
