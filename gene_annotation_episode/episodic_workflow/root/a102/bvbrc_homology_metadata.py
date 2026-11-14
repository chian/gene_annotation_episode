"""Explicit Homology metadata links and conversion to the shared BLAST sheet.

Only supplied annotations become assignments. Sidecar values remain title
derived source annotations, with overwritten/ambiguous associations excluded.
Neither genome identifiers nor provenance categories generate taxonomy or
quality numbers. Full sequence identities use the exact H1 closed records.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import math

from .bvbrc_homology_inputs import (
    _artifact, _decode_description, _diagnostic, _escape, _index, _json,
    _pointer, _positive, _text, SCHEMA as PARSE_SCHEMA,
)


SCHEMA = "bvbrc_homology_metadata_bindings_v1"


def _empty():
    return {"schema": SCHEMA, "status": "complete", "description_links": [], "records": [],
            "bindings": [], "sequence_identity_bindings": [], "target_context_by_query": [],
            "database_profile": None, "diagnostics": []}


def read_homology_metadata(content: bytes, *, artifact: dict, description_links: list[dict]) -> dict:
    result = _empty()
    result["artifact"] = _artifact(content, artifact, None, "homology_metadata_json")
    result["description_links"] = deepcopy(description_links)
    result["diagnostics"].extend(result["artifact"]["diagnostics"])
    if result["artifact"]["status"] == "invalid" or not isinstance(description_links, list):
        result["status"] = "invalid"
        return result
    try:
        document = _json(content)
        if not isinstance(document, dict):
            raise ValueError("homology_format_shape_mismatch")
    except ValueError as error:
        result["status"] = "invalid"
        result["diagnostics"].append(_diagnostic(str(error), artifact=artifact))
        return result
    result["native_document"] = document
    links_by_key = defaultdict(list)
    for link in result["description_links"]:
        if isinstance(link, dict) and isinstance(link.get("metadata_key"), str):
            links_by_key[link["metadata_key"]].append(link)
    for record_index, (key, native) in enumerate(document.items()):
        pointer = "/" + _escape(key)
        record = {"record_index": record_index, "source_ref": artifact["source_ref"], "pointer": pointer,
            "source_identifier": {"namespace": "bvbrc_homology_rewritten_id", "value": key}, "aliases": [],
            "function_assignments": [], "genome_id": None, "taxid": None, "lineage": [],
            "origin": {"kind": "title_derived_bvbrc_metadata", "native_artifact_ref": artifact["raw_artifact_ref"]},
            "assembly_measurements": {}, "full_sequence_identity": None, "study_groups": [],
            "native": deepcopy(native), "diagnostics": []}
        result["records"].append(record)
        if not isinstance(native, dict) or not key:
            record["diagnostics"].append("homology_metadata_row_invalid")
        else:
            genome_id = native.get("genome_id")
            record["genome_id"] = genome_id if isinstance(genome_id, str) else None
            if genome_id is not None and not isinstance(genome_id, str):
                record["diagnostics"].append("homology_metadata_genome_id_invalid")
            # The source sidecar does not contain an NCBI taxid. Preserve any
            # unexpected field in native; do not promote it to linked taxonomy.
            function = native.get("function")
            if function is not None:
                if _text(function):
                    record["function_assignments"].append({"function": function,
                        "assignment_scope": "source_subject_meaning_unresolved", "source_ref": artifact["source_ref"],
                        "pointer": pointer + "/function", "evidence": []})
                else:
                    record["diagnostics"].append("homology_metadata_function_invalid")
            record["origin"].update({field: deepcopy(native[field]) for field in
                ("genome_name", "locus_tag", "alt_locus_tag") if field in native})
        links = links_by_key.get(key, [])
        for link in links:
            locator = {field: link.get(field) for field in ("report_index", "hit_index", "description_index")}
            code = None
            if len(links) > 1 or link.get("status") == "ambiguous":
                code = "homology_metadata_rewritten_id_collision"
                link["status"] = "ambiguous"
            elif link.get("status") != "validated" or record["diagnostics"]:
                code = "homology_metadata_reference_conflict"
                link["status"] = "invalid"
            elif not _text(link.get("transformation_source_ref")):
                code = "homology_metadata_transformation_source_unavailable"
                link["status"] = "missing"
            elif link.get("metadata_pointer") != pointer:
                code = "homology_metadata_reference_conflict"
                link["status"] = "conflicting"
            elif link.get("raw_description_pointer") is not None:
                description = {"id": link.get("raw_id"), "accession": link.get("raw_accession"), "title": link.get("raw_title")}
                transformed, expected = _decode_description(description)
                if transformed.get("id") != key or expected != native:
                    code = "homology_metadata_reference_conflict"
                    link["status"] = "conflicting"
            if code:
                link.setdefault("diagnostics", []).append(code)
                result["diagnostics"].append(_diagnostic(code, artifact=artifact, locator={**locator, "pointer": pointer}))
            else:
                record["origin"]["original_title"] = link.get("raw_title")
                record["origin"]["transformation_source_ref"] = link["transformation_source_ref"]
                result["bindings"].append({**locator, "record_index": record_index,
                    "linkage_source_ref": artifact["source_ref"], "linkage_pointer": pointer})
    for key, links in links_by_key.items():
        if key not in document:
            for link in links:
                link["status"] = "missing"
                link.setdefault("diagnostics", []).append("homology_metadata_record_missing")
                result["diagnostics"].append(_diagnostic("homology_metadata_record_missing", artifact=artifact,
                    locator={field: link.get(field) for field in ("report_index", "hit_index", "description_index")}))
    if result["diagnostics"] or any(record["diagnostics"] for record in result["records"]):
        result["status"] = "partial"
    return result


def _description(query, link):
    normalized = query.get("normalized_result")
    if not normalized:
        return None
    for hit in normalized["hits"]:
        if hit["hit_index"] == link.get("hit_index"):
            for description in hit["descriptions"]:
                if description["source_locator"].get("description_index") == link.get("description_index"):
                    return description
    return None


def _assembly(record, diagnostics, locator):
    raw = record.get("assembly_measurements")
    if raw in (None, {}):
        return {}
    if not isinstance(raw, dict):
        diagnostics.append(_diagnostic("homology_assembly_measurements_invalid", locator=locator))
        return {}
    assembly = deepcopy(raw)
    units = {"completeness_fraction": "fraction", "contamination_fraction": "fraction",
             "contig_count": "count", "contig_n50": "nt", "total_sequence_length": "nt"}
    declared = raw.get("measurement_units", {})
    methods = raw.get("measurement_methods", {})
    linkage = raw.get("feature_to_genome_link")
    provenance_ok = (isinstance(linkage, dict) and _text(linkage.get("source_ref"))
        and _pointer(linkage.get("pointer")) and linkage.get("genome_id") == record.get("genome_id")
        and linkage.get("feature_identifier") == record.get("source_identifier")
        and _text(raw.get("source")))
    for field, unit in units.items():
        value = raw.get(field)
        if value is None:
            continue
        try:
            valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
        except OverflowError:
            valid = False
        if field == "completeness_fraction":
            valid = valid and value <= 1
        if field in {"contig_count", "contig_n50", "total_sequence_length"}:
            valid = valid and type(value) is int
        valid = (valid and isinstance(declared, dict) and declared.get(field) == unit
                 and isinstance(methods, dict) and _text(methods.get(field)) and provenance_ok)
        if not valid:
            assembly[field] = None
            diagnostics.append(_diagnostic("homology_assembly_measurement_units_or_links_unavailable", locator=locator,
                                           required_input=field + ":units_method_and_feature_to_genome_link"))
    return assembly


def _reference_record(record, *, native, db_type, diagnostics):
    if not isinstance(record, dict):
        return None
    identifier = record.get("source_identifier")
    locator = {"pointer": record.get("pointer")}
    if (not isinstance(identifier, dict) or set(identifier) != {"namespace", "value"}
            or not all(_text(identifier.get(key)) for key in ("namespace", "value"))
            or not _text(record.get("source_ref")) or not _pointer(record.get("pointer"))):
        diagnostics.append(_diagnostic("homology_metadata_record_identity_invalid", locator=locator))
        return None
    functions, excluded = [], []
    assignments = record.get("function_assignments", [])
    if not isinstance(assignments, list):
        diagnostics.append(_diagnostic("homology_metadata_assignments_invalid", locator=locator))
        assignments = []
    for assignment in assignments:
        scope = assignment.get("assignment_scope") if isinstance(assignment, dict) else None
        if native and scope == "source_subject_meaning_unresolved":
            scope = "subject_sequence" if db_type in {"faa", "ffn", "frn"} else "contig_or_unknown_title_scope"
        if (not isinstance(assignment, dict) or not _text(assignment.get("function"))
                or not _text(assignment.get("source_ref")) or not _pointer(assignment.get("pointer"))
                or not isinstance(assignment.get("evidence"), list)):
            excluded.append({"assignment": deepcopy(assignment), "reason": "homology_function_assignment_invalid"})
        elif scope != "subject_sequence":
            excluded.append({"assignment": deepcopy(assignment), "reason": "homology_function_assignment_scope_unsupported"})
        else:
            functions.append({"function": assignment["function"], "source": assignment["source_ref"],
                "native_pointer": assignment["pointer"], "assignment_scope": scope,
                "evidence": deepcopy(assignment["evidence"]), "source_assignment": deepcopy(assignment)})
    taxid = record.get("taxid")
    # Invalid taxa remain invalid inputs to H1, preventing attachment of the
    # record rather than silently stripping their contradictory identity.
    if taxid is not None and not _positive(taxid):
        diagnostics.append(_diagnostic("homology_metadata_taxid_invalid", locator=locator))
    return {"accession": identifier["value"], "identifier_namespace": identifier["namespace"],
        "native_pointer": record["pointer"], "source": record["source_ref"], "taxid": taxid,
        "lineage": deepcopy(record.get("lineage", [])), "functions": functions,
        "origin": deepcopy(record.get("origin", {})), "assembly": _assembly(record, diagnostics, locator),
        "sequence_group": None, "study_groups": deepcopy(record.get("study_groups", [])),
        "genome_id": record.get("genome_id"), "aliases": deepcopy(record.get("aliases", [])),
        "full_sequence_identity": deepcopy(record.get("full_sequence_identity")),
        "excluded_function_assignments": excluded, "native_metadata_record": deepcopy(record)}


def bind_homology_metadata(parsed: dict, *, native_metadata: dict | None, supplied_metadata: dict) -> dict:
    """Produce real per-query H1 operands, retaining original source records.

    Output record indices address the merged collection. ``record_origins``
    explicitly maps each index to the native/supplied original record_index;
    no source identifier or original pointer is rewritten for a BLAST join.
    """
    if not isinstance(parsed, dict) or parsed.get("schema") != PARSE_SCHEMA:
        raise ValueError("homology_parse_required")
    if not isinstance(supplied_metadata, dict) or supplied_metadata.get("schema") != SCHEMA:
        raise ValueError("homology_metadata_bindings_required")
    if native_metadata is not None and (not isinstance(native_metadata, dict) or native_metadata.get("schema") != SCHEMA):
        raise ValueError("homology_native_metadata_bindings_required")
    result = _empty()
    result.update(queries=[], record_origins=[], native_metadata=deepcopy(native_metadata),
                  supplied_metadata=deepcopy(supplied_metadata), unresolved_metadata=[])
    result["description_links"] = [deepcopy(link) for query in parsed["queries"] for link in query["description_links"]]
    if native_metadata is not None:
        result["description_links"] = deepcopy(native_metadata.get("description_links", []))
    native_usable = native_metadata is not None and native_metadata.get("status") != "invalid"
    if native_metadata is not None:
        artifact_row = native_metadata.get("artifact")
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        candidates = [row for row in parsed["binding"].get("artifacts", [])
                      if isinstance(artifact, dict) and row == artifact]
        if (len(candidates) != 1 or artifact.get("role") != "homology_metadata_json"
                or artifact.get("task_association", {}).get("task_id") != parsed["binding"]["original_task"]["task_id"]):
            native_usable = False
            result["diagnostics"].append(_diagnostic("homology_metadata_artifact_binding_conflict"))
    db_type = parsed["binding"]["database_binding"].get("requested_selection", {}).get("db_type")
    metadata_rows, index_maps, valid_records = [], {}, set()
    collections = [("supplied", supplied_metadata), ("native", native_metadata)]
    for origin, collection in collections:
        if collection is None:
            continue
        records = collection.get("records", [])
        if not isinstance(records, list):
            raise ValueError("homology_metadata_records_list_required")
        duplicates = defaultdict(list)
        for position, record in enumerate(records):
            if isinstance(record, dict) and _index(record.get("record_index")):
                duplicates[record["record_index"]].append(position)
        for position, record in enumerate(records):
            original_index = record.get("record_index") if isinstance(record, dict) else None
            index = len(metadata_rows)
            reference = _reference_record(record, native=origin == "native", db_type=db_type,
                                          diagnostics=result["diagnostics"])
            # Keep invalid independent record positions. H1 accepts unavailable
            # rows and leaves them unmatched; valid subsequent indices never shift.
            metadata_rows.append(reference if reference is not None else deepcopy(record))
            retained = deepcopy(record)
            if isinstance(retained, dict):
                retained["record_index"] = index
            result["records"].append(retained)
            result["record_origins"].append({"record_index": index, "collection": origin,
                                            "original_record_index": original_index, "original_position": position})
            if _index(original_index) and len(duplicates[original_index]) == 1 and reference is not None:
                index_maps[(origin, original_index)] = index
                valid_records.add(index)
            else:
                result["unresolved_metadata"].append({"collection": origin, "original_record_index": original_index,
                    "record_index": index, "reason": "homology_metadata_record_index_ambiguous_or_invalid"})
        result["diagnostics"].extend(deepcopy(collection.get("diagnostics", [])))
    queries = {query["report_index"]: query for query in parsed["queries"]}
    query_outputs = {}
    for report_index, query in queries.items():
        output = {"report_index": report_index, "source_locator": deepcopy(query["source_locator"]),
            "reference_metadata": deepcopy(metadata_rows), "description_bindings": [], "sequence_identity_bindings": [],
            "target_context": {}, "database_profile": deepcopy(supplied_metadata.get("database_profile")),
            "unresolved_metadata": [], "diagnostics": []}
        query_outputs[report_index] = output
        result["queries"].append(output)
    for origin, collection in collections:
        if collection is None:
            continue
        bindings = collection.get("bindings", [])
        if not isinstance(bindings, list):
            raise ValueError("homology_metadata_binding_list_required")
        for binding in bindings:
            query = queries.get(binding.get("report_index")) if isinstance(binding, dict) else None
            description = _description(query, binding) if query is not None else None
            index = index_maps.get((origin, binding.get("record_index"))) if isinstance(binding, dict) else None
            invalid = (origin == "native" and not native_usable
                       or not isinstance(binding, dict) or set(binding) != {"report_index", "hit_index", "description_index",
                       "record_index", "linkage_source_ref", "linkage_pointer"}
                       or not all(_index(binding.get(key)) for key in ("report_index", "hit_index", "description_index", "record_index"))
                       or not _text(binding.get("linkage_source_ref")) or not _pointer(binding.get("linkage_pointer"))
                       or description is None or index not in valid_records)
            if origin == "native" and not invalid:
                keys = ("report_index", "hit_index", "description_index")
                old_links = [link for link in collection.get("description_links", []) if isinstance(link, dict)
                             and all(link.get(key) == binding[key] for key in keys)]
                current_links = [link for link in query["description_links"]
                                 if all(link.get(key) == binding[key] for key in keys)]
                compared = ("raw_description_pointer", "raw_id", "raw_accession", "raw_title",
                            "processed_description_pointer", "processed_id", "metadata_key", "metadata_pointer",
                            "transformation_source_ref")
                invalid = (len(old_links) != 1 or len(current_links) != 1
                    or old_links[0].get("status") != "validated" or current_links[0].get("status") != "validated"
                    or any(old_links[0].get(key) != current_links[0].get(key) for key in compared))
            if invalid:
                unresolved = {"collection": origin, "binding": deepcopy(binding), "reason": "homology_metadata_reference_conflict"}
                result["unresolved_metadata"].append(unresolved)
                if query is not None:
                    query_outputs[query["report_index"]]["unresolved_metadata"].append(unresolved)
                result["diagnostics"].append(_diagnostic("homology_metadata_reference_conflict",
                    locator=binding if isinstance(binding, dict) else {}))
                continue
            reference = metadata_rows[index]
            snapshot = {key: description.get(key) for key in ("id", "accession", "title", "taxid")}
            explicit = {"report_index": binding["report_index"], "hit_index": binding["hit_index"],
                "description_index": binding["description_index"], "metadata_index": index,
                "native_description": snapshot, "metadata_identifier": {"namespace": reference["identifier_namespace"],
                    "value": reference["accession"]}, "metadata_source_ref": reference["source"],
                "metadata_pointer": reference["native_pointer"], "linkage_source_ref": binding["linkage_source_ref"],
                "linkage_pointer": binding["linkage_pointer"]}
            query_outputs[binding["report_index"]]["description_bindings"].append(explicit)
            result["bindings"].append({**deepcopy(binding), "record_index": index})
    identities = supplied_metadata.get("sequence_identity_bindings", [])
    if not isinstance(identities, list):
        raise ValueError("homology_sequence_identity_bindings_list_required")
    result["sequence_identity_bindings"] = deepcopy(identities)
    for identity in identities:
        report_index = identity.get("report_index") if isinstance(identity, dict) else None
        if report_index in query_outputs:
            query_outputs[report_index]["sequence_identity_bindings"].append(deepcopy(identity))
        else:
            result["unresolved_metadata"].append({"binding": deepcopy(identity), "reason": "homology_sequence_identity_report_unavailable"})
    targets = supplied_metadata.get("target_context_by_query", [])
    if not isinstance(targets, list):
        raise ValueError("homology_target_context_list_required")
    result["target_context_by_query"] = deepcopy(targets)
    result["database_profile"] = deepcopy(supplied_metadata.get("database_profile"))
    for report_index, output in query_outputs.items():
        matches = [target for target in targets if isinstance(target, dict) and target.get("report_index") == report_index]
        if len(matches) == 1:
            target = deepcopy(matches[0])
            if (not _index(target.get("report_index")) or not _text(target.get("source"))
                    or target.get("taxid") is not None and not _positive(target["taxid"])
                    or not isinstance(target.get("lineage"), list)
                    or target.get("independent_of_search") is not None and type(target["independent_of_search"]) is not bool):
                output["diagnostics"].append(_diagnostic("homology_target_context_invalid", locator={"report_index": report_index}))
            else:
                target.pop("report_index", None)
                output["target_context"] = target
        elif len(matches) > 1:
            output["diagnostics"].append(_diagnostic("homology_target_context_ambiguous", locator={"report_index": report_index}))
        if output["database_profile"] is None:
            output["diagnostics"].append(_diagnostic("homology_database_population_unavailable",
                locator={"report_index": report_index}, severity="qualification", required_input="matching_database_population_profile"))
    if result["diagnostics"] or result["unresolved_metadata"]:
        result["status"] = "partial"
    return result


__all__ = ["read_homology_metadata", "bind_homology_metadata"]
