"""Source-bound v3 readers and closed parsed contracts for internal A105 sheets.

These host functions read experimental quantities and preserve source meanings.
"""
from __future__ import annotations
from copy import deepcopy as cp
import json
from functools import lru_cache
from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_v2_inputs as v2
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_inputs as shared

from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_v3_contracts import (
    _schemas, controlled_response_v3_arguments_schema, _extraction_schema
)

def validate_controlled_response_v3_selection(arguments):
    selected = shared._validate_selection(arguments, controlled_response_v3_arguments_schema())
    roster = {(role, None): arm for role, arm in selected["arms"].items()}
    keys = set()
    for row in selected["companion_readings"]:
        key = row["reading_key"]
        if key in keys:
            shared._fail("duplicate_companion_reading_key", "companion_readings")
        keys.add(key)
        roster[(row["primary_role"], key)] = row["reading"]
    def selector(value, field):
        if (value["role"], value["reading_key"]) not in roster:
            shared._fail("controlled_reading_selector_unresolved", field)
    for arm in roster.values():
        if arm and arm["measurement"] and arm["measurement"]["kind"] == "linear_bar":
            v2.graph_reader._validate(v2._graph_request(selected, arm["measurement"]))
    maps = set()
    for row in selected["joint_reading_assignments"]:
        key = tuple(row["assignment"][r] for r in shared.PRIMITIVE_ORDER)
        if key in maps:
            shared._fail("duplicate_joint_reading_assignment", "joint_reading_assignments")
        maps.add(key)
        for role, reading_key in row["assignment"].items():
            selector({"role": role, "reading_key": reading_key}, "joint_reading_assignments")
    indices = [r["assignment_index"] for r in selected["joint_scopes"]]
    if indices != list(range(len(selected["joint_reading_assignments"]))):
        shared._fail("joint_scope_roster_mismatch", "joint_scopes")
    roles = set()
    for row in selected["reading_reconciliations"]:
        role = row["role"]
        if role in roles:
            shared._fail("duplicate_reconciliation_role", "reading_reconciliations")
        roles.add(role)
        auth = row["authority"]
        if auth["status"] == "source_explicit":
            if auth["reading"] is None or auth["reading"]["role"] != role:
                shared._fail("authority_reading_role_mismatch", "reading_reconciliations")
            selector(auth["reading"], "reading_reconciliations.authority.reading")
        elif auth["reading"] is not None:
            shared._fail("authority_reading_without_designation", "reading_reconciliations")
        minimum = 2 if auth["status"] == "conflicting" else 1 if auth["status"] == "source_explicit" else 0
        if len({shared._nomination_key(w) for w in auth["witnesses"]}) < minimum:
            shared._fail("interpretation_witness_required", "reading_reconciliations.authority")
    needed = {r["primary_role"] for r in selected["companion_readings"]}
    if not needed <= roles:
        shared._fail("reading_reconciliation_missing", "reading_reconciliations")
    pairs = set()
    for row in selected["local_pair_assignments"]:
        if row["pair_key"] in pairs:
            shared._fail("duplicate_local_pair_key", "local_pair_assignments")
        pairs.add(row["pair_key"])
        for name, prefix in (("protein", "protein_"), ("control", "empty_")):
            value = row[name]
            selector(value, "local_pair_assignments." + name)
            if value["role"] != prefix + row["condition"]:
                shared._fail("local_pair_role_mismatch", "local_pair_assignments." + name)
    return selected


def _dependencies():
    import hashlib
    from pathlib import Path
    names = list(v2._dependencies()) + ['literature_controlled_response_v3_inputs.py',
        'literature_controlled_response_local_calculations.py']
    paths = {
        'literature_assay_inputs.py': 'gene_annotation_episode/episodic_workflow/root/literature_assay_inputs.py',
        'literature_rate_native_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_rate_native_inputs.py',
        'literature_partner_source_fields.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_partner_source_fields.py',
        'literature_partner_defined_units.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_partner_defined_units.py',
        'literature_kinetic_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_kinetic_inputs.py',
        'literature_binding_visual_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_binding_visual_inputs.py',
        'literature_binding_reader.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_binding_reader.py',
        'literature_controlled_response_calculations.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_calculations.py',
        'literature_controlled_response_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_inputs.py',
        'literature_controlled_response_v2_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_v2_inputs.py',
        'literature_controlled_response_figure_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_figure_inputs.py',
        'literature_controlled_response_owner_calculations.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_owner_calculations.py',
        'literature_controlled_response_v3_inputs.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_v3_inputs.py',
        'literature_controlled_response_local_calculations.py': 'gene_annotation_episode/episodic_workflow/root/library/literature_controlled_response_local_calculations.py',
    }
    return {name: hashlib.sha256((Path(__file__).parents[4]/paths[name]).read_bytes()).hexdigest() for name in names}


def _selector(role, key=None):
    return {'role': role, 'reading_key': key}


def read_controlled_response_v3_inputs(arguments, *, read_source):
    """Read every actual nomination in one authenticated shared source context."""
    validate_controlled_response_v3_selection(arguments)
    with shared.open_controlled_response_sources(arguments, read_source=read_source) as context:
        readings, arms, companions = {}, {}, []
        nominations = [(_selector(r), context.arguments['arms'][r]) for r in shared.PRIMITIVE_ORDER]
        nominations += [(_selector(row['primary_role'], row['reading_key']), row['reading'])
            for row in context.arguments['companion_readings']]
        for selector, selected in nominations:
            arm = None
            if selected is not None:
                science = shared.read_controlled_response_arm_science(context, selected, reading_selector=selector)
                endpoint = science['meanings']['endpoint']
                measurement = (shared.read_controlled_response_graph_measurement(context, selector, endpoint=endpoint)
                    if selected['measurement'] and selected['measurement']['kind'] == 'linear_bar' else
                    shared.read_controlled_response_text_measurement(context, selected['measurement'],
                        endpoint=endpoint, reading_selector=selector))
                arm = shared.finish_controlled_response_arm(context, science, measurement=measurement, reading_selector=selector)
            readings[(selector['role'], selector['reading_key'])] = arm
            if selector['reading_key'] is None: arms[selector['role']] = arm
            else: companions.append((selector, arm))
        scopes = []
        scope_selectors = [({'kind': 'base', 'index': None}, [_selector(r) for r in shared.PRIMITIVE_ORDER])]
        scope_selectors += [({'kind': 'joint', 'index': i}, [_selector(r, row['assignment'][r]) for r in shared.PRIMITIVE_ORDER])
            for i, row in enumerate(context.arguments['joint_reading_assignments'])]
        scope_selectors += [({'kind': 'local', 'index': i}, [row['protein'], row['control']])
            for i, row in enumerate(context.arguments['local_pair_assignments'])]
        for scope, selectors in scope_selectors:
            document = shared.read_controlled_response_covariance_document(context, scope)
            scopes.append(shared.bind_controlled_response_covariance_scope(context, scope, document,
                readings=[(s, readings[(s['role'], s['reading_key'])]) for s in selectors]))
        return shared.finish_controlled_response_inputs(context, arms=arms, companion_arms=companions, covariance_scopes=scopes)


def _relation(context, nomination, field):
    witnesses = [context.witness(w, field) for w in nomination['witnesses']]
    value = nomination['value']
    if any(w['canonical_locator'] is None for w in witnesses): value = 'unknown'
    return {'selection': cp(nomination), 'witnesses': witnesses, 'effective_value': value}


def _same_science(members):
    if not members or any(a is None for _, a in members): return 'unknown'
    arms = [a for _, a in members]
    if any(v['resolved_state'] == 'conflicting' for a in arms for v in a['meanings'].values()): return 'conflicting'
    if any(v['resolved_state'] != 'known' for a in arms for v in a['meanings'].values()): return 'unknown'
    first = arms[0]
    for arm in arms[1:]:
        if any(arm['meanings'][m]['canonical_id'] != first['meanings'][m]['canonical_id'] for m in shared._MEANINGS): return 'conflicting'
        if arm['protein_arrangement']['effective_value'] != first['protein_arrangement']['effective_value']: return 'conflicting'
        if arm['context'] != first['context']: return 'unknown'
    return 'same'


def _domain(arm):
    return shared._exact_response(arm['measurement'], graph=bool(arm['graph_details'])) if arm else None


def _domain_relation(selected, other):
    if selected is None or other is None or selected['unit'] is None or other['unit'] != selected['unit']:
        return 'unknown'
    if selected == other: return 'equal'
    if shared._response_domains_disjoint(selected, other): return 'disjoint'
    # A reported point can be consistent with a display without equating them.
    if selected['relation'] == 'eq' and selected['point'] is not None and other['lower'] and other['upper']:
        point = shared._fraction(selected['point'])
        if shared._fraction(other['lower']) <= point <= shared._fraction(other['upper']): return 'contains'
    return 'unknown'


def _reconcile(context, nomination, members):
    field = 'reading_reconciliations.' + nomination['role']
    relationship = _relation(context, nomination['relationship'], field + '.relationship')
    relations = {k: _relation(context, nomination[k], field + '.' + k) for k in ('normalization', 'calibration', 'revision', 'model_scope')}
    auth = nomination['authority']
    auth_witnesses = [context.witness(w, field + '.authority') for w in auth['witnesses']]
    science = _same_science(members)
    authority = auth['status'] if all(w['canonical_locator'] is not None for w in auth_witnesses) else 'not_established'
    state, method, chosen = 'unknown_authority', 'unresolved', None
    if science != 'same': state = 'scientific_conflict' if science == 'conflicting' else 'unsupported_group_projection'
    elif authority == 'conflicting' or relationship['effective_value'] == 'conflicting': state = 'conflicting_authority'
    elif any(r['effective_value'] in ('unknown', 'conflicting') for k, r in relations.items() if k != 'model_scope'):
        state = 'unsupported_group_projection'
    else:
        domains = [_domain(a) for s, a in members]
        if len(members) == 1:
            state, method, chosen = 'ready', 'single', members[0][0]
        elif relationship['effective_value'] == 'exact_duplicate' and domains[0] is not None and all(d == domains[0] for d in domains):
            state, method, chosen = 'ready', 'exact_equivalence', members[0][0]
        elif authority == 'source_explicit' and relationship['effective_value'] == 'same_reported_mean_and_display':
            selected = next((a for s, a in members if s == auth['reading']), None)
            domain = _domain(selected)
            checks = [_domain_relation(domain, d) for d in domains]
            if domain and domain['relation'] == 'eq' and not domain['approximate'] and all(c in ('equal', 'contains') for c in checks):
                state, method, chosen = 'ready', 'explicit_reported_mean_display', cp(auth['reading'])
            elif 'disjoint' in checks: state = 'different_domains'
        elif any(shared._response_domains_disjoint(a, b) for i, a in enumerate(domains) if a for b in domains[:i] if b):
            state = 'different_domains'
    selected_domain = _domain(next((a for s, a in members if s == chosen), None))
    qualifications = ['same_representation_not_replication'] if len(members) > 1 else []
    if any(a and a['graph_details'] for s, a in members): qualifications.append('conditional_digitization_not_sampling')
    if method == 'explicit_reported_mean_display': qualifications.append('source_explicit_reported_mean')
    origins = {a['calculation_operand']['origin'] for s, a in members if a}
    if len(origins) > 1: qualifications.append('mixed_original_origins_retained')
    model_state = ('original_source_model' if state == 'ready' and relations['model_scope']['effective_value'] in ('same', 'explicit_compatible')
        else 'none' if relations['model_scope']['effective_value'] == 'not_applicable' else 'unresolved')
    return {'role': nomination['role'], 'selection': cp(nomination),
        'witnesses': [w for r in [relationship, *relations.values()] for w in r['witnesses']] + auth_witnesses,
        'reading_selectors': [cp(s) for s, a in members], 'scientific_correspondence': science,
        'method': method, 'state': state, 'selected_reading': cp(chosen),
        'normalized_domain_checks': [{'reading': cp(s), 'relation_to_selected': _domain_relation(selected_domain, _domain(a))} for s, a in members],
        'model_state': model_state, 'qualifications': sorted(set(qualifications))}


def _requested(context, variance, model, field):
    return {'variance_status': shared._interpretation(context, variance, field + '.variance_status'),
        'model_kind': shared._interpretation(context, model, field + '.model_kind')}


def _owner_projection(arms, relationships, covariance, requested, *, variance_scope=True, model_scope=True):
    effective = shared._effective_model(requested, covariance if variance_scope else None, arms)
    if not model_scope: effective['model_kind'] = 'none'
    parsed = shared._calculation_inputs(arms, relationships, covariance, effective)
    parsed['version'] = 'controlled_response_owner_inputs_v2'
    owner.validate_controlled_response_owner_inputs(parsed)
    return parsed, effective


def _group_mask(role, members):
    """A real retained unresolved group, never an invented union origin."""
    from gene_annotation_episode.domain import identity
    actual = [a for s, a in members if a]
    if not actual or _same_science(members) != 'same': return None, 'unavailable_group_identity'
    operands = [a['calculation_operand'] for a in actual]
    if len({a['origin'] for a in operands}) != 1: return None, 'unsupported_origin_projection'
    if any(a['source_observation_id'] is None for a in operands): return None, 'unavailable_group_identity'
    dimensions = {shared.RATE_UNITS[a['unit']][0] for a in operands if a['unit']}
    if len(dimensions) != 1 or any(a['unit'] is None for a in operands): return None, 'unavailable_group_identity'
    payload = {'primary_role': role, 'primary_reading_id': operands[0]['source_observation_id'],
        'companions': [{'reading_key': s['reading_key'], 'reading_id': a['calculation_operand']['source_observation_id']} for s, a in members[1:]],
        'scientific_owner_id': operands[0]['physical_observation_id'],
        'members': [{'source_kind': a['selection']['source_kind'], 'measurement_method':
            'graph' if a['graph_details'] else 'text' if a['selection']['measurement'] else 'not_selected'} for a in actual]}
    mask = cp(operands[0])
    mask.update(value=None, threshold=None, relation='none', status='ambiguous', digitization_interval=None,
        approximate=any(a['approximate'] for a in operands), source_observation_id=identity('controlled_active_reading_group_v3', payload))
    return mask, 'ready'


def _finish_v3(context, *, arms, companion_arms, covariance_scopes):
    selected = context.arguments
    relationships = cp(context.relationships)
    roster = {(r, None): arms[r] for r in shared.PRIMITIVE_ORDER}
    roster.update({(s['role'], s['reading_key']): a for s, a in companion_arms})
    scopes = {(s['scope']['kind'], s['scope']['index']): s for s in covariance_scopes}
    base_covariance = cp(scopes[('base', None)]['whole_projection'])
    requested = _requested(context, selected['variance_status'], selected['model_kind'], 'model')
    decisions = []
    assignment = {r: None for r in shared.PRIMITIVE_ORDER}
    unresolved = []
    groups = owner._groups([arms[r]['calculation_operand'] if arms[r] else None for r in shared.PRIMITIVE_ORDER])
    canceled = {r for g in groups if g['known_owner'] and g['coefficient'] == 0 for r in g['roles']}
    for nomination in selected['reading_reconciliations']:
        role = nomination['role']
        members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
        decision = _reconcile(context, nomination, members); decisions.append(decision)
        if decision['state'] == 'ready': assignment[role] = decision['selected_reading']['reading_key']
        elif role not in canceled or _same_science(members) != 'same': unresolved.append(role)
    joint_rows, alternatives = [], []
    for i, nomination in enumerate(selected['joint_reading_assignments']):
        spec = selected['joint_scopes'][i]
        admissibility = _relation(context, nomination['admissibility'], 'joint_reading_assignments')
        relations = {k: _relation(context, spec[k], 'joint_scopes.' + k) for k in
            ('normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope')}
        compatible = admissibility['effective_value']
        for k in ('normalization', 'calibration', 'revision'):
            if relations[k]['effective_value'] == 'conflicting': compatible = 'conflicting'
            elif relations[k]['effective_value'] == 'unknown' and compatible != 'conflicting': compatible = 'unknown'
        covariance = cp(scopes[('joint', i)]['whole_projection'])
        request = _requested(context, spec['variance_status'], spec['model_kind'], 'joint_scopes')
        joint_arms = {r: roster[(r, nomination['assignment'][r])] for r in shared.PRIMITIVE_ORDER}
        parsed, effective = _owner_projection(joint_arms, relationships, covariance, request,
            variance_scope=relations['covariance_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'),
            model_scope=relations['model_scope']['effective_value'] in ('same', 'explicit_compatible', 'not_applicable'))
        joint_rows.append({'assignment_index': i, 'witnesses': admissibility['witnesses'] +
            [w for rel in relations.values() for w in rel['witnesses']], 'effective_admissibility': compatible,
            'source_covariance': covariance, 'requested_model': request, 'effective_model': effective})
        if compatible == 'compatible':
            alternatives.append({'reading_assignment': cp(nomination['assignment']), 'scope_index': i,
                'source_covariance': covariance, 'requested_model': request, 'effective_model': effective, 'calculation_inputs': parsed})
    projection, basis = None, None
    effective = {'variance_status': 'unknown', 'model_kind': 'none', 'diagnostics': []}
    if not unresolved:
        matching = next((a for a in alternatives if a['reading_assignment'] == assignment), None)
        if all(v is None for v in assignment.values()):
            projection, effective = _owner_projection(arms, relationships, base_covariance, requested,
                model_scope=all(d['model_state'] == 'original_source_model' for d in decisions if d['state'] == 'ready'))
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'base', 'scope_index': None,
                'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        elif matching:
            projection, effective = cp(matching['calculation_inputs']), cp(matching['effective_model'])
            basis = {'reading_assignment': cp(assignment), 'covariance_scope': 'joint', 'scope_index': matching['scope_index'],
                'reconciled_roles': [d['role'] for d in decisions if d['state'] == 'ready']}
        else:
            unresolved = [r for r, key in assignment.items() if key is not None]
    partial, partial_state = None, 'not_required'
    if projection is None:
        masked_arms = {r: cp(dict(a)) if a is not None else None for r, a in arms.items()}
        partial_state = 'ready'
        for role in unresolved:
            members = [(_selector(role), arms[role])] + [(s, a) for s, a in companion_arms if s['role'] == role]
            mask, state = _group_mask(role, members)
            if state != 'ready': partial_state = state; break
            masked_arms[role]['calculation_operand'] = mask
        if partial_state == 'ready':
            partial, unused_effective = _owner_projection(masked_arms, relationships, base_covariance, requested, model_scope=False)
    unknown_uncertainty = {'statistic': 'unknown', 'magnitude': None, 'interval': None, 'confidence_level': None,
        'count': None, 'repetition_basis': 'unknown', 'estimate_basis': 'unknown'}
    local_readings = []
    for (role, key), arm in roster.items():
        local_readings.append({'reading': _selector(role, key), 'arm': cp(arm['calculation_operand']) if arm else None,
            'reported_uncertainty': cp(arm['reported_uncertainty']['canonical']) if arm else cp(unknown_uncertainty),
            'source_kind': arm['selection']['source_kind'] if arm else None,
            'measurement_method': 'graph' if arm and arm['graph_details'] else 'text' if arm and arm['selection']['measurement'] else 'not_selected'})
    documents, source_indices = [], {}
    for scope in covariance_scopes:
        document = scope['document']
        if document is not None and document['source_ref'] not in source_indices:
            source_indices[document['source_ref']] = len(documents); documents.append(cp(document))
    pairs, pair_extractions = [], []
    for i, pair in enumerate(selected['local_pair_assignments']):
        scope = scopes[('local', i)]
        document = scope['document']
        admissibility = _relation(context, pair['admissibility'], 'local_pair_assignments.admissibility')
        scope_relation = _relation(context, pair['scope'], 'local_pair_assignments.scope')
        bindings = [b['binding'] for b in scope['bindings']]
        variance = shared._interpretation(context, pair['variance_status'], 'local_pair_assignments.variance_status')
        pair_extractions.append({'pair_key': pair['pair_key'], 'admissibility': admissibility,
            'scope': scope_relation, 'variance_status': variance})
        pairs.append({'pair_key': pair['pair_key'], 'condition': pair['condition'], 'protein': cp(pair['protein']), 'control': cp(pair['control']),
            'target': shared._relationships_inputs(relationships)[pair['condition'] + '_target'],
            'control_application': relationships[pair['condition'] + '_control_application']['effective_value'],
            'joint_admissibility': admissibility['effective_value'], 'scope_state': scope_relation['effective_value'],
            'covariance_index': source_indices[document['source_ref']] if document else None,
            'protein_binding': cp(bindings[0]) if document else None, 'control_binding': cp(bindings[1]) if document else None,
            'variance_status': variance['effective_value']})
    result = {'version': 'controlled_response_source_extraction_v3', 'selection': cp(selected), 'sources': cp(context.roster),
        'images': cp(context.images), 'arms': {r: cp(dict(a)) if a else None for r, a in arms.items()},
        'relationships': relationships, 'covariance': base_covariance, 'requested_model': requested, 'effective_model': effective,
        'calculation_inputs': projection, 'representation_reconciliations': shared._representations(arms), 'diagnostics': [],
        'implementation_dependencies': {'reader_contract_version': 'controlled_response_source_extraction_v3',
            'calculator_contract_version': 'controlled_response_owner_inputs_v2', 'expected_module_fingerprints': _dependencies()},
        'companion_extractions': [{'reading_key': s['reading_key'], 'primary_role': s['role'], 'reading': cp(dict(a))} for s, a in companion_arms],
        'projection_status': 'ready' if projection is not None else 'unresolved_active_reconciliation', 'final_projection_basis': basis,
        'reconciliation_decisions': decisions, 'joint_scope_extractions': joint_rows, 'alternative_inputs': alternatives,
        'partial_calculation_inputs': partial, 'partial_projection_state': partial_state,
        'local_pair_extractions': pair_extractions,
        'component_local_inputs': {'version': 'controlled_response_local_inputs_v1', 'readings': local_readings, 'pairs': pairs, 'source_covariances': documents},
        'covariance_document_scopes': [{'scope': cp(s['scope']), 'document': cp(s['document'])} for s in covariance_scopes]}
    for record in result['representation_reconciliations']:
        for reading in record['readings']: reading['reading_key'] = None
    result['diagnostics'] = shared._unique_diagnostics(result, stable=True)
    Draft202012Validator(_extraction_schema()).validate(result)
    json.dumps(result, allow_nan=False)
    return cp(result)


def validate_controlled_response_v3_extraction(arguments, extraction):
    def check(selector, selected, measurement, *, source_records, image_records):
        if selected and selected['kind'] == 'linear_bar':
            arm = (extraction['arms'][selector['role']] if selector['reading_key'] is None else
                next(row['reading'] for row in extraction['companion_extractions'] if row['primary_role'] == selector['role'] and row['reading_key'] == selector['reading_key']))
            if arm['graph_details'] is None or arm['graph_details']['measurement'] != measurement:
                shared._fail('saved_graph_measurement_mismatch', 'measurement')
            return v2._validate_graph(selected, arm['graph_details'], sources={(s['source_ref'], s['representation']): s for s in source_records},
                images=image_records, request=arguments)
        return v2._validate_measurement(selected, measurement, source_records=source_records, image_records=image_records)
    return shared.validate_controlled_response_saved_science(arguments, extraction, measurement_checks=check)


__all__ = ['controlled_response_v3_arguments_schema', 'validate_controlled_response_v3_selection',
    'read_controlled_response_v3_inputs', 'validate_controlled_response_v3_extraction']
