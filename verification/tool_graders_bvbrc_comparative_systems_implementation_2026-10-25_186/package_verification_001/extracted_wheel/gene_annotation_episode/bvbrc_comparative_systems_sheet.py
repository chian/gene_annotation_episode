"""Populate ComparativeSystems numerical sheets from explicit saved inputs.

The builder copies native measurements and retains associations/populations. It
does not acquire data, repair source losses or run the separate scientific
component calculators. Population IDs are exclusively caller assignments.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from .bvbrc_comparative_systems_handoff_contracts import canonical_sha256, validate_shape
from .bvbrc_comparative_systems_native import _cell, _diagnostic, _known_producer, _location, _pointer
from .bvbrc_comparative_systems_sheet_contracts import validate_native_document, validate_sheet

__all__ = ("build_comparative_systems_sheet",)

_IDS = ("record_id", "genome_id", "feature_id", "patric_id", "pathway_id", "ec_number",
        "subsystem_id", "role_id", "plfam_id", "pgfam_id", "accession", "sequence_id")
_ENTITY_FIELDS = ("family_kind", "genome_id", "family_id", "pathway_id", "ec_number", "subsystem_id",
                  "role_id", "superclass_native", "superclass_aggregation", "class_name", "subclass",
                  "subsystem_name", "comparison_id")
_SUMMARY_FIELDS = {
    "plfam": {"reported_feature_occurrences": "feature_count", "reported_genome_count": "genome_count",
              "reported_length_min": "aa_length_min", "reported_length_max": "aa_length_max",
              "reported_length_mean": "aa_length_mean", "reported_length_population_sd": "aa_length_std"},
    "pathway": {"reported_genome_count": "genome_count", "reported_ec_token_count": "ec_count",
                "reported_feature_token_count": "gene_count", "reported_genome_ec_count": "genome_ec",
                "reported_ec_conservation_percent": "ec_conservation", "reported_gene_conservation": "gene_conservation"},
    "ecnumber": {"reported_genome_count": "genome_count", "reported_ec_token_count": "ec_count",
                 "reported_feature_token_count": "gene_count", "reported_genome_ec_count": "genome_ec"},
    "subsystems": {"reported_role_token_count": "role_counts", "reported_feature_token_count": "gene_counts",
                   "reported_genome_count": "genome_count", "reported_gene_conservation": "gene_conservation",
                   "reported_role_conservation_percent": "role_conservation", "reported_record_genome_fraction": "prop_active"},
    "variant_matrix": {"reported_active_occurrences": "active", "reported_likely_occurrences": "likely",
                       "reported_inactive_placeholder": "inactive", "reported_missing_genome_count": "missing_genomes"},
}
_SUMMARY_FIELDS["pgfam"] = _SUMMARY_FIELDS["plfam"]
_SHEET_LIST = {"plfam": "family_rows", "pgfam": "family_rows", "pathway": "pathway_rows",
               "ecnumber": "pathway_ec_rows", "subsystems": "subsystem_rows", "variant_matrix": "variant_rows"}
_UNITS = {"reported_feature_occurrences": "occurrence", "reported_genome_count": "genome",
          "reported_length_min": "amino_acid", "reported_length_max": "amino_acid", "reported_length_mean": "amino_acid",
          "reported_length_population_sd": "amino_acid", "reported_ec_token_count": "ec_token",
          "reported_feature_token_count": "feature_token", "reported_genome_ec_count": "genome_ec_pair",
          "reported_ec_conservation_percent": "percent", "reported_role_token_count": "role_token",
          "reported_role_conservation_percent": "percent", "reported_record_genome_fraction": "fraction",
          "reported_active_occurrences": "occurrence", "reported_likely_occurrences": "occurrence",
          "reported_inactive_placeholder": "occurrence", "reported_missing_genome_count": "genome"}


def _entity(kind, **values):
    return {"kind": kind, **{key: values.get(key) for key in _ENTITY_FIELDS}}


def _valid_id(value):
    return (type(value) is str and bool(value.strip()) and value == value.strip()
            and value.lower() not in {"nan", "none", "null"}
            and not any(ord(char) < 32 for char in value))


def _metadata(native):
    return {item["location"]["json_pointer"]: item["value"] for item in native["metadata"]}


def _codes(native):
    return list(dict.fromkeys(d["code"] for d in native["diagnostics"] if d["code"] in {
        "native_first_object_discard", "producer_version_unverified", "native_query_completeness_unknown",
        "artifact_truncated", "reference_release_unknown"}))


def _fields(document, table, row):
    header = table["headers"][-1] if table["headers"] else []
    return [{"name": header[i] if i < len(header) else "", "raw_text": token,
             "location": _location(document, table["table"], row["row_ordinal"], i,
                                   header[i] if i < len(header) else "", table["json_pointer"])}
            for i, token in enumerate(row["tokens"])]


def _row_values(table, row):
    if row["status"] == "invalid":
        return {}
    return dict(zip(table["headers"][-1] if table["headers"] else [], row["tokens"]))


def _association(native, table, row, evidence):
    document = native["document"]
    fields = _fields(document, table, row)
    values = _row_values(table, row)
    ids = {key: values.get("id" if key == "record_id" else key) for key in _IDS}
    ids = {key: value if _valid_id(value) else None for key, value in ids.items()}
    codes = list(row["qualification_codes"])
    required = ["genome_id", "feature_id"]
    family = "pathway" if "pathway" in document["format_profile"] else "subsystem"
    required += ["pathway_id", "ec_number"] if family == "pathway" else ["subsystem_id", "role_id"]
    if any(ids[key] is None for key in required):
        codes.append("native_identifier_placeholder")
    active = values.get("active")
    if active is not None and active not in {"active", "likely", "inactive"}:
        codes.append("native_identifier_placeholder")
    if "start" in values or "end" in values:
        convention = ("one_based_inclusive" if table["table"] == "genes" and _known_producer(document, evidence)
                      else "unknown")
    else:
        convention = "not_applicable"
    return {"association_id": document["document_id"] + ":" + table["table"] + ":" + str(row["row_ordinal"]),
            "document_id": document["document_id"], "record_set_id": None, "table": table["table"],
            "row_ordinal": row["row_ordinal"], "identifiers": ids,
            "active_category": active if active in {"active", "likely", "inactive"} else None,
            "fields": fields, "identity_status": "partial" if codes else "valid",
            "coordinate_convention": convention, "qualification_codes": list(dict.fromkeys(codes))}


def _missing_cell(unit, population_id=None, code="missing_required_field", *, state="missing"):
    return _cell(None, unit, state=state, origin="unavailable", method="unavailable",
                 population_id=population_id, codes=[code])


def _summary(native, table, row, population_id):
    document = native["document"]
    name = table["table"]
    values = _row_values(table, row)
    codes = list(dict.fromkeys(_codes(native) + row["qualification_codes"]))
    if name in ("plfam", "pgfam"):
        entity = _entity("family", family_kind=name, family_id=values.get("family_id"))
    elif name in ("pathway", "ecnumber"):
        entity = _entity("pathway" if name == "pathway" else "pathway_ec", pathway_id=values.get("pathway_id"),
                         ec_number=values.get("ec_number") if name == "ecnumber" else None)
    else:
        superclass = values.get("superclass")
        entity = _entity("subsystem", subsystem_id=values.get("subsystem_id"), superclass_native=superclass,
                         superclass_aggregation=superclass.upper() if superclass is not None else None,
                         class_name=values.get("class"), subclass=values.get("subclass"), subsystem_name=values.get("subsystem_name"))
        if name == "variant_matrix":
            # These pinned source fields do not contain a subsystem ID.
            valid = len(row["tokens"]) >= 4 and row["status"] != "invalid"
            tokens = row["tokens"]
            entity = _entity("variant", superclass_native=tokens[0] if valid else None,
                             superclass_aggregation=tokens[0].upper() if valid else None,
                             class_name=tokens[1] if valid else None, subclass=tokens[2] if valid else None,
                             subsystem_name=tokens[3] if valid else None)
    identity_fields = ("family_id",) if name in ("plfam", "pgfam") else (("pathway_id", "ec_number") if name == "ecnumber"
                      else (("pathway_id",) if name == "pathway" else (("subsystem_id",) if name == "subsystems" else ())))
    for field in identity_fields:
        if not _valid_id(entity[field]):
            entity[field] = None
            codes = list(dict.fromkeys(codes + ["native_identifier_placeholder"]))
    out = {"document_id": document["document_id"], "native_row_ordinal": row["row_ordinal"],
           "entity": entity, "source_locations": [_location(document, name, row["row_ordinal"], pointer=table["json_pointer"])],
           "qualification_codes": codes}
    by_name = {number["native_field"]: number for number in row["numeric_fields"] if number["native_field"] != "genomes"}
    for field, source_field in _SUMMARY_FIELDS[name].items():
        if source_field in by_name:
            cell = deepcopy(by_name[source_field]["cell"])
            cell["population_id"] = population_id
            cell["qualification_codes"] = list(dict.fromkeys(cell["qualification_codes"] + _codes(native)))
        else:
            unit = _UNITS.get(field, "feature_per_role_genome" if name == "subsystems" else "feature_per_ec_genome")
            cell = _missing_cell(unit, population_id)
        out[field] = cell
    if name in ("plfam", "pgfam"):
        meta = _metadata(native)
        ids = meta.get("/genome_ids")
        lists = meta.get("/" + name + "_genomes")
        positive = lists.get(values.get("family_id")) if type(lists) is dict else None
        list_valid = type(positive) is list and all(_valid_id(g) for g in positive)
        out["positive_genome_ids"] = deepcopy(positive) if list_valid else []
        list_codes = []
        if list_valid and len(positive) != len(set(positive)):
            list_codes.append("duplicate_identical_representation")
        if list_valid and type(ids) is list and not set(positive) <= {g for g in ids if type(g) is str}:
            list_codes.append("population_incompatible")
        out["positive_genome_count_from_list"] = (
            _cell(len(set(positive)), "genome", origin="derived_retained_records", method="distinct_valid_members",
                  population_id=population_id, codes=list_codes,
                  refs=[{"kind": "native", "owner_id": document["document_id"], "pointer": "/" + name + "_genomes/" + _pointer(values.get("family_id"))}])
            if list_valid else _missing_cell("genome", population_id))
        out["raw_hex_counts"] = values.get("genomes", "")
        decoded = [number for number in row["numeric_fields"] if number["native_field"] == "genomes"]
        out["genome_counts"] = []
        if type(ids) is list and all(_valid_id(g) for g in ids):
            for ordinal, genome_id in enumerate(ids):
                number = decoded[ordinal] if ordinal < len(decoded) else None
                cell = deepcopy(number["cell"]) if number else _missing_cell("occurrence", population_id, "identity_conflict", state="incompatible")
                cell["population_id"] = population_id
                cell["qualification_codes"] = list(dict.fromkeys(cell["qualification_codes"] + _codes(native)))
                state = ("recorded_positive" if cell["value"] > 0 else "no_record_completeness_unknown") if cell["state"] == "available" else "incompatible"
                out["genome_counts"].append({"genome_id": genome_id, "genome_ordinal": ordinal,
                    "reported_occurrences": cell, "presence_state": state,
                    "source_locations": [deepcopy(number["location"])] if number else []})
    if name == "variant_matrix":
        out.update(raw_tokens=deepcopy(row["tokens"]), header_field_count=len(table["headers"][-1]) if table["headers"] else 0,
                   data_field_count=len(row["tokens"]))
    return out


def _matching(row, entity):
    ids = row["identifiers"]
    for key in ("genome_id", "pathway_id", "ec_number", "subsystem_id", "role_id"):
        if entity[key] is not None and ids[key] != entity[key]:
            return False
    fields = {item["name"]: item["raw_text"] for item in row["fields"]}
    for entity_key, field in (("superclass_aggregation", "superclass"), ("class_name", "class"),
                              ("subclass", "subclass"), ("subsystem_name", "subsystem_name")):
        if entity[entity_key] is not None:
            value = fields.get(field)
            if entity_key == "superclass_aggregation" and value is not None:
                value = value.upper()
            if entity[entity_key] != value:
                return False
    if entity["family_id"] is not None:
        if entity["family_kind"] not in ("plfam", "pgfam") or ids[entity["family_kind"] + "_id"] != entity["family_id"]:
            return False
    return True


def _population(assignment, native_by_id, views, associations, original_request, analysis_id):
    kind, population_id = assignment["kind"], assignment["population_id"]
    members, unresolved, locations, refs, codes, missing_members = [], [], [], [], [], []
    member_kind, unit, raw_count = "genome_id", "genome", None
    state, completeness, relationship = "available", "complete_for_declared_population", "not_applicable"
    if kind == "requested_direct_genomes":
        members = deepcopy(original_request["genome_ids"])
        raw_count = len(members)
        refs = [{"kind": "sheet", "owner_id": analysis_id, "pointer": "/original_request/genome_ids"}]
        if original_request["genome_groups"]:
            codes.append("group_membership_unknown")
    elif kind == "executed_genomes":
        ids = original_request["executed_genome_ids"]
        if ids is None or not original_request["executed_population_evidence"]:
            state, completeness = "missing", "unknown"
            codes.append("group_membership_unknown" if original_request["genome_groups"] else "missing_required_field")
        else:
            members, raw_count = deepcopy(ids), len(ids)
            locations = deepcopy(original_request["executed_population_evidence"])
            refs = [{"kind": "sheet", "owner_id": analysis_id, "pointer": "/original_request/executed_genome_ids"}]
            relationship = "original_execution_snapshot"
    else:
        view = views[assignment["view_id"]]
        native = native_by_id.get(view["document_id"])
        table = next((t for t in native["tables"] if t["table"] == view["table"]), None) if native else None
        if native is None or (table is None and view["table"] != "overview") or native["status"] in ("invalid", "failed"):
            state, completeness = ("failed" if native and native["status"] == "failed" else "missing"), "unknown"
            codes.append("missing_document_selection" if native is None else "missing_required_field")
        else:
            codes = _codes(native)
            document = native["document"]
            refs = [{"kind": "native", "owner_id": document["document_id"], "pointer": table["json_pointer"] if table else "/overview"}]
            rows = [row for row in associations if row["document_id"] == view["document_id"] and row["table"] == view["table"]]
            if kind == "native_view_represented_genomes":
                ids = _metadata(native).get("/genome_ids")
                if ids is not None:
                    if type(ids) is list:
                        members = [g for g in ids if _valid_id(g)]
                        unresolved = [str(g) for g in ids if not _valid_id(g)]
                        raw_count = len(ids)
                    else:
                        state, completeness = "incompatible", "incompatible"
                        codes.append("population_incompatible")
                    locations = [_location(document, pointer="/genome_ids")]
                    refs = [{"kind": "native", "owner_id": document["document_id"], "pointer": "/genome_ids"}]
                elif rows or table and view["table"] in ("pathways_tsv", "subsystems_tsv", "genes"):
                    members = [row["identifiers"]["genome_id"] for row in rows if row["identifiers"]["genome_id"] is not None]
                    unresolved = [row["association_id"] for row in rows if row["identifiers"]["genome_id"] is None]
                    raw_count = len(rows)
                    locations = [_location(document, view["table"], row["row_ordinal"], pointer=table["json_pointer"]) for row in rows]
                else:
                    state, completeness = "missing", "unknown"
                    codes.append("missing_required_field")
            elif kind == "native_retained_records":
                member_kind, unit = "record_id", "record"
                raw_count = len(table["rows"]) if table else None
                if rows:
                    members = [row["identifiers"]["record_id"] for row in rows if row["identifiers"]["record_id"] is not None]
                    unresolved = [row["association_id"] for row in rows if row["identifiers"]["record_id"] is None]
                elif table:
                    members = [document["document_id"] + ":" + table["table"] + ":" + str(row["row_ordinal"])
                               for row in table["rows"] if row["status"] != "invalid"]
                    unresolved = [str(row["row_ordinal"]) for row in table["rows"] if row["status"] == "invalid"]
                locations = [_location(document, view["table"], pointer=table["json_pointer"])] if table else []
            else:
                member_kind = assignment["component_kind"]
                unit = {"ec_number": "ec_token", "role_id": "role_token", "family_id": "family"}[member_kind]
                entity = assignment["entity"]
                if not rows and table and view["table"] not in ("pathways_tsv", "subsystems_tsv", "genes"):
                    state, completeness = "incompatible", "incompatible"
                    codes.append("population_incompatible")
                selected = [row for row in rows if _matching(row, entity)]
                source_key = (entity["family_kind"] + "_id" if entity["family_kind"] in ("plfam", "pgfam") else None) if member_kind == "family_id" else member_kind
                if source_key is None:
                    state, completeness = "incompatible", "incompatible"
                    codes.append("population_incompatible")
                else:
                    members = [row["identifiers"][source_key] for row in selected if row["identifiers"][source_key] is not None]
                    unresolved = [row["association_id"] for row in selected if row["identifiers"][source_key] is None]
                    raw_count = len(selected)
                locations = [_location(document, view["table"], row["row_ordinal"], pointer=table["json_pointer"]) for row in selected]
                # A malformed row may have lost the very identity used by this selection.
                if any(row["identity_status"] != "valid" and not row["identifiers"].get("pathway_id" if member_kind == "ec_number" else "subsystem_id") for row in rows):
                    codes.append("population_incomplete")
                    completeness = "partial"
            if any(row["identity_status"] == "conflicting" for row in rows):
                codes.append("duplicate_record_conflict")
                completeness = "incompatible"
            if document["object_complete"] != "complete" or document["transfer_body_complete"] != "complete":
                completeness = "partial"
            if unresolved:
                codes.append("native_identifier_placeholder")
                completeness = "partial"
            executed = original_request["executed_genome_ids"]
            if kind == "native_view_represented_genomes" and executed is not None and original_request["executed_population_evidence"]:
                # This population is the represented view, not the original
                # executed union. Other original genomes remain in that separate
                # population; they are not missing members of the returned set.
                if not set(members) <= set(executed):
                    codes.append("population_incompatible")
                    completeness = "incompatible"
    codes = list(dict.fromkeys(codes))
    if raw_count is None and state == "available":
        state, completeness = "missing", "unknown"
    raw_cell = _cell(raw_count, unit, state=state, method="record_occurrences", origin="derived_retained_records",
                     population_id=population_id, refs=refs, codes=codes)
    distinct_cell = _cell(len(set(members)), unit, state=state, method="distinct_valid_members", origin="derived_retained_records",
                          population_id=population_id, refs=refs, codes=codes)
    return {"population_id": population_id, "kind": kind, "member_kind": member_kind, "members": list(dict.fromkeys(members)),
            "source_locations": locations, "raw_occurrence_count": raw_cell, "distinct_valid_member_count": distinct_cell,
            "completeness": completeness, "missing_members": missing_members, "unresolved_members": unresolved,
            "relationship_to_original_task": relationship, "qualification_codes": codes}


def _duplicates_and_conflicts(sheet):
    documents = defaultdict(list)
    for native in sheet["native_documents"]:
        document = native["document"]
        documents[(document["format_profile"], document["sha256"])].append(document)
    for rows in documents.values():
        if len(rows) > 1:
            sheet["duplicate_groups"].append({"group_id": "same-bytes:" + rows[0]["sha256"], "kind": "dependent_view",
                "members": [{"kind": "native", "owner_id": document["document_id"], "pointer": ""} for document in rows],
                "native_unique_key": None, "affected_field_ids": []})
    groups = defaultdict(list)
    for i, row in enumerate(sheet["association_rows"]):
        native_key = row["identifiers"]["record_id"]
        if native_key and row["document_id"] is not None:
            groups[(row["document_id"], row["table"], native_key)].append((i, row))
    for (document_id, table, native_key), rows in groups.items():
        if len(rows) < 2:
            continue
        payloads = {canonical_sha256([[field["name"], field["raw_text"]] for field in row["fields"]]) for _, row in rows}
        conflict = len(payloads) > 1 and table != "genes"
        code = "duplicate_record_conflict" if conflict else ("inner_join_many_to_many" if len(payloads) > 1 else "duplicate_identical_representation")
        sheet["duplicate_groups"].append({"group_id": "duplicate:" + document_id + ":" + table + ":" + native_key,
            "kind": "conflicting_record" if conflict else ("dependent_view" if len(payloads) > 1 else "identical_record"),
            "members": [{"kind": "sheet", "owner_id": sheet["analysis_id"], "pointer": f"/association_rows/{i}"} for i, _ in rows],
            "native_unique_key": native_key, "affected_field_ids": []})
        for _, row in rows:
            if conflict:
                row["identity_status"] = "conflicting"
            if code not in row["qualification_codes"]:
                row["qualification_codes"].append(code)
    contexts, ids, categories = defaultdict(set), defaultdict(set), defaultdict(list)
    for row in sheet["association_rows"]:
        if row["document_id"] is None or row["identifiers"]["subsystem_id"] is None:
            continue
        fields = {f["name"]: f["raw_text"] for f in row["fields"]}
        context = (fields.get("superclass", "").upper(), fields.get("class"), fields.get("subclass"), fields.get("subsystem_name"))
        scope = (row["document_id"], row["table"])
        contexts[(scope, context)].add(row["identifiers"]["subsystem_id"])
        ids[(scope, row["identifiers"]["subsystem_id"])].add(context)
        categories[(scope, row["identifiers"]["subsystem_id"], row["identifiers"]["genome_id"])].append(row)
    for row in sheet["association_rows"]:
        if row["document_id"] is None or row["identifiers"]["subsystem_id"] is None:
            continue
        fields = {f["name"]: f["raw_text"] for f in row["fields"]}
        context = (fields.get("superclass", "").upper(), fields.get("class"), fields.get("subclass"), fields.get("subsystem_name"))
        scope = (row["document_id"], row["table"])
        if len(contexts[(scope, context)]) > 1 or len(ids[(scope, row["identifiers"]["subsystem_id"])]) > 1:
            row["identity_status"] = "conflicting"
            row["qualification_codes"] = list(dict.fromkeys(row["qualification_codes"] + ["identity_conflict"]))
    for rows in categories.values():
        if len({row["active_category"] for row in rows if row["active_category"] is not None}) > 1:
            for row in rows:
                if "conflicting_native_categories" not in row["qualification_codes"]:
                    row["qualification_codes"].append("conflicting_native_categories")


def _overview(native, population_id):
    value = _metadata(native).get("/overview")
    numbers = {number["location"]["json_pointer"]: number for number in native["reported_numbers"]
               if number["location"]["table"] == "overview"}
    rows = []

    def visit(node, path, labels):
        if type(node) is not dict:
            return
        if labels:
            row = {"document_id": native["document"]["document_id"], "native_row_ordinal": len(rows),
                   "entity": _entity("overview", superclass_native=labels[0], superclass_aggregation=labels[0].upper(),
                                     class_name=labels[1] if len(labels) > 1 else None, subclass=labels[2] if len(labels) > 2 else None),
                   "source_locations": [_location(native["document"], "overview", pointer=path)],
                   "qualification_codes": _codes(native), "level": ("superclass", "class", "subclass")[len(labels) - 1]}
            for field, source, unit in (("reported_subsystem_name_count", "subsystem_name_counts", "subsystem_name"),
                                         ("reported_feature_count", "gene_counts", "feature_token")):
                number = numbers.get(path + "/" + source)
                row[field] = deepcopy(number["cell"]) if number else _missing_cell(unit, population_id)
                row[field]["population_id"] = population_id
                row[field]["qualification_codes"] = list(dict.fromkeys(row[field]["qualification_codes"] + _codes(native)))
            rows.append(row)
        if len(labels) < 3:
            for name, child in node.items():
                if name not in ("subsystem_name_counts", "gene_counts"):
                    visit(child, path + "/" + _pointer(name), labels + [name])

    visit(value, "/overview", [])
    return rows


def _joins(sheet, views):
    for pair in sheet["document_selection"]["dependent_views"]:
        left, right = views[pair["left_view_id"]], views[pair["right_view_id"]]
        sheet["duplicate_groups"].append({"group_id": "dependent:" + pair["left_view_id"] + ":" + pair["right_view_id"],
            "kind": "dependent_view", "members": [{"kind": "native", "owner_id": view["document_id"],
                "pointer": next((table["json_pointer"] for native in sheet["native_documents"] if native["document"]["document_id"] == view["document_id"]
                                 for table in native["tables"] if table["table"] == view["table"]), "")} for view in (left, right)
                if any(native["document"]["document_id"] == view["document_id"] for native in sheet["native_documents"])],
            "native_unique_key": None, "affected_field_ids": []})
        # This is a retained-table correspondence, not a reconstruction of the
        # unretained original feature-side input to the producer's inner join.
        if {left["table"], right["table"]} not in ({"pathways_tsv", "genes"}, {"subsystems_tsv", "genes"}):
            continue
        keys = ["genome_id", "patric_id" if "pathways_tsv" in (left["table"], right["table"]) else "feature_id"]
        selected = []
        for view in (left, right):
            selected.append([(i, row) for i, row in enumerate(sheet["association_rows"])
                             if row["document_id"] == view["document_id"] and row["table"] == view["table"]])
        maps = []
        for rows in selected:
            mapping = defaultdict(list)
            for index, row in rows:
                key = tuple(row["identifiers"][k] for k in keys)
                if None not in key:
                    mapping[key].append(index)
            maps.append(mapping)
        common = set(maps[0]) & set(maps[1])
        many_left, many_right = any(len(maps[0][k]) > 1 for k in common), any(len(maps[1][k]) > 1 for k in common)
        multiplicity = "many_to_many" if many_left and many_right else ("many_to_one" if many_left else ("one_to_many" if many_right else "one_to_one"))
        matched = [{i for k in common for i in mapping[k]} for mapping in maps]
        refs = [[{"kind": "sheet", "owner_id": sheet["analysis_id"], "pointer": f"/association_rows/{i}"}
                 for i, _ in rows if i not in matched[n]] for n, rows in enumerate(selected)]
        codes = (["inner_join_missing"] if any(refs) else []) + (["inner_join_many_to_many"] if multiplicity == "many_to_many" else [])
        sheet["join_results"].append({"join_id": "retained-correspondence:" + pair["left_view_id"] + ":" + pair["right_view_id"],
            "left_view_id": pair["left_view_id"], "right_view_id": pair["right_view_id"], "keys": keys, "join_kind": "inner",
            "left_occurrence_count": _cell(len(selected[0]), "record", origin="derived_retained_records", method="record_occurrences"),
            "right_occurrence_count": _cell(len(selected[1]), "record", origin="derived_retained_records", method="record_occurrences"),
            "output_occurrence_count": _cell(sum(len(maps[0][k]) * len(maps[1][k]) for k in common), "record", origin="derived_retained_records", method="record_occurrences"),
            "unmatched_left_refs": refs[0], "unmatched_right_refs": refs[1], "multiplicity": multiplicity,
            "qualification_codes": codes})


def build_comparative_systems_sheet(documents: tuple[dict, ...], *, analysis_id: str,
        original_request: dict, producer_evidence: tuple[dict, ...], document_selection: dict,
        population_assignments: dict, supplied_record_sets: dict | None,
        reference_memberships: tuple[dict, ...]) -> dict:
    """Populate an immutable numerical sheet, preserving every selected source."""
    if type(analysis_id) is not str or not analysis_id:
        raise ValueError("comparative_systems_analysis_id_required")
    original = validate_shape("OriginalRequestV1", original_request)
    selection = validate_shape("DocumentSelectionV1", document_selection)
    assignments = validate_shape("PopulationAssignmentsV1", population_assignments)
    evidence = [validate_shape("ProducerEvidenceV1", item) for item in producer_evidence]
    supplied = validate_shape("SuppliedRecordSetsV1", supplied_record_sets) if supplied_record_sets is not None else None
    references = [validate_shape("ReferenceMembershipV1", item) for item in reference_memberships]
    natives = [validate_native_document(item) for item in documents]
    # Validate explicit references before extraction; missing selected artifacts
    # remain requirements, while duplicate/conflicting selections fail the call.
    for rows, key in ((evidence, "evidence_id"), (selection["documents"], "document_id"),
                      (selection["authoritative_views"], "view_id"), (assignments["assignments"], "population_id")):
        if len({row[key] for row in rows}) != len(rows):
            raise ValueError("comparative_systems_duplicate_selection_id")
    native_by_id = {item["document"]["document_id"]: item for item in natives}
    if len(native_by_id) != len(natives):
        raise ValueError("comparative_systems_duplicate_native_document")
    views = {item["view_id"]: item for item in selection["authoritative_views"]}
    selected_ids = {item["document_id"] for item in selection["documents"]}
    if any(view["document_id"] not in selected_ids for view in views.values()):
        raise ValueError("comparative_systems_view_document_reference_missing")
    for assignment in assignments["assignments"]:
        kind = assignment["kind"]
        if kind in ("requested_direct_genomes", "executed_genomes"):
            invalid = any(assignment[key] is not None for key in ("view_id", "entity", "component_kind"))
        else:
            invalid = assignment["view_id"] not in views
            if kind == "selected_component_membership":
                invalid |= assignment["entity"] is None or assignment["component_kind"] is None
            else:
                invalid |= assignment["entity"] is not None or assignment["component_kind"] is not None
        if invalid:
            raise ValueError("comparative_systems_population_assignment_selector_invalid")
    sheet = {"version": "bvbrc_comparative_systems_sheet_v1", "analysis_id": analysis_id,
             "original_request": original, "source_documents": [deepcopy(item["document"]) for item in natives],
             "producer_evidence": evidence, "populations": [], "document_selection": selection,
             "population_assignments": assignments, "native_documents": natives,
             **{key: [] for key in ("family_rows", "pathway_rows", "pathway_ec_rows", "subsystem_rows", "association_rows", "overview_rows", "variant_rows")},
             "supplied_record_sets": supplied, "reference_memberships": references, "duplicate_groups": [], "join_results": [],
             "requirements": [], "diagnostics": [deepcopy(d) for native in natives for d in native["diagnostics"]]}
    for item in selection["documents"]:
        if item["document_id"] not in native_by_id:
            sheet["requirements"].append({"requirement_id": "native-document:" + item["document_id"], "code": "missing_document_selection",
                "required_input_role": item["role"], "document_id": item["document_id"], "affected_field_ids": [], "source_refs": []})
    for native in natives:
        for table in native["tables"]:
            if table["table"] in ("genes", "pathways_tsv", "subsystems_tsv"):
                sheet["association_rows"].extend(_association(native, table, row, evidence) for row in table["rows"])
    if supplied:
        sheet["requirements"].extend(deepcopy(supplied["requirements"]))
        sheet["diagnostics"].extend(deepcopy(supplied["diagnostics"]))
        for record_set in supplied["record_sets"]:
            sheet["association_rows"].extend(deepcopy(row["association"]) for row in record_set["rows"]
                                             if row["association"] is not None)
    _duplicates_and_conflicts(sheet)
    sheet["populations"] = [_population(item, native_by_id, views, sheet["association_rows"], original, analysis_id)
                            for item in assignments["assignments"]]
    if supplied:
        populations = {item["population_id"]: item for item in sheet["populations"]}
        additions = [item["declared_genome_population"] for item in supplied["selection"]["record_sets"]]
        additions += [item["population"] for item in supplied["record_sets"]]
        native_ids = set(populations)
        for population in additions:
            pid = population["population_id"]
            if pid in native_ids or pid in populations and populations[pid] != population:
                raise ValueError("comparative_systems_population_id_collision")
            if pid not in populations:
                sheet["populations"].append(deepcopy(population))
                populations[pid] = population

    def population_for(document_id, table_name):
        exact, compatible = set(), set()
        for assignment in assignments["assignments"]:
            if assignment["kind"] != "native_view_represented_genomes":
                continue
            view = views[assignment["view_id"]]
            if view["document_id"] == document_id:
                compatible.add(assignment["population_id"])
                if view["table"] == table_name:
                    exact.add(assignment["population_id"])
        choices = exact if exact else compatible
        return next(iter(choices)) if len(choices) == 1 else None

    for native in natives:
        document_id = native["document"]["document_id"]
        for table in native["tables"]:
            if table["table"] in _SHEET_LIST:
                sheet[_SHEET_LIST[table["table"]]].extend(_summary(native, table, row, population_for(document_id, table["table"]))
                                                        for row in table["rows"])
        if "/overview" in _metadata(native):
            sheet["overview_rows"].extend(_overview(native, population_for(document_id, "overview")))
    for row in sheet["subsystem_rows"]:
        entity = row["entity"]
        context = tuple(entity[key] for key in ("superclass_aggregation", "class_name", "subclass", "subsystem_name"))
        conflicts = []
        for association in sheet["association_rows"]:
            if association["document_id"] is None or association["identifiers"]["subsystem_id"] is None:
                continue
            fields = {field["name"]: field["raw_text"] for field in association["fields"]}
            other = (fields.get("superclass", "").upper(), fields.get("class"), fields.get("subclass"), fields.get("subsystem_name"))
            same_id = association["identifiers"]["subsystem_id"] == entity["subsystem_id"]
            if (other == context and not same_id) or (same_id and all(value is not None for value in other) and other != context):
                conflicts.append(association)
        if conflicts:
            row["qualification_codes"] = list(dict.fromkeys(row["qualification_codes"] + ["identity_conflict"]))
            sheet["diagnostics"].append(_diagnostic(native_by_id[row["document_id"]]["document"], "identity_conflict",
                phase="association", row=row["native_row_ordinal"], locations=row["source_locations"]))
    for list_name in ("family_rows", "pathway_rows", "pathway_ec_rows", "subsystem_rows"):
        logical_rows = defaultdict(list)
        for i, row in enumerate(sheet[list_name]):
            logical_rows[(row["document_id"], canonical_sha256(row["entity"]))].append((i, row))
        for rows in logical_rows.values():
            if len(rows) < 2:
                continue
            comparable = []
            for _, row in rows:
                table_name = row["entity"]["family_kind"] if list_name == "family_rows" else {
                    "pathway_rows": "pathway", "pathway_ec_rows": "ecnumber", "subsystem_rows": "subsystems"}[list_name]
                native_table = next(table for table in native_by_id[row["document_id"]]["tables"] if table["table"] == table_name)
                comparable.append(native_table["rows"][row["native_row_ordinal"]]["tokens"])
            identical = len({canonical_sha256(value) for value in comparable}) == 1
            code = "duplicate_identical_representation" if identical else "identity_conflict"
            for _, row in rows:
                row["qualification_codes"] = list(dict.fromkeys(row["qualification_codes"] + [code]))
            sheet["duplicate_groups"].append({"group_id": "summary:" + list_name + ":" + str(rows[0][0]),
                "kind": "identical_record" if identical else "conflicting_record", "native_unique_key": None,
                "members": [{"kind": "sheet", "owner_id": analysis_id, "pointer": f"/{list_name}/{i}"} for i, _ in rows],
                "affected_field_ids": []})
    _joins(sheet, views)
    for reference in references:
        if reference["release"] is None and "reference_release_unknown" not in reference["qualification_codes"]:
            reference["qualification_codes"].append("reference_release_unknown")
    return validate_sheet(sheet)
