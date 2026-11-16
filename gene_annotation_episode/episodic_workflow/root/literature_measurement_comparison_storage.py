"""Selected source-comparison cells with immutable scoped returns and cold custody.

Scientific reading/calculation occurs only at population. Durable reconstruction
validates original types, custody and copied relationships, without rerunning it.
This adapter adds no episode, continuation rule, credit or source acquisition.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, identity, validate_schema
from .literature_rate_storage import LiteratureRateRepository

PROVIDER = 'literature.a105.measurement_comparison'
VERSION = 'literature_measurement_comparison_record_v2'
from .library.literature_measurement_comparison_metadata import POPULATION, NAMESPACE, REQUESTED, VIEW, SCOPE, OPERATION

# Immutable reviewed metadata; no runtime verification-file or schema-factory IO.
from .library.literature_measurement_comparison_return_contracts import (
    ORIGINAL_SCHEMAS, MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2, MEASUREMENT_COMPARISON_REQUEST_SCHEMA_V2, COMPONENTS, measurement_comparison_cells_schema, measurement_comparison_operation_schema,
)
PROJECTION = json.loads('{"native_left":{"maximum_roles":["left"],"relationship_names":[],"model_premises":[],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"native_right":{"maximum_roles":["right"],"relationship_names":[],"model_premises":[],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"converted_left":{"maximum_roles":["left"],"relationship_names":[],"model_premises":["conversion.left"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"converted_right":{"maximum_roles":["right"],"relationship_names":[],"model_premises":["conversion.right"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"protocol_difference":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation","protocol","functional_bearing","left_validity","right_validity"],"model_premises":["conversion.left","conversion.right"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"protocol_ratio":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation","protocol","functional_bearing","left_validity","right_validity"],"model_premises":["conversion.left","conversion.right"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"protocol_log_ratio":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation","protocol","functional_bearing","left_validity","right_validity"],"model_premises":["conversion.left","conversion.right"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"common_difference":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"common_ratio":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"common_log_ratio":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"difference_variance":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","sampling","systematic_coverage"],"model_premises":["conversion.left","conversion.right"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"difference_standard_uncertainty":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","sampling","systematic_coverage"],"model_premises":["conversion.left","conversion.right"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"standardized_difference":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"squared_standardized_difference":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"weight_left":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"weight_right":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"combined_estimate":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"combined_variance":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"combined_standard_uncertainty":{"maximum_roles":["left","right"],"relationship_names":["endpoint","denominator","construct","preparation_target","protocol","functional_bearing","left_validity","right_validity","attribution","sampling","systematic_coverage","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","common_model.applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"spectral_multiplier":{"maximum_roles":["epsilon_nuisance","epsilon_signal"],"relationship_names":[],"model_premises":["optical.coefficient_applicability"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"spectral_multiplier_variance":{"maximum_roles":["epsilon_nuisance","epsilon_signal"],"relationship_names":[],"model_premises":["optical.coefficient_applicability"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"observed_interference":{"maximum_roles":["$signal","epsilon_nuisance","epsilon_signal","nuisance"],"relationship_names":["attribution","systematic_coverage","$signal_validity","$signal_readout_isolation"],"model_premises":["optical.coefficient_applicability","optical.raw_optical_relation","optical.estimate_scale_applicability","optical.nuisance_quantity_linkage"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"corrected_estimate":{"maximum_roles":["$signal","epsilon_nuisance","epsilon_signal","nuisance"],"relationship_names":["attribution","systematic_coverage","$signal_validity","$signal_readout_isolation"],"model_premises":["optical.coefficient_applicability","optical.raw_optical_relation","optical.estimate_scale_applicability","optical.nuisance_quantity_linkage"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"corrected_estimate_variance":{"maximum_roles":["$signal","epsilon_nuisance","epsilon_signal","nuisance"],"relationship_names":["attribution","systematic_coverage","$signal_validity","$signal_readout_isolation"],"model_premises":["optical.coefficient_applicability","optical.raw_optical_relation","optical.estimate_scale_applicability","optical.nuisance_quantity_linkage"],"uses_covariance":true,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"required_interference_scenario":{"maximum_roles":["$signal","$anchor"],"relationship_names":["endpoint","denominator","protocol","functional_bearing","attribution","left_validity","right_validity","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","optical.raw_optical_relation","optical.scenario.common_rate_equality","optical.scenario.linear_mixture_on_estimate_scale"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"},"required_nuisance_equivalent_scenario":{"maximum_roles":["$signal","$anchor","epsilon_nuisance","epsilon_signal"],"relationship_names":["endpoint","denominator","protocol","functional_bearing","attribution","left_validity","right_validity","left_readout_isolation","right_readout_isolation"],"model_premises":["conversion.left","conversion.right","optical.raw_optical_relation","optical.scenario.common_rate_equality","optical.scenario.linear_mixture_on_estimate_scale","optical.coefficient_applicability"],"uses_covariance":false,"numeric_return":"exactly saved pure cell; never expand role operand values, source spread/counts or covariance matrix","context_rule":"only mapped roles; all context field statuses retained; fragments exactly caller-selected authenticated subwindows","dependency_rule":"actual mapped roles and cell operand keys; absent roles remain absent; original dependency keys/source locators; no inferred independence"}}')




def _witnesses(value):
    if isinstance(value, dict):
        if {'source_ref', 'representation', 'start', 'end', 'quote'} <= value.keys():
            yield value
        else:
            for child in value.values():
                yield from _witnesses(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _witnesses(child)


def _direct(args):
    selection = args['selection']
    return list(dict.fromkeys([selection['source_ref'],
        *sorted({w['source_ref'] for w in _witnesses(selection)}), *selection['covariance_source_refs']]))


def _location(witness):
    return {k: witness[k] for k in ('source_ref', 'artifact_ref', 'representation', 'start', 'end')}


def _overlap(left, right):
    return (left['artifact_ref'] == right['artifact_ref']
        and left['start'] < right['end'] and right['start'] < left['end'])


def _numeric_locations(extraction):
    result = []
    artifacts = {(x['source_ref'], x['representation']): x['artifact_ref'] for x in extraction['source_artifacts']}
    def visit(value):
        if isinstance(value, dict):
            selector = value if 'witness' in value and any(k in value for k in ('number_start', 'lower_start')) else value.get('selector')
            if isinstance(selector, dict) and isinstance(selector.get('witness'), dict):
                witness = dict(selector['witness'])
                witness.setdefault('artifact_ref', artifacts[(witness['source_ref'], witness['representation'])])
                pairs = [('number_start', 'number_end')] if 'number_start' in selector else (
                    [('lower_start', 'lower_end'), ('upper_start', 'upper_end')] if 'lower_start' in selector else [])
                for start, end in pairs:
                    loc = _location(witness)
                    loc['start'] += len(witness['quote'][:selector[start]].encode())
                    loc['end'] = witness['start'] + len(witness['quote'][:selector[end]].encode())
                    if loc not in result:
                        result.append(loc)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(extraction)
    # Count/spread helpers retain their authenticated witnesses even when their
    # exact token is not a retained_number. Their entire selected span is private.
    for item in extraction['quantities'].values():
        if item is None:
            continue
        for witness in _witnesses(item['selection']['uncertainty']):
            loc = {**_location({**witness, 'artifact_ref': artifacts[(witness['source_ref'], witness['representation'])]})}
            if loc not in result:
                result.append(loc)
    for block in extraction['covariance_blocks']:
        raw = block['raw_document_utf8']
        if raw:
            result.append({'source_ref': block['source_ref'], 'artifact_ref': block['artifact_ref'],
                'representation': 'original', 'start': 0, 'end': len(raw.encode())})
    return result


def _role_witness(item, name):
    if item is None:
        return None
    selected = item['selection']
    if '.' in name:
        group, field = name.split('.', 1)
        target = selected[group][field]
    else:
        target = selected[name]
    if target is None:
        return None
    return next((w for w in item['witnesses']
        if {k: v for k, v in w.items() if k != 'artifact_ref'} == target), None)


def _assertion_witness(extraction, name):
    witness = extraction['selection']['assertion'][name]
    if witness is None:
        return None
    artifact = next(a['artifact_ref'] for a in extraction['source_artifacts']
        if (a['source_ref'], a['representation']) == (witness['source_ref'], witness['representation']))
    return {**witness, 'artifact_ref': artifact}


def _assertion_projection(args, extraction):
    numeric = _numeric_locations(extraction)
    result = {}
    for name, windows in args['return_assertion_context'].items():
        witness = _assertion_witness(extraction, name)
        if windows and witness is None:
            raise ContractError('measurement_comparison_assertion_context_without_witness')
        fragments = []
        for window in windows:
            a, b = window['start'], window['end']
            if not witness['start'] <= a < b <= witness['end']:
                raise ContractError('measurement_comparison_assertion_context_outside_witness')
            location = {**_location(witness), **window}
            if any(_overlap(location, loc) for loc in numeric):
                raise ContractError('measurement_comparison_assertion_context_overlaps_numeric_operand')
            try:
                text = witness['quote'].encode()[a-witness['start']:b-witness['start']].decode()
            except UnicodeError as error:
                raise ContractError('measurement_comparison_assertion_context_utf8_boundary_required') from error
            fragments.append({'text': text, 'location': location})
        result[name] = {'status': 'source_unavailable' if witness is None else 'selected' if windows else 'not_selected',
            'fragments': fragments}
    return result


def _context_projection(args, extraction):
    numeric = _numeric_locations(extraction)
    result = {}
    for role, fields in args['return_context'].items():
        result[role] = []
        for name in sorted(fields):
            windows = fields[name]
            witness = _role_witness(extraction['quantities'][role], name)
            if windows and witness is None:
                raise ContractError('measurement_comparison_context_without_role_witness')
            fragments = []
            for window in windows:
                a, b = window['start'], window['end']
                if not witness['start'] <= a < b <= witness['end']:
                    raise ContractError('measurement_comparison_context_outside_role_witness')
                loc = {**_location(witness), **window}
                if any(_overlap(loc, other) for other in numeric):
                    raise ContractError('measurement_comparison_context_overlaps_numeric_operand')
                try:
                    text = witness['quote'].encode()[a-witness['start']:b-witness['start']].decode()
                except UnicodeError as error:
                    raise ContractError('measurement_comparison_context_utf8_boundary_required') from error
                fragments.append({'text': text, 'location': loc})
            result[role].append({'field': name, 'status': 'source_unavailable' if witness is None
                else 'selected' if windows else 'not_selected', 'fragments': fragments})
    return result


def _roles(selection, component):
    optical = selection['optical']
    signal = optical['signal_role'] if optical else 'left'
    anchor = optical['scenario']['anchor_role'] if optical and optical['scenario'] else (
        'right' if signal == 'left' else 'left')
    replacements = {'$signal': signal, '$anchor': anchor}
    return list(dict.fromkeys(replacements.get(role, role) for role in PROJECTION[component]['maximum_roles']))


def _relationship_names(selection, component):
    signal = selection['optical']['signal_role'] if selection['optical'] else 'left'
    return [signal + '_validity' if name == '$signal_validity' else signal + '_readout_isolation'
        if name == '$signal_readout_isolation' else name for name in PROJECTION[component]['relationship_names']]


def _condition(selection, path):
    node = selection
    for name in path.split('.'):
        if node is None:
            return 'not_selected'
        node = node[name]
    return node['value']


def _settings(selection, component):
    premises = PROJECTION[component]['model_premises']
    common = selection['common_model'] if 'common_model.applicability' in premises else None
    uses_common_covariance = component in ('standardized_difference', 'squared_standardized_difference',
        'weight_left', 'weight_right', 'combined_estimate', 'combined_variance', 'combined_standard_uncertainty')
    uses_combination = component in ('weight_left', 'weight_right', 'combined_estimate',
        'combined_variance', 'combined_standard_uncertainty')
    # Coefficient applicability alone supplies alpha=en/es. The raw observation
    # equation, signal role and nuisance sign have no role in that ratio.
    optical = selection['optical'] if any(p.startswith('optical.')
        and p != 'optical.coefficient_applicability' for p in premises) else None
    scenario = optical['scenario'] if optical and any(p.startswith('optical.scenario.') for p in premises) else None
    return {'common_variance_interpretation': common['variance_interpretation'] if common and uses_common_covariance else 'not_selected',
        'common_combination': common['combination'] if common and uses_combination else 'not_selected',
        'optical_observation_equation': optical['observation_equation'] if optical else None,
        'optical_signal_role': optical['signal_role'] if optical else None,
        'optical_nuisance_sign': optical['nuisance_sign'] if optical else None,
        'scenario_anchor_role': scenario['anchor_role'] if scenario else None}


def _assumptions(selection, component, cell, sheet):
    premises = PROJECTION[component]['model_premises']
    allowed = {'no_reference_distribution_assumed'}
    if 'common_model.applicability' in premises:
        allowed.add('common_unbiased_quantity_model')
    if any(p.startswith('conversion.') for p in premises):
        allowed.add('fixed_reaction_conversion')
    if any(p.startswith('optical.') for p in premises):
        allowed.add('linear_mixture_on_selected_estimate_scale')
    if any(p.startswith('optical.scenario.') for p in premises):
        allowed.update(('common_rate_equality_stipulated', 'linear_estimate_scale_mapping_stipulated'))
    if cell['uncertainty']['variance_status'] == 'estimated' and component in (
            'standardized_difference', 'squared_standardized_difference', 'weight_left', 'weight_right',
            'combined_estimate', 'combined_variance', 'combined_standard_uncertainty'):
        allowed.add('estimated_weights_treated_as_plugin')
    if cell['uncertainty']['scope'] == 'first_order_operand_propagation':
        allowed.add('first_order_covariance_propagation')
    return [name for name in sheet['assumptions'] if name in allowed]


def _project_once(args, extraction, inputs, sheet):
    contexts = _context_projection(args, extraction)
    assertion = _assertion_projection(args, extraction)
    withheld = []
    for w in _witnesses(extraction):
        if 'artifact_ref' in w and _location(w) not in withheld:
            withheld.append(_location(w))
    for loc in _numeric_locations(extraction):
        if loc not in withheld:
            withheld.append(loc)
    for name in ('molecule', 'functional_assertion'):
        witness = _assertion_witness(extraction, name)
        if witness is not None and _location(witness) not in withheld:
            withheld.append(_location(witness))
    selection = args['selection']
    rows = []
    for cell in sheet['cells']:
        component = cell['component']
        roles = _roles(selection, component)
        meanings, dependencies = [], []
        for role in roles:
            item = extraction['quantities'][role]
            if item is None:
                continue
            value = item['value']
            meanings.append({'role': role, **{key: value[key] for key in (
                'estimator_scale', 'quantity_kind', 'semantics', 'normalization', 'origin', 'relation', 'approximate')},
                'qualification': item['selection']['qualification']['value'],
                'reported_uncertainty_statistic': item['reported_uncertainty']['statistic'],
                'reported_uncertainty_meaning': item['reported_uncertainty']['meaning'],
                'contexts': deepcopy(contexts[role])})
            if role in cell['operand_roles']:
                dependencies.append({'role': role, **{key: value[key] for key in (
                    'owner_key', 'physical_owner_key', 'dependency_keys', 'estimator_scale')},
                    'source_locations': [_location(loc) for loc in value['source_locations']],
                    'unit': value['canonical_unit']})
        premises = PROJECTION[component]['model_premises']
        models = [{'name': name, 'state': _condition(selection, name)} for name in premises
            if not name.startswith('conversion.')]
        conversions = []
        for name in premises:
            if name.startswith('conversion.'):
                role = name.split('.')[1]
                original = selection['common_quantity'][role+'_conversion']
                conversions.append({'role': role, 'kind': original['kind'],
                    'direction': original['direction']['value'], 'support_status': original['support_status']['value']})
        covariance = []
        if PROJECTION[component]['uses_covariance']:
            for block in inputs['covariance_blocks']:
                if block['source_ref'] in cell['uncertainty']['covariance_source_refs'] or (
                        block['status'] == 'unavailable' and (not block['roles'] or set(block['roles']) & set(cell['operand_roles']))):
                    covariance.append({key: block[key] for key in ('source_ref', 'artifact_ref', 'basis',
                        'variance_status', 'origin', 'systematic_coverage', 'derivation', 'status')})
        dependence = [deepcopy(item) for item in sheet['dependence']
            if item['roles'] and set(item['roles']) <= set(cell['operand_roles'])]
        rows.append({'row_version': 'measurement_comparison_return_v2', 'evidence_source_ref': selection['source_ref'],
            'evaluation_scope': SCOPE, 'component': component, 'cell': deepcopy(cell),
            'source_kind': selection['source_kind'], 'assertion_question': selection['assertion']['question'],
            'assertion_context': deepcopy(assertion),
            'role_meanings': meanings,
            'relationships': [{'name': name, 'value': sheet['relationship_meanings'][name]}
                for name in _relationship_names(selection, component)],
            'model_conditions': models, 'conversion_conditions': conversions,
            'covariance_provenance': covariance, 'model_settings': _settings(selection, component),
            'dependencies': dependencies, 'dependence': dependence,
            'assumptions': _assumptions(selection, component, cell, sheet), 'withheld_locations': deepcopy(withheld)})
    return rows


class LiteratureMeasurementComparisonRepository(LiteratureRateRepository):
    provider, record_version, components = PROVIDER, VERSION, COMPONENTS
    operations_table = 'literature_measurement_comparison_operations'
    received_table = 'literature_measurement_comparison_received'
    binding_fields = ()

    def __init__(self, store, run_id):
        if type(run_id) is not str or not run_id:
            raise ValueError('explicit_literature_run_required')
        self.store, self.run_id = store, run_id

    def _installed(self, table):
        return self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None

    def _install(self):
        super().__init__(self.store, self.run_id)

    def _native_provenance(self, scope, reference):
        source = super()._native_provenance(scope, reference)
        record = {key: value for key, value in source.items() if key not in ('id', 'origin', 'record_type')}
        if identity('source', {'origin': source['origin'], 'record': record}) != reference:
            raise ContractError('measurement_comparison_input_source_identity_mismatch')
        return source

    @staticmethod
    def _components(values):
        if (not isinstance(values, (list, tuple)) or any(type(v) is not str or v not in COMPONENTS for v in values)
                or len(values) != len(set(values))):
            raise ContractError('measurement_comparison_component_selection_invalid')
        return list(values)

    def _ancestors(self, scope, refs):
        result = list(dict.fromkeys(refs))
        for ref in result:
            for parent in self._native_provenance(scope, ref).get('parent_source_refs', ()):
                if parent not in result:
                    result.append(parent)
        return result

    def populate(self, context, arguments, operation_key):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if type(operation_key) is not str or not operation_key:
            raise ContractError('operation_key_required')
        args = plain(arguments)
        validate_schema(args, MEASUREMENT_COMPARISON_REQUEST_SCHEMA_V2)
        components = self._components(context.assignment.get(REQUESTED, []))
        if components != args['selection']['requested_cells']:
            raise ContractError('measurement_comparison_assignment_request_roster_mismatch')
        request = {'run_id': self.run_id, 'episode_id': context.episode_id, 'role': context.role,
            'operation_key': operation_key, 'scope': plain(context.scope), 'assignment': plain(context.assignment),
            'received_record_refs': list(context.received_record_refs), 'arguments': args, 'components': components}
        signature = canonical(request)
        old = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, context.episode_id, operation_key)).fetchone() if self._installed(self.operations_table) else None
        if old:
            if old['signature'] != signature:
                raise ContractError('operation_key_reused_for_different_work')
            outcome = json.loads(old['outcome'])
            self.read(outcome['result']['sheet_ref'])
            for ref in _direct(args):
                self._native_source(context, ref)
            return outcome
        for ref in _direct(args):
            self._native_source(context, ref)
        errors = []
        def read_source(ref, representation):
            try:
                source = self._native_source(context, ref)
                artifact = source['artifact_ref'] if representation == 'original' else source.get('text_ref')
                if artifact is None:
                    raise ContractError('literature_source_representation_unavailable')
                raw = self.store.get_artifact(artifact)
                if artifact != 'artifact_' + hashlib.sha256(raw).hexdigest():
                    raise ContractError('measurement_comparison_source_artifact_hash_mismatch')
                return {'artifact_ref': artifact, 'content': raw}
            except ContractError as error:
                errors.append(error)
                raise
        from .library.literature_measurement_comparison_inputs import read_measurement_comparison_inputs, compile_measurement_comparison_inputs
        from .library.literature_measurement_comparison_calculations import populate_measurement_comparison, validate_measurement_comparison_sheet
        extraction = read_measurement_comparison_inputs(args['selection'], read_source=read_source)
        if errors:
            raise errors[0]
        inputs = compile_measurement_comparison_inputs(extraction)
        sheet = populate_measurement_comparison(inputs)
        validate_measurement_comparison_sheet(sheet, inputs=inputs)
        direct = list(dict.fromkeys([*_direct(args), *extraction['source_refs']]))
        for ref in direct:
            self._native_source(context, ref)
        parents = self._ancestors(context.scope, direct)
        templates = _project_once(args, extraction, inputs, sheet)
        source = self._native_source(context, args['selection']['source_ref'])
        saved = {'version': VERSION, 'input_source_ref': source['id'], 'input_artifact_ref': source['artifact_ref'],
            'direct_input_source_refs': direct, 'input_source_refs': parents,
            'source_metadata': {ref: self.store.get(ref) for ref in parents},
            'original_schemas': deepcopy(ORIGINAL_SCHEMAS),
            'extraction': extraction, 'calculation_inputs': inputs, 'sheet': sheet, 'row_templates': templates}
        for value, key in ((extraction, 'extraction'), (inputs, 'inputs'), (sheet, 'sheet')):
            validate_schema(value, ORIGINAL_SCHEMAS[key])
        with self.store.transaction():
            self._install()
            artifact = self.store.artifact(canonical(saved), 'application/json')
            request_ref = self.store.artifact(canonical(request), 'application/json')
            record = {'provider': PROVIDER, 'accession': None, 'uri': None, 'artifact_ref': artifact,
                'text_ref': artifact, 'request_ref': request_ref, 'version': VERSION,
                'retrieved_at': None, 'parent_source_refs': parents}
            ref = identity('source', {'origin': 'tool', 'record': record})
            exists = self.store.db.execute('SELECT 1 FROM records WHERE id=?', (ref,)).fetchone()
            self.store.put('source', record, origin='tool', scope=plain(context.scope))
            rows = [{'sheet_ref': ref, **deepcopy(row)} for row in templates]
            validate_schema(rows, ORIGINAL_SCHEMAS['rows'])
            outcome = {'status': 'completed', 'operation_ref': identity('operation', {'run_id': self.run_id,
                'episode_id': context.episode_id, 'key': operation_key}), 'record_refs': [ref],
                'changed_record_refs': [] if exists else [ref], 'result': {'sheet_ref': ref,
                    'view': VIEW, 'record_version': VERSION, 'cells': rows}, 'feedback': None}
            self.store.db.execute(f'INSERT INTO {self.operations_table} VALUES(?,?,?,?,?)',
                (self.run_id, context.episode_id, operation_key, signature, canonical(outcome)))
        return outcome

    def _json(self, ref):
        raw = self.store.get_artifact(ref)
        if ref != 'artifact_' + hashlib.sha256(raw).hexdigest():
            raise ContractError('measurement_comparison_saved_artifact_hash_mismatch')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ContractError('measurement_comparison_saved_object_required')
        return value

    def read(self, ref):
        try:
            return self._read(ref)
        except ContractError:
            raise
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as error:
            raise ContractError('measurement_comparison_saved_binding_mismatch') from error

    def _read(self, ref):
        def require(condition):
            if not condition:
                raise ContractError('measurement_comparison_saved_binding_mismatch')
        source = self.store.get(ref)
        record = {k: v for k, v in source.items() if k not in ('id', 'origin', 'record_type')}
        require(source.get('record_type') == 'source' and source.get('origin') == 'tool'
            and source.get('provider') == PROVIDER and source.get('version') == VERSION
            and identity('source', {'origin': 'tool', 'record': record}) == ref)
        request, saved = self._json(source['request_ref']), self._json(source['artifact_ref'])
        require(set(request) == {'run_id', 'episode_id', 'role', 'operation_key', 'scope', 'assignment',
            'received_record_refs', 'arguments', 'components'} and request['run_id'] == self.run_id)
        require(set(saved) == {'version', 'input_source_ref', 'input_artifact_ref', 'direct_input_source_refs',
            'input_source_refs', 'source_metadata', 'original_schemas',
            'extraction', 'calculation_inputs', 'sheet', 'row_templates'})
        require(saved['version'] == VERSION and source['text_ref'] == source['artifact_ref'])
        require(self._installed(self.operations_table))
        operation = self.store.db.execute(f'SELECT signature,outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?',
            (self.run_id, request['episode_id'], request['operation_key'])).fetchone()
        require(operation is not None and operation['signature'] == canonical(request))
        schemas = saved['original_schemas']
        require(canonical(schemas) == canonical(ORIGINAL_SCHEMAS))
        args, extraction, inputs, sheet = request['arguments'], saved['extraction'], saved['calculation_inputs'], saved['sheet']
        for value, key in ((args, 'request'), (extraction, 'extraction'), (inputs, 'inputs'), (sheet, 'sheet')):
            validate_schema(value, schemas[key])
        require(args['version'] == POPULATION and args['selection'] == extraction['selection'] == inputs['selection'])
        require(request['components'] == request['assignment'].get(REQUESTED, []) == args['selection']['requested_cells'])
        require(inputs['quantities'] == {r: None if q is None else q['value'] for r, q in extraction['quantities'].items()})
        for name in ('conversions', 'relationships', 'covariance_blocks', 'source_artifacts'):
            require(inputs[name] == extraction[name])
        require(sheet['assertion_key'] == inputs['assertion_key'] and sheet['contribution_key'] == inputs['contribution_key'])
        require([c['component'] for c in sheet['cells']] == request['components'])
        require(saved['input_source_ref'] == args['selection']['source_ref'])
        require(saved['direct_input_source_refs'] == list(dict.fromkeys([*_direct(args), *extraction['source_refs']])))
        require(all(r in request['received_record_refs'] for r in saved['direct_input_source_refs']))
        require(saved['input_source_refs'] == source['parent_source_refs'] == self._ancestors(request['scope'], saved['direct_input_source_refs']))
        require(set(saved['source_metadata']) == set(saved['input_source_refs']))
        for r, metadata in saved['source_metadata'].items():
            require(canonical(metadata) == canonical(self._native_provenance(request['scope'], r)))
        require(saved['input_artifact_ref'] == saved['source_metadata'][saved['input_source_ref']]['artifact_ref'])
        templates = saved['row_templates']
        require([r['component'] for r in templates] == request['components'])
        selection = args['selection']
        for row, cell in zip(templates, sheet['cells']):
            component = cell['component']
            require(row['cell'] == cell and row['evidence_source_ref'] == saved['input_source_ref'])
            require(row['source_kind'] == selection['source_kind'] and row['assertion_question'] == selection['assertion']['question'])
            for name, projected in row['assertion_context'].items():
                windows = args['return_assertion_context'][name]
                witness = _assertion_witness(extraction, name)
                require(projected['status'] == ('source_unavailable' if witness is None else 'selected' if windows else 'not_selected'))
                require(len(projected['fragments']) == len(windows))
                for fragment, window in zip(projected['fragments'], windows):
                    require(fragment['location'] == {**_location(witness), **window})
                    a, b = window['start']-witness['start'], window['end']-witness['start']
                    require(0 <= a < b <= len(witness['quote'].encode())
                        and fragment['text'].encode() == witness['quote'].encode()[a:b])
            roles = [r for r in _roles(selection, component) if extraction['quantities'][r] is not None]
            require([m['role'] for m in row['role_meanings']] == roles)
            for meaning in row['role_meanings']:
                role = meaning['role']; item = extraction['quantities'][role]; value = item['value']
                for key in ('estimator_scale', 'quantity_kind', 'semantics', 'normalization', 'origin', 'relation', 'approximate'):
                    require(meaning[key] == value[key])
                require(meaning['qualification'] == item['selection']['qualification']['value'])
                require(meaning['reported_uncertainty_statistic'] == item['reported_uncertainty']['statistic']
                    and meaning['reported_uncertainty_meaning'] == item['reported_uncertainty']['meaning'])
                require([m['field'] for m in meaning['contexts']] == sorted(args['return_context'][role]))
                for projected in meaning['contexts']:
                    name = projected['field']; windows = args['return_context'][role][name]
                    witness = _role_witness(item, name)
                    require(projected['status'] == ('source_unavailable' if witness is None else 'selected' if windows else 'not_selected'))
                    require(len(projected['fragments']) == len(windows))
                    for fragment, window in zip(projected['fragments'], windows):
                        require(fragment['location'] == {**_location(witness), **window})
                        a, b = window['start']-witness['start'], window['end']-witness['start']
                        require(0 <= a < b <= len(witness['quote'].encode())
                            and fragment['text'].encode() == witness['quote'].encode()[a:b])
            names = _relationship_names(selection, component)
            require(row['relationships'] == [{'name': n, 'value': sheet['relationship_meanings'][n]} for n in names])
            premises = PROJECTION[component]['model_premises']
            require(row['model_conditions'] == [{'name': n, 'state': _condition(selection, n)} for n in premises if not n.startswith('conversion.')])
            require(row['model_settings'] == _settings(selection, component))
            expected_conversions = []
            for name in premises:
                if name.startswith('conversion.'):
                    role = name.split('.')[1]; original = selection['common_quantity'][role+'_conversion']
                    expected_conversions.append({'role': role, 'kind': original['kind'],
                        'direction': original['direction']['value'], 'support_status': original['support_status']['value']})
            require(row['conversion_conditions'] == expected_conversions)
            dependency_roles = [r for r in roles if r in cell['operand_roles']]
            require([d['role'] for d in row['dependencies']] == dependency_roles)
            for dependency in row['dependencies']:
                value = inputs['quantities'][dependency['role']]
                for key in ('owner_key', 'physical_owner_key', 'dependency_keys', 'estimator_scale'):
                    require(dependency[key] == value[key])
                require(dependency['source_locations'] == [_location(loc) for loc in value['source_locations']])
                require(dependency['unit'] == value['canonical_unit'])
            expected_covariance = []
            if PROJECTION[component]['uses_covariance']:
                for block in inputs['covariance_blocks']:
                    if block['source_ref'] in cell['uncertainty']['covariance_source_refs'] or (
                            block['status'] == 'unavailable' and (not block['roles'] or set(block['roles']) & set(cell['operand_roles']))):
                        expected_covariance.append({k: block[k] for k in ('source_ref', 'artifact_ref', 'basis',
                            'variance_status', 'origin', 'systematic_coverage', 'derivation', 'status')})
            require(row['covariance_provenance'] == expected_covariance)
            require(row['dependence'] == [d for d in sheet['dependence'] if d['roles'] and set(d['roles']) <= set(cell['operand_roles'])])
            require(row['assumptions'] == _assumptions(selection, component, cell, sheet))
            # Validate saved offset custody, never parse a numerical value or
            # reopen a source. Mask order has no scientific meaning.
            witness_locations = [_location(w) for w in _witnesses(extraction) if 'artifact_ref' in w]
            expected_masks = witness_locations + _numeric_locations(extraction)
            expected_masks += [_location(w) for name in ('molecule', 'functional_assertion')
                if (w := _assertion_witness(extraction, name)) is not None]
            actual_masks = row['withheld_locations']
            require(len(actual_masks) == len({canonical(loc) for loc in actual_masks})
                and {canonical(loc) for loc in actual_masks} == {canonical(loc) for loc in expected_masks})
        rows = [{'sheet_ref': ref, **deepcopy(r)} for r in templates]
        validate_schema(rows, schemas['rows'])
        outcome = json.loads(operation['outcome'])
        require(set(outcome) == {'status', 'operation_ref', 'record_refs', 'changed_record_refs', 'result', 'feedback'}
            and outcome['changed_record_refs'] in ([], [ref]))
        require(outcome['status'] == 'completed' and outcome['feedback'] is None and outcome['record_refs'] == [ref])
        require(outcome['operation_ref'] == identity('operation', {'run_id': self.run_id,
            'episode_id': request['episode_id'], 'key': request['operation_key']}))
        require(canonical(outcome['result']) == canonical({'sheet_ref': ref, 'view': VIEW,
            'record_version': VERSION, 'cells': rows}))
        return saved


    def project_cells(self, sheet_refs, *, permitted_record_refs, components=None):
        selected = None if components is None else self._components(components)
        result = []
        for ref in dict.fromkeys(sheet_refs):
            if ref not in permitted_record_refs:
                raise ContractError('literature_sheet_not_received')
            saved = self.read(ref)
            by_name = {r['component']: r for r in saved['row_templates']}
            result.extend({'sheet_ref': ref, **deepcopy(by_name[name])} for name in
                (list(by_name) if selected is None else selected) if name in by_name)
        return result


    def validate_returned_values(self, cells, *, permitted_record_refs):
        validate_schema(cells, MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2)
        seen = set()
        for row in cells:
            key = row['sheet_ref'], row['component']
            if key in seen:
                raise ContractError('duplicate_measurement_comparison_return_cell')
            seen.add(key)
            expected = self.project_cells([row['sheet_ref']], permitted_record_refs=permitted_record_refs, components=[row['component']])
            if canonical(expected) != canonical([row]):
                raise ContractError('measurement_comparison_return_differs_from_saved_cells')


    def received_cells(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        return super().received_cells(context) if self._installed(self.received_table) else []


    def receive_cells(self, context, cells, operation_key):
        if cells:
            with self.store.transaction():
                self._install(); return super().receive_cells(context, cells, operation_key)


    def selected_sheet_refs(self, context):
        if context.run_id != self.run_id:
            raise ContractError('literature_run_mismatch')
        if not self._installed(self.operations_table):
            return []
        refs = list(dict.fromkeys(json.loads(r['outcome'])['result']['sheet_ref'] for r in self.store.db.execute(
            f'SELECT outcome FROM {self.operations_table} WHERE run_id=? AND episode_id=? ORDER BY rowid', (self.run_id, context.episode_id))))
        for ref in refs:
            self.read(ref)
        return refs


    def available_sheet_refs(self, context):
        return list(dict.fromkeys([*(r for r in self.selected_sheet_refs(context) if r in context.received_record_refs),
            *(r['sheet_ref'] for r in self.received_cells(context) if r['sheet_ref'] in context.received_record_refs)]))


    def has_work(self, context):
        return bool(self.available_sheet_refs(context))


    def validate_empty_return_family(self, context):
        return None


    @staticmethod
    def cell_record_refs(cells):
        refs = []
        def visit(value):
            if isinstance(value, dict):
                for name, child in value.items():
                    if name.endswith('_ref') and isinstance(child, str) and child.startswith(('source_', 'artifact_')):
                        refs.append(child)
                    else:
                        visit(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    visit(child)
        visit(cells)
        return list(dict.fromkeys(refs))


    def receipt_bindings(self):
        result = {}
        if not self._installed(self.operations_table):
            return result
        for row in self.store.db.execute(f'SELECT outcome FROM {self.operations_table} WHERE run_id=?', (self.run_id,)):
            ref = json.loads(row['outcome'])['result']['sheet_ref']; source = self.store.get(ref)
            result[ref] = {'run_id': self.run_id, 'episode_id': self._sheet_owner(ref),
                'artifacts': [source['artifact_ref'], source['request_ref']]}
        return result


    def _private_binding(self, ref, artifact=None):
        bindings = self.receipt_bindings()
        if ref in bindings:
            return bindings[ref]
        for binding in bindings.values():
            if artifact in binding['artifacts']:
                return binding
        source = self.store.get(ref) if ref is not None else {}
        if source.get('provider') == PROVIDER:
            raise ContractError('measurement_comparison_receipt_binding_invalid')
        return None


    def authorize_source_access(self, context, ref, representation, tool_name):
        source = self.store.get(ref)
        if source.get('record_type') != 'source':
            return
        artifact = (source.get('text_ref') or source['artifact_ref']) if representation == 'text' and tool_name == 'source.read' else (
            source['artifact_ref'] if representation == 'original' else source.get(representation+'_ref'))
        binding = self._private_binding(ref, artifact)
        if binding and (binding['run_id'], binding['episode_id']) != (context.run_id, context.episode_id):
            raise ContractError('measurement_comparison_receipt_private')


    def authorize_record_access(self, context, record):
        if record.get('record_type') in {'source', 'artifact'}:
            return
        for anchor in (record, record.get('anchor'), record.get('visual_anchor')):
            if not isinstance(anchor, dict):
                continue
            binding = self._private_binding(anchor.get('source_ref'), anchor.get('artifact_ref'))
            if binding and (binding['run_id'], binding['episode_id']) != (context.run_id, context.episode_id):
                raise ContractError('measurement_comparison_receipt_private')


__all__ = ["LiteratureMeasurementComparisonRepository", "measurement_comparison_cells_schema", "measurement_comparison_operation_schema", "MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2", "MEASUREMENT_COMPARISON_REQUEST_SCHEMA_V2", "PROVIDER", "VERSION", "POPULATION", "NAMESPACE", "REQUESTED", "VIEW", "SCOPE", "OPERATION", "COMPONENTS"]
