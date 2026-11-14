"""Explicit ComparativeSystems provider parameters and shared binding checks."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, schema, validate_shape
from .bvbrc_comparative_systems_calculation_contracts import validate_calculation_parameters
from .bvbrc_comparative_systems_data_contracts import validate_data_population_selection
from .bvbrc_comparative_systems_fact_contracts import require, validate_entity

PROFILE_TABLES = {
    "comparative_systems_families_json_v1": {"plfam", "pgfam"},
    "comparative_systems_pathways_json_v1": {"pathway", "ecnumber", "genes"},
    "comparative_systems_subsystems_json_v1": {"subsystems", "genes", "overview"},
    "comparative_systems_pathways_tsv_v1": {"pathways_tsv"},
    "comparative_systems_subsystems_tsv_v1": {"subsystems_tsv"},
    "comparative_systems_variant_matrix_source670b_v1": {"variant_matrix"},
}
PROFILE_ROLES = {
    "comparative_systems_families_json_v1": {"family_summary", "native_document"},
    "comparative_systems_pathways_json_v1": {"pathway_summary", "pathway_ec_summary", "pathway_associations", "native_document"},
    "comparative_systems_subsystems_json_v1": {"subsystem_summary", "subsystem_associations", "subsystem_overview", "native_document"},
    "comparative_systems_pathways_tsv_v1": {"pathway_associations", "native_document"},
    "comparative_systems_subsystems_tsv_v1": {"subsystem_associations", "native_document"},
    "comparative_systems_variant_matrix_source670b_v1": {"subsystem_variants", "native_document"},
}
TABLE_ROWS = {"plfam": "family_rows", "pgfam": "family_rows", "pathway": "pathway_rows",
              "ecnumber": "pathway_ec_rows", "subsystems": "subsystem_rows", "overview": "overview_rows",
              "variant_matrix": "variant_rows"}


def unique_index(rows, key):
    values = {}
    for row in rows:
        require(row[key] not in values, "duplicate_" + key)
        values[row[key]] = row
    return values


def unique(rows):
    values = {}
    for row in rows:
        values.setdefault(canonical_sha256(row), deepcopy(row))
    return list(values.values())


def parameters_schema():
    return schema("ProviderParametersV1")


def validate_parameters(value):
    parameters = validate_shape("ProviderParametersV1", value)
    validate_calculation_parameters(parameters["calculation_parameters"])
    selection = parameters["document_selection"]
    documents = unique_index(selection["documents"], "document_id")
    views = unique_index(selection["authoritative_views"], "view_id")
    producers = unique_index(parameters["producer_evidence_selections"], "evidence_id")
    for document in documents.values():
        require(document["role"] in PROFILE_ROLES[document["format_profile"]], "document_role_profile_mismatch")
        require(document["producer_evidence_id"] is None or document["producer_evidence_id"] in producers,
                "producer_selection_missing")
    for view in views.values():
        require(view["document_id"] in documents, "view_document_reference_missing")
        require(view["table"] in PROFILE_TABLES[documents[view["document_id"]]["format_profile"]], "view_table_incompatible")
    for pair in selection["dependent_views"]:
        require(pair["left_view_id"] in views and pair["right_view_id"] in views
                and pair["left_view_id"] != pair["right_view_id"], "dependent_view_reference_invalid")
    assignments = unique_index(parameters["population_assignments"]["assignments"], "population_id")
    for assignment in assignments.values():
        if assignment["kind"] in {"requested_direct_genomes", "executed_genomes"}:
            require(all(assignment[key] is None for key in ("view_id", "entity", "component_kind")),
                    "population_assignment_selector_invalid")
        else:
            require(assignment["view_id"] in views, "population_view_reference_missing")
            selected = assignment["kind"] == "selected_component_membership"
            require((assignment["entity"] is not None) == selected
                    and (assignment["component_kind"] is not None) == selected, "population_assignment_selector_invalid")
    references = unique_index(parameters["reference_memberships"], "membership_id")
    for reference in references.values():
        validate_entity(reference["entity"])
        require((reference["component_kind"], reference["entity"]["kind"]) in
                {("ec_number", "pathway"), ("role_id", "subsystem")}, "reference_entity_mismatch")
    identifiers = set(assignments)
    data = parameters["supplied_data_selection"]
    if data is not None:
        data = validate_data_population_selection(data)
        genomes = {}
        for record_set in data["record_sets"]:
            population = record_set["declared_genome_population"]
            pid = population["population_id"]
            require(pid not in assignments and record_set["record_set_id"] not in assignments,
                    "population_id_collision")
            require(pid not in genomes or genomes[pid] == population, "population_id_collision")
            genomes[pid] = population
            identifiers.add(record_set["record_set_id"])
        identifiers.update(genomes)
    require(not identifiers & references.keys(), "population_reference_id_collision")
    return parameters


def original_request(task):
    require(task["required_application_id"] == task["native_application_id"] == "ComparativeSystems",
            "original_task_mismatch")
    native = task["submitted_parameters"]
    # The operation's original parameters, including repeats/order, are copied.
    # An unknown group expansion is never reconstructed from today's records.
    require(all(key in native for key in ("genome_ids", "genome_groups", "output_path", "output_file")),
            "original_task_parameters_missing")
    result = {"application": "ComparativeSystems", "task_ref": task["submission_receipt_ref"],
              "request_source_ref": task["submission_source_ref"],
              **{key: deepcopy(native[key]) for key in ("genome_ids", "genome_groups", "output_path", "output_file")},
              "executed_genome_ids": None, "executed_population_evidence": []}
    result = validate_shape("OriginalRequestV1", result)
    require(bool(result["genome_ids"] or result["genome_groups"]), "original_input_population_empty")
    return result


def issue(code, *, document_id=None, role="native_document", refs=(), fields=(), phase="projection"):
    return {"code": code, "phase": phase, "document_id": document_id, "row_ordinal": None,
            "field": role, "source_refs": list(dict.fromkeys(refs)), "locations": [],
            "affected_field_ids": list(dict.fromkeys(fields)), "required_input_role": role}


def requirement(code, *, document_id=None, role="native_document", refs=(), fields=()):
    value = {"code": code, "required_input_role": role, "document_id": document_id,
             "affected_field_ids": list(dict.fromkeys(fields)), "source_refs": list(dict.fromkeys(refs))}
    return {"requirement_id": "comparative:" + canonical_sha256(value), **value}


def at(value, pointer):
    require(type(pointer) is str and (pointer == "" or pointer.startswith("/"))
            and re.search(r"~(?![01])", pointer) is None, "source_pointer_invalid")
    if not pointer:
        return value
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if type(value) is dict and token in value:
            value = value[token]
        elif type(value) is list and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(value):
            value = value[int(token)]
        else:
            require(False, "source_pointer_unresolved")
    return value


def json_value(raw):
    def pairs(rows):
        result = {}
        for key, item in rows:
            require(key not in result, "duplicate_json_key")
            result[key] = item
        return result
    def invalid(_):
        require(False, "nonfinite_number")
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        canonical_sha256(result)
        return result
    except (ValueError, UnicodeError) as error:
        raise ValueError("comparative_systems_source_json_invalid") from error


def checked_bytes(raw, binding):
    require(type(raw) is bytes and len(raw) == binding["byte_count"]
            and hashlib.sha256(raw).hexdigest() == binding["sha256"], "byte_identity_mismatch")
    return raw


__all__ = ["parameters_schema", "validate_parameters", "original_request"]
