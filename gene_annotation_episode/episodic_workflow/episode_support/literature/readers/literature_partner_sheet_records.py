"""Selected immutable partner sheets and exact typed receipt projection.

Custody validates retained source records; it does not establish the truth of
supplied experimental interpretations. Saved reads never reopen source bytes or
repeat calculation. Ordinary episode accounting belongs to the caller.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import unicodedata
from gene_annotation_episode.episodic_workflow.episode_support.forms.partner_presence_evidence.communication import plain
from gene_annotation_episode.episodic_workflow.episode_support.records.partner_presence_evidence.domain import ContractError, canonical, identity, obj, validate_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.partner_presence_evidence.literature_assay_inputs import SOURCE_KINDS
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_partner_inputs import COMPONENTS, LITERAL_FIELDS, partner_population_schema, read_partner_inputs
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.literature_partner_native_inputs import native_evidence_schema as _native_evidence_schema, partner_source_population_schema as _native_population_schema
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.literature_partner_models import EXPERIMENT_TYPES
from gene_annotation_episode.episodic_workflow.episode_support.readers.source_display_labels import source_literal_label
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading import literature_experiment_assessments as assessments
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.partner_presence_evidence.literature_sheet_updates import publication
PROVIDER = 'literature.experimental.partner'
FORMULA_CODES = dict(zip(COMPONENTS, ('native_partner_reference', 'native_partner_omitted', 'native_partner_addback', 'partner_reference_minus_omitted', 'partner_loss_over_reference', 'partner_addback_minus_omitted', 'partner_gain_over_loss', 'partner_gain_over_reference')))
BINDINGS = {'subject_ref': ('subject', 'reference'), 'partner_ref': ('partner', 'reference'), 'experiment_ref': ('experiment', 'reference'), 'endpoint_ref': ('endpoint', 'term'), 'normalization_ref': ('normalization', 'term'), 'reference_condition_ref': ('reference_condition', 'context'), 'omitted_condition_ref': ('omitted_condition', 'context'), 'addback_condition_ref': ('addback_condition', 'context'), 'function_ref': ('function', 'term')}
LITERAL_REFERENCE_ROLES_VERSION = 'partner_literal_reference_roles'
LITERAL_REFERENCE_TYPES = {'subject': 'literature_result', 'partner': 'literature_result', 'experiment': 'assay'}
NATIVE_UNITS = ('pmol/min/mg', 'nmol/min/mg', 'umol/min/mg', 'per_min', 'per_s', 'uM/min', 'nM/min')
CHECK_REASONS = ('arm_unreported', 'nonpartner_conditions_differ', 'subject_unreported', 'subject_mismatch', 'partner_unreported', 'partner_mismatch', 'endpoint_unreported', 'endpoint_mismatch', 'normalization_unreported', 'normalization_mismatch', 'unit_unreported', 'unit_mismatch', 'partner_presence_not_established', 'condition_factor_scope_unresolved', 'conditions_incomplete', 'measurement_identity_unreported', 'role_measurement_not_distinct')
REASONS = (*CHECK_REASONS, 'measurement_unreported', 'censored_point_unreported', 'nonpositive_reference_domain', 'zero_or_straddling_loss_domain', 'numerical_model_range')
_ROLES = ('reference', 'omitted', 'addback')
_FIXED_METADATA = {'evaluation_scope': 'reference_experimental_partner_components', 'target_correspondence': 'not_evaluated', 'partner_necessity': 'not_inferred', 'statistical_uncertainty': 'not_evaluated', 'measurement_corrections': 'not_applied'}
_NATIVE_ARGUMENT_SCHEMA = _native_population_schema()
_NATIVE_EVIDENCE_SCHEMA = _native_evidence_schema()
_NATIVE_PLAIN_EVIDENCE_SCHEMA = _native_evidence_schema(defined_units=False)

def partner_source_population_schema():
    """Closed native-selector operands; independent of source work at replay."""
    return deepcopy(_NATIVE_ARGUMENT_SCHEMA)

def _arguments_schema(args):
    return partner_source_population_schema() if isinstance(args, dict) and 'input_mode' in args else partner_population_schema(include_assessment=True)

def _native_version(args):
    """Select the frozen representation from declared unit branches, not values."""
    for arm in args['arms'].values():
        if arm is None or arm['rate'] is None:
            continue
        for unit in (arm['rate']['unit'], arm['rate']['spread']['unit']):
            if isinstance(unit, dict) and unit.get('kind') == 'source_defined_rate_unit':
                return 'literature_partner_defined_unit_extraction'
    return 'literature_partner_native_extraction'

def _spread_schema():
    return obj({'kind': {'type': 'string', 'enum': ['SD', 'SEM', 'CI', 'unspecified', 'unreported']}, 'magnitude': {'type': ['number', 'null'], 'minimum': 0}})

def _arm_metadata_schema():
    arm = obj({'partner_state': {'type': 'string', 'enum': ['present', 'absent', 'unreported']}, 'condition_coverage': {'type': 'string', 'enum': ['complete', 'partial', 'unreported']}, 'spread': _spread_schema()})
    return obj({role: {**deepcopy(arm), 'type': ['object', 'null']} for role in _ROLES})

def _check_schema(*, raw=False):
    return obj({'status': {'type': 'string', 'enum': ['matched', 'different', 'unresolved']}, 'differing_factors' if raw else 'differing_factor_refs': {'type': 'array', 'items': {'type': 'string', 'minLength': 1} if raw else {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'term'}, 'uniqueItems': True}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *CHECK_REASONS]}})

def _checks_schema(*, raw=False):
    return obj({name: _check_schema(raw=raw) for name in ('reference_omitted', 'addback_omitted')})

def _cell_schema():
    return obj({**{field: {'type': ['number', 'null']} for field in ('value', 'lower', 'upper')}, 'unit': {'type': ['string', 'null'], 'enum': [*NATIVE_UNITS, 'dimensionless', None]}, 'origin': {'type': ['string', 'null'], 'enum': ['reported', 'graph_derived', 'synthetic', 'derived', None]}, 'bound_kind': {'type': 'string', 'enum': ['point_only_not_uncertainty', 'conditional_input_domain_not_CI']}, 'status': {'type': 'string', 'enum': ['populated', 'bounded', 'unavailable']}, 'unavailable_reason': {'type': ['string', 'null'], 'enum': [None, *REASONS]}})

def _input_schema():
    text = {'type': 'string', 'minLength': 1}
    nullable = {**text, 'type': ['string', 'null']}
    factor = obj({'factor': text, 'level': {'type': ['number', 'string', 'null']}, 'unit': text})
    arm = obj({**{name: deepcopy(nullable) for name in ('subject_ref', 'partner_ref', 'endpoint_ref', 'normalization_ref')}, 'partner_state': {'enum': ['present', 'absent', 'unreported']}, 'unit': {'enum': [*NATIVE_UNITS, 'unreported']}, 'conditions': obj({'coverage': {'enum': ['complete', 'partial', 'unreported']}, 'factors': {'type': 'array', 'items': factor}}), 'measurement': obj({'measurement_id': nullable, 'status': {'enum': ['observed', 'upper_bound', 'unreported']}, 'value': {'type': ['number', 'null'], 'minimum': 0}, 'origin': {'enum': ['reported', 'graph_derived', 'synthetic']}, 'spread': _spread_schema()})})
    return obj({'version': {'const': 'literature_partner_inputs'}, 'arms': obj({role: {**deepcopy(arm), 'type': ['object', 'null']} for role in _ROLES})})

def _metadata(extraction, factor_bindings):
    arms = extraction['recipe']['inputs']['arms']
    return {**_FIXED_METADATA, 'source_kind': extraction['arguments']['source_kind'], 'comparison_checks': {name: {'status': check['status'], 'unavailable_reason': check['unavailable_reason'], 'differing_factor_refs': [factor_bindings[factor] for factor in check['differing_factors']]} for name, check in extraction['calculation']['comparison_checks'].items()}, 'arm_metadata': {role: None if arm is None else {'partner_state': arm['partner_state'], 'condition_coverage': arm['conditions']['coverage'], 'spread': deepcopy(arm['measurement']['spread'])} for role, arm in arms.items()}}

def _direct_references(args):
    direct = list(dict.fromkeys([args['source_ref'], args['data_source_ref'], *(args['literals'][field]['source_ref'] for field in LITERAL_FIELDS if args['literals'][field] is not None), *(entry['source_ref'] for entry in args['interpretation_witnesses'])]))
    if args.get('input_mode') == 'native_source_spans':

        def references(value):
            if isinstance(value, dict):
                if 'source_ref' in value:
                    yield value['source_ref']
                for child in value.values():
                    yield from references(child)
            elif isinstance(value, list):
                for child in value:
                    yield from references(child)
        direct.extend(sorted(set(references(args['arms'])) - set(direct)))
    return direct

def _saved_check(first, omitted):
    """Validate frozen experimental relationships without reading or arithmetic."""

    def result(status, reason, differences=()):
        return {'status': status, 'differing_factors': list(differences), 'unavailable_reason': reason}
    if first is None or omitted is None:
        return result('unresolved', 'arm_unreported')
    left = {f['factor']: f for f in first['conditions']['factors']}
    right = {f['factor']: f for f in omitted['conditions']['factors']}
    differences = sorted((name for name in left.keys() & right.keys() if left[name]['unit'] != right[name]['unit'] or (left[name]['level'] is not None and right[name]['level'] is not None and (left[name]['level'] != right[name]['level']))))
    if differences:
        return result('different', 'nonpartner_conditions_differ', differences)
    for key, stem in (('subject_ref', 'subject'), ('partner_ref', 'partner'), ('endpoint_ref', 'endpoint'), ('normalization_ref', 'normalization')):
        if first[key] is None or omitted[key] is None:
            return result('unresolved', stem + '_unreported')
        if first[key] != omitted[key]:
            return result('different', stem + '_mismatch')
    if first['unit'] == 'unreported' or omitted['unit'] == 'unreported':
        return result('unresolved', 'unit_unreported')
    if first['unit'] != omitted['unit']:
        return result('different', 'unit_mismatch')
    if first['partner_state'] != 'present' or omitted['partner_state'] != 'absent':
        return result('unresolved', 'partner_presence_not_established')
    if left.keys() != right.keys():
        return result('unresolved', 'condition_factor_scope_unresolved')
    if any((a['conditions']['coverage'] != 'complete' for a in (first, omitted))):
        return result('unresolved', 'conditions_incomplete')
    keys = [a['measurement']['measurement_id'] for a in (first, omitted)]
    if None in keys:
        return result('unresolved', 'measurement_identity_unreported')
    if keys[0] == keys[1]:
        return result('unresolved', 'role_measurement_not_distinct')
    return result('matched', None)

def _factor_record(data_source_ref, name):
    return {'namespace': 'literature_partner_condition_factor', 'accession': identity('partner_factor', {'data_source_ref': data_source_ref, 'factor': name}), 'label': name, 'term_type': 'other', 'source_ref': data_source_ref, 'anchor': None}

def _factor_names(extraction):
    return sorted({factor for check in extraction['calculation']['comparison_checks'].values() for factor in check['differing_factors']})

def literal_reference_role(record):
    """Identify original literal roles without interpreting labels or reading sources."""
    if record.get('record_type') != 'reference' or record.get('origin') != 'tool':
        return None
    anchor = record.get('anchor')
    if not isinstance(anchor, dict):
        return None
    for role, kind in BINDINGS.values():
        if kind not in {'reference', 'context'}:
            continue
        if record.get('accession') == identity('partner_literal', {'field': role, **anchor}):
            return role
    return None

def _binding_record(literal, kind, entry):
    witness = entry['witness']
    anchor = {name: witness[name] for name in ('source_ref', 'artifact_ref', 'start', 'end', 'quote')}
    common = {'source_ref': witness['source_ref'], 'anchor': anchor}
    accession = identity('partner_literal', {'field': literal, **anchor})
    label = source_literal_label(entry['value'])
    if kind == 'reference':
        return {**common, 'reference_type': LITERAL_REFERENCE_TYPES.get(literal, 'literature_result'), 'accession': accession, 'label': label, 'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': []}
    if kind == 'term':
        return {**common, 'namespace': 'literature_partner_' + literal, 'accession': accession, 'label': label, 'term_type': 'other'}
    role = _condition_role(literal, entry)
    return {**common, 'context_type': 'assay_condition', 'name': label, 'attributes': [], 'related_refs': [identity('reference', {'origin': 'tool', 'record': role})]}

def _condition_role(literal, entry):
    return _binding_record(literal, 'reference', entry)

def _condition_refs(extraction):
    return [identity('reference', {'origin': 'tool', 'record': _condition_role(literal, entry)}) for literal, kind in BINDINGS.values() if kind == 'context' and (entry := extraction['literals'][literal]) is not None]
_NATIVE_BINDING_VERSION = 'partner_native_operand_bindings'
_NATIVE_IDENTITY_FIELDS = ('subject', 'partner', 'endpoint', 'normalization')
_COMPONENT_ROLES = {'reference_rate': ('reference',), 'omitted_rate': ('omitted',), 'addback_rate': ('addback',), 'partner_loss': ('reference', 'omitted'), 'partner_loss_fraction': ('reference', 'omitted'), 'addback_gain': ('addback', 'omitted'), 'addback_fraction': _ROLES, 'restored_reference_fraction': _ROLES}

def _native_operand_projection(extraction):
    """Build scientific bindings from frozen arm operands, without source IO.

    Global literals describe the selected scope. They do not relabel measured
    arms. Equality here follows the reader's existing operand identities; it
    introduces no additional synonym or source-interpretation requirement.
    """
    evidence = extraction['native_evidence']
    core = extraction['recipe']['inputs']['arms']
    records, arm_bindings, condition_refs = ({}, {}, {})

    def remember(kind, record):
        reference = identity(kind, {'origin': 'tool', 'record': record})
        records[reference] = (kind, record)
        return reference

    def entry(witness):
        return None if witness is None else {'value': witness['quote'], 'witness': witness}

    def literal_binding(field, witness, *, unit=False):
        if witness is None:
            return None
        kind = 'reference' if field in ('subject', 'partner') else 'term'
        record = _binding_record(field, kind, entry(witness))
        if unit:
            record['term_type'] = 'unit'
        return remember(kind, record)
    for role in _ROLES:
        arm = evidence[role]
        arm_bindings[role] = {field + '_ref': literal_binding(field, arm[field]) if arm is not None else None for field in _NATIVE_IDENTITY_FIELDS}
        if arm is None or arm['conditions']['coverage'] == 'unreported':
            condition_refs[role + '_condition_ref'] = None
            continue
        factors = []
        for selected, normalized in zip(arm['conditions']['factors'], core[role]['conditions']['factors']):
            name, level = (selected['factor'], selected['level'])
            factor_ref = remember('term', _factor_record(extraction['arguments']['data_source_ref'], name))
            attributes, source_ref = ([], extraction['arguments']['data_source_ref'])
            if level is not None:
                if level['kind'] == 'literal':
                    witness = level['witness']
                    value_ref = literal_binding('condition_value_' + name, witness)
                    value = {'type': 'term_ref', 'ref': value_ref}
                else:
                    witness = level['selector']['selector']['witness']
                    unit_ref = literal_binding('condition_unit_' + name, level['unit_witness'], unit=True)
                    value = {'type': 'number', 'value': normalized['level'], 'unit_ref': unit_ref}
                source_ref = witness['source_ref']
                attributes.append({'name': 'assay_outcome', 'value': value})
            factors.append(remember('context', {'context_type': 'assay_condition', 'name': 'condition factor ' + name + ' level', 'source_ref': source_ref, 'attributes': attributes, 'related_refs': [factor_ref]}))
        condition_refs[role + '_condition_ref'] = remember('context', {'context_type': 'assay_condition', 'name': role + ' arm selected conditions (' + arm['conditions']['coverage'] + ')', 'source_ref': extraction['arguments']['data_source_ref'], 'attributes': [], 'related_refs': list(dict.fromkeys([*factors, *(ref for ref in arm_bindings[role].values() if ref)]))})

    def common(roles):
        result = {}
        for field in _NATIVE_IDENTITY_FIELDS:
            keys = [core[role][field + '_ref'] if core[role] is not None else None for role in roles]
            result[field + '_ref'] = arm_bindings[roles[0]][field + '_ref'] if keys and keys[0] is not None and all((key == keys[0] for key in keys)) else None
        return result
    components = {name: common(roles) for name, roles in _COMPONENT_ROLES.items()}
    present = tuple((role for role in _ROLES if core[role] is not None))
    shared = common(present)
    interpretation = deepcopy(extraction['literals'])
    for field in _NATIVE_IDENTITY_FIELDS:
        reference = shared[field + '_ref']
        selected = next((entry(evidence[role][field]) for role in present if arm_bindings[role][field + '_ref'] == reference), None) if reference else None
        interpretation[field] = selected
        if selected != extraction['literals'][field] and extraction['literals'][field] is not None:
            interpretation['selected_scope_' + field] = deepcopy(extraction['literals'][field])
        if reference is None:
            for role in _ROLES:
                interpretation[role + '_' + field] = entry(evidence[role][field]) if evidence[role] else None
    for role in _ROLES:
        name, arm = (role + '_condition', evidence[role])
        witnesses, descriptions = ([], [])
        if arm is not None and arm['conditions']['coverage'] != 'unreported':
            for selected, normalized in zip(arm['conditions']['factors'], core[role]['conditions']['factors']):
                level = selected['level']
                if level is None:
                    description = 'unknown'
                elif level['kind'] == 'literal':
                    witnesses.append(level['witness'])
                    description = level['witness']['quote']
                else:
                    witnesses.append(level['selector']['selector']['witness'])
                    if level['unit_witness'] is not None:
                        witnesses.append(level['unit_witness'])
                    description = str(normalized['level']) + ' ' + normalized['unit']
                descriptions.append(selected['factor'] + '=' + description)
            interpretation[name] = {'value': '; '.join(descriptions), 'witnesses': witnesses}
        else:
            interpretation[name] = None
        if extraction['literals'][name] is not None:
            interpretation['selected_scope_' + name] = deepcopy(extraction['literals'][name])
    projection = {'version': _NATIVE_BINDING_VERSION, 'arm_bindings': arm_bindings, 'component_bindings': components, 'condition_refs': condition_refs}
    return (projection, records, {**shared, **condition_refs}, interpretation)

def partner_cells_schema():
    """Closed numerical and source-meaning rows, without raw numerical recipes."""
    source = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}
    properties = {**{field: dict(source) for field in ('sheet_ref', 'evidence_source_ref', 'data_source_ref')}, **{field: {'type': ['string', 'null'], 'format': 'reference', 'x-reference-namespace': kind} for field, (_, kind) in BINDINGS.items()}, 'component': {'type': 'string', 'enum': list(COMPONENTS)}, **deepcopy(_cell_schema()['properties']), 'formula_code': {'type': 'string', 'enum': list(FORMULA_CODES.values())}, 'source_kind': {'type': 'string', 'enum': list(SOURCE_KINDS)}, 'comparison_checks': _checks_schema(), 'arm_metadata': _arm_metadata_schema(), **{field: {'type': 'string', 'enum': [value]} for field, value in _FIXED_METADATA.items()}}
    return {'type': 'array', 'items': obj(properties), 'x-source': 'literature_partner_cells'}
