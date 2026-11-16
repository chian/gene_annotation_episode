"""Pure records for the selected native all-pairs genomic overlap operation.

G1 owns scientific records; these checks validate supplied execution facts and
associations, never observe files, grant source authority or execute work.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator, FormatChecker, validators
from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_contracts import (
    ComparisonSpec, Request, genomic_overlap_schema, validate_genomic_overlap_record,
)

from gene_annotation_episode.episodic_workflow.root.library.native_genomic_overlap_job_schema import (
    POLICY, _EXECUTION_DEFINITIONS, _require, _digest, _references, _definitions,
    genomic_overlap_execution_schema, validate_recorded_genomic_overlap_policy,
)
from gene_annotation_episode.episodic_workflow.root.library.genomic_overlap_job_validation import (
    RUN_PLAN_FILENAME, BATCH_FILENAME, OWNER_FILENAME, STARTED_FILENAME, DRIVER_MODULE,
    _REQUIRED_MODULES, _plain, _STRICT, _validator, _checked, _path, _overlap, _software,
    validate_genomic_overlap_bindings, _request, genomic_overlap_output_files, _environment,
    validate_genomic_overlap_job, compile_genomic_overlap_job, requested_job_from_genomic_overlap,
    validate_genomic_overlap_requested_job,
)
ATTEMPT_DIRECTORY_NAME = "genomic-overlap-attempt"


def validate_genomic_overlap_run_plan(value: dict) -> dict:
    value = _checked(value, "RunPlan")
    request = validate_genomic_overlap_requested_job(value["requested_job"])
    identity = value["identity"]
    execution = _path(identity["execution_id"], absolute=True)
    attempt = _path(value["attempt_directory"], absolute=True)
    from gene_annotation_episode.episodic_workflow.root.library.terminal_plan_identity import terminal_plan_identity
    current = terminal_plan_identity(identity, attempt_directory=str(attempt))
    _require((current or execution.name == "native.json") and attempt == execution.parent / ATTEMPT_DIRECTORY_NAME,
             "original_attempt_mismatch")
    _require(identity["attempt_id"] == _digest(identity["operation_key"]) and
             identity["requested_job_sha256"] == _digest(request), "original_attempt_mismatch")
    _require(current or execution.parent.name == identity["attempt_id"] and execution.parent.parent.name ==
             _digest({"run": identity["run_id"], "episode": identity["episode_id"]}) and
             execution.parent.parent.parent.name == ".episode-operations", "original_attempt_mismatch")
    _require(type(value["policy"]["memory_bytes"]) is int and type(value["policy"]["scratch_bytes"]) is int
             and value["policy"] == validate_recorded_genomic_overlap_policy(value["policy"]), "genomic_overlap_policy_mismatch")
    for row in request["native_genomic_overlap"]["inputs"]:
        _require(not _overlap(_path(row["path"], absolute=True), execution.parent),
                 "genomic_overlap_invalid_path")
    return value


def genomic_overlap_driver_argv(plan: dict) -> list[str]:
    plan = validate_genomic_overlap_run_plan(plan)
    return compile_genomic_overlap_job(plan["requested_job"]["native_genomic_overlap"],
        plan_path=str(PurePosixPath(plan["identity"]["execution_id"]).parent / RUN_PLAN_FILENAME))["argv"]


def genomic_overlap_environment(job: dict, *, attempt_directory: str) -> dict:
    job = validate_genomic_overlap_job(job)
    root = _path(attempt_directory, absolute=True)
    return {**job["environment"], "PYTHONPATH": job["software"]["module_root"],
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "TMP": str(root / "tmp"),
            "TEMP": str(root / "tmp"), "TMPDIR": str(root / "tmp"),
            "XDG_CACHE_HOME": str(root / "cache"), "PIP_CACHE_DIR": str(root / "cache/pip")}


def _native_identity(plan):
    identity = plan["identity"]
    return {**{k: identity[k] for k in ("run_id", "resource_id", "execution_id", "attempt_id", "operation_key")},
            "origin_episode_id": identity["episode_id"]}


def _fingerprint(spec):
    return {"set_key": spec["set_key"], **{k: spec["source"]["file"][k] for k in ("format", "sha256", "size_bytes")}}


def _declared_software(plan):
    software = plan["requested_job"]["native_genomic_overlap"]["software"]
    return {"executable": software["bedtools_executable"], "declared_version": software["bedtools_version"],
            "observed_version": software["bedtools_version"], "executable_sha256": software["bedtools_sha256"]}


def _interval(value):
    try:
        start, finish = (datetime.fromisoformat(value[k].replace("Z", "+00:00"))
                         for k in ("started_at", "finished_at"))
        _require(start.tzinfo is not None and finish.tzinfo is not None and finish >= start,
                 "genomic_overlap_invalid_times")
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("genomic_overlap_invalid_times") from error
    return start, finish


def _declaration(value):
    value = validate_genomic_overlap_record("NativeFileDeclaration", value)
    _path(value["relative_path"], absolute=False)
    _require((value["sha256"] is not None and value["size_bytes"] is not None) if value["state"] == "present"
             else (value["sha256"] is None and value["size_bytes"] is None), "genomic_overlap_file_declaration")
    if value["size_bytes"] == 0:
        _require(value["sha256"] == hashlib.sha256(b"").hexdigest(), "genomic_overlap_file_declaration")
    return value


def _set_outputs(values, request):
    _require(type(values) is list and len(values) == len(request["region_sets"]), "genomic_overlap_set_binding")
    rows = [_checked(row, "SetOutput") for row in values]
    for i, (row, spec) in enumerate(zip(rows, request["region_sets"])):
        _require(row["set_key"] == spec["set_key"] and row["set_position"] == i and
                 all(row[k + "_file_key"] == "s" + str(i) + ":" + k for k in
                     ("original", "rejected", "parsed", "canonical")), "genomic_overlap_set_binding")
        fp = row["measured_fingerprint"]
        if row["input_state"] == "unavailable":
            _require(fp is None and row["parse_extent"] in (None, "unavailable"), "genomic_overlap_set_binding")
        else:
            _require(fp is not None and fp["set_key"] == spec["set_key"] and fp["format"] == spec["format"],
                     "genomic_overlap_input_identity_mismatch")
            _require((fp == _fingerprint(spec)) == (row["input_state"] == "verified"),
                     "genomic_overlap_input_identity_mismatch")
            if row["input_state"] == "digest_mismatch":
                _require(row["parse_extent"] in (None, "unavailable"), "genomic_overlap_set_binding")
    return rows


def validate_genomic_overlap_independent_pair_manifest(value: object, *, plan: dict,
        comparison: ComparisonSpec) -> dict:
    """Validate an original pair seal without inventing missing batch facts.

    This checks only supplied original declarations. Current input availability
    and scientific use are checked separately by G1; source/closure authority
    and the seal's actual byte capture remain host responsibilities.
    """
    plan = validate_genomic_overlap_run_plan(plan)
    request = plan["requested_job"]["native_genomic_overlap"]["request"]
    comparison = validate_genomic_overlap_record("ComparisonSpec", comparison)
    _require(comparison in request["comparisons"], "genomic_overlap_pair_binding")
    sets = {row["set_key"]: (i, row) for i, row in enumerate(request["region_sets"])}
    operands = [sets[comparison[k + "_set_key"]] for k in ("a", "b")]
    value = validate_genomic_overlap_record("NativeDriverManifest", value)
    _require(value["identity"] == _native_identity(plan) and value["comparison_key"] == comparison["comparison_key"]
        and all(value[k + "_set_key"] == comparison[k + "_set_key"] for k in ("a", "b")),
        "genomic_overlap_pair_binding")
    _require(value["input_fingerprints"] == [_fingerprint(spec) for _, spec in operands],
        "genomic_overlap_input_identity_mismatch")
    _require(value["writer_closed"] is True, "genomic_overlap_pair_not_closed")
    if value["derivation"] != "bedtools_intersect":
        _require(value["outcome"] == "not_executed" and value["software"] is None and
            value["returncode"] is None and value["started_at"] is None and value["finished_at"] is None and
            value["realized_argv"] == [] and value["environment"] == {} and value["files"] == [],
            "genomic_overlap_uninvoked_facts")
        return value
    _require(value["outcome"] in ("succeeded", "failed") and type(value["returncode"]) is int
        and ((value["returncode"] == 0) == (value["outcome"] == "succeeded")), "genomic_overlap_native_outcome")
    _interval(value)
    _require(value["software"] == _declared_software(plan), "genomic_overlap_software_binding")
    expected = genomic_overlap_output_files(request)
    by_key = {row["file_key"]: row for row in expected}
    keys = ["s" + str(i) + ":canonical" for i, _ in operands] + ["p" + str(comparison["ordinal"]) + ":" + k
                                                          for k in ("stdout", "stderr")]
    roles = ("canonical_a", "canonical_b", "overlap_stdout", "overlap_stderr")
    _require(len(value["files"]) == 4, "genomic_overlap_pair_files")
    for i, (row, key, role) in enumerate(zip(value["files"], keys, roles)):
        decl = _declaration(row["declaration"])
        _require(row["file_key"] == comparison["comparison_key"] + ":file:" + str(i) and row["role"] == role
            and all(decl[k] == by_key[key][k] for k in ("relative_path", "format")), "genomic_overlap_pair_files")
        if i < 2 or value["outcome"] == "succeeded":
            _require(decl["state"] == "present", "genomic_overlap_pair_files")
        if i < 2:
            _require(decl["size_bytes"] > 0, "genomic_overlap_empty_input_binding")
    attempt = PurePosixPath(plan["attempt_directory"])
    expected_argv = [value["software"]["executable"], "intersect", "-a", str(attempt / by_key[keys[0]]["relative_path"]),
                     "-b", str(attempt / by_key[keys[1]]["relative_path"]), "-wo", "-sorted"]
    _require(value["realized_argv"] == expected_argv and value["environment"] ==
        genomic_overlap_environment(plan["requested_job"]["native_genomic_overlap"], attempt_directory=str(attempt)),
        "genomic_overlap_native_invocation")
    return value


def validate_genomic_overlap_pair_manifest(value: dict, *, plan: dict,
        comparison: ComparisonSpec, set_outputs: list[dict]) -> dict:
    """Also check an original pair against its supplied batch set observations."""
    plan = validate_genomic_overlap_run_plan(plan)
    request = plan["requested_job"]["native_genomic_overlap"]["request"]
    comparison = validate_genomic_overlap_record("ComparisonSpec", comparison)
    _require(comparison in request["comparisons"], "genomic_overlap_pair_binding")
    sets = {row["set_key"]: row for row in _set_outputs(set_outputs, request)}
    operands = [sets[comparison[k + "_set_key"]] for k in ("a", "b")]
    value = validate_genomic_overlap_independent_pair_manifest(value, plan=plan, comparison=comparison)
    _require(all(row["input_state"] == "verified" for row in operands) and
        value["input_fingerprints"] == [row["measured_fingerprint"] for row in operands],
        "genomic_overlap_input_identity_mismatch")
    complete = all(row["parse_extent"] == "complete" for row in operands)
    if value["derivation"] == "validated_empty_input":
        _require(complete, "genomic_overlap_empty_input_binding")
    elif value["derivation"] == "not_executed_invalid_input":
        _require(not complete and any(row["parse_extent"] in ("partial", "unavailable") for row in operands),
                 "genomic_overlap_invalid_input_binding")
    else:
        _require(complete, "genomic_overlap_native_outcome")
    return value


def validate_genomic_overlap_batch(value: dict, *, plan: dict) -> dict:
    """Validate a supplied seal and its joins; never inspect producer paths."""
    plan = validate_genomic_overlap_run_plan(plan)
    value = _checked(value, "BatchManifest")
    job = plan["requested_job"]["native_genomic_overlap"]
    request, software = job["request"], job["software"]
    environment = genomic_overlap_environment(job, attempt_directory=plan["attempt_directory"])
    _require(value["identity"] == _native_identity(plan) and value["plan_sha256"] == _digest(plan)
        and value["requested_job_sha256"] == plan["identity"]["requested_job_sha256"]
        and value["policy"] == plan["policy"] and type(value["policy"]["memory_bytes"]) is int
        and type(value["policy"]["scratch_bytes"]) is int and value["driver_argv"] == genomic_overlap_driver_argv(plan)
        and value["realized_environment"] == environment, "original_attempt_mismatch")
    _require(value["requested_set_keys"] == [row["set_key"] for row in request["region_sets"]]
        and value["requested_comparisons"] == request["comparisons"], "genomic_overlap_batch_population")
    start, finish = _interval(value)
    sets = _set_outputs(value["sets"], request)
    set_index = {row["set_key"]: row for row in sets}
    comparisons = {row["comparison_key"]: row for row in request["comparisons"]}
    specifications = genomic_overlap_output_files(request)
    _require([row["specification"] for row in value["files"]] == specifications[:-1],
             "genomic_overlap_batch_files")
    files = {}
    specs = {row["file_key"]: row for row in specifications}
    for row in value["files"]:
        specification, declaration = row["specification"], _declaration(row["declaration"])
        _require(all(declaration[k] == specification[k] for k in ("relative_path", "format")),
                 "genomic_overlap_batch_files")
        files[specification["file_key"]] = declaration
    failures = value["failures"]
    for failure in failures:
        sk, pk, fk = (failure[k] for k in ("set_key", "comparison_key", "file_key"))
        _require(sk is None or sk in set_index, "genomic_overlap_failure_binding")
        _require(pk is None or pk in comparisons, "genomic_overlap_failure_binding")
        _require(fk is None or fk in specs, "genomic_overlap_failure_binding")
        if sk is not None and pk is not None:
            _require(sk in (comparisons[pk]["a_set_key"], comparisons[pk]["b_set_key"]),
                     "genomic_overlap_failure_binding")
        if fk is not None:
            spec = specs[fk]
            _require(sk is None or spec["set_key"] in (None, sk), "genomic_overlap_failure_binding")
            _require(pk is None or spec["comparison_key"] in (None, pk), "genomic_overlap_failure_binding")
            if pk is not None and spec["set_key"] is not None:
                _require(spec["set_key"] in (comparisons[pk]["a_set_key"], comparisons[pk]["b_set_key"]),
                         "genomic_overlap_failure_binding")
            if sk is not None and spec["comparison_key"] is not None:
                pair = comparisons[spec["comparison_key"]]
                _require(sk in (pair["a_set_key"], pair["b_set_key"]), "genomic_overlap_failure_binding")

    referenced = set()

    def failure_rows(indices, *, set_key=None, comparison=None, software_only=False):
        result = []
        for index in indices:
            _require(index < len(failures), "genomic_overlap_failure_binding")
            failure = failures[index]
            if set_key is not None:
                _require(failure["set_key"] in (None, set_key) and failure["comparison_key"] is None,
                         "genomic_overlap_failure_binding")
            if comparison is not None:
                _require(failure["comparison_key"] in (None, comparison["comparison_key"])
                    and failure["set_key"] in (None, comparison["a_set_key"], comparison["b_set_key"]),
                    "genomic_overlap_failure_binding")
            if software_only:
                _require(failure["stage"] == "software" and failure["set_key"] is None,
                         "genomic_overlap_failure_binding")
            referenced.add(index)
            result.append(failure)
        return result

    verification = value["software_verification"]
    software_failures = failure_rows(verification["failure_indices"], software_only=True)
    python_expected = {"sha256": software["python_sha256"], "version": software["python_version"]}
    if verification["state"] in ("verified", "not_needed"):
        _require(verification["python_observed"] == python_expected and not software_failures,
                 "genomic_overlap_software_binding")
    else:
        _require(bool(software_failures), "genomic_overlap_software_binding")
    implementation_failed = verification["python_observed"] != python_expected or any(
        f["code"] == "software_identity_mismatch" and (f["field_path"] == "/software" or
            (f["field_path"] or "").startswith(("/software/python_", "/software/implementation_files/",
                                                "/software/module_root/"))) for f in software_failures)
    if implementation_failed:
        _require(verification["state"] == "failed" and
            any(f["code"] == "software_identity_mismatch" for f in software_failures) and
            all(row["parse_extent"] is None for row in sets), "genomic_overlap_software_binding")
    probe = verification["version_probe"]
    observed = verification["bedtools_observed"]
    if observed is not None:
        _require(observed["executable"] == software["bedtools_executable"] and
            observed["declared_version"] == software["bedtools_version"], "genomic_overlap_software_binding")
        _require(observed["observed_version"] is None or probe is not None, "genomic_overlap_uninvoked_facts")
    if verification["state"] == "verified":
        _require(observed == _declared_software(plan) and probe is not None and probe["returncode"] == 0,
                 "genomic_overlap_software_binding")
    if verification["state"] == "not_needed":
        _require(probe is None and observed is None, "genomic_overlap_uninvoked_facts")
    if probe is not None:
        probe_start, probe_finish = _interval(probe)
        _require(start <= probe_start <= probe_finish <= finish and probe["realized_argv"] ==
            [software["bedtools_executable"], "--version"] and probe["environment"] == environment,
            "genomic_overlap_native_invocation")
        _require(all(files[k]["state"] == "present" for k in ("version_stdout", "version_stderr")),
                 "genomic_overlap_batch_files")
    elif verification["state"] == "not_needed":
        _require(all(files[k]["state"] == "absent" for k in ("version_stdout", "version_stderr")),
                 "genomic_overlap_uninvoked_facts")

    for row in sets:
        located = failure_rows(row["failure_indices"], set_key=row["set_key"])
        original, rejected, parsed, canonical = [files[row[k + "_file_key"]] for k in
                                                ("original", "rejected", "parsed", "canonical")]
        fp = row["measured_fingerprint"]
        if row["input_state"] == "verified":
            _require(original["state"] == "present" and rejected["state"] == "absent" and
                all(original[k] == fp[k] for k in ("sha256", "size_bytes", "format")),
                "genomic_overlap_input_identity_mismatch")
        elif row["input_state"] == "digest_mismatch":
            _require(original["state"] == "absent" and rejected["state"] == "present" and
                all(rejected[k] == fp[k] for k in ("sha256", "size_bytes", "format")) and
                any(f["code"] == "input_digest_mismatch" for f in located), "genomic_overlap_input_identity_mismatch")
        else:
            _require(original["state"] == "absent" and any(f["code"] in
                ("input_unavailable", "resource_limit", "output_unavailable", "seal_failed") for f in located),
                "genomic_overlap_input_identity_mismatch")
        if row["parse_extent"] is None:
            _require(parsed["state"] == canonical["state"] == "absent" and bool(located or software_failures),
                     "genomic_overlap_set_binding")
        else:
            _require(parsed["state"] == "present", "genomic_overlap_set_binding")
            if row["parse_extent"] == "complete":
                _require(canonical["state"] == "present" or any(f["code"] in
                    ("seal_failed", "resource_limit", "output_unavailable") for f in located),
                    "genomic_overlap_set_binding")
            else:
                _require(canonical["state"] == "absent", "genomic_overlap_set_binding")
        if row["parse_extent"] not in (None, "complete"):
            _require(bool(located), "genomic_overlap_failure_binding")

    _require(len(value["pairs"]) == len(request["comparisons"]), "genomic_overlap_batch_population")
    successful = 0
    needs_bedtools = False
    for row, comparison in zip(value["pairs"], request["comparisons"]):
        _require(row["comparison"] == comparison, "genomic_overlap_pair_binding")
        pair_failures = failure_rows(row["failure_indices"], comparison=comparison)
        operands = [set_index[comparison[k + "_set_key"]] for k in ("a", "b")]
        canonical_files = [files[r["canonical_file_key"]] for r in operands]
        complete = all(r["parse_extent"] == "complete" for r in operands)
        verified_inputs = all(r["input_state"] == "verified" for r in operands)
        # A complete parsed map can survive a failed canonical-file publication.
        # Keep that fact, but do not require an analytic-success disposition for
        # a pair whose other canonical input was never successfully published.
        is_empty = complete and all(f["state"] == "present" for f in canonical_files) and any(
            f["size_bytes"] == 0 for f in canonical_files)
        eligible_native = complete and all(f["state"] == "present" and f["size_bytes"] > 0 for f in canonical_files)
        needs_bedtools |= eligible_native
        stem = "p" + str(comparison["ordinal"]) + ":"
        disposition, manifest = row["disposition"], row["manifest"]
        if disposition in ("input_unavailable", "native_unavailable"):
            _require(manifest is None and row["manifest_file_key"] is None and files[stem + "manifest"]["state"] == "absent"
                and bool(pair_failures), "genomic_overlap_uninvoked_facts")
            if disposition == "input_unavailable":
                _require(not verified_inputs and all(files[stem + k]["state"] == "absent" for k in ("stdout", "stderr")),
                         "genomic_overlap_input_identity_mismatch")
                _require(any(f["code"] in ("input_unavailable", "input_digest_mismatch", "resource_limit",
                    "output_unavailable", "seal_failed") for f in pair_failures), "genomic_overlap_failure_binding")
            else:
                _require(verified_inputs and not is_empty and any(f["code"] in
                    ("native_dependency_unavailable", "native_version_unverified", "software_identity_mismatch",
                     "native_spawn_failed", "resource_limit", "output_unavailable", "seal_failed") for f in pair_failures),
                    "genomic_overlap_failure_binding")
                # A failed interpreter/implementation check may retain verified
                # originals without running G1 on unverified code.
                if not complete:
                    _require(any(r["parse_extent"] is None for r in operands) and
                        (verification["state"] == "failed" and any(f["code"] == "software_identity_mismatch"
                            for f in pair_failures) or any(f["code"] in
                            ("seal_failed", "resource_limit", "output_unavailable") for f in pair_failures)),
                        "genomic_overlap_set_binding")
            continue
        _require(manifest is not None and row["manifest_file_key"] == stem + "manifest"
            and files[stem + "manifest"]["state"] == "present", "genomic_overlap_pair_binding")
        checked = validate_genomic_overlap_pair_manifest(manifest, plan=plan, comparison=comparison, set_outputs=sets)
        # Pair JSON is an immutable canonical control record with one LF. This
        # checks its declared original bytes; the host still captures them.
        raw = json.dumps(checked, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8") + b"\n"
        _require(files[stem + "manifest"]["sha256"] == hashlib.sha256(raw).hexdigest() and
            files[stem + "manifest"]["size_bytes"] == len(raw), "genomic_overlap_pair_seal_mismatch")
        expected = {"native_succeeded": ("bedtools_intersect", "succeeded"),
                    "native_failed": ("bedtools_intersect", "failed"),
                    "analytic_empty": ("validated_empty_input", "not_executed"),
                    "invalid_input": ("not_executed_invalid_input", "not_executed")}[disposition]
        _require((manifest["derivation"], manifest["outcome"]) == expected, "genomic_overlap_native_outcome")
        if disposition in ("analytic_empty", "invalid_input"):
            _require(all(files[stem + k]["state"] == "absent" for k in ("stdout", "stderr")),
                     "genomic_overlap_uninvoked_facts")
            if disposition == "analytic_empty":
                _require(is_empty and not pair_failures, "genomic_overlap_empty_input_binding")
            else:
                _require(any(f["code"] == "invalid_input" for f in pair_failures), "genomic_overlap_failure_binding")
        else:
            _require(eligible_native and verification["state"] == "verified", "genomic_overlap_software_binding")
            pair_start, pair_finish = _interval(manifest)
            _require(start <= pair_start <= pair_finish <= finish and _interval(probe)[1] <= pair_start,
                     "genomic_overlap_invalid_times")
            keys = [r["canonical_file_key"] for r in operands] + [stem + "stdout", stem + "stderr"]
            _require([r["declaration"] for r in manifest["files"]] == [files[k] for k in keys],
                     "genomic_overlap_pair_files")
            if disposition == "native_failed":
                _require(any(f["code"] == "native_nonzero_exit" for f in pair_failures),
                         "genomic_overlap_failure_binding")
            else:
                _require(not pair_failures, "genomic_overlap_failure_binding")
        successful += disposition in ("native_succeeded", "analytic_empty")
    if verification["state"] == "not_needed":
        _require(not needs_bedtools, "genomic_overlap_software_binding")
    if verification["state"] == "verified":
        _require(needs_bedtools, "genomic_overlap_software_binding")
    # Unreferenced seal-level failures can concern the final batch or driver
    # logs; input/software/native failures must resolve to their owning rows.
    _require(all(i in referenced or f["stage"] == "seal" for i, f in enumerate(failures)),
             "genomic_overlap_failure_binding")
    all_success = successful == len(request["comparisons"]) and all(r["parse_extent"] == "complete" for r in sets)
    expected_status = "complete" if all_success else "partial" if successful else "failed"
    _require(value["batch_status"] == expected_status, "genomic_overlap_batch_status")
    return value


__all__ = ["RUN_PLAN_FILENAME", "ATTEMPT_DIRECTORY_NAME", "BATCH_FILENAME", "OWNER_FILENAME", "STARTED_FILENAME", "POLICY",
    "genomic_overlap_execution_schema", "validate_genomic_overlap_bindings", "validate_genomic_overlap_job",
    "genomic_overlap_output_files", "compile_genomic_overlap_job", "requested_job_from_genomic_overlap",
    "validate_genomic_overlap_requested_job", "validate_genomic_overlap_run_plan", "genomic_overlap_driver_argv",
    "genomic_overlap_environment", "validate_genomic_overlap_batch", "validate_genomic_overlap_pair_manifest",
    "validate_genomic_overlap_independent_pair_manifest"]
