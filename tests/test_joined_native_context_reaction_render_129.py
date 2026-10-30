"""Constructed joined126/129 display rows; no primary scientific evidence."""
import asyncio

from gene_annotation_episode.literature_experimental_prompt import _received_returns, _source_result
from test_literature_reaction_native_integration_129 import setup_case, binding_for


def context_row():
    return {'sheet_ref': 'source_constructed_context_sheet', 'evidence_source_ref': 'source_constructed_context',
        'data_source_ref': 'source_constructed_selection', 'context_ref': 'context_constructed',
        'setting_ref': 'context_constructed_setting', 'requirement_ref': 'reference_constructed_requirement',
        'measurement_ref': 'reference_constructed_measurement', 'basis_ref': None, 'sample_unit_ref': None,
        'cluster_ref': None, 'observation_position': 0, 'unit': 'mM', 'lower': 2., 'upper': 2.,
        'lower_closed': True, 'upper_closed': True, 'reported_relation': 'point', 'reported_sd': None,
        'reported_sem': None, 'reported_plusminus': None, 'reported_count': None, 'count_relation': 'unknown',
        'replicate_kind': 'unknown', 'value_basis': 'source_reported_setting', 'origin': 'synthetic',
        'scope_match': 'matched', 'pairing': 'unknown', 'context_kind': 'growth_condition',
        'bound_kind': 'reported_point_not_operating_domain'}


def test_joined_own_outcomes_and_typed_native_returns_keep_family_meanings(tmp_path):
    store, context, args = setup_case(tmp_path / 'state')
    with store:
        outcome = asyncio.run(binding_for(store, context).execute(context, 'literature.reaction.populate', args, 'joined'))
        assert outcome['status'] == 'completed', outcome
        reaction = [{'sheet_ref': outcome['result']['sheet_ref'], **row} for row in outcome['result']['native_observations']]
        biological_context = [context_row()]
        records = {'context_constructed': {'name': 'Constructed culture'},
            'context_constructed_setting': {'name': 'Defined culture medium'},
            'reference_constructed_requirement': {'label': 'External substrate availability'}}
        for rows, own_heading, other_heading in [
                (reaction, 'Requested native reaction observations', 'Native context observations'),
                (biological_context, 'Native context observations', 'Requested native reaction observations')]:
            parts = []
            _source_result(parts, {'result': {'native_observations': rows}}, 'Own selected action', controlled_records=records)
            text = '\n'.join(parts)
            assert text.count(own_heading) == 1 and other_heading not in text
        parts = []
        _received_returns(parts, [{'context_values': biological_context}, {'reaction_values': reaction}], records=records)
        text = '\n'.join(parts)
        assert text.count('Native context observations') == 1
        assert text.count('Requested native reaction observations') == 1
        assert 'source-reported nominal setting' in text and 'technical_repeat' in text
        assert 'reported_point' in text and 'sample_sd' in text
        for rows in ([], [{'unrecognized_native_family': True}]):
            parts = []
            _source_result(parts, {'result': {'native_observations': rows}}, 'Unknown or empty family', controlled_records=records)
            assert 'Native context observations' not in '\n'.join(parts)
            assert 'Requested native reaction observations' not in '\n'.join(parts)
