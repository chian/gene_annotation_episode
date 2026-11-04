"""Saved ComparativeSystems Data handoffs; no decoding or host admission.

These facades use the one packaged shared schema. They check saved identities,
references and count relationships, never repeat extraction or a scientific
calculation. Caller-authored host flags do not establish receiver possession.
"""
from __future__ import annotations

from collections import Counter
import json

from .bvbrc_comparative_systems_handoff_contracts import validate_shape
from .bvbrc_data_fields import FIELD_REGISTRY

__all__ = ("validate_data_population_selection", "validate_supplied_record_sets")

_ROLES = {
    "genome": {"genome_records", "original_genome_population"},
    "genome_feature": {"family_feature_records"},
    "pathway": {"pathway_records"}, "subsystem": {"subsystem_records"},
    "protein_family_ref": {"family_reference"},
    "pathway_ref": {"pathway_reference", "reference_membership"},
    "subsystem_ref": {"subsystem_reference", "reference_membership"},
}


def _require(condition, code):
    if not condition:
        raise ValueError("comparative_systems_data_" + code)


def _count(cell, *, population_id, unit, value=None):
    _require(cell["population_id"] == population_id and cell["unit"] == unit,
             "count_population_mismatch")
    if cell["state"] == "available":
        _require(type(cell["value"]) is int and cell["value"] >= 0, "count_integer_required")
        if value is not None:
            _require(cell["value"] == value, "count_value_mismatch")


def _population(population, *, genome=False):
    pid = population["population_id"]
    _require(population["member_kind"] == ("genome_id" if genome else "record_id"),
             "population_member_kind_mismatch")
    if genome:
        _require(population["kind"] in {"declared_query_genomes", "requested_direct_genomes", "executed_genomes"},
                 "genome_population_kind_mismatch")
    else:
        _require(population["kind"] == "supplied_data_records", "record_population_kind_mismatch")
    unit = "genome" if genome else "record"
    _count(population["raw_occurrence_count"], population_id=pid, unit=unit,
           value=len(population["members"]) if genome else None)
    _count(population["distinct_valid_member_count"], population_id=pid, unit=unit,
           value=len(set(population["members"])))
    _require(not set(population["members"]) & set(population["missing_members"]),
             "population_missing_member_conflict")
    if population["completeness"] == "complete_for_declared_population":
        _require(not population["missing_members"] and not population["unresolved_members"],
                 "complete_population_unresolved")
        _require(all(population[key]["state"] == "available"
                     for key in ("raw_occurrence_count", "distinct_valid_member_count")),
                 "complete_population_count_missing")


def validate_data_population_selection(value: object) -> dict:
    """Validate finite selected IDs and meanings, without claiming evidence."""
    result = validate_shape("DataPopulationSelectionV1", value)
    ids, genomes = set(), {}
    for selected in result["record_sets"]:
        rid, collection = selected["record_set_id"], selected["collection"]
        _require(rid not in ids, "duplicate_record_set_id")
        ids.add(rid)
        population = selected["declared_genome_population"]
        _population(population, genome=True)
        pid = population["population_id"]
        _require(pid not in genomes or genomes[pid] == population, "population_id_collision")
        genomes[pid] = population
        registry = FIELD_REGISTRY[collection]
        _require(all(field in registry["fields"] and registry["fields"][field]["stored"]
                     for field in selected["selected_fields"]), "selected_field_unavailable")
        _require(registry["unique_key"] in selected["selected_fields"], "selected_unique_key_required")
        sort = selected["sort"]
        _require(len({item["field"] for item in sort}) == len(sort), "duplicate_sort_field")
        _require(all(item["field"] in registry["fields"] and registry["fields"][item["field"]]["sort_supported"]
                     for item in sort), "sort_field_unavailable")
        _require(registry["unique_key"] in {item["field"] for item in sort}, "stable_sort_required")
        _require(set(selected["roles"]) <= _ROLES[collection], "role_collection_mismatch")
        _require(selected["annotation_filter"] == "none" or "annotation" in registry["fields"],
                 "annotation_filter_collection_mismatch")
        evidence = selected["snapshot_evidence"]
        _require(evidence["kind"] != "single_complete_response" or evidence["snapshot_id"] is None,
                 "single_response_snapshot_id_invalid")
        for location in evidence["source_locations"]:
            _require(location["source_ref"] in selected["source_refs"], "snapshot_source_not_selected")
    _require(not ids & genomes.keys(), "population_id_collision")
    return result


def _scalar_string(row, field):
    cells = [cell for cell in row["cells"] if cell["field"] == field]
    if len(cells) != 1:
        return None
    cell = cells[0]
    if (cell["status"] == "valid" and cell["native_shape"] == "scalar"
            and len(cell["atoms"]) == 1 and cell["atoms"][0]["kind"] == "string"):
        return cell["atoms"][0]["string_value"]
    return None


def _scalar_identifier(row, field):
    text = _scalar_string(row, field)
    return text if text and text.strip() else None


def _atom_text(atom, *, nested=False):
    if atom["kind"] == "number":
        return atom["number_lexeme"]
    value = (atom["string_value"] if atom["kind"] == "string" else
             atom["boolean_value"] if atom["kind"] == "boolean" else None)
    return value if type(value) is str and not nested else json.dumps(value, ensure_ascii=False)


def _field_text(cell):
    """Correspondence of saved primitive cell values, without source decoding."""
    if cell["presence"] == "null":
        return "null"
    if cell["native_shape"] == "scalar" and len(cell["atoms"]) == 1:
        return _atom_text(cell["atoms"][0])
    if cell["native_shape"] == "array" and (cell["atoms"] or cell["status"] == "valid"):
        return "[" + ",".join(_atom_text(atom, nested=True) for atom in cell["atoms"]) + "]"
    return None


def _saved_reference(record_set, reference):
    _require(reference["kind"] == "supplied" and reference["owner_id"] == record_set["record_set_id"],
             "count_reference_owner_mismatch")
    value = record_set
    for token in reference["pointer"].split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        if type(value) is list:
            _require(token.isascii() and token.isdigit() and str(int(token)) == token
                     and int(token) < len(value), "count_reference_missing")
            value = value[int(token)]
        else:
            _require(type(value) is dict and token in value, "count_reference_missing")
            value = value[token]


def validate_supplied_record_sets(value: object) -> dict:
    """Validate a saved D result without source bytes, extraction or I/O."""
    result = validate_shape("SuppliedRecordSetsV1", value)
    selection = validate_data_population_selection(result["selection"])
    selected = {item["record_set_id"]: item for item in selection["record_sets"]}
    _require([item["record_set_id"] for item in result["record_sets"]] == list(selected),
             "record_set_selection_mismatch")
    association_ids = set()
    for record_set in result["record_sets"]:
        rid = record_set["record_set_id"]
        request = selected[rid]
        collection = record_set["collection"]
        _require(collection == request["collection"] and record_set["annotation_filter"] == request["annotation_filter"],
                 "saved_selection_mismatch")
        population = record_set["population"]
        _population(population)
        _require(population["population_id"] == rid, "record_population_id_mismatch")
        pages = {}
        for page in record_set["pages"]:
            binding = page["binding"]
            source = binding["source_ref"]
            _require(source in request["source_refs"] and source not in pages, "page_source_mismatch")
            _require(binding["collection"] == collection, "page_collection_mismatch")
            pages[source] = page
            for location in page["snapshot_evidence"]["source_locations"]:
                _require(location["source_ref"] == source and location["raw_artifact_ref"] == binding["native_artifact_ref"]
                         and location["document_id"] is None, "snapshot_location_mismatch")
            if page["snapshot_evidence"]["kind"] == "single_complete_response":
                _require(page["snapshot_evidence"]["snapshot_id"] is None and page["body_complete"]
                         and page["partial_results"] is not True and page["num_found_exact"] is True
                         and page["requested_offset"] == page["response_start"] == 0
                         and page["reported_total"] == page["returned_row_count"], "single_response_evidence_mismatch")
            _require(page["snapshot_evidence"]["kind"] != "immutable_snapshot", "immutable_snapshot_proof_unbound")
        for location in population["source_locations"]:
            page = pages.get(location["source_ref"])
            _require(page is not None and location["raw_artifact_ref"] == page["binding"]["native_artifact_ref"]
                     and location["document_id"] is None, "population_location_mismatch")
        seen, occurrences = set(), Counter()
        valid_members = set()
        for row in record_set["rows"]:
            source = row["source_ref"]
            _require(row["record_set_id"] == rid and source in pages, "row_source_mismatch")
            native = row["native_row"]
            binding = pages[source]["binding"]
            key = (source, row["page_row_key"])
            _require(key not in seen, "duplicate_row_occurrence")
            seen.add(key)
            occurrences[source] += 1
            _require(row["native_sha256"] == binding["native_sha256"]
                     and row["page_row_key"] == native["row_key"]
                     and native["row_key"] == row["native_sha256"] + "/row/" + str(native["row_index"])
                     and row["native_unique_key"] == (native["native_id"] or None), "row_identity_mismatch")
            _require([cell["field"] for cell in native["cells"]] == request["selected_fields"],
                     "row_selected_fields_mismatch")
            fields = {cell["field"] for cell in native["cells"]}
            _require(len(fields) == len(native["cells"]), "duplicate_native_field")
            for cell in native["cells"]:
                escaped = cell["field"].replace("~", "~0").replace("/", "~1")
                _require(cell["native_path"] == native["native_path"] + "/" + escaped
                         and cell["cell_key"] == native["row_key"] + "/field/" + escaped,
                         "native_cell_reference_mismatch")
            if request["annotation_filter"] == "none":
                _require(row["filter_state"] == "included", "filter_state_mismatch")
            else:
                annotation = _scalar_string(native, "annotation")
                state = ("filter_undetermined" if annotation is None else "included" if annotation == "PATRIC"
                         else "excluded_by_explicit_filter")
                _require(row["filter_state"] == state, "filter_state_mismatch")
            association = row["association"]
            if association is not None:
                _require(association["association_id"] not in association_ids, "duplicate_association_id")
                association_ids.add(association["association_id"])
                _require(association["document_id"] is None and association["record_set_id"] == rid
                         and association["table"] == "data_rows"
                         and association["row_ordinal"] == native["row_index"], "association_owner_mismatch")
                for field, identifier in association["identifiers"].items():
                    expected = row["native_unique_key"] if field == "record_id" else _scalar_identifier(native, field)
                    _require(identifier == expected, "association_identifier_mismatch")
                active = _scalar_identifier(native, "active")
                _require(association["active_category"] == (active if active in ("active", "likely", "inactive") else None),
                         "association_category_mismatch")
                coordinate = ("one_based_inclusive" if collection == "genome_feature"
                              and fields & {"start", "end"} else "not_applicable")
                _require(association["coordinate_convention"] == coordinate, "association_coordinate_mismatch")
                raw_fields = {field["name"]: field for field in association["fields"]}
                _require(len(raw_fields) == len(association["fields"]), "duplicate_association_field")
                for cell in native["cells"]:
                    raw = raw_fields.get(cell["field"])
                    _require((raw is None) == (cell["presence"] in ("absent", "unselected")), "association_field_presence_mismatch")
                    expected = _field_text(cell)
                    if expected is not None:
                        _require(raw is not None and raw["raw_text"] == expected, "association_field_value_mismatch")
                for field in association["fields"]:
                    location = field["location"]
                    escaped = field["name"].replace("~", "~0").replace("/", "~1")
                    _require(location["source_ref"] == source
                             and location["raw_artifact_ref"] == binding["native_artifact_ref"]
                             and location["document_id"] is None and location["table"] == "data_rows"
                             and location["row_ordinal"] == native["row_index"]
                             and location["native_field"] == field["name"]
                             and location["json_pointer"] in ("", native["native_path"] + "/" + escaped),
                             "association_location_mismatch")
                if row["duplicate_state"] == "conflicting_repeat":
                    _require(association["identity_status"] == "conflicting", "conflict_status_mismatch")
            if (row["filter_state"] == "included" and row["native_unique_key"] is not None
                    and native["status"] == "valid" and row["duplicate_state"] != "conflicting_repeat"
                    and association is not None and association["identity_status"] == "valid"):
                valid_members.add(row["native_unique_key"])
        for source, page in pages.items():
            _require(occurrences[source] == page["returned_row_count"], "page_row_count_mismatch")
            indices = [row["native_row"]["row_index"] for row in record_set["rows"] if row["source_ref"] == source]
            _require(indices == list(range(len(indices))), "page_row_order_mismatch")
        _count(population["raw_occurrence_count"], population_id=rid, unit="record", value=len(record_set["rows"]))
        _require(set(population["members"]) == valid_members, "population_members_mismatch")
        _count(record_set["original_query_record_count"], population_id=rid, unit="record")
        _count(record_set["locally_included_record_count"], population_id=rid, unit="record")
        for cell in (population["raw_occurrence_count"], population["distinct_valid_member_count"],
                     record_set["original_query_record_count"], record_set["locally_included_record_count"]):
            _require((cell["origin"] == "unavailable") == (cell["state"] != "available"),
                     "count_origin_mismatch")
            for reference in cell["input_refs"]:
                _saved_reference(record_set, reference)
        if record_set["original_query_record_count"]["state"] == "available":
            totals = {page["reported_total"] for page in pages.values()}
            _require(totals == {record_set["original_query_record_count"]["value"]}, "query_count_mismatch")
            _require(all(page["body_complete"] and page["partial_results"] is not True and page["num_found_exact"] is True
                         and page["requested_offset"] == page["response_start"] for page in pages.values()),
                     "query_count_evidence_missing")
        local = record_set["locally_included_record_count"]
        if local["state"] == "available":
            _require(all(row["filter_state"] != "filter_undetermined" for row in record_set["rows"]),
                     "local_filter_count_undetermined")
            included = [row for row in record_set["rows"] if row["filter_state"] == "included"]
            _require(all(row["native_unique_key"] is not None and row["duplicate_state"] != "conflicting_repeat"
                         for row in included), "local_count_identity_unknown")
            _require(local["value"] == len({row["native_unique_key"] for row in included}), "local_count_mismatch")
        if population["completeness"] == "complete_for_declared_population":
            _require(record_set["page_coverage"] == "complete"
                     and record_set["snapshot_consistency"] == "single_response"
                     and set(pages) == set(request["source_refs"]), "complete_population_evidence_missing")
            _require(all(row["native_row"]["status"] == "valid" and row["filter_state"] != "filter_undetermined"
                         and row["duplicate_state"] != "conflicting_repeat" and row["association"] is not None
                         and row["association"]["identity_status"] == "valid" for row in record_set["rows"]),
                     "complete_population_invalid_rows")
        if record_set["snapshot_consistency"] == "single_response":
            _require(len({(page["binding"]["native_sha256"], page["requested_offset"])
                          for page in pages.values()}) == 1, "single_response_identity_mismatch")
        if record_set["page_coverage"] == "complete":
            _require(bool(pages) and set(pages) == set(request["source_refs"])
                     and record_set["original_query_record_count"]["state"] == "available",
                     "complete_coverage_evidence_missing")
            end = 0
            for page in sorted(pages.values(), key=lambda p: p["response_start"]):
                _require(page["response_start"] <= end, "complete_coverage_gap")
                end = max(end, page["response_start"] + page["returned_row_count"])
            _require(end == record_set["original_query_record_count"]["value"], "complete_coverage_total_mismatch")
        relationship = request["relationship_to_original_task"]
        _require(population["relationship_to_original_task"] ==
                 ("unverified" if relationship == "original_execution_snapshot" else relationship),
                 "saved_population_relationship_mismatch")
        # No immutable-snapshot attestation format is bound in this version.
        _require(record_set["snapshot_consistency"] != "proven_same_snapshot", "immutable_snapshot_proof_unbound")
        _require(population["relationship_to_original_task"] != "original_execution_snapshot",
                 "original_execution_proof_unbound")
    requirements = result["requirements"]
    _require(len({item["requirement_id"] for item in requirements}) == len(requirements), "duplicate_requirement_id")
    sources = {source for item in selection["record_sets"] for source in item["source_refs"]}
    bindings = {page["binding"]["source_ref"]: page["binding"]
                for item in result["record_sets"] for page in item["pages"]}
    for item in requirements + result["diagnostics"]:
        _require(set(item["source_refs"]) <= sources and item["document_id"] is None,
                 "diagnostic_source_mismatch")
        for location in item.get("locations", []):
            binding = bindings.get(location["source_ref"])
            _require(binding is not None and location["source_ref"] in item["source_refs"]
                     and location["raw_artifact_ref"] == binding["native_artifact_ref"]
                     and location["document_id"] is None, "diagnostic_location_mismatch")
    return result
