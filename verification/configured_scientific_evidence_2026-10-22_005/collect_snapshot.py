"""One short read-only transaction for the fixed additive 111–123 prefix."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
RUN=ROOT/"cases/gene_001/runs/configured_development_002"
PRIOR=OUT.parent/"configured_scientific_evidence_2026-10-22_004"
RUN_ID="run_a9cae64280ed405594a79255d659f917"
EP="episode_b14eea3b01b27015465bafe0cc229f7552fcd9baa33f601b82cc5a23d6c17ea8"
FIRST,LAST=111,123
EXPECTED="0b15ba46395055bc83f7b863b7b79e40b70017207cec6fa2943cb5e5f90a0dee"

def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,obj):
    p=OUT/name
    p.parent.mkdir(parents=True,exist_ok=True)
    assert not p.exists(),p
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
def strings(x):
    if isinstance(x,str):yield x
    elif isinstance(x,dict):
        for v in x.values():yield from strings(v)
    elif isinstance(x,list):
        for v in x:yield from strings(v)

prior_manifest_bytes=(PRIOR/"MANIFEST.json").read_bytes()
assert sha(prior_manifest_bytes)==EXPECTED
prior_manifest={x["path"]:x for x in json.loads(prior_manifest_bytes)["files"]}
for name in ["raw/workspace_records_selected.json","raw/workspace_inputs_selected.json","raw/workspace_artifact_metadata_selected.json"]:
    assert sha((PRIOR/name).read_bytes())==prior_manifest[name]["sha256"]
old_records={x["id"]:x for x in json.loads((PRIOR/"raw/workspace_records_selected.json").read_text())}
old_inputs={x["id"]:x for x in json.loads((PRIOR/"raw/workspace_inputs_selected.json").read_text())}
old_artifacts={x["id"]:x for x in json.loads((PRIOR/"raw/workspace_artifact_metadata_selected.json").read_text())}

started=now()
c=sqlite3.connect((RUN/"workspace/state.sqlite3").as_uri()+"?mode=ro",uri=True)
c.row_factory=sqlite3.Row
c.execute("PRAGMA query_only=ON")
c.execute("BEGIN")
def rows(sql,args=()):return [dict(x) for x in c.execute(sql,args)]
try:
    tables={x["name"] for x in rows("SELECT name FROM sqlite_master WHERE type='table'")}
    established=now()
    actions=rows("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index BETWEEN ? AND ? ORDER BY decision_index",(RUN_ID,EP,FIRST,LAST))
    observations=rows("SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index",(RUN_ID,EP))
    observation_prefix_count=sum(json.loads(x["observation"])["decision_index"]<=LAST for x in observations)
    observations=[x for x in observations if FIRST<=json.loads(x["observation"])["decision_index"]<=LAST]
    slots=rows("SELECT * FROM runtime_completion_slots WHERE run_id=? AND episode_id=? AND original_decision_index BETWEEN ? AND ? ORDER BY sequence",(RUN_ID,EP,FIRST,LAST))
    models=rows("SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index BETWEEN ? AND ? ORDER BY call_index",(RUN_ID,EP,FIRST,LAST))
    receipts=rows("SELECT * FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND source_index BETWEEN ? AND ? ORDER BY receipt_index",(RUN_ID,EP,FIRST,LAST))
    commissions=rows("SELECT run_id,parent_episode_id,original_decision_index,handle,commission_sha256,selected_at FROM runtime_commission_intents WHERE run_id=? AND original_decision_index<=? ORDER BY original_decision_index",(RUN_ID,LAST))
    commission_total=rows("SELECT COUNT(*) AS n FROM runtime_commission_intents WHERE run_id=?",(RUN_ID,))[0]["n"]
    headers=rows("SELECT run_id,episode_id,path,state FROM runtime_episodes WHERE run_id=? ORDER BY path",(RUN_ID,))
    run_header=rows("SELECT run_id,state,started_at,updated_at FROM runtime_runs WHERE run_id=?",(RUN_ID,))
    record_rows={x["id"]:x for x in rows("SELECT * FROM records ORDER BY id")}
    input_rows={x["id"]:x for x in rows("SELECT * FROM inputs ORDER BY id")}
    artifact_rows={x["id"]:x for x in rows("SELECT * FROM artifacts ORDER BY id")}
    live_counts={"actions":rows("SELECT COUNT(*) AS n,MAX(decision_index) AS max_index FROM runtime_actions WHERE run_id=? AND episode_id=?",(RUN_ID,EP))[0],"observations":rows("SELECT COUNT(*) AS n,MAX(unit_index) AS max_index FROM runtime_observations WHERE run_id=? AND episode_id=?",(RUN_ID,EP))[0]}
    through_counts={"actions":rows("SELECT COUNT(*) AS n FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index<=?",(RUN_ID,EP,LAST))[0]["n"],"observations":observation_prefix_count}
    finished=now()
finally:
    c.rollback();c.close()

assert [x["decision_index"] for x in actions]==list(range(FIRST,LAST+1))
assert all(x["result"] is not None for x in actions)
obs={json.loads(x["observation"])["decision_index"]:json.loads(x["observation"]) for x in observations}
selected_indices={FIRST,LAST}
reason_indices=[]
for row in actions:
    i=row["decision_index"]
    if json.loads(row["action"])["kind"]=="reason":
        reason_indices.append(i);selected_indices.add(i)
        if i<LAST:selected_indices.add(i+1)
selected_models=[x for x in models if x["call_index"] in selected_indices]
assert len(selected_models)==len(selected_indices)
new_records={};new_inputs={};new_artifacts={};prior_refs={};seen=set()
pending={x["record_ref"] for x in receipts}
for row in actions:
    pending.update(strings(json.loads(row["action"])));pending.update(strings(json.loads(row["result"])))
while pending:
    ref=pending.pop()
    if ref in seen:continue
    seen.add(ref)
    if ref in record_rows:
        row=record_rows[ref]
        if ref in old_records:
            assert row==old_records[ref]
            prior_refs[ref]={"kind":"record","prior_file":"raw/workspace_records_selected.json","immutable_row":row}
        else:
            new_records[ref]=row
        pending.update(strings(json.loads(row["data"])))
    elif ref in input_rows:
        row=input_rows[ref]
        if ref in old_inputs:
            assert row==old_inputs[ref]
            prior_refs[ref]={"kind":"input","prior_file":"raw/workspace_inputs_selected.json","immutable_row":row}
        else:new_inputs[ref]=row
        pending.update(strings(json.loads(row["data"])))
    elif ref in artifact_rows:
        row=artifact_rows[ref]
        if ref in old_artifacts:
            assert row==old_artifacts[ref]
            digest=row["sha256"];rel=f"artifacts/{digest[:2]}/{digest}"
            assert sha((PRIOR/rel).read_bytes())==digest
            assert (PRIOR/rel).stat().st_size==row["size"]
            prior_refs[ref]={"kind":"artifact","prior_file":rel,"metadata":row}
        else:new_artifacts[ref]=row

write("raw/workspace_actions_additive_111_123.json",actions)
write("raw/workspace_observations_additive_111_123.json",observations)
write("raw/workspace_completion_slots_additive_111_123.json",slots)
write("raw/workspace_model_calls_selected.json",selected_models)
write("raw/workspace_model_calls_additive_index.json",[{k:v for k,v in x.items() if k not in ("request","response")} for x in models])
write("raw/workspace_receipts_111_123.json",receipts)
write("raw/workspace_records_new.json",sorted(new_records.values(),key=lambda x:x["id"]))
write("raw/workspace_inputs_new.json",sorted(new_inputs.values(),key=lambda x:x["id"]))
write("raw/workspace_artifact_metadata_new.json",sorted(new_artifacts.values(),key=lambda x:x["id"]))
write("raw/workspace_commission_intents_through_123.json",commissions)
write("prior_references.json",{"prior_directory":str(PRIOR.relative_to(ROOT)),"prior_manifest_sha256":EXPECTED,"references":prior_refs})

provenance=[]
def copy(src,rel,kind,expected=None):
    data=src.read_bytes();digest=sha(data)
    if expected is not None:assert expected==digest
    dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();dest.write_bytes(data)
    provenance.append({"source_path":str(src.relative_to(ROOT)),"publication_path":rel,"kind":kind,"sha256":digest,"bytes":len(data)})
    return data
for ref,meta in sorted(new_artifacts.items()):
    digest=meta["sha256"]
    data=copy(RUN/"workspace/artifacts"/digest[:2]/digest,f"artifacts/{digest[:2]}/{digest}","immutable_source_or_diagnostic_artifact",digest)
    assert len(data)==meta["size"]

provider="providers/17a83f8aac0749e3b80e02ad63539b23/session-0001"
copy(RUN/provider/"session-001.json",provider+"/session-001.json","actual_provider_session")
matches=[]
for row in selected_models:
    i=row["call_index"];stem=f"{provider}/call-{i+1:05d}"
    request=json.loads(copy(RUN/stem/"request.json",stem+"/request.json","actual_provider_request"))
    response=json.loads(copy(RUN/stem/"response.json",stem+"/response.json","actual_provider_response"))
    q=json.loads(row["request"])
    entry={"decision_index":i,"provider_call_number":i+1,"request_context_matches_original_workspace_request":request["context"]==q["context"],"response_matches_original_workspace_response":response==json.loads(row["response"]),"schemas_identical":request["output_schema"]==q["schema"],"authoritative_schema_sha256":sha(json.dumps(q["schema"],sort_keys=True,separators=(",", ":")).encode()),"transport_schema_sha256":sha(json.dumps(request["output_schema"],sort_keys=True,separators=(",", ":")).encode())}
    assert entry["request_context_matches_original_workspace_request"] and entry["response_matches_original_workspace_response"]
    matches.append(entry)
write("verification/provider_context_matches.json",matches)

anchors=[]
for ref,row in sorted(new_records.items()):
    x=json.loads(row["data"]);anchor=x.get("anchor")
    if not anchor:continue
    artifact=anchor["artifact_ref"]
    meta=artifact_rows[artifact];digest=meta["sha256"];rel=f"artifacts/{digest[:2]}/{digest}"
    source=OUT if artifact in new_artifacts else PRIOR
    data=(source/rel).read_bytes()
    entry={"record_ref":ref,"source_ref":anchor["source_ref"],"artifact_ref":artifact,"start":anchor["start"],"end":anchor["end"],"quote_matches_exact_utf8_byte_slice":data[anchor["start"]:anchor["end"]].decode("utf-8")==anchor["quote"],"artifact_publication":"005" if source==OUT else "004"}
    assert entry["quote_matches_exact_utf8_byte_slice"]
    anchors.append(entry)
write("verification/source_anchor_matches.json",anchors)
mapping=[{"decision_index":i,"unit_index":x["unit_index"],"cumulative_scientific_progress":obs[i]["credit"]["credit"],"actual_marginal_credit":obs[i]["step"]["marginal_credit"]} for x in observations for i in [json.loads(x["observation"])["decision_index"]]]
assert {x["decision_index"] for x in mapping}=={x["original_decision_index"] for x in slots}
write("verification/own_action_observation_mapping.json",mapping)
snapshot={"version":"configured_scientific_additive_evidence_checkpoint_v1","run_directory":str(RUN.relative_to(ROOT)),"run_id":RUN_ID,"episode_id":EP,"capture_started_at":started,"sqlite_snapshot_established_no_later_than":established,"sqlite_selected_reads_finished_at":finished,"sqlite_access":"URI mode=ro; PRAGMA query_only=ON; one explicit BEGIN read transaction, then rollback; no application constructors","additive_prefix":{"first_decision_index":FIRST,"last_decision_index":LAST,"actions":len(actions),"observations":len(observations),"completion_slots":len(slots),"model_calls":len(models),"selected_full_model_calls":len(selected_models)},"root_prefix_through_123":through_counts,"live_counts_at_capture":live_counts,"commission_intents_through_123":len(commissions),"commission_intents_total_at_capture":commission_total,"episode_headers_at_capture":headers,"run_header_at_capture":run_header,"return_admission_table_exists":"runtime_return_admissions" in tables,"prior_manifest_sha256":EXPECTED,"implementation_pin":"a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a","json_column_preservation":"Original SQLite JSON cell text is retained as strings in raw exports.","later_live_actions_excluded":True,"not_a_complete_database_backup":True,"not_an_atomic_cross_database_or_filesystem_snapshot":True}
write("snapshot.json",snapshot)
write("file_provenance.json",{"copy_finished_at":now(),"copies_are_not_new_runtime_results":True,"original_files":provenance,"private_provider_events_read":False,"execution_tokens_worker_argv_or_credentials_read":False,"old_source_bytes_referenced_without_recopying":True})
print(json.dumps({"snapshot":snapshot,"reason_indices":reason_indices,"new_records":len(new_records),"new_artifacts":len(new_artifacts),"new_anchors":len(anchors),"selected_indices":sorted(selected_indices),"mapping":mapping},indent=2))
