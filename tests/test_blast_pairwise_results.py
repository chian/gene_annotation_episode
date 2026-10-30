"""Native numerical examples and synthetic missing/custody counterexamples."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import socket

import pytest

from gene_annotation_episode.blast_report_collection import parse_blast_report_collection
from gene_annotation_episode.blast_pairwise_results import populate_blast_pairwise_sheet, calculate_blast_pairwise_components
from gene_annotation_episode.native_blast_contracts import _options

ROOT=Path(__file__).resolve().parents[1]
EXAMPLES=ROOT/'verification/tool_graders_blast_pairwise_2026-10-26_294/native_examples'
RANGES=ROOT/'verification/tool_graders_blast_pairwise_2026-10-26_294/native_ranges'


def from_native(directory):
    """Test fixture adapter; production custody remains the root-owned host."""
    plan=json.loads((directory/'plan.json').read_bytes());bundle=json.loads((directory/'attempt/bundle.json').read_bytes())
    job=plan['requested_job']['native_blast'];program=job['program'];options=_options(job)
    operands=[];bindings={}
    for selected in job['operands']:
        query=selected['role']=='query_sequence';axis='query' if query else 'reference'
        lines=Path(selected['path']).read_text().splitlines();title=lines[0][1:];length=len(''.join(lines[1:]))
        protein=program in ({'blastp','tblastn'} if query else {'blastp','blastx'})
        interval=options.get('-query_loc' if query else '-subject_loc')
        interval=[int(interval.split('-')[0])-1,int(interval.split('-')[1])] if interval else None
        descriptor={'subject_ref':'query_subject' if query else 'paired_reference','length':length,
            'molecule':'protein' if protein else 'dna','artifact_key':selected['role'],'native_id':title.split()[0],'selected_interval':interval}
        operands.append({'role':'query' if query else 'subject',**descriptor,'record_ordinal':0,
            'native_title':title,'selected_interval':interval,'identity':None})
        bindings[axis]=descriptor
    output=next(r for r in job['outputs'] if r['role'] not in {'stdout','stderr'})
    content=(directory/'attempt'/output['relative_path']).read_bytes()
    invocation={'execution_program':program,'scientific_mode':'pairwise','resource_kind':'local','query_kind':'sequence','reference_kind':'sequence',
        'request':plan['requested_job'],'effective_options':{**options,'requested_hit_limit':int(options['-max_target_seqs']) if '-max_target_seqs' in options else None,
            'requested_hsp_limit':int(options['-max_hsps']) if '-max_hsps' in options else None},
        'operands':operands,'completion':{'native_returncode':bundle['returncode'],'producer_complete':not bundle['failures']}}
    artifact={'artifact_key':'report','role':output['role'],'format':output['format'],'fields':output['fields'],'delimiter':output['delimiter']}
    collection=parse_blast_report_collection({'report':content},artifacts=[artifact],invocation=invocation)
    assert not collection['issues']
    assert len(collection['searches'])==1
    return collection['searches'][0],bindings


def example(case='blastp_gaps',fmt='json15',root=EXAMPLES):
    search,bindings=from_native(root/(case+'_'+fmt))
    return populate_blast_pairwise_sheet(search,operand_bindings=bindings)


def components(sheet):return calculate_blast_pairwise_components(sheet)['components']


def synthetic_native_change(search):
    """Keep deliberate synthetic perturbations internally consistent."""
    search['native']['report']['results']['bl2seq'][0]=deepcopy(search['native']['search'])
    search['normalized']['native']['document']['BlastOutput2'][0]['report']=deepcopy(search['native']['report'])


def test_actual_blastp_gaps_preserves_known_measurements_and_denominators():
    sheet=example();before=deepcopy(sheet);actual=components(sheet);hsp=actual['hsps'][0]['components']
    assert hsp['counts']['alignment_columns']==253
    assert hsp['counts']['paired_columns']==243
    assert hsp['counts']['identical_pairs']==238
    assert hsp['counts']['paired_columns']-hsp['counts']['identical_pairs']==5
    assert hsp['counts']['reference_gap_columns']==10
    assert hsp['fractions']['query_paired_coverage']==pytest.approx(243/253)
    assert hsp['fractions']['reference_paired_coverage']==1
    assert hsp['fractions']['paired_identity']==pytest.approx(238/243)
    assert hsp['native_scores']=={'score':1252,'bit_score':486.878,'evalue':0}
    assert sheet==before


@pytest.mark.parametrize('case,program,qcovered,rcovered,qlength,rlength',[
 ('blastx_reverse','blastx',240,80,244,80),('tblastn_reverse','tblastn',80,240,80,243),
 ('tblastx_frames','tblastx',240,240,243,243),
])
@pytest.mark.parametrize('fmt',['json15','tabular7'])
def test_actual_translated_original_coordinates_and_coverage(case,program,qcovered,rcovered,qlength,rlength,fmt):
    sheet=example(case,fmt);hsp=components(sheet)['hsps'][0]['components']
    assert hsp['geometry_available']
    assert hsp['counts']['paired_query_positions']==qcovered
    assert hsp['counts']['paired_reference_positions']==rcovered
    assert hsp['fractions']['query_paired_coverage']==pytest.approx(qcovered/qlength)
    assert hsp['fractions']['reference_paired_coverage']==pytest.approx(rcovered/rlength)
    if program=='blastx':assert hsp['pairs'][0]['query_start']==239 and hsp['pairs'][-1]['query_start']==2
    else:assert hsp['pairs'][0]['reference_start']==239 and hsp['pairs'][-1]['reference_start']==2


@pytest.mark.parametrize('case,qlength,covered', [('blastn_range_forward',240,180),('blastx_range_reverse',244,186)])
@pytest.mark.parametrize('fmt',['json15','tabular7'])
def test_selected_range_native_length_is_not_full_operand_denominator(case,qlength,covered,fmt):
    sheet=example(case,fmt,RANGES)
    assert sheet['search']['normalized']['query']['length']==covered
    assert sheet['operand_bindings']['query']['length']==qlength
    actual=components(sheet);hsp=actual['hsps'][0]['components']
    assert hsp['geometry_available']
    assert hsp['denominators']['query_length']==qlength
    assert hsp['counts']['paired_query_positions']==covered
    assert hsp['fractions']['query_paired_coverage']==pytest.approx(covered/qlength)
    assert min(p['query_start'] for p in hsp['pairs'])==(30 if case=='blastn_range_forward' else 29)


@pytest.mark.parametrize('fmt',['json15','tabular7'])
def test_actual_nucleotide_reverse_coordinates(fmt):
    hsp=components(example('blastn_reverse',fmt,RANGES))['hsps'][0]['components']
    assert hsp['geometry_available'] and hsp['counts']['paired_columns']==240
    assert hsp['pairs'][0]['reference_start']==239 and hsp['pairs'][-1]['reference_start']==0


def test_multiple_hsps_retain_alternative_mappings_and_do_not_sum_overlap():
    actual=components(example('blastp_multiple_hsps'))
    assert len(actual['hsps'])==2
    assert actual['union']['counts']['paired_query_positions']==80
    assert actual['union']['counts']['paired_reference_positions']==160
    assert actual['union']['fractions']['paired_identity'] is None
    assert actual['union']['conflicts']


def test_complete_zero_hit_and_unqualified_empty_are_distinct():
    zero=components(example('blastn_no_hits'))
    assert zero['status']=='no_reported_alignment' and not zero['hsps']
    assert zero['union']['fractions']['query_paired_coverage'] is None
    empty=components(example('blastn_no_hits','tabular6'))
    assert empty['status']=='alignment_report_unavailable'


@pytest.mark.parametrize('mutation,code',[
 ('query_id','query_native_identity'),('query_length','query_length_conflict'),('query_artifact','operand_binding_conflict'),
 ('query_subject','operand_binding_conflict'),('reference_id','reference_native_identity'),('reference_length','reference_length_conflict'),
 ('molecule','molecule_conflict'),('geometry','geometry_unresolved'),('geometry_replaced','program_context_conflict'),
 ('original_hsp','original_measurement_conflict'),('row_map','original_row_map_conflict'),
])
def test_wrong_identity_custody_or_geometry_is_not_repaired(mutation,code):
    sheet=example();search,bindings=sheet['search'],sheet['operand_bindings']
    if mutation=='query_id':
        # Remove binding so a contradictory native identity must still fail.
        search['operand_binding']=None;bindings['query']['native_id']='unrelated'
    elif mutation=='query_length':search['operand_binding']=None;bindings['query']['length']+=1
    elif mutation=='query_artifact':bindings['query']['artifact_key']='other-source'
    elif mutation=='query_subject':bindings['query']['subject_ref']='other-target'
    elif mutation=='reference_id':bindings['reference']['native_id']='unrelated'
    elif mutation=='reference_length':bindings['reference']['length']+=1
    elif mutation=='molecule':bindings['reference']['molecule']='dna'
    elif mutation=='geometry':search['program_context']['geometry_program']=None
    elif mutation=='geometry_replaced':search['program_context']['geometry_program']='blastn'
    elif mutation=='original_hsp':search['normalized']['hits'][0]['hsps'][0]['score']=999
    elif mutation=='row_map':search['row_map'][0]['hsp_ordinals']=[20]
    with pytest.raises(ValueError,match=code):populate_blast_pairwise_sheet(search,operand_bindings=bindings)


def test_unknown_reference_identity_is_not_invented():
    sheet=example();sheet['operand_bindings']['reference']['native_id']=None
    saved=populate_blast_pairwise_sheet(sheet['search'],operand_bindings=sheet['operand_bindings'])
    assert saved['operand_bindings']['reference']['native_id'] is None


def test_saved_sheet_recalculation_needs_no_files_network_or_execution(monkeypatch):
    saved=json.loads(json.dumps(example()))
    expected=components(saved)
    def forbidden(*a,**k):pytest.fail('saved numerical calculation performed external work')
    monkeypatch.setattr(Path,'open',forbidden);monkeypatch.setattr(Path,'read_bytes',forbidden)
    monkeypatch.setattr(subprocess,'run',forbidden);monkeypatch.setattr(socket,'socket',forbidden)
    assert components(saved)==expected


def test_missing_traceback_keeps_reported_counts_but_not_correspondence():
    search,bindings=from_native(EXAMPLES/'blastp_gaps_json15')
    for row in (search['normalized']['hits'][0]['hsps'][0],search['native']['search']['hits'][0]['hsps'][0]):
        row.pop('qseq');row.pop('hseq')
    synthetic_native_change(search)
    actual=components(populate_blast_pairwise_sheet(search,operand_bindings=bindings))
    hsp=actual['hsps'][0]['components']
    assert hsp['counts']['identical_pairs']==238 and not hsp['traceback_available']
    assert hsp['fractions']['query_paired_coverage'] is None


def test_evalue_is_never_a_correspondence_multiplier():
    sheet=example();first=components(sheet)
    for row in (sheet['search']['normalized']['hits'][0]['hsps'][0],sheet['search']['native']['search']['hits'][0]['hsps'][0]):row['evalue']=100000
    synthetic_native_change(sheet['search'])
    second=components(sheet)
    assert first['union']==second['union']
    assert first['hsps'][0]['components']['counts']==second['hsps'][0]['components']['counts']
    assert first['hsps'][0]['components']['fractions']==second['hsps'][0]['components']['fractions']


@pytest.mark.parametrize('filename,fmt',[('native_pair_result.json','json15'),('native_pair_result.tsv','tabular7')])
def test_existing_253_column_fixture_retains_its_original_meaning(filename,fmt):
    descriptors={axis:{'subject_ref':axis,'length':length,'molecule':'protein','artifact_key':axis,
        'native_id':identifier,'selected_interval':None} for axis,length,identifier in [
            ('query',253,'public_ybhP_pair_test'),('reference',243,'synthetic_deletion_and_substitutions')]}
    operands=[{'role':'query' if axis=='query' else 'subject',**row,'record_ordinal':0,
        'native_title':row['native_id'],'identity':None} for axis,row in descriptors.items()]
    invocation={'execution_program':'blastp','scientific_mode':'pairwise','resource_kind':'local','query_kind':'sequence','reference_kind':'sequence',
        'request':{},'effective_options':{},'operands':operands,'completion':{'native_returncode':0,'producer_complete':True}}
    raw=(ROOT/'tests/fixtures/blast_grading_inputs'/filename).read_bytes()
    collection=parse_blast_report_collection({'original':raw},artifacts=[{'artifact_key':'original','role':'primary_report',
        'format':fmt,'fields':None,'delimiter':None if fmt=='json15' else '\t'}],invocation=invocation)
    result=components(populate_blast_pairwise_sheet(collection['searches'][0],operand_bindings=descriptors))
    hsp=result['hsps'][0]['components']
    assert hsp['counts']['alignment_columns']==253 and hsp['counts']['paired_columns']==243
    assert hsp['counts']['identical_pairs']==238 and hsp['counts']['reference_gap_columns']==10
    assert hsp['fractions']['query_paired_coverage']==pytest.approx(243/253)
    assert hsp['fractions']['reference_paired_coverage']==1


def test_selected_context_has_both_full_and_selected_explicit_denominators():
    sheet=example('blastn_range_forward','tabular7',RANGES)
    actual=components(sheet)
    assert actual['coordinate_context']=={
        'query':{'reported_length':180,'full_length':240,'selected_interval':[30,210],'coordinate_unit':'nt'},
        'reference':{'reported_length':240,'full_length':240,'selected_interval':[30,240],'coordinate_unit':'nt'}}
    assert actual['selected_operand_coverage']['query']=={'numerator':180,'denominator':180,'value':1,'unit':'fraction'}
    assert actual['selected_operand_coverage']['reference']=={'numerator':180,'denominator':210,'value':180/210,'unit':'fraction'}
    assert sheet['search']['normalized']['query']['length']==180


def test_native_report_pointer_and_retained_measurements_must_agree():
    sheet=example();sheet['search']['search_key']['search_pointer']='/BlastOutput2/0/report/results/bl2seq/99'
    with pytest.raises(ValueError,match='original_search_pointer_conflict'):components(sheet)
    sheet=example();sheet['search']['native']['search']['query_len']=999
    with pytest.raises(ValueError,match='original_search_pointer_conflict'):components(sheet)


def test_missing_or_conflicting_selected_range_is_not_reconstructed_from_endpoints():
    sheet=example('blastn_range_forward','tabular7',RANGES)
    sheet['operand_bindings']['query']['selected_interval']=None
    with pytest.raises(ValueError,match='selected_interval_conflict'):components(sheet)
    sheet=example('blastn_range_forward','tabular7',RANGES)
    sheet['operand_bindings']['reference']['selected_interval']=[100,240]
    with pytest.raises(ValueError,match='outside_selected_interval'):components(sheet)


def test_failed_producer_preserves_measured_counts_and_withholds_complete_selected_coverage():
    sheet=example();sheet['search']['reporting'].update(native_returncode=7,producer_complete=False)
    actual=components(sheet)
    assert actual['status']=='partial'
    assert actual['hsps'][0]['components']['counts']['identical_pairs']==238
    assert actual['selected_operand_coverage']['query']['numerator'] is None
    assert any(r['code']=='blast_pairwise_native_execution_failed' for r in actual['issues'])


def test_zero_selected_population_requires_actual_complete_zero_report():
    sheet=example('blastn_no_hits');actual=components(sheet)
    assert actual['selected_operand_coverage']['query']=={'numerator':0,'denominator':60,'value':0,'unit':'fraction'}
    sheet['search']['reporting']['producer_complete']=False
    assert components(sheet)['selected_operand_coverage']['query']['value'] is None


def test_missing_hsp_objects_do_not_make_remaining_geometry_complete():
    sheet=example();search=sheet['search']
    search['native']['search']['hits'][0]['hsps'].append('synthetic malformed HSP')
    search['issues'].append({'code':'blast_hsp_object_required','pointer':'/synthetic','field':None,'details':{}})
    search['normalized']['issues']=deepcopy(search['issues'])
    synthetic_native_change(search)
    actual=components(sheet)
    assert actual['hsps'][0]['components']['geometry_available']
    assert actual['selected_operand_coverage']['query']['value'] is None


def test_tabular_original_data_row_ordinal_cannot_point_outside_section():
    sheet=example(fmt='tabular7');sheet['search']['row_map'][0]['hsp_ordinals']=[999]
    with pytest.raises(ValueError,match='original_row_map_conflict'):components(sheet)


def test_calculator_uses_explicit_descriptors_without_private_original_request_lookup():
    sheet=example('blastn_range_forward','tabular7',RANGES)
    expected=components(sheet)
    sheet['search']['normalized']['search']['request']={}
    actual=components(sheet)
    assert actual['coordinate_context']==expected['coordinate_context']
    assert actual['selected_operand_coverage']==expected['selected_operand_coverage']


def test_unknown_format_is_not_inferred_from_local_resource():
    sheet=example();sheet['search']['normalized']['format']='unknown'
    with pytest.raises(ValueError,match='normalized_search_conflict'):components(sheet)


def test_unknown_execution_preserves_legacy_selected_coverage_without_claiming_success():
    # Explicit missing-completion engineering control over unchanged retained
    # native measurements; no execution metadata is inferred from readability.
    sheet = example()
    sheet['search']['reporting'].update(native_returncode=None, producer_complete=None)
    result = calculate_blast_pairwise_components(sheet, _retain_correspondence=True)
    common = result.pop('correspondence')['instances'][0]
    assert result == calculate_blast_pairwise_components(sheet)
    selected = common['components']['selected']['query']
    assert result['components']['selected_operand_coverage']['query']['value'] == 243 / 253
    assert selected['execution_qualified_value'] == 243 / 253
    assert selected['execution_success_value'] is None
    assert common['sheet']['population']['execution_state'] == 'unknown'
    assert common['sheet']['population']['producer_state'] == 'unknown'
    sheet['search']['reporting'].update(native_returncode=0, producer_complete=True)
    known = calculate_blast_pairwise_components(sheet, _retain_correspondence=True)['correspondence']['instances'][0]
    assert known['components']['selected']['query']['execution_success_value'] == 243 / 253
