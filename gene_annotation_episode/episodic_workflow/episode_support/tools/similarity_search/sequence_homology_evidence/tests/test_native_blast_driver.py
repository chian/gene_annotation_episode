"""Synthetic faults exercise one-process custody; real jobs are retained in 294."""
from gene_annotation_episode.workflow_budget import ENVIRONMENT_BOUNDS
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.native_blast_contracts import requested_job_from_native, native_blast_digest
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.native_blast_driver import run_native_blast, validate_native_blast_bundle_files, main
from gene_annotation_episode.episodic_workflow.episode_support.forms.similarity_search.tests.test_native_blast_contracts import job_for


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
        'policy':{'memory_bytes': ENVIRONMENT_BOUNDS['memory_bytes'], 'scratch_bytes': 4 * 1024 ** 3}}


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
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence.native_blast_driver.subprocess.run',run)
    return calls


def test_unowned_directory_and_cli_argument_count(tmp_path):
    with pytest.raises(ValueError,match='exact_plan'):main([])
    plan=plan_for(tmp_path);Path(plan['attempt_directory']).mkdir()
    with pytest.raises(ValueError,match='not_exclusively_owned'):run_native_blast(plan)


