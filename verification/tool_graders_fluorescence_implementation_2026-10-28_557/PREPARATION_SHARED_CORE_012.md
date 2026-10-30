# Shared fluorescence types for selected preparation and native report inputs

Implementation contract, 2026-10-28. The original user-entered goal and all
earlier records remain unchanged. This settles the shared-core changes required
by the remaining preparation/report boundary in contract008. It does not mark
either fluorescence operation complete or introduce another numerical sheet.

## Evidence and boundaries

Read proposal573/PROPOSAL_001.md together with its
REVIEW_CORRECTION_002.md. The latter preserves declared report comparisons when
their association support is unavailable. Proposal573's remaining producer,
preparation and report interfaces are planning evidence for their future exact
coding assignments; this contract settles only the shared-core owner below.
Contracts009–011 continue to define partial primary inputs, independent saved
calculation completion and control-support custody.

Both operation names continue to use fluorescence_event_population_sheet_v1,
calculate_fluorescence_sheet(sheet, *, parameters), and
project_fluorescence_result. No acquisition, numerical transform, matrix solve,
report parser, new episode, execution loop or annotation formula belongs here.
Selected preparation remains a primitive calculation within the selected
producer. Its future producer must use actual pinned libraries and retain both
original and prepared data. Merely adding these types does not enable it.

Tool-library information population is already user-authorized. The prior
interpretation that library wording required another approval was wrong.
New model-facing TASK/STEERING templates still require the user's concrete
review. No such template is settled or implemented by this contract.

## Owner S: exact additive contract

Exclusive production files:

- gene_annotation_episode/fluorescence_event_contracts.py
- gene_annotation_episode/fluorescence_event_calculations.py

Exclusive new test file: tests/test_fluorescence_prepared_core.py. Evidence goes
in the newly assigned owner's verification directory. Do not change sheet
builder, event readers, result/context views, producer, receipt, return, runtime
or prompt files. Report affected downstream consumers so their owners can make
the matching changes. Read complete changed functions and all their consumers.

1. Domain accepts its exact existing keys and, optionally, `scaling`.
   When present, scaling uses the existing closed Preparation shape:
   `{state,method,parameters_file}`, with its existing enumerations and actual
   FileIdentity rules. No other optional key is admitted. When absent, leave
   the original object and its bytes unchanged; absence means undocumented
   scaling provenance, not an inferred `not_applied` value. Validation must not
   fill defaults or mutate old sheets.

2. Measurement accepts the additional state `derived`. Its value must be
   finite, excluding bool, just as observed and supplied_predicted values are.
   The existing raw field retains its existing nullable string shape; a native
   token must not be invented for a calculated number.

3. A derived event measurement is allowed only in a nonprimary domain with
   its existing explicit source_ordinal-to-event_ordinal correspondence and at
   least one applied preparation among the domain's present scaling,
   compensation or transformation records. Existing applied-record validation
   requires method and parameters_file. A primary event cannot become an
   observed acquisition by declaring derived. Validate this in the common
   event/parse/sheet path, not only in a producer validator. Existing observed
   and supplied_predicted records remain accepted under their existing rules.

4. The shared _Operands.measurement accepts finite derived values for the same
   counts, gate predicates, fractions, intensities and control calculations.
   There is no new score, weight, transform or second calculator. Retain all
   current population, missing-value and dependency rules. Untouched columns
   can keep their original observed/supplied_predicted states in a prepared
   domain; do not require every value in that domain to be newly derived.

5. In the existing _Calculation.native_comparison, an input-stage
   native_population_unknown Issue with the report's source_key prevents
   native_minus_calculated from being evaluated. Preserve the declared
   component_request, native value/unit/precision, and any independently
   calculated linked cell. The delta is null/unavailable and carries the exact
   saved Issue and its `sheet:/issues/<index>` operand pointer. Preserve all
   existing operands and qualifications; stable-deduplicate matching issues.
   No such issue is invented for an unrelated report source. Do not conflate
   unavailable association support with a numerically malformed native token.

6. For an unlinked native report, retain existing unlinked behavior. For a
   valid linked report with no matching input issue, preserve existing exact
   subtraction. Do not add a rounding tolerance, infer a population from a
   percentage, clear a selected relationship, or change native numbers.

These changes preserve the current public signatures and sheet identifier.
Closed historical receipts/projections are never recalculated or rewritten.
A newly requested calculation of a saved qualified sheet uses the shared
calculator and preserves its qualifications. No old score history is repriced.

## Concrete verification

- Old sheet/parse/domain objects without scaling validate unchanged, including
  exact canonical bytes. Unknown extra keys still fail.
- Scaling has precisely the existing Preparation validation; an applied record
  without method or parameter identity fails. Absence remains absence.
- Finite derived values in an explicitly mapped, prepared child domain enter
  the existing calculations. Derived primary values, unmapped values, values
  in a domain with no applied preparation, booleans and NaN/Inf fail.
- A synthetic original channel [110,20] and explicitly supplied derived child
  channel [100,0], with the same two original event identities, give selected
  counts1 and0 respectively for separately selected >=105 gates. Original
  values, selected gates, sample and event identities remain unchanged. This
  tests the core, not a claimed compensation execution.
- Derived selected values [100,50] give the existing sum150, mean75 and
  median75; equivalent observed inputs use the same calculator and values.
- A native value33.33 and linked calculated100/3 retain the exact ordinary
  subtraction when supported. A matching source-scoped input issue makes
  only that delta unavailable, preserving33.33, the declaration and100/3.
  A second independent report remains usable.
- Saved-only recalculation preserves the same unavailable delta, issue and
  pointer without reading a file, acquiring evidence or running preparation.
- Existing partial-primary/control-support tests remain applicable. New
  source parsing, installed libraries and full episode delivery remain
  separate verification; these pure tests cannot close either tool operation.

Root runs the meaningful selected tests through the existing bounded lifecycle
(20GiB RAM,4GiB scratch,0swap,no wall cap). The owner may use host stdlib
source/AST/JSON/hash checks, but may not import application modules or launch
tests/native work on the unbounded host. Preserve all failed attempt evidence.
Reread the original objective and entire OPERATING PRINCIPLES after each logical
tool/substantial review, and this contract before declaring the scoped work
ready. Never read GOAL.md or mutate earlier contracts.
