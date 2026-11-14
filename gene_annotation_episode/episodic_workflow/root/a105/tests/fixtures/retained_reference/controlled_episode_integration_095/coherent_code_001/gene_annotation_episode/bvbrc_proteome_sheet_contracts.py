"""Validate retained GenomeComparison sheets without reconstructing their work.

This boundary checks declared relationships, copied values and stored-array
populations. It does not select joins, parse artifacts or calculate scientific
components. Source custody and numerical formula verification remain separate.
The exact-execution and occurrence-witness interfaces are still unavailable;
locators cannot qualify their scientific claims (review correction 002).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
import json
from pathlib import Path
import re

from .bvbrc_proteome_data_contracts import (
    ProteomeDataError, _plain, _Validator, validate_proteome_data,
)
from .bvbrc_proteome_native_contracts import (
    COMPARISON_FIELDS, REFERENCE_FIELDS, NativeValidationError,
    validate_native_projection,
)


_NAMES = frozenset({"NativeSheet", "NativeSheetResult", "NativeCalculationParameters",
                    "NativeComponents", "NativeComponentsResult", "NativeJoins", "NativeJoinsResult"})
_TRACK = re.compile(r"comp_genome_([1-9][0-9]*)\Z")
_ASSOCIATION = re.compile(r"(comp_genome_[1-9][0-9]*)/row/(0|[1-9][0-9]*)\Z")
_FIELD_KEYS = {"source_ref", "sha256", "pointer", "row_ordinal", "field_name"}
_CELL_KEYS = {"state", "value", "reason_codes", "source_fields"}
_DOCUMENT = json.loads(Path(__file__).with_name("bvbrc_proteome_sheet_schemas.json").read_text(encoding="utf-8"))


def _require(condition, code, path=""):
    if not condition:
        raise ProteomeDataError("proteome_sheet_" + code, path)


def _pointer(path, token):
    return path + "/" + str(token).replace("~", "~0").replace("/", "~1")


def _key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _unique(values, path, code="duplicate_identity"):
    keys = [_key(value) for value in values]
    _require(len(keys) == len(set(keys)), code, path)


@lru_cache(maxsize=None)
def _schema(name):
    _require(type(name) is str and name in _NAMES, "unknown_contract")
    definitions, reachable = _DOCUMENT["$defs"], set()

    def visit(node):
        if type(node) is dict:
            if "$ref" in node:
                target = node["$ref"]
                if not target.startswith("#/$defs/") or target[8:] not in definitions:
                    raise RuntimeError("invalid_packaged_proteome_sheet_reference")
                target = target[8:]
                if target not in reachable:
                    reachable.add(target)
                    visit(definitions[target])
            for child in node.values():
                visit(child)
        elif type(node) is list:
            for child in node:
                visit(child)

    result = {"$schema": _DOCUMENT["$schema"], "$ref": "#/$defs/" + name}
    visit(result)
    result["$defs"] = {key: value for key, value in definitions.items() if key in reachable}
    return result


def proteome_sheet_schema(name: str) -> dict:
    """Return a detached frozen schema for a supported validation entry point."""
    _require(type(name) is str, "unknown_contract")
    return deepcopy(_schema(name))


@lru_cache(maxsize=None)
def _validator(name):
    return _Validator(_schema(name))


def _common(value, path="", bindings=None, *, claims=False):
    """One walk of scalar states and source identities, without native parsing."""
    bindings = {} if bindings is None else bindings
    if type(value) is dict:
        if set(value) == _FIELD_KEYS:
            _require(re.search(r"~(?![01])", value["pointer"]) is None,
                     "source_pointer_invalid", path)
        if not claims and {"source_ref", "sha256"} <= set(value):
            ref, digest = value["source_ref"], value["sha256"]
            _require(ref not in bindings or bindings[ref] == digest,
                     "source_digest_conflict", path)
            bindings[ref] = digest
        if set(value) == _CELL_KEYS:
            _require((value["state"] == "value") == (value["value"] is not None),
                     "cell_state_conflict", path)
            _require(value["state"] == "value" or bool(value["reason_codes"]),
                     "missing_reason", path)
            _unique(value["reason_codes"], path + "/reason_codes")
            _unique(value["source_fields"], path + "/source_fields")
        for key, child in value.items():
            raw_claim = claims or key in {"execution_links", "requested_native_links", "requested_metadata_links", "link"}
            _common(child, _pointer(path, key), bindings, claims=raw_claim)
    elif type(value) is list:
        for index, child in enumerate(value):
            _common(child, _pointer(path, index), bindings, claims=claims)


def _envelope(value, path=""):
    _require((value["status"] == "invalid") == (value["value"] is None),
             "result_state_conflict", path)
    if value["status"] == "ok":
        _require(not any(d["severity"] == "error" for d in value["diagnostics"]),
                 "successful_result_errors", path)


def _validate_part(name, value, path):
    try:
        validate_proteome_data(name, value)
    except ProteomeDataError as error:
        raise ProteomeDataError(error.code, path + error.path) from error


def _parameters(value, path=""):
    keys = value["track_keys"]
    _unique(keys, path + "/track_keys")
    _require(all(_TRACK.fullmatch(key) for key in keys), "comparison_track_required", path + "/track_keys")
    if value["allowed_hit_categories"] is not None:
        _unique(value["allowed_hit_categories"], path + "/allowed_hit_categories")


def _missing_denominator(cell, path):
    _require(cell["state"] not in {"value", "zero_denominator", "not_applicable"},
             "execution_witness_unavailable", path)


def _map(rows, field, path):
    _unique([row[field] for row in rows], path)
    return {row[field]: row for row in rows}


def _protein_key(ref):
    return ref["inventory_key"], ref["record_ordinal"]


def _protein(ref, inventories, path, *, usable=False):
    inventory = inventories.get(ref["inventory_key"])
    _require(inventory is not None and ref["record_ordinal"] < len(inventory["records"]),
             "protein_occurrence_missing", path)
    row = inventory["records"][ref["record_ordinal"]]
    if usable:
        _require(row["record_complete"] and row["valid_sequence"] and row["identifier"] is not None,
                 "protein_occurrence_invalid", path)
    return row


def _metadata(ref, snapshots, path, *, usable=False):
    snapshot = snapshots.get(ref["snapshot_key"])
    _require(snapshot is not None and ref["row_ordinal"] < len(snapshot["records"]),
             "metadata_occurrence_missing", path)
    row = snapshot["records"][ref["row_ordinal"]]
    _require(not usable or row["valid"], "metadata_occurrence_invalid", path)
    return row


def _selector_key(selector):
    return selector["kind"], selector["reference_row_ordinal"], selector["track_key"], selector["association_key"]


def _selector(selector, primary, associations, path):
    binding = primary["source"]["content"]
    _require((selector["source_ref"], selector["sha256"]) == (binding["source_ref"], binding["sha256"]),
             "native_selector_source_conflict", path)
    ordinal = selector["reference_row_ordinal"]
    _require(ordinal < len(primary["reference_rows"]), "native_selector_row_missing", path)
    if selector["kind"] == "reference":
        _require(selector["track_key"] == "ref_genome" and selector["association_key"] is None,
                 "native_selector_identity_conflict", path)
        return primary["reference_rows"][ordinal]
    row = associations.get(selector["association_key"])
    _require(row is not None and row["track_key"] == selector["track_key"] and
             row["reference_row_ordinal"] == ordinal, "native_selector_identity_conflict", path)
    return row


def _layout_uncertain(primary, row):
    if primary["format"] != "genome_comparison_tsv_v1":
        return False
    ref = primary["reference_rows"][row.get("reference_row_ordinal", row.get("row_ordinal"))]
    return any(d["code"] == "native_table_width_invalid" for r in (row, ref) for d in r["diagnostics"])


def _joins_internal(value):
    """Only relationships represented in NativeJoins, without absent inputs.

    NativeSheet additionally checks every admitted link against the retained
    native projection, input index, inventories and metadata snapshots.
    """
    bindings = _map(value["track_bindings"], "track_key", "/track_bindings")
    _unique([b["input_key"] for b in bindings.values()], "/track_bindings")
    execution = defaultdict(list)
    for link in value["execution_links"]:
        execution[link["input_key"]].append(link)
    for binding in bindings.values():
        _require(binding["track_key"] == "ref_genome" or _TRACK.fullmatch(binding["track_key"]), "join_track_identity_conflict", "/track_bindings")
        _missing_denominator(binding["input_record_count"], "/track_bindings/input_record_count")
        _require(binding["execution_relation"] != "exact_executed_fasta", "execution_witness_unavailable", "/track_bindings")
        _require(binding["membership_complete"] != "yes", "execution_membership_unavailable", "/track_bindings")
        if binding["inventory_key"] is None:
            _require(binding["execution_relation"] == "unknown" and binding["membership_complete"] == "unknown", "unbound_execution_claim", "/track_bindings")
        links = execution[binding["input_key"]]
        if binding["inventory_key"] is not None:
            matching = [link for link in links if link["inventory_key"] == binding["inventory_key"]]
            _require(bool(matching), "execution_link_missing", "/track_bindings")
            if any(link["relation"] == "exact_executed_fasta" for link in matching):
                _require(binding["execution_relation"] == "unknown" and binding["membership_complete"] == "unknown" and
                         "execution_witness_interface_unavailable" in binding["input_record_count"]["reason_codes"], "execution_witness_unavailable", "/track_bindings")
    requested = value["requested_native_links"]
    for kind, field in (("reference", "reference_joins"), ("association_subject", "subject_joins")):
        _unique([j["native"] for j in value[field]], "/" + field)
        for join in value[field]:
            selector = join["native"]
            path = "/" + field
            _require(selector["source_ref"] == value["primary_source_ref"] and selector["kind"] == kind,
                     "join_selector_conflict", path)
            if kind == "reference":
                _require(selector["track_key"] == "ref_genome" and selector["association_key"] is None, "join_selector_conflict", path)
            else:
                _require(_TRACK.fullmatch(selector["track_key"]) and selector["association_key"] == f'{selector["track_key"]}/row/{selector["reference_row_ordinal"]}', "join_selector_conflict", path)
            _unique(join["candidates"], path + "/candidates")
            _unique(join["accepted_link_indices"], path + "/accepted_link_indices")
            _require((join["state"] == "joined") == (join["protein"] is not None), "operand_join_state_conflict", path)
            if join["state"] != "joined":
                _require(not join["accepted_link_indices"], "unresolved_join_admits_link", path)
                continue
            _require(join["candidates"] == [join["protein"]] and bool(join["accepted_link_indices"]), "joined_occurrence_not_unique", path)
            binding = bindings.get(selector["track_key"])
            _require(binding is not None and binding["inventory_key"] == join["protein"]["inventory_key"], "operand_input_conflict", path)
            for index in join["accepted_link_indices"]:
                _require(index < len(requested), "native_link_missing", path)
                link = requested[index]
                _require(link["basis"] == "unique_exact_identifier", "occurrence_witness_unavailable", path)
                _require(link["native"] == selector and link["protein"] == join["protein"], "accepted_native_link_conflict", path)
    joins = value["metadata_joins"]
    _unique([j["link_index"] for j in joins], "/metadata_joins")
    _require({j["link_index"] for j in joins} == set(range(len(value["requested_metadata_links"]))), "metadata_join_population_conflict", "/metadata_joins")
    for join in joins:
        link = value["requested_metadata_links"][join["link_index"]]
        _require(join["protein"] == link["protein"], "metadata_protein_conflict", "/metadata_joins")
        if join["state"] == "joined":
            _require(link["basis"] == "exact_feature_identifier", "occurrence_witness_unavailable", "/metadata_joins")
            _require(join["feature"] is not None and all(join[name] == link[name] for name in ("feature", "genome", "feature_sequence")), "metadata_link_conflict", "/metadata_joins")
        else:
            _require(all(join[name] is None for name in ("feature", "genome", "feature_sequence")), "unresolved_metadata_admits_record", "/metadata_joins")
    members = set()
    digests = set()
    for group in value["sequence_groups"]:
        _require(bool(group["members"]), "sequence_group_empty", "/sequence_groups")
        keys = [_protein_key(ref) for ref in group["members"]]
        _require(len(keys) == len(set(keys)) and not members.intersection(keys) and group["sequence_sha256"] not in digests, "sequence_group_member_repeated", "/sequence_groups")
        members.update(keys)
        digests.add(group["sequence_sha256"])


def _joins(value, primary, index, inventories, features, genomes, sequences):
    path = "/joins"
    _require(value["primary_source_ref"] == primary["source"]["content"]["source_ref"],
             "join_primary_conflict", path)
    inputs = {} if index is None else {i["input_key"]: i for i in index["inputs"]}
    bindings = _map(value["track_bindings"], "track_key", path + "/track_bindings")
    _unique([b["input_key"] for b in bindings.values()], path + "/track_bindings")
    _require(set(bindings) == {i["expected_track_key"] for i in inputs.values()},
             "join_track_population_conflict", path + "/track_bindings")
    execution = defaultdict(list)
    for link in value["execution_links"]:
        # Rejected requests remain raw claims. Only admitted bindings below
        # must resolve; their locators are not execution witnesses.
        execution[link["input_key"]].append(link)
    for key, binding in bindings.items():
        bp = path + "/track_bindings"
        entry = inputs.get(binding["input_key"])
        _require(entry is not None and entry["expected_track_key"] == key,
                 "join_track_input_conflict", bp)
        _missing_denominator(binding["input_record_count"], bp + "/input_record_count")
        _require(binding["execution_relation"] != "exact_executed_fasta",
                 "execution_witness_unavailable", bp)
        _require(binding["membership_complete"] != "yes", "execution_membership_unavailable", bp)
        links = execution[binding["input_key"]]
        if binding["inventory_key"] is not None:
            _require(binding["inventory_key"] in inventories, "inventory_missing", bp)
            matching = [link for link in links if link["inventory_key"] == binding["inventory_key"]]
            _require(bool(matching), "execution_link_missing", bp)
            _require(len({link["inventory_key"] for link in links}) == 1,
                     "execution_link_conflict", bp)
            content = inventories[binding["inventory_key"]]["source"]["content"]
            _require(all(link["executed_fasta"] is None or
                         all(link["executed_fasta"][field] == content[field]
                             for field in ("sha256", "byte_count")) for link in matching),
                     "execution_content_conflict", bp)
            if binding["execution_relation"] != "unknown":
                _require(all(link["relation"] == binding["execution_relation"] for link in matching),
                         "execution_relation_conflict", bp)
            if any(link["relation"] == "exact_executed_fasta" for link in matching):
                _require(binding["execution_relation"] == "unknown" and binding["membership_complete"] == "unknown" and
                         "execution_witness_interface_unavailable" in binding["input_record_count"]["reason_codes"],
                         "execution_witness_unavailable", bp)
        else:
            _require(binding["execution_relation"] == "unknown" and binding["membership_complete"] == "unknown",
                     "unbound_execution_claim", bp)
        _unique(binding["identifier_collisions"], bp + "/identifier_collisions")

    # Index occurrence identities once; validating a chosen link must not create
    # a new matching/selection process for every field.
    occurrences = {}
    for key, inventory in inventories.items():
        ids = defaultdict(list)
        for record in inventory["records"]:
            if record["identifier"] is not None:
                ids[record["identifier"]].append(record["record_ordinal"])
        occurrences[key] = ids
    identifier_tracks = defaultdict(set)
    for key, binding in bindings.items():
        if binding["inventory_key"] is not None:
            for identifier in occurrences[binding["inventory_key"]]:
                identifier_tracks[identifier].add(key)
    for key, binding in bindings.items():
        if binding["inventory_key"] is not None:
            actual = {identifier for identifier in occurrences[binding["inventory_key"]]
                      if len(identifier_tracks[identifier]) > 1}
            _require(set(binding["identifier_collisions"]) == actual,
                     "identifier_collision_population_conflict", path + "/track_bindings")

    associations = {row["association_key"]: row for row in primary["associations"]}
    joins_by_kind = {}
    requested = value["requested_native_links"]
    requested_by_selector = defaultdict(list)
    for link in requested:
        requested_by_selector[_key(link["native"])].append(link)
    for kind, field, expected in (
        ("reference", "reference_joins", {("reference", r["row_ordinal"], "ref_genome", None) for r in primary["reference_rows"]}),
        ("association_subject", "subject_joins", {("association_subject", r["reference_row_ordinal"], r["track_key"], r["association_key"]) for r in primary["associations"]}),
    ):
        joins = value[field]
        _unique([_selector_key(j["native"]) for j in joins], path + "/" + field)
        _require({_selector_key(j["native"]) for j in joins} == expected,
                 "operand_join_population_conflict", path + "/" + field)
        joins_by_kind[kind] = {_selector_key(j["native"]): j for j in joins}
        for ordinal, join in enumerate(joins):
            jp = f"{path}/{field}/{ordinal}"
            native = _selector(join["native"], primary, associations, jp + "/native")
            _require((join["state"] == "joined") == (join["protein"] is not None),
                     "operand_join_state_conflict", jp)
            _unique(join["candidates"], jp + "/candidates")
            _unique(join["accepted_link_indices"], jp + "/accepted_link_indices")
            for candidate in join["candidates"]:
                _protein(candidate, inventories, jp + "/candidates")
            if join["state"] != "joined":
                _require(not join["accepted_link_indices"], "unresolved_join_admits_link", jp)
                continue
            protein = _protein(join["protein"], inventories, jp + "/protein")
            binding = bindings.get(join["native"]["track_key"])
            _require(binding is not None and binding["inventory_key"] == join["protein"]["inventory_key"],
                     "operand_input_conflict", jp)
            _require(join["candidates"] == [join["protein"]] and bool(join["accepted_link_indices"]),
                     "joined_occurrence_not_unique", jp)
            identifier = native["patric_id"]
            _require(not _layout_uncertain(primary, native) and identifier["presence"] == "value" and
                     identifier["value"] == protein["identifier"], "native_identifier_conflict", jp)
            _require(occurrences[join["protein"]["inventory_key"]][protein["identifier"]] == [protein["record_ordinal"]] and
                     len(identifier_tracks[protein["identifier"]]) == 1,
                     "identifier_occurrence_ambiguous", jp)
            length = native["aa_length"]
            if length["presence"] == "value" and protein["record_complete"] and protein["valid_sequence"] and "*" not in protein["sequence"]:
                _require(length["value"] == protein["sequence_symbol_count"], "sequence_length_conflict", jp)
            for link_index in join["accepted_link_indices"]:
                _require(link_index < len(requested), "native_link_missing", jp)
                link = requested[link_index]
                _require(link["basis"] == "unique_exact_identifier", "occurrence_witness_unavailable", jp)
                _require(link["native"] == join["native"] and link["protein"] == join["protein"] and
                         link["native_identifier"] == identifier["value"], "accepted_native_link_conflict", jp)
            applicable = requested_by_selector[_key(join["native"])]
            _require(all(link["protein"] == join["protein"] for link in applicable),
                     "contradictory_native_links", jp)

    # Build identity indices once, including invalid rows' usable cells. Whole
    # record validity is deliberately not substituted for local ID agreement.
    feature_identities = {}
    for key, snapshot in features.items():
        identities = defaultdict(set)
        for row in snapshot["records"]:
            for name in ("feature_id", "patric_id"):
                if row[name]["presence"] == "value":
                    identities[row[name]["value"]].add(row["row_ordinal"])
        feature_identities[key] = identities
    metadata = value["metadata_joins"]
    _unique([j["link_index"] for j in metadata], path + "/metadata_joins")
    _require({j["link_index"] for j in metadata} == set(range(len(value["requested_metadata_links"]))),
             "metadata_join_population_conflict", path + "/metadata_joins")
    for ordinal, join in enumerate(metadata):
        mp = f"{path}/metadata_joins/{ordinal}"
        link = value["requested_metadata_links"][join["link_index"]]
        _require(join["protein"] == link["protein"], "metadata_protein_conflict", mp)
        if join["state"] != "joined":
            _require(all(join[name] is None for name in ("feature", "genome", "feature_sequence")),
                     "unresolved_metadata_admits_record", mp)
            continue
        _require(link["basis"] == "exact_feature_identifier", "occurrence_witness_unavailable", mp)
        _require(join["feature"] is not None and all(join[name] == link[name] for name in ("feature", "genome", "feature_sequence")),
                 "metadata_link_conflict", mp)
        protein = _protein(join["protein"], inventories, mp + "/protein")
        feature = _metadata(join["feature"], features, mp + "/feature")
        identifiers = {feature[name]["value"] for name in ("feature_id", "patric_id") if feature[name]["presence"] == "value"}
        _require(protein["identifier"] in identifiers, "metadata_identifier_conflict", mp)
        matching = feature_identities[join["feature"]["snapshot_key"]][protein["identifier"]]
        _require(len(matching) == 1 and occurrences[join["protein"]["inventory_key"]][protein["identifier"]] == [protein["record_ordinal"]],
                 "metadata_identifier_ambiguous", mp)
        md5 = feature["aa_sequence_md5"]
        _require(md5["presence"] != "invalid", "metadata_sequence_conflict", mp)
        complete_sequence = protein["record_complete"] and protein["valid_sequence"]
        if md5["presence"] == "value" and complete_sequence:
            _require(md5["value"].lower() == protein["sequence_md5"], "metadata_sequence_conflict", mp)
        if join["genome"] is not None:
            genome = _metadata(join["genome"], genomes, mp + "/genome")
            _require(feature["genome_id"]["presence"] == genome["genome_id"]["presence"] == "value" and
                     feature["genome_id"]["value"] == genome["genome_id"]["value"], "metadata_genome_conflict", mp)
        if join["feature_sequence"] is not None:
            sequence = _metadata(join["feature_sequence"], sequences, mp + "/feature_sequence", usable=True)
            _require(md5["presence"] == "value" and md5["value"].lower() == sequence["md5"]["value"].lower(), "metadata_sequence_conflict", mp)
            normalized = sequence["sequence"]["value"].translate(str.maketrans({**{ord(c): None for c in " \t\n\r\v\f"}, **{n: n-32 for n in range(97, 123)}}))
            if complete_sequence:
                _require(sequence["computed_sha256"] == protein["sequence_sha256"] and normalized == protein["sequence"], "metadata_sequence_conflict", mp)

    grouped_members, grouped_sequences = set(), set()
    for ordinal, group in enumerate(value["sequence_groups"]):
        gp = f"{path}/sequence_groups/{ordinal}"
        _require(bool(group["members"]), "sequence_group_empty", gp)
        _unique(group["members"], gp + "/members")
        rows = [_protein(ref, inventories, gp, usable=True) for ref in group["members"]]
        keys = {_protein_key(ref) for ref in group["members"]}
        _require(not grouped_members.intersection(keys), "sequence_group_member_repeated", gp)
        grouped_members.update(keys)
        sequence = rows[0]["sequence"]
        _require(sequence not in grouped_sequences and all(r["sequence"] == sequence for r in rows),
                 "sequence_group_equality_conflict", gp)
        grouped_sequences.add(sequence)
        _require(group["sequence_sha256"] == rows[0]["sequence_sha256"] and
                 group["sequence_symbol_count"] == rows[0]["sequence_symbol_count"], "sequence_group_value_conflict", gp)
    return bindings, joins_by_kind, metadata


def _representations(comparisons, projections):
    _unique([sorted((c["link"]["left_source_ref"], c["link"]["right_source_ref"])) for c in comparisons],
            "/representation_comparisons")
    for ordinal, comparison in enumerate(comparisons):
        path = f"/representation_comparisons/{ordinal}"
        link = comparison["link"]
        left, right = projections.get(link["left_source_ref"]), projections.get(link["right_source_ref"])
        _require(link["left_source_ref"] != link["right_source_ref"], "representation_self_link", path)
        references = link["reference_pairs"]
        associations = link["association_pairs"]
        for pairs, a, b in ((references, "left_row_ordinal", "right_row_ordinal"),
                            (associations, "left_association_key", "right_association_key")):
            _unique([p[a] for p in pairs], path)
            _unique([p[b] for p in pairs], path)
        correspondence_diagnostic = any(d["code"] == "representation_correspondence_missing" for d in comparison["diagnostics"])
        if left is None or right is None:
            _require(comparison["state"] == "unbound" and not comparison["conflict_source_fields"] and correspondence_diagnostic,
                     "representation_unbound_conflict", path)
            continue
        ref_mapping = {}
        conflict_fields, unavailable, unbound = [], False, False

        def compare(a, b, fields):
            nonlocal unavailable
            if _layout_uncertain(left, a) or _layout_uncertain(right, b):
                unavailable = True
                return
            for name in fields:
                ac, bc = a[name], b[name]
                if ac["presence"] == bc["presence"] == "value":
                    equal = (Decimal(ac["lexeme"]) == Decimal(bc["lexeme"]) if "lexeme" in ac else ac["value"] == bc["value"])
                    if not equal:
                        conflict_fields.extend([ac["source_field"], bc["source_field"]])
                elif ac["presence"] == "value" or bc["presence"] == "value" or "invalid" in (ac["presence"], bc["presence"]):
                    unavailable = True

        for pair in references:
            a, b = pair["left_row_ordinal"], pair["right_row_ordinal"]
            if a >= len(left["reference_rows"]) or b >= len(right["reference_rows"]):
                unbound = True
                continue
            ref_mapping[a] = b
            compare(left["reference_rows"][a], right["reference_rows"][b], REFERENCE_FIELDS)
        lm = {r["association_key"]: r for r in left["associations"]}
        rm = {r["association_key"]: r for r in right["associations"]}
        for pair in associations:
            a, b = lm.get(pair["left_association_key"]), rm.get(pair["right_association_key"])
            if (a is None or b is None or a["track_key"] != b["track_key"] or
                    ref_mapping.get(a["reference_row_ordinal"]) != b["reference_row_ordinal"]):
                unbound = True
                continue
            compare(a, b, COMPARISON_FIELDS)
        _require(not unbound or correspondence_diagnostic, "representation_rejection_diagnostic_missing", path)
        if conflict_fields:
            _require(comparison["state"] == "conflicting" and
                     {_key(f) for f in comparison["conflict_source_fields"]} == {_key(f) for f in conflict_fields},
                     "representation_conflict_claim", path)
        else:
            _require(not comparison["conflict_source_fields"], "representation_false_conflict", path)
            if unbound:
                _require(comparison["state"] == "unbound", "representation_unbound_conflict", path)
                continue
            complete = (bool(references or associations) and not unavailable and
                        {t["track_key"] for t in left["tracks"]} == {t["track_key"] for t in right["tracks"]} and
                        len(references) == len(left["reference_rows"]) == len(right["reference_rows"]) and
                        len(associations) == len(lm) == len(rm) and
                        left["projection_completeness"] == right["projection_completeness"] == "complete_document")
            _require(comparison["state"] == ("equal_observed_cells" if complete else "incomplete_comparison"),
                     "representation_state_conflict", path)


def _sheet(value):
    projections = {}
    for ordinal, result in enumerate(value["native_results"]):
        path = f"/native_results/{ordinal}"
        _envelope(result, path)
        if result["value"] is None:
            continue
        projection = result["value"]
        try:
            validate_native_projection(projection)
        except NativeValidationError as error:
            raise ProteomeDataError(error.code, path + "/value" + error.path) from error
        source_ref = projection["source"]["content"]["source_ref"]
        _require(source_ref not in projections, "native_source_repeated", path)
        projections[source_ref] = projection
    primary = projections.get(value["primary_source_ref"])
    _require(primary is not None and primary["projection_completeness"] != "invalid_document", "primary_projection_missing", "/primary_source_ref")
    index = value["input_index"]
    if index is not None:
        _validate_part("InputIndex", index, "/input_index")
    maps = []
    snapshot_keys = set()
    for field, name in (("inventories", "ProteinInventory"), ("feature_snapshots", "FeatureSnapshot"),
                        ("genome_snapshots", "GenomeSnapshot"), ("sequence_snapshots", "FeatureSequenceSnapshot")):
        identity = "inventory_key" if field == "inventories" else "snapshot_key"
        mapping = _map(value[field], identity, "/" + field)
        for ordinal, data in enumerate(value[field]):
            _validate_part(name, data, f"/{field}/{ordinal}")
            if identity == "snapshot_key":
                _require(data[identity] not in snapshot_keys, "snapshot_identity_repeated", f"/{field}/{ordinal}")
                snapshot_keys.add(data[identity])
        maps.append(mapping)
    inventories, features, genomes, sequences = maps
    bindings, operand_joins, metadata = ({}, {}, []) if value["joins"] is None else _joins(value["joins"], primary, index, *maps)
    native_tracks = {t["track_key"]: t for t in primary["tracks"]}
    inputs = {} if index is None else {i["expected_track_key"]: i for i in index["inputs"]}
    tracks = _map(value["tracks"], "track_key", "/tracks")
    _require(set(tracks) == set(native_tracks).union(inputs), "sheet_track_population_conflict", "/tracks")
    for ordinal, track in enumerate(value["tracks"]):
        path = f"/tracks/{ordinal}"
        key, native = track["track_key"], native_tracks.get(track["track_key"])
        match = _TRACK.fullmatch(key)
        _require((key == "ref_genome" and track["comparison_ordinal"] is None) or
                 (match is not None and str(track["comparison_ordinal"]) == match[1]), "sheet_track_identity_conflict", path)
        _require(track["native_materialization"] == (native["materialization"] if native else "not_in_projection") and
                 track["native_source_fields"] == (native["source_fields"] if native else []), "sheet_track_copy_conflict", path)
        _require(track["original_input_key"] == (inputs[key]["input_key"] if key in inputs else None), "sheet_input_mapping_conflict", path)
        binding = bindings.get(key)
        _require(track["inventory_key"] == (binding["inventory_key"] if binding else None), "sheet_inventory_mapping_conflict", path)
        _missing_denominator(track["input_record_count"], path + "/input_record_count")
        if binding is not None:
            _require(track["input_record_count"] == binding["input_record_count"], "sheet_denominator_copy_conflict", path)
        _require(track["complete_reference_row_membership"] != "yes" and track["complete_published_association_membership"] != "yes",
                 "execution_membership_unavailable", path)

    def copied_join(row, native, protein_name, state_name, kind, path):
        selector = (kind, native.get("reference_row_ordinal", native.get("row_ordinal")),
                    "ref_genome" if kind == "reference" else native["track_key"],
                    None if kind == "reference" else native["association_key"])
        join = operand_joins.get(kind, {}).get(selector)
        _require(row[state_name] == (join["state"] if join else "not_supplied") and
                 row[protein_name] == (join["protein"] if join else None), "sheet_join_copy_conflict", path)

    def inventory_count(cell, protein, path):
        if protein is None:
            _require(cell["state"] != "value", "unbound_sequence_count", path)
        else:
            source = _protein(protein, inventories, path)
            if source["record_complete"]:
                _require(cell["state"] == "value" and cell["value"] == source["sequence_symbol_count"] and
                         cell["source_fields"] == [source["source_field"]], "sequence_count_copy_conflict", path)
            else:
                _require(cell["state"] != "value", "incomplete_sequence_count", path)

    def metadata_indices(row, protein, path):
        _unique(row["metadata_links"], path + "/metadata_links")
        for number in row["metadata_links"]:
            _require(number < len(metadata) and protein is not None and metadata[number]["state"] == "joined" and
                     metadata[number]["protein"] == protein, "sheet_metadata_link_conflict", path)
        expected = {i for i, join in enumerate(metadata) if join["state"] == "joined" and join["protein"] == protein}
        _require(set(row["metadata_links"]) == expected, "sheet_metadata_population_conflict", path)

    references = value["reference_rows"]
    _require(len(references) == len(primary["reference_rows"]), "sheet_reference_population_conflict", "/reference_rows")
    for ordinal, row in enumerate(references):
        path, native = f"/reference_rows/{ordinal}", primary["reference_rows"][ordinal]
        _require(row["reference_row_ordinal"] == ordinal and row["reference_row_key"] == native["reference_row_key"], "sheet_reference_identity_conflict", path)
        for target, source in (("native_aa_length", "aa_length"), ("native_start", "start"), ("native_end", "end"), ("native_strand", "strand")):
            _require(_key(row[target]) == _key(native[source]), "native_cell_copy_conflict", path + "/" + target)
        copied_join(row, native, "protein", "join_state", "reference", path)
        inventory_count(row["inventory_sequence_symbol_count"], row["protein"], path)
        metadata_indices(row, row["protein"], path)
        if row["coordinate_kind"] == "artificial_layout":
            _require(row["join_state"] == "joined" and inputs.get("ref_genome", {}).get("kind") == "user_genome", "coordinate_origin_unbound", path)
        elif row["coordinate_kind"] == "genomic_metadata":
            _require(inputs.get("ref_genome", {}).get("kind") in {"genome_id", "user_feature_group"} and
                     row["join_state"] == "joined" and bool(row["metadata_links"]), "coordinate_origin_unbound", path)
            conventions = set()
            for link_index in row["metadata_links"]:
                feature_ref = metadata[link_index]["feature"]
                snapshot = features[feature_ref["snapshot_key"]]
                feature = snapshot["records"][feature_ref["row_ordinal"]]
                conventions.add(snapshot["coordinate_convention"]["value"])
                _require(all(native[name]["presence"] == feature[name]["presence"] == "value" and
                             native[name]["value"] == feature[name]["value"]
                             for name in ("start", "end", "strand")), "coordinate_origin_conflict", path)
            _require("unknown" not in conventions and len(conventions) == 1, "coordinate_origin_unbound", path)
    associations = value["association_rows"]
    _require(len(associations) == len(primary["associations"]), "sheet_association_population_conflict", "/association_rows")
    for ordinal, row in enumerate(associations):
        path, native = f"/association_rows/{ordinal}", primary["associations"][ordinal]
        _require(all(row[name] == native[name] for name in ("association_key", "track_key", "reference_row_ordinal")), "sheet_association_identity_conflict", path)
        for target, source in (("native_hit_category", "hit"), ("native_subject_length_aa", "aa_length"),
                               ("native_first_hsp_alignment_identity_fraction", "percent_identity"),
                               ("native_subject_endpoint_difference_fraction", "seq_coverage")):
            _require(_key(row[target]) == _key(native[source]), "native_cell_copy_conflict", path + "/" + target)
        ref = primary["reference_rows"][row["reference_row_ordinal"]]
        copied_join(row, ref, "reference_protein", "reference_join_state", "reference", path)
        copied_join(row, native, "subject_protein", "subject_join_state", "association_subject", path)
        inventory_count(row["inventory_subject_sequence_symbol_count"], row["subject_protein"], path)
        metadata_indices(row, row["subject_protein"], path)
        _require(row["native_subject_identifier_present"] == (native["patric_id"]["presence"] == "value"), "subject_presence_conflict", path)
        _require(row["layout_state"] == ("uncertain_table_layout" if _layout_uncertain(primary, native) else "source_field_located"), "table_layout_claim_conflict", path)
    _representations(value["representation_comparisons"], projections)
    attachment = value["directional_attachment"]
    if attachment is not None:
        _require(attachment["state"] == "unavailable" and not attachment["reports"] and not attachment["operand_links"], "directional_interface_unavailable", "/directional_attachment")
        _require(any(r["required_input"] == "directional_report" for r in attachment["requirements"]), "directional_requirement_missing", "/directional_attachment")
        _unique(attachment["expected_scopes"], "/directional_attachment/expected_scopes")
        _require(all(s["comparison_track_key"] in tracks and s["comparison_track_key"] != "ref_genome" for s in attachment["expected_scopes"]), "directional_track_missing", "/directional_attachment")


def _component_field(field, track, ordinal, native_name, path):
    name = track + "_" + native_name
    _require(field["field_name"] == name, "component_field_name_conflict", path)
    pointer = field["pointer"]
    if pointer.startswith("/feature_matches/"):
        _require(pointer == f"/feature_matches/{ordinal}/{name}" and str(field["row_ordinal"]) == str(ordinal),
                 "component_field_location_conflict", path)
    else:
        match = re.fullmatch(r"/rows/(0|[1-9][0-9]*)/(0|[1-9][0-9]*)", pointer)
        _require(match is not None and str(field["row_ordinal"]) == match[1], "component_field_location_conflict", path)


def _count(cell, expected, path):
    _require(cell["state"] == "value" and cell["value"] == expected, "component_population_conflict", path)


def _components(value):
    _parameters(value["parameters"], "/parameters")
    selected = value["parameters"]["track_keys"]
    _require([t["track_key"] for t in value["tracks"]] == selected, "component_track_population_conflict", "/tracks")
    _unique([r["association_key"] for r in value["associations"]], "/associations")
    by_track = defaultdict(list)
    enabled = {name for name, parameter in (("identity", "minimum_identity_fraction"), ("subject_endpoint_difference", "minimum_subject_endpoint_difference_fraction"), ("category", "allowed_hit_categories"))
               if value["parameters"][parameter] is not None}
    source_bindings = set()
    for ordinal, row in enumerate(value["associations"]):
        path = f"/associations/{ordinal}"
        match = _ASSOCIATION.fullmatch(row["association_key"])
        _require(match is not None and match[1] == row["track_key"] and row["track_key"] in selected, "component_association_identity_conflict", path)
        by_track[row["track_key"]].append(row)
        _unique(row["failed_conditions"], path + "/failed_conditions")
        _unique(row["unknown_conditions"], path + "/unknown_conditions")
        failed, unknown = set(row["failed_conditions"]), set(row["unknown_conditions"])
        _require(not failed.intersection(unknown) and failed.union(unknown) <= enabled, "selection_condition_conflict", path)
        _require(row["selection"] == ("fail" if failed else "unknown" if unknown else "pass"), "selection_state_conflict", path)
        for name, native_name in (("first_hsp_alignment_identity_percent", "percent_identity"), ("subject_endpoint_difference_percent", "seq_coverage")):
            cell = row[name]
            _require(len(cell["source_fields"]) == 1 and cell["state"] in {"value", "missing_input", "invalid", "ambiguous"}, "association_component_state_conflict", path + "/" + name)
            field = cell["source_fields"][0]
            _component_field(field, row["track_key"], match[2], native_name, path + "/" + name)
            source_bindings.add((field["source_ref"], field["sha256"]))
            condition = "identity" if native_name == "percent_identity" else "subject_endpoint_difference"
            if condition in enabled:
                _require((condition in unknown) == (cell["state"] != "value"), "selection_missingness_conflict", path)
    _require(len(source_bindings) <= 1, "component_primary_source_conflict", "/associations")
    reference_count = None
    for ordinal, track in enumerate(value["tracks"]):
        path = f"/tracks/{ordinal}"
        rows = by_track[track["track_key"]]
        n = len(rows)
        _count(track["source_association_record_count"], n, path)
        if track["materialization"] in {"unknown", "not_in_projection"}:
            _require(not rows, "unmaterialized_associations", path)
        for name in ("reference_input_record_count", "comparison_input_record_count"):
            _missing_denominator(track[name], path + "/" + name)
        if reference_count is None:
            reference_count = track["reference_input_record_count"]
        _require(track["reference_input_record_count"] == reference_count, "component_reference_denominator_conflict", path)
        _require(track["no_published_reference_count"]["state"] != "value", "execution_membership_unavailable", path)
        counts = {name: cell["value"] for name, cell in track.items() if type(cell) is dict and set(cell) == _CELL_KEYS and name not in {"reference_input_record_count", "comparison_input_record_count", "no_published_reference_count"}}
        _require(all(type(count) is int for count in counts.values()), "component_count_unavailable", path)
        published = counts["published_association_record_count"]
        _require(published <= n, "published_population_conflict", path)
        _require(sum(counts["native_" + kind + "_count"] for kind in ("bi", "uni", "other_category", "missing_category")) == n,
                 "category_partition_conflict", path)
        selections = Counter(r["selection"] for r in rows)
        for state in ("pass", "fail", "unknown"):
            _count(track["selection_counts"][state], selections[state], path + "/selection_counts/" + state)
        for operand in ("reference", "subject"):
            unresolved = counts[f"unresolved_{operand}_association_count"]
            bound = counts[f"observed_bound_{operand}_count"]
            _require(unresolved <= published and bound <= published - unresolved and
                     (bound > 0) == (unresolved < published), "bound_population_conflict", path)
        bound_ref, bound_sub = counts["observed_bound_reference_count"], counts["observed_bound_subject_count"]
        _require(counts["observed_selected_reference_count"] <= min(bound_ref, selections["pass"]), "selected_population_conflict", path)
        _require(counts["multiple_reference_subject_count"] <= bound_sub and counts["excess_bound_pair_count"] <= published and
                 (bound_ref > 0 and bound_sub > 0 or counts["multiple_reference_subject_count"] == counts["excess_bound_pair_count"] == 0), "bound_pair_population_conflict", path)
        groups, unresolved = counts["demonstrated_subject_sequence_group_count"], counts["unresolved_subject_sequence_count"]
        _require(unresolved <= bound_sub and groups <= bound_sub - unresolved and (groups > 0) == (unresolved < bound_sub), "sequence_population_conflict", path)
        for summary_name, percent_name in (("first_hsp_identity_summary", "first_hsp_alignment_identity_percent"), ("subject_endpoint_difference_summary", "subject_endpoint_difference_percent")):
            summary = track[summary_name]
            sp = path + "/" + summary_name
            fields = {_key(r[percent_name]["source_fields"][0]): r for r in rows}
            _require(len(fields) == n, "component_source_field_repeated", sp)
            used, all_fields = [], set()
            for partition in ("value", "omitted", "null", "blank", "invalid", "layout_uncertain"):
                cell = summary[partition + "_count"]
                _count(cell, len(cell["source_fields"]), sp + "/" + partition + "_count")
                for field in cell["source_fields"]:
                    key = _key(field)
                    _require(key in fields and key not in all_fields, "summary_population_conflict", sp)
                    all_fields.add(key)
                    row = fields[key]
                    expected = {"value": "value", "invalid": "invalid", "layout_uncertain": "ambiguous"}.get(partition, "missing_input")
                    _require(row[percent_name]["state"] == expected, "summary_missingness_conflict", sp)
                    if partition == "value":
                        used.append(row["association_key"])
            _require(all_fields == set(fields) and summary["used_association_keys"] == used, "summary_membership_conflict", sp)
            _require(summary["sum"]["state"] == "value" and summary["sum"]["source_fields"] == summary["value_count"]["source_fields"], "summary_source_conflict", sp)
            for name in ("mean", "minimum", "maximum"):
                cell = summary[name]
                _require(cell["state"] == ("value" if used else "not_applicable") and
                         cell["source_fields"] == summary["value_count"]["source_fields"], "summary_state_conflict", sp + "/" + name)
        for name, numerator in (("observed_reference_fraction", "observed_bound_reference_count"),
                                ("complete_published_reference_fraction", "observed_bound_reference_count"),
                                ("observed_selected_reference_fraction", "observed_selected_reference_count"),
                                ("complete_selected_reference_fraction", "observed_selected_reference_count")):
            ratio = track[name]
            _require(ratio["numerator"] == track[numerator] and ratio["denominator"] == reference_count,
                     "ratio_cell_copy_conflict", path + "/" + name)
            _require(ratio["fraction"]["state"] not in {"value", "zero_denominator"}, "ratio_unknown_denominator_conflict", path + "/" + name)


def validate_proteome_sheet_data(name: str, value: dict) -> dict:
    """Validate saved contract data; return a detached copy or fixed code/path.

    No source bytes or sheet are reacquired. NativeComponents carries a digest,
    not its source sheet: this function checks that digest's shape, not external
    custody or agreement with an absent sheet. B4 records the supplied digest.
    """
    _require(type(name) is str and name in _NAMES, "unknown_contract")
    try:
        _plain(value)
        error = next(_validator(name).iter_errors(value), None)
        if error is not None:
            path = ""
            for token in error.absolute_path:
                path = _pointer(path, token)
            raise ProteomeDataError("proteome_sheet_schema_invalid", path)
        _common(value)
        data, target = value, name
        if name.endswith("Result"):
            _envelope(value)
            data, target = value["value"], name.removesuffix("Result")
            if data is not None:
                _require(("requirements" not in data or value["requirements"] == data["requirements"]) and value["diagnostics"] == data["diagnostics"], "result_projection_conflict")
                if value["status"] == "ok":
                    _require(not value["requirements"] and not any(d["severity"] == "error" for d in data["diagnostics"]), "successful_result_requirements")
        if data is not None:
            {"NativeSheet": _sheet, "NativeCalculationParameters": _parameters, "NativeComponents": _components,
             "NativeJoins": _joins_internal}[target](data)
        return deepcopy(value)
    except RecursionError as error:
        raise ProteomeDataError("proteome_sheet_excessive_nesting") from error


__all__ = ["proteome_sheet_schema", "validate_proteome_sheet_data"]
