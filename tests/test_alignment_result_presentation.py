"""Typed numerical returns rendered through the real provider presentation."""
import asyncio
from copy import deepcopy

from gene_annotation_episode.episodic_workflow.root.library.alignment_result_presentation import alignment_report_presentation
from gene_annotation_episode.episodic_workflow.root.library.bvbrc_alignment_bundle_contracts import encode_reference
from gene_annotation_episode.episodic_workflow.root.decision_context import state_frame
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


