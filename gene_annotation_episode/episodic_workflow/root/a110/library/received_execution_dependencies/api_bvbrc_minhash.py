from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_analysis_protocol import prepare_rpc_request
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_analysis_transport import BVBRCAnalysisClient
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_minhash_contracts import minhash_result_selector_schema, validate_minhash_result_selector, validate_minhash_pair_metadata
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_minhash_grader import METHODS
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError, identity, obj, validate_schema
SERVICE = 'bvbrc_minhash'
RESULT_OPERATION = 'api.bvbrc.minhash.result'
NATIVE_ARGUMENTS = ('query', 'max_pvalue', 'max_distance', 'max_hits', 'include_reference', 'include_representative', 'bacterial', 'viral')
REQUEST_SCHEMA = obj({'mode': {'enum': ['genome', 'fasta']}, 'query': {'type': 'string', 'minLength': 1}, 'max_pvalue': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'max_distance': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'max_hits': {'type': 'integer', 'minimum': 0}, **{field: {'type': 'integer'} for field in NATIVE_ARGUMENTS[4:]}})
EMPTY = obj({})

def _request(request):
    validate_schema(request, REQUEST_SCHEMA)
    if request['mode'] == 'fasta':
        path = request['query']
        parts = path.split('/')
        if not path.startswith('/') or len(parts) < 4 or any((part in ('', '.', '..') for part in parts[1:])) or any((char in path for char in '\r\n\x00')):
            raise ContractError('bvbrc_minhash_workspace_fasta_path_required')
    rpc = prepare_rpc_request(METHODS[request['mode']], [request[field] for field in NATIVE_ARGUMENTS], request_id=identity('minhash_rpc', request))
    return (deepcopy(request), rpc)

class BVBRCMinhashService:
    service = SERVICE
    request_schema = deepcopy(REQUEST_SCHEMA)
    selector_schema = minhash_result_selector_schema()

    def __init__(self, tool_registry, configuration=None, *, client=None, _received_configuration=False):
        if not isinstance(configuration, dict):
            raise ContractError('bvbrc_minhash_configuration_required')
        allowed = {'kind', 'service', 'endpoint', 'timeout', 'authorization_env', 'authorization_origins'}
        if set(configuration) - allowed or 'endpoint' not in configuration or configuration.get('kind', 'api') != 'api' or (configuration.get('service', SERVICE) != SERVICE):
            raise ContractError('bvbrc_minhash_configuration_invalid')
        if not _received_configuration and 'timeout' in configuration:
            raise ValueError('transport_timeout_configuration_not_supported')
        configured = BVBRCAnalysisClient({'Minhash': configuration['endpoint']}, authorization_env=configuration.get('authorization_env'), authorization_origins=configuration.get('authorization_origins', ()), _saved_transport_metadata=configuration if _received_configuration else None)
        self.tools = tool_registry
        self.configuration = deepcopy(configuration)
        self.client = configured if client is None else client

    def validate_request(self, request, scope):
        original, _ = _request(request)
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return original

    def result_catalog(self, request, selector):
        original = self.validate_request(request, None)
        selected = validate_minhash_result_selector(selector)
        if selected:
            validate_minhash_pair_metadata(selected['pair_metadata'], request=original)
        return self.result_capabilities()

    @staticmethod
    def result_capabilities():
        return [{'name': RESULT_OPERATION, 'description': 'Read a retained BV-BRC Similar Genome Finder response, or recalculate from a selected saved MinHash sheet using explicitly supplied pair inputs. Return requested native measurements, calculated components, counts or diagnostics. Calculated values remain separate from service-reported values; supplied parameters do not establish what the remote service used. This operation makes no search or metadata request.', 'input_schema': deepcopy(EMPTY)}]
