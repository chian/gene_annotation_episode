"""Selected SubspeciesClassification tables on existing AppService custody."""
from copy import deepcopy
import hashlib
from pathlib import Path

from .bvbrc_annotation_bundle_adapter import _resolve, _record
from .bvbrc_annotation_native import _canonical, _finite_json
from .bvbrc_assembly_bundle_adapter import _select_members
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_subspecies_contracts import (
    APPLICATIONS, VALUE_VERSION, validate_parameters, validate_requested_form, validate_facts,
    parameters_schema, requested_form_schema,
)
from .bvbrc_subspecies_native import (
    COMPONENTS_VERSION as NATIVE_COMPONENTS_VERSION, REPRESENTATIONS,
    parse_subspecies_artifact, validate_subspecies_document, calculate_subspecies_components,
)


ADAPTER_ID = "bvbrc_subspecies"
ADAPTER_VERSION = "1"
SHEET_VERSION = "bvbrc_subspecies_observations_v1"
COMPONENTS_VERSION = "bvbrc_subspecies_retained_components_v1"
_FORMATS = {name: {"tsv"} for name in REPRESENTATIONS}
_DEPENDENCIES = ("__init__.py", "acquisition.py", "domain.py", "public_configuration.py",
    "bvbrc_subspecies_native.py", "bvbrc_subspecies_contracts.py", "bvbrc_subspecies_bundle_adapter.py",
    "bvbrc_assembly_bundle_adapter.py", "bvbrc_assembly_contracts.py", "bvbrc_assembly_native.py",
    "bvbrc_annotation_bundle_adapter.py", "bvbrc_annotation_native.py", "bvbrc_annotation_contracts.py",
    "alignment_correspondence.py", "sequence_composition_grader.py", "sequence_composition_counts.py",
    "ucsc_acquisition.py", "data_acquisition_receipts.py", "bvbrc_appservice_contracts.py",
    "bvbrc_appservice_schemas.json", "phylogeny_formats.py", "phylogeny_format_contracts.py")


def _require(condition, code="bvbrc_subspecies_bundle_invalid"):
    if not condition:
        raise ValueError(code)


def implementation_sha256():
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = Path(__file__).with_name(name).read_bytes()
        digest.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
    return digest.hexdigest()


def _saved(sheet, components, parameters):
    """Read saved associations only; host ContentBindings authenticate values."""
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
            and row["state"] in {"available", "missing", "ambiguous", "incompatible"}
            and type(row["candidate_contents"]) is list)
        if row["state"] == "available":
            document = validate_subspecies_document(row["document"])
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
    for result, resolution in zip(components["documents"], sheet["documents"], strict=True):
        _require(type(result) is dict and set(result) == {"document_id", "components"}
            and result["document_id"] == resolution["document_id"])
        value, document = result["components"], resolution["document"]
        if document is None:
            _require(value is None)
            continue
        _require(type(value) is dict and set(value) == {"version", "document_sha256", "representation", "status",
            "population", "rows", "definitions", "issues"}
            and value["version"] == NATIVE_COMPONENTS_VERSION and value["representation"] == document["representation"]
            and value["status"] == ("partial" if document["issues"] else "complete")
            and value["document_sha256"] == hashlib.sha256(_canonical(document)).hexdigest()
            and type(value["definitions"]) is dict and _canonical(value["issues"]) == _canonical(document["issues"]))
        rows = None if document["native_document"] is None else document["native_document"]["rows"]
        population = value["population"]
        _require(type(population) is dict and set(population) == {"scope", "observed_row_count",
            "complete_artifact_population", "intended_query_population_complete"}
            and population["scope"] == "one_selected_retained_artifact"
            and population["intended_query_population_complete"] is None
            and population["observed_row_count"] == (None if rows is None else len(rows))
            and (type(population["observed_row_count"]) is int if rows is not None else population["observed_row_count"] is None)
            and population["complete_artifact_population"] is
                (None if rows is None else document["capture_complete"] and not document["issues"]))
        _require((value["rows"] is None) == (rows is None))
        if rows is not None:
            _require(type(value["rows"]) is list and len(value["rows"]) == len(rows))
            for ordinal, row in enumerate(value["rows"]):
                _require(type(row) is dict and set(row) == {"row_ordinal", "fields"}
                    and type(row["row_ordinal"]) is int and row["row_ordinal"] == ordinal
                    and type(row["fields"]) is dict)
                for field in row["fields"].values():
                    _require(type(field) is dict and set(field) == {"state", "column_ordinals", "tokens"}
                        and field["state"] in {"column_missing", "column_ambiguous", "cell_missing", "stored_empty", "available"}
                        and type(field["column_ordinals"]) is list and type(field["tokens"]) is list
                        and len(field["column_ordinals"]) == len(field["tokens"]))
                    for index, token in zip(field["column_ordinals"], field["tokens"], strict=True):
                        _require(type(index) is int and index >= 0
                            and token == (rows[ordinal]["cells"][index] if index < len(rows[ordinal]["cells"]) else None))
    return sheet, components


def project_subspecies_facts(sheet, components, *, parameters, requested_form):
    parameters, form = validate_parameters(parameters), validate_requested_form(requested_form)
    sheet, components = _saved(sheet, components, parameters)
    documents = {row["document_id"]: row for row in sheet["documents"]}
    measured = {row["document_id"]: row["components"] for row in components["documents"]}
    facts = {}
    for name in form["required"]:
        selection = form["properties"][name]["x-bvbrc-subspecies-selection"]
        _require(selection["document_id"] in documents, "bvbrc_subspecies_selected_document_missing")
        resolution = documents[selection["document_id"]]
        document, result = resolution["document"], measured[selection["document_id"]]
        source = None if document is None else document["native_document"]
        kind, records, total, requested, matched = selection["kind"], [], None, None, None
        issues = deepcopy([] if document is None else document["issues"])
        if document is None:
            issues.append(dict(code="subspecies_document_" + resolution["state"],
                path="/documents/" + resolution["document_id"], severity="qualification"))
        if kind == "records" and source is not None:
            total = len(source["rows"])
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else list(range(total))
            requested, matched = len(ordinals), 0
            for ordinal in ordinals:
                pointer = "/native_document/rows/" + str(ordinal)
                if ordinal >= total:
                    records.append(_record(None, ordinal, pointer, state="path_missing"))
                else:
                    value, notes = _select_members(source["rows"][ordinal], selection["member_names"], pointer)
                    issues.extend(notes)
                    matched += 1
                    records.append(_record(value, ordinal, pointer))
        elif kind != "records" and document is not None and (source is not None or kind == "components"):
            total = requested = matched = 1
            pointer = "/components" if kind == "components" else "/native_document"
            value, notes = _select_members(result if kind == "components" else source, selection["member_names"], pointer)
            issues.extend(notes)
            records = [_record(value, None, pointer)]
        else:
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else [None]
            records = [_record(None, ordinal, None, state="source_unavailable") for ordinal in ordinals]
            requested = len(selection["ordinals"]) if selection["ordinals"] is not None else None
        records = records[selection["offset"]:selection["offset"] + selection["limit"]]
        facts[name] = dict(version=VALUE_VERSION, selection=deepcopy(selection), records=records,
            record_accounting=dict(retained_total=total, requested_occurrences=requested,
                matched_occurrences=matched, returned_occurrences=len(records),
                population_scope="retained_native_records_only", intended_population_complete=None),
            context=dict(analysis_id=parameters["analysis_id"], original_task=deepcopy(sheet["original_task"]),
                document_id=resolution["document_id"], resolution=resolution["state"],
                representation=resolution["specification"]["representation"],
                content=None if document is None else deepcopy(document["content"]),
                capture_complete=None if document is None else document["capture_complete"],
                definitions=None if result is None else deepcopy(result["definitions"])), issues=issues)
    return validate_facts(facts, requested_form=form)


def validate_saved_subspecies_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_subspecies_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), "bvbrc_subspecies_saved_facts_conflict")
    return deepcopy(expected)


def subspecies_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
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
        "bvbrc_subspecies_original_application_conflict")
    _require(type(artifact_bytes) is dict and type(supplied_values) is list)
    resolutions, values, missing, diagnostics = [], [], [], []
    for specification in parameters["documents"]:
        resolution, requirements, notes = _resolve(bundle, specification, artifact_bytes,
            parse_artifact=parse_subspecies_artifact, formats=_FORMATS, family="subspecies")
        resolutions.append(resolution)
        values.append(dict(document_id=specification["document_id"],
            components=None if resolution["document"] is None else calculate_subspecies_components(resolution["document"])))
        missing.extend(requirements)
        diagnostics.extend(notes)
    sheet = dict(version=SHEET_VERSION, analysis_id=parameters["analysis_id"], original_task=deepcopy(task), documents=resolutions)
    components = dict(version=COMPONENTS_VERSION, analysis_id=parameters["analysis_id"], documents=values)
    facts = project_subspecies_facts(sheet, components, parameters=parameters, requested_form=form)
    return dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION,
        status=subspecies_projection_status(bundle_status=bundle["status"], missing_requirements=missing,
            diagnostics=diagnostics, facts=facts), sheet=sheet, components=components, facts=facts,
        missing_requirements=missing, diagnostics=diagnostics)


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "SHEET_VERSION", "COMPONENTS_VERSION", "implementation_sha256",
    "parameters_schema", "requested_form_schema", "consume_bundle", "project_subspecies_facts",
    "validate_saved_subspecies_facts", "subspecies_projection_status"]
