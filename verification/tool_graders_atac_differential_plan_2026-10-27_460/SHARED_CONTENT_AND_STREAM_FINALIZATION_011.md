# ATAC shared content and stream finalization

This additive clarification follows inspection of the actual Store consumers.
The original goal and earlier contracts remain intact. It corrects an interface
assumption in461/010 before production integration: `artifact_ref` is content
addressed. Equality of that reference is not equality of the complete selected
role/run/source occurrence, and does not by itself contradict a comparison.

## Preserve occurrences and dependence

Distinct native files or selected roles can contain identical bytes, including
two genuinely empty outputs or two equal background tracks. Keep each selected
role, producer run, condition and sample relationship. Never deduplicate those
occurrences or reject a numerical join solely because their hashes or artifact
references match.

The native sheet records `duplicate_record`, requirement=`none`, with precise
fields `shared_artifact_content`, `shared_samples` or `shared_treatment_inputs`
for these relationships. Shared sample/input relationships also do not alone
invalidate the arithmetic of an explicitly selected comparison. They do forbid
inventing independent replication or independent evidence from the repeated
representation. The calculator estimates no replicate uncertainty here.

Actual contradictions remain contradictions: wrong producer/run/condition/role
binding, absent identity relationships, conflicting units/references, duplicate
logical keys and mismatched observed count sources are not repaired by this
clarification. Both native post-filter depth operands must still be taken from
their own explicitly bound report/run. No source path or condition is silently
substituted. The original defective wrapper's duplicated path assignment must
still be repaired in the selected native command construction.

Implementation ownership:464 corrects sheet/depth-selection qualifications and
tests;467 applies these meanings when constructing calculation inputs;466 uses
role/run/source occurrences in its execution/capture/result contract. No extra
sharing-approval field, runtime gate or scientific score is introduced.

## Missing depths and external streams

A genuine missing native depth alongside observed200 retains depth1=null,
depth2=200, depth_unit=tags, eligibility.depths=unavailable. The leaf can report
the resulting unavailable calculations using those exact operands. A mismatched
unit/population or forged/unbound selection must not be treated as that genuine
missing-data case. The native sheet itself is never rewritten by projection.

`ordered_track_rows` supplies every present retained-table track by its exact
track key. It does not override an in-memory native table. Reject such an
ambiguous override rather than silently choose one source.

All-stream finalization belongs to the result-worker consumer. The bridge and
the existing iterators propagate their first source failure normally. The
worker retains previously emitted data and, in its finalization path, exhausts
the other already supplied iterators to validate their final identities and
record any additional failures. It does not reacquire bytes, restart analysis,
calculate extra records, choose retries or produce another episode observation.
No failed or unconsumed stream can establish complete output. A bridge wrapper
must not add a private recovery loop that silently consumes other sources.

Verification must distinguish same-content separate roles from actual swapped
role/run bindings; preserve shared samples/inputs without inventing independence;
and show that a late failure in one table does not prevent the worker from
recording a separate later failure in another supplied table. These are
implementation checks, not new user approvals or episode actions.
