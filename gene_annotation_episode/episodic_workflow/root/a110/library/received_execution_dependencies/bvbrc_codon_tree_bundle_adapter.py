from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_phylogeny_bundle_contracts import validate_requested_form
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_phylogeny_bundle_contracts import validate_parameters as _parameters
ADAPTER_ID = 'bvbrc_codon_tree'
ADAPTER_VERSION = '1'

def validate_parameters(parameters):
    return _parameters(parameters, provider='codon_tree')
