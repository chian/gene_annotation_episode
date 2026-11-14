"""Selected A105 product/cofactor views with authenticated, scoped custody.

Fresh population alone reads scientific source bytes and runs the frozen pure
reader/calculator. Saved reads check original records and structural bindings;
they do not parse source statistics or recalculate scientific components.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_product_coupling_inputs import CONTEXT_FIELDS, QUANTITY_MEANINGS, RELATIONSHIPS, NU_STATUSES, ORIGINS, product_coupling_extraction_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_product_coupling_calculations import COMPONENTS, QUALIFICATIONS, product_coupling_cell_schema
NAMESPACE = 'literature_product_coupling_cells'
SCOPE = 'source_product_coupling'

def _array(schema):
    return {'type': 'array', 'items': deepcopy(schema)}

def _ref(nullable=False, namespace='source'):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}

def _exact_schema():
    return obj({'numerator': {'type': 'string', 'pattern': '^-?[0-9]+$'}, 'denominator': {'type': 'string', 'pattern': '^[1-9][0-9]*$'}})

def _location_schema():
    return obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'), 'representation': {'enum': ['original', 'text']}, 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})

def _meaning_schema():
    return _nullable(obj({**_location_schema()['properties'], 'display_text': {'type': 'string', 'minLength': 1}, 'status': {'enum': ['selected', 'unrequested_numbers_withheld', 'numerical_scope_unresolved']}, 'unavailable_reason': {'enum': ['unrequested_numerical_scope_unresolved', None]}}))

def product_coupling_cells_schema():
    interpreted = lambda values: obj({'value': {'enum': list(values)}, 'support': _array(_meaning_schema())})
    quantity = _nullable(obj({'label': _meaning_schema(), 'unit': _meaning_schema(), **{name: interpreted(values) for name, values in QUANTITY_MEANINGS.items()}, 'measurement_key': {'type': ['string', 'null']}, 'physical_identity_key': {'type': ['string', 'null']}, 'physical_identity': _meaning_schema(), 'dependency_support': _array(_meaning_schema())}))
    model = _nullable(obj({'kind': {'const': 'interpreted_reaction_account'}, 'direction': {'const': 'cofactor_per_product'}, 'status': {'enum': list(NU_STATUSES)}, 'exact_value': _nullable(_exact_schema()), 'model_key': {'type': ['string', 'null']}, 'support': _array(_meaning_schema())}))
    covariance_fields = product_coupling_extraction_schema()['properties']['covariance']['properties']
    covariance = _nullable(obj({name: deepcopy(value) for name, value in covariance_fields.items() if name != 'matrix_exact'}))
    row = obj({**product_coupling_cell_schema()['properties'], 'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': SCOPE}, 'component': {'enum': list(COMPONENTS)}, 'source_kind': {'enum': list(ORIGINS)}, 'source_meanings': obj({name: _meaning_schema() for name in CONTEXT_FIELDS}), 'quantity_meanings': obj({role: quantity for role in ('product', 'cofactor', 'reported_coupling')}), 'relationships': obj({name: interpreted(values) for name, values in RELATIONSHIPS.items()}), 'reaction_account': model, 'covariance': covariance, 'source_scope': _array(_ref()), 'withheld_locations': _array(_location_schema()), 'model_support_locations': _array(_location_schema()), 'qualifications': {'const': list(QUALIFICATIONS)}})
    return {'type': 'array', 'items': row, 'x-source': NAMESPACE}
