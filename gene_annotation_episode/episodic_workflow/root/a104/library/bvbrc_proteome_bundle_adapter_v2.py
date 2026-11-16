"""Explicitly selected v2 facade for retained GenomeComparison measurements."""
from .bvbrc_proteome_bundle_v2_contracts import parameters_schema_v2 as parameters_schema, validate_parameters_v2 as validate_parameters, validate_result_selector_v2 as validate_result_selector
from .bvbrc_proteome_bundle_v2_resolution import _construct_bundle
from .bvbrc_proteome_directional_fact_contracts import requested_form_schema_v2 as requested_form_schema, validate_requested_form_v2 as validate_requested_form
from .bvbrc_proteome_directional_projection import project_requested_facts_v2
ADAPTER_ID = 'bvbrc_proteome'
ADAPTER_VERSION = '2'

def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    built = _construct_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values, requested_form=requested_form, parameters=parameters)
    projected = project_requested_facts_v2(**built, requested_form=requested_form, parameters=parameters)
    return dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION, **projected, sheet=built['sheet'], components=built['components'])
__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'parameters_schema', 'validate_parameters', 'validate_result_selector', 'requested_form_schema', 'validate_requested_form', 'consume_bundle']
