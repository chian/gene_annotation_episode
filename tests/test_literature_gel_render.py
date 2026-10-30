"""Rendering constructed selectively possessed gel rows, without model claims."""
from dataclasses import replace
import json

from gene_annotation_episode import literature_gel_render as render
from gene_annotation_episode import literature_gel_inputs as inputs
from test_literature_gel_storage import native_case,repository,source


def text_for(rows,records,bindings):
    parts=[]
    render.render_received(parts,rows,records,section=lambda p,t,b:p.append(t+'\n'+b),
        table=lambda h,r:json.dumps([h,list(r)]),values=json.dumps,bindings=bindings)
    return '\n'.join(parts)


def test_derived_only_render_keeps_meaning_and_qualifications_without_raw_numbers_or_host_ids(tmp_path):
    store,context,args=native_case(tmp_path,alternatives=True)
    try:
        repo=repository(store,context);outcome=repo.populate(context,args,'render');ref=outcome['result']['sheet_ref']
        rows=[r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift']
        bindings=repo.semantic_bindings(rows);records={r:store.get(r) for r in repo.cell_record_refs(rows)}
        text=text_for(rows,records,bindings)
        assert 'Requested gel display components' in text and 'direct competitor sensitive shift' in text
        assert text.count('Lane and band numbers are local labels for this returned subset, not original gel numbering.')==1
        assert 'DNA shift' in text and '"P"' in text and '"C"' in text
        assert 'not_established_by_display_arithmetic' in text and 'baseline_cancels_from_direct_form' in text
        assert '80' not in text and '100' not in text
        for secret in (ref,'artifact_','observation_baseline','observation_protein','declared','same:region','component_key','lane_id'):
            assert secret not in text
        assert 'mean' in text and 'not_supplied' in text
        hidden=render.hidden_records([{'requested':rows}],records,bindings=bindings)
        assert set(records)<=hidden
        parts=[]
        assert render.render_own_result(parts,{'result':{'cells':rows}},section=lambda p,t,b:p.append(b),
            table=lambda h,r:json.dumps(list(r)),values=json.dumps,records=records,bindings=bindings)
        assert not render.render_own_result([],{'ordinary':1},section=None,table=None,values=None)
    finally:store.close()


def test_full_source_witnesses_are_hidden_but_disjoint_scientific_numbers_remain_meaningful(tmp_path):
    store,context,args=native_case(tmp_path)
    try:
        caption=b'Synthetic protein P construct C, DNA shift; lanes baseline, protein, competitor. Signal 80; CI 95%; n = 3; calibration 2.5.'
        caption_ref=source(store,caption)
        for w in inputs._witnesses(args['selection']):w.update(source_ref=caption_ref,end=len(caption),quote=caption.decode())
        context=replace(context,received_record_refs=(*context.received_record_refs,caption_ref))
        repo=repository(store,context);outcome=repo.populate(context,args,'numeric-caption')
        rows=[r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift']
        bindings=repo.semantic_bindings(rows);records={r:store.get(r) for r in repo.cell_record_refs(rows)}
        artifact=store.get(caption_ref)['artifact_ref']
        def fact(label):
            start=caption.index(label.encode())
            return {'label':label,'source_ref':caption_ref,'anchor':{'source_ref':caption_ref,
                'artifact_ref':artifact,'start':start,'end':start+len(label),'quote':label}}
        # Original source-witness records are hidden regardless of their digits.
        # Separate admitted text facts are not image-derived gel operands.
        records.update(interval=fact('CI 95%'),count=fact('n = 3'),calibration=fact('calibration 2.5'),disjoint=fact('DNA shift'))
        hidden=render.hidden_records([{'requested':rows}],records,bindings=bindings)
        for entries in bindings.values():
            assert {b['record_ref'] for b in entries.values() if b['category']=='source_witness'}<=hidden
        assert not {'interval','count','calibration','disjoint'}&hidden
        text=text_for(rows,records,bindings)
        for numeric in ('95%','80','n = 3','2.5'):assert numeric not in text
        assert 'DNA shift' in text
        assert list(render.rows_from_reports([{'requested':rows,'other':[{}]}]))==rows
    finally:store.close()


def test_source_bound_numeric_condition_concentration_and_construct_are_preserved(tmp_path):
    store,context,args=native_case(tmp_path)
    try:
        caption=b'30 nM IscR; pH 7.5; construct 101 residues; DNA shift; independent experimental context.'
        caption_ref=source(store,caption)
        for w in inputs._witnesses(args['selection']):w.update(source_ref=caption_ref,end=len(caption),quote=caption.decode())
        args['selection']['context']['subject']['value']='30 nM IscR'
        args['selection']['context']['construct']['value']='construct 101 residues'
        for lane in args['selection']['lanes']:
            lane['subject']['value']='IscR';lane['construct']['value']='construct 101 residues'
            lane['condition']['value']='pH 7.5'
        context=replace(context,received_record_refs=(*context.received_record_refs,caption_ref))
        repo=repository(store,context);outcome=repo.populate(context,args,'numeric-meanings')
        rows=[r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift']
        bindings=repo.semantic_bindings(rows);records={r:store.get(r) for r in repo.cell_record_refs(rows)}
        text=text_for(rows,records,bindings)
        assert '30 nM IscR' in text and 'pH 7.5' in text and 'construct 101 residues' in text
        assert '80' not in text and '100' not in text
        assert all(loc['source_ref']!=caption_ref for loc in rows[0]['numeric_locations'])
        hidden=render.hidden_records([{'requested':rows}],records,bindings=bindings)
        assert caption_ref in hidden
        assert all(r['record_ref'] in hidden for r in bindings[rows[0]['sheet_ref']].values() if r['category']=='source_witness')
        assert caption.decode() not in text
    finally:store.close()


def test_caption_text_and_image_pixels_can_share_source_without_coordinate_aliasing(tmp_path):
    store,context,args=native_case(tmp_path)
    try:
        original=store.get(args['selection']['image']['source_ref'])
        caption=b'30 nM IscR; pH 7.5; construct 101 residues; DNA shift.'
        text_ref=store.artifact(caption)
        body={k:v for k,v in original.items() if k not in ('id','record_type','origin')}
        body['text_ref']=text_ref
        shared=store.put('source',body,origin='caller')['id']
        args['selection']['image']['source_ref']=shared
        for w in inputs._witnesses(args['selection']):w.update(source_ref=shared,end=len(caption),quote=caption.decode())
        args['selection']['context']['subject']['value']='30 nM IscR'
        for lane in args['selection']['lanes']:
            lane['condition']['value']='pH 7.5';lane['construct']['value']='construct 101 residues'
        context=replace(context,received_record_refs=(*context.received_record_refs,shared))
        repo=repository(store,context);outcome=repo.populate(context,args,'shared-source-representations')
        rows=[r for r in outcome['result']['cells'] if r['component_key']=='comparison:declared:direct_competitor_sensitive_shift']
        bindings=repo.semantic_bindings(rows);records={r:store.get(r) for r in repo.cell_record_refs(rows)}
        text=text_for(rows,records,bindings)
        assert '30 nM IscR' in text and 'pH 7.5' in text and 'construct 101 residues' in text
        assert '80' not in text and '100' not in text and caption.decode() not in text
        assert shared in render.hidden_records([{'requested':rows}],records,bindings=bindings)
    finally:store.close()


def test_sensitivity_only_render_shows_range_meaning_without_granting_all_raw_alternatives(tmp_path):
    store,context,args=native_case(tmp_path,alternatives=True)
    try:
        repo=repository(store,context);outcome=repo.populate(context,args,'sensitivity')
        rows=[r for r in outcome['result']['cells'] if r['component_key']=='sensitivity:direct_competitor_sensitive_shift']
        text=text_for(rows,{},{});info=rows[0]['cell']['sensitivity']
        assert 'Reading-choice range meaning' in text and info['kind'] in text
        assert 'available reading choices' in text and 'sampling confidence level' in text
        assert '80' not in text and '100' not in text and 'declared' not in text and 'same:region' not in text
        assert all(r['view']=='sensitivity' for r in rows)
    finally:store.close()


def capture(rows,records,bindings):
    parts=[]
    render.render_received(parts,rows,records,section=lambda p,t,b:p.append((t,b)),
        table=lambda headings,rows:{'headings':list(headings),'rows':list(rows)},values=lambda v:v,bindings=bindings)
    return parts


def test_lane_band_and_comparison_associations_are_unambiguous_for_all_rows_and_subset(tmp_path):
    store,context,args=native_case(tmp_path,alternatives=True)
    try:
        for choice in args['selection']['roi_assignments']:
            protein=next(l for l in choice['lanes'] if l['lane_id']=='protein')
            protein['bands'].append({'band_id':'second:shifted / β','role':'shifted','region':[1,2,2,3]})
        repo=repository(store,context);outcome=repo.populate(context,args,'associations')
        names={'shifted_display_fraction','sum_darkness','background_corrected_band_darkness','direct_competitor_sensitive_shift'}
        rows=[r for r in outcome['result']['cells'] if r['component'] in names and r['view']!='sensitivity']
        bindings=repo.semantic_bindings(rows);records={r:store.get(r) for r in repo.cell_record_refs(rows)}
        parts=capture(rows,records,bindings);numeric=parts[0][1]
        display=[dict(zip(numeric['headings'],row)) for row in numeric['rows']]
        assert {'Lane','Region / band','Reading choice'}<=set(numeric['headings'])
        lane_conditions={}
        for title,body in parts:
            if title.endswith(' source meaning'):
                lane_conditions[title.removesuffix(' source meaning')]=next(r[2] for r in body['rows'] if r[0]=='condition')
        assert set(lane_conditions.values())=={'baseline','protein','competitor'}
        fractions=[r for r in display if r['Component']=='shifted display fraction']
        assert len(fractions)==6 and len({(r['Reading choice'],r['Lane']) for r in fractions})==6
        for row in fractions:
            condition=lane_conditions[row['Lane']]
            assert row['Value']=={'baseline':0,'protein':9/11,'competitor':.2}[condition]
        shifted=[r for r in display if r['View']=='raw_region' and r['Reading choice']=='1'
            and lane_conditions[r['Lane']]=='protein' and '(shifted)' in r['Region / band']]
        assert {r['Value'] for r in shifted}=={80,10}
        assert len({r['Region / band'] for r in shifted})==2
        for row in shifted:
            matching=[r for r in display if r['View']=='corrected_band' and r['Reading choice']==row['Reading choice']
                and r['Lane']==row['Lane'] and r['Region / band']==row['Region / band']]
            assert len(matching)==1 and matching[0]['Value']==row['Value']
        for title,body in parts:
            if title=='Gel comparison lane roles':
                assert {role:lane_conditions[lane] for _,role,lane in body['rows']}=={
                    'baseline':'baseline','protein':'protein','competitor':'competitor'}
        text=json.dumps(parts)
        for secret in ('second:shifted','observation_protein',outcome['result']['sheet_ref'],'same:region'):
            assert secret not in text
        subset=[r for r in rows if r['assignment_id']=='declared' and r['lane_id']=='protein'
            and r['band_id']=='second:shifted / β']
        subset_parts=capture(subset,records,repo.semantic_bindings(subset))
        table=subset_parts[0][1];subset_display=[dict(zip(table['headings'],r)) for r in table['rows']]
        assert len(subset_display)==2 and {r['Lane'] for r in subset_display}=={'Lane 1'}
        assert {r['Region / band'] for r in subset_display}=={'Band 1 (shifted)'}
        assert any(t=='Lane 1 source meaning' and ('condition','known','protein') in b['rows'] for t,b in subset_parts)
        subset_text=json.dumps(subset_parts)
        assert 'baseline' not in subset_text and 'competitor' not in subset_text
        assert '80' not in subset_text and '100' not in subset_text
        assert 'local labels for this returned subset, not original gel numbering' in subset_text
    finally:store.close()
