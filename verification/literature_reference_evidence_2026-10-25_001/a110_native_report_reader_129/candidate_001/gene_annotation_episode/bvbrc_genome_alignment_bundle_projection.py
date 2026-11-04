"""Saved-only selected GenomeAlignment facts and exact request completion.

Only stored rows/cells are projected. No parser, source binder, scientific
calculator or resolver is imported here. D's structural validators check saved
relationships; acquisition custody remains the existing host's responsibility.
"""
from copy import deepcopy
import hashlib

from . import bvbrc_genome_alignment_bundle_contracts as c
from .bvbrc_appservice_contracts import validate_contract
from .bvbrc_alignment_values import diagnostic, requirement
from .bvbrc_genome_alignment_sheet import validate_genome_alignment_sheet


def _union_requirements(*groups):
    result, seen = [], {}
    for group in groups:
        for row in group:
            validate_contract('AcquisitionRequirement', row)
            rid = row['requirement_id']
            c._require(rid not in seen or c._same(row, seen[rid]), 'saved_reports_conflict')
            if rid not in seen:
                result.append(deepcopy(row)); seen[rid] = row
    return result


def _union_diagnostics(*groups):
    result = []
    for group in groups:
        for row in group:
            validate_contract('Diagnostic', row)
            if not any(c._same(row, old) for old in result):
                result.append(deepcopy(row))
    return result


def _prepare(sheet, components, missing_requirements, diagnostics, requested_form, parameters):
    c._require(type(missing_requirements) is tuple and type(diagnostics) is tuple, 'argument_invalid')
    parameters = c.validate_parameters(parameters)
    form = c.validate_requested_form(requested_form)
    c._validate_selections(parameters, form)
    requirements = _union_requirements(missing_requirements)
    reports = _union_diagnostics(diagnostics)
    c._require((sheet is None) == (components is None), 'saved_identity_conflict')
    if sheet is None:
        return parameters, form, None, requirements, reports
    saved = validate_genome_alignment_sheet(sheet)
    c._require(c._same(saved['components'], components), 'saved_identity_conflict')
    c._require(saved['analysis_id'] == parameters['analysis_id'] and
        c._same(saved['data']['document_slots'], parameters['document_slots']) and
        c._same(components['calculation_plan'], parameters['calculation_plan']), 'saved_identity_conflict')
    c._validate_selections(parameters, form, data=saved['data'])
    # Identical reused reports deduplicate; conflicting reused IDs already
    # raised above. D reports retain their immutable order in the union.
    c._require(c._same(requirements[:len(saved['requirements'])], saved['requirements']) and
               c._same(reports[:len(saved['diagnostics'])], saved['diagnostics']), 'saved_reports_conflict')
    return parameters, form, saved, requirements, reports


def _one(rows, **keys):
    matches = [r for r in rows if all(c._same(r[k], value) for k, value in keys.items())]
    c._require(len(matches) <= 1, 'saved_identity_conflict')
    return matches[0] if matches else None


def _metric_row(value, target):
    family = target['family']
    if family in ('v4_member', 'v4_pair'):
        rows = value['member_segments' if family == 'v4_member' else 'pair_segments']
        rows = [r for r in rows if all(r['segment'][k] == target[k] for k in ('interval_index', 'segment_index'))]
        row = _one(rows, **{k: target[k] for k in ('member',) if k in target}) if family == 'v4_member' else _one(rows, pair=target['pair'])
        return None if row is None else row if family == 'v4_member' else row['counts']
    if family in ('v4_coverage', 'backbone_coverage'):
        return _one(value['coverage'], member=target['member'])
    if family in ('backbone_row', 'backbone_span', 'bbcols_row'):
        row = _one(value['rows'], row_index=target['row_index'])
        return None if row is None else _one(row['member_spans'], member=target['member']) if family == 'backbone_span' else row
    if family == 'bbcols_interval':
        return _one(value['intervals'], native_interval_index_0based=target['native_interval_index_0based'])
    if family.startswith('xmfa_') and family not in ('xmfa_coverage', 'xmfa_original_coverage'):
        block = _one(value['blocks'], block_index=target['block_index'])
        if block is None or family == 'xmfa_block':
            return block
        if family == 'xmfa_pair':
            return _one(block['pairs'], member_a=target['member_a'], member_b=target['member_b'])
        site = _one(block['sites'], column_0based=target['column_0based'])
        return None if site is None else _one(site['symbol_counts'], symbol=target['symbol']) if family == 'xmfa_symbol' else site
    member = _one(value['members'], member_number=target['member_number'])
    return None if member is None else _one(member['original_coverage'], original_member=target['original_member']) if family == 'xmfa_original_coverage' else member


def _measure(row, ref):
    value = {k: deepcopy(row[k]) for k in ('value', 'state', 'unit', 'origin', 'numerator', 'denominator')}
    value.update(population_ref=ref('population', row['population_id']), method_ref=ref('method', row['method_id']),
                 uncertainty=None, requirement_refs=[ref('requirement', rid) for rid in row['requirement_ids']])
    if row['uncertainty'] is not None:
        value['uncertainty'] = {k: deepcopy(row['uncertainty'][k]) for k in ('kind', 'lower', 'upper', 'value')}
        value['uncertainty']['method_ref'] = ref('method', row['uncertainty']['method_id'])
    return value


def _selected_value(selector, outcome, ref):
    """Return (closed fact value, exact stored target, completion dependency)."""
    value = outcome['measurement']['value']; kind = selector['kind']
    if kind == 'measurement':
        row = _metric_row(value, selector['metric'])
        cell = None if row is None else row[selector['metric']['field']]
        return (None, None, False) if cell is None else (_measure(cell, ref), cell, cell['state'] == 'available')
    if kind == 'v4_segment':
        row = _metric_row(value, dict(family='v4_member', **{k: selector[k] for k in ('interval_index', 'segment_index', 'member')}))
        if row is None:
            return None, None, False
        result = {k: deepcopy(selector[k]) for k in ('interval_index', 'segment_index', 'member')}
        result.update({k: deepcopy(row[k]) for k in ('state', 'strand', 'native_interval_0based_half_open', 'symbols_origin', 'source_comparison')})
        number = row['native_start']
        result.update(native_start=None if number is None else number['value'], native_start_state=None if number is None else number['state'],
                      native_start_token_kind=None if number is None else number['token_kind'])
        return result, row, row['state'] in ('present', 'absent_zero')
    if kind == 'backbone_span':
        row = _one(value['rows'], row_index=selector['row_index'])
        span = None if row is None else _one(row['member_spans'], member=selector['member'])
        if span is None:
            return None, None, False
        return ({'row_index': row['row_index'], 'selected_by_multiplicity': row['selected_by_multiplicity'],
            **{k: deepcopy(span[k]) for k in ('member', 'state', 'interval_0based_half_open', 'strand')}},
            span, span['state'] in ('present', 'absent_zero'))
    if kind == 'bbcols_interval':
        row = _one(value['intervals'], native_interval_index_0based=selector['native_interval_index_0based'])
        return (None, None, False) if row is None else ({k: deepcopy(row[k]) for k in (
            'native_interval_index_0based', 'contributing_row_indices', 'known_union_intervals', 'population_state')},
            row, row['union_columns']['state'] == 'available')
    if kind == 'coverage_intervals':
        xmfa = outcome['kind'] == 'xmfa_coverage'; part = selector['part']
        row = (_one(value['members'], member_number=selector['member']['index']) if xmfa else
               _one(value['coverage'], member=selector['member']))
        if row is None:
            return None, None, False
        intervals = row['known_union_intervals' if part == 'union' else 'complement_intervals']
        cell = row['known_union_bases' if part == 'union' else 'complement_bases']
        result = {'member': deepcopy(selector['member']), 'part': part, 'intervals': deepcopy(intervals),
            'population_state': None if xmfa else row['population_state'],
            'membership_completeness': row['membership_completeness'] if xmfa else None,
            'basis': value['parameters']['basis'] if xmfa else None,
            'denominator_kind': 'validated_xmfa_source_length' if xmfa else row['denominator_kind']}
        return result, cell, cell['state'] == 'available' and intervals is not None
    if kind == 'xmfa_inverse_coordinates':
        row = _one(value['queries'], **selector['query'])
        return (None, None, False) if row is None else ({k: deepcopy(row[k]) for k in (
            'member_number', 'position_0based', 'state', 'matches', 'search_completeness')}, row,
            row['search_completeness'] == 'complete' and row['state'] != 'unknown')
    row = _one(value['cells'], cell=selector['cell'])
    if row is None:
        return None, None, False
    result = {k: deepcopy(row[k]) for k in ('cell', 'member_number')}
    if kind == 'xmfa_native_coordinate':
        result.update({k: deepcopy(row[k]) for k in ('aligned_symbol', 'state', 'native_position_1based',
            'native_position_0based', 'native_strand', 'forward_symbol')})
        usable = row['state'] in ('residue', 'gap', 'absent_zero')
    elif kind == 'xmfa_source_coordinate':
        source = row['source_coordinate']
        result.update(source_state=row['source_state'], source_coordinate=None)
        if source is not None:
            result['source_coordinate'] = {k: source[k] for k in ('entry_1based', 'position_0based', 'strand')}
            result['source_coordinate'].update(file_ref=ref('file', source['file_id']),
                record_ref=ref('record', c._canonical([source['file_id'], source['record_id']])))
        usable = row['source_state'] == 'resolved' or row['source_state'] == 'not_applicable' and row['state'] in ('gap', 'absent_zero')
    else:
        result.update(state=row['state'], original_coordinates=[{**{k: original[k] for k in ('position_0based', 'original_length', 'strand')},
            'member_ref': ref('member', c._canonical(original['original_member'])),
            'transformation_ref': ref('transformation', original['transformation_id'])} for original in row['original_coordinates']])
        usable = row['state'] == 'residue' and bool(row['original_coordinates']) or row['state'] in ('gap', 'absent_zero') and not row['original_coordinates']
    return result, row, usable


def _association(outcome, data):
    if outcome['document_id'] is None or data['associations'] is None:
        return None
    slot = _one(data['document_slots'], slot_id=outcome['document_slot_id'])
    resolution = _one(data['slot_resolutions'], slot_id=outcome['document_slot_id'])
    return _one([r for r in data['associations']['artifacts'] if r['document_id'] == outcome['document_id']
        and r['role'] == slot['role'] and r['observed_format'] == slot['reader']['format']
        and all(r['artifact'][k] == resolution['artifact'][k] for k in ('raw_artifact_ref', 'source_ref', 'sha256'))])


def _projection_cause(parameters, field, selector, reason):
    rid = selector['request_id']; request = _one(parameters['calculation_plan']['requests'], request_id=rid)
    slot = _one(parameters['document_slots'], slot_id=request['document_slot_id'])
    code = c.PREFIX + reason
    payload = (parameters['analysis_id'], field, rid, c._canonical(selector), code)
    identity = 'ga_projection_req:' + hashlib.sha256(c._canonical(payload).encode()).hexdigest()
    refs = [] if slot['source_ref'] is None else [slot['source_ref']]
    return (requirement(identity, kind='parser_binding', role=slot['role'], source_refs=refs, reason_code=code),
        diagnostic(code, phase='publication', path='/facts/' + field.replace('~', '~0').replace('/', '~1'), evidence_refs=refs))


def _project(sheet, components, missing_requirements, diagnostics, requested_form, parameters):
    parameters, form, saved, supplied_requirements, supplied_diagnostics = _prepare(
        sheet, components, missing_requirements, diagnostics, requested_form, parameters)
    if saved is None:
        return {'facts': {}, 'missing_requirements': supplied_requirements, 'diagnostics': supplied_diagnostics}, 'invalid'
    aid = parameters['analysis_id']
    ref = lambda kind, identity: c.encode_reference(kind, aid, identity)
    outcomes = {o['request_id']: o for o in saved['components']['outcomes']}
    values, usable, extra_requirements, extra_diagnostics, extra_by_request = {}, [], [], [], {}
    for field, schema in form['properties'].items():
        selector = schema['x-genome-alignment-fact']; kind = selector['kind']
        if kind in ('qualifications', 'missing_requirements'):
            continue
        outcome = outcomes[selector['request_id']]
        requirement_ids = [r['requirement_id'] for r in outcome['requirements']]
        document_ref = None if outcome['document_id'] is None else ref('document', outcome['document_id'])
        if kind == 'request_status':
            values[field] = dict(request_ref=ref('request', outcome['request_id']), document_ref=document_ref,
                kind=outcome['kind'], state=outcome['state'], measurement_status=None if outcome['measurement'] is None else outcome['measurement']['value']['status'],
                requirement_refs=[ref('requirement', r) for r in requirement_ids])
            usable.append(True)
            continue
        result, target, available = (None, None, False) if outcome['measurement'] is None else _selected_value(selector, outcome, ref)
        state = ('incompatible' if outcome['state'] == 'incompatible' else 'missing') if target is None else 'resolved'
        # Accepted012: a present malformed native symbol remains in D, but
        # cannot be represented by E's closed DNA-symbol coordinate fact.
        incompatible_symbol = (kind == 'xmfa_native_coordinate' and target is not None and
                               not c._Validator(c.SYMBOL).is_valid(target['aligned_symbol']))
        if incompatible_symbol:
            result, state, available = None, 'incompatible', False
        if outcome['measurement'] is not None and (target is None or incompatible_symbol):
            reason = 'projection_target_incompatible' if incompatible_symbol else 'projection_target_missing'
            req, diag = _projection_cause(parameters, field, selector, reason)
            extra_requirements.append(req); extra_diagnostics.append(diag)
            extra_by_request.setdefault(outcome['request_id'], []).append((req, diag))
            requirement_ids.append(req['requirement_id'])
        if target is not None:
            requirement_ids.extend(target.get('requirement_ids', []))
        association = _association(outcome, saved['data'])
        if association is not None:
            requirement_ids.extend(association['requirement_ids'])
        values[field] = dict(request_ref=ref('request', outcome['request_id']), document_ref=document_ref,
            state=state, value=result, requirement_refs=[ref('requirement', r) for r in dict.fromkeys(requirement_ids)])
        usable.append(target is not None and available and association is not None and association['state'] == 'bound')
    requirements = _union_requirements(saved['requirements'], extra_requirements)
    reports = _union_diagnostics(saved['diagnostics'], extra_diagnostics)
    # Initial projection takes D reports. Replay may supply the exact augmented
    # reports, but cannot smuggle in a different selector's orphan causes.
    c._require(c._same(_union_requirements(supplied_requirements, requirements), requirements) and
        c._same(_union_diagnostics(supplied_diagnostics, reports), reports), 'saved_reports_conflict')
    ids = {r['requirement_id'] for r in requirements}
    for field, schema in form['properties'].items():
        selector = schema['x-genome-alignment-fact']; kind = selector['kind']
        if kind == 'missing_requirements':
            rows = requirements if selector['scope'] == 'all' else _union_requirements(
                outcomes[selector['request_id']]['requirements'], [r for r, _ in extra_by_request.get(selector['request_id'], [])])
            values[field] = [dict(requirement_ref=ref('requirement', r['requirement_id']), kind=r['kind'],
                role_ref=None if r['role'] is None else ref('role', r['role']), source_refs=deepcopy(r['source_refs']),
                reason_ref=ref('reason', r['reason_code'])) for r in rows]
        elif kind == 'qualifications':
            rows = reports if selector['scope'] == 'all' else _union_diagnostics(
                outcomes[selector['request_id']]['diagnostics'], [d for _, d in extra_by_request.get(selector['request_id'], [])])
            values[field] = [dict(qualification_ref=ref('qualification', str(reports.index(d))), code_ref=ref('reason', d['code']),
                phase=d['phase'], severity=d['severity']) for d in rows]
        else:
            for reference in values[field]['requirement_refs']:
                c._require(c.decode_reference(reference)[2] in ids, 'saved_reports_conflict')
    facts = {field: values[field] for field in form['properties']}
    c._validate(form, facts, 'saved_facts_conflict')
    return {'facts': deepcopy(facts), 'missing_requirements': requirements, 'diagnostics': reports}, 'ok' if all(usable) else 'partial'


def project_genome_alignment_facts(*, sheet: dict | None, components: dict | None,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict) -> dict:
    return _project(sheet, components, missing_requirements, diagnostics, requested_form, parameters)[0]


def validate_projected_facts(facts: dict, *, sheet: dict | None, components: dict | None,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict) -> dict:
    result, _ = _project(sheet, components, missing_requirements, diagnostics, requested_form, parameters)
    c._require(c._same(facts, result['facts']), 'saved_facts_conflict')
    c._require(c._same(list(missing_requirements), result['missing_requirements']) and
        c._same(list(diagnostics), result['diagnostics']), 'saved_reports_conflict')
    return deepcopy(facts)


def requested_projection_status(facts: dict, *, sheet: dict | None, components: dict | None,
    missing_requirements: tuple[dict, ...], diagnostics: tuple[dict, ...], requested_form: dict, parameters: dict) -> str:
    result, status = _project(sheet, components, missing_requirements, diagnostics, requested_form, parameters)
    c._require(c._same(facts, result['facts']), 'saved_facts_conflict')
    c._require(c._same(list(missing_requirements), result['missing_requirements']) and
        c._same(list(diagnostics), result['diagnostics']), 'saved_reports_conflict')
    return status


__all__ = ['project_genome_alignment_facts', 'validate_projected_facts', 'requested_projection_status']
