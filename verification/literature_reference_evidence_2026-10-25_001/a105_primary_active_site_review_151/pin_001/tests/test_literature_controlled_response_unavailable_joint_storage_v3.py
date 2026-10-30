"""Constructed unavailable joint scopes; no fabricated numerical alternatives."""
from copy import deepcopy as cp
from dataclasses import replace

import pytest

from gene_annotation_episode import literature_controlled_response_storage as storage
from gene_annotation_episode import literature_controlled_response_local_calculations as local
from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.domain import ContractError
from test_literature_controlled_response_storage_v3 import native_case,owned,seed_runtime_rows
from test_literature_controlled_response_render_v3 import text_for


def forbidden(*a,**k):raise AssertionError('numerical population must not run during projection')


@pytest.mark.parametrize('field,value',[
    ('admissibility','unknown'),('admissibility','conflicting'),
    ('normalization','unknown'),('calibration','conflicting'),('revision','conflicting')])
def test_unavailable_original_joint_index_map_and_independent_readings(tmp_path,monkeypatch,field,value):
    def modify(f):
        if field=='admissibility':
            # A conflicting interpretation requires distinct actual witnesses.
            f.args['joint_reading_assignments'][0]['admissibility']={
                'value':value,'witnesses':[] if value=='unknown' else [f.witness('nmol/min'),f.witness('Physical A.')]}
        else:
            f.args['joint_scopes'][0][field]={'value':value,
                'witnesses':[] if value=='unknown' else [f.witness('nmol/min'),f.witness('Physical A.')]}
    store,context,args,_=native_case(tmp_path,companion=True,joints=True,modify=modify)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'unavailable');ref=outcome['result']['sheet_ref'];saved=repo.read(ref)
        assert [r['scope_index'] for r in saved['population']['alternatives']]==[1]
        original=saved['extraction']['joint_scope_extractions'][0]
        assert original['effective_admissibility']==value
        conditional=[r for r in outcome['result']['cells'] if r['kind']=='conditional']
        assert [r['component_key'] for r in conditional[:12]]==['joint:0:'+c for c in storage.arithmetic.COMPONENTS]
        assert all(r['component_key'].startswith('joint:1:') for r in conditional[12:])
        for row in conditional[:12]:
            assert row['reading_assignment']==args['joint_reading_assignments'][0]['assignment']
            cell=row['cell'];assert [cell[k] for k in ('value','lower','upper','unit','origin')]==[None]*5
            assert cell['status']=='unavailable' and cell['unavailable_reason']==[value+'_joint_applicability']
            assert row['native_reading'] is None and row['reported_uncertainty'] is None
            deps=row['dependencies']
            assert all(deps[k]==[] for k in ('numeric_readings','numeric_fields','uncertainty_readings','model_readings','covariance_owner_ids','source_variable_indices'))
            assert deps['covariance_index'] is None and not deps['full_source_covariance_required']
            assert row['context']['variance_status']=='unknown' and row['context']['model_kind']=='none'
        expected={r['component']:r['cell'] for r in saved['population']['conditional_components']}
        assert all(r['cell']==expected[r['component']] for r in conditional[12:])
        assert outcome['result']['cells'][0]['cell']['value'] is not None
        assert next(r for r in outcome['result']['cells'] if r['kind']=='local_difference')['cell']['value'] is not None
        monkeypatch.setattr(storage.population,'populate_controlled_response_v3',forbidden)
        monkeypatch.setattr(local,'populate_controlled_response_local',forbidden)
        monkeypatch.setattr(owner,'populate_controlled_response_owner',forbidden)
        assert storage._component_rows(saved['extraction'],saved['population'],ref)==outcome['result']['cells']
        assert repo.read(ref)==saved
    finally:store.close()


def test_exact_unavailable_subset_receipt_and_tampered_assignment_rejected(tmp_path):
    def modify(f):
        for i,value in enumerate(('unknown','conflicting')):
            f.args['joint_reading_assignments'][i]['admissibility']={'value':value,
                'witnesses':[] if value=='unknown' else [f.witness('nmol/min'),f.witness('Physical A.')]}
    store,context,args,_=native_case(tmp_path,index=7,companion=True,joints=True,modify=modify)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'fixture-run:fixture-child:4');ref=outcome['result']['sheet_ref']
        selected=[r for r in outcome['result']['cells'] if r['component_key']=='joint:1:controlled_response_difference']
        assert len(selected)==1
        parent,key=seed_runtime_rows(store,context,outcome,selected)
        repo.receive_cells(parent,selected,key)
        assert repo.received_cells(parent)==selected
        possessed=replace(parent,received_record_refs=tuple(repo.cell_record_refs(selected)))
        assert repo.fact_cells(possessed,[ref],components=outcome['result']['component_keys'])==selected
        keys=repo.requested_component_keys(ref,dict(context.assignment))
        assert 'joint:0:controlled_response_difference' in keys and 'joint:1:controlled_response_difference' in keys
        corrupted=cp(selected);corrupted[0]['reading_assignment']['protein_condition1']=None
        with pytest.raises(ContractError,match='differs_from_original'):
            repo.validate_returned_values(corrupted,permitted_record_refs=[ref])
        bindings=repo.semantic_bindings(selected);records={r:store.get(r) for r in repo.cell_record_refs(selected)}
        text=text_for(selected,records,bindings)
        assert 'conflicting_joint_applicability' in text
        assert '95%' not in text and 'n = 3' not in text and 'Requested native reading' not in text
        assert not store.list('observation')
    finally:store.close()
