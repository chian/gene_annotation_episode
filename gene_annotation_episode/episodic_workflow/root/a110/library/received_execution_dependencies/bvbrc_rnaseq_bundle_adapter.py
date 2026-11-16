import gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_intervention_bundle_adapter as shared
ADAPTER_ID = 'bvbrc_rnaseq'
ADAPTER_VERSION = '1'
validate_requested_form = shared.validate_requested_form

def validate_parameters(parameters):
    parameters = shared.validate_parameters(parameters)
    if parameters['application_id'] != 'RNASeq':
        raise ValueError('bvbrc_rnaseq_application_required')
    return parameters
