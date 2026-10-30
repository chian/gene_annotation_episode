"""Requested saved facts: retained native measurements, synthetic commissioning.

No new producer job is executed. Saved provider examples preserve complete
numerical records; wrap_saved supplies explicitly synthetic bundle selection
envelopes for provider examples that predate the adapter.
"""
from copy import deepcopy
from functools import lru_cache
import builtins
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_alignment_bundle_contracts as c
from gene_annotation_episode import bvbrc_alignment_bundle_projection as p
from test_bvbrc_alignment_bundle_resolution import (
    basic_fixture, msa_native_fixture, meta_fixture, meta_native_fixture,
    xmfa_native_fixture, cross_family_fixture, slot,
)

ROOT = Path(__file__).resolve().parents[1]
MSA = ROOT / 'verification/tool_graders_bvbrc_msa_sheet_2026-10-25/filled_examples_009'
META = ROOT / 'verification/tool_graders_bvbrc_metacats_provider_2026-10-25/EXAMPLES_001'


def unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(deepcopy(row))
    return result


def wrap_saved(sheet, components, provider='msa'):
    """Retain scientific data; add a labelled synthetic original selector."""
    sheet, components = deepcopy(sheet), deepcopy(components)
    aid = sheet['analysis']['analysis_id']; refs = {}; tree_refs = {}; selections = []; slots = []
    for index, doc in enumerate(sheet['documents']):
        value, kind = doc['value'], doc['kind']
        did = value.get('alignment_id', value.get('table_id', value.get('document_id')))
        existing = next((r for r in sheet['read_outcomes'] if did in r['document_ids']), None)
        sid = existing['slot_id'] if existing else 'saved:' + str(index)
        if kind == 'xmfa':
            sid = sheet['analysis']['full_xmfa_slot_id']
        ref = slot(aid, sid); refs[did] = ref
        if existing:
            reader = existing['reader']
        elif kind == 'alignment':
            reader = {'reader': 'aligned_fasta', 'id_rule': 'first_whitespace_token', 'encoding': value['encoding']}
        elif kind == 'tree':
            reader = {'reader': 'newick', 'dialect': value['dialect'], 'allow_multiple': True}
        elif kind == 'msa_frequency':
            reader = {'reader': 'msa_frequency', **{k: value[k] for k in ('alphabet','layout','encoding')}}
        elif kind in ('metacats_chisq','metacats_pair','metacats_raw_r'):
            reader = {'reader': kind, **{k: value[k] for k in ('layout','category_id','encoding')}}
            if kind == 'metacats_raw_r': reader['kind'] = value['kind']
        elif kind == 'metadata':
            reader = {'reader': 'metacats_metadata', **{k: value[k] for k in ('header','delimiter','encoding')}}
        elif kind == 'adjusted_matrix':
            reader = {'reader': 'metacats_adjusted_matrix', **{k: value[k] for k in ('category_id','encoding')}}
        else:
            raise AssertionError(kind)
        semantic = {'alignment':'alignment','tree':'tree','msa_frequency':'msa_frequency','metadata':'metadata',
            'metacats_chisq':'chisq_export','metacats_pair':'pair_export','adjusted_matrix':'adjusted_matrix','xmfa':'full_xmfa'}.get(kind)
        if kind == 'metacats_raw_r': semantic = 'raw_r_' + value['kind']
        original = {'analysis_id': aid,'slot_id': sid,'semantic_role': semantic,
            'source': {'kind':'acquired_role','bundle_role':'synthetic:saved:' + sid},'reader':reader}
        slots.append(original)
        tids = []
        if kind == 'tree':
            for tree in value['trees']:
                tree_refs[tree['tree_id']] = {**ref,'tree_index':tree['tree_index']}; tids.append(tree['tree_id'])
        selections.append({**deepcopy(original), 'state':'resolved','artifacts':[value['artifact']],
            'content_bindings':[],'acquisition_receipt_refs':[],'document_ids':[did], 'tree_ids':tids,
            'requirement_ids':[],'diagnostics':[]})
        if not existing:
            sheet['read_outcomes'].append({'read_id':'synthetic:saved:'+sid,'slot_id':sid,'artifact':value['artifact'],
                'reader':deepcopy(reader),'status':'ok','document_ids':[did],'diagnostics':[]})
    def reference(identity):
        return deepcopy(tree_refs[identity] if identity in tree_refs else refs[identity])
    analysis = deepcopy(sheet['analysis'])
    for key in ('alignment_id','frequency_table_id','consensus_alignment_id','xmfa_document_id','tree_id','metadata_document_id'):
        if key in analysis and analysis[key] is not None: analysis[key] = reference(analysis[key])
    for key in ('adjusted_matrix_ids','chisq_table_ids','pair_table_ids','raw_r_table_ids'):
        if key in analysis: analysis[key] = [reference(v) for v in analysis[key]]
    if analysis.get('reference') is not None:
        analysis['reference']['alignment_id'] = reference(analysis['reference']['alignment_id'])
    populations = []
    for pop in sheet['populations']['alignments']:
        populations.append({'kind':'alignment_subset','population_id':pop['population_id'],'alignment':reference(pop['alignment_id']),
            **{k:deepcopy(pop[k]) for k in ('row_indices','columns_0based','completeness','evidence')}})
    for kind in ('composition','taxonomy'):
        populations += [{'kind':kind,'population':deepcopy(pop)} for pop in sheet['populations'][kind]]
    populations += [{'kind':'whole_tree','population_id':pop['population_id'],'tree':reference(pop['tree_id'])} for pop in sheet['populations']['leaves']]
    params = deepcopy(components['parameters'])
    for request in params['requests']:
        for key in ('alignment_id','observed_table_id','document_id','gene_tree_id','organismal_tree_id'):
            if key in request and request[key] is not None: request[key] = reference(request[key])
        if request['kind'] == 'msa_reference_differences': request['reference']['alignment_id'] = reference(request['reference']['alignment_id'])
        if request['kind'] == 'relationship_comparison':
            for row in request['injective_tip_join']:
                for key in ('gene_tree_id','organismal_tree_id'): row[key] = reference(row[key])
        if request['kind'].startswith('xmfa_') and 'selection' in request:
            request['selection']['document_id'] = reference(request['selection']['document_id'])
        if request['kind'] == 'multiplicity' and request['p_values']['kind'] == 'native_tables':
            request['p_values']['table_ids'] = [reference(v) for v in request['p_values']['table_ids']]
    parameters = {'version':'bvbrc_alignment_bundle_parameters_v1','artifact_selection':slots,
        'analyses':[{'analysis':analysis,'population_plans':populations,'scientific_inputs':[],
            'read_parameters':{'source_dialect':'retained_bvbrc_'+provider},'calculation_parameters':params}], 'multiplicity_families':[]}
    requirements = unique(sheet['requirements'] + components['requirements'])
    diagnostics = unique(sheet['diagnostics'] + components['diagnostics'])
    return {'parameters':parameters,'provider':provider,'missing_requirements':tuple(requirements),'diagnostics':tuple(diagnostics),
        'sheet_set':{'schema_version':'bvbrc_alignment_sheet_set_v1','tool':sheet['tool'],'selections':selections,
            'analyses':[{'analysis_id':aid,'status':'partial' if requirements else 'ok','sheet':sheet,'requirements':requirements,'diagnostics':diagnostics}]},
        'component_set':{'schema_version':'bvbrc_alignment_component_set_v1','analyses':[{'analysis_id':aid,'components':components}],'multiplicity_families':[]}}


@lru_cache(None)
def saved(case, provider='msa'):
    if provider == 'msa':
        value = json.loads((MSA / (case+'.answer.json')).read_text())
        return wrap_saved(value['parse_result']['value'],value['components'])
    sheet = json.loads((META / (case+'-sheet.json')).read_text())
    components = json.loads((META / (case+'-components.json')).read_text())
    return wrap_saved(sheet,components,'metacats')


def operands(fixture):
    result = fixture.consume({})
    assert result['sheet'] is not None, result
    return {'parameters':fixture.parameters,'provider':fixture.provider,'sheet_set':result['sheet'],'component_set':result['components'],
        'missing_requirements':tuple(result['missing_requirements']),'diagnostics':tuple(result['diagnostics'])}


def project(args, fields):
    form = c.requested_form_schema(fields,provider=args['provider'])
    answer = p.project_requested_facts(**args,requested_form=form)
    assert p.validate_projected_facts(answer,**args,requested_form=form) == answer
    return answer


def selection(kind, aid, rid, **kwargs):
    return {'kind':kind,'analysis_id':aid,'request_id':rid,**kwargs}


def values(args):
    comp = args['component_set']['analyses'][0]['components']
    return comp['analysis_id'], {r['request_id']:r['value'] for r in comp['results']}, comp['parameters']['requests']


def metric_fields(args):
    aid, results, requests = values(args); fields = {}
    for request in requests:
        kind, rid = request['kind'], request['request_id']; value = results[rid]
        if value is None: continue
        for metric, spec in c.MEASUREMENT_CATALOG.items():
            if kind not in spec['request_kinds']: continue
            keys = set(spec['selector']['properties']); selector = {}
            if 'test' in keys:
                rows = value['rows'] if kind == 'expected_adequacy' else value['omnibus'] + value['pairs']
                if not rows: continue
                row = rows[-1]; selector['test'] = {k:row[k] for k in ('column_0based','kind','group_ids')} | {'category_id':value['category_id']}
            if 'column_0based' in keys:
                if not value['sites']: continue
                selector['column_0based'] = value['sites'][0]['column_0based']
            if 'row_index' in keys:
                rows = value['counts'] if kind == 'msa_reference_differences' else value['rows']
                if not rows: continue
                selector['row_index'] = rows[0]['row_index']
                if 'member_id' in keys: selector.update(rows[0]['member'])
                if 'category' in keys: selector['category'] = rows[0]['category']
            if 'row_a' in keys:
                if not value['pairs']: continue
                selector.update({k:value['pairs'][0][k] for k in ('row_a','row_b')})
            if 'group_ids' in keys:
                pairs=value['sites'][0]['pairs']
                if not pairs: continue
                selector['group_ids'] = pairs[0]['group_ids']
                if 'symbol' in keys:
                    if not pairs[0]['frequency_deltas']: continue
                    selector['symbol'] = pairs[0]['frequency_deltas'][0]['symbol']
            for key, collection in (('function_key','rows'),('taxon_id','rows'),('node_index','branches')):
                if key in keys:
                    if not value[collection]: break
                    selector[key] = value[collection][0][key]
            if 'node_a' in keys:
                if not value['distances']: continue
                selector.update({k:value['distances'][0][k] for k in ('node_a','node_b')})
            if set(selector) != keys: continue
            fields[rid+'|'+metric] = selection('measurement',aid,rid,metric=metric,selector=selector)
    return fields


@pytest.mark.parametrize('case,provider', [('dna','msa'),('protein','msa'),('reference','msa'),('original_coverage','msa'),('composition','msa'),('trees','msa'),('aa_two_groups','metacats'),('aa_three_groups','metacats')])
def test_every_metric_family_copies_actual_cells(case,provider):
    args=saved(case,provider); fields=metric_fields(args); facts=project(args,fields)
    assert facts and set(facts)==set(fields)
    for fact in facts.values():
        assert fact['method_ref'] is not None
        assert c.decode_reference(fact['method_ref'])[0]=='method'


def test_all_catalog_metrics_are_exercised():
    args=operands(basic_fixture())
    assert project(args,metric_fields(args))['alignment|site_count']['value']==2
    covered={s['metric'] for s in metric_fields(args).values()}
    for case,provider in [('dna','msa'),('reference','msa'),('original_coverage','msa'),('composition','msa'),('trees','msa'),('aa_two_groups','metacats')]:
        covered.update(s['metric'] for s in metric_fields(saved(case,provider)).values())
    assert covered==set(c.MEASUREMENT_CATALOG)


@pytest.mark.parametrize('alphabet,field,row,expected',[('dna',{'kind':'score'},1,92),('dna',{'kind':'n_sequences'},1,3),('dna',{'kind':'dna_count','symbol':'Deletion'},1,1),('protein',{'kind':'protein_count','detail_index':0},3,2)])
def test_exact_native_msa_row_and_field(alphabet,field,row,expected):
    args=operands(msa_native_fixture(alphabet))
    selected={'kind':'native_measurement','analysis_id':'analysis','table':slot('analysis','frequency'),'row_index':row,'field':field}
    fact=project(args,{'number':selected})['number']
    assert fact['value']==expected
    assert fact['method_ref'] is None and fact['origin']=='native_observation'


@pytest.mark.parametrize('case',['official_na','aa_two_groups','aa_three_groups','native_pair_tail_underflow','metadata_only_first_group','all_missing','twelve_groups'])
def test_retained_native_metacats_cases_exact_requested_tests(case):
    args=saved(case,'metacats');aid,results,requests=values(args);fields={}
    for request in requests:
        if request['kind'] not in ('native_statistics','biological_statistics'): continue
        value=results[request['request_id']]
        selected=[] if not value['pairs'] else [{k:value['pairs'][0][k] for k in ('category_id','column_0based','kind','group_ids')}]
        fields[request['request_id']]=selection('statistical_tests',aid,request['request_id'],tests=selected)
    facts=project(args,fields)
    if case=='all_missing': assert all(v==[] for v in facts.values())
    if case=='native_pair_tail_underflow':
        assert all(v[0]['p_value'] is None and v[0]['log_p']==pytest.approx(-2004.3710655188884) for v in facts.values())
        native=next(v[0] for k,v in facts.items() if k.startswith('native'))
        biological=next(v[0] for k,v in facts.items() if k.startswith('biological'))
        assert native['native_zero_rule_p']==1 and biological['native_zero_rule_p'] is None
        assert native['test_ref']!=biological['test_ref']


@pytest.mark.parametrize('reader,field',[('metacats_chisq',{'kind':'chi_square'}),('metacats_chisq',{'kind':'p_value'}),('metacats_chisq',{'kind':'df'}),('metacats_chisq',{'kind':'export_group_count','heading_index':0,'count_index':0}),('metacats_pair',{'kind':'p_value'}),('metacats_raw_r',{'kind':'raw_r_group_count','position_1based':1,'count_index':0})])
def test_native_metacats_field_selectors(reader,field):
    args=saved('aa_two_groups','metacats'); aid,_,_=values(args)
    slotrow=next(s for s in args['parameters']['artifact_selection'] if s['reader']['reader']==reader and (reader!='metacats_raw_r' or s['reader']['kind']=='omnibus'))
    facts=project(args,{'number':{'kind':'native_measurement','analysis_id':aid,'table':slot(aid,slotrow['slot_id']),'row_index':1 if reader=='metacats_raw_r' else 0,'field':field}})
    assert facts['number']['value'] is not None and facts['number']['method_ref'] is None


def test_native_underflow_observation_and_calculated_test_remain_distinct():
    args=saved('native_pair_tail_underflow','metacats');aid,results,requests=values(args)
    slotrow=next(s for s in args['parameters']['artifact_selection'] if s['reader']['reader']=='metacats_raw_r' and s['reader']['kind']=='pairwise')
    req=next(r for r in requests if r['kind']=='native_statistics'); test=results[req['request_id']]['pairs'][0]
    fields={'observed':{'kind':'native_measurement','analysis_id':aid,'table':slot(aid,slotrow['slot_id']),'row_index':1,'field':{'kind':'p_value'}},
        'calculated':selection('statistical_tests',aid,req['request_id'],tests=[{k:test[k] for k in ('category_id','column_0based','kind','group_ids')}])}
    facts=project(args,fields)
    assert facts['observed']['value']==1 and facts['calculated'][0]['p_value'] is None


@pytest.mark.parametrize('case',['reference','composition','trees'])
def test_nonmeasurement_fact_families(case):
    args=saved(case);aid,results,requests=values(args);fields={}
    if case=='reference':
        req=requests[0];fields['differences']=selection('reference_differences',aid,req['request_id'],row_indices=req['member_row_indices'],columns_0based=[0,1])
    elif case=='composition':
        fields['functions']=selection('function_composition',aid,requests[0]['request_id'],function_keys=[r['function_key'] for r in results[requests[0]['request_id']]['rows']])
    else:
        fields['branches']=selection('tree_branches',aid,'tree',node_indices=[r['node_index'] for r in results['tree']['branches']])
    assert next(iter(project(args,fields).values()))


def test_sites_group_counts_and_known_absent_symbol_zero():
    args=operands(msa_native_fixture());fact=project(args,{'sites':selection('msa_sites','analysis','entropy',columns_0based=[1,2])})['sites']
    assert [r['native_score_recalculated'] for r in fact]==[92,81]
    assert fact[0]['literal_entropy_bits']==pytest.approx(.9182958340544896)
    args=operands(meta_fixture());groups=['metacats_group:category/B','metacats_group:category/C']
    fact=project(args,{'counts':selection('group_counts','analysis','counts',columns_0based=[1],group_ids=groups,symbols=['C','T','Z'])})['counts']
    assert [r['count'] for r in fact]==[1,0,0,0,1,0]


@pytest.mark.parametrize('case',['xmfa','xmfa_missing_sources','source_distinct_original_occurrences','source_one_missing_source'])
def test_all_four_xmfa_routes_and_all_three_coverage_bases(case):
    args=saved(case);aid,results,requests=values(args);fields={}
    for request in requests:
        rid=request['request_id'];kind=request['kind']
        if kind=='xmfa_column_coordinates': fields[rid]=selection('xmfa_coordinates',aid,rid,cells=request['cells'])
        elif kind=='xmfa_source_positions': fields[rid]=selection('xmfa_source_positions',aid,rid,queries=request['queries'])
        elif kind=='xmfa_interval_coverage': fields[rid]=selection('xmfa_coverage',aid,rid,member_numbers=request['selection']['member_numbers'],include_intervals=True,include_original_coverage=True)
        else:
            block=results[rid]['blocks'][0]; site=block['sites'][0]
            metrics=[{'metric':k,'block_index':block['block_index']} for k in ('selected_column_count','present_member_count','zero_member_count','omitted_member_count')]
            metrics += [{'metric':k,'block_index':block['block_index'],'column_0based':site['column_0based']} for k in ('site_present_member_count','absent_member_count','gap_count','nongap_count','canonical_count','ambiguity_count','other_count','literal_entropy_bits','canonical_entropy_bits','canonical_majority_fraction')]
            metrics += [{'metric':'symbol_count','block_index':block['block_index'],'column_0based':site['column_0based'],'symbol':site['symbol_counts'][0]['symbol']}]
            metrics += [{'metric':k,'block_index':block['block_index'],'member_a':1,'member_b':3} for k in ('identical_canonical','substitutions','a_only_gap','b_only_gap','both_gap','ambiguous_or_other','comparable_canonical','identity_fraction')]
            fields[rid]=selection('xmfa_alignment_measurements',aid,rid,measurements=metrics)
    facts=project(args,fields)
    if case=='xmfa':
        assert [r['known_union_bases'] for r in facts['represented']]==[50,41,49]
        assert [r['known_union_bases'] for r in facts['multi_member_block']]==[48,0,47]
        assert [r['known_union_bases'] for r in facts['cooccupied_column']]==[46,0,46]
        assert [r['native_position_0based'] for r in facts['xmfa_column_coordinates']]==[48,None,1]
        assert [r['native_position_1based'] for r in facts['xmfa_column_coordinates']]==[49,None,2]
        pair={r['selection']['metric']:r['measurement']['value'] for r in facts['xmfa_alignment_components'] if r['selection']['member_a'] is not None}
        assert pair['identical_canonical']==39 and pair['substitutions']==7 and pair['comparable_canonical']==46
    if case=='xmfa_missing_sources':
        assert facts['represented'][0]['source_length'] is None
        assert facts['represented'][0]['known_union_bases']==50


def test_native_full_xmfa_bundle_selected_facts():
    args=operands(xmfa_native_fixture())
    fact=project(args,{'coverage':selection('xmfa_coverage','analysis','represented',member_numbers=[1],include_intervals=False,include_original_coverage=False)})['coverage'][0]
    assert fact['known_union_bases']==50 and fact['known_union_intervals'] is None and fact['original_coverage'] is None


def test_local_and_cross_analysis_multiplicity_selection():
    args=saved('aa_two_groups','metacats'); aid,results,requests=values(args)
    for req in requests:
        if req['kind']!='multiplicity':continue
        fields={'all':{'kind':'multiplicity','analysis_id':aid,'request_id':req['request_id'],'family_request_id':None,'selection':'all_family','tests':[]},
            'empty':{'kind':'multiplicity','analysis_id':aid,'request_id':req['request_id'],'family_request_id':None,'selection':'explicit_tests','tests':[]}}
        facts=project(args,fields);assert facts['all'] and facts['empty']==[]
    args=operands(cross_family_fixture())
    test={'category_id':'category','column_0based':1,'kind':'pairwise','group_ids':['metacats_group:category/B','metacats_group:category/C']}
    base={'kind':'multiplicity','analysis_id':None,'request_id':None,'family_request_id':'both'}
    facts=project(args,{'all':{**base,'selection':'all_family','tests':[]},'one':{**base,'selection':'explicit_tests','tests':[{'analysis_id':'second','test':test}]},'empty':{**base,'selection':'explicit_tests','tests':[]}})
    assert len(facts['all'])==2 and len(facts['one'])==1 and facts['empty']==[]
    assert c.decode_reference(facts['one'][0]['test_ref'])[1]=='second'
    assert c.decode_reference(facts['one'][0]['family_ref'])[1]=='@families'


@pytest.mark.parametrize('change',['value','method','unit','population','requirement','extra_field','null','selector'])
def test_forged_saved_facts_are_rejected(change):
    args=operands(basic_fixture());fields={'count':selection('measurement','analysis','alignment',metric='member_count',selector={})}
    form=c.requested_form_schema(fields,provider='msa');facts=p.project_requested_facts(**args,requested_form=form)
    if change=='value':facts['count']['value']=3
    elif change=='method':facts['count']['method_ref']=None
    elif change=='unit':facts['count']['unit']='columns'
    elif change=='population':facts['count']['population_ref']=c.encode_reference('population','sibling','whole')
    elif change=='requirement':facts['count']['requirement_refs']=[c.encode_reference('requirement','@requirements','invented')]
    elif change=='extra_field':facts['extra']={}
    elif change=='null':facts['count']=None
    else:form['properties']['count']['x-alignment-fact']['request_id']='absent'
    with pytest.raises(ValueError):p.validate_projected_facts(facts,**args,requested_form=form)


@pytest.mark.parametrize('field',[selection('measurement','other','alignment',metric='member_count',selector={}),selection('measurement','analysis','missing',metric='member_count',selector={}),selection('measurement','analysis','alignment',metric='site_gap_count',selector={'column_0based':9}),selection('measurement','analysis','alignment',metric='row_nongap_count',selector={'row_index':3}),selection('measurement','analysis','alignment',metric='pair_identity_fraction',selector={'row_a':1,'row_b':0}),selection('msa_sites','analysis','alignment',columns_0based=[])])
def test_unknown_analysis_request_wrong_kind_and_population_rejected(field):
    with pytest.raises(ValueError):project(operands(basic_fixture()),{'bad':field})


def test_missing_quarantined_original_request_and_exact_requirement_references():
    f=basic_fixture();plan=f.plan();plan['analysis']['reference']={'alignment_id':slot('analysis','alignment'),'row_index':0,'original_member':None,'native_ref_type':'first','native_ref_string':None,'identity_state':'resolved','evidence':[]}
    plan['calculation_parameters']['requests'].append({'kind':'msa_reference_differences','request_id':'difference','population_id':'whole','reference':deepcopy(plan['analysis']['reference']),'member_row_indices':[1],'alphabet':'dna','case_policy':'uppercase'})
    f.bundle['artifacts']=[];f.raw={};args=operands(f)
    fields={'count':selection('measurement','analysis','alignment',metric='member_count',selector={}),
        'difference':selection('reference_differences','analysis','difference',row_indices=[1],columns_0based=[0]),'requirements':{'kind':'missing_requirements'},
        'qualifications':{'kind':'qualifications','analysis_id':'analysis','slot_id':None,'request_id':'difference'}}
    facts=project(args,fields)
    assert facts['count']['value'] is None and facts['count']['method_ref'] is None and facts['difference'] is None
    assert facts['count']['requirement_refs']
    refs={f['requirement_ref'] for f in facts['requirements']}
    assert set(facts['count']['requirement_refs'])<=refs
    assert all(c.decode_reference(r)[1]=='@requirements' for r in refs)
    bad=deepcopy(args);bad['missing_requirements']=tuple(r for r in bad['missing_requirements'] if r['role']!='difference')
    with pytest.raises(ValueError):project(bad,fields)


@pytest.mark.parametrize('kind,extra',[('msa_sites',{'columns_0based':[]}),('reference_differences',{'row_indices':[],'columns_0based':[]}),('function_composition',{'function_keys':[]}),('tree_branches',{'node_indices':[]})])
def test_explicit_empty_collections_never_select_all(kind,extra):
    case,rid={'msa_sites':('dna','msa_entropy'),'reference_differences':('reference','msa_reference_differences'),'function_composition':('composition','function_composition'),'tree_branches':('trees','tree')}[kind]
    args=saved(case);aid,_,_=values(args)
    assert project(args,{'empty':selection(kind,aid,rid,**extra)})['empty']==[]


def test_partial_counts_are_null_not_zero():
    args=operands(meta_fixture(data=b'>a\nAC\n>b\nA\n'))
    facts=project(args,{'counts':selection('group_counts','analysis','counts',columns_0based=[1],group_ids=['metacats_group:category/B'],symbols=['Z'])})
    assert facts['counts'][0]['count'] is None and facts['counts'][0]['requirement_refs']


@pytest.mark.parametrize('defect',['category','group','column','pair_order'])
def test_statistical_selector_relationship_rejections(defect):
    args=saved('aa_three_groups','metacats');aid,results,requests=values(args);req=next(r for r in requests if r['kind']=='biological_statistics')
    row=results[req['request_id']]['pairs'][0];test={k:deepcopy(row[k]) for k in ('category_id','column_0based','kind','group_ids')}
    if defect=='category':test['category_id']='other'
    if defect=='group':test['group_ids'][0]='other'
    if defect=='column':test['column_0based']=999
    if defect=='pair_order':test['group_ids'].reverse()
    with pytest.raises(ValueError):project(args,{'test':selection('statistical_tests',aid,req['request_id'],tests=[test])})


@pytest.mark.parametrize('defect',['row','field','native_alphabet','observation','original_mode','saved_population','saved_request'])
def test_native_and_saved_identity_forgeries(defect):
    args=deepcopy(operands(msa_native_fixture()));selected={'kind':'native_measurement','analysis_id':'analysis','table':slot('analysis','frequency'),'row_index':1,'field':{'kind':'score'}}
    if defect=='row':selected['row_index']=99
    elif defect=='field':selected['field']={'kind':'p_value'}
    elif defect=='native_alphabet':selected['field']={'kind':'protein_count','detail_index':0}
    elif defect=='observation':
        obs=next(o for o in args['sheet_set']['analyses'][0]['sheet']['native_observations'] if o['row_index']==1 and o['field']=='msa_score');obs['number']['value']=91
    elif defect=='original_mode':args['sheet_set']['analyses'][0]['sheet']['analysis']['mode']='segment_alignment'
    elif defect=='saved_population':args['component_set']['analyses'][0]['components']['results'][0]['value']['population_id']='other'
    else:args['component_set']['analyses'][0]['components']['parameters']['requests'][0]['alphabet']='protein'
    with pytest.raises(ValueError):project(args,{'native':selected})


@pytest.mark.parametrize('defect',['cell','member','block','column','pair','symbol','mode'])
def test_xmfa_selected_identity_rejections(defect):
    args=deepcopy(saved('xmfa'));aid,_,_=values(args)
    chosen=selection('xmfa_alignment_measurements',aid,'xmfa_alignment_components',measurements=[{'metric':'identical_canonical','block_index':0,'member_a':1,'member_b':3}])
    if defect=='cell':chosen=selection('xmfa_coordinates',aid,'xmfa_column_coordinates',cells=[{'block_index':0,'record_index':1,'column_0based':0}])
    elif defect=='member':chosen=selection('xmfa_coverage',aid,'represented',member_numbers=[9],include_intervals=False,include_original_coverage=False)
    elif defect=='block':chosen['measurements'][0]['block_index']=99
    elif defect=='column':chosen['measurements']=[{'metric':'gap_count','block_index':0,'column_0based':99}]
    elif defect=='pair':chosen['measurements'][0].update(member_a=3,member_b=1)
    elif defect=='symbol':chosen['measurements']=[{'metric':'symbol_count','block_index':0,'column_0based':0,'symbol':'Z'}]
    else:args['sheet_set']['analyses'][0]['sheet']['analysis']['mode']='mauve_first_block_projection'
    with pytest.raises(ValueError):project(args,{'bad':chosen})


def test_pure_saved_validation_with_io_parsers_and_calculators_blocked(monkeypatch):
    args=saved('xmfa');aid,_,_=values(args)
    fields={'coordinates':selection('xmfa_coordinates',aid,'xmfa_column_coordinates',cells=[{'block_index':0,'record_index':0,'column_0based':0}]),
        'coverage':selection('xmfa_coverage',aid,'represented',member_numbers=[1],include_intervals=True,include_original_coverage=True)}
    form=c.requested_form_schema(fields,provider='msa');facts=p.project_requested_facts(**args,requested_form=form)
    import gene_annotation_episode.bvbrc_msa_grader as grader
    import gene_annotation_episode.bvbrc_msa_formats as readers
    import gene_annotation_episode.xmfa_calculators as math
    import gene_annotation_episode.xmfa_coordinates as coordinates
    import gene_annotation_episode.bvbrc_msa_provider_contracts as validators
    def forbidden(*args,**kwargs):raise AssertionError('saved projection attempted I/O, parsing or calculation')
    for obj,name in [(builtins,'open'),(Path,'open'),(Path,'read_bytes'),(Path,'read_text'),(socket,'socket'),(subprocess,'run'),(subprocess,'Popen'),(grader,'calculate_msa'),(readers,'parse_msa_frequency_table'),(math,'xmfa_alignment_components'),(math,'xmfa_interval_coverage'),(coordinates,'xmfa_column_coordinates'),(coordinates,'xmfa_source_positions'),(validators,'validate_msa_components')]:monkeypatch.setattr(obj,name,forbidden)
    assert p.project_requested_facts(**args,requested_form=form)==facts
    assert p.validate_projected_facts(facts,**args,requested_form=form)==facts
    facts['coverage'][0]['known_union_bases']=49
    with pytest.raises(ValueError):p.validate_projected_facts(facts,**args,requested_form=form)


def test_detachment_and_original_source_refs_are_preserved():
    args=operands(basic_fixture());before=deepcopy(args)
    facts=project(args,{'requirements':{'kind':'missing_requirements'},'qualifications':{'kind':'qualifications','analysis_id':'analysis','slot_id':None,'request_id':None}})
    assert args==before
    assert [r['source_refs'] for r in facts['requirements']]==[r['source_refs'] for r in args['missing_requirements']]
    facts['requirements'].clear();assert args==before


@pytest.mark.parametrize('case,field',[('blank',{'kind':'dna_count','symbol':'T'}),('native_na',{'kind':'score'})])
def test_actual_native_missing_tokens_are_not_measured_zero(case,field):
    args=saved(case);aid,_,_=values(args)
    selected=next(s for s in args['parameters']['artifact_selection'] if s['reader']['reader']=='msa_frequency')
    fact=project(args,{'native':{'kind':'native_measurement','analysis_id':aid,'table':slot(aid,selected['slot_id']),'row_index':0,'field':field}})['native']
    assert fact['value'] is None and fact['state']!='available' and fact['method_ref'] is None


@pytest.mark.parametrize('case',['ragged_alignment','empty_population','incomplete_original_map'])
def test_partial_and_empty_saved_measurements_keep_states_and_denominators(case):
    args=saved(case);fields=metric_fields(args)
    if case=='incomplete_original_map':
        for selected in fields.values():selected['selector'].update(row_index=1,member_id='b')
    facts=project(args,fields)
    assert facts
    if case=='ragged_alignment':assert any(v['value'] is None and v['requirement_refs'] for v in facts.values())
    if case=='empty_population':
        assert facts['alignment|member_count']['value']==0
        assert facts['alignment|gap_fraction']['value'] is None
    if case=='incomplete_original_map':assert any(v['value'] is None and v['requirement_refs'] for v in facts.values())


@pytest.mark.parametrize('kind,extra',[('xmfa_coordinates',{'cells':[]}),('xmfa_source_positions',{'queries':[]}),('xmfa_alignment_measurements',{'measurements':[]}),('xmfa_coverage',{'member_numbers':[],'include_intervals':True,'include_original_coverage':True})])
def test_explicit_empty_xmfa_selectors(kind,extra):
    args=saved('xmfa');aid,_,_=values(args)
    rid={'xmfa_coordinates':'xmfa_column_coordinates','xmfa_source_positions':'xmfa_source_positions','xmfa_alignment_measurements':'xmfa_alignment_components','xmfa_coverage':'represented'}[kind]
    assert project(args,{'empty':selection(kind,aid,rid,**extra)})['empty']==[]


@pytest.mark.parametrize('defect',['missing_result','foreign_cell_population','foreign_native_id','wrong_test_category','wrong_effect_raw_table'])
def test_saved_cells_must_belong_to_actual_requested_results(defect):
    if defect in ('wrong_test_category','wrong_effect_raw_table'):
        args=deepcopy(saved('aa_two_groups','metacats'));aid,results,requests=values(args)
        req=next(r for r in requests if r['kind']==('biological_statistics' if defect=='wrong_test_category' else 'biological_effects'))
        if defect=='wrong_test_category':results[req['request_id']]['pairs'][0]['category_id']='other'
        else:results[req['request_id']]['sites'][0]['raw_table_id']='other'
        fields=metric_fields(args)
    else:
        args=deepcopy(operands(msa_native_fixture()));comp=args['component_set']['analyses'][0]['components']
        fields={'value':selection('measurement','analysis','alignment',metric='member_count',selector={})}
        if defect=='missing_result':comp['results'].pop(0)
        elif defect=='foreign_cell_population':comp['results'][0]['value']['member_count']['population_ref']='other'
        else:
            obs=next(o for o in args['sheet_set']['analyses'][0]['sheet']['native_observations'] if o['row_index']==1 and o['field']=='msa_score');obs['observation_id']='other'
            fields={'value':{'kind':'native_measurement','analysis_id':'analysis','table':slot('analysis','frequency'),'row_index':1,'field':{'kind':'score'}}}
    with pytest.raises(ValueError):project(args,fields)


def test_empty_filtered_native_export_does_not_return_fake_row():
    args=saved('native_pair_tail_underflow','metacats');aid,_,_=values(args)
    selected=next(s for s in args['parameters']['artifact_selection'] if s['reader']['reader']=='metacats_pair')
    with pytest.raises(ValueError):project(args,{'bad':{'kind':'native_measurement','analysis_id':aid,'table':slot(aid,selected['slot_id']),'row_index':0,'field':{'kind':'p_value'}}})


def test_noncanonical_saved_refs_and_nonfinite_numbers_are_rejected():
    args=operands(basic_fixture());fields={'value':selection('measurement','analysis','alignment',metric='member_count',selector={})};form=c.requested_form_schema(fields,provider='msa')
    facts=p.project_requested_facts(**args,requested_form=form)
    facts['value']['population_ref']='bvbrc_alignment_population:analysis/%77hole'
    with pytest.raises(ValueError):p.validate_projected_facts(facts,**args,requested_form=form)
    facts=p.project_requested_facts(**args,requested_form=form);facts['value']['value']=float('nan')
    with pytest.raises(ValueError):p.validate_projected_facts(facts,**args,requested_form=form)


def test_forged_numerical_fact_rejected_without_recomputing_scientific_formula(monkeypatch):
    args=saved('dna');aid,_,_=values(args)
    form=c.requested_form_schema({'entropy':selection('measurement',aid,'msa_entropy',metric='literal_entropy_bits',selector={'column_0based':1})},provider='msa')
    facts=p.project_requested_facts(**args,requested_form=form)
    import math
    def forbidden(*args,**kwargs):raise AssertionError('scientific formula invoked')
    for name in ('log','log2','sqrt','exp','fsum'):monkeypatch.setattr(math,name,forbidden)
    assert p.validate_projected_facts(facts,**args,requested_form=form)==facts
    facts['entropy']['value']=0.9
    with pytest.raises(ValueError):p.validate_projected_facts(facts,**args,requested_form=form)


@pytest.mark.parametrize('symbol',['','AA',' ','\t','µ'])
def test_scientific_symbol_selector_is_a_single_printable_ascii_character(symbol):
    args=operands(meta_fixture())
    with pytest.raises(ValueError):project(args,{'bad':selection('group_counts','analysis','counts',columns_0based=[1],group_ids=['metacats_group:category/B'],symbols=[symbol])})


def test_outward_consensus_literal_cannot_be_arbitrary_text():
    args=deepcopy(saved('dna'));aid,results,_=values(args)
    results['msa_entropy']['sites'][0]['strict_majority_consensus']='arbitrary prose'
    with pytest.raises(ValueError):project(args,{'bad':selection('msa_sites',aid,'msa_entropy',columns_0based=[0])})


@pytest.mark.parametrize('symbol',['','AA',' ','\t','µ'])
@pytest.mark.parametrize('missing',[False,True])
def test_frequency_delta_symbol_is_bounded_before_missing_dependency(symbol,missing):
    fixture=meta_fixture()
    if missing:fixture.bundle['artifacts']=[];fixture.raw={}
    args=operands(fixture)
    selected=selection('measurement','analysis','effects',metric='frequency_delta',
        selector={'column_0based':1,'group_ids':['metacats_group:category/B','metacats_group:category/C'],'symbol':symbol})
    with pytest.raises(ValueError):project(args,{'bad':selected})


def test_valid_frequency_delta_symbol_retains_missing_dependency():
    fixture=meta_fixture();fixture.bundle['artifacts']=[];fixture.raw={}
    selected=selection('measurement','analysis','effects',metric='frequency_delta',
        selector={'column_0based':1,'group_ids':['metacats_group:category/B','metacats_group:category/C'],'symbol':'A'})
    fact=project(operands(fixture),{'missing':selected})['missing']
    assert fact['value'] is None and fact['method_ref'] is None and fact['requirement_refs']
