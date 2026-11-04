"""Full provider native numerical examples and strict saved-record boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest

from gene_annotation_episode import bvbrc_msa_provider_contracts as c
from gene_annotation_episode.bvbrc_msa_inputs import extract_msa_sheet
from gene_annotation_episode.bvbrc_msa_grader import calculate_msa
from gene_annotation_episode.bvbrc_alignment_provider_contracts import ASSOCIATION_KEYS
from gene_annotation_episode.bvbrc_msa_formats import parse_msa_frequency_table
from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta, parse_newick
from gene_annotation_episode.bvbrc_msa_format_contracts import frequency_header
from gene_annotation_episode.bvbrc_msa_xmfa_inputs import verify_xmfa_source_inputs, extract_msa_xmfa_bindings

ROOT=Path(__file__).resolve().parents[1]
NATIVE=ROOT/'verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25/native_examples'
ASSOCIATIONS=ROOT/'verification/tool_graders_bvbrc_alignment_associations_2026-10-25/EXAMPLES_001'
XMFA=ROOT/'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'
SOURCES=ROOT/'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples'


def artifact(data,name):
    return {'raw_artifact_ref':name,'source_ref':'source:'+name,'sha256':hashlib.sha256(data).hexdigest()}


def evidence(data=b'actual test declaration',name='declaration'):
    a=artifact(data,name)
    return {'content':{'artifact_ref':name,'artifact_field':'artifact_ref','source_ref':a['source_ref'],'sha256':a['sha256'],'byte_count':len(data)},'pointer':''}


def alignment(data=b'>a\nAC\n>b\nAT\n',name='aligned'):
    return parse_aligned_fasta(data,artifact=artifact(data,name),id_rule='first_whitespace_token',encoding='ascii')['value']


def population(al, rows=None, columns=None, name='all'):
    return {'population_id':name,'alignment_id':al['alignment_id'],'row_indices':list(range(len(al['rows']))) if rows is None else rows,
        'columns_0based':list(range(al['observed_column_count'] or max((len(r['sequence']) for r in al['rows']),default=0))) if columns is None else columns,
        'completeness':al['completeness'],'evidence':[]}


def request(kind,**kwargs):
    return {'kind':kind,'request_id':kind,**kwargs}


def parameters(*requests):
    return {'version':c.VERSION,'requests':list(requests)}


def entropy_request(alphabet='dna',table=None,**changes):
    return request('msa_entropy',population_id='all',alphabet=alphabet,case_policy='uppercase',terminal_gap='-',observed_table_id=table['table_id'] if table else None,native_rounding='binary64_fixed_2_ties_to_even')|changes


def operands(al=None,table=None,consensus=None,*,mode='ordinary_new_alignment',documents=None,associations=None,inputs=(),segments=(),reference=None):
    al=alignment() if al is None and documents is None else al
    docs=list(documents or ([] if al is None else [{'kind':'alignment','value':al}]))
    if table: docs.append({'kind':'msa_frequency','value':table})
    if consensus: docs.append({'kind':'alignment','value':consensus})
    return {'analysis':{'analysis_id':'analysis','mode':mode,'alignment_id':al['alignment_id'] if al else None,'frequency_table_id':table['table_id'] if table else None,
        'consensus_alignment_id':consensus['alignment_id'] if consensus else None,'tree_id':None,'full_xmfa_slot_id':None,'xmfa_document_id':None,'segment_ids':[r['segment_id'] for r in segments],
        'reference':reference,'output_role_evidence':[]},'inputs':inputs,'documents':tuple(docs),'read_outcomes':(),
        'run':{'original_task_id':'task','settings':[],'commands':[],'versions':[],'conflicts':[],'completeness':'unknown'},
        'associations':associations or {k:[] for k in ASSOCIATION_KEYS},'populations':{'alignments':[population(al)] if al else [],'composition':[],'taxonomy':[],'leaves':[]},
        'segments':segments,'tree_bindings':(),'parameters':{'source_dialect':'retained_bvbrc_msa'},'xmfa_bindings':()}


def make(**kwargs):
    result=extract_msa_sheet(**operands(**kwargs)); assert result['value'] is not None,result
    return result['value']


def native_operands(alphabet='dna'):
    al=alignment((NATIVE/alphabet/'output.afa').read_bytes(),alphabet+'.afa')
    data=(NATIVE/alphabet/'foma.table').read_bytes()
    table=parse_msa_frequency_table(data,artifact=artifact(data,alphabet+'.table'),alphabet=alphabet,layout='current_without_reference',encoding='ascii')['value']
    cons=alignment((NATIVE/alphabet/'cons.fasta').read_bytes(),alphabet+'.cons.fasta')
    return operands(al,table,consensus=cons),table


def associated_operands(name,mode='ordinary_new_alignment'):
    saved=json.loads((ASSOCIATIONS/(name+'.json')).read_text())
    docs=saved['common_operands']['documents']; al=next(d['value'] for d in docs if d['kind']=='alignment' and d['value']['alignment_id']=='aligned#alignment')
    downstream=saved['downstream_operands'] or {}
    return operands(al,documents=docs,inputs=saved['common_operands']['inputs'],associations=saved['common_result']['value'],mode=mode,
        reference=downstream.get('reference'),segments=downstream.get('segments',[]))


def xmfa_operands(case='combined_native',with_sources=True):
    saved=json.loads((SOURCES/(case+'-inputs.json')).read_text()); doc=saved['document']
    op=operands(documents=[{'kind':'xmfa','value':doc}],mode='mauve_blocks')
    op['analysis'].update(full_xmfa_slot_id='full',xmfa_document_id=doc['document_id'])
    op['read_outcomes']=({'read_id':'xmfa','slot_id':'full','artifact':doc['artifact'],'reader':{'reader':'mauve_xmfa_v1','dialect':'mauve1','alphabet':'dna','encoding':'ascii'},'status':'ok','document_ids':[doc['document_id']],'diagnostics':[]},)
    if with_sources:
        inputs=saved['inputs']; payloads={f['artifact']['raw_artifact_ref']:(XMFA/f['file_id']).read_bytes() for f in inputs['files']}
        contents=tuple({'artifact_ref':f['artifact']['raw_artifact_ref'],'source_ref':f['artifact']['source_ref'],'sha256':f['artifact']['sha256'],'byte_count':len(payloads[f['artifact']['raw_artifact_ref']]),'artifact_field':'artifact_ref'} for f in inputs['files'])
        readers=tuple({'file_id':f['file_id'],'reader':'fasta_records_for_xmfa_v1','id_rule':'first_whitespace_token','encoding':'ascii'} for f in inputs['files'])
        verified=verify_xmfa_source_inputs(inputs,source_readers=readers,artifact_bytes=payloads,content_bindings=contents,associations=op['associations'])
        op['xmfa_bindings']=(extract_msa_xmfa_bindings(doc,verification=verified,source_comparison='case_insensitive_iupac_exact',evidence=()),)
    selection={'population_id':'xmfa-all','document_id':doc['document_id'],'member_numbers':[1,2,3],
        'block_columns':[{'block_index':b['block_index'],'columns_0based':list(range(b['alignment_column_count']))} for b in doc['blocks']],
        'completeness':doc['completeness'],'evidence':[]}
    req=[request('xmfa_alignment_components',document_id=doc['document_id'],selection=selection,selected_pairs=[[1,3]],case_policy='uppercase')]
    for basis in ('represented','multi_member_block','cooccupied_column'):
        req.append(request('xmfa_interval_coverage',document_id=doc['document_id'],selection=selection,use_source_bindings=True,basis=basis)|{'request_id':basis})
    req.append(request('xmfa_column_coordinates',document_id=doc['document_id'],cells=[{'block_index':0,'record_index':0,'column_0based':i} for i in (0,28,48)],use_source_bindings=True))
    req.append(request('xmfa_source_positions',document_id=doc['document_id'],queries=[{'member_number':1,'position_0based':48}],use_source_bindings=True))
    return op,parameters(*req)


@pytest.mark.parametrize('alphabet',['dna','protein'])
def test_native_scores_entropy_and_consensus(alphabet):
    op,table=native_operands(alphabet); parsed=extract_msa_sheet(**op); sheet=parsed['value']; assert sheet is not None,parsed
    result=calculate_msa(sheet,parameters(entropy_request(alphabet,table)))['results'][0]['value']
    assert result is not None
    assert sheet['consensus_associations'][0]['state']=='resolved'
    assert len(sheet['native_observations']) == sum(2+(5 if alphabet=='dna' else len(r['protein_detail'])) for r in table['rows'])
    if alphabet=='dna':
        assert result['sites'][1]['literal_entropy_bits']['value']==pytest.approx(.9182958340544896)
        assert result['sites'][1]['native_score_recalculated']['value']==92
        assert result['sites'][2]['literal_entropy_bits']['value']==pytest.approx(.8112781244591328)
        assert result['sites'][2]['native_score_recalculated']['value']==81
    else:
        assert result['sites'][3]['literal_entropy_bits']['value']==1
        assert result['sites'][3]['strict_majority_consensus']=='X'
        assert table['rows'][3]['score']['value']==100


def test_ordinary_components_with_missing_originals_survive():
    sheet=make(); p=parameters(request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,1]]),request('original_coverage',population_id='all'),request('ungapped_map',alignment_id=sheet['analysis']['alignment_id'],row_indices=[0,1]))
    result=calculate_msa(sheet,p)
    assert result['results'][0]['value']['pairs'][0]['substitutions']['value']==1
    assert result['results'][1]['value'] is None
    assert result['results'][2]['value'][1]['ungapped_position_0based']==1
    assert c.validate_msa_components(json.loads(json.dumps(result)),sheet=sheet)==result


def test_full_row_terminal_masks_subset_and_strict_majority_deletion():
    al=alignment(b'>a\nA--C\n>b\nA--C\n>c\nATGC\n>d\n---C\n')
    op=operands(al); op['populations']['alignments'][0]['columns_0based']=[1]
    sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,parameters(entropy_request()))['results'][0]['value']['sites'][0]
    assert result['included_row_indices']==[0,1,2] and result['excluded_terminal_row_indices']==[3]
    assert result['strict_majority_consensus']=='-' and result['internal_gap_count']['value']==2
    assert result['literal_entropy_bits']['value']==pytest.approx(.9182958340544896)


@pytest.mark.parametrize('kind',['blank','unknown','duplicate','malformed'])
def test_native_partial_tokens_never_overwritten(kind):
    if kind=='unknown':
        data=('\t'.join(frequency_header('protein','current_without_reference'))+'\n1\t0\tFoo\tFoo=2\t2\n').encode(); alpha='protein'
    else:
        line='1\t0\tA\t2\t0\t0\t0\t0\t2\n'
        if kind=='blank': line=line.replace('\t2\t0','\t2\t',1)
        if kind=='malformed': line=line.replace('\t0\tA','\tNA\tA')
        data=('\t'.join(frequency_header('dna','current_without_reference'))+'\n'+line+(line if kind=='duplicate' else '')).encode(); alpha='dna'
    table=parse_msa_frequency_table(data,artifact=artifact(data,'partial'),alphabet=alpha,layout='current_without_reference',encoding='ascii')['value']
    sheet=make(al=alignment(b'>a\nA\n>b\nA\n'),table=table)
    result=calculate_msa(sheet,parameters(entropy_request(alpha,table)))['results'][0]['value']
    assert result['sites'][0]['literal_entropy_bits']['value']==0
    assert next(d['value'] for d in sheet['documents'] if d['kind']=='msa_frequency')==table
    if kind=='duplicate': assert result['sites'][0]['score_residual']['value'] is None
    if kind=='malformed': assert sheet['native_observations'][0]['number']['raw_token']=='NA'


@pytest.mark.parametrize('name',['unique_dna','unique_protein','explicit_reference_identity','duplicate_physical_headers','identical_sequences_ambiguous'])
def test_original_associations_and_reference(name):
    op=associated_operands(name); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; reqs=[request('original_coverage',population_id='all')]
    if op['analysis']['reference']:
        reqs.append(request('msa_reference_differences',population_id='all',reference=op['analysis']['reference'],member_row_indices=[1],alphabet='dna',case_policy='uppercase'))
    result=calculate_msa(sheet,parameters(*reqs))
    if name in ('duplicate_physical_headers','identical_sequences_ambiguous'):
        assert result['results'][0]['value'] is None
    elif name=='explicit_reference_identity':
        value=result['results'][1]['value']; assert value['counts'][0]['count']['value']==1 and value['counts'][1]['count']['value']==1
        assert value['differences'][0]['member_original_correspondence'] is not None


def test_reverse_translated_concatenated_segments_keep_separate_originals():
    op=associated_operands('reverse_translation_concatenation','segment_concatenation'); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; result=calculate_msa(sheet,parameters(request('original_coverage',population_id='all'),entropy_request('protein')))
    assert result['results'][0]['value'] is None
    assert result['results'][1]['value'] is not None
    maps=sheet['associations']['correspondences']; assert [r['original_interval_0based_half_open'] for r in maps]==[[3,6],[0,3],[0,3]]
    assert maps[0]['strand']=='-' and maps[0]['translation_table']==11
    bad=deepcopy(sheet); bad['segments'][0]['concatenated_interval_0based_half_open']=[0,1]
    with pytest.raises(ValueError): c.validate_msa_sheet(bad)


@pytest.mark.parametrize('mode',['ordinary_new_alignment','ordinary_prealigned','segment_alignment','segment_concatenation','mauve_first_block_projection'])
def test_modes_retain_numerical_work_and_precise_missing_evidence(mode):
    sheet=make(mode=mode); result=calculate_msa(sheet,parameters(entropy_request()))
    assert result['results'][0]['value']['sites'][1]['literal_entropy_bits']['value']==1
    if mode=='ordinary_prealigned': assert 'msa_prealigned_definition_mismatch' in {r['reason_code'] for r in sheet['requirements']}
    if mode.startswith('segment'): assert 'msa_segment_membership_unresolved' in {r['reason_code'] for r in sheet['requirements']}


def tree_operands(observed=False):
    op=operands(); ev=evidence(); trees=[]
    for name,text in [('gene','((a:1,b:2)0.9:3,(c:4,d:5):6);'),('organismal','((a:1,c:2):3,(b:4,d:5):6);')]:
        data=text.encode(); doc=parse_newick(data,artifact=artifact(data,name),dialect='newick',allow_multiple=False)['value']; op['documents']+=({'kind':'tree','value':doc},); trees.append(doc['trees'][0])
    for tree in trees:
        tid=tree['tree_id']; op['tree_bindings']+=({'tree_id':tid,'role':'inference' if tree is trees[0] else 'organismal','source_tree_id':None,'alignment_id':None,'command_id':'cmd' if observed else None,
            'branch_unit':'expected_substitutions_per_model_site','support_method':'fasttree_sh_like','support_scale':'fraction','tip_rows':[],'evidence':[ev]},)
    if observed: op['run']['commands']=[{'command_id':'cmd','role':'tree_inference','argv':['FastTree','-nt'],'raw_command':None,'origin':'observed','evidence':[ev],'location':None}]
    tree=trees[0]; op['analysis']['tree_id']=tree['tree_id']; tips=[n['node_index'] for n in tree['nodes'] if not n['child_indices']]
    op['populations']['leaves']=[{'population_id':'leaves','tree_id':tree['tree_id'],'node_indices':tips,'completeness':'complete','evidence':[]}]
    reqs=[request('tree',population_id='leaves',branch_unit='expected_substitutions_per_model_site' if observed else 'native_unknown',pairs=[[tips[0],tips[1]]])]
    joins=[]
    for a in [n for n in trees[0]['nodes'] if not n['child_indices']]:
        b=next(n for n in trees[1]['nodes'] if n['decoded_label']==a['decoded_label'])
        op['associations']['source_records'].append({'source_record_id':'genome:'+a['decoded_label'],'kind':'genome','evidence':ev})
        joins.append({'gene_tree_id':trees[0]['tree_id'],'gene_node_index':a['node_index'],'organismal_tree_id':trees[1]['tree_id'],'organismal_node_index':b['node_index'],
            'subject':{'kind':'genome','id':a['decoded_label'],'source_record_id':'genome:'+a['decoded_label']},'evidence':[ev]})
    reqs.append(request('relationship_comparison',comparison_id='comparison',gene_tree_id=trees[0]['tree_id'],organismal_tree_id=trees[1]['tree_id'],injective_tip_join=joins))
    return op,parameters(*reqs)


@pytest.mark.parametrize('observed',[False,True])
def test_optional_actual_trees_and_explicit_relationships(observed):
    op,p=tree_operands(observed); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    result=calculate_msa(parsed['value'],p); value=result['results'][0]['value']; assert value is not None,result
    assert value['branch_length_sum']['value']==21
    assert value['branch_length_sum']['unit']==('expected_substitutions_per_model_site' if observed else 'native_unknown')
    assert value['distances'][0]['value']['value']==3
    supported=next(r for r in value['branches'] if r['native_support_observation_ids'])
    assert supported['support_rescaled']['value']==(.9 if observed else None)
    assert result['results'][1]['value']['rf']['value']==2


@pytest.mark.parametrize('with_sources',[False,True])
def test_complete_native_xmfa_and_three_coverage_bases(with_sources):
    op,p=xmfa_operands(with_sources=with_sources); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    result=calculate_msa(parsed['value'],p); values=[r['value'] for r in result['results']]; assert all(v is not None for v in values),result
    pair=values[0]['blocks'][0]['pairs'][0]
    assert len(values[0]['blocks'])==6 and pair['identical_canonical']['value']==39 and pair['substitutions']['value']==7 and pair['comparable_canonical']['value']==46
    for value,expected in zip(values[1:4],([50,41,49],[48,0,47],[46,0,46])):
        assert [r['known_union_bases']['value'] for r in value['members']]==expected
        assert [r['source_length']['value'] for r in value['members']]==([50,41,49] if with_sources else [None,None,None])
    assert [r['native_position_0based'] for r in values[4]['cells']]==[48,None,1]
    assert values[4]['cells'][0]['original_coordinates']==[]


@pytest.mark.parametrize('mutation',['extra','bool','duplicate','wrong_tag','self_pair'])
def test_parameter_rejections(mutation):
    p=parameters(request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,1]]))
    if mutation=='extra': p['requests'][0]['invented']=1
    if mutation=='bool': p['requests'][0]['pairs']=[[False,1]]
    if mutation=='duplicate': p['requests']*=2
    if mutation=='wrong_tag': p['requests'][0]['kind']='native_statistics'
    if mutation=='self_pair': p=parameters(request('xmfa_alignment_components',document_id='x',selection={'population_id':'p','document_id':'x','member_numbers':[1],'block_columns':[],'completeness':'complete','evidence':[]},selected_pairs=[[1,1]],case_policy='uppercase'))
    with pytest.raises(ValueError): c.validate_msa_parameters(p)


@pytest.mark.parametrize('mutation',['native_value','native_missing','population','reference','extra','xmfa_slot'])
def test_saved_sheet_relationship_rejections(mutation):
    if mutation=='reference':
        op=associated_operands('explicit_reference_identity'); sheet=extract_msa_sheet(**op)['value']; sheet['analysis']['reference']['native_ref_string']='>a\nTT\n'; sheet['analysis']['reference']['identity_state']='resolved'
    elif mutation=='xmfa_slot':
        op,_=xmfa_operands(with_sources=False); sheet=extract_msa_sheet(**op)['value']; sheet['analysis']['full_xmfa_slot_id']='wrong'
    else:
        op,_=native_operands(); sheet=extract_msa_sheet(**op)['value']
        if mutation=='native_value': sheet['native_observations'][0]['number']['value']=33
        if mutation=='native_missing': sheet['native_observations'].pop()
        if mutation=='population': sheet['native_observations'][0]['population_id']='fabricated'
        if mutation=='extra': sheet['master_score']=1
    with pytest.raises(ValueError): c.validate_msa_sheet(sheet)


@pytest.mark.parametrize('mutation',['parameter','kind','unit','source','population'])
def test_saved_components_cannot_change_original_selection(mutation):
    op,table=native_operands(); sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,parameters(entropy_request(table=table)))
    if mutation=='parameter': result['parameters']['requests'][0]['native_rounding']=None
    if mutation=='kind': result['results'][0]['kind']='alignment'
    if mutation=='unit': result['results'][0]['value']['sites'][0]['literal_entropy_bits']['unit']='probability'
    if mutation=='source': result['results'][0]['value']['sites'][0]['native_observation_ids']=['msa_frequency_table:'+'0'*64+'/rows/0/score']
    if mutation=='population': result['results'][0]['value']['population_id']='wrong'
    with pytest.raises(ValueError): c.validate_msa_components(result,sheet=sheet)


def composition_operands():
    op=associated_operands('unique_dna'); ev=evidence(); associations=op['associations']; subjects=[]
    for index,member in enumerate(associations['original_members']):
        sid='source-member:'+str(index); associations['source_records'].append({'source_record_id':sid,'kind':'original_input','evidence':evidence(name=sid)})
        member['evidence']=[evidence(name=sid)]; member['source_record_ids']=[sid]
        subjects.append({'kind':'input_member','id':'input_member_occurrence:original/'+member['key']['member_id']+'/0','source_record_id':sid})
        associations['functions'].append({'assignment_id':'f'+str(index),'subject':subjects[-1],'function_key':'enzyme','function_label':'explicit supplied function','source_record_id':sid,'evidence':[ev]})
        associations['taxonomy'].append({'subject':subjects[-1],'taxon_id':'strain'+str(index),'rank':'strain','lineage':[{'taxon_id':'same-species','rank':'species'}],'source_record_id':sid,'evidence':[ev]})
    for name,kind in [('composition','composition'),('taxonomy','taxonomy')]:
        op['populations'][kind]=[{'population_id':name,'unit':'sequence_member','member_subjects':subjects,'assignment_completeness':'complete','membership_completeness':'complete','evidence':[ev]}]
    return op,parameters(request('function_composition',population_id='composition'),request('taxonomy',population_id='taxonomy',rank='species'))


def test_explicit_function_and_taxonomic_composition():
    op,p=composition_operands(); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    result=calculate_msa(parsed['value'],p); functions,taxa=[r['value'] for r in result['results']]
    assert functions['rows'][0]['assigned_members']['value']==2 and functions['rows'][0]['fraction_all']['value']==1
    assert taxa['same_taxon_pairs']['value']==1 and taxa['distinct_known_taxa']['value']==1
    assert c.validate_msa_components(json.loads(json.dumps(result)),sheet=parsed['value'])==result


def test_empty_explicit_population_is_measured_zero_without_inventing_entropy():
    op=operands(); op['populations']['alignments'][0]['row_indices']=[]
    sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[])))
    assert result['results'][0]['value']['sites'][0]['eligible_count']['value']==0
    assert result['results'][0]['value']['sites'][0]['literal_entropy_bits']['value'] is None
    assert result['results'][1]['value']['member_count']['value']==0


def test_incomplete_alignment_retains_raw_rows_and_null_full_population_values():
    al=alignment(b'>a\nACT\n>b\nA\n'); sheet=make(al=al)
    result=calculate_msa(sheet,parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,1]])))
    assert result['results'][0]['value']['sites'][0]['eligible_count']['value'] is None
    assert result['results'][1]['value']['cell_count']['value'] is None
    assert result['results'][1]['value']['rows'][0]['nongap_count']['value']==3


def test_incomplete_original_map_preserves_known_union():
    op=associated_operands('explicit_reference_identity'); op['associations']['correspondences']=op['associations']['correspondences'][:-1]
    sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,parameters(request('original_coverage',population_id='all')))['results'][0]['value']
    assert result['rows'][0]['original_member_coverage']['value']==1
    assert result['rows'][1]['original_covered_positions']['value']==1
    assert result['rows'][1]['original_member_coverage']['value'] is None


def test_failed_request_does_not_discard_independent_entropy():
    sheet=make(); p=parameters(entropy_request(),request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,99]]))
    result=calculate_msa(sheet,p); assert result['results'][0]['value']['sites'][1]['literal_entropy_bits']['value']==1
    assert result['results'][1]['status']=='invalid' and result['results'][1]['value'] is None
    assert result['results'][1]['requirements'][0]['reason_code']=='phylogeny_pair_member_outside_population'


def test_missing_requested_native_table_preserves_entropy():
    sheet=make(); req=entropy_request()|{'observed_table_id':'missing-table'}
    result=calculate_msa(sheet,parameters(req))['results'][0]
    assert result['status']=='partial' and result['value']['sites'][1]['literal_entropy_bits']['value']==1
    assert result['value']['sites'][1]['native_observation_ids']==[]


def test_unavailable_consensus_table_does_not_recalculate_native_consensus():
    sheet=make(consensus=alignment(b'>consensus\nAC\n','consensus'))
    assert not sheet['consensus_associations']
    assert 'msa_consensus_correspondence_unresolved' in {r['reason_code'] for r in sheet['requirements']}


def gap_fill_operands():
    op=associated_operands('reverse_translation_concatenation','segment_concatenation')
    final=alignment(b'>merged\nMGK-\n','aligned')
    op['documents']=[{'kind':d['kind'],'value':final if d['kind']=='alignment' and d['value']['alignment_id']==final['alignment_id'] else d['value']} for d in op['documents']]
    op['populations']['alignments']=[population(final)]
    ev=evidence(); segment={'segment_id':'missing','native_segment_token':'missing','genome_id':None,'genome_sequence_record_id':None,'contig_id':None,'original_interval_0based_half_open':None,
        'strand':'unknown','input_member':None,'alignment_id':None,'concatenated_interval_0based_half_open':[3,4],'order_index':2,'state':'missing','evidence':[ev]}
    op['segments']=list(op['segments'])+[segment]; op['analysis']['segment_ids'].append('missing')
    transform={'transformation_id':'gap-fill','kind':'missing_segment_gap_fill','input_members':[],'input_rows':[],'output_rows':[{'alignment_id':final['alignment_id'],'row_index':0}],'evidence':[ev],
        'segment_id':'missing','output_interval_0based_half_open':[3,4]}
    op['associations']['transformations'].append(transform); op['associations']['row_members'][0]['transformation_ids'].append('gap-fill')
    return op


def test_segment_gap_fill_and_actual_interval_validation():
    op=gap_fill_operands(); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; result=calculate_msa(sheet,parameters(request('alignment',population_id='all',alphabet='protein',case_policy='uppercase',pairs=[])))
    assert result['results'][0]['value']['gap_cells']['value']==1
    assert 'msa_segment_membership_unresolved' in {r['reason_code'] for r in sheet['requirements']}
    bad=deepcopy(sheet); bad['associations']['transformations'][-1]['output_interval_0based_half_open']=[2,3]
    with pytest.raises(ValueError): c.validate_msa_sheet(bad)


def test_xmfa_binding_tamper_and_wrong_mode_are_separate_failures():
    op,p=xmfa_operands(); sheet=extract_msa_sheet(**op)['value']; bad=deepcopy(sheet)
    bad['xmfa_bindings'][0]['bindings']['members'][0]['source_sequence']='A'*50
    with pytest.raises(ValueError): c.validate_msa_sheet(bad)
    sheet['analysis']['mode']='mauve_first_block_projection'
    result=calculate_msa(sheet,p); assert all(r['value'] is None and r['status']=='invalid' for r in result['results'])


def reference_operands(ref_text='>a\nAC\n',query_text='>b\nAT\n'):
    from gene_annotation_episode.bvbrc_alignment_associations import extract_alignment_associations
    op=operands(); ev=evidence(); aid=op['analysis']['alignment_id']; bindings=[]
    for key,text in [('reference',ref_text),('query',query_text)]:
        bindings.append({'binding_id':key,'parameter_pointer':'/'+key,'kind':'inline_parameter','content':None,'workspace_path':None,'inline_value':text,'link_evidence':None,'members':[]})
    declarations={'common':{'version':'bvbrc_alignment_associations_v1','analysis_id':'analysis','input_sequences':[{'kind':'inline_fasta','input_binding_id':b['binding_id'],'id_rule':'first_whitespace_token','encoding':'ascii','molecule':'dna','evidence':[ev]} for b in bindings],
        'row_joins':[],'automatic_row_joins':[{'alignment':aid,'input_binding_ids':['reference','query'],'method':'exact_unique_header','case_policy':'literal','gap_policy':'literal','transformation_ids':[],'evidence':[ev]}],
        'transformations':[],'correspondences':[],'feature_genomes':[],'source_records':[],'member_entities':[]},'functions':None,'taxonomy':None}
    associations=extract_alignment_associations(inputs=tuple(bindings),documents=op['documents'],declarations=declarations); assert associations['value'] is not None,associations
    op['inputs']=bindings; op['associations']=associations['value']
    op['analysis']['reference']={'alignment_id':aid,'row_index':0,'original_member':None,'native_ref_type':'string','native_ref_string':ref_text,'identity_state':'resolved','evidence':[ev]}
    return op


def test_reference_original_string_and_occurrence_proof():
    op=reference_operands(); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; assert sheet['analysis']['reference']['identity_state']=='resolved'
    p=parameters(request('msa_reference_differences',population_id='all',reference=op['analysis']['reference'],member_row_indices=[1],alphabet='dna',case_policy='preserve'))
    result=calculate_msa(sheet,p); assert result['results'][0]['value']['counts'][1]['count']['value']==1
    for change in ('input','string','row'):
        bad=deepcopy(sheet)
        if change=='input': bad['inputs'][0]['inline_value']='>a\nTT\n'
        if change=='string': bad['analysis']['reference']['native_ref_string']='>a\nTT\n'
        if change=='row': bad['analysis']['reference']['row_index']=1
        with pytest.raises(ValueError): c.validate_msa_sheet(bad)


@pytest.mark.parametrize('ref_text',['AC','>a\nAC\n>a\nAC\n','>a\nTT\n'])
def test_unproven_reference_preserves_requested_string_and_staged_differences(ref_text):
    op=reference_operands(ref_text); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; assert sheet['analysis']['reference']['identity_state']=='unresolved'
    assert sheet['analysis']['reference']['native_ref_string']==ref_text
    p=parameters(request('msa_reference_differences',population_id='all',reference=op['analysis']['reference'],member_row_indices=[1],alphabet='dna',case_policy='preserve'))
    result=calculate_msa(sheet,p); assert result['parameters']==p
    assert result['results'][0]['value']['reference']['identity_state']=='unresolved'
    assert result['results'][0]['value']['counts'][1]['count']['value']==1
    sheet['analysis']['reference']['identity_state']='resolved'
    with pytest.raises(ValueError): c.validate_msa_sheet(sheet)


def test_missing_original_reference_content_is_qualified_not_upgraded():
    op=associated_operands('explicit_reference_identity'); sheet=extract_msa_sheet(**op)['value']
    assert sheet['analysis']['reference']['identity_state']=='unresolved'
    bad=deepcopy(sheet); bad['analysis']['reference']['identity_state']='resolved'
    with pytest.raises(ValueError): c.validate_msa_sheet(bad)


def first_block_projection_operands():
    full,p=xmfa_operands(with_sources=False); doc=full['documents'][0]['value']
    data=''.join('>synthetic_native_row_'+str(r['record_index'])+'\n'+r['sequence']+'\n' for r in doc['blocks'][0]['records']).encode()
    al=alignment(data,'native_derived_first_block.afa')
    op=operands(al,mode='mauve_first_block_projection',documents=[{'kind':'alignment','value':al},*full['documents']])
    op['read_outcomes']=full['read_outcomes']; op['analysis'].update(full_xmfa_slot_id='full',xmfa_document_id=doc['document_id'])
    return op,parameters(request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,2]]),entropy_request())


def source_example_operands(case):
    """Consume complete C1 saved records without modifying their original files."""
    base=ROOT/'verification/tool_graders_bvbrc_msa_provider_2026-10-25/source_examples_004'
    saved=json.loads((base/(case+'.inputs.json')).read_text())
    answer=json.loads((base/(case+'.answer.json')).read_text())
    op,p=xmfa_operands(with_sources=False)
    doc=saved['document']
    op['documents']=[{'kind':'xmfa','value':doc}]
    op['analysis']['xmfa_document_id']=doc['document_id']
    op['read_outcomes'][0]['artifact']=doc['artifact']; op['read_outcomes'][0]['document_ids']=[doc['document_id']]
    for req in p['requests']:
        req['document_id']=doc['document_id']
        if 'selection' in req:
            req['selection']['document_id']=doc['document_id']
            req['selection']['block_columns']=[{'block_index':b['block_index'],'columns_0based':list(range(b['alignment_column_count']))} for b in doc['blocks']]
    op['xmfa_bindings']=[answer['binding']]
    op['associations']=saved['operands']['associations']
    if op['associations']['original_members']:
        op['inputs']=[{'binding_id':'original','parameter_pointer':'/fasta','kind':'inline_parameter','content':None,'workspace_path':None,
            'inline_value':'>same\n'+'A'*100+'\n>same\n'+'A'*100+'\n','link_evidence':None,'members':[]}]
    return op,p


@pytest.mark.parametrize('case',['separate_native','one_missing_source','contradictory_json_sequence','missing_reader','partial_record_population','distinct_original_occurrences'])
def test_source_verification_qualifications_survive_provider_calculations(case):
    op,p=source_example_operands(case); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; result=calculate_msa(sheet,p)
    value=result['results'][0]['value']; assert value is not None,result
    if case not in ('separate_native','one_missing_source'):
        assert value['blocks'][0]['pairs'][0]['identical_canonical']['value']==39
    assert sheet['xmfa_bindings']==op['xmfa_bindings']
    if case=='distinct_original_occurrences':
        originals=result['results'][4]['value']['cells'][0]['original_coordinates']
        assert len(originals)==2 and {r['original_member']['occurrence_index'] for r in originals}=={0,1}
    elif case!='separate_native':
        assert sheet['xmfa_bindings'][0]['requirements']
        assert all(r in result['results'][4]['requirements'] for r in sheet['xmfa_bindings'][0]['requirements'])


def test_inconsistent_original_occurrence_in_common_associations_is_rejected():
    op,p=source_example_operands('unknown_original_occurrence')
    parsed=extract_msa_sheet(**op)
    assert parsed['value'] is None and parsed['status']=='invalid'


def test_same_artifact_name_does_not_join_distinct_analyses():
    one=operands(alignment(b'>a\nAA\n>b\nAA\n','same.afa'))
    two=operands(alignment(b'>a\nAT\n>b\nAA\n','same.afa'))
    one['analysis']['analysis_id']='first'; two['analysis']['analysis_id']='second'
    sheets=[extract_msa_sheet(**op)['value'] for op in (one,two)]
    p=parameters(request('alignment',population_id='all',alphabet='dna',case_policy='uppercase',pairs=[[0,1]]))
    results=[calculate_msa(sheet,p) for sheet in sheets]
    assert [r['results'][0]['value']['pairs'][0]['substitutions']['value'] for r in results]==[0,1]
    with pytest.raises(ValueError): c.validate_msa_components(results[0],sheet=sheets[1])


def test_saved_object_key_order_does_not_change_native_dna_field_identity():
    op,table=native_operands(); sheet=extract_msa_sheet(**op)['value']
    saved=json.loads(json.dumps(sheet,sort_keys=True))
    assert c.validate_msa_sheet(saved)==sheet
    assert calculate_msa(saved,parameters(entropy_request(table=table)))==calculate_msa(sheet,parameters(entropy_request(table=table)))


def unbound_source_operands(source_format):
    import base64
    base=ROOT/'verification/tool_graders_bvbrc_msa_provider_2026-10-25/source_examples_004'
    record=json.loads((base/'combined_native.inputs.json').read_text())
    source=record['operands']; source['inputs']['files'][0]['format']=source_format
    source['source_readers']=[]
    source['artifact_bytes']={k:base64.b64decode(v) for k,v in source['artifact_bytes'].items()}
    verified=verify_xmfa_source_inputs(**source)
    op,p=xmfa_operands(with_sources=False)
    op['xmfa_bindings']=[extract_msa_xmfa_bindings(record['document'],verification=verified,source_comparison='case_insensitive_iupac_exact',evidence=())]
    return op,p


@pytest.mark.parametrize('source_format',['GenBank','DNAstar'])
def test_unbound_source_formats_preserve_literal_xmfa_components(source_format):
    op,p=unbound_source_operands(source_format); parsed=extract_msa_sheet(**op); assert parsed['value'] is not None,parsed
    sheet=parsed['value']; result=calculate_msa(sheet,p)
    assert result['results'][0]['value']['blocks'][0]['pairs'][0]['identical_canonical']['value']==39
    assert 'xmfa_source_extractor_unbound' in {r['reason_code'] for r in sheet['requirements']}
    assert result['results'][4]['value']['cells'][0]['source_coordinate'] is None


def test_native_derived_first_block_is_separate_from_complete_xmfa():
    op,p=first_block_projection_operands(); sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,p)
    value=result['results'][0]['value']; assert value['site_count']['value']==49
    assert value['pairs'][0]['identical_positions']['value']==39 and value['pairs'][0]['substitutions']['value']==7
    assert 'alignment_transformation_unproven' in {r['reason_code'] for r in sheet['requirements']}
    assert sheet['analysis']['mode']=='mauve_first_block_projection'


@pytest.mark.parametrize('token',['1e-9999','NaN','Inf'])
def test_native_tree_support_underflow_nonfinite_are_not_zero(token):
    op,p=tree_operands(False)
    for index,document in enumerate(op['documents']):
        if document['kind']=='tree' and document['value']['artifact']['raw_artifact_ref']=='gene':
            data=('((a:1,b:2)'+token+':3,(c:4,d:5):6);').encode()
            op['documents']=list(op['documents']); op['documents'][index]={'kind':'tree','value':parse_newick(data,artifact=artifact(data,'gene'),dialect='newick',allow_multiple=False)['value']}; break
    sheet=extract_msa_sheet(**op)['value']; assert sheet is not None
    support=next(o for o in sheet['native_tree_measurements'] if o['field']=='branch_support_native')
    assert support['value'] is None and support['state']=='failed' and support['raw_token']==token
    result=calculate_msa(sheet,p); assert result['results'][0]['value'] is not None
    bad=deepcopy(sheet); bad['native_tree_measurements']=[r for r in bad['native_tree_measurements'] if r['field']!='branch_support_native']; bad['support_observations']=[]
    with pytest.raises(ValueError): c.validate_msa_sheet(bad)


@pytest.mark.parametrize('mutation',['native','source','inverse','length'])
def test_xmfa_saved_calculation_rejects_foreign_coordinate_relations(mutation):
    op,p=xmfa_operands(); sheet=extract_msa_sheet(**op)['value']; result=calculate_msa(sheet,p)
    if mutation=='native':
        row=result['results'][4]['value']['cells'][0]; row['native_position_0based']=10; row['native_position_1based']=11
    if mutation=='source': result['results'][4]['value']['cells'][0]['source_coordinate']['record_id']='wrong'
    if mutation=='inverse': result['results'][5]['value']['queries'][0]['matches'][0]['column_0based']=1
    if mutation=='length': result['results'][1]['value']['members'][0]['source_length']['value']=500
    with pytest.raises(ValueError): c.validate_msa_components(result,sheet=sheet)
