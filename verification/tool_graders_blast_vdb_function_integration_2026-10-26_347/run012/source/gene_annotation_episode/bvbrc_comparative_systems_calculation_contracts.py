"""Closed parameter and saved-component relationships for ComparativeSystems.

This module validates storage and selectors. It does not parse native output,
extract Data API populations, calculate scientific values, or establish custody.
"""
from __future__ import annotations

from .bvbrc_comparative_systems_handoff_contracts import (
    canonical_sha256, validate_shape,
)

__all__ = ("validate_calculation_parameters", "validate_components")

_PAIR = frozenset(("observed_family_set_intersection_count",
                   "observed_family_set_union_count", "observed_family_set_jaccard"))
_SCALAR = _PAIR - {"observed_family_set_jaccard"} | {
    "subsystem_explicit_category_genome_count", "reported_formula_check"}
_FAMILY_NATIVE = frozenset(("family_returned_genome_occupancy",
                            "family_occurrences_per_positive_genome", "family_length_cv"))
_FORMULA_FIELDS = {
    "pathway_ec_conservation": ("pathway_rows", "reported_ec_conservation_percent", "percent"),
    "pathway_gene_conservation": ("pathway_rows", "reported_gene_conservation", "feature_per_ec_genome"),
    "subsystem_role_conservation": ("subsystem_rows", "reported_role_conservation_percent", "percent"),
    "subsystem_gene_conservation": ("subsystem_rows", "reported_gene_conservation", "feature_per_role_genome"),
    "subsystem_prop_active": ("subsystem_rows", "reported_record_genome_fraction", "fraction"),
}


def _fail(code):
    raise ValueError("comparative_systems_" + code)


def _entity_context(entity):
    """Compare scientific context without erasing each source's literal case."""
    return {key: value for key, value in entity.items() if key != "superclass_native"}


def _same_entity(left, right):
    return _entity_context(left) == _entity_context(right)


def _entity(entity, kind):
    if entity["kind"] != kind:
        _fail("component_entity_kind_invalid")
    required = {"family": {"family_kind", "family_id"}, "pathway": {"pathway_id"},
                "subsystem": {"subsystem_id"}, "pair": {"comparison_id"}}[kind]
    allowed = required | ({"superclass_native", "superclass_aggregation", "class_name",
                           "subclass", "subsystem_name"} if kind == "subsystem" else set())
    if any(not isinstance(entity[key], str) or not entity[key].strip() for key in required):
        _fail("component_entity_identifier_required")
    if any(value is not None for key, value in entity.items() if key not in allowed | {"kind"}):
        _fail("irrelevant_component_entity_field")


def validate_calculation_parameters(value: object) -> dict:
    """Validate finite explicit tolerances and every quantity's selector fields."""
    result = validate_shape("CalculationParametersV1", value)
    seen = set()
    for request in result["requests"]:
        if request["component_id"] in seen:
            _fail("duplicate_component_id")
        seen.add(request["component_id"])
        quantity, selection = request["quantity"], request["view_selection"]
        native = selection["kind"] == "native_view"
        if ((selection["view_id"] is None) == native or
                (selection["record_set_id"] is not None) == native):
            _fail("component_view_selection_invalid")
        family = quantity.startswith("family_") or quantity in _PAIR
        if family:
            _entity(request["entity"], "pair" if quantity in _PAIR else "family")
            if request["family_kind"] is None:
                _fail("component_family_kind_required")
            if quantity not in _PAIR and request["entity"]["family_kind"] != request["family_kind"]:
                _fail("component_family_kind_mismatch")
        else:
            if quantity == "reference_component_representation":
                kind = request["entity"]["kind"]
                if kind not in ("pathway", "subsystem"):
                    _fail("component_reference_entity_invalid")
            elif quantity == "reported_formula_check":
                if request["native_formula"] is None:
                    _fail("component_native_formula_required")
                kind = request["native_formula"].split("_", 1)[0]
            else:
                kind = quantity.split("_", 1)[0]
            _entity(request["entity"], kind)
            if request["family_kind"] is not None:
                _fail("irrelevant_component_family_kind")
        for field, applicable in (
                ("comparison_genome_ids", quantity in _PAIR),
                ("reference_membership_id", quantity == "reference_component_representation"),
                ("category", quantity == "subsystem_explicit_category_genome_count"),
                ("native_formula", quantity == "reported_formula_check")):
            if (request[field] is not None) != applicable:
                _fail("component_selector_field_invalid:" + field)
        if quantity in _FAMILY_NATIVE or "_retained_" in quantity or quantity == "reported_formula_check":
            if not native:
                _fail("native_component_view_required")
        if quantity == "family_record_genome_occupancy" or "_record_" in quantity:
            if native:
                _fail("supplied_component_record_set_required")
    return result


def _units(request):
    """Output unit, numerator unit, denominator unit, scale, output method."""
    quantity = request["quantity"]
    if quantity == "reported_formula_check":
        return (_FORMULA_FIELDS[request["native_formula"]][2], None, None, None,
                "reported_formula_check")
    if quantity == "subsystem_explicit_category_genome_count":
        return "genome", None, None, None, "explicit_category_exact_set"
    if quantity == "observed_family_set_intersection_count":
        return "family", None, None, None, "set_intersection"
    if quantity == "observed_family_set_union_count":
        return "family", None, None, None, "set_union"
    if quantity == "observed_family_set_jaccard":
        return "fraction", "family", "family", 1, "set_jaccard"
    if quantity == "family_length_cv":
        return "dimensionless", "amino_acid", "amino_acid", 1, "coefficient_of_variation"
    if quantity == "family_occurrences_per_positive_genome":
        return "occurrence_per_positive_genome", "occurrence", "genome", 1, "ratio"
    if quantity in ("family_returned_genome_occupancy", "family_record_genome_occupancy"):
        return "fraction", "genome", "genome", 1, "ratio"
    if quantity == "reference_component_representation":
        token = "ec_token" if request["entity"]["kind"] == "pathway" else "role_token"
        return "fraction", token, token, 1, "ratio"
    pathway = quantity.startswith("pathway_")
    denominator = "ec_genome_opportunity" if pathway else "role_genome_opportunity"
    if quantity.endswith("occupancy_percent"):
        return "percent", "genome_ec_pair" if pathway else "genome_role_pair", denominator, 100, "ratio"
    return ("feature_per_ec_genome" if pathway else "feature_per_role_genome",
            "feature", denominator, 1, "ratio")


def _pointer(value, pointer):
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        try:
            if type(value) is list:
                if not token.isdigit() or str(int(token)) != token:
                    _fail("component_reference_invalid")
                value = value[int(token)]
            else:
                value = value[token]
        except (KeyError, IndexError, TypeError):
            _fail("component_reference_unresolved")
    return value


def _unique_index(rows, key):
    indexed = {}
    for row in rows:
        if row[key] in indexed:
            _fail("duplicate_saved_identifier:" + key)
        indexed[row[key]] = row
    return indexed


def validate_components(value: object, *, sheet: dict) -> dict:
    """Validate saved relationships without invoking any scientific calculator.

    Formula arithmetic is calculated once by C. Host content bindings protect
    the resulting bytes; this function is not a second scientific grader.
    """
    saved = validate_shape("ComparativeSystemsSheetV1", sheet)
    result = validate_shape("ComparativeSystemsComponentsV1", value)
    parameters = validate_calculation_parameters(result["parameters"])
    if result["analysis_id"] != saved["analysis_id"] or result["sheet_sha256"] != canonical_sha256(saved):
        _fail("component_sheet_identity_mismatch")
    requests = _unique_index(parameters["requests"], "component_id")
    components = _unique_index(result["components"], "component_id")
    if list(requests) != list(components):
        _fail("component_request_identity_mismatch")
    populations = _unique_index(saved["populations"], "population_id")
    memberships = _unique_index(saved["reference_memberships"], "membership_id")
    documents = {row["document"]["document_id"]: row for row in saved["native_documents"]}
    if len(documents) != len(saved["native_documents"]):
        _fail("duplicate_saved_identifier:document_id")
    views = _unique_index(saved["document_selection"]["authoritative_views"], "view_id")
    supplied = saved["supplied_record_sets"]
    record_sets = _unique_index(supplied["record_sets"], "record_set_id") if supplied else {}

    def reference(ref):
        kind, owner = ref["kind"], ref["owner_id"]
        if kind == "sheet":
            if owner != saved["analysis_id"]:
                _fail("component_reference_owner_mismatch")
            return _pointer(saved, ref["pointer"])
        if kind == "native" and owner in documents:
            return _pointer(documents[owner], ref["pointer"])
        if kind == "supplied" and owner in record_sets:
            return _pointer(record_sets[owner], ref["pointer"])
        if kind == "component" and owner in components:
            return _pointer(components[owner], ref["pointer"])
        _fail("component_reference_owner_unresolved")

    for component_id, component in components.items():
        request = requests[component_id]
        if (component["quantity"] != request["quantity"] or component["entity"] != request["entity"] or
                component["reference_membership_id"] != request["reference_membership_id"]):
            _fail("component_request_identity_mismatch")
        unit, numerator_unit, denominator_unit, scale, method = _units(request)
        cell, ratio = component["value"], component["ratio"]
        if cell["unit"] != unit or cell["method_id"] != method:
            _fail("component_unit_or_method_mismatch")
        if cell["population_id"] != request["population_id"]:
            _fail("component_population_mismatch")
        available = cell["state"] == "available"
        if available and cell["origin"] != "derived_calculation":
            _fail("component_origin_mismatch")
        for population_id in component["population_ids"]:
            if population_id not in populations and population_id not in memberships:
                _fail("component_population_unresolved")
        if request["population_id"] in populations and request["population_id"] not in component["population_ids"]:
            _fail("component_population_missing")
        if available and request["population_id"] not in populations:
            _fail("available_component_population_unresolved")
        selection = request["view_selection"]
        view = views.get(selection["view_id"]) if selection["kind"] == "native_view" else None
        record_set = record_sets.get(selection["record_set_id"]) if selection["kind"] == "supplied_record_set" else None
        if available and view is None and record_set is None:
            _fail("available_component_view_unresolved")
        if available and request["reference_membership_id"] is not None:
            membership = memberships.get(request["reference_membership_id"])
            if membership is None or not _same_entity(membership["entity"], request["entity"]):
                _fail("component_reference_membership_mismatch")
        cells = [cell]
        if request["quantity"] in _SCALAR:
            if ratio is not None:
                _fail("scalar_component_ratio_invalid")
        else:
            if ratio is None or ratio["output"] != cell or ratio["scale"] != scale:
                _fail("component_ratio_identity_mismatch")
            if ratio["numerator"]["unit"] != numerator_unit or ratio["denominator"]["unit"] != denominator_unit:
                _fail("component_operand_unit_mismatch")
            if ratio["genome_population_id"] != request["population_id"]:
                _fail("component_ratio_population_mismatch")
            component_population = ratio["component_population_id"]
            if component_population is not None and component_population not in populations and component_population not in memberships:
                _fail("component_population_unresolved")
            if request["quantity"] == "reference_component_representation":
                if available and component_population != request["reference_membership_id"]:
                    _fail("component_reference_membership_mismatch")
            cells.extend((ratio["numerator"], ratio["denominator"]))
        if cell["qualification_codes"] != component["qualification_codes"]:
            _fail("component_qualification_mismatch")
        for ref in component["input_refs"]:
            reference(ref)
            if not available or ref["kind"] != "sheet":
                continue
            tokens = ref["pointer"].split("/")[1:]
            if not tokens:
                continue
            # Validate the selected identities, not the numerical calculation.
            # Whole-collection references are allowed by the review examples;
            # an exact row reference cannot silently point into another view.
            if tokens[0] in {"family_rows", "pathway_rows", "subsystem_rows", "association_rows"} and len(tokens) >= 2:
                row = _pointer(saved, "/" + "/".join(tokens[:2]))
                if view is None or row["document_id"] != view["document_id"]:
                    _fail("component_dependency_view_mismatch")
                if tokens[0] == "association_rows":
                    expected_table = "genes" if request["native_formula"] == "subsystem_role_conservation" else view["table"]
                    if row["table"] != expected_table:
                        _fail("component_dependency_table_mismatch")
                    identity_field = "pathway_id" if request["entity"]["kind"] == "pathway" else "subsystem_id"
                    if (request["entity"]["kind"] in {"pathway", "subsystem"} and
                            row["identifiers"][identity_field] != request["entity"][identity_field]):
                        _fail("component_dependency_entity_mismatch")
                elif request["quantity"] in _PAIR:
                    if row["entity"]["family_kind"] != request["family_kind"]:
                        _fail("component_dependency_entity_mismatch")
                elif not _same_entity(row["entity"], request["entity"]):
                    _fail("component_dependency_entity_mismatch")
            elif tokens[0] == "populations" and len(tokens) >= 2:
                population = _pointer(saved, "/" + "/".join(tokens[:2]))
                if population["population_id"] not in component["population_ids"]:
                    _fail("component_dependency_population_mismatch")
            elif tokens[0] == "reference_memberships" and len(tokens) >= 2:
                membership = _pointer(saved, "/" + "/".join(tokens[:2]))
                if membership["membership_id"] != request["reference_membership_id"]:
                    _fail("component_dependency_membership_mismatch")
            elif tokens[:2] == ["supplied_record_sets", "record_sets"] and len(tokens) >= 3:
                dependency = _pointer(saved, "/" + "/".join(tokens[:3]))
                if record_set is None or dependency["record_set_id"] != record_set["record_set_id"]:
                    _fail("component_dependency_record_set_mismatch")
            elif tokens[:2] == ["document_selection", "authoritative_views"] and len(tokens) >= 3:
                dependency = _pointer(saved, "/" + "/".join(tokens[:3]))
                if view is None or dependency["view_id"] != view["view_id"]:
                    _fail("component_dependency_view_mismatch")
        for item in cells:
            for ref in item["input_refs"]:
                reference(ref)
                if ref not in component["input_refs"]:
                    _fail("component_dependency_missing")
            if item["state"] == "available" and item["population_id"] is not None:
                if item["population_id"] not in populations and item["population_id"] not in memberships:
                    _fail("component_operand_population_unresolved")
                if item["population_id"] not in component["population_ids"]:
                    _fail("component_operand_population_missing")
            if item["state"] == "available" and item["value"] < 0:
                _fail("component_negative_quantity")
            if (item["state"] == "available" and item["unit"] in {
                    "genome", "feature", "family", "ec_token", "role_token", "occurrence",
                    "genome_ec_pair", "genome_role_pair", "ec_genome_opportunity", "role_genome_opportunity"}
                    and type(item["value"]) is not int):
                _fail("component_exact_count_required")
        expected_fields = {
            "family_length_cv": ("reported_length_population_sd", "reported_length_mean"),
            "family_occurrences_per_positive_genome": ("reported_feature_occurrences", "reported_genome_count"),
            "family_returned_genome_occupancy": ("positive_genome_count_from_list", None),
        }.get(request["quantity"])
        if available and expected_fields:
            for operand, expected_field in zip((ratio["numerator"], ratio["denominator"]), expected_fields):
                exact_fields = [ref["pointer"].split("/")[3:] for ref in operand["input_refs"]
                                if ref["kind"] == "sheet" and ref["pointer"].startswith("/family_rows/")]
                if expected_field is not None and any(fields and fields != [expected_field] for fields in exact_fields):
                    _fail("component_dependency_native_field_mismatch")
    for row in result["requirements"] + result["diagnostics"]:
        if not set(row["affected_field_ids"]) <= set(components):
            _fail("component_diagnostic_field_unresolved")
    return result
