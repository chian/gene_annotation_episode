"""Actual publication inventory method and original Python script, no native job."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from .. import native_blast_database_result_publication as publication
from .. import native_blast_database_result_worker as worker
from ..local_jobs import LocalJobPolicy

PROFILE=Path(__file__).parent/'fixtures/native07_publication_inventory_owners.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('program,function_mode',(('blastp',False),('psiblast',False),('deltablast',False),('blastn',True)))
def test_actual_publication_inventory_uses_current_owners_and_authenticates_cached_bytes(tmp_path,monkeypatch,program,function_mode):
    profile=json.loads(PROFILE.read_bytes());calls=[]
    def controlled_interpreter(command,*,cwd,policy,stdout_path,stderr_path,env):
        # Execute the exact original local interpreter payload inside the parent
        # workload. No native executable, provider, network or separate policy
        # launcher is selected by this controlled port.
        assert command[:3]==[sys.executable,'-B','-c'] and len(command)==6
        assert command[5]==str(tmp_path/'implementation.json')
        assert Path(cwd)==tmp_path and isinstance(policy,LocalJobPolicy)
        calls.append(command)
        with Path(stdout_path).open('wb') as stdout,Path(stderr_path).open('wb') as stderr:
            result=subprocess.run(command,cwd=cwd,env={**os.environ,**env},stdout=stdout,stderr=stderr,check=False)
        return SimpleNamespace(returncode=result.returncode,metadata={'controlled_python_source_inventory':True,'native_program_executed':False})
    monkeypatch.setattr(publication,'run_local_job',controlled_interpreter)
    policy=LocalJobPolicy.from_config()
    result=publication._implementation(tmp_path,policy,execution_program=program,vdb_function=function_mode)
    selected=list(profile['base_modules'])
    if program in ('psiblast','deltablast'):selected+=profile['iteration_modules']
    if function_mode:selected+=profile['function_modules']
    expected={profile['current_owners'][name] for name in selected}
    actual={row['module'] for row in result['files'] if row['module'].startswith(profile['axis']+'.')}
    assert actual==expected and len(calls)==1
    required = {name for name in worker._implementation_modules(
        execution_program=program, vdb_function=function_mode)
        if name.startswith(profile['axis'] + '.')}
    assert actual == required
    assert result['manifest_sha256']==publication.native_blast_database_implementation_identity(result['files'])
    for row in result['files']:assert sha(Path(row['path']).read_bytes())==row['sha256']
    receipt=json.loads((tmp_path/'implementation-receipt.json').read_bytes())
    assert receipt=={'controlled_python_source_inventory':True,'native_program_executed':False}
    assert publication._implementation(tmp_path,policy,execution_program=program,vdb_function=function_mode)==result
    assert len(calls)==1
    changed=json.loads((tmp_path/'implementation.json').read_bytes());changed['files'][0]['sha256']='0'*64
    (tmp_path/'implementation.json').write_text(publication.canonical(changed)+'\n')
    with pytest.raises(publication.ContractError,match='native_blast_database_implementation_identity_conflict'):
        publication._implementation(tmp_path,policy,execution_program=program,vdb_function=function_mode)
    assert len(calls)==1
