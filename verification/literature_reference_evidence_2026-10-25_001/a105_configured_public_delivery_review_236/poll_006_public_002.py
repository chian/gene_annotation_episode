"""Read-only exact durable lifecycle, counters and process identity; no content."""
from pathlib import Path
import sqlite3,json,time
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
RUN=BASE/'a105_joined_control_binding_review_141/configured_primary_006'
def ro(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;return db
with ro(RUN/'state/state.sqlite3') as db:
    counters={table:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in
        ('runtime_episodes','runtime_actions','runtime_observations','runtime_report_attempts','runtime_model_calls')}
    states=[dict(row) for row in db.execute('SELECT run_id,state FROM runtime_runs')]
with ro(RUN/'run/episode-execution/executions.sqlite') as db:
    commissions=[dict(row) for row in db.execute('SELECT handle,lifecycle_state,execution_identity,return_id FROM commissions')]
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
for row in commissions:
    identity=json.loads(row.pop('execution_identity')) if row['execution_identity'] else None
    row['identity']=identity;live=False
    if identity and identity.get('boot_id')==boot:
        try:
            text=(Path('/proc')/str(identity['pid'])/'stat').read_text();parts=text[text.rindex(')')+2:].split()
            live=parts[0]!='Z' and parts[19]==str(identity['start_ticks'])
        except FileNotFoundError:pass
    row['live_identity_verified_now']=live
result={'observed_unix':time.time(),'counters':counters,'run_states':states,'commissions':commissions,
    'scope':'Public counters/lifecycle and exact current OS process identity only. No scientific forms or private provider/model contents read. No restart or state modification.'}
with (HERE/'CONFIGURED006_PUBLIC_STATUS_002.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
