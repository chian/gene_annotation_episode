# Biological assignment and unavailable expected-table clarifications

Additive correction to accepted MATH_HANDOFF_001.md, 2026-10-25. No existing
saved record or permanent goal is changed.

1. A single `BiologicalAssignment` with `state='conflicting'` is a valid record
   of an unresolved join. Preserve it; its physical alignment row contributes
   to `unresolved_row_indices`. It must not discard independent known rows.
   Reject duplicate assignment records for the same physical row and
   structurally contradictory resolved records. The earlier phrase
   "conflicting assignments are rejected structurally" means the latter,
   not rejection of the explicitly declared `conflicting` state itself.

2. Emitted native and biological statistical rows require the actual R-by-K
   expected-count matrix. Do not relax biological validation to admit `[]`
   merely to exercise a proposed empty-matrix adequacy example. No eligible
   tests are represented by empty omnibus/pair collections plus their actual
   exclusions/requirements. Missing inference can also occur with a legitimate
   zero-margin expected matrix; its known zero cells still supply numerical
   adequacy, while statistical missingness remains recorded. Malformed emitted
   rows with `expected_counts=[]` fail validation for either kind. This
   clarifies the earlier generic empty/unavailable-matrix test requirement
   without changing existing native validation or inventing unavailable data.

The shared counting/statistics/adequacy workload owns implementation of these
clarifications. The downstream provider must retain recorded join conflicts
and request missing information rather than converting the conflict to a
made-up membership or invalidating unrelated categories.
