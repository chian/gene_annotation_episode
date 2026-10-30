# A105 FrsA negative pyruvate-decarboxylation evidence: source-to-sheet audit

## Source and claim boundary

This is an additive scientific audit of the retained 2013 FrsA review packet
`research/experimental_scoring_review_2026-10-23/template_a105_reactions_002/frsa_2013_review.md`
and its retained original main-text and supplement text. The tested subject is
recombinant wild-type *Vibrio vulnificus* FrsA expressed in *E. coli*, with two
reported protein-production routes (original pQE/JM109 F′ and codon-optimized
pET15b/BL21(DE3), His tag cleaved). These routes are preparation provenance;
they are not a wild-type-versus-mutant coexistence experiment. The tested
functional assertion is direct FrsA-catalyzed pyruvate decarboxylation to
acetaldehyde/CO2 under the stated in-vitro conditions. It is not an organismal
fitness or target-homolog transfer result.

## Paired extraction fields and numerical cells

| Assay/measurement | Required extracted source fields | Numerical cell and calculation | What the number evaluates |
| --- | --- | --- | --- |
| MIMS labeled-CO2 endpoint | FrsA preparation, 50 nM enzyme, 1 mM labeled pyruvate, 12 min, labeled-CO2 signal and matched blank, endpoint detection rule, uncertainty, source location | Enzyme exposure: `0.05 µM × 720 s = 36 µM·s`; calibrated CO2 excess and upper rate: **unavailable** | Exposure is a design operand; a calibrated excess would quantify product generation attributable to the enzyme under these conditions. |
| Proton NMR acetaldehyde endpoint | FrsA preparation, 5 µM enzyme, 10 mM pyruvate, 90 min, acetaldehyde peak and matched blank, detection rule, uncertainty, source location | Enzyme exposure: `5 µM × 5400 s = 27000 µM·s`; calibrated acetaldehyde excess and upper rate: **unavailable** | A chemically different product readout addresses a weakness of the MIMS CO2 measurement, but its missing detection limit prevents a numerical rate bound. |
| ADH/NADH coupled endpoint | FrsA amount (1 nM–1 µM), 5 mM pyruvate, 0.2 mM NADH, 3.7 U ADH, time course, matched blank, acetaldehyde spike dose/recovery, source location | Reporter capacity to supplied pyruvate: `0.2/5 = 0.04` as a **molar pool ratio**; net coupled rate, recovery fraction and FrsA upper rate: **unavailable** | The ratio records a stoichiometric capacity constraint, not 4% enzyme activity or assay reliability. The end spike shows qualitative detector response, not numerical recovery without a spike amount and response. |

The first two exposures have ratio `27000/36 = 750`. It describes differences
in enzyme concentration and observation time. Different substrates,
concentrations, readouts and detection characteristics mean this is **not** a
750-fold sensitivity, replication, or evidence-strength factor. Nondetection is
not an observed zero.

## Conditional scoring conversion

For a calibrated product endpoint with a source-supported upper excess-product
limit `L` in concentration units, enzyme concentration `E`, duration `t`, and
an experimentally supported fraction `K` converting generated product to
detected product, a conditional enzyme-normalized rate constraint is
`v < L/(E × t × K)` (or the corresponding non-strict bound). This operation
requires the endpoint to be in the regime where product accumulation is
proportional to time and measured enzyme amount. `L`, `K`, their uncertainty,
blank variation, and those regime conditions are **not established** for these
FrsA observations. Consequently no numerical upper rate, confidence interval,
assay error probability, contradiction score, or aggregate A105 credit is
populated here. A later calibrated assay could populate the bound without
changing this extraction/score meaning.

The source-level worksheet needs separate per-readout cells for enzyme exposure,
observed product/blank excess or its calibrated limit, recovery and
enzyme-normalized rate constraint, with typed missingness and source dependencies.
Distinct endpoints may address named measurement weaknesses, but cannot be
counted as independent preparations or multiplied as independent evidence
without their repetition and dependence bases. The current rate table reader
accepts explicit numeric limits in mapped CSV/TSV rows; it does not convert
paper prose such as “no detectable activity” into a limit. The current logical
A105 worksheet also lacks a composition rule for such cross-endpoint negative
evidence. Those are open implementation and scoring-definition gaps, not
permission to insert a categorical fallback grade.

## Authority and verification

After reading the paper-specific packet and original retained supplement/main
text, the root reread the complete original user goal attachment, root and case
AGENTS instructions, EPISODE_STRUCTURE, TIME_AWARE_ESTIMATION, TOOL_KNOWLEDGE,
TASK_AND_STEERING, the two relevant amendments, both verbatim direction/recovery
records, W04 evidence-axis instructions, the earlier numerical review example,
and the current A105 worksheet/rate reader/bound/contract paths. The latest user
steering was applied last. Arithmetic above was checked by explicit decimal and
unit conversion. No original paper was reacquired and no production path was
changed by this audit.
