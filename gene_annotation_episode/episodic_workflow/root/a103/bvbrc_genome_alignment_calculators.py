"""Explicit native dispatch and acquisition-free saved-sheet recalculation.

Each original request receives one outcome. Only the exact D002 native target
errors become local incompatible outcomes; every other exception propagates.
"""
from . import bvbrc_genome_alignment_calculation_contracts as c
from .bvbrc_genome_alignment_sheet import (validate_genome_alignment_data,
    validate_genome_alignment_sheet, build_genome_alignment_sheet)
from .mauve_v4_calculators import calculate_mauve_v4_segments
from .mauve_backbone_calculators import calculate_mauve_backbone_components, calculate_mauve_bbcols_components
from .xmfa_calculators import xmfa_alignment_components, xmfa_interval_coverage
from .xmfa_coordinates import xmfa_column_coordinates, xmfa_source_positions
from .xmfa_sources import bind_xmfa_sources


def _dispatch(document, call, data, documents, binding):
    kind = call['kind']
    if kind == 'mauve_v4_segments':
        return calculate_mauve_v4_segments(document, selection=call['selection'],
            inputs=data['inputs'] if call['inputs_used'] else None)
    if kind == 'mauve_backbone':
        return calculate_mauve_backbone_components(document, selection=call['selection'],
            inputs=data['inputs'] if call['inputs_used'] else None)
    if kind == 'mauve_bbcols':
        return calculate_mauve_bbcols_components(document, selection=call['selection'],
            xmfa_document=documents.get(call['xmfa_document_id']),
            associations=data['associations'] if call['associations_used'] else None)
    if kind == 'xmfa_alignment':
        return xmfa_alignment_components(document, selection=call['selection'],
            selected_pairs=tuple(tuple(p) for p in call['selected_pairs']), case_policy=call['case_policy'])
    if kind == 'xmfa_coverage':
        return xmfa_interval_coverage(document, selection=call['selection'], bindings=binding, basis=call['basis'])
    if kind == 'xmfa_coordinates':
        return xmfa_column_coordinates(document, cells=tuple(call['cells']), bindings=binding)
    return xmfa_source_positions(document, queries=tuple(call['queries']), bindings=binding)


def calculate_genome_alignment_components(data: dict, *, calculation_plan: dict) -> dict:
    data = validate_genome_alignment_data(data)
    plan = c.validate_genome_alignment_calculation_plan(calculation_plan, document_slots=tuple(data['document_slots']))
    _, resolutions, documents = c._indexes(data)
    result = {'schema_version': 'bvbrc_genome_alignment_components_v2', 'analysis_id': data['analysis_id'],
        'calculation_plan': plan, 'source_bindings': [], 'outcomes': [], 'requirements': [], 'diagnostics': []}
    bindings = {}
    for index, request in enumerate(plan['requests']):
        resolution = resolutions[request['document_slot_id']]
        call = c._call(data, request, resolutions)
        outcome = {'request_id': request['request_id'], 'request_index': index, 'kind': request['kind'],
            'document_slot_id': request['document_slot_id'], 'document_id': None,
            'state': 'incompatible' if resolution['state'] == 'incompatible' else 'missing',
            'call': call, 'measurement': None, 'requirements': [], 'diagnostics': []}
        groups = [c._request_reports(data, request, index, call)]
        if call is not None:
            did = resolution['document_id']; document = documents[did]
            outcome['document_id'] = did
            binding_id = call.get('source_binding_document_id')
            if binding_id is not None and binding_id not in bindings:
                # This is a new calculation from saved source data, not reuse
                # of an old check or an acquisition of missing source bytes.
                binding = bind_xmfa_sources(document, inputs=data['inputs']['xmfa_source_inputs'],
                    source_comparison='case_insensitive_iupac_exact')
                bindings[binding_id] = binding
                result['source_bindings'].append({'document_id': binding_id,
                    'source_comparison': 'case_insensitive_iupac_exact', 'bindings': binding})
            binding = bindings.get(binding_id)
            if binding is not None:
                groups.append(binding)
            try:
                measurement = _dispatch(document, call, data, documents, binding)
            except ValueError as error:
                code = str(error)
                if code not in c.TARGET_ERRORS[request['kind']]:
                    raise
                outcome['state'] = 'incompatible'
                reason = 'selection_target_missing' if code in c.MISSING_TARGET_ERRORS else 'selection_target_incompatible'
                groups.append(c._cause(data, request, index, reason, affected=code))
            else:
                outcome['state'] = 'calculated'
                outcome['measurement'] = {'kind': request['kind'], 'value': measurement}
                groups.append(measurement)
        for field in ('requirements', 'diagnostics'):
            outcome[field] = c._union(groups, field)
        result['outcomes'].append(outcome)
    groups = [data, *[s['bindings'] for s in result['source_bindings']], *result['outcomes']]
    for field in ('requirements', 'diagnostics'):
        result[field] = c._union(groups, field)
    return c.validate_genome_alignment_components(result, data=data)


def recalculate_genome_alignment_sheet(sheet: dict, *, calculation_plan: dict) -> dict:
    previous = validate_genome_alignment_sheet(sheet)
    components = calculate_genome_alignment_components(previous['data'], calculation_plan=calculation_plan)
    return build_genome_alignment_sheet(data=previous['data'], components=components)


__all__ = ['calculate_genome_alignment_components', 'recalculate_genome_alignment_sheet']
