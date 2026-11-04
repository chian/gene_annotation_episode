"""Bounded copies of requested saved values; no parsing or recalculation."""
from __future__ import annotations

from copy import deepcopy

from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, schema, validate_shape
from .bvbrc_comparative_systems_sheet_contracts import validate_sheet
from .bvbrc_comparative_systems_calculation_contracts import validate_components
from .bvbrc_comparative_systems_fact_contracts import requested_selection, validate_requested_form, require
from .bvbrc_comparative_systems_bundle_contracts import (
    TABLE_ROWS, issue, original_request, requirement, unique, unique_index, validate_parameters,
)

_UNITS = {
    "positive_genome_count_from_list": "genome", "reported_active_occurrences": "occurrence",
    "reported_ec_conservation_percent": "percent", "reported_ec_token_count": "ec_token",
    "reported_feature_count": "feature_token", "reported_feature_occurrences": "occurrence",
    "reported_feature_token_count": "feature_token", "reported_genome_count": "genome",
    "reported_genome_ec_count": "genome_ec_pair", "reported_inactive_placeholder": "occurrence",
    "reported_length_max": "amino_acid", "reported_length_mean": "amino_acid", "reported_length_min": "amino_acid",
    "reported_length_population_sd": "amino_acid", "reported_likely_occurrences": "occurrence",
    "reported_missing_genome_count": "genome", "reported_record_genome_fraction": "fraction",
    "reported_role_conservation_percent": "percent", "reported_role_token_count": "role_token",
    "reported_subsystem_name_count": "subsystem_name",
}
_ROW_SCHEMAS = {"plfam": "FamilyRowV1", "pgfam": "FamilyRowV1", "pathway": "PathwayRowV1",
                "ecnumber": "PathwayECRowV1", "subsystems": "SubsystemRowV1", "overview": "OverviewRowV1",
                "variant_matrix": "VariantRowV1"}
_ENTITY_KINDS = {"plfam": "family", "pgfam": "family", "pathway": "pathway", "ecnumber": "pathway_ec",
                 "subsystems": "subsystem", "overview": "overview", "variant_matrix": "variant"}


def validate_projection_failure_context(value: object) -> dict:
    """Validate original failure inputs separately from final projection rows."""
    require(type(value) is dict and set(value) == {
        "retained_requirements", "retained_diagnostics", "failure_status"}, "failure_context_shape_invalid")
    canonical_sha256(value)
    require(type(value["retained_requirements"]) is list and type(value["retained_diagnostics"]) is list,
            "failure_context_arrays_required")
    require(value["failure_status"] is None or type(value["failure_status"]) is str
            and value["failure_status"] in {"partial", "invalid"}, "failure_context_status_invalid")
    return {"retained_requirements": [validate_shape("RequirementV1", row) for row in value["retained_requirements"]],
            "retained_diagnostics": [validate_shape("DiagnosticV1", row) for row in value["retained_diagnostics"]],
            "failure_status": value["failure_status"]}


def _worst(states):
    return max(states, key=("satisfied", "unavailable", "partial", "invalid").index, default="satisfied")


def _cell_missing(field, table, *, population=None, state="missing", code="missing_required_field"):
    unit = _UNITS.get(field, "feature_per_role_genome" if table == "subsystems" else "feature_per_ec_genome")
    return {"state": state, "value": None, "unit": unit, "origin": "unavailable",
            "population_id": population, "method_id": "unavailable", "input_refs": [],
            "uncertainty": None, "qualification_codes": [code]}


class _Projection:
    def __init__(self, sheet, components, form, *, retained_requirements=(), retained_diagnostics=(), failure_status=None):
        self.sheet, self.components = sheet, components
        self.retained_requirements, self.retained_diagnostics = retained_requirements, retained_diagnostics
        self.failure_status = failure_status
        self.selected = requested_selection(form)["fields"]
        self.facts, self.requirements, self.diagnostics = {}, [], []
        self.views = unique_index(sheet["document_selection"]["authoritative_views"], "view_id") if sheet else {}
        self.documents = unique_index(sheet["source_documents"], "document_id") if sheet else {}
        self.populations = unique_index(sheet["populations"], "population_id") if sheet else {}
        self.assignments = unique_index(sheet["population_assignments"]["assignments"], "population_id") if sheet else {}
        self.references = unique_index(sheet["reference_memberships"], "membership_id") if sheet else {}
        self.calculated = unique_index(components["components"], "component_id") if components else {}
        supplied = sheet["supplied_record_sets"] if sheet else None
        self.records = unique_index(supplied["record_sets"], "record_set_id") if supplied else {}
        self.data_selection = unique_index(supplied["selection"]["record_sets"], "record_set_id") if supplied else {}

    def problem(self, field, code, *, role="native_document", document=None, refs=()):
        args = dict(document_id=document, role=role, refs=refs, fields=[field["field_id"]])
        self.requirements.append(requirement(code, **args))
        self.diagnostics.append(issue(code, **args))

    def native(self, field):
        selector = field["selector"]
        view = self.views.get(selector["view_id"])
        if view is None:
            self.problem(field, "missing_document_selection")
            return [_cell_missing(selector["native_field"], None)], "satisfied"
        table, document_id = view["table"], view["document_id"]
        definition = _ROW_SCHEMAS.get(table)
        if (definition is None or selector["native_field"] not in schema(definition)["$defs"][definition]["properties"]
                or selector["entity"]["kind"] != _ENTITY_KINDS[table]
                or table in {"plfam", "pgfam"} and selector["entity"]["family_kind"] != table):
            self.problem(field, "format_incompatible", document=document_id)
            return [], "invalid"
        document = self.documents.get(document_id)
        rows = [row for row in self.sheet[TABLE_ROWS[table]] if row["document_id"] == document_id
                and row["entity"] == selector["entity"]]
        if rows:
            return [deepcopy(row[selector["native_field"]]) for row in rows], "satisfied"
        populations = [assignment["population_id"] for assignment in self.assignments.values()
                       if assignment["kind"] == "native_view_represented_genomes"
                       and assignment["view_id"] == view["view_id"]]
        state, code = "missing", "missing_required_field"
        if document is None:
            code = "missing_document_selection"
        else:
            native = next(row for row in self.sheet["native_documents"] if row["document"]["document_id"] == document_id)
            if native["status"] in {"invalid", "failed"}:
                state, code = native["status"], "format_incompatible"
            elif document["object_complete"] != "complete" or document["transfer_body_complete"] != "complete":
                state, code = "truncated", "artifact_truncated"
        self.problem(field, code, role=document["role"] if document else "native_document", document=document_id,
                     refs=[document["source_ref"]] if document else [])
        return [_cell_missing(selector["native_field"], table, population=populations[0] if len(populations) == 1 else None,
                              state=state, code=code)], "satisfied"

    def calculated_value(self, field):
        selector = field["selector"]
        component = self.calculated.get(selector["component_id"])
        if component is None:
            self.problem(field, "invalid_component_request")
            return [], "partial"
        if selector["kind"] == "ratio":
            if component["ratio"] is None:
                self.problem(field, "invalid_component_request")
                return [], "invalid"
            return [deepcopy(component["ratio"])], "satisfied"
        return [deepcopy(component["value"])], "satisfied"

    def population(self, field):
        population = self.populations.get(field["selector"]["population_id"])
        if population is None:
            self.problem(field, "missing_required_field", role="original_genome_population")
            return [], "partial"
        return [{key: deepcopy(population[key]) for key in schema("PopulationFactV1")["$defs"]["PopulationFactV1"]["required"]}], "satisfied"

    @staticmethod
    def _association_matches(row, selector):
        entity, ids = selector["entity"], row["identifiers"]
        if selector["genome_id"] is not None and selector["genome_id"] != ids["genome_id"]:
            return False
        kind = entity["kind"]
        if kind == "family":
            return selector["member_id"] == entity["family_id"] == ids[entity["family_kind"] + "_id"]
        field, component = ("pathway_id", "ec_number") if kind.startswith("pathway") else ("subsystem_id", "role_id")
        if entity[field] != ids[field] or selector["member_id"] != ids[component]:
            return False
        if entity[component] is not None and entity[component] != selector["member_id"]:
            return False
        raw = {item["name"]: item["raw_text"] for item in row["fields"]}
        for name, original in (("superclass_native", "superclass"), ("class_name", "class"),
                               ("subclass", "subclass"), ("subsystem_name", "subsystem_name")):
            if entity[name] is not None and entity[name] != raw.get(original):
                return False
        return True

    def membership(self, field):
        selector = field["selector"]
        result = {key: deepcopy(selector[key]) for key in ("entity", "genome_id", "member_id", "population_id")}
        result.update(presence_state="no_record_completeness_unknown", source_locations=[])
        population = self.populations.get(selector["population_id"])
        if population is None:
            self.problem(field, "missing_required_field", role="original_genome_population")
            return [], "partial"
        entity = selector["entity"]
        if selector["genome_id"] is not None and population["member_kind"] == "genome_id" \
                and selector["genome_id"] not in population["members"]:
            self.problem(field, "population_incompatible", role="original_genome_population")
            return [], "invalid"
        assignment = self.assignments.get(selector["population_id"])
        associations, complete, source_exists = [], False, False
        if assignment and assignment["view_id"] in self.views:
            view = self.views[assignment["view_id"]]
            source_exists = view["document_id"] in self.documents
            if view["table"] in {"plfam", "pgfam"} and entity["kind"] == "family":
                require(selector["member_id"] == entity["family_id"], "membership_entity_mismatch")
                matches = [row for row in self.sheet["family_rows"] if row["document_id"] == view["document_id"]
                           and row["entity"] == entity and entity["family_kind"] == view["table"]]
                if len(matches) > 1:
                    self.problem(field, "ambiguous_document_selection", document=view["document_id"])
                    result["presence_state"] = "conflicting"
                    return [result], "invalid"
                if matches:
                    row = matches[0]
                    counts = [item for item in row["genome_counts"] if item["genome_id"] == selector["genome_id"]]
                    positive = row["positive_genome_count_from_list"]
                    if ((selector["genome_id"] in row["positive_genome_ids"] or
                         selector["genome_id"] is None and bool(row["positive_genome_ids"])) and positive["state"] == "available"
                            and "population_incompatible" not in positive["qualification_codes"]):
                        # Positive list membership survives an undecodable hex
                        # count. Its source remains the actual retained map.
                        result["presence_state"] = "recorded_positive"
                        native = next(item for item in self.sheet["native_documents"] if item["document"]["document_id"] == view["document_id"])
                        result["source_locations"] = [deepcopy(item["location"]) for item in native["metadata"]
                                                      if item["location"]["json_pointer"] == "/" + view["table"] + "_genomes"]
                    elif len(counts) == 1:
                        result["presence_state"] = counts[0]["presence_state"]
                        result["source_locations"] = deepcopy(counts[0]["source_locations"])
                    return [result], "satisfied"
            associations = [row for row in self.sheet["association_rows"]
                            if row["document_id"] == view["document_id"] and row["table"] == view["table"]]
        else:
            record_sets = [row for key, row in self.records.items() if key == selector["population_id"]
                           or self.data_selection[key]["declared_genome_population"]["population_id"] == selector["population_id"]]
            expected_collection = "genome_feature" if entity["kind"] == "family" else "pathway" if entity["kind"].startswith("pathway") else "subsystem"
            record_sets = [row for row in record_sets if row["collection"] == expected_collection]
            if len(record_sets) > 1:
                self.problem(field, "ambiguous_document_selection")
                result["presence_state"] = "incompatible"
                return [result], "invalid"
            if record_sets:
                source_exists = True
                records = record_sets[0]
                complete = (records["population"]["completeness"] == "complete_for_declared_population"
                            and records["page_coverage"] == "complete" and records["snapshot_consistency"] == "single_response")
                associations = [row["association"] for row in records["rows"]
                                if row["filter_state"] == "included" and row["association"] is not None]
        matches = [row for row in associations if self._association_matches(row, selector)]
        if (selector["genome_id"] is not None and population["member_kind"] != "genome_id"
                and not any(row["identifiers"]["genome_id"] == selector["genome_id"] for row in associations)):
            self.problem(field, "missing_required_field", role="original_genome_population")
            return [], "partial"
        identity_selector = {**selector, "genome_id": None}
        identified = any(self._association_matches(row, identity_selector) for row in associations)
        identified |= any(reference["entity"] == entity and selector["member_id"] in reference["members"]
                          for reference in self.references.values())
        if not identified:
            # A caller's arbitrary string is not a retained native identifier.
            # A measured complete empty query count remains in its population
            # facts; that count does not manufacture a membership identity.
            self.problem(field, "missing_required_field")
            return [], "partial"
        if matches:
            result["presence_state"] = ("conflicting" if any(row["identity_status"] == "conflicting" for row in matches)
                                        else "recorded_positive")
            result["source_locations"] = unique([item["location"] for row in matches for item in row["fields"]])
        elif complete:
            result["presence_state"] = "zero_in_qualified_record_population"
            result["source_locations"] = deepcopy(record_sets[0]["population"]["source_locations"])
        elif not source_exists:
            result["presence_state"] = "not_measured"
            self.problem(field, "missing_document_selection")
        return [result], "satisfied"

    def complete(self, population_id):
        population = self.populations.get(population_id) or self.references.get(population_id)
        return population is not None and population["completeness"] == "complete_for_declared_population"

    def available(self, field, value):
        requirement_kind = field["availability_requirement"]
        if requirement_kind == "typed_state":
            return True
        kind = field["selector"]["kind"]
        if kind in {"measurement", "computed_measurement"}:
            available, population_ids = value["state"] == "available", [value["population_id"]]
        elif kind == "ratio":
            available = all(value[key]["state"] == "available" for key in ("output", "numerator", "denominator"))
            population_ids = [value["genome_population_id"]]
            if value["component_population_id"] is not None:
                population_ids.append(value["component_population_id"])
        elif kind == "population":
            available = all(value[key]["state"] == "available" for key in ("raw_occurrence_count", "distinct_valid_member_count"))
            population_ids = [value["population_id"]]
        elif kind == "membership":
            available = value["presence_state"] in {"recorded_positive", "zero_in_qualified_record_population"}
            population_ids = [value["population_id"]]
        else:
            return True
        return available and (requirement_kind != "available_complete_population" or all(self.complete(pid) for pid in population_ids))

    def add(self, field, values, status):
        expected = field["expected_cardinality"]
        if len(values) != expected:
            code = "ambiguous_document_selection" if len(values) > expected else "missing_required_field"
            self.problem(field, code)
            status = "invalid" if len(values) > expected else _worst([status, "partial"])
        if any(not self.available(field, value) for value in values):
            self.problem(field, "population_incomplete" if field["availability_requirement"] == "available_complete_population"
                         else "missing_required_field")
            status = _worst([status, "partial"])
        self.facts[field["field_id"]] = {"field_id": field["field_id"], "values": deepcopy(values), "status": status}

    def run(self):
        handlers = {"measurement": self.native, "computed_measurement": self.calculated_value,
                    "ratio": self.calculated_value, "population": self.population, "membership": self.membership}
        for field in self.selected:
            if field["selector"]["kind"] in handlers:
                self.add(field, *handlers[field["selector"]["kind"]](field))
        # Select bounded original requirements/diagnostics plus explicit
        # scientific projection dependency failures. Metadata selectors share
        # one snapshot: their own cardinality failures belong to the result's
        # failure arrays, not recursively to a later sibling's selected facts.
        source_rows = {
            "requirements": unique([*(self.sheet["requirements"] if self.sheet else []),
                *(self.components["requirements"] if self.components else []),
                *self.retained_requirements,
                *self.requirements]),
            "diagnostics": unique([*(self.sheet["diagnostics"] if self.sheet else []),
                *(self.components["diagnostics"] if self.components else []),
                *self.retained_diagnostics,
                *self.diagnostics]),
        }
        for field in self.selected:
            kind, selector = field["selector"]["kind"], field["selector"]
            if kind in {"requirement", "qualification"}:
                key = "requirements" if kind == "requirement" else "diagnostics"
                rows = source_rows[key]
                wanted = "required_input_role" if kind == "requirement" else "code"
                values = [row for row in rows if row[wanted] == selector[wanted]]
                self.add(field, values, "satisfied")
        state = _worst([field["status"] for field in self.facts.values()]) if self.sheet is not None else "unavailable"
        if self.failure_status == "invalid":
            state = "invalid"
        affected = [key for key, value in self.facts.items() if value["status"] != "satisfied"]
        for field in self.selected:
            if field["selector"]["kind"] == "request_status":
                self.add(field, [{"status": state, "affected_field_ids": affected}], "satisfied")
        facts = {field["field_id"]: self.facts[field["field_id"]] for field in self.selected}
        return facts, unique(self.requirements), unique(self.diagnostics)


def project_details(sheet, components, *, requested_form, failure_context):
    form = validate_requested_form(requested_form)
    context = validate_projection_failure_context(failure_context)
    saved = validate_sheet(sheet) if sheet is not None else None
    require(components is None or saved is not None, "components_without_sheet")
    calculated = validate_components(components, sheet=saved) if components is not None else None
    facts, requirements, diagnostics = _Projection(saved, calculated, form,
        **context).run()
    validate_shape("ProviderFactsV1", facts)
    return facts, requirements, diagnostics


def project_comparative_systems_facts(sheet, components, *, requested_form):
    return project_details(sheet, components, requested_form=requested_form, failure_context={
        "retained_requirements": [], "retained_diagnostics": [], "failure_status": None})[0]


def assemble_projection(sheet, components, *, requested_form, failure_context):
    context = validate_projection_failure_context(failure_context)
    retained_requirements, retained_diagnostics, failure_status = (
        context["retained_requirements"], context["retained_diagnostics"], context["failure_status"])
    facts, requirements, diagnostics = project_details(sheet, components, requested_form=requested_form,
        failure_context=context)
    states = [value["status"] for value in facts.values()]
    status = "invalid" if "invalid" in states else "partial" if any(state != "satisfied" for state in states) else "ok"
    if failure_status is not None:
        require((sheet is None or components is None) and failure_status in {"partial", "invalid"}, "invalid_failure_status")
        status = "invalid" if failure_status == "invalid" or status == "invalid" else "partial"
    elif sheet is None:
        status = "partial" if status == "ok" else status
    return {"adapter_id": "bvbrc_comparative_systems", "adapter_version": "1", "status": status,
            "sheet": deepcopy(sheet), "components": deepcopy(components), "facts": facts,
            "missing_requirements": unique([*(sheet["requirements"] if sheet else []),
                                             *(components["requirements"] if components else []), *retained_requirements, *requirements]),
            "diagnostics": unique([*(sheet["diagnostics"] if sheet else []),
                                    *(components["diagnostics"] if components else []), *retained_diagnostics, *diagnostics])}


def _failure_records(parameters, bundle, form, requirements, diagnostics):
    """Check retained failure identities; I authenticates their original bytes."""
    documents = {row["document_id"] for row in parameters["document_selection"]["documents"]}
    content = [*bundle.get("supplied_contents", []), *(row["content"] for row in bundle["supplied_scientific_metadata"])]
    pairs = {(row["source_ref"], row["raw_artifact_ref"]) for row in bundle["artifacts"]}
    pairs.update((row["source_ref"], row["artifact_ref"]) for row in content)
    document_pairs = {}
    sources = {row["source_ref"] for row in bundle["artifacts"]}
    sources.update(row["source_ref"] for row in bundle.get("supplied_contents", []))
    sources.update(row["content"]["source_ref"] for row in bundle["supplied_scientific_metadata"])
    sources.update(bundle["original_task"][key] for key in ("submission_receipt_ref", "submission_source_ref"))
    for row in parameters["document_selection"]["documents"]:
        selected = row["input"]
        if selected["kind"] == "possessed_artifact":
            selected_pairs = {(selected["source_ref"], selected["raw_artifact_ref"])}
        else:
            selected_pairs = {(member["source_ref"], member["raw_artifact_ref"]) for member in bundle["artifacts"]
                              if selected["requirement_id"] in member.get("requirement_ids", [])}
        document_pairs[row["document_id"]] = selected_pairs
        pairs.update(selected_pairs)
    if parameters["supplied_data_selection"]:
        sources.update(source for row in parameters["supplied_data_selection"]["record_sets"] for source in row["source_refs"])
    pairs.update((location["source_ref"], location["raw_artifact_ref"])
                 for row in parameters["reference_memberships"] for location in row["source_locations"])
    pairs.update((row["source_ref"], row["raw_artifact_ref"]) for row in parameters["producer_evidence_selections"])
    sources.update(source for source, _ in pairs)
    field_ids = {row["field_id"] for row in requested_selection(form)["fields"]}
    field_ids.update(row["component_id"] for row in parameters["calculation_parameters"]["requests"])
    for record in [*requirements, *diagnostics]:
        require(record["document_id"] is None or record["document_id"] in documents, "saved_failure_document_mismatch")
        require(set(record["source_refs"]) <= sources, "saved_failure_source_mismatch")
        require(set(record["affected_field_ids"]) <= field_ids, "saved_failure_field_mismatch")
        for location in record.get("locations", []):
            pair = (location["source_ref"], location["raw_artifact_ref"])
            require(pair in pairs and (location["document_id"] is None or
                    pair in document_pairs.get(location["document_id"], set())), "saved_failure_location_mismatch")


def _compare_projection(expected, facts, status, missing_requirements, diagnostics):
    for key, value in (("facts", facts), ("status", status), ("missing_requirements", missing_requirements), ("diagnostics", diagnostics)):
        require(canonical_sha256(expected[key]) == canonical_sha256(value), "saved_projection_mismatch:" + key)


def validate_saved_comparative_systems_projection(sheet, components, *, facts, status,
        missing_requirements, diagnostics, requested_form, parameters, original_task, bundle, failure_context):
    """Validate saved identity and exact selected copies without rerunning N/D/C.

    The host separately authenticates these original saved bytes and receiver
    possession. Equality here never substitutes for the host's custody checks.
    """
    selected = validate_parameters(parameters)
    context = validate_projection_failure_context(failure_context)
    form = validate_requested_form(requested_form)
    bound = validate_contract("ArtifactBundle", bundle)
    task = validate_contract("OriginalTask", original_task)
    require(canonical_sha256(task) == canonical_sha256(bound["original_task"]), "original_task_mismatch")
    original = original_request(task)
    validate_shape("ProviderResultV1", {"adapter_id": "bvbrc_comparative_systems", "adapter_version": "1",
        "sheet": sheet, "components": components, "facts": facts, "status": status,
        "missing_requirements": missing_requirements, "diagnostics": diagnostics})
    require(components is None or sheet is not None, "components_without_sheet")
    _failure_records(selected, bound, form, context["retained_requirements"], context["retained_diagnostics"])
    _failure_records(selected, bound, form, missing_requirements, diagnostics)
    require(status != "invalid" or bool(missing_requirements or diagnostics), "saved_invalid_without_failure")
    if sheet is None:
        require(status in {"partial", "invalid"}, "saved_unavailable_status_mismatch")
        expected = assemble_projection(None, None, requested_form=form, failure_context=context)
        _compare_projection(expected, facts, status, missing_requirements, diagnostics)
        return
    saved = validate_sheet(sheet)
    calculated = validate_components(components, sheet=saved) if components is not None else None
    require(saved["analysis_id"] == selected["analysis_id"]
            and saved["original_request"] == original, "saved_original_request_mismatch")
    for key in ("document_selection", "population_assignments"):
        require(canonical_sha256(saved[key]) == canonical_sha256(selected[key]), "saved_parameters_mismatch")
    if calculated is not None:
        require(canonical_sha256(calculated["parameters"]) == canonical_sha256(selected["calculation_parameters"]),
                "saved_calculation_parameters_mismatch")
    data = saved["supplied_record_sets"]
    require((data is None) == (selected["supplied_data_selection"] is None), "saved_data_selection_mismatch")
    if data is not None:
        require(canonical_sha256(data["selection"]) == canonical_sha256(selected["supplied_data_selection"]),
                "saved_data_selection_mismatch")
    requested_references = {row["membership_id"]: row for row in selected["reference_memberships"]}
    for reference in saved["reference_memberships"]:
        original = deepcopy(requested_references.get(reference["membership_id"]))
        require(original is not None, "saved_reference_selection_mismatch")
        if original["release"] is None and "reference_release_unknown" not in original["qualification_codes"]:
            original["qualification_codes"].append("reference_release_unknown")
        pairs = {(location["source_ref"], location["raw_artifact_ref"]) for location in original["source_locations"]}
        for record in (data["record_sets"] if data else []):
            if pairs == {(page["binding"]["source_ref"], page["binding"]["native_artifact_ref"]) for page in record["pages"]}:
                original["qualification_codes"] = list(dict.fromkeys(
                    requested_references[reference["membership_id"]]["qualification_codes"]
                    + record["population"]["qualification_codes"] + ["reference_release_unknown"]))
        require(original == reference, "saved_reference_selection_mismatch")
    selected_producers = {row["evidence_id"] for row in selected["producer_evidence_selections"]}
    require({row["evidence_id"] for row in saved["producer_evidence"]} == selected_producers,
            "saved_producer_selection_mismatch")
    # Exact binding resolution is repeated, but bytes are not read or parsed.
    for document in saved["source_documents"]:
        selection = next(row for row in selected["document_selection"]["documents"] if row["document_id"] == document["document_id"])
        source = selection["input"]
        matches = [member for member in bound["artifacts"] if
                   (source["requirement_id"] in member.get("requirement_ids", []) if source["kind"] == "requirement"
                    else member["source_ref"] == source["source_ref"] and member["raw_artifact_ref"] == source["raw_artifact_ref"])]
        require(len(matches) == 1, "saved_document_selection_mismatch")
        member = matches[0]
        require(all(document[key] == member[key] for key in ("source_ref", "raw_artifact_ref", "sha256", "byte_count", "role"))
                and member["declared_format"]["format"] == document["format_profile"]
                and document["original_task_ref"] == task["submission_receipt_ref"], "saved_document_binding_mismatch")
        require(document["transfer_body_complete"] == ("complete" if member["transfer"]["body_complete"] else "partial")
                and document["object_complete"] == {"yes": "complete", "no": "partial", "unknown": "unknown"}[member["transfer"]["object_complete"]],
                "saved_document_transfer_mismatch")
    expected = assemble_projection(saved, calculated, requested_form=form, failure_context=context)
    _compare_projection(expected, facts, status, missing_requirements, diagnostics)


__all__ = ["project_comparative_systems_facts", "validate_saved_comparative_systems_projection",
           "validate_projection_failure_context"]
