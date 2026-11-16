"""Dedicated RNASeq scientific adapter using A106 intervention result custody."""
from . import bvbrc_intervention_bundle_adapter as intervention

ADAPTER_ID = "bvbrc_rnaseq"
ADAPTER_VERSION = "1"
parameters_schema = intervention.parameters_schema
requested_form_schema = intervention.requested_form_schema
validate_requested_form = intervention.validate_requested_form


def validate_parameters(parameters):
    parameters = intervention.validate_parameters(parameters)
    if parameters["application_id"] != "RNASeq":
        raise ValueError("bvbrc_rnaseq_application_required")
    return parameters


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    parameters = validate_parameters(parameters)
    return intervention.consume_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
        requested_form=requested_form, parameters=parameters)
