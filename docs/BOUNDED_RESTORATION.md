# Bounded added history for a fresh model conversation

This runtime changes transport restoration only. Scientific state,
selected-action replay, action identities, historical credit and numerical
controller reconstruction retain their existing authorities. The verification
below distinguishes fixture checks from actual configured-model recovery.

Previously a fresh provider received every earlier full context and response for
the active Episode. The runtime now supplies `restored_episode_history`, a
deterministic index of at most the configured number of its own prior decisions.
SQLite projects the index fields without bringing archived context strings,
tool-result bodies or repeated schemas into Python.

The index contains:

```json
{
  "total_prior_decisions": 42,
  "preview_size": 3,
  "omitted_prior_decisions": 39,
  "entries": [
    {"decision_index": 39, "kind": "tool", "tool": "source.read", "status": "completed", "credit": 1.0},
    {"decision_index": 40, "kind": "tool", "tool": "source.read", "status": "failed", "credit": null},
    {"decision_index": 41, "kind": "reason", "tool": null, "status": "completed", "credit": 2.0}
  ],
  "exact_read_tool": "episode.history"
}
```

This is an illustrative representation, not saved biological evidence. Entries
are the newest prior decisions in original order. A decision index is stable
within the owning Episode. It is an operational identity, not a semantic record
reference and not an index into another Episode's work. A saved model response
does not establish completion: status comes from the recorded action/result or
delivery attempt. An action with an unfinished result is `pending`; a child
whose parent action has not returned is also `pending`. A decision without a
recorded execution is `unexecuted`. Failed/invalid/unavailable results retain
their actual statuses. Report redelivery is identified as `report_delivered` or
`report_delivery_failed`, without manufacturing a scientific action.

No model fills this index, and it contains no newly inferred biological account.
The new conversation still receives its actual goal/scope, current typed state,
last outcome/feedback, effective credit binding, controller state, parent purpose,
requested form, current admitted report values and their actual recorded basis.
Reconstruction of an existing pending request retains that request's saved
scientific context. Before dispatch the exact context, including its bounded
operational index, is journaled in `runtime_model_calls.request`. Completed old
calls are never rewritten. Cached replay returns the same context the owner
received. Because the index contains only metadata, recording it never embeds
previous full contexts or a recursive conversation tree.

## Ordinary exact recall

`episode.history` is available through the same Workflow catalog/execution path
as other selected tools. The host fixes the current Episode and the strict
prior-decision boundary. The model cannot provide an Episode ID or read the
current/future decision recursively.

Under `decision_exchange_v1`, `request_context` reads own attempt metadata and
selected inputs. Its `own_attempt_detail` pointers do not address outcomes.
The ordinary `episode.history` reader remains available for `records` and
`publications`; the metadata-only `index` view is supplied by pending lookups.
An outcome fingerprint includes an actionable `read_with` declaration for its
exact prior decision. Several selected own read results can therefore be recalled
together without rereading their sources. This remains one ordinary completed
read with the existing observation semantics; it does not replay old work or
award its old credit. It does not grant another episode's private history.
This interface correction was source reviewed on 2026-11-05; its fresh full
workflow validation is tracked in the evidence-axis ledger.

Examples:

```json
{"view":"index","offset":0,"limit":10}
```

```json
{"view":"records","decision_indices":[0,7]}
```

`view` is `index` or `records`. Optional `offset` and `limit` page the ordered
prior decisions. The default ordinary page size is `max(1, preview_size)`:
disabling automatic preview entries does not disable a selected read or make
its next offset fail to advance. The effective page `limit` is recorded in the
read result. `decision_indices`
selects exact prior IDs and cannot be mixed with pagination arguments.

An exact record returns its recorded selection, actual saved outcome or null,
historical credit or null, any actual admitted direct-child form for that
decision, and constrained delivery failure feedback when applicable. It does
not return old model contexts, native private reasoning, unadmitted child forms,
or child-private decisions/results. Actual admitted forms pass the same typed
contract/reference boundary on recall. The historical child form is not silently
reinterpreted as a new judgment. A later redelivery has its own prior decision.

The outer read is `completed` when reading succeeds; an old `failed` outcome
inside it remains failed with its original credit null. History reads return
no newly committed/changed semantic references. This is one selected ordinary
read, permitting zero gain like `state.query`; it never executes old work.
Its own outcome is journaled and replayed exactly. A recovery that reuses that
read does not acquire it or observe it twice. Automatic index assembly itself
creates no action, observation or credit and makes no model/composer call.

## Generated publication batches and bounded ID recall

`reads.map`, `genes.predict`, `sequence.view`, `sequence.translate`,
`reads.inspect` and `reads.align` declare the host-owned outer
`published_batch.representation = "native_publications_v1"`. This describes
generated publications, not a scientific assessment. Completed row counts,
structured failure-row counts when known, and an optional common-source
observation query come from the actual selected operation. A late failure keeps
the same declaration and valid partial publications. A completed row is a
producer-defined whole output: a lone feature from an unfinished
feature/product/observation group is retained but is not counted as a completed
gene candidate. Counts earn no credit.

One runtime boundary presents automatic prefixes using the run's actual
`restoration.preview_size`. It bounds the declared outer publication-ID array,
existing result-row prefixes, the partial fallback's duplicate retained-ID
array, and generated failure rows at the known result/feedback positions.
Exact total/included/truncated metadata distinguishes the preview from complete
work. No arbitrary nested field or unrestricted source payload controls this
presentation. The next decision's visible basis is derived from its presented
state/outcome, rather than hidden full publication IDs. Repeated native failure
feedback uses that same presented prefix.

Complete outcomes remain in both durable journals and `source.last_outcome`.
Parent-requested fact arrays and admitted forms remain complete. An explicit
state/source/history page retains its selected bounds; a nested historical
outcome or child form is never recursively previewed. This does not bound all
current model input, active publication memory or arbitrary native/provider
results. The protocol currently applies only to the declared producers above.

The existing `episode.history` tool also offers a bounded publication-ID view:

```json
{"view":"publications","decision_index":7,"offset":0,"limit":24}
```

It selects one prior own decision, preserving actual array order and duplicate
entries. `records` contain `publication_index` and `record_ref`; `total`,
`next_offset` and executable `next_query` describe that exact array. SQLite
projects only the selected ID page, without decoding its full outcome, source
bodies or contexts. The result identifies `action_status` and `result_recorded`.
Pending/unexecuted work has unknown (`null`) total; a recorded empty array has
total zero. Failed/partial work keeps its actual status and surviving IDs.
The read's outer committed/changed arrays are empty: recalling IDs does not
republish work or create credit. Default page size reuses
`max(1, restoration.preview_size)`; zero automatic preview still permits a
positive explicit page. Current/future decisions and another Episode's private
history remain unavailable. Existing `index`/`records` semantics are unchanged.

Automatic batch previews supply this exact own-action query. Common-source
producers additionally supply an ordinary `state.query` observation page;
candidate observations identify their real feature/product subjects. Separate
sources in `reads.align` require no synthetic shared source: publication paging
exposes the actual retained IDs. Full `episode.history` records and retained
source bytes remain explicitly readable without another model/composer call.

## Caller configuration and recovery

The single packaged authority is `gene_annotation_episode/defaults.toml`:

```toml
[restoration]
preview_size = 24
```

`preview_size` is a nonnegative integer. Zero omits preview entries while keeping
the exact prior count and recall tool available. A full caller config may
override its `restoration` section, or the Python caller may pass
`run_workflow(..., restoration_settings={"preview_size": 8})`. The explicit
argument takes precedence. The effective setting is recorded in both run.json
and the authoritative run settings. An Episode cannot override it.

Resume uses the recorded value even if the packaged default changed. An explicit
different resume value is an operational configuration mismatch. Older runs
without this binding require their original code snapshot; this stage does not
rewrite their decision schemas or import old model histories into a new format.
The setting controls metadata size, never work, scientific acceptance or
numerical continuation.

## Limits and verification

This bounds the **added automatic replay index**, not the entire current model
input. Current subject collections, raw controller scores, admitted direct-child
forms and an explicitly requested large tool result remain separate potential
sources of growth. Typed parent forms can be needed for future scientific
decisions; their existence is not a reason to discard them as private history.
Closed child trees and native provider conversations retain their existing
archive/release path. No history summarizer or scientific gate was introduced.

Focused offline checks are in `tests/test_runtime_history.py`. They exercise a
large archived-payload interruption/resume, metadata-only row/decoder sentinels,
exact failed-outcome recall and its recovery accounting, owning-Episode
isolation, parent-only admitted forms, pending/unexecuted distinctions, exact
pagination and caller configuration persistence. Synthetic fixture controller
counts are test boundaries only. Test results are recorded in the staged review;
no native provider or live run is launched by these checks.

Verification on 2026-10-19:

- First focused restoration/history selection: 10 passed, 27 deselected in
  48.48 s (session 94734).
- Runtime/history plus operational-feedback integration: 55 passed in 133.62 s
  (session 32087). That process was collected before the final exact-context
  journaling and SQL tag-normalization adjustments; it does not alone verify
  those adjustments.
- Fresh post-provenance/SQL `tests/test_runtime.py tests/test_runtime_history.py`:
  **37 passed in 144.48 s** (session 60780). This includes exact pending and
  successful supplied-context persistence, recovery without old-call rewrites,
  and a row/decoder sentinel against both large archived bodies and malformed
  metadata tags. This process preceded the final ordinary-page fallback below.
- Final ordinary-page correction: zero automatic preview still gives an
  advancing default ordinary page of one record. The effective page limit is
  recorded. Fresh focused index/records, pagination and persisted-configuration
  checks: **4 passed, 7 deselected in 9.35 s** (session 50657).
- Independent source inspection found the requested history ownership,
  admission and observation boundaries coherent, and confirmed the request
  provenance correction. Root's separate full application-stage suite remains
  responsible for broader integration after the other staged modules freeze.

These are fixture/source results. No native provider recovery, live context
limit or biological annotation quality is established here.

### Actual configured-model recovery on 2026-10-20

The fixed-gene investigation `investigation_002` was interrupted to reload new
spreadsheet capabilities. Its first recovery attempt exposed schema comparison
against the expanded catalog. Saved decisions now retain their actual original
schema, including the pending decision; only genuinely new decisions receive
the added tools. A new tool attempted under an old pending contract remains
invalid. An existing saved restoration index is retained rather than regenerated.
Newly needed indexes resolve tool labels against each decision's saved catalog,
so adding a tool cannot relabel a prior unavailable-tool proposal.

The runtime/recovery group passed 38 checks in 125.93 seconds after these changes.
The affected history/publication-recall group then passed 19 checks in 81.66
seconds. These groups overlap earlier coverage; their counts are not additive
with the historical groups above. Independent source rereview found no remaining
concrete defect in the focused recovery correction.

The actual configured-model run resumed under its original identity
`run_f006289903de4ae9a4ff7067f52c11fb`. All 44 completed action/result/credit rows
and 44 controller observations matched their pre-reload hashes after recovery.
Pending decision 44 retained its 57-tool schema and original scientific context,
with a newly needed bounded restoration index. It completed; new decisions 45
and 46 used the expanded 59-tool catalog to select the sheet and row readers.
The original completed work was not executed or credited again. These records
establish this actual recovery path, not a bound on all active memory or
completion of the annotation investigation. See [SPREADSHEET_SOURCES.md](SPREADSHEET_SOURCES.md).
