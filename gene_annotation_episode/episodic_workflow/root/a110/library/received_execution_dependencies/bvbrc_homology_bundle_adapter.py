from __future__ import annotations
from copy import deepcopy
import math
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_appservice_contracts import ContractValidationError, _finite_json, _same, _Validator, contract_schema, validate_contract
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_homology_inputs import FIELDS, FORMATS, _index, _text
ADAPTER_ID = 'bvbrc_homology'
ADAPTER_VERSION = '1'
PARAMETERS_VERSION = 'bvbrc_homology_bundle_parameters_v1'
_PRIMARY = {'raw': 'blast_json15_raw', 'processed': 'homology_processed_json', 'tabular': 'blast_tabular'}
_ROLES = tuple(FORMATS)

def _object(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}
_STRING = {'type': 'string', 'minLength': 1}
_EVIDENCE_SCHEMA = contract_schema('SourceEvidence')
PARAMETERS_SCHEMA = _object({'version': {'const': PARAMETERS_VERSION}, 'scientific_mode': {'enum': ['database_identification', 'pairwise_correspondence']}, 'primary_representation': {'enum': list(_PRIMARY)}, 'artifact_source_refs': _object({role: _nullable(_STRING) for role in _ROLES}), 'scientific_inputs': _nullable({'$ref': '#/$defs/SourceEvidence'}), 'tabular_fields': _nullable({'const': FIELDS}), 'database_model': _nullable(_object({'temperature_bits': {'type': 'number', 'exclusiveMinimum': 0}, 'function_priors': _nullable({'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0}})}))})
PARAMETERS_SCHEMA['$defs'] = deepcopy(_EVIDENCE_SCHEMA['$defs'])

def _validate(schema, value, code):
    _finite_json(value)
    error = next(_Validator(schema).iter_errors(value), None)
    if error is not None:
        path = ''.join(('/' + str(k).replace('~', '~0').replace('/', '~1') for k in error.absolute_path))
        raise ContractValidationError(code, path)
    return deepcopy(value)

def validate_parameters(parameters: dict) -> dict:
    result = _validate(PARAMETERS_SCHEMA, parameters, 'homology_adapter_parameters_invalid')
    if result['scientific_inputs'] is not None:
        validate_contract('SourceEvidence', result['scientific_inputs'])
    if result['scientific_mode'] == 'pairwise_correspondence' and result['database_model'] is not None:
        raise ContractValidationError('homology_database_model_unused_for_pairwise', '/database_model')
    model = result['database_model']
    if model is not None:
        numbers = [model['temperature_bits'], *(model['function_priors'] or {}).values()]
        try:
            valid = all((math.isfinite(value) for value in numbers))
        except OverflowError:
            valid = False
        if not valid:
            raise ContractValidationError('homology_adapter_parameters_invalid', '/database_model')
    return result
_QUERY_METRICS = {'reported_hit_count': ('integer', 'native'), 'query_length': ('integer', 'native'), 'sequence_group_count': ('integer', 'coverage'), 'groups_with_explicit_function': ('integer', 'coverage'), 'groups_without_explicit_function': ('integer', 'coverage'), 'matched_metadata_row_count': ('integer', 'coverage'), 'duplicate_native_hit_count': ('integer', 'dependence'), 'unannotated_reference_kernel_fraction': ('number', 'kernel')}
_HIT_METRICS = {'hsp_count': 'integer', 'maximum_bit_score': 'number', 'minimum_evalue': 'number', 'observed_paired_query_positions': 'integer', 'observed_paired_reference_positions': 'integer', 'query_paired_coverage': 'number', 'reference_paired_coverage': 'number', 'unique_pair_count': 'integer', 'overlap_pair_representations': 'integer', 'reference_length': 'integer', 'query_span_coverage': 'number', 'reference_span_coverage': 'number'}
_HSP_METRICS = {'hsp_bit_score': ('number', 'native_scores', 'bit_score'), 'hsp_score': ('number', 'native_scores', 'score'), 'hsp_evalue': ('number', 'native_scores', 'evalue'), 'alignment_columns': ('integer', 'counts', 'alignment_columns'), 'paired_columns': ('integer', 'counts', 'paired_columns'), 'identical_pairs': ('integer', 'counts', 'identical_pairs'), 'query_gap_columns': ('integer', 'counts', 'query_gap_columns'), 'reference_gap_columns': ('integer', 'counts', 'reference_gap_columns'), 'hsp_query_paired_coverage': ('number', 'fractions', 'query_paired_coverage'), 'hsp_reference_paired_coverage': ('number', 'fractions', 'reference_paired_coverage'), 'paired_identity': ('number', 'fractions', 'paired_identity'), 'alignment_identity': ('number', 'fractions', 'alignment_identity'), 'substitution_columns': ('integer', 'supplement', 'substitution_columns'), 'query_gap_runs': ('integer', 'supplement', 'query_gap_runs'), 'reference_gap_runs': ('integer', 'supplement', 'reference_gap_runs')}
_PAIR_METRICS = {'pairwise_query_coverage': ('number', 'fractions', 'query_paired_coverage'), 'pairwise_reference_coverage': ('number', 'fractions', 'reference_paired_coverage'), 'pairwise_identity': ('number', 'fractions', 'paired_identity'), 'pairwise_distinct_pairs': ('integer', 'counts', 'distinct_residue_pairs')}
_FUNCTION_METRICS = {'conditional_function_weight': ('number', 'unadjusted_probabilities'), 'representation_adjusted_function_weight': ('number', 'representation_adjusted_probabilities'), 'function_kernel_mass': ('number', 'function_masses'), 'database_function_count': ('integer', 'database_sequence_count'), 'database_function_fraction': ('number', 'database_fraction')}
_DISTRIBUTION_METRICS = {'conditional_function_weights': 'unadjusted_probabilities', 'representation_adjusted_function_weights': 'representation_adjusted_probabilities'}
_TAXON_METRICS = {'same_taxon_pair_count': 'integer', 'comparable_pair_count': 'integer', 'same_taxon_pair_fraction': 'number', 'target_matching_groups': 'integer', 'target_conflicting_groups': 'integer', 'target_matching_fraction': 'number', 'unknown_group_count': 'integer', 'ambiguous_group_count': 'integer'}
_QUALITY_FIELDS = {'completeness_fraction', 'contamination_fraction', 'contig_count', 'contig_n50', 'total_sequence_length'}

def _selector_type(selection):
    if type(selection) is not dict or not _text(selection.get('metric')):
        raise ContractValidationError('homology_fact_selector_invalid')
    metric, fields = (selection['metric'], {'metric', 'report_index'})
    if metric == 'missing_requirements':
        fields, value_type = ({'metric'}, 'requirements')
    elif metric in _QUERY_METRICS:
        value_type = _QUERY_METRICS[metric][0]
    elif metric in _HIT_METRICS:
        fields.add('hit_index')
        value_type = _HIT_METRICS[metric]
    elif metric in _HSP_METRICS:
        fields.update(('hit_index', 'hsp_index'))
        value_type = _HSP_METRICS[metric][0]
    elif metric in _PAIR_METRICS:
        value_type = _PAIR_METRICS[metric][0]
    elif metric in _FUNCTION_METRICS:
        fields.add('function')
        value_type = _FUNCTION_METRICS[metric][0]
    elif metric in _DISTRIBUTION_METRICS:
        value_type = 'distribution'
    elif metric in _TAXON_METRICS:
        fields.add('rank')
        value_type = _TAXON_METRICS[metric]
    elif metric == 'source_quality_mean':
        fields.update(('field', 'method'))
        value_type = 'number'
    elif metric in {'tabular_mismatch', 'tabular_gapopen', 'tabular_pident'}:
        fields.add('line')
        value_type = 'number' if metric == 'tabular_pident' else 'integer'
    else:
        raise ContractValidationError('homology_fact_metric_unknown')
    if set(selection) != fields:
        raise ContractValidationError('homology_fact_selector_invalid')
    for field in fields - {'metric'}:
        value = selection[field]
        valid = _index(value) if field in {'report_index', 'hit_index', 'hsp_index'} else type(value) is int and value > 0 if field == 'line' else value in _QUALITY_FIELDS if field == 'field' and type(value) is str else _text(value)
        if not valid:
            raise ContractValidationError('homology_fact_selector_invalid')
    return value_type

def requested_form_schema(fields: dict) -> dict:
    """Build the closed original requested form from exact metric selections."""
    _finite_json(fields)
    if type(fields) is not dict or not fields or any((not _text(k) for k in fields)):
        raise ContractValidationError('homology_requested_form_invalid')
    properties = {}
    for name, selection in fields.items():
        kind = _selector_type(selection)
        if kind == 'requirements':
            node = {'type': 'array', 'items': contract_schema('AcquisitionRequirement')['$defs']['AcquisitionRequirement']}
        elif kind == 'distribution':
            node = {'type': ['array', 'null'], 'items': _object({'function': _STRING, 'weight': {'type': 'number', 'minimum': 0, 'maximum': 1}})}
        else:
            node = {'type': [kind, 'null']}
        properties[name] = {**node, 'x-homology-fact': deepcopy(selection)}
    return _object(properties)

def validate_requested_form(requested_form: dict) -> dict:
    _finite_json(requested_form)
    if type(requested_form) is not dict or set(requested_form) != {'type', 'properties', 'required', 'additionalProperties'} or type(requested_form.get('properties')) is not dict:
        raise ContractValidationError('homology_requested_form_invalid')
    selections = {}
    for name, node in requested_form['properties'].items():
        if type(node) is not dict or 'x-homology-fact' not in node:
            raise ContractValidationError('homology_fact_selector_required')
        selections[name] = node['x-homology-fact']
    expected = requested_form_schema(selections)
    required = requested_form.get('required')
    if type(required) is not list or any((type(v) is not str for v in required)) or len(required) != len(set(required)) or (set(required) != set(selections)):
        raise ContractValidationError('homology_requested_form_invalid')
    expected['required'] = required
    if not _same(expected, requested_form):
        raise ContractValidationError('homology_requested_form_invalid')
    return deepcopy(requested_form)
