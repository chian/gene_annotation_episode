"""Constructed received facts: semantic links, bounded values and possession."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import _steering, render_literature_experimental_prompt
from gene_annotation_episode.literature_received_fact_render import ReceivedFactDisplay
from test_literature_experimental_prompt_delivery import LiteratureWire, complete, snapshot
from test_literature_rate_source_semantic_prompt import constructed_rows, state_with_rows


QUOTE = 'Enzyme X variant: activity <0.2 U/mg at pH 7.5; product was not identified.'


def constructed_facts():
    anchor = {'source_ref': 'source_constructed', 'artifact_ref': 'artifact_constructed',
              'start': 0, 'end': len(QUOTE.encode()), 'quote': QUOTE}
    rows = [
        {'id': 'reference_enzyme', 'record_type': 'reference', 'reference_type': 'construct',
         'label': 'enzyme X variant', 'accession': 'source_entity_' + 'a' * 24,
         'source_ref': 'source_constructed', 'anchor': anchor, 'origin': 'extracted'},
        {'id': 'term_unit', 'record_type': 'term', 'label': 'U/mg', 'term_type': 'unit',
         'namespace': 'source_local', 'accession': 'source_term_' + 'b' * 24,
         'source_ref': 'source_constructed', 'anchor': anchor, 'origin': 'extracted'},
        {'id': 'term_reaction', 'record_type': 'term', 'label': 'reaction R', 'term_type': 'reaction',
         'namespace': 'RHEA', 'accession': 'RHEA:12345', 'anchor': None},
        {'id': 'context_assay', 'record_type': 'context', 'context_type': 'assay_condition',
         'name': 'pH 7.5; 50 mM buffer', 'related_refs': ['reference_enzyme'],
         'attributes': [{'name': 'ph', 'value': {'type': 'number', 'value': 7.5, 'unit_ref': None}}],
         'anchor': anchor},
        {'id': 'observation_activity', 'record_type': 'observation', 'kind': 'biochemical_assay',
         'subject_refs': ['reference_enzyme'], 'source_subject_refs': ['reference_enzyme'],
         'measurements': [{'name': 'activity', 'value': {'type': 'number', 'value': 0.2,
            'bound': 'less_than', 'qualifier': 'approximate', 'unit_ref': 'term_unit',
            'uncertainty': {'representation': 'plus_minus', 'magnitude': 0.03, 'statistic': 'unspecified'}}},
            {'name': 'assay_outcome', 'value': {'type': 'enum', 'value': 'not_measured'}}],
         'dependencies': ['context_assay'], 'anchor': anchor, 'origin': 'extracted'},
        {'id': 'hypothesis_function', 'record_type': 'hypothesis', 'subject_refs': ['reference_enzyme'],
         'predicate': 'catalyzes', 'value': {'type': 'term_ref', 'ref': 'term_reaction'},
         'context_refs': ['context_assay'], 'origin': 'reasoning'},
        {'id': 'assessment_qualification', 'record_type': 'assessment',
         'hypothesis_ref': 'hypothesis_function', 'observation_ref': 'observation_activity',
         'relation': 'weakens', 'applicability': 'direct', 'extent_basis': 'observed_extent',
         'condition_refs': ['context_assay'], 'assumption_refs': [], 'revision': 3,
         'investigation_finding': {'source_claim': {'subject_refs': ['reference_enzyme'],
            'predicate': 'catalyzes', 'value': {'type': 'term_ref', 'ref': 'term_reaction'},
            'context_refs': ['context_assay']}, 'qualification': {'kind': 'measurement_does_not_establish_claim',
            'context_refs': ['context_assay'], 'assumption_refs': []},
            'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
            'same_source_claim_as_ref': None, 'replaces_refs': []}, 'origin': 'reasoning'},
    ]
    return {row['id']: row for row in rows}


def received_state():
    state = snapshot()
    state['literature_received_fact_display'] = {'records': constructed_facts()}
    # The relevant data deliberately falls outside this generic page.
    state['working_state']['references'] = [{'id': 'reference_private', 'record_type': 'reference',
        'label': 'PRIVATE_UNRECEIVED_GLOBAL_ROW'}] * 24
    state['child_reports'] = [{'changed_assessment_refs': ['assessment_qualification'],
        'interpretation_basis_refs': ['observation_activity'],
        'unresolved_hypothesis_refs': ['hypothesis_function']}]
    state['working_state']['received_revision_status'] = [
        {'record_ref': 'assessment_qualification', 'is_current_revision': False}]
    return state


def test_same_received_scientific_facts_are_compact_linked_qualified_and_pure():
    state = received_state();before = deepcopy(state)
    text = _steering(state, ())
    for meaning in ('enzyme X variant', 'pH 7.5; 50 mM buffer', '≈<0.2 ± 0.03 (statistic: unspecified)',
                    'not_measured', 'RHEA:12345', 'weakens', 'direct', 'observed_extent',
                    'measurement_does_not_establish_claim', 'retained',
                    'received revision state=stale', 'origin=reasoning'):
        assert meaning in text
    assert text.count(QUOTE) == 1
    assert '| [0].changed_assessment_refs | Assessment 1 |' in text
    assert '| [0].interpretation_basis_refs | Fact 1 |' in text
    assert len(text) < 5500
    for secret in (*constructed_facts(), 'source_constructed', 'artifact_constructed',
                   'source_entity_', 'source_term_', 'PRIVATE_UNRECEIVED_GLOBAL_ROW'):
        assert secret not in text
    assert 'do not establish independent experiments' in text
    assert state == before
    assert 'revision=3' not in text and 'received revision=3' not in text


def test_equal_valued_distinct_facts_and_equal_quotes_at_distinct_anchors_stay_distinct():
    state = received_state();records = state['literature_received_fact_display']['records']
    second = deepcopy(records['observation_activity']);second['id'] = 'observation_other'
    second['anchor']['start'] = 100;second['anchor']['end'] += 100
    records[second['id']] = second
    state['child_reports'][0]['interpretation_basis_refs'].append(second['id'])
    text = _steering(state, ())
    assert text.count('≈<0.2 ± 0.03 (statistic: unspecified)') == 2
    assert text.count(QUOTE) == 2
    assert 'Fact 1; Fact 2' in text


def test_source_identity_links_and_sequence_association_survive_without_source_or_sequence_reads():
    state = received_state();records = state['literature_received_fact_display']['records']
    records['reference_enzyme']['sequence_ref'] = 'artifact_sequence_private'
    other = deepcopy(records['reference_enzyme']);other['id'] = 'reference_other'
    other['label'] = 'second construct';other['source_ref'] = 'source_second'
    other['sequence_ref'] = None;other['anchor'] = None
    records[other['id']] = other
    state['current_report_basis_refs'] = ['reference_other']
    text = _steering(state, ())
    assert max(text.count('source identity=Source handle 1'), text.count('source identity=Source handle 2')) >= 2
    assert 'source identity=Source handle 1' in text and 'source identity=Source handle 2' in text
    assert 'sequence association=Sequence handle 1' in text
    assert 'sequence association=unknown' in text
    assert 'source_second' not in text and 'artifact_sequence_private' not in text


def test_missing_possession_does_not_reenter_through_global_page_and_unknown_meaning_is_explicit():
    state = received_state();removed = state['literature_received_fact_display']['records'].pop('term_reaction')
    state['working_state']['terms'] = [removed]
    text = _steering(state, ())
    assert 'meaning unavailable in this scoped display' in text
    assert 'reaction R' not in text and 'RHEA:12345' not in text
    assert 'term_reaction' not in text


def test_parent_chosen_typed_field_names_link_actual_possessed_records_without_name_heuristics():
    state = received_state()
    state['child_reports'] = [{'caller_selected_assessments':['assessment_qualification'],
        'caller_selected_basis':['observation_activity']}]
    text = _steering(state, ())
    assert 'enzyme X variant' in text and 'weakens' in text
    assert '| [0].caller_selected_assessments[0] | Assessment 1 |' in text
    assert '| [0].caller_selected_basis[0] | Fact 1 |' in text
    assert 'assessment_qualification' not in text and 'observation_activity' not in text


def test_hash_shaped_external_scientific_accessions_and_numeric_conditions_are_preserved():
    state = received_state();records=state['literature_received_fact_display']['records']
    records['reference_enzyme'].update(origin='external', accession='source_entity_'+'a'*24)
    records['term_reaction'].update(origin='tool', namespace='external_reaction_catalog',
        accession='external_identifier_'+'b'*24)
    text=_steering(state,())
    assert 'source_entity_'+'a'*24 in text
    assert 'external_identifier_'+'b'*24 in text
    assert 'pH 7.5; 50 mM buffer' in text and '≈<0.2 ± 0.03' in text
    # An arbitrary returned accession without a declared generation context
    # remains a scientific string even if it has a host-like shape.
    display=ReceivedFactDisplay([])
    arbitrary={'accession':'native_rate_subject_'+'c'*24}
    assert display.project(arbitrary)==arbitrary


@pytest.mark.parametrize('kind,namespace,accession',[
    ('reference',None,'source_assay_'+'a'*24),
    ('reference',None,'gel_scientific_meaning_'+'a'*24),
    ('reference',None,'binding_interaction_subject_'+'a'*24),
    ('term','literature_endpoint','native_rate_endpoint_'+'a'*24),
    ('term','literature_reaction_endpoint','reaction_literal_'+'a'*24),
])
def test_only_inspected_tool_generation_context_hides_host_accession(kind,namespace,accession):
    row={'id':kind+'_fixture','record_type':kind,'origin':'tool','label':'pH 7.5; 50 mM buffer',
        'accession':accession}
    if namespace is not None:row['namespace']=namespace
    display=ReceivedFactDisplay([row])
    assert accession not in display.render_records(table=lambda _,rows:str(list(rows)))
    row['origin']='external';display=ReceivedFactDisplay([row])
    assert accession in display.render_records(table=lambda _,rows:str(list(rows)))


def test_unrecognized_record_fields_remain_explicit_and_relational_roles_keep_direction():
    state = snapshot()
    state['working_state']['observations'] = [{'id': 'observation_novel', 'record_type': 'future_kind',
        'negative_result': False, 'extra': {'type': 'relation', 'roles': [
            {'role': 'donor', 'ref': 'reference_donor'}, {'role': 'acceptor', 'ref': 'reference_acceptor'}]}}]
    state['current_report_basis_refs'] = ['observation_novel']
    text = _steering(state, ())
    assert 'unrecognized record type=future_kind' in text and 'negative_result=false' in text
    assert 'donor=Unresolved link 1' in text and 'acceptor=Unresolved link 2' in text
    assert 'reference_donor' not in text and 'reference_acceptor' not in text


def test_native_masking_precedes_received_fact_render_and_preserves_unrelated_same_paper_fact():
    rows, meanings = constructed_rows()
    state = state_with_rows(rows, meanings)
    records = {**meanings, **constructed_facts()}
    for record in records.values():
        record['source_ref'] = rows[0]['evidence_source_ref']
    state['literature_received_fact_display'] = {'records': records}
    state['current_report_basis_refs'] = ['assessment_qualification']
    text = _steering(state, ())
    assert text.count('molecule Alpha') == 1
    assert 'measurement_does_not_establish_claim' in text and 'pH 7.5; 50 mM buffer' in text
    assert 'PRIVATE_ACCESSION' not in text
    assert '| Reference − test rate | 9 |' in text


def test_provider_bootstrap_delta_lookup_reconstruction_keep_task_and_typed_contract_exact(tmp_path):
    first = received_state();second = deepcopy(first)
    second['feedback'] = {'code': 'source_condition_unresolved'}
    wire = LiteratureWire(tmp_path / 'wire');restart = LiteratureWire(tmp_path / 'restart')
    lookup = {'version': 'decision_context_v1', 'kind': 'decision_lookup_result',
        'decision_index': 5, 'exchange_index': 1, 'result': {'status': 'completed',
        'result': {'record_refs': ['assessment_qualification']}}}
    async def exercise():
        await complete(wire, state_frame(first));await complete(wire, state_frame(second, first))
        await complete(wire, lookup);await complete(restart, state_frame(second))
    asyncio.run(exercise())
    tasks=[]
    for transport in (wire, restart):
        for turn in transport.turns_sent():
            task, steering = turn['input'][0]['text'].split('\n\nSTEERING\n')
            tasks.append(task)
            assert QUOTE in steering and 'RHEA:12345' in steering
            assert 'assessment_qualification' not in steering and 'PRIVATE_UNRECEIVED' not in steering
            assert turn['outputSchema']['properties']['fixture']['const'] is True
    assert all(task == tasks[0] for task in tasks)


def test_metadata_hook_checks_receipt_then_scope_before_record_access_and_omits_source_handles():
    facts=constructed_facts();accesses=[];checks=[]
    def allowed(reference, scope, namespace):
        checks.append(reference);return reference in facts and reference != 'context_assay'
    def read(reference):
        assert reference in checks
        accesses.append(reference);return facts[reference]
    services=SimpleNamespace(reference_in_scope=allowed, read_record=read)
    binding=LiteratureEpisodes(services, rate_population=True)
    context=BindingContext('fixture', 'episode', 'literature', (('literature','fixture'),),
        {'subject_refs':['input_fixture']}, {}, {}, ('reference_enzyme','source_private','artifact_private'))
    assert binding._received_fact_display_context(context)['literature_received_fact_display']['records'] == {
        'reference_enzyme': facts['reference_enzyme']}
    assert accesses == ['reference_enzyme']
    with pytest.raises(ContractError, match='literature_reference_unavailable'):
        binding._received_fact_display_context(replace(context, received_record_refs=('context_assay',)))
    assert 'context_assay' not in accesses
