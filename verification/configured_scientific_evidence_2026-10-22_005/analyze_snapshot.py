"""Document actual saved contributions, integration, partial work and contexts."""
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text())
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
actions={x["decision_index"]:x for x in read("raw/workspace_actions_additive_111_123.json")}
records={x["id"]:json.loads(x["data"]) for x in read("raw/workspace_records_new.json")}
mapping=read("verification/own_action_observation_mapping.json")
models={x["call_index"]:x for x in read("raw/workspace_model_calls_selected.json")}
assert [x["decision_index"] for x in mapping if x["actual_marginal_credit"]!=0]==[113,121]
assert sum(x["actual_marginal_credit"] for x in mapping)==2.0
assert mapping[0]["cumulative_scientific_progress"]==8.0 and mapping[-1]["cumulative_scientific_progress"]==10.0
snapshot=read("snapshot.json")
prior=OUT.parent/"configured_scientific_evidence_2026-10-22_004"
old_snapshot=json.loads((prior/"snapshot.json").read_text())
assert old_snapshot["fixed_prefix"]["actions"]+len(actions)==snapshot["root_prefix_through_123"]["actions"]==124
assert old_snapshot["fixed_prefix"]["observations"]+len(mapping)==snapshot["root_prefix_through_123"]["observations"]==123
contexts=[]
for i,row in sorted(models.items()):
    q=json.loads(row["request"])["context"]
    item={"decision_index":i,"current_credit":q["current_credit"],"investigation_progress":q["investigation_progress"],"annotation_score":q["annotation_score"],"annotation_evidence_vector":q["annotation_evidence_vector"],"monitoring_information_credit":q["monitoring_information_credit"],"assessments_present":[x["id"] for x in q["working_state"]["assessments"]],"annotations_present":[{"id":x["id"],"revision":x["revision"],"resolution":x["resolution"]} for x in q["working_state"]["annotations"]],"actual_selected_action":json.loads(row["response"]),"last_local_outcome":q["last_local_outcome"],"controller_stop":q["controller"]["decision"]["stop"]}
    assert item["annotation_score"]==0.0 and all(x==0.0 for x in item["annotation_evidence_vector"].values())
    assert item["monitoring_information_credit"]==3.0
    contexts.append(item)
byindex={x["decision_index"]:x for x in contexts}
for action,next_index,assessment,annotation in [(113,114,"assessment_5f1dbdad727d22a0eb3c63d7","annotation_1eff6d83bf001368a03679d2"),(121,122,"assessment_88796f5a02b8a1782059fcdb","annotation_fe55ce2238da0350fd418365")]:
    assert assessment in byindex[next_index]["assessments_present"]
    account=records[annotation]
    assert assessment in [ref for s in account["coherent_sets"] for x in s["interpretations"] for ref in x["assessment_refs"]]
    assert annotation in [x["id"] for x in byindex[next_index+1]["annotations_present"]]
assert byindex[113]["last_local_outcome"]==json.loads(actions[112]["result"])
partial=json.loads(actions[112]["result"])
assert partial["status"]=="partial"
assert [x["code"] for x in partial["errors"]]==["anchor_transcription_mismatch","unresolved_alias"]
write("verification/actual_post_contribution_context_fields.json",contexts)
trace=[]
for i in [112,113,114,121,122]:
    result=json.loads(actions[i]["result"])
    trace.append({"decision_index":i,"actual_result":result,"records":[records[ref] for ref in result["record_refs"]],"observation":next(x for x in mapping if x["decision_index"]==i)})
write("verification/scientific_contribution_trace.json",trace)
write("verification/additive_consistency.json",{"prior_manifest_sha256":snapshot["prior_manifest_sha256"],"previous_actions":111,"previous_observations":110,"additive_actions":len(actions),"additive_observations":len(mapping),"combined_actions_through_123":124,"combined_observations_through_123":123,"new_nonzero_credit_actions":[113,121],"recorded_scientific_increment":2.0,"recorded_scientific_progress_through_123":10.0,"explicit_commission_intents_query_through_123":snapshot["commission_intents_through_123"],"explicit_commission_intents_query_total_at_capture":snapshot["commission_intents_total_at_capture"],"existing_publications_changed":False})
print(json.dumps({"new_nonzero_credit_actions":[113,121],"recorded_progress":10.0,"annotation_revisions":[8,9],"actual_partial_repair_pair":[112,113],"focused_contexts":len(contexts)},indent=2))
