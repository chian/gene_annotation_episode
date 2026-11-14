import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_intervention_bundle_adapter as shared
ADAPTER_ID = 'bvbrc_tnseq'
ADAPTER_VERSION = '1'
implementation_sha256 = shared.implementation_sha256
validate_requested_form = shared.validate_requested_form

def validate_parameters(parameters):
    parameters = shared.validate_parameters(parameters)
    if parameters['application_id'] != 'TnSeq':
        raise ValueError('bvbrc_tnseq_application_required')
    return parameters
