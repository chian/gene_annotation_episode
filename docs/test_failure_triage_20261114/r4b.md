# r4b: causes for the 72 unrecorded groups in a102-a110 and the shared `root/tests`

Work list: `runs/claude_summary_final_20261114_05/unrecorded_r4b.tsv` (72 groups, 109 failing cases, 45 distinct messages).
Every message has a row in `r4b_causes.tsv` (45 rows, 109 cases, joins back on `message` with no remainder).
`R/` = `gene_annotation_episode/episodic_workflow/root/`. Slot `r4b`, runs `runs/claude_r4b_001` .. `043`, one test file
per launcher run in the BRIEF3 form. Marks: **[run NNN]** observed in that launcher run; **[read]** from code, tracebacks
and git history; **[copied]** cause taken from the named earlier report, not re-diagnosed.

Diagnostic runs used throw-away pytest plugins that only print (source-failure tracebacks, provider contexts, the failing
`_require` call, the returning line of one function). They are kept outside the repository in the session scratch
directory (`.../scratchpad/r4b/`); no repository file was involved and none of them is a fix.

Totals by class (cases): product_defect 38, stale_test 37, test_wiring 17, environment 9, unclear 8.
Outcome: 12 cases now pass, 4 cases (2 tests) retired, 93 still fail (6 of them at a new, recorded layer).
No product file was edited. Nothing was committed.

## 1. Causes

| # | Cause | Class | Cases (groups) | Evidence | Action | Scientific? |
|---|---|---|---|---|---|---|
| 1 | a105 scripted loop tests do not declare the original task credit (r2d C2) | stale_test | 14: `(0.0 == 0 and 0 == 1)` 6 of 11 (binding_model 2, missing_input_semantics_156 1, transport 2, transport_quantity 1), `(3 == 2)` 4, `(5 == 4)` 1, `2 in (4, 5)` 1, `[[]] == [[0, 0], [0]]` 1, plus a106 `{'own'} == {'own', 'parent'}` 1 (r2e C6) | Child commission rejected with `literature_original_task_credit_required` (`R/a105/scientific_process/published_evidence_assessment/goal.py:61`; a106 `goal.py:55-59`); the provider script is then out of step [run 013, 018-024]. The a105 `_scientific_credit_invocation` defect (r2d C1) is fixed in the tree (`R/a105/published_evidence_assessment/credit.py:256`), so this is now the first layer | left failing | Yes: choosing a `literature_task` and credit unit per test states what A105/A106 credit a scripted action earns (owner question, r2d C2) |
| 2 | `test_a105_partition_time_joined_149` expects method task text in the root's first prompt | stale_test | 3 (`(0.0 == 0 and 0 == 1)`) | `assert_prompt` (test line 71) requires `COMPLETION_TIME_TASK` and `PRODUCT_PARTITION_TASK`; sections are selected only from assignment, requested form, own outputs and lookups (`R/a105/library/literature_task_selection.py:163-191`, same function at `078b77668` and `b5d7c94e2`); the reference-parent root's first context has none [run 017]. Test unchanged since the import commit. Cause 1 is behind it | left failing | No (prompt text); cause 1 behind it is |
| 3 | a102: seven literature homes all answer the same received-report source | product_defect | 2 (`(0.0 == 0 and 0 == 1)`, `test_literature_structure_integration::test_structure_selected...`) | Root's first decision raises `received_report_field_conflict:received_report_sources` (`R/a102/episode_bindings.py:284`) [run 001]. Each home returns the structure fact source for a non-literature role (`R/a102/published_evidence_assessment/received_evidence.py:7-8`); a102's own `create_binding_tree` gives all seven the same configuration (`episode.py:91-100`); the a102 registry has no `context_hook_applies` filter, which a105/a106/a108 have (`R/a105/episode_bindings.py:183,197`, `R/a105/published_evidence_assessment/episode.py:67`). The product factory only ever calls `create_binding_tree(None)`, so only `structure_population=True` reaches this | left failing | Plumbing, but which home delivers structure cells to a parent; owner question |
| 4 | a102 cannot rebuild its literature bindings from saved descriptors (triage_d C6) | product_defect | 3 (`unavailable_binding`) | [copied] `R/a102/episode_composition.py:85,144-145` vs `binding_record.py:11`, `a102_investigation.py:124,150` | left failing, owner question in triage_d | No |
| 5 | Shared-root `ExecutionEpisodes` is a shell (r2e C16, r2c C07) | product_defect | 8: `allowed_children` 1, `yield_controller` 2, `type object ... 'execute'` 4, `object ... 'execute'` 1 | `allowed_children`, `yield_controller`, `prepare_assignment`, `initialize`, `execute`, `fact_sources`, `assignment_schema` are defined in no `R/execution_*.py` [read]; at `078b77668` they were methods of the class | left failing, owner decision in r2e C16 | `credit_view`/`validate_report` are among the missing methods |
| 6 | Tests of the removed monoliths, hidden one layer in front of cause 5 | stale_test | 4: `terminal_execution_episodes` 2, `explicit_execution_transport_configuration_required` 1, `practical_execution_operations` 1 | `TerminalExecutionEpisodes` exists nowhere (replaced by `R/terminal_binding_catalogue.py`); the pbs_ssh fixture lacks the `scheduler` key that `R/terminal_execution.py:446-452` requires (same line at `078b77668`); `R/tests/test_native_genomic_overlap_shared.py:297` patches a module with no shared-root copy and then calls `prepare_assignment`/`initialize` | left failing | No |
| 7 | Root product code uses role-only `for_role` where a role has one binding per parent (r2f C07 family) | product_defect | 1 (`assert 0 == 3`) + the 4 infernal cases after cause 13 | `R/composition_information.py:110` `for_role(name)` -> `episode_role_requires_parent:literature` [run 027]; second site `R/decision_information.py:32` `for_role('launch')` -> `episode_role_requires_parent:launch` [run 041] | left failing (product change) | No |
| 8 | Genome-alignment grader rejects every capped acquisition receipt | product_defect | 5: `metadata_record_unverified` 4, `('partial' == 'ok'` 1 | `R/library/bvbrc_genome_alignment_retained_records.py:274` accepts only `{url, byte_range}`; the receipt's call is `{url, byte_range, max_bytes}` [run 026] because the host requires a cap on fresh downloads (`R/bvbrc_appservice_host.py:205-206`) and `bvbrc_appservice_contracts.py:461` admits both shapes. Validator, host rule and test arguments are the same at `078b77668` [read] | left failing | Yes: which retained records the grader accepts. Owner question |
| 9 | `retained_policy(..., historical=...)` defined nowhere (triage_f 1-2) | product_defect | 9 (atac 7, chromatin 2) | [copied] `R/library/atac_result_native_receipts.py:232,287`, `chromatin_result_native_receipts.py:205,260` | left failing, owner decision in triage_f | Yes (receipt policy) |
| 10 | A106 finalize feedback does not forward `detail` (triage_d 1a) | product_defect | 5 (`KeyError: 'detail'`) | [copied] `R/a106/published_evidence_assessment/source_operations.py:114` | left failing, owner question | Yes |
| 11 | a107 saved partner evidence is re-interpreted before replay (r2e) | product_defect | 4 | [copied] `R/a107/published_evidence_assessment/source_operations.py:43,96` | left failing | Yes |
| 12 | A105 implementation-digest pin (triage_d C3, r2d P1) | product_defect | 1 (`'completed' == 'invalid'`) | [copied] `R/a105/library/literature_ion_discrimination_storage.py:187` | left failing, owner question | Yes |
| 13 | Role-only `for_role('results')` in a test fixture | test_wiring | 4 (`episode_role_requires_parent:results`) | `R/tests/test_native_infernal_results_integration.py:312`; the root registry has one results binding per parent | **fixed** (`for_child((('annotation','root'),), 'results')`, raising for the nested case). The 4 cases then stop at cause 7 [run 033, 041] | No |
| 14 | Top-level `BindingContext` used against root code | test_wiring | 8: `assert False is True` 6 (local file sources), `fluorescence_input_invalid_context` 2 | `R/received_native_file_inputs.py:15,33` and `R/library/fluorescence_operands.py:10,26` check the root class | local file sources **fixed** (import, line 27): 63/13 -> 69/7 [run 031]. Fluorescence left: the context is built in `tests/test_fluorescence_returns.py:18,116` (top-level `tests/`, outside this slot) | No |
| 15 | Un-rewritten flat module strings | test_wiring | 2: `mauve_v4_formats` 1, `literature_compiled_assay_storage` 1 | `R/tests/test_bvbrc_genome_alignment_host.py:446,492`; `R/a105/tests/test_literature_compiled_assay_binding_185.py:105`; all targets exist in `R/library` / `R/a105/library` | **fixed**; both tests pass [run 043, 028] | No |
| 16 | a104 proteome helper used names it did not import | test_wiring | 2 (`asyncio`) | `R/a104/tests/proteome_partner/proteome_host_fixture.py:200`; sibling `appservice_host_fixture.py:1,5,21` | **fixed**. Next layer [run 030]: `unknown required BV-BRC application identity`: `R/a104/bvbrc_application_definitions.py:30` lists Homology, GeneTree, CodonTree only, while the test and `R/a104/library/bvbrc_proteome_*` need GenomeComparison | Owner question: should a104 carry GenomeComparison |
| 17 | a103 fake workflow lacks `shared_information_repository` (triage_d C9) | test_wiring | 1 | [copied] test line 268, `R/a103/runtime.py:2705` | left failing | No |
| 18 | Census of `episode.py` homes counts two homes that own no binding | stale_test | 2 (a107, a110 `test_private_reconstruction`) | `R/a107/episode.py`, `R/a107/annotation_improvement/episode.py` (and a110) hold routing functions / the root task source, no `as_record`; every catalog entry needs an `owner_class` | **fixed** in the tests: the two homes are named and asserted present; 14/1 -> 15/0 each [run 034, 035] | No |
| 19 | Before-change "baseline" captures in a107 | stale_test | 4 (`received_report_sources` 3, `received_execution_original_factory_required` 1) | File docstring: "Run baseline selectors before application, connected selectors afterward"; binding callback replaced by the catalog (`R/a107/episode_bindings.py:287-296, 624-627`); `test_connected_*` cover the current behaviour | **retired** 2 tests; 12/4 -> 12/0 [run 039] | No |
| 20 | Container type of a private helper | stale_test | 2 (`test_root_binding_owners`) | `_report_source_bindings` returns a tuple (`R/execution_family_composition.py:295`, `R/resource_binding_catalogue.py:268,281`); members and order match | **fixed**: compared as lists; 26/2 -> 28/0 [run 036] | No |
| 21 | Hand-built unauthenticated context | stale_test | 1 (`assert False is True`, protein structure) | `resolve` returns False after `native_blast_masking_return_context_conflict` (`R/episode_return_records.py:84-87`, caught at `R/execution_request_custody.py:617-618`) [run 037, 042]; code and fixture the same at `078b77668` [read] | left failing | No |
| 22 | a110 reference-parent prompt compared with the shared task text | stale_test | 1 | `R/a110/library/literature_reference_parent_presentation.py:7,24` uses `A110_SOURCE_LEAD`; the test imports `REFERENCE_PARENT_TASK` from `R/library` | left failing: no second piece of evidence that the a110 text is the intended one | Prompt text; owner to confirm |
| 23 | Stale expectations already recorded | stale_test | 6: a103 legacy report x2 (triage_d C9), `22 == 19` 2 (triage_d C5), `assert False` 1 (triage_d C4), `{'cpu': 3` 1 (triage_c G11) | [copied] | left failing | a103 report form: owner choice |
| 24 | Environment variables | environment | 9: `NMF488_SOFTWARE` 5, `A104_CONTEXT_SOURCE_EPOCH` 2, `GENE_OPERATIONAL_LEGACY_PREPARATION` 2 | [copied] r2a 19, triage_e 6, triage_c G12; nothing tracked sets them | left failing | No |
| 25 | Wrong-parent redelivery accepted in a107/a110 Launch (triage_a B2) | unclear | 8 (`DID NOT RAISE WorkflowError`) | [copied] `launch_connected.py:621` | left failing, owner decision 2 in triage_a | Delivery identity |

## 2. Edits (test files and one test helper only)

```
 a104/tests/proteome_partner/proteome_host_fixture.py      |  3 ++-
 a105/tests/test_literature_compiled_assay_binding_185.py  |  2 +-
 a107/tests/test_private_reconstruction.py                 |  6 +++++-
 a107/tests/test_received_api_role_discovery.py            | 21 ---------------------
 a110/tests/test_private_reconstruction.py                 |  6 +++++-
 tests/test_bvbrc_genome_alignment_host.py                 |  4 ++--
 tests/test_execution_local_file_sources.py                |  2 +-
 tests/test_native_infernal_results_integration.py         |  6 +++++-
 tests/test_root_binding_owners.py                         |  2 +-
 9 files changed, 22 insertions(+), 30 deletions(-)   (paths under R/)
```

`R/a104/tests/registered_saved_bindings.py` was already modified before this round and is not mine.
At the end of this round `git status` also shows six modified product files directly under `R/`
(`expression_nmf_result_receipts.py`, `genomic_overlap_result_receipts.py`, `protein_structure_result_receipts.py`,
`protein_structure_return_operands.py`, `rna_comparison_result_custody.py`, `rna_result_custody.py`). They are not mine
(another slot is working in the same tree); my reruns of the root test files happened while they may have been changing.
An import change tried in `R/tests/test_protein_structure_source_boundaries.py` did not change the outcome and was reverted.
Two rows appended to `retired.tsv` (now 103 lines).

Judgement calls the owner may want to reverse: cause 18 (the two homes are excluded by name; if they are meant to get
binding owners, the original assertion was right) and cause 19 (the two baseline tests are deleted, not kept as history).

## 3. Before / after (passed/failed/errors; before = final run 05)

| File (under `R/`) | Before | After | Run |
|---|---|---|---|
| `a105/tests/test_literature_common_assessment_binding_223.py` | 1/25/0 | 2/24/0 | 028 |
| `a105/tests/test_literature_compiled_assay_binding_185.py` (edited helper) | 0/4/0 | 0/4/0 | 029 |
| `a104/tests/test_api_owner_shared_support.py` | 0/2/0 | 0/2/0 (new layer) | 030 |
| `a104/tests/proteome_partner/test_proteome_saved_host.py` (uses the helper) | not in any results file | 0/66/0 | 038 |
| `tests/test_execution_local_file_sources.py` | 63/13/0 | 69/7/0 | 031 |
| `tests/test_native_infernal_results_integration.py` | 2/10/30 | 2/10/30 (4 cases at a new layer) | 033 |
| `a107/tests/test_private_reconstruction.py` | 14/1/0 | 15/0/0 | 034 |
| `a110/tests/test_private_reconstruction.py` | 14/1/0 | 15/0/0 | 035 |
| `tests/test_root_binding_owners.py` | 26/2/0 | 28/0/0 | 036 |
| `a107/tests/test_received_api_role_discovery.py` | 12/4/0 | 12/0/0 (2 tests retired) | 039 |
| `tests/test_protein_structure_source_boundaries.py` (edit reverted) | 22/1/0 | 22/1/0 | 040 |
| `tests/test_bvbrc_genome_alignment_host.py` | 3/9/0 | 4/8/0 | 043 |

Sum over the 11 files with a before: passed 157 -> 169, failed 72 -> 56 (4 of the 16 by retirement), errors 30 -> 30. No file lost a passing test.
Durations: the nine-file batch was expected at about 115 s and took 77 s; the genome-alignment file was expected at
390 s and took 198 s; the a107 role-discovery file was expected at 94 s and took 53 s.

## 4. Found on the way, not in the work list

- `R/a104/tests/proteome_partner/test_proteome_saved_host.py` (66 tests) is in no results file of the final run; all 66
  fail on the GenomeComparison identity (cause 16, next layer).
- Eight more a105 test files still build guard targets as `'gene_annotation_episode.' + module`
  (`test_literature_binding_interaction_model_storage.py:136`, `test_literature_compiled_assay_185.py:290`,
  `test_literature_calibration_recovery_binding_173.py:377`, `test_literature_ion_discrimination_binding_199.py:88`,
  `test_literature_kinetic_model_storage.py:124`, `test_literature_measurement_validation_binding_209.py:404`,
  `test_literature_product_coupling_binding_218.py:660`, `test_literature_rate_observations_166.py:392`). Not edited:
  their current failures have other recorded causes and none is in this work list.
- a103, a104, a107 and a110 registries also lack the `context_hook_applies` filter of cause 3 (r2e C5 met the same
  conflict in a107). Not exercised here.

## 5. Owner questions

1. Cause 1/2: which `literature_task` and credit unit should each scripted A105/A106 loop test declare (14 + 3 cases)?
2. Cause 8: should the genome-alignment retained-record validator accept the capped download call shape? As it stands
   no fresh acquisition receipt can be verified, so the adapter result is always `partial`.
3. Cause 3: should the a102 literature homes get the family hook filter that a105/a106/a108 have?
4. Cause 16: is GenomeComparison meant to be an a104 application (the proteome partner library is there, the
   application definitions are not)?
5. Cause 22: is `A110_SOURCE_LEAD` the intended reference-parent task text for a110?
6. Causes 18 and 19: confirm or reverse the two judgement calls in section 2.
7. Already open and unchanged: r2e C16 (root `ExecutionEpisodes` shell, 8 + 4 cases here), r2f C07 (5), triage_f
   `retained_policy` (9), triage_d C6 (3), triage_d 1a (5), triage_a decision 2 (8), A105 pins (1), a107 partner replay (4).
