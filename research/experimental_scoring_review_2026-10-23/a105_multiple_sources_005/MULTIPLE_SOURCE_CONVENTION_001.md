# A105: combining different assayed homologs with different correspondence

2026-10-23. **Unadopted arithmetic convention for discussion.** Every filled
number below is SYNTHETIC. No paper or paper-specific packet was read. No
production scorer, reader, prompt, run or previous record was changed. This
supplies one missing combination, not a completed A105 sheet or a calibrated
target-function score. Authority and input reads are listed separately.

The smallest proposed combination is the **arithmetic mean of the signed
correspondence-adjusted indexes over a declared set of distinct assayed
molecules/states**. It preserves the single-source convention exactly. It has
the limited meaning of an average over that source set; it does not measure
the amount of independent target evidence. Its substantial limitations below
are part of the proposal, not a claim that averaging solves transfer.

## Existing calculations remain the input

The particular target statement may emerge from investigating supplied sequence,
file contents or snippets; a candidate name is not a prerequisite. For this
combination it must then have one specified molecular endpoint, direction,
boundary and condition scope. Conversion, transport and binding are A105.
Perturbation/restoration remains A106.

For each distinct source molecule/state i:

1. Identify original experimental observations, independently of their paper,
   table, figure, repository or later review representations.
2. Combine compatible observations of that source's SAME parameter through the
   existing joint likelihood, retaining shared calibration/control/preparation
   terms. Maximize after combining. Multiple assays of the same molecule are
   not multiple homolog votes.
3. Preserve the corrected effect, units, uncertainty, likelihood model,
   source-scoped S_i, and B_i = tanh(S_i/2). Experimental comparability and effect
   isolation remain different correction/uncertainty cells. Their already-used
   corrections do not become another reliability multiplier.
4. Preserve each actual correspondence measurement r_ij and its declared
   numerical normalization and family weight w_ij. For the elected uncalibrated
   route use R_i = sum_j(w_ij r_ij)/sum_j(w_ij) on its explicitly stated observed
   basis, and D_i = R_i B_i. Preserve missing-family bounds and coverage.

S_i retains its source likelihood meaning; B_i retains its normalized source
fit meaning. D_i has conventional-score meaning. Neither the combination below
nor a high correspondence creates a measured target rate or a target likelihood.
Measured endpoint-transfer h, when available, uses its existing joint target
model instead; it is not counted again as an independent D_i confirmation.

## Two candidate arithmetic combinations, and the proposed choice

For N distinct source molecule/state blocks, all relating the same scoped
target statement through the elected uncalibrated convention:

```
Candidate M: M = (D_1 + ... + D_N)/N.

Candidate K: P = product_i(1 + D_i); Q = product_i(1 - D_i)
             K = (P-Q)/(P+Q).
             For two sources: K = (D_1+D_2)/(1+D_1*D_2).
```

Both are bounded signed CONVENTIONS, not probabilities or likelihoods. Equal
source coefficients 1/N in M are an exposed design choice, not empirical
reliability weights. K is a possible cumulative score operation, not legitimate
independent likelihood multiplication. Its algebraic relation to inverse
hyperbolic tangents does not recover a target S from R_i B_i.

**Propose M for the narrow descriptive purpose.** It is linear, preserves the
single-source D, respects sign reversal, keeps every represented opposing
source, and does not amplify identical D values merely because more sources
have them. Cross-source independence is unnecessary to calculate this
descriptive average. It is required, or must be replaced by a supplied
dependence model, for any claim about repeated independent evidence or
uncertainty reduction. K adds strong source-count amplification without those
inputs, so it is not the proposed default.

If the separately unadopted positive-support coordinate policy F is elected,
the handoff is c_A105 = max(0,M), applied AFTER combination. Unknown M stays
unknown. Negative M and all native values remain in the sheet. This does not
adopt F, change the retained hypervolume, define ten-axis weights, or complete
the nullable runtime handoff. No positive source is selected by a maximum.

## Fully specified synthetic calculation

The molecular statement is preference for substrate X over Y in catalytic
efficiency under the declared common assay conditions. For each source i,
theta_i = log((kcat/Km)_X/(kcat/Km)_Y). The natural boundary is zero. Different
source molecules have different theta_i; no common molecular effect across
homologs is assumed.

Each assay below reports a corrected estimate y of theta_i with a known normal
sampling variance 1 in squared log-ratio units. These are complete synthetic
observation-model inputs, not confidence intervals reconstructed from a paper.
Preparation and assay identities are distinct. The reported ratio is exp(y).
Source comparability, attribution and calibration are assumed accounted for in
these synthetic corrected estimates; no further unknown weakness is assumed
away for a real assay by this example.

| Original observation | Actual assayed source/state | y | Known variance | Reported ratio |
|---|---|---:|---:|---:|
| h1-preparation-1 | H1, stated purified state | +2 | 1 | 7.389056099 |
| h1-preparation-2 | Same H1/state, independent preparation | +2 | 1 | 7.389056099 |
| h2-preparation-1 | Different homolog H2, stated purified state | -2 | 1 | 0.135335283 |

For each source's common effect, the two known-normal half-line fits give
S_i = sign(y_pooled)*y_pooled^2/(2 V_pooled). H1's independent assays first give
y_pooled=2, V_pooled=1/2, S_1=4, B_1=0.964027580. H2 gives S_2=-2 and
B_2=-0.761594156. No assay-level B values were averaged.

The supplied synthetic target and both sources are complete molecules. Use
the existing correspondence conventions with all FIVE applicable families
given weight 1. All numerators and denominators are provided:

| Correspondence component | H1-to-target operands and calculation | r_1j | H2-to-target operands and calculation | r_2j |
|---|---|---:|---|---:|
| Sequence | Valid local pair raw score 240; source/target self scores 300 each; 2*240/600 | 0.8 | Pair score 90; self scores 300 each; 2*90/600 | 0.3 |
| Structure | Native TM scores 0.92 and 0.90; minimum | 0.9 | Native TM scores 0.45 and 0.40; minimum | 0.4 |
| Defined functional site | 7 exact matches among 10 predefined, fully observed mapped sites | 0.7 | 2/10, fully observed mapped sites | 0.2 |
| Declared evolutionary placement | 60 supporting among 100 eligible tree replicates | 0.6 | 10/100 | 0.1 |
| Declared condition descriptor | Source and target 25 degrees C; variance scale 100 degrees C squared; exp[-(25-25)^2/(2*100)] | 1.0 | Same operands | 1.0 |
| Equal-family arithmetic mean | (0.8+0.9+0.7+0.6+1)/5 | **0.8** | (0.3+0.4+0.2+0.1+1)/5 | **0.4** |

The valid sequence-score assumptions are those of the inspected correspondence
proposal. The temperature index covers only that declared descriptor; it does
not assert complete experimental-system identity. The same declared scopes and
component definitions apply to both sources. No native comparison measurement
is treated as an independent experiment or fitted functional probability.

```
D_1 = 0.8 * 0.9640275800758169 = +0.7712220640606535
D_2 = 0.4 * (-0.7615941559557649) = -0.30463766238230594
M = (D_1+D_2)/2 = +0.2332922008391738
K = (D_1+D_2)/(1+D_1*D_2) = +0.6098690379571442
```

Under F, this example's conventional A105 coordinate would be 0.233292201.
Clipping each D before averaging would incorrectly give 0.385611032 and remove
the measured opposition. Reversing the SAME directional statement reverses M;
F would then be zero while M=-0.233292201 remains recorded.

| Synthetic variation | M | K | Consequence |
|---|---:|---:|---|
| Above opposing source effects | 0.233292201 | 0.609869038 | Unequal R and unequal native strength remain explicit |
| Change H2's observed y from -2 to +2; all else unchanged | 0.537929863 | 0.871181485 | Both formulas reflect the actual direction change |
| Only H1's first preparation was available, with H2 unchanged | 0.152318831 | 0.374063259 | A genuine second H1 assay improves its joint source calculation before cross-source averaging |
| Any D and exactly -D | 0 | 0 | Cancellation does not mean either source measured zero |
| Ten distinct sources each with D=0.1 | 0.1 | 0.762998937 | K can turn many weak correspondences into a large index |
| Ten distinct H1-like sources, each with its own stated two-assay model and R=0.8, plus the original H2 | 0.673416634 | 0.999999995 | Dense evolutionary sampling changes both; K almost saturates |

The D=0.1 row can be generated exactly by each source having one known-normal
estimate y=sqrt(2*log(3)), variance 1, hence B=0.5, and every one of the five
declared correspondence components equal to 0.2. The arithmetic artifact
provides their actual component operands. It does not assume these ten source
relationships are independent.

## Identity, shared measurements and evolutionary dependence

**Repeated representation is not new data.** Returning h1-preparation-1 again,
or publishing it in a second paper, leaves the three original observations,
two source blocks, their S/B/R/D and M unchanged. A paper containing both H1
preparations is not one experiment; two papers reproducing one preparation are
not two experiments. Equal measured numbers do not establish duplication.
Conflicting representations of one original measurement remain a representation
conflict; they are not averaged as biological disagreement. If overlap cannot
be resolved, show the conditional distinct/reused interpretations, not an
unqualified source count.

**A known shared calibration changes the within-source joint fit.** Replace
the original independence model by

```
y_ij = theta_i + U + e_ij,
U ~ Normal(0,0.75), e_ij ~ Normal(0,0.25), all e independent of U and each other.
```

The marginal variance of every y remains 1; covariance of any two is 0.75.
H1's mean variance becomes 0.75+0.25/2=0.875, not 0.5. H1 now has
S_1=16/7=2.285714286, B_1=0.815373942, D_1=0.652299154. H2's marginal source
calculation remains S_2=-2. The descriptive M becomes **0.173830746**.
This uses a fully specified SYNTHETIC covariance, not a standard discount.
If the calibration is instead a fixed unknown offset, it needs its actual
calibration observations/profile; the stated random-normal model is not a
license to supply that missing information.

Covariance between H1's mean and H2's observation is also 0.75. It does not
change the arithmetic point M conditional on the resulting marginal B values.
It does change uncertainty about M as a repeated-measurement statistic. With
fixed R and the stated known variances, first-order propagation gives

```
g_i = dM/dy_i = R_i*(1-B_i^2)*abs(y_i)/(2*N*V_i)
Var_delta(M) = sum_i(g_i^2 V_i) + 2*sum_(i<j)(g_i g_j Cov(y_i,y_j)).
```

Here g=(0.153218438,0.083994868); omitting the cross-source covariance gives
0.027596542, including it gives **0.046900885**. These are conditional delta
approximations for the score's sampling variation, not uncertainty in the
target's actual function. Uncertain R operands require their own derivatives
and joint covariance too. No statistical interval is asserted from these two
synthetic sources. Missing covariance is not zero.

**Evolutionary correlation is a different unknown.** Native assay errors can
be independent while homologs share the same unresolved functional difference
from the target. R and tree placement do not identify covariance of that
functional transfer. The ten-H1-like example shows the density problem even
for M: a cluster with ten members contributes ten terms. Known common ancestry
does not by itself supply a correlation coefficient or an effective sample
size. A declared cluster map permits leave-one-cluster-out sensitivity: retaining
only the positive cluster gives 0.771222064; retaining only the negative cluster
gives -0.304637662. These are alternate roster calculations, not confidence
bounds or replacement point scores.

No fixed within-cluster discount, selected clustering cutoff, one-source maximum
or independence gate is supplied. A statistically cumulative target inference
would need a shared calibration and source-to-target residual model, its
covariance inputs and an identifiable endpoint relation. M can still be printed
as the declared set's descriptive index while those inputs remain unknown; it
cannot be advertised as independent corroboration.

## Missing information, scopes and nondetections

The declared complete source roster contains both H1 and H2. Bounds below are
identification/sensitivity bounds, not probability intervals; endpoints are not
imputed values. For rectangular allowed D_i intervals, the exact image under M
is [sum lower_i/N, sum upper_i/N]. With constrained dependence between missing
operands, optimize over that actual joint allowed set; the rectangular result
is only an outer bound. It never supplies an automatic midpoint score.

| Missing input in the original example | Retained facts | Complete-roster M |
|---|---|---|
| All H2 correspondence unknown | B_2=-0.761594156; R_2 in [0,1], so D_2 in [-0.761594156,0] | Point unknown; possible range [0.004813954,0.385611032] |
| H2's assay uncertainty/model unavailable | Observed native effect -2 and R_2=0.4; B_2 not fabricated | Point unknown; domain-only outer range [0.185611032,0.585611032] from B_2 in [-1,1] |
| H1 evolutionary component unknown; other four retained | R_available=3.4/4=0.85; hypothetical full R_1 in [0.68,0.88] | Elected available-family point 0.257392890; hypothetical full-family range [0.175450546,0.271853304] |

The second row's broad B range assumes only the index domain; it is not a
claim that a negative native estimate establishes positive evidence. An actual
identified likelihood family and permitted variance range could sharpen it.
Neither SD, SE nor df is invented. A missing corresponding term cannot simply
be dropped while retaining a label of complete-roster M. The known-source
subset value 0.771222064 remains a valid explicitly conditional calculation.
The third row illustrates why a newly missing component can INCREASE an
available-component point: 0.6 was removed from an average of 0.8. Report the
basis change and full-family bounds instead of calling that new evidence.

**Partial target snippets:** suppose only a 50-residue target snippet is known.
The source is 200 residues, with the compared source span also 50. Compatible
local raw scores 90, 100, 100 give snippet r_sequence=0.9. Three of ten declared
source sites fall within the available material and all three match: the
observed-site fraction is 1, coverage is 3/10, and the full-site fraction is
bounded by [0.3,1]. Full target length, full sequence self score and the other
sites remain unknown. A separately labeled two-family snippet calculation gives
R_snippet=(0.9+1)/2=0.95 and H1's D_snippet=0.915826201. This is support
conditional on the observed region; it is not a whole-molecule R of 0.95.
It neither invents the rest of the target nor blocks investigation from snippets.
Full-length and snippet R values must not be mixed in one average as if their
scope and denominators were identical. Repeated or overlapping supplied snippets
also do not become extra sources.

**Different endpoints:** affinity, transport rate, catalytic preference and
product identification do not become commensurate just because B or D is
dimensionless. They remain separate scoped statement calculations unless an
explicit compound claim and joint measurement relation has been supplied. A
binding result is not an activation result. Different source conditions likewise
require the stated correction/scope relation, not an average of unrelated effects.

**Nondetection:** preserve the actual censored-observation likelihood and
detection limit in the source joint model. A zero source presence-profile
improvement from a stand-alone nondetection is not a measured zero rate or
contrary specificity result. A missing detection limit supplies no substitute
point. This cross-source convention does not repair missing source likelihood
operands or broaden a measured statement.

## Exact cells, unresolved choices and failures

| Cell | Meaning and deterministic population |
|---|---|
| `source_effect`, `source_covariance`, `source_profile_S`, `source_B` | Existing source calculation after original-observation deduplication and compatible within-source fitting |
| `correspondence_components`, `family_weights`, `observed_basis`, `R_available`, `R_full_bounds` | Existing decomposed relevance convention; same actual measurement cannot be counted twice as two independent modalities |
| `source_D` | R_available * source_B, tagged conventional; native S/B unchanged |
| `distinct_source_count`, `source_set`, `source_state_scope` | Actual declared source roster and pooling units; count is the mean's denominator, not number of publications |
| `combined_D_mean` | sum(source_D)/distinct_source_count; unknown for a required missing term unless an explicitly conditional subset is named |
| `combined_D_bounds` | Image of the stated allowed operand set; never a substituted midpoint |
| `dependence_operands`, `cluster_map`, `conditional_assumptions` | Supplied shared errors, their covariance or unresolved status; no fixed discounts |
| `coordinate_value` | Only if F is elected, positive part of combined_D_mean after combination; unknown stays unknown |

These are sheet/reader-interface definitions, not implemented readers. The
reader supplies actual operands and identities; it does not select favorable
sources, weights, endpoints or a hidden uncertainty model.

M has material failures even though it is a valid deterministic convention:

- A source with a smaller positive D can lower a previously positive mean.
  Identical independent homolog confirmations do not raise it. It is not an
  accumulated-evidence-strength measure.
- Adding a known D=0 source changes the denominator and dilutes the mean. With
  H1 alone M=0.771222064; adding a source whose R is exactly zero gives
  M=0.385611032. This is dilution of an average, not opposing evidence. A desired
  rule that zero-relevance sources have no effect is therefore NOT met by M.
- Dense sampling of one evolutionary cluster changes M. Neither equal source
  weighting nor a cluster partition is a biological calibration. Unknown
  dependence is exposed, not solved.
- Corpus expansion, endpoint selection, missing-family changes and inconsistent
  molecule/state grouping can change the mean without new target information.
  The source roster and scope must accompany every value; no favorable subset
  or source-count claim is inferred from a search result list.
- K has the stronger accumulation problem demonstrated above. At simultaneous
  exact +1 and -1 inputs its product expression is 0/0; finite native S and
  unrounded operands avoid mistaking floating-point saturation for certainty,
  but do not fix its scientific interpretation.

Thus the exact choice is whether an average correspondence-adjusted support
index over the declared source set is the intended annotation operand. If the
required meaning is cumulative independent support or invariance to adding
zero-relevance sources, this proposal does not meet it. No statistical model is
smuggled in to claim otherwise. A user decision on M and the separate F policy
is still needed before adoption; dependence-sensitive cumulative target scoring
requires additional modeled relationships and inputs, not an arbitrary discount.

`check_multiple_source_arithmetic_001.py` was executed with Python 3's standard
library. Its JSON records the specified operands, duplicate/sign/interval checks,
shared-covariance calculations and both candidate combinations. These checks
establish arithmetic under the stated synthetic assumptions only.
