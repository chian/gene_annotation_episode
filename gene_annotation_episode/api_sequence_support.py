"""Single selected molecular request under the common API episode.

The service executes explicit operands and publishes the retained response. It
does not choose a provider, candidate, locus, feature, retry or investigation.
"""
from copy import deepcopy

from .api_services import event, object_schema, validate_service_configuration, validate_value
from .sequence_support_contracts import (
    REQUEST_SCHEMA, SELECTOR_SCHEMA, validate_sequence_support_request,
    validate_sequence_support_selector, validate_sequence_support_snapshot,
)

EMPTY = object_schema({})
COLLECT = 'api.sequence_support.collect'
NAMES = {'ncbi_gene': 'api.sequence_support.gene',
         'get_gene_coding_sequence': 'get_gene_coding_sequence',
         'get_plasmid_sequence': 'get_plasmid_sequence'}


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

    def capabilities(self):
        descriptions = {
            'ncbi_gene': 'Retrieve the explicit NCBI Gene IDs as native XML, preserving all loci and recursive sequence relationships.',
            'get_gene_coding_sequence': 'Retrieve the explicit Nucleotide record for selected CDS extraction through the common sequence extraction sheet and calculator.',
            'get_plasmid_sequence': 'Retrieve the explicitly selected NCBI record or Addgene page, preserving native sequence alternatives and availability.',
        }
        shared = ('Use the configured API resource with an immutable explicit request and max_bytes. '
            'The selected action has empty arguments and performs one bounded GET. '
            'Obtain the original retained response through api.sequence_support.collect with an explicit '
            'result selector; collection does not repeat acquisition. Source annotations describe their '
            'original subjects and do not assign a function or identity to the investigated target. '
            'Keep failed, incomplete, unavailable and measured empty results distinct. ')
        instructions = {
            'ncbi_gene': ('Set operation=ncbi_gene and supply the exact gene_ids. The result selector '
                'view=gene retains every original returned record and locus; choose any later locus, '
                'accession and version explicitly in a separate selected request. No first record or '
                'coordinate conversion is selected by this operation.'),
            'get_gene_coding_sequence': ('Supply the exact accession and explicit dna/rna processing '
                'model. Set result selector view=cds and features to the ordered list of native '
                'record_ordinal/feature_ordinal pairs. These are original source ordinals, not filtered '
                'array positions. Whole native features and qualifiers are retained. The selected '
                'CDS views use the existing extraction sheet/calculator; extraction correctness is '
                'not gene-function confidence. Mixed orientations and unsupplied remote locations '
                'currently return specific unavailable states.'),
            'get_plasmid_sequence': ('Choose provider explicitly: ncbi requires an accession and '
                'dna/rna processing model; addgene requires the exact numeric plasmid_id. Use result '
                'selector view=sequences with explicit native record_ordinals. Addgene full/partial '
                'categories remain source labels. An authentication banner or download link supplies '
                'no bases. Do not infer topology or replace an unavailable provider with another.'),
        }
        return [{'name': NAMES[operation], 'description': descriptions[operation],
                 'input_schema': deepcopy(EMPTY), 'instructions': shared + instructions[operation]}
                for operation in NAMES]

    @staticmethod
    def result_capabilities():
        return [{'name': COLLECT, 'description': 'Publish the original retained molecular sequence response and the explicit selected records or CDSs.',
                 'input_schema': deepcopy(EMPTY), 'instructions':
                    'Apply the parent-selected original result selector to the retained response. '
                    'Keep native source identities, ordinals, qualifiers and partial failures. '
                    'No new GET, candidate selection, provider fallback or scientific confidence is added.'}]

    def launch_catalog(self, request):
        request = self.validate_request(request, None)
        return [row for row in self.capabilities() if row['name'] == NAMES[request['operation']]]

    def result_catalog(self, request, selector):
        validate_sequence_support_selector(request, selector)
        return self.result_capabilities()

    def prepare(self, name, request, arguments, *, scope, previous_events, handle=None, selector=None):
        request = self.validate_request(request, scope)
        validate_value(arguments, EMPTY, 'sequence_support_action_arguments_invalid')
        if name == COLLECT:
            selector = validate_sequence_support_selector(request, selector)
        elif name == NAMES[request['operation']] and selector is None:
            selector = None
        else:
            raise ValueError('sequence_support_operation_not_available')
        return {'operation': name, 'mutates_remote': False, 'request': request,
                'selector': selector, 'cache_original': name == COLLECT}

    def invoke(self, prepared):
        if prepared['cache_original']:
            raise ValueError('sequence_support_collect_requires_original_response')
        request = prepared['request']
        if request['operation'] == 'ncbi_gene':
            return self.client.ncbi_gene(request['gene_ids'], max_bytes=request['max_bytes'])
        if request.get('provider') == 'addgene':
            return self.client.addgene_sequences(request['plasmid_id'], max_bytes=request['max_bytes'])
        return self.client.ncbi_sequence(request['accession'], max_bytes=request['max_bytes'])

    def decode(self, prepared, snapshot):
        native = validate_sequence_support_snapshot(snapshot, request=prepared['request'])
        return event('response', 'completed', native_handle={}, handoff_ready=True, result_available=True,
                     facts={'retained_bytes': len(snapshot.content), 'representation': native['representation'],
                            'response_complete': True})

    def publish(self, request, selector, snapshot, scope, operation_key, *, submission_snapshot=None, handle=None):
        from .sequence_support_publication import publish_sequence_support
        return publish_sequence_support(self.tools, request=request, selector=selector,
            snapshot=snapshot, scope=scope, operation_key=operation_key)

    def prepare_observation(self, request, handle, *, scope):
        self.validate_request(request, scope)
        return None


__all__ = ['SequenceSupportService']
