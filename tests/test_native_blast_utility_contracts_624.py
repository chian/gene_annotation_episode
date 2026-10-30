"""Compiler and shared preparation-consumer checks; no native reruns."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.blast_database_preparation import (
    populate_database_artifact_set, project_prepared_blast_database,
)
from gene_annotation_episode.native_blast_utility_contracts import (
    compile_native_blast_utility_job, validate_native_blast_utility_job,
    requested_job_from_native_blast_utility, validate_native_blast_utility_requested_job,
)
from gene_annotation_episode.native_blast_utility_tool_info import native_blast_utility_tool_contracts
from test_blast_utility_contracts_625 import operation

EVIDENCE = Path(__file__).resolve().parents[1]/'verification/tool_graders_blast_database_preparation_2026-10-28_627'


def native_case(name='build_dna_v5'):
    data=json.loads((EVIDENCE/'PREPARATION_INPUTS_001.json').read_text())
    return next(r for r in data['cases'] if r['name']==name)['arguments'],data['source_capture']


def build_job(name='build_dna_v5'):
    a,receipt=native_case(name)
    return {'version':'native_blast_utility_job_v1','operation':a['operation'],
        'software':{'executable':a['argv'][0],'sha256':a['software']['executable_sha256'],'engine_version':None},
        'environment':{'BLAST_USAGE_REPORT':'false','NCBI_DONT_USE_NCBIRC':'1'},
        'inputs':[{'input_key':r['occurrence_id'],'role':r['role'],'path':r['native_path'],
            'format':r['native_format'],'sha256':r['sha256'],'size_bytes':r['size_bytes'],
            'artifact_ref':r['artifact_ref']} for r in a['inputs']],
        'databases':[], 'outputs':[
            {'role':'stdout','path_kind':'file','relative_path':'stdout.txt','format':'text'},
            {'role':'stderr','path_kind':'file','relative_path':'stderr.txt','format':'text'},
            {'role':'database_family','path_kind':'prefix','relative_path':'database','format':'blastdb_family'}]}


def inspect_job(mode='extract_sequences',name='build_dna_v5'):
    a,receipt=native_case(name)
    record=populate_database_artifact_set(**a)
    result=project_prepared_blast_database(record,contract='standard',
        preparation_receipt=receipt,input_manifest=None,metadata_manifests=[])
    manifest=result['manifest']
    assert result['status']=='available'
    raw=json.dumps(manifest,sort_keys=True).encode()
    op=operation(mode,molecule=a['operation']['molecule'])
    op['database_key']=manifest['database_key']
    program=op['program']
    job={'version':'native_blast_utility_job_v1','operation':op,
        'software':{'executable':'/configured/'+program,'sha256':'b'*64,'engine_version':None},
        'environment':{},'inputs':[], 'databases':[{
            'database_key':manifest['database_key'],'kind':manifest['kind'],'identity':manifest['identity'],
            'native_paths':manifest['native_paths'],'role':'target','manifest':manifest,
            'manifest_file':{'path':'/retained/manifest.json','sha256':hashlib.sha256(raw).hexdigest(),
                             'size_bytes':len(raw),'artifact_ref':None}}],
        'outputs':[{'role':'stdout','path_kind':'file','relative_path':'stdout.txt',
            'format':{'extract_sequences':'blastdbcmd_tabular_v1','info':'blastdb_info_text',
                      'metadata':'blastdb_metadata_json','integrity':'blastdbcheck_text'}[mode]},
            {'role':'stderr','path_kind':'file','relative_path':'stderr.txt','format':'text'}]}
    return job


def compile_job(job,output_directory='/selected/output'):
    return compile_native_blast_utility_job(job,
        input_paths={r['input_key']:r['path'] for r in job['inputs']},
        database_paths={r['database_key']:r['native_paths'] for r in job['databases']},
        output_directory=output_directory)


@pytest.mark.parametrize('name',['build_dna_v4','build_dna_v5','build_protein_v5'])
def test_makeblastdb_compiler_reproduces_original_native_command(name):
    args,_=native_case(name)
    job=build_job(name)
    output_directory=str(Path(args['native_paths'][0]).parent)
    assert compile_job(job,output_directory)==args['argv']
    request=requested_job_from_native_blast_utility(job)
    assert validate_native_blast_utility_requested_job(request)==request
    assert request['argv'][request['argv'].index('-out')+1]=='database'


@pytest.mark.parametrize('mode',['extract_sequences','info','metadata','integrity'])
def test_actual_prepared_manifest_reaches_selected_compiler_without_native_work(mode):
    job=inspect_job(mode)
    argv=compile_job(job)
    assert argv[0]==job['software']['executable']
    assert argv[argv.index('-db')+1]==job['databases'][0]['native_paths'][0]
    assert argv[argv.index('-dbtype')+1]=='nucl'
    assert argv.count(argv[0])==1
    assert ('-entry' in argv)==(mode=='extract_sequences')
    assert ('-full' in argv)==(mode=='integrity')
    assert ('-info' in argv)==(mode=='info')
    assert ('-metadata' in argv)==(mode=='metadata')
    assert argv==compile_job(json.loads(json.dumps(job)))


def test_range_strand_and_duplicate_requests_are_literal_selected_operands():
    job=inspect_job()
    job['operation']['parameters'].update(selectors=[{'ordinal':0,'value':'seqB'},{'ordinal':1,'value':'seqB'}],
        range={'start_1based':2,'end_1based':7},strand='minus')
    argv=compile_job(job)
    assert argv[argv.index('-entry')+1]=='seqB,seqB'
    assert argv[argv.index('-range')+1]=='2-7'
    assert argv[argv.index('-strand')+1]=='minus'
    assert argv[argv.index('-outfmt')+1]=='%o\t%i\t%a\t%l\t%s'


@pytest.mark.parametrize('change',[
    lambda j:j['operation']['parameters'].update(get_dups=True,target_only=True),
    lambda j:j['operation']['parameters']['selectors'][0].update(value='all'),
    lambda j:j['operation'].update(database_key='unselected'),
    lambda j:j['operation'].update(molecule='protein'),
    lambda j:j['databases'][0]['manifest'].update(inventory_complete=False),
    lambda j:j['environment'].update(TMPDIR='/unowned'),
    lambda j:j['outputs'][0].update(relative_path='../elsewhere'),
    lambda j:j['outputs'][0].update(relative_path='stderr.txt'),
])
def test_unselected_or_invalid_work_rejected_before_execution(change):
    job=inspect_job()
    change(job)
    with pytest.raises((ContractError,ValueError)):
        compile_job(job)


def test_cannot_substitute_original_command_or_environment_after_selection():
    request=requested_job_from_native_blast_utility(build_job())
    request['argv']+=['-taxid','9606']
    with pytest.raises(ContractError,match='requested_command_conflict'):
        validate_native_blast_utility_requested_job(request)


def test_pure_compilation_never_reads_paths_or_invokes_software(monkeypatch):
    job=inspect_job()
    import builtins,socket,subprocess
    def forbidden(*a,**k): pytest.fail('pure command compiler performed IO')
    for obj,key in ((builtins,'open'),(Path,'open'),(Path,'resolve'),
                    (subprocess,'run'),(subprocess,'Popen'),(socket,'socket')):
        monkeypatch.setattr(obj,key,forbidden)
    assert compile_job(job)


def test_configured_information_cannot_advertise_different_software_or_resource():
    job=build_job()
    bindings=[{'program':'makeblastdb','mode':'create_sequence_database',
               'software':job['software'],'molecules':['dna','protein']}]
    info=native_blast_utility_tool_contracts(bindings,resource_kind='local',resource_id='chosen-local')[0]
    assert set(('name','description','resources','instructions'))<=set(info)
    assert info['invocation_route']['routes'][0]['resource_id']=='chosen-local'
    request=requested_job_from_native_blast_utility(job)
    jsonschema.Draft202012Validator(info['input_schema']).validate(request)
    other=deepcopy(request)
    other['native_blast_utility']['software']['executable']='/different/software'
    assert list(jsonschema.Draft202012Validator(info['input_schema']).iter_errors(other))
    with pytest.raises(ContractError,match='configured_local_resource_required'):
        native_blast_utility_tool_contracts(bindings,resource_kind='hpc',resource_id='not-configured')
