"""Read-only, finite-prefix evidence export; never loads application classes.

Run once into this new publication directory. Publication finishing and the
report are separate; this collector deliberately does not regenerate a manifest.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "cases/gene_001/runs/configured_development_002"
PRIOR = ROOT / "verification/configured_scientific_evidence_2026-10-21_003"
RUN_ID = "run_a9cae64280ed405594a79255d659f917"
EPISODE = "episode_b14eea3b01b27015465bafe0cc229f7552fcd9baa33f601b82cc5a23d6c17ea8"
LAST = 110
SELECTED = [37,38,39,40,41,42,58,59,60,61,65,66,67,68,79,80,81,82,83,84,100,101,102,103,104,105,106,107,108,109,110]

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def write(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    assert not p.exists(), p
    p.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

def sha(data):
    return hashlib.sha256(data).hexdigest()

def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for x in value.values():
            yield from strings(x)
    elif isinstance(value, list):
        for x in value:
            yield from strings(x)

started = now()
c = sqlite3.connect((RUN / "workspace/state.sqlite3").as_uri() + "?mode=ro", uri=True)
c.row_factory = sqlite3.Row
c.execute("PRAGMA query_only=ON")
c.execute("BEGIN")

def rows(sql, parameters=()):
    return [dict(x) for x in c.execute(sql, parameters)]

try:
    tables = {x["name"] for x in rows("SELECT name FROM sqlite_master WHERE type='table'")}
    established = now()
    actions = rows("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index<=? ORDER BY decision_index", (RUN_ID, EPISODE, LAST))
    slots = rows("SELECT * FROM runtime_completion_slots WHERE run_id=? AND episode_id=? AND original_decision_index<=? ORDER BY sequence", (RUN_ID, EPISODE, LAST))
    observations = rows("SELECT * FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index", (RUN_ID, EPISODE))
    observations = [x for x in observations if json.loads(x["observation"])["decision_index"] <= LAST]
    models = rows("SELECT * FROM runtime_model_calls WHERE run_id=? AND episode_id=? AND call_index<=? ORDER BY call_index", (RUN_ID, EPISODE, LAST))
    receipts = rows("SELECT * FROM runtime_record_receipts WHERE run_id=? AND episode_id=? AND (source_index<=? OR source_index IS NULL) ORDER BY receipt_index", (RUN_ID, EPISODE, LAST))
    commissions = rows("SELECT run_id,parent_episode_id,original_decision_index,handle,commission_sha256,selected_at FROM runtime_commission_intents WHERE run_id=? AND original_decision_index<=? ORDER BY original_decision_index", (RUN_ID, LAST))
    run_header = rows("SELECT run_id,state,started_at,updated_at FROM runtime_runs WHERE run_id=?", (RUN_ID,))
    episode_headers = rows("SELECT run_id,episode_id,path,state FROM runtime_episodes WHERE run_id=? ORDER BY path", (RUN_ID,))
    record_rows = {x["id"]: x for x in rows("SELECT * FROM records ORDER BY id")}
    inputs = {x["id"]: x for x in rows("SELECT * FROM inputs ORDER BY id")}
    artifacts = {x["id"]: x for x in rows("SELECT * FROM artifacts ORDER BY id")}
    live_counts = {
        "actions": rows("SELECT COUNT(*) AS n,MAX(decision_index) AS max_index FROM runtime_actions WHERE run_id=? AND episode_id=?", (RUN_ID, EPISODE))[0],
        "observations": rows("SELECT COUNT(*) AS n,MAX(unit_index) AS max_index FROM runtime_observations WHERE run_id=? AND episode_id=?", (RUN_ID, EPISODE))[0],
    }
    finished = now()
finally:
    c.rollback()
    c.close()

assert [x["decision_index"] for x in actions] == list(range(LAST + 1))
assert all(x["result"] is not None for x in actions)
selected_models = [x for x in models if x["call_index"] in SELECTED]
assert len(selected_models) == len(SELECTED)
pending = {x["record_ref"] for x in receipts} | set(inputs)
for x in actions:
    pending.update(strings(json.loads(x["action"])))
    pending.update(strings(json.loads(x["result"])))
for x in selected_models:
    pending.update(strings(json.loads(x["request"])["context"]))
selected_records, selected_inputs, selected_artifacts = {}, {}, {}
seen = set()
while pending:
    ref = pending.pop()
    if ref in seen:
        continue
    seen.add(ref)
    if ref in record_rows:
        row = selected_records[ref] = record_rows[ref]
        pending.update(strings(json.loads(row["data"])))
    elif ref in inputs:
        row = selected_inputs[ref] = inputs[ref]
        pending.update(strings(json.loads(row["data"])))
    elif ref in artifacts:
        selected_artifacts[ref] = artifacts[ref]

write("raw/workspace_actions_prefix_000_110.json", actions)
write("raw/workspace_completion_slots_prefix_000_110.json", slots)
write("raw/workspace_observations_prefix_000_110.json", observations)
write("raw/workspace_model_calls_selected.json", selected_models)
write("raw/workspace_model_calls_prefix_index.json", [{k: v for k,v in x.items() if k not in ("request", "response")} for x in models])
write("raw/workspace_receipts_through_110.json", receipts)
write("raw/workspace_records_selected.json", sorted(selected_records.values(), key=lambda x: x["id"]))
write("raw/workspace_inputs_selected.json", sorted(selected_inputs.values(), key=lambda x: x["id"]))
write("raw/workspace_artifact_metadata_selected.json", sorted(selected_artifacts.values(), key=lambda x: x["id"]))
write("raw/workspace_commission_index.json", commissions)

provenance = []
def copy(source, relative, kind, expected_sha=None):
    data = source.read_bytes()
    digest = sha(data)
    if expected_sha is not None:
        assert digest == expected_sha, source
    target = OUT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), target
    target.write_bytes(data)
    provenance.append({"source_path": str(source.relative_to(ROOT)), "publication_path": relative, "kind": kind, "bytes": len(data), "sha256": digest})
    return data

for ref, meta in sorted(selected_artifacts.items()):
    digest = meta["sha256"]
    data = copy(RUN / "workspace/artifacts" / digest[:2] / digest, f"artifacts/{digest[:2]}/{digest}", "immutable_source_or_diagnostic_artifact", digest)
    assert len(data) == meta["size"]

prior_manifest = json.loads((PRIOR / "MANIFEST.json").read_text())
for entry in prior_manifest["files"]:
    rel = entry["path"]
    if rel.startswith(("implementation/", "binding/")):
        copy(PRIOR / rel, rel, "unchanged_prior_preserved_pinned_source_or_binding", entry["sha256"])

provider = "providers/17a83f8aac0749e3b80e02ad63539b23/session-0001"
copy(RUN / provider / "session-001.json", provider + "/session-001.json", "actual_provider_session")
provider_matches = []
for row in selected_models:
    i = row["call_index"]
    stem = f"{provider}/call-{i+1:05d}"
    request = json.loads(copy(RUN / stem / "request.json", stem + "/request.json", "actual_provider_request"))
    response = json.loads(copy(RUN / stem / "response.json", stem + "/response.json", "actual_provider_response"))
    authoritative = json.loads(row["request"])
    original_response = json.loads(row["response"])
    match = {
        "decision_index": i,
        "provider_call_number": i + 1,
        "request_path": stem + "/request.json",
        "request_context_matches_original_workspace_request": request["context"] == authoritative["context"],
        "response_matches_original_workspace_response": response == original_response,
        "workspace_authoritative_schema_sha256": sha(json.dumps(authoritative["schema"], sort_keys=True, separators=(",", ":")).encode()),
        "provider_transport_schema_sha256": sha(json.dumps(request["output_schema"], sort_keys=True, separators=(",", ":")).encode()),
        "schemas_identical": request["output_schema"] == authoritative["schema"],
        "schema_boundary": "Authoritative workspace schema and transformed provider transport schema are distinct originals; equal contexts and responses do not require identical schemas.",
    }
    assert match["request_context_matches_original_workspace_request"]
    assert match["response_matches_original_workspace_response"]
    provider_matches.append(match)
write("verification/provider_context_matches.json", provider_matches)

mapping = []
for row in observations:
    x = json.loads(row["observation"])
    mapping.append({"decision_index": x["decision_index"], "unit_index": row["unit_index"], "cumulative_scientific_progress": x["credit"]["credit"], "controller_estimation_action_index": x["credit"]["estimation_action_index"], "marginal_credit": x["step"]["marginal_credit"]})
assert len(mapping) == len({x["decision_index"] for x in mapping}) == len(slots)
assert {x["decision_index"] for x in mapping} == {x["original_decision_index"] for x in slots}
write("verification/own_action_observation_mapping.json", mapping)

anchor_matches = []
for ref, row in sorted(selected_records.items()):
    record = json.loads(row["data"])
    anchor = record.get("anchor")
    if not anchor:
        continue
    digest = selected_artifacts[anchor["artifact_ref"]]["sha256"]
    data = (OUT / "artifacts" / digest[:2] / digest).read_bytes()
    actual = data[anchor["start"]:anchor["end"]].decode("utf-8")
    match = {"record_ref": ref, "source_ref": anchor["source_ref"], "artifact_ref": anchor["artifact_ref"], "start": anchor["start"], "end": anchor["end"], "quote_matches_exact_utf8_byte_slice": actual == anchor["quote"]}
    assert match["quote_matches_exact_utf8_byte_slice"], match
    anchor_matches.append(match)
write("verification/source_anchor_matches.json", anchor_matches)

snapshot = {
    "version": "configured_scientific_evidence_checkpoint_v1",
    "run_directory": str(RUN.relative_to(ROOT)), "run_id": RUN_ID, "episode_id": EPISODE,
    "implementation_pin": "a192366fa67def7bbeb7b7ef87330e402f4244c154d2dd635444f5e98265383a",
    "capture_started_at": started, "sqlite_snapshot_established_no_later_than": established,
    "sqlite_selected_reads_finished_at": finished,
    "sqlite_access": "URI mode=ro; PRAGMA query_only=ON; one explicit BEGIN read transaction, then rollback; no application constructors",
    "fixed_prefix": {"first_decision_index": 0, "last_decision_index": LAST, "actions": len(actions), "observations": len(observations), "completion_slots": len(slots), "model_calls": len(models), "selected_full_model_calls": len(selected_models), "commission_intents": len(commissions), "failed_actions_without_observation": sorted({x["decision_index"] for x in actions} - {x["decision_index"] for x in mapping})},
    "live_root_counts_at_capture": live_counts,
    "run_header_at_capture": run_header, "episode_headers_at_capture": episode_headers,
    "return_admission_table": {"exists": "runtime_return_admissions" in tables, "interpretation": "absence is not a zero-row installed ledger"},
    "json_column_preservation": "Original SQLite JSON cell text is retained as strings in raw exports.",
    "later_live_actions_excluded": True, "not_a_complete_database_backup": True,
    "not_an_atomic_cross_database_or_filesystem_snapshot": True,
    "prior_checkpoint_manifest_sha256": sha((PRIOR / "MANIFEST.json").read_bytes()),
}
write("snapshot.json", snapshot)
write("file_provenance.json", {"copy_finished_at": now(), "copies_are_not_new_runtime_results": True, "original_files": provenance, "provider_private_events_read": False, "execution_tokens_or_worker_argv_read": False})
print(json.dumps({"snapshot": snapshot, "records": len(selected_records), "artifacts": len(selected_artifacts), "anchors": len(anchor_matches), "copied_files": len(provenance)}, indent=2))
