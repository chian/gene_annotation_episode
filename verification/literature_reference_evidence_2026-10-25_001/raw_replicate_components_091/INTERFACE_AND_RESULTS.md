# Raw replicate measurement components 091

This is an implementation record and interface description, not a replacement
goal or governing amendment. The full fixed pasted literature goal remains
incomplete. No paper was read and no model was called for this change. The
examples are explicitly constructed, not primary-source evidence.

## Interfaces

New `literature_rate_replicate_inputs.read_rate_replicate_table` accepts the same
five table-envelope fields as the existing summary reader: source/artifact IDs,
literal text, representation and explicit CSV/TSV delimiter. It has a separate
raw-table header, including explicit sampling-unit and physical-observation IDs.
It retains the entire table and every literal source row. Source fields establish
the supplied subject, experiment, arm, condition, endpoint, normalization, unit,
sampling basis and value origin. It does not infer what an assay isolates.

`validate_rate_replicate_extraction` reparses the retained literal text and checks
the detached record exactly, including boolean/numeric distinctions. It requires
no source reacquisition. Counts and grouping do not certify biological
independence. The caller must map the actual experimental identities correctly.

New `literature_rate_replicate_calculations.summarize_rate_replicates` provides:

| Component | Operand/denominator | Meaning |
|---|---|---|
| Within-unit mean | Unique point observations for that actual unit | Average repeated reading; no independence assumption |
| Within-unit observed-point SD | Point deviations, denominator point count minus one | Descriptive spread among available readings |
| Group mean | Equally weighted complete sampling-unit means | Average endpoint across the selected units |
| Group sample SD | Unit-mean deviations, denominator unit count minus one | Observed spread across units |
| Conditional group mean SE | Group sample SD divided by square root of unit count | Estimated mean uncertainty under explicitly selected IID units |

`populate_rate_replicate_contrast` selects two exact arm/condition/endpoint/
normalization groups. It populates reference/test rates, their difference,
test/reference retained fraction, fractional decrease, and conditional difference
SE. It never fabricates a one-row reported summary to feed the old reader.
Independent-group SE is `sqrt(SE_reference^2 + SE_test^2)`; paired SE is the
sample SD of within-unit differences divided by the square root of pair count.
Paired SD itself is descriptive and remains obtainable without selecting IID.
Across-group dependence stays unknown unless explicitly selected. Shared unit
IDs preclude the independent-group SE; unequal unit sets preclude paired SE.
The individual measured group values remain available in both cases.

These are operands for numerical evidence components. A magnitude, ratio or
sampling SE does not establish assay validity or an experimental error rate.
The endpoint remains, for example, oxygen consumption rather than silently
becoming isolated product formation. No W05 credit or target transfer is made.

## Missing, duplicate and numeric behavior

Blanks, ND and censoring remain distinct. No full-set mean/SD/SE is populated
when selected units contain missing/censored measurements. Available-point
descriptions and unaffected unit means remain available, explicitly marked with
their own operands. There is no automatic complete-case group estimate or
imputation. This is a current capability boundary, not a prohibition on adding
an appropriate missing-data or censoring model when justified.

Repeated representations of the same physical observation preserve all source
locations without inflating the measurement count. Equal numbers with distinct
physical-observation IDs remain distinct readings. Conflicting uses of one
observation ID invalidate the affected summaries without discarding other groups.
Technical-reading count and unit count are always separate. Biological,
technical and unspecified unit meanings remain visible, including when IID is
selected conditionally. Different endpoints, normalizations and conditions are
separate groups; incompatible physical dimensions are not averaged.

Calculations use exact source decimals and unit multipliers before final float
projection. Exact contrast operands retain rational numerator/denominator
strings. This preserves a small paired difference even when two large means
round to the same displayed float. Nonrepresentable results remain unavailable,
not zero. A genuinely observed zero spread remains a descriptive zero; it does
not assert that an assay has zero error probability.

## Constructed examples and verification

Two preparation means from readings (9,11) and (19,20,21) nmol/min are 10 and
20. The equal-preparation group mean is 15 nmol/min, SD 7.0710678119 nmol/min,
and conditional SE 5 nmol/min: two preparations, five readings.

Paired preparation readings (10,20,30) versus (9,18,27) nmol/min yield a mean
difference of 2 nmol/min and conditional paired SE 0.5773502692 nmol/min.
The same values from distinct independent preparations yield difference SE
7.7674534652 nmol/min. Unknown dependence preserves the 2 nmol/min difference
with SE unavailable. None of these numbers is an assay-specific overall grade.

The executable `build_examples.py` captures five full worked outputs, source
hashes, and the focused test result. It also reconstructs the nested and paired
outputs from detached JSON with file and network acquisition forbidden. Tests
cover literal custody, partial evidence, duplication, pairing, dimensions,
numerical range, and the existing summary reader/calculator regressions.

## Remaining work

This change adds source-level reading and calculation, with constructed examples.
It does not install a LiteratureEpisodes operation, a persistence repository,
typed child-to-parent return, interpretation TASK, or primary-paper raw-table
example. Those paths need implementation and verification against the full
goal. The existing bound tool menu is unchanged. This is shared measurement
support, not another completed assay-specific grader.
