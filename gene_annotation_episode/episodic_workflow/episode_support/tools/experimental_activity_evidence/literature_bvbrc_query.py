"""A105's own copy of the BV-BRC Data API v2 request validation and native request building.

Copied from A101's ``bvbrc_data_query`` (request shape, endpoint paths, Solr escaping, paging, the fixed public headers).
Like A101's, it sends no token: the requests are public and unauthenticated. No acquisition, file access, Store access,
retry or scoring occurs here; the request is executed by the generic ``BVBRCDataClient.query_prepared``.

What differs from A101's copy, for resolving a subject a paper names:
- an ``eq``/``in`` filter is allowed on a case-insensitive text field (``string_ci``: ``gene``, ``product``,
  ``genome_name``, ``taxon_name``), as a whole-value phrase match; A101's version refuses these fields;
- the field registry holds only the collections and fields this arm reads (taken from A101's frozen registry,
  contract ``bvbrc_data_fields_2026_10_24``): ``genome_feature``, ``genome``, ``taxonomy``, ``feature_sequence``.
"""
from __future__ import annotations

from copy import deepcopy as _deepcopy
import hashlib as _hashlib
import json as _json
import math as _math
from urllib.parse import quote as _quote, urlencode as _urlencode, urlsplit as _urlsplit

from jsonschema import Draft202012Validator as _Draft202012Validator
from jsonschema import ValidationError as _ValidationError
from jsonschema.validators import extend as _extend_validator

from gene_annotation_episode.domain import ContractError as _ContractError

__all__ = ("FIELD_CONTRACT_VERSION", "COMPILER_VERSION", "FIELD_REGISTRY", "validate_data_query", "encode_native_query")

COMPILER_VERSION = "bvbrc_solr_compiler"
FIELD_CONTRACT_VERSION = 'bvbrc_data_fields_2026_10_24'

# (name, solr_type, multi_valued, exact_filter, range_filter, existence_filter, sort, facet); every field here is stored.
_COLLECTION_ROWS = {
    'genome_feature': ('feature_id', (
        ('feature_id', 'string', False, True, False, True, True, True),
        ('genome_id', 'string', False, True, False, True, True, True),
        ('taxon_id', 'int', False, True, True, True, True, False),
        ('accession', 'string', False, True, False, True, True, True),
        ('annotation', 'string', False, True, False, True, True, True),
        ('patric_id', 'string', False, True, False, True, True, True),
        ('refseq_locus_tag', 'string', False, True, False, True, True, True),
        ('alt_locus_tag', 'string', False, True, False, True, True, True),
        ('gene', 'string_ci', False, False, False, True, True, False),
        ('product', 'string_ci', False, False, False, True, True, False),
        ('protein_id', 'string', False, True, False, True, True, True),
        ('uniprotkb_accession', 'string', False, True, False, True, True, True),
        ('feature_type', 'string', False, True, False, True, True, True),
        ('aa_length', 'int', False, True, True, True, True, False),
        ('aa_sequence_md5', 'string', False, True, False, True, True, True),
        ('public', 'boolean', False, True, False, True, True, False),
    )),
    'genome': ('genome_id', (
        ('genome_id', 'string', False, True, False, True, True, True),
        ('genome_name', 'string_ci', False, False, False, True, True, False),
        ('taxon_id', 'int', False, True, True, True, True, False),
        ('taxon_lineage_ids', 'string', True, True, False, True, False, True),
        ('taxon_lineage_names', 'string', True, True, False, True, False, True),
        ('public', 'boolean', False, True, False, True, True, False),
    )),
    'taxonomy': ('taxon_id', (
        ('taxon_id', 'string', False, True, False, True, True, True),
        ('taxon_id_i', 'int', False, True, True, True, True, False),
        ('taxon_name', 'string_ci', False, False, False, True, True, False),
        ('taxon_rank', 'string', False, True, False, True, True, True),
        ('lineage_ids', 'int', True, True, True, True, False, False),
        ('lineage_names', 'string', True, True, False, True, False, True),
    )),
    'feature_sequence': ('md5', (
        ('md5', 'string', False, True, False, True, True, True),
        ('sequence_type', 'string', False, True, False, True, True, True),
        ('sequence', 'string_raw', False, False, False, False, False, False),
    )),
}

_FIELD_KEYS = ('name', 'solr_type', 'multi_valued', 'exact_filter_supported', 'range_filter_supported',
               'existence_filter_supported', 'sort_supported', 'facet_supported')
FIELD_REGISTRY = {collection: {'unique_key': unique_key, 'fields': {row[0]: dict(zip(_FIELD_KEYS, row)) for row in rows}}
                  for collection, (unique_key, rows) in _COLLECTION_ROWS.items()}

_SCHEMA_DEFS = {
    'Field': {'type': 'string'},
    'Sort': {'type': 'object',
             'properties': {'field': {'$ref': '#/$defs/Field'}, 'direction': {'type': 'string', 'enum': ['asc', 'desc']}},
             'required': ['field', 'direction'], 'additionalProperties': False},
    'Predicate': {'oneOf': [
        {'type': 'object',
         'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'eq'}, 'value': {}},
         'required': ['field', 'operator', 'value'], 'additionalProperties': False},
        {'type': 'object',
         'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'in'},
                        'value': {'type': 'array', 'items': {'type': ['string', 'number', 'boolean']}, 'minItems': 1}},
         'required': ['field', 'operator', 'value'], 'additionalProperties': False},
        {'type': 'object',
         'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'range'},
                        'lower': {}, 'lower_inclusive': {'type': 'boolean'},
                        'upper': {}, 'upper_inclusive': {'type': 'boolean'}},
         'required': ['field', 'operator', 'lower', 'lower_inclusive', 'upper', 'upper_inclusive'],
         'additionalProperties': False},
        {'type': 'object',
         'properties': {'field': {'$ref': '#/$defs/Field'}, 'operator': {'const': 'exists'}, 'present': {'type': 'boolean'}},
         'required': ['field', 'operator', 'present'], 'additionalProperties': False}]},
    'FacetRequest': {'type': 'object',
                     'properties': {'field': {'$ref': '#/$defs/Field'}, 'offset': {'type': 'integer', 'minimum': 0},
                                    'limit': {'type': 'integer', 'minimum': 1}, 'min_count': {'type': 'integer', 'minimum': 0},
                                    'sort': {'type': 'string', 'enum': ['count', 'index']},
                                    'include_missing': {'type': 'boolean'}},
                     'required': ['field', 'offset', 'limit', 'min_count', 'sort', 'include_missing'],
                     'additionalProperties': False},
    'DataQuery': {'type': 'object',
                  'properties': {'version': {'const': 'bvbrc_data_request'}, 'collection': {'type': 'string'},
                                 'mode': {'type': 'string', 'enum': ['page', 'count', 'facet']},
                                 'filters': {'type': 'array', 'items': {'$ref': '#/$defs/Predicate'}},
                                 'fields': {'type': 'array', 'items': {'$ref': '#/$defs/Field'}, 'minItems': 1, 'uniqueItems': True},
                                 'sort': {'type': 'array', 'items': {'$ref': '#/$defs/Sort'}},
                                 'offset': {'type': 'integer', 'minimum': 0},
                                 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25000},
                                 'facet': {'$ref': '#/$defs/FacetRequest'}},
                  'required': ['version', 'collection', 'mode', 'filters'], 'additionalProperties': False},
    'PageSelector': {'type': 'object',
                     'properties': {'offset': {'type': 'integer', 'minimum': 0},
                                    'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25000}},
                     'required': ['offset', 'limit'], 'additionalProperties': False},
}


def _schema(name: str) -> dict:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": _deepcopy(_SCHEMA_DEFS), "$ref": "#/$defs/" + name}


# JSON integers are distinct from floating operands, even for values like 2.0.
_TYPE_CHECKER = _Draft202012Validator.TYPE_CHECKER.redefine_many({
    "integer": lambda _checker, value: type(value) is int,
    "number": lambda _checker, value: type(value) in (int, float),
})
_Validator = _extend_validator(_Draft202012Validator, type_checker=_TYPE_CHECKER)
_REQUEST_VALIDATOR = _Validator(_schema("DataQuery"))
_PAGE_VALIDATOR = _Validator(_schema("PageSelector"))
_SOLR_SPECIALS = frozenset('\\"+-!(){}[]^~*?:/&|')
_HEADERS = (
    ("User-Agent", "gene-annotation-episode/0.2"),
    ("Accept", "application/solr+json"),
    ("Content-Type", "application/solrquery+x-www-form-urlencoded"),
)


def _finite_copy(value, *, error_code: str = "bvbrc_data_request_schema_invalid"):
    """Copy only JSON values; do not coerce tuples, keys, numbers or omissions."""
    active = set()

    def copy(item):
        kind = type(item)
        if item is None or kind in (str, int, bool):
            return item
        if kind is float:
            if not _math.isfinite(item):
                raise _ContractError("bvbrc_nonfinite_number")
            return item
        if kind not in (dict, list) or id(item) in active:
            raise _ContractError(error_code)
        active.add(id(item))
        try:
            if kind is list:
                return [copy(child) for child in item]
            if any(type(key) is not str for key in item):
                raise _ContractError(error_code)
            return {key: copy(child) for key, child in item.items()}
        finally:
            active.remove(id(item))

    try:
        return copy(value)
    except RecursionError as error:
        raise _ContractError(error_code) from error


def _mode_conflicts(request: dict) -> None:
    mode = request.get("mode")
    if mode in ("count", "facet") and any(key in request for key in ("fields", "sort", "offset", "limit")):
        raise _ContractError("bvbrc_mode_parameter_conflict")
    if (mode in ("page", "count") and "facet" in request or mode == "facet" and "facet" not in request):
        raise _ContractError("bvbrc_mode_parameter_conflict")


def _field_spec(collection: str, field: str) -> dict:
    spec = FIELD_REGISTRY[collection]["fields"].get(field)
    if spec is None:
        raise _ContractError("bvbrc_unknown_field")
    return spec


def _typed_scalar(value, spec: dict) -> None:
    native_type = spec["solr_type"]
    kind = type(value)
    valid = (
        native_type in ("int", "long") and kind is int
        or native_type == "float" and kind in (int, float)
        or native_type == "boolean" and kind is bool
        or native_type in ("string", "string_ci", "string_raw") and kind is str
    )
    if not valid:
        raise _ContractError("bvbrc_filter_value_type_mismatch")


def _validate_predicate(collection: str, predicate: dict) -> None:
    spec = _field_spec(collection, predicate["field"])
    operator = predicate["operator"]
    if operator in ("eq", "in"):
        # The one difference from A101's copy: a case-insensitive text field is matched as a whole-value phrase.
        if not (spec["exact_filter_supported"] or spec["solr_type"] == "string_ci"):
            raise _ContractError("bvbrc_exact_filter_field_not_supported")
        value = predicate["value"]
        if operator == "in":
            if type(value) is not list or not value:
                raise _ContractError("bvbrc_filter_value_shape_mismatch")
            operands = value
        else:
            if type(value) not in (str, int, float, bool):
                raise _ContractError("bvbrc_filter_value_shape_mismatch")
            operands = [value]
        for operand in operands:
            if type(operand) not in (str, int, float, bool):
                raise _ContractError("bvbrc_filter_value_shape_mismatch")
            _typed_scalar(operand, spec)
    elif operator == "range":
        if not spec["range_filter_supported"]:
            raise _ContractError("bvbrc_range_filter_field_not_supported")
        lower, upper = predicate["lower"], predicate["upper"]
        for value in (lower, upper):
            if value is not None:
                _typed_scalar(value, spec)
        if (lower is None and upper is None
                or lower is None and predicate["lower_inclusive"]
                or upper is None and predicate["upper_inclusive"]
                or lower is not None and upper is not None and lower > upper):
            raise _ContractError("bvbrc_invalid_range_bounds")
    elif not spec["existence_filter_supported"]:
        raise _ContractError("bvbrc_exists_filter_field_not_supported")


def validate_data_query(request: dict) -> dict:
    """Return a detached, finite original request, without defaults or I/O."""
    original = _finite_copy(request)
    if type(original) is dict:
        _mode_conflicts(original)
    try:
        _REQUEST_VALIDATOR.validate(original)
    except _ValidationError as error:
        raise _ContractError("bvbrc_data_request_schema_invalid") from error
    collection = original["collection"]
    if collection not in FIELD_REGISTRY:
        raise _ContractError("bvbrc_unknown_collection")
    for field in original.get("fields", []):
        _field_spec(collection, field)
    for predicate in original["filters"]:
        _validate_predicate(collection, predicate)
    sort_fields = set()
    for sort in original.get("sort", []):
        field = sort["field"]
        if field in sort_fields:
            raise _ContractError("bvbrc_duplicate_sort_field")
        sort_fields.add(field)
        if not _field_spec(collection, field)["sort_supported"]:
            raise _ContractError("bvbrc_sort_field_not_supported")
    if "facet" in original:
        if not _field_spec(collection, original["facet"]["field"])["facet_supported"]:
            raise _ContractError("bvbrc_facet_field_not_supported")
    return original


def _base_url(value: str) -> str:
    if type(value) is not str:
        raise _ContractError("bvbrc_invalid_base_url")
    try:
        parsed = _urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            raise _ContractError("bvbrc_invalid_base_url")
    except ValueError as error:
        raise _ContractError("bvbrc_invalid_base_url") from error
    return value.rstrip("/")


def _scalar_text(value) -> str:
    return value if type(value) is str else _json.dumps(value, allow_nan=False)


def _quoted_literal(value) -> str:
    # Solr escaping and URL quoting are separate layers. A literal wildcard, quote, backslash or boolean-looking string
    # stays data.
    return '"' + "".join("\\" + char if char in _SOLR_SPECIALS else char for char in _scalar_text(value)) + '"'


def _expression(predicate: dict) -> str:
    field, operator = predicate["field"], predicate["operator"]
    if operator == "eq":
        return field + ":" + _quoted_literal(predicate["value"])
    if operator == "in":
        return field + ":(" + " OR ".join(_quoted_literal(value) for value in predicate["value"]) + ")"
    if operator == "range":
        lower = "*" if predicate["lower"] is None else _scalar_text(predicate["lower"])
        upper = "*" if predicate["upper"] is None else _scalar_text(predicate["upper"])
        left = "[" if predicate["lower_inclusive"] else "{"
        right = "]" if predicate["upper_inclusive"] else "}"
        return f"{field}:{left}{lower} TO {upper}{right}"
    exists = field + ":[* TO *]"
    return exists if predicate["present"] else "(*:* AND -" + exists + ")"


def encode_native_query(request: dict, *, base_url: str, page_selector: dict | None = None) -> dict:
    """Prepare exactly one reproducible GET without executing it (the A101 request building, unchanged).

    Row/facet windows and field/sort selections are separate from the query population. A population key describes the
    query semantics at an endpoint; it does not claim an atomic snapshot or unchanged database contents.
    """
    original = validate_data_query(request)
    endpoint = _base_url(base_url)
    selector = _finite_copy(page_selector, error_code="bvbrc_invalid_page_selector")
    if selector is not None:
        if original["mode"] != "page":
            raise _ContractError("bvbrc_invalid_page_selector")
        try:
            _PAGE_VALIDATOR.validate(selector)
        except _ValidationError as error:
            raise _ContractError("bvbrc_invalid_page_selector") from error

    unique_key = FIELD_REGISTRY[original["collection"]]["unique_key"]
    field_selection = {"requested_fields": _deepcopy(original.get("fields")), "defaulted_fields": [], "custody_added_fields": []}
    sort_selection = {"requested_sort": _deepcopy(original.get("sort")), "defaulted_sort": [], "tie_breaker_added": None}
    effective = {
        "version": "bvbrc_data_effective_query",
        "collection": original["collection"], "mode": original["mode"],
        "filters": _deepcopy(original["filters"]), "fields": [], "sort": [],
        "offset": 0, "limit": 0, "facet": _deepcopy(original.get("facet")),
    }
    if original["mode"] == "page":
        if "fields" not in original:
            field_selection["defaulted_fields"] = [unique_key]
            effective["fields"] = [unique_key]
        else:
            effective["fields"] = list(original["fields"])
            if unique_key not in effective["fields"]:
                effective["fields"].append(unique_key)
                field_selection["custody_added_fields"] = [unique_key]
        unique_sort = {"field": unique_key, "direction": "asc"}
        if not original.get("sort"):
            effective["sort"] = [unique_sort]
            sort_selection["defaulted_sort"] = _deepcopy(effective["sort"])
        else:
            effective["sort"] = _deepcopy(original["sort"])
            if unique_key not in {item["field"] for item in effective["sort"]}:
                effective["sort"].append(unique_sort)
                sort_selection["tie_breaker_added"] = _deepcopy(unique_sort)
        effective["offset"] = original.get("offset", 0)
        effective["limit"] = original.get("limit", 25)
        if selector is not None:
            effective.update(selector)

    population = {
        "version": "bvbrc_data_population", "base_url": endpoint,
        "collection": original["collection"], "filters": _deepcopy(original["filters"]),
        "visibility": "public_unauthenticated", "compiler_version": COMPILER_VERSION,
        "field_contract_version": FIELD_CONTRACT_VERSION,
    }
    try:
        canonical = _json.dumps(population, sort_keys=True, separators=(",", ":"),
                                ensure_ascii=False, allow_nan=False).encode("utf-8")
        population["population_key"] = _hashlib.sha256(canonical).hexdigest()
        expressions = [_expression(predicate) for predicate in effective["filters"]]
        query = ("*:*" if not expressions else expressions[0] if len(expressions) == 1
                 else " AND ".join("(" + expression + ")" for expression in expressions))
        parameters = [("q", query), ("rows", str(effective["limit"])), ("start", str(effective["offset"]))]
        if effective["mode"] == "page":
            parameters.extend([
                ("fl", ",".join(effective["fields"])),
                ("sort", ",".join(item["field"] + " " + item["direction"] for item in effective["sort"])),
            ])
        elif effective["mode"] == "facet":
            facet = effective["facet"]
            parameters.extend([
                ("facet", "true"), ("facet.field", facet["field"]),
                ("facet.limit", str(facet["limit"])), ("facet.offset", str(facet["offset"])),
                ("facet.mincount", str(facet["min_count"])),
                ("facet.missing", "true" if facet["include_missing"] else "false"),
                ("facet.sort", facet["sort"]),
            ])
        url = endpoint + "/" + original["collection"] + "/?" + _urlencode(parameters, quote_via=_quote, safe="")
    except (ValueError, UnicodeError) as error:
        raise _ContractError("bvbrc_data_request_schema_invalid") from error

    return {
        "version": "bvbrc_data_prepared", "service": "bvbrc_data",
        "original_request": original, "page_selector": selector,
        "effective_request": effective, "query_population": population,
        "field_selection": field_selection, "sort_selection": sort_selection,
        "request_profile": "solr_query_solr_json",
        "native_request": {
            "method": "GET", "url": url,
            "headers": [{"name": name, "value": value} for name, value in _HEADERS],
            "body": None,
            "query_parameters": [{"name": name, "value": value} for name, value in parameters],
        },
    }
