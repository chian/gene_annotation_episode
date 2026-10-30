# Twelve saved regression failures: confirmed causes and proposed repairs

Each numbered entry corresponds to one actual check061 failure, including parameter variants. The exact saved rows were read only inside the bounded check062 collector. Original and staged database hashes remained unchanged. See `FAILURE_CLASSIFICATION_004.json` for exact node IDs, database identities, selected actions and request hashes.

`RUNTIME_COMPARISON_003.json` compares complete methods with the check060 snapshot. Root tool guards and the retired constructor precede the receipt-context repair. In cases 1–5 and 7–8, receipt-based projectors already selected the same received-record path before the repair. Cases 9–12 have no receipts ledger. Case 6 fails before runtime. This is a source-and-saved-record causal comparison, not a claim that these old tests were rerun against check060.

## 1. tests/test_episode_receipts.py::test_runtime_credits_only_requested_child_information_and_replay_keeps_history[False]

The child completed two reasoning actions and the requested finding was admitted. Root credit rose from 3 to 6. The next root decision selected episode.credit, excluded by the saved root action schema; the following call contains action_contract/schema_validation/anyOf feedback. Its script exhausted with three completed observations, before the expected fourth.

Saved completed actions: 3; observations: 3; report attempts: 1.

Proposed repair: Replace only the parent episode.credit selection with a valid nonempty reasoning commit of an already received hypothesis (same subject_refs/predicate/value/context_refs, no assessment). Preserve root deltas [3,0], child deltas [3,3], four total observations, exact returned finding, unreturned finding survival and frozen replay. Do not use an all-empty commit.

## 2. tests/test_episode_receipts.py::test_runtime_credits_only_requested_child_information_and_replay_keeps_history[True]

The standard-binding variant also completed both child reasoning actions, returned exactly the requested finding, and reached root credit 6 from initial 3. Root episode.credit was then rejected by the saved schema. Three observations survive, not the expected four.

Saved completed actions: 3; observations: 3; report attempts: 1.

Proposed repair: Apply the same lawful parent reasoning action to the standard-binding variant, retaining its distinct default binding, units, requested-return and replay assertions.

## 3. tests/test_episode_receipts.py::test_native_workbook_pages_return_one_finding_through_child_form_and_replay

Two saved source.xlsx.rows operations and two child reasoning actions completed. The child returned two assessment representations of one finding; root credit is 1. The root episode.credit action was rejected. Five observations survive, including child deltas [0,1,0,0] and root delta [1]; the expected sixth was never completed.

Saved completed actions: 5; observations: 5; report attempts: 1.

Proposed repair: Use a valid nonempty root reasoning action over its admitted hypothesis for the final zero finding-gain action. Replace the impossible root episode.credit action-result query with a direct verification-only call to the unchanged ScientificFindingProgress.read_details using that root's actual ledger-known assessments. Preserve two native operations, one retained finding, two representation refs, six action observations and unchanged closed replay. Classification uses saved bytes only; any future execution repair must reuse the retained native results rather than repeat original extraction merely to diagnose this rejection.

## 4. tests/test_episode_receipts.py::test_selected_state_read_delivers_existing_findings_but_detail_read_does_not[False]

The paged state.query selection occurs at the annotation root, whose saved tool list is empty and whose schema has no tool alternative. The following context contains action_contract/schema_validation/anyOf, credit 0 and no assessment. No action, tool operation or observation exists. The next callback incorrectly expects credit 5.

Saved completed actions: 0; observations: 0; report attempts: 0.

Proposed repair: Replace the obsolete positive root-discovery assertion with a boundary regression for paged state.query: the selected root tool is rejected, the next actual context has credit 0/no assessment, and zero completed actions/receipts/observations were added. Retain the stored finding unchanged. Do not expose state.query or bypass the root boundary; requested-return positive custody is already a separate test responsibility.

## 5. tests/test_episode_receipts.py::test_selected_state_read_delivers_existing_findings_but_detail_read_does_not[True]

The exact-reference state.query selection is rejected at the same root boundary. Its distinct saved arguments are refs=[saved finding]. No action, tool operation or observation exists; the next context still has credit 0 and no assessment, contrary to the callback expectation of 5.

Saved completed actions: 0; observations: 0; report attempts: 0.

Proposed repair: Keep the exact-reference parameter case and assert the same rejection/no-admission behavior, including that even knowledge of a stored identifier is not delivered knowledge. No production capability or scoring change.

## 6. tests/test_episode_receipts.py::test_different_parent_scalar_does_not_grant_unreceived_information_to_child

CreditPolicy raises its explicit retirement error before Workflow creation. The saved database has zero runtime episodes, calls, actions or observations. This failure did not exercise either visibility guard.

Saved completed actions: 0; observations: 0; report attempts: 0.

Proposed repair: Authorized direct regression repaired separately with an ordinary two-argument custom zero-credit parent, explicit receipts, empty initial-known refs, child ScientificFindingProgress and a legal zero finding-gain reasoning action. All custody, original-finding and one-observation assertions remain; see DIRECT_TEST_REVIEW_CORRECTION_005.md and the final check065 receipt.

## 7. tests/test_episode_receipts.py::test_failed_form_repair_and_interruption_preserve_work_and_observation_boundary[False]

The child reasoning action and detail action completed. Initial child return failed maxItems and produced root delta 0. Resume repaired the saved form successfully at root decision 1; root current credit became 3 while controller history stayed [0]. Root decision 2 then selected forbidden episode.credit; decision 3 contains schema rejection feedback and exhausts the script. There are three observations and one scientific reasoning commit; redelivery manufactured no observation.

Saved completed actions: 3; observations: 3; report attempts: 2.

Proposed repair: Keep child detail/recovery behavior separate. Replace the parent's forbidden final lookup with a valid nonempty reasoning commit over its already admitted hypothesis. Preserve original child commit identity/count 1, zero extra redelivery observations, root decision indices [0,2], deltas [0,3], four total observations and two report attempts. Count the new lawful parent reasoning commit separately (one child commit plus one parent commit), rather than mistaking it for a duplicate child analysis.

## 8. tests/test_episode_receipts.py::test_failed_form_repair_and_interruption_preserve_work_and_observation_boundary[True]

The alternative interruption boundary has the same retained original child work and successful form repair, with exactly two report attempts (failed then admitted). After resume, root decision 2 episode.credit is rejected; root current credit is 3 and its original observed history remains [0]. Three observations and one original reasoning commit survive.

Saved completed actions: 3; observations: 3; report attempts: 2.

Proposed repair: Apply the same final parent-action change while preserving interruption after redelivery, original immutable child work and exact original observation/order assertions. Do not combine or remove this boundary variant.

## 9. tests/test_runtime_decision_exchanges.py::test_multiple_context_exchanges_complete_one_actual_action_slot_and_observation

Both context lookups resolved with empty own-attempt pages in decision 0. The subsequent root sequence.inspect selection is normalized and saved, then rejected by the ordinary action schema. The durable decision effect is rejected; there are zero actions, completion observations or tool operations. A new pending decision asks the exhausted fixture for another response.

Saved completed actions: 0; observations: 0; report attempts: 0.

Proposed repair: Keep the real Store and completion-ledger path. Replace root sequence.inspect with a valid nonempty typed unresolved-hypothesis reasoning commit from the supplied target, and filter the second lookup by category reason. Retain three exchanges in one decision, one completed action/slot/observation/effect, exact normalized selection, and original saved-context assertions.

## 10. tests/test_runtime_decision_exchanges.py::test_own_input_detail_requests_stay_inside_pending_decision

Root fixture.measure(page=7) is rejected at decision 0. In decision 1, own-attempt lookup truthfully returns that attempt as unexecuted, and own-attempt-detail still returns the exact saved input value 7. The later valid reason(0) completes one action and one observation; the controller requests its second action, exhausting the fixture. Lookup correctness is not the failure.

Saved completed actions: 1; observations: 1; report attempts: 0.

Proposed repair: Use two legal fixture reasoning actions. First select reason(7), request its saved /commit/fixture_value detail (value 7), then select reason(0). Preserve two completed actions/observations, one pending decision containing both lookups, exact input value and no tool execution. Alternatively keep tool-specific inputs in a separately commissioned permitted child; do not enable root fixture.measure.

## 11. tests/test_runtime_decision_exchanges.py::test_lookup_visible_publications_extend_interpretation_basis_without_changing_raw_context

Root fixture.measure is rejected at decision 0 and publishes nothing. Two subsequent reason(0) actions complete, leaving only two observations where the fixture controller requires three. The lookup of decision 0 returns status unexecuted, no published references and saved_marginal_credit_unavailable. The target observation_1_0_14 could not have been produced.

Saved completed actions: 2; observations: 2; report attempts: 0.

Proposed repair: Keep the three-action root exchange/replay test by selecting reason(0) first and padding earlier assessment records instead of observation records so the first newly published assessment remains outside the bounded working-state page after the second action. Obtain its exact reference from decision 0's recorded result, look it up in decision 2, and retain the assertions that the original raw context lacks it while interpretation basis and replay include it. This preserves actual own publication lookup without root tool execution.

## 12. tests/test_runtime_decision_exchanges.py::test_injected_legacy_default_and_markerless_resume_do_not_migrate

This newly created run omits decision_protocol but explicitly records root_action_boundary=root_episode_commissioning_v1. Its initial fixture.measure was rejected, leaving zero actions and observations. The saved unfinished request has an empty tool list, so the assertion that episode.history is present fails. Absence of a protocol marker is not absence of the root-action marker.

Saved completed actions: 0; observations: 0; report attempts: 0.

Proposed repair: Create the markerless-direct-protocol run using reason(0), then interrupt its second decision. Assert decision_protocol is absent while the root-action marker and empty tool list remain. Preserve rejection of attempted protocol rebinding, exact interrupted-context replay, total two completed legal actions after resume, and absence of the exchange table. Do not assert availability of episode.history at the restricted root.

No other test has been repaired under this assignment. No new production defect is established by these twelve failures; wider runtime correctness and the remaining original goal stay unverified.
