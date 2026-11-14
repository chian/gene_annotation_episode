"""Populate a GenomeComparison sheet from supplied projections and explicit joins.

This B3 boundary copies native measurements; B4 calculates their components.
It never parses source bytes, selects protein/input links, reads artifacts, or
authenticates a run. The caller selects the primary source and supplies B2's
NativeJoins *value*. Execution and occurrence witness locators remain unqualified
under correction002, so executed denominators and complete membership stay
unavailable. Full directional reports are a separate unfinished interface.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
import json

from jsonschema import Draft202012Validator, validators

from .bvbrc_proteome_data_contracts import ProteomeDataError, validate_proteome_data
from .bvbrc_proteome_native_contracts import (
    COMPARISON_FIELDS, REFERENCE_FIELDS, NativeValidationError,
    validate_native_projection,
)
from .bvbrc_proteome_sheet_contracts import (
    proteome_sheet_schema, validate_proteome_sheet_data,
)


_SCOPE = ("track_key", "reference_row_ordinal", "association_key", "protein_key",
          "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")
_JOIN_REASON = {"not_supplied": "row_join_missing", "unmatched": "row_join_missing",
                "ambiguous": "row_join_ambiguous", "conflicting": "row_join_conflict"}
_TYPES = Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda checker, value: type(value) is int,
    "number": lambda checker, value: type(value) in (int, float),
    "array": lambda checker, value: type(value) is list,
    "object": lambda checker, value: type(value) is dict,
})
_Validator = validators.extend(Draft202012Validator, type_checker=_TYPES)


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _unique(values):
    result, seen = [], set()
    for value in values:
        key = _key(value)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(value))
    return result


def _scope(**values):
    return {key: values.get(key) for key in _SCOPE}


def _diagnostic(code, path="", *, scope=None, fields=(), severity="qualification"):
    return {"code": code, "severity": severity, "path": path,
            "scope": _scope() if scope is None else deepcopy(scope),
            "source_fields": _unique(fields)}


def _requirement(code, required_input, *, scope=None, fields=()):
    return {"code": code, "required_input": required_input,
            "scope": _scope() if scope is None else deepcopy(scope),
            "source_fields": _unique(fields)}


def _cell(value=None, *, state="missing_input", reasons=(), fields=()):
    return {"state": state, "value": value, "reason_codes": list(dict.fromkeys(reasons)),
            "source_fields": _unique(fields)}


def _invalid(code, path):
    return validate_proteome_sheet_data("NativeSheetResult", {
        "status": "invalid", "value": None,
        "requirements": [_requirement(code, "valid_saved_sheet")],
        "diagnostics": [_diagnostic(code, path, severity="error")],
    })


@lru_cache(maxsize=None)
def _shape_validator(name):
    # Use the public frozen package schema, never a caller's rule document.
    schema = proteome_sheet_schema("NativeSheet")
    schema["$ref"] = "#/$defs/" + name
    return _Validator(schema)


def _shape(name, value, path):
    error = next(_shape_validator(name).iter_errors(value), None)
    if error is not None:
        suffix = "".join("/" + str(p).replace("~", "~0").replace("/", "~1")
                         for p in error.absolute_path)
        raise ProteomeDataError("supplied_contract_invalid", path + suffix)


def _require(condition, path):
    if not condition:
        raise ProteomeDataError("supplied_contract_invalid", path)


def _layout_uncertain(projection, row):
    if projection["format"] != "genome_comparison_tsv_v1":
        return False
    ordinal = row.get("reference_row_ordinal", row.get("row_ordinal"))
    ref = projection["reference_rows"][ordinal]
    return any(d["code"] == "native_table_width_invalid"
               for r in (ref, row) for d in r["diagnostics"])


def _comparison(link, projections, path):
    """Compare only the supplied one-to-one correspondence, without selecting it."""
    diagnostics, conflicts = [], []
    left = projections.get(link["left_source_ref"])
    right = projections.get(link["right_source_ref"])
    _require(link["left_source_ref"] != link["right_source_ref"], path)
    for field, names in (("reference_pairs", ("left_row_ordinal", "right_row_ordinal")),
                         ("association_pairs", ("left_association_key", "right_association_key"))):
        for name in names:
            values = [pair[name] for pair in link[field]]
            _require(len(values) == len(set(values)), path + "/" + field)

    def unbound(where, scope=None):
        diagnostics.append(_diagnostic("representation_correspondence_missing", where,
                                       scope=scope))

    if left is None or right is None:
        unbound(path)
        return {"link": deepcopy(link), "state": "unbound", "conflict_source_fields": [],
                "diagnostics": diagnostics}
    unavailable = False
    ref_map = {p["left_row_ordinal"]: p["right_row_ordinal"] for p in link["reference_pairs"]}

    def compare(a, b, fields):
        nonlocal unavailable
        if _layout_uncertain(left, a) or _layout_uncertain(right, b):
            unavailable = True
            return
        for name in fields:
            ac, bc = a[name], b[name]
            if ac["presence"] == bc["presence"] == "value":
                equal = (Decimal(ac["lexeme"]) == Decimal(bc["lexeme"])
                         if "lexeme" in ac else ac["value"] == bc["value"])
                if not equal:
                    conflicts.extend([ac["source_field"], bc["source_field"]])
            elif "value" in (ac["presence"], bc["presence"]) or "invalid" in (ac["presence"], bc["presence"]):
                unavailable = True

    for i, pair in enumerate(link["reference_pairs"]):
        a, b = pair["left_row_ordinal"], pair["right_row_ordinal"]
        if a >= len(left["reference_rows"]) or b >= len(right["reference_rows"]):
            unbound(f"{path}/reference_pairs/{i}", _scope(track_key="ref_genome", reference_row_ordinal=a))
        else:
            compare(left["reference_rows"][a], right["reference_rows"][b], REFERENCE_FIELDS)
    lm = {r["association_key"]: r for r in left["associations"]}
    rm = {r["association_key"]: r for r in right["associations"]}
    for i, pair in enumerate(link["association_pairs"]):
        a, b = lm.get(pair["left_association_key"]), rm.get(pair["right_association_key"])
        if (a is None or b is None or a["track_key"] != b["track_key"] or
                ref_map.get(a["reference_row_ordinal"]) != b["reference_row_ordinal"]):
            scope = (_scope(association_key=pair["left_association_key"]) if a is None else
                     _scope(track_key=a["track_key"], reference_row_ordinal=a["reference_row_ordinal"],
                            association_key=a["association_key"]))
            unbound(f"{path}/association_pairs/{i}", scope)
        else:
            compare(a, b, COMPARISON_FIELDS)
    if conflicts:
        # Usable explicit pairs retain their measured disagreement even when a
        # separate pair is unbound. Never replace that pair with an inferred one.
        state = "conflicting"
        diagnostics.append(_diagnostic("representation_conflict", path, fields=conflicts))
    elif diagnostics:
        state = "unbound"
    else:
        complete = (bool(link["reference_pairs"] or link["association_pairs"]) and not unavailable and
                    {t["track_key"] for t in left["tracks"]} == {t["track_key"] for t in right["tracks"]} and
                    len(ref_map) == len(left["reference_rows"]) == len(right["reference_rows"]) and
                    len(link["association_pairs"]) == len(lm) == len(rm) and
                    left["projection_completeness"] == right["projection_completeness"] == "complete_document")
        state = "equal_observed_cells" if complete else "incomplete_comparison"
        if not complete:
            diagnostics.append(_diagnostic("representation_correspondence_missing", path))
    diagnostics.append(_diagnostic("alternate_representation_not_independent", path))
    return {"link": deepcopy(link), "state": state, "conflict_source_fields": _unique(conflicts),
            "diagnostics": diagnostics}


def _symbol_count(protein, state, inventories, path):
    if protein is None:
        return _cell(state={"ambiguous": "ambiguous", "conflicting": "conflicting"}.get(state, "missing_input"),
                     reasons=[_JOIN_REASON[state]])
    inventory = inventories.get(protein["inventory_key"])
    _require(inventory is not None and protein["record_ordinal"] < len(inventory["records"]), path)
    record = inventory["records"][protein["record_ordinal"]]
    if not record["record_complete"]:
        return _cell(state="truncated", reasons=["fasta_record_incomplete"], fields=[record["source_field"]])
    # Complete invalid/empty text still has an actual symbol count. This is not
    # an amino-acid length, sequence-validity claim or executed denominator.
    return _cell(record["sequence_symbol_count"], state="value", fields=[record["source_field"]])


def _row_diagnostics(native, scope, *, uncertain=False):
    result = []
    if uncertain:
        result.append(_diagnostic("native_table_layout_uncertain", native["native_pointer"], scope=scope))
    for name, cell in native.items():
        if type(cell) is not dict or "presence" not in cell:
            continue
        if cell["presence"] == "invalid":
            result.append(_diagnostic("native_invalid_cell", cell["source_field"]["pointer"], scope=scope,
                                      fields=[cell["source_field"]], severity="error"))
    if native["patric_id"]["presence"] != "value":
        result.append(_diagnostic("native_identifier_unavailable", native["native_pointer"], scope=scope,
                                  fields=[native["patric_id"]["source_field"]]))
    if "hit" in native and native["hit"]["presence"] == "value" and native["hit"]["value"] not in {"bi (<->)", "uni (->)"}:
        result.append(_diagnostic("native_category_invalid", native["native_pointer"], scope=scope,
                                  fields=[native["hit"]["source_field"]]))
    return result


def _coordinate_kind(protein, input_entry, metadata_indices, metadata, features, native):
    if protein is None or input_entry is None:
        return "unknown"
    if input_entry["kind"] == "user_genome":
        return "artificial_layout"
    # A later/partial assignment cannot by itself identify coordinate semantics.
    # Require the supplied feature's known convention and agreeing actual cells.
    known = []
    for index in metadata_indices:
        feature_ref = metadata[index]["feature"]
        snapshot = features.get(feature_ref["snapshot_key"])
        if snapshot is None or feature_ref["row_ordinal"] >= len(snapshot["records"]):
            continue  # The shared saved-data validator rejects the bad binding.
        feature = snapshot["records"][feature_ref["row_ordinal"]]
        convention = snapshot["coordinate_convention"]["value"]
        if convention == "unknown" or any(native[k]["presence"] != "value" or
                feature[k]["presence"] != "value" or native[k]["value"] != feature[k]["value"]
                for k in ("start", "end", "strand")):
            return "unknown"
        known.append(convention)
    return "genomic_metadata" if known and len(set(known)) == 1 else "unknown"


def build_native_sheet(native_results: list[dict], *, primary_source_ref: str,
                       input_index: dict | None, inventories: list[dict],
                       feature_snapshots: list[dict], genome_snapshots: list[dict],
                       sequence_snapshots: list[dict], joins: dict | None,
                       representation_links: list[dict],
                       directional_attachment: dict | None = None) -> dict:
    """Return NativeSheetResult, retaining all supplied inputs and native cells.

    Invalid saved contracts return fixed diagnostics. Well-shaped unresolved
    correspondence stays local. The output and every nested object are detached
    from caller data. No best-file choice, implicit mapping or scientific score
    calculation occurs here.
    """
    try:
        _require(type(primary_source_ref) is str and bool(primary_source_ref), "/primary_source_ref")
        _require(type(native_results) is list, "/native_results")
        projections = {}
        for i, result in enumerate(native_results):
            path = f"/native_results/{i}"
            _shape("NativeProjectionResult", result, path)
            _require((result["status"] == "invalid") == (result["value"] is None), path)
            _require(result["status"] != "ok" or not any(d["severity"] == "error" for d in result["diagnostics"]), path)
            if result["value"] is not None:
                validate_native_projection(result["value"])
                ref = result["value"]["source"]["content"]["source_ref"]
                _require(ref not in projections, path)
                projections[ref] = result["value"]
        _require(primary_source_ref in projections, "/primary_source_ref")
        primary = projections[primary_source_ref]
        _require(primary["projection_completeness"] != "invalid_document", "/primary_source_ref")
        if input_index is not None:
            validate_proteome_data("InputIndex", input_index)
        maps = []
        for field, name, values in (("inventories", "ProteinInventory", inventories),
                                   ("feature_snapshots", "FeatureSnapshot", feature_snapshots),
                                   ("genome_snapshots", "GenomeSnapshot", genome_snapshots),
                                   ("sequence_snapshots", "FeatureSequenceSnapshot", sequence_snapshots)):
            _require(type(values) is list, "/" + field)
            identity = "inventory_key" if field == "inventories" else "snapshot_key"
            mapping = {}
            for i, value in enumerate(values):
                validate_proteome_data(name, value)
                _require(value[identity] not in mapping, f"/{field}/{i}")
                mapping[value[identity]] = value
            maps.append(mapping)
        if joins is not None:
            validate_proteome_sheet_data("NativeJoins", joins)
        _require(type(representation_links) is list, "/representation_links")
        seen = set()
        comparisons = []
        for i, link in enumerate(representation_links):
            path = f"/representation_links/{i}"
            _shape("RepresentationLink", link, path)
            pair = frozenset((link["left_source_ref"], link["right_source_ref"]))
            _require(pair not in seen, path)
            seen.add(pair)
            comparisons.append(_comparison(link, projections, path))
        if directional_attachment is not None:
            _shape("DirectionalAttachment", directional_attachment, "/directional_attachment")
            _require(directional_attachment["state"] == "unavailable" and
                     not directional_attachment["reports"] and not directional_attachment["operand_links"],
                     "/directional_attachment")
    except (ProteomeDataError, NativeValidationError) as error:
        return _invalid("supplied_contract_invalid", error.path)
    except RecursionError:
        return _invalid("supplied_contract_invalid", "")

    requirements, diagnostics = [], []
    inputs = {} if input_index is None else {i["expected_track_key"]: i for i in input_index["inputs"]}
    bindings = {} if joins is None else {b["track_key"]: b for b in joins["track_bindings"]}
    ref_joins = {} if joins is None else {j["native"]["reference_row_ordinal"]: j for j in joins["reference_joins"]}
    sub_joins = {} if joins is None else {j["native"]["association_key"]: j for j in joins["subject_joins"]}
    metadata = [] if joins is None else joins["metadata_joins"]
    metadata_indices = defaultdict(list)
    for position, join in enumerate(metadata):
        if join["state"] == "joined":
            metadata_indices[_key(join["protein"])].append(position)
    tracks = []
    native_tracks = {t["track_key"]: t for t in primary["tracks"]}
    for key in dict.fromkeys([*native_tracks, *inputs]):
        native, entry, binding = native_tracks.get(key), inputs.get(key), bindings.get(key)
        scope = _scope(track_key=key)
        count = (deepcopy(binding["input_record_count"]) if binding is not None else
                 _cell(reasons=["exact_executed_input_missing", "execution_witness_interface_unavailable"]))
        track_diagnostics = deepcopy(binding["diagnostics"]) if binding is not None else []
        track_diagnostics.append(_diagnostic("execution_witness_interface_unavailable", scope=scope))
        materialization = native["materialization"] if native else "not_in_projection"
        if materialization in {"unknown", "not_in_projection"}:
            code = "track_materialization_unknown" if native else "track_missing_from_projection"
            track_diagnostics.append(_diagnostic(code, scope=scope))
            requirements.append(_requirement(code, "producer_execution_facts", scope=scope))
        requirements.append(_requirement("execution_witness_interface_unavailable", "execution_input_witness", scope=scope))
        tracks.append({"track_key": key, "comparison_ordinal": None if key == "ref_genome" else int(key.removeprefix("comp_genome_")),
                       "original_input_key": entry["input_key"] if entry else None,
                       "native_materialization": materialization,
                       "native_source_fields": deepcopy(native["source_fields"]) if native else [],
                       "inventory_key": binding["inventory_key"] if binding else None, "input_record_count": count,
                       "complete_reference_row_membership": "unknown",
                       "complete_published_association_membership": "unknown", "diagnostics": track_diagnostics})
        diagnostics.extend(track_diagnostics)

    def operand(join, scope):
        protein, state = (None, "not_supplied") if join is None else (join["protein"], join["state"])
        local = [] if join is None else deepcopy(join["diagnostics"])
        if state != "joined":
            code = _JOIN_REASON[state]
            local.append(_diagnostic(code, scope=scope))
            requirements.append(_requirement(code, "occurrence_mapping", scope=scope))
        return deepcopy(protein), state, local

    references, associations = [], []
    try:
        for native in primary["reference_rows"]:
            ordinal = native["row_ordinal"]
            scope = _scope(track_key="ref_genome", reference_row_ordinal=ordinal)
            protein, state, local = operand(ref_joins.get(ordinal), scope)
            indices = metadata_indices.get(_key(protein), [])
            local.extend(_row_diagnostics(native, scope, uncertain=_layout_uncertain(primary, native)))
            row = {"reference_row_ordinal": ordinal, "reference_row_key": native["reference_row_key"],
                   "protein": protein, "join_state": state,
                   "inventory_sequence_symbol_count": _symbol_count(protein, state, maps[0], f"/reference_rows/{ordinal}"),
                   "coordinate_kind": _coordinate_kind(protein, inputs.get("ref_genome"), indices, metadata, maps[1], native),
                   "metadata_links": list(indices), "diagnostics": _unique(local)}
            for target, source in (("native_aa_length", "aa_length"), ("native_start", "start"),
                                   ("native_end", "end"), ("native_strand", "strand")):
                row[target] = deepcopy(native[source])
            if row["inventory_sequence_symbol_count"]["state"] == "truncated":
                requirements.append(_requirement("fasta_record_incomplete", "complete_bytes", scope=scope,
                                                 fields=row["inventory_sequence_symbol_count"]["source_fields"]))
            references.append(row)
            diagnostics.extend(local)
        for native in primary["associations"]:
            ordinal, key = native["reference_row_ordinal"], native["association_key"]
            scope = _scope(track_key=native["track_key"], reference_row_ordinal=ordinal, association_key=key)
            protein, state, local = operand(sub_joins.get(key), scope)
            ref = references[ordinal]
            uncertain = _layout_uncertain(primary, native)
            local.extend(_row_diagnostics(native, scope, uncertain=uncertain))
            row = {"association_key": key, "reference_row_ordinal": ordinal, "track_key": native["track_key"],
                   "reference_protein": deepcopy(ref["protein"]), "reference_join_state": ref["join_state"],
                   "subject_protein": protein, "subject_join_state": state,
                   "inventory_subject_sequence_symbol_count": _symbol_count(protein, state, maps[0], "/association_rows/" + str(len(associations))),
                   "layout_state": "uncertain_table_layout" if uncertain else "source_field_located",
                   "native_subject_identifier_present": native["patric_id"]["presence"] == "value",
                   "metadata_links": list(metadata_indices.get(_key(protein), [])), "diagnostics": _unique(local)}
            for target, source in (("native_hit_category", "hit"), ("native_subject_length_aa", "aa_length"),
                                   ("native_first_hsp_alignment_identity_fraction", "percent_identity"),
                                   ("native_subject_endpoint_difference_fraction", "seq_coverage")):
                row[target] = deepcopy(native[source])
            if row["inventory_subject_sequence_symbol_count"]["state"] == "truncated":
                requirements.append(_requirement("fasta_record_incomplete", "complete_bytes", scope=scope,
                                                 fields=row["inventory_subject_sequence_symbol_count"]["source_fields"]))
            associations.append(row)
            diagnostics.extend(local)
    except ProteomeDataError as error:
        return _invalid("sheet_relationship_invalid", error.path)

    if input_index is None:
        requirements.append(_requirement("input_arrays_unavailable", "original_parameters"))
    for value in ([input_index] if input_index is not None else []) + inventories + feature_snapshots + genome_snapshots + sequence_snapshots + ([joins] if joins is not None else []):
        diagnostics.extend(value["diagnostics"])
    for i, result in enumerate(native_results):
        projection = result["value"]
        if projection is None or projection["projection_completeness"] == "invalid_document":
            # An unusable projection does not establish a truncated transfer.
            # Its original A envelope retains the specific parser failure.
            diagnostics.append(_diagnostic("projection_incomplete", f"/native_results/{i}"))
            requirements.append(_requirement("projection_incomplete", "producer_execution_facts"))
        elif not projection["source"]["body_complete"] or projection["source"]["object_complete"] != "yes":
            diagnostics.append(_diagnostic("projection_incomplete", f"/native_results/{i}"))
            requirements.append(_requirement("projection_incomplete", "complete_bytes"))
        if projection is not None:
            ref = projection["source"]["content"]["source_ref"]
            linked = any({c["link"]["left_source_ref"], c["link"]["right_source_ref"]} ==
                         {primary_source_ref, ref} for c in comparisons)
            if ref != primary_source_ref and not linked:
                # Keep the separate projection; no invented relation or mapping
                # is needed merely to name the missing correspondence.
                diagnostics.append(_diagnostic("representation_correspondence_missing", f"/native_results/{i}"))
                requirements.append(_requirement("representation_correspondence_missing", "representation_correspondence"))
    if primary["source_contract"]["deployment_match"] == "unobserved":
        diagnostics.append(_diagnostic("producer_format_unverified", "/source_contract"))
        requirements.append(_requirement("producer_format_unverified", "producer_execution_facts"))
    for comparison in comparisons:
        diagnostics.extend(comparison["diagnostics"])
        if comparison["state"] != "equal_observed_cells":
            code = "representation_conflict" if comparison["state"] == "conflicting" else "representation_correspondence_missing"
            requirements.append(_requirement(code, "representation_correspondence", fields=comparison["conflict_source_fields"]))
    if directional_attachment is not None:
        requirements.extend(directional_attachment["requirements"])
        diagnostics.extend(directional_attachment["diagnostics"])
    requirements.append(_requirement("full_reports_not_retained", "directional_report"))
    for code in ("full_reports_not_retained", "legacy_first_hsp_only", "legacy_rounded_fraction",
                 "legacy_subject_endpoint_difference", "legacy_zero_fallback_possible",
                 "native_category_not_orthology_probability", "reported_rows_not_input_population"):
        diagnostics.append(_diagnostic(code))
    sheet = {"version": "bvbrc_proteome_native_sheet_proposal_v1", "scientific_mode": "proteome_comparison",
             "primary_source_ref": primary_source_ref, "native_results": deepcopy(native_results),
             "input_index": deepcopy(input_index), "inventories": deepcopy(inventories),
             "feature_snapshots": deepcopy(feature_snapshots), "genome_snapshots": deepcopy(genome_snapshots),
             "sequence_snapshots": deepcopy(sequence_snapshots), "joins": deepcopy(joins),
             "representation_comparisons": comparisons, "tracks": tracks,
             "reference_rows": references, "association_rows": associations,
             "directional_attachment": deepcopy(directional_attachment),
             "requirements": _unique(requirements), "diagnostics": _unique(diagnostics)}
    result = {"status": "partial", "value": sheet,
              "requirements": deepcopy(sheet["requirements"]), "diagnostics": deepcopy(sheet["diagnostics"])}
    try:
        # This is the cross-input boundary: validation checks the supplied B2
        # handoff against the retained A/B1 records, without constructing joins.
        return validate_proteome_sheet_data("NativeSheetResult", result)
    except ProteomeDataError as error:
        return _invalid("sheet_relationship_invalid", error.path)


__all__ = ["build_native_sheet"]
