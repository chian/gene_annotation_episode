# Addendum: the mean changes the estimand; neither combination is adopted

2026-10-23. Additive clarification/correction to
`MULTIPLE_SOURCE_CONVENTION_001.md`. The original remains unchanged. All numbers
below are the checked synthetic values in `arithmetic_001.json`.

The opening phrase "supplies one missing combination" means that an explicit
candidate arithmetic operation was supplied. It **does not mean that the
intended annotation-evidence aggregation is complete**. Candidate M estimates
nothing about target activity. It summarizes the average represented-source
index. That is a change in estimand if the desired output is cumulative evidence
for the target molecular statement. Its failure to accumulate independent
homolog support is substantive, not repaired by the word "conventional".

In particular, adding weaker POSITIVE evidence can lower M:

| Declared source set | Signed indexes | M, represented-source mean | K, cumulative arithmetic convention |
|---|---|---:|---:|
| H1 only, two independent preparations already combined | +0.771222064 | 0.771222064 | 0.771222064 |
| Add H2 with a genuinely positive measured effect +2, variance 1, R=0.4 | +0.771222064, +0.304637662 | **0.537929863** | **0.871181485** |

No new contrary evidence was added. M fell because its denominator and source
composition changed. If positive nonredundant corroboration must not lower the
target support operand, M does not meet that requirement. This is distinct from
the original note's other dilution example, where a source with R exactly zero
halves H1's mean to 0.385611032.

The evolutionary-density example is equally material. Let the ten positive
homologs share one evolutionary cluster while H2 belongs to another:

| Source roster | M | K |
|---|---:|---:|
| One positive H1-like source plus opposing H2 | 0.233292201 | 0.609869038 |
| Ten distinct positive H1-like sources plus opposing H2 | **0.673416634** | **0.999999995** |

These are ten distinct assayed molecules, not ten publications of one assay.
They can have independent laboratory errors while sharing an unresolved
source-to-target functional difference. Neither formula identifies that
dependence. A tree cluster does not supply a numerical correlation coefficient.
No equal-cluster weighting, fixed discount or arbitrary cutoff is substituted.

K is a fully specified cumulative SCORE CONVENTION. To call its growth evidence
accumulation requires an account of what the separate source relationships add
after shared experiments, calibration, controls, family effects and target
uncertainty are considered. Distinct publications or assays do not supply that
account. Even demonstrated nonredundancy would not turn K into a likelihood:
R is uncalibrated, and independently profiled S values do not generally add as
likelihood ratios. Dependence information is necessary for a cumulative-evidence
interpretation, but is not sufficient for statistical calibration.

The concrete choice for review is therefore:

- Elect M only if an average over the stated source roster is the wanted
  annotation operand, accepting the two dilution behaviors and density effect.
- Elect K only as an explicitly cumulative index, accepting its strong count
  effect and keeping unmodeled dependence visible; it does not claim independent
  evidence or probability merely because the arithmetic runs.

If neither meaning is acceptable, neither candidate supplies the intended final
aggregation. A dependency-sensitive cumulative target calculation remains
unresolved. The numeric sheet cells and conditional calculations remain useful;
no arbitrary empirical weights, max-positive-source selection or approval gate
is invented to hide the gap. The separate F coordinate policy also remains
unadopted.

One numerical transcription correction: in proposal 001's synthetic-variation
table, the row "Only H1's first preparation was available, with H2 unchanged"
lists K as 0.374063259. The executed calculation gives
**K=0.37406769859257244**, rounded **0.374067699**. Its listed M=0.152318831
was correct. This correction changes no other formula or example.
