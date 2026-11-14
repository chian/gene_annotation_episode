"""Closed supporting restriction records; no native work or confidence score.

References are selected operands, not proof of permission or custody. Native
literal data stays separate from the reader's derived coordinate components.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

from jsonschema import Draft202012Validator


def _obj(**properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _arr(items, *, unique=False):
    return {"type": "array", "items": items, **({"uniqueItems": True} if unique else {})}


def _enum(*values):
    return {"enum": list(values)}


def _null(schema):
    return {"anyOf": [schema, {"type": "null"}]}


TEXT = {"type": "string", "minLength": 1}
STRING = {"type": "string"}
INT = {"type": "integer"}
UINT = {"type": "integer", "minimum": 0}
BOOL = {"type": "boolean"}
SHA256 = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
TOPOLOGY = _enum("linear", "circular")
MEANING = _enum("first_base_after_cut_1based", "recognition_start_1based", "unknown")
SCHEMAS = {}
SCHEMAS["FilePin"] = _obj(path=TEXT, sha256=SHA256, size_bytes=UINT)
SCHEMAS["Pattern"] = _obj(text=STRING, flags=_null(INT))
SCHEMAS["NativeException"] = _obj(module=TEXT, **{"class": TEXT}, message=STRING)
SCHEMAS["NativeWarning"] = _obj(category_module=TEXT, category_name=TEXT,
    message=STRING, filename=STRING, lineno=UINT)
SCHEMAS["Issue"] = _obj(code=_enum("input_invalid", "sequence_binding_conflict", "enzyme_unknown",
    "catalog_unavailable", "catalog_incompatible", "native_search_failed", "native_mapping_incomplete",
    "match_capture_unavailable", "match_owner_ambiguous", "native_position_meaning_unknown",
    "cut_geometry_unknown", "association_unavailable", "association_ambiguous", "retained_record_conflict",
    "unsupported_native_version", "native_failure", "request_conflict"),
    phase=_enum("input", "catalog", "search", "capture", "association", "read"),
    enzyme_ordinal=_null(UINT), match_ordinal=_null(UINT), position_ordinal=_null(UINT))
SCHEMAS["SequenceBinding"] = _obj(version=_enum("restriction_selected_sequence_v1"),
    namespace=_enum("subject", "reference"), sequence_ref=TEXT, source_ref=TEXT,
    sequence_version=_null(UINT), content_sha256=SHA256,
    length_nt={"type": "integer", "minimum": 1}, origin_mapping_ref=_null(TEXT))
SCHEMAS["EnzymeSelection"] = {"anyOf": [
    _obj(kind=_enum("explicit"), names=_arr(TEXT, unique=True)),
    _obj(kind=_enum("commercial_native_batch"), names={"type": "null"})]}
SCHEMAS["CatalogRow"] = _obj(ordinal=UINT, name=TEXT, native_site=STRING, size_nt=UINT,
    elucidate_text=_null(STRING), elucidate_error=_null(SCHEMAS["NativeException"]),
    fst5=_null(INT), fst3=_null(INT), scd5=_null(INT), scd3=_null(INT), native_ovhg=_null(INT),
    native_pattern=SCHEMAS["Pattern"], native_class_mro=_arr(TEXT, unique=True),
    cut_kind=_enum("one_cut", "two_cuts", "no_cut", "unknown"),
    symmetry=_enum("palindromic", "nonpalindromic", "unknown"), position_meaning=MEANING,
    is_commercial=BOOL, rebase_id=_null(INT), rebase_uri=_null(STRING), dictionary_entry_json=STRING)
SCHEMAS["Catalog"] = _obj(version=_enum("restriction_catalog_snapshot_v1"),
    biopython_version=TEXT, dictionary_file=SCHEMAS["FilePin"], selection=SCHEMAS["EnzymeSelection"],
    resolved_names=_arr(TEXT, unique=True), enzymes=_arr(SCHEMAS["CatalogRow"]))
SCHEMAS["SearchRow"] = _obj(catalog_ordinal=UINT, name=TEXT, search_ordinal=_null(UINT),
    state=_enum("not_started", "returned", "failed"), native_search_positions_1based=_null(_arr(INT)),
    native_on_minus_before_drop=_null(_arr(INT)), error=_null(SCHEMAS["NativeException"]))
SCHEMAS["Group"] = _obj(name=TEXT, text=_null(STRING))
SCHEMAS["Match"] = _obj(match_ordinal=UINT, native_start_1based=INT, groups=_arr(SCHEMAS["Group"]))
SCHEMAS["MatchCall"] = _obj(call_ordinal=UINT, owner_ordinals=_arr(UINT, unique=True),
    native_pattern=SCHEMAS["Pattern"], site_size_nt=UINT, linear=BOOL,
    state=_enum("returned", "failed"), matches=_null(_arr(SCHEMAS["Match"])),
    error=_null(SCHEMAS["NativeException"]))
SCHEMAS["NativeResult"] = _obj(version=_enum("restriction_mapping_native_v1"),
    request=_obj(sequence=STRING, normalized_sequence=STRING, sequence_binding=SCHEMAS["SequenceBinding"],
        enzyme_selection=SCHEMAS["EnzymeSelection"], topology=TOPOLOGY),
    software=_obj(biopython_version=_null(TEXT), dictionary_file=_null(SCHEMAS["FilePin"]),
        native_source_file=_null(SCHEMAS["FilePin"])), catalog=_null(SCHEMAS["Catalog"]),
    formatted_sequence=_null(STRING), native_batch_member_order=_arr(TEXT, unique=True),
    batch_state=_enum("not_started", "returned", "failed"), native_mapping_order=_null(_arr(TEXT, unique=True)),
    enzyme_searches=_arr(SCHEMAS["SearchRow"]), match_observations=_arr(SCHEMAS["MatchCall"]),
    warnings=_arr(SCHEMAS["NativeWarning"]), issues=_arr(SCHEMAS["Issue"]),
    exception=_null(SCHEMAS["NativeException"]))
SCHEMAS["RecognitionEvent"] = _obj(match_call_ordinal=UINT, match_ordinal=UINT,
    native_start_1based=INT, orientation=_enum("forward", "reverse", "palindromic", "unknown"),
    unwrapped_span_0based=_null({"type": "array", "prefixItems": [INT, INT],
        "items": False, "minItems": 2, "maxItems": 2}),
    segments=_null(_arr(_obj(start=INT, end=INT))), crosses_origin=_null(BOOL),
    native_groups=_arr(SCHEMAS["Group"]))
SCHEMAS["Position"] = _obj(position_ordinal=UINT, native_position=INT,
    watson_boundary_0based=_null(INT), crick_boundary_0based=_null(INT),
    watson_canonical_boundary_0based=_null(INT), crick_canonical_boundary_0based=_null(INT),
    geometry_state=_enum("known", "unknown", "unavailable"),
    recognition_association=_enum("not_recorded"), recognition_event_ordinal={"type": "null"})
SCHEMAS["ResultRow"] = _obj(catalog_ordinal=UINT, name=TEXT,
    catalog_row=_null(SCHEMAS["CatalogRow"]),
    search_state=_enum("not_started", "returned", "failed", "invalid"), position_meaning=MEANING,
    native_search_positions_1based=_null(_arr(INT)), returned_position_count=_null(UINT),
    recognition_match_count=_null(UINT), recognition_events=_null(_arr(SCHEMAS["RecognitionEvent"])),
    positions=_null(_arr(SCHEMAS["Position"])), issues=_arr(SCHEMAS["Issue"]))
SCHEMAS["MappingResult"] = _obj(version=_enum("restriction_mapping_result_v1"),
    native_sha256=_null(SHA256), selected_sequence=SCHEMAS["SequenceBinding"],
    native_sequence=_null(SCHEMAS["SequenceBinding"]),
    binding_status=_enum("matched", "conflicting", "unavailable"), topology=_null(TOPOLOGY),
    enzyme_selection=_null(SCHEMAS["EnzymeSelection"]),
    catalog_identity=_null(_obj(biopython_version=TEXT, dictionary_file=SCHEMAS["FilePin"])),
    population=_obj(selected_enzyme_count=_null(UINT), attempted_enzyme_count=UINT,
        returned_enzyme_count=UINT, complete_empty_enzyme_count=UINT, recognition_match_count=_null(UINT)),
    enzyme_rows=_arr(SCHEMAS["ResultRow"]), unassociated_match_calls=_arr(UINT, unique=True),
    status=_enum("complete", "partial", "invalid", "unavailable"), issues=_arr(SCHEMAS["Issue"]))
_VALIDATORS = {name: Draft202012Validator(schema) for name, schema in SCHEMAS.items()}


def _finite(value):
    stack = [value]
    while stack:
        item = stack.pop()
        if item is None or type(item) in (str, int, bool):
            continue
        if type(item) is float and math.isfinite(item):
            continue
        if type(item) is list:
            stack.extend(item)
        elif type(item) is dict and all(type(key) is str for key in item):
            stack.extend(item.values())
        else:
            raise ValueError("restriction_finite_json_required")


def restriction_canonical(value):
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        _finite(value)
        return encoded
    except (TypeError, OverflowError, RecursionError) as error:
        raise ValueError("restriction_finite_json_required") from error


def restriction_digest(value):
    return hashlib.sha256(restriction_canonical(value).encode("utf-8")).hexdigest()


def restriction_schema(kind):
    if kind not in SCHEMAS:
        raise ValueError("restriction_unknown_record_kind:" + str(kind))
    return deepcopy(SCHEMAS[kind])


def _strict(value, schema):
    """JSON Schema permits integral floats; native counts do not."""
    if "anyOf" in schema:
        branches = [branch for branch in schema["anyOf"] if Draft202012Validator(branch).is_valid(value)]
        if not any(_strict(value, branch) for branch in branches):
            return False
    if schema.get("type") == "integer" and type(value) is not int:
        return False
    if isinstance(value, dict):
        return all(_strict(v, schema.get("properties", {}).get(k, {})) for k, v in value.items())
    if isinstance(value, list):
        prefix = schema.get("prefixItems", [])
        return all(_strict(v, prefix[i] if i < len(prefix) else schema.get("items", {}))
                   for i, v in enumerate(value))
    return True


def _require(value, code):
    if not value:
        raise ValueError("restriction_" + code)


def _decoded(value):
    def pairs(rows):
        result = {}
        for key, child in rows:
            _require(key not in result, "duplicate_dictionary_key")
            result[key] = child
        return result
    def nonfinite(_):
        raise ValueError("restriction_finite_json_required")
    result = json.loads(value, object_pairs_hook=pairs, parse_constant=nonfinite)
    _finite(result)
    return result


def _semantic(kind, value):
    if kind == "FilePin":
        path = value["path"]
        p = PurePosixPath(path)
        _require(p.is_absolute() and str(p) == path and ".." not in p.parts
            and path != "/" and not path.startswith("//")
            and not any(c in path for c in "\0\r\n\\"), "invalid_file_pin_path")
    elif kind == "CatalogRow":
        original = _decoded(value["dictionary_entry_json"])
        _require(type(original) is dict, "dictionary_object_required")
        joins = {"site": "native_site", "size": "size_nt", "ovhg": "native_ovhg", "id": "rebase_id",
                 "uri": "rebase_uri", **{k: k for k in ("fst5", "fst3", "scd5", "scd3")}}
        _require(all(restriction_canonical(original.get(k)) == restriction_canonical(value[v])
                     for k, v in joins.items()), "catalog_dictionary_conflict")
        pattern = original.get("compsite")
        expected = pattern.get("pattern") if isinstance(pattern, dict) else pattern
        _require(expected == value["native_pattern"]["text"], "catalog_pattern_conflict")
        try:
            if isinstance(pattern, dict):
                flags = pattern["flags"]
                _require(type(flags) is int, "catalog_pattern_flags_conflict")
                re.compile(expected, flags)
            else:
                flags = re.compile(expected).flags
        except (re.error, TypeError, KeyError, ValueError) as error:
            raise ValueError("restriction_catalog_pattern_conflict") from error
        _require(type(value["native_pattern"]["flags"]) is int
            and value["native_pattern"]["flags"] == flags, "catalog_pattern_flags_conflict")
        mro = value["native_class_mro"]
        cut = next((label for cls, label in (("NoCut", "no_cut"), ("TwoCuts", "two_cuts"),
                    ("OneCut", "one_cut")) if cls in mro), "unknown")
        symmetry = next((label for cls, label in (("Palindromic", "palindromic"),
                    ("NonPalindromic", "nonpalindromic")) if cls in mro), "unknown")
        meaning = ("recognition_start_1based" if cut == "no_cut" else
                   "first_base_after_cut_1based" if cut in ("one_cut", "two_cuts") else "unknown")
        _require((cut, symmetry, meaning) == (value["cut_kind"], value["symmetry"], value["position_meaning"]),
                 "native_class_meaning_conflict")
    elif kind == "Catalog":
        _semantic("FilePin", value["dictionary_file"])
        names = value["resolved_names"]
        _require(names == [r["name"] for r in value["enzymes"]]
            and [r["ordinal"] for r in value["enzymes"]] == list(range(len(names))), "catalog_identity_conflict")
        selection = value["selection"]
        _require(names == (selection["names"] if selection["kind"] == "explicit" else sorted(names)),
                 "catalog_selection_conflict")
        for row in value["enzymes"]:
            _semantic("CatalogRow", row)
            if selection["kind"] == "commercial_native_batch":
                _require(row["is_commercial"], "catalog_commercial_membership_conflict")
    elif kind == "SearchRow":
        returned = value["state"] == "returned"
        _require((value["native_search_positions_1based"] is not None) == returned, "search_positions_state_conflict")
        _require((value["search_ordinal"] is None) == (value["state"] == "not_started"), "search_ordinal_state_conflict")
        _require((value["error"] is not None) == (value["state"] == "failed"), "search_error_state_conflict")
        if value["state"] == "not_started":
            _require(value["native_on_minus_before_drop"] is None, "unstarted_native_data_conflict")
    elif kind == "MatchCall":
        _require((value["matches"] is not None) == (value["state"] == "returned"), "match_capture_state_conflict")
        _require((value["error"] is not None) == (value["state"] == "failed"), "match_error_state_conflict")
        for i, row in enumerate(value["matches"] or []):
            _require(row["match_ordinal"] == i and len({g["name"] for g in row["groups"]}) == len(row["groups"]),
                     "match_identity_conflict")
    elif kind == "NativeResult":
        request = value["request"]
        for field in ("dictionary_file", "native_source_file"):
            if value["software"][field] is not None:
                _semantic("FilePin", value["software"][field])
        _require(request["normalized_sequence"] == request["sequence"].upper(), "normalization_conflict")
        catalog = value["catalog"]
        if catalog is not None:
            _semantic("Catalog", catalog)
            _require(catalog["selection"] == request["enzyme_selection"]
                and catalog["dictionary_file"] == value["software"]["dictionary_file"]
                and catalog["biopython_version"] == value["software"]["biopython_version"], "native_catalog_conflict")
            names = catalog["resolved_names"]
            _require([r["name"] for r in value["enzyme_searches"]] == names
                and [r["catalog_ordinal"] for r in value["enzyme_searches"]] == list(range(len(names))),
                "native_search_identity_conflict")
            _require(set(value["native_batch_member_order"]) == set(names), "native_population_conflict")
        else:
            _require(not value["enzyme_searches"] and not value["native_batch_member_order"]
                and value["batch_state"] == "not_started", "native_missing_catalog_conflict")
        for row in value["enzyme_searches"]:
            _semantic("SearchRow", row)
        attempts = sorted(r["search_ordinal"] for r in value["enzyme_searches"] if r["search_ordinal"] is not None)
        _require(attempts == list(range(len(attempts))), "native_search_order_conflict")
        for i, call in enumerate(value["match_observations"]):
            _semantic("MatchCall", call)
            _require(call["call_ordinal"] == i and catalog is not None
                and all(0 <= n < len(catalog["enzymes"]) for n in call["owner_ordinals"])
                and call["linear"] == (request["topology"] == "linear"), "native_match_owner_conflict")
        if value["batch_state"] != "not_started":
            binding = request["sequence_binding"]
            _require(binding["length_nt"] == len(request["sequence"])
                and binding["content_sha256"] == hashlib.sha256(request["sequence"].encode("utf-8")).hexdigest(),
                "sequence_binding_conflict")
            _require(value["formatted_sequence"] == " " + request["normalized_sequence"], "native_formatted_sequence_conflict")
        if value["batch_state"] == "returned":
            _require(value["native_mapping_order"] == value["native_batch_member_order"]
                and all(r["state"] == "returned" for r in value["enzyme_searches"])
                and value["exception"] is None, "native_complete_mapping_conflict")
        else:
            _require(value["native_mapping_order"] is None, "native_unreturned_mapping_conflict")
    elif kind == "ResultRow":
        catalog = value["catalog_row"]
        if catalog is not None:
            _semantic("CatalogRow", catalog)
            _require((catalog["ordinal"], catalog["name"]) == (value["catalog_ordinal"], value["name"]),
                "result_catalog_identity_conflict")
        if value["positions"] is not None:
            native = value["native_search_positions_1based"]
            _require(native is not None and len(value["positions"]) == len(native), "result_positions_conflict")
            for i, row in enumerate(value["positions"]):
                _require(row["position_ordinal"] == i and row["native_position"] == native[i],
                    "result_position_identity_conflict")
    elif kind == "MappingResult":
        if value["catalog_identity"] is not None:
            _semantic("FilePin", value["catalog_identity"]["dictionary_file"])
        for row in value["enzyme_rows"]:
            _semantic("ResultRow", row)
        _require(len({r["catalog_ordinal"] for r in value["enzyme_rows"]}) == len(value["enzyme_rows"])
            and len({r["name"] for r in value["enzyme_rows"]}) == len(value["enzyme_rows"]),
            "result_row_identity_conflict")


def validate_restriction_record(kind, value):
    if kind not in SCHEMAS:
        raise ValueError("restriction_unknown_record_kind:" + str(kind))
    restriction_canonical(value)
    if not _VALIDATORS[kind].is_valid(value) or not _strict(value, SCHEMAS[kind]):
        raise ValueError("restriction_invalid_record:" + kind)
    detached = deepcopy(value)
    _semantic(kind, detached)
    return detached


def restriction_issue(code, phase, *, enzyme_ordinal=None, match_ordinal=None, position_ordinal=None):
    return validate_restriction_record("Issue", dict(code=code, phase=phase,
        enzyme_ordinal=enzyme_ordinal, match_ordinal=match_ordinal, position_ordinal=position_ordinal))


__all__ = ["restriction_schema", "validate_restriction_record", "restriction_issue",
           "restriction_canonical", "restriction_digest"]
