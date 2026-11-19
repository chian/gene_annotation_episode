"""Replace one marked span of an instruction text.

The old episodes replaced a span of their ``INSTRUCTIONS`` when the decision exchange protocol was in use
(``INSTRUCTIONS[INSTRUCTIONS.index(start):INSTRUCTIONS.index(end)]``). This does that explicitly: the span
starts at ``start`` (included) and ends before ``end`` (kept); a missing or misordered marker raises.
"""
from __future__ import annotations


def replace_span(text, start, end, replacement):
    """``text`` with the span from ``start`` up to (not including) ``end`` replaced by ``replacement``."""
    for name, value in (('text', text), ('start', start), ('end', end), ('replacement', replacement)):
        if type(value) is not str:
            raise TypeError('replace_span_' + name + '_must_be_text')
    if not start or not end:
        raise ValueError('replace_span_markers_required')
    if text.count(start) != 1:
        raise ValueError('replace_span_start_marker_must_occur_once')
    first = text.index(start)
    last = text.find(end, first + len(start))
    if last < 0:
        raise ValueError('replace_span_end_marker_must_follow_start')
    return text[:first] + replacement + text[last:]


__all__ = ['replace_span']
