# A106 paper packet 02: Cas2 acquisition perturbations

Research draft only. Selected primary: Nuñez et al. (2014), *Cas1–Cas2 complex formation mediates spacer acquisition during CRISPR–Cas adaptive immunity*, [DOI 10.1038/nsmb.2820](https://doi.org/10.1038/nsmb.2820), [PMC4075942](https://pmc.ncbi.nlm.nih.gov/articles/PMC4075942/). Selection and gap were sent by file before this paper was opened. No 2015 primary or other-species nuclease paper was freshly opened in this workload.

## Experimental definitions

The donor cas1/cas2 sequences come from E. coli K12 MG1655. The acquisition assay expresses both from pCDF-1b in E. coli BL21-AI, stated to lack all cas genes. It compares WT constructs with the specified substituted/deleted construct while retaining the other Cas protein. That means WT Cas1 coexists with a Cas2 variant; it does **not** mean WT Cas2 coexists with variant Cas2. Native host factors remain, and the plasmid also supplies donor DNA. Expression is induced for 20–24 h with 0.2% L-arabinose and 0.1 mM IPTG. PCR template amounts are normalized by culture OD600.

The endpoint is expansion of the cellular CRISPR locus detected on an agarose gel, not purified nuclease turnover. WT, empty-vector/single-protein controls, and specific variants are present. Experiments using Cas1-FLAG/Cas2-HA for pull-downs have tag-activity controls in Supplementary Fig. 1a. Different Cas1/Cas2 combinations, deletion interfaces, charge reversals and signature-site substitutions ask distinct questions. The assayed variant's intended residue change is excluded from comparability; its expression or stability change is not.

The main-text account and inspected Figures 3–4 contrast Cas2 E9A/E9R, which retain visible acquisition, with deletion of the Cas2 β6–β7 region, which lacks detectable acquisition. The co-precipitation comparison provides an assembly-related complementary endpoint. These are not interchangeable biological replications, and the truncation has not been shown to change only one interaction. A low-expression Cas2 E65R is explicitly noted in the Fig. 3 caption; no numeric abundance ratio is supplied.

## Actual numeric cells and their limits

The paper's qualitative descriptions of acquisition are not converted into percentages. The following are genuinely numeric source-derived entries, including a useful boundary case where the arithmetic is possible but its application is narrower than the functional claim.

| Cell | Native quantities and denominator | Derived value | Proposed use in the numerical sheet |
|---|---|---:|---|
| Nominal expansion step | 33-bp spacer plus 28-bp repeat | 61 bp | Measurement identity check for a canonical expansion; not acquisition frequency |
| Selected spacer lengths, Supplementary Table 1 | 30 displayed entries of length 33 bp; 2 of length 34 bp; 32 total entries | `f_33=30/32=0.9375`; `f_34=2/32=0.0625` | Measured length distribution among the listed selected expanded clones. If an inference specifically asserts exact 33-bp fidelity, these fractions quantify its qualification. They are not generic validity grades or evidence that 6.25% of acquisition is false |
| Source of listed spacers, same table | 26 plasmid entries and 6 genomic entries out of 32 | `f_plasmid=26/32=0.8125`; `f_genomic=6/32=0.1875` | Conditional composition of the selected listed events; does not estimate overall acquisition rate or immunity |
| Replication lower bound | All acquisition assays reported repeated at least three times | `n_acquisition_runs≥3` | Provenance for replication extent; no standard error follows without run values or sampling relationships |
| Cas2 E9A/E9R acquisition effect | Visible expanded bands; numerical cell/event numerator and eligible denominator not supplied | `W,K,θ,U = null` | Keep “similar” as a qualified source observation, not `K/W=1` or an equivalence probability |
| Cas2 β6–β7 deletion acquisition | No detectable expanded band; quantitative detection limit not supplied | `K=null`, `censor=below_unquantified_detection` | Do not replace nondetection by zero; a numerical lower bound on the loss requires a measured detection limit |
| Residual E. coli Cas2 E9 activity | No protein/assay-specific residual nuclease value established here | `P_activity=null` | Cannot populate “activity abolished” from another homolog's substitution experiment |

The 32 entries include a repeated sequence; without separate clone/culture identity it is not 32 independent acquisition experiments. The table is explicitly a sample of already expanded clones. The main narrative's general 33-bp statement is therefore qualified by the table's two printed 34-bp entries. This is an additive factual qualification, not a reinterpretation of the uninspected raw sequencing data.

## Numerator, denominator and measurement validity

For a future numeric cellular acquisition endpoint, one defensible quantity is `newly_expanded_independent_cells / eligible_cells_examined` under a defined sampling design, or a calibrated molecular fraction of expanded loci. This source does not report that denominator. OD normalization controls how much culture enters PCR; it does not establish equal viable cells, equal Cas protein, equal PCR amplification of different amplicon lengths, or quantitative gel response. Counting bands is not counting cells. Densitometry alone would not supply missing PCR-efficiency calibration.

For comparison, the printed spacer-length/source fractions have an exact denominator of **listed selected spacer entries**, so they are computable but must remain conditional. They cannot fill the acquisition-frequency cells. Molecular binding Kd, crystallographic distances and purification stoichiometry reported elsewhere in the same paper have separate meanings; they are not substitutes for a numerical perturbation effect.

## Separate comparability and isolation calculations

If calibrated matched quantities `A_variant,A_WT` were supplied, the proposed amount agreement is `C_amount=min(A_variant,A_WT)/max(A_variant,A_WT)`. Here it is null, including for the visibly weaker E65R input. Equal plasmid/promoter/induction settings are recorded design facts, not a string-to-score replacement for unmeasured protein abundance.

For a functional-loss claim with measured reference `W`, perturbed `K`, and restoration `R`, the numerical combination in the cross-case sheet is:

`q_point = θ × r × C × I × H`,

where `θ=(W−K)/(W+K)`, `r=clip(1−|R−W|/|W−K|,0,1)`, and `I=clip(1−B/|W−K|,0,1)`. `B` is an endpoint-scale bound from actual controls on unintended explanations. The complete joint uncertainty treatment, the correspondence product `H`, and the bounded aggregate are defined in `a106_numerical_sheet.md`; this packet supplies source inputs, not an alternative total grade.

The absence of a quantified E9 phenotype change is not evidence that the Cas2 component contributes nothing. It challenges the narrower inference that the particular residue is indispensable under the tested expression regime. To challenge **nuclease necessity**, the experiment must also establish the perturbation's remaining nuclease capacity in the relevant assayed protein/conditions. That missing `P_activity` cannot be replaced with the mutation's sequence confirmation. Likewise, a downstream acquisition loss does not establish which protein directly catalyzes strand transfer.

For a precisely scoped necessity claim that predicts an oriented contrast of at least `θ_required`, a future numerical negative result can be scored as:

`q_counter = −max(0, θ_required−θ_upper) × P_effective × C × I_cancel × H`.

Here `θ_upper` is an uncertainty/censoring upper bound, `P_effective` is the measured degree of the **claimed molecular perturbation**, and `I_cancel` bounds unintended changes that might hide the predicted phenotype. No factor is populated from “similar to WT” here. `θ_required` is an explicit scientific requirement attached to that necessity claim, not a universal number chosen after seeing the result. The sheet contains a complete synthetic calculation of this form, clearly separated from these published observations.

## Complementary evidence, transfer and unanswered inputs

Pull-downs and assembly controls narrow an alternative explanation of the cellular endpoint; they do not automatically provide independent acquisition replications. In particular, normal retention in one Cas1 mutant's gel-filtration assay does not validate every Cas2 mutant's folding. A quantitative dose–response and matched protein measurements could address the expression question. A calibrated acquisition assay could supply `W,K,R` and their shared-control covariance. A direct, relevant Cas2 residual-activity assay could populate the activity-specific perturbation extent.

The study itself notes variation of inter-protein contacts across homologs. Thus transferring a residue-specific inference needs actual mapping of the implicated positions, partner/interface context and tested system. A broad name “Cas2” is insufficient. For the supplied target here, sequence/structure correspondence and system overlap are unmeasured, so `H=null`; no ybhP result is inferred. The complete sheet supports experiments on relevant homologs without requiring an initially named function or public identifier.

## Exact targeted-reader return fields

Unimplemented readers would populate: `protein_donor`, `recipient_background`, `cas_genes_present`, `constructs_per_arm`, `intended_change`, `coexisting_same_protein_wt`, `endpoint_kind`, `eligible_numerator`, `eligible_denominator`, `normalization_to_OD`, `PCR_efficiency_by_product`, `calibration_curve`, `detection_limit`, `detection_limit_unit`, `independent_culture_ids`, `shared_control_ids`, `raw_replica_values`, `residual_activity`, `residual_activity_reference`, `residual_amount`, `restoration_amount`, `joint_uncertainty`, `selected_clone_sampling`, `listed_spacer_count_by_length`, and `listed_spacer_count_by_source`, each with exact source locator and unknown reason. These fields are inputs to the defined cells, not a generic independent reader design.

Finite remaining empirical gaps: no calibrated acquisition frequencies or raw replicate distribution; no quantified detection limit; no matched numerical protein ratios for key Cas2 variants; no relevant E9 residual nuclease measurement; no quantitative target correspondence; and unknown identities/dependence among listed clones. This source's complete `q` remains unpopulated while its actual numeric subcells and constraints are usable.

## Inspection and reset coverage

Inspected complete retained main narrative and Online Methods, all main figure captions, images of Figures 1, 3 and 4, complete Supplementary Table 1 and complete captions for Supplementary Figures 1–3 and 5. Supplementary alignment figures and uncropped image details were not independently interpreted. The main output's truncated locus-binding paragraph was reread in full at lines 44–48, with adjacent passage and tail read as well. All authority files listed by local AGENTS.md were then reread completely, including SOURCE_CORRECTIONS.md, the A105/A106 assignment boundary and active ten-axis goal. Latest human/parent steering was read last, before this interpretation. Counts/fractions are checked in the standalone arithmetic record; no source paper, prior research record or production component is edited.

## Additive calculation-reference update

The current complete formula and reader specification are `a106_numerical_sheet_002.md` and `reader_io_002.md`. They retain this packet's unknown values while specifying separate perturbation/restoration nuisance bounds and applying joint uncertainty once after aggregation. The original cross-case drafts are preserved. Exact arithmetic checks of the listed source counts/fractions and explicitly synthetic examples passed; no biological result or complete Cas2 score is invented by those checks.
