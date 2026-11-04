"""Receiver-selected typed facts, with exact cardinality and honest absence."""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_fastqutils_contracts import (
    validate_contract, validate_parameters, validate_requested_form, validate_sheet, validate_components,
)
from .bvbrc_fastqutils_identity import document_ref, field_ref, literal_ref
from .bvbrc_fastqutils_metadata import _check, _unique, _requirement, _escape, _diagnostic
from .bvbrc_fastqutils_resolution import select_rows


def _payload(kind, row, analysis, documents):
    if kind == "measurement":
        axis = row["axis"]
        result = {k: deepcopy(row[k]) for k in ("state", "value", "unit", "meaning", "precision", "population_ref", "association_ref")}
        result.update(measurement_ref=row["id"], document_id=documents[row["artifact_ref"]]["document_id"],
            quantity=row["metric"], axis=dict(kind=axis["kind"], lower=axis["lower"], upper=axis["upper"],
                label_ref=None if axis["label"] is None else literal_ref(analysis, row["id"], "/axis/label")),
            native_token_ref=None if row["native_token"] is None else literal_ref(analysis, row["id"], "/native_token"))
    elif kind == "component":
        result = {k: deepcopy(v) for k, v in row.items() if k not in ("id", "metric", "diagnostic_codes")}
        result.update(component_ref=row["id"], quantity=row["metric"])
    elif kind == "category":
        result = dict(category_ref=row["id"], native_label_ref=literal_ref(analysis, row["id"], "/native_label"),
                      value=row["value"], association_ref=row["association_ref"])
    elif kind == "population":
        result = {k: deepcopy(row[k]) for k in ("kind", "scope", "representation", "association_ref",
            "member_artifact_refs", "parent_population_refs", "quality_encoding", "encoding_basis")}
        result["population_ref"] = row["id"]
    else:
        result = {k: deepcopy(row[k]) for k in ("library_ref", "stage_ref", "mate", "branch", "state", "basis", "artifact_refs")}
        result["association_ref"] = row["id"]
    return result


def _row_state(kind, row):
    if kind in {"measurement", "component"}:
        return row["state"]
    if kind == "population":
        return {"complete": "available", "partial": "partial", "unknown": "missing"}[row["scope"]]
    if kind == "association":
        return {"established": "available", "unresolved": "missing", "conflicting": "incompatible"}[row["state"]]
    return "available"


def _sources(kind, row, documents, population_index, measurements):
    artifacts = []
    if kind in {"measurement", "category"}:
        artifacts = [row["artifact_ref"]]
    elif kind == "population":
        artifacts = row["member_artifact_refs"]
    elif kind == "association":
        artifacts = row["artifact_refs"]
    elif kind == "component":
        artifacts = [ref for p in row["population_refs"] for ref in population_index[p]["member_artifact_refs"]]
        artifacts += [measurements[r]["artifact_ref"] for r in row["operand_measurement_refs"]]
    result = [documents[r]["artifact"]["source_ref"] for r in artifacts]
    if kind == "association":
        result += row["evidence_refs"]
    if kind in {"component", "population"}:
        for key in ("encoding_basis", "lineage_basis"):
            basis = row.get(key)
            if basis is not None and basis["evidence"] is not None:
                result.append(basis["evidence"]["content"]["source_ref"])
    return _unique(result)


def project_fastqutils_facts(sheet: dict | None, components: dict | None, *,
    requested_form: dict, parameters: dict, failure_context: dict) -> dict:
    parameters = validate_parameters(parameters)
    form = validate_requested_form(requested_form)
    failure_context = validate_contract("ProjectionFailureContext", failure_context)
    if sheet is not None:
        validate_sheet(sheet)
        _check(sheet["analysis_id"] == parameters["analysis_id"])
    if components is not None:
        _check(sheet is not None)
        validate_components(components, sheet=sheet)
    analysis = parameters["analysis_id"]
    declared_documents = {d["document_id"] for d in parameters["documents"]}
    declared_calculations = {r["calculation_id"] for r in parameters["calculation_requests"]}
    fields = {row["field"]: row["selection"] for row in form["fields"]}
    for name, selection in fields.items():
        target = selection["target"]
        if target["kind"] == "request_status":
            other = fields.get(target["field"])
            _check(target["field"] != name and other is not None and other["target"]["kind"] != "request_status", "requested_form_invalid")
        elif "selector" in target and target["selector"]["selection"] == "semantic":
            selector = target["selector"]
            _check("document_id" not in selector or selector["document_id"] in declared_documents, "requested_form_invalid")
            _check("calculation_id" not in selector or selector["calculation_id"] in declared_calculations, "requested_form_invalid")
    documents = {d["artifact"]["id"]: d for d in (sheet or {}).get("documents", [])}
    docmap = {d["document_id"]: d for d in documents.values()}
    resolutions = {r["document_id"]: r for r in (sheet or {}).get("document_resolutions", [])}
    populations = {p["id"]: p for p in (sheet or {}).get("populations", [])}
    measurements = {r["id"]: r for r in (sheet or {}).get("measurements", [])}
    requirements = _unique(failure_context["requirements"] + (sheet or {}).get("requirements", []) + (components or {}).get("requirements", []))
    diagnostics = _unique(failure_context["diagnostics"] + (sheet or {}).get("diagnostics", []) + (components or {}).get("diagnostics", []))
    facts = {}
    # Requirements and request status are derived only after ordinary selections;
    # this order prevents self-support and request-status cycles.
    for name, selection in fields.items():
        target, kind = selection["target"], selection["target"]["kind"]
        if kind in {"requirements", "request_status"}:
            continue
        selector = target["selector"]
        rows = select_rows(sheet, kind, selector, components)
        document_id = selector.get("document_id")
        resolution = resolutions.get(document_id)
        document = docmap.get(document_id)
        target_refs = {document_ref(analysis, document_id)} if document_id else set()
        unavailable_codes, missing_requirements = [], []
        source_complete = False
        if document is not None:
            source_complete = document["parse_scope"] == "complete" and document["artifact"]["transfer_scope"] == "complete"
            if "section_key" in selector:
                sections = [s for s in document["sections"] if s["key"] == selector["section_key"] and s["ordinal"] == selector["section_ordinal"]]
                source_complete = source_complete and len(sections) == 1 and sections[0]["state"] == "complete"
        elif kind == "component":
            source_complete = components is not None
        if resolution is not None and resolution["state"] != "available":
            missing_requirements = list(resolution["requirement_refs"])
            unavailable_codes = list(resolution["diagnostic_codes"])
        if not rows and not source_complete and not missing_requirements:
            relevant = [r for r in requirements if set(r["affected_refs"]) & target_refs]
            missing_requirements = [r["id"] for r in relevant]
            unavailable_codes = _unique([r["code"] for r in relevant])
        records = []
        for row in rows:
            state = _row_state(kind, row)
            row_refs = {row["id"]}
            if kind == "component":
                row_refs.update(row["population_refs"])
                row_refs.update(row["operand_measurement_refs"])
            elif kind == "measurement" and row["population_ref"] is not None:
                row_refs.add(row["population_ref"])
            # Artifact-wide numerical failures qualify a missing/partial row;
            # unrelated stage, sample and reference metadata never erase counts.
            if state != "available":
                if "artifact_ref" in row:
                    row_refs.add(row["artifact_ref"])
                if kind == "population":
                    row_refs.update(row["member_artifact_refs"])
            relevant = [r for r in requirements if set(r["affected_refs"]) & row_refs]
            record = dict(kind=kind, record_ref=row["id"], state=state,
                payload=_payload(kind, row, analysis, documents),
                source_refs=_sources(kind, row, documents, populations, measurements),
                requirement_refs=_unique([r["id"] for r in relevant]),
                diagnostic_codes=_unique(row.get("diagnostic_codes", []) +
                    (["association_unresolved"] if kind == "association" and state != "available" else [])))
            records.append(record)
        matched_count = len(rows)
        cardinality = selection["cardinality"]
        if cardinality == "one_target" and not rows:
            if not unavailable_codes:
                unavailable_codes = ["missing_requested_value"]
            if not missing_requirements:
                req = _requirement(analysis, "/facts/" + _escape(name), unavailable_codes[0], "requested_measurement", list(target_refs))
                requirements.append(req)
                missing_requirements = [req["id"]]
            missing_state = "ambiguous" if resolution and resolution["state"] == "ambiguous" else "incompatible" if resolution and resolution["state"] == "incompatible" else "missing"
            records = [dict(kind=kind, record_ref=None, state=missing_state, payload=None, source_refs=[],
                requirement_refs=missing_requirements, diagnostic_codes=unavailable_codes)]
        selected_requirements = _unique(missing_requirements + [ref for r in records for ref in r["requirement_refs"]])
        codes = []
        if cardinality == "one_target" and (matched_count > 1 or resolution and resolution["state"] == "ambiguous"):
            field_state, codes = "ambiguous", ["selection_ambiguous"]
        elif cardinality == "exact_rows" and matched_count != selection["expected_cardinality"]:
            field_state, codes = "cardinality_mismatch", ["selection_cardinality_mismatch"]
        elif cardinality == "exact_rows" and not matched_count and not source_complete:
            field_state, codes = "missing_value", unavailable_codes or ["missing_requested_value"]
        elif selection["availability_requirement"] == "available_value" and any(
                r["payload"] is None or r["state"] != "available" for r in records):
            field_state = "missing_value"
            codes = _unique([code for r in records for code in r["diagnostic_codes"]]) or ["missing_requested_value"]
        else:
            field_state = "satisfied"
            # Missing slot envelopes retain their explanation even when typed
            # absence is precisely the receiver's requested information.
            if not rows and records:
                codes = unavailable_codes
        fact = dict(selection=deepcopy(selection), matched_count=matched_count, state=field_state,
            satisfied=field_state == "satisfied", records=records, requirement_refs=selected_requirements,
            diagnostic_codes=_unique(codes))
        facts[name] = validate_contract("ProjectedField", fact)
        if field_state != "satisfied":
            diagnostics.extend(_diagnostic(code, [field_ref(analysis, name)]) for code in codes)
    requirements = _unique(requirements)
    for name, selection in fields.items():
        if selection["target"]["kind"] != "requirements":
            continue
        record = dict(kind="requirements", record_ref=field_ref(analysis, name), state="available",
            payload=dict(requirements=deepcopy(requirements)),
            source_refs=_unique([s for r in requirements for s in r["source_refs"]]),
            requirement_refs=[r["id"] for r in requirements], diagnostic_codes=[])
        count_ok = selection["cardinality"] == "one_target" or selection["expected_cardinality"] == 1
        facts[name] = dict(selection=deepcopy(selection), matched_count=1,
            state="satisfied" if count_ok else "cardinality_mismatch", satisfied=count_ok, records=[record],
            requirement_refs=record["requirement_refs"], diagnostic_codes=[] if count_ok else ["selection_cardinality_mismatch"])
    for name, selection in fields.items():
        if selection["target"]["kind"] != "request_status":
            continue
        other_name = selection["target"]["field"]
        other = facts[other_name]
        record = dict(kind="request_status", record_ref=field_ref(analysis, name), state="available",
            payload=dict(field=other_name, satisfied=other["satisfied"], state=other["state"],
                matched_count=other["matched_count"], requirement_refs=deepcopy(other["requirement_refs"])),
            source_refs=_unique([s for r in other["records"] for s in r["source_refs"]]),
            requirement_refs=deepcopy(other["requirement_refs"]), diagnostic_codes=[])
        count_ok = selection["cardinality"] == "one_target" or selection["expected_cardinality"] == 1
        facts[name] = dict(selection=deepcopy(selection), matched_count=1,
            state="satisfied" if count_ok else "cardinality_mismatch", satisfied=count_ok, records=[record],
            requirement_refs=deepcopy(other["requirement_refs"]), diagnostic_codes=[] if count_ok else ["selection_cardinality_mismatch"])
    facts = {name: facts[name] for name in fields}
    result = dict(facts=facts, status="ok" if all(r["satisfied"] for r in facts.values()) else "partial",
        requirements=requirements, diagnostics=_unique(diagnostics), failure_context=deepcopy(failure_context))
    return validate_contract("ProjectionResult", result)


__all__ = ["project_fastqutils_facts"]
