"""Pure qualification of explicitly supplied BLAST population assertions.

The source assertion relates the complete literal database operand to a
semantic population and a particular census record. It is an asserted identity,
not confidence or a measurement. This module neither reads sources nor infers
aliases, prevalence, sequence identity or execution authority. Native adapters
authenticate the retained facts against the selected job and received sources.
"""
from __future__ import annotations

import math
import re


CONTEXT_SCHEMA = "blast_database_population_context_v1"
ASSOCIATION_SCHEMA = "blast_database_population_association_input_v1"
RELATION_SCHEMA = "blast_database_population_relation_v1"
ASSERTION_SCHEMA = "blast_database_population_assertion_v1"
PREFIX = "blast_database_population_"
_KEY = {"artifact_key", "member_ordinal", "report_index", "search_pointer"}
_PROVENANCE = {"source_ref", "pointer"}
_SEMANTIC = {"namespace", "value", "version", "release", "scope", "preparation_type"}
_SELECTED = {"native_database_operand", "native_paths", "identity", "manifest_sha256",
             "manifest_size_bytes", "invocation_source", "manifest_source"}
_RECORD = {"source_ref", "artifact_ref", "sha256", "size_bytes", "pointer", "value"}
_ASSOCIATION = {"schema", "association_key", "search_key", "database_key", "metadata_source",
                "assertion_source", "census_source", "selected_database", "assertion_record", "census_record"}
_ASSERTION = {"schema", "relation", "native_database_operand", "database_manifest_sha256",
              "population_identity", "census_artifact"}
_CENSUS = {"database", "release", "scope", "count_unit", "total_count", "function_counts"}
_UNAVAILABLE = {"association_missing", "source_record_unavailable", "selected_database_unavailable",
                "population_release_unavailable", "population_scope_unavailable"}


def _copy(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if type(value) is list:
        return [_copy(v) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: _copy(v) for k, v in value.items()}
    raise ValueError(PREFIX + "finite_json_required")


def _fields(value, keys):
    return type(value) is dict and set(value) == keys


def _text(value):
    return type(value) is str and bool(value.strip())


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _pointer(value):
    return (type(value) is str and (not value or value.startswith("/"))
            and re.search(r"~(?![01])", value) is None)


def _digest(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _provenance(value):
    return _fields(value, _PROVENANCE) and _text(value["source_ref"]) and _pointer(value["pointer"])


def _key(value):
    return (_fields(value, _KEY) and _text(value["artifact_key"]) and _integer(value["report_index"])
            and (value["member_ordinal"] is None or _integer(value["member_ordinal"]))
            and _pointer(value["search_pointer"]))


def _identity(value, *, source):
    return (_fields(value, _SEMANTIC | ({"source"} if source else set()))
            and all(_text(value[k]) for k in ("namespace", "value"))
            and all(value[k] is None or _text(value[k]) for k in ("version", "release", "scope"))
            and value["preparation_type"] in ("sequence_database", "rps", "delta", "unknown")
            and (not source or _provenance(value["source"])))


def _record(value):
    return (_fields(value, _RECORD) and all(_text(value[k]) for k in ("source_ref", "artifact_ref"))
            and _digest(value["sha256"]) and _integer(value["size_bytes"]) and _pointer(value["pointer"]))


def _selected(value):
    return (_fields(value, _SELECTED) and _text(value["native_database_operand"])
            and type(value["native_paths"]) is list and bool(value["native_paths"])
            and all(_text(p) for p in value["native_paths"])
            and _identity(value["identity"], source=True) and _digest(value["manifest_sha256"])
            and _integer(value["manifest_size_bytes"])
            and _provenance(value["invocation_source"]) and _provenance(value["manifest_source"]))


def validate_blast_database_population_context(context: dict) -> dict:
    """Detach the unchanged closed input, preserving every raw source value.

    Structural caller errors raise the two closed contract codes. An assertion
    or census's original JSON ``value`` is intentionally not normalized here;
    malformed source contents remain inspectable during qualification.
    """
    context = _copy(context)
    valid = (_fields(context, {"schema", "search_key", "associations"})
             and context["schema"] == CONTEXT_SCHEMA and _key(context["search_key"])
             and type(context["associations"]) is list)
    if valid:
        for row in context["associations"]:
            valid = (_fields(row, _ASSOCIATION) and row["schema"] == ASSOCIATION_SCHEMA
                     and _key(row["search_key"]) and all(_text(row[k]) for k in ("association_key", "database_key"))
                     and all(_provenance(row[k]) for k in ("metadata_source", "assertion_source", "census_source"))
                     and (row["selected_database"] is None or _selected(row["selected_database"]))
                     and all(row[k] is None or _record(row[k]) for k in ("assertion_record", "census_record")))
            if not valid:
                break
    if not valid:
        raise ValueError(PREFIX + "context_fields_invalid")
    return context


def _assertion(value):
    if not (_fields(value, _ASSERTION) and value["schema"] == ASSERTION_SCHEMA
            and value["relation"] == "same_population" and _text(value["native_database_operand"])
            and _digest(value["database_manifest_sha256"]) and _identity(value["population_identity"], source=False)):
        return False
    census = value["census_artifact"]
    return (_fields(census, {"sha256", "size_bytes", "pointer"}) and _digest(census["sha256"])
            and _integer(census["size_bytes"]) and _pointer(census["pointer"]))


def _census(value):
    return (_fields(value, _CENSUS) and _text(value["database"]) and _text(value["scope"])
            and (value["release"] is None or _text(value["release"]))
            and value["count_unit"] in ("unique_sequences", "sequence_groups")
            and _integer(value["total_count"], 1) and type(value["function_counts"]) is dict
            and all(_text(k) and _integer(v) for k, v in value["function_counts"].items()))


def _status(reasons):
    return "incompatible" if any(r not in _UNAVAILABLE for r in reasons) else "unavailable" if reasons else "available"


def _identity_relation(left, right, reasons, conflict):
    """Unknown required release/scope cannot establish equality or conflict."""
    for field in ("release", "scope"):
        if left[field] is None or right[field] is None:
            reasons.append("population_" + field + "_unavailable")
    if any(left[field] != right[field] and not (
            field in ("release", "scope") and (left[field] is None or right[field] is None)) for field in left):
        reasons.append(conflict)


def _source_conflicts(rows):
    """Check all supplied custody facts without selecting an input-order winner."""
    conflicts = set()
    records = [(i, row[k]) for i, row in enumerate(rows) for k in ("assertion_record", "census_record") if row[k] is not None]
    for n, (i, left) in enumerate(records):
        for j, right in records[n + 1:]:
            same_source = left["source_ref"] == right["source_ref"]
            same_artifact = left["artifact_ref"] == right["artifact_ref"]
            if (same_source or same_artifact) and (
                    (left["sha256"], left["size_bytes"]) != (right["sha256"], right["size_bytes"])
                    or left["pointer"] == right["pointer"] and left["value"] != right["value"]):
                conflicts.update((i, j))
    return conflicts


def qualify_blast_database_population_context(context: dict, *, normalized_result: dict,
        database_identity: dict | None, database_profile: dict | None) -> dict:
    """Qualify only the source-asserted population relation, without scoring.

    Each selected declaration participates, including unavailable declarations
    beside a valid one. An empty list grants no relation. Old exact-identity
    population checks remain the numerical grader's separate responsibility.
    """
    context = validate_blast_database_population_context(context)
    normalized_result = _copy(normalized_result)
    database_identity, database_profile = _copy(database_identity), _copy(database_profile)
    if (type(normalized_result) is not dict or normalized_result.get("schema") != "blast_normalized_result_v1"
            or type(normalized_result.get("search")) is not dict or type(normalized_result.get("native")) is not dict
            or database_identity is not None and not _identity(database_identity, source=True)
            or database_profile is not None and type(database_profile) is not dict):
        raise ValueError(PREFIX + "context_fields_invalid")
    key, rows = context["search_key"], context["associations"]
    locator = normalized_result.get("source_locator")
    locator = locator if type(locator) is dict else {}
    native = normalized_result["native"]
    member = native.get("archive_member")
    member = member if type(member) is dict else {}
    digests = {v for v in (native.get("sha256"), member.get("sha256"), locator.get("member_sha256")) if _digest(v)}
    report_source_ref = locator.get("source_ref")
    common = []
    if (locator.get("search_key") != key or locator.get("report_index") != key["report_index"]
            or locator.get("pointer") != key["search_pointer"]
            or locator.get("member_ordinal") != key["member_ordinal"]):
        common.append("search_key_mismatch")
    if not _text(locator.get("artifact_ref")) or not _digest(native.get("sha256")):
        common.append("source_record_unavailable")
    if rows and not _text(report_source_ref):
        common.append("source_record_unavailable")
    if key["member_ordinal"] is not None:
        if not _digest(member.get("sha256")) or not _digest(locator.get("member_sha256")):
            common.append("source_record_unavailable")
        elif member.get("ordinal") != key["member_ordinal"] or member["sha256"] != locator["member_sha256"]:
            common.append("source_address_conflict")
    elif member or locator.get("member_sha256") is not None:
        common.append("source_address_conflict")
    source_conflicts = _source_conflicts(rows)
    results, all_reasons = [], set(common)
    for index, row in enumerate(rows):
        reasons = list(common)
        if row["search_key"] != key:
            reasons.append("search_key_mismatch")
        if index in source_conflicts:
            reasons.append("source_address_conflict")
        identity_key = (row["metadata_source"], row["association_key"])
        if any((other["metadata_source"], other["association_key"]) == identity_key and other != row for other in rows):
            reasons.append("association_record_conflict")
        selected = row["selected_database"]
        if selected is None or database_identity is None:
            reasons.append("selected_database_unavailable")
        else:
            _identity_relation(selected["identity"], database_identity, reasons, "selected_database_conflict")
            if selected["identity"]["preparation_type"] != "sequence_database":
                reasons.append("population_identity_conflict")
            if selected["native_database_operand"] != " ".join(selected["native_paths"]):
                reasons.append("native_operand_conflict")
            # The independently captured selected database is one original job
            # input. Two contradictory selected facts cannot both establish it.
            for other in rows:
                other_selected = other["selected_database"]
                if other_selected is None:
                    continue
                if other["database_key"] != row["database_key"] or any(
                        other_selected[k] != selected[k] for k in selected if k != "identity"):
                    reasons.append("selected_database_conflict")
                _identity_relation(selected["identity"], other_selected["identity"], reasons, "selected_database_conflict")
        for kind in ("assertion", "census"):
            record, address = row[kind + "_record"], row[kind + "_source"]
            if record is None:
                reasons.append("source_record_unavailable")
                continue
            if {k: record[k] for k in _PROVENANCE} != address:
                reasons.append("source_address_conflict")
            if record["artifact_ref"] == locator.get("artifact_ref") or record["source_ref"] == report_source_ref or record["sha256"] in digests:
                reasons.append("report_used_as_population_source")
        assertion_record, census_record = row["assertion_record"], row["census_record"]
        assertion = assertion_record["value"] if assertion_record is not None else None
        census = census_record["value"] if census_record is not None else None
        if assertion_record is not None and not _assertion(assertion):
            reasons.append("source_record_invalid")
        if census_record is not None and not _census(census):
            reasons.append("source_record_invalid")
        if _assertion(assertion):
            if selected is not None:
                if assertion["native_database_operand"] != selected["native_database_operand"]:
                    reasons.append("native_operand_conflict")
                if assertion["database_manifest_sha256"] != selected["manifest_sha256"]:
                    reasons.append("manifest_identity_conflict")
                _identity_relation(assertion["population_identity"], {k: selected["identity"][k] for k in _SEMANTIC},
                                   reasons, "population_identity_conflict")
            if census_record is not None and assertion["census_artifact"] != {k: census_record[k] for k in ("sha256", "size_bytes", "pointer")}:
                reasons.append("census_record_conflict")
        if database_identity is not None:
            for field in ("release", "scope"):
                if database_identity[field] is None:
                    reasons.append("population_" + field + "_unavailable")
            request = normalized_result["search"].get("request") or {}
            if type(request) is not dict:
                reasons.append("native_operand_conflict")
                request = {}
            for original in (normalized_result["search"], request):
                for field in ("database", "db"):
                    allowed = [database_identity["value"]]
                    if selected is not None:
                        allowed.append(selected["native_database_operand"])
                    if selected is not None and original.get(field) is not None and original[field] not in allowed:
                        reasons.append("native_operand_conflict")
                for field in ("release", "scope", "namespace", "version"):
                    if original.get("database_" + field) is not None and original["database_" + field] != database_identity[field]:
                        reasons.append("population_identity_conflict")
        if census_record is not None:
            if database_profile is None:
                reasons.append("source_record_unavailable")
            elif (database_profile.get("source") != row["census_source"]["source_ref"]
                  or census != {k: v for k, v in database_profile.items() if k != "source"}):
                reasons.append("census_record_conflict")
            if _census(census) and database_identity is not None:
                for field, target in (("database", "value"), ("release", "release"), ("scope", "scope")):
                    if field in ("release", "scope") and census[field] is None:
                        reasons.append("population_" + field + "_unavailable")
                    elif database_identity[target] is not None and census[field] != database_identity[target]:
                        reasons.append("population_identity_conflict")
        reasons = sorted(set(reasons))
        all_reasons.update(reasons)
        results.append(dict(metadata_source=_copy(row["metadata_source"]), association_key=row["association_key"],
            status=_status(reasons), reason_codes=[PREFIX + r for r in reasons]))
    if not rows:
        all_reasons.add("association_missing")
    return dict(schema=RELATION_SCHEMA, search_key=_copy(key), status=_status(all_reasons),
        association_results=results, reason_codes=[PREFIX + r for r in sorted(all_reasons)])


__all__ = ["validate_blast_database_population_context", "qualify_blast_database_population_context"]
