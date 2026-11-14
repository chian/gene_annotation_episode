"""Pinned pure MSA adapter facade for the existing AppService results owner."""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import bvbrc_alignment_bundle_contracts as contracts
from . import bvbrc_alignment_bundle_resolution as resolution

ADAPTER_ID = 'bvbrc_msa'
ADAPTER_VERSION = '1'
_DEPENDENCIES = (
    'bvbrc_alignment_bundle_contracts.py', 'bvbrc_alignment_bundle_resolution.py',
    'bvbrc_alignment_bundle_projection.py', 'bvbrc_msa_bundle_adapter.py', 'bvbrc_metacats_bundle_adapter.py',
    'bvbrc_alignment_provider_contracts.py', 'bvbrc_alignment_associations.py',
    'bvbrc_alignment_values.py', 'bvbrc_msa_provider_contracts.py', 'bvbrc_msa_inputs.py',
    'bvbrc_msa_grader.py', 'bvbrc_msa_xmfa_inputs.py', 'bvbrc_msa_formats.py',
    'bvbrc_msa_format_contracts.py', 'bvbrc_msa_calculators.py', 'bvbrc_msa_calculation_contracts.py',
    'bvbrc_metacats_provider_contracts.py', 'bvbrc_metacats_inputs.py', 'bvbrc_metacats_grader.py',
    'bvbrc_metacats_associations.py', 'bvbrc_metacats_association_contracts.py',
    'bvbrc_metacats_formats.py', 'bvbrc_metacats_format_contracts.py', 'bvbrc_metacats_input_formats.py',
    'bvbrc_metacats_calculators.py', 'bvbrc_metacats_calculation_contracts.py',
    'bvbrc_metacats_biological_calculators.py', 'bvbrc_metacats_biological_contracts.py',
    'bvbrc_metacats_adequacy.py', 'bvbrc_contingency_math.py',
    'phylogeny_formats.py', 'phylogeny_format_contracts.py', 'phylogeny_calculators.py',
    'phylogeny_calculation_contracts.py', 'xmfa_formats.py', 'xmfa_format_contracts.py',
    'xmfa_sources.py', 'xmfa_source_contracts.py', 'xmfa_coordinates.py',
    'xmfa_calculators.py', 'xmfa_calculation_contracts.py',
    'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json',
)


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


def implementation_sha256() -> str:
    """Configuration-only digest; grading and saved reads do not read files."""
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        content = Path(__file__).with_name(name).read_bytes()
        result.update(name.encode() + b'\0' + str(len(content)).encode() + b'\0' + content)
    return result.hexdigest()


__all__ = ['ADAPTER_ID', 'ADAPTER_VERSION', 'validate_parameters', 'parameters_schema',
    'requested_form_schema', 'validate_requested_form', 'consume_bundle', 'implementation_sha256']
