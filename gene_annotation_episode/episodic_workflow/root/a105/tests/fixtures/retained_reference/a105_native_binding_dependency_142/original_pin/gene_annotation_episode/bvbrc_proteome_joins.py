"""Construct explicit GenomeComparison operand and metadata relationships.

Only supplied, validated data participate. Identifier correspondence is distinct
from sequence validity and from proof of an executed input. The current contract
has no decoded execution/occurrence witness; source locators cannot replace it.
No acquisition, native parsing, execution, scoring or episode decisions occur.
"""
from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
import json
import re

from .bvbrc_proteome_data_contracts import (
    ProteomeDataError, _Validator, _normalize, _plain, validate_proteome_data,
)
from .bvbrc_proteome_native_contracts import NativeValidationError, validate_native_projection
from .bvbrc_proteome_sheet_contracts import proteome_sheet_schema, validate_proteome_sheet_data


_SCOPE = ("track_key", "reference_row_ordinal", "association_key", "protein_key",
          "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _scope(**fields):
    return {name: fields.get(name) for name in _SCOPE}


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


class _Problems:
    def __init__(self):
        self.diagnostics = []
        self.requirements = []

    def add(self, code, path, scope=None, *, fields=(), required=None, severity="qualification"):
        scope = _scope() if scope is None else scope
        fields = list({_key(field): field for field in fields}.values())
        item = {"code": code, "severity": severity, "path": path,
                "scope": scope, "source_fields": fields}
        self.diagnostics.append(item)
        if required is not None:
            need = {"code": code, "scope": scope, "required_input": required, "source_fields": fields}
            if need not in self.requirements:
                self.requirements.append(need)
        return item


@lru_cache(maxsize=None)
def _link_validator(name):
    schema = proteome_sheet_schema("NativeJoins")
    return _Validator({"$schema": schema["$schema"], "$ref": "#/$defs/" + name,
                       "$defs": schema["$defs"]})


def _links(name, values, path):
    if type(values) is not list:
        raise ProteomeDataError("proteome_join_links_array_required", path)
    _plain(values, path)
    for ordinal, value in enumerate(values):
        error = next(_link_validator(name).iter_errors(value), None)
        if error is not None:
            location = f"{path}/{ordinal}"
            for token in error.absolute_path:
                location = _pointer(location, token)
            raise ProteomeDataError("proteome_join_link_shape_invalid", location)
        # Raw links are assertions, so conflicting source digests are not
        # authoritative bindings. Pointer syntax must nevertheless be valid.
        stack = [(value, f"{path}/{ordinal}")]
        while stack:
            node, location = stack.pop()
            if type(node) is dict:
                if "pointer" in node and re.search(r"~(?![01])", node["pointer"]):
                    raise ProteomeDataError("proteome_join_source_pointer_invalid", location)
                stack.extend((child, _pointer(location, key)) for key, child in node.items())
            elif type(node) is list:
                stack.extend((child, _pointer(location, i)) for i, child in enumerate(node))


def _sources(native, index, groups):
    """A source identity cannot denote two different supplied byte objects."""
    found = {}
    stack = [("/native", native), ("/input_index", index)] + [("/" + name, values) for name, values in groups]
    while stack:
        path, value = stack.pop()
        if type(value) is dict:
            if {"source_ref", "sha256"} <= set(value):
                reference, digest, size = value["source_ref"], value["sha256"], value.get("byte_count")
                old = found.get(reference)
                if old is not None and (old[0] != digest or size is not None and old[1] is not None and old[1] != size):
                    raise ProteomeDataError("proteome_join_source_identity_conflict", path)
                found[reference] = (digest, size if size is not None else old[1] if old is not None else None)
            stack.extend((_pointer(path, key), child) for key, child in value.items())
        elif type(value) is list:
            stack.extend((_pointer(path, i), child) for i, child in enumerate(value))


def _supplied(native, input_index, groups):
    _plain(native, "/native")
    try:
        validate_native_projection(native)
    except NativeValidationError as error:
        raise ProteomeDataError(error.code, "/native" + error.path) from error
    if input_index is not None:
        try:
            validate_proteome_data("InputIndex", input_index)
        except ProteomeDataError as error:
            raise ProteomeDataError(error.code, "/input_index" + error.path) from error
    maps, snapshot_keys = [], set()
    types = ("ProteinInventory", "FeatureSnapshot", "GenomeSnapshot", "FeatureSequenceSnapshot")
    for (name, values), contract in zip(groups, types):
        if type(values) is not list:
            raise ProteomeDataError("proteome_join_inputs_array_required", "/" + name)
        identity = "inventory_key" if name == "inventories" else "snapshot_key"
        mapping = {}
        for ordinal, value in enumerate(values):
            try:
                validate_proteome_data(contract, value)
            except ProteomeDataError as error:
                raise ProteomeDataError(error.code, f"/{name}/{ordinal}" + error.path) from error
            key = value[identity]
            if key in mapping or identity == "snapshot_key" and key in snapshot_keys:
                raise ProteomeDataError("proteome_join_duplicate_input_identity", f"/{name}/{ordinal}")
            mapping[key] = value
            if identity == "snapshot_key":
                snapshot_keys.add(key)
        maps.append(mapping)
    _sources(native, input_index, groups)
    return maps


def _missing(code, fields=()):
    return {"state": "missing_input", "value": None, "reason_codes": [code], "source_fields": list(fields)}


def _identifiers(inventories):
    result = {}
    for key, inventory in inventories.items():
        ids = defaultdict(list)
        for row in inventory["records"]:
            if row["identifier"] is not None:
                ids[row["identifier"]].append({"inventory_key": key, "record_ordinal": row["record_ordinal"]})
        result[key] = ids
    return result


def _track_bindings(index, inventories, links, problems, ids):
    inputs = {} if index is None else {row["input_key"]: row for row in index["inputs"]}
    if index is None:
        problems.add("input_arrays_unavailable", "/input_index", required="original_parameters")
    requested = defaultdict(list)
    for ordinal, link in enumerate(links):
        requested[link["input_key"]].append((ordinal, link))
        if link["input_key"] not in inputs:
            problems.add("input_binding_conflict", f"/execution_links/{ordinal}", required="original_parameters")
    bindings = []
    for key, entry in inputs.items():
        path, scope = f"/track_bindings/{len(bindings)}", _scope(track_key=entry["expected_track_key"])
        diagnostics, inventory_key, relation = [], None, "unknown"
        rows = requested[key]
        reason = "exact_executed_input_missing"
        if rows:
            inventory_keys = {r["inventory_key"] for _, r in rows}
            relations = {r["relation"] for _, r in rows}
            if len(inventory_keys) != 1 or len(relations) != 1:
                reason = "input_binding_conflict"
            else:
                selected = inventories.get(rows[0][1]["inventory_key"])
                if selected is None:
                    reason = "input_binding_conflict"
                elif any(link["executed_fasta"] is not None and
                         any(link["executed_fasta"][field] != selected["source"]["content"][field]
                             for field in ("sha256", "byte_count")) for _, link in rows):
                    reason = "input_binding_conflict"
                else:
                    inventory_key = selected["inventory_key"]
                    relation = rows[0][1]["relation"]
                    if relation == "exact_executed_fasta":
                        relation, reason = "unknown", "execution_witness_interface_unavailable"
                    elif relation == "later_snapshot":
                        diagnostics.append(problems.add("later_snapshot_not_original_input", path, scope))
        diagnostics.append(problems.add(reason, path, scope, fields=[entry["source_field"]],
                                        required="execution_input_witness" if inventory_key is not None else "exact_executed_fasta"))
        bindings.append({"track_key": entry["expected_track_key"], "input_key": key,
                         "inventory_key": inventory_key, "execution_relation": relation,
                         "input_record_count": _missing(reason, [entry["source_field"]]),
                         "membership_complete": "unknown", "identifier_collisions": [],
                         "diagnostics": diagnostics})
    tracks_by_id = defaultdict(set)
    for binding in bindings:
        if binding["inventory_key"] is not None:
            for identifier in ids[binding["inventory_key"]]:
                tracks_by_id[identifier].add(binding["track_key"])
    for ordinal, binding in enumerate(bindings):
        if binding["inventory_key"] is not None:
            binding["identifier_collisions"] = [identifier for identifier in ids[binding["inventory_key"]]
                                                if len(tracks_by_id[identifier]) > 1]
            if binding["identifier_collisions"]:
                binding["diagnostics"].append(problems.add("cross_input_identifier_collision",
                    f"/track_bindings/{ordinal}", _scope(track_key=binding["track_key"]), required="occurrence_mapping"))
    return bindings, tracks_by_id


def _selector(native, row, kind):
    binding = native["source"]["content"]
    return {"source_ref": binding["source_ref"], "sha256": binding["sha256"], "kind": kind,
            "reference_row_ordinal": row["row_ordinal"] if kind == "reference" else row["reference_row_ordinal"],
            "track_key": "ref_genome" if kind == "reference" else row["track_key"],
            "association_key": None if kind == "reference" else row["association_key"]}


def _address(selector):
    return tuple(selector[field] for field in ("kind", "reference_row_ordinal", "track_key", "association_key"))


def _record(ref, inventories):
    inventory = inventories.get(ref["inventory_key"])
    return (inventory["records"][ref["record_ordinal"]]
            if inventory is not None and ref["record_ordinal"] < len(inventory["records"]) else None)


def _operands(native, inventories, bindings, ids, tracks_by_id, links, problems):
    by_track = {binding["track_key"]: binding for binding in bindings}
    requested = defaultdict(list)
    for ordinal, link in enumerate(links):
        requested[_address(link["native"])].append((ordinal, link))
    owned, returned = set(), []
    for kind, values in (("reference", native["reference_rows"]), ("association_subject", native["associations"])):
        joins = []
        for row in values:
            selector = _selector(native, row, kind)
            address = _address(selector)
            owned.add(address)
            requested_rows = requested[address]
            path = f'/{"reference_joins" if kind == "reference" else "subject_joins"}/{len(joins)}'
            scope = _scope(**selector)
            join = {"native": selector, "state": "not_supplied", "protein": None,
                    "candidates": [], "accepted_link_indices": [], "diagnostics": []}

            def failed(state, code, *, required="occurrence_mapping"):
                join["state"] = state
                join["diagnostics"].append(problems.add(code, path, scope, required=required))

            identifier = row["patric_id"]
            binding = by_track.get(selector["track_key"])
            refrow = native["reference_rows"][selector["reference_row_ordinal"]]
            uncertain = native["format"] == "genome_comparison_tsv_v1" and any(
                d["code"] == "native_table_width_invalid" for r in (refrow, row) for d in r["diagnostics"])
            if not requested_rows:
                failed("not_supplied", "row_join_missing")
            elif uncertain or identifier["presence"] != "value":
                failed("unmatched", "native_table_layout_uncertain" if uncertain else "native_identifier_unavailable")
            elif binding is None or binding["inventory_key"] is None:
                failed("not_supplied", "row_join_missing", required="original_parameters" if binding is None else "exact_executed_fasta")
            else:
                name = identifier["value"]
                matches = list(ids[binding["inventory_key"]].get(name, []))
                candidates = list(matches)
                if len(tracks_by_id[name]) > 1:
                    for other in bindings:
                        if other["inventory_key"] is not None:
                            candidates.extend(ids[other["inventory_key"]].get(name, []))
                join["candidates"] = list({_key(ref): ref for ref in candidates}.values())
                supplied = [link for _, link in requested_rows]
                occurrence_claim = any(link["basis"] == "producer_occurrence_mapping" for link in supplied)
                if occurrence_claim:
                    join["diagnostics"].append(problems.add("occurrence_witness_interface_unavailable", path, scope,
                                                            required="occurrence_mapping"))
                if any(link["native"] != selector or link["native_identifier"] != name for link in supplied):
                    failed("conflicting", "identifier_mapping_conflict")
                elif len({_key(link["protein"]) for link in supplied}) > 1:
                    failed("conflicting", "row_join_conflict")
                elif len(matches) > 1 or len(tracks_by_id[name]) > 1:
                    failed("ambiguous", "cross_input_identifier_collision" if len(tracks_by_id[name]) > 1 else "duplicate_identifier")
                elif not matches:
                    failed("unmatched", "identifier_mapping_missing")
                elif supplied[0]["protein"] != matches[0]:
                    failed("conflicting", "identifier_mapping_conflict")
                elif not any(link["basis"] == "unique_exact_identifier" for link in supplied):
                    failed("not_supplied", "occurrence_witness_interface_unavailable")
                else:
                    record = _record(matches[0], inventories)
                    length = row["aa_length"]
                    if (length["presence"] == "value" and record["record_complete"] and record["valid_sequence"] and
                            "*" not in record["sequence"] and length["value"] != record["sequence_symbol_count"]):
                        failed("conflicting", "sequence_length_conflict")
                    else:
                        join.update(state="joined", protein=matches[0], candidates=matches,
                                    accepted_link_indices=[i for i, link in requested_rows if link["basis"] == "unique_exact_identifier"])
            joins.append(join)
        returned.append(joins)
    for address, rows in requested.items():
        if address not in owned:
            for ordinal, _ in rows:
                problems.add("identifier_mapping_conflict", f"/requested_native_links/{ordinal}", required="occurrence_mapping")
    return returned


def _metadata_row(ref, snapshots):
    snapshot = snapshots.get(ref["snapshot_key"])
    return (snapshot["records"][ref["row_ordinal"]]
            if snapshot is not None and ref["row_ordinal"] < len(snapshot["records"]) else None)


def _metadata(inventories, features, genomes, sequences, ids, links, problems):
    feature_ids = {}
    for key, snapshot in features.items():
        index = defaultdict(set)
        for row in snapshot["records"]:
            for field in ("feature_id", "patric_id"):
                if row[field]["presence"] == "value":
                    index[row[field]["value"]].add(row["row_ordinal"])
        feature_ids[key] = index
    joins = []
    for ordinal, link in enumerate(links):
        path = f"/metadata_joins/{ordinal}"
        scope = _scope(protein_key=_key(link["protein"]))
        join = {"link_index": ordinal, "state": "unmatched", "protein": link["protein"],
                "feature": None, "genome": None, "feature_sequence": None, "diagnostics": []}

        def reject(state, code, required):
            join["state"] = state
            join["diagnostics"].append(problems.add(code, path, scope, required=required))

        protein = _record(link["protein"], inventories)
        feature = _metadata_row(link["feature"], features)
        if link["basis"] == "producer_occurrence_mapping":
            reject("unmatched", "occurrence_witness_interface_unavailable", "occurrence_mapping")
        elif protein is None or feature is None or protein["identifier"] is None:
            reject("unmatched", "metadata_join_missing", "feature_metadata")
        else:
            identifier = protein["identifier"]
            matching = feature_ids[link["feature"]["snapshot_key"]].get(identifier, set())
            if feature["row_ordinal"] not in matching:
                reject("conflicting", "metadata_join_conflict", "feature_metadata")
            elif len(matching) != 1 or len(ids[link["protein"]["inventory_key"]][identifier]) != 1:
                reject("ambiguous", "metadata_join_ambiguous", "occurrence_mapping")
            else:
                md5 = feature["aa_sequence_md5"]
                complete_sequence = protein["record_complete"] and protein["valid_sequence"]
                if md5["presence"] == "invalid" or (md5["presence"] == "value" and complete_sequence and
                                                         md5["value"].lower() != protein["sequence_md5"]):
                    reject("conflicting", "sequence_digest_conflict", "feature_sequence")
                else:
                    join.update(state="joined", feature=link["feature"], genome=link["genome"], feature_sequence=link["feature_sequence"])
                if join["state"] == "joined" and link["genome"] is not None:
                    genome = _metadata_row(link["genome"], genomes)
                    if genome is None or any(row["genome_id"]["presence"] != "value" for row in (feature, genome)):
                        reject("unmatched", "metadata_join_missing", "genome_metadata")
                    elif feature["genome_id"]["value"] != genome["genome_id"]["value"]:
                        reject("conflicting", "metadata_join_conflict", "genome_metadata")
                if join["state"] == "joined" and link["feature_sequence"] is not None:
                    sequence = _metadata_row(link["feature_sequence"], sequences)
                    if sequence is None:
                        reject("unmatched", "metadata_join_missing", "feature_sequence")
                    elif (sequence["md5"]["presence"] == "value" and sequence["computed_md5"] is not None and
                          sequence["md5"]["value"].lower() != sequence["computed_md5"]):
                        reject("conflicting", "sequence_digest_conflict", "feature_sequence")
                    elif not sequence["valid"]:
                        reject("unmatched", "metadata_record_invalid", "feature_sequence")
                    elif md5["presence"] != "value":
                        reject("unmatched", "metadata_join_missing", "feature_sequence")
                    elif (md5["value"].lower() != sequence["md5"]["value"].lower() or
                          complete_sequence and (sequence["computed_sha256"] != protein["sequence_sha256"] or
                                                _normalize(sequence["sequence"]["value"]) != protein["sequence"])):
                        reject("conflicting", "sequence_digest_conflict", "feature_sequence")
        if join["state"] != "joined":
            join.update(feature=None, genome=None, feature_sequence=None)
        joins.append(join)
    return joins


def _sequence_groups(inventories):
    groups = {}
    for key, inventory in inventories.items():
        for row in inventory["records"]:
            if row["record_complete"] and row["valid_sequence"] and row["identifier"] is not None:
                group = groups.setdefault(row["sequence"], {"molecule": "aa", "normalization": inventory["normalization"],
                    "sequence_sha256": row["sequence_sha256"], "sequence_symbol_count": row["sequence_symbol_count"], "members": []})
                group["members"].append({"inventory_key": key, "record_ordinal": row["record_ordinal"]})
    return list(groups.values())


def build_native_joins(native: dict, *, input_index: dict | None,
                       inventories: list[dict], feature_snapshots: list[dict],
                       genome_snapshots: list[dict], sequence_snapshots: list[dict],
                       execution_links: list[dict], native_links: list[dict],
                       metadata_links: list[dict]) -> dict:
    """Return NativeJoinsResult while retaining each explicit rejected request.

    Malformed global inputs produce invalid/null; well-shaped wrong links fail
    locally without discarding usable native measurements or neighboring joins.
    Returned dictionaries are detached from all caller inputs.
    """
    problems = _Problems()
    groups = (("inventories", inventories), ("feature_snapshots", feature_snapshots),
              ("genome_snapshots", genome_snapshots), ("sequence_snapshots", sequence_snapshots))
    try:
        maps = _supplied(native, input_index, groups)
        for name, values, path in (("ExecutionInputLink", execution_links, "/execution_links"),
                                  ("NativeProteinLink", native_links, "/requested_native_links"),
                                  ("ProteinMetadataLink", metadata_links, "/requested_metadata_links")):
            _links(name, values, path)
    except (ProteomeDataError, RecursionError) as error:
        problems.add("supplied_contract_invalid", getattr(error, "path", ""), severity="error", required="valid_saved_sheet")
        return validate_proteome_sheet_data("NativeJoinsResult", {"status": "invalid", "value": None,
            "requirements": problems.requirements, "diagnostics": problems.diagnostics})
    inventory_map, features, genomes, sequences = maps
    ids = _identifiers(inventory_map)
    bindings, tracks_by_id = _track_bindings(input_index, inventory_map, execution_links, problems, ids)
    references, subjects = _operands(native, inventory_map, bindings, ids, tracks_by_id, native_links, problems)
    metadata = _metadata(inventory_map, features, genomes, sequences, ids, metadata_links, problems)
    value = {"version": "bvbrc_proteome_joins_proposal_v1", "primary_source_ref": native["source"]["content"]["source_ref"],
             "execution_links": execution_links, "requested_native_links": native_links, "requested_metadata_links": metadata_links,
             "track_bindings": bindings, "reference_joins": references, "subject_joins": subjects,
             "metadata_joins": metadata, "sequence_groups": _sequence_groups(inventory_map), "diagnostics": problems.diagnostics}
    result = {"status": "partial" if problems.diagnostics or problems.requirements else "ok", "value": value,
              "requirements": problems.requirements, "diagnostics": problems.diagnostics}
    # Implementation errors here must remain visible, not become input failures.
    return validate_proteome_sheet_data("NativeJoinsResult", result)


__all__ = ["build_native_joins"]
