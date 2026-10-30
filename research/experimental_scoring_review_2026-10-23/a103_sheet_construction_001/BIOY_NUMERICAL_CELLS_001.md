# A103: BioY context, parent conversion 001

Numerical-sheet research proposal. Existing records, production scoring,
readers, prompts and episode behavior are unchanged. A103 is unfinished.

## Actual comparison and source

Hebbeln et al. 2007, DOI 10.1073/pnas.0609905104,
https://pmc.ncbi.nlm.nih.gov/articles/PMC1815280/ . The relevant A103 observations
are genomic arrangements among retained BioY homologs, not their uptake rates.
The comparative Results and Methods report a survey of complete/nearly complete
genomes using SEED and PFAM. One representative was retained from BioY groups
exceeding 98% amino-acid identity. This filter describes the sample; it does not
prove independence of the retained genomes.

The separate experimental comparison expressed R. capsulatus SB1003 genes in
E. coli S1039, which lacks high-affinity biotin uptake. Both BioY-alone and
BioMNY conditions contain BioY. These are not a deliberate mixture of wild-type
and mutant BioY. A TTG-to-ATG initiation-codon change was made for expression.
Host contribution and expression differences therefore matter to experimental
interpretation. Direct transport and perturbation results are not extra A103
genomic observations.

## Numerical cells supported by the inspected article

| Cell | Input / calculation | Result | Numerical role and limit |
| --- | --- | ---: | --- |
| Retained BioY genes | Comparative Results | 150 | Gene-level sample count; not 150 independent genomes |
| Represented genomes | Same paragraph | 127 | Different counting unit from the gene-level numerator |
| Genes per represented genome | 150 / 127 | 1.1811023622 | Copy redundancy diagnostic, not a support multiplier |
| Excess retained copies over one per represented genome | 150 − 127 | 23 | Does not identify how many genomes have multiple copies |
| BioY association with BioMN | Reported approximately one-third | approximate fraction only | Exact numerator is unavailable; do not replace it with 50 |
| Spatial distances/strands and comparison windows | Not supplied in the inspected numerical text | unknown | A diagram or “linked” statement does not supply exact bp endpoints |
| Same endpoint among matched background loci | Not supplied | unknown | Needed to distinguish enrichment from a common arrangement |
| Historical complete A103 coordinate | Essential association/background operands missing | unknown | No point grade is manufactured from the approximate fraction |

The score must bear on the proposed relation. Lack of linked BioMN can oppose
a claim that every BioY has that particular adjacent module. It is not by
itself evidence against BioY-mediated uptake: the source distinguishes transport
from a module-dependent transport property. Genome absence, lack of adjacency,
lack of expression and lack of transport are different observations.

## Explicit component calculation for review

The A103 worker proposes a normalized excess/depletion calculation. For the
same declared spatial endpoint in matched foreground and background cohorts,
let p=k/n and b=k0/n0. Then

    g(p,b) = 0                    when p=b
             (p-b)/(1-b)         when p>b
             (p-b)/b             when p<b.

This is a proposed scoring transformation of actual frequencies, not a
confidence probability or a fraction reported by this paper. Branch conditions
keep denominators nonzero. In the single matched-stratum example below,
comparison overlap is C=1 and t=C*g=g. Its single-question coordinate under the
worker's proposal is max(t,0)*(1-max(-t,0)); signed opposition is retained.

All exact cohort counts in the next table are **synthetic**, not a reconstruction
of the article's approximate one-third. The foreground spatial relation occurs
in 3 of 9 eligible independent-block representatives in both examples.

| Synthetic comparison | Background | Calculation | Signed result | Single-question coordinate |
| --- | --- | --- | ---: | ---: |
| Arrangement rare in background | 1/10 | (1/3−1/10)/(1−1/10) | 7/27 = 0.2592592593 | 0.2592592593 |
| Arrangement common in background | 5/10 | (1/3−1/2)/(1/2) | −1/3 | 0, with opposition retained |

The same foreground fraction supports opposite association directions under
these different measured backgrounds. This is why converting the historical
one-third directly into one-third annotation credit would omit a substantive
calculation. It is not a reason to replace available native context scores with
an LLM judgment. A native score is another explicitly scoped route, to be
reviewed separately, not a second independent vote for the same observation.

Sampling comparability and association magnitude remain separate. The worker's
multi-stratum proposal computes overlap from actual foreground/background
sampling proportions and multiplies it by a within-stratum association
contrast. Neither matching strata nor a native association score establishes
causal isolation of a protein's activity.

## Missingness, dependency and exact future population

For an enumerated cohort of 10 with three positives, six observed negatives and
one unresolved locus, p lies in [3/10,4/10]. Against a known background of 1/10,
g lies in [2/9,1/3]; no midpoint is supplied. This is an identification bound,
not a sampling-confidence interval. An incomplete assembly is not an observed
negative, and an unknown denominator is not zero opportunities.

A future reader must populate the actual assembly/locus pair, coordinate/strand
data, endpoint definition, eligible denominator, observed-positive/negative/
unresolved membership, comparison population, dependence blocks and sampling
strata. These fields determine k/n, b and overlap; they are not independent
confidence grades. Native context scores additionally retain the actual tool,
channel, version, pair, numerical value and scope. Source names themselves do
not enter the arithmetic. Reader implementation is outside this research task.

The missing spreadsheet is the direct next source for the old cohort identities.
It would not by itself supply a matched null population or prove independence.
Repeated article/table representations, paralogous copies and overlapping
windows must not be treated as independent genomes. No binomial standard error
is inferred from 150 related gene entries or an approximate proportion.

## Parent inspection and reset

Parent read the complete worker `paper_01_bioy.md`, then the primary Abstract,
Introduction, all Results, Discussion, Methods, figure captions and references
through overlapping web opens. No fresh visual inspection of figures or
supplement spreadsheet is claimed. The PNAS historical SI link redirected to
the article; PMC spreadsheet/index links returned browser challenges, and the
SI PDF link returned a download placeholder. No challenge was bypassed and no
spreadsheet contents were obtained.

Parent then completely reread root AGENTS.md and GOAL.md; EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, TOOL_KNOWLEDGE and TASK_AND_STEERING; the task/steering
and evidence-axis amendments; VERBATIM_DIRECTION and VERBATIM_RECOVERY_002;
the complete evidence-axis library instructions with corrections; numerical
template002; research AGENTS, SOURCE_CORRECTIONS and the A105 assignment/boundary
brief. Active goal and latest human/continuation direction were read last.
All reset outputs were untruncated. Interpretation above followed that reset.

Parent subsequently read the general formula and synthetic/dependency sections
of the A103 draft, excluding its second-paper/current-data table. The RibK
scientific packet is not reviewed by this conversion. `check_bioy_context_001.py`
checks the source count arithmetic and clearly separate synthetic comparisons;
`bioy_parent_arithmetic_001.json` retains the result. No genome analysis,
production reader or scientific episode was executed.
