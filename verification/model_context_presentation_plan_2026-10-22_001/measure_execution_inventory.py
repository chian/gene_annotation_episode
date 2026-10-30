"""Root-requested narrow lifecycle counts only; no bodies, application imports or construction."""
from pathlib import Path
from urllib.parse import quote
import json
import sqlite3
ROOT=Path('/home/chia/repos/gene_annotation_episode/cases/gene_001/runs/configured_development_002')
RUN='run_a9cae64280ed405594a79255d659f917'
OUT=Path('/tmp/scientific-context-proposal002-xmmw8Rca')
def connection(path):
    db=sqlite3.connect('file:'+quote(str(path))+'?mode=ro',uri=True,isolation_level=None,timeout=1)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db
with connection(ROOT/'workspace/state.sqlite3') as db:
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    selected=sorted(t for t in tables if t.startswith(('provider_','public_search_','api_','runtime_','tool_operations','native_','homology_')))
    counts={t:db.execute('SELECT count(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in selected}
    lifecycle={}
    for table,col in [('provider_jobs','state'),('runtime_commissions','state'),('runtime_pending_work','state'),('runtime_work_items','state')]:
        if table in tables:
            columns={r['name'] for r in db.execute('PRAGMA table_info("'+table+'")')}
            if col in columns:
                lifecycle[table]=[dict(r) for r in db.execute('SELECT "'+col+'",count(*) AS count FROM "'+table+'" GROUP BY "'+col+'"')]
    schemas={t:[dict(r) for r in db.execute('PRAGMA table_info("'+t+'")')] for t in selected if t.startswith(('provider_','public_search_','api_','runtime_commissions'))}
    records=[dict(r) for r in db.execute('SELECT record_type,count(*) AS count FROM records GROUP BY record_type ORDER BY record_type')]
    run_counts={t:db.execute('SELECT count(*) FROM "'+t+'" WHERE run_id=?',(RUN,)).fetchone()[0] for t in ('runtime_actions','runtime_observations','runtime_episodes')}
registry=ROOT/'native-jobs/jobs.sqlite'
external={'path':str(registry),'exists':registry.is_file(),'authorization':'Root latest narrow request for actual HomologyJobs registry lifecycle counts, no old job state construction.'}
if registry.is_file():
    with connection(registry) as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        external['table_counts']={t:db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in sorted(tables)}
        external['order_lifecycle_counts']=([dict(r) for r in db.execute('SELECT staged,submission_requested,count(*) AS count FROM orders GROUP BY staged,submission_requested')] if 'orders' in tables else [])
result={'status':'readonly_typed_counts_only','source_run_id':RUN,'workspace_execution_table_counts':counts,'workspace_lifecycle_counts':lifecycle,'workspace_execution_schemas':schemas,'scientific_record_kind_counts':records,'original_run_counts':run_counts,'native_registry':external,'private_events_or_scientific_bodies_read':False}
(OUT/'EXECUTION_INVENTORY002.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ('workspace_execution_table_counts','workspace_lifecycle_counts','original_run_counts','native_registry')},indent=2))
