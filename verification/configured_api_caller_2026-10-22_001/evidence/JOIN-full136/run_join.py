from pathlib import Path
import hashlib,json,os,shlex,shutil,stat,subprocess,sys,time
ROOT=Path('/tmp/gene-annotation-configured-caller-20261022-006')
EVIDENCE=Path(__file__).resolve().parent
PYTHON='/home/chia/repos/gene_annotation_episode/.venv/bin/python'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def check_baseline():
    baseline=json.loads((ROOT/'GENERATION_BASELINE_006.json').read_text());out={}
    for group in ('files','static_assets','instructions'):
        errors=[]
        for name,item in baseline[group].items():
            path=ROOT/name
            if not path.is_file() or sha(path)!=item['sha256'] or path.stat().st_size!=item['bytes']:errors.append(name)
        out[group]={'count':len(baseline[group]),'mismatches':errors}
    assert not any(item['mismatches'] for item in out.values()),out
    return out

def inputs():
    files=sorted(path for pkg in ('gene_annotation_episode','method_loop') for path in (ROOT/pkg).rglob('*.py'))
    digest=hashlib.sha256()
    values={}
    for path in files:
        name=str(path.relative_to(ROOT));raw=path.read_bytes();hashed=hashlib.sha256(raw)
        digest.update(name.encode()+b'\0');digest.update(hashed.digest())
        values[name]={'sha256':hashed.hexdigest(),'bytes':len(raw)}
    for name in ('tests/test_scientific_checkpoint_api_caller.py','tests/test_scientific_checkpoint_fork.py',
            'tests/test_api_planning_case_policy.py','GENERATION_BASELINE_006.json','ADDITIONAL_TEST_INPUTS006.json',
            'docs/SCIENTIFIC_CHECKPOINT_API_CALLER_JOIN_SCOPE_2026-10-22_001.md',
            'verification/scientific_checkpoint_custody_plan_2026-10-22_001/SCHEMAS004.json'):
        path=ROOT/name;values[name]={'sha256':sha(path),'bytes':path.stat().st_size}
    return {'runtime_file_count':len(files),'implementation_sha256':digest.hexdigest(),'files':values,'baseline':check_baseline()}

def tree(path):
    out={}
    for item in [path,*sorted(path.rglob('*'))] if path.exists() else []:
        info=item.lstat();rel='.' if item==path else str(item.relative_to(path))
        entry={'mode':stat.S_IMODE(info.st_mode),'mtime_ns':info.st_mtime_ns}
        if stat.S_ISLNK(info.st_mode):entry.update(kind='symlink',target=os.readlink(item))
        elif stat.S_ISDIR(info.st_mode):entry['kind']='directory'
        elif stat.S_ISREG(info.st_mode):entry.update(kind='file',bytes=info.st_size,sha256=sha(item))
        else:raise AssertionError((str(item),info.st_mode))
        out[rel]=entry
    return out

if __name__=='__main__':
    expected_pin=sys.argv[1];invocation=EVIDENCE/sys.argv[2];invocation.mkdir()
    before=inputs();dump(invocation/'INPUTS_BEFORE.json',before)
    assert before['runtime_file_count']==136
    assert before['implementation_sha256']==expected_pin
    assert before['files']['gene_annotation_episode/api_planning_case_policy.py']['sha256']=='4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f'
    assert before['files']['verification/scientific_checkpoint_custody_plan_2026-10-22_001/SCHEMAS004.json']['sha256']=='b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112'
    for name in before['files']:
        dest=invocation/'input-snapshots'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    basetemp=invocation/'basetemp';assert not basetemp.exists()
    command=[PYTHON,'-m','pytest','-q','tests/test_scientific_checkpoint_api_caller.py','--basetemp',str(basetemp),'--junitxml',str(invocation/'junit.xml')]
    dump(invocation/'COMMAND.json',{'cwd':str(ROOT),'argv':command,'shell_display':shlex.join(command)})
    start=time.time()
    with (invocation/'stdout.log').open('wb') as output:
        result=subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT)
    elapsed=time.time()-start
    raw=tree(basetemp);dump(invocation/'RAW_FIXTURE_TREE.json',{'version':'raw_fixture_tree_v1','original_base':str(basetemp),'retained_base':str(basetemp),'members':raw})
    after=inputs();dump(invocation/'INPUTS_AFTER.json',after)
    changed={name:{'before':item,'after':after['files'].get(name)} for name,item in before['files'].items() if after['files'].get(name)!=item}
    report={'version':'joined_fixture_invocation_v1','exit_code':result.returncode,'elapsed_seconds':elapsed,'source_pin':expected_pin,'runtime_source_unchanged':before['implementation_sha256']==after['implementation_sha256'],'input_changes':changed,'raw_member_count':len(raw),'raw_regular_file_count':sum(item['kind']=='file' for item in raw.values()),'original_scientific_state_opened':False,'actual_model_public_HTTP_native_calls':0}
    dump(invocation/'INVOCATION_RESULT.json',report)
    print(json.dumps(report,sort_keys=True));sys.exit(result.returncode if not changed else 90)
