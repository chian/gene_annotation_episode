"""Select closed numerical chromatin returns without changing their population."""
from __future__ import annotations

from copy import deepcopy

from .chromatin_interaction_contracts import (
    ChromatinComponents, ContactSheet, RequestedProjection, ResultSelector,
    chromatin_record_digest, validate_chromatin_record,
)
from .chromatin_interaction_calculations import (
    _failure, _measurement, _pair_population_known, _require, _source_keys,
    _table_identities, _unique_failures,
)


_KINDS = {
    'contact_pairs': ('contact', 'pairs', 'pair_key', 'pair_keys'),
    'distance_expectations': ('contact', 'distance_expectations', 'separation_bins', 'separations'),
    'insulation_windows': ('insulation', 'windows', 'boundary_bin_id', 'boundary_bin_ids'),
    'domains': ('insulation', 'domains', 'domain_key', 'domain_keys'),
}
_RAW_COUNTS = {
    'directed_cell_count': 'directed_cells',
    'unique_unordered_cell_count': 'unique_unordered_cells',
    'stored_row_count': 'stored_rows',
    'explicit_zero_row_count': 'explicit_zero_rows',
    'implicit_zero_directed_cell_count': 'implicit_zero_directed_cells',
    'native_nonfinite_directed_cell_count': 'native_nonfinite_directed_cells',
    'unavailable_directed_cell_count': 'unavailable_directed_cells',
}


def _same_measurement_population(measurements, key):
    _require(all(m['population_key'] == key for m in measurements.values()), 'measurement_population_join')


def _validate_joins(sheet, components, selector):
    digest, identities = chromatin_record_digest(sheet), _table_identities(sheet)
    _require(components['source_sheet_sha256'] == digest, 'component_sheet_digest')
    _require(components['table_identities'] == identities, 'component_table_identity_order')
    _require(components['parameters'] == selector['parameters'], 'selector_parameters')
    populations = {p['population_key']: p for p in sheet['populations']}
    keys = list(populations)
    _require(set(selector['population_keys']) <= set(keys), 'selector_population_join')
    for name, mode in (('contact', 'cis_anchor_contact_enrichment'),
                       ('insulation', 'cross_window_insulation_heuristic')):
        inner = components[name]
        _require((inner is not None) == (mode in sheet['request']['analysis_modes']), 'component_mode_join')
        _require((inner is not None) == (components['parameters'][name] is not None), 'parameter_mode_join')
        if inner is None:
            continue
        _require(inner['source_sheet_sha256'] == digest and inner['table_identities'] == identities,
                 'inner_component_source_join')
        _require(inner['parameters'] == components['parameters'][name]
                 and inner['normalization'] == components['parameters']['normalization'], 'inner_parameter_join')
        _require([p['population_key'] for p in inner['populations']] == keys, 'component_population_order')
        for p in inner['populations']:
            key, source = p['population_key'], populations[p['population_key']]
            _require(p['source_table_keys'] == _source_keys(sheet, key), 'population_table_order')
            _same_measurement_population(p['counts' if name == 'contact' else 'statistics'], key)
            for collection in (('pairs', 'distance_expectations') if name == 'contact' else ('windows', 'domains')):
                for row in p[collection]:
                    _require(row['population_key'] == key, 'component_row_population')
                    _same_measurement_population(row['measurements'], key)
                    q = row['qualifications']
                    _require(q['normalization_kind'] == inner['normalization']['kind'], 'row_normalization_join')
            if name == 'contact':
                _require([r['pair_key'] for r in p['pairs']] == [r['pair_key'] for r in source['pair_rows']],
                         'pair_order_join')
                for row, basis in zip(p['pairs'], source['pair_rows']):
                    for field in ('enhancer_element_key', 'promoter_element_key', 'enhancer_bin_id', 'promoter_bin_id'):
                        _require(row[field] == basis[field], 'pair_foreign_key_join')
                    _require(row['measurements']['raw_contact'] == basis['raw_contact'], 'pair_native_measurement_join')
                expected = (list(range(inner['parameters']['minimum_separation_bins'], source['bin_count']))
                            if source['read_evidence']['axes_extent'] == 'complete' and source['bin_count'] is not None else [])
                _require([r['separation_bins'] for r in p['distance_expectations']] == expected,
                         'distance_order_population')
            else:
                w = inner['parameters']['window_bins']
                expected = (list(range(w, source['bin_count'] - w + 1))
                            if source['read_evidence']['axes_extent'] == 'complete' and source['bin_count'] is not None else [])
                _require([r['boundary_ordinal'] for r in p['windows']] == expected, 'window_order_population')
                _require(len({r['boundary_bin_id'] for r in p['windows']}) == len(p['windows']), 'window_bin_identity')
                selected = [r for r in p['windows'] if r['measurements']['is_boundary']['value'] is True]
                _require(len(p['domains']) == max(0, len(selected) - 1), 'adjacent_boundary_domains')
                for i, (row, left, right) in enumerate(zip(p['domains'], selected, selected[1:])):
                    _require(row['domain_key'] == f'{key}.domain{i}'
                             and row['left_boundary_bin_id'] == left['boundary_bin_id']
                             and row['right_boundary_bin_id'] == right['boundary_bin_id'], 'domain_boundary_join')
                    m = row['measurements']
                    start, end = (left['measurements']['boundary_position_bp']['value'],
                                  right['measurements']['boundary_position_bp']['value'])
                    _require(m['domain_start_bp']['value'] == start and m['domain_end_bp']['value'] == end
                             and m['domain_length_bp']['value'] == end - start
                             and m['domain_size_kb']['value'] == (end - start) / 1000, 'domain_coordinate_join')
    if selector['mode'] == 'saved_sheet_recalculation':
        saved = selector['saved_sheet_bundle']
        _require(saved['sheet']['sha256'] == digest and saved['sheet']['format'] == sheet['version'],
                 'saved_sheet_identity')
        _require(saved['tables'] == identities, 'saved_table_identity_order')


def _base_qualification(sheet, population, normalization):
    relations = [r['relation'] for r in sheet['references']['relations']
                 if r['population_key'] == population['population_key']]
    reference = ('conflicting_assertions' if 'conflicting_assertions' in relations else
                 'unknown' if not relations or 'unknown' in relations else 'consistent_assertions')
    available = population['normalization']
    state = ('not_requested' if normalization['kind'] == 'raw' else
             available['availability'] if available['specification']['weight_column'] == normalization['weight_column']
             else 'missing')
    return {'data_extent': population['extent'], 'reference_relation': reference,
            'normalization_kind': normalization['kind'], 'normalization_state': state,
            'eligibility': 'eligible' if population['extent'] == 'complete' else 'incomplete_population',
            'interpretation': 'complete_population' if population['extent'] == 'complete' else 'known_subset',
            'reasons': [] if population['extent'] == 'complete' else ['incomplete_comparison_population']}


def _population_fields(sheet, population, components, requested):
    key = population['population_key']
    contact = next((p for p in components['contact']['populations'] if p['population_key'] == key), None) if components['contact'] else None
    insulation = next((p for p in components['insulation']['populations'] if p['population_key'] == key), None) if components['insulation'] else None
    fields = {}
    for name in requested:
        if name == 'bin_count' or name in _RAW_COUNTS:
            value = population['bin_count'] if name == 'bin_count' else population['raw_cell_population'][_RAW_COUNTS[name]]
            fields[name] = _measurement(key, 'count', None, value,
                reason='population_unavailable' if value is None else None)
        elif contact is not None and name in contact['counts']:
            fields[name] = deepcopy(contact['counts'][name])
        elif insulation is not None and name in insulation['statistics']:
            fields[name] = deepcopy(insulation['statistics'][name])
        else:
            fields[name] = _measurement(key, 'count', None, state='not_measured')
    q = _base_qualification(sheet, population, components['parameters']['normalization'])
    needed = []
    if contact and any(name in contact['counts'] for name in requested):
        needed.append(contact['qualifications'])
    if insulation and any(name in insulation['statistics'] for name in requested):
        needed.append(insulation['qualifications'])
    if needed:
        q = deepcopy(needed[0])
        q['reasons'] = list(dict.fromkeys(r for row in needed for r in row['reasons']))
        if any(row['interpretation'] == 'known_subset' for row in needed):
            q['interpretation'] = 'known_subset'
    return {'population_key': key, 'fields': fields, 'qualifications': q}


def _row_total_known(sheet, population, kind):
    if kind == 'contact_pairs':
        return _pair_population_known(sheet, population)
    if kind == 'domains':
        return population['extent'] == 'complete'
    return population['bin_count'] is not None and population['read_evidence']['axes_extent'] == 'complete'


def project_chromatin_result(sheet: ContactSheet, components: ChromatinComponents,
                             *, selector: ResultSelector) -> RequestedProjection:
    """Project selected fields/rows with mandatory qualified source identities.

    Explicit keys retain request order within each selected population. Paging
    flattens that population order and the complete frozen component row order.
    The full private components are neither modified nor returned wholesale.
    """
    validate_chromatin_record('ContactSheet', sheet)
    validate_chromatin_record('ChromatinComponents', components)
    validate_chromatin_record('ResultSelector', selector)
    _validate_joins(sheet, components, selector)
    selection = selector['projection']
    kind, requested = selection['kind'], selection['fields']
    source_populations = {p['population_key']: p for p in sheet['populations']}
    chosen = [source_populations[key] for key in selector['population_keys']]
    rows, qualifications, failures = [], [], []
    page = None
    if kind == 'population_metrics':
        rows = [_population_fields(sheet, p, components, requested) for p in chosen]
        qualifications = [_base_qualification(sheet, p, components['parameters']['normalization']) for p in chosen]
    else:
        mode, collection, key_field, key_selection = _KINDS[kind]
        _require(components[mode] is not None, 'projection_unselected_mode')
        by_population = {p['population_key']: p for p in components[mode]['populations']}
        mode_populations = [by_population[key] for key in selector['population_keys']]
        qualifications = [deepcopy(p['qualifications']) for p in mode_populations]
        flattened = []
        if selection['selection']['by'] == 'keys':
            keys = selection['selection'][key_selection]
            found = set()
            for p in mode_populations:
                indexed = {r[key_field]: r for r in p[collection]}
                for key in keys:
                    if key in indexed:
                        flattened.append(indexed[key])
                        found.add(key)
                    elif kind in ('distance_expectations', 'insulation_windows'):
                        # Numeric keys apply independently to each selected
                        # population; a nonexistent mathematical row is not a
                        # missing measurement with invented foreign keys.
                        failures.append(_failure(sheet, p['population_key'], 'requested_field_unavailable',
                            stage='projection', field_path='/projection/selection/' + key_selection))
            if kind in ('contact_pairs', 'domains'):
                _require(found == set(keys), 'projection_unknown_row_key')
        else:
            for p in mode_populations:
                flattened.extend(p[collection])
            paging = selection['selection']['page']
            offset, limit = paging['offset'], paging['limit']
            known = all(_row_total_known(sheet, p, kind) for p in chosen)
            total = len(flattened) if known else None
            count = len(flattened)
            flattened = flattened[offset:offset + limit]
            page = {'offset': offset, 'returned_count': len(flattened), 'total_row_count': total,
                    'has_more': count > offset + len(flattened)}
        for row in flattened:
            rows.append({name: deepcopy(value) for name, value in row.items() if name != 'measurements'}
                        | {'fields': {name: deepcopy(row['measurements'][name]) for name in requested}})
    # Return only failures that qualify selected rows/fields or the selected
    # population. Unrelated pair diagnostics remain in the private components.
    selected_keys = set(selector['population_keys'])
    selected_pairs = {r['pair_key'] for r in rows if 'pair_key' in r}
    needed_reasons = {m['reason'] for row in rows for m in row['fields'].values() if m['reason']}
    needed_reasons.update(r for row in rows for r in row['qualifications']['reasons'])
    candidates = list(sheet['failures']) + list(components['failures'])
    for mode in ('contact', 'insulation'):
        if components[mode] is not None:
            candidates.extend(components[mode]['failures'])
            for population in components[mode]['populations']:
                if population['population_key'] in selected_keys:
                    candidates.extend(population['failures'])
    for failure in candidates:
        if failure['population_key'] is not None and failure['population_key'] not in selected_keys:
            continue
        if failure['pair_key'] is not None and failure['pair_key'] not in selected_pairs:
            continue
        if failure['code'] in needed_reasons:
            failures.append(deepcopy(failure))
    for row_index, row in enumerate(rows):
        for field, measurement in row['fields'].items():
            if measurement['value'] is None and measurement['reason'] is not None:
                failures.append(_failure(sheet, row['population_key'], measurement['reason'],
                    pair_key=row.get('pair_key'), stage='projection', field_path=f'/rows/{row_index}/fields/{field}'))
    result = {'version': 'chromatin_interaction_projection_v1',
              'source_sheet_sha256': components['source_sheet_sha256'],
              'parameters': deepcopy(components['parameters']), 'kind': kind,
              'population_keys': deepcopy(selector['population_keys']), 'requested_fields': deepcopy(requested),
              'rows': rows, 'page': page, 'qualifications': qualifications,
              'failures': _unique_failures(failures)}
    validate_chromatin_record('RequestedProjection', result)
    return result


__all__ = ['project_chromatin_result']
