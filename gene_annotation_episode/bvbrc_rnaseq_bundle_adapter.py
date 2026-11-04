"""Dedicated RNASeq scientific adapter using shared intervention result custody."""
from . import bvbrc_intervention_bundle_adapter as shared

ADAPTER_ID = "bvbrc_rnaseq"
ADAPTER_VERSION = "1"
implementation_sha256 = shared.implementation_sha256
parameters_schema = shared.parameters_schema
requested_form_schema = shared.requested_form_schema
validate_requested_form = shared.validate_requested_form


def validate_parameters(parameters):
    parameters = shared.validate_parameters(parameters)
    if parameters["application_id"] != "RNASeq":
        raise ValueError("bvbrc_rnaseq_application_required")
    return parameters


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    parameters = validate_parameters(parameters)
    return shared.consume_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
        requested_form=requested_form, parameters=parameters)
