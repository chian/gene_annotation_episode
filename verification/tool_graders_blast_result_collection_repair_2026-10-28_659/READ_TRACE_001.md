# Collection repair implementation trace

This record describes the implementation review for frozen IMPLEMENTATION_PORT_001.md. It does not alter the user-supplied objective, the port, or any prior requirement.

The original attachment and AGENTS.md were read in full before work. The objective and entire OPERATING PRINCIPLES block were reread verbatim throughout work after tool use and substantial inspection. GOAL.md and goal/scope amendment files were not read. The frozen port is reread before reporting this assignment complete.

## Design and complete paths inspected

- docs/EPISODE_STRUCTURE.md, docs/TIME_AWARE_ESTIMATION.md, docs/PRACTICAL_EXECUTION.md, docs/PRACTICAL_EXECUTION_CONTRACT_2026-10-22_001.md, docs/TASK_AND_STEERING.md.
- Full native_blast_utility_results.py: selected operation authentication; immutable intent, observation, receipt and index; original-capture reuse; preparation/publication; current facts; historical result access; reference grants; credit and practical completion.
- Full native_blast_utility_acquisition.py, native_blast_utility_result_publication.py and native_blast_utility_result_worker.py: original file identity custody, saved capture validation, new action-local workers, result-null failure receipts and selected projection validation.
- Full blast_utility_result_views.py and native_blast_utility_returns.py: requested field projection, status/missing/failure distinctions, authenticated episode ancestry, typed report grants and reconstruction.
- ExecutionEpisodes affected complete methods: catalog, execute, _target, _selected_result_action, facts, initial_references, received_form_references, validate_report, received_report_facts, validate_received_report, project_credit, completion_for_action, _proof_for_action, verify_completion, practical_estimator; utility branch of _native_results_complete. Constructor bindings and decision_context target description were inspected where consumed.
- Full execution_service_setup.py and practical_yield.py; complete ExecutionContextController and DecisionSource.restore; CompletionLedger.restore_source. Shared reconstruction retains original observations and expectation snapshots. Source inspection does not establish live original113b reconstruction.
- execution_progress.py describe_target affected local-utility path, including its actual handoff receipt JSON requirement, was inspected to correct the controlled fixture.
- Existing tests/publication helpers inspected: test_native_blast_utility_workflow_634.py, test_blast_utility_episode_wiring_632.py, test_native_blast_utility_publication_631.py, preparation ambiguity test657, and relevant producer628/preparation649/publication653 fixtures. native_blast_utility_tool_info.py binding validation and variant handling were inspected for the v2 preparation fixture.
- test_native_hmmer_preparation_nested_workflow.py was inspected for the real strict provider transport and shared Workflow fixture conventions; test_practical_yield.py supplies an existing typed completion context helper.
- Bounded529 run_checks.py and bounded_entry.py were inspected for controlled imports, source snapshots, dependency pins, cgroup/scratch policy, terminal collection and audit evidence.

## Ownership and behavior trace

| Responsibility | Selected behavior and authoritative state | Changed? |
| --- | --- | --- |
| Episode choice | Existing execution.results.collect with empty arguments must already be selected in runtime_actions. | No |
| Parsed-result reuse | Authenticated prior preparation is reusable exactly when result_artifact_ref is nonnull; valid partial and native-failed parsed results qualify. | Shared predicate added in host |
| Repair | An explicit new collect without a parsed result invokes existing preparation once in its new action directory using the original retained capture and observation. | Host predicate corrected |
| Same-action replay | Existing immutable receipt is validated and returned without preparation. | No |
| Capture custody | Existing acquisition links, retained identities and immutable preparation/publication validators remain authoritative. | No |
| Current requested facts | Within the authenticated episode and assignment, a later parsed body suppresses an earlier unparsed body for the exact same captured bundle in requested FACT_SOURCES. | Host projection filter added |
| History and grants | _own_bodies retains every body; source grants, historical receipts and old returned forms remain recorded. | No |
| Credit | Existing unique-bundle acquisition credit remains unchanged by reparsing. | No |
| Completion | Existing proof validates actual selected typed result; ordinary practical estimator sets future expectation to exact zero while preserving completed action observations. | No |
| Continued execution | Existing configured shared controller owns the next decision; completed assignments reject new work. | No |

No production module other than native_blast_utility_results.py was changed by this owner. No templates, schemas, numerical policy, launch behavior, native lifecycle, runtime, scientific grader, acquisition mechanism or original113b state was edited. Test fixtures use explicitly synthetic producer bytes and deterministic choices; these are engineering assertions, not scientific measurements or configured-model behavior.
