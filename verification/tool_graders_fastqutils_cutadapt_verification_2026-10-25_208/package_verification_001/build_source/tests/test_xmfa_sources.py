from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.phylogeny_formats import parse_aligned_fasta
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
from gene_annotation_episode.xmfa_sources import bind_xmfa_sources, validate_xmfa_bindings_for_document
from gene_annotation_episode.xmfa_source_contracts import (
    validate_xmfa_source_inputs, validate_xmfa_source_bindings, validate_xmfa_original_map)

BASE=Path(__file__).resolve().parents[1]/'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples'


def artifact(data,name):
    return {'raw_artifact_ref':name,'source_ref':'source:'+name,'sha256':hashlib.sha256(data).hexdigest()}


def evidence(data,name):
    return [{'content':{'source_ref':'source:'+name,'artifact_field':'artifact_ref',
        'artifact_ref':name,'sha256':hashlib.sha256(data).hexdigest(),'byte_count':len(data)},'pointer':''}]


def native_document(name='combined.xmfa',data=None):
    data=(BASE/name).read_bytes() if data is None else data
    parsed=parse_mauve_xmfa(data,artifact=artifact(data,name),dialect='mauve1',alphabet='dna',encoding='ascii')
    assert parsed['value'] is not None
    return parsed['value']


def input_file(name,data=None):
    data=(BASE/name).read_bytes() if data is None else data
    parsed=parse_aligned_fasta(data,artifact=artifact(data,name),id_rule='first_whitespace_token')['value']
    # These are supplied unaligned records. Different lengths are expected;
    # the source-file row population is independently known complete here.
    return {'file_id':name,'native_path_token':name,'artifact':artifact(data,name),
        'format':'FastA','record_completeness':'complete',
        'path_binding_evidence':evidence(data,name),
        'records':[{'record_id':'row:'+str(row['row_index']),'entry_1based':row['row_index']+1,
            'header':row['raw_header'],'sequence':row['sequence'],'source_location':row['source_location']}
            for row in parsed['rows']]}


def supplied(mode='single_file_entries'):
    names=['combined.fa'] if mode=='single_file_entries' else ['equCab1.fa','canFam2.fa','mm9.fa']
    files=[input_file(n) for n in names]
    # The invocation is an explicit test input. This is not a claim that a
    # live AppService task or its command has been authenticated here.
    declaration=json.dumps({'mode':mode,'ordered_file_ids':names}).encode()
    return {'schema_version':'mauve_xmfa_source_inputs_v1',
        'invocation':{'mode':mode,'ordered_file_ids':names,
                      'evidence':evidence(declaration,'fixture-declared-invocation')},
        'files':files,'original_maps':[]}


def bind(document=None, inputs=None):
    return bind_xmfa_sources(document or native_document(),inputs=inputs or supplied(),
                             source_comparison='case_insensitive_iupac_exact')


def reasons(result):
    return {r['reason_code'] for r in result['requirements']}


def forbidden(*args,**kwargs):
    raise AssertionError('No acquisition, native execution, or native parsing allowed')


def test_complete_combined_native_entries_and_reverse_complement_checks():
    document=native_document(); inputs=supplied()
    original=deepcopy((document,inputs))
    result=bind(document,inputs)
    assert result['status']=='ok'
    assert [m['source_length'] for m in result['members']]==[50,41,49]
    assert [m['entry_1based'] for m in result['members']]==[1,2,3]
    assert result['member_registry_completeness']=='complete'
    checks=result['source_checks']
    assert len(checks)==8
    assert checks[0]['compared_bases']==48 and checks[0]['state']=='match'
    assert checks[1]['state']=='absent_zero' and checks[1]['compared_bases']==0
    assert checks[2]['compared_bases']==47 and checks[2]['state']=='match'
    assert sum(c['state']=='match' for c in checks)==7
    assert validate_xmfa_bindings_for_document(document,json.loads(json.dumps(result)))==result
    assert (document,inputs)==original


def test_separate_files_use_native_argv_order_not_sorted_labels():
    result=bind(native_document('separate.xmfa'),supplied('multiple_files_concatenated'))
    assert result['status']=='ok'
    assert [m['file_id'] for m in result['members']]==['equCab1.fa','canFam2.fa','mm9.fa']
    assert [m['source_length'] for m in result['members']]==[50,49,41]
    assert all(m['entry_1based'] is None for m in result['members'])
    assert all(c['state']=='match' for c in result['source_checks'])


def test_concatenated_file_records_remain_ordered_across_native_span():
    data=(b'#FormatVersion Mauve1\n#Sequence1File file1.fa\n#Sequence1Format FastA\n'
          b'#Sequence2File file2.fa\n#Sequence2Format FastA\n'
          b'>1:2-5 + file1.fa\nCGTA\n>2:1-4 - file2.fa\nCGTA\n=\n')
    document=native_document('two-contig-test.xmfa',data)
    files=[input_file('file1.fa',b'>repeat\nACG\n>repeat\nTAA\n'),
           input_file('file2.fa',b'>last\nTACG\n')]
    inputs={'schema_version':'mauve_xmfa_source_inputs_v1',
        'invocation':{'mode':'multiple_files_concatenated','ordered_file_ids':['file1.fa','file2.fa'],
            'evidence':evidence(b'explicit fixture argv','fixture-argv')},'files':files,'original_maps':[]}
    result=bind(document,inputs)
    assert result['status']=='ok'
    assert result['members'][0]['source_sequence']=='ACGTAA'
    assert [c['member_interval_0based_half_open'] for c in result['members'][0]['components']]==[[0,3],[3,6]]
    assert [c['record_id'] for c in result['members'][0]['components']]==['row:0','row:1']
    assert [c['compared_bases'] for c in result['source_checks']]==[4,4]
    assert all(c['state']=='match' for c in result['source_checks'])
    inputs['files'][0]['records'].reverse()
    with pytest.raises(ValueError,match='source_entry_order_conflict'):
        validate_xmfa_source_inputs(inputs)


@pytest.mark.parametrize('change,reason', [
    ('unknown_mode','xmfa_invocation_mode_missing'),('missing_invocation_proof','xmfa_invocation_mode_missing'),
    ('missing_path_proof','xmfa_source_binding_missing'),('basename_only','xmfa_source_binding_missing'),
    ('partial_records','xmfa_input_population_partial'),('wrong_format','xmfa_source_binding_conflict'),
])
def test_missing_or_conflicting_source_evidence_never_uses_likely_match(change,reason):
    inputs=supplied()
    if change=='unknown_mode': inputs['invocation']['mode']='unknown'
    if change=='missing_invocation_proof': inputs['invocation']['evidence']=[]
    if change=='missing_path_proof': inputs['files'][0]['path_binding_evidence']=[]
    if change=='basename_only': inputs['files'][0]['native_path_token']='/somewhere/combined.fa'
    if change=='partial_records': inputs['files'][0]['record_completeness']='partial'
    if change=='wrong_format': inputs['files'][0]['format']='GenBank'
    result=bind(inputs=inputs)
    assert result['status']=='partial' and reason in reasons(result)
    assert all(m['source_length'] is None for m in result['members'])
    assert all(c['state'] in ('not_checked','absent_zero') for c in result['source_checks'])


def test_input_entry_identity_changes_source_check_and_does_not_join_by_header():
    inputs=supplied()
    records=inputs['files'][0]['records']
    records[0]['sequence'],records[2]['sequence']=records[2]['sequence'],records[0]['sequence']
    result=bind(inputs=inputs)
    assert result['members'][0]['source_length']==49
    assert result['members'][2]['source_length']==50
    assert result['status']=='partial'
    assert 'xmfa_source_sequence_mismatch' in reasons(result)
    assert 'xmfa_source_span_outside_input' in reasons(result)


def test_exact_mismatch_columns_and_other_native_rows_remain_usable():
    inputs=supplied()
    row=inputs['files'][0]['records'][0]
    assert row['sequence'][0]=='G'
    row['sequence']='A'+row['sequence'][1:]
    result=bind(inputs=inputs)
    changed=[c for c in result['source_checks'] if c['state']=='mismatch']
    assert len(changed)==1
    assert changed[0]['record']=={'block_index':1,'record_index':0}
    assert changed[0]['mismatch_columns_0based']==[0] and changed[0]['compared_bases']==1
    assert result['source_checks'][0]['state']=='match'


def test_outside_source_span_is_not_clipped_or_partially_compared():
    inputs=supplied();inputs['files'][0]['records'][0]['sequence']=''
    result=bind(inputs=inputs)
    assert result['members'][0]['source_length']==0
    assert 'xmfa_source_span_outside_input' in reasons(result)
    for check in result['source_checks']:
        if check['member_number']==1:
            assert check['state']=='not_checked' and check['compared_bases']==0


def test_duplicate_same_metadata_retained_but_conflicting_file_not_selected():
    data=(BASE/'combined.xmfa').read_bytes()
    same=native_document(data=data.replace(b'#Sequence1File\tcombined.fa',b'#Sequence1File\tcombined.fa\n#Sequence1File\tcombined.fa'))
    result=bind(same)
    assert result['members'][0]['state']=='resolved'
    assert len(result['members'][0]['metadata_indices'])==4
    bad=native_document(data=data.replace(b'#Sequence1File\tcombined.fa',b'#Sequence1File\tcombined.fa\n#Sequence1File\tother.fa'))
    result=bind(bad)
    assert result['members'][0]['state']=='conflicting'
    assert result['members'][1]['state']=='resolved'


def test_missing_entry_remains_missing_without_row_position_fallback():
    data=(BASE/'combined.xmfa').read_bytes().replace(b'#Sequence2Entry\t2\n',b'')
    result=bind(native_document(data=data))
    assert result['members'][1]['state']=='missing'
    assert result['members'][0]['state']=='resolved'


@pytest.mark.parametrize('invalid_entry',[b'1e0',b'+1',b'NA',b'0'])
def test_entry_tokens_require_native_decimal_ordinal_syntax(invalid_entry):
    data=(BASE/'combined.xmfa').read_bytes().replace(b'#Sequence1Entry\t1',b'#Sequence1Entry\t'+invalid_entry)
    result=bind(native_document(data=data))
    assert result['members'][0]['state']=='conflicting'
    assert result['members'][0]['source_length'] is None


def test_multiple_candidate_paths_do_not_choose_first_matching_record():
    inputs=supplied();duplicate=deepcopy(inputs['files'][0]);duplicate['file_id']='other'
    inputs['files'].append(duplicate)
    result=bind(inputs=inputs)
    assert all(m['state']=='conflicting' for m in result['members'])


def mapping(inputs, *, occurrence=0, offset=10):
    return {'file_id':'combined.fa','record_id':'row:0','staged_interval_0based_half_open':[0,50],
        'original_member':{'input_binding_id':'original','member_id':'same-label','occurrence_index':occurrence},
        'original_length':100,'original_interval_0based_half_open':[offset,offset+50],
        'strand':'+','transformation_id':'supplied-map','evidence':inputs['files'][0]['path_binding_evidence']}


def test_original_maps_optional_distinct_occurrences_retained_conflicts_qualified():
    inputs=supplied();inputs['original_maps']=[mapping(inputs),mapping(inputs,occurrence=1,offset=20)]
    result=bind(inputs=inputs)
    assert result['status']=='ok' and len(result['original_maps'])==2
    inputs['original_maps'][1]['original_member']['occurrence_index']=0
    result=bind(inputs=inputs)
    assert result['status']=='partial' and 'xmfa_original_map_conflict' in reasons(result)
    assert len(result['original_maps'])==2


@pytest.mark.parametrize('field,value', [('original_interval_0based_half_open',[0,49]),
    ('staged_interval_0based_half_open',[0,200]),('original_length',20),('strand','unknown')])
def test_wrong_original_map_bounds_and_types_fail_explicitly(field,value):
    inputs=supplied();m=mapping(inputs);m[field]=value;inputs['original_maps']=[m]
    with pytest.raises(ValueError,match='xmfa_'):
        validate_xmfa_source_inputs(inputs)


@pytest.mark.parametrize('field,value', [('source_length',51),('state','unknown'),
    ('metadata_indices',[1,1]),('components',[])])
def test_saved_binding_internal_relationships_checked(field,value):
    result=bind();result['members'][0][field]=value
    with pytest.raises(ValueError,match='xmfa_'):
        validate_xmfa_source_bindings(result)


def test_saved_match_flag_does_not_override_changed_source_sequence():
    document=native_document();result=bind(document)
    result['members'][0]['source_sequence']='A'+result['members'][0]['source_sequence'][1:]
    with pytest.raises(ValueError,match='xmfa_source_checks_conflict'):
        validate_xmfa_bindings_for_document(document,result)


def test_saved_original_map_rechecks_bound_source_length():
    inputs=supplied();inputs['original_maps']=[mapping(inputs)]
    result=bind(inputs=inputs)
    result['original_maps'][0]['staged_interval_0based_half_open']=[0,51]
    result['original_maps'][0]['original_interval_0based_half_open']=[10,61]
    with pytest.raises(ValueError,match='original_map_outside_source'):
        validate_xmfa_source_bindings(result)


@pytest.mark.parametrize('change',['duplicate_record','source_gap','unknown_map_record','bad_requirement'])
def test_malformed_closed_source_operands_are_explicit_errors(change):
    inputs=supplied()
    if change=='duplicate_record': inputs['files'][0]['records'].append(deepcopy(inputs['files'][0]['records'][0]))
    if change=='source_gap': inputs['files'][0]['records'][0]['sequence']+='-'
    if change=='unknown_map_record':
        inputs['original_maps']=[mapping(inputs)];inputs['original_maps'][0]['record_id']='absent'
    if change=='bad_requirement':
        result=bind();result['requirements']=[{'made_up':'field'}]
        with pytest.raises(ValueError,match='xmfa_'):
            validate_xmfa_source_bindings(result)
    else:
        with pytest.raises(ValueError,match='xmfa_'):
            validate_xmfa_source_inputs(inputs)


def test_saved_binding_does_not_accept_foreign_document_or_entry():
    document=native_document();result=bind(document)
    result['document_id']='unrelated'
    with pytest.raises(ValueError,match='xmfa_source_document_conflict'):
        validate_xmfa_bindings_for_document(document,result)
    result=bind(document);result['members'][0]['entry_1based']=2
    result['members'][0]['components'][0]['entry_1based']=2
    with pytest.raises(ValueError,match='xmfa_source_entry_conflict'):
        validate_xmfa_bindings_for_document(document,result)


@pytest.mark.parametrize('change', ['multiple_file_entry', 'format_conflict'])
def test_saved_binding_rejects_contradictory_native_metadata(change):
    data=(BASE/'separate.xmfa').read_bytes()
    extra=(b'#Sequence1Entry\t1\n' if change=='multiple_file_entry'
           else b'#Sequence1Format\tFastA\n')
    data=data.replace(b'#FormatVersion Mauve1\n',b'#FormatVersion Mauve1\n'+extra)
    # Native files use a tab; preserve that delimiter when adding the fixture.
    if extra not in data:
        data=data.replace(b'#FormatVersion\tMauve1\n',b'#FormatVersion\tMauve1\n'+extra)
    assert extra in data
    document=native_document('metadata-original.xmfa',data)
    result=bind(document,supplied('multiple_files_concatenated'))
    assert result['members'][0]['state']=='resolved'
    replacement=(b'#Sequence1Entry\t9\n' if change=='multiple_file_entry'
                 else b'#Sequence1Format\tGenBank\n')
    changed=native_document('metadata-changed.xmfa',data.replace(extra,replacement,1))
    # Source sequences and coordinate checks are unchanged, but the native
    # association declaration now contradicts the saved resolved binding.
    result['document_id']=changed['document_id']
    with pytest.raises(ValueError,match='xmfa_source_(entry|format)_conflict'):
        validate_xmfa_bindings_for_document(changed,result)


def test_native_tab_delimiter_preserves_leading_spaces_in_exact_file_token():
    data=(BASE/'combined.xmfa').read_bytes().replace(b'File\tcombined.fa',b'File\t  combined.fa')
    inputs=supplied();inputs['files'][0]['native_path_token']='  combined.fa'
    result=bind(native_document(data=data),inputs)
    assert result['status']=='ok'
    assert all(m['native_file_token']=='  combined.fa' for m in result['members'])


def test_pure_binding_and_saved_recheck_without_any_acquisition(monkeypatch):
    document=native_document();inputs=supplied();expected=bind(document,inputs)
    with monkeypatch.context() as locked:
        locked.setattr(builtins,'open',forbidden);locked.setattr(Path,'open',forbidden)
        locked.setattr(Path,'read_bytes',forbidden);locked.setattr(socket,'socket',forbidden)
        locked.setattr(subprocess,'Popen',forbidden)
        locked.setattr('gene_annotation_episode.xmfa_formats.parse_mauve_xmfa',forbidden)
        result=bind(document,inputs)
        assert result==expected
        assert validate_xmfa_bindings_for_document(document,json.loads(json.dumps(result)))==expected
