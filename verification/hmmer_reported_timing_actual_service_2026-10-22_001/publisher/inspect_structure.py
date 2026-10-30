from pathlib import Path
from contextlib import contextmanager
import hashlib,json,sqlite3,os
E=Path('/tmp/hmmer-reported-timing-service-verification-20261022-001')
W=Path('/tmp/hmmer-reported-timing-fixed-target-20261022-001')
O=Path('/tmp/hmmer-reported-timing-publication-20261022-001')
def j(p): return json.loads(p.read_bytes())
def inventory(root):
    return {str(p.relative_to(root)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'mode':oct(p.stat().st_mode&0o777)} for p in sorted(root.rglob('*')) if p.is_file()}
assert not (O/'PRIVATE_BEFORE.json').exists()
(O/'PRIVATE_BEFORE.json').write_text(json.dumps({str(p):inventory(p) for p in (E,W)},sort_keys=True,indent=2)+'\n')
b=j(E/'selected-binding.json')
summary={'private_parents':{str(p):oct(p.stat().st_mode&0o777) for p in (E,W)},'binding_keys':sorted(b),'binding':{k:b[k] for k in ('registry','local_limits','scope','translation_arguments','product_ref','protein_sha256','protein_length','submitted_fasta_sha256','order','order_scope','request','timing_ledger')},'seed_keys':sorted(b['seed']),'seed_fixed_identity':b['seed']['fixed_identity'],'phases':[],'tables':{}}
for p in sorted((E/'invocations').iterdir()):
    v=j(p/'intent.json');a=v['arguments']
    result=j(p/'result.json') if (p/'result.json').exists() else None
    selected=j(p/'selected-outcome.json') if (p/'selected-outcome.json').exists() else None
    item={'directory':p.name,'arguments':a,'sources_pin':v['sources']['runtime_implementation_sha256'],'script_sha256':v['script_sha256'],'source_guard':j(p/'sources-after.json')['unchanged'],'failure_file':(p/'failure.json').exists(),'result_keys':sorted(result['result']) if result else None,'selected_keys':sorted(selected) if selected else None}
    if selected:
        item['safe_outcome']={k:selected[k] for k in ('receipt_ref','operation','operation_key','observed_at','outcome','state','remote_id','failure','reported_result_count','native_attempt_count','api_execution_measurements','timing_source_refs') if k in selected}
    summary['phases'].append(item)
for p in (W/'state.sqlite3',E/'api-timing.sqlite3',E/'reported-statistics.sqlite3'):
    db=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True,timeout=0)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        names=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        summary['tables'][str(p)]={n:{'columns':[row[1] for row in db.execute('PRAGMA table_info('+n+')')],'count':db.execute('SELECT count(*) FROM '+n).fetchone()[0]} for n in names}
        db.rollback()
    finally: db.close()
(O/'STRUCTURE.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(summary,sort_keys=True,indent=2))
