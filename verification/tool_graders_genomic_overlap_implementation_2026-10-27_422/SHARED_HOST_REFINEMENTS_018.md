# Shared results integration refinements

Additive2026-10-27. These clarify016/017 and the actual015 consumer without
changing scientific formulas or the user's original goal.

- The exact accepted parameter is `minimum_overlap_bp`, not the illustrative
  `minimum_overlap_bases` spelling in017. No alias is introduced.
- Scientific-role closure facts pass through
  `Workflow.facts -> EpisodeBindings.received_report_facts ->
  ExecutionEpisodes.received_report_facts`. That consumer must call435's
  `facts_for_closure`, preserving the private receipt witness in the existing
  frozen runtime facts. Execution-role facts use `ExecutionEpisodes.facts`.
  The private witness is not registered as a public source or rendered in a
  model prompt.015's reference to only ExecutionEpisodes.facts was incomplete.
- 436 also supplies `owns_reference(reference) -> bool`: classification of
  saved numerical-sheet and derived worker-output artifact identities from
  authenticated completed receipts, using controls/metadata only. It grants
  nothing. Root must consult this before generic Store reference fallback.
  Actual own explicit saved returns use resolve_own; actual received scientific
  saved returns use435; an exact assigned inherited saved operand uses435's
  authenticate_received_saved_sheet. Original caller input artifacts are not
  newly private output merely because the native operation copied them.
- Preserve every matching original episode/action for a saved sheet while
  requiring its selected handoff to identify one consistent historical target.
  No arbitrary first origin, current native probe or replacement source scan.
- The selected native ResourceObservation already contains its original
  native_lifecycle.status evidence under `native`. Freeze that observation and
  terminal/quiescent evidence; do not add a second status poll just to create
  the closure record.

Root owns shared wiring.436 owns host controls and publication;437 owns complete
Workflow verification. All counts remain unchanged until actual end-to-end
verification and the remaining required information/decision boundaries pass.
