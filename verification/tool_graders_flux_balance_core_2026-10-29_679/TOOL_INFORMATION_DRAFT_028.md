# Proposed FBA static tool information — awaiting user feedback

Printed in the conversation's asynchronous feedback request on2026-10-29.
This is an unsettled template proposal, not an implementation or a goal record.
docs/TASK_AND_STEERING.md requires seeing each proposed template and running
feedback before implementation. No response has been received at this record.
An additive conversation correction replaces the original phrase "fitted fluxes"
with "predicted fluxes conditional on the model and constraints". FBA does not
fit observed fluxes in this declared mode. The corrected full proposal follows.

Name: perform_flux_balance_analysis

Resources currently implemented: explicitly bound local Cobra/GLPK software,
using a supplied SBML or Cobra JSON model.

Description: Calculate steady-state molecular-model fluxes and inspect the
retained solution's objective, bounds, balance constraints and missing-data
qualifications.

## Proposed recurring TASK instructions

Calculate the selected flux-balance analysis for the supplied molecular model
within the parent's assigned scope and resource constraints. Preserve the
selected model, software, objective, explicit bound changes, calculation
parameters and requested return fields. Check whether each selected bound change
has the required supplied source; distinguish sourced experimental constraints
from model defaults and unsupported assumptions. Do not invent constraints,
concentrations, units or calibration.

Choose the next useful action from the information available: inspect or repair
an input problem, start the selected job, observe an existing attempt, acquire
its closed outputs, or recalculate an explicitly received saved sheet with
selected parameters. Revise that choice using actual outcomes. An elapsed wait
does not authorize replacing a job. Use status and bounded log information to
assess execution; process liveness alone does not show useful progress.

For native results, retain the original model and request, effective model and
solver problem, solution, flux CSV, native log and manifest. Preserve valid
partial outputs and distinguish infeasible, failed, missing, conflicting and
unavailable results. For saved-sheet recalculation, use the received sheet and
explicit parameters without rerunning optimization.

Inspect the requested reaction fluxes, objective components, bound checks and
balance residuals through the common numerical sheet and calculations. Keep
reaction/gene associations, populations, denominators, units, tolerances and
unavailable values attached to their measurements. Model feasibility and
predicted fluxes are conditional on the model and constraints; they do not
establish an observed reaction rate or a probability that a gene annotation is
correct. Return only the parent-requested typed measurements, saved-sheet
identities and recorded qualifications.

## Decision/information trace (implementation evidence, outside the prompt)

| Episode decision | Relevant supplied information |
| --- | --- |
| Inspect or repair an input |selected File/format, explicit bounds, actual source qualifications |
| Start selected work |parent scope/allocation, exact software/model/objective selection, actual available resource |
| Observe existing work |original handle, actual status and bounded logs, timing information when measured |
| Acquire outputs |original selection, writer closure, declared outputs and partial/conflict facts |
| Recalculate saved data |explicitly received sheet, selected parameters and requested typed fields |
| Return information |parent's original exact typed contract and recorded common-sheet projection |

This static tool-information text supplies TASK guidance, with no past history
or STEERING. The separate pending scientific-parent STEERING draft has its own
feedback boundary. Host IDs/hashes, custody controls and bookkeeping remain
outside model-facing text. Native runtime/catalog/full scientific-parent
verification is still required; this draft alone establishes none of them.
