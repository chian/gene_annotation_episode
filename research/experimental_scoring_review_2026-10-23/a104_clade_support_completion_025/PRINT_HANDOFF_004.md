# Print-ready A104 handoff

The current proposal measures family-tree agreement with the **organismal**
tree and target placement in a function-conserving reference clade. It requires
no incompatible-function group. Broad comparisons for frequently transferred
families are not applicable; a very local comparison needs its actual scientific
scope. Known mixed functions limit the functional resolution, and distant
queries give little positive information. Exact current user wording remains
preserved in `CURRENT_TWO_CONDITION_PROPOSAL_002.md` and
`CURRENT_USER_STEERING_003.md`.

For a region, the proposed observed contribution is:

    A_observed = C_f * sum_z w_z * F_z * J_z * O_z

| Component | Actual operands and interpretation |
| --- | --- |
| F | Identical **resolved** rooted triplets or justified unrooted quartets, divided by all intended taxon subsets. Print discordant and unresolved/missing counts separately. Do not improve the score by dropping intended unmapped taxa. |
| J | Actual query attachment strictly inside a fixed query-pruned crown:1; stem/outside/resolved nonmonophyly:0; unresolved boundary:bounds. Sum actual native placement weights on those edges. |
| C_f | k/n unique reference members with observed f assignments, provided the known class set is homogeneous at the stated resolution. A known mixed precise-function clade gives0 precise support, regardless of majority. Unknown members are not verified matches. |
| O | Proposed distance attenuation min(1,b/d): d is query distance to its nearest characterized member; b is the median nearest-other distance among characterized members, on the same tree scale. One usable reference can leave b genuinely missing. |

C_f measures **observed association coverage**, not full-clade purity or function
probability. Full-clade purity is printed separately and may remain unknown;
its completion bounds can include zero even with positive observed association.
No exhaustive search for all other functions is imposed. A known multifunctional
member may fail the only-f-clade condition without contradicting the target's f
activity. A legitimate broader common function is a different explicit assertion,
not a higher score selected for the precise assertion.

All components share the same native tree/graft and reference scenarios. For
several necessary applicable regions, propose the minimum **within each actual
joint draw**, then native weighted averaging; take the conservative minimum
over included comparable analyses. If only marginal distributions are known,
the exact admissible-coupling minimum/maximum supplies bounds. Missing included
samples/requirements remain unknown; never-included function alternatives do
not become phantom missing observations.

The outlier ratio has explicit zero conventions: d=0 gives O=1, including b=0;
b=0,d>0 gives O=0; missing/censored values use their actual bounds with no epsilon.
These are exposed proposed conventions, not native method definitions. Zero
positive information is never automatically turned into opposing credit.

| Fully checked synthetic contrast | Result |
| --- | --- |
| Four placements with weights(.6,.2,.1,.1), F=(1,.75,.75,.25), J=(1,1,0,0), C_f=1 | .75, without any contrary functional reference |
| Same tree/placement weights, but only query pendant length grows so interior d rises from.3 to6 while b=.6 | .075; EDPL unchanged at46/325=.141538 |
| Known different-function reference outside the fixed crown | .75 unchanged |
| Known g or{f,g} member inside that crown | 0 precise f support; retain known function set |
| Matching five-tip tree, three-member crown, two characterized f and one unknown | observed2/3; full-clade completion[0,1] |
| Same clade later known mixed f/g, with a justified common broader h | precise f=0; separately stated h=1 |
| Only one of two references characterized, positive query distance and no b normalizer | null point, observed bounds[0,.375] |
| Four intended rooted taxa but organism tree supplies only one agreeing three-tip subset | native common-leaf1/1; F_supported=1/4, completion[.25,1] |
| Main region plus another necessary region scoring.4 in every same draw | whole candidate.32, not min(.75,.4)=.4 |
| Two required regions score(1,0) then(0,1) in two equal-weight joint draws | candidate0; only their marginals would give bounds[0,.5] |
| An included required region is unavailable | conditional candidate[0,.75], not dropped |
| Broad frequent-HGT scope | null/not_applicable, not zero |

Native metric sources are [tqDist](https://doi.org/10.1093/bioinformatics/btu157)
for triplet/quartet topology comparison and
[pplacer](https://doi.org/10.1186/1471-2105-11-538) for placement weights and
EDPL. EDPL measures dispersion among attachment locations and omits query
pendant distance; it is a diagnostic, not another multiplier of placement
uncertainty. The primary pplacer manuscript read was
<https://matsen.fhcrc.org/pplacer/pplacer.pdf>.

Published-case components are deliberately bounded:

* [Wege et al.2010](https://doi.org/10.1111/j.1365-313X.2010.04288.x) compares
  separately expressed AtCLCa WT and P160S. Ion preference changes while broader
  exchange remains supported; reported current-ratio means4.0/.90 give4.4444.
  The engineered mutant is not a second natural tree tip or a natural change-rate
  estimate. Complete F/J/O and clade coverage are unavailable.
* [Stockbridge et al.2012](https://doi.org/10.1073/pnas.1210896109) supplies eight
  characterized natural fluoride/proton-antiport homologs among29 screened:
  screened-panel coverage8/29=.275862. The full crown inventory and independent
  organismal tree are missing. Exact1:1 stoichiometry was measured for only1/8
  of the successful transport panel. Failed expression, unstable preparation
  and assay inactivity do not establish other-substrate functions.
* Worker029 independently inspected the TyrA source and returned a bounded
  source-listed two-of-five conserved-function example. Its strict canonical
  C_f and F/J/O remain null because identity and native-tree operands are
  unresolved. See that worker's `SOURCE_TO_CELLS_001.md` and
  `PRINTABLE_HANDOFF_001.md`; this worker did not reread its primary paper.

Earlier Hehemann/Smillie transfer material is inherited background, not a
positive vertical-concordance example or a way to repair F. Primary methods
sources do not supply experimentally known functions. Complete synthetic examples
demonstrate compilation without fabricating missing published tree scores.

The coherent current sheet is `A104_CURRENT_NUMERICAL_PROPOSAL_004.md`; exact
targeted, unimplemented reader fields are in `EXACT_READER_FIELDS_004.md`.
`arithmetic_checks_005.py` ran successfully and saved exact-fraction results,
256 grid checks and the contrasting fixtures in `arithmetic_results_005.json`.
No biological dataset, native phylogenetic program, target annotation, production
scorer, HPC work or permanent record was changed. The per-paper receipts record
actual full resets and one provisional-message ordering error with its withdrawal
and completed reassessment. No flawless-compliance claim is made.

Mathematical components and combination are defined; missing empirical operands
have explicit states/bounds. Published examples populate only what was measured.
Equal weighting, C_f, the distance transform/zero conventions and pooling are
proposals for judgment. Adoption, calibration and reader implementation are
separate from defining the arithmetic. No axis or overall-goal completion is
declared by this worker.
