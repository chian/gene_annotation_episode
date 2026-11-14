"""Selected precision/control sections and exactly scoped durable fact custody.

Only fresh population reads source bytes or invokes scientific calculations.
Saved reconstruction authenticates the original request and recorded values.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_measurement_validation_inputs import CONTEXT_FIELDS, RELATIONSHIPS, FORMULA_RELATIONS
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_measurement_validation_calculations import COMPONENTS, QUALIFICATIONS, measurement_validation_cell_schema
NAMESPACE = 'literature_measurement_validation_cells'
SCOPE = 'source_measurement_validation'

def _array(schema):
    return {'type': 'array', 'items': deepcopy(schema)}

def _ref(nullable=False, namespace='source'):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

def _meaning_schema():
    return _nullable(obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'), 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'display_text': {'type': 'string', 'minLength': 1}, 'status': {'enum': ['selected', 'unrequested_numbers_withheld', 'numerical_scope_unresolved']}, 'unavailable_reason': {'enum': ['unrequested_numerical_scope_unresolved', None]}}))

def measurement_validation_cells_schema():
    interpreted = lambda values: obj({'value': {'enum': list(values)}, 'support': _array(_meaning_schema())})
    row = obj({**measurement_validation_cell_schema()['properties'], 'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': SCOPE}, 'component': {'enum': list(COMPONENTS)}, 'family': {'enum': ['precision', 'zprime', 'raw_control']}, 'measurement_key': {'type': ['string', 'null'], 'minLength': 1}, 'source_kind': {'enum': ['primary_source', 'retained_extraction', 'synthetic_fixture']}, 'source_meanings': obj({name: _meaning_schema() for name in CONTEXT_FIELDS}), 'relationships': _nullable(obj({name: interpreted(values) for name, values in RELATIONSHIPS.items()})), 'formula_relation': _nullable(interpreted(FORMULA_RELATIONS)), 'basis': {'enum': [*RELATIONSHIPS['basis'], None]}, 'source_scope': _array(_ref()), 'withheld_locations': _array(obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'), 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})), 'recovery_operand_scope': {'const': 'possessed_rows_retained_without_unrequested_values_or_invented_source_locations'}, 'qualifications': {'const': list(QUALIFICATIONS)}})
    return {'type': 'array', 'items': row, 'x-source': NAMESPACE}
