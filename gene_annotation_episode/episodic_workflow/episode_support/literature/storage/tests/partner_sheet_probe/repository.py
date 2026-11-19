"""A working partner-sheet repository for the sheet-update tests: it saves each sheet as a ``source`` record whose
request artifact names the acting episode and the arguments, and publishes through the library's ``publication``."""
import json

from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_sheet_updates import publication
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError

PROVIDER = 'literature.experimental.partner'


def save_sheet(store, episode_id, arguments, version, origin):
    """Write a sheet and its request; the sheet record's reference."""
    request_ref = store.artifact(json.dumps({'episode_id': episode_id, 'arguments': arguments}, sort_keys=True),
                                 'application/json')
    content_ref = store.artifact(json.dumps({'arguments': arguments, 'version': version}, sort_keys=True),
                                 'application/json')
    return store.put('source', {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': content_ref,
                                'text_ref': None, 'request_ref': request_ref, 'version': version,
                                'retrieved_at': None}, origin=origin)['id']


class ProbePartnerRepository:
    provider = PROVIDER
    components = ('cell',)

    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id

    def read(self, ref):
        return self.store.get(ref)

    def fact_cells(self, context, refs, components):
        return [{'sheet_ref': ref, 'component': component} for ref in refs for component in components]

    @publication
    def populate(self, context, arguments, operation_key):
        if arguments['input']['sheet_ref'] in arguments.get('refuse', []):
            raise ContractError('partner_input_component_not_received')
        ref = save_sheet(self.store, context.episode_id, arguments, operation_key, 'tool')
        return {'status': 'completed', 'result': {'sheet_ref': ref}, 'record_refs': [ref],
                'operation_ref': operation_key}
