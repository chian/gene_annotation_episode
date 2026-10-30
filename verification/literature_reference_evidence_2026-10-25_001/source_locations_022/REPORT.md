# Literal source positions: workload 022

Implemented `source.locate` as an ordinary selected primitive in the existing
ToolRegistry and LiteratureEpisodes. This is synthetic engineering verification;
no paper, model inference, biological conclusion, new score, controller policy,
episode type or private extraction loop was introduced.

## Scope and authorities

Read the complete SOURCE_LOCATION_INTERFACES_022 contract first, then the full
active attachment at
`/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt`,
root AGENTS.md, GOAL.md, EPISODE_STRUCTURE.md, TIME_AWARE_ESTIMATION.md,
TASK_AND_STEERING.md and the W04 evidence-axis instructions. No primary source
or private model/provider/child history was inspected.

Changes are confined to the new `source_locations.py`, narrow literal-operation
additions in `tools.py` and `literature_episodes.py`, two new test modules, and
this new verification directory. Initial shared-file snapshots, exact shared
diff and starting/final hashes are retained here. Their diff shows only the
owned additions; no unexpected concurrent shared-file drift was observed.
Wait021 runtime/durable/native-event files and other-session grader code were
not changed. No old run, pin, history or scientific state was changed.

## Implementation and consumer trace

1. The episode selects `source.locate` through its existing tool action. C7's
   catalog exposes it for every literature role. C7 validates the unchanged
   assignment and selected argument schema, preserves its assigned-page ancestry
   check, and supplies the episode's actual received references through the
   existing WorkflowServices permitted-record port.
2. The registry preserves the original selected argument object, operation key,
   scope and journal result. Successful replay rechecks actual source receipt,
   source/ancestor scope, immutable source identity and representation/artifact
   identity without opening any source bytes. Different work cannot reuse the
   key. Failed original attempts replay their exact saved failure envelope;
   their absent scientific result is not reinterpreted by new custody checks.
   Non-JSON operands, including NaN/Infinity, return structured invalid feedback
   before canonical identity; they cannot be stored as canonical JSON.
3. The helper requires explicit original/text representation, never falls back
   from absent text, and verifies source metadata identity and ancestor scope.
   A bounded incremental UTF8 decoder searches raw exact bytes in source order.
   It retains enough overlap for chunk-spanning and overlapping occurrences,
   stopping after the selected result count plus a real additional occurrence
   or EOF. The continuation starts at that actual extra occurrence, retaining
   needle, representation, limit and context width exactly.
4. Results report artifact identity, source byte size, original starting offset,
   actually decoded scan range, exact matches, real continuation and independent
   unchanged context windows. Context boundaries clip partial outer UTF8
   characters inward, retain the entire match, and reject malformed source EOF,
   short reads and size changes. No total match count or unexamined suffix
   validity is claimed. NUL/bad UTF8, absent representation, invalid parameters,
   receipt/scope violations and identity inconsistencies are ordinary failures;
   missing storage remains an execution failure, never no-match.
5. Each witness has exactly the existing five input fields: source_ref,
   representation, start, end and quote. Artifact identity is alongside it.
   The unchanged native _Sources and NumberSelector readers consume those exact
   witnesses. A comparator outside a numeric quote remains a censoring relation,
   and shortening a unit still fails the existing token/context checks. The
   locator does not infer numerical, experimental or physical-measurement meaning.
6. Dispatch returns no published source/observation/assessment references.
   The ordinary shared action path supplies one observation for the actual
   completed selected operation, with no scientific information gain from
   locating bytes. Selected native population remains a separate ordinary
   action using the existing source-bound reader and numerical calculator.
7. The controlled workflow selects a source read, three literal lookups and one
   native assay population. Every native witness comes from those lookup
   outputs. The synthetic source explicitly reports the sample-minus-no-enzyme-
   blank net rate. The original source/subject/endpoint survive normal typed
   child closure, exact requested component projection and parent admission:
   net_rate = 1 uM/min; corrected_activity = null with
   correction_inputs_unreported. Interpretation and missing correction inputs
   stay separate from the literal location operation.
8. This five-action child contributes one closed child action to the parent;
   the parent then completes one own reasoning action. Exactly seven runtime
   observations are retained: five child actions and two parent actions.
   Source reading, lookup internals, calculation and typed report construction
   add no synthetic observations. All controller scores remain zero. No
   scientific observation or assessment records are created; the one new
   source after the original fixture is the selected numerical sheet.
9. Existing text rendering supplies the full detailed experimental TASK, actual
   tool description/schema and terse result tables on initial, delta and
   reconstructed decisions. No prompt renderer changes were needed. Reopened
   C7 descriptors retain the actual operation and fingerprint source_locations.py;
   a changed helper produces the existing identity-conflict rejection before
   worker use. Assigned-page descendants work; other pages, unreceived direct
   sources and cross-scope ancestors fail.

Inspected consumers include the complete modified registry execution/replay
functions and catalog; the literature assignment/catalog/dispatch/fact/return
paths; WorkflowServices and EpisodeServices permitted-record interfaces; the
existing source-window/artifact identity paths; native _Sources and NumberSelector
number/unit readers; native assay population/storage/projection/admission; the
ordinary selected ActionLeaf dispatch, result preview and experimental text
rendering; and descriptor reconstruction. Unrelated native tool implementation
branches were not changed.

## Verification

Final focused command:

```
.venv/bin/pytest -q tests/test_source_locations.py tests/test_literature_source_locations.py
```

Result: **42 passed in 76.14s**. Exact output: focused_final.log. This run includes
the explicit synthetic net-rate wording and corrected test inspection of the
actual generated run identity. Earlier test-only fixture corrections concerned
binding paths, baseline source count, descriptor exception type, empty parent
commit and use of the fixture's different run identity; no production scoring
behavior was weakened to accommodate them.

Final concrete replay follow-up command:

```
.venv/bin/pytest -q tests/test_source_locations.py::test_registry_failed_attempt_replays_its_original_failure_details tests/test_source_locations.py::test_registry_original_arguments_replay_receipts_scope_and_no_publication tests/test_source_locations.py::test_registry_reopens_original_result_read_only_without_source_io
```

Result: **5 passed in 6.60s**. Exact output: replay_final.log. Three parametrized
failure cases cover missing text, schema-invalid stdout and invalid offset.
The two completed-result checks overlap the focused run: **45 distinct new
checks passed across the final runs**. The follow-up tests the final narrow
failed-replay correction and continued completed-result receipt/scope checks.

Relevant existing synthetic regression command:

```
.venv/bin/pytest -q tests/test_tools.py tests/test_source_representations.py tests/test_source_custody_contracts.py tests/test_tool_schema_validation.py tests/test_literature_episode_branches.py tests/test_literature_assay_integration.py tests/test_literature_experimental_prompt_delivery.py -k 'not saved_primary_original_heading and not downloaded_reference_replay'
```

Result: **5 failed, 39 passed, 1 skipped, 2 deselected in 94.01s**. All five
failures reach the unchanged retired categorical scoring entrypoint only after
their source/read/replay assertions have passed:

```
credit.py:51 project_credit -> _retired()
credit.py:34 _retired -> AnnotationScoringUnavailable:
categorical_annotation_scoring_retired_use_original_snapshot_for_historical_replay
```

Exact failing test names and exception trace, command, current credit.py hash
and existing test-source hashes are in existing_regression_result.json. The
tests and scoring entrypoint were left unchanged. Primary-paper replay and
downloaded-reference replay were deliberately deselected; no giant unrelated
grader suite or live model/job was run.

CONTROLLED_RESULT.json copies only this workload's newly generated synthetic
literal-operation outputs, exact admitted typed cells and aggregate accounting.
It reads no model/provider/child history. HASHES.json records the final owned
file hashes and initial shared hashes; shared_integration.diff preserves the
narrow shared changes.

## Limits and handoff

Search memory is bounded by the supplied needle/result/context sizes plus one
64 KiB chunk; the operation does not impose scientific action quotas or a new
episode itinerary. Partial scans rely on the existing content-addressed store's
artifact custody and validate only examined bytes; a complete scan from zero
also verifies the full artifact digest. The operation neither rereads an entire
huge artifact merely to locate a bounded result nor claims a whole-file digest
verification when it stopped early.

Existing native numerical readers may still load their selected source as they
did before this change; the locator's bounded-memory behavior does not claim to
refactor them. These synthetic checks establish selected primitive execution,
literal native-reader compatibility, typed delivery and ordinary accounting.
They do not establish successful model-backed extraction, experimental truth,
completion of the literature goal or any W05/A101/annotation aggregation work.
Coordinator review, joined current checks, any new captured runtime and any model
use remain with the coordinator; no existing pin was copied or changed.
