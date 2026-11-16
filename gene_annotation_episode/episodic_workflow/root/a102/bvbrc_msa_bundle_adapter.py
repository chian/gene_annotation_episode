"""Pinned pure MSA adapter facade for the existing AppService results owner."""
from __future__ import annotations

from . import bvbrc_alignment_bundle_contracts as contracts
from . import bvbrc_alignment_bundle_resolution as resolution

ADAPTER_ID = 'bvbrc_msa'
ADAPTER_VERSION = '1'


def validate_parameters(parameters: dict) -> dict:
    return contracts.validate_parameters(parameters, provider='msa')


def parameters_schema() -> dict:
    return contracts.parameters_schema(provider='msa')


def requested_form_schema(fields: dict) -> dict:
    return contracts.requested_form_schema(fields, provider='msa')


def validate_requested_form(requested_form: dict) -> dict:
    return contracts.validate_requested_form(requested_form, provider='msa')


def consume_bundle(bundle: dict, *, artifact_bytes: dict[str, bytes], supplied_values: list[dict], requested_form: dict, parameters: dict) -> dict:
    return resolution.consume_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
        requested_form=requested_form, parameters=parameters, provider='msa')


__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle']
