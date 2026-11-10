"""Constructed native reaction display rows; no primary scientific evidence."""
import asyncio

from gene_annotation_episode.literature_experimental_prompt import _received_returns, _source_result
from test_literature_reaction_native_integration_129 import setup_case, binding_for


def test_own_outcomes_and_typed_native_returns_keep_reaction_meanings(tmp_path):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        outcome = asyncio.run(binding_for(store, context).execute(context, 'literature.reaction.populate', args, 'joined'))
        assert outcome['status'] == 'completed', outcome
        reaction = [{'sheet_ref': outcome['result']['sheet_ref'], **row} for row in outcome['result']['native_observations']]
        parts = []
        _source_result(parts, {'result': {'native_observations': reaction}}, 'Own selected action')
        assert '\n'.join(parts).count('Requested native reaction observations') == 1
        parts = []
        _received_returns(parts, [{'reaction_values': reaction}])
        text = '\n'.join(parts)
        assert text.count('Requested native reaction observations') == 1
        assert 'technical_repeat' in text
        assert 'reported_point' in text and 'sample_sd' in text
        for rows in ([], [{'unrecognized_native_family': True}]):
            parts = []
            _source_result(parts, {'result': {'native_observations': rows}}, 'Unknown or empty family')
            assert 'Requested native reaction observations' not in '\n'.join(parts)
