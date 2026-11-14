"""Separate deterministic population of source-bound v3 experimental components."""
from __future__ import annotations
from copy import deepcopy as cp
import json
from jsonschema import Draft202012Validator

from . import literature_controlled_response_v3_inputs as source
from . import literature_controlled_response_local_calculations as local
from . import literature_controlled_response_owner_calculations as owner
from . import literature_controlled_response_calculations as arithmetic
from . import literature_controlled_response_inputs as shared


def _registry(extraction):
    rows = {(r, None): extraction['arms'][r] for r in shared.PRIMITIVE_ORDER}
    rows.update({(r['primary_role'], r['reading_key']): r['reading'] for r in extraction['companion_extractions']})
    return rows


def _dependencies(extraction, sheet, assignment, component, covariance):
    index = arithmetic.COMPONENTS.index(component)
    roles = ([shared.PRIMITIVE_ORDER[index]] if index < 4 else
        list(shared.PRIMITIVE_ORDER[:2]) if index == 4 else
        list(shared.PRIMITIVE_ORDER[2:]) if index == 5 else list(shared.PRIMITIVE_ORDER))
    scientific = [source._selector(r, assignment[r]) for r in roles]
    numeric_roles = roles if index < 6 else sheet['contrast_dependencies']['active_roles']
    numeric = [source._selector(r, assignment[r]) for r in numeric_roles]
    roster = _registry(extraction)
    arms = [roster[(s['role'], s['reading_key'])]['calculation_operand'] if roster[(s['role'], s['reading_key'])] else None for s in scientific]
    covariance_index = None
    if index >= 7 and covariance is not None:
        covariance_index = next((i for i, d in enumerate(extraction['component_local_inputs']['source_covariances'])
            if d['source_ref'] == covariance['source_ref']), None)
    dependencies = local._dependency(scientific, arms, numeric=index < 7, covariance_index=covariance_index)
    dependencies['numeric_readings'] = cp(numeric) if index < 7 or index >= 10 else []
    dependencies['numeric_fields'] = [{'reading': cp(s), 'fields':
        ['value', 'threshold', 'relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval'] if index < 7 or index >= 10 else
        ['relation', 'approximate', 'unit', 'status', 'origin', 'digitization_interval_presence']} for s in numeric]
    if index >= 7:
        dependencies['covariance_owner_ids'] = cp(sheet['contrast_dependencies']['required_covariance_owner_ids'])
        dependencies['source_variable_indices'] = ([] if covariance is None else
            list(dict.fromkeys(row['source_variable_index'] for row in covariance['provided_owner_projection']
                if row['physical_observation_id'] in dependencies['covariance_owner_ids'])))
    if index >= 10: dependencies['model_readings'] = cp(numeric)
    return dependencies


def _semantic(extraction, dependencies):
    roster = _registry(extraction)
    readings = []
    for selector in dependencies['scientific_readings']:
        row = roster[(selector['role'], selector['reading_key'])]
        readings.append(None if row is None else {'meanings': row['meanings'], 'context': row['context'],
            'arrangement': row['protein_arrangement'], 'source_kind': row['selection']['source_kind'],
            'measurement_method': 'graph' if row['graph_details'] else 'text' if row['selection']['measurement'] else 'not_selected'})
    return readings, extraction['relationships']


def populate_controlled_response_v3(extraction):
    """Populate final, partial, explicit joint alternatives and independent locals.

    Alternatives are original nominated source-supported assignments. They are
    never combined as independent experiments or used to choose a final reading.
    """
    source.validate_controlled_response_v3_extraction(extraction['selection'], extraction)
    final = (owner.populate_controlled_response_owner(extraction['calculation_inputs'])
        if extraction['calculation_inputs'] is not None else None)
    partial = (owner.populate_controlled_response_owner(extraction['partial_calculation_inputs'])
        if extraction['partial_calculation_inputs'] is not None else None)
    local_sheet = local.populate_controlled_response_local(extraction['component_local_inputs'])
    unresolved = [d['role'] for d in extraction['reconciliation_decisions'] if d['state'] != 'ready']
    if extraction['projection_status'] == 'ready': unresolved = []
    alternatives, conditional = [], []
    signatures = {}
    for i, alternative in enumerate(extraction['alternative_inputs']):
        sheet = owner.populate_controlled_response_owner(alternative['calculation_inputs'])
        assignment = alternative['reading_assignment']
        alternatives.append({'reading_assignment': cp(assignment), 'scope_index': alternative['scope_index'], 'sheet': sheet})
        for component, cell in sheet['cells'].items():
            dependencies = _dependencies(extraction, sheet, assignment, component, alternative['source_covariance'])
            conditional.append({'assignment_index': alternative['scope_index'], 'component': component,
                'cell': cp(cell), 'dependencies': dependencies})
            signatures.setdefault(component, []).append((cell, dependencies, _semantic(extraction, dependencies)))
    unaffected = []
    candidate = final if final is not None else partial
    if candidate is not None:
        assignment = (extraction['final_projection_basis']['reading_assignment'] if final is not None else
            {r: None for r in shared.PRIMITIVE_ORDER})
        covariance = extraction['covariance']
        if final is not None and extraction['final_projection_basis']['covariance_scope'] == 'joint':
            covariance = extraction['joint_scope_extractions'][extraction['final_projection_basis']['scope_index']]['source_covariance']
        for component, cell in candidate['cells'].items():
            dependencies = _dependencies(extraction, candidate, assignment, component, covariance)
            # A masked group's source value is not an unconditional raw reading.
            # All cross-condition conclusions remain conditional when unresolved.
            if (any(s['role'] in unresolved for s in dependencies['scientific_readings'])
                    or extraction['projection_status'] != 'ready' and arithmetic.COMPONENTS.index(component) >= 6):
                continue
            if cell['status'] not in ('available', 'bounded', 'partial'): continue
            signature = (cell, dependencies, _semantic(extraction, dependencies))
            if all(other == signature for other in signatures.get(component, [])):
                unaffected.append({'component': component, 'cell': cp(cell), 'dependencies': dependencies})
    # When whole partial projection is unavailable, a real local raw remains a
    # useful component. No absence of alternatives is treated as equivalence.
    present = {row['component'] for row in unaffected}
    for row in local_sheet['raw']:
        selector = row['reading']
        if selector['reading_key'] is not None or selector['role'] in unresolved or row['cell']['status'] not in ('available', 'bounded', 'partial'):
            continue
        component = selector['role'] + '_response'
        if component in present: continue
        signature = (row['cell'], row['dependencies'], _semantic(extraction, row['dependencies']))
        if all(other == signature for other in signatures.get(component, [])):
            unaffected.append({'component': component, 'cell': cp(row['cell']), 'dependencies': cp(row['dependencies'])})
    result = {'version': 'controlled_response_conditional_population_v3', 'projection_status': extraction['projection_status'],
        'final_sheet': final, 'partial_sheet': partial, 'local_sheet': local_sheet, 'unresolved_roles': unresolved,
        'alternatives': alternatives, 'unaffected_components': unaffected, 'conditional_components': conditional}
    Draft202012Validator(source._schemas()['POPULATION_SCHEMA_V3_007']).validate(result)
    json.dumps(result, allow_nan=False)
    return result


def validate_controlled_response_v3_population(extraction, population):
    local._schema_check(source._schemas()['POPULATION_SCHEMA_V3_007'], population, 'controlled_v3_population_schema_invalid')
    expected = populate_controlled_response_v3(extraction)
    if json.dumps(population, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        shared._fail('controlled_v3_population_reconstruction_mismatch', 'population')
    return cp(population)


__all__ = ['populate_controlled_response_v3', 'validate_controlled_response_v3_population']
