# A101: TriA/AtzA numerical conversion, parent review 003

Research component proposal. This does not complete A101 or adopt a whole-axis
formula. Existing records, production readers and annotation scoring are unchanged.

## Source and comparison

Primary: Seffernick et al. 2001, DOI 10.1128/JB.183.8.2405-2410.2001,
https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/ . Methods: DNA sequencing;
Results: DNA sequence of triA; Figure 3.

For this sheet the supplied target is the paper's TriA from Pseudomonas sp.
NRRL B-12227 and the comparison protein is AtzA from Pseudomonas sp. ADP.
This orientation is a research convention, not a reconstructed search query.
The paper reports the GCG software suite, but not its particular program,
version, substitution matrix, gap settings or a native raw, bit or E score.
No missing score is inferred from the rounded identity percentage.

## Numerical cells and their roles

| Cell | Source input and calculation | Value | Use in the scoring sheet |
| --- | --- | ---: | --- |
| Compared protein positions | Figure 3, residues 1–475 in both proteins | 475 pairs | Exact compared extent; terminal stop is excluded |
| Differences | Nine boxed substitutions | 9 pairs | Observed differences, not experimentally defined functional sites |
| Identical positions | 475 − 9 | 466 pairs | Numerator for exact identity |
| Pair identity | 466 / 475 | 0.981052631579 | Sequence correspondence over this particular alignment |
| Target coverage | 475 / 475 | 1 | Whole supplied target is represented |
| Reference coverage | 475 / 475 | 1 | Whole comparison protein is represented |
| Identical fraction of target | coverage × paired-observation fraction × pair identity | 0.981052631579 | One derived component, not three independent evidence contributions |
| Conditional coding-DNA identity | (1425 − 9) / 1425 | 0.993684210526 | Conditional on the stated common coding span; not a second independent protein comparison |
| Functional-site agreement | Required site set and validated mapping not supplied | unknown | Do not turn the postselected nine differences into a 0/9 functional score |

The nine AtzA→TriA changes are F84L, V92L, E125D, T217I, T219P, I253L,
G255W, N328D and S331C. This paper does not establish the causal contribution
of any individual substitution. That would require separate experiments and
does not become an A101 measurement merely because the proteins differ there.

For disjoint displayed blocks b, the correct recombination is

    sum_b (paired_positions_b / 475) * (identical_positions_b / paired_positions_b)
      = sum_b identical_positions_b / 475
      = 466 / 475.

These are printing intervals, not biological domains. The final block has 25
positions; weighting it as though it had 50 produces a different and incorrect
whole-alignment identity. Overlapping or duplicate descriptions are reconciled
by physical coordinate before either numerator or denominator is counted.

## Function, experimental comparability and effect isolation

The paper's TriA and AtzA preparations are separate, not two proteins intentionally
co-mingled in one assay. TriA was expressed from pJS3 in E. coli DH5α; TriA
substrate specificity used a partially purified preparation, while AtzA
competition assays used highly purified enzyme. Common buffer and iron treatment
do not establish equal active protein amounts or equal purity. The experiment's
question is the activity of the proteins, not whether their sequences are equal.

The direct TriA reaction measurements and detection limits belong to A105.
They qualify transfer of a precise reaction from AtzA without rewriting the
observed 466/475 sequence identity. Earlier AtzA substrate exclusions cited in
this article remain attributed to the earlier paper; they are not newly assayed
here. No raw rates are added to the A101 numerical component.

The implication for the eventual combination is precise: whole-sequence identity
can supply a correspondence operand but cannot alone establish that the target
performs the comparison protein's exact reaction. Broad family correspondence
and discrimination between characterized reaction alternatives require scoped
operands. The paper does not supply an alternative-family score margin, a
calibrated function probability or an experimentally defined discriminating site
set. Those cells remain unknown, rather than being invented to make a final
coordinate computable.

This case contrasts with the already reviewed QueF-like pocket/domain case and
the CodA source-identification case. It does not authorize replacing any native
score with a categorical function-transfer judgment. A101 compilation is being
specified separately from these source-derived components.

## Uncertainty, repetition and exact population fields

Counts are exact arithmetic conditional on the published alignment. Base-call,
alignment and protein-identity error distributions are not reported. Do not
attach a binomial confidence interval to these 475 evolutionarily dependent
positions or interpret absence of an error model as zero uncertainty. The
paper's duplicate, both-strand sequencing and overlapping genomic fragments
verify the sequence in a different way; they do not create independent homologs
or 1800 distinct covered nucleotides. The nine nucleotide differences being
nonsynonymous does not supply dN/dS.

A reader can populate integer target/reference lengths, unique residue-pair
coordinates, residue identities, gap/ambiguity counts and the native score fields
when actually present. The calculations above consume these cells. Required
functional positions, comparison program/settings, native scores and score-error
distributions remain nullable with explicit reasons. Source IDs and experimental
identity support custody and dependence; they do not become score operands.

## Inspection and arithmetic provenance

Parent inspected the worker's complete component packet and cells; read the
primary article's Abstract, Introduction, Methods, Results, Discussion and
references through overlapping web opens; and viewed the retained full Figure 3.
This review did not open external sequence records or perform a new alignment.
No claim of fresh parent inspection of Figures 1, 2 or 4 is made here. The
initial combined cells output was truncated; three sequential reads covering
lines 1–800 repaired it through the actual file end.

Before this conversion, parent completely reread AGENTS.md, GOAL.md,
EPISODE_STRUCTURE.md, TIME_AWARE_ESTIMATION.md, TOOL_KNOWLEDGE.md,
TASK_AND_STEERING.md; both task/steering and evidence-axis amendments;
VERBATIM_DIRECTION.md and VERBATIM_RECOVERY_002.md; the complete evidence-axis
library instructions; the numerical review002 template; the research AGENTS.md,
SOURCE_CORRECTIONS.md and A105 assignment/boundary brief. The active goal
attachment and latest human reminder were read last. All reset outputs were
untruncated. The all-ten goal supersedes the older A105-only assignment scope.

`check_tria_source_cells_003.py` independently reconstructs the count arithmetic
and coordinate reconciliation, checks agreement with the retained cells and
preserves unavailable native scores. Its separate immutable receipt is
`tria_parent_arithmetic_003.json`. It is arithmetic on published inputs, not a
production-reader test, new biological observation or completed A101 sheet.
