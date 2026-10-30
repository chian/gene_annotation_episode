# Clarifications to the accepted interval calculation contract005

These resolve concrete implementation questions from workload463. Contract005
and original user decisions remain unchanged as records; these additions state
the exact intended behavior, not a change to the goal or an episode decision.

1. A category's false membership proven by one known false predicate is
   sufficient to bridge that interval. Under the specified AND rule, unknown
   remaining operands cannot make that category true. Thus005's wording
   "fully observed false-membership gap" means false membership is established,
   not that every numerical operand is present. Preserve partial source extent
   when inputs are incomplete. Such a gap contributes no score or denominator.
   A genuinely unknown membership still breaks the region and is never bridged.
2. If an unresolved bridge encounters unknown membership before its known
   false gap has exceeded max_gap, close with right_boundary=unknown_gap. The
   region is closed because continuation cannot be established. If the observed
   gap has already exceeded max_gap, close with observed_gap before inspecting
   later unknown membership. This field describes the evidence for closure,
   not merely the classification immediately adjacent to the last positive row.
3. After selected population intervals end, drain the remaining supplied row
   streams to validate declared ordering and final identity checks. A late
   failure preserves already yielded records but cannot establish a complete
   calculation/table. This is input validation inside the selected operation,
   not extra acquisition, another action or additional credit.
4. Emit regions in deterministic streaming closure order. For simultaneous
   closures use condition1,condition2,common order. The result makes no claim
   to global start-coordinate sorting; do not buffer/sort all regions merely
   for display. Each region retains its exact population/coordinate identity.
5. Multiple covering rows take the ambiguous state even when unlocated invalid
   rows also exist: retain a null single value, every covering ordinal, and the
   separate unlocated-invalid count. Neither defect is silently discarded.
6. Region source_extent is partial if a qualifying or actually bridged gap
   segment has a source extent other than complete or a track state other than
   observed. An unknown_gap boundary also makes extent partial. A trailing gap
   that is not bridged affects the boundary qualification, not the weighted
   score. Apply the same max-gap reasoning to the left boundary: an earlier
   unknown remains relevant until a sufficiently long observed-false gap
   separates it from the current region.
7. At a selected population endpoint, a known-false prefix/suffix of length
   <=max_gap leaves the respective boundary label population_boundary. Once
   the known-false gap exceeds max_gap, use observed_gap. These fields describe
   why extension stopped, not a claim that the qualifying region coordinate
   equals the selected population endpoint. Actual coordinates remain unchanged.
