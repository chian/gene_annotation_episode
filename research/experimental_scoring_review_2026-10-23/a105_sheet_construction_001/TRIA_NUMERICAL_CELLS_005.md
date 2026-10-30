# TriA numerical cells and their limits

Additive research conversion, 2026-10-23. Prior records are preserved. This is
one case within A105, not a finished axis or an adopted scoring policy. No
production reader, prompt, library entry or scientific run is changed.

Primary source: Seffernick et al. 2001,
[DOI 10.1128/JB.183.8.2405-2410.2001](https://doi.org/10.1128/JB.183.8.2405-2410.2001),
[PMC95154](https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/).

## Experimental definition

The natural TriA sequence from Pseudomonas sp. NRRL B-12227 was expressed in
E. coli DH5alpha(pJS3). Table 1 measures a partially purified preparation, with
specific activity divided by total preparation protein mass. The comparison
changes substrate identity. TriA and AtzA were not deliberately mixed. Host
proteins can remain in the TriA preparation; their catalytic contribution is not
numerically partitioned. AtzA's separate inhibitor assays used highly purified
enzyme and atrazine as the baseline substrate, unlike TriA's melamine baseline.

Natural sequence differences do not supply an engineered perturbation series.
This case does not import an A106 mutation/restoration score.

## Filled numerical cells

| Cell | Reported operands | Calculation | Result and meaning |
|---|---|---|---|
| Melamine preparation activity | Table 1: 245 +/- 2 | Native measurement | 245 nmol/min/mg total protein; +/- meaning unspecified |
| CAAT preparation activity | 135 +/- 1 | Native measurement | 135 nmol/min/mg total protein |
| Ammeline preparation activity | 17 +/- 1 | Native measurement | 17 nmol/min/mg total protein |
| Aminoatrazine preparation activity | 17 +/- 1 | Native measurement | 17 nmol/min/mg total protein |
| Atrazine nondetection limit | 10 pmol/min/mg | 10/1000 | 0.01 nmol/min/mg; not a zero or measured blank |
| Aminoatrazine / atrazine contrast | Positive mean 17; limit 0.01 | 17/0.01 | Greater than 1700 for a positive undetected denominator; point/limit calculation, not a confidence bound |
| Corresponding log contrast | Same observations | ln(1700) | Greater than 7.438383530; this is a log activity ratio, not a log likelihood ratio |
| Melamine / ammeline contrast | 245 and 17 | 245/17 | 14.411764706 under the reported preparation conditions; not a kcat ratio |
| Full-span sequence identity | 475 residues, 9 differences | (475-9)/475 | 0.981052632; a sequence comparison, not function probability |
| TriA residual rate with aminoatrazine competitor | 71 percent inhibition | 1-71/100 | 0.29 of its own no-competitor baseline |
| TriA residual rate with atrazine competitor | 12 percent inhibition | 1-12/100 | 0.88 of its own no-competitor baseline |
| Residual-rate contrast | 0.29 and 0.88 | 0.29/0.88 | 0.329545455; not a binding-affinity ratio |

The twelve Table 1 nondetections are different tested substrates in one
preparation protocol, not twelve independent confirmations of one function.
The paper supplies duplicate samples, not identified independent preparations.
The definition of +/- in Table 1 is not supplied. Figure 4 calls its own bars
SEM, but that does not define the table's errors. Consequently a statistical
variance or likelihood score is not inferred from those printed halfwidths.

## Conversion into the user's components

**Experimental comparability** excludes the deliberately changed substrate.
Protein identity, preparation class and total-protein denominator are shared.
The table's substrate concentrations, saturation, temperature and per-substrate
measurement recovery are not completely specified. The known native rate
ratio is retained; an unknown condition-response correction is not set to one.

**Isolation of the measured effect** concerns background catalysis and the
fraction of measured chemistry attributable to TriA. A model with additive
background gives, for substrate s:

`protein_activity_s = (preparation_activity_s - background_activity_s) / protein_mass_fraction`.

All three activity terms must use the stated mass denominator. With the same
protein fraction in two assays, that fraction cancels from their activity ratio.
Background terms do not cancel merely because the preparations match. A purity
fraction is not itself the fraction of catalysis due to TriA. Neither the purity
fraction nor the numerical background is measured here, so this formula defines
missing operands without fabricating corrected activity.

**Signal and uncertainty** retain the native magnitudes, comparator and detection
limit. For positive measured x and y with known sampling covariance, the local
log-ratio variance would be

`Var(log(x/y)) = Var(x)/x^2 + Var(y)/y^2 - 2*Cov(x,y)/(x*y)`

to first order. Here those variances/covariance are unknown. Nondetection enters
a censored likelihood only if its measurement model is supplied. It is not
replaced by zero, half the limit, or a guessed standard error.

**Relationship to the supplied target** retains the actual comparison. The
natural TriA/AtzA alignment has 0.981052632 identity while the paper describes
different reactions. High sequence identity cannot replace reaction-specific
measurements. The nine observed differences are not an independently established
functional-site denominator. Sequence-only correspondence is not a completed
five-component relationship estimate or a calibrated rate-transfer function.

**Combination and dependence:** the substrate means, their pairwise ratios and
their log ratios are representations of the same observations. Calculate one
joint contribution from those observations when an applicable statistical model
is available; do not add each derived contrast as another experiment. Shared
normalization induces covariance. Inhibitor measurements describe reaction-rate
changes; they do not supply Kd or an independent direct binding curve.

## Exact missing-data result for this source

The sheet retains the native measurements and derived ratios above. It leaves
`background_activity`, `protein_mass_fraction`, `condition_response`,
`sampling_covariance`, `source_profile_log_ratio` and `source_signed_index`
unknown where their operands are absent. An unknown target relationship or
source score produces an unknown target contribution, not a numerical zero.
This is an incompletely populated case, distinct from a mathematical formula
whose inputs have not been defined. It does not discard the source's useful
reaction profile or prevent further investigation.

## Inspection and checks

The parent inspected the worker's SOURCE_RECORD_001.md, NUMERICAL_SHEET_001.md
and CONVENTION_COMPARISON_001.md, then the primary article's complete Methods,
Results and Discussion in retained text lines 1131-1366 and rendered Figures 3
and 4. The initial combined web/packet output truncated; complete retained reads
repaired the relevant omissions. No raw data, earlier AtzA specificity paper or
unavailable PDF was inspected. Figure 4 visibly uses mM while the text states
100 micromolar starting melamine; no rate was digitized from that discrepancy.

After primary inspection and before this conversion, the parent fully reread
all documents required by the local AGENTS.md in six nontruncated groups:
root AGENTS/GOAL; EPISODE_STRUCTURE/TASK_AND_STEERING;
TIME_AWARE_ESTIMATION/TOOL_KNOWLEDGE; the task/steering and axis-review amendments
plus both VERBATIM records; EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS and numerical
review002; finally local AGENTS, A105_REVIEW_ASSIGNMENTS and the active goal
attachment, followed by the latest human reminder about outcome criteria.

`check_tria_cells_005.py` independently checks the printed arithmetic and writes
only the new parent result. It does not fit a source score or validate biological
independence. The full substrate and inhibition transcriptions remain in the
separately owned worker packet.
