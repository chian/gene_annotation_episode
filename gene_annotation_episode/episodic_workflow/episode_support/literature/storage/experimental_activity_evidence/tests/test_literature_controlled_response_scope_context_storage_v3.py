"""Actual constructed scope states survive exact native typed custody."""
from copy import deepcopy as cp
from dataclasses import replace
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError
from .unit_world import in_unit
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence import literature_controlled_response_storage as storage
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence import literature_controlled_response_render as render
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.tests.test_literature_controlled_response_storage_v3 import native_case
from gene_annotation_episode.episodic_workflow.episode_support.literature.rendering.experimental_activity_evidence.tests.test_literature_controlled_response_render_v3 import text_for
FIELDS = ('normalization', 'calibration', 'revision', 'covariance_scope', 'model_scope')

@pytest.mark.parametrize('state', ['same', 'explicit_compatible', 'not_applicable', 'unknown', 'conflicting'])
@in_unit
def test_all_scope_relationship_states_preserve_original_witness_associations(store, ctx, state):

    def modify(f):
        for name in FIELDS:
            witnesses = [] if state == 'unknown' else [f.witness('nmol/min')]
            if state == 'conflicting':
                witnesses.append(f.witness('Physical A.'))
            f.args['joint_scopes'][1][name] = {'value': state, 'witnesses': witnesses}
    store, context, args, _ = native_case(store, ctx, companion=True, joints=True, modify=modify)
    repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
    outcome = repo.populate_v3(context, args, 'scope-states')
    saved = repo.read(outcome['result']['sheet_ref'])
    row = next((r for r in outcome['result']['cells'] if r['component_key'] == 'joint:1:controlled_response_difference'))
    scope = row['joint_scope_context']
    actual = saved['extraction']['joint_scope_extractions'][1]
    assert scope['reading_assignment'] == row['reading_assignment'] == args['joint_reading_assignments'][1]['assignment']
    assert scope['effective_admissibility'] == actual['effective_admissibility']
    for name in FIELDS:
        assert scope[name]['selected_value'] == scope[name]['effective_value'] == state
        selected = args['joint_scopes'][1][name]['witnesses']
        assert len(scope[name]['witnesses']) == len(selected)
        for projected, original in zip(scope[name]['witnesses'], selected):
            retained = saved['scope_witness_bindings'][projected['witness_ref']]['witness']
            assert retained['selection'] == original
            assert projected['authentication'] == retained['authentication']
            assert store.get(projected['witness_ref'])['label'] == ' '.join(original['quote'].split())
    assert scope['effective_model'] == actual['effective_model']
    assert scope['covariance_context']['source_model'] == actual['source_covariance']['source_model']
    assert scope['requested_model']['model_kind']['selected_value'] == actual['requested_model']['model_kind']['selection']['value']
    if state in ('unknown', 'conflicting'):
        assert row['cell']['value'] is None
        assert row['cell']['unavailable_reason'] == [state + '_joint_applicability']
    assert all((r['joint_scope_context'] is None for r in outcome['result']['cells'] if r['kind'].startswith('local') or r['kind'] == 'native_raw'))

@in_unit
def test_unauthenticated_source_witness_gets_generic_actual_record_and_unknown_effective_state(store, ctx):
    store, context, args, _ = native_case(store, ctx, companion=True, joints=True)
    artifact = store.artifact(b'Available original; no selected text representation.')
    source_ref = store.put('source', {'provider': 'constructed_missing_representation', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': [args['source_ref']]}, origin='caller')['id']
    nomination = {'kind': 'text', 'source_ref': source_ref, 'representation': 'text', 'start': 0, 'end': 16, 'quote': 'UNVERIFIED QUOTE'}
    args['joint_scopes'][1]['model_kind'] = {'value': 'known_joint_normal_source_means', 'witnesses': [nomination]}
    context = replace(context, received_record_refs=(*context.received_record_refs, source_ref))
    repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
    outcome = repo.populate_v3(context, args, 'missing-witness')
    ref = outcome['result']['sheet_ref']
    saved = repo.read(ref)
    row = next((r for r in outcome['result']['cells'] if r['component_key'] == 'joint:1:controlled_response_difference'))
    request = row['joint_scope_context']['requested_model']['model_kind']
    assert request['selected_value'] == 'known_joint_normal_source_means' and request['effective_value'] == 'unknown'
    witness = request['witnesses'][0]
    assert witness['authentication'] == 'unavailable'
    record = store.get(witness['witness_ref'])
    assert record['label'] == 'Source witness unavailable' and record['anchor'] is None
    assert saved['scope_witness_bindings'][witness['witness_ref']]['witness']['selection'] == nomination
    bindings = repo.semantic_bindings([row])
    records = {r: store.get(r) for r in repo.cell_record_refs([row])}
    text = text_for([row], records, bindings)
    assert 'UNVERIFIED' not in text and 'source witness unavailable' in text
    assert row['context']['model_kind'] == 'none'
