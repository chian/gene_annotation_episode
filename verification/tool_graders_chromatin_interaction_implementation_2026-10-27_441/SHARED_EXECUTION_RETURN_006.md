# Shared execution and return integration, additive record

This record describes implementation, not new goal requirements. The original
user attachment remains authoritative. No tool count changes are assigned here.

The shared practical assignment admits `native_chromatin_interactions` only
through C3's complete `RequestedJob` schema and deterministic validator. The
resource must be local and have a caller-supplied resource identity. Local
operations require the selected software, input format and every selected
analysis mode to be present in a bound configuration row, and retain the fixed
20 GiB RAM / 4 GiB scratch / zero swap / no wall-time limit.

`LocalPracticalOperations._handle` calls C3's
`prepare_local_chromatin_interaction(state, operation_key, root, policy)` from
the existing selected start action. The existing native lifecycle dispatches.
Reopening authenticates the same original reservation. Status, collection and
output reads authenticate the original assignment, run, episode, resource and
attempt through `local_chromatin_interaction_plan`. The existing explicit
failed-job retry action remains the only route to another reservation.

The root-owned `native_chromatin_interaction_observations.py` accepts a complete
validated original plan and one lifecycle view. It returns the existing output
availability, log-window and result-availability shapes. It reads only fixed
original paths and control logs, without following producer symlinks. Original
input copies and unsealed table files alone do not establish result availability.
The presence of a population manifest or final bundle still requires validation
in the separate results path. Observations do not create additional turns,
credit, scientific interpretations or completion proofs.

`ExecutionTargetReader` validates receipt attempt identity before describing,
observing or passing on the selected execution. A failed authenticated attempt
can be returned for its partial work; this does not mark that work complete.

The pure return module exposes three separately requested sources:
`chromatin_interaction_projection`, `chromatin_interaction_saved_sheets`, and
`chromatin_interaction_failures`. Shared communication accepts only their exact
registered schemas. Values undergo deterministic relationship validation and
saved artifacts require the receiving boundary's reference resolver. A schema
registration alone does not establish received-artifact authority or the full
results-to-parent path.

Verification: return/communication check001 had 30 passes and 2 failures because
the shared validator had not yet registered these schemas. After registration,
check002 passed all 34 checks, including unavailable saved references, altered
registered schemas and a mismatched projection population. Executed source and
interpreter pins were unchanged. Shared local execution and its later complete
Workflow path are being tested separately; no completed tool is claimed.
