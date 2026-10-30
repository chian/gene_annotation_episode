# Shared RNA comparison binding

This packet owns only `execution_episodes.py`, `execution_progress.py`, the two
new shared comparison test files, and its own fixtures and verification. It
implements 362 addendum009 against A/B/C scientific contracts and D007/E008
ports. Addendum010's original received-report prefix is root/E work and is
consumed through E's existing selected-input validation port.

## Construction and selected work

`ExecutionEpisodes` constructs `NativeRNAStructureComparisonResults(self)` and
`RNAStructureComparisonReturns(self)` wherever the original native RNA adapters
are bound. Both new attributes remain `None` otherwise. The results assignment
schema preserves both original `RESULT_SELECTOR_SCHEMA.oneOf` variants and adds
the exact `RNA_COMPARISON_SELECTOR_SCHEMA` alternative under the existing
version conditional.

The exact `native_rna_structure_comparison_selector_v1` route precedes the old
single-target native RNA route in selector validation, operation catalog,
execution, facts, credit and completion. Parent preparation and child initial
references call:

```python
validate_rna_comparison_selected_inputs(store, context, selector,
    anchor_handoff_ref=assignment['handoff_ref'],
    returns=owner.native_rna_structure_returns)
```

The original handoff remains an authenticated routing anchor. E supplies the
selected reference list and independently authenticates each original operand;
shared wiring neither substitutes that anchor for the baseline nor invokes the
old single-saved-input helper for a comparison.

## Actual results and communication

Selected `execution.results.status` and `execution.results.collect` use E's
empty-argument catalog and `execute(context, target, tool_name, arguments,
operation_key)`. E owns the durable result receipt and D's worker/publication
validation. Shared wiring exposes actual own facts from `facts(context)` and
actual received facts through `RNAStructureComparisonReturns.received_facts`.

The only added scientific source is
`execution_rna_structure_comparison_projections`. Report validation and
admission use E's exact adapters. Receipt/calculation identifiers resolve only
through `rna_comparison_receipt` and `rna_comparison_calculation`; these are
symbolic identities, not Store records. `record_admission` returns no Store
references. The retained-artifact guard runs before generic reference fallback.
Original source and artifact permissions are not expanded.

Scientific initial context may expose E's `received_context` as
`received_rna_comparison_values`. This is internal selected data only. This lane
does not add a renderer, prompt, recursive context dump or model call.

## Credit and practical endpoint

`project_credit` delegates to E's comparison `credit_view`. Actual completed
actions use E's `completion` proof through the original shared practical
completion methods and estimator. No scientific score, monitoring score,
scheduler, independent continuation rule, extra observation or extra zero turn
is introduced. A comparison recomputes retained information; it does not earn
new native-acquisition credit.

## Pre-collection description

`ExecutionTargetReader.describe_target` authenticates the routing handoff and
then emits the exact009 retained-comparison descriptor, before original native
producer status/read information. It declares `called_operation: null`, the
selected comparison question/parameters, retained-input validation and
calculation/projection implementations. It explicitly says the anchor is not
the baseline and no fresh native observation is performed. The no-selector
`describe_execution_target` path is unchanged.

## Verification interpretation

Fixtures label original producer energies, software declarations and terminal
native reports as synthetic. They make original scoped practical reservations,
real original result collections, actual Workflow child commissions and typed
returns, and actual bounded comparison worker calls. No ViennaRNA driver,
scientific native model, API, HPC or configured LLM execution is claimed.
The bounded requests and results are retained separately under each check.
Final numerical examples and source pins are recorded after the stable suite.
