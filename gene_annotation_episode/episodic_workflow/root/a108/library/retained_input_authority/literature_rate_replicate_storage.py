"""Selected raw-table rate summaries and exact, source-bound saved returns.

The existing reader and calculator own measurement parsing and arithmetic.
This adapter owns selection, persistence and custody, and never reinterprets or
recalculates scientific inputs when reading a committed sheet.
"""
from __future__ import annotations
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a108.domain import obj
from gene_annotation_episode.episodic_workflow.root.a108.library.literature_experimental_contracts import ORIGINS, RATE_UNITS, REPRESENTATIONS, SAMPLING_BASES
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_rate_replicate_inputs import GROUP_FIELDS
NAMESPACE = 'literature_rate_replicate_cells'
COMPONENTS = ('reference_rate', 'test_rate', 'rate_difference', 'retained_fraction', 'fractional_decrease', 'paired_sample_sd', 'difference_se', 'reference_sample_sd', 'test_sample_sd', 'reference_mean_se', 'test_mean_se')
REASONS = ('numerical_model_range', 'no_point_observations', 'insufficient_measurement_count', 'conflicting_observation_identity', 'censored_measurement', 'nondetection_without_point', 'source_measurement_unavailable', 'sampling_basis_mismatch', 'incompatible_rate_dimensions', 'incomplete_sampling_units', 'unit_model_unspecified', 'missing_reference_group', 'missing_test_group', 'endpoint_mismatch', 'normalization_mismatch', 'zero_reference_rate', 'dependence_unknown', 'paired_model_not_selected', 'shared_sampling_units', 'pairing_incomplete')
CONDITIONS = ('iid_units', 'independent_groups', 'iid_unit_pairs')
UNIT_CODES = (*RATE_UNITS, 'fraction', None)
_TEXT = {'type': 'string', 'minLength': 1}
_NATURAL = {'type': 'integer', 'minimum': 0}
_NUMBER = {'type': ['number', 'null']}

def _array(schema, *, unique=False):
    return {'type': 'array', 'items': deepcopy(schema), **({'uniqueItems': True} if unique else {})}

def _nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}

def _selection_schema():
    return obj({name: deepcopy(_TEXT) for name in GROUP_FIELDS})

def _exact_schema():
    return _nullable(obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}}))

def _source_row_schema():
    return obj({'source_ref': deepcopy(_TEXT), 'artifact_ref': deepcopy(_TEXT), 'representation': {'enum': list(REPRESENTATIONS)}, 'row_number': {'type': 'integer', 'minimum': 2}, 'header': deepcopy(_TEXT), 'raw_row': {'type': 'string'}})

def _cell_schema(*, exact=False):
    fields = {'value': deepcopy(_NUMBER), 'unit': {'enum': list(UNIT_CODES)}, 'formula': deepcopy(_TEXT), 'origin': {'const': 'derived'}, 'status': {'enum': ['populated', 'unavailable']}, 'unavailable_reason': {'enum': [*REASONS, None]}, 'conditional_on': _array({'enum': list(CONDITIONS)}, unique=True), 'approximate': {'type': 'boolean'}, 'input_rows': _array(_source_row_schema()), 'input_origins': _array({'enum': list(ORIGINS)}, unique=True)}
    if exact:
        fields['source_exact_value'] = _exact_schema()
    return obj(fields)

def _unit_schema(*, numeric):
    fields = {'sampling_unit': deepcopy(_TEXT), 'sampling_basis': {'enum': [*SAMPLING_BASES, None]}, 'observation_ids': _array(_TEXT, unique=True), 'measurement_count': deepcopy(_NATURAL), 'point_observation_ids': _array(_TEXT, unique=True), 'point_count': deepcopy(_NATURAL), 'representation_count': deepcopy(_NATURAL), 'conflicting_identity': {'type': 'boolean'}, 'complete': {'type': 'boolean'}, 'limitations': _array({'enum': list(REASONS)}, unique=True)}
    if numeric:
        fields['cells'] = obj({name: _cell_schema() for name in ('observed_point_mean', 'observed_point_sd', 'mean')})
    return obj(fields)

def _group_schema(*, numeric):
    fields = {**_selection_schema()['properties'], 'sampling_basis': {'enum': [*SAMPLING_BASES, None]}, **{name: deepcopy(_NATURAL) for name in ('measurement_count', 'representation_count', 'sampling_unit_count', 'complete_unit_count')}, 'units': _array(_unit_schema(numeric=numeric))}
    if numeric:
        fields['cells'] = obj({name: _cell_schema() for name in ('mean', 'sample_sd', 'mean_se')})
    return obj(fields)

def rate_replicate_cells_schema():
    """Complete registered fact view; source strings are never model-authored."""
    reference = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    group = obj({'selection': _selection_schema(), 'status': {'enum': ['observed', 'not_observed']}, 'observed': _nullable(_group_schema(numeric=False))})
    fields = {'sheet_ref': deepcopy(reference), 'evidence_source_ref': deepcopy(reference), 'evaluation_scope': {'const': 'source_raw_rate_replicates'}, 'component': {'enum': list(COMPONENTS)}, 'value': deepcopy(_NUMBER), 'unit': {'enum': list(UNIT_CODES)}, 'formula': deepcopy(_TEXT), 'status': {'enum': ['populated', 'unavailable']}, 'origin': {'const': 'derived'}, 'unavailable_reason': {'enum': [*REASONS, None]}, 'conditional_on': _array({'enum': list(CONDITIONS)}, unique=True), 'approximate': {'type': 'boolean'}, 'source_exact_value': _exact_schema(), 'observed_subject': _nullable(_TEXT), 'observed_experiment': _nullable(_TEXT), 'groups': obj({role: deepcopy(group) for role in ('reference', 'test')}), 'unit_model': {'enum': ['none', 'iid_units']}, 'dependence': {'enum': ['unknown', 'independent', 'paired_units']}, 'pairing': obj({key: _array(_TEXT, unique=True) for key in ('shared_units', 'reference_only', 'test_only')}), 'input_origins': _array({'enum': list(ORIGINS)}, unique=True)}
    return {'type': 'array', 'items': obj(fields), 'x-source': NAMESPACE}
