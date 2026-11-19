"""Constructed Store/runtime-row fixtures, not model or primary-paper proof."""
from copy import deepcopy as cp
from dataclasses import replace
import json
import subprocess
import sys
import pytest
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.domain import ContractError, canonical, obj
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence.literature_context import LiteratureContext
from gene_annotation_episode.episodic_workflow.episode_support.records.experimental_activity_evidence.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.experimental_activity_evidence import literature_controlled_response_storage as storage
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.experimental_activity_evidence.tests.test_literature_controlled_response_v3_inputs import Fixture

def native_case(path, index=0, *, modify=None, **kwargs):
    fixture = Fixture(index, **kwargs)
    if modify:
        modify(fixture)
    store = Store(path)
    store.create_problem(raw_sequence='MKWAA', molecule='protein')
    sources = {}
    for ref in [fixture.main_ref, *[ref for ref in fixture.data if ref != fixture.main_ref]]:
        data = fixture.data[ref]
        artifact = store.artifact(data)
        sources[ref] = store.put('source', {'provider': 'constructed_controlled_fixture', 'accession': ref, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': [] if ref == fixture.main_ref else [sources[fixture.main_ref]]}, origin='caller')['id']

    def remap(value):
        if isinstance(value, dict):
            return {k: remap(v) for k, v in value.items()}
        if isinstance(value, list):
            return [remap(v) for v in value]
        return sources.get(value, value) if isinstance(value, str) else value
    args = remap(fixture.args)
    assignment = {'source_ref': args['source_ref'], 'requested_controlled_response_components': list(storage.COMPONENTS), 'requested_controlled_response_views': list(storage.VIEWS)}
    context = LiteratureContext('fixture-run', 'fixture-child', 'literature_page', (('literature', 'fixture-parent'), ('literature_page', 'fixture-child')), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), assignment, {}, tuple(sources.values()))
    return (store, context, args, fixture)

def owned(context, outcome):
    return replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))

@pytest.mark.parametrize('kwargs', [{}, {'index': 6}, {'companion': True, 'joints': True}, {'companion': True, 'authority': True, 'joints': True}])
def test_real_source_to_saved_projection_exact_keys_and_replay(tmp_path, monkeypatch, kwargs):
    store, context, args, _ = native_case(tmp_path, **kwargs)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, args, 'selected')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        rows = outcome['result']['cells']
        keys = outcome['result']['component_keys']
        assert len(keys) == len(set(keys))
        assert repo.project_cells([ref], permitted_record_refs=[ref], components=keys) == rows
        with pytest.raises(ContractError, match='original_runtime_required'):
            repo.fact_cells(owned(context, outcome), [ref], components=keys)
        assert all((r['context']['condition_control_applications']['condition0'] is None for r in rows if r['kind'] == 'native_raw'))
        if kwargs.get('companion') and (not kwargs.get('authority')):
            assert not any((r['kind'] == 'final' for r in rows))
            assert len([r for r in rows if r['kind'] == 'conditional']) == 24
            assert [r['reading_assignment'] for r in rows if r['component_key'] == 'joint:1:protein_condition1_response'][0]['protein_condition1'] == 'A-display'
        allowed = {store.get(ref)['artifact_ref'], store.get(ref)['request_ref']}
        get = store.get_artifact
        monkeypatch.setattr(store, 'get_artifact', lambda r: get(r) if r in allowed else pytest.fail('scientific source reacquisition'))
        monkeypatch.setattr(storage.source, 'read_controlled_response_v3_inputs', lambda *_a, **_k: pytest.fail('source reader rerun'))
        monkeypatch.setattr(storage.population, 'populate_controlled_response_v3', lambda *_a, **_k: pytest.fail('population rerun'))
        from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_controlled_response_local_calculations as local
        from gene_annotation_episode.episodic_workflow.episode_support.literature.calculations.experimental_activity_evidence import literature_controlled_response_owner_calculations as owner
        monkeypatch.setattr(local, 'populate_controlled_response_local', lambda *_a, **_k: pytest.fail('local calculator rerun'))
        monkeypatch.setattr(owner, 'populate_controlled_response_owner', lambda *_a, **_k: pytest.fail('whole calculator rerun'))
        before = store.db.total_changes
        assert repo.read(ref) == saved
        assert repo.populate_v3(context, args, 'selected') == outcome
        assert store.db.total_changes == before
        changed = cp(args)
        changed['local_pair_assignments'] = []
        with pytest.raises(ContractError, match='operation_key_reused'):
            repo.populate_v3(context, changed, 'selected')
    finally:
        store.close()



def test_parent_receives_reprojected_child_cells_bound_by_digest(tmp_path):
    store, context, args, _ = native_case(tmp_path)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, args, 'selected')
        ref = outcome['result']['sheet_ref']
        key = outcome['result']['component_keys'][0]
        cells = repo.project_cells([ref], permitted_record_refs=[ref], components=[key])
        parent = replace(context, episode_id='fixture-parent', path=context.path[:1], received_record_refs=(*context.received_record_refs, ref))
        assert repo.received_cells(parent) == []
        repo.receive_cells(parent, cells, 'child_return:0')
        repo.receive_cells(parent, cells, 'child_return:0')
        assert repo.received_cells(parent) == cells
        assert repo.fact_cells(parent, [ref], components=[key]) == cells
        with pytest.raises(ContractError, match='literature_delivery_binding_mismatch'):
            repo.receive_cells(parent, [], 'child_return:0')
        store.db.execute(f'UPDATE {repo.received_table} SET cells=? WHERE episode_id=?', ('[]', parent.episode_id))
        with pytest.raises(ContractError, match='literature_delivery_binding_mismatch'):
            repo.received_cells(parent)
    finally:
        store.close()


def test_original_outcome_association_cannot_be_replaced_by_self_hash(tmp_path):
    store, context, args, _ = native_case(tmp_path)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, args, 'selected')
        ref = outcome['result']['sheet_ref']
        saved = repo.read(ref)
        record = store.get(ref)
        saved['population']['local_sheet']['raw'][0]['cell']['value'] = 123
        artifact = store.artifact(canonical(saved), 'application/json')
        forged = {k: v for k, v in record.items() if k not in ('id', 'record_type', 'origin')}
        forged.update(artifact_ref=artifact, text_ref=artifact)
        forged_ref = store.put('source', forged, origin='tool')['id']
        with pytest.raises(ContractError, match='original_outcome_mismatch'):
            repo.read(forged_ref)
    finally:
        store.close()



@pytest.mark.parametrize('mode', ['absent', 'empty_covariance'])
def test_saved_partial_read_preserves_missing_values_and_empty_covariance(tmp_path, mode):

    def modify(f):
        if mode == 'absent':
            f.args['arms']['protein_condition1'] = None
            f.args['covariance']['bindings']['protein_condition1'] = None
        else:
            f.data[f.cov_ref] = b''
            f.args['covariance']['bindings'] = dict.fromkeys(storage.shared.PRIMITIVE_ORDER)
            f.args['variance_status'] = {'value': 'unknown', 'witnesses': []}
            f.args['model_kind'] = {'value': 'none', 'witnesses': []}
            f.args['local_pair_assignments'][0]['covariance_selection'] = cp(f.args['covariance'])
            f.args['local_pair_assignments'][0]['variance_status'] = cp(f.args['variance_status'])
    store, context, args, _ = native_case(tmp_path, modify=modify)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, args, mode)
        saved = repo.read(outcome['result']['sheet_ref'])
        if mode == 'absent':
            row = outcome['result']['cells'][0]
            assert row['cell']['value'] is None and row['cell']['origin'] is None and (row['native_reading'] is None)
        else:
            document = saved['extraction']['covariance_document_scopes'][0]['document']
            assert document['raw_text'] == '' and document['document_state'] == 'unsupported_format'
            variance = next((r for r in outcome['result']['cells'] if r['kind'] == 'local_variance'))
            assert variance['cell']['value'] is None
            assert document['exact_matrix'] is None
    finally:
        store.close()

def test_declared_evidence_profile_is_bound_without_claiming_publication_truth(tmp_path):
    store, context, args, _ = native_case(tmp_path, companion=True)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        reported = storage.LiteratureControlledResponseRepository(store, context.run_id)
        with pytest.raises(ContractError, match='evidence_profile_mismatch'):
            reported.populate_v3(context, args, 'profile')
        relabeled = cp(args)
        relabeled['companion_readings'][0]['reading']['source_kind'] = 'primary_source'
        with pytest.raises(ContractError, match='evidence_profile_mismatch'):
            repo.populate_v3(context, relabeled, 'profile')
        outcome = repo.populate_v3(context, args, 'profile')
        ref = outcome['result']['sheet_ref']
        assert repo.read(ref)['evidence_origin'] == 'synthetic_fixture'
        assert repo.descriptor()['evidence_origin'] == 'synthetic_fixture'
        with pytest.raises(ContractError, match='evidence_profile_mismatch'):
            reported.read(ref)
        with pytest.raises(ContractError, match='implementation_binding_mismatch'):
            storage.LiteratureControlledResponseRepository(store, context.run_id, expected_descriptor=repo.descriptor())
    finally:
        store.close()

def test_component_specific_variance_model_metadata_matches_dependencies(tmp_path):
    store, context, args, _ = native_case(tmp_path, companion=True, joints=True, authority=True)
    try:
        repo = storage.LiteratureControlledResponseRepository(store, context.run_id, evidence_origin='synthetic_fixture')
        outcome = repo.populate_v3(context, args, 'metadata')
        saved = repo.read(outcome['result']['sheet_ref'])
        for row in outcome['result']['cells']:
            if row['kind'] not in ('final', 'conditional'):
                continue
            index = storage.arithmetic.COMPONENTS.index(row['component'])
            if index < 7:
                assert row['context']['variance_status'] == 'unknown' and row['context']['model_kind'] == 'none'
                assert not row['dependencies']['model_readings'] and (not row['dependencies']['covariance_owner_ids'])
            elif index < 10:
                assert row['context']['variance_status'] == 'known' and row['context']['model_kind'] == 'none'
                assert not row['dependencies']['model_readings']
            else:
                assert row['context']['model_kind'] == 'known_joint_normal_source_means'
                assert row['dependencies']['model_readings']
        assert saved['population']['final_sheet']['inputs']['model_kind'] == 'known_joint_normal_source_means'
    finally:
        store.close()
