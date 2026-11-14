"""Explicitly selected v2 facade for retained GenomeComparison measurements."""
import hashlib
from pathlib import Path

from .bvbrc_proteome_bundle_v2_contracts import (
    parameters_schema_v2 as parameters_schema, validate_parameters_v2 as validate_parameters,
    validate_result_selector_v2 as validate_result_selector,
)
from .bvbrc_proteome_bundle_v2_resolution import _construct_bundle
from .bvbrc_proteome_directional_fact_contracts import (
    requested_form_schema_v2 as requested_form_schema, validate_requested_form_v2 as validate_requested_form,
)
from .bvbrc_proteome_directional_projection import project_requested_facts_v2
from .bvbrc_proteome_bundle_adapter import _DEPENDENCIES as _LEGACY_DEPENDENCIES

ADAPTER_ID = 'bvbrc_proteome'
ADAPTER_VERSION = '2'
_DEPENDENCIES = tuple(sorted(set(_LEGACY_DEPENDENCIES) | {
    'bvbrc_proteome_bundle_adapter_v2.py', 'bvbrc_proteome_bundle_v2_contracts.py',
    'bvbrc_proteome_bundle_v2_schemas.json', 'bvbrc_proteome_bundle_v2_resolution.py',
    'bvbrc_proteome_numerical_sheet.py', 'bvbrc_proteome_directional_saved_validation.py',
    'bvbrc_proteome_directional.py', 'bvbrc_proteome_directional_contracts.py',
    'bvbrc_proteome_directional_schemas.json', 'bvbrc_proteome_directional_numerical_contracts.py',
    'bvbrc_proteome_directional_numerical_schemas.json', 'bvbrc_proteome_directional_sheet.py',
    'bvbrc_proteome_directional_geometry.py', 'bvbrc_proteome_directional_calculators.py',
    'bvbrc_proteome_directional_fact_contracts.py', 'bvbrc_proteome_directional_projection.py',
    'blast_pairwise_grader.py', 'blast_search.py',
}))


def implementation_sha256():
    result = hashlib.sha256()
    for name in _DEPENDENCIES:
        raw = Path(__file__).with_name(name).read_bytes()
        result.update(name.encode() + b'\0' + str(len(raw)).encode() + b'\0' + raw)
    return result.hexdigest()


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters):
    built = _construct_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values,
                              requested_form=requested_form, parameters=parameters)
    projected = project_requested_facts_v2(**built, requested_form=requested_form, parameters=parameters)
    return dict(adapter_id=ADAPTER_ID, adapter_version=ADAPTER_VERSION, **projected,
                sheet=built['sheet'], components=built['components'])


__all__ = ['ADAPTER_ID','ADAPTER_VERSION','parameters_schema','validate_parameters','validate_result_selector',
           'requested_form_schema','validate_requested_form','implementation_sha256','consume_bundle']
