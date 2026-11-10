"""Actual presentation transport preserves reusable operands and per-use needs.

The controlled wire validates delivery and reconstruction, not model decisions.
"""
import asyncio
from copy import deepcopy

from gene_annotation_episode.domain import obj
from gene_annotation_episode.composition_information import CONTRACT_ARGUMENT_TRANSPORT, CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.episode_contract_information import operation_contract_information
from gene_annotation_episode.literature_reaction_storage import reaction_semantic_cells_schema
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot


def state():
    value = snapshot()
    value['goal']['objective'] = 'Inspect the reported chemical ratio; target application is separate.'
    value['contract_information_profile'] = CONTRACT_INFORMATION_PROFILE
    value['literature_assignment'] = {'version': 'literature_assignment_v1',
        'source_refs': ['source_selected'], 'question_context_refs': [],
        'requested_reaction_components': ['ratio_mean']}
    value['requested_form'] = obj({'components': reaction_semantic_cells_schema()})
    value['component_axis_source_access'] = {
        'version': 'component_axis_source_access_v1',
        'own_source_inspection': {'version': 'component_axis_source_inspection_v1',
            'read_sources': [{'source_ref': 'source_selected', 'artifact_ref': 'artifact_selected',
                'inspected_ranges': [{'start': 0, 'end': 100}], 'decision_indices': [0]}],
            'located_passages': [{'source_ref': 'source_selected', 'decision_indices': [1],
                'matches': [{'artifact_ref': 'artifact_selected', 'witness': {
                    'source_ref': 'source_selected', 'start': 40, 'end': 49,
                    'quote': 'ratio=1:1'}}]}],
            'credit_change': False, 'permission_change': False}}
    value['component_axis_scoring_sheets'] = {'A110': {
        'numerical_results': [{'sheet_ref': 'source_original_sheet',
            'assessment_state': 'current', 'experimental_bindings': {'molecule_ref': None},
            'components': {'ratio_mean': {'component': 'ratio_mean', 'status': 'populated',
                'value': 1.0, 'unit': 'mol_per_mol', 'conditional_on': ['reported_ratio_scale']}}}],
        'tool_qualifications': [{
            'source_ref': 'source_use_region_20_40', 'target_regions': [{'start': 20, 'end': 40}],
            'current': True, 'result': {'state': 'per_use_application_unresolved',
                'selected_components': ['ratio_mean'], 'missing': ['actual_assayed_molecule_identity']}},
            {'source_ref': 'source_use_region_40_60', 'target_regions': [{'start': 40, 'end': 60}],
             'current': True, 'result': {'state': 'per_use_application_unresolved',
                'selected_components': ['ratio_mean'], 'missing': ['particular_residue_map']}}]}}
    return value


def test_exact_witness_and_received_use_needs_survive_delta_and_cold_wire(tmp_path):
    first = state()
    second = deepcopy(first)
    second['last_local_outcome'] = {'status': 'completed', 'result': {'text': 'An unrelated later read.'}}
    second['component_axis_scoring_sheets']['A110']['tool_qualifications'][0].update(
        current=False, changed_received_operand_refs=['assessment_revised_operand'])
    before = deepcopy((first, second))
    wire, cold = LiteratureWire(tmp_path / 'wire'), LiteratureWire(tmp_path / 'cold')

    async def exercise():
        await complete(wire, state_frame(first))
        await complete(wire, state_frame(second, first))
        await complete(cold, state_frame(second))
    asyncio.run(exercise())
    for turn in (*wire.turns_sent(), *cold.turns_sent()):
        text = turn['input'][0]['text']
        assert 'Recorded source inspections and access' in text
        assert 'ratio=1:1' in text and 'inspected_ranges' in text
        assert 'source_original_sheet' in text and '"value": 1.0' in text
        assert 'actual_assayed_molecule_identity' in text
        assert 'particular_residue_map' in text
        assert 'source_use_region_20_40' in text and 'source_use_region_40_60' in text
        assert '"start": 20' in text and '"end": 60' in text
        assert 'permission_change' in text and 'credit_change' in text
    assert (first, second) == before
    assert 'assessment_revised_operand' in wire.turns_sent()[-1]['input'][0]['text']
    assert '"current": false' in wire.turns_sent()[-1]['input'][0]['text']


def test_other_operations_remain_named_and_exact_contract_lookup_still_delivers(tmp_path):
    current = state()
    unrelated = {'name': 'literature.binding.populate',
        'description': 'UNRELATED_FULL_BINDING_MEANING', 'input_schema': obj({
            'selected_curve': {'type': 'string', 'description': 'EXACT_BINDING_OPERAND'}})}
    current['tools'].extend([{**unrelated, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT},
        {'name': 'literature.reaction.source.populate', 'description': 'RELEVANT_RATIO_OPERATION',
         'input_schema': obj({}), 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT}])
    before = deepcopy(current)
    information = operation_contract_information(catalog=[unrelated], operation=unrelated['name'])
    wire = LiteratureWire(tmp_path / 'wire')

    async def exercise():
        await complete(wire, state_frame(current))
        await complete(wire, {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
            'decision_index': 1, 'exchange_index': 1, 'result': information,
            'pending_contract_information': [information]})
    asyncio.run(exercise())
    initial, looked_up = [turn['input'][0]['text'] for turn in wire.turns_sent()]
    assert 'literature.binding.populate' in initial and 'RELEVANT_RATIO_OPERATION' in initial
    assert 'UNRELATED_FULL_BINDING_MEANING' not in initial
    assert 'UNRELATED_FULL_BINDING_MEANING' in looked_up and 'EXACT_BINDING_OPERAND' in looked_up
    assert current == before
