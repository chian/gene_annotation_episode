# Shared-core source review and bounded-test handoff

Implementation is confined to the two production files and new test file assigned by PREPARATION_SHARED_CORE_012.md. The original goal was read from the user attachment; GOAL.md was not read. Contract012 and dependencies009–011, proposal573 and its correction were read. No goal, scope, progress, prompt, historical receipt or saved observation was edited.

## Changes

- Optional Domain.scaling reuses the existing closed Preparation and FileIdentity validators. Absence remains absent; no defaults or mutations.
- Finite derived measurements pass through the common event validation only for an explicitly mapped nonprimary domain with an applied present preparation record. Observed and supplied-predicted columns retain their existing rules.
- The existing _Operands.measurement admits derived values into the unchanged gate/count/fraction/intensity/control calculations.
- The existing native comparison preserves the native cell and linked cell. Matching, located input native_population_unknown issues make only native_minus_calculated unavailable. Existing operands and qualifications remain; matching issue values are stable-deduplicated, with operand pointers retained for their saved issue locations. Unlinked, unrelated-source, noninput and unlocated cases retain existing behavior.
- No public signatures or sheet identifiers changed. No preparation, transform, report parser, endpoint, acquisition or model call was added.

## Source paths inspected

The complete core contracts/calculations, sheet builder, result projector, CSV/snapshot readers, FCS reader, context projector and result worker were read. Changed functions were reread in full after editing. Relevant complete downstream functions read include original parsed-batch validation and unavailable-input assembly, native input/definition/support validation, and result/context validators. Existing numerical test fixtures and partial-primary/control-support consumers were inspected.

Root was notified of the matching consumers: context and job schemas/closed domain validation; original ParsedBatch derived-state rejection; and scaling parameter-file support custody. Root reports those changes in its separate owned files. They were not edited by this lane.

## Verification actually performed here

Only stdlib source/AST/JSON/hash checks ran. All three owned Python files parse; public function argument ASTs match the saved baseline; no trailing whitespace or conflict markers were found. Git diff/status checks could not run because this directory is not a Git repository; their failed exit codes are retained in SOURCE_CHECK_003.json. Earlier inspection failures are retained in SOURCE_ATTEMPTS_001.md.

No application imports, pytest, native jobs, library installation, download or scientific execution ran here. The new file contains16 test functions, including parametrized cases. Synthetic expected examples are original[110,20] versus prepared[100,0] at independently selected >=105 gates giving1 versus0; derived[100,50] giving sum150/mean75/median75; supported native33.33 versus the existing calculated100*(1/3) retaining exact subtraction, with only its delta unavailable after a matching association issue. These are test expectations, not observed run results.

Root-selected bounded test selectors:

- tests/test_fluorescence_prepared_core.py
- tests/test_fluorescence_event_calculations.py
- tests/test_fluorescence_event_sheet.py
- tests/test_fluorescence_partial_primary.py
- tests/test_fluorescence_control_support.py

Root owns its new tests/test_fluorescence_prepared_bindings.py selector and the existing bounded lifecycle. Runtime verification remains pending that run. New source parsing, installed preparation libraries and full episode/live-resource verification are outside this core change and are not established by these tests.

The synthetic helper _prepared_batches in the new test file returns primary/prepared parse objects; preparation="scaling" supplies the optional field for root-owned context tests. It does not execute preparation.
