# Actual existing fixed-case baseline parameter contract

Planning only. The stopped original caller files are unchanged; no factory was imported/executed.

The actual recorded factory source is cases/gene_001/runs/configured_development_002/policy-787117fa5d397694ea1377413f6932401b5cfec9acd92af934517ea044e71dfc.py, SHA256787117fa5d397694ea1377413f6932401b5cfec9acd92af934517ea044e71dfc. Its complete create_policy path accepts exactly top-level policy/services. It calls gene_annotation_episode.investigation_policy.create_policy(parameters['policy'],episode_roles=...), then dataclasses.replace retains that PolicyBindings.initial_known_record_refs while setting episode_record_receipts=True and the explicit assembled services/roles. Current saved caller has12 original initial-known refs; no list values or scientific bodies are printed here.

The exact existing new-caller JSON operand is:

    parameters.policy.scientific_progress.initial_known_record_refs

That scientific_progress object has exactly finding_unit,initial_known_record_refs,loss_preview_size; scientific_child must be 'received_findings'. All existing scientific/controller/operational/monitoring numeric operands remain the caller's original values. No new PolicyBindings field,source factory edit or new production policy module is needed. A fresh caller can use the same actual source snapshot under its unchanged source SHA and new JSON parameters that replace only this list (plus independently required new physical service/resource paths outside the numeric policy).

Concrete JSON shape for that existing section, using symbolic REF_A and REF_B solely to show the string-array contract, not a runnable new caller:

    {"policy": {"scientific_child": "received_findings", "scientific_progress": {"finding_unit": 1, "initial_known_record_refs": ["REF_A", "REF_B"], "loss_preview_size": 24}}}

The example uses the original caller's actual bound numeric values; the refs are symbolic and no new launch document is created. A real new caller must preserve every original numeric operand exactly. The schema in BASELINE_PARAMETER_CONTRACT.json defines the actual target operand without fabricating future content addresses. The complete new parameters document must preserve every original required policy/services field. A partial patch object alone is not accepted by create_policy.

The future checkpoint receipt can expose `initial_known_record_refs` as an actual finite,unique list of existing destination scientific record IDs plus newly registered checkpoint/lineage source IDs. Root materializes that exact array at the path above in a NEW parameters.json. It is impossible to provide the final new lineage source IDs before actual artifacts exist; do not invent them or mutate the original12-ref list. The caller selects all preserved committed scientific contributions intended for reuse as inherited initial knowledge, with forward dependency closure; custody preserves other partial/uncommitted work without calling it completed science.

Complete existing consumer path:

1. case_execution._load_policy snapshots the supplied NEW policy source, calls module.create_policy(_json_copy(parameters)), requires exact PolicyBindings, and records source SHA,complete parameters,definitions and initial_known_record_refs in NEW policy-binding.json.
2. investigation_policy.create_policy validates the closed scientific_progress fields, constructs existing ScientificFindingProgress/FindingProgressPolicy, and returns initial_known_record_refs unchanged into PolicyBindings. PolicyBindings validates that this is a list of strings. The assembled wrapper's replace retains it and enables explicit receipts.
3. prepared_case_bindings forwards policy.initial_known_record_refs and episode_record_receipts=True to run_workflow, alongside the actual same scientific projectors/controller definitions.
4. _run_bound_workflow requires receipt semantics,sorts/deduplicates that list and resolves each ref with store.get in the NEW destination. New runtime settings save scientific_knowledge.initial_known_record_refs. Resume must preserve that saved value and cannot substitute another list.
5. Workflow.build binds new root receipts; receive(kind='initial') delivers fixed subject+the explicit initial list and forward declared dependencies before initial_credit=source_credit_view(source)['credit'] is journaled. EpisodeReceipts remains keyed by NEW run_id. No copied old receipt is relabelled as a new receipt or new contribution.
6. projection_arguments supplies the new root's actual known assessment refs to ScientificFindingProgress; YieldController receives that credit as initial baseline. New action observations begin separately. Old runtime rows remain under the OLD run_id as lineage; neither _run_location(resume=False) nor the new run directory selects that old run. No old175 rows are appended to new local history.

No baseline integration was run in this analysis. Future C tests must use the real factory/PolicyBindings/receipts/progress path with isolated fixtures and demonstrate that an unchanged old finding read yields no new scientific gain, while a genuinely new retained finding can change credit once. This expresses the baseline through actual existing factory parameters; custody and actual new launch still require their separate implementation/adoption.
