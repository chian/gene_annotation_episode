"""Original source-location and reported-grid input contracts; no reader execution."""
from copy import deepcopy
from gene_annotation_episode.domain import REF, obj

SOURCE_KINDS = ('primary_source', 'retained_extraction', 'synthetic_fixture')
TEXT = {'type': 'string', 'minLength': 1}
CELL = {'type': 'string', 'pattern': '^[A-Z]+[1-9][0-9]*$'}
STATUSES = ('observed', 'missing', 'not_detected', 'censored', 'unsupported_cell')
ENTRY_REASONS = ('source_measurement_unavailable', 'nondetection_without_point',
    'censored_measurement', 'formula_measurement_unsupported', 'numeric_cell_type_required',
    'source_cell_error', 'invalid_numeric_lexeme')


GRID_INPUT_VERSION = 'a105_reported_rate_grid_v1'
GRID_SOURCE_STATUSES = ('observed', 'missing', 'not_detected', 'censored', 'unsupported_cell')
GRID_ENTRY_REASONS = (*ENTRY_REASONS, 'source_error_cell')


def label_schema():
    return obj({'cell': deepcopy(CELL), 'expected_text': deepcopy(TEXT)})


def _grid_array(schema, *, minimum=0):
    return {'type': 'array', 'minItems': minimum, 'items': deepcopy(schema)}


def _grid_nullable(schema):
    return {'anyOf': [deepcopy(schema), {'type': 'null'}]}


def _grid_exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'},
                'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})


def _grid_context_selector_schema():
    return obj({'kind': {'const': 'context_span'}, 'source_ref': deepcopy(REF),
        'artifact_ref': deepcopy(REF), 'start': {'type': 'integer', 'minimum': 0},
        'end': {'type': 'integer', 'minimum': 1}, 'quote': deepcopy(TEXT)})


def _grid_witness_selector_schema():
    return {'anyOf': [obj({'kind': {'const': 'xlsx_label'}, **label_schema()['properties']}),
                      _grid_context_selector_schema()]}


def reported_rate_grid_population_schema():
    """Locations/meanings only: measured operands always come from XLSX bytes."""
    witness = _grid_witness_selector_schema()
    interpretation = obj({'status': {'enum': ['reported_convention_only', 'supported', 'unknown', 'conflicting']},
                          'witnesses': _grid_array(witness)})
    sampling = obj({'status': {'enum': ['supported', 'stipulated_sensitivity', 'unknown', 'conflicting']},
        'assumption': {'enum': ['none', 'iid_reported_curve_vectors']},
        'source_claim': {'enum': ['iid_reporting_vectors_supported', 'not_established', 'unknown', 'conflicting']},
        'witnesses': _grid_array(witness)})
    return obj({'version': {'const': GRID_INPUT_VERSION}, 'source_ref': deepcopy(REF),
        'source_kind': {'enum': list(SOURCE_KINDS)}, 'worksheet': deepcopy(TEXT),
        **{name: label_schema() for name in ('panel', 'subject', 'native_rate_label')},
        'curves': _grid_array(obj({'header': label_schema()}), minimum=1),
        'points': _grid_array(obj({'concentration_cell': deepcopy(CELL),
                                  'rate_cells': _grid_array(CELL, minimum=1)}), minimum=1),
        'rate_unit': obj({'code': {'enum': ['umol/min', 'nmol/min', 'mmol/min']}, 'witness': witness}),
        'concentration_unit': obj({'code': {'enum': ['M', 'mM', 'uM', 'nM', 'unknown']},
                                   'witness': _grid_nullable(witness)}),
        'endpoint_relationship': interpretation, 'curve_sampling': sampling})


def _grid_custody_schema():
    return obj({name: deepcopy(TEXT) for name in
        ('source_ref', 'artifact_ref', 'workbook_sha256', 'worksheet', 'member', 'member_sha256')})


def _grid_cell_witness_schema():
    return obj({**_grid_custody_schema()['properties'], 'cell': deepcopy(CELL),
        'cell_type': deepcopy(TEXT), **{name: {'type': ['string', 'null']} for name in
            ('value', 'raw_value', 'style_index', 'error')},
        'formula': _grid_nullable(obj({'text': {'type': ['string', 'null']},
            'attributes': {'type': 'object', 'additionalProperties': {'type': 'string'}}})),
        'value_is_formula_cache': {'type': 'boolean'}})


def _grid_quantity_schema():
    return obj({'measurement_key': deepcopy(TEXT), 'status': {'enum': list(GRID_SOURCE_STATUSES)},
        'unavailable_reason': {'enum': [*GRID_ENTRY_REASONS, None]},
        'bound': {'enum': ['none', '<', '>', '<=', '>=', '≤', '≥']},
        'exact_value': _grid_nullable(_grid_exact_schema()),
        'exact_limit': _grid_nullable(_grid_exact_schema()),
        'origin': {'enum': ['reported', 'synthetic']}, 'witness': _grid_cell_witness_schema()})


def reported_rate_grid_extraction_schema():
    return obj({'version': {'const': GRID_INPUT_VERSION},
        'original_arguments': reported_rate_grid_population_schema(),
        'custody': _grid_custody_schema(),
        'meanings': obj({name: _grid_cell_witness_schema() for name in ('panel', 'subject', 'native_rate_label')}),
        'context_witnesses': _grid_array(_grid_witness_selector_schema()),
        'curves': _grid_array(obj({'curve_key': deepcopy(TEXT), 'header': _grid_cell_witness_schema(),
                                 'selection_indices': _grid_array({'type': 'integer', 'minimum': 0})}), minimum=1),
        'points': _grid_array(obj({'point_key': deepcopy(TEXT), 'concentration': _grid_quantity_schema(),
            'entries': _grid_array(obj({'curve_key': deepcopy(TEXT), 'representation_key': deepcopy(TEXT),
                                      'quantity': _grid_quantity_schema()}), minimum=1),
            'selection_indices': _grid_array({'type': 'integer', 'minimum': 0})}), minimum=1),
        'qualifications': _grid_array({'enum': ['reporting_columns_not_physical_units',
            'physical_preparation_count_unknown', 'published_estimator_identity_unknown',
            'no_product_specific_rate_conversion', 'no_Vmax_to_kcat_conversion']})})


