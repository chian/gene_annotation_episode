"""Facade for retained GenomeComparison measurements."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_bundle_contracts import parameters_schema, validate_parameters, validate_result_selector
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.bvbrc_proteome_bundle_resolution import _construct_bundle
from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.evolutionary_history_evidence.bvbrc_proteome_directional_fact_contracts import requested_form_schema, validate_requested_form
from gene_annotation_episode.episodic_workflow.episode_support.readers.expression_and_perturbation.bvbrc_proteome_directional_projection import project_requested_facts
ADAPTER_ID = 'bvbrc_proteome'
ADAPTER_VERSION = '1'

def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    built = _construct_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values, requested_form=requested_form, parameters=parameters)
    projected = project_requested_facts(**built, requested_form=requested_form, parameters=parameters)
    return dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION, **projected, sheet=built['sheet'], components=built['components'])
__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'parameters_schema', 'validate_parameters', 'validate_result_selector', 'requested_form_schema', 'validate_requested_form', 'consume_bundle']
