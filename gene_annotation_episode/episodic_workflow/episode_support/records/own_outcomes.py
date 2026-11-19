"""One page of an episode's unit outcomes (``EpisodeView.outcomes``), in the shape of the old ``own_outcomes``
page that the old runner served from its ``runtime_actions`` table."""
from __future__ import annotations

from collections.abc import Mapping

from gene_annotation_episode.domain import ContractError


def outcome_page(outcomes, *, offset, limit, tools=None, tool_of=None):
    """One page of ``outcomes`` in position order, shaped like the old ``own_outcomes`` page.

    ``tools`` (a collection of tool names) keeps only outcomes whose ``tool_of(outcome)`` is in it; ``tool_of``
    is then required. Returns ``{'records', 'offset', 'limit', 'total', 'next_offset'}``; ``next_offset`` is
    ``None`` on the last page.
    """
    if type(offset) is not int or offset < 0 or type(limit) is not int or limit < 1:
        raise ContractError('invalid_page')
    rows = list(outcomes)
    if any(not isinstance(row, Mapping) for row in rows):
        raise ContractError('outcome_page_rows_must_be_records')
    if tools is not None:
        if tool_of is None:
            raise ContractError('outcome_page_tool_filter_requires_tool_of')
        wanted = set(tools)
        rows = [row for row in rows if tool_of(row) in wanted]
    page = rows[offset:offset + limit]
    end = offset + len(page)
    return {'records': page, 'offset': offset, 'limit': limit, 'total': len(rows),
            'next_offset': end if end < len(rows) else None}


__all__ = ['outcome_page']
