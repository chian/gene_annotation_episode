"""Original native_hmmer_preparation_result_worker scientific values and explicit received-record contracts."""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.a101.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_preparation_capture_contracts import _shape
from copy import deepcopy

PREFIX = "native_hmmer_preparation_"

def failure(stage, code, record_key=None):
    return {"stage": stage, "code": code, "record_key": record_key}

def validate_failures(rows):
    if type(rows) is not list or any(type(row) is not dict or set(row) != {
            "stage", "code", "record_key"} or any(type(row[k]) is not str or not row[k]
            for k in ("stage", "code")) or row["record_key"] is not None and
            (type(row["record_key"]) is not str or not row["record_key"]) for row in rows):
        raise ContractError(PREFIX + "result_failures_invalid")
    return rows

def unique_failures(rows):
    validate_failures(rows)
    return list({(r["stage"], r["code"], r["record_key"]): r for r in rows}.values())

def qualified_occurrences(bundle, bundle_ref, capture):
    """Pure association reconstruction from the original, validated capture.

    Input descriptors describe FINAL bytes. Only bytes equal to both the staged
    and expected identity qualify as original operands for the pure grader.
    """
    capture = _shape(capture)
    if (not capture["bundle_validated"] or capture["bundle_artifact_ref"] != bundle_ref
            or type(bundle_ref) is not str or not bundle_ref.startswith("artifact_")):
        raise ContractError(PREFIX + "grading_validated_capture_required")
    declared = {}
    sources = {(r["role"], r["ordinal"]): r for r in bundle["inputs"]}
    for collection, direction in (("inputs", "input"), ("working_copies", "working_copy"),
                                   ("artifacts", "output")):
        for index, row in enumerate(bundle[collection]):
            role = row["operand_role"] if direction == "working_copy" else row["role"]
            ordinal = row["operand_ordinal"] if direction == "working_copy" else row.get("ordinal", 0)
            fmt = sources[role, ordinal]["format"] if direction == "working_copy" else row["format"]
            sha = row["sha256"] if direction == "output" else row["final_sha256"]
            size = row["size_bytes"] if direction == "output" else row["final_size_bytes"]
            complete = bundle["returncode"] == 0 and not bundle["failures"]
            if direction == "input":
                complete = (sha is not None and sha == row["staged_sha256"] == row["expected_sha256"]
                    and size == row["staged_size_bytes"] == row["expected_size_bytes"])
            elif direction == "working_copy" and not row["mutable"]:
                original = sources[role, ordinal]
                complete = (sha is not None and sha == row["initial_sha256"] == row["source_sha256"]
                    == original["expected_sha256"] and size == row["initial_size_bytes"]
                    == original["expected_size_bytes"])
            key = direction, role, ordinal, row["relative_path"]
            declared[key] = {"occurrence_id": bundle_ref + "#/" + collection + "/" + str(index),
                "direction": direction, "role": role, "ordinal": ordinal, "format": fmt,
                "relative_path": row["relative_path"], "sha256": sha, "size_bytes": size,
                "completeness": "complete" if complete else "partial"}
    result, seen, problems = [], set(), deepcopy(capture["failures"])
    for row in capture["artifacts"]:
        key = tuple(row[k] for k in ("direction", "role", "ordinal", "relative_path"))
        actual = declared.get(key)
        if (actual is None or key in seen or row["format"] != actual["format"]
                or actual["sha256"] is None or row["artifact_ref"] != "artifact_" + actual["sha256"]):
            raise ContractError(PREFIX + "grading_occurrence_association_conflict")
        seen.add(key)
        result.append({**actual, "artifact_ref": row["artifact_ref"]})
        if row["direction"] == "input" and actual["completeness"] != "complete":
            problems.append(failure("custody", PREFIX + "input_not_original_selected_bytes", actual["occurrence_id"]))
    for index, row in enumerate(bundle["failures"]):
        matches = [r for r in result if r["role"] == row["role"] and (
            r["direction"] == "input" and row["detail"].get("ordinal") == r["ordinal"]
            or r["direction"] == "working_copy" and row["detail"].get("operand_ordinal") == r["ordinal"]
            or r["direction"] == "output" and row["stage"] == "outputs")]
        problems.append(failure(row["stage"], row["code"],
            matches[0]["occurrence_id"] if len(matches) == 1 else bundle_ref + "#/failures/" + str(index)))
    if bundle["returncode"] != 0:
        problems.append(failure("native", PREFIX + "native_execution_unsuccessful", bundle_ref + "#/returncode"))
    return result, unique_failures(problems)

def effective_metadata(bundle, occurrences, *, include_map_context=True):
    """Project original producer facts; imported declarations stay explicit.

    This function authenticates no external producer history. A current build
    has its own recorded ABI, attempt and input/output association. A caller's
    imported declaration remains a declaration, including any mismatch.
    """
    if type(include_map_context) is not bool:
        raise ContractError(PREFIX + "map_context_selection_invalid")
    job = bundle["requested_job"]["native_hmmer_preparation"]
    original = deepcopy(job["input_metadata"])
    metadata, problems = deepcopy(original), []
    lookup = {(r["direction"], r["role"], r["ordinal"]): r for r in occurrences}
    if bundle["program"] == "alimask" and include_map_context:
        from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_alignment_preparation_calculations import resolve_alimask_map_context
        alignment = lookup.get(("input", "alignment", 0))
        if alignment is not None and alignment["completeness"] == "complete":
            occurrence = {key: alignment[key] for key in ("occurrence_id", "direction", "role", "ordinal",
                "artifact_ref", "sha256", "size_bytes", "completeness")}
            metadata["map_reconstruction_context"] = resolve_alimask_map_context(operation=bundle["operation"],
                software=bundle["software"], source_occurrence=occurrence, requested_options=job["options"])
    source = lookup.get(("input", "models", 0))
    copy = lookup.get(("working_copy", "models", 0))
    valid_copy = (source is not None and copy is not None
        and source["completeness"] == copy["completeness"] == "complete"
        and source["sha256"] == copy["sha256"] and bundle["returncode"] is not None)
    if bundle["program"] in {"hmmconvert", "hmmfetch", "hmmpress"}:
        bindings = []
        for row in occurrences:
            if row["direction"] != "output" or row["role"] not in {
                    "ssi", "binary_models", "ssi_index", "msv_profiles", "remaining_profiles"}:
                continue
            selected = (bundle["program"] == "hmmpress" or
                        (bundle["program"], bundle["mode"]) == ("hmmfetch", "index"))
            if valid_copy and selected:
                bindings.append({"artifact_occurrence_id": row["occurrence_id"],
                    "source_occurrence_id": source["occurrence_id"], "source_sha256": source["sha256"],
                    "producer_attempt_id": bundle["identity"]["attempt_id"],
                    "staged_source_stem": copy["relative_path"], "actual_relative_path": row["relative_path"]})
            else:
                problems.append(failure("metadata", PREFIX + "artifact_binding_unavailable", row["occurrence_id"]))
        if bindings:
            metadata["artifact_bindings"] = bindings
    if bundle["program"] == "makehmmerdb":
        abi = bundle["native_abi"]
        contract = {"format": "hmmer_fm_3_4", "engine_version": bundle["operation"]["engine_version"],
            **{key: abi[key] for key in ("byte_order", "uint8_bytes", "uint16_bytes", "uint32_bytes", "uint64_bytes", "int32_bytes")}}
        if "producer_contract" in original and original["producer_contract"] != contract:
            problems.append(failure("metadata", PREFIX + "supplied_fm_producer_contract_conflict"))
        metadata["producer_contract"] = contract
        database = lookup.get(("output", "fm_database", 0))
        sources = [r for r in occurrences if r["direction"] == "input" and r["role"] == "sequences"]
        if database is not None and sources and all(r["completeness"] == "complete" for r in sources):
            binding = {"database_occurrence_id": database["occurrence_id"],
                "source_occurrence_ids": [r["occurrence_id"] for r in sources],
                "source_sha256s": [r["sha256"] for r in sources],
                "producer_attempt_id": bundle["identity"]["attempt_id"]}
            if "source_binding" in original and original["source_binding"] != binding:
                problems.append(failure("metadata", PREFIX + "supplied_fm_source_binding_conflict"))
            metadata["source_binding"] = binding
    return metadata, problems

def grading_context(bundle, occurrences, metadata):
    return {"version": PREFIX + "grading_v1", "operation": deepcopy(bundle["operation"]),
        "formats": {r["occurrence_id"]: r["format"] for r in eligible_occurrences(occurrences)},
        "metadata": deepcopy(metadata), "native_abi": deepcopy(bundle["native_abi"]),
        "requested_parameters": deepcopy(bundle["requested_job"]["native_hmmer_preparation"]["grading_parameters"])}

def eligible_occurrences(occurrences):
    return [r for r in occurrences if r["direction"] == "output" or
            r["direction"] == "input" and r["completeness"] == "complete"]
