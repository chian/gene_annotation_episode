"""Reconstruct reviewed literature changes, excluding later shared-main edits."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
ORIGIN = BASE / 'literature_model_run_024/pin_001'
DEST = BASE / 'literature_model_run_030/pin_001'
ORIGIN_HASH = '77d12c3fa01403640d47aa8c38a3a4f7b0f9d06c9408f94537e010f865ce6940'
LAYERS = [
 ('amount_components_027/SOURCE_MANIFEST_002.json', 'amount_components_027/SOURCE_DELTA_002.patch', 'baseline024_sha256'),
 ('numeric_range_scope_029/SOURCE_MANIFEST_003.json', 'numeric_range_scope_029/SOURCE_DELTA_003.patch', 'baseline_sha256'),
 ('witness_repair_feedback_030/SOURCE_MANIFEST_FINAL.json', 'witness_repair_feedback_030/OWNED_FINAL.diff', 'before_sha256')]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')
def verify(directory, manifest):
    paths=set()
    for row in manifest['files']:
        relative=Path(row['pin_relative_path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        assert str(relative) not in paths
        paths.add(str(relative)); p=directory/relative
        assert not p.is_symlink() and p.stat().st_size==row['size'] and sha(p)==row['sha256'], relative
    assert paths=={str(p.relative_to(directory)) for p in directory.rglob('*')
                   if p.is_file() and p != directory/'SOURCE_MANIFEST.json'}

def main():
    assert sha(ORIGIN/'SOURCE_MANIFEST.json')==ORIGIN_HASH
    origin_manifest=json.loads((ORIGIN/'SOURCE_MANIFEST.json').read_bytes())
    verify(ORIGIN, origin_manifest)
    old={r['pin_relative_path']:r for r in origin_manifest['files']}
    assert not DEST.exists()
    DEST.mkdir(parents=True)
    for relative in old:
        p=DEST/relative; p.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ORIGIN/relative,p)
    layers=[]; expected={}
    for manifest_name, patch_name, before_field in LAYERS:
        doc=json.loads((BASE/manifest_name).read_bytes())
        entries=doc if isinstance(doc,list) else doc['files']
        bypath={row['path']:row for row in entries}
        for relative,row in bypath.items():
            p=DEST/relative; before=row.get(before_field)
            assert (sha(p) if p.exists() else None)==before, (relative,'before',before)
        lines=(BASE/patch_name).read_text().splitlines(keepends=True)
        normalized=[]; seen=[]; index=0
        while index<len(lines):
            line=lines[index]
            if line.startswith('--- ') and index+1<len(lines) and lines[index+1].startswith('+++ '):
                relative=lines[index+1][4:].strip().split(' (')[0]
                if relative.startswith('current027/'): relative=relative[len('current027/'):]
                assert relative in bypath and relative not in seen, relative
                before=bypath[relative].get(before_field)
                normalized.extend(['--- '+('a/'+relative if before else '/dev/null')+'\n',
                                   '+++ b/'+relative+'\n'])
                seen.append(relative); index+=2
            else:
                normalized.append(line); index+=1
        assert set(seen)==set(bypath)
        result=subprocess.run(['patch','--batch','--fuzz=0','--no-backup-if-mismatch','-p1','-d',str(DEST)],
                              input=''.join(normalized),text=True,capture_output=True)
        log=BASE/'unified_literature_pin_030'/(Path(patch_name).parent.name+'_APPLY.log')
        log.write_text(result.stdout+result.stderr)
        assert result.returncode==0, (patch_name,result.stdout,result.stderr)
        for relative,row in bypath.items():
            assert sha(DEST/relative)==row['sha256'],(relative,'after')
            expected[relative]=row['sha256']
        layers.append({'manifest':manifest_name,'manifest_sha256':sha(BASE/manifest_name),
                       'patch':patch_name,'patch_sha256':sha(BASE/patch_name),
                       'files':len(entries),'exact_after_hashes_verified':True})
    # The029 old-generation reconstruction test uses these unchanged saved facts.
    fixture_root=BASE/'amount_components_027/case025_replay_state_001'
    fixtures=[]
    for p in sorted(fixture_root.rglob('*')):
        if not p.is_file():continue
        relative=str(p.relative_to(ROOT)); target=DEST/relative
        assert not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        fixtures.append({'path':relative,'sha256':sha(target),'size':target.stat().st_size})
    dependencies=set();pending=[r for r in expected if r.startswith('tests/')]
    while pending:
        relative=pending.pop()
        if relative in dependencies:continue
        dependencies.add(relative)
        for node in ast.walk(ast.parse((DEST/relative).read_text())):
            names=([node.module] if isinstance(node,ast.ImportFrom) and node.module else
                   [a.name for a in node.names] if isinstance(node,ast.Import) else [])
            for name in names:
                if name.startswith('test_'):
                    child='tests/'+name+'.py'
                    if (ROOT/child).is_file():
                        assert (DEST/child).is_file(),child
                        pending.append(child)
    shutil.copyfile(ORIGIN/'SOURCE_MANIFEST.json',DEST/'ORIGIN_MANIFEST_024.json')
    save(DEST/'CHANGES_030.json',{'layers':layers,'reviewed_files':expected,
        'saved_fixture_inputs':fixtures,'test_dependency_closure':sorted(dependencies),
        'shared_main_copied':False,'amount_TASK_unwired':True,
        'models_source_job_target_generic_runner_controller_changed':False})
    files=[]
    for p in sorted(DEST.rglob('*')):
        if p.is_file():
            relative=str(p.relative_to(DEST))
            files.append({'pin_relative_path':relative,'size':p.stat().st_size,'sha256':sha(p),
                          'prior_sha256':old.get(relative,{}).get('sha256')})
    manifest={'version':'configured_literature_source_job_pin_030','origin_root':str(ORIGIN),
              'origin_manifest_sha256':ORIGIN_HASH,'files':files}
    save(DEST/'SOURCE_MANIFEST.json',manifest)
    verify(DEST,manifest);verify(ORIGIN,origin_manifest)
    assert sha(DEST/'runner/run_literature_source_job_019.py')==sha(ORIGIN/'runner/run_literature_source_job_019.py')
    report={'written_utc':datetime.now(timezone.utc).isoformat(),'status':'captured_verification_pending',
        'pin':str(DEST),'pin_manifest_sha256':sha(DEST/'SOURCE_MANIFEST.json'),
        'files':len(files),'reviewed_code_test_files':len(expected),'fixture_files':len(fixtures),
        'layers':layers,'old_pin_unchanged':True,'actual_model_execution_proved':False}
    save(BASE/'UNIFIED_LITERATURE_PIN_CAPTURE_030.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='layers'}))

if __name__=='__main__':main()
