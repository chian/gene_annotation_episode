"""Exact declared reaction accounting and conditional chemical Gibbs terms.

The input's identities, equations and physical assumptions remain assertions of
their original source. Balance is not enzyme activity or pathway operation.
"""
from collections import defaultdict
from copy import deepcopy
from fractions import Fraction
import math
import re

from .component_axis_native_contracts import PROFILES, validate_source
from .literature_reaction_calculations import populate_reaction_constraints


VERSION = PROFILES['A110']
GAS_CONSTANT_KJ_PER_MOL_K = 0.00831446261815324
ELEMENTS = set(('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn '
    'Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd '
    'Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac '
    'Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og').split())


def require(condition, code):
    if not condition:
        raise ValueError('a110_accounting_'+code)


def rational(value, *, positive=False):
    require(type(value) is str and len(value) <= 120 and re.fullmatch(
        r'[+-]?[0-9]+(?:/[0-9]+|\.[0-9]+)?', value) is not None,
        'explicit_fraction_or_decimal_coefficient_required')
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError('a110_accounting_invalid_coefficient') from error
    require(result > 0 if positive else result != 0, 'nonzero_coefficient_required')
    return result


def exact(value):
    return str(value.numerator) if value.denominator == 1 else str(value.numerator)+'/'+str(value.denominator)


def unique(rows, key):
    result = {}
    for index, row in enumerate(rows):
        require(row[key] not in result, 'duplicate_'+key)
        result[row[key]] = (index, row)
    return result


def composition(species):
    if species['kind'] == 'electron':
        return ({}, None) if species['formula'] is None and species['charge'] == -1 else (
            None, 'electron_requires_null_formula_and_charge_minus_one')
    if species['kind'] != 'chemical' or species['formula'] is None:
        return None, 'chemical_identity_or_formula_unreported'
    formula = species['formula']
    if len(formula) > 4096:
        return None, 'formula_exceeds_supported_representation'
    terms = list(re.finditer(r'([A-Z][a-z]?)([0-9]*)', formula))
    if not terms or ''.join(term[0] for term in terms) != formula:
        return None, 'unsupported_formula_notation; require_explicit_isotope_free_sum_formula'
    result = defaultdict(int)
    for term in terms:
        if term[1] not in ELEMENTS or len(term[2]) > 12:
            return None, 'unsupported_element_or_formula_count'
        count = int(term[2]) if term[2] else 1
        if count <= 0:
            return None, 'nonpositive_formula_count'
        result[term[1]] += count
    return dict(result), None


def residuals(coefficients, species):
    atoms, charge, missing_atoms, missing_charge = defaultdict(Fraction), Fraction(0), [], []
    electron = Fraction(0)
    for key, coefficient in coefficients.items():
        if not coefficient:
            continue
        _, item = species[key]
        counts, reason = composition(item)
        if reason:
            missing_atoms.append({'species_id': key, 'reason': reason})
        else:
            for element, count in counts.items():
                atoms[element] += coefficient*count
        if item['charge'] is None:
            missing_charge.append(key)
        else:
            charge += coefficient*item['charge']
        if item['kind'] == 'electron':
            electron += coefficient
            if reason and key not in missing_charge:
                missing_charge.append(key)
    return {'atom_residuals': {key: exact(value) for key, value in sorted(atoms.items())},
        'atom_balance': 'unknown' if missing_atoms else 'balanced' if not any(atoms.values()) else 'imbalanced',
        'missing_atom_inputs': missing_atoms,
        'charge_residual': None if missing_charge else exact(charge),
        'known_charge_partial_sum': exact(charge),
        'charge_balance': 'unknown' if missing_charge else 'balanced' if charge == 0 else 'imbalanced',
        'missing_charge_species': missing_charge, 'explicit_electron_coefficient': exact(electron),
        'electron_interpretation': 'signed_explicit_electron_terms_only; no_inferred_oxidation_states',
        'sign_convention': 'products_positive; reactants_negative',
        'unit': 'per_declared_stoichiometric_reaction_extent',
        'formula': 'sum(signed_stoichiometric_coefficient*species_composition_or_charge)',
        'conditional_on': ['declared_species_identity_formula_charge_and_compartments',
            'selected_equation_complete_as_declared; no_automatic_water_proton_or_electron_balancing']}


def gibbs(reaction, coefficients):
    standard, conditions = reaction['standard_gibbs'], reaction['conditions']
    missing, logarithms = [], []
    if standard is None:
        missing.append('standard_reaction_gibbs_unreported')
    elif standard['convention'] != 'chemical':
        missing.append('only_chemical_standard_state_supported; transformed_convention_requires_its_own_definition')
    if conditions is None or conditions['temperature_kelvin'] is None:
        missing.append('temperature_and_actual_condition_identity_required')
    if standard is not None and conditions is not None and (
            standard['conditions']['key'] != conditions['key'] or
            standard['conditions']['temperature_kelvin'] != conditions['temperature_kelvin']):
        missing.append('standard_and_actual_conditions_or_temperature_do_not_match')
    activities = unique(reaction['activities'], 'species_id')
    require(set(activities) <= set(coefficients), 'activity_species_outside_reaction')
    for key, coefficient in coefficients.items():
        if not coefficient:
            continue
        item = activities.get(key)
        if item is None or item[1]['value'] is None:
            missing.append('dimensionless_activity_unreported:'+key)
        else:
            value = item[1]['value']
            require(math.isfinite(value) and value > 0, 'positive_finite_activity_required')
            logarithms.append(float(coefficient)*math.log(value))
    value, lnq = None, None
    if not missing:
        try:
            lnq = math.fsum(logarithms)
            value = standard['value_kj_per_mol'] + GAS_CONSTANT_KJ_PER_MOL_K*conditions['temperature_kelvin']*lnq
            if not math.isfinite(value):
                value = None
                missing.append('conditional_gibbs_numerical_range')
        except (ValueError, OverflowError):
            missing.append('conditional_gibbs_numerical_range')
    return {'value': value, 'unit': 'kJ_per_mol_declared_reaction_extent',
        'status': 'available' if value is not None else 'unavailable', 'missing': missing,
        'directional_sign': None if value is None else 'negative' if value < 0 else 'positive' if value > 0 else 'zero',
        'formula': 'delta_G=delta_G_standard+R*T*sum(nu_i*ln(dimensionless_activity_i))',
        'gas_constant_kj_per_mol_kelvin': GAS_CONSTANT_KJ_PER_MOL_K, 'ln_reaction_quotient': lnq,
        'standard_gibbs': deepcopy(standard), 'conditions': deepcopy(conditions),
        'activities': deepcopy(reaction['activities']),
        'limitations': ['Conditions and chemical standard-state meanings are supplied source assertions.',
            'No temperature extrapolation, concentration-to-activity conversion or transformed-state calculation.',
            'No electrical potential, transport work, kinetic barrier or enzyme activity is inferred.']}


def pathway_gibbs(steps, reactions):
    """The explicit Hess sum at one declared physical condition, not a score."""
    rows, missing, applicability = [], [], []
    conditions = set()
    exact_sum = Fraction(0)
    for step in steps:
        energy = reactions[step['reaction_id']]['conditional_gibbs']
        rows.append({'reaction_id': step['reaction_id'], 'multiplier': step['multiplier'],
            'reaction_gibbs': deepcopy(energy)})
        if energy['value'] is None:
            missing.append('reaction_gibbs_unavailable:'+step['reaction_id'])
        else:
            exact_sum += rational(step['multiplier'])*Fraction(energy['value'])
        physical = energy['conditions']
        if physical is None or physical['temperature_kelvin'] is None:
            missing.append('reaction_conditions_unreported:'+step['reaction_id'])
        else:
            conditions.add((physical['key'], physical['temperature_kelvin']))
        applicability.extend(step['reaction_id']+':'+reason for reason in energy['applicability_missing'])
    if not steps:
        missing.append('declared_pathway_steps_unreported')
    if len(conditions) > 1:
        missing.append('pathway_step_physical_conditions_do_not_match')
    value = None
    if not missing:
        try:
            value = float(exact_sum)
            if not math.isfinite(value) or value == 0 and exact_sum != 0:
                value = None
                missing.append('pathway_gibbs_numerical_range')
        except OverflowError:
            missing.append('pathway_gibbs_numerical_range')
    return {'value': value, 'unit': 'kJ_per_mol_declared_pathway_extent',
        'status': 'available' if value is not None else 'unavailable',
        'missing': list(dict.fromkeys(missing)), 'applicability_missing': list(dict.fromkeys(applicability)),
        'qualified_for_declared_pathway_conditions': value is not None and not applicability,
        'directional_sign': None if value is None else 'negative' if value < 0 else 'positive' if value > 0 else 'zero',
        'formula': 'sum(declared_signed_reaction_multiplier*reaction_delta_G_at_one_declared_condition)',
        'exact_combination_of_native_point_values': exact(exact_sum) if not missing else None,
        'steps': rows, 'declared_condition_keys_and_temperatures': [list(row) for row in sorted(conditions)],
        'limitations': ['This is a chemical free-energy sum of the explicitly declared weighted steps.',
            'A favorable net sum does not establish favorable individual steps, physical coupling, kinetics or operation.',
            'Shared input activities, chemical identities and source standard values retain their dependence.']}


def calculate(document, selection):
    validate_source('A110', document)
    species = unique(document['species'], 'id')
    reactions = unique(document['reactions'], 'id')
    require(set(selection['reaction_ids']) <= set(reactions), 'unknown_selected_reaction')
    coefficients, findings = {}, []
    for key in selection['reaction_ids']:
        index, reaction = reactions[key]
        values = defaultdict(Fraction)
        for participant in reaction['participants']:
            name = participant['species_id']
            require(name in species, 'unknown_reaction_species')
            values[name] += rational(participant['coefficient'])
        values = dict(values)
        coefficients[key] = values
        active_species = {name for name, value in values.items() if value}
        compartments = {species[name][1]['compartment'] for name in active_species}
        accounting = residuals(values, species)
        energetic = gibbs(reaction, values)
        applicability = []
        if len(compartments) > 1:
            applicability.append('cross_compartment_electrochemical_work_not_supported')
        if not compartments or None in compartments:
            applicability.append('compartment_identity_unreported')
        if not active_species:
            applicability.append('no_net_chemical_transformation_in_declared_equation')
        if reaction['entity_id'] is None:
            applicability.append('reaction_entity_identity_unreported')
        if any(species[name][1]['entity_id'] is None or species[name][1]['kind'] != 'chemical'
                for name in active_species):
            applicability.append('chemical_species_identity_unresolved')
        if accounting['atom_balance'] != 'balanced' or accounting['charge_balance'] != 'balanced':
            applicability.append('complete_balanced_chemical_equation_not_established')
        if any(species[name][1]['kind'] == 'electron' for name in active_species):
            applicability.append('electrode_potential_and_half_reaction_work_not_supported')
        energetic['applicability_missing'] = applicability
        energetic['qualified_for_declared_chemical_conditions'] = (
            energetic['status'] == 'available' and not applicability)
        findings.append({'reaction_id': key, 'entity_id': reaction['entity_id'],
            'source_locator': reaction['source_locator'], 'pointer': '/reactions/'+str(index),
            'participants': deepcopy(reaction['participants']), 'accounting': accounting,
            'signed_net_stoichiometry': {name: exact(value) for name, value in sorted(values.items())},
            'coefficient_interpretation': 'sum_of_literal_signed_terms; same_declared_species_terms_may_cancel',
            'conditional_gibbs': energetic})
    pathway, used_species = None, {name for values in coefficients.values() for name in values}
    if selection['include_declared_pathway']:
        net, steps = defaultdict(Fraction), []
        for step in document['pathway']:
            require(step['reaction_id'] in coefficients, 'pathway_steps_must_be_selected_reactions')
            multiplier = rational(step['multiplier'])
            for name, coefficient in coefficients[step['reaction_id']].items():
                net[name] += multiplier*coefficient
            steps.append(deepcopy(step))
        pools, pool_ids = [], set()
        for pool in document['carrier_pools']:
            require(pool['id'] not in pool_ids, 'duplicate_carrier_pool')
            pool_ids.add(pool['id'])
            members, total = {}, Fraction(0)
            for member in pool['members']:
                name = member['species_id']
                require(name in species and name not in members, 'unknown_or_repeated_carrier_member')
                units = rational(member['carrier_units'], positive=True)
                members[name] = {'net_coefficient': exact(net[name]), 'carrier_units': exact(units),
                    'source_locator': member['source_locator']}
                total += units*net[name]
            restored = all(net[name] == 0 for name in members)
            participating = any(name in coefficients[step['reaction_id']] for name in members for step in document['pathway'])
            pools.append({'pool_id': pool['id'], 'members': members, 'net_carrier_units': exact(total),
                'state': 'unknown' if not steps or not pool['members_complete'] else
                    'no_declared_pool_member_in_selected_pathway' if not participating else
                    'declared_forms_restored_in_net_equation' if restored else 'declared_forms_not_restored',
                'members_complete': pool['members_complete'], 'source_locator': pool['source_locator'],
                'limitation': 'Pool conservation alone does not regenerate each required form or demonstrate flux.'})
            used_species.update(members)
        pathway = {'steps': steps, 'net_species_coefficients': {name: exact(value) for name, value in sorted(net.items())},
            'accounting': residuals(net, species) if steps else None, 'carrier_pools': pools,
            'conditional_gibbs': pathway_gibbs(steps, {row['reaction_id']: row for row in findings}),
            'limitation': 'Explicit weighted equation sum; no pathway search, optimization or steady-state activity proof.'}
    reported = None
    if selection['include_reported_constraints']:
        reported = populate_reaction_constraints(document['reported_constraints']) if (
            document['reported_constraints'] is not None) else {'status': 'unavailable', 'missing': ['reported_constraints_unreported']}
    return {'version': VERSION, 'dataset_id': document['dataset_id'], 'origin': document['origin'],
        'selection': deepcopy(selection), 'species': [{**deepcopy(species[key][1]),
            'pointer': '/species/'+str(species[key][0])} for key in sorted(used_species)],
        'reactions': findings, 'pathway': pathway, 'reported_constraints': reported,
        'limitations': ['Chemical entity, species/protonation, compartment and source meanings are supplied assertions.',
            'Unknown identity, formulas, charge, activities and standard-state prerequisites remain unknown.',
            'A source equation or balanced net pathway does not establish that the submitted molecule performs it.',
            'Shared input species, equations and datasets are shared evidence; distinct views are not confirmations.'],
        'combined_scientific_score': None}
