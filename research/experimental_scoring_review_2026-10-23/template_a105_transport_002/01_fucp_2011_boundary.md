# FucP 2011: no measured transport quantity in this source

Primary source: Muraoka and Zhang, *Phenotypic and Genotypic Evidence for l-Fucose Utilization by Campylobacter jejuni*, J Bacteriol 193:1065–1075, DOI [10.1128/JB.01252-10](https://pmc.ncbi.nlm.nih.gov/articles/PMC3067607/). This is distinct from the PNAS FucP paper reviewed earlier.

## Actual experimental definitions

The main genetic comparison is C. jejuni NCTC 11168 versus its ΔfucP::cat derivative CjWM114a. Complementation adds fucP alone or progressively more downstream genes at the ribosomal locus. These are separate bacterial cultures, not WT and mutant proteins deliberately coexpressed in one cell. Other proteins, membrane processes and metabolism coexist in every whole-cell preparation. Intended variable: the fucP-containing genetic region. Additional change: the deletion has polar transcriptional effects on cj0487, cj0488 and aldA (Fig. 1B; Results, PR2 locus). Native promoter regulation is not restored by the complementation construct.

Measured outcomes are tetrazolium reduction, viable counts, transcript abundance and colonization; no direct fucose translocation, accumulation time course, flux, transport kinetics or compartment-resolved fucose measurement was found in the complete Methods/Results/Discussion. Growth experiments use 50 mM fucose and three separate experiments; field-isolate growth was tested once per isolate.

Table 4 defines R_fucose as CFU/mL with fucose divided by CFU/mL in basal medium. The turkey fucP-positive isolate has R_fucose = 2.77×10³ and the fucP-negative isolate 1.64. These dimensionless growth ratios are not fucose molecules transported per time. The ratio 2770/1.64 = 1689.024 is a ratio of distinct isolates' growth responses, not transporter specificity. No uncertainty on that derived ratio is available.

## Conversion into the user's A105 sheet

This paper provides a counterexample for the endpoint cell: it cannot fill an A105 transport-activity row from its genetic or growth numbers. Missing activity is `unknown/not measured`, not zero activity, zero reliability or a fixed categorical grade. The genetic contrasts and their polar-effect qualification belong to A106 and are preserved there conceptually; this note does not develop that sheet.

The proposed transport calculation is

`J = d[(n_inside - n_surface - n_trapped_external - n_blank)/recovery]/dt / N_active`,

where amounts are moles, time is seconds, recovery is the measured assay recovery fraction, and N_active is the measured amount of accessible transporter (moles) if the inference concerns molecular turnover. A per-cell or per-membrane-protein denominator is retained instead when that is all the assay measured. This paper supplies none of those fucose amount/time operands. Therefore neither J nor a numerical uncertainty, comparability correction or effect-isolation fraction can be computed.

For an actual transport contrast, nuisance comparability would concern matched accessible transporter amount, energetic gradient, pH, membrane condition, substrate availability and assay recovery, excluding the intended changed variable. Those are not inferred from similar CFU growth. Separate isolation would require subtraction or resolution of surface adsorption, other transport routes and metabolism/trapping. A correction that removes a measured background would enter J once; it would not also be multiplied as a second penalty.

Explicit combination proposal for a future valid measurement: propagate independently measured nuisance corrections multiplicatively inside J and measured background contributions additively in its numerator; use their full covariance to calculate uncertainty of the final contrast. A numerical annotation contribution cannot be obtained from this source without the absent activity and source-to-target response relationship. This is a genuine gap, not permission to insert a relevance weight. The target need not be related only by sequence, but this paper alone supplies no quantitative relationship to the project's supplied target.

Complementary experiment: measure labeled fucose movement in a controlled membrane preparation or quantified early whole-cell uptake, with paired surface/trapped-label controls, a time course, protein normalization and explicit metabolic trapping assessment. Such data would fill A105 without converting growth to flux. The existing PNAS source may provide other measurements, but its numbers were not reopened or pooled here.

## Read/reset provenance

Primary evidence was read first via PMC and the retained full HTML text in this directory. A truncated combined paper/authority output was repaired by a complete Discussion read and complete reread of AGENTS.md + GOAL.md + EPISODE_STRUCTURE.md. The full authority set was then read before this interpretation: root AGENTS.md; GOAL.md; EPISODE_STRUCTURE.md; TIME_AWARE_ESTIMATION.md; TOOL_KNOWLEDGE.md; TASK_AND_STEERING.md; TASK_AND_STEERING amendment001; EVIDENCE_AXIS_REVIEW amendment001; VERBATIM_DIRECTION.md; VERBATIM_RECOVERY_002.md; EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment001; scoring_sheet_numeric_review_002.md; SOURCE_CORRECTIONS.md; complete local AGENTS.md; A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md; TEN_SCORING_SHEETS_GOAL_2026-10-23_001.md. The 18-token truncation around TIME_AWARE_ESTIMATION lines 368–371 was repaired by reading lines 350–388 in full. Latest task directions were read last. No next paper had been opened when this note was written.

This is research only; no production scorer, reader, prompt or run changed.
