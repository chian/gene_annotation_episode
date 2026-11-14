"""Prepare bounded paired BLAST grading and publish authenticated selected facts.

Acquisition belongs to the original-result adapter. Parsing and calculation run
in the caller-limited deterministic worker. Publication uses only frozen rows;
closed-return validation neither calculates again nor reads producer paths.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from .acquisition import AcquisitionError
from .blast_pairwise_result_views import (NATIVE_BLAST_METRICS, projected_measurements,
                                         row_schema, validate_native_blast_result_selector)
from .domain import ContractError, identity, validate_schema
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from .materials import artifact_file, artifact_path
from .native_blast_contracts import finite_json_copy, native_blast_digest
from .native_blast_result_worker import record_key, write_json
from .native_hmmer_result_publication import _subject_chunks
from .tool_grading_artifacts import retain_tool_grading


_PREPARED_VERSION = "native_blast_prepared_grading_v1"
_SCHEMA_VERSION = "native_blast_retained_grading_v1"
_ARTIFACT_FIELDS = ("bundle_artifact_ref", "source_grading_artifact_ref", "grading_artifact_ref",
                    "sheet_artifact_ref", "scores_artifact_ref", "selected_rows_artifact_ref")


def _failure(stage, code, record_key=None):
    return {"stage": stage, "code": code, "record_key": record_key}


def _read_json(store, ref):
    with artifact_path(store, ref).open(encoding="utf-8") as stream:
        return finite_json_copy(json.load(stream))


def _original_bundle(store, bundle, bundle_artifact_ref, policy):
    from .native_blast_acquisition import validate_original_bundle
    if _read_json(store, bundle_artifact_ref) != bundle:
        raise ContractError("native_blast_captured_bundle_identity_mismatch")
    # Original-attempt qualification is supplied by acquisition. Revalidate all
    # manifest/request/compiler relationships without touching original paths.
    try:
        root = Path(bundle["environment"]["TMPDIR"]).parent
        plan = {"version": "native_blast_run_plan_v1", "identity": bundle["identity"],
            "requested_job": bundle["requested_job"], "attempt_directory": str(root),
            "policy": policy.to_dict()}
        validate_original_bundle(bundle, plan)
    except (ValueError, KeyError, TypeError) as error:
        raise ContractError("native_blast_original_bundle_invalid") from error


def _captured_paths(store, bundle, artifacts):
    declared, paths, failures, seen = {}, [], [], set()
    for kind, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        for row in rows:
            key = (row["role"], row["format"], row["relative_path"])
            if key in declared:
                raise ContractError("native_blast_duplicate_bundle_artifact")
            declared[key] = kind, row
    for item in artifacts:
        if type(item) is not dict or set(item) != {"role", "format", "relative_path", "artifact_ref"}:
            raise ContractError("native_blast_captured_artifact_shape_invalid")
        key = (item["role"], item["format"], item["relative_path"])
        if key not in declared or key in seen:
            raise ContractError("native_blast_captured_artifact_binding_invalid")
        seen.add(key)
        kind, native = declared[key]
        expected = native["actual_sha256"] if kind == "input" else native["sha256"]
        try:
            stored = store.get(item["artifact_ref"])
            if (stored.get("record_type") != "artifact" or stored["sha256"] != expected
                    or stored["size"] != native["size_bytes"]):
                raise ContractError("native_blast_captured_artifact_digest_mismatch")
            if kind == "input" and (expected != native["expected_sha256"]
                    or native["size_bytes"] != native["expected_size_bytes"]):
                raise ContractError("native_blast_input_not_original_selected_bytes")
            paths.append({**item, "kind": kind, "path": str(artifact_path(store, item["artifact_ref"]))})
        except (ValueError, OSError) as error:
            failures.append(_failure("custody", str(error) if isinstance(error, ValueError)
                                     else "native_blast_captured_artifact_unreadable"))
    for key in declared.keys() - seen:
        failures.append(_failure("custody", "native_blast_captured_artifact_missing:" + key[0]))
    return paths, sorted(failures, key=lambda row: (row["stage"], row["code"]))


def _binding_snapshots(store, bundle):
    snapshots = {}
    for binding in bundle["operand_bindings"]:
        for key in ("subject_ref", "reference_ref"):
            ref = binding[key]
            if ref is None or ref in snapshots:
                continue
            try:
                record = store.get(ref)
                digest = hashlib.sha256()
                for chunk in _subject_chunks(store, ref):
                    digest.update(chunk)
                snapshots[ref] = {"record_type": record["record_type"],
                    "length": store.subject_length(ref), "molecule": store.subject_molecule(ref),
                    "sequence_sha256": digest.hexdigest(), "accession": record.get("accession"), "error": None}
            except (ValueError, OSError, KeyError, UnicodeError) as error:
                snapshots[ref] = {"error": "native_blast_store_binding_unavailable", "detail": str(error)}
    return snapshots


def prepare_native_blast_grading(store, *, bundle, bundle_artifact_ref, artifacts,
                                 directory, policy, selector):
    bundle, artifacts = finite_json_copy(bundle), finite_json_copy(artifacts)
    if not isinstance(policy, LocalJobPolicy):
        raise ContractError("native_blast_local_job_policy_required")
    selector = validate_native_blast_result_selector(selector, program=bundle["program"])
    _original_bundle(store, bundle, bundle_artifact_ref, policy)
    paths, failures = _captured_paths(store, bundle, artifacts)
    failures += [_failure(row["stage"], row["code"]) for row in bundle["failures"]]
    if bundle["returncode"] != 0:
        failures.append(_failure("native", "native_blast_native_execution_unsuccessful"))
    directory = Path(directory).resolve() / "native-blast-grading"
    fingerprint = native_blast_digest({"bundle": bundle, "bundle_artifact_ref": bundle_artifact_ref,
        "artifacts": artifacts, "policy": policy.to_dict(), "selector": selector})
    if directory.exists():
        intent, saved = directory / "intent.json", directory / "prepared.json"
        if not intent.is_file() or json.loads(intent.read_text())["request_sha256"] != fingerprint:
            raise ContractError("native_blast_grading_directory_identity_conflict")
        if not saved.is_file():
            raise ContractError("native_blast_grading_original_preparation_incomplete")
        prepared = json.loads(saved.read_text())
        original_failures = {(row["stage"], row["code"], row.get("record_key")) for row in prepared["failures"]}
        if any((row["stage"], row["code"], row.get("record_key")) not in original_failures for row in failures):
            raise ContractError("native_blast_grading_retained_artifact_changed")
        for field in _ARTIFACT_FIELDS:
            if prepared[field] is not None:
                artifact_path(store, prepared[field])
        stable = _read_json(store, prepared["source_grading_artifact_ref"])["grading"]
        for ref in [stable.get("complete_rows_artifact_ref"), *stable.get("sequence_artifact_refs", {}).values()]:
            if ref is not None:
                artifact_path(store, ref)
        return prepared
    directory.mkdir(parents=True)
    write_json(directory / "intent.json", {"request_sha256": fingerprint})
    plan = {"version": "native_blast_grading_plan_v1", "bundle": bundle,
        "artifacts": paths, "directory": str(directory), "selector": selector,
        "binding_snapshots": _binding_snapshots(store, bundle), "failures": failures}
    write_json(directory / "plan.json", plan)
    prepared = {"version": _PREPARED_VERSION, "bundle_artifact_ref": bundle_artifact_ref,
        **{field: None for field in _ARTIFACT_FIELDS if field != "bundle_artifact_ref"},
        "failures": failures, "numerical_complete": False}
    receipt = None
    try:
        for name in ("tmp", "cache"):
            (directory / name).mkdir()
        check_scratch_budget(directory, policy)
        result = run_local_job([sys.executable, "-m", "gene_annotation_episode.native_blast_result_worker",
            str(directory / "plan.json")], cwd=directory, policy=policy,
            stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr",
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]),
                 **{key: str(directory / "tmp") for key in ("TMPDIR", "TMP", "TEMP")},
                 "XDG_CACHE_HOME": str(directory / "cache")})
        receipt = result.metadata
        if result.returncode != 0:
            failures.append(_failure("worker", "native_blast_grading_worker_nonzero"))
    except (AcquisitionError, OSError, ValueError) as error:
        failures.append(_failure("worker", getattr(error, "code", "native_blast_grading_worker_failed")))
        receipt = {"exception_type": type(error).__name__, "detail": str(error),
                   "operational": getattr(error, "operational", None)}
    write_json(directory / "worker-receipt.json", receipt)
    manifest = {}
    try:
        manifest = json.loads((directory / "worker-result.json").read_text())
    except (ValueError, OSError):
        failures.append(_failure("worker", "native_blast_grading_manifest_unavailable"))
    failures = list({(row["stage"], row["code"], row.get("record_key")): row
        for row in [*failures, *manifest.get("failures", [])]}.values())
    for field, name, media in (("sheet_artifact_ref", "sheet.json", "application/json"),
            ("scores_artifact_ref", "scores.json", "application/json"),
            ("selected_rows_artifact_ref", "selected-rows.ndjson", "application/x-ndjson")):
        if (directory / name).is_file():
            prepared[field] = artifact_file(store, directory / name, media)
    retained = [{"role": name, "artifact_ref": artifact_file(store, directory / name)}
        for name in ("diagnostics.json", "worker.stdout", "worker.stderr", "worker-result.json", "worker-receipt.json")
        if (directory / name).is_file()]
    rows_ref = (artifact_file(store, directory / "complete-rows.ndjson", "application/x-ndjson")
                if (directory / "complete-rows.ndjson").is_file() else None)
    sequences = {axis: artifact_file(store, directory / ("sequence-" + axis + ".txt"), "text/plain")
        for axis in ("query", "reference") if (directory / ("sequence-" + axis + ".txt")).is_file()}
    prepared.update(failures=failures, numerical_complete=bool(manifest.get("numerical_complete"))
        and all(prepared[field] is not None for field in ("sheet_artifact_ref", "scores_artifact_ref", "selected_rows_artifact_ref"))
        and rows_ref is not None and not failures)
    stable = {"schema": _SCHEMA_VERSION, "bundle_sha256": native_blast_digest(bundle),
        "sheet_artifact_ref": prepared["sheet_artifact_ref"], "sheet_schema": manifest.get("sheet_schema"),
        "scores_artifact_ref": prepared["scores_artifact_ref"], "scores_schema": manifest.get("scores_schema"),
        "complete_rows_artifact_ref": rows_ref, "sequence_artifact_refs": sequences,
        "captured_artifacts": [{k: v for k, v in row.items() if k != "path"} for row in paths]}
    prepared["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=bundle_artifact_ref, grading=stable)
    selected = {**stable, "source_grading_artifact_ref": prepared["source_grading_artifact_ref"],
        "selected_rows_artifact_ref": prepared["selected_rows_artifact_ref"],
        "selected_rows_schema": "native_blast_selected_row_v1", "selector": selector,
        "failures": failures, "numerical_complete": prepared["numerical_complete"],
        "diagnostic_artifacts": retained, "worker_receipt": receipt}
    prepared["grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=bundle_artifact_ref, grading=selected)
    write_json(directory / "prepared.json", prepared)
    return prepared


def _qualified_grading(store, source_ref, bundle, prepared, selector):
    if (type(prepared) is not dict or set(prepared) != {"version", *_ARTIFACT_FIELDS, "failures", "numerical_complete"}
            or prepared["version"] != _PREPARED_VERSION):
        raise ContractError("native_blast_prepared_grading_required")
    source = store.get(source_ref)
    if (source.get("record_type") != "source" or source.get("provider") != "episode.execution_result"
            or source.get("origin") != "tool" or source.get("version") != "native_blast_bundle_v1"
            or source.get("artifact_ref") != prepared["bundle_artifact_ref"]
            or prepared["source_grading_artifact_ref"] not in source.get("auxiliary_artifact_refs", [])
            or source.get("accession") != "native_blast_" + native_blast_digest(bundle["identity"])
            or source.get("retrieved_at") != bundle["finished_at"]):
        raise ContractError("native_blast_publication_source_custody_mismatch")
    if _read_json(store, prepared["bundle_artifact_ref"]) != bundle:
        raise ContractError("native_blast_captured_bundle_identity_mismatch")
    selected = _read_json(store, prepared["grading_artifact_ref"])
    original = _read_json(store, prepared["source_grading_artifact_ref"])
    for envelope in (selected, original):
        if (set(envelope) != {"schema", "provider", "native_artifact_ref", "grading"}
                or envelope["schema"] != "tool_grading_artifact_v1"
                or envelope["provider"] != source["provider"] or envelope["native_artifact_ref"] != source["artifact_ref"]):
            raise ContractError("native_blast_grading_source_custody_mismatch")
    grading, stable = selected["grading"], original["grading"]
    if (grading.get("schema") != _SCHEMA_VERSION or grading.get("bundle_sha256") != native_blast_digest(bundle)
            or grading.get("selector") != selector or grading.get("failures") != prepared["failures"]
            or grading.get("numerical_complete") != prepared["numerical_complete"]
            or any(grading.get(field) != prepared[field] for field in _ARTIFACT_FIELDS
                   if field not in {"bundle_artifact_ref", "grading_artifact_ref"})
            or any(grading.get(field) != value for field, value in stable.items())):
        raise ContractError("native_blast_prepared_grading_identity_mismatch")
    for field in ("sheet_artifact_ref", "scores_artifact_ref", "complete_rows_artifact_ref"):
        if stable.get(field) is not None:
            artifact_path(store, stable[field])
    captured = [{k: v for k, v in row.items() if k != "kind"} for row in stable["captured_artifacts"]]
    _, custody_failures = _captured_paths(store, bundle, captured)
    original_failures = {(row["stage"], row["code"]) for row in prepared["failures"]}
    if any((row["stage"], row["code"]) not in original_failures for row in custody_failures):
        raise ContractError("native_blast_retained_capture_changed")
    if any(row["artifact_ref"] not in source["auxiliary_artifact_refs"] for row in captured):
        raise ContractError("native_blast_source_captured_artifact_missing")
    return grading


def _frozen_rows(store, grading, selector, bundle):
    selected_ref, rows_ref = grading["selected_rows_artifact_ref"], grading["complete_rows_artifact_ref"]
    if selected_ref is None:
        return []
    if rows_ref is None:
        raise ContractError("native_blast_complete_rows_unavailable")
    requested = selector["projection"]
    selection = requested["rows"]
    wanted = selection.get("record_keys")
    rows, expected, seen, ordinal = [], [], set(), 0
    with artifact_path(store, rows_ref).open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["family"] != requested["family"]:
                continue
            if row["record_key"] in seen:
                raise ContractError("native_blast_complete_row_duplicate")
            seen.add(row["record_key"])
            if row["record_key"] != record_key(bundle, row["search_key"], row["family"], row["hit_ordinal"], row["hsp_ordinal"]):
                raise ContractError("native_blast_complete_row_identity_mismatch")
            chosen = (row["record_key"] in wanted if wanted is not None else
                      selection["offset"] <= ordinal < selection["offset"] + selection["limit"])
            if chosen:
                values, unavailable = projected_measurements(row, requested["metrics"])
                rows.append(row)
                expected.append({"version": "native_blast_selected_row_v1", "family": row["family"],
                    "record_key": row["record_key"], "native_ordinal": ordinal,
                    "measurements": values, "unavailable": unavailable})
            ordinal += 1
    with artifact_path(store, selected_ref).open(encoding="utf-8") as stream:
        actual = [json.loads(line) for line in stream]
    if actual != expected:
        raise ContractError("native_blast_selected_rows_frozen_measurement_mismatch")
    return list(zip(rows, expected))


def _validate_sequence(store, operand, reference, *, scope=None, intervals=()):
    if operand["binding_error"]:
        raise ContractError(operand["binding_error"])
    if (store.subject_length(reference) != operand["length"]
            or store.subject_molecule(reference) != operand["molecule"]):
        raise ContractError("native_blast_subject_molecule_or_length_mismatch")
    digest = hashlib.sha256()
    for chunk in _subject_chunks(store, reference):
        digest.update(chunk)
    if digest.hexdigest() != operand["sequence_sha256"]:
        raise ContractError("native_blast_subject_sequence_mismatch")
    if scope is not None:
        if reference not in store.reference_subset([reference], scope):
            raise ContractError("native_blast_subject_outside_scope")
        for interval in intervals:
            if not (type(interval) is list and len(interval) == 2 and all(type(v) is int for v in interval)
                    and 0 <= interval[0] < interval[1] <= operand["length"]):
                raise ContractError("native_blast_subject_interval_invalid")
            footprint = store.map_segments(reference, [{"start": interval[0], "end": interval[1]}])
            if store.roots(reference) and (not footprint or not store.scope_covers(footprint, scope)):
                raise ContractError("native_blast_subject_interval_outside_scope")


def _record(store, kind, payload, scope, publish):
    if publish:
        return store.put(kind, payload, origin="tool", scope=scope)["id"]
    ref = identity(kind, {"origin": "tool", "record": payload})
    expected = {**payload, "id": ref, "record_type": kind, "origin": "tool"}
    if store.get(ref) != expected:
        raise ContractError("native_blast_frozen_record_mismatch")
    return ref


def _reference(store, operand, grading, source_ref, scope, publish):
    if operand["binding_error"]:
        raise ContractError(operand["binding_error"])
    supplied = (operand["binding"] or {}).get("reference_ref")
    if supplied is not None:
        record = store.get(supplied)
        if record.get("record_type") != "reference" or record.get("accession") != operand["native_id"]:
            raise ContractError("native_blast_reference_binding_identity_mismatch")
        _validate_sequence(store, operand, supplied)
        return supplied
    seqref = grading["sequence_artifact_refs"].get("reference")
    if seqref is None:
        raise ContractError("native_blast_reference_sequence_unavailable")
    sequence = store.get(seqref)
    artifact_path(store, seqref)
    if sequence["sha256"] != operand["sequence_sha256"] or sequence["size"] != operand["length"]:
        raise ContractError("native_blast_reference_sequence_mismatch")
    accession = operand["native_id"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]{0,199}", accession):
        accession = identity("native_operand", {"artifact_ref": operand["artifact_ref"],
            "role": operand["operand_role"], "ordinal": operand["record_ordinal"]})
    payload = {"reference_type": "protein" if operand["molecule"] == "protein" else "sequence",
        "source_ref": source_ref, "accession": accession, "label": operand["native_title"][:512],
        "sequence_ref": seqref, "molecule": operand["molecule"], "length": operand["length"],
        "term_refs": [], "context_refs": []}
    return _record(store, "reference", payload, scope, publish)


def _publication(store, *, source_ref, bundle, prepared, scope, selector, publish):
    selector = validate_native_blast_result_selector(selector, program=bundle["program"])
    scope = store.validate_scope(scope)
    grading = _qualified_grading(store, source_ref, bundle, prepared, selector)
    result = {"record_refs": [source_ref], "rows": [], "failures": deepcopy(prepared["failures"])}
    for row, selected in _frozen_rows(store, grading, selector, bundle):
        projected = {key: deepcopy(row[key]) for key in ("record_key", "search_key", "hit_ordinal", "hsp_ordinal",
                                                       "program", "coordinate_units", "native_status")}
        projected.update(source_ref=source_ref, observation_ref=None, subject_ref=None, reference_refs=[],
            status="invalid" if row["invalid"] else "unbound",
            measurements=selected["measurements"], unavailable=selected["unavailable"])
        try:
            if row["invalid"]:
                raise ContractError("native_blast_invalid_native_row")
            query, reference = row["operands"].get("query"), row["operands"].get("reference")
            if query is None or reference is None:
                raise ContractError("native_blast_operand_unavailable")
            subject = (query["binding"] or {}).get("subject_ref")
            if subject is None:
                raise ContractError("native_blast_subject_binding_unavailable")
            selection = query["selected_interval"] or [0, query["length"]]
            intervals = [selection]
            if row["family"] == "pairwise_hsp":
                intervals.append(row["intervals"]["query"])
            _validate_sequence(store, query, subject, scope=scope, intervals=intervals)
            with store.transaction():
                ref = _reference(store, reference, grading, source_ref, scope, publish)
                observation = None
                if row["family"] == "pairwise_hsp":
                    all_values, _ = projected_measurements(row, NATIVE_BLAST_METRICS["pairwise_hsp"])
                    payload = {"subject_refs": [subject], "source_subject_refs": [ref], "kind": "comparison",
                        "source_ref": source_ref, "measurements": [{"name": value["name"],
                            "value": {"type": "number", "value": value["value"], "unit_ref": None}} for value in all_values],
                        "dependencies": list(dict.fromkeys([source_ref, subject, ref])), "anchor": None,
                        "operand_intervals": [{"role": axis, "subject_ref": operand_ref,
                            "start": row["intervals"][axis][0], "end": row["intervals"][axis][1],
                            "unit": row["coordinate_units"][axis], "model_unit": row["coordinate_units"]["alignment"]}
                            for axis, operand_ref in (("query", subject), ("reference", ref))],
                        "native_blast_pairwise": {"version": "native_blast_pairwise_observation_v1",
                            "program": bundle["program"], "record_key": row["record_key"],
                            "search_key": row["search_key"], "hit_ordinal": row["hit_ordinal"], "hsp_ordinal": row["hsp_ordinal"],
                            "bundle_artifact_ref": prepared["bundle_artifact_ref"]}}
                    observation = _record(store, "observation", payload, scope, publish)
            projected.update(observation_ref=observation, subject_ref=subject, reference_refs=[ref], status="published")
            # A union is a view of the same source/HSPs, not another scientific record.
            if row["family"] == "pairwise_hsp":
                result["record_refs"].extend([ref, observation])
        except (ValueError, KeyError, TypeError, OSError) as error:
            if str(error) != "native_blast_subject_binding_unavailable":
                projected["status"] = "invalid"
            result["failures"].append(_failure("publication", str(error) if isinstance(error, ValueError)
                else "native_blast_row_publication_failed", row["record_key"]))
        validate_schema(projected, row_schema(row["family"]))
        result["rows"].append(projected)
    result["record_refs"] = list(dict.fromkeys(result["record_refs"]))
    return result


def publish_selected_native_blast_rows(store, *, source_ref, bundle, prepared, scope, selector):
    return _publication(store, source_ref=source_ref, bundle=bundle, prepared=prepared,
                        scope=scope, selector=selector, publish=True)


def validate_native_blast_publication(store, *, source_ref, bundle, prepared, scope, selector, publication):
    """Authenticate a frozen return without writes, parsing or recalculation."""
    expected = _publication(store, source_ref=source_ref, bundle=bundle, prepared=prepared,
                            scope=scope, selector=selector, publish=False)
    if finite_json_copy(publication) != expected:
        raise ContractError("native_blast_frozen_publication_mismatch")
    return expected


__all__ = ["prepare_native_blast_grading", "publish_selected_native_blast_rows", "validate_native_blast_publication"]
