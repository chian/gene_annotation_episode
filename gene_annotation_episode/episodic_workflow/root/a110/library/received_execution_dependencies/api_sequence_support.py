from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.api_services import object_schema, validate_service_configuration
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.sequence_support_contracts import REQUEST_SCHEMA, SELECTOR_SCHEMA, validate_sequence_support_request, validate_sequence_support_selector
EMPTY = object_schema({})
COLLECT = 'api.sequence_support.collect'

class SequenceSupportService:
    service = 'sequence_support'
    request_schema = REQUEST_SCHEMA
    selector_schema = SELECTOR_SCHEMA

    def __init__(self, tool_registry, configuration=None, *, client=None):
        self.configuration = validate_service_configuration(self.service, configuration or {})
        self.tools = tool_registry
        self.client = tool_registry.clients if client is None else client

    def validate_request(self, request, scope):
        request = validate_sequence_support_request(request)
        if scope is not None:
            self.tools.store.validate_scope(scope)
        return request

    @staticmethod
    def result_capabilities():
        return [{'name': COLLECT, 'description': 'Publish the original retained molecular sequence response and the explicit selected records or CDSs.', 'input_schema': deepcopy(EMPTY), 'instructions': 'Apply the parent-selected original result selector to the retained response. Keep native source identities, ordinals, qualifiers and partial failures. No new GET, candidate selection, provider fallback or scientific confidence is added.'}]

    def result_catalog(self, request, selector):
        validate_sequence_support_selector(request, selector)
        return self.result_capabilities()
