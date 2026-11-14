"""Retain bounded native grading and publish exactly selected numerical rows.

This adapter consumes original-attempt custody supplied by results acquisition.
It makes one deterministic parser call under the supplied resource allocation,
and never chooses work, runs a scientific search, or creates an episode action.
Acquisition/attempt qualification and receiver admission remain with the caller.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from .acquisition import AcquisitionError
from .domain import ContractError, canonical, identity, validate_schema
from .hmmer_native_result_views import (NATIVE_HMMER_METRICS, row_schema,
    validate_native_hmmer_result_selector)
from .local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from .materials import artifact_file, artifact_path
from .native_hmmer_contracts import finite_json_copy, native_hmmer_digest
from .tool_grading_artifacts import retain_tool_grading


_PREPARED_VERSION = "native_hmmer_prepared_grading_v1"
_SCHEMA_VERSION = "native_hmmer_retained_grading_v1"


def _failure(stage, code, record_key=None):
    return {"stage": stage, "code": code, "record_key": record_key}


def _json_file(path, value):
    temporary = path.with_suffix(path.suffix + ".writing")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, allow_nan=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
    temporary.replace(path)


def _captured_paths(store, bundle, artifacts):
    """Use retained, digest-checked paths only, never producer original paths."""
    declared = {}
    for kind, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        for row in rows:
            key = (row["role"], row["format"], row["relative_path"])
            if key in declared:
                raise ContractError("native_hmmer_duplicate_bundle_artifact")
            declared[key] = kind, row
    paths, failures, seen = [], [], set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"role", "format", "relative_path", "artifact_ref"}:
            raise ContractError("native_hmmer_captured_artifact_shape_invalid")
        key = (item["role"], item["format"], item["relative_path"])
        if key not in declared or key in seen:
            raise ContractError("native_hmmer_captured_artifact_binding_invalid")
        seen.add(key)
        kind, native = declared[key]
        expected = native["actual_sha256"] if kind == "input" else native["sha256"]
        try:
            stored = store.get(item["artifact_ref"])
            if (stored.get("record_type") != "artifact" or stored["sha256"] != expected
                    or stored["size"] != native["size_bytes"]):
                raise ContractError("native_hmmer_captured_artifact_digest_mismatch")
            if kind == "input" and (expected != native["expected_sha256"] or native["size_bytes"] != native["expected_size_bytes"]):
                raise ContractError("native_hmmer_input_not_original_selected_bytes")
            paths.append({**item, "kind": kind, "path": str(artifact_path(store, item["artifact_ref"]))})
        except (ValueError, OSError) as error:
            failures.append(_failure("custody", str(error) if isinstance(error, ValueError) else "native_hmmer_captured_artifact_unreadable"))
    for key in declared.keys() - seen:
        failures.append(_failure("custody", "native_hmmer_captured_artifact_missing:" + key[0]))
    return paths, failures


def prepare_native_hmmer_grading(store, *, bundle, bundle_artifact_ref, artifacts,
                                 directory, policy, selector):
    """Prepare one retained numerical result, with no full host hydration.

    The dedicated directory records interrupted preparation instead of silently
    retrying it. Repeating an already completed identical preparation reuses its
    original artifacts; a different request needs its own acquisition directory.
    """
    bundle = finite_json_copy(bundle)
    if bundle.get("version") != "native_hmmer_bundle_v1":
        raise ContractError("native_hmmer_original_bundle_required")
    if not isinstance(policy, LocalJobPolicy):
        raise ContractError("native_hmmer_local_job_policy_required")
    selector = validate_native_hmmer_result_selector(selector, program=bundle["program"])
    artifact_path(store, bundle_artifact_ref)
    paths, failures = _captured_paths(store, bundle, artifacts)
    failures += [_failure(row["stage"], row["code"]) for row in bundle.get("failures", [])]
    if bundle.get("returncode") != 0:
        failures.append(_failure("native", "native_hmmer_native_execution_unsuccessful"))
    directory = Path(directory).resolve() / "native-hmmer-grading"
    fingerprint = native_hmmer_digest({"bundle": bundle, "bundle_artifact_ref": bundle_artifact_ref,
        "artifacts": artifacts, "policy": policy.to_dict(), "selector": selector})
    if directory.exists():
        saved = directory / "prepared.json"
        intent = directory / "intent.json"
        if not intent.is_file() or json.loads(intent.read_text())["request_sha256"] != fingerprint:
            raise ContractError("native_hmmer_grading_directory_identity_conflict")
        if not saved.is_file():
            raise ContractError("native_hmmer_grading_original_preparation_incomplete")
        prepared = json.loads(saved.read_text())
        for name, reference in prepared.items():
            if name.endswith("artifact_ref") and reference is not None:
                artifact_path(store, reference)
        return prepared
    directory.mkdir(parents=True)
    _json_file(directory / "intent.json", {"request_sha256": fingerprint})
    plan = {"version": "native_hmmer_grading_plan_v1", "bundle": bundle,
        "artifacts": paths, "directory": str(directory), "selector": selector, "failures": failures}
    _json_file(directory / "plan.json", plan)
    prepared = {"version": _PREPARED_VERSION, "bundle_artifact_ref": bundle_artifact_ref,
        "source_grading_artifact_ref": None, "grading_artifact_ref": None, "sheet_artifact_ref": None,
        "scores_artifact_ref": None, "selected_rows_artifact_ref": None,
        "failures": failures, "numerical_complete": False}
    receipt = None
    try:
        for name in ("tmp", "cache"):
            (directory / name).mkdir()
        check_scratch_budget(directory, policy)
        result = run_local_job([sys.executable, "-m", "gene_annotation_episode.native_hmmer_result_worker",
            str(directory / "plan.json")], cwd=directory, policy=policy,
            stdout_path=directory / "worker.stdout", stderr_path=directory / "worker.stderr",
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1]),
                 "TMPDIR": str(directory / "tmp"), "TMP": str(directory / "tmp"),
                 "TEMP": str(directory / "tmp"), "XDG_CACHE_HOME": str(directory / "cache")})
        receipt = result.metadata
        if result.returncode != 0:
            failures.append(_failure("worker", "native_hmmer_grading_worker_nonzero"))
    except (AcquisitionError, OSError, ValueError) as error:
        failures.append(_failure("worker", getattr(error, "code", "native_hmmer_grading_worker_failed")))
        receipt = {"exception_type": type(error).__name__, "detail": str(error),
                   "operational": getattr(error, "operational", None)}
    manifest_path = directory / "worker-result.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    failures = list({(r["stage"], r["code"], r.get("record_key")): r
        for r in [*failures, *manifest.get("failures", [])]}.values())
    retained = []
    for field, name, media_type in (
            ("sheet_artifact_ref", "sheet.json", "application/json"),
            ("scores_artifact_ref", "scores.json", "application/json"),
            ("selected_rows_artifact_ref", "selected-rows.ndjson", "application/x-ndjson")):
        path = directory / name
        if path.is_file():
            prepared[field] = artifact_file(store, path, media_type)
    for name in ("diagnostics.json", "worker.stdout", "worker.stderr", "worker-result.json"):
        path = directory / name
        if path.is_file():
            retained.append({"role": name, "artifact_ref": artifact_file(store, path)})
    prepared.update(failures=failures, numerical_complete=bool(manifest.get("numerical_complete")) and not failures)
    custody = [{k: v for k, v in row.items() if k != "path"} for row in paths]
    stable = {"schema": _SCHEMA_VERSION, "sheet_artifact_ref": prepared["sheet_artifact_ref"],
        "sheet_schema": manifest.get("sheet_schema"), "sheet_format": "json",
        "scores_artifact_ref": prepared["scores_artifact_ref"], "scores_schema": manifest.get("scores_schema"),
        "scores_format": "json", "captured_artifacts": custody}
    prepared["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=bundle_artifact_ref, grading=stable)
    selected = {**stable, "source_grading_artifact_ref": prepared["source_grading_artifact_ref"],
        "selected_rows_artifact_ref": prepared["selected_rows_artifact_ref"],
        "selected_rows_schema": "native_hmmer_selected_row_v1", "selected_rows_format": "ndjson",
        "bundle_sha256": native_hmmer_digest(bundle), "selector": selector,
        "failures": failures, "numerical_complete": prepared["numerical_complete"],
        "diagnostic_artifacts": retained, "worker_receipt": receipt}
    prepared["grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=bundle_artifact_ref, grading=selected)
    _json_file(directory / "prepared.json", prepared)
    return prepared


def _subject_chunks(store, reference, start=0, end=None, reverse=False):
    """Read actual Store sequence symbols with bounded windows, including features."""
    row = store.get(reference)
    length = store.subject_length(reference)
    end = length if end is None else end
    if not 0 <= start <= end <= length:
        raise ContractError("native_hmmer_subject_window_invalid")
    if row["record_type"] == "feature":
        # Feature segments concatenate in declared order before native strand.
        if row["strand"] == "-":
            start, end, reverse = length - end, length - start, not reverse
        segments, cursor = [], 0
        for segment in row["segments"]:
            n = segment["end"] - segment["start"]
            a, b = max(start, cursor), min(end, cursor + n)
            if a < b:
                segments.append((segment["start"] + a - cursor, segment["start"] + b - cursor))
            cursor += n
        for a, b in reversed(segments) if reverse else segments:
            yield from _subject_chunks(store, row["subject_ref"], a, b, reverse)
        return
    path = artifact_path(store, row["sequence_ref"]) if row.get("sequence_ref") else None
    if path is None and row["record_type"] != "read_subject":
        raise ContractError("native_hmmer_subject_sequence_unavailable")
    from . import materials_packing
    molecule = store.subject_molecule(reference)
    if reverse and molecule not in {"dna", "rna"}:
        raise ContractError("native_hmmer_reverse_sequence_model_invalid")
    # A window read never asks Store.get_artifact to hydrate a whole chromosome.
    def read(a, b):
        if path is not None:
            with path.open("rb") as handle:
                handle.seek(a)
                return handle.read(b - a)
        return materials_packing.component_window(store, store.get(row["member_ref"]), "sequence", a, b - a)
    cursor = end if reverse else start
    while cursor > start if reverse else cursor < end:
        a, b = (max(start, cursor - 65536), cursor) if reverse else (cursor, min(end, cursor + 65536))
        chunk = read(a, b).decode("ascii").upper()
        if len(chunk) != b - a:
            raise ContractError("native_hmmer_subject_sequence_truncated")
        if reverse:
            chunk = chunk.translate(str.maketrans("ACGTRYSWKMBDHVNU", "TGCAYRSWMKVHDBNA"))[::-1]
            if molecule == "rna":
                chunk = chunk.replace("T", "U")
        yield chunk.encode("ascii")
        cursor = a if reverse else b


def _validate_sequence_binding(store, operand, reference, *, scope=None, interval=None):
    if operand.get("kind") not in {"protein_sequence", "nucleotide_sequence"} or not operand.get("sequence_sha256"):
        raise ContractError("native_hmmer_biological_sequence_operand_required")
    if store.subject_length(reference) != operand["length"]:
        raise ContractError("native_hmmer_subject_length_mismatch")
    unit = store.subject_unit(reference)
    if unit not in ({"aa"} if operand["kind"] == "protein_sequence" else {"nt"}):
        raise ContractError("native_hmmer_subject_molecule_mismatch")
    digest = hashlib.sha256()
    for chunk in _subject_chunks(store, reference):
        digest.update(chunk)
    if digest.hexdigest() != operand["sequence_sha256"]:
        raise ContractError("native_hmmer_subject_sequence_mismatch")
    if scope is not None:
        if reference not in store.reference_subset([reference], scope):
            raise ContractError("native_hmmer_subject_outside_scope")
        if interval is None or not (len(interval) == 2 and all(type(n) is int for n in interval)
                                   and 0 <= interval[0] < interval[1] <= operand["length"]):
            raise ContractError("native_hmmer_subject_interval_unavailable")
        footprint = store.map_segments(reference, [{"start": interval[0], "end": interval[1]}])
        if store.roots(reference) and (not footprint or not store.scope_covers(footprint, scope)):
            raise ContractError("native_hmmer_subject_interval_outside_scope")
    return unit


def _reference(store, operand, source_ref, scope):
    binding = operand.get("binding") or {}
    supplied = binding.get("reference_ref")
    if supplied is not None:
        record = store.get(supplied)
        if record.get("record_type") != "reference" or record["accession"] not in {operand["name"], operand.get("accession")}:
            raise ContractError("native_hmmer_reference_binding_identity_mismatch")
        if operand["kind"] == "profile":
            if record["reference_type"] != "family":
                raise ContractError("native_hmmer_profile_reference_required")
        else:
            _validate_sequence_binding(store, operand, supplied)
        return supplied
    # A parsed original profile/sequence is a source subject, never a new target.
    accession = operand.get("accession") or operand["name"]
    if not isinstance(accession, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/+%#?=;&@~-]{0,199}", accession):
        accession = identity("native_operand", {"artifact_ref": operand["artifact_ref"],
            "role": operand["operand_role"], "ordinal": operand["record_ordinal"]})
    profile = operand["kind"] in {"profile", "msa"}
    record = store.put("reference", {"reference_type": "family" if profile else
        "protein" if operand["kind"] == "protein_sequence" else "sequence", "source_ref": source_ref,
        "accession": accession, "label": str(operand["name"] or accession)[:512],
        "sequence_ref": None, "molecule": None if profile else "protein" if operand["alphabet"] == "amino" else operand["alphabet"],
        "length": None if profile else operand["length"], "term_refs": [], "context_refs": []},
        origin="tool", scope=scope)
    return record["id"]


def publish_selected_native_hmmer_rows(store, *, source_ref, bundle, prepared, scope, selector):
    """Publish stable native row observations and return requested closed facts."""
    selector = validate_native_hmmer_result_selector(selector, program=bundle["program"])
    scope = store.validate_scope(scope)
    source = store.get(source_ref)
    if (prepared.get("version") != _PREPARED_VERSION or source.get("provider") != "episode.execution_result"
            or source.get("origin") != "tool" or source.get("artifact_ref") != prepared.get("bundle_artifact_ref")
            or prepared.get("source_grading_artifact_ref") not in source.get("auxiliary_artifact_refs", [])):
        raise ContractError("native_hmmer_publication_source_custody_mismatch")
    envelope = json.loads(store.get_artifact(prepared["grading_artifact_ref"]))
    grading = envelope.get("grading", {})
    if (envelope.get("schema") != "tool_grading_artifact_v1" or envelope.get("provider") != source["provider"]
            or envelope.get("native_artifact_ref") != source["artifact_ref"]
            or grading.get("bundle_sha256") != native_hmmer_digest(bundle) or grading.get("selector") != selector
            or any(grading.get(field) != prepared.get(field) for field in (
                "sheet_artifact_ref", "scores_artifact_ref", "selected_rows_artifact_ref", "source_grading_artifact_ref"))):
        raise ContractError("native_hmmer_prepared_grading_identity_mismatch")
    result = {"record_refs": [source_ref], "rows": [], "failures": deepcopy(prepared["failures"])}
    if prepared["selected_rows_artifact_ref"] is None:
        return result
    family = selector["projection"]["family"]
    requested = selector["projection"]["metrics"]
    rejected_bindings = {row["record_key"]: row["code"] for row in prepared["failures"]
        if row["stage"] == "binding" and row.get("record_key") is not None}
    seen = set()
    with artifact_path(store, prepared["selected_rows_artifact_ref"]).open(encoding="utf-8") as stream:
        for line in stream:
            native = json.loads(line)
            key = native.get("record_key")
            if key in seen:
                raise ContractError("native_hmmer_selected_row_duplicate")
            seen.add(key)
            if native.get("version") != "native_hmmer_selected_row_v1" or native.get("family") != family:
                raise ContractError("native_hmmer_selected_row_schema_mismatch")
            projected = {"record_key": key, "source_ref": source_ref, "observation_ref": None,
                "subject_ref": None, "reference_refs": [], "query_occurrence": native["query_occurrence"],
                "target_occurrence": native["target_occurrence"], "iteration": native["iteration"],
                "strand": {"+": "plus", "-": "minus", None: None}[native["strand"]],
                "status": "invalid" if native["invalid"] else "unbound",
                "measurements": native["measurements"], "unavailable": native["unavailable"]}
            names = [row["name"] for row in projected["measurements"] + projected["unavailable"]]
            if len(names) != len(set(names)) or set(names) != set(requested):
                raise ContractError("native_hmmer_selected_metrics_mismatch")
            validate_schema(projected, row_schema(family))
            try:
                operand = native["subject_operand"]
                binding = (operand or {}).get("binding") or {}
                subject = binding.get("subject_ref")
                if native["invalid"]:
                    raise ContractError("native_hmmer_invalid_native_row")
                if key in rejected_bindings:
                    raise ContractError(rejected_bindings[key])
                if subject is None:
                    raise ContractError("native_hmmer_subject_binding_unavailable")
                unit = _validate_sequence_binding(store, operand, subject, scope=scope, interval=native["subject_interval"])
                with store.transaction():
                    references = list(dict.fromkeys(_reference(store, other, source_ref, scope)
                        for other in native["related_operands"] if other is not None))
                    values = native["observation_measurements"]
                    if (len({v["name"] for v in values}) != len(values) or
                            any(v["name"] not in NATIVE_HMMER_METRICS[family] for v in values)):
                        raise ContractError("native_hmmer_observation_metrics_invalid")
                    observation = store.put("observation", {"subject_refs": [subject],
                        "source_subject_refs": references, "kind": "alignment" if family == "alignment_sequence" else "profile_match",
                        "source_ref": source_ref, "measurements": [{"name": v["name"],
                            "value": {"type": "number", "value": v["value"], "unit_ref": None}} for v in values],
                        "dependencies": list(dict.fromkeys([source_ref, subject, *references])), "anchor": None,
                        "operand_intervals": [{"role": "query", "subject_ref": subject, "start": native["subject_interval"][0],
                            "end": native["subject_interval"][1], "unit": unit, "model_unit": unit}],
                        "native_hmmer": {"version": "native_hmmer_observation_v1", "program": bundle["program"],
                            "family": family, "record_key": key, "bundle_artifact_ref": source["artifact_ref"]}},
                        origin="tool", scope=scope)
                projected.update(observation_ref=observation["id"], subject_ref=subject,
                                 reference_refs=references, status="published")
                result["record_refs"].extend([*references, observation["id"]])
            except (ValueError, KeyError, TypeError, OSError) as error:
                # An absent association differs from a supplied association
                # that failed validation. Keep each failure local to its row.
                if str(error) != "native_hmmer_subject_binding_unavailable":
                    projected["status"] = "invalid"
                result["failures"].append(_failure("publication", str(error) if isinstance(error, ValueError)
                    else "native_hmmer_row_publication_failed", key))
            result["rows"].append(projected)
    result["record_refs"] = list(dict.fromkeys(result["record_refs"]))
    return result


__all__ = ["prepare_native_hmmer_grading", "publish_selected_native_hmmer_rows"]
