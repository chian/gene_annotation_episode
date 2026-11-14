"""Ordinary source and sequence publication for retained protein results.

Payload construction is pure; publication validates retained original bytes.
The result host separately authenticates capture and worker custody. A source's
auxiliary list preserves original files and grants no receiving episode access.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib

from .domain import ContractError, RECORD_SCHEMAS, identity, validate_schema
from .execution_contracts import canonical, digest
from .native_protein_structure_acquisition import (
    ProteinStructureCapture, retained_protein_structure_file,
)
from .native_protein_structure_contracts import NativeProteinBundle, validate_protein_structure_bundle
from .protein_structure_contracts import (
    FileIdentity, ReferenceRef, SourceRef, StructureSequence,
    validate_file_identity, validate_structure_sequence,
)
from .protein_structure_result_worker import (
    ProteinResultWorkerResult, validate_protein_structure_result_worker_result,
)


def protein_structure_source_payload(*, bundle: NativeProteinBundle,
        capture: ProteinStructureCapture,
        worker_result: ProteinResultWorkerResult | None,
        request_ref: str | None = None) -> dict:
    """Build the single approved immutable payload from qualified actual files.

This checks the supplied metadata relationship. It does not acquire bytes or
establish original episode authority. Saved recalculation must use the original
source, rather than pass its later worker output to this function.
    """
    if capture["bundle_validated"] is not True or capture["original_plan"] is None or capture["bundle_file"] is None:
        raise ValueError("capture_incomplete")
    original = validate_protein_structure_bundle(bundle, plan=capture["original_plan"])
    bundle_file = validate_file_identity(capture["bundle_file"])
    if (bundle_file["format"] != "native_protein_structure_bundle_v1"
            or bundle_file["sha256"] != digest(original)
            or bundle_file["byte_length"] != len(canonical(original).encode("utf-8"))):
        raise ValueError("input_digest_mismatch")
    references = []
    for row in capture["files"]:
        if row["observed"] is not None:
            references.append(validate_file_identity(row["observed"])["artifact_ref"])
    if worker_result is not None:
        result = validate_protein_structure_result_worker_result(worker_result)
        operation = original["requested_job"]["native_protein_structure"]["request"]["operation"]
        if result["mode"] != "original_native_result" or result["operation"] != operation:
            raise ValueError("original_commission_mismatch")
        for name in ("native_result_file", "sheet_file", "components_file"):
            if result[name] is not None:
                references.append(result[name]["file_identity"]["artifact_ref"])
    return {"provider": "episode.execution_result",
        "accession": "native_protein_structure_" + digest(original["identity"]),
        "uri": None, "artifact_ref": bundle_file["artifact_ref"], "text_ref": None,
        "request_ref": request_ref, "version": "native_protein_structure_bundle_v1",
        "retrieved_at": original["finished_at"],
        "auxiliary_artifact_refs": list(dict.fromkeys(references))}


def _ordinary_record(store, reference, kind):
    """Validate the existing domain identity without creating a new namespace."""
    if type(reference) is not str:
        raise ValueError("invalid_schema")
    try:
        record = store.get(reference)
    except ContractError as error:
        raise ValueError("conflicting_identity") from error
    except (ValueError, TypeError) as error:
        raise ValueError("invalid_schema") from error
    if (type(record) is not dict or record.get("id") != reference
            or record.get("record_type") != kind or record.get("origin") != "tool"):
        raise ValueError("conflicting_identity")
    payload = {key: value for key, value in record.items()
        if key not in {"id", "record_type", "origin"}}
    try:
        expected = identity(kind, {"origin": record["origin"], "record": payload})
    except (ValueError, TypeError) as error:
        raise ValueError("invalid_schema") from error
    if reference != expected:
        raise ValueError("conflicting_identity")
    try:
        validate_schema(payload, RECORD_SCHEMAS[kind])
    except ContractError as error:
        raise ValueError("invalid_schema") from error
    return record


def _put_original(store, kind, payload):
    """Store.put remains the publisher; check its INSERT OR IGNORE replay too."""
    expected_ref = identity(kind, {"origin": "tool", "record": payload})
    expected = {**payload, "id": expected_ref, "record_type": kind, "origin": "tool"}
    with store.transaction():
        try:
            store.get(expected_ref)
        except ContractError as error:
            if str(error) != "unknown_reference":
                raise ValueError("conflicting_identity") from error
        else:
            if canonical(_ordinary_record(store, expected_ref, kind)) != canonical(expected):
                raise ValueError("conflicting_identity")
        try:
            published = store.put(kind, payload, origin="tool")
        except ContractError as error:
            raise ValueError("invalid_schema") from error
        actual = _ordinary_record(store, expected_ref, kind)
        if canonical(published) != canonical(expected) or canonical(actual) != canonical(expected):
            raise ValueError("conflicting_identity")
        return actual["id"]


def _retained_bytes(store, file):
    path = retained_protein_structure_file(store, file)
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValueError("retained_artifact_missing") from error


def publish_protein_structure_source(store, *, bundle: NativeProteinBundle,
        capture: ProteinStructureCapture,
        worker_result: ProteinResultWorkerResult | None,
        request_ref: str | None = None) -> SourceRef:
    """Publish original retained provenance after host custody authentication.

    Diagnostic capture identities stay diagnostic. Publication grants no use of
    their bytes and cannot replace the original source with saved recalculation.
    """
    try:
        payload = protein_structure_source_payload(
            bundle=bundle, capture=capture, worker_result=worker_result, request_ref=request_ref)
        if request_ref is not None:
            request = store.get(request_ref)
            if request.get("record_type") != "artifact":
                raise ValueError("original_commission_mismatch")
        if _retained_bytes(store, capture["bundle_file"]) != canonical(bundle).encode("utf-8"):
            raise ValueError("input_digest_mismatch")
        if len(capture["files"]) != len(bundle["files"]):
            raise ValueError("original_commission_mismatch")
        for index, row in enumerate(capture["files"]):
            if (type(row["manifest_index_0based"]) is not int
                    or row["manifest_index_0based"] != index
                    or canonical(row["declared"]) != canonical(bundle["files"][index])):
                raise ValueError("original_commission_mismatch")
            if row["observed"] is not None:
                if row["observed"]["format"] != row["declared"]["format"]:
                    raise ValueError("unsupported_format")
                retained_protein_structure_file(store, row["observed"])
        if worker_result is not None:
            for name in ("native_result_file", "sheet_file", "components_file"):
                if worker_result[name] is not None:
                    retained_protein_structure_file(store, worker_result[name]["file_identity"])
    except (KeyError, TypeError, IndexError, UnicodeError) as error:
        raise ValueError("invalid_schema") from error
    except ValueError as error:
        if str(error) == "capture_incomplete":
            raise ValueError("original_commission_mismatch") from error
        raise
    return _put_original(store, "source", payload)


def publish_structure_sequence_reference(store, *, source_ref: SourceRef,
        sequence: StructureSequence, sequence_file: FileIdentity,
        residue_map_file: FileIdentity) -> ReferenceRef:
    """Publish one supplied original sequence and its complete retained map.

    The caller authenticates the original extraction. This checks publication
    relationships and exact bytes without parsing or reconstructing a structure.
    """
    sequence = validate_structure_sequence(sequence)
    sequence_file = validate_file_identity(sequence_file)
    residue_map_file = validate_file_identity(residue_map_file)
    if (sequence_file["format"] != "ascii_protein_sequence_v1"
            or residue_map_file["format"] != "protein_structure_sequence_v1"):
        raise ValueError("unsupported_format")
    if not sequence["sequence_available"] or not sequence["alignment_sequence"]:
        raise ValueError("sequence_artifact_mismatch")
    try:
        sequence_bytes = sequence["alignment_sequence"].encode("ascii")
    except UnicodeError as error:
        raise ValueError("sequence_artifact_mismatch") from error
    if sequence_bytes != sequence_bytes.upper():
        raise ValueError("sequence_artifact_mismatch")
    if (_retained_bytes(store, sequence_file) != sequence_bytes
            or _retained_bytes(store, residue_map_file) != canonical(sequence).encode("utf-8")):
        raise ValueError("sequence_artifact_mismatch")
    with store.transaction():
        source = _ordinary_record(store, source_ref, "source")
        if (source["provider"] != "episode.execution_result"
                or source["version"] != "native_protein_structure_bundle_v1"):
            raise ValueError("original_commission_mismatch")
        if any(file["artifact_ref"] not in source.get("auxiliary_artifact_refs", [])
                for file in (sequence_file, residue_map_file)):
            raise ValueError("original_commission_mismatch")
        return _put_original(store, "reference", {
            "reference_type": "protein", "source_ref": source_ref,
            "accession": "structure_sequence_" + digest(sequence),
            "label": "Structure-derived protein sequence",
            "sequence_ref": sequence_file["artifact_ref"], "molecule": "protein",
            "length": sequence["sequence_length"], "term_refs": [],
            "context_refs": [], "anchor": None,
        })


def publish_protein_structure_action_result(registry, work, *, authority):
    """Publish the selected ordinary action from freshly validated retained work.

    This immediate publication boundary may validate captured input Files. Later
    reading uses the recorded action capsule and retained scientific outputs.
    A terminal attempt without a validated bundle has no scientific Source.
    """
    from .protein_structure_tools import validate_prepared_protein_structure_work
    from .protein_structure_tools import SAVED_WORK_VERSION
    if type(work) is dict and work.get("version") == SAVED_WORK_VERSION:
        checked = validate_prepared_protein_structure_work(registry, work, authority=authority)
        if checked["redisplay"] is not None:
            result = deepcopy(checked["redisplay"]["result"])
            return result, [result["source_ref"]]
        values = saved_protein_action_values(checked)
        public_ref = registry.store.artifact(canonical(values), media_type="application/json")
        retained_work = deepcopy(checked)
        retained_work["scientific"] = None
        capsule = dict(version="protein_structure_saved_action_publication_v1", work=retained_work)
        request_ref = registry.store.artifact(canonical(capsule), media_type="application/json")
        payload = saved_protein_action_source_payload(registry.store, capsule=capsule,
            public_ref=public_ref, request_ref=request_ref)
        source_ref = _put_original(registry.store, "source", payload)
        registry._written.append(source_ref)
        return saved_protein_action_result(values, source_ref=source_ref), [source_ref]
    from .protein_structure_contracts import (
        issue, validate_saved_sheet_descriptor_v2,
        validate_structure_sequence_descriptor_v2,
    )
    from .protein_structure_result_views import project_protein_structure_results
    from .protein_structure_action_records import (
        action_view_from_projection_rows, project_protein_structure_action_views,
        validate_protein_structure_tool_result,
    )

    checked = validate_prepared_protein_structure_work(registry, work, authority=authority)
    if checked["bundle"] is None or checked["capture"] is None:
        raise ValueError("capture_incomplete")
    store = registry.store
    capsule = {"version": "protein_structure_action_publication_v1", **{
        name: deepcopy(checked[name]) for name in (
            "invocation", "tool_name", "arguments", "scope", "binding", "plan",
            "execution", "capture", "worker", "qualified_files")}}
    request_ref = store.artifact(canonical(capsule), media_type="application/json")
    worker_result = None if checked["worker"] is None else checked["worker"]["result"]
    source_ref = publish_protein_structure_source(store, bundle=checked["bundle"],
        capture=checked["capture"], worker_result=worker_result, request_ref=request_ref)
    registry._written.append(source_ref)
    references = [source_ref]
    scientific, files = checked["scientific"], checked["qualified_files"]
    selection = checked["arguments"]["selection"]
    operation = checked["arguments"]["request"]["operation"]
    custody = {"version": "protein_structure_action_custody_v1", "source_ref": source_ref}
    sequences, saved_sheets, issues = [], [], deepcopy(checked["issues"])
    if selection["sequence_allowed_uses"]:
        if (scientific is not None and scientific["kind"] == "extraction"
                and scientific["sequence"]["sequence_available"]
                and files["sequence_file"] is not None and files["residue_map_file"] is not None):
            sequence = scientific["sequence"]
            reference_ref = publish_structure_sequence_reference(store, source_ref=source_ref,
                sequence=sequence, sequence_file=files["sequence_file"], residue_map_file=files["residue_map_file"])
            registry._written.append(reference_ref)
            descriptor = validate_structure_sequence_descriptor_v2({
                "version": "structure_sequence_descriptor_v2", "custody": custody,
                "reference_ref": reference_ref, "sequence_file": files["sequence_file"],
                "residue_map_file": files["residue_map_file"], "structure_file": sequence["selection"]["file_identity"],
                "selection": sequence["selection"], "sequence_length": sequence["sequence_length"],
                "allowed_uses": selection["sequence_allowed_uses"]})
            scientific["descriptor"] = descriptor
            sequences.append(descriptor)
            references.extend([reference_ref, files["sequence_file"]["artifact_ref"],
                files["residue_map_file"]["artifact_ref"]])
        else:
            issues.append(issue("selected_field_unavailable", stage="projection", field="descriptor", artifact_role="sequence"))
    if selection["return_saved_sheet"]:
        if (scientific is not None and scientific["kind"] == "comparison"
                and files["sheet_file"] is not None and files["original_components_file"] is not None):
            descriptor = validate_saved_sheet_descriptor_v2({"version": "protein_structure_saved_sheet_v2",
                "custody": custody, "sheet_file": files["sheet_file"],
                "original_components_file": files["original_components_file"],
                "operation": "compare_protein_structures", "original_mode": scientific["sheet"]["scientific_mode"],
                "allowed_uses": ["recalculate", "select_projection", "use_transform"]})
            saved_sheets.append(descriptor)
            references.extend([files["sheet_file"]["artifact_ref"], files["original_components_file"]["artifact_ref"]])
        else:
            issues.append(issue("selected_field_unavailable", stage="projection", field="descriptor"))
    issues = list({canonical(value): value for value in issues}.values())
    selected_views = []
    for selected in selection["projections"]:
        # The pure projector retains other valid selections when this one is
        # unavailable. It never creates an artifact identity without its bytes.
        if scientific is None:
            selected_views.extend(project_protein_structure_action_views(None, source_ref=source_ref,
                operation=operation, selections=[selected], issues=issues))
            continue
        try:
            rows, = project_protein_structure_results(scientific, selection=[selected])
        except ValueError:
            selected_views.extend(project_protein_structure_action_views(scientific, source_ref=source_ref,
                operation=operation, selections=[selected], issues=issues))
            continue
        table_file = None
        if selected["delivery_kind"] == "artifact":
            data = canonical({"version": "protein_structure_projection_table_v1", "rows": rows["rows"]}).encode("utf-8")
            sha256 = hashlib.sha256(data).hexdigest()
            table_ref = store.artifact(data, media_type="application/json")
            table_file = {"artifact_ref": table_ref, "sha256": sha256, "byte_length": len(data),
                "format": "protein_structure_projection_table_v1"}
            retained_protein_structure_file(store, table_file)
            references.append(table_ref)
        selected_views.append(action_view_from_projection_rows(rows, source_ref=source_ref,
            operation=operation, table_file=table_file))
    result = validate_protein_structure_tool_result({"version": "protein_structure_tool_result_v1",
        "source_ref": source_ref, "operation": operation, "views": selected_views,
        "sequences": sequences, "saved_sheets": saved_sheets, "issues": issues})
    references = list(dict.fromkeys(references))
    bridge = getattr(registry, 'publish_a102_comparison_bridge', None)
    if callable(bridge) and saved_sheets:
        references = list(dict.fromkeys([*references, *bridge(scientific=scientific,
            source_ref=source_ref, selection=selection)]))
    registry._written.extend(reference for reference in references if reference not in registry._written)
    return result, references


def saved_protein_action_values(work):
    """Project only the explicitly selected values; retain unavailable meanings."""
    from .protein_structure_contracts import IssueCode, issue
    from .protein_structure_result_views import project_protein_structure_results
    from typing import get_args
    rows = []
    for selection in work["arguments"]["projections"]:
        if work["scientific"] is None:
            outcome = dict(version="protein_structure_action_unavailable_v1", issues=deepcopy(work["issues"]) or [
                issue("selected_field_unavailable", stage="projection", field="projection_fields")])
        else:
            try:
                outcome, = project_protein_structure_results(work["scientific"], selection=[selection])
            except ValueError as error:
                code = str(error) if str(error) in get_args(IssueCode) else "invalid_schema"
                outcome = dict(version="protein_structure_action_unavailable_v1", issues=[
                    issue(code, stage="projection", field="projection_fields")])
        rows.append(dict(selection=deepcopy(selection), outcome=outcome))
    return dict(version="protein_structure_saved_action_values_v1", operation="compare",
        projections=rows, issues=deepcopy(work["issues"]))


def saved_protein_action_source_payload(store, *, capsule, public_ref, request_ref):
    from .protein_structure_action_records import SAVED_ACTION_SOURCE_VERSION
    work = capsule["work"]
    descriptor = work["arguments"]["saved_sheet"]
    parent = _ordinary_record(store, descriptor["custody"]["source_ref"], "source")
    parents = list(dict.fromkeys([parent["id"], work["admission"]["result_ref"]]))
    auxiliary = [work["qualified_files"][name]["artifact_ref"]
        for name in ("sheet_file", "original_components_file", "components_file")
        if work["qualified_files"][name] is not None]
    if work["worker"] is not None:
        prepared = work["worker"]["prepared"]
        auxiliary.extend(prepared[name] for name in ("plan_artifact_ref", "execution_receipt_artifact_ref",
            "worker_result_artifact_ref") if prepared[name] is not None)
        auxiliary.extend(row["artifact_ref"] for row in prepared["diagnostic_files"])
    return dict(provider="episode.execution_result", accession="protein_structure_saved_action_" + digest(work["invocation"]),
        uri=None, artifact_ref=public_ref, text_ref=None, request_ref=request_ref, version=SAVED_ACTION_SOURCE_VERSION,
        retrieved_at=None, parent_source_refs=parents,
        auxiliary_artifact_refs=list(dict.fromkeys(auxiliary)))


def saved_protein_action_result(values, *, source_ref):
    from .protein_structure_action_records import validate_protein_structure_tool_result
    return validate_protein_structure_tool_result(dict(version="protein_structure_tool_result_v1",
        source_ref=source_ref, operation="compare", views=[dict(version="protein_structure_action_view_v1",
            source_ref=source_ref, operation="compare", **deepcopy(row)) for row in values["projections"]],
        sequences=[], saved_sheets=[], issues=deepcopy(values["issues"])))
