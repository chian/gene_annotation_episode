from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import math
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
from gene_annotation_episode.episodic_workflow.root.a110.acquisition import AcquisitionError, SourceSnapshot
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_query import DATA_QUERY_SCHEMA, validate_data_query
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_schema import schema as data_schema
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, obj, validate_schema
SERVICE = 'bvbrc_data'
DEFAULT_BASE_URL = 'https://www.bv-brc.org/api'
COLLECTIONS = ('genome', 'genome_feature', 'protein_family_ref')
FIELD = {'type': 'string', 'pattern': '^[A-Za-z_][A-Za-z0-9_]*$'}
SCALAR = {'type': ['string', 'number', 'boolean']}
FILTER = obj({'field': FIELD, 'operator': {'enum': ['eq', 'ne', 'gt', 'lt', 'in']}, 'value': {'type': ['string', 'number', 'boolean', 'array'], 'items': SCALAR, 'minItems': 1}})
SORT = obj({'field': FIELD, 'direction': {'enum': ['asc', 'desc']}})
REQUEST_SCHEMA = obj({'collection': {'enum': list(COLLECTIONS)}, 'filters': {'type': 'array', 'items': FILTER}, 'fields': {'type': 'array', 'items': FIELD, 'uniqueItems': True}, 'sort': {'type': 'array', 'items': SORT}, 'limit': {'type': 'integer', 'minimum': 1, 'default': 25}, 'offset': {'type': 'integer', 'minimum': 0, 'default': 0}}, required=['collection', 'filters'])
SELECTOR_SCHEMA = obj({'offset': {'type': 'integer', 'minimum': 0}, 'limit': {'type': 'integer', 'minimum': 1}}, required=[])
EMPTY_ARGUMENTS = obj({})
RESULT_OPERATION = 'api.bvbrc.result'
DATA_RESULT_OPERATION = 'api.bvbrc.data.result'
_SECRET_HEADERS = {'authorization', 'proxy-authorization', 'cookie', 'set-cookie'}

def _embedded_schema(definition: dict) -> dict:
    """Expand local references before nesting under a host assignment schema.

    A JSON Pointer beginning at ``#`` resolves against the outer document, not
    a nested schema's own $defs. These finite records have no recursive types.
    """
    definitions = definition.get('$defs', {})

    def expand(value):
        if isinstance(value, dict):
            if '$ref' in value:
                reference = value['$ref']
                if not reference.startswith('#/$defs/'):
                    raise ValueError('bvbrc_nonlocal_schema_reference')
                return expand(definitions[reference.removeprefix('#/$defs/')])
            return {key: expand(child) for key, child in value.items() if key not in {'$defs', '$schema'}}
        if isinstance(value, list):
            return [expand(child) for child in value]
        return value
    return expand(definition)

def _data_request(request) -> bool:
    return isinstance(request, dict) and request.get('version') == 'bvbrc_data_request_v2'

def _validated_request(request: dict) -> dict:
    validate_schema(request, REQUEST_SCHEMA)
    for condition in request['filters']:
        operator, value = (condition['operator'], condition['value'])
        if (operator == 'in') != isinstance(value, list):
            raise ContractError('bvbrc_filter_value_shape_mismatch')
        if operator in {'gt', 'lt'} and type(value) is bool:
            raise ContractError('bvbrc_ordered_filter_requires_number_or_string')
    return deepcopy(request)

def _effective_request(request: dict, selector: dict | None=None) -> dict:
    result = _validated_request(request)
    result.setdefault('fields', [])
    result.setdefault('sort', [])
    result.setdefault('offset', 0)
    result.setdefault('limit', 25)
    if selector is not None:
        validate_schema(selector, SELECTOR_SCHEMA)
        result.update(deepcopy(selector))
    return result

def _base_url(value: str) -> str:
    if not isinstance(value, str):
        raise ContractError('bvbrc_invalid_base_url')
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.username is not None or (parsed.password is not None) or parsed.query or parsed.fragment:
        raise ContractError('bvbrc_invalid_base_url')
    return value.rstrip('/')

def _literal(value: Any) -> str:
    text = ('true' if value else 'false') if type(value) is bool else str(value)
    return urllib.parse.quote(text, safe='')

def request_url(base_url: str, request: dict) -> str:
    """Encode fields/values, retaining actual RQL operator delimiters."""
    request = _effective_request(request)
    expressions = []
    for condition in request['filters']:
        field, operator, value = (condition[key] for key in ('field', 'operator', 'value'))
        operand = '(' + ','.join((_literal(item) for item in value)) + ')' if operator == 'in' else _literal(value)
        expressions.append(f"{operator}({urllib.parse.quote(field, safe='')},{operand})")
    if request['fields']:
        expressions.append('select(' + ','.join(request['fields']) + ')')
    if request['sort']:
        expressions.append('sort(' + ','.join((('+' if item['direction'] == 'asc' else '-') + item['field'] for item in request['sort'])) + ')')
    expressions.append(f"limit({request['limit']},{request['offset']})")
    return _base_url(base_url) + '/' + request['collection'] + '/?' + '&'.join(expressions)

def _header_items(headers) -> list[list[str]]:
    return [[name, '<redacted>' if name.lower() in _SECRET_HEADERS else value] for name, value in (headers or {}).items()]

class _NoRedirect(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None

class BVBRCDataClient:
    """One explicit public GET per query, with no retry or pagination loop."""

    def __init__(self, *, base_url: str=DEFAULT_BASE_URL, _saved_transport_metadata=None):
        self.base_url = _base_url(base_url)
        if _saved_transport_metadata is not None and 'timeout' in _saved_transport_metadata:
            timeout = _saved_transport_metadata['timeout']
            if type(timeout) not in {int, float} or not math.isfinite(timeout) or timeout <= 0:
                raise ContractError('bvbrc_invalid_timeout')

    def query(self, request: dict) -> SourceSnapshot:
        request = _effective_request(request)
        address = request_url(self.base_url, request)
        headers = {'User-Agent': 'gene-annotation-episode/0.2', 'Accept': 'application/json'}
        return self._query_once(request, address, headers)

    def query_prepared(self, prepared: dict) -> SourceSnapshot:
        """Execute the selected, persisted v2 GET without compiling another query.

        The host owns preparation and recovery. This method sends one request;
        it neither selects a query nor retries, follows redirects or pages.
        """
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_schema import validate
        prepared = validate('PreparedQuery', prepared)
        native = prepared['native_request']
        address = native['url']
        expected_prefix = self.base_url + '/' + prepared['effective_request']['collection'] + '/?'
        if prepared['query_population']['base_url'] != self.base_url or not address.startswith(expected_prefix) or urllib.parse.urlsplit(address).fragment:
            raise ContractError('bvbrc_prepared_endpoint_conflict')
        headers = {item['name']: item['value'] for item in native['headers']}
        if len(headers) != len(native['headers']):
            raise ContractError('bvbrc_prepared_header_conflict')
        return self._query_once(prepared['effective_request'], address, headers, prepared_native=native)

    def _query_once(self, request, address, headers, *, prepared_native=None):
        native_request = urllib.request.Request(address, headers=headers, method='GET')
        recorded_request = {'method': 'GET', 'url': address, 'headers': deepcopy(headers)}
        if prepared_native is not None:
            recorded_request['body'] = prepared_native['body']
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(native_request) as response:
                items = _header_items(response.headers)
                transport = {'status': response.status, 'headers': {k.lower(): v for k, v in items}, 'header_items': items, 'effective_url': response.geturl(), 'request': deepcopy(recorded_request), 'representation': 'http_response_bytes', 'automatic_redirects': False}
                try:
                    content = response.read()
                except Exception as error:
                    transport.update(body_complete=False, body_capture_error=type(error).__name__)
                    snapshot = SourceSnapshot(SERVICE, address, request, datetime.now(timezone.utc).isoformat(), getattr(error, 'partial', b''), response.headers.get('content-type', 'application/octet-stream'), transport)
                    raise AcquisitionError('provider_response_body_incomplete', snapshot=snapshot, phase='http_response') from error
                transport['body_complete'] = True
                return SourceSnapshot(SERVICE, address, request, datetime.now(timezone.utc).isoformat(), content, response.headers.get('content-type', 'application/octet-stream'), transport)
        except urllib.error.HTTPError as error:
            items = _header_items(error.headers)
            transport = {'status': error.code, 'headers': {k.lower(): v for k, v in items}, 'header_items': items, 'effective_url': error.geturl(), 'request': deepcopy(recorded_request), 'representation': 'http_error_response_bytes', 'automatic_redirects': False, 'body_complete': True}
            try:
                content = error.read()
            except Exception as capture_error:
                content = getattr(capture_error, 'partial', b'')
                transport.update(body_complete=False, body_capture_error=type(capture_error).__name__)
            finally:
                error.close()
            snapshot = SourceSnapshot(SERVICE, address, request, datetime.now(timezone.utc).isoformat(), content, (error.headers or {}).get('content-type', 'application/octet-stream'), transport)
            delay = (error.headers or {}).get('retry-after')
            raise AcquisitionError('provider_redirect_not_followed' if 300 <= error.code < 400 else 'provider_http_' + str(error.code), snapshot=snapshot, phase='http_response', retry_after=float(delay) if delay and delay.isdigit() else None) from error
        except (urllib.error.URLError, TimeoutError) as error:
            timeout = isinstance(error, TimeoutError) or isinstance(getattr(error, 'reason', None), TimeoutError)
            reason = getattr(error, 'reason', error)
            raise AcquisitionError('provider_request_timeout' if timeout else 'provider_connection_failed', phase='http_request', diagnostic={'exception_type': type(error).__name__, 'reason_type': type(reason).__name__, 'message': str(reason)}) from error

class BVBRCDataService:
    service = SERVICE
    request_schema = {'oneOf': [deepcopy(REQUEST_SCHEMA), _embedded_schema(DATA_QUERY_SCHEMA)]}
    selector_schema = {'oneOf': [deepcopy(SELECTOR_SCHEMA), _embedded_schema(data_schema('ResultSelector'))]}

    def __init__(self, tool_registry, configuration=None, *, client=None, _received_configuration=False):
        self.tools = tool_registry
        configuration = dict(configuration or {})
        if set(configuration) - {'kind', 'service', 'base_url', 'timeout'}:
            raise ContractError('bvbrc_unsupported_configuration')
        if configuration.get('kind', 'api') != 'api' or configuration.get('service', SERVICE) != SERVICE:
            raise ContractError('bvbrc_configuration_service_mismatch')
        self.configuration = configuration
        if not _received_configuration and 'timeout' in configuration:
            raise ValueError('transport_timeout_configuration_not_supported')
        default_client = BVBRCDataClient(base_url=configuration.get('base_url', DEFAULT_BASE_URL), _saved_transport_metadata=configuration if _received_configuration else None)
        self.client = default_client if client is None else client

    def validate_request(self, request, scope):
        if self.tools is not None and scope is not None:
            self.tools.store.validate_scope(scope)
        return validate_data_query(request) if _data_request(request) else _validated_request(request)

    def result_catalog(self, request, selector):
        if _data_request(request):
            from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_views import validate_data_result_selector
            validate_data_result_selector(selector, request=request)
            name = DATA_RESULT_OPERATION
        else:
            _effective_request(request, selector)
            name = RESULT_OPERATION
        return [row for row in self.result_capabilities() if row['name'] == name]

    @staticmethod
    def result_capabilities():
        """Declared selected-page operation without inventing a data query."""
        return [{'name': RESULT_OPERATION, 'description': 'Acquire the selected BV-BRC page under the original filters and fields. Reuse the actual initial response for that same page; a different offset or limit makes one new request.', 'input_schema': deepcopy(EMPTY_ARGUMENTS)}, {'name': DATA_RESULT_OPERATION, 'description': "Retain the assigned BV-BRC v2 result and its complete numerical sheet, deterministic components and explicitly selected supplied-page joins. Reuse the original native request's response; only an explicit changed row page makes one GET.", 'input_schema': deepcopy(EMPTY_ARGUMENTS)}]
