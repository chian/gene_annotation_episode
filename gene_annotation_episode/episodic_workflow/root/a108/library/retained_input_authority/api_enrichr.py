"""Finite Enrichr HTTP stages and publication of their retained native table.

The API episode owns selected intents, stage retention and original-action
authentication. This adapter supplies deterministic wire requests and makes one
HTTP call per invocation; it never chooses a retry or calculates enrichment.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
from urllib.parse import urlsplit
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.enrichr_contracts import validate_enrichr_request
PREPARED_VERSION = 'enrichr_prepared_protocol_v1'
PROTOCOL_VERSION = 'enrichr_protocol_snapshot_v1'
WIRE_PROFILE = 'enrichr_direct_http_v1'
QUERY = 'api.enrichr.query'
RESULT = 'api.enrichr.result'
_CONFIG_FIELDS = {'kind', 'service', 'protocol_profile', 'base_url', 'timeout', 'response_byte_limit'}
_PREPARED_FIELDS = {'version', 'operation', 'request', 'configuration', 'mutates_remote', 'cache_original'}

def _require(condition, code):
    if not condition:
        raise ValueError(code)

def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, OverflowError, RecursionError) as error:
        raise ValueError('enrichr_finite_json_required') from error

def _positive(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and (value > 0)
    except OverflowError:
        return False

def validate_enrichr_configuration(configuration):
    """Validate the exact selected API root; no route/default is substituted."""
    _require(type(configuration) is dict and set(configuration) == _CONFIG_FIELDS, 'enrichr_configuration_invalid')
    _canonical(configuration)
    value = deepcopy(configuration)
    _require(value['kind'] == 'api' and value['service'] == 'enrichr' and (value['protocol_profile'] in ('standard_enrichr_v1', 'speedrichr_v1')) and (type(value['base_url']) is str) and value['base_url'] and (value['base_url'] == value['base_url'].strip()) and (not any((character in value['base_url'] for character in '\r\n\t'))) and (not value['base_url'].endswith('/')) and _positive(value['timeout']) and (type(value['response_byte_limit']) is int) and (value['response_byte_limit'] > 0), 'enrichr_configuration_invalid')
    try:
        address = urlsplit(value['base_url'])
        valid = address.scheme in ('http', 'https') and bool(address.hostname) and (address.username is None) and (address.password is None) and (not address.query) and (not address.fragment)
        address.port
    except ValueError as error:
        raise ValueError('enrichr_configuration_invalid') from error
    _require(valid, 'enrichr_configuration_invalid')
    return value

def _prepared(value, *, query_only=False):
    _require(type(value) is dict and set(value) == _PREPARED_FIELDS and (value['version'] == PREPARED_VERSION) and (value['operation'] in (QUERY, RESULT)), 'enrichr_prepared_invalid')
    request = validate_enrichr_request(value['request'])
    query = value['operation'] == QUERY
    _require(type(value['mutates_remote']) is bool and value['mutates_remote'] == query and (type(value['cache_original']) is bool) and (value['cache_original'] != query) and (not query_only or query), 'enrichr_prepared_invalid')
    if query:
        configuration = validate_enrichr_configuration(value['configuration'])
        _require(configuration['protocol_profile'] == request['protocol_profile'], 'enrichr_configuration_profile_conflict')
    else:
        _require(value['configuration'] is None, 'enrichr_prepared_invalid')
        configuration = None
    return {**deepcopy(value), 'request': request, 'configuration': configuration}
