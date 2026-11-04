"""Typed numerical returns rendered through the real provider presentation."""
import asyncio
from copy import deepcopy

from gene_annotation_episode.alignment_result_presentation import alignment_report_presentation
from gene_annotation_episode.bvbrc_alignment_bundle_contracts import encode_reference
from gene_annotation_episode.decision_context import state_frame
from test_scientific_process_prompt_delivery import ScientificWire, complete, snapshot, OUTPUT_SCHEMA


SOURCE = 'source_' + 'a' * 24
ARTIFACT = 'artifact_' + 'b' * 64


def report(source=SOURCE, value=6 / 28):
    ref = lambda kind, name: encode_reference(kind,
        '@requirements' if kind in {'reason', 'requirement'} else 'analysis', name)
    return {'completed': True, 'references': ['source_needed_for_another_action', source],
        'numbers': [{'source_ref': source, 'field': ref('field', 'gap_fraction'), 'value': {
            'value': value, 'unit': 'fraction', 'state': 'available', 'origin': 'derived',
            'numerator': 6, 'denominator': 28, 'population_ref': ref('population', 'whole'),
            'method_ref': ref('method', 'gap_cell_fraction'), 'requirement_refs': []}}],
        'sites': [{'source_ref': source, 'field': ref('field', 'sites'), 'value': [{
            'alignment_ref': ref('alignment', ARTIFACT + '#alignment'),
            'column_0based': 1, 'literal_entropy_bits': 0.9182958340544896,
            'strict_majority_consensus': 'A', 'native_score_recalculated': 92.0}]}],
        'missing': [{'source_ref': source, 'field': ref('field', 'missing'), 'value': [{
            'kind': 'scientific_metadata',
            'reason_ref': ref('reason', 'alignment_deployed_version_unproven'),
            'source_refs': []}]}]}


def test_exact_numbers_qualifications_and_unrelated_operands_survive():
    original = report()
    before = deepcopy(original)
    projected = alignment_report_presentation(original)
    row = projected['numbers'][0]
    assert row['selected_field'] == 'gap_fraction' and row['analysis'] == 'analysis'
    assert row['value'] == {'value': 6 / 28, 'unit': 'fraction', 'state': 'available',
        'origin': 'derived', 'numerator': 6, 'denominator': 28,
        'population': 'analysis / whole', 'method': 'analysis / gap_cell_fraction', 'requirements': []}
    assert projected['references'] == ['source_needed_for_another_action']
    assert projected['sites'][0]['value'][0] == {'alignment': 'alignment 1',
        'column_0based': 1, 'literal_entropy_bits': 0.9182958340544896,
        'strict_majority_consensus': 'A', 'native_score_recalculated': 92.0}
    assert projected['missing'][0]['value'][0]['reason'] == 'alignment_deployed_version_unproven'
    assert SOURCE not in str(projected) and ARTIFACT not in str(projected)
    assert original == before


def test_distinct_publications_and_distinct_alignments_are_not_merged():
    first, second = report(), report('source_' + 'c' * 24, 0)
    second['sites'][0]['value'][0]['alignment_ref'] = encode_reference(
        'alignment', 'analysis', 'artifact_' + 'd' * 64 + '#alignment')
    original = {key: first[key] + second[key] if isinstance(first[key], list) else first[key]
        for key in first}
    projected = alignment_report_presentation(original)
    assert [row['result'] for row in projected['numbers']] == ['result 1', 'result 2']
    assert [row['value']['value'] for row in projected['numbers']] == [6 / 28, 0]
    assert [row['value'][0]['alignment'] for row in projected['sites']] == ['alignment 1', 'alignment 2']
    assert projected['references'] == ['source_needed_for_another_action'] * 2


def test_missing_and_other_provider_fields_are_not_reinterpreted():
    original = report(value=None)
    original['numbers'][0]['value'].update(state='missing', numerator=None, denominator=None)
    original['other'] = [{'source_ref': SOURCE, 'field': 'another_provider_field:chosen', 'value': 0}]
    projected = alignment_report_presentation(original)
    assert projected['numbers'][0]['value']['value'] is None
    assert projected['numbers'][0]['value']['state'] == 'missing'
    assert projected['other'] == original['other']
    standalone = {'references': [SOURCE], 'other': original['other']}
    assert alignment_report_presentation(standalone) == standalone


def test_actual_provider_update_omits_source_envelope_and_preserves_full_task(tmp_path):
    wire = ScientificWire(tmp_path / 'wire')
    initial = snapshot()
    updated = deepcopy(initial)
    updated['child_reports'] = [report()]
    updated['working_state']['sources'].append({'id': SOURCE, 'artifact_ref': ARTIFACT,
        'accession': 'PRIVATE_BUNDLE_ACCESSION', 'request_ref': 'PRIVATE_REQUEST_HASH',
        'provider': 'episode.bvbrc_appservice_bundle_data', 'version': 'PRIVATE_STORAGE_VERSION'})
    original = deepcopy(updated)

    async def exercise():
        await complete(wire, state_frame(initial))
        await complete(wire, state_frame(updated, initial))
        await complete(wire, {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
            'result': {'status': 'completed', 'text': 'The same decision continues.'}})
    asyncio.run(exercise())
    turns = wire.turns_sent()
    task = turns[0]['input'][0]['text'].split('\n\nSTEERING\n')[0]
    for turn in turns[1:]:
        text = turn['input'][0]['text']
        assert text.split('\n\nSTEERING\n')[0] == task
        for forbidden in (SOURCE, ARTIFACT, 'PRIVATE_BUNDLE_ACCESSION', 'PRIVATE_REQUEST_HASH', 'PRIVATE_STORAGE_VERSION'):
            assert forbidden not in text
        for needed in ('gap_fraction', 'fraction', 'analysis / whole', '0.9182958340544896',
                '92.0', 'alignment_deployed_version_unproven', 'source_needed_for_another_action'):
            assert needed in text
        assert turn['outputSchema'] == OUTPUT_SCHEMA
    assert updated == original
    assert wire.scientific_prompt_states[('episode', 'REASONING')] == original


def test_genome_alignment_native_fact_presentation_preserves_selected_measurements():
    from gene_annotation_episode.bvbrc_genome_alignment_bundle_adapter import consume_bundle
    from gene_annotation_episode.bvbrc_genome_alignment_bundle_contracts import encode_reference as genome_ref
    from test_bvbrc_genome_alignment_bundle_resolution import arguments, measurement
    args = arguments(fields={'coverage': measurement(field='coverage_fraction')})
    result = consume_bundle(**args)
    original = {'references': [SOURCE], 'numbers': [{'source_ref': SOURCE,
        'field': genome_ref('field', args['parameters']['analysis_id'], 'coverage'),
        'value': result['facts']['coverage']}]}
    before = deepcopy(original)
    projected = alignment_report_presentation(original)
    row = projected['numbers'][0]
    assert row['selected_field'] == 'coverage'
    assert row['value']['state'] == 'resolved'
    cell = row['value']['value']
    assert cell['state'] == 'available'
    assert cell['value'] == 690 / 693
    assert cell['numerator'] == 690 and cell['denominator'] == 693
    assert cell['unit'] == 'fraction' and cell['origin'] == 'calculated'
    assert 'method' in cell and 'population' in cell
    assert SOURCE not in str(projected) and 'bvbrc_genome_alignment_' not in str(projected)
    assert original == before
