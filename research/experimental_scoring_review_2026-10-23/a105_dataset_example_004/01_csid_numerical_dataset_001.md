# One CsiD numerical dataset example for the A105 sheet

2026-10-23. **Research example; graph-derived measurements, conditional arithmetic,
and unadopted contribution calculations.** No production reader/scorer, prompt,
library, scientific run, target correspondence or annotation coordinate is
implemented. A105 remains unfinished; this does not change the 0/10 count.

## Actual experiment and comparison

The assayed molecule is recombinant **E. coli BW25113 CsiD with an N-terminal
6×His tag**, expressed in **E. coli BL21(DE3)**, purified with Ni-NTA, checked by
SDS gel, and buffer-exchanged by size-exclusion columns. The paper does not give
an activity-based contaminant fraction or independent preparation identities.
There is no deliberate mixture of mutant and wild-type CsiD. The compared arms
use the same described construct; they are not different organisms or genotypes.
The annotation target is a separately supplied sequence/file/snippet: none was
mapped to this construct here. In particular, **no ybhP correspondence is asserted**.

The selected comparison is the **oxygen-consumption rate of this preparation
without added inhibitor versus with 5 mM L-2-hydroxyglutarate (L2HG)**, as displayed
in Supplementary Figure 5. L2HG addition is the intended changed variable.
The endpoint is micromoles of oxygen consumed per minute in a Clark electrode;
the denominator is **time**, not protein mass, protein moles or reaction volume.
The plotted unit is µmol/min, **not µM/min**. The no-inhibitor arm contains the
enzyme reaction; it is **not a no-enzyme blank**.

The general CsiD electrode method specifies 180 nM CsiD, 30 °C, 100 mM MOPS,
70 mM NaCl, 20 mM KCl, pH 7.2, 400 µM ascorbate and 4 µM iron salt, in a sealed,
stirred chamber. Figure 5 does not independently supply arm-specific preparation
identities, stock/vehicle/pH changes, reaction volume or the substrate and
co-substrate concentrations for this inhibition comparison. The kinetic Methods
give companion-substrate concentrations for the Km titrations; those must not
silently become Figure 5's concentrations.

These are direct molecular-assay rate measurements. They are retained here as
preparation chemistry and assay-condition evidence. They do not score a gene's
causal contribution from deletion/restoration. The paper's genetic, growth and
cellular accumulation comparisons remain outside this A105 example and belong
to the separately retained A106 work.

## Exact source and data access

Knorr et al., *Widespread bacterial lysine degradation proceeding via glutarate
and L-2-hydroxyglutarate*, Nature Communications 9, 5071 (2018),
[DOI 10.1038/s41467-018-07563-6](https://doi.org/10.1038/s41467-018-07563-6),
[PMC6265302](https://pmc.ncbi.nlm.nih.gov/articles/PMC6265302/).

| Material inspected | Exact location and retained file | What it supplies |
|---|---|---|
| Primary Methods and CsiD Results | [Europe PMC full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6265302/fullTextXML); `primary_fulltext.xml`; sections “Bacterial strains and general culture conditions,” “Protein purification,” “CsiD reactions analysed by Clark-type O2 electrode,” “NMR of the CsiD reaction,” “Stereospecificity of the CsiD reaction” | Construct, preparation, general assay, distinction between oxygen proxy and product identification |
| Published numerical plot | Supplementary Information, **PDF page 7, Supplementary Figure 5**; `41467_2018_7563_MOESM1_ESM.pdf`; [publisher PDF](https://static-content.springer.com/esm/art%3A10.1038%2Fs41467-018-07563-6/MediaObjects/41467_2018_7563_MOESM1_ESM.pdf) | Individual plotted measurements, bars, SD whiskers, concentrations and n |
| Supplement package | [Europe PMC supplementaryFiles](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC6265302/supplementaryFiles); `europepmc_supplementaryFiles.zip` | Two PDFs and figure image files; no attached CSV/XLSX/Prism measurement file in this retrieved package |
| Product characterization | Same supplement, Figures 1–3, PDF pages 3–5 | NMR and derivatized LC-MS product identification; no quantitative same-interval product/O2 balance |
| Reviewer/author clarification | `41467_2018_7563_MOESM2_ESM.pdf`; retained text `peer_review_001.txt`, lines 529–543 | Single-concentration measurements do not establish a fitted Ki; the revision changes the description to weak inhibition |
| Primary data-availability statement | XML `notes[@notes-type='data-availability']` | Supporting measurements are available from the corresponding author on request; no raw measurement delivery occurred here |

The PMC browser route presented an access challenge, and the springer-cdn
hostname failed. The Europe PMC XML and supplementary ZIP were obtained, and
the publisher's `static-content.springer.com` PDF independently matched the
supplement bytes. `source_manifest_001.json` records URLs, byte hashes and ZIP
members. No author was contacted.

This is an **actual published plotted dataset reconstructed from vector
coordinates**, not a newly supplied raw instrument dataset and not synthetic
values. Figure-derived numbers are approximate. The original observation
precision, unplotted values, calibration and electrode time traces cannot be
recovered from these graphics.

## Filled numerical measurement cells

The caption defines bars as means, error bars as **standard deviations**, and
the measurements as triplicates except D2HG, which has n=2. It does not identify
independent protein preparations or label pairings across arms. Thus the
reported measurement counts are known; biological/preparation independence is
unknown. The main-text CsiD kinetic result `53 ± 3 µmol/min/mg` still has an
unresolved ± definition in the inspected text. Figure 5's SD definition is
not retroactively assigned to that other result.

| Plotted arm | Added compound | Recovered mean, µmol O2/min | Recovered SD, same unit | Reported n |
|---|---:|---:|---:|---:|
| No inhibitor | 0 | ≈0.16062 | ≈0.01026 | 3 |
| NOG | 0.1 mM | ≈0.07473 | ≈0.00173 | 3 |
| L2HG | 5 mM | ≈0.10484 | ≈0.01091 | 3 |
| D2HG | 5 mM | ≈0.09049 | ≈0.00738 | 2 |

The NOG and D2HG rows preserve the displayed panel; they are not added as two
independent confirmations of the chosen control/L2HG contrast. These are not
matched-concentration NOG-versus-L2HG affinity measurements.

`pdftocairo -svg -f 7 -l 7` supplied `supplement_fig5_page7.svg`. The chosen
axis centers are y=245.80859424 at 0.00 and y=99.72265647 at 0.20. Therefore:

```
k = 0.20 / (245.80859424 - 99.72265647)
  = 0.00136905716631 (µmol/min)/PDF-point
mean_rate = (y_zero - y_bar_top) * k
SD_rate   = (y_bar_top - y_upper_SD_cap) * k
```

For the no-inhibitor arm the bar and cap y coordinates are 128.48437549 and
120.99218756. For L2HG they are 169.23046922 and 161.26171860. Complete path and
transform operands are in `csid_plot_arithmetic_001.json`. A PNG of PDF page 7
is retained for visual checking.

As a separate graphical cross-check, the displayed point centers recover
approximately `[0.15349, 0.17228, 0.15521]` for control and
`[0.11267, 0.10919, 0.09221]` for L2HG. Their means and SDs agree with the
bar/whisker reconstruction within 0.00030 µmol/min for these two arms.
They are the **same measurements**, not a second dataset or extra replication.
Marker order/x-jitter does not reveal pairing. The small bar/marker difference
is retained as graphical reconstruction uncertainty; it is not arbitrarily
added as biological variance or claimed as a guaranteed error bound.

## Native contrast and explicit uncertainty arithmetic

Let C and L denote the control and L2HG mean rates. The selected statement is:
**the preparation's oxygen-consumption rate is greater without added L2HG than
with 5 mM L2HG under the reported assay.** This statement can emerge from
investigation; no initial annotation hypothesis is required.

| Numerical cell | Calculation | Result and meaning |
|---|---|---|
| Mean rate contrast | `d = C - L = 0.1606235625 - 0.1048398308` | **≈0.05578373 µmol O2/min** lower rate with L2HG |
| Retained rate fraction | `R = L/C` | **≈0.6527052**, denominator is the uninhibited preparation rate |
| Fractional rate reduction | `1 - R` | **≈0.3472948 = 34.73%**; not a reliability score, attribution fraction or Ki |
| Log retained-rate ratio | `log(L/C)` | **≈−0.4266297**; reexpression of the same contrast |
| Control mean variance, conditional | `vC = sC²/3` | `0.00003507028025 (µmol/min)²` |
| L2HG mean variance, conditional | `vL = sL²/3` | `0.00003967367060 (µmol/min)²` |
| Difference variance | `vC + vL - 2 cov(C,L)` | Covariance must remain explicit |
| Under independent-arm measurement errors | `Vd = vC + vL` | `0.00007474395086 (µmol/min)²`; **SE≈0.00864546 µmol/min** |

The `s²/3` mean-variance conversion assumes three independent measurements
within each arm for the scope being estimated. It does not assert three
independent protein preparations. The independent-arm SE is a **conditional
assay-repeat calculation**, not total experimental uncertainty or the SE of a
biological/preparation population.

Under separate independent normal measurement errors, the Welch calculation is:

```
df = (vC+vL)^2 / (vC^2/(3-1) + vL^2/(3-1)) = 3.984884614
t  = d/sqrt(vC+vL) = 6.452374075
95% interval = d ± t_(0.975,df)*SE = [0.03174414, 0.07982332] µmol/min
```

The derived two-sided p-value is about 0.00301. **It was not reported by the
paper for this comparison**, is conditional on the model, and is neither an
annotation probability nor converted to a likelihood score.

For the ratio the first-order combination, retaining the covariance term, is:

```
Var(L/C) ≈ vL/C² + L²*vC/C⁴ - 2*L*cov(C,L)/C³
```

With the independent-arm assumption, the first two contributions are
`0.001537743413 + 0.000579101706 = 0.002116845119`, giving SE(R)≈0.0460092.
For log(L/C), `vL/L² + vC/C² = 0.003609522556 + 0.001359316939`, giving
SE(log R)≈0.0704900. These are local propagation approximations; their terms
are not independent extra evidence scores.

If the two arm means have correlation ρ, the difference variance is instead
`vC+vL−2ρ√(vC*vL)`. Varying ρ over [−1,1] while holding the marginal variance
estimates fixed gives SE between 0.00037669 and 0.01222072 µmol/min. This is
an **algebraic dependence sensitivity**, not an estimated confidence interval.
The absent pairing/preparation records do not justify selecting ρ=0 as fact.
Unmeasured shared calibration, preparation effects and condition-dependent
bias are additional unresolved uncertainty, not included in this range.

## Comparability and isolation remain separate

**Comparability outside the intended variable:** same described construct,
general electrode method and rate endpoint. L2HG addition is the intended
variable and is not penalized merely for differing. Stock addition, final pH,
vehicle, arm-specific protein amounts and preparation/date pairing are not
quantified. There is no measured numerical condition-response correction or
covariance for those differences. Nominal method agreement is not converted
to a score of 1 or an intuitive grade.

**Isolation of the measured effect:** the control is an uninhibited enzyme
reaction, not a chemical/electrode blank. Possible iron/ascorbate oxygen
consumption, contaminating activity and uncoupled oxygen consumption are not
numerically separated in this panel. An inhibitor effect on any of these could
change the measured contrast. The NMR and LC-MS product evidence supports
reaction identification, but does not supply a calibrated product/O2 ratio in
the Figure 5 intervals. A precise oxygen contrast therefore remains a
preparation oxygen contrast; it is not automatically the isolated L2HG
formation rate or proof of inhibition at a particular binding site.

If those actual measurements become available, a corrected oxygen contrast
could be populated as

```
d_corrected = (C - blank_C - contaminant_C)/condition_response_C
              - (L - blank_L - contaminant_L)/condition_response_L
Var(d_corrected) = J * Cov(all_input_estimates) * J^T
```

Each subtraction must describe a distinct measured contribution, and each
response factor a measured change in endpoint outside the intended variable.
Product-rate inference additionally needs the measured productive coupling in
each arm. These missing operands are **unknown**, not zeros/ones. They do not
erase the useful narrower uncorrected measurement. A matched chemical blank,
paired calibration checks, product/O2 measurement in the same interval, or
resolved preparation composition would address different listed weaknesses;
they are not a mandatory assay itinerary.

## Conditional numerical contribution using the existing proposal

The following fills the UNADOPTED `CONTRIBUTION_PROPOSAL_001.md` interface for
the scoped preparation-rate statement. It introduces no artificial expected
function rate. Define `H+ : μC >= μL` and `H− : μC <= μL` in the **same model**.
For independent normal measurement errors in each arm with separately unknown
variances, the reported means/SDs/counts are sufficient statistics. Set

```
RSSfit,j = (nj−1)*sj²
RSS0,j(m) = RSSfit,j + nj*(mean_j−m)²
S = min_m sum_j [nj/2 * log(RSS0,j(m)/RSSfit,j)]
```

The minimum profiles the two variances and the common mean at the boundary of
the opposed direction. Since the observed difference is positive, S is
positive. The calculations explicitly **sum** the two log-likelihood terms;
uncertainty enters through each measured squared SD and n. No reported SD is
treated as a known variance or an independent-preparation SE.

Using the graph-derived summaries:

```
RSSfit,C = 0.0002104216815
RSSfit,L = 0.0002380420236              (both in squared rate units)
best opposed common mean = 0.1593406718 µmol/min
S = 5.508230002 nats
B = tanh(S/2) = 0.991926175             (unadopted normalization)
```

The boundary likelihood has more than one local optimum; the checker searches
all detected minima and endpoints. Using a single local optimizer from the
pooled mean would not suffice. Reconstructing from point centers instead of
bars/whiskers gives S≈5.48845 and B≈0.99177. This is a reconstruction comparison,
not an uncertainty interval. Assuming a **common** unknown error variance
instead gives S≈7.30302 and B≈0.99865. The difference demonstrates why the error
model must remain visible; choosing equal variances is an extra assumption.

S and B are conditional on independent Gaussian assay errors, the plot
reconstruction and the narrower oxygen endpoint. No distribution validation is
possible from these small summary samples. B does not establish biological
importance, target function, probability of correctness or absence of bias.
It saturates even though the native effect retains its stated magnitude.
Reversing the statement about these same data gives −S and −B; this is not
another observation. Activity magnitude, fractional reduction, the Welch
statistic and S/B all reuse this one comparison and must not be multiplied
as independent confirmations.

As required by `ANNOTATION_INTERFACE_ADDENDUM_001.md`, this signed B is **not
a directly usable nonnegative hypervolume coordinate**. Source-to-target
correspondence and the annotation-coordinate interface remain uncomputed and
owned by their separate work. No unconditional source reliability score or
target A105 coordinate is claimed.

## Nondetection, limits and selection

No Figure 5 rate is replaced with zero. The paper separately reports no
detectable D-product and no conversion of other tested dicarboxylates. Without
their numerical limits/noise, those reports cannot supply zero rates,
infinite selectivity or a numerical exclusion contribution. The current
5 mM L2HG row is an exact-concentration measurement, not an inhibition titration.
It does not identify Ki. The supplement's Ki wording and the review response
are not used to manufacture a fitted parameter or its uncertainty.

The displayed panel has three added compounds plus control; the complete
screening/selection history is unknown. The selected contrast is analyzed as
the stated comparison, without presenting its conditional p-value or B as a
selection-calibrated annotation probability. All three other displayed rows
and the shared control remain visible for later joint analysis.

## Exact reader inputs and outputs for this example

These are targets for separately implemented readers/graders, **not an
implemented production reader**. The research checker only verifies this
retained figure and arithmetic.

| Reader input fields | Output cells | Deterministic operation or explicit missing value |
|---|---|---|
| `source_file`, `page`, `axis_tick_values`, `axis_tick_y`, `bar_top_y`, `sd_cap_y`, `value_origin=plot_reconstruction` | `endpoint_mean`, `endpoint_sd`, `units` | Linear axis conversion above; retain approximation and exact coordinates |
| Caption `error_type=SD`, `measurement_count`, preparation IDs, pairing IDs | `reported_measurement_count`, `independent_unit_count`, `pairing`, `error_df` | Counts 3/3; independent-preparation count and pairing null; df model-dependent |
| Assayed ORF source, tag, expression host, purification; separately supplied annotation target | `assayed_subject`, `target_subject`, `source_target_response_operands` | Extract actual construct; target correspondence null here |
| Endpoint names and conditions; contrast coefficients `[1,-1]` | `effect_estimate`, `native_ratio`, `contrast_boundary=0` | Subtract means; divide only with defined nonzero denominator |
| SDs, counts, supplied cross-arm covariance | `variance_terms`, `contrast_variance`, `contrast_se` | Sum/multiply covariance formula; conditional independent-arm result stored separately |
| Actual blanks, contamination rates, condition responses, calibration/coupling data | `comparability_corrections`, `isolation_corrections`, their covariance | All unmeasured numerical operands stay null; no default grade or perfect correction |
| Explicit normal observation model, mean/SD/n and parameter regions | `profile_log_ratio`, `bounded_profile_contrast`, `model_scope` | Constrained likelihood maximization; conditional values only |
| Censoring flag, numerical limit, detector-noise model | `censored_likelihood_operands` | No invented zero; absent threshold/noise remain null |
| Experiment/arm/control identity and representation IDs | `shared_evidence_group` | Bar, markers, text, PNG and SVG share one measurement block |

## Checks and completion limit

Executed `.venv/bin/python check_csid_plot_arithmetic_001.py`; output is
`csid_plot_arithmetic_001.json`. Checks passed for all 11 point markers and
the caption's 3/3/3/2 counts, graphical mean/SD agreement, explicit variance
addition, all detected profile-boundary minima, unit invariance, direction
reversal and preserved missing operands. These are extraction and arithmetic
checks, not evidence of raw-data access, biological independence, an assay
error model's validity or a production implementation.

The assigned source supports this **bounded graphical dataset example**.
If an original raw reaction dataset is required instead, the specific next
input is the authors' Figure 5 electrode time traces/Prism source file with
blank records, preparation IDs and pairing. The paper's data-availability
route is the corresponding author; no request was sent. There was no expansion
to a second paper.

## Required authority reset provenance

Read the full authority set at startup, repairing initial aggregate truncation
with complete fresh reads. After the one-paper retained packet, relevant primary
sections, supplementary evidence and review clarification, and **before the
above scoring interpretation**, fully reread:

1. `AGENTS.md` and `GOAL.md`.
2. `docs/EPISODE_STRUCTURE.md` and `docs/TIME_AWARE_ESTIMATION.md`.
3. `docs/TOOL_KNOWLEDGE.md` and `docs/TASK_AND_STEERING.md`.
4. `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md`.
5. `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`.
6. `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md`
   and `VERBATIM_RECOVERY_002.md`.
7. `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`.
8. `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`.
9. The entire local `research/experimental_scoring_review_2026-10-23/AGENTS.md`
   and `A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md`.
10. **Last**, `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`.

The complete post-paper reread had no truncated authority output. Startup also
read `SOURCE_CORRECTIONS.md`, the complete parent reliability proposal,
contribution proposal and annotation-interface addendum. Their arithmetic
remains unadopted. The original CsiD note and its arithmetic correction were
read as one retained paper packet; their older proposed product/quality grades
were not adopted here. No second paper or target-relevance packet was read.
