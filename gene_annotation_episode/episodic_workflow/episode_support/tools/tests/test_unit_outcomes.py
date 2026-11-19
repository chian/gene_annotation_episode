"""Offered catalogs and failed-unit outcomes over a real Store."""
from __future__ import annotations

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import offered_catalog


def test_offered_catalog_keeps_the_selected_tools_in_selection_order():
    catalog = {'state.query': {'d': 1}, 'source.read': {'d': 2}, 'blast.run': {'d': 3}}
    assert offered_catalog(catalog) == catalog
    assert list(offered_catalog(catalog, ['source.read', 'state.query'])) == ['source.read', 'state.query']
    with pytest.raises(ContractError, match='offered_tool_not_in_catalog'):
        offered_catalog(catalog, ['missing.tool'])
    with pytest.raises(ContractError, match='offered_catalog_selection_must_be_a_list'):
        offered_catalog(catalog, 'state.query')
