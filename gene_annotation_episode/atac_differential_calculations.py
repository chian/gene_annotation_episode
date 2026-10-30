"""Streaming ATAC track partitions, likelihood components and derived regions.

The supplied sheet consumer owns reference, condition, sample and raw-pileup
compatibility checks. These functions consume ordered numerical rows; they do
not read files, run MACS2, infer reference bounds or repair native BED records.
Unknown track spans remain unknown. Region scores are likelihood ratios, not
p-values, replicate uncertainty or annotation confidence.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from copy import deepcopy
import math
import struct

from .atac_differential_scores import (
    calculate_atac_interval_scores, validate_atac_likelihood_parameters,
)


_ROLES = ('signal1', 'background1', 'signal2', 'background2')
_CATEGORIES = ('condition1', 'condition2', 'common')
_EXTENTS = ('complete', 'partial', 'missing', 'failed')
_STATES = ('observed', 'missing', 'invalid', 'ambiguous')
_MAX_COORDINATE = 2**63 - 1


def _integer(value, *, minimum=0):
    return type(value) is int and value >= minimum


def _finite_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _geometry(chromosome, start, end):
    if (type(chromosome) is not str or not chromosome or
            not _integer(start) or not _integer(end, minimum=1) or
            not start < end <= _MAX_COORDINATE):
        raise ValueError('atac_valid_interval_geometry_required')
    try:
        return chromosome.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError('atac_utf8_chromosome_required') from error


def _row_key(row):
    if not isinstance(row, (tuple, list)) or len(row) != 9:
        raise ValueError('atac_nine_column_track_row_required')
    ordinal, line, byte_start, byte_end, chromosome, start, end, value, lexeme = row
    chromosome_key = _geometry(chromosome, start, end)
    if (not _integer(ordinal) or not _integer(line, minimum=1) or
            not _integer(byte_start) or not _integer(byte_end, minimum=1) or
            byte_start >= byte_end or
            value is not None and not _finite_number(value) or
            lexeme is not None and type(lexeme) is not str):
        raise ValueError('atac_valid_track_row_fields_required')
    return chromosome_key, start, end, ordinal


class _TrackCursor:
    """One lookahead and only rows that can still cover the current position."""

    def __init__(self, rows):
        try:
            self.rows = iter(rows)
        except TypeError as error:
            raise ValueError('atac_track_row_iterable_required') from error
        self.pending = None
        self.previous_key = None
        self.started = False
        self.active = []

    def advance(self):
        try:
            row = next(self.rows)
        except StopIteration:
            self.pending = None
            return
        key = _row_key(row)
        if self.previous_key is not None and key <= self.previous_key:
            raise ValueError('atac_track_rows_out_of_order')
        self.previous_key = key
        self.pending = tuple(row)

    def at(self, chromosome_key, position):
        if not self.started:
            self.started = True
            self.advance()
        self.active = [row for row in self.active
                       if row[4].encode('utf-8') == chromosome_key and row[6] > position]
        while self.pending is not None:
            row = self.pending
            key = row[4].encode('utf-8')
            if key > chromosome_key or key == chromosome_key and row[5] > position:
                break
            if key == chromosome_key and row[6] > position:
                self.active.append(row)
            self.advance()

    def next_boundary(self, chromosome_key, end):
        for row in self.active:
            end = min(end, row[6])
        if self.pending is not None and self.pending[4].encode('utf-8') == chromosome_key:
            end = min(end, self.pending[5])
        return end

    def measurement(self, unlocated_count):
        ordinals = sorted(row[0] for row in self.active)
        if not self.active:
            return None, 'missing', ordinals
        if len(self.active) > 1:
            return None, 'ambiguous', ordinals
        value = self.active[0][7]
        state = ('invalid' if value is None or value < 0 or unlocated_count
                 else 'observed')
        return value, state, ordinals

    def finish(self):
        # A selected population may end before the table does. Exhausting its
        # iterator validates late ordering/hash failures without inventing more
        # intervals or claiming that a consumed prefix was a complete table.
        self.active.clear()
        if not self.started:
            self.started = True
            self.advance()
        while self.pending is not None:
            self.advance()


def iter_atac_track_segments(tracks: Mapping[str, dict], *,
                             intervals: Iterable[dict]) -> Iterator[dict]:
    """Partition explicit populations at every overlapping track boundary.

    Rows use the native nine-column tuple and exact UTF-8 chromosome ordering.
    Population intervals must be ordered and disjoint; touching intervals stay
    separate populations. No genome-sized array or full-stream copy is made.
    Already yielded records survive a later input exception, but the caller
    must retain that failure and must not publish the stream as complete.
    """
    if not isinstance(tracks, Mapping) or set(tracks) != set(_ROLES):
        raise ValueError('atac_exact_four_track_roles_required')
    cursors, extents, unlocated = {}, {}, {}
    for role in _ROLES:
        track = tracks[role]
        if (not isinstance(track, Mapping) or
                set(track) != {'rows', 'extent', 'unlocated_invalid_row_count'} or
                track['extent'] not in _EXTENTS or
                not _integer(track['unlocated_invalid_row_count'])):
            raise ValueError('atac_valid_track_port_required')
        cursors[role] = _TrackCursor(track['rows'])
        extents[role] = track['extent']
        unlocated[role] = track['unlocated_invalid_row_count']

    previous, ordinal = None, 0
    for population_ordinal, population in enumerate(intervals):
        if not isinstance(population, Mapping) or set(population) != {'chromosome', 'start', 'end'}:
            raise ValueError('atac_population_interval_required')
        chromosome, start, end = (population[name] for name in ('chromosome', 'start', 'end'))
        chromosome_key = _geometry(chromosome, start, end)
        if previous is not None and (chromosome_key < previous[0] or
                chromosome_key == previous[0] and start < previous[1]):
            raise ValueError('atac_populations_out_of_order_or_overlapping')
        previous = chromosome_key, end
        position = start
        while position < end:
            boundary = end
            for cursor in cursors.values():
                cursor.at(chromosome_key, position)
                boundary = cursor.next_boundary(chromosome_key, boundary)
            values, states, sources = {}, {}, {}
            for role, cursor in cursors.items():
                values[role], states[role], sources[role] = cursor.measurement(unlocated[role])
            yield {
                'interval_ordinal': ordinal, 'population_ordinal': population_ordinal,
                'chromosome': chromosome, 'start': position, 'end': boundary,
                'values': values, 'states': states, 'source_rows': sources,
                'source_extents': dict(extents), 'unlocated_invalid_rows': dict(unlocated),
            }
            ordinal += 1
            position = boundary
    for cursor in cursors.values():
        cursor.finish()


def _validate_segment(segment):
    if not isinstance(segment, Mapping):
        raise ValueError('atac_segment_required')
    try:
        chromosome_key = _geometry(segment['chromosome'], segment['start'], segment['end'])
        if not _integer(segment['interval_ordinal']) or not _integer(segment['population_ordinal']):
            raise ValueError('atac_segment_ordinal_required')
        for name in ('values', 'states', 'source_rows', 'source_extents', 'unlocated_invalid_rows'):
            if not isinstance(segment[name], Mapping) or set(segment[name]) != set(_ROLES):
                raise ValueError('atac_segment_role_fields_required')
        for role in _ROLES:
            value, state = segment['values'][role], segment['states'][role]
            if (state not in _STATES or value is not None and not _finite_number(value) or
                    state == 'observed' and (value is None or value < 0) or
                    state in ('missing', 'ambiguous') and value is not None or
                    segment['source_extents'][role] not in _EXTENTS or
                    not _integer(segment['unlocated_invalid_rows'][role])):
                raise ValueError('atac_valid_segment_measurements_required')
            rows = segment['source_rows'][role]
            if (not isinstance(rows, list) or any(not _integer(row) for row in rows) or
                    state == 'missing' and rows or state == 'ambiguous' and len(rows) < 2 or
                    state in ('observed', 'invalid') and len(rows) != 1):
                raise ValueError('atac_segment_source_rows_required')
    except KeyError as error:
        raise ValueError('atac_complete_segment_fields_required') from error
    return chromosome_key


def iter_atac_interval_components(segments: Iterable[dict], *, depth1: int | float | None,
                                  depth2: int | float | None, depth_unit: str,
                                  pseudocount: int | float) -> Iterator[dict]:
    """Preserve each partition record and add its independently usable scores."""
    validate_atac_likelihood_parameters(depth_unit=depth_unit, pseudocount=pseudocount)
    for segment in segments:
        _validate_segment(segment)
        operands = {role: segment['values'][role] if segment['states'][role] == 'observed'
                    else None for role in _ROLES}
        scores = calculate_atac_interval_scores(**operands, depth1=depth1, depth2=depth2,
                                               depth_unit=depth_unit, pseudocount=pseudocount)
        yield {**deepcopy(segment), 'scores': scores}


def _native_likelihoods(component):
    values = []
    try:
        for name in ('condition1_vs_background', 'condition2_vs_background', 'condition1_vs_condition2'):
            measurement = component['scores']['likelihoods'][name]['native_float32']
            value, state = measurement['value'], measurement['state']
            if (state not in ('derived', 'missing', 'invalid', 'undefined') or
                    measurement['unit'] != 'signed_log10_likelihood_ratio' or
                    (value is not None) != (state == 'derived') or
                    value is not None and not _finite_number(value)):
                raise ValueError('atac_native_likelihood_measurement_required')
            values.append(value)
    except (KeyError, TypeError) as error:
        raise ValueError('atac_native_likelihood_measurement_required') from error
    return values


def _and(*predicates):
    if any(value is False for value in predicates):
        return False
    return None if any(value is None for value in predicates) else True


def _memberships(first, second, between, cutoff):
    first_high = None if first is None else first >= cutoff
    second_high = None if second is None else second >= cutoff
    return {
        'condition1': _and(first_high, None if between is None else between >= cutoff),
        'condition2': _and(second_high, None if between is None else between <= -cutoff),
        'common': _and(first_high, second_high,
                       None if between is None else -cutoff <= between <= cutoff),
    }


def _partial(segment):
    return any(segment['source_extents'][role] != 'complete' or
               segment['states'][role] != 'observed' for role in _ROLES)


class _RegionAccumulator:
    """Only one open region and its pending false gap for one category."""

    def __init__(self, category, minimum, max_gap):
        self.category, self.minimum, self.max_gap = category, minimum, max_gap
        self.region = None
        self.boundary = 'population_boundary'
        self.gap_bp = 0
        self.gap_partial = False

    def close(self, boundary):
        region, self.region = self.region, None
        if region is None or region['end'] - region['start'] < self.minimum:
            return None
        region['span_bp'] = region['end'] - region['start']
        region['bridged_gap_bp'] = region['span_bp'] - region['qualifying_bp']
        region['score_denominator_bp'] = region['qualifying_bp']
        region['mean_score'] = region['score_numerator'] / region['score_denominator_bp']
        region['right_boundary'] = boundary
        if boundary == 'unknown_gap':
            region['source_extent'] = 'partial'
        try:
            native = struct.unpack('<f', struct.pack('<f', region['mean_score']))[0]
        except (OverflowError, struct.error):
            native = None
        if native is not None and not math.isfinite(native):
            native = None
        region['native_float32_mean_score'] = native
        region['numerical_reason'] = None if native is not None else 'float32_overflow'
        return region

    def consume(self, component, membership, between):
        length = component['end'] - component['start']
        if membership is None:
            closed = self.close('unknown_gap')
            self.boundary, self.gap_bp, self.gap_partial = 'unknown_gap', 0, False
            return closed
        if membership is False:
            self.gap_bp += length
            self.gap_partial = self.gap_partial or _partial(component)
            if self.gap_bp > self.max_gap:
                closed = self.close('observed_gap')
                self.boundary = 'observed_gap'
                return closed
            return None

        if self.region is None:
            self.region = {
                'category': self.category, 'population_ordinal': component['population_ordinal'],
                'chromosome': component['chromosome'], 'start': component['start'],
                'end': component['end'], 'qualifying_bp': 0, 'qualifying_interval_ordinals': [],
                'score_numerator': 0.0, 'score_unit': 'signed_log10_likelihood_ratio',
                'left_boundary': self.boundary,
                'source_extent': 'partial' if self.boundary == 'unknown_gap' else 'complete',
            }
        elif self.gap_partial:
            self.region['source_extent'] = 'partial'
        if _partial(component):
            self.region['source_extent'] = 'partial'
        score = (between if self.category == 'condition1' else
                 -between if self.category == 'condition2' else abs(between))
        numerator = self.region['score_numerator'] + score * length
        if not math.isfinite(numerator):
            raise ValueError('atac_region_numerator_overflow')
        self.region['score_numerator'] = numerator
        self.region['qualifying_bp'] += length
        self.region['qualifying_interval_ordinals'].append(component['interval_ordinal'])
        self.region['end'] = component['end']
        self.gap_bp, self.gap_partial = 0, False
        return None


def iter_atac_differential_regions(components: Iterable[dict], *, cutoff: int | float,
                                   min_length_bp: int, max_gap_bp: int) -> Iterator[dict]:
    """Emit regions in deterministic streaming closure order.

    Inclusive native thresholds may put an interval in multiple categories.
    A known-false AND predicate is enough to bridge a gap, even when another
    operand is unavailable. Unknown membership always breaks a region. Only
    qualifying lengths enter the weighted score; bridge lengths enter its span.
    Boundary labels describe why extension stopped, not coordinate equality
    with a population endpoint. Population/unknown boundaries remain relevant
    across at most ``max_gap_bp`` known-false bases.
    """
    if not _finite_number(cutoff) or cutoff < 0:
        raise ValueError('atac_finite_nonnegative_cutoff_required')
    if (not _integer(min_length_bp, minimum=1) or not _integer(max_gap_bp) or
            max_gap_bp >= min_length_bp):
        raise ValueError('atac_positive_minimum_and_smaller_nonnegative_gap_required')
    accumulators = None
    previous = None
    for component in components:
        chromosome_key = _validate_segment(component)
        current = (component['population_ordinal'], chromosome_key,
                   component['start'], component['end'], component['interval_ordinal'])
        if previous is not None:
            if (current[4] <= previous[4] or current[0] < previous[0] or
                    current[0] == previous[0] and
                    (current[1] != previous[1] or current[2] != previous[3]) or
                    current[0] > previous[0] and
                    (current[1] < previous[1] or current[1] == previous[1] and current[2] < previous[3])):
                raise ValueError('atac_components_out_of_partition_order')
        first, second, between = _native_likelihoods(component)
        if previous is None or current[0] != previous[0]:
            if accumulators is not None:
                for accumulator in accumulators:
                    region = accumulator.close('population_boundary')
                    if region is not None:
                        yield region
            accumulators = [_RegionAccumulator(category, min_length_bp, max_gap_bp)
                            for category in _CATEGORIES]
        memberships = _memberships(first, second, between, cutoff)
        for accumulator in accumulators:
            region = accumulator.consume(component, memberships[accumulator.category], between)
            if region is not None:
                yield region
        previous = current
    if accumulators is not None:
        for accumulator in accumulators:
            region = accumulator.close('population_boundary')
            if region is not None:
                yield region


__all__ = ['iter_atac_track_segments', 'iter_atac_interval_components',
           'iter_atac_differential_regions']
