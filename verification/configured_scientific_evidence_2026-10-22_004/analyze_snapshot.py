"""Derive documentary indexes from preserved bytes; no scorer or database use."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
PRIOR = OUT.parent / "configured_scientific_evidence_2026-10-21_003"

def read(name):
    return json.loads((OUT / name).read_text())

def write(name, value):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

actions = {x["decision_index"]:x for x in read("raw/workspace_actions_prefix_000_110.json")}
observations = {json.loads(x["observation"])["decision_index"]:(x["unit_index"],json.loads(x["observation"])) for x in read("raw/workspace_observations_prefix_000_110.json")}
records = {x["id"]:json.loads(x["data"]) for x in read("raw/workspace_records_selected.json")}
models = {x["call_index"]:x for x in read("raw/workspace_model_calls_selected.json")}

mapping = [{"decision_index":i,"unit_index":unit,"cumulative_scientific_progress":x["credit"]["credit"],"controller_estimation_action_index":x["credit"]["estimation_action_index"],"marginal_credit":x["step"]["marginal_credit"]} for i,(unit,x) in observations.items()]
write("verification/own_action_observation_mapping.json", mapping)
assert sum(x["marginal_credit"] for x in mapping) == mapping[-1]["cumulative_scientific_progress"] == 8.0
assert [x["decision_index"] for x in mapping if x["decision_index"] > 42 and x["marginal_credit"] != 0] == [59,66,82,101,104]

prior_checks = []
for previous,current in [
    ("raw/workspace_actions_prefix_000_042.json","raw/workspace_actions_prefix_000_110.json"),
    ("raw/workspace_completion_slots_prefix_000_042.json","raw/workspace_completion_slots_prefix_000_110.json"),
    ("raw/workspace_observations_prefix_000_042.json","raw/workspace_observations_prefix_000_110.json"),
]:
    old = json.loads((PRIOR/previous).read_text())
    new = read(current)
    same = old == new[:len(old)]
    assert same
    prior_checks.append({"prior_file":str((PRIOR/previous).relative_to(OUT.parent.parent)),"new_file":current,"rows_compared":len(old),"exact_raw_rows_equal":same})
old_records = json.loads((PRIOR/"raw/workspace_records_selected.json").read_text())
new_records = {x["id"]:x for x in read("raw/workspace_records_selected.json")}
assert all(x == new_records[x["id"]] for x in old_records)
write("verification/prior_prefix_unchanged.json", {"prior_manifest_sha256":hashlib.sha256((PRIOR/"MANIFEST.json").read_bytes()).hexdigest(),"prefix_checks":prior_checks,"all_prior_selected_records_retained_unchanged":True,"prior_selected_records_compared":len(old_records)})

scientific = []
for i in [59,60,66,67,80,81,82,83,101,102,104,105]:
    row=actions[i]
    result=json.loads(row["result"])
    entry={"decision_index":i,"action_kind":json.loads(row["action"])["kind"],"record_refs":result["record_refs"],"record_types":{ref:records[ref]["record_type"] for ref in result["record_refs"]},"outcome_status":result.get("status"),"errors":result.get("errors"),"conflicts":result.get("conflicts"),"notices":result.get("notices"),"unit_index":observations[i][0],"cumulative_scientific_progress":observations[i][1]["credit"]["credit"],"actual_marginal_credit":observations[i][1]["step"]["marginal_credit"]}
    entry["assessments"]=[records[ref] for ref in result["record_refs"] if records[ref]["record_type"]=="assessment"]
    entry["annotations"]=[records[ref] for ref in result["record_refs"] if records[ref]["record_type"]=="annotation"]
    scientific.append(entry)
write("verification/scientific_contribution_trace.json", scientific)

contexts=[]
for i in [60,61,67,68,81,82,83,84,102,103,105,106,107,108,109,110]:
    row=models[i]
    q=json.loads(row["request"])["context"]
    context={"decision_index":i,"actual_selected_action":json.loads(row["response"]),"annotation_score":q["annotation_score"],"annotation_evidence_vector":q["annotation_evidence_vector"],"current_credit":q["current_credit"],"monitoring_information_credit":q["monitoring_information_credit"],"investigation_progress":q["investigation_progress"],"annotations_present":[{"id":x["id"],"revision":x["revision"],"resolution":x["resolution"]} for x in q["working_state"]["annotations"]],"assessments_present":[x["id"] for x in q["working_state"]["assessments"]],"controller_current_credit":q["controller"]["current_credit"],"controller_stop":q["controller"]["decision"]["stop"]}
    assert context["annotation_score"]==0.0
    assert all(x==0.0 for x in context["annotation_evidence_vector"].values())
    assert context["monitoring_information_credit"]==3.0
    contexts.append(context)
for committed,next_index,ref in [(59,60,"assessment_6fcba1b962a12c83a49f9ad1"),(66,67,"assessment_75fad9f2acab7ad2410da24a"),(81,82,"assessment_9be1853857bb56d1cb286e18"),(82,83,"assessment_9cb2b27c7fce9d01fab0eefc"),(101,102,"assessment_bf9cecf5910596864965f9ec"),(104,105,"assessment_73995a50be2311ea6b45f2bf")]:
    assert ref in next(x for x in contexts if x["decision_index"]==next_index)["assessments_present"]
for committed,next_index,ref in [(60,61,"annotation_4b275f8a91e7d2ce016c3881"),(67,68,"annotation_b30f918e63d1f52892023cb8"),(81,82,"annotation_5cc4ff35b0fffce68875dfa2"),(83,84,"annotation_45032053bec849a63d6a4c71"),(102,103,"annotation_d734e4ec0e8684069b1b9139"),(105,106,"annotation_5c6c121b92023b9f2f0deace")]:
    assert ref in [x["id"] for x in next(x for x in contexts if x["decision_index"]==next_index)["annotations_present"]]
write("verification/actual_post_contribution_context_fields.json", contexts)
print(json.dumps({"scientific_trace_actions":len(scientific),"focused_decision_contexts":len(contexts),"new_nonzero_credit_actions":[59,66,82,101,104],"raw_observation_marginal_credit_total":8.0,"prior_prefix_and_records_unchanged":True},indent=2))
