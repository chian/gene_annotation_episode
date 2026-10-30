# Proposed scoring rubrics: experimental evidence axes A105, A106 and A111

These are **proposed numerical rules for review**, not an approved policy, a
probability of function, an installed caller binding or a replacement annotation
formula. They score a formal evidence entry about a stated annotation claim.
The same entry can be extracted from a publication or produced by analysis of
an actual dataset. Neither source route receives a bonus.

## Common formal input and accounting

Each entry identifies the actual experiment/analysis, assayed subject/construct,
claim, conditions, controls, measured endpoint and source/dataset lineage. A
homolog-derived entry additionally identifies the actual sequence/structural
correspondence to the target and the relevant mapped region. Missing transfer
information gives an unknown target-transfer result; it does not make the
homolog's measured experiment disappear.

Native values retain units, method, denominator, bounds, uncertainty and control
identities. In particular, a larger rate or kcat, a lower Kd, or a higher-resolution
structure does not automatically mean a stronger target-function assignment.

The implemented evaluator is `score_axis(entry, evidence_units)`. Each formal
unit contains `experiment_id`, `representation_id`, `origin` (`literature` or
`dataset`), native `measurements`, the closed `judgment`, and actual `witnesses`.
It returns `experiments[].routes[]`, including `route_id`, `status`, `polarity`,
`score`, `score_bounds`, `score_unit` and the retained measurement/provenance
records. `score` is null for unknown/unusable input or a non-point bound. Positive,
negative and non-discriminating routes are separate. A competent negative
must test the relevant claim under the reported conditions with a working assay
and a source-defined detection/equivalence limit; an ordinary nonsignificant
result is not an absence measurement.

For a usable native evidence-strength statistic, the explicit proposed native
route is `-log10(p_or_q)`, retaining the actual statistic and interpretation.
For example, a matched native q-value of `0.0001` gives `4`, in units of negative
log10 native tail probability. A reported upper bound `q < 0.0001` gives a lower
bound `score > 4`; an underflow/displayed zero gives no invented finite/infinite
score. Values outside `[0,1]` are unavailable as probability inputs. A p-value
is a tail probability under its stated null, not a function probability; an assay
magnitude is not a confidence statistic. A native statistic is usable only when
its tested contrast, direction, controls and method actually address the claim.
The rule table below is an explicitly proposed **ordinal assurance route**, used
when there is no usable native strength score for the desired comparison. The
evaluator keeps native and ordinal routes separate: it does not sum them, choose
an annotation aggregate or secretly replace one with the other. Raw activity,
Kd, growth and structural quantities have separate identity routes marked
`non_discriminating`; their magnitude is not functional-confidence evidence.

Choose the highest row whose conditions are all established by actual witnesses.
The implemented ordinal route returns a score interval when unresolved criteria
leave several levels possible. A demonstrated 0.50 level with an unexamined
discriminating comparison warrants at least 0.50; it does not manufacture proof
that the higher level is false. No midpoint or scalar annotation aggregate is
chosen implicitly.
Do not average criterion judgments or apply a generic direct/transfer multiplier.
A literature statement and its underlying deposited dataset have the same
experiment identity: they do not earn two contributions. Conflicting
representations require retained conflict/correction, not a silent maximum over
positive wording. This document defines no aggregation across different
experiments or axes.

## A105 — experimental molecular activity

This axis asks what molecule was converted, transported or bound by the actual
preparation, and what the experiment distinguishes. It includes experiments on
identified close homologs when their correspondence to the target is retained.

| Proposed score | Required observed evidence |
| --- | --- |
| unknown / null | Actual assayed subject, operative assay, required input/output identity or necessary claim-specific controls are unavailable; no target correspondence is available for a transferred claim. |
| 0.00, non-discriminating | A competent measurement was made, but its endpoint does not distinguish the candidate effect from the explicit alternative being assessed. This is not an assertion of no activity. |
| 0.25 | A preparation-dependent proxy or binding signal is reproducible under stated controls, but identified productive conversion/transport or the claimed specificity remains unestablished. The returned claim must stay at that proxy/binding level. |
| 0.50 | The actual input and molecular endpoint are identified and competence/background controls attribute the tested effect to the preparation. Native activity/affinity measurements and conditions are retained. This establishes tested capacity, not native physiological responsibility or exclusive specificity. |
| 0.75 | The 0.50 conditions hold and a matched input/partner/alternative comparison distinguishes the particular substrate, reaction, binding or transport claim from its stated competing explanation. |
| 1.00 | The 0.75 conditions hold and an independent measurement principle authenticates the claimed molecular endpoint or productive effect, with the same preparation/conditions and relevant control relationship preserved. Orthogonal validation improves this experiment's grade; it is not another independent experiment. |

The opposing route assigns 0.50 for a competent molecular exclusion, 0.75 when
the exclusion is bounded by the actual specificity/condition comparison, and
1.00 when an orthogonal endpoint test confirms that bounded exclusion. Assay failure,
missing partner, insolubility and untested substrates are unknown. A native
specificity ratio is retained with its actual substrate panel; it is not a claim
about every untested substrate.

Examples from preserved cases:

- **QueF:** HPLC and proton-NMR correspondence to authentic preQ1 can satisfy
  endpoint authentication. NADPH loss alone cannot receive that grade.
- **YadB:** binding to both Q-containing and Q-lacking tRNA supports binding;
  the matched glutamylation difference bears on productive substrate specificity.
  A binding-only entry cannot receive the transformation-specific 0.75/1.00 score.
- **Hypothetical formal fixture:** a controlled assay identifies product P but
  tests no alternative substrate: score 0.50. Adding a matched alternative test
  that distinguishes the claimed specificity raises it to 0.75. Adding an
  orthogonal product-identity measurement permits 1.00. Changing the reported
  rate from 2 to 20 in the same units does not by itself change any of these grades.

## A106 — experimental contribution by perturbation/restoration

This axis scores evidence that the protein contributes to a specified output,
including perturbation knowledge from close homologs. A phenotype, molecular
activity and native responsibility remain different claims.

| Proposed score | Required observed evidence |
| --- | --- |
| unknown / null | The actual perturbation, construct/background, operative readout, matched control or required homolog correspondence is unavailable. |
| 0.00, non-discriminating | A competent perturbation comparison does not distinguish the claimed contribution from the specified competing explanation. A silent single loss does not establish dispensability under every condition. |
| 0.25 | A validated perturbation is associated with a repeatable specified endpoint change under matched conditions, but a relevant general defect, abundance, stability, localization or background explanation remains unresolved. |
| 0.50 | The perturbation/control comparison establishes the stated bounded contribution and a suitable restoration or independent perturbation comparison ties that effect to the tested component. Native endpoint/effect measurements and time/condition scope are retained. Rescue alone does not identify the molecular route. |
| 0.75 | The 0.50 conditions hold and selective perturbation/property-dissociation evidence separates the proposed role from the relevant abundance, localization, bypass or compensation explanation. |
| 1.00 | The 0.75 conditions hold and a second measurement principle or complementary selective intervention corroborates the same contribution while retaining the alternative-control relationships. Connected readouts of one restoration remain one experiment. |

The opposing route assigns 0.50 for a validated perturbation with a competent
claim-matched exclusion, 0.75 when efficacy, endpoint sensitivity and relevant
masking alternatives are controlled, and 1.00 when the orthogonal/complementary
test confirms that exclusion. It requires conditions and detection limits. Failure to
restore in an unvalidated heterologous expression setting remains unknown.
A larger growth defect, more colonies or a higher reporter signal does not
independently increase the grade: these are native effect quantities whose
interpretation depends on the actual contrast.

Examples from preserved cases:

- **EnvC:** stable, septally localized variants that lose separation and AmiB
  activation distinguish activation from a simple abundance/localization defect.
- **TsaE:** retained ATPase activity with lost efficient repeated t6A production
  supports a coupling distinction. ATPase magnitude cannot substitute for the
  repeated-output observation.
- **YabA:** complementary defective variants restoring foci and initiation control
  provide a selective restoration comparison. Foci and DNA-content readouts of
  that repair are connected observations, not two independent restorations.
- **Hypothetical formal fixture:** a knockout changes growth and restoration
  reverses the change: score 0.50 for the bounded contribution. If an expression
  defect could explain it, the 0.75 condition is not met. A matched selective
  variant retaining expression/localization while losing the proposed coupling
  permits 0.75. No claim about a purified molecular reaction follows automatically.

## A111 — experimental structural evidence through homologs

This axis concerns an experimentally constrained ligand, metal, contact or
assembly state, with a mapped correspondence to the target. A102 scores
structural homology/comparison; A111 scores what the actual experimentally
studied homolog structure establishes. Wholly predicted/docked/simulated models
do not become experimental entries on this axis.

| Proposed score | Required observed evidence |
| --- | --- |
| unknown / null | Experimental origin, studied construct, relevant structure/state, ligand/partner assignment or target correspondence is unavailable. |
| 0.00, non-discriminating | A competent structural observation does not distinguish the claimed ligand/contact/architecture alternative. A compatible docking pose is not an observed occupied state. |
| 0.25 | An experimentally constrained model places relevant density/contact/architecture, but the particular ligand/state assignment or claim-relevant interpretation remains ambiguous. Preserve it as an ambiguous structural observation. |
| 0.50 | The experimental/model record identifies the relevant ligand, metal, contact or architecture with its source-reported validation limits, and the actual correspondence maps that feature to the target. This is physical-state evidence, not activity, affinity or necessity. |
| 0.75 | The 0.50 conditions hold and an experimentally observed alternative state, substrate/partner contrast or matched site comparison distinguishes the stated structural claim from its explicit competing explanation. |
| 1.00 | The 0.75 conditions hold and orthogonal chemical/state identification or a selective functional comparison independently tests the specific structural interpretation. Preserve which facts come from the structure and which from the functional test; neither is silently reclassified as target experimentation. |

The opposing route assigns 0.50 for a validated incompatible structural feature,
0.75 when the incompatible alternative is positively identified rather than
inferred from missing density, and 1.00 with a relevant orthogonal/selective test.

Native resolution, occupancy and contact distances are retained when actually
available. Their extractors are currently unbound in this workflow, so the host
cannot fabricate those fields. A lower resolution number, shorter distance or
larger occupancy never increases this grade by itself. A model-derived contact
and a distance calculated from it are one dependent structural observation.

Examples from preserved cases:

- **TT1927b:** modeled octaprenyl pyrophosphate plus a C40 mass constrains ligand
  identity but does not establish exclusive physiological ligand or function.
- **FrsA:** density modeled as hexanoate remained an unknown ligand. This cannot
  receive the identified-state 0.50 grade for a definite hexanoate assignment.
- **Cas2:** contact geometry and selective contact-site mutant effects are
  connected but different observations. R77's tolerated contact-site change
  prevents treating every modeled contact as necessary.
- **Hypothetical formal fixture:** an experimentally constrained homolog has
  identified ligand L and a mapped target site: score 0.50 for that structural
  state. A matched alternative-state comparison can permit 0.75. A shorter
  calculated contact distance alone changes no grade. If L is only a fitted
  unidentified density, the identified-state score is unavailable.

## Implementation boundary

The source entries retain their original case observations and inspection limits.
The numeric rules above are proposals for review and are represented in each
entry's `scoring_rubric`. The deterministic evaluator executes those descriptors.
There is no adopted aggregation across experiments, routes or axes; output says
`annotation_aggregate_status=not_defined_by_per_axis_rubric`. This work does not
adopt a caller policy, alter old scores or create new observations.
