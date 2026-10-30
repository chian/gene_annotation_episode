# Ten scoring sheets: progress 004

2026-10-23. Additive record. Earlier instructions, designs, goals, case packets
and progress records remain intact. The active outcome is **ten usable numerical
scoring sheets**, beginning with A105, under the seven criteria in the active
goal attachment. Completion remains **0/10**. Neither new papers nor checked
conditional calculations establish a finished whole-axis score.

## Fixed checklist

- [ ] A105 — numerical source/statement calculations, source examples and
  model-specific field contracts delivered; uncalibrated combination policy,
  whole-annotation axis scope/combination and user judgment remain unresolved.
- [ ] A101 — complete numerical sheet remains unfinished.
- [ ] A102 — complete numerical sheet remains unfinished.
- [ ] A103 — complete numerical sheet remains unfinished.
- [ ] A104 — complete numerical sheet remains unfinished.
- [ ] A106 — complete numerical sheet remains unfinished; perturbation work is
  preserved for this axis, outside A105.
- [ ] A107 — complete numerical sheet remains unfinished.
- [ ] A108 — complete numerical sheet remains unfinished.
- [ ] A110 — retained separately; complete numerical sheet remains unfinished.
- [ ] A111 — complete numerical sheet remains unfinished.

A109 remains removed. The items and order match progress001-003.

## Concrete additions to A105

| Deliverable | Actual numerical result and boundary |
|---|---|
| `a105_sheet_construction_001/FOLE2_NUMERICAL_CELLS_004.md` | Measured relative metal-condition activity and a separately fitted substrate response: zinc/manganese 0.14; GTP 50-to-3 micromolar rate ratio 0.279114219. These are activity responses, not generic reliability penalties. Their different protocols do not justify multiplying them. |
| `a105_sheet_construction_001/TRIA_NUMERICAL_CELLS_005.md` | Natural proteins have 466/475 identity; TriA preparation activity is 17 nmol/min/mg for aminoatrazine versus an atrazine nondetection below 0.01. The point/limit ratio exceeds 1700; it is not a confidence bound or calibrated transfer score. Unknown table error meaning, purity and backgrounds remain unknown. |
| `a105_sheet_construction_001/CALIBRATED_COMBINATION_006.md` | Explicit common-target contrast and joint covariance calculation. Synthetic mapped values [0.8,0.6,0.9] give effect 0.773913043, variance 0.155481634, S=1.926084074 and signed index 0.745630705. Native correspondence is not multiplied in again after its response mapping. |
| `a105_calibrated_contract_007/CALIBRATED_FIELD_CONTRACT_001.md` and populated JSON | Exact primitive and derived cells, separate condition/attribution corrections, fitted mapping, all 289 primitive covariance entries and 51 Jacobian entries, residual ownership and declared missing-data outcomes. These are fields for future readers, not implemented readers. |
| `a105_sheet_construction_001/MODEL_FIELD_CROSSWALK_007.md` | Maps named numerical cells to known-normal presence/signed contrasts, paired unknown-variance, joint known covariance, censored and compound models; also native rate, affinity, occupancy and substrate-response equations. Additive final section defines the independent-two-group unknown-variance profile and its global constrained optimum. |
| `a105_uncalibrated_combination_007/BLOCK_ALLOCATION_COMBINATION_PROPOSAL_001.md` | A fully specified candidate conventional combination with explicit allocation inputs, finite-value handling, intervals and an output in the proposed nonnegative range. It is unadopted and has material dilution/count consequences described below. |
| `a105_completion_criteria_007/COMPLETION_CRITERIA_REVIEW_001.md` and scope addendum | Finite criterion review. Missing empirical inputs differ from undefined arithmetic; no extra paper quota or production-reader requirement is added to the research goal. The per-statement/whole-annotation distinction is explicit. |

## Source inspection and authority resets

For FolE2 (DOI 10.1128/JB.00287-09), the parent inspected the worker packet,
retained primary Methods/Table 2/Figure 3/kinetic and relevant structural
passages, and the rendered figure. The primary-page network attempts did not
supply a usable full article; the retained source was used and the inspected
limits are recorded. The parent fully reread the complete authority set in six
nontruncated groups before conversion. No complete raw-data or supplement
inspection is claimed.

For TriA (DOI 10.1128/JB.183.8.2405-2410.2001), the parent inspected the full
worker packet, complete primary Methods/Results/Discussion retained text and
rendered Figures 3 and 4. The initial combined output truncated; separate reads
repaired the relevant omissions. The parent then performed all six complete
authority-reread groups before conversion, latest user goal/reminder last. No
earlier AtzA specificity paper, raw dataset or unavailable PDF was inspected.
The figure/text concentration-unit discrepancy is retained without digitizing
that curve. No new engineered-mutant evidence was imported into A105.

## Parallel ownership and verification

The completed 006 source/calculation workloads were followed by three **fresh**
007 workers with separate owned directories: uncalibrated combination,
calibrated field contract, and a criterion/scope review. The latter three read
no papers or paper-specific packets. No unrelated agent thread was resumed.

- The parent wrote and ran its FolE2 and TriA numerical checks. Their new JSON
  results preserve previous worker files and distinguish synthetic algebra from
  paper measurements.
- The parent inspected and reran the calibrated 006 main script and sensitivity
  script into `a105_sheet_construction_001/correlated_parent_check_006/`.
  The main **115 checks passed**; known independent covariance was preserved in
  the sensitivity calculation.
- The calibrated-contract worker independently used exact rational linear
  algebra: **125 checks passed**. This reproduces effect 89/115, variance
  16593/106720, S=3675344/1908195 and disagreement Q=5/23.
- The criterion worker independently checked **22 numerical relationships**.
  This is arithmetic review, not fresh paper verification.
- The uncalibrated-convention worker reported **255 checks passed**, including
  partial/all-unknown inputs, allocation scenarios and finite saturation. The
  parent read the full proposal and separately checked its main values,
  opposition and zero-correspondence dilution in
  `a105_sheet_construction_001/uncalibrated_parent_check_007.json`.
- The parent separately checked the two-normal-group stationary roots: for
  synthetic groups (n,mean,SD)=(3,3,1) and (3,1,1), the constrained optimum is
  not at the mean midpoint. Correct S=2.687639203842 versus midpoint 2.748872195622.

These overlapping check counts are not summed as unique coverage. No production
test suite, reader, library publication, annotation wiring or scientific run was
invoked. The checker results establish the stated arithmetic, not biological
calibration or user acceptance.

## Numerical behavior printed for judgment

For the calibrated synthetic model with identical mapped effects 0.8 and
marginal variance 0.25, ten independent estimates give B=0.999994478. Keeping a
shared component with C=0.10 I+0.15 J gives B=0.761594156. A repeated original
observation is counted once. Adding a positive but smaller independent effect
can reduce common-effect support: [0.8,0.1] gives B=0.384219009 versus 0.564899553
from 0.8 alone. This is not a monotonic evidence-count score.

For the uncalibrated candidate, each source contributes
`q_i=atanh(R_i*tanh(S_i/2))`. Proposed block coefficients are `1/member_count`;
their weighted sum Q becomes K=tanh(Q), followed by proposed c=max(0,K) after
all signed terms combine. These are accounting allocations, not measured
covariance or independence. With synthetic (S,R)=(4,0.8) and (-2,0.4):

- Separate allocated blocks give K=0.609869038.
- One shared block gives K=0.340233353.
- Unknown membership leaves those two possible results and their hull, with
  no preferred point or midpoint selected.

The parent printed a material defect for judgment: adding a source with **R=0**
to the first source's block changes K from 0.771222064 to 0.471244037 merely by
changing the denominator. No opposing contribution was added. The candidate is
therefore not described as validated dependence correction or silently adopted.
The three source-free deliverables do not answer the pending user choice between
average represented-source strength and accumulation with shared information.

## Exact remaining work

1. Resolve the intended uncalibrated combination and its numerical behavior.
   The candidate arithmetic is explicit, but the allocation is a scoring
   convention with demonstrated shortcomings. An unknown covariance cannot be
   supplied by a group label or by calling the convention calibrated.
2. Define the scope promised for the axis output. Current rows quantify **one
   declared molecular statement**. A specified compound statement has a joint
   route. If A105 is to produce one scalar across the entire annotation's
   molecular claims, the numerical reducer remains essential design work; it
   is not merely W05 wiring.
3. Present and incorporate actual user judgment on the proposed S/B scale,
   native correspondence combination, missing-component output and support-only
   projection. The earlier correction-versus-extra-penalty question is also
   unanswered; the existing correction-plus-uncertainty calculation remains a
   proposal and does not duplicate the same measured weakness as a penalty.
4. Complete the other nine sheets under the same outcome criteria. They are
   retained on the fixed list and have not been silently declared done, merged
   or replaced by the A105 component work.

The field crosswalk identified as unfinished by the criterion reviewer has now
been supplied by the parent and calibrated-contract worker. It does not resolve
the remaining numerical-policy or whole-annotation scope questions. Unknown
case inputs have explicit retention/missing-data behavior and are not a demand
for new experiments before useful evidence can be retained.

Goal-turn classification: progress. The goal remains active, unbudgeted and
incomplete. This record does not amend the permanent user requirements or
change the goal into an instruction checklist.

Final worker handoff: all three fresh 007 workers completed. The parent also
read `a105_uncalibrated_combination_007/PROJECTION_BOUNDARY_ADDENDUM_002.md`.
It clarifies that a proposed support coordinate can be identified as zero if
the entire allowed signed range is nonpositive, even when the signed point is
unknown. This follows the specified projection; it does not impute missing
evidence as zero. The worker reports eight additional boundary checks. The
all-unknown case still has an unknown coordinate with bounds [0,1]. This
clarification changes no completed-axis count or adoption status.
