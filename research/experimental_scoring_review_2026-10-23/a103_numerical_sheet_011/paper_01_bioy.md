# A103 source packet 01 — BioY, research draft

Source: [Hebbeln et al., 2007](https://pmc.ncbi.nlm.nih.gov/articles/PMC1815280/), DOI 10.1073/pnas.0609905104. Corpus seed: `context_bioy_optional_module_2007`.

## Inspected source measurements and definitions

Full main-text Results, Discussion, Methods and figure captions were read. The comparative survey used complete/nearly complete genomes, SEED similarity/context tools and PFAM. It retained 150 BioY sequences in 127 genomes, selecting one representative from groups exceeding 98% amino-acid identity. Approximately one-third were associated with BioMN. Several genomes contained multiple BioY copies. Neither a context probability nor a spatial distance threshold was reported in the inspected main text.

The experimental system used *R. capsulatus* SB1003 genes expressed in *E. coli* S1039 deficient in high-affinity biotin uptake. BioY alone and BioMNY were compared; BioMN was deliberately changed, alongside the construct arrangement. BioY’s start codon was altered for expression. Both conditions contained BioY, rather than wild-type and mutant BioY mixed together. Uptake and kinetic assays distinguished transport from module-dependent affinity; those assay measurements are outside this A103 score. Background includes host transport and expression effects. Population context counts are observational, not a matched perturbation experiment.

Locations: comparative Results paragraphs 1–5; Fig. 1; Methods “Bacterial Strains,” “Plasmids,” “Bioinformatic Techniques.”

## Conversion into the numerical sheet — proposed analysis

The unit of the reported context denominator is a retained BioY gene, not a genome, independent lineage, assay, paper or functional validation. Thus 150/127 = 1.1811023622 genes per represented genome is a measurable redundancy diagnostic, **not** a support/confidence multiplier. The difference 150 − 127 = 23 is the excess of retained copies over one per represented genome; it does not establish exactly 23 duplicated genomes.

The reported association proportion can populate `observed_fraction.reported_value = 1/3` with `precision = approximate`; it cannot populate an exact `positive_count = 50`. It does not establish the full number of genomes searched, the number without BioY, the number of independently varying contexts, or a false-positive rate. The exact numerator, coordinates, gene identities and dependence groups remain missing because the supplementary spreadsheet could not be retrieved.

This is useful to the sheet because two scoped inferences must behave differently:

- For “BioY participates in biotin uptake,” a locus lacking linked BioMN is not automatically an opposing observation. That scope does not demand this module.
- For “all BioY loci have an adjacent BioMN module,” linked and unlinked observations address a genuine universal arrangement claim. The approximate two-thirds unlinked proportion challenges that arrangement; it is not two-thirds evidence against transport activity.

For a calibrated context-to-function score, the final sheet will require either a native channel-specific association score with defined calibration, or a matched background frequency for the same spatial endpoint. The paper's approximate proportion alone supplies neither. Consequently the historical cohort gets bounded/unknown compilation, not a made-up point estimate. This is a missing empirical input, not undefined arithmetic: interval operands can be propagated through the final sheet.

Comparability concerns genome completeness, gene-calling/similarity methods and the selection of comparison loci. Effect isolation asks whether a context association discriminates the proposed module/function from other causes of colocation. These are different cells. A common operon, duplicated BioY copies, overlapping windows and related genomes cannot produce independent copies of the same evidence. Do not transplant the >98% filtering threshold into a runtime acceptance gate; retain it as a definition of the historical sample.

Complementary work that directly fills the gaps: recover SI Table 1 and its gene/assembly identities, then compute the declared spatial endpoint on an explicitly enumerated cohort and matched null loci. A targeted native context score can fill a different, documented measurement cell; it must not be called the historical paper's score. Neither another assay nor another citation supplies the missing genomic denominator.

## Retrieval and reset provenance

- Primary article inspected through PMC; retained corpus packet also read in the same paper-specific inspection.
- PMC supplementary link returned a browser challenge; PNAS supplementary XLS returned cookie/403 responses; Europe PMC supplementaryFiles returned XML rather than a ZIP. No spreadsheet counts are claimed.
- Full authority reset completed after source inspection and before this interpretation: `AGENTS.md`, `GOAL.md`, `docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`, `docs/TOOL_KNOWLEDGE.md`, `docs/TASK_AND_STEERING.md`, both task/steering and evidence-axis-review amendments, both verbatim publication records, the complete evidence-axis-library amendment including corrections, numerical review002, research `AGENTS.md`, and the active goal attachment. Latest human goal reminder was reread last.
- Research draft only. No experimental assay, genome reconstruction, production reader or scientific episode was run.
