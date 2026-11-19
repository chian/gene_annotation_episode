"""Ordinary protein action views and their typed fact sources.

Scientific rows and calculations belong to the existing protein modules. This
adapter validates typed action views and deliveries; public Source
custody never creates an execution episode, handoff or File permission.
"""
from copy import deepcopy
import json
import math

from jsonschema import Draft202012Validator, validators

from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.domain import canonical, identity
from gene_annotation_episode.episodic_workflow.episode_support.forms.structural_homology_evidence.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_homology_evidence import protein_structure_contracts as science
from gene_annotation_episode.episodic_workflow.episode_support.readers.protein_structure.structural_homology_evidence import protein_structure_result_views as views
from gene_annotation_episode.episodic_workflow.episode_support.tools.protein_structure.protein_structure_authority import ProteinStructureOperandError

VIEW_SOURCE = "protein_structure_action_views"
SEQUENCE_SOURCE = "protein_structure_action_sequences"
SAVED_SOURCE = "protein_structure_action_saved_sheets"
FACT_SOURCES = (VIEW_SOURCE, SEQUENCE_SOURCE, SAVED_SOURCE)
TOOLS = {"inspect_protein_structure": "inspect",
    "extract_protein_structure_sequence": "extract_sequence", "compare_protein_structures": "compare"}
RESULT_VERSION = "protein_structure_tool_result_v1"
SAVED_ACTION_SOURCE_VERSION = "protein_structure_saved_action_v1"
_PAYLOAD_FIELDS = {VIEW_SOURCE: "views", SEQUENCE_SOURCE: "sequences", SAVED_SOURCE: "saved_sheets"}


def _error(code="original_commission_mismatch", *, field="receipt"):
    return ProteinStructureOperandError(science.issue(code, stage="authority", field=field))


def _require(condition, code="original_commission_mismatch", *, field="receipt"):
    if not condition:
        raise _error(code, field=field)


def _object(**properties):
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def _definitions():
    # Reuse shared row/cell schemas. Only this opt-in resource admits action
    # descriptors; the default legacy public resources are untouched.
    definitions = views._schema("ProjectionRows")["$defs"]
    definitions.update(science.protein_structure_schema_definitions(action_custody=True))
    ref = lambda name: {"$ref": "#/$defs/" + name}
    artifact = deepcopy(definitions["ProjectionRows"]["oneOf"])
    artifacts = []
    for row_ref in artifact:
        row_type = deepcopy(definitions[row_ref["$ref"].rsplit("/", 1)[1]])
        properties = row_type["properties"]
        properties.pop("rows")
        properties["version"] = {"const": "protein_structure_action_artifact_view_v1"}
        properties["delivery"] = ref("ArtifactDelivery")
        row_type["required"] = list(properties)
        artifacts.append(row_type)
    definitions["ProteinActionArtifactView"] = {"oneOf": artifacts}
    definitions["ProteinActionUnavailable"] = _object(
        version={"const": "protein_structure_action_unavailable_v1"},
        issues={"type": "array", "items": ref("StructuredIssue"), "minItems": 1})
    definitions["ProteinActionView"] = _object(
        version={"const": "protein_structure_action_view_v1"},
        source_ref={"type": "string", "format": "reference", "x-reference-namespace": "source",
            "pattern": "^source_[a-f0-9]{24,64}$"},
        operation={"enum": list(TOOLS.values())}, selection=ref("ProjectionSelection"),
        outcome={"oneOf": [ref("ProjectionRows"), ref("ProteinActionArtifactView"), ref("ProteinActionUnavailable")]})
    definitions["ProteinActionResult"] = _object(
        version={"const": RESULT_VERSION},
        source_ref=deepcopy(definitions["ProteinActionView"]["properties"]["source_ref"]),
        operation={"enum": list(TOOLS.values())},
        views={"type": "array", "items": ref("ProteinActionView")},
        sequences={"type": "array", "items": ref("StructureSequenceDescriptorV2")},
        saved_sheets={"type": "array", "items": ref("SavedSheetDescriptorV2")},
        issues={"type": "array", "items": ref("StructuredIssue")})
    return definitions


def _schema(name):
    return {"$defs": _definitions(), "$ref": "#/$defs/" + name}


def _shape(name, value):
    science._json_only(value)
    strict = validators.extend(Draft202012Validator, type_checker=
        Draft202012Validator.TYPE_CHECKER.redefine("integer", lambda _, item: type(item) is int)
        .redefine("number", lambda _, item: type(item) in (int, float) and math.isfinite(item)))
    if not strict(_schema(name)).is_valid(value):
        raise ValueError("invalid_schema")


def _reachable_definitions(definitions, name):
    pending, selected = [name], set()
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        selected.add(name)
        nodes = [definitions[name]]
        while nodes:
            value = nodes.pop()
            if isinstance(value, dict):
                reference = value.get("$ref")
                if isinstance(reference, str) and reference.startswith("#/$defs/"):
                    pending.append(reference[len("#/$defs/"):])
                nodes.extend(value.values())
            elif isinstance(value, list):
                nodes.extend(value)
    return {name: deepcopy(value) for name, value in definitions.items() if name in selected}


def protein_structure_action_fact_sources():
    names = {VIEW_SOURCE: "ProteinActionView", SEQUENCE_SOURCE: "StructureSequenceDescriptorV2",
        SAVED_SOURCE: "SavedSheetDescriptorV2"}
    meanings = {VIEW_SOURCE: "Exactly selected retained protein values or selected-table identity from an authenticated ordinary action.",
        SEQUENCE_SOURCE: "Original structure-derived sequence descriptor and explicitly selected allowed uses from an authenticated ordinary action.",
        SAVED_SOURCE: "Original protein saved-sheet descriptor with declared uses; Source custody does not itself grant Files or authority."}
    result = {}
    for source, name in names.items():
        resource = {"$defs": _reachable_definitions(_definitions(), name), "type": "array", "items": {"$ref": "#/$defs/" + name}}
        resource["$id"] = "urn:gene-annotation:protein-action:" + digest(resource)
        document = {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": deepcopy(resource["$defs"]), "type": "array", "allOf": [resource], "x-source": source}
        document["$id"] = "urn:gene-annotation:protein-action:" + digest(document)
        result[source] = dict(type="array", meaning=meanings[source], report_schema=document)
    return result


def validate_protein_structure_action_view(value):
    _shape("ProteinActionView", value)
    selection, outcome = value["selection"], value["outcome"]
    views.validate_protein_structure_projection_selection(selection)
    kind, family = value["operation"], selection["family"]
    if (kind == "inspect" and family != "structure_inventory"
            or kind == "extract_sequence" and family not in {"extracted_sequence", "native_uncertainty"}
            or kind == "compare" and family in {"structure_inventory", "extracted_sequence"}
            or family == "native_uncertainty" and (kind == "extract_sequence") != (
                selection["members"]["structure_role"] == "single")):
        raise ValueError("invalid_schema")
    if outcome["version"] == "protein_structure_action_unavailable_v1":
        science._relations(outcome)
        return deepcopy(value)
    if not science.same(selection, outcome["selection"]):
        raise ValueError("conflicting_identity")
    if outcome["version"] == "protein_structure_projection_rows_v1":
        if selection["delivery_kind"] != "values":
            raise ValueError("conflicting_identity")
        views.validate_protein_structure_projection_rows(outcome)
    else:
        if selection["delivery_kind"] != "artifact":
            raise ValueError("conflicting_identity")
        views._envelope(outcome, None)
        delivery = outcome["delivery"]
        science.validate_file_identity(delivery["table_file"])
        if (delivery["table_file"]["format"] != "protein_structure_projection_table_v1"
                or delivery["row_count"] != outcome["returned_count"]
                or "artifact_descriptor_not_numerical_delivery" not in outcome["qualifications"]):
            raise ValueError("conflicting_identity")
    return deepcopy(value)


def protein_structure_action_view_identity(value):
    value = validate_protein_structure_action_view(value)
    return value["source_ref"], canonical(value["selection"])


def validate_protein_structure_tool_result(value):
    _shape("ProteinActionResult", value)
    keys = []
    for item in value["views"]:
        validate_protein_structure_action_view(item)
        if item["source_ref"] != value["source_ref"] or item["operation"] != value["operation"]:
            raise ValueError("conflicting_identity")
        keys.append(protein_structure_action_view_identity(item))
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate_selection")
    for field, version, operation, validator in (
            ("sequences", "structure_sequence_descriptor_v2", "extract_sequence", science.validate_structure_sequence_descriptor_v2),
            ("saved_sheets", "protein_structure_saved_sheet_v2", "compare", science.validate_saved_sheet_descriptor_v2)):
        if value[field] and value["operation"] != operation:
            raise ValueError("conflicting_identity")
        for item in value[field]:
            validator(item)
            if item["version"] != version or item["custody"]["source_ref"] != value["source_ref"]:
                raise ValueError("conflicting_identity")
        if len(value[field]) > 1:
            raise ValueError("duplicate_selection")
    return deepcopy(value)


def action_view_from_projection_rows(rows, *, source_ref, operation, table_file=None):
    rows = views.validate_protein_structure_projection_rows(rows)
    if rows["selection"]["delivery_kind"] == "values":
        if table_file is not None:
            raise ValueError("conflicting_identity")
        outcome = rows
    else:
        if table_file is None:
            raise ValueError("selected_field_unavailable")
        science.validate_file_identity(table_file)
        outcome = {key: deepcopy(item) for key, item in rows.items() if key != "rows"}
        outcome.update(version="protein_structure_action_artifact_view_v1", delivery=dict(kind="artifact",
            table_file=deepcopy(table_file), row_count=rows["returned_count"], allowed_use="read_exact_selected_table"))
    return validate_protein_structure_action_view(dict(version="protein_structure_action_view_v1",
        source_ref=source_ref, operation=operation, selection=deepcopy(rows["selection"]), outcome=outcome))


def project_protein_structure_action_views(scientific, *, source_ref, operation, selections,
                                         issues=(), artifact_files=None):
    if type(selections) is not list or len({item["projection_id"] for item in selections}) != len(selections):
        raise ValueError("duplicate_selection")
    output = []
    for selection in selections:
        selection = views.validate_protein_structure_projection_selection(selection)
        if scientific is None:
            selected_issues = list(deepcopy(issues)) or [science.issue("selected_field_unavailable", stage="projection", field="projection_fields")]
            item = dict(version="protein_structure_action_view_v1", source_ref=source_ref, operation=operation,
                selection=selection, outcome=dict(version="protein_structure_action_unavailable_v1", issues=selected_issues))
        else:
            try:
                rows, = views.project_protein_structure_results(scientific, selection=[selection])
            except ValueError as error:
                from typing import get_args
                code = str(error) if str(error) in get_args(science.IssueCode) else "invalid_schema"
                item = dict(version="protein_structure_action_view_v1", source_ref=source_ref, operation=operation,
                    selection=selection, outcome=dict(version="protein_structure_action_unavailable_v1",
                        issues=[science.issue(code, stage="projection", field="projection_fields")]))
            else:
                table = None if artifact_files is None else artifact_files.get(selection["projection_id"])
                item = action_view_from_projection_rows(rows, source_ref=source_ref, operation=operation, table_file=table)
        output.append(validate_protein_structure_action_view(item))
    return output


def _validate_fact(value, fact_source):
    if fact_source == VIEW_SOURCE:
        return validate_protein_structure_action_view(value)
    if fact_source == SEQUENCE_SOURCE:
        return science.validate_structure_sequence_descriptor_v2(value)
    if fact_source == SAVED_SOURCE:
        return science.validate_saved_sheet_descriptor_v2(value)
    raise ValueError("invalid_schema")


def _fact_source_ref(value, fact_source):
    return value["source_ref"] if fact_source == VIEW_SOURCE else value["custody"]["source_ref"]


def merge_protein_structure_action_facts(*groups, fact_source):
    result, seen = [], {}
    for group in groups:
        _require(type(group) is list, "invalid_schema")
        for item in group:
            item = _validate_fact(item, fact_source)
            source = _fact_source_ref(item, fact_source)
            key = (protein_structure_action_view_identity(item) if fact_source == VIEW_SOURCE else
                (source, item["reference_ref"]) if fact_source == SEQUENCE_SOURCE else source)
            encoded = canonical(item)
            _require(key not in seen or seen[key] == encoded)
            if key not in seen:
                result.append(item)
                seen[key] = encoded
    return result


def requested_protein_structure_action_fields(schema, *, fact_source):
    if fact_source not in FACT_SOURCES:
        raise ValueError("invalid_schema")
    properties = plain(schema).get("properties", {})
    if not any(isinstance(node, dict) and node.get("x-source") == fact_source for node in properties.values()):
        return []
    expected = protein_structure_action_fact_sources()[fact_source]["report_schema"]
    fields = []
    for name, node in properties.items():
        if node.get("x-source") == fact_source:
            _require(science.same(node, expected), "invalid_schema")
            fields.append(name)
    return fields


def protein_structure_action_form_references(form, schema):
    """Project typed references after the caller's frozen-value admission check.

    This projection is not producer authority and never grants File identities
    or private publication controls. Existing native/received owners perform
    the actual value and receipt checks before this specialist hook is called.
    """
    form, references = plain(form), []
    for source in FACT_SOURCES:
        for field in requested_protein_structure_action_fields(schema, fact_source=source):
            _require(type(form) is dict and field in form and type(form[field]) is list, "invalid_schema")
            for value in form[field]:
                value = _validate_fact(value, source)
                references.append(_fact_source_ref(value, source))
                if source == SEQUENCE_SOURCE:
                    references.append(value["reference_ref"])
    return list(dict.fromkeys(references))


__all__ = ["FACT_SOURCES", "VIEW_SOURCE", "SEQUENCE_SOURCE", "SAVED_SOURCE",
    "protein_structure_action_fact_sources", "validate_protein_structure_tool_result", "validate_protein_structure_action_view",
    "protein_structure_action_view_identity", "action_view_from_projection_rows", "project_protein_structure_action_views",
    "merge_protein_structure_action_facts", "requested_protein_structure_action_fields", "protein_structure_action_form_references"]
