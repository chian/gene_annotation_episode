"""A110 numerical and semantic scientific return schemas."""
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.biochemical_feasibility_evidence.reaction_population_contracts import BASES, BINDINGS, COMPONENTS, CONDITIONAL_CODES, DEMAND_FIELDS, FORMULA_CODES, MEANINGS_NAMESPACE, MODEL_FIELDS, REASONS, RESOURCE_FIELDS, SOURCE_KINDS, _FIXED_METADATA, deepcopy, obj, reaction_return_view_requirements

def reaction_cells_schema():
    """Closed scientific return: selected cells and their numeric model panel."""
    source = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    nullable_number = {'type': ['number', 'null']}

    def nullable_enum(values):
        return {'type': ['string', 'null'], 'enum': [None, *values]}
    properties = {'sheet_ref': dict(source), 'evidence_source_ref': dict(source), 'data_source_ref': {**source, 'type': ['string', 'null']}, **{field: {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': kind} for field, (_, kind) in BINDINGS.items()}, 'component': {'type': 'string', 'enum': list(COMPONENTS)}, 'value': dict(nullable_number), 'unit': {'type': 'string', 'enum': ['mol_per_mol', 'signal_per_signal', 'squared_ratio', 'dimensionless', 'umol', 'uM', 'umol_per_min', 'uM_per_min', 'unreported']}, 'status': {'type': 'string', 'enum': ['populated', 'unavailable']}, 'formula_code': {'type': 'string', 'enum': list(FORMULA_CODES.values())}, 'origin': {'type': 'string', 'enum': ['reported', 'graph_derived', 'synthetic', 'derived', 'proposed']}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]}, 'conditional_on': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': list(CONDITIONAL_CODES)}}, 'ratio_mode': nullable_enum(['independent_units', 'source_summary']), 'ratio_kind': nullable_enum(['product_pair', 'formed_per_consumed', 'formed_per_supplied', 'signal_ratio']), 'ratio_unit': nullable_enum(['mol_per_mol', 'signal_per_signal']), 'ratio_origin': nullable_enum(['reported', 'graph_derived', 'synthetic']), 'budget_origin': nullable_enum(['reported', 'graph_derived', 'synthetic']), 'independent_n': {'type': ['integer', 'null'], 'minimum': 1}, 'reported_sample_sd': {**nullable_number, 'minimum': 0}, 'derived_sample_sd': {**nullable_number, 'minimum': 0}, 'ratio_uncertainty': {'type': 'string', 'enum': ['reported_sample_sd', 'descriptive_sample_sd', 'unreported']}, 'claim_prediction': dict(nullable_number), 'alternative_predictions': {'type': 'array', 'items': dict(nullable_number)}, 'budget_basis': nullable_enum(['supplied_reagent_batch', 'usable_batch', 'usable_rate']), 'budget_unit': nullable_enum(['umol', 'uM', 'umol_per_min', 'uM_per_min']), 'resources_complete': {'type': ['boolean', 'null']}, 'demand': {**nullable_number, 'exclusiveMinimum': 0}, 'operand_source_kind': {'type': 'string', 'enum': list(SOURCE_KINDS)}, **{field: {'type': 'string', 'enum': [value]} for field, value in _FIXED_METADATA.items()}}
    return {'type': 'array', 'items': obj(properties), 'x-source': 'literature_reaction_cells', 'description': 'Numerical cells from literature_reaction_record, including supported numerical measurement datasets. A literature_reaction_semantic_record sheet returns its numerical cells together with source-bound meanings through literature_reaction_semantic_cells instead. ' + reaction_return_view_requirements()['detail']}

def reaction_semantic_cells_schema():
    """Closed named scientific view of the same15 existing numerical cells."""
    schema = deepcopy(reaction_cells_schema())
    schema['x-source'] = MEANINGS_NAMESPACE
    schema['description'] = 'Numerical cells and saved source-bound meanings from literature_reaction_semantic_record. A literature_reaction_record sheet does not provide this view. ' + reaction_return_view_requirements()['detail']
    properties = schema['items']['properties']

    def ref(kind, nullable=True):
        return {'type': ['string', 'null'] if nullable else 'string', 'format': 'reference', 'x-reference-namespace': kind}

    def meaning(kind, fields, bases):
        return {kind + '_ref': ref('reference', False), 'definition_reported': {'type': 'boolean'}, **{field + '_ref': ref(namespace) for field, namespace in fields.items() if field != 'definition'}, **{basis: {'type': 'string', 'enum': list(BASES)} for basis in bases}}
    model = obj({**meaning('model', MODEL_FIELDS, ('prediction_basis',)), 'role': {'type': 'string', 'enum': ['claim', 'alternative']}, 'prediction': {'type': ['number', 'null']}, 'unit': {'type': 'string', 'enum': ['mol_per_mol', 'signal_per_signal']}})
    resource = obj({**meaning('resource', RESOURCE_FIELDS, ('supply_basis', 'coefficient_basis')), 'coefficient': {'type': 'number', 'exclusiveMinimum': 0}, 'coefficient_role': {'type': 'string', 'enum': ['resource_unit_per_demand_unit']}, 'coefficient_demand_ref': ref('reference', False)})
    demand = obj({**meaning('demand', DEMAND_FIELDS, ('demand_basis',)), 'value': {'type': ['number', 'null'], 'exclusiveMinimum': 0}, 'unit': {'type': 'string', 'enum': ['umol', 'uM', 'umol_per_min', 'uM_per_min']}})
    fields = {'model_definitions': {'type': 'array', 'items': model}, 'comparison_member_refs': {'type': 'array', 'uniqueItems': True, 'items': ref('reference', False)}, 'comparison_reduction': {'type': 'string', 'enum': ['minimum_over_declared_alternatives']}, 'resource_definitions': {'type': 'array', 'items': resource}, 'demand_definition': {**demand, 'type': ['object', 'null']}, 'nominal_limiting_resource_refs': {'type': 'array', 'uniqueItems': True, 'items': ref('reference', False)}}
    properties.update(fields)
    schema['items']['required'].extend(fields)
    return schema

# What each saved view means (the old ``literature_component_binding.fact_sources`` meanings, owner's text).
CELLS_MEANING = 'Saved reported reference reaction-ratio residuals, fixed named-prediction comparisons and simple resource budgets. Source summary uncertainty and incomplete resources remain explicit unknowns. Product-pair ratios and supplied reagent coverage do not establish consumption, native capacity or measured coupling. Logical domain bounds are not confidence intervals; no target correspondence or annotation credit is calculated.'
SEMANTIC_CELLS_MEANING = 'The same saved reference reaction/resource components with source-supported claim and alternative identities, named predictions and exact comparison membership. Resource meanings preserve supply basis, coefficient-to-demand linkage, period and compartment. Missing descriptions add no numerical gate. These are conditional source comparisons and fixed-consumption constraints, not extra assays, physiological sufficiency, target correspondence or annotation credit.'
NATIVE_OBSERVATIONS_MEANING = 'Separately requested native reaction observations preserving exact reported points or ratio-expression operands, source unit conversion, measurement/calibration basis, actual uncertainty kind and count basis. Reported technical or unknown counts are not independent n. These are source operands, not extra scoring components or independent evidence.'
