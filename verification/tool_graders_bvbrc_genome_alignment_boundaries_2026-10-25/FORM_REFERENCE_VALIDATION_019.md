# Reuse authenticated facts within one form validation

This is a bounded implementation contract for a fresh candidate repair. The
current production sources and both running Workflow tests remain unchanged.
Candidate work belongs in a separate directory until root accepts the actual
test evidence and applies it after the protected runs have finished.

## Observed repeated work

The original GenomeAlignment Workflow run001 has a saved results form with157
typed-reference occurrences and71 distinct namespace/reference pairs. A single
actual ExecutionEpisodes.resolve on its already-closed coverage field, using a
private read-only Store copy and strict saved-science barriers, took11.5123s
under cProfile and30,977,136 calls. The original publication read used10.5243s;
the trace included179 custody authenticate calls and135 commission calls.
These are nested profiled cold timings, not a forecast of the entire Workflow.

BVBRCGenomeAlignmentReturns.resolve_own calls facts for every accepted reference;
resolve_received reconstructs received_context for every accepted reference.
communication.validate_form visits each typed-reference occurrence separately.
BVBRCAlignmentReturns has the same rebuilding pattern. Its earlier saved-reader
diagnostics and current full Workflow remain separate evidence. Both providers
must still authenticate real original records and check requested quantities.

## Chosen modular correction

Use an in-memory frame whose lifetime is exactly one validate_form call. The
native parsers, scientific calculators, source records, stored schemas, action
records, received forms, original forecasts and method_loop remain unchanged.
This is not a new runtime gate, durable cache or episode state store.

Add a small internal module form_reference_validation.py exposing:

```python
@contextmanager
def form_reference_validation():
    ...

def form_validation_value(key: tuple, produce: Callable[[], dict]) -> dict:
    ...
```

The context manager installs a fresh ContextVar frame for each form check.
Nested form checks get separate frames and restore their caller's frame.
On every exit, including an exception, mark the frame inactive, release all
values and reset the context variable. A copied asynchronous context retaining
an old frame must not keep a usable cache after that form has ended. There is
no cache across validate_form calls, episode turns, report admissions, direct
resolver calls or source updates. Without an active frame, produce runs normally.

The value helper creates a private detached copy of the first successful
produced value and returns a detached copy on every use. Failed production is
not remembered. It must not turn an exception into success or retain a partial
factory result. Cache keys are internal, not model-generated identifiers.

Wrap communication.validate_form's existing validation in this scope, preserving
its function signature, closed-schema and finite-value checks, reference walk,
error types/codes/paths and actual return. Do not alter the form or resolver
interface and do not introduce a mandatory new binding protocol.

Only the two named return providers opt in. Their resolve_own memoizes the
unchanged facts(context, original_requested_schema) result; resolve_received
memoizes the unchanged received_context result converted to the same source
mapping. Use a key including provider instance, direction, the complete immutable
BindingContext identity/assignment/request/scope and explicit received_record_refs,
plus the actual schema when relevant. Do not key solely by episode or source ID.
Namespace matching, membership, per-source possession and existing False/None
fallback behavior remain unchanged. Direct calls outside form validation still
perform the original complete checks.

The original values are still checked again by the existing semantic report
validator after the generic form check. Those independent value/custody checks
must not be removed or made conditional on the memo. A new partial publication,
modified source, missing receipt, forged value, different receiving context or
changed original schema must be observed on the next validation call.

## Exclusive candidate ownership

The fresh worker owns only
verification/tool_graders_form_reference_validation_2026-10-25/ and an isolated
candidate package inside it. Its candidate production diff may contain only:

- new form_reference_validation.py;
- communication.py (validation-frame lifetime only);
- bvbrc_genome_alignment_returns.py (two resolver lookup sites only);
- bvbrc_alignment_returns.py (two resolver lookup sites only).

No existing worktree production or test file may change during either protected
Workflow. Copy the current package and unchanged method_loop as needed for the
isolated imports, retain before hashes, and ensure commands import candidate
modules rather than the worktree. Reuse original retained native data read-only.
Do not copy the entire historical verification tree; explicit read-only links
or selected fixture copies suffice. No new scientific or remote jobs.

The worker reads the full immutable goal, applicable repository/design documents,
complete four affected implementation paths and all actual callers. It rereads
the goal's sixteen design principles after examination before implementing.
If a required change lies outside this ownership, report the exact dependency
before editing. Root owns later integration and prospective source pins.

## Required evidence

1. Complete returned values, exception behavior and reference decisions remain
   identical for both actual GenomeAlignment and MSA/MetaCATS saved forms.
   Authenticate the original source, assignment, requested fields, scopes and
   completed child/parent relationships with the real Store/Journal/custody.
2. Count calls on a real multi-reference form: each selected provider's facts or
   received_context runs once within that form, rather than once per occurrence.
   Do not patch those functions to return hand-authored successful facts.
3. Same resolver reused for a second form check reauthenticates. Direct standalone
   resolution reauthenticates. Exceptions clear the frame. Nested and copied
   contexts cannot leak a usable value. A returned mutable copy cannot alter the
   privately retained snapshot or a subsequent call.
4. Unknown/cross-episode identifiers, wrong schema, altered native/saved content,
   changed ownership, unreceived sources and forged numeric values still reject.
   Newer partial current results and already-admitted historical results retain
   their existing distinct semantics. No fallback to older completed facts.
5. Strictly prohibit network, native processes, native parsers, source comparison
   and scientific calculators during saved validation. Preserve every original
   file and action/model/observation/report/receipt count on private replay copies.
6. Report comparable before/after timings and invocation counts, stating cold or
   warm and profiler overhead. A complete saved form check is required; timing
   only the dictionary lookup does not establish a production improvement.
7. Run the relevant original communication/provider/replay tests against the
   candidate, then hand root exact source hashes/diff and all original failures.
   No full Workflow rerun is needed merely to develop the candidate while the
   two original baselines are active. Root will choose the necessary integrated
   follow-up after reviewing the actual changed path.

The adapter/native scientific implementation pins do not change merely because
this presentation-independent validation mechanism changes. Any affected wider
configured binding hash is recomputed prospectively; historical runs and pins
are never edited to make a test pass.
