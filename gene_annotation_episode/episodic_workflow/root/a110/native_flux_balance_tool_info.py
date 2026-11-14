"""Bound FBA information with scientific operands and a commissioning route."""
from .flux_balance_request_binding import scientific_request_schema
from .native_flux_balance_bindings import validate_flux_balance_bindings


INSTRUCTIONS = (
    'Use the assigned question and model, together with any supplied hypothesis, evidence and reaction correspondence. '
    'For an assigned reaction knockout, set both bounds of that existing model reaction to zero. '
    'Select SBML or COBRA JSON input, optional bounds for existing reactions, and either the model\'s objective or one '
    'existing reaction as objective. Objective direction is retained. Describe an objective as growth only when the '
    'supplied model/question identifies it as growth or biomass. Return requested objective values or named reaction '
    'fluxes with relevant conditions and diagnostic qualifications through the existing FBA result forms and calculators. '
    'Predictions remain conditional on the supplied model and correspondence. Saved-sheet recalculation changes '
    'supported diagnostics/projections; changed models, bounds, or objectives require new selected native work.'
)


def flux_balance_tool_contracts(bindings, *, resource_kind, resource_id):
    if resource_kind != 'local' or type(resource_id) is not str or not resource_id:
        raise ValueError('flux_balance_local_resource_required')
    bindings = validate_flux_balance_bindings(bindings)
    if not bindings:
        return []
    schema = scientific_request_schema()
    schema['properties']['model_input']['properties']['file']['properties']['format'] = {
        'enum': sorted({format for row in bindings for format in row['model_formats']})}
    return [{'name': 'perform_flux_balance_analysis',
        'description': 'Test a supplied metabolic model with selected reaction bounds or objective, returning the requested objective value or reaction fluxes.',
        'resources': 'local', 'instructions': INSTRUCTIONS, 'input_schema': schema,
        'invocation_route': {'kind': 'commission', 'routes': [{'entry_role': 'launch',
            'resource_id': resource_id, 'resource_role': 'launch_local'}]}}]
