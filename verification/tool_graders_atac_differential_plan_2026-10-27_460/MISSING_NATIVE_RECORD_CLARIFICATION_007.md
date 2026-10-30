# Missing source identities at the native sheet boundary

This resolves workload464's concrete missing-slot question against accepted
native contract461. It is additive and does not change the user's goal.

The sheet retains all four requested track slots, including an unavailable
source. Do not invent a reserved artifact reference to fill a mandatory string.
For a missing-only track descriptor:

- track key, role, condition, reference and sample IDs come exactly from the
  explicit comparison and condition bindings;
- `artifact.artifact_ref` may be null, and
  `binding.source_artifact_ref` may be null;
- `binding.value_unit` may be null when the actual unit is unknown;
- source name/version/byte identity remain unknown, rows are empty and
  `data_row_count` is null; zero inspected/readable rows is still a structural
  fact, not a measured zero biological population;
- attach a declared expected artifact identity only when actually supplied;
  an unambiguous existing callpeak binding may supply its known relationships,
  while conflicting bindings stay conflicts rather than first-record choices.

Present source records retain the original non-null identity/unit requirements.
This exception records absence; it does not create a native measurement or
grant source access to an episode.

The specified streaming events and exact nine-element numerical JSONL table
encoding are the implemented storage ports. In-memory metadata and streamed
envelopes are supported. No new separate header/issue storage format is
invented in the parser. The existing result worker owns retention of event
outputs and complete original bytes, under its actual resource allocation.

DepthCount may likewise have `callpeak_run_key=null` only for missing/conflicting
selection, with no selected count or source. In that state `sample_ids=[]`
means no authoritative sample binding was selected, not an observed empty
sample population. Preserve all candidate reports/bindings and their conflicts
in the sheet. Observed or zero native counts require their exact matching run.

Two parsed track records with the same track_key are an invalid assembly call:
raise `ValueError('duplicate_atac_track_key')` before mutation or presenting a
partially assembled object as a complete sheet. Inputs remain intact for
repair; never choose the first. The four requested slots need unambiguous
keys. Repeated native rows or source artifacts within uniquely keyed roles
remain retained scientific records with explicit conflicts, not this
programming-identity error.
