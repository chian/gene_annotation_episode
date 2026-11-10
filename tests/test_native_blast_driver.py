"""Synthetic faults exercise one-process custody; real jobs are retained in 294."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.native_blast_contracts import requested_job_from_native, native_blast_digest
from gene_annotation_episode.native_blast_driver import run_native_blast, validate_native_blast_bundle_files, main
from test_native_blast_contracts import job_for


def plan_for(tmp_path,program='blastp'):
    job=job_for(program)
    executable=tmp_path/'executable'
    executable.write_text('synthetic executable; invocation replaced by test')
    executable.chmod(0o700)
    job['software'].update(executable=str(executable),sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),engine_version='synthetic')
    for row in job['operands']:
        path=tmp_path/(row['role']+'.fa');path.write_text('>'+row['role']+'\nACGTACGT\n')
        row.update(path=str(path),size_bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    request=requested_job_from_native(job)
    return {'version':'native_blast_run_plan_v1','identity':{'run_id':'synthetic','episode_id':'resource-child','resource_id':'local',
        'execution_id':'original','attempt_id':'one','operation_key':'selected-start','requested_job_sha256':native_blast_digest(request)},
        'requested_job':request,'attempt_directory':str(tmp_path/'attempt'),
        'policy':{'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}}


def seal(plan):
    plan['requested_job']=requested_job_from_native(plan['requested_job']['native_blast'])
    plan['identity']['requested_job_sha256']=native_blast_digest(plan['requested_job'])
    return plan


def fake_native(monkeypatch,*,returncode=0,report=b'{"synthetic":"retained"}',escape=None):
    calls=[]
    def run(argv,**kwargs):
        calls.append((argv,kwargs))
        kwargs['stdout'].write(b'complete synthetic stdout\n')
        kwargs['stderr'].write(b'complete synthetic stderr\n')
        path=Path(argv[argv.index('-out')+1])
        if escape:path.symlink_to(escape)
        elif report is not None:path.write_bytes(report)
        return subprocess.CompletedProcess(argv,returncode)
    monkeypatch.setattr('gene_annotation_episode.native_blast_driver.subprocess.run',run)
    return calls


def test_exact_original_staging_sealed_replay_and_original_source_independence(tmp_path,monkeypatch):
    plan=plan_for(tmp_path);calls=fake_native(monkeypatch)
    bundle=run_native_blast(plan)
    assert bundle['failures']==[] and bundle['returncode']==0 and len(calls)==1
    root=Path(plan['attempt_directory'])
    for row in bundle['inputs']:
        assert (root/row['relative_path']).read_bytes()==Path(row['original_path']).read_bytes()
        assert row['actual_sha256']==row['expected_sha256']
        Path(row['original_path']).unlink()
    assert bundle['requested_job']['argv']!=bundle['realized_argv']
    assert 'timeout' not in calls[0][1]
    before=(root/'bundle.json').read_bytes()
    assert run_native_blast(plan)==bundle and len(calls)==1
    assert (root/'bundle.json').read_bytes()==before


@pytest.mark.parametrize('fault,code',[
 ('missing','input_missing'),('size','input_size_mismatch'),('digest','input_digest_mismatch'),
 ('software_missing','software_unavailable'),('software_digest','software_digest_mismatch'),('scratch','scratch_limit'),
 ('multiple','exactly_one_fasta_record'),('no_header','fasta_input_required'),('empty','nonempty_fasta'),
 ('molecule','molecule_symbols_conflict'),('range','selected_interval_outside'),('binding','operand_name_conflict'),
])
def test_preexecution_fault_retains_failure_without_invocation_and_replays(tmp_path,monkeypatch,fault,code):
    plan=plan_for(tmp_path,'blastn');job=plan['requested_job']['native_blast'];row=job['operands'][0]
    path=Path(row['path'])
    if fault=='missing':row['path']=str(tmp_path/'missing')
    elif fault=='size':row['size_bytes']+=1
    elif fault=='digest':row['sha256']='0'*64
    elif fault=='software_missing':job['software']['executable']=str(tmp_path/'missing')
    elif fault=='software_digest':job['software']['sha256']='0'*64
    elif fault=='scratch':plan['policy']['scratch_bytes']=1
    elif fault=='range':job['options']+=['-query_loc','1-50']
    elif fault=='binding':job['operand_bindings']=[{'operand_role':'query_sequence','record_ordinal':0,
        'native_name':'other','native_accession':None,'subject_ref':None,'reference_ref':None}]
    else:
        text={'multiple':'>first\nACGT\n>second\nACGT\n','no_header':'ACGT\n','empty':'>first\n','molecule':'>first\nPEPTIDE\n'}[fault]
        path.write_text(text);row.update(size_bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    seal(plan);calls=fake_native(monkeypatch);bundle=run_native_blast(plan)
    assert not calls and bundle['returncode'] is None
    assert any(code in row['code'] for row in bundle['failures'])
    assert run_native_blast(plan)==bundle and not calls


@pytest.mark.parametrize('returncode,report',[(7,b'partial native output'),(0,None),(0,b'')])
def test_nonzero_partial_missing_and_empty_remain_distinct(tmp_path,monkeypatch,returncode,report):
    plan=plan_for(tmp_path);calls=fake_native(monkeypatch,returncode=returncode,report=report)
    bundle=run_native_blast(plan)
    assert bundle['returncode']==returncode and len(calls)==1
    roles={r['role']:r for r in bundle['artifacts']}
    assert {'stdout','stderr'}<=roles.keys()
    assert ('primary_report' in roles)==(report is not None)
    assert any('missing_output' in r['code'] for r in bundle['failures'])==(report is None)
    assert any('nonzero_returncode' in r['code'] for r in bundle['failures'])==(returncode!=0)
    if report==b'':assert roles['primary_report']['size_bytes']==0
    assert run_native_blast(plan)==bundle and len(calls)==1


@pytest.mark.parametrize('category',['input','output'])
def test_changed_retained_bytes_fail_replay_without_recapture(tmp_path,monkeypatch,category):
    plan=plan_for(tmp_path);calls=fake_native(monkeypatch);bundle=run_native_blast(plan)
    row=bundle['inputs' if category=='input' else 'artifacts'][0]
    path=Path(plan['attempt_directory'])/row['relative_path'];path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='digest_mismatch'):run_native_blast(plan)
    path.unlink();path.symlink_to(Path(bundle['inputs'][0]['original_path']))
    with pytest.raises(ValueError,match='path_escape'):validate_native_blast_bundle_files(bundle,plan['attempt_directory'])
    assert len(calls)==1


def test_nonowned_unsealed_and_changed_identity_never_invoke_again(tmp_path,monkeypatch):
    plan=plan_for(tmp_path);calls=fake_native(monkeypatch);run_native_blast(plan)
    changed=deepcopy(plan);changed['identity']['operation_key']='different'
    with pytest.raises(ValueError,match='identity_conflict'):run_native_blast(changed)
    Path(plan['attempt_directory'],'bundle.json').unlink()
    with pytest.raises(ValueError,match='execution_uncertain'):run_native_blast(plan)
    assert len(calls)==1


def test_unowned_directory_and_cli_argument_count(tmp_path):
    with pytest.raises(ValueError,match='exact_plan'):main([])
    plan=plan_for(tmp_path);Path(plan['attempt_directory']).mkdir()
    with pytest.raises(ValueError,match='not_exclusively_owned'):run_native_blast(plan)


def test_output_symlink_is_retained_as_failure_not_external_artifact(tmp_path,monkeypatch):
    plan=plan_for(tmp_path);fake_native(monkeypatch,escape=plan['requested_job']['native_blast']['operands'][0]['path'])
    bundle=run_native_blast(plan)
    assert any(r['code']=='native_blast_invalid_output' for r in bundle['failures'])
    assert {r['role'] for r in bundle['artifacts']}=={'stdout','stderr'}
