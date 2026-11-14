"""Selected A105 ion components and authenticated, exactly scoped saved returns.

Only population reads scientific artifacts and invokes the frozen reader and
calculator. Reconstruction copies original facts and checks their custody; it
does not reattest current scientific code or reinterpret original evidence.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.domain import obj
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_compiled_assay_storage import compiled_assay_cells_schema
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.literature_ion_discrimination_inputs import ion_discrimination_population_schema, ion_discrimination_sheet_schema
NAMESPACE = 'literature_ion_discrimination_cells'
SCOPE = 'source_ion_discrimination'

def _array(schema):
    return {'type': 'array', 'items': deepcopy(schema)}

def _ref(nullable=False, namespace='source'):
    return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': namespace}

def _enum(values):
    return {'type': 'string', 'enum': list(values)}

def _meaning_schema():
    return {'anyOf': [obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'), 'representation': _enum(('original', 'text')), 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}, 'display_text': {'type': 'string', 'minLength': 1}, 'status': _enum(('selected', 'unrequested_numbers_withheld'))}), {'type': 'null'}]}

def _interpreted(schema):
    return obj({'value': deepcopy(schema['properties']['value']), 'support': _array(_meaning_schema())})

def ion_discrimination_cells_schema():
    """Exact host type; the numerical definitions are never prompt instructions."""
    original = ion_discrimination_population_schema()['$defs']
    sheet = ion_discrimination_sheet_schema()
    contexts = original['Context']['properties']
    context = obj({name: obj({field: _meaning_schema() for field in schema['properties']}) if name in ('preferred', 'alternative') else _meaning_schema() for name, schema in contexts.items()})
    relationships = obj({name: _interpreted(node) for name, node in original['Relationships']['properties'].items()})
    quantity = obj({name: _interpreted(node) for name, node in original['SourceQuantity']['properties'].items() if name not in ('number', 'unit')})
    compiled = compiled_assay_cells_schema()['items']['properties']
    compiled_meanings = obj({**{name: deepcopy(compiled[name]) for name in ('operand_meanings', 'assay_meanings', 'endpoint_kind', 'arrangement_kind', 'correction_stages')}, 'literal_display_status': obj({name: _enum(('selected', 'not_selected', 'unrequested_numerical_scope_unresolved')) for name in compiled['assay_meanings']['properties']}), 'literal_source_ref': _ref(), 'literal_location_status': {'const': 'not_available_in_possessed_compiled_row'}})
    operand = obj({'role': _enum(('preferred', 'alternative', 'reported')), 'route': _enum(('source_quantity', 'compiled_activity')), 'source_quantity_meanings': {'anyOf': [quantity, {'type': 'null'}]}, 'compiled_meanings': {'anyOf': [compiled_meanings, {'type': 'null'}]}})
    cell = deepcopy(sheet['$defs']['Cell'])
    properties = {**cell['properties'], 'sheet_ref': _ref(), 'evidence_source_ref': _ref(), 'evaluation_scope': {'const': SCOPE}, 'route': deepcopy(sheet['properties']['route']), 'source_kind': _enum(('primary_source', 'retained_extraction', 'synthetic_fixture')), 'source_meanings': context, 'relationships': relationships, 'operands': _array(operand), 'nonintended_differences': _array(obj({'aspect': deepcopy(original['NonintendedDifference']['properties']['aspect']), 'support': _array(_meaning_schema())})), 'adjustment_bindings': _array(obj({**{name: deepcopy(node) for name, node in original['AdjustmentBinding']['properties'].items() if name != 'witnesses'}, 'support': _array(_meaning_schema()), 'compiled_stage_verified': {'type': 'boolean'}})), 'covariance': obj({'status': _enum(('not_selected', 'valid', 'covariance_owner_or_dependency_mismatch', 'covariance_units_incompatible', 'covariance_status_unknown', 'shared_activity_covariance_inconsistent', 'covariance_invalid')), 'source_ref': _ref(True), 'origin': {'type': ['string', 'null'], 'enum': ['reported', 'derived', 'synthetic', None]}}), 'source_scope': _array(_ref()), 'withheld_locations': _array(obj({'source_ref': _ref(), 'artifact_ref': _ref(namespace='artifact'), 'representation': _enum(('original', 'text')), 'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 1}})), 'replication_status': {'const': 'not_evaluated_by_this_component'}}

    def inline(node):
        if isinstance(node, dict):
            if '$ref' in node:
                return inline(sheet['$defs'][node['$ref'].removeprefix('#/$defs/')])
            return {name: inline(value) for name, value in node.items()}
        if isinstance(node, list):
            return [inline(value) for value in node]
        return node
    return {'type': 'array', 'items': inline(obj(properties)), 'x-source': NAMESPACE}
