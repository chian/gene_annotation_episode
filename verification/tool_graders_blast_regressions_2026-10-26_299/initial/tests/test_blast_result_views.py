"""Native HSP custody and closed scoped reads; no provider requests."""
from copy import deepcopy
from dataclasses import replace
import asyncio
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.blast_result_views import read_blast_hsp, blast_hsp_facts
from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def snapshot(content, request):
    return SourceSnapshot('ncbi_blast', 'https://example.invalid/offline-blast', request,
        '2026-10-23T00:00:00+00:00', content, 'application/json', {'status': 200})


def published(tmp_path, *, alignment=True):
    store = Store(tmp_path/'store')
    target, = store.create_problem(raw_sequence='TTACGTAGGGGG', molecule='dna')['subject_refs']
    tools = ToolRegistry(store)
    request = {'subject_ref': target, 'program': 'blastn', 'database': 'nt'}
    service = NCBIBlastService(tools)
    native = {'query_from': 3, 'query_to': 9, 'hit_from': 11, 'hit_to': 5,
        'query_strand': 'Plus', 'hit_strand': 'Minus', 'bit_score': 0., 'score': 12.,
        'evalue': 0., 'identity': 6, 'align_len': 8}
    if alignment:
        native.update(qseq='ACG-TAGG', hseq='ACGT-AGG', midline='|||  |||')
    body = {'BlastOutput2': [{'report': {'program': 'blastn', 'results': {'search': {
        'query_title': target, 'query_len': 12, 'hits': [{'len': 18,
            'description': [{'accession': 'NATIVE.1', 'title': 'Original native reference'}], 'hsps': [native]}]}}}}]}
    original = snapshot(b'RID = ORIGINAL_RID\nRTOE = 0\n', {'action': 'submit'})
    result = service.publish(request, {}, snapshot(json.dumps(body).encode(), {}),
        store.validate_scope(None), 'original-publication', submission_snapshot=original,
        handle={'rid': 'ORIGINAL_RID', 'rtoe_seconds': 0})
    assert result['status'] == 'completed', result
    observation = result['result']['records'][0]['observation_ref']
    return store, tools, target, observation, result


def test_bounded_native_alignment_preserves_scores_gaps_reverse_coordinates_and_custody(tmp_path):
    store, tools, target, observation, result = published(tmp_path)
    with store:
        before = store.count('observation'), store.count('source')
        scope = store.validate_scope(None)
        window = read_blast_hsp(store, observation, 2, 4, permitted_inputs=[observation], scope=scope)
        assert window['alignment'] == {'column_offset': 2, 'column_end': 6, 'total_columns': 8,
            'query': 'G-TA', 'reference': 'GT-A', 'midline': '|  |', 'next_column_offset': 6}
        values = {row['name']: row['value']['value'] for row in window['measurements'] if row['value']['type'] == 'number'}
        assert values['bitscore'] == values['evalue'] == 0.
        assert values['alignment_score'] == 12. and values['identity_fraction'] == .75
        assert window['native_blast']['hit_from'] == 11 and window['native_blast']['hit_to'] == 5
        assert window['operand_intervals'][0]['start'] == 2 and window['operand_intervals'][1]['start'] == 4
        assert not window['full_reference_sequence_available']
        assert (store.count('observation'), store.count('source')) == before
        source = store.get(window['source_ref'])
        native = json.loads(store.get_artifact(source['artifact_ref']))
        assert native['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]['qseq'] == 'ACG-TAGG'


def test_unreceived_hsp_and_cached_tool_reply_cannot_bypass_host_permission(tmp_path):
    store, tools, _, observation, _ = published(tmp_path)
    with store:
        args = {'observation_ref': observation, 'column_offset': 0, 'column_limit': 3}
        allowed = tools.execute('result.blast.hsp', args, operation_key='read', permitted_record_refs=[observation])
        assert allowed['status'] == 'completed'
        assert allowed['record_refs'] == []
        assert tools.execute('result.blast.hsp', args, operation_key='read', permitted_record_refs=[observation]) == allowed
        refused = tools.execute('result.blast.hsp', args, operation_key='read', permitted_record_refs=[])
        assert refused['status'] == 'invalid' and refused['result'] is None
        assert refused['feedback']['code'] == 'blast_hsp_input_not_received'
        unbound = tools.execute('result.blast.hsp', args, operation_key='read')
        assert unbound['status'] == 'invalid' and unbound['result'] is None
        assert unbound['feedback']['code'] == 'blast_hsp_inputs_not_bound'


def test_scope_and_native_record_integrity_are_required_even_with_received_reference(tmp_path):
    store, _, target, observation, _ = published(tmp_path)
    with store:
        restricted = {'subject_refs': [target], 'segments': [{'target_ref': target, 'start': 0, 'end': 2, 'unit': 'nt'}]}
        with pytest.raises(ContractError, match='outside_assigned_scope'):
            read_blast_hsp(store, observation, 0, 2, permitted_inputs=[observation], scope=restricted)
        stored = store.get(observation)
        stored['native_blast']['hit_from'] = 12
        store.db.execute('UPDATE records SET data=? WHERE id=?', (json.dumps(stored), observation))
        with pytest.raises(ContractError, match='record_identity_conflict'):
            read_blast_hsp(store, observation, 0, 2, permitted_inputs=[observation], scope=None)


def test_missing_alignment_stays_unknown_while_actual_scores_remain_available(tmp_path):
    store, _, _, observation, _ = published(tmp_path, alignment=False)
    with store:
        result = read_blast_hsp(store, observation, 0, 8, permitted_inputs=[observation], scope=None)
        assert not result['alignment_available'] and result['alignment'] is None
        assert result['alignment_unavailable_reason'] == 'native_alignment_not_reported'
        assert len(result['measurements']) > 1
        for offset, limit in ((-1, 1), (0, 0), (0, 4097), (True, 1)):
            with pytest.raises(ContractError, match='bounded_blast_alignment_window_required'):
                read_blast_hsp(store, observation, offset, limit, permitted_inputs=[observation], scope=None)


def test_recorded_hsp_facts_fill_closed_parent_form_and_service_port_preserves_host_inputs(tmp_path):
    from gene_annotation_episode.blast_result_views import BLAST_HSP_FACT_SCHEMA
    store, tools, target, observation, acquired = published(tmp_path)
    with store:
        facts = blast_hsp_facts(store, acquired['record_refs'])
        assert len(facts) == 1 and facts[0]['hsp_ref'] == observation
        assert facts[0]['target_coverage'] == 7/18  # Native reference/hit coverage.
        form = {'type': 'object', 'additionalProperties': False, 'required': ['matches'],
            'properties': {'matches': {**deepcopy(BLAST_HSP_FACT_SCHEMA), 'x-source': 'execution_blast_hsps'}}}
        returned = form_with_facts({}, form, {'execution_blast_hsps': facts})
        validate_form(returned, form, lambda ref, ns: ref in acquired['record_refs'] and ns == 'execution_result')
        source_refs = [observation]
        context = BindingContext('run', 'child', 'scientific_process', (('scientific_process', 'child'),),
            {'subject_refs': [target]}, {}, {}, source_refs)
        source_refs.clear()
        assert context.received_record_refs == (observation,)
        assert 'received_record_refs' not in context.as_record()  # Host-only authorization.
        services = WorkflowServices(SimpleNamespace(tools=tools))
        read = asyncio.run(services.execute_tool('result.blast.hsp',
            {'observation_ref': observation, 'column_offset': 0, 'column_limit': 2},
            scope=context.scope, operation_key='service-read', permitted_record_refs=context.received_record_refs))
        assert read['status'] == 'completed' and read['result']['alignment']['query'] == 'AC'
