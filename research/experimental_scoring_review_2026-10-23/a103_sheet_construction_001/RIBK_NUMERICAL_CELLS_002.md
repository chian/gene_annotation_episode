# A103 parent conversion: RibK and a separate native neighborhood score

New parent research record, 2026-10-23. Earlier packets and instructions remain
unchanged. This is numerical-sheet research, not a production reader, scoring
policy adoption, annotation run or completed evidence axis.

## Inspected material and reset

The parent read the complete `a103_numerical_sheet_011/paper_02_ribk.md`, the
retained full main-article text in `ribk_primary_body.txt` (abstract, introduction,
interleaved Methods/Results, Figure 1 caption, addendum and acknowledgments), and
the separate native-score notes. No new visual review of Figure 1 or review of
the cited papers is claimed. The browser PMC endpoint returned a challenge; the
existing retained article body was used, without bypassing that challenge.

Primary: Mashhadi et al., DOI 10.1128/JB.01900-07,
https://pmc.ncbi.nlm.nih.gov/articles/PMC2293203/ .

After this paper-specific inspection, before this conversion, the parent read
the following complete documents without truncation:

- root `AGENTS.md` and `GOAL.md`;
- `docs/EPISODE_STRUCTURE.md`, `docs/TASK_AND_STEERING.md`,
  `docs/TIME_AWARE_ESTIMATION.md` and `docs/TOOL_KNOWLEDGE.md`;
- `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md` and
  `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`;
- publication `2026-10-23-002/VERBATIM_DIRECTION.md` and
  `VERBATIM_RECOVERY_002.md`;
- `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`;
- `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`;
- research `AGENTS.md`, `SOURCE_CORRECTIONS.md` and
  `A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md`;
- the active goal attachment, followed last by the current human instruction:
  “Remember a goal is a goal - so you have to set the goal and the goal criteria
  more than the instructions”.

The active all-ten-sheet goal supersedes the historical A105-only workload
restriction; the separation of A105 from A106 remains binding.

The parent separately checked STRING's official API output-field table and FAQ
score-column definitions. A combined web output was truncated; the relevant
field definitions were recovered in a second focused call. Complete manual-page
inspection is not claimed.

## Experimental definitions

The characterized protein is MJ0056 from *Methanocaldococcus jannaschii*.
Expression/purification in *E. coli* and the activity assays are separate from
the genomic-arrangement observation. The cell-extract comparison uses other
expressed enzymes, not a matched RibK replacement experiment; endogenous host
enzymes remain possible contributors to the extract result. These assay facts
are not additional A103 neighborhood evidence.

For A103 the observation is natural genomic arrangement: RibK homologs occur
next to RibB homologs in nine named genomes. No mutant/wild-type mixture,
expression ratio or rescue result is part of that comparison. The paper does
not give the full tested cohort, negative neighborhoods, assembly coordinates,
strand relations, pairwise homology scores or matched background rate in that
paragraph.

## Actual numerical cells

| Cell | Value | Meaning for the sheet |
| --- | ---: | --- |
| Named positive genomes | 9 | Nine reported positive examples, before any dependence-block reduction. |
| Fraction within the named-positive list | 9/9 = 1 | A description of a positively selected list; not genome-wide prevalence. |
| Complete eligible-survey denominator | Unknown | Cannot infer it from the list length. |
| Matched background adjacency fraction | Unknown | Cannot infer zero from omission. |
| Individual distance/orientation | Unknown | “Next to” does not supply base-pair distances or strands. |
| Historical count-route contribution | Point unknown, bounds [-1,1] | Missing denominator/background prevent computing the proposed contrast. |
| Historical A103 coordinate | Point unknown, bounds [0,1] | An unknown point is not a zero score. |

The relation supports a riboflavin-related genomic association. It does not,
on its own, distinguish kinase activity or the preferred phosphoryl donor.
Candidates predicting the same neighborhood receive the same contextual number.

## Separate recorded program output

The worker's `string_ribk_pair.json` records a public STRING API response dated
2026-10-24 02:15:33 UTC. This is a new dataset observation, not the paper's 2008
score. The parent inspected the exact retained pair and fields; it did not rerun
the request. The worker reports API version 12.5; the parent did not independently
retrieve that version endpoint.

| Native field | Recorded value | Numerical role |
| --- | ---: | --- |
| `nscore` | 0.956 | Gene-neighborhood score for `243232.MJ_0055`–`243232.MJ_0056`. |
| `score` | 0.959 | Combined channel score, excluded from A103 compilation. |
| `tscore` | 0.114 | Text-mining score, excluded from A103 compilation. |

For one explicitly scoped neighborhood question with weight 1, the proposed
index yields supporting total 0.956, opposing total 0 and coordinate
`0.956 * (1 - 0) = 0.956`. The API documentation identifies `nscore` separately
from combined, phyletic-profile, coexpression, experimental and text channels:
https://string-db.org/help/api/ . Its FAQ relates neighborhood scores to
intergene nucleotide distances: https://string-db.org/help/faq/ .

That number is not a 95.6% probability of the exact reaction. Mapping a newly
supplied sequence to this database entity remains a separate empirical input;
a gene label is not proof of that mapping. Native biological calibration
uncertainty and direct/transferred provenance remain unreported in this compact
response. Neither receives an invented numerical default.

The nine paper examples and the native neighborhood score are not additive
independent evidence. One context question selects one declared metric route;
the alternate observations remain available with their actual meanings.

## Checked arithmetic and next decision

`check_a103_review_002.py` independently verified the exact pair/selected channel
and the one-question value 239/250 = 0.956, alongside the general formula checks
recorded in `A103_FORMULA_REVIEW_003.md`. No biological analysis was rerun.

The scoring question for review is whether to use the explicitly proposed
weighted-support/opposition index for several distinct contextual relations.
The recorded native single-pair value does not require inventing an overall
applicability grade. Historical missing data stay bounded rather than becoming
an excuse to fabricate a complete past cohort.
