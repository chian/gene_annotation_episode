"""Deterministic contact/insulation measurements from retained numerical data.

No native-file reader, acquisition, execution, resource choice or inference of
element identity belongs here. Sparse arrays stay sparse. The population is the
selected cis interval, not a projection page or an assumed whole chromosome.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math

import numpy as np

from .chromatin_interaction_contracts import (
    CalculationParameters, ChromatinComponents, ContactComponents,
    ContactParameters, ContactSheet, ContactTables, InsulationComponents,
    InsulationParameters, NormalizationSpec, chromatin_record_digest,
    validate_chromatin_record,
)


_ROLES = ('bins', 'contacts', 'weights', 'cell_states', 'dense_values')
_CONTACT_MODE = 'cis_anchor_contact_enrichment'
_INSULATION_MODE = 'cross_window_insulation_heuristic'
_MAX = float.fromhex('0x1.fffffffffffffp+1023')


def _require(condition, code):
    if not condition:
        raise ValueError('chromatin_' + code)


def _state(reason):
    if reason in ('zero_denominator', 'zero_variance', 'no_valid_distance_pairs',
                  'no_full_windows', 'same_bin_not_evaluated', 'below_minimum_separation'):
        return 'undefined'
    if reason in ('reference_conflict', 'incompatible_variable_bins',
                  'incompatible_matrix_symmetry'):
        return 'incompatible'
    if reason in ('native_output_partial', 'incomplete_comparison_population',
                  'incomplete_window', 'boundary_neighbor_unavailable'):
        return 'truncated'
    if reason in ('native_value_nonfinite', 'native_value_negative',
                  'normalization_weight_invalid', 'duplicate_native_pixel', 'numerical_overflow'):
        return 'failed'
    return 'missing'


def _measurement(key, unit, source_unit, value=None, *, reason=None, state=None,
                 numerator=None, denominator=None):
    # Keep each component's overflow separate: an overflowing sum of squares
    # does not erase an otherwise finite sum, mean, or raw observation.
    if value is not None and (not math.isfinite(value) or abs(value) > _MAX):
        value, reason, state = None, 'numerical_overflow', 'failed'
    if numerator is not None and (not math.isfinite(numerator) or abs(numerator) > _MAX):
        numerator = None
    if denominator is not None and (not math.isfinite(denominator) or abs(denominator) > _MAX):
        denominator = None
    return {'value': value, 'state': state or (_state(reason) if reason else 'derived'),
            'unit': {'kind': unit, 'source_unit': source_unit if 'contact' in unit
                     and unit != 'contact_pairs' else None},
            'reason': reason, 'population_key': key, 'numerator': numerator,
            'denominator': denominator,
            'uncertainty': {'kind': 'not_measured', 'value': None, 'unit': None}}


def _boolean(key, value=None, reason=None):
    return {'value': value, 'state': 'derived' if value is not None else _state(reason),
            'reason': reason, 'population_key': key}


def _failure(sheet, key, reason, *, pair_key=None, field_path=None, stage='calculation'):
    requirements = {
        'zero_denominator': 'positive_denominator',
        'normalization_missing': 'selected_weight_vector',
        'normalization_masked_bin': 'finite_positive_weights',
        'normalization_weight_invalid': 'finite_positive_weights',
        'reference_conflict': 'compatible_reference',
        'incompatible_variable_bins': 'fixed_bin_grid',
        'incompatible_matrix_symmetry': 'valid_native_structure',
        'native_value_negative': 'finite_nonnegative_contact_values',
        'native_value_nonfinite': 'finite_nonnegative_contact_values',
        'numerical_overflow': 'finite_numerical_result',
        'duplicate_native_pixel': 'valid_native_structure',
        'incomplete_window': 'complete_window',
        'boundary_neighbor_unavailable': 'complete_window',
        'requested_field_unavailable': 'requested_selected_field',
    }
    return {'code': reason, 'stage': stage,
            'input_key': sheet['request']['contact']['input_key'],
            'population_key': key, 'element_key': None, 'pair_key': pair_key,
            'artifact_ref': None, 'locator': None, 'field_path': field_path,
            'partial_artifact_refs': [],
            'requirement': requirements.get(reason, 'complete_population')}


def _unique_failures(rows):
    result, seen = [], set()
    for row in rows:
        identity = chromatin_record_digest(row)
        if identity not in seen:
            result.append(deepcopy(row))
            seen.add(identity)
    return result


def _table_identities(sheet):
    return [deepcopy(row['file']) for row in sheet['data_tables'] if row['file'] is not None]


def _source_keys(sheet, key):
    return [row['table_key'] for row in sheet['data_tables']
            if row['population_key'] == key and row['file'] is not None]


class _Sum:
    """Streaming error-free partial sums; storage is unrelated to pixel count."""
    def __init__(self):
        self.integer = 0
        self.partials = []
        self.failed = False

    def add(self, value):
        if self.failed:
            return
        if type(value) is int and not self.partials:
            self.integer += value
            if abs(self.integer) > _MAX:
                self.failed = True
            return
        if self.integer:
            self.partials.append(float(self.integer))
            self.integer = 0
        value = float(value)
        if not math.isfinite(value):
            self.failed = True
            return
        index = 0
        for other in self.partials:
            if abs(value) < abs(other):
                value, other = other, value
            high = value + other
            if not math.isfinite(high):
                self.failed = True
                return
            low = other - (high - value)
            if low:
                self.partials[index] = low
                index += 1
            value = high
        self.partials[index:] = [value]

    def value(self):
        if self.failed:
            return None
        try:
            value = math.fsum(self.partials) if self.partials else self.integer
            return value if math.isfinite(value) and abs(value) <= _MAX else None
        except OverflowError:
            return None


def _weighted(raw, left, right, convention):
    if raw == 0:
        return 0.0, None
    # Exponent arithmetic avoids an overflowing/underflowing intermediate
    # weight product when the final normalized value is representable.
    a, ae = math.frexp(raw)
    b, be = math.frexp(left)
    c, ce = math.frexp(right)
    try:
        value = (math.ldexp(a * b * c, ae + be + ce) if convention == 'multiplicative'
                 else math.ldexp(a / (b * c), ae - be - ce))
    except OverflowError:
        return None, 'numerical_overflow'
    if not math.isfinite(value) or value == 0:
        return None, 'numerical_overflow'
    return value, None


def _square(value):
    result = value * value
    # A nonzero source value must not become a measured square/variance zero
    # merely because its square is below the representable floating range.
    return float('inf') if value != 0 and result == 0 else result


def _pair_range(array, first, second):
    """Locate one ordered pair without a Python object per retained pixel."""
    if array is None:
        return 0, 0
    lo = int(np.searchsorted(array['bin1_id'], first, side='left'))
    hi = int(np.searchsorted(array['bin1_id'], first, side='right'))
    column = array['bin2_id'][lo:hi]
    return (lo + int(np.searchsorted(column, second, side='left')),
            lo + int(np.searchsorted(column, second, side='right')))


class _Population:
    def __init__(self, sheet, population, arrays, normalization):
        self.sheet, self.population, self.arrays = sheet, population, arrays
        self.normalization = normalization
        self.key = population['population_key']
        self.bins = arrays['bins']
        self.n = population['bin_count']
        self.source_unit = sheet['request']['contact']['value_unit']
        self.unit = ('source_contact' if normalization['kind'] == 'raw'
                     else 'normalized_contact')
        relations = [row['relation'] for row in sheet['references']['relations']
                     if row['population_key'] == self.key]
        self.reference = ('conflicting_assertions' if 'conflicting_assertions' in relations
                          else 'unknown' if not relations or 'unknown' in relations
                          else 'consistent_assertions')
        evidence = population['read_evidence']
        self.axes = self.bins is not None and evidence['axes_extent'] == 'complete'
        self.complete = (population['extent'] == 'complete' and self.axes
                         and evidence['index_extent'] == 'complete'
                         and evidence['selected_records_extent'] == 'complete')
        self.implicit = self.complete and evidence['implicit_zero_semantics'] == 'validated_sparse_absence'
        self.triangular = population['native_storage_mode'] in ('symmetric-upper', 'hic-symmetric')
        self.compatibility = (None if self.axes else 'population_unavailable')
        if self.axes and population['fixed_bin_size_bp'] is None:
            self.compatibility = 'incompatible_variable_bins'
        elif self.axes and evidence['symmetry'] == 'not_established':
            self.compatibility = 'incompatible_matrix_symmetry'
        self.weights = arrays['weights']
        self.weight_reason = None
        self.mask = self.invalid = None
        if normalization['kind'] == 'raw':
            self.normalization_state = 'not_requested'
        elif (self.weights is None or population['normalization']['specification']['weight_column']
              != normalization['weight_column']):
            self.weight_reason = 'normalization_missing'
            self.normalization_state = 'missing'
        else:
            self.mask = np.isnan(self.weights)
            self.invalid = (~np.isfinite(self.weights) | (self.weights <= 0)) & ~self.mask
            self.normalization_state = ('partial' if np.any(self.mask) or np.any(self.invalid)
                                        else 'available')

    def m(self, value=None, unit=None, **kwargs):
        return _measurement(self.key, unit or self.unit, self.source_unit, value, **kwargs)

    def q(self, reason=None, eligibility=None, *, heuristic=False):
        eligibility = eligibility or {
            'reference_conflict': 'reference_unresolved',
            'normalization_masked_bin': 'masked_bin',
            'normalization_weight_invalid': 'invalid_weight',
            'incomplete_comparison_population': 'incomplete_population',
            'incompatible_variable_bins': 'incompatible',
            'incompatible_matrix_symmetry': 'incompatible',
            'same_bin_not_evaluated': 'below_minimum_separation',
            'below_minimum_separation': 'below_minimum_separation',
            'zero_variance': 'undefined_statistic',
            'no_valid_distance_pairs': 'undefined_statistic',
            'no_full_windows': 'not_applicable',
        }.get(reason, 'cell_unavailable' if reason else 'eligible')
        return {'data_extent': self.population['extent'], 'reference_relation': self.reference,
                'normalization_kind': self.normalization['kind'],
                'normalization_state': self.normalization_state,
                'eligibility': eligibility,
                'interpretation': ('known_subset' if not self.complete
                                   else 'heuristic_prediction' if heuristic
                                   else 'complete_population'),
                'reasons': [reason] if reason else []}

    def weight_status(self, i, j):
        if self.weight_reason:
            return self.weight_reason
        if self.mask is not None:
            if self.mask[i] or self.mask[j]:
                return 'normalization_masked_bin'
            if self.invalid[i] or self.invalid[j]:
                return 'normalization_weight_invalid'
        return None

    def cell(self, i, j):
        """Return raw, selected, reason. Negative raw data remain inspectable."""
        if not self.axes or i is None or j is None:
            return None, None, 'anchor_bin_unavailable'
        if self.triangular and i > j:
            i, j = j, i
        first, second = int(self.bins[i]['bin_id']), int(self.bins[j]['bin_id'])
        states = self.arrays['cell_states']
        lo, hi = _pair_range(states, first, second)
        if hi > lo:
            code = int(states[lo]['state'])
            return None, None, 'native_value_nonfinite' if code in (2, 3, 4) else 'native_chunk_unavailable'
        contacts = self.arrays['contacts']
        lo, hi = _pair_range(contacts, first, second)
        if hi - lo > 1:
            return None, None, 'duplicate_native_pixel'
        dense = self.arrays['dense_values']
        if hi > lo:
            raw = contacts[lo]['value'].item()
            if dense is not None:
                _require(raw == dense[i, j] or (not math.isfinite(raw)
                         and not math.isfinite(dense[i, j])), 'sparse_dense_conflict')
        elif dense is not None:
            raw = dense[i, j].item()
        elif self.implicit and contacts is not None:
            raw = 0
        else:
            return None, None, ('native_output_partial' if self.population['extent'] == 'partial'
                                else 'population_unavailable')
        if not math.isfinite(raw):
            return None, None, 'native_value_nonfinite'
        if raw < 0:
            return raw, None, 'native_value_negative'
        reason = self.weight_status(i, j)
        if reason:
            return raw, None, reason
        if self.normalization['kind'] == 'raw':
            return raw, raw, None
        selected, reason = _weighted(raw, float(self.weights[i]), float(self.weights[j]),
                                     self.normalization['convention'])
        return raw, selected, reason

    def explicit_pairs(self):
        """Merge ordered sparse pairs and exceptional states, retaining duplicates.

        Yield one mathematical cell at a time; cell() detects a duplicate rather
        than summing or arbitrarily choosing a native occurrence. Dense/square
        data use a repeated upper-triangle traversal without allocating a copy.
        """
        if self.arrays['dense_values'] is not None or not self.triangular:
            for i in range(self.n or 0):
                for j in range(i + 1, self.n):
                    yield i, j
            return
        contacts, states = self.arrays['contacts'], self.arrays['cell_states']
        a = b = 0
        na, nb = len(contacts) if contacts is not None else 0, len(states) if states is not None else 0
        while a < na or b < nb:
            left = (int(contacts[a]['bin1_id']), int(contacts[a]['bin2_id'])) if a < na else None
            right = (int(states[b]['bin1_id']), int(states[b]['bin2_id'])) if b < nb else None
            pair = right if left is None else left if right is None else min(left, right)
            while a < na and (int(contacts[a]['bin1_id']), int(contacts[a]['bin2_id'])) == pair:
                a += 1
            while b < nb and (int(states[b]['bin1_id']), int(states[b]['bin2_id'])) == pair:
                b += 1
            i, j = (int(np.searchsorted(self.bins['bin_id'], v)) for v in pair)
            _require(i < self.n and j < self.n and int(self.bins[i]['bin_id']) == pair[0]
                     and int(self.bins[j]['bin_id']) == pair[1], 'cell_bin_join')
            _require(i <= j, 'upper_triangle_required')
            if i != j:
                yield i, j


def _validate_inputs(sheet, tables, normalization, parameters, mode):
    validate_chromatin_record('ContactSheet', sheet)
    validate_chromatin_record('NormalizationSpec', normalization)
    validate_chromatin_record('ContactParameters' if mode == _CONTACT_MODE
                              else 'InsulationParameters', parameters)
    _require(mode in sheet['request']['analysis_modes'], 'unselected_calculation_mode')
    _require(isinstance(tables, dict) and set(tables) == {'version', 'populations'}
             and tables['version'] == 'chromatin_contact_arrays_v1', 'contact_arrays_required')
    keys = [p['population_key'] for p in sheet['populations']]
    _require(set(tables['populations']) == set(keys), 'array_population_join')
    for population in sheet['populations']:
        arrays = tables['populations'][population['population_key']]
        _require(set(arrays) == {'population_key', *_ROLES}
                 and arrays['population_key'] == population['population_key'], 'array_roles')
        descriptors = {d['role']: d for d in sheet['data_tables']
                       if d['population_key'] == population['population_key']}
        for role in _ROLES:
            value, descriptor = arrays[role], descriptors[role]
            _require((value is None) == (descriptor['availability'] != 'present'), 'array_availability')
            if value is None:
                continue
            _require(isinstance(value, np.ndarray) and not value.flags.writeable
                     and not value.dtype.hasobject, 'readonly_numeric_array_required')
            shape = (descriptor['row_count'],) if role == 'bins' else tuple(descriptor['shape'])
            _require(value.shape == shape, 'array_shape_join')
            if role == 'bins':
                dtype = np.dtype([(name, '<i8') for name in
                                  ('bin_id', 'chromosome_index', 'start_bp', 'end_bp')])
            else:
                spec = descriptor['dtype_descriptor']
                dtype = (np.dtype([(f['name'], f['dtype']) for f in spec['fields']])
                         if spec['kind'] == 'structured' else np.dtype(spec['dtype']))
            _require(value.dtype == dtype, 'array_dtype_join')
        bins = arrays['bins']
        if bins is not None:
            _require(len(bins) == population['bin_count'], 'array_bin_count_join')
            _require(bool(np.all(bins['bin_id'][1:] > bins['bin_id'][:-1])), 'ordered_bin_ids')
            for pair in population['pair_rows']:
                for prefix in ('enhancer', 'promoter'):
                    ordinal, bin_id = pair[prefix + '_bin_ordinal'], pair[prefix + '_bin_id']
                    _require((ordinal is None) == (bin_id is None), 'pair_bin_nullability')
                    if ordinal is not None:
                        _require(0 <= ordinal < len(bins) and int(bins[ordinal]['bin_id']) == bin_id,
                                 'pair_bin_ordinal_join')
                        _require(int(bins[ordinal]['start_bp']) <= pair[prefix + '_anchor_bp']
                                 < int(bins[ordinal]['end_bp']), 'pair_anchor_interval_join')
        for role in ('contacts', 'cell_states'):
            array = arrays[role]
            if array is None:
                continue
            # Bounded slices, not a whole-pixel object copy. Source rows may be
            # duplicated; ordering is required for exact random access.
            for start in range(1, len(array), 65536):
                end = min(len(array), start + 65536)
                previous, current = array[start - 1:end - 1], array[start:end]
                bad = ((current['bin1_id'] < previous['bin1_id']) |
                       ((current['bin1_id'] == previous['bin1_id']) &
                        (current['bin2_id'] < previous['bin2_id'])))
                _require(not bool(np.any(bad)), 'ordered_sparse_pairs_required')


def _distance_rows(ctx, minimum):
    if not ctx.axes:
        return []
    # One accumulator per distance, not per pixel. Sparse implicit zeros enter
    # exact counts and central variance in bulk, never as fabricated stored rows.
    data = {d: {'raw': _Sum(), 'raw_sq': _Sum(), 'sum': _Sum(), 'sq': _Sum(),
                'central': _Sum(), 'offset': _Sum(), 'origin': None,
                'known': 0, 'bad': 0, 'reasons': []}
            for d in range(minimum, ctx.n)}
    for i, j in ctx.explicit_pairs():
        d = j - i
        if d not in data:
            continue
        item = data[d]
        raw, value, reason = ctx.cell(i, j)
        if reason:
            if reason != 'normalization_masked_bin':
                item['bad'] += 1
                if reason not in item['reasons']:
                    item['reasons'].append(reason)
            continue
        item['known'] += 1
        if item['origin'] is None:
            item['origin'] = value
        item['offset'].add(value - item['origin'])
        item['raw'].add(raw)
        item['raw_sq'].add(_square(raw))
        item['sum'].add(value)
        item['sq'].add(_square(value))
    for d, item in data.items():
        nominal = ctx.n - d
        masked = (int(np.count_nonzero(ctx.mask[:-d] | ctx.mask[d:])) if ctx.mask is not None
                  else None if ctx.weight_reason else 0)
        invalid = (int(np.count_nonzero((ctx.invalid[:-d] | ctx.invalid[d:])
                   & ~(ctx.mask[:-d] | ctx.mask[d:]))) if ctx.invalid is not None else 0)
        # Invalid weights already counted on stored cells must not be counted
        # twice. Count valid pairs directly from known rows unless every cell is
        # established, then use nominal minus masks minus distinct invalid cells.
        if ctx.implicit and not ctx.weight_reason:
            bad_cells = 0
            # Accumulated failures exclude masks, but include invalid weights.
            # The weight union below covers also sparse zero cells.
            for reason in item['reasons']:
                if reason != 'normalization_weight_invalid':
                    bad_cells = None
                    break
            if bad_cells is None:
                # Exceptional cells are rare; exact random-access traversal
                # prevents an invalid weight/cell overlap from being double-counted.
                valid = sum(ctx.cell(i, i + d)[2] is None for i in range(nominal))
            else:
                valid = nominal - (masked or 0) - invalid
        else:
            valid = item['known']
        reason = ctx.compatibility or ctx.weight_reason
        if not reason and not ctx.complete:
            reason = 'incomplete_comparison_population'
        if not reason and invalid:
            reason = 'normalization_weight_invalid'
        if not reason and item['reasons']:
            reason = item['reasons'][0]
        if not reason and valid == 0:
            reason = 'no_valid_distance_pairs'
        total = item['sum'].value()
        if not reason and total is None:
            reason = 'numerical_overflow'
        mean = total / valid if reason is None else None
        if mean == 0 and total != 0:
            reason, mean = 'numerical_overflow', None
        origin = item['origin'] if item['origin'] is not None else 0
        item['offset'].add(-origin * (valid - item['known']))
        offset_sum = item['offset'].value()
        center = offset_sum / valid if reason is None and offset_sum is not None else None
        item.update(nominal=nominal, masked=masked, valid=valid, reason=reason,
                    mean=mean, center=center, origin=origin)
    # Stable centered second pass avoids Q/n - mean**2 cancellation. Add the
    # unrepresented established zeros as one central-moment contribution.
    for i, j in ctx.explicit_pairs():
        item = data.get(j - i)
        if item is None or item['center'] is None:
            continue
        _, value, reason = ctx.cell(i, j)
        if reason is None:
            # Subtract an exact native integer origin before conversion; uint64
            # or int64 differences smaller than a float ULP remain measurable.
            delta = (value - item['origin']) - item['center']
            item['central'].add(_square(delta))
    rows = []
    for d, item in data.items():
        reason, mean = item['reason'], item['mean']
        if item['center'] is not None:
            zero_delta = -item['origin'] - item['center']
            zero_count = item['valid'] - item['known']
            if zero_count:
                item['central'].add(zero_count * _square(zero_delta))
        elif mean is not None:
            item['central'].failed = True
        sums = {name: item[name].value() for name in ('raw', 'raw_sq', 'sum', 'sq', 'central')}
        m = {
            'nominal_distance_pair_count': ctx.m(item['nominal'], 'contact_pairs'),
            'masked_distance_pair_count': ctx.m(item['masked'], 'contact_pairs',
                reason=ctx.weight_reason if item['masked'] is None else None),
            'valid_distance_pair_count': ctx.m(item['valid'], 'contact_pairs'),
            'raw_distance_sum': ctx.m(sums['raw'], 'source_contact',
                reason='numerical_overflow' if sums['raw'] is None else None),
            'raw_distance_sum_squares': ctx.m(sums['raw_sq'], 'source_contact_squared',
                reason='numerical_overflow' if sums['raw_sq'] is None else None),
            'distance_sum': ctx.m(sums['sum'], reason='numerical_overflow' if sums['sum'] is None else None),
            'distance_sum_squares': ctx.m(sums['sq'], ctx.unit + '_squared',
                reason='numerical_overflow' if sums['sq'] is None else None),
            'expected_contact': ctx.m(mean, reason=reason, numerator=sums['sum'] if reason is None else None,
                                      denominator=item['valid'] if reason is None else None),
            'distance_population_variance': ctx.m(
                sums['central'] / item['valid'] if reason is None and sums['central'] is not None else None,
                ctx.unit + '_squared', reason=reason or ('numerical_overflow' if sums['central'] is None else None),
                numerator=sums['central'] if reason is None else None,
                denominator=item['valid'] if reason is None else None),
        }
        rows.append({'population_key': ctx.key, 'separation_bins': d, 'measurements': m,
                     'qualifications': ctx.q(reason)})
    return rows


def _pair_population_known(sheet, population):
    return (sheet['elements'] is not None and sheet['elements']['extent'] == 'complete'
            and population['read_evidence']['axes_extent'] == 'complete'
            and all(row['membership'] != 'unresolved' for row in population['element_anchor_rows'])
            and not any(f['code'] == 'element_assignment_missing' for f in sheet['elements']['failures']))


def calculate_contact_enrichment(sheet: ContactSheet, *, tables: ContactTables,
                                 normalization: NormalizationSpec,
                                 parameters: ContactParameters) -> ContactComponents:
    """Retain occurrence pairs and exact same-population diagonal statistics."""
    _validate_inputs(sheet, tables, normalization, parameters, _CONTACT_MODE)
    populations = []
    for population in sheet['populations']:
        ctx = _Population(sheet, population, tables['populations'][population['population_key']], normalization)
        distances = _distance_rows(ctx, parameters['minimum_separation_bins'])
        by_distance = {row['separation_bins']: row['measurements']['expected_contact'] for row in distances}
        multiplicities = Counter(tuple(sorted((p['enhancer_bin_id'], p['promoter_bin_id'])))
            for p in population['pair_rows'] if p['enhancer_bin_id'] is not None and p['promoter_bin_id'] is not None)
        pairs, failures = [], deepcopy(population['failures'])
        for pair in population['pair_rows']:
            i, j = pair['enhancer_bin_ordinal'], pair['promoter_bin_ordinal']
            raw, value, cell_reason = ctx.cell(i, j)
            # C1's raw measurement is retained, including its original failure
            # state. Known observations must agree with the supplied arrays.
            if pair['raw_contact']['value'] is not None:
                _require(raw == pair['raw_contact']['value'], 'pair_raw_array_conflict')
            separation = abs(i - j) if i is not None and j is not None else None
            reason = ctx.compatibility
            if pair['reference_relation'] == 'conflicting_assertions':
                reason = 'reference_conflict'
            if not reason and separation is None:
                reason = 'anchor_bin_unavailable'
            if not reason and separation < parameters['minimum_separation_bins']:
                reason = 'same_bin_not_evaluated' if separation == 0 else 'below_minimum_separation'
            if not reason and not ctx.complete:
                reason = 'incomplete_comparison_population'
            if not reason:
                reason = cell_reason
            expectation = deepcopy(by_distance.get(separation))
            if reason:
                expectation = ctx.m(reason=reason)
            elif expectation is None:
                reason = 'no_valid_distance_pairs'
                expectation = ctx.m(reason=reason)
            elif expectation['value'] is None:
                reason = expectation['reason']
            eligibility_reason = reason
            if reason is None and expectation['value'] == 0:
                reason = 'zero_denominator'
            fold = None
            if reason is None:
                fold = value / expectation['value']
                if not math.isfinite(fold) or fold == 0 and value != 0:
                    reason, fold = 'numerical_overflow', None
            multiplicity = (multiplicities[tuple(sorted((pair['enhancer_bin_id'], pair['promoter_bin_id'])))]
                            if i is not None and j is not None else None)
            measurements = {
                'raw_contact': deepcopy(pair['raw_contact']),
                'normalized_contact': (ctx.m(unit='normalized_contact', state='not_measured')
                    if normalization['kind'] == 'raw' else ctx.m(value, 'normalized_contact',
                        state='normalized' if value is not None else None, reason=cell_reason)),
                'anchor_distance_bp': ctx.m(abs(pair['enhancer_anchor_bp'] - pair['promoter_anchor_bp']), 'bp'),
                'bin_separation': ctx.m(separation, 'bins', reason='anchor_bin_unavailable' if separation is None else None),
                'expected_contact': expectation,
                'fold_enrichment': ctx.m(fold, 'dimensionless', reason=reason,
                    numerator=value if reason in (None, 'zero_denominator') else None,
                    denominator=expectation['value'] if reason in (None, 'zero_denominator') else None),
                'occurrence_multiplicity': ctx.m(multiplicity, 'count',
                    reason='anchor_bin_unavailable' if multiplicity is None else None),
                'above_fold_threshold': _boolean(ctx.key, fold > parameters['fold_threshold'] if fold is not None else None, reason),
            }
            q = ctx.q(eligibility_reason)
            if reason and reason not in q['reasons']:
                q['reasons'].append(reason)
            q['reference_relation'] = pair['reference_relation']
            pairs.append({name: deepcopy(pair[name]) for name in
                          ('pair_key', 'population_key', 'enhancer_element_key', 'promoter_element_key',
                           'enhancer_bin_id', 'promoter_bin_id')} | {'measurements': measurements, 'qualifications': q})
            if reason:
                failures.append(_failure(sheet, ctx.key, reason, pair_key=pair['pair_key']))
        known = _pair_population_known(sheet, population)
        population_reason = ctx.compatibility or ctx.weight_reason or (
            'normalization_weight_invalid' if ctx.invalid is not None and np.any(ctx.invalid) else None) or (
            'incomplete_comparison_population' if not ctx.complete or not known else None)
        values = {'requested_pair_count': len(pairs) if known else None,
                  'eligible_pair_count': sum(r['qualifications']['eligibility'] == 'eligible' for r in pairs),
                  'fold_defined_pair_count': sum(r['measurements']['fold_enrichment']['value'] is not None for r in pairs),
                  'above_threshold_pair_count': sum(r['measurements']['above_fold_threshold']['value'] is True for r in pairs)
                    if not population_reason else None,
                  'distinct_bin_pair_count': len(multiplicities) if known else None}
        counts = {name: ctx.m(value, 'contact_pairs', reason=(population_reason
                             if name == 'above_threshold_pair_count' else 'incomplete_comparison_population')
                             if value is None else None) for name, value in values.items()}
        for index, row in enumerate(distances):
            for field, measurement in row['measurements'].items():
                if measurement['reason']:
                    failures.append(_failure(sheet, ctx.key, measurement['reason'],
                        field_path=f'/populations/{len(populations)}/distance_expectations/{index}/measurements/{field}'))
        populations.append({'population_key': ctx.key, 'source_table_keys': _source_keys(sheet, ctx.key),
            'pairs': pairs, 'distance_expectations': distances, 'counts': counts,
            'qualifications': ctx.q(population_reason), 'failures': _unique_failures(failures)})
    result = {'version': 'chromatin_contact_components_v1', 'source_sheet_sha256': chromatin_record_digest(sheet),
              'table_identities': _table_identities(sheet), 'normalization': deepcopy(normalization),
              'mode': _CONTACT_MODE, 'parameters': deepcopy(parameters), 'populations': populations,
              'failures': deepcopy(sheet['failures'])}
    validate_chromatin_record('ContactComponents', result)
    return result


def calculate_insulation_components(sheet: ContactSheet, *, tables: ContactTables,
                                    normalization: NormalizationSpec,
                                    parameters: InsulationParameters) -> InsulationComponents:
    """All full cross windows, population z scores and adjacent-minimum domains."""
    _validate_inputs(sheet, tables, normalization, parameters, _INSULATION_MODE)
    populations = []
    w = parameters['window_bins']
    for population_ordinal, population in enumerate(sheet['populations']):
        ctx = _Population(sheet, population, tables['populations'][population['population_key']], normalization)
        windows, failures = [], deepcopy(population['failures'])
        for k in range(w, ctx.n - w + 1) if ctx.axes else ():
            total, valid, reasons = _Sum(), 0, []
            for i in range(k - w, k):
                for j in range(k, k + w):
                    _, value, reason = ctx.cell(i, j)
                    if reason:
                        if reason not in reasons:
                            reasons.append(reason)
                    else:
                        valid += 1
                        total.add(value)
            known = total.value()
            reason = ctx.compatibility or ctx.weight_reason or (
                'incomplete_window' if valid != w * w else 'numerical_overflow' if known is None else None)
            value = known if reason is None else None
            m = {'boundary_position_bp': ctx.m(int(ctx.bins[k]['start_bp']), 'bp'),
                 'nominal_window_cell_count': ctx.m(w * w, 'contact_pairs'),
                 'valid_window_cell_count': ctx.m(valid, 'contact_pairs'),
                 'known_cross_contact_sum': ctx.m(known, reason='numerical_overflow' if known is None else None),
                 'cross_contact_sum': ctx.m(value, reason=reason),
                 'cross_contact_mean': ctx.m(value / (w * w) if value is not None else None,
                     ctx.unit + '_per_pair', reason=reason, numerator=value,
                     denominator=w * w if value is not None else None),
                 'insulation_z': ctx.m(unit='dimensionless', reason=reason or 'zero_variance'),
                 'boundary_strength': ctx.m(unit='dimensionless', state='not_measured'),
                 'is_boundary': _boolean(ctx.key, reason=reason or 'zero_variance')}
            q = ctx.q(reason, heuristic=True)
            q['reasons'] = list(dict.fromkeys(q['reasons'] + reasons))
            windows.append({'population_key': ctx.key, 'boundary_bin_id': int(ctx.bins[k]['bin_id']),
                            'boundary_ordinal': k, 'measurements': m, 'qualifications': q})
        values = [r['measurements']['cross_contact_sum']['value'] for r in windows
                  if r['measurements']['cross_contact_sum']['value'] is not None]
        total, central, offset = _Sum(), _Sum(), _Sum()
        origin = values[0] if values else 0
        for value in values:
            total.add(value)
            offset.add(value - origin)
        s = total.value()
        statistical_reason = ctx.compatibility or ctx.weight_reason or (
            'no_full_windows' if not windows else 'incomplete_window' if not values
            else 'numerical_overflow' if s is None else None)
        mean = s / len(values) if statistical_reason is None else None
        if mean == 0 and s != 0:
            statistical_reason, mean = 'numerical_overflow', None
        center = offset.value() / len(values) if mean is not None and offset.value() is not None else None
        if center is not None:
            for value in values:
                delta = (value - origin) - center
                central.add(_square(delta))
        elif mean is not None:
            central.failed = True
        qsum = central.value()
        variance = qsum / len(values) if mean is not None and qsum is not None else None
        if mean is not None and variance is None:
            statistical_reason = 'numerical_overflow'
        z_reason = statistical_reason or ('zero_variance' if variance == 0 else None)
        for index, row in enumerate(windows):
            m = row['measurements']
            value = m['cross_contact_sum']['value']
            reason = m['cross_contact_sum']['reason'] or z_reason
            delta = (value - origin) - center if reason is None else None
            z = delta / math.sqrt(variance) if reason is None else None
            m['insulation_z'] = ctx.m(z, 'dimensionless', reason=reason,
                numerator=delta,
                denominator=math.sqrt(variance) if reason is None else None)
        selected = []
        for index, row in enumerate(windows):
            m = row['measurements']
            z, reason = m['insulation_z']['value'], m['insulation_z']['reason']
            edge = index in (0, len(windows) - 1)
            if edge:
                flag = False
                # Edge ineligibility is known even when z is undefined.
                m['is_boundary'] = _boolean(ctx.key, False)
                row['qualifications']['eligibility'] = 'ineligible_edge'
            elif z is None:
                flag = None
                m['is_boundary'] = _boolean(ctx.key, reason=reason)
                row['qualifications']['eligibility'] = 'undefined_statistic'
            else:
                neighbors = [windows[index + offset]['measurements']['insulation_z']['value'] for offset in (-1, 1)]
                reason = 'boundary_neighbor_unavailable' if None in neighbors else None
                flag = (z < neighbors[0] and z < neighbors[1] and z < parameters['z_threshold']) if reason is None else None
                m['is_boundary'] = _boolean(ctx.key, flag, reason)
                if reason:
                    row['qualifications']['eligibility'] = 'cell_unavailable'
            if flag:
                m['boundary_strength'] = ctx.m(-z, 'dimensionless')
                selected.append(row)
            elif flag is None:
                m['boundary_strength'] = ctx.m(unit='dimensionless', reason=reason)
            if reason and reason not in row['qualifications']['reasons']:
                row['qualifications']['reasons'].append(reason)
        domains = []
        for index, (left, right) in enumerate(zip(selected, selected[1:])):
            start = left['measurements']['boundary_position_bp']['value']
            end = right['measurements']['boundary_position_bp']['value']
            domains.append({'domain_key': f'p{population_ordinal}.domain{index}', 'population_key': ctx.key,
                'left_boundary_bin_id': left['boundary_bin_id'], 'right_boundary_bin_id': right['boundary_bin_id'],
                'measurements': {'domain_start_bp': ctx.m(start, 'bp'), 'domain_end_bp': ctx.m(end, 'bp'),
                    'domain_length_bp': ctx.m(end - start, 'bp'),
                    'domain_size_kb': ctx.m((end - start) / 1000, 'kb', numerator=end - start, denominator=1000)},
                'qualifications': ctx.q(heuristic=True)})
        counts = {'nominal_window_count': len(windows) if ctx.axes else None,
                  'complete_window_count': len(values), 'omitted_window_count': len(windows) - len(values) if ctx.axes else None,
                  'z_population_count': len(values), 'selected_boundary_count': len(selected), 'domain_count': len(domains)}
        statistics = {name: ctx.m(value, 'count', reason='population_unavailable' if value is None else None)
                      for name, value in counts.items()}
        statistics['z_population_mean'] = ctx.m(mean, reason=statistical_reason,
            numerator=s if mean is not None else None, denominator=len(values) if mean is not None else None)
        statistics['z_population_variance'] = ctx.m(variance, ctx.unit + '_squared', reason=statistical_reason,
            numerator=qsum if variance is not None else None, denominator=len(values) if variance is not None else None)
        for index, row in enumerate(windows):
            for field, measurement in row['measurements'].items():
                if measurement['reason']:
                    failures.append(_failure(sheet, ctx.key, measurement['reason'],
                        field_path=f'/populations/{len(populations)}/windows/{index}/measurements/{field}'))
        if z_reason:
            failures.append(_failure(sheet, ctx.key, z_reason,
                field_path=f'/populations/{len(populations)}/statistics'))
        population_reason = statistical_reason or ('incomplete_window' if len(values) < len(windows) else None)
        populations.append({'population_key': ctx.key, 'source_table_keys': _source_keys(sheet, ctx.key),
            'windows': windows, 'statistics': statistics, 'domains': domains,
            'qualifications': ctx.q(population_reason, heuristic=True), 'failures': _unique_failures(failures)})
    result = {'version': 'chromatin_insulation_components_v1', 'source_sheet_sha256': chromatin_record_digest(sheet),
              'table_identities': _table_identities(sheet), 'normalization': deepcopy(normalization),
              'mode': _INSULATION_MODE, 'parameters': deepcopy(parameters), 'populations': populations,
              'failures': deepcopy(sheet['failures'])}
    validate_chromatin_record('InsulationComponents', result)
    return result


def calculate_chromatin_components(sheet: ContactSheet, *, tables: ContactTables,
                                   parameters: CalculationParameters) -> ChromatinComponents:
    """Calculate the originally selected modes with one explicit parameter snapshot."""
    validate_chromatin_record('CalculationParameters', parameters)
    modes = sheet['request']['analysis_modes']
    _require((parameters['contact'] is not None) == (_CONTACT_MODE in modes)
             and (parameters['insulation'] is not None) == (_INSULATION_MODE in modes), 'parameter_mode_join')
    contact = (calculate_contact_enrichment(sheet, tables=tables, normalization=parameters['normalization'],
               parameters=parameters['contact']) if parameters['contact'] is not None else None)
    insulation = (calculate_insulation_components(sheet, tables=tables, normalization=parameters['normalization'],
                  parameters=parameters['insulation']) if parameters['insulation'] is not None else None)
    result = {'version': 'chromatin_interaction_components_v1', 'source_sheet_sha256': chromatin_record_digest(sheet),
              'table_identities': _table_identities(sheet), 'parameters': deepcopy(parameters),
              'contact': contact, 'insulation': insulation, 'failures': deepcopy(sheet['failures'])}
    validate_chromatin_record('ChromatinComponents', result)
    return result


__all__ = ['calculate_contact_enrichment', 'calculate_insulation_components', 'calculate_chromatin_components']
