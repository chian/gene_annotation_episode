"""Actual constructed scope states survive exact native typed custody."""
from copy import deepcopy as cp
from dataclasses import replace

import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode import literature_controlled_response_storage as storage
from gene_annotation_episode import literature_controlled_response_render as render
from test_literature_controlled_response_storage_v3 import native_case,seed_runtime_rows
from test_literature_controlled_response_render_v3 import text_for

FIELDS=('normalization','calibration','revision','covariance_scope','model_scope')


@pytest.mark.parametrize('state',['same','explicit_compatible','not_applicable','unknown','conflicting'])
def test_all_scope_relationship_states_preserve_original_witness_associations(tmp_path,state):
    def modify(f):
        for name in FIELDS:
            witnesses=[] if state=='unknown' else [f.witness('nmol/min')]
            if state=='conflicting':witnesses.append(f.witness('Physical A.'))
            f.args['joint_scopes'][1][name]={'value':state,'witnesses':witnesses}
    store,context,args,_=native_case(tmp_path,companion=True,joints=True,modify=modify)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'scope-states');saved=repo.read(outcome['result']['sheet_ref'])
        row=next(r for r in outcome['result']['cells'] if r['component_key']=='joint:1:controlled_response_difference')
        scope=row['joint_scope_context'];actual=saved['extraction']['joint_scope_extractions'][1]
        assert scope['reading_assignment']==row['reading_assignment']==args['joint_reading_assignments'][1]['assignment']
        assert scope['effective_admissibility']==actual['effective_admissibility']
        for name in FIELDS:
            assert scope[name]['selected_value']==scope[name]['effective_value']==state
            selected=args['joint_scopes'][1][name]['witnesses']
            assert len(scope[name]['witnesses'])==len(selected)
            for projected,original in zip(scope[name]['witnesses'],selected):
                retained=saved['scope_witness_bindings'][projected['witness_ref']]['witness']
                assert retained['selection']==original
                assert projected['authentication']==retained['authentication']
                assert store.get(projected['witness_ref'])['label']==' '.join(original['quote'].split())
        assert scope['effective_model']==actual['effective_model']
        assert scope['covariance_context']['source_model']==actual['source_covariance']['source_model']
        assert scope['requested_model']['model_kind']['selected_value']==actual['requested_model']['model_kind']['selection']['value']
        if state in ('unknown','conflicting'):
            assert row['cell']['value'] is None
            assert row['cell']['unavailable_reason']==[state+'_joint_applicability']
        assert all(r['joint_scope_context'] is None for r in outcome['result']['cells'] if r['kind'].startswith('local') or r['kind']=='native_raw')
    finally:store.close()


def test_final_joint_context_exact_subset_semantic_refs_masking_and_readonly_restore(tmp_path,monkeypatch):
    def modify(f):
        f.args['companion_readings'][0]['reading']['measurement']=cp(f.args['arms']['protein_condition1']['measurement'])
        f.args['reading_reconciliations'][0]['authority']['reading']['reading_key']='A-display'
        for index,number in enumerate(('0.123456789','0.987654321')):
            quote='The source calibration used '+number+' standards.'
            f.append(quote);f.args['joint_scopes'][index]['calibration']={'value':'same','witnesses':[f.witness(quote)]}
    store,context,args,_=native_case(tmp_path,companion=True,authority=True,joints=True,modify=modify)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'fixture-run:fixture-child:4');ref=outcome['result']['sheet_ref'];saved=repo.read(ref)
        assert saved['extraction']['final_projection_basis']['covariance_scope']=='joint'
        row=next(r for r in outcome['result']['cells'] if r['component_key']=='final:controlled_response_difference')
        assert row['reading_assignment'] is None
        assert row['joint_scope_context']['reading_assignment']==saved['extraction']['final_projection_basis']['reading_assignment']
        allowed={store.get(ref)['artifact_ref'],store.get(ref)['request_ref']};get_artifact=store.get_artifact
        def no_scientific_content(reference):
            assert reference in allowed
            return get_artifact(reference)
        monkeypatch.setattr(store,'get_artifact',no_scientific_content)
        selected=[row];parent,key=seed_runtime_rows(store,context,outcome,selected)
        repo.receive_cells(parent,selected,key);assert repo.received_cells(parent)==selected
        refs=repo.cell_record_refs(selected);bindings=repo.semantic_bindings(selected)
        witness_ref=row['joint_scope_context']['calibration']['witnesses'][0]['witness_ref']
        other=next(r for r in outcome['result']['cells'] if r['component_key']=='joint:0:controlled_response_difference')
        other_ref=other['joint_scope_context']['calibration']['witnesses'][0]['witness_ref']
        assert witness_ref in refs and other_ref not in refs
        records={reference:store.get(reference) for reference in refs}
        text=text_for(selected,records,bindings)
        assert '0.987654321' not in text and '0.123456789' not in text
        assert 'Selected meaning' in text and 'Retained effective meaning' in text
        assert 'Joint assignment' not in text and 'A-display' not in text
        assert 'Source scope 1 relationships' in text
        forged=cp(selected);forged[0]['joint_scope_context']['calibration']['witnesses'][0]['witness_ref']=other_ref
        with pytest.raises(ContractError,match='differs_from_original'):repo.validate_returned_values(forged,permitted_record_refs=[ref])
        # A disjoint, independently bounded source fact is not hidden by the
        # selected calibration numeral or other native source measurements.
        w=saved['extraction']['arms']['protein_condition1']['meanings']['endpoint']['canonical_witness']
        anchor={k:w['selection'][k] for k in ('source_ref','start','end','quote')};anchor['artifact_ref']=w['artifact_ref']
        records['independent_fact']={'source_ref':w['selection']['source_ref'],'label':w['selection']['quote'],'anchor':anchor}
        assert 'independent_fact' not in render.hidden_records([{'selected':selected}],records,bindings=bindings)
        assert not store.list('observation')
    finally:store.close()
    store=Store(tmp_path);store.db.execute('PRAGMA query_only=1')
    try:
        get=store.get_artifact
        def saved_only(reference):
            assert reference in allowed
            return get(reference)
        store.get_artifact=saved_only
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        assert repo.read(ref)==saved
        assert repo.received_cells(parent)==selected
        assert store.db.total_changes==0
    finally:store.close()


def test_unauthenticated_source_witness_gets_generic_actual_record_and_unknown_effective_state(tmp_path):
    store,context,args,_=native_case(tmp_path,companion=True,joints=True)
    try:
        artifact=store.artifact(b'Available original; no selected text representation.')
        source_ref=store.put('source',{'provider':'constructed_missing_representation','accession':None,'uri':None,
            'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,
            'parent_source_refs':[args['source_ref']]},origin='caller')['id']
        nomination={'kind':'text','source_ref':source_ref,'representation':'text','start':0,'end':16,'quote':'UNVERIFIED QUOTE'}
        args['joint_scopes'][1]['model_kind']={'value':'known_joint_normal_source_means','witnesses':[nomination]}
        context=replace(context,received_record_refs=(*context.received_record_refs,source_ref))
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'missing-witness');ref=outcome['result']['sheet_ref'];saved=repo.read(ref)
        row=next(r for r in outcome['result']['cells'] if r['component_key']=='joint:1:controlled_response_difference')
        request=row['joint_scope_context']['requested_model']['model_kind']
        assert request['selected_value']=='known_joint_normal_source_means' and request['effective_value']=='unknown'
        witness=request['witnesses'][0];assert witness['authentication']=='unavailable'
        record=store.get(witness['witness_ref']);assert record['label']=='Source witness unavailable' and record['anchor'] is None
        assert saved['scope_witness_bindings'][witness['witness_ref']]['witness']['selection']==nomination
        bindings=repo.semantic_bindings([row]);records={r:store.get(r) for r in repo.cell_record_refs([row])}
        text=text_for([row],records,bindings)
        assert 'UNVERIFIED' not in text and 'source witness unavailable' in text
        assert row['context']['model_kind']=='none'
    finally:store.close()
