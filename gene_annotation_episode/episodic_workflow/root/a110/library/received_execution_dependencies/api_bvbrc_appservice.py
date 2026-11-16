from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_analysis_transport import BVBRCAnalysisClient
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import contract_schema, validate_contract, validate_request
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_tool_info import operation_catalog
from gene_annotation_episode.episodic_workflow.root.a110.domain import ContractError
SERVICE = 'bvbrc_appservice'

def _check(condition, code):
    if not condition:
        raise ContractError(code)

def _embedded_schema(name):
    schema = contract_schema(name)
    schema['$id'] = 'urn:gene-annotation:bvbrc-appservice:' + name
    return schema

class BVBRCAppServiceService:
    service = SERVICE
    request_schema = _embedded_schema('AppServiceRequest')
    selector_schema = _embedded_schema('ResultSelector')

    def __init__(self, tool_registry, configuration=None, *, client=None, publication_callback=None, _received_configuration=False):
        config = validate_contract('ServiceConfiguration', configuration)
        if not _received_configuration:
            _check('timeout' not in config, 'transport_timeout_configuration_not_supported')
        configured = BVBRCAnalysisClient(config['endpoints'], authorization_env=config.get('authorization_env'), authorization_origins=config.get('authorization_origins', ()), _saved_transport_metadata=config if _received_configuration else None)
        _check(publication_callback is None or callable(publication_callback), 'appservice_publication_callback_invalid')
        self.tools, self.configuration = (tool_registry, config)
        self.client = configured if client is None else client
        self.publication_callback = publication_callback
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_adapters import bind_adapters
        self.scientific_adapters = bind_adapters(config['scientific_adapters'])

    def validate_request(self, request, scope):
        value = validate_request(request)
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return value

    @staticmethod
    def result_capabilities():
        return operation_catalog('results')

    def result_catalog(self, request, selector):
        self.validate_request(request, None)
        validate_contract('ResultSelector', selector)
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_appservice_adapters import selected_adapter
        binding = selected_adapter(self, selector['adapter'])
        if binding is not None:
            implementation, _ = binding
            implementation.validate_parameters(selector['adapter']['parameters'])
            implementation.validate_requested_form(selector['requested_schema'])
            if (selector['adapter']['adapter_id'], selector['adapter']['adapter_version']) == ('bvbrc_proteome', '2'):
                implementation.validate_result_selector(selector)
        return self.result_capabilities()
