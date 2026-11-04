"""Selected HA TSV/alignment observations within the existing Results bundle.

The host authenticates native task and File custody. This adapter never submits
a job, creates an episode, or assigns credit. Saved projection copies the
original observations and shared components without parsing or calculation.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import re

from .bvbrc_annotation_bundle_adapter import _resolve, _record, _diagnostic, _missing
from .bvbrc_annotation_native import _canonical, _finite_json, _issue
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_influenza_ha_contracts import (
    APPLICATION_ID, NATIVE_APPLICATION_ID, VALUE_VERSION, validate_parameters,
    validate_requested_form, validate_facts, parameters_schema, requested_form_schema,
    selected_field_schema, validate_selected_field,
)
from .bvbrc_influenza_ha_native import (
    COMPONENTS_VERSION as NATIVE_COMPONENTS_VERSION, annotation_rows,
    parse_influenza_ha_artifact, validate_influenza_ha_document, calculate_influenza_ha_components,
)


ADAPTER_ID = "bvbrc_influenza_ha"
ADAPTER_VERSION = "1"
SHEET_VERSION = "bvbrc_influenza_ha_observations_v1"
COMPONENTS_VERSION = "bvbrc_influenza_ha_retained_components_v1"
_FORMATS = {"sequence_annotation_tsv": {"tsv"}, "result_alignment_fasta": {"aligned_fasta", "fasta"}}
_DEPENDENCIES = ("__init__.py", "acquisition.py", "domain.py", "public_configuration.py",
    "bvbrc_influenza_ha_native.py", "bvbrc_influenza_ha_contracts.py", "bvbrc_influenza_ha_bundle_adapter.py",
    "bvbrc_annotation_native.py", "bvbrc_annotation_contracts.py", "bvbrc_annotation_bundle_adapter.py",
    "phylogeny_formats.py", "phylogeny_format_contracts.py", "phylogeny_calculators.py",
    "phylogeny_calculation_contracts.py", "bvbrc_appservice_contracts.py", "bvbrc_appservice_schemas.json",
    "alignment_correspondence.py", "sequence_composition_grader.py", "sequence_composition_counts.py",
    "ucsc_acquisition.py", "data_acquisition_receipts.py")
_NATIVE_FIELDS = {"version", "document_sha256", "representation", "status", "native_scores",
    "alignment_selection", "alignment_population", "alignment_components", "ungapped_coordinates",
    "query_reference_correspondence", "definitions", "issues"}


def _require(condition, code="bvbrc_influenza_ha_bundle_invalid"):
    if not condition:
        raise ValueError(code)


def implementation_sha256():
    digest = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = Path(__file__).with_name(name).read_bytes()
        digest.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
    return digest.hexdigest()


def _original_task(task):
    task = validate_contract("OriginalTask", task)
    _require(task["required_application_id"] == APPLICATION_ID
        and task["native_application_id"] == NATIVE_APPLICATION_ID,
        "bvbrc_influenza_ha_original_application_conflict")
    return task


def _query_bindings(documents):
    """Join explicit same-task native QueryIds; keep every candidate occurrence."""
    tables = [(row["document_id"], row["document"]) for row in documents
        if row["document"] is not None and row["specification"]["representation"] == "sequence_annotation_tsv"]
    result = []
    for resolution in documents:
        document, specification = resolution["document"], resolution["specification"]
        if specification["representation"] != "result_alignment_fasta":
            continue
        selection = specification["alignment_selection"]
        native = None if document is None else document["native_document"]
        index = selection["query_row_index"]
        row = None if native is None or index >= len(native["rows"]) else native["rows"][index]
        query_id = None if row is None else row["member_label"]
        candidates = []
        for table_id, table in tables:
            for observation in annotation_rows(table):
                if observation["fields"]["QueryId"] == query_id:
                    candidates.append(dict(document_id=table_id, row_index=observation["row_index"],
                        fields=deepcopy(observation["fields"]), content=deepcopy(table["content"]),
                        capture_complete=table["capture_complete"],
                        parsing_complete=table["native_document"]["completeness"] == "complete"))
        label_count = 0 if native is None else sum(item["member_label"] == query_id for item in native["rows"])
        state = ("incompatible" if query_id is None or re.fullmatch(r"query[1-9][0-9]*", query_id, re.ASCII) is None
            or label_count != 1 else "ambiguous" if len(candidates) > 1 else "missing" if not candidates
            else "incomplete" if not candidates[0]["capture_complete"] or not candidates[0]["parsing_complete"]
                or not document["capture_complete"] or native["completeness"] != "complete" else "resolved")
        result.append(dict(document_id=resolution["document_id"], query_row_index=index, query_id=query_id,
            state=state, candidates=candidates,
            original_sequence_name=candidates[0]["fields"]["Sequence Name"] if state == "resolved" else None,
            identity_scope="native_same_task_QueryId_to_Sequence_Name_only",
            original_input_sequence_content_verified=False))
    return result


def _saved(sheet, components, parameters):
    """Check retained structure/associations; no native parser or calculator."""
    _finite_json(sheet)
    _finite_json(components)
    _require(type(sheet) is dict and set(sheet) == {"version", "analysis_id", "original_task", "documents"}
        and sheet["version"] == SHEET_VERSION and sheet["analysis_id"] == parameters["analysis_id"])
    task = _original_task(sheet["original_task"])
    _require(type(sheet["documents"]) is list and len(sheet["documents"]) == len(parameters["documents"]))
    for row, specification in zip(sheet["documents"], parameters["documents"], strict=True):
        _require(type(row) is dict and set(row) == {"document_id", "specification", "state", "candidate_contents", "document"}
            and row["document_id"] == specification["document_id"]
            and _canonical(row["specification"]) == _canonical(specification)
            and type(row["state"]) is str and row["state"] in {"available", "missing", "ambiguous", "incompatible"}
            and type(row["candidate_contents"]) is list)
        if row["state"] == "available":
            document = validate_influenza_ha_document(row["document"])
            _require(document["expected_task_id"] == task["task_id"]
                and document["representation"] == specification["representation"]
                and _canonical(row["candidate_contents"]) == _canonical([document["content"]]))
        else:
            _require(row["document"] is None)
        for content in row["candidate_contents"]:
            validate_contract("ContentBinding", content)
        _require(row["state"] != "ambiguous" or len(row["candidate_contents"]) > 1)
        _require(row["state"] != "incompatible" or len(row["candidate_contents"]) == 1)
    _require(type(components) is dict and set(components) == {"version", "analysis_id", "documents", "query_bindings"}
        and components["version"] == COMPONENTS_VERSION and components["analysis_id"] == parameters["analysis_id"]
        and type(components["documents"]) is list and len(components["documents"]) == len(sheet["documents"])
        and _canonical(components["query_bindings"]) == _canonical(_query_bindings(sheet["documents"])))
    for result, row in zip(components["documents"], sheet["documents"], strict=True):
        _require(type(result) is dict and set(result) == {"document_id", "components"}
            and result["document_id"] == row["document_id"])
        value, document = result["components"], row["document"]
        if document is None:
            _require(value is None)
            continue
        _require(type(value) is dict and set(value) == _NATIVE_FIELDS
            and value["version"] == NATIVE_COMPONENTS_VERSION
            and value["document_sha256"] == hashlib.sha256(_canonical(document)).hexdigest()
            and value["representation"] == document["representation"]
            and value["status"] in {"complete", "partial"}
            and value["alignment_selection"] == row["specification"]["alignment_selection"]
            and type(value["native_scores"]) is list and type(value["definitions"]) is dict
            and type(value["issues"]) is list, "bvbrc_influenza_ha_saved_document_conflict")
        observations = annotation_rows(document)
        _require(len(value["native_scores"]) == len(observations))
        for observed, retained in zip(value["native_scores"], observations, strict=True):
            _require(type(observed) is dict and set(observed) == {
                "row_index", "query_id", "original_sequence_name", "bitscore", "evalue"}
                and observed["row_index"] == retained["row_index"]
                and observed["query_id"] == retained["fields"]["QueryId"]
                and observed["original_sequence_name"] == retained["fields"]["Sequence Name"])
            for name, field, unit in (("bitscore", "Bitscore", "bits"), ("evalue", "E-value", "expected_random_hits")):
                score = observed[name]
                _require(type(score) is dict and set(score) == {"raw_token", "value", "state", "unit", "origin",
                    "row_index", "field", "population", "uncertainty", "denominator"}
                    and score["raw_token"] == retained["fields"][field]
                    and score["row_index"] == retained["row_index"] and score["field"] == field
                    and score["unit"] == unit and score["origin"] == "native_reported"
                    and score["population"] == "producer_selected_best_hsp_only"
                    and score["uncertainty"] is None and score["denominator"] is None
                    and score["state"] in {"available", "native_missing", "invalid", "not_represented_as_finite_binary64"}
                    and (score["value"] is None) == (score["state"] != "available")
                    and (score["value"] is None or type(score["value"]) in {int, float}))
        alignment = document["native_document"] if document["representation"] == "result_alignment_fasta" else None
        population = value["alignment_population"]
        if population is not None:
            _require(alignment is not None and type(population) is dict
                and population["alignment_id"] == alignment["alignment_id"]
                and population["row_indices"] == list(range(len(alignment["rows"])))
                and population["completeness"] == alignment["completeness"]
                and type(value["alignment_components"]) is dict and type(value["ungapped_coordinates"]) is list
                and type(value["query_reference_correspondence"]) is list)
        else:
            _require(all(value[name] is None for name in
                ("alignment_components", "ungapped_coordinates", "query_reference_correspondence")))
    return sheet, components


def _members(value, names, pointer):
    if names is None:
        return deepcopy(value), []
    if type(value) is not dict:
        return None, []
    return ({name: deepcopy(value[name]) for name in names if name in value},
        [_issue("selected_component_member_missing", pointer + "/" + name.replace("~", "~0").replace("/", "~1"))
            for name in names if name not in value])


def project_influenza_ha_facts(sheet, components, *, parameters, requested_form):
    parameters, form = validate_parameters(parameters), validate_requested_form(requested_form)
    sheet, components = _saved(sheet, components, parameters)
    documents = {row["document_id"]: row for row in sheet["documents"]}
    values = {row["document_id"]: row["components"] for row in components["documents"]}
    facts = {}
    for name in form["required"]:
        selection = form["properties"][name]["x-bvbrc-influenza-ha-selection"]
        _require(selection["document_id"] in documents, "bvbrc_influenza_ha_selected_document_missing")
        resolution = documents[selection["document_id"]]
        document, result = resolution["document"], values[selection["document_id"]]
        native = None if document is None else document["native_document"]
        kind, records, total, requested, matched = selection["kind"], [], None, None, None
        issues = deepcopy(result["issues"] if result is not None else [
            _issue("ha_document_" + resolution["state"], "/documents/" + resolution["document_id"])])
        if kind == "query_bindings":
            indexed_bindings = [(index, row) for index, row in enumerate(components["query_bindings"])
                if row["document_id"] == resolution["document_id"]]
            source = [row for _, row in indexed_bindings]
        elif kind == "records":
            source = None if native is None else native["rows"]
        elif kind == "components":
            source = None if result is None else [result]
        else:
            source = None if native is None else [native]
        if source is None:
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else [None]
            records = [_record(None, ordinal, None, state="source_unavailable") for ordinal in ordinals]
            requested = len(selection["ordinals"]) if selection["ordinals"] is not None else None
        else:
            total = len(source)
            ordinals = selection["ordinals"] if selection["ordinals"] is not None else list(range(total))
            requested, matched = len(ordinals), 0
            for ordinal in ordinals:
                pointer = ("/query_bindings" if kind == "query_bindings" else "/components" if kind == "components"
                    else "/native_document/rows" if kind == "records" else "/native_document")
                if kind in {"records", "query_bindings"}:
                    pointer += "/" + str(indexed_bindings[ordinal][0] if kind == "query_bindings" and ordinal < total else ordinal)
                returned_ordinal = ordinal if kind in {"records", "query_bindings"} else None
                if ordinal >= total:
                    records.append(_record(None, returned_ordinal, pointer, state="path_missing"))
                else:
                    value, notes = _members(source[ordinal], selection["member_names"], pointer)
                    issues.extend(notes)
                    matched += 1
                    records.append(_record(value, returned_ordinal, pointer, state="incompatible" if value is None else None))
        records = records[selection["offset"]:selection["offset"] + selection["limit"]]
        context = dict(analysis_id=parameters["analysis_id"], original_task=deepcopy(sheet["original_task"]),
            document_id=resolution["document_id"], resolution=resolution["state"],
            representation=resolution["specification"]["representation"],
            content=None if document is None else deepcopy(document["content"]),
            capture_complete=None if document is None else document["capture_complete"],
            definitions=None if result is None else deepcopy(result["definitions"]))
        facts[name] = dict(version=VALUE_VERSION, selection=deepcopy(selection), records=records,
            record_accounting=dict(retained_total=total, requested_occurrences=requested,
                matched_occurrences=matched, returned_occurrences=len(records),
                population_scope="retained_native_records_only", intended_population_complete=None),
            context=context, issues=issues)
    return validate_facts(facts, requested_form=form)


def validate_saved_influenza_ha_facts(facts, *, sheet, components, parameters, requested_form):
    expected = project_influenza_ha_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    _require(_canonical(facts) == _canonical(expected), "bvbrc_influenza_ha_saved_facts_conflict")
    return deepcopy(expected)


def influenza_ha_projection_status(*, bundle_status, missing_requirements, diagnostics, facts):
    qualified = bool(missing_requirements) or any(row["severity"] == "error"
        or row["code"] == "native_capture_incomplete" for row in diagnostics)
    qualified |= any(record["state"] not in {"available", "stored_null"}
        for fact in facts.values() for record in fact["records"])
    qualified |= any(issue["code"] == "selected_component_member_missing"
        for fact in facts.values() for issue in fact["issues"])
    return "partial" if qualified or bundle_status != "ok" else "ok"


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    parameters, requested_form = validate_parameters(parameters), validate_requested_form(requested_form)
    bundle = validate_contract("ArtifactBundle", bundle)
    task = _original_task(bundle["original_task"])
    _require(type(artifact_bytes) is dict and type(supplied_values) is list, "bvbrc_influenza_ha_supplied_input_invalid")
    resolutions, values, missing, diagnostics = [], [], [], []
    for specification in parameters["documents"]:
        resolution, requirements, notes = _resolve(bundle, specification, artifact_bytes,
            parse_artifact=parse_influenza_ha_artifact, formats=_FORMATS, family="ha")
        resolutions.append(resolution)
        value = None if resolution["document"] is None else calculate_influenza_ha_components(
            resolution["document"], alignment_selection=specification["alignment_selection"])
        values.append(dict(document_id=specification["document_id"], components=value))
        missing.extend(requirements)
        diagnostics.extend(notes)
        if value is not None:
            diagnostics.extend(_diagnostic(row["code"], row["path"],
                [resolution["document"]["content"]["source_ref"]], severity=row["severity"])
                for row in value["issues"] if row not in resolution["document"]["issues"])
    bindings = _query_bindings(resolutions)
    for binding in bindings:
        if binding["state"] != "resolved":
            specification = next(row for row in parameters["documents"] if row["document_id"] == binding["document_id"])
            code = "ha_original_query_identity_" + binding["state"]
            missing.append(_missing(specification, code, [row["content"]["source_ref"] for row in binding["candidates"]]))
            diagnostics.append(_diagnostic(code, "/query_bindings/" + binding["document_id"]))
    sheet = dict(version=SHEET_VERSION, analysis_id=parameters["analysis_id"], original_task=deepcopy(task), documents=resolutions)
    components = dict(version=COMPONENTS_VERSION, analysis_id=parameters["analysis_id"], documents=values, query_bindings=bindings)
    facts = project_influenza_ha_facts(sheet, components, parameters=parameters, requested_form=requested_form)
    return dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION,
        status=influenza_ha_projection_status(bundle_status=bundle["status"], missing_requirements=missing,
            diagnostics=diagnostics, facts=facts), sheet=sheet, components=components, facts=facts,
        missing_requirements=missing, diagnostics=diagnostics)


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "SHEET_VERSION", "COMPONENTS_VERSION", "VALUE_VERSION",
    "implementation_sha256", "parameters_schema", "requested_form_schema", "validate_parameters", "validate_requested_form",
    "selected_field_schema", "validate_selected_field", "consume_bundle", "project_influenza_ha_facts",
    "validate_saved_influenza_ha_facts", "influenza_ha_projection_status"]
