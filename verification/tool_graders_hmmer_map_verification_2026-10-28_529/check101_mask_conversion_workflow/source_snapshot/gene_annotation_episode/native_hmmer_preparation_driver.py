"""Retain one selected preparation command under the existing native lifecycle.

The caller owns the job and allocation. This producer copies selected operands,
executes one compiled command and seals its actual bytes. It does not interpret
scientific output, choose follow-up work, poll, retry or dispatch another job.
"""
from __future__ import annotations

from datetime import datetime
import ctypes
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

from .local_jobs import LocalJobPolicy
from .native_infernal_contracts import finite_json_copy
from .native_infernal_driver import (
    _ScratchLimit, _absolute_directory, _atomic_new, _confined_file, _digest_file,
    _environment, _now, _read_json, _regular_reader, _scratch, _sha, _validate_identity,
)
from .native_hmmer_preparation_contracts import (
    RANGE_FLAGS, native_options, parse_ranges,
    compile_native_hmmer_preparation_job,
    recorded_operation_matches_compiled,
    validate_native_hmmer_preparation_requested_job,
)


PLAN_VERSION = "native_hmmer_preparation_run_plan_v1"
BUNDLE_VERSION = "native_hmmer_preparation_bundle_v1"
OWNER_NAME = ".native-hmmer-preparation-owner.json"
BUNDLE_NAME = "bundle.json"
INPUT_DIRECTORY = "inputs"
MODEL_STAGING_PATH = "inputs/models.hmm"
SSI_STAGING_PATH = "inputs/models.hmm.ssi"
_BUNDLE_FIELDS = {"version", "identity", "requested_job", "program", "mode", "operation",
    "software", "realized_argv", "environment", "inputs", "working_copies", "returncode",
    "artifacts", "failures", "started_at", "finished_at", "native_abi"}
_INPUT_FIELDS = {"role", "ordinal", "format", "original_path", "relative_path", "artifact_ref",
    "expected_sha256", "expected_size_bytes", "staged_sha256", "staged_size_bytes",
    "final_sha256", "final_size_bytes"}
_COPY_FIELDS = {"operand_role", "operand_ordinal", "relative_path", "mutable", "source_sha256",
    "initial_sha256", "initial_size_bytes", "final_sha256", "final_size_bytes"}
_ARTIFACT_FIELDS = {"role", "format", "relative_path", "size_bytes", "sha256"}
_PREFIX = "native_hmmer_preparation_"
# Closed codes and exact typed context fields. These describe custody/execution,
# never annotation confidence or natural-language interpretation of a result.
_FAILURES = {
    "invalid_alimask_input": ({"preflight"}, {"reason": "preflight_reason"}),
    "unsupported_alimask_model_map": ({"preflight"}, {"reason": "preflight_reason"}),
    "unsafe_alimask_range": ({"preflight"}, {"start": "uint", "end": "uint", "last_match": "uint"}),
    "invalid_exactmatch_queries": ({"preflight"}, {"ordinal": "uint", "reason": "preflight_reason"}),
    "incompatible_fm_abi": ({"preflight"}, {"reason": "preflight_reason"}),
    "invalid_fm_database": ({"preflight"}, {"reason": "preflight_reason", "issue_codes": "fm_issue_codes"}),
    "invalid_model_format": ({"preflight"}, {"reason": "preflight_reason"}),
    "source_binding_digest_mismatch": ({"preflight"}, {"reason": "preflight_reason"}),
    "software_digest_mismatch": ({"software"}, {}),
    "software_not_executable": ({"software"}, {}),
    "software_unavailable": ({"software"}, {"reason": "reason", "errno": "errno"}),
    "input_missing": ({"inputs"}, {"ordinal": "uint"}),
    "input_io_error": ({"inputs"}, {"ordinal": "uint", "errno": "errno"}),
    "input_not_regular": ({"inputs"}, {"ordinal": "uint"}),
    "input_identity_mismatch": ({"inputs"}, {"ordinal": "uint"}),
    "working_copy_not_staged": ({"staging"}, {"operand_ordinal": "uint", "relative_path": "path"}),
    "working_copy_io_error": ({"staging"}, {"operand_ordinal": "uint", "relative_path": "path", "errno": "errno"}),
    "working_copy_identity_mismatch": ({"staging"}, {"operand_ordinal": "uint", "relative_path": "path"}),
    "scratch_limit": ({"staging", "execution"}, {"observed_bytes": "uint", "limit_bytes": "uint", "relative_path": "nullable_path"}),
    "nonzero_returncode": ({"execution"}, {"returncode": "int"}),
    "command_unavailable": ({"execution"}, {"errno": "errno"}),
    "immutable_input_changed": ({"execution"}, {"ordinal": "uint"}),
    "immutable_working_copy_changed": ({"execution"}, {"operand_ordinal": "uint", "relative_path": "path"}),
    "input_final_unavailable": ({"inputs", "execution"}, {"ordinal": "uint", "reason": "reason", "errno": "errno"}),
    "working_copy_final_unavailable": ({"staging", "execution"}, {"operand_ordinal": "uint", "relative_path": "path", "reason": "reason", "errno": "errno"}),
    "missing_output": ({"outputs"}, {"relative_path": "path"}),
    "invalid_output": ({"outputs"}, {"relative_path": "path", "reason": "reason", "errno": "errno"}),
}
FAILURE_CODES = frozenset(_PREFIX + code for code in _FAILURES)
PREFLIGHT_REASONS = frozenset({"alignment_format_not_established", "malformed_stockholm", "multiple_alignments",
    "rf_required", "empty_model_map", "weighted_map_not_established", "pb_subsampling_not_established", "map_configuration_unavailable",
    "explicit_alphabet_required", "unsupported_alignment_symbols", "invalid_weights", "range_outside_alignment",
    "query_requires_final_lf", "query_empty", "query_exceeds_254_symbols", "query_requires_literal_canonical_dna",
    "producer_byte_order_mismatch", "producer_integer_width_mismatch", "invalid_fm_framing", "dna_only_reader", "fm_reader_header_incompatible",
    "invalid_fm_arrays", "invalid_fm_segments", "invalid_fm_ambiguities", "source_sha256_order_mismatch",
    "wrong_model_signature", "no_model_bytes", "malformed_alignment", "alphabet_undetermined",
    "alphabet_source_semantics_unestablished", "decoder_source_semantics_unestablished"})
PREFLIGHT_FAILURE_CONTEXT = {
    "invalid_alimask_input": {"role": "alignment", "programs": frozenset({"alimask"}),
        "reasons": frozenset({"malformed_stockholm", "malformed_alignment", "multiple_alignments", "invalid_weights", "range_outside_alignment", "empty_model_map"})},
    "unsupported_alimask_model_map": {"role": "alignment", "programs": frozenset({"alimask"}),
        "reasons": frozenset({"alignment_format_not_established", "rf_required", "weighted_map_not_established",
            "pb_subsampling_not_established", "map_configuration_unavailable", "explicit_alphabet_required", "unsupported_alignment_symbols", "invalid_weights",
            "alphabet_undetermined", "alphabet_source_semantics_unestablished", "decoder_source_semantics_unestablished"})},
    "unsafe_alimask_range": {"role": "alignment", "programs": frozenset({"alimask"}), "reasons": None},
    "invalid_exactmatch_queries": {"role": "queries", "programs": frozenset({"hmmerfm-exactmatch"}),
        "reasons": frozenset({"query_requires_final_lf", "query_empty", "query_exceeds_254_symbols", "query_requires_literal_canonical_dna"})},
    "incompatible_fm_abi": {"role": "fm_database", "programs": frozenset({"hmmerfm-exactmatch"}),
        "reasons": frozenset({"producer_byte_order_mismatch", "producer_integer_width_mismatch"})},
    "invalid_fm_database": {"role": "fm_database", "programs": frozenset({"hmmerfm-exactmatch"}),
        "reasons": frozenset({"invalid_fm_framing", "dna_only_reader", "fm_reader_header_incompatible"})},
    "invalid_model_format": {"role": "models", "programs": frozenset({"hmmconvert", "hmmemit", "hmmfetch", "hmmpress", "hmmsim", "hmmstat"}),
        "reasons": frozenset({"wrong_model_signature", "no_model_bytes"})},
    "source_binding_digest_mismatch": {"role": "source_sequences", "programs": frozenset({"hmmerfm-exactmatch"}),
        "reasons": frozenset({"source_sha256_order_mismatch"})},
}
NATIVE_ABI_FIELDS = frozenset({"byte_order", "float_format", "bytes_per_float", "uint8_bytes", "uint16_bytes",
    "uint32_bytes", "uint64_bytes", "int32_bytes", "c_int_bytes", "c_long_bytes", "c_float_bytes"})


def native_abi():
    """Observe the producer's C ABI; never infer an imported database's ABI."""
    ieee = (ctypes.sizeof(ctypes.c_double) == 8 and sys.float_info.radix == 2
        and sys.float_info.mant_dig == 53 and sys.float_info.max_exp == 1024
        and struct.pack("=d", 1.) == (b"\x00\x00\x00\x00\x00\x00\xf0\x3f" if sys.byteorder == "little" else b"\x3f\xf0\x00\x00\x00\x00\x00\x00"))
    return {"byte_order": sys.byteorder, "float_format": "ieee754_binary64" if ieee else "unsupported",
        "bytes_per_float": ctypes.sizeof(ctypes.c_double), "uint8_bytes": ctypes.sizeof(ctypes.c_uint8),
        "uint16_bytes": ctypes.sizeof(ctypes.c_uint16), "uint32_bytes": ctypes.sizeof(ctypes.c_uint32),
        "uint64_bytes": ctypes.sizeof(ctypes.c_uint64), "int32_bytes": ctypes.sizeof(ctypes.c_int32),
        "c_int_bytes": ctypes.sizeof(ctypes.c_int), "c_long_bytes": ctypes.sizeof(ctypes.c_long),
        "c_float_bytes": ctypes.sizeof(ctypes.c_float)}


def _error(reason):
    raise ValueError(_PREFIX + reason)


def _staged_relative(operand):
    if operand["role"] == "models":
        return MODEL_STAGING_PATH
    if operand["role"] == "ssi":
        return SSI_STAGING_PATH
    return "inputs/" + operand["role"] + "/" + str(operand["ordinal"])


def _compile(job, root):
    paths = {}
    for row in job["operands"]:
        paths.setdefault(row["role"], []).append(str(root / _staged_relative(row)))
    return compile_native_hmmer_preparation_job(job, input_paths=paths, output_directory=str(root))


def validate_preparation_plan(value):
    """Validate the separate preparation plan; perform no native execution."""
    plan = finite_json_copy(value)
    if (type(plan) is not dict or set(plan) != {"version", "identity", "requested_job",
            "attempt_directory", "policy"} or plan["version"] != PLAN_VERSION):
        _error("run_plan_required")
    request = validate_native_hmmer_preparation_requested_job(plan["requested_job"])
    _validate_identity(plan["identity"], request)
    policy = plan["policy"]
    if type(policy) is not dict or set(policy) != {"memory_bytes", "scratch_bytes", "wall_seconds"}:
        _error("explicit_policy_required")
    LocalJobPolicy(**policy)
    root = _absolute_directory(plan["attempt_directory"])
    job = request["native_hmmer_preparation"]
    if any(Path(row["path"]).is_relative_to(root) for row in job["operands"]):
        _error("supplied_operand_inside_attempt")
    if Path(job["software"]["executable"]).is_relative_to(root):
        _error("supplied_software_inside_attempt")
    _compile(job, root)
    return plan


def _failure(bundle, stage, code, role=None, **detail):
    bundle["failures"].append({"stage": stage, "code": _PREFIX + code,
        "role": role, "detail": detail})


def _problem(error):
    return {"reason": "missing" if isinstance(error, FileNotFoundError)
        else "unsafe_file" if isinstance(error, ValueError) else "io_error",
        "errno": error.errno if isinstance(error, OSError) else None}


def _measurement(root, relative):
    try:
        size, digest = _digest_file(_confined_file(root, relative))
        return (size, digest), None
    except (OSError, ValueError) as error:
        return (None, None), _problem(error)


def _put_pair(row, prefix, pair):
    row[prefix + "_size_bytes"], row[prefix + "_sha256"] = pair


def _pair(row, prefix):
    return row[prefix + "_size_bytes"], row[prefix + "_sha256"]


def _copy_bytes(source, destination, root, policy, expected_size):
    """Copy whole supplied bytes exclusively; a failed copy remains on disk."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _regular_reader(source) as reader:
        if os.fstat(reader.fileno()).st_size != expected_size:
            _error("copy_source_size_mismatch")
        _scratch(root, policy, expected_size)
        with destination.open("xb") as writer:
            for block in iter(lambda: reader.read(1024 * 1024), b""):
                writer.write(block)
                writer.flush()
                _scratch(root, policy)
            os.fsync(writer.fileno())


def _stage_inputs(root, job, policy, bundle):
    for operand in job["operands"]:
        role, ordinal = operand["role"], operand["ordinal"]
        row = {"role": role, "ordinal": ordinal, "format": operand["format"],
            "original_path": operand["path"], "relative_path": _staged_relative(operand),
            "artifact_ref": operand["artifact_ref"], "expected_sha256": operand["sha256"],
            "expected_size_bytes": operand["size_bytes"], "staged_sha256": None,
            "staged_size_bytes": None, "final_sha256": None, "final_size_bytes": None}
        bundle["inputs"].append(row)
        try:
            _copy_bytes(Path(operand["path"]), _confined_file(root, row["relative_path"]),
                root, policy, operand["size_bytes"])
        except _ScratchLimit as error:
            _failure(bundle, "staging", "scratch_limit", role, observed_bytes=error.observed,
                limit_bytes=error.limit, relative_path=row["relative_path"])
        except FileNotFoundError:
            _failure(bundle, "inputs", "input_missing", role, ordinal=ordinal)
        except OSError as error:
            _failure(bundle, "inputs", "input_io_error", role, ordinal=ordinal, errno=error.errno)
        except ValueError as error:
            code = "input_identity_mismatch" if str(error) == _PREFIX + "copy_source_size_mismatch" else "input_not_regular"
            _failure(bundle, "inputs", code, role, ordinal=ordinal)
        pair, _ = _measurement(root, row["relative_path"])
        _put_pair(row, "staged", pair)
        if pair[0] is not None and pair != (operand["size_bytes"], operand["sha256"]):
            _failure(bundle, "inputs", "input_identity_mismatch", role, ordinal=ordinal)


def _stage_copies(root, compiled, policy, bundle):
    sources = {(row["role"], row["ordinal"]): row for row in bundle["inputs"]}
    for copy in compiled["working_copies"]:
        role, ordinal = copy["operand_role"], copy["operand_ordinal"]
        source = sources[role, ordinal]
        relative = str(Path(copy["destination"]).relative_to(root))
        row = {"operand_role": role, "operand_ordinal": ordinal, "relative_path": relative,
            "mutable": copy["mutable"], "source_sha256": source["staged_sha256"],
            "initial_sha256": None, "initial_size_bytes": None, "final_sha256": None, "final_size_bytes": None}
        bundle["working_copies"].append(row)
        detail = {"operand_ordinal": ordinal, "relative_path": relative}
        if _pair(source, "staged") != (source["expected_size_bytes"], source["expected_sha256"]):
            _failure(bundle, "staging", "working_copy_not_staged", role, **detail)
            continue
        try:
            _copy_bytes(_confined_file(root, source["relative_path"]), _confined_file(root, relative),
                root, policy, source["staged_size_bytes"])
        except _ScratchLimit as error:
            _failure(bundle, "staging", "scratch_limit", role, observed_bytes=error.observed,
                limit_bytes=error.limit, relative_path=relative)
        except OSError as error:
            _failure(bundle, "staging", "working_copy_io_error", role, **detail, errno=error.errno)
        except ValueError:
            _failure(bundle, "staging", "working_copy_identity_mismatch", role, **detail)
        pair, _ = _measurement(root, relative)
        _put_pair(row, "initial", pair)
        if pair[0] is not None and pair != _pair(source, "staged"):
            _failure(bundle, "staging", "working_copy_identity_mismatch", role, **detail)


def _alimask_preflight_shared(root, job, bundle):
    """Prevent unsafe ali2model scans using the first MSA's shared operands."""
    if job["mode"] != "alignment_to_model":
        # The other modes never perform the unsafe alignment-to-model scan.
        # Their ordinary native range/format/alphabet refusals remain native.
        return
    from .hmmer_alignment_preparation_data import (
        read_hmmer_alignment_input, selected_alphabet, valid_alignment)
    from .hmmer_alignment_input_validation import input_decoding_local_valid
    from .hmmer_alignment_preparation_calculations import (
        reconstruct_alimask_model_map, resolve_alimask_map_context)

    entries = [(i, row) for i, row in enumerate(bundle["inputs"])
               if row["role"] == "alignment" and row["ordinal"] == 0]
    if len(entries) != 1:
        _error("alimask_input_slot_conflict")
    input_index, retained = entries[0]
    path = _confined_file(root, retained["relative_path"])
    occurrence = {"occurrence_id": "preflight:" + bundle["identity"]["attempt_id"] + "#/inputs/" + str(input_index),
        "direction": "input", "role": "alignment", "ordinal": 0,
        "artifact_ref": retained["artifact_ref"] or str(path), "sha256": retained["staged_sha256"],
        "size_bytes": retained["staged_size_bytes"], "completeness": "complete"}
    operation = bundle["operation"]
    settings = operation["settings"]
    parsed = read_hmmer_alignment_input(path.read_bytes(), declared_format=retained["format"],
        occurrence=occurrence, explicit_alphabet=selected_alphabet(settings),
        engine_version=operation["engine_version"])
    if any(item["code"] in {"occurrence_size_mismatch", "occurrence_digest_mismatch"} for item in parsed["issues"]):
        _failure(bundle, "inputs", "input_identity_mismatch", "alignment", ordinal=0)
        return
    first_key = occurrence["occurrence_id"] + "#alignment/0"
    candidates = [row for row in parsed["records"] if row["record_key"] == first_key
                  and row["occurrence_id"] == occurrence["occurrence_id"]]
    first = candidates[0] if len(candidates) == 1 else None
    decoding = parsed["input_decoding"]
    if not input_decoding_local_valid(decoding, alignment=first, settings=settings):
        _error("alimask_input_decoding_contract")
    if decoding["effective_alphabet"] is None:
        reason = ("alphabet_undetermined" if decoding["file_end_state"] == "alphabet_undetermined"
                  else "alphabet_source_semantics_unestablished")
        _failure(bundle, "preflight", "unsupported_alimask_model_map", "alignment", reason=reason)
        return
    malformed = "malformed_stockholm" if retained["format"] in {"stockholm", "pfam"} else "malformed_alignment"
    # Later MSAs or invalid suffix bytes remain retained, unprocessed evidence.
    if first is not None and not first["complete"] and any(
            row["record_key"] == occurrence["occurrence_id"] + "#alignment/1"
            and row["occurrence_id"] == occurrence["occurrence_id"]
            and row["original_events"][0]["kind"] == "header" for row in parsed["records"]):
        _failure(bundle, "preflight", "invalid_alimask_input", "alignment", reason="multiple_alignments")
        return
    if not valid_alignment(first):
        native = first.get("native_input") if first is not None else None
        unavailable = (first is None and decoding["file_end_state"] == "source_semantics_unestablished"
            or native is not None and any(problem["code"] == "native_source_semantics_unestablished"
                and problem["details"]["actual"] != "annotation_byte_interpretation" for problem in native["diagnostics"]))
        _failure(bundle, "preflight", "unsupported_alimask_model_map" if unavailable else "invalid_alimask_input",
                 "alignment", reason="decoder_source_semantics_unestablished" if unavailable else malformed)
        return
    first_codes = {item["code"] for item in first["issues"]}
    weight_events = [event for event in first["original_events"] if event["kind"] == "GS" and event["tag"] == "WT"]
    if "weight_invalid" in first_codes or weight_events and (len(weight_events) != len(first["rows"])
            or any(row["weight"]["state"] != "present" for row in first["rows"])):
        _failure(bundle, "preflight", "invalid_alimask_input", "alignment", reason="invalid_weights")
        return
    syntax_codes = {"alignment_invalid", "alignment_incomplete", "alignment_empty", "row_geometry_invalid",
        "row_symbols_invalid", "annotation_geometry_invalid", "annotation_join_ambiguous", "duplicate_sequence_name"}
    if first_codes & syntax_codes:
        _failure(bundle, "preflight", "invalid_alimask_input", "alignment", reason=malformed)
        return
    ranges = parse_ranges(settings[RANGE_FLAGS[job["mode"]]])
    if any(end > first["column_count"] for _, end in ranges):
        _failure(bundle, "preflight", "invalid_alimask_input", "alignment", reason="range_outside_alignment")
        return
    context = resolve_alimask_map_context(operation=operation, software=bundle["software"],
        source_occurrence=occurrence, requested_options=job["options"])
    reconstructed = reconstruct_alimask_model_map(first, settings=settings, map_reconstruction_context=context)
    if reconstructed["map"] is None:
        reasons = {"rf_missing": "rf_required", "alphabet_missing": "explicit_alphabet_required",
            "alphabet_incompatible": "unsupported_alignment_symbols", "weight_invalid": "invalid_weights",
            "weighting_unsupported": "weighted_map_not_established", "pb_sampling_unsupported": "pb_subsampling_not_established",
            "map_context_unavailable": "map_configuration_unavailable", "map_context_invalid": "map_configuration_unavailable",
            "alphabet_undetermined": "alphabet_undetermined",
            "alphabet_source_semantics_unestablished": "alphabet_source_semantics_unestablished"}
        code = reconstructed["issues"][0]["code"] if reconstructed["issues"] else None
        if code in {"alignment_invalid", "settings_invalid"}:
            _failure(bundle, "preflight", "invalid_alimask_input", "alignment", reason=malformed)
        elif code in reasons:
            _failure(bundle, "preflight", "unsupported_alimask_model_map", "alignment", reason=reasons[code])
        else:
            _error("alimask_reconstruction_failure_contract")
        return
    mapping = reconstructed["map"]
    if not mapping:
        _failure(bundle, "preflight", "invalid_alimask_input", "alignment", reason="empty_model_map")
        return
    for start, end in ranges:
        if start > mapping[-1]:
            _failure(bundle, "preflight", "unsafe_alimask_range", "alignment", start=start, end=end, last_match=mapping[-1])


def _preflight(root, job, bundle):
    """Validate dangerous native preconditions from already captured bytes only."""
    if bundle["failures"]:
        return
    paths = {r["role"]: _confined_file(root, r["relative_path"]) for r in bundle["inputs"]}
    if "models" in paths:
        with paths["models"].open("rb") as stream:
            prefix = stream.read(64)
        fmt = next(r["format"] for r in job["operands"] if r["role"] == "models")
        valid = (re.match(rb"HMMER3/[a-f]\s", prefix) is not None if fmt == "hmmer3_ascii"
            else prefix.startswith(b"HMMER2.0") if fmt == "hmmer2_ascii"
            else len(prefix) >= 4 and int.from_bytes(prefix[:4], sys.byteorder) in {0xe8ededb6, 0xe8ededb7, 0xe8ededb8, 0xe8ededb9, 0xe8ededb0, 0xe8ededba})
        if not valid:
            _failure(bundle, "preflight", "invalid_model_format", "models", reason="wrong_model_signature" if prefix else "no_model_bytes")
    if job["program"] == "alimask":
        _alimask_preflight_shared(root, job, bundle)
    if job["program"] == "hmmerfm-exactmatch":
        _preflight_exactmatch(root, job, bundle, paths)


def _preflight_exactmatch(root, job, bundle, paths):
    from .hmmer_fm_data import extract_hmmer_fm_database

    query = paths["queries"].read_bytes()
    if not query.endswith(b"\n"):
        _failure(bundle, "preflight", "invalid_exactmatch_queries", "queries", ordinal=max(0, query.count(b"\n")), reason="query_requires_final_lf")
    for ordinal, line in enumerate(query.split(b"\n")[:-1]):
        reason = ("query_empty" if not line else "query_exceeds_254_symbols" if len(line) > 254
            else "query_requires_literal_canonical_dna" if re.fullmatch(rb"[ACGTacgt]+", line) is None else None)
        if reason:
            _failure(bundle, "preflight", "invalid_exactmatch_queries", "queries", ordinal=ordinal, reason=reason)
    contract = job["input_metadata"]["producer_contract"]
    if contract["byte_order"] != bundle["native_abi"]["byte_order"]:
        _failure(bundle, "preflight", "incompatible_fm_abi", "fm_database", reason="producer_byte_order_mismatch")
        return
    if any(contract[k] != bundle["native_abi"][k] for k in ("uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes")):
        _failure(bundle, "preflight", "incompatible_fm_abi", "fm_database", reason="producer_integer_width_mismatch")
        return
    source_binding = job["input_metadata"].get("source_binding")
    if source_binding is not None and source_binding["source_sha256s"] != [r["sha256"] for r in job["operands"] if r["role"] == "source_sequences"]:
        _failure(bundle, "preflight", "source_binding_digest_mismatch", "source_sequences", reason="source_sha256_order_mismatch")
    row = next(r for r in bundle["inputs"] if r["role"] == "fm_database")
    occurrence = {"occurrence_id": "preflight:input:fm_database:0", "direction": "input", "role": "fm_database", "ordinal": 0,
        "artifact_ref": row["artifact_ref"] or "preflight:input:fm_database:0", "sha256": row["staged_sha256"],
        "size_bytes": row["staged_size_bytes"], "completeness": "complete"}
    decoded = extract_hmmer_fm_database(paths["fm_database"].read_bytes(), occurrence=occurrence, producer_contract=contract)
    codes = sorted({issue["code"] for issue in decoded["issues"]})
    if decoded["metadata"] and decoded["metadata"]["dna_reader_compatibility"] != "compatible":
        _failure(bundle, "preflight", "invalid_fm_database", "fm_database",
            reason="dna_only_reader" if decoded["metadata"]["alph_type"] != 0 else "fm_reader_header_incompatible", issue_codes=codes)
        return
    if not decoded["population"]["complete"] or not decoded["population"]["body_complete"] or decoded["issues"]:
        _failure(bundle, "preflight", "invalid_fm_database", "fm_database", reason="invalid_fm_framing", issue_codes=codes)
        return
    # F1's extractor validates complete structural arrays as well as framing;
    # every extraction issue above prevents this unsafe native reader call.


def _final_inputs(root, bundle):
    for row in bundle["inputs"]:
        pair, problem = _measurement(root, row["relative_path"])
        _put_pair(row, "final", pair)
        if problem is not None and row["staged_sha256"] is not None:
            _failure(bundle, "execution", "input_final_unavailable", row["role"], ordinal=row["ordinal"], **problem)
        if pair != _pair(row, "staged"):
            _failure(bundle, "execution", "immutable_input_changed", row["role"], ordinal=row["ordinal"])
    for row in bundle["working_copies"]:
        pair, problem = _measurement(root, row["relative_path"])
        _put_pair(row, "final", pair)
        detail = {"operand_ordinal": row["operand_ordinal"], "relative_path": row["relative_path"]}
        if problem is not None and row["initial_sha256"] is not None:
            _failure(bundle, "execution", "working_copy_final_unavailable", row["operand_role"], **detail, **problem)
        if not row["mutable"] and pair != _pair(row, "initial"):
            _failure(bundle, "execution", "immutable_working_copy_changed", row["operand_role"], **detail)


def _collect_outputs(root, job, bundle):
    for output in job["outputs"]:
        pair, problem = _measurement(root, output["relative_path"])
        if problem is None:
            bundle["artifacts"].append({**output, "size_bytes": pair[0], "sha256": pair[1]})
        elif problem["reason"] == "missing":
            _failure(bundle, "outputs", "missing_output", output["role"], relative_path=output["relative_path"])
        else:
            _failure(bundle, "outputs", "invalid_output", output["role"], relative_path=output["relative_path"], **problem)


def _validate_failures(bundle, root):
    if type(bundle["failures"]) is not list:
        _error("bundle_failures_required")
    input_roles = {r["role"] for r in bundle["requested_job"]["native_hmmer_preparation"]["operands"]}
    output_roles = {r["role"] for r in bundle["requested_job"]["native_hmmer_preparation"]["outputs"]}
    for failure in bundle["failures"]:
        if (type(failure) is not dict or set(failure) != {"stage", "code", "role", "detail"}
                or type(failure["code"]) is not str or failure["code"] not in FAILURE_CODES):
            _error("bundle_failure_shape")
        stages, fields = _FAILURES[failure["code"][len(_PREFIX):]]
        if (type(failure["stage"]) is not str or failure["stage"] not in stages or type(failure["detail"]) is not dict
                or set(failure["detail"]) != set(fields)
                or failure["role"] is not None and (type(failure["role"]) is not str
                    or failure["role"] not in input_roles | output_roles)):
            _error("bundle_failure_context")
        if failure["stage"] == "software" and failure["role"] is not None:
            _error("bundle_failure_role")
        for key, kind in fields.items():
            value = failure["detail"][key]
            if kind in {"uint", "int", "errno"}:
                valid = value is None and kind == "errno" or type(value) is int and (kind != "uint" or value >= 0)
            elif kind == "reason":
                valid = type(value) is str and value in {"missing", "unsafe_file", "io_error"}
            elif kind == "preflight_reason":
                valid = type(value) is str and value in PREFLIGHT_REASONS
            elif kind == "fm_issue_codes":
                from .hmmer_fm_data import ISSUE_CODES
                valid = type(value) is list and all(type(v) is str and v in ISSUE_CODES for v in value)
                valid = valid and value == sorted(set(value))
            else:
                valid = value is None and kind == "nullable_path" or type(value) is str
                if valid and value is not None:
                    # Validate syntax without trusting the current file type.
                    _confined_file(root / ".path-validation", value)
            if not valid:
                _error("bundle_failure_context_type")
        code, role, detail = failure["code"][len(_PREFIX):], failure["role"], failure["detail"]
        if code in PREFLIGHT_FAILURE_CONTEXT:
            relation = PREFLIGHT_FAILURE_CONTEXT[code]
            job = bundle["requested_job"]["native_hmmer_preparation"]
            if (role != relation["role"] or job["program"] not in relation["programs"]
                    or relation["reasons"] is not None and detail["reason"] not in relation["reasons"]):
                _error("bundle_preflight_failure_context")
            if code == "unsafe_alimask_range" and (job["mode"] != "alignment_to_model"
                    or (detail["start"], detail["end"]) not in parse_ranges(native_options(job)["--ali2model"])
                    or detail["start"] <= detail["last_match"]):
                _error("bundle_preflight_range_context")
            if code == "source_binding_digest_mismatch":
                binding = job["input_metadata"].get("source_binding")
                expected = [r["sha256"] for r in job["operands"] if r["role"] == "source_sequences"]
                if binding is None or binding["source_sha256s"] == expected:
                    _error("bundle_preflight_failure_context")
            if code == "incompatible_fm_abi":
                contract, abi = job["input_metadata"]["producer_contract"], bundle["native_abi"]
                mismatch = (contract["byte_order"] != abi["byte_order"] if detail["reason"] == "producer_byte_order_mismatch"
                    else any(contract[k] != abi[k] for k in ("uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes")))
                if not mismatch:
                    _error("bundle_preflight_failure_context")
        if ("ordinal" in detail or "operand_ordinal" in detail) and code != "invalid_exactmatch_queries":
            ordinal = detail.get("ordinal", detail.get("operand_ordinal"))
            if not any(r["role"] == role and r["ordinal"] == ordinal
                    for r in bundle["requested_job"]["native_hmmer_preparation"]["operands"]):
                _error("bundle_failure_operand_conflict")
        if failure["stage"] == "outputs":
            if not any(r["role"] == role and r["relative_path"] == detail["relative_path"]
                    for r in bundle["requested_job"]["native_hmmer_preparation"]["outputs"]):
                _error("bundle_failure_output_conflict")
        if code == "nonzero_returncode" and (role is not None or detail["returncode"] == 0
                or detail["returncode"] != bundle["returncode"]):
            _error("bundle_failure_returncode_conflict")
        if code == "command_unavailable" and (role is not None or bundle["returncode"] is not None):
            _error("bundle_failure_execution_conflict")
        if code == "scratch_limit" and ((failure["stage"] == "execution"
                and (role is not None or detail["relative_path"] is not None))
                or failure["stage"] == "staging" and (role not in input_roles or detail["relative_path"] is None)
                or detail["observed_bytes"] <= detail["limit_bytes"]):
            _error("bundle_failure_scratch_conflict")


def _has(bundle, code=None, *, role=None, **detail):
    return any((code is None or f["code"] == _PREFIX + code) and f["role"] == role
        and all(f["detail"].get(k) == v for k, v in detail.items()) for f in bundle["failures"])


def _validate_pair(row, prefix):
    size, digest = _pair(row, prefix)
    if not (size is None and digest is None or type(size) is int and size >= 0 and _sha(digest)):
        _error("bundle_measurement_pair_invalid")


def _validate_final(row, root):
    _validate_pair(row, "final")
    pair, _ = _measurement(root, row["relative_path"])
    if pair != _pair(row, "final"):
        _error("sealed_file_digest_mismatch:" + row["relative_path"])


def validate_preparation_bundle_files(value, directory):
    """Validate original associations and retained bytes, without reacquisition.

    A complete retained directory may be moved. Realized argv/environment still
    describe the original location; the owner record anchors it when present.
    """
    bundle = finite_json_copy(value)
    if type(bundle) is not dict or set(bundle) != _BUNDLE_FIELDS or bundle["version"] != BUNDLE_VERSION:
        _error("bundle_required")
    request = validate_native_hmmer_preparation_requested_job(bundle["requested_job"])
    _validate_identity(bundle["identity"], request)
    job, root = request["native_hmmer_preparation"], _absolute_directory(str(directory))
    if bundle["program"] != job["program"] or bundle["mode"] != job["mode"]:
        _error("bundle_request_conflict")
    abi = bundle["native_abi"]
    if (type(abi) is not dict or set(abi) != NATIVE_ABI_FIELDS
            or abi["byte_order"] not in {"little", "big"}
            or abi["float_format"] not in {"ieee754_binary64", "unsupported"}
            or any(type(abi[k]) is not int or abi[k] <= 0 for k in NATIVE_ABI_FIELDS - {"byte_order", "float_format"})
            or abi["float_format"] == "ieee754_binary64" and abi["bytes_per_float"] != 8):
        _error("bundle_native_abi_invalid")
    environment = bundle["environment"]
    if type(environment) is not dict or type(environment.get("TMPDIR")) is not str:
        _error("bundle_environment_conflict")
    original = _absolute_directory(str(Path(environment["TMPDIR"]).parent))
    if environment != _environment(job, original):
        _error("bundle_environment_conflict")
    compiled = _compile(job, original)
    if (bundle["realized_argv"] != compiled["argv"]
            or not recorded_operation_matches_compiled(bundle["operation"], compiled["operation"])):
        _error("bundle_realized_command_conflict")
    owner = _confined_file(root, OWNER_NAME)
    if owner.exists():
        plan = validate_preparation_plan(_read_json(owner, sealed=True))
        if (plan["identity"] != bundle["identity"] or plan["requested_job"] != request
                or plan["attempt_directory"] != str(original)):
            _error("bundle_owner_conflict")
    software = bundle["software"]
    if (type(software) is not dict or set(software) != {"executable", "expected_sha256", "actual_sha256", "declared_engine_version"}
            or software["executable"] != job["software"]["executable"]
            or software["expected_sha256"] != job["software"]["sha256"]
            or software["declared_engine_version"] != job["software"]["engine_version"]
            or software["actual_sha256"] is not None and not _sha(software["actual_sha256"])):
        _error("bundle_software_conflict")
    rc = bundle["returncode"]
    if rc is not None and type(rc) is not int:
        _error("bundle_returncode_required")
    try:
        started, finished = (datetime.fromisoformat(bundle[k]) for k in ("started_at", "finished_at"))
        if started.utcoffset() is None or finished.utcoffset() is None or finished < started:
            raise ValueError
    except (ValueError, TypeError) as error:
        raise ValueError(_PREFIX + "bundle_timestamp_conflict") from error
    _validate_failures(bundle, root)
    prevented = any(f["stage"] in {"software", "inputs", "staging", "preflight"}
        or f["code"] in {_PREFIX + "command_unavailable", _PREFIX + "scratch_limit"}
        for f in bundle["failures"])
    if ((rc is None and not prevented)
            or rc not in (None, 0) and not _has(bundle, "nonzero_returncode", returncode=rc)):
        _error("bundle_execution_failure_missing")
    if rc is not None and any(f["stage"] in {"software", "inputs", "staging", "preflight"} for f in bundle["failures"]):
        _error("execution_after_preexecution_failure")
    if rc is not None and software["actual_sha256"] != software["expected_sha256"]:
        _error("executed_software_identity_conflict")
    if software["actual_sha256"] is None and not _has(bundle, "software_unavailable"):
        _error("bundle_software_failure_missing")
    if software["actual_sha256"] not in {None, software["expected_sha256"]} and not _has(bundle, "software_digest_mismatch"):
        _error("bundle_software_failure_missing")
    inputs = bundle["inputs"]
    if type(inputs) is not list or len(inputs) != len(job["operands"]):
        _error("bundle_inputs_required")
    sources = {}
    for row, operand in zip(inputs, job["operands"]):
        expected = {"role": operand["role"], "ordinal": operand["ordinal"], "format": operand["format"],
            "original_path": operand["path"], "relative_path": _staged_relative(operand),
            "artifact_ref": operand["artifact_ref"], "expected_sha256": operand["sha256"],
            "expected_size_bytes": operand["size_bytes"]}
        if (type(row) is not dict or set(row) != _INPUT_FIELDS
                or type(row["ordinal"]) is not int or type(row["expected_size_bytes"]) is not int
                or any(row[k] != v for k, v in expected.items())):
            _error("bundle_input_identity_conflict")
        _validate_pair(row, "staged")
        _validate_final(row, root)
        sources[row["role"], row["ordinal"]] = row
        valid_input = _pair(row, "staged") == (operand["size_bytes"], operand["sha256"])
        failed = _has(bundle, role=row["role"], ordinal=row["ordinal"]) or _has(
            bundle, "scratch_limit", role=row["role"], relative_path=row["relative_path"])
        if not valid_input and (rc is not None or not failed):
            _error("bundle_input_capture_conflict")
        if _pair(row, "staged") != _pair(row, "final") and not _has(
                bundle, "immutable_input_changed", role=row["role"], ordinal=row["ordinal"]):
            _error("bundle_changed_input_failure_missing")
    copies = bundle["working_copies"]
    if type(copies) is not list or len(copies) != len(compiled["working_copies"]):
        _error("bundle_working_copies_required")
    for row, copy in zip(copies, compiled["working_copies"]):
        source = sources[copy["operand_role"], copy["operand_ordinal"]]
        expected = {"operand_role": copy["operand_role"], "operand_ordinal": copy["operand_ordinal"],
            "relative_path": str(Path(copy["destination"]).relative_to(original)),
            "mutable": copy["mutable"], "source_sha256": source["staged_sha256"]}
        if (type(row) is not dict or set(row) != _COPY_FIELDS or type(row["mutable"]) is not bool
                or type(row["operand_ordinal"]) is not int
                or any(row[k] != v for k, v in expected.items())):
            _error("bundle_working_copy_identity_conflict")
        _validate_pair(row, "initial")
        _validate_final(row, root)
        detail = {"operand_ordinal": row["operand_ordinal"], "relative_path": row["relative_path"]}
        failed = _has(bundle, role=row["operand_role"], **detail) or _has(
            bundle, "scratch_limit", role=row["operand_role"], relative_path=row["relative_path"])
        if (row["initial_sha256"] is None or _pair(row, "initial") != _pair(source, "staged")) and (rc is not None or not failed):
            _error("bundle_working_copy_capture_conflict")
        if not row["mutable"] and _pair(row, "initial") != _pair(row, "final") and not _has(
                bundle, "immutable_working_copy_changed", role=row["operand_role"], **detail):
            _error("bundle_changed_working_copy_failure_missing")
        if row["initial_sha256"] is not None and row["final_sha256"] is None and not _has(
                bundle, "working_copy_final_unavailable", role=row["operand_role"], **detail):
            _error("bundle_missing_working_copy_failure_missing")
    selected, seen = {row["role"]: row for row in job["outputs"]}, set()
    if type(bundle["artifacts"]) is not list:
        _error("bundle_artifacts_required")
    for row in bundle["artifacts"]:
        if (type(row) is not dict or set(row) != _ARTIFACT_FIELDS or type(row["role"]) is not str
                or row["role"] not in selected or row["role"] in seen
                or any(row[k] != selected[row["role"]][k] for k in ("format", "relative_path"))
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0 or not _sha(row["sha256"])):
            _error("bundle_output_identity_conflict")
        seen.add(row["role"])
        if _digest_file(_confined_file(root, row["relative_path"])) != (row["size_bytes"], row["sha256"]):
            _error("sealed_artifact_digest_mismatch:" + row["relative_path"])
    for role in selected.keys() - seen:
        relative = selected[role]["relative_path"]
        pair, problem = _measurement(root, relative)
        code = "missing_output" if problem and problem["reason"] == "missing" else "invalid_output"
        if pair[0] is not None or not _has(bundle, code, role=role, relative_path=relative):
            _error("bundle_missing_output_conflict")
    return bundle


def run_native_hmmer_preparation(value):
    """Execute a fresh selected attempt once, or return its sealed original."""
    plan = validate_preparation_plan(value)
    root, request = Path(plan["attempt_directory"]), plan["requested_job"]
    job = request["native_hmmer_preparation"]
    owner, manifest = root / OWNER_NAME, root / BUNDLE_NAME
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        if not _confined_file(root, OWNER_NAME).is_file():
            _error("attempt_not_exclusively_owned")
        if _read_json(owner, sealed=True) != plan:
            _error("attempt_identity_conflict")
        if not _confined_file(root, "bundle.json").is_file():
            _error("unsealed_attempt_execution_uncertain")
        saved = _read_json(manifest, sealed=True)
        if saved.get("identity") != plan["identity"] or saved.get("requested_job") != request:
            _error("sealed_manifest_identity_conflict")
        return validate_preparation_bundle_files(saved, root)
    _atomic_new(owner, plan)
    for name in ("inputs", "tmp", "cache"):
        (root / name).mkdir()
    compiled = _compile(job, root)
    bundle = {"version": BUNDLE_VERSION, "identity": plan["identity"], "requested_job": request,
        "program": job["program"], "mode": job["mode"], "operation": compiled["operation"],
        "software": {"executable": job["software"]["executable"], "expected_sha256": job["software"]["sha256"],
            "actual_sha256": None, "declared_engine_version": job["software"]["engine_version"]},
        "realized_argv": compiled["argv"], "environment": _environment(job, root), "inputs": [],
        "working_copies": [], "returncode": None, "artifacts": [], "failures": [],
        "started_at": _now(), "finished_at": None, "native_abi": native_abi()}
    try:
        _, actual = _digest_file(Path(job["software"]["executable"]))
        bundle["software"]["actual_sha256"] = actual
        if actual != job["software"]["sha256"]:
            _failure(bundle, "software", "software_digest_mismatch")
        elif not os.access(job["software"]["executable"], os.X_OK):
            _failure(bundle, "software", "software_not_executable")
    except (OSError, ValueError) as error:
        _failure(bundle, "software", "software_unavailable", **_problem(error))
    _stage_inputs(root, job, plan["policy"], bundle)
    _stage_copies(root, compiled, plan["policy"], bundle)
    _preflight(root, job, bundle)
    outputs = {row["role"]: _confined_file(root, row["relative_path"]) for row in job["outputs"]}
    for path in outputs.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    if not bundle["failures"]:
        try:
            _scratch(root, plan["policy"])
            with outputs["stdout"].open("xb") as stdout, outputs["stderr"].open("xb") as stderr:
                outcome = subprocess.run(compiled["argv"], cwd=root, env=bundle["environment"],
                    stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, check=False)
            bundle["returncode"] = outcome.returncode
            if outcome.returncode:
                _failure(bundle, "execution", "nonzero_returncode", returncode=outcome.returncode)
            _scratch(root, plan["policy"])
        except _ScratchLimit as error:
            _failure(bundle, "execution", "scratch_limit", observed_bytes=error.observed,
                limit_bytes=error.limit, relative_path=None)
        except OSError as error:
            _failure(bundle, "execution", "command_unavailable", errno=error.errno)
    _final_inputs(root, bundle)
    _collect_outputs(root, job, bundle)
    bundle["finished_at"] = _now()
    validate_preparation_bundle_files(bundle, root)
    _atomic_new(manifest, bundle)
    return bundle


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        _error("exact_plan_file_operand_required")
    plan = _read_json(Path(arguments[0]))
    result = run_native_hmmer_preparation(plan)
    print(json.dumps({"version": result["version"], "returncode": result["returncode"],
        "failure_count": len(result["failures"]), "bundle_path": str(Path(plan["attempt_directory"]) / "bundle.json")}))
    return 0 if not result["failures"] else 1


__all__ = ["PLAN_VERSION", "BUNDLE_VERSION", "OWNER_NAME", "BUNDLE_NAME", "INPUT_DIRECTORY",
    "MODEL_STAGING_PATH", "SSI_STAGING_PATH", "NATIVE_ABI_FIELDS", "FAILURE_CODES", "PREFLIGHT_REASONS", "PREFLIGHT_FAILURE_CONTEXT", "native_abi",
    "validate_preparation_plan", "run_native_hmmer_preparation", "validate_preparation_bundle_files"]


if __name__ == "__main__":
    raise SystemExit(main())
