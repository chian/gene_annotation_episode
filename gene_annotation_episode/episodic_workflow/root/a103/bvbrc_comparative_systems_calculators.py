"""Deterministic ComparativeSystems quantities from a saved numerical sheet.

The native reports and supplied snapshots stay separate. Ratios retain their
operands and named populations. Counts describe stored assignment records,
never physical absence, biochemical completion, or annotation probability.
Nothing here parses bytes, acquires data, executes a process, or chooses work.
"""
from __future__ import annotations

from copy import deepcopy
import math

from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, validate_shape
from .bvbrc_comparative_systems_calculation_contracts import (
    _FAMILY_NATIVE, _FORMULA_FIELDS, _PAIR, _SCALAR, _same_entity, _unique_index,
    _units, validate_calculation_parameters, validate_components,
)

__all__ = ("calculate_comparative_systems_components",)


def _distinct(values):
    return list(dict.fromkeys(values))


def _refs(*groups):
    result, seen = [], set()
    for group in groups:
        for ref in group:
            key = (ref["kind"], ref["owner_id"], ref["pointer"])
            if key not in seen:
                seen.add(key)
                result.append(ref)
    return result


def _cell(value, unit, population, method, refs, *, state="available",
          origin="derived_calculation", codes=()):
    return {"state": state, "value": value if state == "available" else None,
            "unit": unit, "origin": origin if state == "available" else "unavailable",
            "population_id": population, "method_id": method, "input_refs": deepcopy(refs),
            "uncertainty": None, "qualification_codes": _distinct(codes)}


class _Unavailable(Exception):
    def __init__(self, code, role, *, state="missing", refs=()):
        self.code, self.role, self.state, self.refs = code, role, state, list(refs)


def _unavailable(code, role, *, state="missing", refs=()):
    raise _Unavailable(code, role, state=state, refs=refs)


def _view_family(table, profile):
    if table in ("plfam", "pgfam"):
        return "family"
    if "pathways" in profile:
        return "pathway"
    if "subsystems" in profile or "variant_matrix" in profile:
        return "subsystem"
    return None


class _Context:
    def __init__(self, sheet):
        self.sheet = sheet
        self.populations = _unique_index(sheet["populations"], "population_id")
        self.views = _unique_index(sheet["document_selection"]["authoritative_views"], "view_id")
        self.assignments = _unique_index(sheet["population_assignments"]["assignments"], "population_id")
        self.documents = _unique_index(sheet["source_documents"], "document_id")
        self.native = {}
        for document in sheet["native_documents"]:
            key = document["document"]["document_id"]
            if key in self.native:
                raise ValueError("comparative_systems_duplicate_saved_identifier:document_id")
            self.native[key] = document
        self.memberships = _unique_index(sheet["reference_memberships"], "membership_id")
        supplied = sheet["supplied_record_sets"]
        self.record_sets = _unique_index(supplied["record_sets"], "record_set_id") if supplied else {}
        self.data_selections = _unique_index(supplied["selection"]["record_sets"], "record_set_id") if supplied else {}

    def ref(self, pointer):
        return {"kind": "sheet", "owner_id": self.sheet["analysis_id"], "pointer": pointer}

    def row_ref(self, key, row):
        return self.ref("/" + key + "/" + str(next(
            index for index, value in enumerate(self.sheet[key]) if value is row)))

    def population(self, request):
        population = self.populations.get(request["population_id"])
        if population is None:
            _unavailable("missing_required_field", "original_genome_population")
        ref = self.row_ref("populations", population)
        if population["member_kind"] != "genome_id":
            _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=[ref])
        count = population["distinct_valid_member_count"]
        if count["state"] == "available" and (
                type(count["value"]) is not int or count["value"] != len(set(population["members"]))):
            _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=[ref])
        return population, ref

    def source(self, request):
        selection = request["view_selection"]
        population, population_ref = self.population(request)
        family = request["entity"]["kind"]
        if family == "pair":
            family = "family"
        result = {"population": population, "refs": [population_ref], "codes": list(population["qualification_codes"]),
                  "state": "available", "role": family + "_records", "view": None, "record_set": None}
        if family == "family":
            result["role"] = "family_feature_records"
        count = population["distinct_valid_member_count"]
        if count["state"] != "available":
            result["state"] = count["state"]
            result["codes"].append("population_incomplete")
        elif (population["completeness"] != "complete_for_declared_population" or
              population["missing_members"] or population["unresolved_members"]):
            result["state"] = "incompatible" if population["completeness"] == "incompatible" else "missing"
            result["codes"].append("population_incomplete")
        if selection["kind"] == "native_view":
            view = self.views.get(selection["view_id"])
            if view is None:
                _unavailable("missing_document_selection", "native_document", refs=result["refs"])
            result["view"] = view
            result["refs"].append(self.ref("/document_selection/authoritative_views/" + str(
                self.sheet["document_selection"]["authoritative_views"].index(view))))
            document = self.documents.get(view["document_id"])
            native = self.native.get(view["document_id"])
            if document is None or native is None:
                _unavailable("missing_required_field", "native_document", refs=result["refs"])
            result.update(document=document, native=native)
            if native["status"] in ("invalid", "failed"):
                _unavailable("format_incompatible", document["role"], state=native["status"], refs=result["refs"])
            if _view_family(view["table"], document["format_profile"]) != family:
                _unavailable("population_incompatible", document["role"], state="incompatible", refs=result["refs"])
            if family == "family" and view["table"] != request["family_kind"]:
                _unavailable("population_incompatible", "family_summary", state="incompatible", refs=result["refs"])
            tables = [table for table in native["tables"] if table["table"] == view["table"]]
            if len(tables) != 1:
                _unavailable("missing_required_field" if not tables else "ambiguous_document_selection",
                             document["role"], refs=result["refs"])
            result["table"] = tables[0]
            assignment = self.assignments.get(population["population_id"])
            if population["kind"] != "native_view_represented_genomes" or assignment is None:
                _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=result["refs"])
            population_view = self.views.get(assignment["view_id"])
            population_doc = self.documents.get(population_view["document_id"]) if population_view else None
            if (population_view is None or population_doc is None or
                    _view_family(population_view["table"], population_doc["format_profile"]) != family):
                _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=result["refs"])
            # The same native run can have raw and joined tables in different
            # selected artifacts. A later Data population cannot stand in for it.
            if document["original_task_ref"] != population_doc["original_task_ref"]:
                _unavailable("original_task_mismatch", "native_document", state="incompatible", refs=result["refs"])
            result["population_view"] = population_view
            result["role"] = document["role"]
            # A formula check selects one summary row's native operands. Its
            # row/field and original-population checks happen below; unrelated
            # damaged summaries do not make those saved operands unavailable.
            # Set/population quantities still need the entire selected table.
            if (request["quantity"] not in _FAMILY_NATIVE | {"reported_formula_check"} and
                    any(row["status"] != "ok" for row in tables[0]["rows"])):
                result["state"] = "missing"
                result["codes"].append("population_incomplete")
            for diagnostic in native["diagnostics"]:
                if diagnostic["code"] in {"producer_version_unverified", "native_first_object_discard",
                                           "native_query_completeness_unknown", "reference_release_unknown"}:
                    result["codes"].append(diagnostic["code"])
        else:
            record_set = self.record_sets.get(selection["record_set_id"])
            data_selection = self.data_selections.get(selection["record_set_id"])
            if record_set is None or data_selection is None:
                _unavailable("data_input_unavailable", result["role"], refs=result["refs"])
            result["record_set"] = record_set
            index = self.sheet["supplied_record_sets"]["record_sets"].index(record_set)
            result["record_pointer"] = "/supplied_record_sets/record_sets/" + str(index)
            result["refs"].append(self.ref(result["record_pointer"] + "/population"))
            expected = "genome_feature" if family == "family" else family
            if (record_set["collection"] != expected or population["population_id"] !=
                    data_selection["declared_genome_population"]["population_id"] or
                    population != data_selection["declared_genome_population"]):
                _unavailable("population_incompatible", result["role"], state="incompatible", refs=result["refs"])
            rp = record_set["population"]
            result["codes"].extend(rp["qualification_codes"])
            if (rp["completeness"] != "complete_for_declared_population" or
                    record_set["page_coverage"] != "complete" or
                    record_set["snapshot_consistency"] not in ("single_response", "proven_same_snapshot")):
                result["state"] = "incompatible" if rp["completeness"] == "incompatible" else "missing"
                result["codes"].append("population_incomplete")
        result["codes"] = _distinct(result["codes"])
        return result

    def associations(self, request, source, *, joined=False):
        """Select already normalized rows; this performs no source decoding."""
        rows, codes, refs = [], [], []
        state = source["state"]
        if source["view"] is not None:
            view = source["view"]
            table = "genes" if joined else view["table"]
            if table not in ("genes", "pathways_tsv", "subsystems_tsv"):
                _unavailable("format_incompatible", source["role"], state="incompatible", refs=source["refs"])
            if joined:
                tables = [t for t in source["native"]["tables"] if t["table"] == "genes"]
                if len(tables) != 1:
                    _unavailable("missing_required_field", "subsystem_associations", refs=source["refs"])
                if any(r["status"] != "ok" for r in tables[0]["rows"]):
                    state = "missing"
                    codes.append("population_incomplete")
            for index, row in enumerate(self.sheet["association_rows"]):
                if row["document_id"] == view["document_id"] and row["table"] == table:
                    rows.append((row, self.ref("/association_rows/" + str(index))))
            # An intact table with rows but no normalized associations is not a
            # measured empty set. Do not reparse its text here.
            selected_table = next((t for t in source["native"]["tables"] if t["table"] == table), None)
            if selected_table and selected_table["rows"] and not rows:
                _unavailable("missing_required_field", source["role"], refs=source["refs"])
        else:
            for index, supplied in enumerate(source["record_set"]["rows"]):
                if supplied["filter_state"] == "excluded_by_explicit_filter":
                    continue
                ref = self.ref(source["record_pointer"] + "/rows/" + str(index))
                if supplied["filter_state"] == "filter_undetermined" or supplied["association"] is None:
                    state = "missing"
                    codes.append("missing_required_field")
                    refs.append(ref)
                    continue
                row = supplied["association"]
                if supplied["duplicate_state"] == "conflicting_repeat":
                    row = {**row, "identity_status": "conflicting", "qualification_codes":
                           _distinct(row["qualification_codes"] + ["duplicate_record_conflict"])}
                rows.append((row, ref))
        return rows, state, _distinct(codes), refs


def _entity_rows(request, source, rows, *, keys):
    """Check only identities used by this quantity, retaining all occurrences."""
    kind = request["entity"]["kind"]
    identity_key = {"pathway": "pathway_id", "subsystem": "subsystem_id", "family": request["family_kind"] + "_id" if request["family_kind"] else None}.get(kind)
    target = request["entity"].get(identity_key) if identity_key else None
    if kind == "family":
        target = request["entity"]["family_id"]
    genomes = set(source["population"]["members"])
    result, refs, codes, state = [], [], [], "available"
    grouped = {}
    joined_role = (source["view"] is not None and
                   request["native_formula"] == "subsystem_role_conservation")
    joined_identities = {}
    if joined_role:
        # The native inner join repeats a subsystem association for matching
        # feature-side rows. Compare its join identity, role operands and
        # subsystem context, not feature-side product/accession metadata. Check
        # all repeats before entity filtering so a reused ID cannot silently
        # change subsystem. Unknown required operands remain missing below.
        for row, _ in rows:
            ids = row["identifiers"]
            if ids["record_id"] is None or any(ids[key] is None for key in (*keys, identity_key)):
                continue
            fields = {f["name"]: f["raw_text"] for f in row["fields"]}
            context = tuple(fields.get(field) for field in ("class", "subclass", "subsystem_name"))
            superclass = fields.get("superclass")
            signature = (ids["genome_id"], ids["feature_id"], ids["subsystem_id"], ids["role_id"],
                         superclass.upper() if superclass is not None else None, context)
            joined_identities.setdefault(ids["record_id"], set()).add(signature)
    for row, ref in rows:
        identifiers = row["identifiers"]
        if identity_key and identifiers[identity_key] is not None and identifiers[identity_key] != target:
            continue
        if identity_key and identifiers[identity_key] is None:
            # A missing family assignment is a valid no-assignment record; an
            # unidentified pathway/subsystem row cannot be assigned to another.
            if kind == "family":
                continue
            state = "missing" if state != "incompatible" else state
            codes.append("native_identifier_placeholder")
            refs.append(ref)
            continue
        refs.append(ref)
        codes.extend(row["qualification_codes"])
        if (row["identity_status"] == "conflicting" or
                joined_role and "duplicate_record_conflict" in row["qualification_codes"]):
            state = "incompatible"
            codes.append("identity_conflict")
            continue
        if any(identifiers[key] is None for key in keys):
            if state != "incompatible":
                state = "missing"
            codes.append("native_identifier_placeholder")
            continue
        if identifiers["genome_id"] not in genomes:
            state = "incompatible"
            codes.append("population_incompatible")
            continue
        if kind == "subsystem":
            fields = {f["name"]: f["raw_text"] for f in row["fields"]}
            for native_key, entity_key in (("superclass", "superclass_aggregation"), ("class", "class_name"),
                                           ("subclass", "subclass"), ("subsystem_name", "subsystem_name")):
                observed, requested = fields.get(native_key), request["entity"][entity_key]
                if observed is not None and native_key == "superclass":
                    observed = observed.upper()
                if observed is not None and requested is not None and observed != requested:
                    state = "incompatible"
                    codes.append("identity_conflict")
        record_id = identifiers["record_id"]
        if record_id is not None:
            # Original source conflicts remain incompatible. Only the native
            # role formula has a feature-join dependency projection above.
            signature = (tuple(sorted(identifiers.items())), row["active_category"],
                         tuple(sorted((f["name"], f["raw_text"]) for f in row["fields"])))
            if joined_role and len(joined_identities.get(record_id, ())) > 1:
                state = "incompatible"
                codes.append("duplicate_record_conflict")
            elif record_id in grouped and grouped[record_id] != signature:
                if joined_role:
                    codes.append("inner_join_many_to_many")
                else:
                    state = "incompatible"
                    codes.append("duplicate_record_conflict")
            elif record_id in grouped:
                codes.append("duplicate_identical_representation")
            grouped[record_id] = signature
        result.append(row)
    return result, state, _distinct(codes), refs


def _worst(*states):
    order = ("available", "not_measured", "missing", "truncated", "failed", "invalid", "incompatible")
    return max(states, key=order.index)


def _input_cell(context, source, row_key, row, field, *, unit, integer=False):
    native = row[field]
    pointer = context.row_ref(row_key, row)["pointer"] + "/" + field
    refs = [context.ref(pointer)]
    result = deepcopy(native)
    result["input_refs"] = refs
    if result["unit"] != unit or (result["state"] == "available" and (
            result["value"] < 0 or integer and type(result["value"]) is not int)):
        return _cell(None, unit, source["population"]["population_id"], "native_field", refs,
                     state="invalid", codes=["numeric_token_invalid"])
    return result


def _ratio(request, source, numerator, denominator, *, component_population=None, codes=(), state="available"):
    unit, _, _, scale, method = _units(request)
    refs = _refs(source["refs"], numerator["input_refs"], denominator["input_refs"])
    codes = _distinct(source["codes"] + list(codes) + numerator["qualification_codes"] + denominator["qualification_codes"])
    result_state = _worst(state, source["state"], numerator["state"], denominator["state"])
    if denominator["state"] == "available" and denominator["value"] == 0:
        codes.append("empty_denominator")
        result_state = _worst(result_state, "missing")
    value = None
    if result_state == "available":
        try:
            value = scale * numerator["value"] / denominator["value"]
        except OverflowError:
            value = None
        if value is None or not math.isfinite(value):
            value, result_state = None, "invalid"
            codes.append("nonfinite_number")
    output = _cell(value, unit, request["population_id"], method, refs, state=result_state, codes=codes)
    return output, {"numerator": numerator, "denominator": denominator, "scale": scale,
                    "output": deepcopy(output), "genome_population_id": request["population_id"],
                    "component_population_id": component_population}, refs


def _genome_denominator(context, request, source):
    population = source["population"]
    cell = deepcopy(population["distinct_valid_member_count"])
    cell["input_refs"] = [context.row_ref("populations", population)]
    return cell


def _family_row(context, request, source):
    candidates = [row for row in context.sheet["family_rows"]
                  if row["document_id"] == source["view"]["document_id"] and _same_entity(row["entity"], request["entity"])]
    if len(candidates) != 1:
        _unavailable("missing_required_field" if not candidates else "ambiguous_document_selection",
                     "family_summary", state="missing" if not candidates else "incompatible", refs=source["refs"])
    return candidates[0]


def _family(context, request, source):
    row = _family_row(context, request, source)
    quantity = request["quantity"]
    if quantity == "family_returned_genome_occupancy":
        numerator = _input_cell(context, source, "family_rows", row, "positive_genome_count_from_list", unit="genome", integer=True)
        if numerator["state"] == "available" and (
                numerator["value"] != len(set(row["positive_genome_ids"])) or
                not set(row["positive_genome_ids"]) <= set(source["population"]["members"])):
            numerator = _cell(None, "genome", request["population_id"], "distinct_valid_members", numerator["input_refs"],
                              state="incompatible", codes=["population_incompatible"])
        denominator = _genome_denominator(context, request, source)
    elif quantity == "family_occurrences_per_positive_genome":
        numerator = _input_cell(context, source, "family_rows", row, "reported_feature_occurrences", unit="occurrence", integer=True)
        denominator = _input_cell(context, source, "family_rows", row, "reported_genome_count", unit="genome", integer=True)
    else:
        numerator = _input_cell(context, source, "family_rows", row, "reported_length_population_sd", unit="amino_acid")
        denominator = _input_cell(context, source, "family_rows", row, "reported_length_mean", unit="amino_acid")
    if quantity != "family_returned_genome_occupancy":
        # The reported mean/SD and occurrence/positive-genome quantities do not
        # need the overall represented-genome count to be available.
        source = {**source, "state": "available"}
    # Ambiguous per-genome hex encoding does not invalidate aggregate lengths,
    # occurrence counts or independently retained positive membership.
    relevant_codes = [c for c in row["qualification_codes"] if c not in {"hex_count_width_ambiguous"}]
    return _ratio(request, source, numerator, denominator, codes=relevant_codes)


def _record_quantities(context, request, source):
    quantity = request["quantity"]
    family = quantity == "family_record_genome_occupancy"
    component_key = "ec_number" if request["entity"]["kind"] == "pathway" else "role_id"
    density = quantity.endswith("feature_density")
    keys = ["genome_id"] if family else ["genome_id", component_key]
    raw, source_state, source_codes, extra_refs = context.associations(request, source)
    rows, row_state, codes, refs = _entity_rows(request, source, raw, keys=keys)
    refs = _refs(refs, extra_refs)
    codes = _distinct(source_codes + codes)
    origin = "derived_retained_records" if source["view"] else "derived_supplied_records"
    pop = request["population_id"]
    component_population = None
    if family:
        if _worst(source_state, row_state) != "available":
            codes.append("population_incomplete")
        numerator = _cell(len({r["identifiers"]["genome_id"] for r in rows}), "genome", pop,
                          "distinct_valid_members", refs, origin=origin, codes=codes)
        return _ratio(request, source, numerator, _genome_denominator(context, request, source),
                      codes=codes, state=_worst(source_state, row_state))
    components = {r["identifiers"][component_key] for r in rows}
    # Retained component sets have caller-assigned IDs. Supplied records do not
    # need an invented population ID for each newly selected component set.
    if source["view"]:
        matches = [a for a in context.assignments.values() if a["kind"] == "selected_component_membership"
                   and a["view_id"] == source["view"]["view_id"] and a["component_kind"] == component_key
                   and a["entity"] is not None and _same_entity(a["entity"], request["entity"])]
        if len(matches) == 1:
            selected = context.populations.get(matches[0]["population_id"])
            if selected is not None:
                component_population = selected["population_id"]
                refs = _refs(refs, [context.row_ref("populations", selected)])
                if selected["completeness"] == "complete_for_declared_population" and set(selected["members"]) != components:
                    row_state = "incompatible"
                    codes.append("population_incompatible")
        elif len(matches) > 1:
            row_state = "incompatible"
            codes.append("population_incompatible")
    genome_count = _genome_denominator(context, request, source)
    if _worst(source_state, row_state) != "available":
        codes.append("population_incomplete")
    denominator_state = genome_count["state"]
    denominator = _cell(len(components) * len(set(source["population"]["members"])),
                        "ec_genome_opportunity" if component_key == "ec_number" else "role_genome_opportunity",
                        pop, "opportunity_product", _refs(refs, genome_count["input_refs"]),
                        state=denominator_state, origin=origin, codes=codes)
    if density:
        feature_rows, feature_state, feature_codes, feature_refs = _entity_rows(request, source, raw, keys=["genome_id", "feature_id"])
        feature_ids = {(r["identifiers"]["genome_id"], r["identifiers"]["feature_id"]) for r in feature_rows}
        numerator = _cell(len(feature_ids), "feature", pop, "distinct_valid_feature_pairs",
                          _refs(feature_refs, extra_refs), origin=origin,
                          codes=source_codes + feature_codes)
        row_state = _worst(row_state, feature_state)
    else:
        pairs = {(r["identifiers"]["genome_id"], r["identifiers"][component_key]) for r in rows}
        numerator = _cell(len(pairs), "genome_ec_pair" if component_key == "ec_number" else "genome_role_pair", pop,
                          "distinct_valid_genome_ec_pairs" if component_key == "ec_number" else "distinct_valid_genome_role_pairs",
                          refs, origin=origin, codes=codes)
    return _ratio(request, source, numerator, denominator, component_population=component_population,
                  state=_worst(source_state, row_state), codes=codes)


def _categories(context, request, source):
    raw, source_state, source_codes, extra_refs = context.associations(request, source)
    rows, state, codes, refs = _entity_rows(request, source, raw, keys=["genome_id"])
    categories = {}
    for row in rows:
        genome = row["identifiers"]["genome_id"]
        categories.setdefault(genome, set()).add(row["active_category"])
    if any(None in values for values in categories.values()):
        state = _worst(state, "missing")
        codes.append("missing_required_field")
    if any(len(values - {None}) > 1 for values in categories.values()):
        codes.append("conflicting_native_categories")
    if set(source["population"]["members"]) - categories.keys():
        codes.append("absent_record_not_measured")
    value = sum(values == {request["category"]} for values in categories.values())
    refs = _refs(source["refs"], refs, extra_refs)
    cell = _cell(value, "genome", request["population_id"], "explicit_category_exact_set", refs,
                 state=_worst(source_state, state), codes=source["codes"] + source_codes + codes)
    return cell, None, refs


def _family_sets(context, request, source):
    pair = request["comparison_genome_ids"]
    if not set(pair) <= set(source["population"]["members"]):
        _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=source["refs"])
    sets = {genome: set() for genome in pair}
    refs, codes, state = list(source["refs"]), list(source["codes"]), source["state"]
    if source["view"]:
        seen = set()
        for row in context.sheet["family_rows"]:
            if row["document_id"] != source["view"]["document_id"] or row["entity"]["family_kind"] != request["family_kind"]:
                continue
            ref = context.row_ref("family_rows", row)
            refs.append(ref)
            family = row["entity"]["family_id"]
            if family in seen:
                codes.append("ambiguous_document_selection")
                state = "incompatible"
            seen.add(family)
            count = row["positive_genome_count_from_list"]
            if (count["state"] != "available" or count["value"] != len(set(row["positive_genome_ids"])) or
                    not set(row["positive_genome_ids"]) <= set(source["population"]["members"])):
                state = _worst(state, count["state"] if count["state"] != "available" else "incompatible")
                codes.append("population_incompatible")
            codes.extend(count["qualification_codes"])
            for genome in pair:
                if genome in row["positive_genome_ids"]:
                    sets[genome].add(family)
        if source["table"]["rows"] and not seen:
            state = "missing"
            codes.append("missing_required_field")
    else:
        raw, row_state, row_codes, extra_refs = context.associations(request, source)
        rows, identity_state, identity_codes, row_refs = _entity_rows(request, source, raw, keys=["genome_id"])
        state = _worst(state, row_state, identity_state)
        codes.extend(row_codes + identity_codes)
        refs = _refs(refs, row_refs, extra_refs)
        for row in rows:
            family = row["identifiers"][request["family_kind"] + "_id"]
            genome = row["identifiers"]["genome_id"]
            if genome in sets and family is not None:
                sets[genome].add(family)
    intersection = len(sets[pair[0]] & sets[pair[1]])
    union = len(sets[pair[0]] | sets[pair[1]])
    numerator = _cell(intersection, "family", request["population_id"], "set_intersection", refs, state=state, codes=codes)
    denominator = _cell(union, "family", request["population_id"], "set_union", refs, state=state, codes=codes)
    if request["quantity"] == "observed_family_set_jaccard":
        return _ratio(request, source, numerator, denominator, state=state, codes=codes)
    return (numerator if request["quantity"].endswith("intersection_count") else denominator), None, refs


def _reference(context, request, source):
    membership = context.memberships.get(request["reference_membership_id"])
    unit = "ec_token" if request["entity"]["kind"] == "pathway" else "role_token"
    key = "ec_number" if unit == "ec_token" else "role_id"
    raw, source_state, source_codes, extra_refs = context.associations(request, source)
    rows, row_state, codes, refs = _entity_rows(request, source, raw, keys=["genome_id", key])
    refs = _refs(refs, extra_refs)
    if membership is None:
        numerator = _cell(None, unit, request["population_id"], "set_intersection", refs,
                          state="missing", codes=["reference_membership_missing"])
        denominator = _cell(None, unit, request["population_id"], "distinct_valid_members", [],
                            state="missing", codes=["reference_membership_missing"])
        return _ratio(request, source, numerator, denominator)
    membership_ref = context.row_ref("reference_memberships", membership)
    refs.append(membership_ref)
    if not _same_entity(membership["entity"], request["entity"]) or membership["component_kind"] != key:
        _unavailable("population_incompatible", "reference_membership", state="incompatible", refs=refs)
    members = set(membership["members"])
    membership_state = "available"
    codes.extend(membership["qualification_codes"])
    if membership["release"] is None:
        codes.append("reference_release_unknown")
    if membership["completeness"] != "complete_for_declared_population":
        membership_state = "incompatible" if membership["completeness"] == "incompatible" else "missing"
        codes.append("incomplete_reference_membership")
    observed = {r["identifiers"][key] for r in rows}
    if _worst(source_state, row_state) != "available":
        codes.append("population_incomplete")
    numerator = _cell(len(observed & members), unit, request["population_id"], "set_intersection", refs,
                      codes=source_codes + codes)
    denominator = _cell(len(members), unit, membership["membership_id"], "distinct_valid_members", [membership_ref],
                        codes=codes)
    return _ratio(request, source, numerator, denominator, component_population=membership["membership_id"],
                  state=_worst(source_state, row_state, membership_state))


def _reported_formula(context, request, source, parameters):
    formula = request["native_formula"]
    row_key, field, unit = _FORMULA_FIELDS[formula]
    expected_table = "pathway" if row_key == "pathway_rows" else "subsystems"
    if source["view"]["table"] != expected_table:
        _unavailable("format_incompatible", source["role"], state="incompatible", refs=source["refs"])
    candidates = [row for row in context.sheet[row_key]
                  if row["document_id"] == source["view"]["document_id"] and _same_entity(row["entity"], request["entity"])]
    if len(candidates) != 1:
        _unavailable("missing_required_field" if not candidates else "identity_conflict", source["role"],
                     state="missing" if not candidates else "incompatible", refs=source["refs"])
    row = candidates[0]
    if row_key == "subsystem_rows" and any(
            other["document_id"] == source["view"]["document_id"] and
            other["entity"]["subsystem_id"] == request["entity"]["subsystem_id"] and
            not _same_entity(other["entity"], row["entity"]) for other in context.sheet[row_key]):
        _unavailable("identity_conflict", "subsystem_summary", state="incompatible", refs=source["refs"])
    # Native source formulas use their original represented-genome set. Even
    # an otherwise compatible explicit subset must not change that denominator.
    if source["population_view"]["document_id"] != source["view"]["document_id"]:
        _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=source["refs"])
    original_lists = [item["value"] for item in source["native"]["metadata"]
                      if item["location"]["json_pointer"] == "/genome_ids"]
    if (len(original_lists) != 1 or type(original_lists[0]) is not list or
            any(type(value) is not str for value in original_lists[0]) or
            set(original_lists[0]) != set(source["population"]["members"])):
        _unavailable("population_incompatible", "original_genome_population", state="incompatible", refs=source["refs"])
    count = _genome_denominator(context, request, source)
    reported = _input_cell(context, source, row_key, row, field, unit=unit)
    cells = [count, reported]
    codes = source["codes"] + row["qualification_codes"]
    if any(code in codes for code in ("identity_conflict", "duplicate_record_conflict")):
        _unavailable("identity_conflict", source["role"], state="incompatible", refs=source["refs"])
    if formula == "subsystem_role_conservation":
        raw, state, row_codes, extra_refs = context.associations(request, source, joined=True)
        rows, identity_state, identity_codes, refs = _entity_rows(request, source, raw, keys=["genome_id", "role_id"])
        pairs = {(r["identifiers"]["genome_id"], r["identifiers"]["role_id"]) for r in rows}
        numerator = _cell(len(pairs), "genome_role_pair", request["population_id"], "distinct_valid_genome_role_pairs",
                          _refs(refs, extra_refs), state=_worst(state, identity_state), codes=row_codes + identity_codes)
    else:
        numerator_field = {"pathway_ec_conservation": "reported_genome_ec_count",
                           "pathway_gene_conservation": "reported_feature_token_count",
                           "subsystem_gene_conservation": "reported_feature_token_count",
                           "subsystem_prop_active": "reported_genome_count"}[formula]
        numerator_unit = "genome_ec_pair" if formula == "pathway_ec_conservation" else (
            "genome" if formula == "subsystem_prop_active" else "feature_token")
        numerator = _input_cell(context, source, row_key, row, numerator_field, unit=numerator_unit, integer=True)
    cells.append(numerator)
    components = None
    if formula != "subsystem_prop_active":
        component_field = "reported_ec_token_count" if formula.startswith("pathway_") else "reported_role_token_count"
        components = _input_cell(context, source, row_key, row, component_field,
                                 unit="ec_token" if formula.startswith("pathway_") else "role_token", integer=True)
        cells.append(components)
    state = _worst(source["state"], *(c["state"] for c in cells))
    refs = _refs(source["refs"], *(c["input_refs"] for c in cells))
    codes = _distinct(codes + [code for c in cells for code in c["qualification_codes"]])
    discrepancy = None
    if state == "available":
        denominator = count["value"] * (components["value"] if components else 1)
        # This reproduces the source's zero sentinel for a consistency check;
        # newly calculated descriptive ratios use missing for zero denominator.
        try:
            scale = 100 if formula in ("pathway_ec_conservation", "subsystem_role_conservation") else 1
            recomputed = scale * numerator["value"] / denominator if denominator else 0
            discrepancy = abs(reported["value"] - recomputed)
        except OverflowError:
            discrepancy = None
        if discrepancy is None or not math.isfinite(discrepancy):
            discrepancy, state = None, "invalid"
            codes.append("nonfinite_number")
        elif discrepancy > parameters["absolute_tolerance"] + parameters["relative_tolerance"] * abs(recomputed):
            codes.append("native_formula_mismatch")
    output = _cell(discrepancy, unit, request["population_id"], "reported_formula_check", refs, state=state, codes=codes)
    return output, None, refs


def _failure(context, request, problem):
    unit, numerator_unit, denominator_unit, scale, method = _units(request)
    output = _cell(None, unit, request["population_id"], method, problem.refs, state=problem.state, codes=[problem.code])
    if request["quantity"] in _SCALAR:
        return output, None, problem.refs
    numerator = _cell(None, numerator_unit, request["population_id"], "unavailable", problem.refs,
                      state=problem.state, codes=[problem.code])
    denominator = _cell(None, denominator_unit, request["population_id"], "unavailable", problem.refs,
                        state=problem.state, codes=[problem.code])
    return output, {"numerator": numerator, "denominator": denominator, "scale": scale,
                    "output": deepcopy(output), "genome_population_id": request["population_id"],
                    "component_population_id": None}, problem.refs


def calculate_comparative_systems_components(sheet: dict, *, parameters: dict) -> dict:
    """Calculate each selected QuantityV1 once using only saved supplied data.

    Repeating this call with changed explicit parameters returns a detached new
    result. The sheet, previous components, and all historical credit are untouched.
    """
    saved = validate_shape("ComparativeSystemsSheetV1", sheet)
    selected = validate_calculation_parameters(parameters)
    context = _Context(saved)
    result = {"version": "bvbrc_comparative_systems_components_v1",
              "formula_version": "bvbrc_comparative_systems_formulas_v1",
              "analysis_id": saved["analysis_id"], "sheet_sha256": canonical_sha256(saved),
              "parameters": selected, "components": [], "requirements": [], "diagnostics": []}
    for request in selected["requests"]:
        role, document_id = "native_document", None
        source_refs = []
        try:
            source = context.source(request)
            role = source["role"]
            document_id = source["view"]["document_id"] if source["view"] else None
            source_refs = ([source["document"]["source_ref"]] if source["view"] else
                           _distinct(row["source_ref"] for row in source["record_set"]["rows"]))
            quantity = request["quantity"]
            if quantity in _FAMILY_NATIVE:
                value, ratio, refs = _family(context, request, source)
            elif quantity == "subsystem_explicit_category_genome_count":
                value, ratio, refs = _categories(context, request, source)
            elif quantity in _PAIR:
                value, ratio, refs = _family_sets(context, request, source)
            elif quantity == "reference_component_representation":
                role = "reference_membership"
                value, ratio, refs = _reference(context, request, source)
            elif quantity == "reported_formula_check":
                value, ratio, refs = _reported_formula(context, request, source, selected)
            else:
                value, ratio, refs = _record_quantities(context, request, source)
        except _Unavailable as problem:
            role = problem.role
            value, ratio, refs = _failure(context, request, problem)
        population_ids = [request["population_id"]] if request["population_id"] in context.populations else []
        if ratio and ratio["component_population_id"] is not None:
            population_ids.append(ratio["component_population_id"])
        component = {"component_id": request["component_id"], "quantity": request["quantity"],
                     "entity": deepcopy(request["entity"]), "value": value, "ratio": ratio, "input_refs": refs,
                     "population_ids": _distinct(population_ids), "reference_membership_id": request["reference_membership_id"],
                     "qualification_codes": list(value["qualification_codes"])}
        result["components"].append(component)
        for code in component["qualification_codes"]:
            result["diagnostics"].append({"code": code, "phase": "calculation", "document_id": document_id,
                                          "row_ordinal": None, "field": role, "source_refs": source_refs, "locations": [],
                                          "affected_field_ids": [request["component_id"]], "required_input_role": None})
        if value["state"] != "available":
            repair_codes = [code for code in component["qualification_codes"] if code in {
                "missing_required_field", "missing_document_selection", "data_input_unavailable", "population_incomplete",
                "population_incompatible", "empty_denominator", "reference_membership_missing", "incomplete_reference_membership",
                "identity_conflict", "duplicate_record_conflict", "native_identifier_placeholder", "format_incompatible",
                "numeric_token_invalid", "ambiguous_document_selection", "original_task_mismatch", "nonfinite_number"}]
            for code in repair_codes or ["missing_required_field"]:
                result["requirements"].append({"requirement_id": request["component_id"] + ":" + code,
                                               "code": code, "required_input_role": role, "document_id": document_id,
                                               "affected_field_ids": [request["component_id"]], "source_refs": source_refs})
    return validate_components(result, sheet=saved)
