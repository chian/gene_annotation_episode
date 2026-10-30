"""Additive metadata-only correction; never opens SQLite connections or imports app code."""
from pathlib import Path
import datetime, hashlib, json, os, stat
ROOT=Path(__file__).parent
FIRST=ROOT/'invocation-001'
OUT=ROOT/'metadata-correction-002'

def digest(data):return hashlib.sha256(data).hexdigest()
def read_json(path):return json.loads(path.read_bytes())
def descriptor(path):
    before=path.lstat()
    assert stat.S_ISREG(before.st_mode) and not path.is_symlink()
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    try:
        with os.fdopen(fd,'rb') as stream:data=stream.read()
    except BaseException:
        # fdopen closes its fd even on read failure.
        raise
    after=path.lstat()
    assert (before.st_size,before.st_mtime_ns,before.st_ino,before.st_dev,before.st_mode)==(after.st_size,after.st_mtime_ns,after.st_ino,after.st_dev,after.st_mode)
    return dict(path=str(path),sha256=digest(data),bytes=len(data),mode=stat.S_IMODE(after.st_mode),mtime_ns=after.st_mtime_ns,inode=after.st_ino,device=after.st_dev)

def main():
    OUT.mkdir()
    result_path=FIRST/'RESULTS001.json';code_path=ROOT/'verify_closed_fixture001.py';readset_path=FIRST/'READSET_FINAL001.json'
    original=read_json(result_path);rows=read_json(readset_path)['files']
    assert digest(result_path.read_bytes())=='f3c1c379aac7fb76c744d0022799201036ce19acfef96d16ea332211e7295fe9'
    assert digest(code_path.read_bytes())=='7b541d50153c57fcfe6129f20fcc2fe793a05e2f0c864ca6203122a73cc4005d'
    assert original['all_opened_inputs_unchanged_after_explicit_close'] is False
    assert original['status']=='verified_closed_scripted_worker_fixture'
    assert original['check_count']==279 and all(x['passed'] for x in original['checks'])
    actual=[descriptor(Path(x['path'])) for x in rows]
    differences=[dict(path=x['path'],expected=x,actual=y) for x,y in zip(rows,actual) if x!=y]
    closed_paths={str(Path('/tmp/direct-hmmer-root008-evidence-20261022-001/invocation-004/preserved-fixtures/test_real_detached_direct_sear0')/n) for n in ['case/workspace/state.sqlite3','run/episode-execution/executions.sqlite']}
    assert {x['path'] for x in rows if '.sqlite' in x['path']}==closed_paths
    result={'version':'direct_hmmer_root004_metadata_correction_v1','status':'verified_closed_scripted_worker_fixture_with_metadata_correction' if not differences else 'failed_metadata_control','corrected_all_opened_inputs_unchanged':not differences,'witness_count':len(rows),'original_result':descriptor(result_path),'original_operator':descriptor(code_path),'original_readset':descriptor(readset_path),'original_reported_guard':False,'original_result_unchanged':True,'guard_error':'Original witness returns bytes; final loop compared bytes to the stored descriptor dict. Its internal descriptor equality assertions ran, but its final boolean was incorrectly False. Original verified status failed to require that boolean.','correction':'This additive check compares fresh descriptor dicts to retained descriptor dicts. Corrected status requires no differences. It does not replace original279 scientific/engineering checks or original result bytes.','differences':differences,'actual_witnesses':actual,'performed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'calls':{'sqlite_connections':0,'application_imports':0,'tests':0,'model_service_native':0},'limits':['Original result and operator remain unchanged, including the false guard.','File bytes and metadata were rehashed only. No SQLite connection, app, projector, test, worker, HTTP or native execution was performed.','The279 original checks establish only the original scripted closed fixture scope; corrected status additionally requires this metadata guard.']}
    p=OUT/'RESULTS_METADATA002.json';p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':result['status'],'witness_count':len(rows),'differences':len(differences),'sha256':digest(p.read_bytes()),'result':str(p)},sort_keys=True))
    return 0 if not differences else 1
if __name__=='__main__':raise SystemExit(main())
