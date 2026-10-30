# 030 selected-witness repair feedback handoff

Implemented only the released three production paths and the new assigned test
file. The full active literature goal remains incomplete. This contribution
adds factual repair information; it creates no scoring component, scientific
interpretation, source acquisition or model call.

## Changed behavior

`ExperimentalContractError` accepts optional keyword-only `detail`, detached by
deepcopy. Existing two-argument construction, `code`, `field`, string and `args`
are unchanged. `_Sources.witness` attaches detail only for literal quote mismatch
after authorized source reading, valid bounds and strict selected UTF8 decoding.

The observation contains the exact selected source/artifact/representation and
offsets, actual and nominated UTF8 lengths, first mismatch byte and exact raw
selected text. The first mismatch is relative to the selected start; a length
only mismatch uses the common-prefix byte length. An unencodable nomination
retains the same error with unknown nominated length and mismatch byte.

The accompanying JSON string literal round-trips to the exact selected text,
escaping controls, Unicode, pipes and angle brackets for the unchanged Markdown
table renderer. It is a representation of selected bytes, not a suggested
experiment, operand or repaired argument object. Existing scientific parsing,
source selection and source custody are unchanged. The episode chooses repair.

C7 propagates attached detail only for ExperimentalContractError with code
source_quote_mismatch. Other invalid feedback retains its previous shape.

## Complete affected-path inspection

Read the active attachment and root instructions; GOAL, EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, TASK_AND_STEERING and W04 evidence-axis instructions;
the workload030 interface; the three owned implementation files; native rate
reader, repository custody/population/return paths; runtime selected execution,
failure feedback, next-decision construction, saved-action replay and observation
handling; journal persistence; and ordinary factual feedback rendering. Enumerated
all exception and _Sources consumers. Every other catch of this exception only
reraises it. No consumer requires reconstructing the exception from its args.

The actual runtime records an invalid selected operation before raising
ActionFailure. FeedbackEpisode uses the unchanged controller decision without a
new observation. The next iteration receives recorded feedback. Replay reads
the saved invalid result before dispatch, preserving old failures verbatim.
Successful numerical population and typed return continue through the existing
native source-rate sheet and projection.

## Controlled evidence

The source, provider choices and controller are explicitly synthetic. The fixture
selected a mismatched experiment quote, received exact selected-byte feedback,
then explicitly chose a predetermined exact repair. There was no automatic
retry or modification of the failed arguments. It populated one native sheet
and returned only requested rate_difference and difference_se cells. The former
was 0.009 umol/min/mg; the latter remained unavailable. No target credit or new
scientific measurement was inferred from the fixture.

The exact focused fixture is retained under controlled_repair_fixture_001.
CONTROLLED_REPAIR_EVIDENCE.json includes file hashes, actual action rows,
observation rows and requested typed forms. Counts are four selected actions,
one invalid population with null credit, one successful population, three
controller observations, and one admitted native-return subset. The child has
one completed population observation; the failed attempt adds none. Annotation
credit is zero.

The actual DecisionSource.execute saved-result branch replayed that invalid
action with dispatch/source reads forbidden, leaving its row and observation
count unchanged. A separately constructed legacy synthetic failure without
detail also replayed without retrospective enrichment. This is a saved-action
replay check, not a new detached/reconstructed model-run demonstration.

## Verification and limits

The new 34-check suite passed in 26.56 seconds (exit0), including ASCII and
multibyte Unicode, internal/length-only mismatch, representation identity,
escaped literal round-trip, lone surrogate nomination, unchanged success/other
failures, rejected receipt/scope/ancestry/representation and invalid selected
UTF8/span handling, controlled repair, typed delivery and saved replay. An
initial fixture-only role/path mismatch was corrected before that terminal run.
The broader joined literature run is recorded separately in TEST_JOINED_FINAL.log
and terminal results; its running output is not a success claim.

No primary paper or private model/provider history was inspected. No actual
model execution, run024 state/pin mutation, source rewriting, occurrence search,
fuzzy matching, normalization, new source-processing observation, TASK/renderer,
form, role, controller, scoring or credit change was made. The byte checks retain
the existing selected-span UTF8 validation; they add no full-artifact decoding
requirement. Actual-model repair behavior remains unverified.

OWNED_FINAL.diff and SOURCE_MANIFEST_FINAL.json define the final owned changes.

## Additive shared-generation qualification

The parent independently verified the preserved controlled fixture and owned
030 bytes. It also identified unrelated divergence in current shared
episode_services.py after the reviewed027 release. This workload did not edit
that file. The broad regression therefore verifies the current-main generation,
not the separately reconstructed unified pin. The parent owns reconstruction
from the reviewed027/029/030 changes over immutable024 and its final integration
verification; no equivalence to that pin is claimed by this workload.

## Terminal broader result

The exact joined current-main process exited 0: 3750 passed, 11 skipped in
2258.42 seconds (37 minutes 38 seconds). The new focused suite separately passed
34 tests in 26.56 seconds. These are overlapping results and are not added as
unique coverage. TERMINAL_RESULTS.json records the exact commands, generation
qualification, actual exit/counts, controlled counts and final source hashes.
All four frozen owned files were rehashed after terminal completion and still
match SOURCE_MANIFEST_FINAL.json. No further code edits followed the focused
fixture-path correction. The 11 skipped checks are not claimed as verified.
