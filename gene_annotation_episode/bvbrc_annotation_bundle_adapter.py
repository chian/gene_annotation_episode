"""Selected AppService artifacts → native GTO observations → existing components.

This adapter makes no request and owns no episode. Its caller authenticates the
ArtifactBundle. Saved projection below consumes only retained documents and
components; it performs no raw-byte parsing or numerical recalculation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_annotation_contracts import (
    APPLICATIONS, validate_parameters, validate_requested_form, validate_facts,
    parameters_schema, requested_form_schema, VALUE_VERSION,
)
from .bvbrc_annotation_native import (
    COMPONENTS_VERSION as NATIVE_COMPONENTS_VERSION,
    _canonical, _finite_json, _field, _issue, parse_annotation_artifact,
    validate_annotation_document, calculate_annotation_components,
)


ADAPTER_ID = "bvbrc_annotation"
ADAPTER_VERSION = "1"
SHEET_VERSION = "bvbrc_annotation_observations_v1"
COMPONENTS_VERSION = "bvbrc_annotation_retained_components_v1"
_FORMATS = {"gto": {"gto", "genome"}, "quality_json": {"quality_json", "json"}}
_DEPENDENCIES = ("__init__.py", "acquisition.py", "domain.py", "public_configuration.py",
    "bvbrc_annotation_native.py", "bvbrc_annotation_contracts.py",
    "bvbrc_annotation_bundle_adapter.py", "alignment_correspondence.py",
    "sequence_composition_grader.py", "sequence_composition_counts.py",
    "ucsc_acquisition.py", "data_acquisition_receipts.py", "bvbrc_appservice_contracts.py",
    "bvbrc_appservice_schemas.json")


def implementation_sha256():
    """Pin the selected pure call path and its import-time source dependencies.

    Uncalled HTTP/publication functions in the shared reversible-JSON owner are
    not adapter operations. The execution runner separately pins its selected
    whole application closure. This pin is not native provenance.
    """
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        data = Path(__file__).with_name(name).read_bytes()
        digest.update(name.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
    return digest.hexdigest()


def _require(condition, code="bvbrc_annotation_bundle_invalid"):
    if not condition:
        raise ValueError(code)


def _diagnostic(code, path, refs=(), *, severity="qualification"):
    return {"code": code, "phase": "association", "path": path,
        "severity": severity, "evidence_refs": list(dict.fromkeys(refs))}


def _missing(specification, code, refs=()):
    return {"requirement_id": specification["requirement_id"], "kind": "parser_binding",
        "role": None, "source_refs": list(dict.fromkeys(refs)), "reason_code": code}


def _content(artifact):
    return {"source_ref": artifact["source_ref"], "artifact_field": "artifact_ref",
        "artifact_ref": artifact["raw_artifact_ref"], "sha256": artifact["sha256"],
        "byte_count": artifact["byte_count"]}


def _resolve(bundle, specification, artifact_bytes, *, parse_artifact=None, formats=None, family="annotation"):
    """Resolve one explicitly selected artifact using the shared task binding.

    Other application families supply their own reader and declared formats;
    this function owns no acquisition, Source custody or scientific calculation.
    """
    parse_artifact = parse_annotation_artifact if parse_artifact is None else parse_artifact
    formats = _FORMATS if formats is None else formats
    identifier = specification["document_id"]
    candidates = [artifact for artifact in bundle["artifacts"]
        if specification["requirement_id"] in artifact.get("requirement_ids", [])]
    refs = [artifact["source_ref"] for artifact in candidates]
    resolution = {"document_id": identifier, "specification": deepcopy(specification),
        "state": "missing", "candidate_contents": [_content(row) for row in candidates], "document": None}
    if len(candidates) != 1:
        code = family + ("_artifact_missing" if not candidates else "_artifact_ambiguous")
        resolution["state"] = "missing" if not candidates else "ambiguous"
        return resolution, [_missing(specification, code, refs)], [_diagnostic(code, "/documents/" + identifier, refs)]
    artifact, = candidates
    task = bundle["original_task"]
    association = artifact["task_association"]
    if (association["task_id"] != task["task_id"] or association["kind"] == "unverified_original_path"
            or artifact["declared_format"]["format"] not in formats[specification["representation"]]):
        resolution["state"] = "incompatible"
        code = family + "_artifact_task_or_format_conflict"
        return resolution, [_missing(specification, code, refs)], [_diagnostic(code, "/documents/" + identifier, refs, severity="error")]
    reference = artifact["raw_artifact_ref"]
    if reference not in artifact_bytes:
        code = family + "_artifact_bytes_missing"
        return resolution, [_missing(specification, code, refs)], [_diagnostic(code, "/documents/" + identifier, refs)]
    transfer = artifact["transfer"]
    document = parse_artifact(artifact_bytes[reference], content=_content(artifact),
        representation=specification["representation"],
        capture_complete=transfer["body_complete"] and transfer["object_complete"] == "yes",
        expected_task_id=task["task_id"])
    resolution.update(state="available", document=document)
    diagnostics = [_diagnostic(row["code"], row["path"], refs, severity=row["severity"])
        for row in document["issues"]]
    return resolution, [], diagnostics


def _saved(sheet, components, parameters):
    """Authenticate structure/association only; the host authenticates content."""
    _finite_json(sheet)
    _finite_json(components)
    _require(type(sheet) is dict and set(sheet) == {"version", "analysis_id", "original_task", "documents"}
        and sheet["version"] == SHEET_VERSION and sheet["analysis_id"] == parameters["analysis_id"])
    task = validate_contract("OriginalTask", sheet["original_task"])
    _require(task["required_application_id"] == task["native_application_id"] == parameters["application_id"]
        and parameters["application_id"] in APPLICATIONS)
    _require(type(sheet["documents"]) is list and len(sheet["documents"]) == len(parameters["documents"]))
    for row, specification in zip(sheet["documents"], parameters["documents"], strict=True):
        _require(type(row) is dict and set(row) == {"document_id", "specification", "state", "candidate_contents", "document"}
            and row["document_id"] == specification["document_id"]
            and _canonical(row["specification"]) == _canonical(specification)
            and type(row["state"]) is str and row["state"] in {"available", "missing", "ambiguous", "incompatible"}
            and type(row["candidate_contents"]) is list)
        if row["state"] == "available":
            document = validate_annotation_document(row["document"])
            _require(document["expected_task_id"] == task["task_id"]
                and document["representation"] == specification["representation"]
                and _canonical(row["candidate_contents"]) == _canonical([document["content"]]))
        else:
            _require(row["document"] is None)
        for content in row["candidate_contents"]:
            validate_contract("ContentBinding", content)
        _require(row["state"] != "ambiguous" or len(row["candidate_contents"]) > 1)
        _require(row["state"] != "incompatible" or len(row["candidate_contents"]) == 1)
    _require(type(components) is dict and set(components) == {"version", "analysis_id", "documents"}
        and components["version"] == COMPONENTS_VERSION and components["analysis_id"] == parameters["analysis_id"]
        and type(components["documents"]) is list and len(components["documents"]) == len(sheet["documents"]))
    for result, row in zip(components["documents"], sheet["documents"], strict=True):
        _require(type(result) is dict and set(result) == {"document_id", "components"}
            and result["document_id"] == row["document_id"])
        value, document = result["components"], row["document"]
        if document is None:
            _require(value is None)
            continue
        _require(type(value) is dict and set(value) == {"version", "status", "document_sha256", "population",
            "capture_complete", "reported_contig_count", "reported_feature_count", "contigs", "features", "definitions", "issues"}
            and value["version"] == NATIVE_COMPONENTS_VERSION
            and type(value["status"]) is str and value["status"] in {"complete", "partial"}
            and type(value["definitions"]) is dict and type(value["issues"]) is list
            and value["capture_complete"] is document["capture_complete"]
            and value["document_sha256"] == hashlib.sha256(_canonical(document)).hexdigest(),
            "bvbrc_annotation_saved_document_conflict")
        for name, count in (("contigs", "reported_contig_count"), ("features", "reported_feature_count")):
            records = document["records"][name]["rows"]
            if records is None:
                _require(value[count] is None and value[name] is None)
            else:
                _require(type(value[count]) is int and value[count] == len(records)
                    and type(value[name]) is list and len(value[name]) == len(records))
                for calculated, record in zip(value[name], records, strict=True):
                    _require(type(calculated) is dict and type(calculated.get("ordinal")) is int
                        and calculated["ordinal"] == record["ordinal"] and calculated.get("id") == record["id"])
    return sheet, components


def _member_selection(node, names):
    if names is None:
        return deepcopy(node)
    if node["kind"] != "object":
        return None
    selected = set(names)
    return {"kind": "object", "members": [deepcopy(row) for row in node["members"] if row["name"] in selected]}


def _missing_members(node, names, path):
    if names is None or node["kind"] != "object":
        return []
    present = {row["name"] for row in node["members"]}
    return [_issue("native_selected_member_missing", path + "/" + name.replace("~", "~0").replace("/", "~1"))
        for name in names if name not in present]


def _record(value, ordinal, pointer, *, state=None):
    if state is None:
        state = "stored_null" if value is None or type(value) is dict and value.get("kind") == "null" else "available"
    return {"requested_ordinal": ordinal, "source_pointer": pointer,
        "state": state, "value": deepcopy(value)}


def project_annotation_facts(sheet, components, *, parameters, requested_form):
    """Copy selected retained values; never reparse or recalculate a saved run."""
    parameters, form = validate_parameters(parameters), validate_requested_form(requested_form)
    sheet, components = _saved(sheet, components, parameters)
    documents = {row["document_id"]: row for row in sheet["documents"]}
    calculated = {row["document_id"]: row["components"] for row in components["documents"]}
    facts = {}
    for name in form["required"]:
        selection = form["properties"][name]["x-bvbrc-annotation-selection"]
        _require(selection["document_id"] in documents, "bvbrc_annotation_selected_document_missing")
        resolution = documents[selection["document_id"]]
        document, result = resolution["document"], calculated[selection["document_id"]]
        kind, records, total, requested, matched = selection["kind"], [], None, None, None
        issues = deepcopy(document["issues"] if document is not None else [
            _issue("annotation_document_" + resolution["state"], "/documents/" + resolution["document_id"])])
        if document is None or document["native_document"] is None and kind != "components":
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else [None]
            records = [_record(None, ordinal, None, state="source_unavailable")
                for ordinal in ordinals]
            requested = len(selection["ordinals"]) if selection["ordinals"] is not None else None
        elif kind in {"contigs", "features", "analysis_events"}:
            source = document["records"][kind]
            rows = source["rows"]
            total = None if rows is None else len(rows)
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else (
                list(range(total)) if total is not None else [None])
            requested, matched = len(ordinals), None if rows is None else 0
            for ordinal in ordinals:
                if rows is None:
                    records.append(_record(None, ordinal, source["path"], state="source_unavailable"))
                elif ordinal >= len(rows):
                    records.append(_record(None, ordinal, source["path"], state="path_missing"))
                else:
                    row = rows[ordinal]
                    value = _member_selection(row["native_record"], selection["member_names"])
                    issues.extend(_missing_members(row["native_record"], selection["member_names"], row["path"]))
                    matched += 1
                    records.append(_record(value, ordinal, row["path"],
                        state="incompatible" if value is None else None))
        else:
            total, requested, matched = 1, 1, 1
            if kind == "components":
                value = deepcopy(result)
                if selection["member_names"] is not None:
                    issues.extend(_issue("selected_component_member_missing", "/components/" + key)
                        for key in selection["member_names"] if key not in value)
                    value = {key: value[key] for key in selection["member_names"] if key in value}
                records = [_record(value, None, "/components")]
            else:
                node, pointer = document["native_document"], "/native_document"
                if kind == "quality" and document["representation"] != "quality_json":
                    quality = _field(node, "quality", pointer)
                    node, pointer = quality["value"], quality["path"]
                    if quality["state"] in {"missing", "ambiguous"}:
                        records = [_record(None, None, pointer, state="path_missing" if quality["state"] == "missing" else "incompatible")]
                        matched = 0
                if not records:
                    value = _member_selection(node, selection["member_names"])
                    issues.extend(_missing_members(node, selection["member_names"], pointer))
                    records = [_record(value, None, pointer, state="incompatible" if value is None else None)]
        records = records[selection["offset"]:selection["offset"] + selection["limit"]]
        context = {"analysis_id": parameters["analysis_id"], "original_task": deepcopy(sheet["original_task"]),
            "document_id": resolution["document_id"], "resolution": resolution["state"],
            "representation": resolution["specification"]["representation"],
            "content": None if document is None else deepcopy(document["content"]),
            "capture_complete": None if document is None else document["capture_complete"],
            "native_task_identity": None if document is None else deepcopy(document["identity"]),
            "definitions": None if result is None else deepcopy(result["definitions"])}
        facts[name] = {"version": VALUE_VERSION, "selection": deepcopy(selection), "records": records,
            "record_accounting": {"retained_total": total, "requested_occurrences": requested,
                "matched_occurrences": matched, "returned_occurrences": len(records),
                "population_scope": "retained_native_records_only", "intended_population_complete": None},
            "context": context, "issues": issues}
    return validate_facts(facts, requested_form=form)


def validate_saved_annotation_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_annotation_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), "bvbrc_annotation_saved_facts_conflict")
    return deepcopy(expected)


def annotation_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
    """Status of this selected projection, without native success inference."""
    critical = {"native_analysis_reported_failure", "native_capture_incomplete", "native_task_identity_conflict", "native_task_identity_ambiguous"}
    qualified = bool(missing_requirements) or any(row["severity"] == "error" or row["code"] in critical for row in diagnostics)
    qualified |= any(record["state"] not in {"available", "stored_null"}
        for fact in facts.values() for record in fact["records"])
    qualified |= any(issue["code"] in {"native_selected_member_missing", "selected_component_member_missing"}
        for fact in facts.values() for issue in fact["issues"])
    return "partial" if qualified or bundle_status != "ok" else "ok"


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    parameters, requested_form = validate_parameters(parameters), validate_requested_form(requested_form)
    bundle = validate_contract("ArtifactBundle", bundle)
    task = bundle["original_task"]
    _require(task["required_application_id"] == task["native_application_id"] == parameters["application_id"],
        "bvbrc_annotation_original_application_conflict")
    _require(type(artifact_bytes) is dict and type(supplied_values) is list,
        "bvbrc_annotation_supplied_input_invalid")
    resolutions, values, missing, diagnostics = [], [], [], []
    for specification in parameters["documents"]:
        resolution, requirements, notes = _resolve(bundle, specification, artifact_bytes)
        resolutions.append(resolution)
        values.append({"document_id": specification["document_id"],
            "components": None if resolution["document"] is None else calculate_annotation_components(resolution["document"])})
        missing.extend(requirements)
        diagnostics.extend(notes)
    sheet = {"version": SHEET_VERSION, "analysis_id": parameters["analysis_id"],
        "original_task": deepcopy(task), "documents": resolutions}
    components = {"version": COMPONENTS_VERSION, "analysis_id": parameters["analysis_id"], "documents": values}
    facts = project_annotation_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    return {"adapter_id": ADAPTER_ID, "adapter_version": ADAPTER_VERSION,
        "status": annotation_projection_status(bundle_status=bundle["status"],
            missing_requirements=missing, diagnostics=diagnostics, facts=facts),
        "sheet": sheet, "components": components, "facts": facts,
        "missing_requirements": missing, "diagnostics": diagnostics}


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "SHEET_VERSION", "COMPONENTS_VERSION", "implementation_sha256",
    "parameters_schema", "requested_form_schema", "consume_bundle", "project_annotation_facts",
    "validate_saved_annotation_facts", "annotation_projection_status"]
