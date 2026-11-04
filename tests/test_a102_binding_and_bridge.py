"""Small synthetic geometry verifies existing-comparison delivery and feature unknowns."""
from importlib import import_module
import json

import pytest

from gene_annotation_episode.a102_credit import A102StructuralCredit
from gene_annotation_episode.a102_publication import received_grade
from gene_annotation_episode.a102_structural_bridge import publish_bridge
from gene_annotation_episode.a102_structures import bind_structure,binding_summary,sequence_map
from gene_annotation_episode.a102_tools import A102ToolRegistry
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.protein_structure_calculations import calculate_protein_structure_components
from gene_annotation_episode.state import Store

f=import_module('verification.tool_graders_protein_structure_calculations_2026-10-27_389.fixture_helpers')


def test_existing_fitted_alignment_is_credited_only_with_selected_recalculation_and_maps(tmp_path):
    with Store(tmp_path/'state') as store:
        target,=store.create_problem(raw_sequence='AGST',molecule='protein')['subject_refs']
        scope={'subject_refs':[target]}
        registry=A102ToolRegistry(store,a102_work_directory=tmp_path/'native')
        fixed=f.a.fixture_pdb(coordinates=[[3,-2,5],[3,-1,5],[2,-2,5],[3,-2,6]])
        moving=f.a.fixture_pdb(role='moving',chain='B')
        sheet=f.make_sheet(fixed,moving)
        components=calculate_protein_structure_components(sheet,parameters=sheet['native_request'])
        references=[]
        for side,fixture in [('fixed',fixed),('moving',moving)]:
            data=fixture[0];artifact=store.artifact(data,'chemical/x-pdb')
            source=registry._source('synthetic.coordinate_fixture',{'label':side})
            body=bind_structure(data,{'format':'pdb_3x_text','artifact_ref':artifact,'block_ordinal':0,
                'model_ordinal':0,'chain_id':'A' if side=='fixed' else 'B','file_source_ref':source,
                'target_ref':target if side=='fixed' else None,
                'supplied_sequence':'AGST' if side=='fixed' else None,
                'model_metadata':{'origin':'supplied_unknown'}})
            reference=registry._source('native.a102.structure_binding',binding_summary(body))
            store.db.execute('INSERT INTO a102_structure_bindings VALUES(?,?)',(reference,canonical(body)))
            references.append(reference)
        original=registry._source('compare_protein_structures',{'label':'synthetic_original_comparison'})
        arguments={'scientific':{'kind':'comparison','sheet':sheet,'components':components},
            'source_ref':original,'scope':scope,'known_record_refs':references}
        assert publish_bridge(registry,**arguments,selection={'return_saved_sheet':False})==[]
        assert publish_bridge(registry,**{**arguments,'known_record_refs':[]},selection={'return_saved_sheet':True})==[]
        native,=publish_bridge(registry,**arguments,selection={'return_saved_sheet':True})
        grade=received_grade(store,native)['grade']
        assert grade['producer']=='compare_protein_structures'
        assert grade['components']['B']==pytest.approx(1)
        assert max(grade['distances_A'])<1e-10
        assert A102StructuralCredit()(store,scope,known_record_refs=[native])['credit']==pytest.approx(1)

        function=store.put('hypothesis',{'subject_refs':[target],'predicate':'functional_family',
            'value':{'type':'enum','value':'unresolved'},'context_refs':[]},origin='reasoning')['id']
        definition=registry._source('synthetic.feature_definition',{'meaning':'Engineering-only required anchors; no biological function claim.'})
        known={*references,native,function,definition,target}
        result,delivered=registry._features({'comparison_source_ref':native,'function_ref':function,
            'definition_source_refs':[definition],'features':[
                {'physical_feature_key':f'synthetic-anchor-{i}','state':'measure','target_position':i,
                    'reference_position':i,'target_atom':'CA' if i<2 else 'CB','reference_atom':'CA' if i<2 else 'CB',
                    'witness_refs':[definition,native],'reason':'Synthetic geometry verification.'} for i in range(3)]},known,scope)
        assert result['K']==3 and result['n_unresolved']==1
        assert result['F'] is result['E'] is None
        projected=A102StructuralCredit()(store,scope,known_record_refs=[native,*delivered])
        assert projected['credit']==pytest.approx(1)
        assert projected['functional_sheets']['features'][0]['E'] is None
        repeated=[{'physical_feature_key':key,'state':'measure','target_position':0,'reference_position':0,
            'target_atom':'CA','reference_atom':'CA','witness_refs':[definition,native],
            'reason':'Same physical requirement with two labels.'} for key in ('first-label','second-label')]
        with pytest.raises(ValueError,match='duplicate_physical_feature'):
            registry._features({'comparison_source_ref':native,'function_ref':function,
                'definition_source_refs':[definition],'features':repeated},known,scope)


def test_coordinate_mapping_is_unique_and_retains_construct_substitutions():
    mapping,details=sequence_map('MALWFGKRTVE','MALWAGKRTVE')
    assert mapping==list(range(11))
    assert details['substitutions']==[{'input_position':4,'model_position':4,'input_symbol':'F','model_symbol':'A'}]
    with pytest.raises(ValueError,match='ambiguous_coordinate_to_input_mapping'):
        sequence_map('AAAAAA','AAA')
