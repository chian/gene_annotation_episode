# Selected FBA InputVersion validation (024)

This packet records implementation of
[024](../tool_graders_flux_balance_core_2026-10-29_679/IMPLEMENTATION_CONTRACT_024.md).
It does not redefine the original supplied goal or claim full episode/result
publication.

Owned code is `gene_annotation_episode/execution_input_versions.py` and
`tests/test_flux_balance_input_versions_708.py`. ExecutionEpisodes wiring and
the 021A received-control reader belong to the coordinating owner.

The shared validator accepts optional `flux_balance_assignments=()`. Actual
selected FBA jobs use their existing authenticated 014 binding. An exactly
matching launch_local receiving context first reads its original 021A control;
its frozen witness records are consumed without fetching current source rows.
Never-initialized receiving controls use current admission. Missing, partial or
forged existing controls fail through the existing reader.

Only witnesses from the selected model/prior rows qualify. The original selected
InputVersion array and receiving scope must match; current record digests and
agreement across bindings are checked. Eligible versions use the sole existing
`flux_balance_operands._check_version`. Source primary content hashes retain
their sequence_ref/artifact_ref meaning, independently of selected File hashes.
Existing shared protected-reference checks run before the eligible shortcut.
Unrelated selected inputs retain the generic scope, revision and byte checks,
including Store's existing `artifact_digest_mismatch` failure.

No authority cache, grant, scientific decoder, solver, acquisition, installation,
native operation, observation, credit or controller change was added. Molecular
and software bytes in the new tests are explicitly synthetic. Real Store,
Journal, receipt, commission, immutable-control and selected-input primitives
are reused from 694 and 704.

Verification uses the existing 529 launcher with explicit retained 3.12
interpreter and 134c dependencies, 20 GiB memory, 4 GiB monitored scratch, zero
swap and no wall-time cap. The original handles, closure receipts, audits and
test records remain in the 529 packet. `EXECUTION_EVIDENCE.json` records final
outcomes and artifact pins; `SOURCE_PINS.json` compares owned files with the
frozen snapshots. `TEST_FIXTURE_CORRECTIONS.diff` preserves the only test edits
after the first run. Validator code did not change after that first snapshot.

| Original attempt | Actual outcome |
| --- | --- |
| check168_fba_versions708 | 31 passed, two fixture assertions failed; 200.32 s. |
| check168b_fba_versions708 | Collection error from an unstaged optional ATAC replay fixture; no cases executed. |
| check168c_fba_versions708 | Four passed: the two corrected cases and existing fluorescence/ATAC version regressions; 59.46 s. |

There are 33 unique passing new cases and two unique passing shared regressions.
All three original handles are terminal and quiescent; module/mapping audits
contain no external or unbound entries; native/retained-fixture and all frozen
closure pins are unchanged. The current validator matches all three snapshots;
both current owned files match the final snapshot. The NMF regression selected
in the collection-failed attempt did not execute and is not counted.

The inspected paths include the complete shared version helper, 014 operand
binding/freezing/checking helper, 021A receiving-control consumer, real 694/704
fixture paths and affected ExecutionEpisodes admission/initialization/parent
revalidation consumers. EPISODE_STRUCTURE and TIME_AWARE_ESTIMATION were read.
Full configured-model episodes, native FBA execution and result publication are
separate verification obligations.
