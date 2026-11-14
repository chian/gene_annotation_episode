"""Shared TnSeq/RNASeq acquisition-to-native-sheet and saved return plumbing."""
from copy import deepcopy
import hashlib
from pathlib import Path

from .bvbrc_annotation_bundle_adapter import _resolve, _record
from .bvbrc_annotation_native import _canonical, _finite_json
from .bvbrc_assembly_bundle_adapter import _select_members
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_intervention_contracts import (
    VALUE_VERSION, validate_parameters, validate_requested_form, validate_facts,
    parameters_schema, requested_form_schema, selected_field_schema, validate_selected_field,
)
from .intervention_analysis_native import (
    REPRESENTATIONS, parse_intervention_artifact, validate_intervention_document,
    calculate_intervention_components, validate_intervention_components,
)

SHEET_VERSION = "bvbrc_intervention_observations_v1"
COMPONENTS_VERSION = "bvbrc_intervention_retained_components_v1"
APPLICATION_ADAPTERS = {"TnSeq": "bvbrc_tnseq", "RNASeq": "bvbrc_rnaseq"}
_FORMATS = {name: {"tsv", "txt", "text"} for name in REPRESENTATIONS}
_DEPENDENCIES = (
    "bvbrc_intervention_bundle_adapter.py", "bvbrc_intervention_contracts.py",
    "intervention_analysis_native.py", "bvbrc_tnseq_bundle_adapter.py", "bvbrc_rnaseq_bundle_adapter.py",
    "bvbrc_assembly_bundle_adapter.py", "bvbrc_assembly_contracts.py", "bvbrc_assembly_native.py",
    "bvbrc_annotation_bundle_adapter.py", "bvbrc_annotation_contracts.py", "bvbrc_annotation_native.py",
    "bvbrc_appservice_contracts.py", "bvbrc_appservice_schemas.json", "domain.py",
    "alignment_correspondence.py", "sequence_composition_grader.py", "sequence_composition_counts.py",
    "ucsc_acquisition.py", "data_acquisition_receipts.py", "acquisition.py", "public_configuration.py",
    "phylogeny_formats.py", "phylogeny_format_contracts.py", "__init__.py",
)


def _require(condition, code="bvbrc_intervention_bundle_invalid"):
    if not condition:
        raise ValueError(code)


def implementation_sha256():
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = Path(__file__).with_name(name).read_bytes()
        digest.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
    return digest.hexdigest()


def _saved(sheet, components, parameters):
    _finite_json(sheet)
    _finite_json(components)
    _require(type(sheet) is dict and set(sheet) == {"version", "analysis_id", "original_task", "documents",
        "input_bindings", "query_bindings", "scientific_metadata"}
        and sheet["version"] == SHEET_VERSION and sheet["analysis_id"] == parameters["analysis_id"])
    task = validate_contract("OriginalTask", sheet["original_task"])
    _require(task["required_application_id"] == task["native_application_id"] == parameters["application_id"])
    for key, contract in (("input_bindings", "InputBinding"), ("query_bindings", "QueryBinding"),
                          ("scientific_metadata", "SourceEvidence")):
        _require(type(sheet[key]) is list)
        for item in sheet[key]:
            validate_contract(contract, item)
    _require(type(sheet["documents"]) is list and len(sheet["documents"]) == len(parameters["documents"]))
    _require(type(components) is dict and set(components) == {"version", "analysis_id", "documents"}
        and components["version"] == COMPONENTS_VERSION and components["analysis_id"] == parameters["analysis_id"]
        and type(components["documents"]) is list and len(components["documents"]) == len(sheet["documents"]))
    for row, result, spec in zip(sheet["documents"], components["documents"], parameters["documents"], strict=True):
        _require(type(row) is dict and set(row) == {"document_id", "specification", "state", "candidate_contents", "document"}
            and row["document_id"] == spec["document_id"] and row["specification"] == spec
            and row["state"] in {"available", "missing", "ambiguous", "incompatible"}
            and type(row["candidate_contents"]) is list)
        _require(type(result) is dict and set(result) == {"document_id", "components"}
            and result["document_id"] == row["document_id"])
        for content in row["candidate_contents"]:
            validate_contract("ContentBinding", content)
        if row["state"] == "available":
            doc = validate_intervention_document(row["document"])
            _require(doc["expected_task_id"] == task["task_id"] and doc["representation"] == spec["representation"]
                and row["candidate_contents"] == [doc["content"]])
            validate_intervention_components(result["components"], doc)
        else:
            _require(row["document"] is None and result["components"] is None)
        _require(row["state"] != "ambiguous" or len(row["candidate_contents"]) > 1)
        _require(row["state"] != "incompatible" or len(row["candidate_contents"]) == 1)
    return sheet, components


def project_intervention_facts(sheet, components, *, parameters, requested_form):
    parameters, form = validate_parameters(parameters), validate_requested_form(requested_form)
    sheet, components = _saved(sheet, components, parameters)
    documents = {row["document_id"]: row for row in sheet["documents"]}
    measured = {row["document_id"]: row["components"] for row in components["documents"]}
    facts = {}
    for name in form["required"]:
        selection = form["properties"][name]["x-bvbrc-intervention-selection"]
        _require(selection["document_id"] in documents, "bvbrc_intervention_selected_document_missing")
        resolution = documents[selection["document_id"]]
        document, result = resolution["document"], measured[selection["document_id"]]
        native = None if document is None else document["native_document"]
        records, total, requested, matched = [], None, None, None
        issues = deepcopy([] if result is None else result["issues"])
        kind = selection["kind"]
        if kind == "records" and native is not None:
            total = len(native["table"]["rows"])
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else list(range(total))
            requested, matched = len(ordinals), 0
            for ordinal in ordinals:
                pointer = "/native_document/table/rows/" + str(ordinal)
                if ordinal >= total:
                    records.append(_record(None, ordinal, pointer, state="path_missing"))
                else:
                    row = deepcopy(native["table"]["rows"][ordinal])
                    row["measurements"] = deepcopy(result["rows"][ordinal]["metrics"])
                    row["source_location"] = deepcopy(native["lines"][row["line_index"]])
                    value, notes = _select_members(row, selection["member_names"], pointer)
                    issues.extend(notes)
                    records.append(_record(value, ordinal, pointer))
                    matched += 1
        elif kind != "records" and document is not None and (native is not None or kind == "components"):
            total = requested = matched = 1
            pointer = "/components" if kind == "components" else "/native_document"
            value, notes = _select_members(result if kind == "components" else native, selection["member_names"], pointer)
            issues.extend(notes)
            records = [_record(value, None, pointer)]
        else:
            issues.append(dict(code="intervention_document_" + resolution["state"],
                path="/documents/" + resolution["document_id"], severity="qualification"))
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else [None]
            records = [_record(None, ordinal, None, state="source_unavailable") for ordinal in ordinals]
            requested = len(selection["ordinals"]) if selection["ordinals"] is not None else None
        records = records[selection["offset"]:selection["offset"] + selection["limit"]]
        facts[name] = dict(version=VALUE_VERSION, selection=deepcopy(selection), records=records,
            record_accounting=dict(retained_total=total, requested_occurrences=requested, matched_occurrences=matched,
                returned_occurrences=len(records), population_scope="retained_native_records_only", intended_population_complete=None),
            context=dict(analysis_id=parameters["analysis_id"], original_task=deepcopy(sheet["original_task"]),
                document_id=resolution["document_id"], resolution=resolution["state"],
                representation=resolution["specification"]["representation"],
                content=None if document is None else deepcopy(document["content"]),
                capture_complete=None if document is None else document["capture_complete"],
                header=None if native is None else deepcopy(native["table"]["header"]),
                input_bindings=deepcopy(sheet["input_bindings"]), query_bindings=deepcopy(sheet["query_bindings"]),
                scientific_metadata=deepcopy(sheet["scientific_metadata"]),
                definitions=None if result is None else deepcopy(result["definitions"])), issues=issues)
    return validate_facts(facts, requested_form=form)


def validate_saved_intervention_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_intervention_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), "bvbrc_intervention_saved_facts_conflict")
    return deepcopy(expected)


def intervention_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
    qualified = bool(missing_requirements) or bool(diagnostics)
    qualified |= any(record["state"] not in {"available", "stored_null"}
                     for fact in facts.values() for record in fact["records"])
    qualified |= any(fact["issues"] for fact in facts.values())
    return "partial" if qualified or bundle_status != "ok" else "ok"


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    parameters, form = validate_parameters(parameters), validate_requested_form(requested_form)
    bundle = validate_contract("ArtifactBundle", bundle)
    task = bundle["original_task"]
    _require(task["required_application_id"] == task["native_application_id"] == parameters["application_id"],
        "bvbrc_intervention_original_application_conflict")
    _require(type(artifact_bytes) is dict and type(supplied_values) is list)
    resolutions, values, missing, diagnostics = [], [], [], []
    # Acquisition already reports absent required outputs. Publication requires
    # one entry per requirement; parser qualifications remain in diagnostics.
    missing_ids = {row["requirement_id"] for row in bundle["missing_requirements"]}
    for spec in parameters["documents"]:
        resolution, requirements, notes = _resolve(bundle, spec, artifact_bytes,
            parse_artifact=parse_intervention_artifact, formats=_FORMATS, family="intervention")
        resolutions.append(resolution)
        values.append(dict(document_id=spec["document_id"], components=None if resolution["document"] is None
            else calculate_intervention_components(resolution["document"])))
        for requirement in requirements:
            if requirement["requirement_id"] not in missing_ids:
                missing.append(requirement)
                missing_ids.add(requirement["requirement_id"])
        diagnostics.extend(notes)
    sheet = dict(version=SHEET_VERSION, analysis_id=parameters["analysis_id"], original_task=deepcopy(task), documents=resolutions,
        input_bindings=deepcopy(bundle["input_bindings"]), query_bindings=deepcopy(bundle["query_bindings"]),
        scientific_metadata=deepcopy(bundle["supplied_scientific_metadata"]))
    components = dict(version=COMPONENTS_VERSION, analysis_id=parameters["analysis_id"], documents=values)
    facts = project_intervention_facts(sheet, components, parameters=parameters, requested_form=form)
    return dict(adapter_id=APPLICATION_ADAPTERS[parameters["application_id"]], adapter_version="1",
        status=intervention_projection_status(bundle_status=bundle["status"], missing_requirements=missing,
            diagnostics=diagnostics, facts=facts), sheet=sheet, components=components, facts=facts,
        missing_requirements=missing, diagnostics=diagnostics)
