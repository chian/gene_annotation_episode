# A105: complete numerical example from assay cells to a candidate coordinate

2026-10-23. New review proposal; earlier records remain intact. No numerical
policy is adopted and no production reader, prompt, scorer, library publication
or scientific run is changed. The ten-sheet completion count remains 0/10.

The outcome sought is one A105 coordinate for **one persistent candidate
annotation**, with its exact molecular meaning and evidence retained. The
following example now supplies that numerical endpoint. It does not calculate
the other nine coordinates or a complete annotation hypervolume.

## The three responsibilities remain separate

The existing discovery TASK begins from supplied sequence, selected file
contents or snippets and investigates possible molecular activities; it does
not require a candidate function or public identifier at launch. The numerical
sheet below is separate from that prompt. Targeted readers or dataset analyses
populate its defined numerical cells; they do not choose an overall intuitive
relevance grade or copy this sheet wholesale into the prompt.

No new prompt wording is introduced by this review. The exact measurement/model
cells are in MODEL_FIELD_CROSSWALK_007.md and the calibrated field contract.
The new whole-candidate fields and formula are in the reducer proposal and its
FINAL_CLARIFICATIONS_AND_CHECKS_002.md. They are proposed research IO, not fields
already available through the current runtime.

## A fully numerical synthetic example

This new **synthetic composition** explicitly assigns the two previously checked
synthetic calculations to the same invented target T and reference condition C.
The candidate asserts: T performs molecular reaction A under C, and its stated
activity on A exceeds that on B under C. These are stipulated compatible
assertions for this arithmetic example, not new biological findings or mandatory
assay requirements. Source measurements from earlier fixtures are reused as
inputs; they are not counted as new independent experiments.

### Activity assertion

The source assay is the existing corrected-activity fixture. Its required
numerical assumptions and inputs are explicit:

| Cell | Calculation/operand | Value |
|---|---|---:|
| Preparation rate after blank | 1.20 minus 0.20 micromolar/min | 1.00 micromolar/min |
| Rate attributable to the assayed molecule | 1.00 minus measured contaminant contribution 0.15 | 0.85 micromolar/min |
| Recovery | Declared measured calibration ratio | 1.00 |
| Assayed protein amount | Declared concentration | 1.00 micromolar |
| Measured condition response | 2.00/1.60 for the same endpoint outside the intended contrast | 1.25 |
| Corrected molecular activity | 0.85/(1.00*1.00*1.25) | 0.68/min |
| Total variance | 0.0256 + 0.001156 + 0.00296225 + 0.0144 + 0.004624 + 0.0625 | 0.11124225/min squared |
| Source directional profile separation | 0.68 squared/(2*0.11124225) under the stated known-normal presence model | 2.078347030917 |
| Source index | tanh(2.078347030917/2) | 0.777561486079 |

The variance terms represent measurement, recovery, condition response,
contaminating contribution, protein amount and distinct residual preparation
variation respectively. They are propagated numerical uncertainties, not six
qualitative quality grades. The fixture explicitly supplies their independence;
unknown dependence in a real case would not be filled with zero.

For this source-to-target relationship, the existing native-component proposal
has these **synthetic native operands**, with each family weight explicitly one:

| Component | Declared native operands and conversion | Result |
|---|---|---:|
| Sequence | Compatible raw pair score 240; self scores 300 and 320; 2*240/(300+320) | 0.774193548387 |
| Structure | Native directional TM scores 0.90 and 0.85; minimum | 0.85 |
| Defined functional sites | 8 matches among 10 predefined fully observed sites | 0.80 |
| Phylogenetic placement | 85 supporting placements among 100 eligible replicates | 0.85 |
| Stated system descriptors | exp[-0.5*(7 squared/100 + 0.5 squared/1)] | 0.690734330637 |
| Equal-family mean | Sum of these five values divided by 5 | 0.792985575805 |
| Target activity index | 0.777561486079*0.792985575805 | **0.616595042762** |

This target index is a declared **uncalibrated scoring convention**, not a
predicted target rate or a probability. The system scale constants are proposed
fixture parameters. The raw-score sequence conversion has its stated scoring
conditions; arbitrary HMM bit scores or E-values cannot fill those operands.
The separate native families are not asserted to be independent proofs. Other
targets may have different relevant measurement families; five is not a
mandatory data-collection requirement.

### Specificity assertion

The existing calibrated synthetic fixture independently supplies three mapped
estimates of the same target log activity ratio, with comparability and
attribution corrections kept separate:

```
mapped_estimates = [0.8, 0.6, 0.9]
joint_covariance = [[0.230, 0.115, 0.060],
                    [0.115, 0.300, 0.085],
                    [0.060, 0.085, 0.400]]
```

The complete primitive operands, 17-variable covariance and mapping Jacobian
are retained in `a105_calibrated_contract_007/SYNTHETIC_RECORD_001.json`.
They are synthetic fit/calibration summaries, not an actual biological fit.
The calculated target log-ratio estimate is **0.773913043478**, variance
**0.155481634183**, profile separation **1.926084074217**, and bounded signed
specificity index **0.745630704507**. Its fitted correspondence is already in
the effect and covariance; the activity assertion's native correspondence mean
is not multiplied into this specificity result again.

### One candidate coordinate

No complete joint target likelihood spans both of these different input routes.
The proposed whole-candidate conventional rule therefore gives:

`signed_A105 = min(activity_index, specificity_index)`

`A105_coordinate = max(0, signed_A105)`

`= max(0, min(0.616595042762, 0.745630704507))`

`= 0.616595042762`.

This is one candidate-level A105 coordinate conditional on the fully specified
synthetic inputs, the explicit asserted conjunction and the proposed numerical
conventions. It is not a joint likelihood, an adopted policy, a score of ybhP,
or a current runtime output. If an upstream input is only conditional or has
missing required operands, this composition preserves that status; it cannot
upgrade it to a complete point.

## Exact rule for candidate meaning

Represent the actual molecular assertion using canonical statements and
explicit `all_of`/`any_of` relationships. For the conventional route:

- Statements required together combine by minimum signed index.
- Genuinely sufficient alternatives within the same asserted molecular meaning
  combine by maximum signed index.
- Apply the proposed positive part once at the end, retaining the signed index.

Competing candidate annotations retain separate identities and scores. They
are not alternatives inside this formula merely because the investigation has
not decided between them. Different assays of the same statement also do not
become alternative molecular claims: their observations belong in that
statement's upstream calculation.

This is an explicit noncompensatory convention, not a probability law. A
complete supported joint observation model, when available for the assertion,
instead evaluates the same assertion and its complement in that model before
normalization. Min/max does not claim to reconstruct that joint calculation.

Proven synonyms, duplicate clauses and logically absorbed clauses add no
support. For example `A OR (A AND B)` reduces to A even when B is unknown.
An unrelated binding result is not inserted as a requirement of a conversion
claim, nor can it replace evidence of conversion. Biological entailment between
different statements is not inferred from similar names or equal scores.

## Several homolog sources for one statement

This is a different combination from the whole-candidate rule. The 007 group
mean had a demonstrated defect: adding a zero-correspondence member reduced the
existing result by changing its denominator. The explicit 008 correction is:

`source_term_i = atanh(correspondence_i * tanh(source_S_i/2))`

`combined_signed_index = tanh(sum_i allocation_i * source_term_i)`.

Keep previously declared numerical allocations fixed when genuinely irrelevant
information is appended; there is no current-roster denominator. An exact
zero-correspondence append then contributes zero and leaves the result unchanged.
The original source observations are deduplicated and jointly fitted before S;
distinct phylogenetically related sources are not mislabeled exact duplicates.

The allocation vector is an **additional declared scoring-policy input**. It
cannot be inferred from native S/R values or a family label. For the checked
synthetic two-source case, allocations (1,1) give **0.609869038**, whereas
(0.5,0.5) give **0.340233353**. Neither table is installed as a default. If the
allowed set contains those two tables, the output is that two-point set and its
explicit bounds, not a midpoint. Known shared assay errors affect the original
joint source fit; allocations do not substitute for covariance.

This closes the undefined arithmetic by stating the exact required operand and
missing-data result. It does not resolve the user's still-pending choice of
scoring meaning or empirically calibrate cross-source transfer. A calibrated
target calculation needs its actual response mapping and joint uncertainty.

## Missing data and contradiction at the candidate boundary

| Complete declared calculation | Returned result |
|---|---|
| Both required; signed indexes 0.84 and 0.42 | Coordinate 0.42 |
| Either truly sufficient for the same assertion; same inputs | Coordinate 0.84 |
| Required 0.84 plus an unavailable statement in [-1,1] | Point unknown; coordinate bounds [0,0.84] |
| Required opposed statement -0.2 plus unknown remainder | Coordinate identified as 0; signed interval retained |
| No data for the nonempty assertion | Point unknown; bounds [0,1] |
| Repeated representation, synonym or absorbed clause | No extra contribution |
| Contradictory observations of one statement | Update that statement's actual joint/conventional calculation before this reducer; no historical maximum |

Intervals describe the actual allowed numerical inputs. They are not confidence
intervals unless a simultaneous sampling model supplies that meaning. Preserve
joint constraints; rectangular bounds are labeled outer bounds when needed.
Known zero, opposition, unavailable inputs and incomplete semantics remain
different statuses. None creates an episode stopping or scientific-acceptance
gate. Investigation progress remains separate from annotation support.

## Source trace retained from the inspected cases

| Inspected source and parent conversion | Actual numerical component and preserved limit |
|---|---|
| CsiD, DOI 10.1038/s41467-018-07563-6; CSID_NUMERICAL_CELLS_003.md | Graph-derived preparation oxygen-rate difference about 0.05578 micromoles/min; conditional two-group profile calculation. Not isolated product formation or target activity. |
| BtsT, DOI 10.1128/JB.00599-17; BTST_NUMERICAL_CELLS_001.md | Km=16.5 micromolar; specified 40-to-10 micromolar substrate response 0.53302. Shared parameter covariance matters; not transferred to a different vesicle preparation. |
| IscR, DOI 10.1038/nsmb.2568; ISCR_NUMERICAL_CELLS_001.md | IC50 values 32 nM and >510 nM give a point/limit selectivity ratio >15.9375. This is not Kd or a confidence bound. |
| IscR, DOI 10.1111/mmi.70021; ISCR_STATE_QUALIFICATION_002.md | Apparent Kd 22 nM versus >1000 nM; measured molecular state qualifies interpretation. Preparation labels are not state measurements. |
| FolE2, DOI 10.1128/JB.00287-09; FOLE2_NUMERICAL_CELLS_004.md | Metal-condition relative activity 0.14 and separately fitted substrate response 0.279114219. Their different protocols do not justify multiplying them. |
| TriA, DOI 10.1128/JB.183.8.2405-2410.2001; TRIA_NUMERICAL_CELLS_005.md | 466/475 sequence identity; native aminoatrazine activity 17 versus atrazine limit 0.01 nmol/min/mg. Reaction-specific point/limit contrast >1700 is distinct from sequence correspondence. |

No paper was newly read for this integration. The parent conversion files retain
actual source inspection, complete authority rereads and numerical checks.
Reported measurements, fitted/graph-derived values, synthetic illustrations and
proposed scoring transformations retain their different origins.

## Implementation and remaining judgment

The current code inspection establishes that an unchanged hypothesis can retain
its identity while evidence changes. Existing annotation accounts contain
coherent sets and hypothesis alternatives, but do not supply a persistent
multi-claim candidate identity/score contract. `score_axis` still returns
`annotation_aggregate: null`; the current assembled policy binds no annotation
scorer. Thus the research candidate contract is explicitly proposed, not falsely
reported as already wired.

The retained hypervolume formula is unchanged. It can later consume a defined
finite [0,1] coordinate per explicitly configured axis. Reader implementation,
candidate storage/assembly, interval-aware consumption and complete annotation
path verification remain separate work; they are not accomplished by this sheet.

The principal choices for user judgment are now concrete: the source S/B
normalization; the native correspondence combination and missing-family basis;
the fixed numerical allocations across uncalibrated homolog sources; the
required/sufficient candidate convention; and the positive-part output. The
current proposal applies measured corrections and remaining uncertainty once,
without a duplicate penalty for the same correction. No unanswered question is
treated as approval, and A105 is not marked complete by this review packet.
