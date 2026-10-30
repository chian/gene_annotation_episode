"""Detached saved-shape and reference validation, without parsing or grading.

These checks do not authenticate artifacts. Native creation and Data extraction
own source interpretation; calculators own scientific formulas. Here only saved
identities, source fields, selectors and relationships are checked.
"""
from __future__ import annotations

from .bvbrc_comparative_systems_handoff_contracts import validate_shape

__all__ = ("validate_native_document", "validate_sheet")

_COUNT_UNITS = {"occurrence", "genome", "feature", "feature_token", "ec_token", "role_token",
                "family", "subsystem_name", "record", "genome_ec_pair", "genome_role_pair",
                "ec_genome_opportunity", "role_genome_opportunity"}
_NATIVE_FIELDS = {
    "reported_feature_occurrences": "feature_count", "reported_genome_count": "genome_count",
    "reported_length_min": "aa_length_min", "reported_length_max": "aa_length_max",
    "reported_length_mean": "aa_length_mean", "reported_length_population_sd": "aa_length_std",
    "reported_ec_token_count": "ec_count", "reported_genome_ec_count": "genome_ec",
    "reported_ec_conservation_percent": "ec_conservation", "reported_gene_conservation": "gene_conservation",
    "reported_role_token_count": "role_counts", "reported_role_conservation_percent": "role_conservation",
    "reported_record_genome_fraction": "prop_active", "reported_active_occurrences": "active",
    "reported_likely_occurrences": "likely", "reported_inactive_placeholder": "inactive",
    "reported_missing_genome_count": "missing_genomes", "reported_subsystem_name_count": "subsystem_name_counts",
    "reported_feature_count": "gene_counts",
}
_NATIVE_UNITS = {"feature_count": "occurrence", "genome_count": "genome", "ec_count": "ec_token",
                 "gene_count": "feature_token", "genome_ec": "genome_ec_pair", "ec_conservation": "percent",
                 "role_counts": "role_token", "gene_counts": "feature_token", "role_conservation": "percent",
                 "prop_active": "fraction", "aa_length_min": "amino_acid", "aa_length_max": "amino_acid",
                 "aa_length_mean": "amino_acid", "aa_length_std": "amino_acid", "genomes": "occurrence",
                 "active": "occurrence", "likely": "occurrence", "inactive": "occurrence", "missing_genomes": "genome",
                 "subsystem_name_counts": "subsystem_name"}


def _fail(code):
    raise ValueError("comparative_systems_" + code)


def _unique(items, key, code):
    result = {}
    for item in items:
        value = item[key]
        if value in result:
            _fail(code)
        result[value] = item
    return result


def _walk(value):
    if type(value) is dict:
        yield value
        if set(value) == {"location", "value"}:
            # Losslessly retained native JSON is data, not another contract.
            yield from _walk(value["location"])
            return
        for item in value.values():
            yield from _walk(item)
    elif type(value) is list:
        for item in value:
            yield from _walk(item)


def _resolve(value, pointer):
    if not pointer:
        return value
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        try:
            if type(value) is list:
                if not token.isascii() or not token.isdigit() or str(int(token)) != token:
                    _fail("reference_pointer_invalid")
                value = value[int(token)]
            elif type(value) is dict:
                value = value[token]
            else:
                _fail("reference_pointer_invalid")
        except (KeyError, IndexError, ValueError):
            _fail("reference_pointer_invalid")
    return value


def _native_pointer(native, pointer):
    if not pointer:
        return native
    for table in native["tables"]:
        if table["json_pointer"] == pointer:
            return table
    for item in native["metadata"]:
        prefix = item["location"]["json_pointer"]
        if pointer == prefix:
            return item["value"]
        if pointer.startswith(prefix + "/"):
            return _resolve(item["value"], pointer[len(prefix):])
    _fail("reference_pointer_invalid")


def _cell(cell):
    if cell["state"] == "available":
        value, unit = cell["value"], cell["unit"]
        if unit in _COUNT_UNITS and (type(value) is not int or value < 0):
            _fail("count_cell_invalid")
        if unit == "amino_acid" and value < 0:
            _fail("length_cell_invalid")
        if unit == "percent" and not 0 <= value <= 100:
            _fail("percentage_cell_invalid")
        if unit == "fraction" and not 0 <= value <= 1:
            _fail("fraction_cell_invalid")


def _location(location, docs):
    document_id = location["document_id"]
    if document_id is None:
        return
    if document_id not in docs:
        _fail("source_document_reference_missing")
    document = docs[document_id]["document"]
    if any(location[field] != document[field] for field in ("source_ref", "raw_artifact_ref")):
        _fail("source_location_binding_mismatch")
    table_name = location["table"]
    if table_name is not None and table_name not in ("overview", "document"):
        tables = [t for t in docs[document_id]["tables"] if t["table"] == table_name]
        if len(tables) != 1:
            # A decode diagnostic can point at a table that could not be read.
            if location["row_ordinal"] is None:
                return
            _fail("source_table_reference_missing")
        table = tables[0]
        row = location["row_ordinal"]
        if row is not None and row >= len(table["rows"]):
            _fail("source_row_reference_missing")
        if location["json_pointer"] != table["json_pointer"]:
            _fail("source_pointer_mismatch")


def validate_native_document(value: object) -> dict:
    """Validate a saved native result without reading or decoding source bytes."""
    native = validate_shape("NativeDocumentResultV1", value)
    document_id = native["document"]["document_id"]
    tables = _unique(native["tables"], "table", "duplicate_native_table")
    row_numbers = []
    for table in tables.values():
        for ordinal, row in enumerate(table["rows"]):
            if row["row_ordinal"] != ordinal:
                _fail("native_row_ordinal_mismatch")
            for number in row["numeric_fields"]:
                location = number["location"]
                if location["table"] != table["table"] or location["row_ordinal"] != ordinal:
                    _fail("native_number_location_mismatch")
                column = location["column_ordinal"]
                if column is not None and column < len(row["tokens"]):
                    if number["raw_lexeme"] != row["tokens"][column]:
                        _fail("native_number_lexeme_mismatch")
                elif number["raw_lexeme"] is not None:
                    _fail("native_number_column_mismatch")
                if location["native_field"] != number["native_field"]:
                    _fail("native_number_field_mismatch")
                row_numbers.append(number)
    reported = native["reported_numbers"]
    for number in row_numbers:
        if number not in reported:
            _fail("native_number_projection_missing")
    for number in reported:
        if number["location"]["table"] != "overview" and number not in row_numbers:
            _fail("native_number_projection_extra")
        native_field = number["native_field"]
        unit = _NATIVE_UNITS.get(native_field)
        if native_field == "gene_conservation":
            unit = "feature_per_role_genome" if number["location"]["table"] == "subsystems" else "feature_per_ec_genome"
        if unit is None or number["cell"]["unit"] != unit:
            _fail("native_number_unit_mismatch")
        method = "native_hex_exact_width" if native_field == "genomes" else "native_field"
        if number["cell"]["method_id"] != method or number["cell"]["origin"] != "program_reported_derived":
            _fail("native_number_meaning_mismatch")
        if number["cell"]["population_id"] is not None:
            _fail("native_population_not_assigned")
    docs = {document_id: native}
    for item in _walk(native):
        if set(item) == {"state", "value", "unit", "origin", "population_id", "method_id", "input_refs", "uncertainty", "qualification_codes"}:
            _cell(item)
        if set(item) == {"source_ref", "raw_artifact_ref", "document_id", "json_pointer", "table", "row_ordinal", "column_ordinal", "native_field"}:
            _location(item, docs)
        if set(item) == {"kind", "owner_id", "pointer"}:
            if item["kind"] != "native" or item["owner_id"] != document_id:
                _fail("native_cell_reference_mismatch")
            _native_pointer(native, item["pointer"])
    return native


def _selection(selection, documents, evidence, task_ref):
    selected = _unique(selection["documents"], "document_id", "duplicate_document_selection")
    views = _unique(selection["authoritative_views"], "view_id", "duplicate_view_id")
    for document_id, native in documents.items():
        document = native["document"]
        if document_id not in selected:
            _fail("unselected_native_document")
        item = selected[document_id]
        if document["original_task_ref"] != task_ref:
            _fail("original_task_mismatch")
        for field in ("role", "format_profile", "producer_evidence_id"):
            if document[field] != item[field]:
                _fail("document_selection_mismatch")
        source = item["input"]
        if source["kind"] == "possessed_artifact":
            if any(source[field] != document[field] for field in ("source_ref", "raw_artifact_ref")):
                _fail("document_selection_binding_mismatch")
        producer_id = document["producer_evidence_id"]
        if producer_id is not None and producer_id not in evidence:
            _fail("producer_reference_missing")
    for item in selected.values():
        if item["producer_evidence_id"] is not None and item["producer_evidence_id"] not in evidence:
            _fail("producer_reference_missing")
    for view in views.values():
        if view["document_id"] not in selected:
            _fail("view_document_reference_missing")
        profile = selected[view["document_id"]]["format_profile"].removeprefix("comparative_systems_")
        allowed = {"families_json_v1": {"plfam", "pgfam"}, "pathways_json_v1": {"pathway", "ecnumber", "genes"},
                   "subsystems_json_v1": {"subsystems", "genes", "overview"}, "pathways_tsv_v1": {"pathways_tsv"},
                   "subsystems_tsv_v1": {"subsystems_tsv"}, "variant_matrix_source670b_v1": {"variant_matrix"}}[profile]
        if view["table"] not in allowed:
            _fail("view_table_incompatible")
    for pair in selection["dependent_views"]:
        if pair["left_view_id"] == pair["right_view_id"] or any(pair[k] not in views for k in ("left_view_id", "right_view_id")):
            _fail("dependent_view_reference_invalid")
    return views


def validate_sheet(value: object) -> dict:
    """Validate saved identities, cells and field relationships, not formulas."""
    sheet = validate_shape("ComparativeSystemsSheetV1", value)
    docs = {}
    for native in sheet["native_documents"]:
        native = validate_native_document(native)
        doc_id = native["document"]["document_id"]
        if doc_id in docs:
            _fail("duplicate_native_document")
        docs[doc_id] = native
    sources = _unique(sheet["source_documents"], "document_id", "duplicate_source_document")
    if set(sources) != set(docs) or any(sources[key] != docs[key]["document"] for key in docs):
        _fail("source_document_projection_mismatch")
    evidence = _unique(sheet["producer_evidence"], "evidence_id", "duplicate_producer_id")
    views = _selection(sheet["document_selection"], docs, evidence, sheet["original_request"]["task_ref"])
    populations = _unique(sheet["populations"], "population_id", "duplicate_population_id")
    for population in populations.values():
        for key in ("raw_occurrence_count", "distinct_valid_member_count"):
            if population[key]["population_id"] != population["population_id"]:
                _fail("population_count_identity_mismatch")
        distinct = population["distinct_valid_member_count"]
        if distinct["state"] == "available" and distinct["value"] != len(set(population["members"])):
            _fail("population_membership_count_mismatch")
        raw = population["raw_occurrence_count"]
        if raw["state"] == distinct["state"] == "available" and raw["value"] < distinct["value"]:
            _fail("population_occurrence_count_mismatch")
    assignments = _unique(sheet["population_assignments"]["assignments"], "population_id", "duplicate_population_assignment")
    for population_id, assignment in assignments.items():
        if population_id not in populations or populations[population_id]["kind"] != assignment["kind"]:
            _fail("population_assignment_mismatch")
        if assignment["kind"] in ("requested_direct_genomes", "executed_genomes"):
            if any(assignment[k] is not None for k in ("view_id", "entity", "component_kind")):
                _fail("population_assignment_selector_invalid")
        elif assignment["view_id"] not in views:
            _fail("population_view_reference_missing")
        elif assignment["kind"] == "selected_component_membership":
            if assignment["entity"] is None or assignment["component_kind"] is None:
                _fail("population_component_selector_invalid")
            entity, component = assignment["entity"], assignment["component_kind"]
            if component == "ec_number" and (entity["kind"] not in ("pathway", "pathway_ec") or not entity["pathway_id"]):
                _fail("population_component_selector_invalid")
            if component == "role_id" and (entity["kind"] not in ("subsystem", "subsystem_role") or not entity["subsystem_id"]):
                _fail("population_component_selector_invalid")
            if component == "family_id" and (entity["family_kind"] not in ("plfam", "pgfam") or entity["kind"] not in ("family", "genome")):
                _fail("population_component_selector_invalid")
        elif assignment["entity"] is not None or assignment["component_kind"] is not None:
            _fail("population_assignment_selector_invalid")
    references = _unique(sheet["reference_memberships"], "membership_id", "duplicate_reference_membership")
    if set(references) & set(populations):
        _fail("population_reference_id_collision")
    record_sets = {}
    supplied = sheet["supplied_record_sets"]
    if supplied:
        record_sets = _unique(supplied["record_sets"], "record_set_id", "duplicate_record_set_id")
        for record_set in record_sets.values():
            population = record_set["population"]
            if populations.get(population["population_id"]) != population:
                _fail("supplied_population_projection_mismatch")
            if population["population_id"] in assignments:
                _fail("population_id_collision")
    associations = _unique(sheet["association_rows"], "association_id", "duplicate_association_id")
    for row in associations.values():
        if (row["document_id"] is None) == (row["record_set_id"] is None):
            _fail("association_owner_invalid")
        if row["document_id"] is not None:
            if row["document_id"] not in docs:
                _fail("association_document_reference_missing")
            tables = [t for t in docs[row["document_id"]]["tables"] if t["table"] == row["table"]]
            if len(tables) != 1 or row["row_ordinal"] >= len(tables[0]["rows"]):
                _fail("association_table_reference_missing")
            tokens = tables[0]["rows"][row["row_ordinal"]]["tokens"]
            for field in row["fields"]:
                loc = field["location"]
                if (loc["document_id"], loc["table"], loc["row_ordinal"]) != (row["document_id"], row["table"], row["row_ordinal"]):
                    _fail("association_field_location_mismatch")
                col = loc["column_ordinal"]
                if col is None or col >= len(tokens) or tokens[col] != field["raw_text"]:
                    _fail("association_field_value_mismatch")
            fields = {f["name"]: f["raw_text"] for f in row["fields"]}
            for name, identifier in row["identifiers"].items():
                field_name = "id" if name == "record_id" else name
                if identifier is not None and fields.get(field_name) != identifier:
                    _fail("association_identifier_mismatch")
            if row["active_category"] is not None and fields.get("active") != row["active_category"]:
                _fail("association_category_mismatch")
        elif row["record_set_id"] not in record_sets:
            _fail("association_record_set_reference_missing")
    for list_name in ("family_rows", "pathway_rows", "pathway_ec_rows", "subsystem_rows", "overview_rows", "variant_rows"):
        seen = set()
        for row in sheet[list_name]:
            if row["document_id"] not in docs:
                _fail("measurement_document_reference_missing")
            identity = (row["document_id"], row["native_row_ordinal"], row["entity"]["family_kind"])
            if identity in seen:
                _fail("duplicate_measurement_row")
            seen.add(identity)
            native = docs[row["document_id"]]
            table_name = {"pathway_rows": "pathway", "pathway_ec_rows": "ecnumber", "subsystem_rows": "subsystems",
                          "variant_rows": "variant_matrix", "overview_rows": "overview"}.get(list_name, row["entity"]["family_kind"])
            source_numbers = []
            source_row = None
            if table_name == "overview":
                pointers = {location["json_pointer"] for location in row["source_locations"]}
                source_numbers = [n for n in native["reported_numbers"] if n["location"]["table"] == "overview"
                                  and n["location"]["json_pointer"].rsplit("/", 1)[0] in pointers]
            else:
                tables = [table for table in native["tables"] if table["table"] == table_name]
                if len(tables) != 1 or row["native_row_ordinal"] >= len(tables[0]["rows"]):
                    _fail("measurement_row_reference_missing")
                source_row = tables[0]["rows"][row["native_row_ordinal"]]
                source_numbers = source_row["numeric_fields"]
                fields = dict(zip(tables[0]["headers"][-1] if tables[0]["headers"] else [], source_row["tokens"]))
                entity = row["entity"]
                field_pairs = {"family_rows": [("family_id", "family_id")], "pathway_rows": [("pathway_id", "pathway_id")],
                    "pathway_ec_rows": [("pathway_id", "pathway_id"), ("ec_number", "ec_number")],
                    "subsystem_rows": [("subsystem_id", "subsystem_id"), ("superclass_native", "superclass"),
                                       ("class_name", "class"), ("subclass", "subclass"), ("subsystem_name", "subsystem_name")],
                    "variant_rows": [("superclass_native", "Superclass"), ("class_name", "Class"),
                                     ("subclass", "Subclass"), ("subsystem_name", "SS")]}.get(list_name, [])
                for entity_field, native_field in field_pairs:
                    if entity[entity_field] is not None and entity[entity_field] != fields.get(native_field):
                        _fail("measurement_entity_mismatch")
                if entity["superclass_native"] is not None and entity["superclass_aggregation"] != entity["superclass_native"].upper():
                    _fail("measurement_hierarchy_mismatch")
            numbers = {n["native_field"]: n for n in source_numbers if n["native_field"] != "genomes"}
            for name, cell in row.items():
                if name not in _NATIVE_FIELDS and name != "reported_feature_token_count":
                    continue
                native_field = _NATIVE_FIELDS.get(name, "gene_counts" if table_name == "subsystems" else "gene_count")
                number = numbers.get(native_field)
                if number is not None:
                    if any(cell[key] != number["cell"][key] for key in ("state", "value", "unit", "origin", "method_id", "input_refs", "uncertainty")):
                        _fail("measurement_native_value_mismatch")
                    if not set(number["cell"]["qualification_codes"]) <= set(cell["qualification_codes"]):
                        _fail("measurement_qualification_missing")
                    required_codes = {d["code"] for d in native["diagnostics"] if d["code"] in {
                        "native_first_object_discard", "native_query_completeness_unknown", "producer_version_unverified",
                        "artifact_truncated", "reference_release_unknown"}}
                    if not required_codes <= set(cell["qualification_codes"]):
                        _fail("measurement_qualification_missing")
                elif cell["state"] == "available":
                    _fail("measurement_native_field_missing")
                population_id = cell["population_id"]
                if population_id is not None:
                    assignment = assignments.get(population_id)
                    if assignment is None or assignment["kind"] != "native_view_represented_genomes":
                        _fail("measurement_population_mismatch")
                    if views[assignment["view_id"]]["document_id"] != row["document_id"]:
                        _fail("measurement_population_mismatch")
            if list_name == "family_rows":
                if row["entity"]["kind"] != "family" or row["entity"]["family_kind"] not in ("plfam", "pgfam"):
                    _fail("family_entity_invalid")
                for ordinal, count in enumerate(row["genome_counts"]):
                    if count["genome_ordinal"] != ordinal:
                        _fail("family_genome_ordinal_mismatch")
                    cell = count["reported_occurrences"]
                    if cell["state"] == "available" and (cell["value"] > 255 or (cell["value"] > 0) != (count["presence_state"] == "recorded_positive")):
                        _fail("family_count_presence_mismatch")
                    decoded = [number for number in source_numbers if number["native_field"] == "genomes"]
                    if ordinal < len(decoded) and any(cell[key] != decoded[ordinal]["cell"][key] for key in ("state", "value", "unit", "method_id")):
                        _fail("family_decoded_count_mismatch")
                list_count = row["positive_genome_count_from_list"]
                if list_count["state"] == "available" and list_count["value"] != len(set(row["positive_genome_ids"])):
                    _fail("family_membership_count_mismatch")
    for join in sheet["join_results"]:
        if join["left_view_id"] not in views or join["right_view_id"] not in views:
            _fail("join_view_reference_missing")
    for item in _walk(sheet):
        if set(item) == {"state", "value", "unit", "origin", "population_id", "method_id", "input_refs", "uncertainty", "qualification_codes"}:
            _cell(item)
            if item["population_id"] is not None and item["population_id"] not in populations and item["population_id"] not in references:
                _fail("cell_population_reference_missing")
        if set(item) == {"source_ref", "raw_artifact_ref", "document_id", "json_pointer", "table", "row_ordinal", "column_ordinal", "native_field"}:
            _location(item, docs)
        if set(item) == {"kind", "owner_id", "pointer"}:
            if item["kind"] == "native":
                if item["owner_id"] not in docs:
                    _fail("native_reference_owner_missing")
                _native_pointer(docs[item["owner_id"]], item["pointer"])
            elif item["kind"] == "sheet":
                if item["owner_id"] != sheet["analysis_id"]:
                    _fail("sheet_reference_owner_mismatch")
                _resolve(sheet, item["pointer"])
            elif item["kind"] == "supplied":
                if item["owner_id"] not in record_sets and item["owner_id"] not in references:
                    _fail("supplied_reference_owner_missing")
                _resolve(record_sets.get(item["owner_id"], references.get(item["owner_id"])), item["pointer"])
            else:
                _fail("sheet_component_reference_invalid")
    return sheet
