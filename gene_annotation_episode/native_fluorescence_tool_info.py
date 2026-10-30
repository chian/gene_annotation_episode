"""Actual supplied-fluorescence operations in the resource tool library.

These entries describe the configured tool. They do not define an episode TASK,
choose a resource, populate scientific results or grant access to artifacts.
"""
from copy import deepcopy

from .fluorescence_tool_guidance import expand_fluorescence_tool_instructions
from .native_fluorescence_contracts import (
    JOB_SCHEMA, JOB_V2_SCHEMA, NATIVE_FLUORESCENCE_REQUESTED_JOB_SCHEMA, validate_fluorescence_bindings,
)


DESCRIPTIONS = {
    'perform_facs_cell_sorting':
        'Calculate counts, fractions and intensities for explicitly defined populations in supplied fluorescence event data.',
    'analyze_cytokine_production_in_cd4_tcells':
        'Calculate fluorescence population counts, fractions and intensities using the supplied cell-population and cytokine-channel associations.',
}

INSTRUCTIONS = (
    'Quantify the supplied fluorescence measurements for the requested samples and event populations. '
    'Use the supplied channel assignments, measurement units, value domains, gates and control relationships. '
    'Preserve unknown associations; a channel label alone does not establish molecular identity.\n\n'
    'Select the required input files and an available parser: CSV, a structured event table, or encoded FCS '
    'when its decoder is configured. Preserve sample, condition and preparation relationships across files. '
    'Already prepared measurements can be supplied with their preparation information. Performing new '
    'compensation or transformations, and importing numerical reports from other software, remain '
    'unavailable in this implementation.\n\n'
    'Request the counts, fractions, percentages, intensities or control differences needed for the investigation. '
    'Each fraction must identify its reference population. Preserve missing-data and comparison qualifications. '
    'A complete empty population differs from an unavailable population. Return only the selected measurements '
    'and the requested sample, channel, population or control information needed to interpret them; retain '
    'the complete underlying data for later requests.\n\n'
    'Run through the selected local-compute child within its assigned allocation. Observe the original execution '
    'handle when checking progress. Saved-sheet recalculation uses retained measurements and the newly selected '
    'calculation parameters without repeating the original data acquisition. These measurements describe the '
    'supplied events; they do not operate laboratory equipment or assign probabilities to gene functions.'
)


def _bound_schema(binding):
    schema = deepcopy(NATIVE_FLUORESCENCE_REQUESTED_JOB_SCHEMA)
    v2 = binding.get('version') == 'native_fluorescence_binding_v2'
    schema['properties']['native_fluorescence'] = deepcopy(JOB_V2_SCHEMA if v2 else JOB_SCHEMA)
    job = schema['properties']['native_fluorescence']['properties']
    job['operation'] = {'const': binding['operation']}
    job['mode'] = {'const': binding['mode']}
    job['software'] = {'enum': [deepcopy(binding['software'])]}
    job['inputs']['items']['properties']['parser'] = {'enum': list(binding['parsers'])}
    if v2:
        preparations = job['preparations']
        if binding['preparation_methods']:
            recipes = preparations['items']['properties']['recipe']['anyOf']
            preparations['items']['properties']['recipe']['anyOf'] = [row for row in recipes
                if row['properties']['method']['const'] in binding['preparation_methods']]
        else:
            job['preparations'] = {'type': 'array', 'maxItems': 0}
        if binding['report_profiles']:
            reports = job['report_inputs']['items']['anyOf']
            job['report_inputs']['items']['anyOf'] = [row for row in reports
                if row['properties']['profile']['const'] in binding['report_profiles']]
        else:
            job['report_inputs'] = {'type': 'array', 'maxItems': 0}
    return schema


def fluorescence_tool_contracts(bindings, *, resource_kind, resource_id):
    """Keep each configured software/parser combination in one alternative."""
    if resource_kind != 'local' or type(resource_id) is not str or not resource_id:
        raise ValueError('fluorescence_local_resource_required')
    selected = validate_fluorescence_bindings(bindings)
    grouped = {}
    for row in selected:
        grouped.setdefault(row['operation'], []).append(_bound_schema(row))
    return [{'name': operation, 'description': DESCRIPTIONS[operation],
        'resources': 'local', 'instructions': expand_fluorescence_tool_instructions(INSTRUCTIONS,
            bindings=[row for row in selected if row['operation'] == operation]),
        'input_schema': schemas[0] if len(schemas) == 1 else {'anyOf': schemas},
        'invocation_route': {'kind': 'commission', 'routes': [{
            'entry_role': 'launch', 'resource_id': resource_id, 'resource_role': 'launch_local'}]}}
        for operation, schemas in grouped.items()]


def fluorescence_tool_information(bindings, *, resource_kind, resource_id):
    return [{key: row[key] for key in ('name', 'description', 'resources', 'instructions')}
        for row in fluorescence_tool_contracts(bindings,
            resource_kind=resource_kind, resource_id=resource_id)]
