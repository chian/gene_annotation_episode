"""Pure selection/compiler tests; no episode-integration claim."""
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode.native_blast_contracts import (
    PROGRAMS, NATIVE_BLAST_JOB_SCHEMA, NATIVE_BLAST_REQUESTED_JOB_SCHEMA,
    compile_native_blast_job, requested_job_from_native, validate_native_blast_job,
    validate_native_blast_requested_job,
)
from gene_annotation_episode.native_blast_tool_info import (
    native_blast_tool_contracts, native_blast_tool_information, validate_native_blast_bindings,
)


def job_for(program='blastp', fmt='json15'):
    return {'version': 'native_blast_job_v1', 'program': program, 'mode': 'pairwise',
        'software': {'executable': '/selected/bin/'+program, 'sha256': 'b'*64, 'engine_version': '2.17.0+'},
        'environment': {}, 'operands': [{'role': role, 'path': '/selected/'+role+'.fa', 'format':'fasta',
            'sha256': 'a'*64, 'size_bytes': 10, 'artifact_ref': None} for role in ('query_sequence','subject_sequence')],
        'operand_bindings': [], 'options':['-num_threads','1'],
        'outputs': [{'role': role,'format':'text','relative_path':role+'.txt','fields':None,'delimiter':None}
                    for role in ('stdout','stderr')] + [{'role':'primary_report','format':fmt,
                    'relative_path':'report','fields':None if fmt=='json15' else ['qseqid','sseqid','qlen','slen','qseq','sseq'],
                    'delimiter':None if fmt=='json15' else '\t'}], 'metadata':{}, 'grading_parameters':{}}


@pytest.mark.parametrize('program',PROGRAMS)
@pytest.mark.parametrize('fmt',['json15','tabular6','tabular7'])
def test_actual_contract_compiles_exact_selected_options_without_io(monkeypatch,program,fmt):
    job=job_for(program,fmt)
    if program in {'blastx','tblastx'}:job['options']+=['-query_gencode','11','-strand','minus']
    if program in {'tblastn','tblastx'}:job['options']+=['-db_gencode','11']
    job['options']+=['-query_loc','3-9','-subject_loc','2-8','-max_hsps','4','-evalue','0.00001']
    original=deepcopy(job)
    monkeypatch.setattr(Path,'open',lambda *a,**k:pytest.fail('pure compiler opened source'))
    monkeypatch.setattr(Path,'resolve',lambda *a,**k:pytest.fail('pure compiler resolved path'))
    compiled=compile_native_blast_job(job)
    assert compiled['argv'][1:1+len(job['options'])]==job['options']
    request=requested_job_from_native(job)
    assert validate_native_blast_requested_job(request)==request
    Draft202012Validator(NATIVE_BLAST_JOB_SCHEMA).validate(job)
    Draft202012Validator(NATIVE_BLAST_REQUESTED_JOB_SCHEMA).validate(request)
    staged=compile_native_blast_job(job,input_paths={r['role']:'/attempt/'+r['role'] for r in job['operands']},output_directory='/attempt')
    assert staged['argv'][staged['argv'].index('-query')+1]=='/attempt/query_sequence'
    assert staged['argv'][-1]=='/attempt/report'
    assert job==original


@pytest.mark.parametrize('options,code',[
 (['-query','elsewhere'],'compiler_owned'),(['-subject','elsewhere'],'compiler_owned'),(['-outfmt','6'],'compiler_owned'),
 (['-out','elsewhere'],'compiler_owned'),(['-remote'],'forbidden'),(['-db','nt'],'forbidden'),
 (['-import_search_strategy','file'],'forbidden'),(['-export_search_strategy','file'],'forbidden'),
 (['-use_index','false'],'forbidden'),(['-window_masker_taxid','9606'],'forbidden'),(['-in_pssm','file'],'forbidden'),
 (['-num_threads'],'operand_required'),(['-num_threads','1.2'],'invalid_option'),(['-max_hsps','0'],'invalid_option'),
 (['-evalue','NaN'],'invalid_option'),(['-query_loc','9-2'],'invalid_option'),(['-num_threads','1','-num_threads','2'],'duplicate'),
 (['-culling_limit','1','-best_hit_overhang','0.1'],'conflicting'),(['-mt_mode','1'],'required_option'),
 (['-max_target_seqs','1','-num_alignments','1'],'conflicting'),(['-query_gencode','11'],'unsupported'),
])
def test_rejects_unselected_operands_resources_and_invalid_options(options,code):
    job=job_for();job['options']=options
    with pytest.raises(ValueError,match=code):validate_native_blast_job(job)


@pytest.mark.parametrize('program,options',[
 ('blastn',['-task','dc-megablast','-template_type','coding','-template_length','18','-dust','20 64 1','-penalty','-2','-reward','1']),
 ('blastp',['-task','blastp-short','-seg','12 2.2 2.5','-comp_based_stats','0','-matrix','PAM30','-ungapped']),
 ('blastx',['-task','blastx-fast','-query_gencode','11','-sum_stats','true']),
 ('tblastn',['-task','tblastn-fast','-db_gencode','4','-max_intron_length','0']),
 ('tblastx',['-strand','both','-query_gencode','11','-db_gencode','11']),
])
def test_documented_scientific_options_are_preserved(program,options):
    job=job_for(program);job['options']=options
    assert compile_native_blast_job(job)['argv'][1:1+len(options)]==options


@pytest.mark.parametrize('path',['../escape','/absolute','a/../b','a//b','inputs/x','tmp/x','cache/x','bundle.json','.native-blast-owner.json','.bundle.json.writing'])
def test_output_paths_are_confined(path):
    job=job_for();job['outputs'][-1]['relative_path']=path
    with pytest.raises(ValueError):validate_native_blast_job(job)


def test_tabular_contract_is_explicit_and_preserves_custom_delimiter():
    job=job_for(fmt='tabular7');job['outputs'][-1]['delimiter']='@'
    assert compile_native_blast_job(job)['argv'][-3]=='7 delim=@ qseqid sseqid qlen slen qseq sseq'
    job['outputs'][-1]['fields']=['std']
    with pytest.raises(ValueError,match='explicit_tabular_fields'):validate_native_blast_job(job)
    job=job_for(fmt='tabular6');job['outputs'][-1]['delimiter']=None
    with pytest.raises(ValueError,match='delimiter'):validate_native_blast_job(job)


def test_requested_job_cannot_replace_compiler_inputs_or_environment():
    for field,value in [('argv',['/other']),('environment',{'EXTRA':'1'})]:
        request=requested_job_from_native(job_for());request[field]=value
        with pytest.raises(ValueError,match='compiler_mismatch'):validate_native_blast_requested_job(request)


@pytest.mark.parametrize('bad',[float('nan'),(1,2),{1:'value'}])
def test_nonfinite_or_non_json_metadata_rejected(bad):
    job=job_for();job['metadata']={'bad':bad}
    with pytest.raises(ValueError,match='finite_json'):validate_native_blast_job(job)


def test_configured_public_rows_have_exactly_four_fields_and_only_local_commission():
    bindings=[{'program':p,'mode':'pairwise','software':job_for(p)['software']} for p in PROGRAMS]
    contracts=native_blast_tool_contracts(bindings,resource_kind='local',resource_id='selected-local')
    public=native_blast_tool_information(bindings,resource_kind='local',resource_id='selected-local')
    assert len(public)==5 and all(set(r)=={'name','description','resources','instructions'} for r in public)
    for program,contract in zip(PROGRAMS,contracts):
        assert contract['invocation_route']=={'kind':'commission','routes':[{'entry_role':'launch','resource_role':'launch_local','resource_id':'selected-local'}]}
        validator=Draft202012Validator(contract['input_schema'])
        assert validator.is_valid(requested_job_from_native(job_for(program)))
        changed=job_for(program);changed['software']['sha256']='c'*64
        assert not validator.is_valid(requested_job_from_native(changed))
    with pytest.raises(ValueError,match='local_paired_resource'):native_blast_tool_contracts(bindings,resource_kind='hpc',resource_id='hpc')
    with pytest.raises(ValueError,match='duplicate_program_mode'):validate_native_blast_bindings(bindings+[bindings[0]])
