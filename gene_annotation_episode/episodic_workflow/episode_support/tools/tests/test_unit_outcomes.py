"""Offered catalogs and failed-unit outcomes over a real Store."""
from __future__ import annotations

import json

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.tools.unit_outcomes import failure_outcome, offered_catalog
from gene_annotation_episode.state import Store


def test_offered_catalog_keeps_the_selected_tools_in_selection_order():
    catalog = {'state.query': {'d': 1}, 'source.read': {'d': 2}, 'blast.run': {'d': 3}}
    assert offered_catalog(catalog) == catalog
    assert list(offered_catalog(catalog, ['source.read', 'state.query'])) == ['source.read', 'state.query']
    with pytest.raises(ContractError, match='offered_tool_not_in_catalog'):
        offered_catalog(catalog, ['missing.tool'])
    with pytest.raises(ContractError, match='offered_catalog_selection_must_be_a_list'):
        offered_catalog(catalog, 'state.query')


def test_failure_outcome_archives_the_handled_traceback(tmp_path):
    with Store(tmp_path / 'state') as store:
        try:
            raise ContractError('provider_unreachable')
        except ContractError as error:
            outcome = failure_outcome(store, error, category='episode_execution', cause_code='selected_operation_failed')
        assert outcome['status'] == 'failed' and outcome['record_refs'] == [] == outcome['changed_record_refs']
        feedback = outcome['feedback']
        assert feedback['code'] == 'provider_unreachable' and feedback['exception_type'] == 'ContractError'
        diagnostic = json.loads(store.get_artifact(feedback['diagnostic_ref']))
        assert diagnostic['exception_type'] == 'ContractError' and 'provider_unreachable' in diagnostic['traceback']
        with pytest.raises(ContractError, match='failure_outcome_category_required'):
            failure_outcome(store, ContractError('x'), category='', cause_code='x')
