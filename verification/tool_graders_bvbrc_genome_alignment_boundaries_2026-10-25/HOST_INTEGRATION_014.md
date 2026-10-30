# GenomeAlignment production integration — 014

Additive coding contract, 2026-10-25. The immutable tool-grader goal remains
authoritative. C extraction 001/002, root boundaries 006–013, E001 and F001
define the unchanged numerical and return meanings. This connects their actual
implementations; it does not create another episode or scientific score.

## Ownership and handoffs

Root owns registration, existing API/execution/publication/host consumers,
selected-tool information and prospective pins. Root also owns the new narrow
`bvbrc_genome_alignment_host_inputs.py` collector, called only by the actual
`AppServicePublications._genome_alignment_retained_records` method. Worker159
owns the five native structural validators and D dispatch, exclusively.

A fresh integration-test worker owns only new
`tests/test_bvbrc_genome_alignment_host.py` and
`verification/tool_graders_bvbrc_genome_alignment_host_2026-10-25/`. It may import
existing test helpers read-only. It must not replace publications, custody,
registries, native extraction, sheets, calculators, projection or return classes.
Controlled native service responses and scripted original selections are
permitted and must be labelled as such. They do not establish live BV-BRC access
or a complete configured-model Workflow.

## Host extraction input

`AppServicePublications._genome_alignment_retained_records(self, context,
inputs, bundle, *, current_acquisition: dict)` returns
`(tuple[RetainedRecord, ...], dict[str, bytes])` from authenticated existing
records and their immutable bytes. The tuple and byte dictionary are passed to
the real `bvbrc_genome_alignment_bundle_adapter.consume_bundle` alongside the
existing explicitly supplied metadata, requested schema and parameters.

The selected branch is exactly `(bvbrc_genome_alignment, 1)`. Other registered
providers retain their existing signatures and numerical semantics. No network,
new action, extra model call, inferred source relationship or source acquisition
occurs in this collector.

Records are the original handoff, bundle's exact acquisition receipts, and
explicit supplied-metadata sources whose actual Store provider/version identify
an AppService TaskInfoReceipt or AcquisitionReceipt. Deduplicate only the same
source identity; preserve distinct receipts. All records must match the
original handoff, task, request and resource. Prior records require actual
possession before the current decision and completed original actions. The
current acquisition is the exact freshly published record from this action;
authenticate it with the existing records reader's `require_completed=False`
only for this one identity, then require equality with the supplied record.

Receipt ContentBindings point to their actual canonical Store envelopes. Raw
bytes are keyed by actual artifact identity and conflicting bytes reject.
Include the original handoff's authenticated native submission snapshot and
the selected acquisition artifacts already belonging to this bundle. Supplied
metadata documents and supplied contents must pass existing custody checks.

For TaskInfoReceipt, include snapshot bytes only when that exact ContentBinding
is already explicitly supplied in the selector (as content or metadata
evidence). A receipt reference does not implicitly supply stdout/stderr or
other task-info bytes. Retain a valid receipt with missing snapshot bytes so C
can report its existing local `content_missing` requirement. Do not invent a
producer witness or upgrade the bundle's original byte-version uncertainty.

## Shared consumers

Register the actual E facade in `bvbrc_appservice_adapters.bind_adapters` with
the caller's exact implementation pin. Instantiate F as
`APIServiceExecution.genome_alignment_returns`. Connect its twelve actual
fact descriptors to ExecutionEpisodes, and its own/received resolvers,
validation and admission to existing corresponding consumer methods. Host facts
include only requested F sources. Use original immutable publications for
admitted historical reports, and the newest matching publication for own facts.

For this versioned provider, requested projection completion uses E's exact
status while retaining optional missing requirements. Missing required output
artifacts still prevent completion. A newer partial/invalid publication must
not inherit an older completion proof. Do not change the estimator or create
observations for reading, grading or projecting results.

## Required integration evidence

Use real Store/Journal, original selected actions, real primitive execution,
AppServiceRecords, custody, publication, registered E, and F. Exercise original
prepare/submission, task-info, Workspace capability and selected download using
controlled service bytes. The resulting publication must contain real C/D/E
outputs, not a hand-authored publication body. Carry requested numeric facts
through an actual frozen typed form and original parent admission.

Cover the retained v4/XMFA/backbone/BBCols examples where their actual format
fits the selected input (distinct formats need not share one fake output),
including a checkable 690/693 native coverage or 40/48 identity value; zero vs
missing; explicit metadata and task-info content; unreceived logs; wrong
task/receipt/selector; partial latest result and original historical return;
saved projection without network/native/parser/scientific calculation; and
explicit saved recalculation separately. Do not monkeypatch production
validation into success. Keep original failures and report tested scope.

The existing full MSA/MetaCATS Workflow worker must wait for shared source
changes and prospective pin reconciliation before launching a new pinned run.
That exact dependency does not prevent the independent host tests above.
