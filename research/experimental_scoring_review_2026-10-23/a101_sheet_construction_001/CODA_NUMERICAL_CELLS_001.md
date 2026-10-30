# A101: CodA conversion into numerical cells

New parent research record, 2026-10-23. Earlier records remain intact. This is
one source conversion toward the ten-sheet goal, not a completed A101 sheet or
an adopted annotation formula. No production prompt, reader or scorer changed.

## Actual inspection and required reset

The parent read the complete worker conversion and checked arithmetic, the
complete retained three-page primary article text and six-page supplement text.
It inspected rendered primary page 5556, including the network caption, and
supplement Table S2. The author's primary PDF was also opened through the web
tool. No exact sequences, alignment files, original spectra or raw assay data
were retrieved or analyzed. The parent does not claim to have visually checked
every figure or supplement table merely because the worker did so.

Before this conversion, the parent actually reread the complete authority set
in six nontruncated groups: AGENTS.md and GOAL.md; EPISODE_STRUCTURE.md and
TASK_AND_STEERING.md; TIME_AWARE_ESTIMATION.md and TOOL_KNOWLEDGE.md; both
TASK_AND_STEERING and EVIDENCE_AXIS_REVIEW amendments and both verbatim recovery
records; EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS and scoring_sheet_numeric_review_002;
local research AGENTS.md, SOURCE_CORRECTIONS.md and A105_REVIEW_ASSIGNMENTS.
The active ten-sheet goal attachment and latest user instruction were read last.
The historical A105 assignment does not turn the current A101 work into A105.

## Definition of the evidence comparison

The initial uncharacterized protein was from Picrophilus torridus, expressed in
E. coli. The suggested relationship was to an SAH-deaminase subgroup, including
an author-reported glutamine corresponding to SAH-deaminase His137. The paper
does not provide the target/reference alignment, a pair-specific sequence
score, or an experimentally established molecular activity of that archaeal
protein. Its soluble activity was not isolated from host contributors.

The subsequently identified E. coli CodA is a different assayed molecule. Its
purified activity grounds an experimentally studied reference function. Those
measurements do not fill the absent archaeal sequence-comparison cells. The
paper is not evidence that a specified high sequence score predicted a wrong
function: it does not report such a score.

Source: Hitchcock et al., DOI 10.1021/bi200680y,
[primary article](https://www.chem.tamu.edu/rgroup/raushel/publications/P258-Biochemistry-Isoguanine%20Deaminase-2011.pdf),
[supporting information](https://ndownloader.figshare.com/files/4288957).

## Filled cells and exact scoring role

| Quantity | Actual value and calculation | Role in the numerical sheet |
| --- | --- | --- |
| Network construction cutoff | E-value cutoff 10^-70, Fig. 1 | Search/network parameter only. It cannot fill a particular pair's E-value or alignment score. |
| Reported named-site identity | One specified H/Q comparison: 0 identical / 1 observed site = 0 | Exact identity at this one reported comparison. Neither overall functional incompatibility nor a whole-axis zero follows. Target-coordinate verification is unavailable. |
| Named-site observation coverage | 1 observed / 1 declared site = 1 | Denominator for that exact one-site question. Multiplying by local identity gives 0/1, the same information, not another proof. |
| CodA source-position set | Q156, E217, H246, D313, D314 | Defines five candidate positions for a later sequence mapping. With no target alignment, target agreement and mapping coverage remain unknown. Structural observations retain their A111 origin. |
| Source-identifying peptide coverage | Ten nonoverlapping inclusive intervals contain 142 residues | Identity of the assayed preparation; not homolog alignment coverage. Whole protein length is absent, so no coverage percentage is calculated. |
| Pair raw/bit score, result E-value, target/reference alignment coverage | Not reported for the proposed target comparison | Unknown. The threshold, one site, peptide count and model span cannot replace them. |

The source's substrate-efficiency ratio, calculated from rounded reported
central estimates, is 6.7/1.5 = 4.4667. It is A105 biochemical information about
CodA, not an A101 score. Its reported error meanings and covariance are not
defined here. The knockout evidence remains A106, outside this conversion.

## Component arithmetic the case requires

Use one resolved target/reference alignment mapping. Define:

- L: number of residues in the supplied target material, with fragment versus
  complete sequence preserved.
- A: distinct target residues covered by the selected mapping.
- P: those positions paired to a resolved nongap reference residue.
- I: identical residue pairs among P.

Then target coverage is A/L, pair observation fraction is P/A, and identity
among observed pairs is I/P. Their product is I/L. This is a counted observed
match fraction, not annotation probability. Do not add all four values as
independent support; the fourth is exactly the product of the first three.
Retain reference coverage separately. A fragment's denominator never establishes
whole-protein coverage. Unavailable mappings stay unknown; they are not measured
mismatches. Zero denominators leave the corresponding ratio undefined.

For a predeclared set of R relevant positions, let K be observed mapped pairs
and M be exact matches. Observation coverage K/R times conditional identity M/K
equals M/R. If U = R-K sites are unresolved, complete-set identity is bounded by
M/R and (M+U)/R. These are missing-data bounds, not sampling confidence intervals
or probabilities of function. Substitutions can preserve function, so a count
of exact matches is not a universal biochemical acceptance rule.

Native raw score, bit score and E-value remain separate typed inputs with the
actual program, scoring parameters and search-space definition. They are
different summaries of the same comparison, not three independent experiments.
For competing characterized references, a bit-score difference can be calculated
only from compatible actual scores. This source supplies neither operand.

## Remaining work toward A101

These component formulas provide explicit arithmetic, but this case cannot fill
a complete A101 calculation. Other cases or actual comparison datasets must
supply the native score operands and distinguish region coverage from functional
specificity. Their combination into an annotation coordinate still needs a
defined numerical proposal. No overall correspondence grade or A105 S/B formula
is imported to hide that missing work.

| Follow-up Lane | Annotation question exposed by this case | Numerical inputs needed | Source / available operation category |
| --- | --- | --- | --- |
| Sequence comparison tied to the measured reference function | Does the supplied sequence match the functionally relevant region of a truly characterized reference, and how does it compare with characterized alternatives? | Native pair scores, exact nonoverlapping correspondence, target/reference coverage, mapped functional sites, function-specific reference grounding | This article exposes missing pair operands and host-attribution limits; actual sequence alignment/search outputs would populate the missing comparison cells. No new tool capability or execution is claimed. |

The parent independently checked the interval union, one-site arithmetic and
rounded kinetic ratio. Those checks establish arithmetic and boundary retention,
not homology calibration or A101 completion. Results are recorded separately in
`coda_parent_arithmetic_001.json`.
