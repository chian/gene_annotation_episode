"""Lossless storage codec between the native provider and AppService records.

The numerical sheet has its own content binding. This wrapper retains native
requirements and diagnostics beside the calculations, without a schema change
or a second calculation. Generic summary records are deterministic projections.
"""
from copy import deepcopy

from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_comparative_systems_handoff_contracts import schema, validate_shape
from .bvbrc_comparative_systems_bundle_projection import validate_projection_failure_context

VERSION = 'bvbrc_comparative_systems_published_components_v2'
_OUTPUT_ROLES = frozenset({'family_summary', 'pathway_summary', 'pathway_ec_summary',
    'pathway_associations', 'subsystem_summary', 'subsystem_associations',
    'subsystem_overview', 'subsystem_variants', 'native_document'})
_METADATA_ROLES = frozenset({'family_feature_records', 'pathway_records', 'subsystem_records',
    'genome_records', 'family_reference', 'pathway_reference', 'subsystem_reference',
    'original_genome_population', 'producer_identity', 'reference_membership'})
_PARSER_CODES = frozenset({'format_incompatible'})
_PHASES = {'decode': 'native_decode', 'association': 'association', 'population': 'publication',
           'calculation': 'publication', 'projection': 'publication'}


def _require(condition, code):
    if not condition:
        raise ValueError('comparative_systems_publication_' + code)


def _requirement(row):
    row = validate_shape('RequirementV1', row)
    role, code = row['required_input_role'], row['code']
    _require(role in _OUTPUT_ROLES | _METADATA_ROLES, 'unhandled_role')
    _require(code in schema('DiagnosticCodeV1')['$defs']['DiagnosticCodeV1']['enum'], 'unhandled_code')
    kind = ('parser_binding' if code in _PARSER_CODES else
            'output_bytes' if role in _OUTPUT_ROLES else 'scientific_metadata')
    return {'requirement_id': row['requirement_id'], 'kind': kind, 'role': role,
            'source_refs': deepcopy(row['source_refs']), 'reason_code': code}


def encode_comparative_publication_result(result: dict, *, failure_context: dict) -> dict:
    """Validate and retain every native field in the ordinary host envelope."""
    native = validate_shape('ProviderResultV1', result)
    original = validate_projection_failure_context(failure_context)
    storage = {'version': VERSION, 'calculations': deepcopy(native['components']),
               'missing_requirements': deepcopy(native['missing_requirements']),
               'diagnostics': deepcopy(native['diagnostics']), 'failure_context': original}
    diagnostics = []
    for index, row in enumerate(native['diagnostics']):
        _require(row['phase'] in _PHASES, 'unhandled_phase')
        diagnostics.append({'code': row['code'], 'phase': _PHASES[row['phase']],
            'path': '/diagnostics/' + str(index),
            'severity': 'error' if native['status'] == 'invalid' else 'qualification',
            'evidence_refs': deepcopy(row['source_refs'])})
    return {**{key: deepcopy(native[key]) for key in ('adapter_id', 'adapter_version', 'status', 'facts', 'sheet')},
            'components': storage, 'missing_requirements': [_requirement(row) for row in native['missing_requirements']],
            'diagnostics': diagnostics}


def decode_comparative_publication_result(adapter: dict, *, sheet: dict | None, components: dict) -> tuple[dict, dict]:
    """Reconstruct the original provider object from authenticated saved values.

    The caller authenticates the two content bindings and original publication.
    This codec checks the entire storage wrapper and both deterministic summaries.
    P separately validates the saved projection against the original selector.
    """
    saved = validate_contract('AdapterResult', adapter)
    _require((saved['adapter_id'], saved['adapter_version']) == ('bvbrc_comparative_systems', '1'), 'adapter_mismatch')
    _require(type(components) is dict and set(components) == {
        'version', 'calculations', 'missing_requirements', 'diagnostics', 'failure_context'}
        and components['version'] == VERSION, 'components_wrapper_invalid')
    original = validate_projection_failure_context(components['failure_context'])
    native = validate_shape('ProviderResultV1', {
        **{key: deepcopy(saved[key]) for key in ('adapter_id', 'adapter_version', 'status', 'facts')},
        'sheet': deepcopy(sheet), 'components': deepcopy(components['calculations']),
        'missing_requirements': deepcopy(components['missing_requirements']),
        'diagnostics': deepcopy(components['diagnostics'])})
    encoded = encode_comparative_publication_result(native, failure_context=original)
    for key in ('missing_requirements', 'diagnostics'):
        _require(encoded[key] == saved[key], 'generic_' + key + '_mismatch')
    return native, original


__all__ = ['encode_comparative_publication_result', 'decode_comparative_publication_result']
