# IscR2013 primary-source binding packet

Scoped new research output, 2026-10-25. DOI 10.1038/nsmb.2568; Rajagopalan et al., *Studies of IscR reveal a unique mechanism for metal-dependent regulation of DNA binding specificity*. Original author-manuscript article and table image were inspected through PMC3676455. Raw HTML, BioC projection and original Table 3 JPEG are retained. This is one paper. No second paper, production reader, model-backed episode or final annotation calculation was run.

The complete mandated authority/current-sheet/current-contract reset was performed after source inspection and before the interpretation below. `READ_PROVENANCE_001.json` records actual reads and limitations. This packet is awaiting the parent's independent source review/reset.

## Experimental definitions before numerical interpretation

The studied reference molecule is **Escherichia coli IscR**. The narrow retained comparison is Table 3's **wild-type apo-IscR**, competing unlabeled wild-type **hya** DNA versus hya **7C to G** DNA. Table 3 also tests **apo-IscR-E43A** and additional mutant/shuffled DNAs. These are separate protein preparations/assay sets; wild-type IscR and E43A are not deliberately mixed in a common reaction. Each competition reaction does contain both labeled wild-type hya tracer and an unlabeled competitor. That ligand coexistence is essential to interpreting the endpoint.

Methods, “Strain construction,” describes mutagenesis of pPK6161 (wild-type iscR under a T7 promoter) and transformation into PK7878, BL21(DE3) ΔhimA::tet ΔiscR::kan. “Purification of IscR for DNA binding experiments” identifies PK8581 for wild type and PK9124 for E43A (other listed variant strains are retained in the original text). Exact binding-protein residue boundaries, tag presence/cleavage and batch-specific purity are **not established by the inspected binding Methods**. Do not copy the crystallography construct's C-terminal 6xHis tag, C92/98/104A substitutions, or the unbound structural construct's 1–133 truncation into this binding experiment. Those belong to different preparations.

The binding proteins were initially anaerobically purified with partial Fe-S occupancy. Methods reports 40–50% for wild type and 27–50% for variants in the purification paragraph, and 27–56% for anaerobically isolated proteins in the direct-isotherm paragraph. These are separate reported ranges, not a repaired common range. **Table 3 competition uses the apo preparations**, made with 100-fold excess EDTA and 10-fold excess dithionite until absorbance at 420 nm stopped decreasing, followed by Biorex70 purification/removal of EDTA. That optical endpoint is the paper's evidence for cluster removal. A measured zero cluster fraction with a detection limit is not supplied. Do not treat the partially occupied anaerobic stock as Table 3's assayed state, or claim apo means the 3CA construct.

## What Table 3 actually measures

The primary Table 3 image, not searchable article text alone, contains **32 ± 2 nM** for wild-type apo-IscR with unlabeled wild-type hya competitor, and **>510 nM** for that same protein with hya(7C to G). The column is **IC50**, not Kd. Table footnote a defines it as the unlabeled competitor concentration reducing binding to labeled hya by a factor of 0.5. Table footnote c describes the ± number as **standard deviation derived from a four-parameter logistic fit to the average of at least three independent titration experiments**. This is not an identified sample SD of independent fitted IC50s, a SEM, or a known-error likelihood.

This corrects the current sheet section 8's incomplete retained statement that the 32 nM point has missing sampling uncertainty: the source does print **±2**, with the specific fit-to-average basis above. What remains missing is a defensible sampling/error model and covariance for likelihood or confidence inference. The historical sheet is unchanged; this is an additive source correction proposal.

Table 3 source cells (all nM):

| Unlabeled competitor | Wild-type apo-IscR IC50 | Apo-IscR-E43A IC50 |
|---|---:|---:|
| hya | 32 ± 2 | 11 ± 1 |
| shuffled | >1000 | >1000 |
| hya (7C to G) | >510 | 17 ± 3 |
| hya (8C to G) | >740 | 7 ± 3 |
| hya (8C to A) | >1000 | 6 ± 1 |
| hya (8C to T) | >1000 | 8 ± 1 |

`table3_measurements_001.json` retains 12 distinct reported cells, manual-visual-transcription origin, inequalities, original table/column/row and uncertainty basis. A table image, its article placement and its BioC table footnotes are representations of the same observations.

Methods, “DNA-binding fluorescence polarization assays,” last paragraph, supplies the competition design:

| Field | Reported content and role |
|---|---|
| Tracer | 5 nM Texas Red labeled wild-type hya DNA; 5′ top-strand label; binding Methods describes 30-bp duplexes |
| Unlabeled competitor | 8–1000 nM; competitor DNA identity/mutation is the deliberate within-protein change |
| Protein input | 22 nM apo-IscR **or** 20 nM apo-IscR-E43A |
| Buffer | 40 mM Tris-Cl pH 7.9, 250 mM KCl, 5% glycerol, 10 µM DTT; anaerobic |
| Readout | Fluorescence polarization/anisotropy on Beacon2000 with Texas Red filters |
| Baselines | Afree: DNA without IscR; Abound: DNA/protein without competitor |
| Normalized response | (A−Afree)/(Abound−Afree); denominator is the no-competitor response range, not an absolute molecular concentration |
| Fit | Four-parameter logistic curve, SigmaPlot12.0 |
| Repetition | At least three independent occasions/titration experiments; exact n, preparation/batch independence and individual curves unavailable |

The prior direct-isotherm paragraph states 12 minutes before reading and 10-second light-exclusion delay; competition says measured “as described above.” Record these as inherited-by-cross-reference procedural details, rather than claiming an independently specified competition time course or demonstrated equilibration. Temperature of the competition reaction is not explicitly established here; room temperature in the apo-preparation paragraph is not automatically assay temperature. Total reaction volume is absent, so nM does not supply femtomoles. Protein nM is reported as protein concentration; monomer-versus-dimer concentration convention is not made explicit in this inspected paragraph.

The separate **direct binding isotherms** use 150 mM KCl, increasing protein concentration and a four-parameter Hill fit, which the paper labels Kd. Tables 2/4 belong to that model. They cannot supply an equilibrium Kd for Table 3's 250 mM KCl competition experiment by relabeling IC50. The authors also flag unclear physical meaning for Hill n>2 and possible monomer–dimer effects. These model limitations are retained, not scored by an invented validity category.

## Functional bearing, comparability and effect isolation

Within wild-type apo-IscR's competition series, changing the competitor at position7 greatly reduces displacement potency relative to wild-type hya. E43A retains displacement by that competitor. This bears on **sequence discrimination of apo-IscR under these assay conditions**, with the matched protein/ligand identities stated. It does not directly measure transcriptional activation, in vivo repression, a chemical reaction rate or a native whole-cell phenotype. The proposed Glu43 mechanism also uses structural/mutational evidence; Table 3 alone does not establish every molecular step.

**Comparability outside the deliberate change:** buffer, label, tracer input and protein identity/input are described as common within each protein's competitor series. Competitor nucleotide change is the variable being tested and is not a comparability penalty. Across wild type and E43A, nominal protein inputs differ: 22/20=1.1. This numerical distinction must accompany comparisons; IC50 is affected by assay occupancy and competition conditions. It is not an automatic 0.9/1.1 reliability weight or a calibrated correction of binding potency. Direct-isotherm 150 mM versus competition 250 mM KCl is a separate protocol difference; their numerical parameters cannot be pooled as one experiment.

**Isolation of the measured effect:** purified-protein competition, no-protein baseline, no-competitor normalization, self competitor and shuffled DNA help distinguish protein-associated, sequence-dependent displacement from baseline signal or nonspecific competition. They do not quantify residual contaminants, active protein fraction, labeling effects or all optical artifacts. Purification does not equal measured zero contamination. A mutation can influence folding or oligomerization as well as a contact. Additional structure/direct binding results address some alternatives, but are complementary readouts rather than automatically independent repetitions of the IC50 experiment.

The shuffled competitor's >1000 is a finite assay limit, not zero binding or infinitely strong specificity. Likewise **>510 is not automatically the 1000 nM maximum input**: the inspected table/Methods do not state how this particular threshold was selected, whether it is a failed/saturation-limited fit or another reporting rule. Preserve its literal inequality and leave the limit-generation mechanism unknown. It is not a confidence interval.

## Paired fields and numerical components

The useful extension to the current source-native contract is a **competition-parameter route**, distinct from both rate correction and reported-signal ratios. This is a proposal for exact later population, not an installed runtime operation.

| Reader extraction fields | Numerical cell, operands and meaning |
|---|---|
| quantity=IC50; protein/apo state; tracer identity/input; competitor identity; source value versus limit; nM unit; row/column/footnotes | `reported_ic50` or `ic50_lower_limit`; finite fitted response parameter or lower threshold; never Kd |
| `reported_fit_sd`, `uncertainty_basis=logistic_fit_to_average_titrations`, exact n nullable, minimum n=3 | `relative_reported_fit_spread=reported_fit_sd/abs(reported_ic50)`; e.g. 2/32=.0625; relative reported fit spread, not biological CV/SEM |
| Ordered within-protein competitor and self-competitor point/limit cells; same protocol/response model; bound direction | `native_ic50_ratio`; less-favored/favored IC50. WT >510/32=>15.9375; dimensionless, evaluated at the reported denominator point |
| Same operands and positivity | `log_native_ic50_ratio`; WT >ln(510/32)=>2.768674822919; log response-contrast threshold, not binding free energy |
| E43A point cells 17±3 and 11±1 | `native_ic50_ratio=17/11=1.545454545455`; `log_native_ic50_ratio=.435318071258`; uncertainty remains unavailable without supported joint error/covariance |
| Protein nominal inputs 22 and20 nM, explicitly not intended DNA-change operands | `protein_input_ratio=22/20=1.1`; comparability diagnostic; not a likelihood or automatic quality multiplier |
| Same four IC50 cells with distinct shared-denominator identities | Optional `ratio_of_ic50_ratios` threshold >(510/32)/(17/11)=10.3125, log>2.333356751661; descriptive assay response contrast with the unequal protein-input qualification retained |
| Independent titration IDs, shared controls/curve IDs, covariance/error likelihood, censor-limit mechanism, parameter hypothesis | `source_profile_log_ratio` and proposed source index: **null here**, specific missingness retained |

For WT, “>15.9375” is **reported-limit/reported-point arithmetic**. The denominator is a fitted estimate with a reported spread. It is not an uncertainty-aware lower bound on the true affinity or population IC50 ratio. The source component should therefore separate `threshold_arithmetic` from `confidence_lower_bound` and `parameter_identification_bound`; the last two are null here. Do not silently treat 32 as an error-free true value.

All operands, source IDs, calculations, units and unavailable outputs are retained in `numerical_components_001.json`; no raw value is replaced with a category or confidence number. Alternative representations (ratio/log ratio, relative spread/raw spread) do not add independent evidence or get multiplied together.

### Explicit combination and uncertainty limits

For a later **identified** positive competition model, the numerical contrast is

`e = ln(IC50_mutant) − ln(IC50_self)`

and its first-order variance would be

`V(e) = V(IC50_mutant)/IC50_mutant² + V(IC50_self)/IC50_self² − 2 Cov(IC50_mutant,IC50_self)/(IC50_mutant·IC50_self)`.

That sum combines measurement uncertainty and shared-denominator covariance once. Here one operand is censored, its error model is absent, the reported fit spread is not automatically the sampling variance needed above, and covariance is missing: **no numerical V(e)** follows. Other mutants sharing self-competitor32 share that same denominator; they are not five independent specificity proofs. Repeated use of Table3 in a caption/HTML/image does not increase n.

The optional across-protein contrast is the explicit sum `e_WT − e_E43A`; its uncertainty needs the full four-parameter joint model and any cross-protein dependence. It concerns the specified fixed-input assay, not intrinsic affinity, unless a supported concentration/occupancy model supplies that relationship. No mapped target relationship is built here.

Where an actual likelihood is supplied, the current sheet's source convention could use `S=sup_Hplus logL − sup_Hminus logL` and proposed `B=tanh(S/2)`. Neither is computed from a threshold or fitted SD alone. No independent-normal noise, known variance, zero covariance, pseudocount, IC50-to-Kd relation, target multiplier, source-pooling policy or final annotation aggregation is invented. The corrected-activity primitive model q,g,k,E,u,v is **endpoint-incompatible** with these static competition parameters; its absent outputs should say endpoint/model mismatch rather than invite molecular-turnover arithmetic.

## Proposed interpretation instructions, separate from the sheet

For this aspect, ask the reader to identify the actual protein/state and tracer/competitor species; distinguish increasing-protein direct binding from increasing-competitor displacement; identify Afree/Abound and normalization; locate the fitted parameter and printed uncertainty definition; state which comparison changes only DNA and which changes protein amount as well; identify repeated titrations versus independent preparations; preserve the inequality's actual limit mechanism if stated.

Suggested closed meanings: `parameter_kind=ic50|reported_hill_kd|other|unknown|conflicting`; `design=equilibrium_competition|direct_binding_isotherm|other|unknown|conflicting`; `uncertainty_basis=fit_to_averaged_curve|between_independent_fitted_parameters|raw_endpoint_sd|unknown|conflicting`; `construct_relation=same_protein_different_competitor|separate_variant_proteins|protein_mixture|unknown|conflicting`; `limit_mechanism=stated_maximum_tested_concentration|fit_or_saturation_limit|other_stated|unstated|conflicting`. Each answer needs its source witness; unknown is permitted. These are meanings that constrain extraction, not numerical quality grades. Deterministic parsing and arithmetic should populate numbers from the retained image transcription/source spans, not model-supplied values.

## Missingness and handoff

Exact replicate counts, individual curves, batch/preparation independence, all fit parameter covariances, full censoring mechanism for >510, competition temperature/volume, protein-concentration oligomer convention, active protein fraction, and binding construct boundaries/tag status remain unknown here. Individual raw anisotropies are not acquired. The supplement and article PDF requests returned challenge HTML; a candidate publisher supplement URL failed DNS. These failures are in acquisition_001.json. Their bytes were not treated as PDFs or scientific evidence. The available article and Table3 suffice to verify the retained values/definitions, with those limitations.

The packet supplies a primary-source correction, paired extraction fields, numerical components, precise combination limits and reconstruction bytes. It does not implement a reader/calculator/runtime binding, A106/A111 graders, target correspondence or W05. The parent owns additive interface design, printed user feedback, coding and integration decisions after independent reset.
