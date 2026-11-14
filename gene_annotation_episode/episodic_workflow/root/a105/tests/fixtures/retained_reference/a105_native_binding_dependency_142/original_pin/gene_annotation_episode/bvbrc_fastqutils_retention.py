"""Pure retention arithmetic over explicitly selected saved-sheet counts."""
from __future__ import annotations

from copy import deepcopy
import re

from .bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, canonical_json, json_sha256, validate_contract, validate_sheet,
)
from .bvbrc_fastqutils_identity import component_ref
from .bvbrc_fastqutils_metric_specs import component_spec, COMPONENT_ORDER

_COUNT_UNITS = ('reads', 'bases', 'pairs', 'alignment_records')


def _matches(selector, population):
    if selector['selection'] == 'record':
        return selector['record_ref'] == population['id']
    return (selector['document_id'] in population['document_ids'] and
            selector['population_key'] == population['population_key'] and
            selector['population_ordinal'] == population['population_ordinal'])


def _comparison_inputs(sheet, job, parameters_sha256, method):
    """Validate structure, then resolve ONLY the job's actual permitted refs."""
    validate_sheet(sheet)
    job = validate_contract('CalculationBinding', job)
    if job['method'] != method or type(parameters_sha256) is not str or not re.fullmatch('[0-9a-f]{64}', parameters_sha256):
        raise FastqUtilsContractError('shape_invalid')
    populations = {p['id']: p for p in sheet['populations']}
    cells = {c['id']: c for c in sheet['measurements']}
    selected_populations = [populations.get(ref) for ref in job['population_refs']]
    selected_cells = [cells.get(ref) for ref in job['operand_measurement_refs']]
    codes = list(job['diagnostic_codes'])
    state = 'available'
    if job['state'] != 'ready':
        state = 'incompatible' if job['state'] == 'incompatible' else 'missing'
    if len(selected_populations) != 2 or len(selected_cells) != 2 or any(row is None for row in selected_populations + selected_cells):
        return job, selected_populations, selected_cells, 'missing' if state != 'incompatible' else state, codes + ['missing_denominator']
    if any(cell['population_ref'] != population['id'] for cell, population in zip(selected_cells, selected_populations)):
        return job, selected_populations, selected_cells, 'incompatible', codes + ['incompatible_population']
    for cell, population in zip(selected_cells, selected_populations):
        if cell['unit'] not in _COUNT_UNITS or cell['meaning'] != 'observed_count' or cell['precision'] != 'exact_for_retained_population' or cell['axis']['kind'] not in ('none', 'native_label'):
            return job, selected_populations, selected_cells, 'incompatible', codes + ['incompatible_population']
        if population['scope'] == 'partial' or cell['state'] in ('partial', 'truncated'):
            state = 'truncated'; codes.append('partial_transfer')
        elif population['scope'] == 'unknown':
            if state == 'available': state = 'missing'
            codes.append('missing_denominator')
        elif cell['state'] != 'available':
            if state == 'available': state = cell['state']
            codes.extend(cell['diagnostic_codes'] or ['missing_requested_value'])
    if selected_cells[0]['unit'] != selected_cells[1]['unit']:
        state = 'incompatible'; codes.append('incompatible_population')
    basis = job['lineage_basis']
    if basis is None or basis['basis'] == 'unknown':
        if state == 'available': state = 'missing'
        codes.append('lineage_asserted_only')
    elif basis['basis'] == 'explicit_source_bound_declaration':
        metadata = next((m for m in sheet['supplied_metadata'] if m['metadata_id'] == basis['metadata_id']), None)
        declaration = basis['declaration']
        valid = (metadata is not None and metadata['kind'] == 'lineage_declaration' and declaration is not None and
                 canonical_json(metadata['value']) == canonical_json(declaration) and
                 canonical_json(metadata['evidence']) == canonical_json(basis['evidence']) and
                 basis['native_lineage_ref'] is None and
                 _matches(declaration['before'], selected_populations[0]) and
                 _matches(declaration['after'], selected_populations[1]))
        relations = ('same_population',) if method == 'report_consistency_v1' else ('successor_population', 'subset_population')
        conflicting = [m for m in sheet['supplied_metadata']
            if m['kind'] == 'lineage_declaration' and
            _matches(m['value']['before'], selected_populations[0]) and
            _matches(m['value']['after'], selected_populations[1]) and
            (declaration is None or m['value']['relation'] != declaration['relation'])]
        if not valid or declaration['relation'] not in relations or conflicting:
            state = 'incompatible'; codes.append('incompatible_population')
        else:
            codes.append('explicit_lineage_assumption')
    else:
        edge = next((e for e in sheet['native_lineage'] if e['id'] == basis['native_lineage_ref']), None)
        expected = 'native_report_before_after' if basis['basis'] == 'native_report' else 'observed_record_correspondence'
        valid = (edge is not None and edge['kind'] == expected and
                 edge['before_population_ref'] == selected_populations[0]['id'] and
                 edge['after_population_ref'] == selected_populations[1]['id'] and
                 all(basis[k] is None for k in ('metadata_id', 'evidence', 'declaration')))
        if job['lineage_ref'] is not None and job['lineage_ref'] != basis['native_lineage_ref']:
            valid = False
        if method == 'report_consistency_v1' and basis['basis'] == 'native_report':
            valid = False  # A before/after relation does not say these are the same population.
        if not valid:
            state = 'incompatible'; codes.append('incompatible_population')
        elif basis['basis'] == 'native_report':
            codes.append('native_report_local_lineage')
    return job, selected_populations, selected_cells, state, list(dict.fromkeys(codes))


def _component(sheet, job, parameter_hash, metric, *, state, value, unit, cells, populations, numerator, denominator, codes):
    spec = component_spec(metric)
    comparison = job['comparison_kind']
    row = {'id': component_ref(sheet['analysis_id'], json_sha256(sheet), parameter_hash, job['calculation_id'], metric, None),
        'metric': metric, 'state': state, 'value': value, 'unit': unit, 'method': job['method'],
        'population_refs': [p['id'] for p in populations if p is not None],
        'operand_measurement_refs': [c['id'] for c in cells if c is not None],
        'numerator': numerator, 'denominator': denominator, 'threshold': None,
        'meaning': spec.get('meaning_by_comparison_kind', {}).get(comparison, spec['meaning']),
        'uncertainty': spec.get('uncertainty_by_comparison_kind', {}).get(comparison, spec['uncertainty']),
        'parameter_sha256': parameter_hash, 'diagnostic_codes': list(dict.fromkeys(codes)),
        'calculation_id': job['calculation_id'], 'encoding_basis': None, 'lineage_basis': deepcopy(job['lineage_basis'])}
    return validate_contract('Component', row)


def calculate_retention(sheet: dict, *, job: dict, parameters_sha256: str) -> list[dict]:
    job, populations, cells, state, codes = _comparison_inputs(sheet, job, parameters_sha256, 'retention_v1')
    kind = job['comparison_kind']
    fractions = {'read_retention': 'read_retention_fraction', 'base_retention': 'base_retention_fraction',
                 'pair_retention': 'pair_retention_fraction', 'native_report_retention': 'native_report_retention_fraction'}
    if kind not in fractions:
        raise FastqUtilsContractError('shape_invalid', '/comparison_kind')
    count_unit = next((c['unit'] for c in cells if c is not None and c['unit'] in _COUNT_UNITS),
                      {'base_retention': 'bases', 'pair_retention': 'pairs'}.get(kind, 'reads'))
    required_unit = {'read_retention': 'reads', 'base_retention': 'bases', 'pair_retention': 'pairs'}.get(kind)
    if required_unit is not None and count_unit != required_unit:
        state = 'incompatible'; codes.append('incompatible_population')
    before = cells[0]['value'] if len(cells) > 0 and cells[0] is not None else None
    after = cells[1]['value'] if len(cells) > 1 and cells[1] is not None else None
    if state == 'available' and (before is None or after is None):
        state = 'missing'; codes.append('missing_denominator')
    if state == 'available' and after > before:
        state = 'incompatible'; codes.append('count_inconsistent')
    removed = before - after if before is not None and after is not None else None
    output = []
    for metric in COMPONENT_ORDER:
        if metric not in (fractions[kind], 'removed_count', 'removed_fraction'): continue
        local_state = state; local_codes = list(codes); value = None
        numerator = after if metric == fractions[kind] else removed
        denominator = None if metric == 'removed_count' else before
        if state == 'available':
            if metric == 'removed_count': value = removed
            elif before == 0:
                local_state = 'undefined'; local_codes.append('zero_denominator')
            else: value = numerator / before
        output.append(_component(sheet, job, parameters_sha256, metric, state=local_state, value=value,
            unit=count_unit if metric == 'removed_count' else 'fraction', cells=cells, populations=populations,
            numerator=numerator, denominator=denominator, codes=local_codes))
    return output
