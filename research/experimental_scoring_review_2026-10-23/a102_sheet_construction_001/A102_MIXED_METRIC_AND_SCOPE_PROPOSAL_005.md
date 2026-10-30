# A102 additive proposal: mixed metrics and recorded comparisons

This new research proposal addresses gaps 1, 3 and 4 in
`A102_PARENT_FORMULA_REVIEW_004.md`. It does not modify the permanent draft 002,
source conversions or historical calculations. It changes no production code,
reader, prompt, library, annotation or episode behavior. The user has not
adopted these numerical conventions. A105 remains first in goal accounting.

The parent reread the complete draft 002, including its native definitions,
scope/dependence rules and proposed populating IO, before writing this addition.
No new paper or paper-specific packet was opened. The primary interpretations
and the published rows retain their existing inspection records.

## 1. Preserve native calculations; define the composite explicitly

The two existing native profiles are unchanged:

    RMSD base = [2*n_pairs/(L_target+L_reference)]
                / [1+(rmsd/2 angstrom)^2]
    TM base = min(TM_target_normalized, TM_reference_normalized)

The TM values must belong to the same retained map/transform and the stated
normalization scopes. No additional coverage multiplier is applied to TM.
Native Z, RMSD, TM, counts, maps, settings and model diagnostics retain their
actual meanings. One score cannot be reconstructed from another without its
required native inputs. The existing source-designated-primary/variant-range
rule still prevents choosing the most favorable transform of one comparison.

For each metric profile t, use its own matching maps and feature geometry to
calculate reference contributions E_ti. Their feature definition and the
biological function/scope must be compatible before pooling. Let:

    S_t = max(E_ti over available supporting reference comparisons)
    O_t = max({E_ti over available incompatible reference comparisons} union {0})
    signed_margin_t = S_t-O_t

The proposed named calculation profiles are:

| Calculation profile | RMSD weight | TM weight |
|---|---:|---:|
| `rmsd_only` | 1 | 0 |
| `tm_only` | 0 | 1 |
| `rmsd_tm_equal` | 1/2 | 1/2 |

The selected profile is part of the calculation's meaning. It is not selected
by maximizing the answer. Both per-metric results remain visible. An explicitly
included but unavailable metric stays unknown; a different single-metric
calculation can be shown separately without filling that missing operand.
No second structure-comparison operation is required before an investigation
can continue.

The exact mixed contribution is:

    mixed_signed_margin = sum_t weight_t*(S_t-O_t)
    A102 = max(0,mixed_signed_margin)

Apply the positive part once, after retaining contrary contributions from
every included profile. Averaging individually clipped margins would hide
an adverse metric result. This is a defined composite convention, not a
claim that RMSD and TM already have calibrated functional units. Equal
metric weights are proposed, not measured or fitted. They combine two
descriptions of structural correspondence; they do not count two independent
experiments. A common comparison appearing in both profiles retains its
shared identity, and repeated representations within either maximum add no
weight.

## 2. An unsearched alternative is not a missing compulsory observation

The point above is conditional on the recorded comparisons. If no incompatible
comparison was included or received, O_t=0 means **no recorded opposition**.
It does not mean that an alternative search was complete, that no competing
function exists, or that the structural match uniquely identifies the function.
The support S_t and search/alternative scope remain separate outputs.

This replaces draft 002's restriction that an unexamined alternative panel
always prevents a point contribution. It supplies a current-evidence index
without creating a mandatory search itinerary or a scientific acceptance gate.

Distinguish an unsearched comparison from an unavailable result that is
explicitly part of the selected calculation. If an included alternative's
result is missing, its E has its real domain (default [0,1]), and O_t's bound
must include it. Do not relabel that case as an empty observed set to improve
the point. Unresolved function membership similarly enters possible support
or opposition with its shared assignment constraints; it is not two certain
observations.

Unknown unsearched alternatives may be represented in a separate sensitivity
range [0,current A102], conditional on the current supporting comparisons.
That is not a confidence interval and not evidence that all endpoints are
equally likely. If the entire supporting set or its scope is unspecified,
S_t remains unknown under the original rule. An empty entire evidence input
does not earn a positive point or create an observed negative experiment.

## 3. Relevant geometry versus demonstrated necessity

Draft 002's feature mean remains the graded geometric component: exact physical
anchors, distances, denominator and kernels must be stated. Equal anchor
weights remain a proposed convention. A disfavored anchor may not be removed
or duplicated by renaming panels.

A distinct, source-established necessity predicate can state that an exact
chemical role or structural element is indispensable for the **specific
function under the declared conditions**. It requires identified evidence,
the original tested molecular state and a justified relation to the comparison.
Conservation, a catalytic-sounding name, a large geometric distance or an
arbitrary distance cutoff does not establish necessity by itself.

For each such predicate h, v_h=1 when its stated condition is demonstrably met,
v_h=0 when an actual mapped observation contradicts it, and v_h in [0,1] when
unresolved. Let V_i=product_h v_h. No established predicates gives a neutral
empty conjunction V_i=1, explicitly labelled `none_established` rather than
a measurement of all possible requirements. Then:

    E_ti = base_ti * mean_relevant_geometry_i * V_i

These logical predicates are not an ordinal quality ladder. Geometric distance
and an independently established chemical requirement can concern the same
anchor but ask different questions; they qualify one correspondence and are
never counted as independent findings. A duplicate predicate gets one entry.
The same predicate must not also be inserted into the geometry mean as an
extra binary bonus. An established incompatible indispensable role makes
that specific function's E zero; the broad fold descriptor remains available.
This is a numerical statement about the claim, not a runtime stopping rule.

## 4. Complete synthetic examples

All quantities in this section are invented arithmetic fixtures, not new
native output or measurements from the published cases. RMSD uses the earlier
complete 100-residue example, with base .72 and feature mean .55 for the
supporting reference, and base .40 and feature mean .25 for its alternative.
For the new TM profile stipulate compatible paired native scores .8/.7 for
the supporting reference and .6/.5 for its alternative, with their stated
maps giving the same feature means in this fixture. No necessity predicate
is established, so V=1 is neutral.

| Profile | Supporting E | Opposing E | Signed margin |
|---|---:|---:|---:|
| RMSD | .72*.55=.396 | .40*.25=.100 | .296 |
| TM | min(.8,.7)*.55=.385 | min(.6,.5)*.25=.125 | .260 |
| Equal composite | — | — | (.296+.260)/2 = **.278** |

With no incompatible comparisons received, the same observed support yields
(.396+.385)/2=.3905, explicitly labelled recorded-opposition-only. Its open-
alternative sensitivity is [0,.3905], not a claim that contrary matches were
excluded. If the TM supporting result is known but its **included** alternative
is unavailable, its opposing value is [0,1]; the mixed point is null, with
bounds [0,.3405]. This differs from an unsearched comparison.

If the entire included TM channel is unavailable, S_TM and O_TM each have
[0,1] domains. Together with the known RMSD margin .296, the mixed bounds are
[0,.648], with point null. The separately named RMSD-only calculation remains
.296; it cannot stand in for the missing mixed result.

For a second constructed contrast, keep the RMSD margin .296 but let the TM
support and opposition be .2 and .6. The mixed signed margin is -.052 and
A102=0. Clipping each channel first would instead give .148 and discard the
adverse TM result; that is not this proposal.

If an actually incompatible necessary feature is established for the specific
supporting function, V=0 makes its E zero in both profiles. The broad RMSD
base .72 remains a measured descriptor in the fixture; it is not erased or
turned into evidence that the structures are unrelated. If that necessity
predicate is unresolved, shared V in [0,1] gives mixed contribution bounds
[0,.278] for the original mixed example, not an invented 0.5 factor.

## 5. Exact bounds and additions to the unimplemented IO

For profile intervals S_t in [sL_t,sU_t] and O_t in [oL_t,oU_t]:

    signed_lower = sum_t weight_t*(sL_t-oU_t)
    signed_upper = sum_t weight_t*(sU_t-oL_t)
    contribution_bounds = [max(0,signed_lower), max(0,signed_upper)]

These are conservative outer bounds; actual shared-coordinate, membership,
model-variant and necessity constraints may narrow them. Shared variables
remain shared during any tighter joint calculation. Statistical intervals,+model-sensitivity ranges and missing-input bounds remain separately typed.

Additional exact fields for the proposed populating/compiling functions:

| Field | Type / meaning |
|---|---|
| `calculation_profile` | `rmsd_only`, `tm_only`, `rmsd_tm_equal` |
| `metric_weights` | Exact nonnegative rational weights, sum one |
| `metric_panels[]` | Native profile; declared target/function/scope; original reference comparisons; map/variant identities; S, O and bounds |
| `comparison_availability` | `available`, `included_unavailable`, `not_included`; never an evidence-quality number |
| `opposition_interpretation` | `recorded_only`; separate actual search scope and reporting completeness |
| `function_membership` | Guaranteed/possible support and guaranteed/possible incompatibility, with mutually exclusive assignments retained |
| `necessary_predicates[]` | Unique physical predicate; source evidence and conditions; target/reference mapping; satisfied/contradicted/unresolved status; v bounds |
| `necessary_conjunction` | V point/bounds; `none_established` only for a neutral empty conjunction |
| `metric_signed_margins[]` | S_t-O_t and separately typed bounds |
| `mixed_signed_margin` | Weighted sum before clipping |
| `A102_recorded_contribution` | Its positive part and separately typed bounds |
| `open_alternative_sensitivity` | [0,current contribution] conditional on the stated current support; not a CI |
| `policy_parameters` | Existing geometry scales and new metric weights, all `proposed_parameter` |

An existing native comparison can populate several relevant metric cells,
but it remains one underlying structural observation. None of these fields
implements a reader, launches a structure search, changes a prompt or selects
episode continuation. The checked examples make the numerical choices
reviewable; biological calibration and user feedback remain outstanding.

## Additive correction 001: synthetic TM normalization and a typographic error

The section 4 fixture keeps equal 100-residue target/reference normalization
lengths. Under one fixed map/transform and native distance-scale definition,
the two normalized TM scores must therefore be equal. The initially written
.8/.7 and .6/.5 pairs do not satisfy that condition. The corrected synthetic
pairs are **.7/.7 for the supporting comparison and .5/.5 for the alternative**.
They can be produced arithmetically by 70 and 50 exactly superposed C-alpha
pairs respectively, each divided by the corresponding 100-residue length.
Their TM comparison maps are distinct from the earlier RMSD maps; each metric
retains its own actual scope/map/transform and its own side-chain/feature
geometry. The stated feature means are fixture inputs, not inferred from a
TM score or a claim that all side-chain atoms superpose with C-alpha atoms.
No coordinate model, optimized alignment or native program run is asserted.

The smaller scores, .7 and .5, and every subsequent numerical result are
unchanged. This correction makes the assumed native inputs consistent; it
does not claim a biological observation. The parent checker uses these
corrected inputs only. The earlier text remains a record of the draft error.

In section 5, the text `intervals,+model-sensitivity` contains a typographic
plus sign, not an arithmetic operator. That sentence means: statistical
intervals, model-sensitivity ranges and missing-input bounds remain separately
typed.
