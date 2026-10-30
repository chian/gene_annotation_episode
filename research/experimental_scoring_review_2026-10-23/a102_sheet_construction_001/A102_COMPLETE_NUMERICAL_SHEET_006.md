# A102 current numerical scoring sheet — complete research proposal

This is the current entry point for the additive combination of draft 002 and
proposal 005, including 005's corrected synthetic TM inputs. Earlier records
remain unchanged. A105 was delivered first. This completes a proposed numerical
sheet for research review, not an approved policy, production reader/scorer,
prompt change, target annotation or new structural comparison job.

## What the numerical result means

One persistent candidate function and its actual molecular scope receive one
structural-correspondence contribution. Investigation can start from sequence,
selected file material, coordinates or snippets; a candidate may emerge later.
Comparison evidence, its missing operands and its numerical output remain
separate from the investigation prompt and the targeted population functions.

The result describes the recorded structural comparisons and relevant local
geometry. It is not an assay of activity or a calibrated function probability.
Its scope cannot change from a matched accessory domain to an entire catalytic
protein without changing the actual declared question and denominators.

## Native and derived numerical cells

Every cell carries value/null, units, origin, actual operand/source identity
and any supplied uncertainty or missing-input bounds. The complete native
record and residue/atom-map schema are retained from draft 002 sections 2–3.

| Cell | Exact populated operands and calculation | Units / interpretation |
|---|---|---|
| Target/reference lengths | Declared functional scope lengths Lt,Lr, including known residues lacking coordinates | Positive residue counts; not silently replaced by observed-model lengths |
| Native comparison | Unique mapped residue count n; RMSD r and its actual atom denominator; native bidirectional TM values, maps and transforms | Counts, Angstrom, native dimensionless TM; metrics from different maps stay separate |
| Symmetric coverage | C=2n/(Lt+Lr) | [0,1]; one extent factor |
| RMSD base | B=C/[1+(r/2 Angstrom)^2] | [0,1]; 2 Angstrom scale is proposed |
| TM base | B=min(TM_target,TM_reference) for the same map/transform and respective scope normalization | [0,1]; no second coverage multiplier |
| Relevant feature geometry | For K distinct physical anchors, f_k=1/[1+(d_k/1 Angstrom)^2]; F=sum(f_k)/K | Actual mapped anchor distances; equal weights and 1 Angstrom scale proposed |
| Established absence versus missing feature | Known incompatible/absent specified feature f=0; unresolved coordinate/map/chemistry f in [0,1], point null | Missing density is not an observed deletion |
| Demonstrated necessary predicates | v=1 met, v=0 contradicted, v in [0,1] unresolved; V=product(v) | Logical conjunction for source-established necessity; conservation alone does not establish it |
| Reference contribution | E=B*F*V | [0,1]; a neutral V=1 when no necessity predicate is established is not a measured positive |
| Per-metric support/opposition | S_t=max(supporting E); O_t=max(incompatible received E union {0}) | Declared same-scope scientific relationship; names alone cannot establish incompatibility |
| Mixed signed margin | Z=sum_t pi_t*(S_t-O_t) | [-1,1]; preserves negative metric contributions |
| Candidate A102 contribution | max(0,Z) | One positive projection after combining signed metrics |

The fixed profiles are RMSD-only (weight 1), TM-only (weight 1), or equal
RMSD/TM (weights 1/2 each). The profile is declared independently of its score.
An included but unavailable metric remains missing; a separately displayed
single-metric calculation does not fill it. RMSD and TM are different index
conventions; the equal composite is proposed, not a fitted equivalence.

Native Z scores, resolution, R-work/R-free, pLDDT and PAE retain their actual
meanings. They are not extra multiplicative proofs or generic reliability
weights. DALI RMSD/count can fill the RMSD route; a Z-only excerpt cannot
invent the missing geometry. Aggregate RMSD cannot reconstruct native TM.

## Complete synthetic sheet

All inputs in this table are invented for checking arithmetic. Each scope
has 100 residues. Every metric retains its own specified map and feature
geometry; no native program or physical coordinate determination is claimed.

| Component | Supporting reference | Incompatible reference |
|---|---:|---:|
| RMSD paired count n | 90 | 80 |
| RMSD r, Angstrom | 1 | 2 |
| C | .9 | .8 |
| RMSD base B | .9/(1+.25)=.72 | .8/(1+1)=.40 |
| Four feature distances, Angstrom | 0,1,1,2 | 1,2,2,3 |
| F | (1+.5+.5+.2)/4=.55 | (.5+.2+.2+.1)/4=.25 |
| V | 1, no established necessity predicate | 1, same neutral convention |
| RMSD reference E | .396 | .100 |
| Corrected same-length TM pair | .7/.7 | .5/.5 |
| TM reference E | .7*.55=.385 | .5*.25=.125 |

RMSD margin=.296; TM margin=.260; equal mixed contribution
**(.296+.260)/2=.278**. The corrected .7/.7 and .5/.5 pairs respect equal
normalization lengths. Earlier inconsistent .8/.7 and .6/.5 pairs remain
identified as draft errors in additive correction 005, not live inputs.

If TM support/opposition are instead .2/.6, its signed margin is -.4. The
mixed result is max(0,(.296-.4)/2)=0. Clipping TM first would incorrectly
retain .148 under this declared formula. Duplicate reports and weaker
supporting comparisons do not increase the maxima.

## Contrasting populated published components

These values retain earlier documented primary/source inspection. They are
different proteins, not a supporting/opposing panel for one candidate.

| Published comparison | Reported native values and stated denominators | C | Proposed B |
|---|---|---:|---:|
| AF2372–MJ0109 | n=209, r=1.5 Angstrom, Lt=Lr=252; exact RMSD atom choice unresolved | 209/252=.829365079365 | .530793650794 |
| MJ0226–histidyl-tRNA synthetase | n=76 C-alpha pairs, r=2.7 Angstrom, whole-deposit lengths 193/421 | 152/614=.247557003257 | .087708415680 |
| MJ0226–glycyl-tRNA synthetase | n=75 C-alpha pairs, r=3.1 Angstrom, whole-deposit lengths 193/505 | 150/698=.214899713467 | .063159357375 |

Their function-specific F and comparison panels remain missing, so E is bounded
by [0,B] and the candidate point is unknown. The whole-polymer denominator in
the two partial MJ comparisons does not establish coverage of the actual
matched domain. No missing exact map or feature measurement is fabricated.

Sources: Stieglitz et al., DOI 10.1074/jbc.M201042200; Hwang et al., DOI
10.1038/10745; recorded RCSB polymer metadata for 1B78/1ADJ/1ATI. Draft 002
section 9 is the complete source-to-cell table; the parent conversions 001
and 003 and coverage correction 002 preserve the precise inspection limits.
Official TM-score documentation/implementation supplies native normalization;
the proposed 2/1 Angstrom scales and pooling are not attributed to those papers.

## Comparability, isolation, uncertainty and missingness

Construct/state/assembly differences must be represented by actual matching
comparisons or justified coordinate bounds, not an overall applicability grade.
For fixed-map RMSD perturbation bounds ut,ur, r lies within
[max(0,r-ut-ur),r+ut+ur]. The decreasing kernel propagates reversed endpoints.
Apply separately justified bounds to actual feature distances. Unknown error
is not zero error; SD is not a hard bound without its numerical model.

The measured geometry isolates correspondence between the selected models;
it does not isolate biochemical activity. A105/A106/A111 findings can establish
which structural question matters without becoming extra A102 observations.

For K anchors, known kernel sum H and u unresolved anchors, F is in
[H/K,(H+u)/K]. Multiply nonnegative B/F/V intervals. For each metric, support
and opposition bounds are maxima of the corresponding endpoint bounds. Then
Z_low=sum(pi*(S_low-O_high)), Z_high=sum(pi*(S_high-O_low)); apply the positive
part to both. Shared constraints remain shared; rectangular results are outer
bounds, not probability intervals. Supplied finite model/assignment variants
can be enumerated through the same formula to narrow the range.

For the RMSD fixture, an unresolved last supporting anchor gives F=[.5,.75]
and contribution [.26,.44], point null. Established absence instead gives .26.
With a genuinely supplied .2 Angstrom bound on all relevant distances, the
RMSD-only example gives [.1910171542,.4001224025]; these synthetic bounds do not
supply uncertainties for the published cases.

No received incompatible comparison means O=0 for the recorded-evidence
index, not proof that alternatives were excluded. Unsearched alternatives
have separate sensitivity [0,current contribution]. An INCLUDED missing TM
opponent in the complete fixture instead gives mixed bounds [0,.3405], and
an entire included missing TM channel gives [0,.648], both with null points.
An empty supporting population or unknown required scope remains unknown.

## Shared evidence, replication and alternative representations

Metrics from one alignment, duplicate deposits/reports, symmetry copies and
shared models retain their actual dependencies. Multiple supporting references
use maxima, not citation or replication counts. Independent determinations can
populate comparison ranges and sample SD with its actual n-1 denominator;
there is no invented precision from counting atoms as experiments.

Use a source-designated primary representation of one underlying comparison.
Without one, retain the admissible variants and their range, with a null point;
do not choose the most favorable. Distinct physical states retain their scopes.
An unsuccessful search is not RMSD infinity or proof of universal absence.
Only a genuine native reporting guarantee supplies a quantitative nondetection
bound; missing data/access failures do not.

## Exact separate population responsibilities

All functions remain UNIMPLEMENTED. Draft 002 section 10 supplies their full
typed native/coordinate schema; proposal 005 section 5 adds the exact mixed
profile, membership, availability and necessity fields. The current obligations
are summarized here without adding a new reader or prompt.

| Responsibility | Exact input cells | Exact numerical output |
|---|---|---|
| Reported/native comparison reader | Reported metric/count/units; software/schema; original residue/atom map; transforms and normalization lengths | n, RMSD and atom denominator, TM pair, native Z, actual uncertainty and field-specific nulls |
| Scope/metadata reader | Supplied material/construct, selected chain/model/state and scoped sequence | Lt,Lr and separately observed lengths; actual scope/map relationships |
| Feature reader | Physical anchor definitions/equivalences, source roles, coordinates and comparison transform | K, distances, known-zero versus unresolved features, source-established necessity predicates |
| Component calculator | Native cells, profile, proposed scales, feature/necessity cells, justified bounds | C,B,F,V,E and separate nominal/missingness/measurement outputs |
| Panel calculator | Current scoped reference contributions, guaranteed/possible supporting/incompatible membership, dependencies/variants and availability | Per-metric S,O, signed margins and bounds; no duplicated representation or scope borrowing |
| Composite calculator | Named profile, exact weights, metric panels and shared constraints | Z, max(0,Z), bounds, recorded-opposition qualifier and separate open-alternative sensitivity |

Numeric coefficients have proposed origin; observations retain their source
origin. Missing fields preserve usable components and return specific causes.
No population function launches comparisons, constructs episode prompts or
selects continuation. Those are different responsibilities.

## Completion evidence and remaining judgments

The parent read the complete draft 002, current additive proposal 005 and its
corrections, prior formula review, and exact IO. Prior source conversions and
their arithmetic receipts remain preserved. The earlier independent 15-check
mixed-profile receipt covers the current corrected example, missing channels,
negative metrics, shared necessity and duplicate invariance. No unchanged test
grid or primary source was rerun merely to increase activity.

All seven numerical research criteria have concrete outputs here and in the
specified full schemas: defined cells/uncertainty, complete formulas,
contrasting published cells and a complete checked fixture, dependency and
nondetection treatment, source trace, targeted population fields, and printed
formulas/examples/choices incorporating known corrections. No essential
mixed-profile operation is left undefined. The formula remains proposed:
the 2/1 Angstrom scales, equal feature/metric weights, maxima and unit opposing
subtraction require scientific judgment, not fabricated empirical calibration.
Actual missing native observations remain missing with defined arithmetic.
