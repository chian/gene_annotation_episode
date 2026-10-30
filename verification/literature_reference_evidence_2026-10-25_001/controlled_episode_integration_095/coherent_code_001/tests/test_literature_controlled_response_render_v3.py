"""Rendering constructed possessed facts; no model interpretation claim."""
import json

from gene_annotation_episode import literature_controlled_response_render as render
from gene_annotation_episode import literature_controlled_response_storage as storage
from test_literature_controlled_response_storage_v3 import native_case


def text_for(rows,records,bindings):
    parts=[]
    render.render_received(parts,rows,records,section=lambda p,title,body:p.append(title+'\n'+body),
        table=lambda headings,rows:json.dumps([headings,list(rows)]),values=lambda value:json.dumps(value),bindings=bindings)
    return '\n'.join(parts)


def test_derived_component_keeps_labels_and_masks_unrequested_raw_numbers(tmp_path):
    store,context,args,_=native_case(tmp_path,index=7)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture')
        outcome=repo.populate_v3(context,args,'render');ref=outcome['result']['sheet_ref']
        row=next(r for r in outcome['result']['cells'] if r['component_key']=='local:condition0-real:variance')
        rows=[row];bindings=repo.semantic_bindings(rows)
        records={r:store.get(r) for r in repo.cell_record_refs(rows)}
        text=text_for(rows,records,bindings)
        assert 'local_variance' in text and 'Requested native reading' not in text
        assert 'Physical C.' in text
        assert ref not in text and 'artifact_' not in text and 'controlled_' not in text
        assert 'reported_uncertainty' not in text and '95%' not in text and 'n = 3' not in text
        hidden=render.hidden_records([{'requested':rows}],records,bindings=bindings)
        assert set(records)<=hidden
        parts=[]
        assert render.render_own_result(parts,{'result':{'cells':rows}},section=lambda p,t,b:p.append(b),
            table=lambda h,r:json.dumps(list(r)),values=json.dumps,records=records,bindings=bindings)
        assert not render.render_own_result([],{'ordinary_result':1},section=None,table=None,values=None)
    finally:store.close()


def test_uncertainty_numeric_spans_mask_broad_labels_but_preserve_disjoint_source_facts(tmp_path):
    store,context,args,_=native_case(tmp_path,index=7)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture');outcome=repo.populate_v3(context,args,'mask')
        row=next(r for r in outcome['result']['cells'] if r['kind']=='local_variance')
        saved=repo.read(row['sheet_ref']);u=saved['extraction']['arms']['protein_condition1']['reported_uncertainty']
        records={}
        for name in ('interval','confidence_level','count'):
            witness=u[name]['witness']['selection']
            anchor={k:witness[k] for k in ('source_ref','start','end','quote')}
            anchor['artifact_ref']=u[name]['witness']['artifact_ref']
            records[name]={'label':witness['quote'],'source_ref':witness['source_ref'],'anchor':anchor}
        meaning=saved['extraction']['arms']['protein_condition1']['meanings']['endpoint']['canonical_witness']
        w=meaning['selection'];anchor={k:w[k] for k in ('source_ref','start','end','quote')};anchor['artifact_ref']=meaning['artifact_ref']
        records['independent_source_fact']={'label':w['quote'],'source_ref':w['source_ref'],'anchor':anchor}
        hidden=render.hidden_records([{'requested':[row]}],records)
        assert {'interval','confidence_level','count'}<=hidden
        assert 'independent_source_fact' not in hidden
        assert list(render.rows_from_reports([{'requested':[row], 'unrelated':[{}]}]))==[row]
    finally:store.close()


def test_raw_requested_view_preserves_exact_operand_and_graph_qualifications(tmp_path):
    store,context,args,_=native_case(tmp_path,index=6)
    try:
        repo=storage.LiteratureControlledResponseRepository(store,context.run_id,evidence_origin='synthetic_fixture');outcome=repo.populate_v3(context,args,'graph')
        row=outcome['result']['cells'][0];saved=repo.read(row['sheet_ref'])
        operand=saved['extraction']['arms']['protein_condition1']['calculation_operand']
        assert row['native_reading']=={k:operand[k] for k in row['native_reading']}
        assert any(t['kind']=='image_region' for t in row['numeric_locations'])
        text=text_for([row],{},{});assert 'Requested native reading' in text
        assert 'conditional_digitization' in text and 'digitization_interval' in text
        assert row['native_reading']['source_observation_id'] not in text
    finally:store.close()
