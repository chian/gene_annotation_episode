# Inspection and authority-reset provenance

Research date: 2026-10-23 America/Chicago (arithmetic/write checkpoint
2026-10-24T00:50:56Z). Owner: fresh one-paper worker `a105_tria_case_006`.
Exclusive output directory:
`research/experimental_scoring_review_2026-10-23/a105_tria_case_006/`.

## Source scope actually inspected

One assigned primary paper: DOI 10.1128/JB.183.8.2405-2410.2001,
PMCID PMC95154. The complete article body was read: abstract, introduction,
all Materials and Methods subsections, all Results subsections, Discussion,
acknowledgments and reference list. Table 1 and its footnote were read in the
original PMC article. Figures 1–4 were visually inspected. Figure 3's differing
residues were inspected again in the original image-server tiles; Figure 4's
axis units were inspected in original tiles. These are views of the same paper,
not additional papers or new experiments. No plotting or image editing was used.

Access route:

- DOI web search located the PubMed, PMC and publisher records. An initial
  guessed PMC95115 URL returned a browser-check page; it supplied no evidence.
  The correct PMCID was then obtained from the DOI's PubMed result.
- `https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/` supplied complete original
  text and Table 1 through the web tool and a retained HTML download.
- PMC figure-page links returned browser-check pages; the article's original
  CDN JPEGs and NCBI tile-image endpoints were downloaded and inspected instead.
- The PMC PDF request returned HTML, not a PDF. Europe PMC and publisher PDF
  requests returned HTTP 403. **No PDF was read or claimed read.** The failed
  response is retained with an HTML name rather than passed off as a PDF.
- `source/PMC95154_fulltext.txt` is a local HTML-to-text extraction for custody;
  article body reading used the original rendered web text. The reference-list
  tail was read from the local extraction. No source cited by the article was
  opened for its scientific evidence.

The original tile service reported Figure 3 at 3901×4110 pixels; six tiles from
its 25% level were inspected at the printed difference positions. Figure 4
reported 3513×2777 pixels; two tiles from its 25% level were inspected for the
axis label. Source-manifest URLs and byte digests identify the retained objects.

The optional older packet
`a105_target_relevance_003/01_tria_atza_target_correspondence_001.md`, the earlier
reaction-lane TriA packet, and the old `case_records.json` evidence entry were
not read in this workload. The assignment supplied the DOI directly, and this
worker went to the original source. No old ordinal grades were imported.
`SOURCE_CORRECTIONS.md` was read completely before the primary paper; its YeaG
correction was not converted into A105 evidence.

## Complete authority set actually read and reread

The following files were read in full before the paper and **again after** the
primary paper's final Figure 4 inspection, before task-specific scoring
interpretation. The after-paper reset used separate, bounded-output reads;
none of the after-paper reads was truncated. Each file is listed explicitly
to distinguish the actual reread from a summary or remembered instruction.

| Order in after-paper reset | Complete file |
|---:|---|
| 1 | `AGENTS.md` |
| 2 | `GOAL.md` |
| 3 | `docs/EPISODE_STRUCTURE.md` |
| 4 | `docs/TIME_AWARE_ESTIMATION.md` |
| 5 | `docs/TOOL_KNOWLEDGE.md` |
| 6 | `docs/TASK_AND_STEERING.md` |
| 7 | `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md` |
| 8 | `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md` |
| 9 | `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md` |
| 10 | `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md` |
| 11 | `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md` |
| 12 | `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md` |
| 13 | `research/experimental_scoring_review_2026-10-23/AGENTS.md`, including all subsequent user quotations |
| 14 | `research/experimental_scoring_review_2026-10-23/A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md`, including A105/A106 steering |
| 15, last human instructions | `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt` |

Initial onboarding attempted a batch whose combined display was truncated;
that attempt alone was not counted as a full read. Its contents were recovered
through subsequent nontruncated output: GOAL/EPISODE_STRUCTURE, then separate
TIME_AWARE_ESTIMATION, then TOOL_KNOWLEDGE/TASK_AND_STEERING. The remaining
authority groups were read fully. The later complete after-paper reset is
independent of that onboarding correction.

After the main design/instruction reset and before the final current-human
instruction files, the entire source-free
`a105_target_relevance_003/UNCALIBRATED_CORRESPONDENCE_CONVENTION_002.md` was read.
It contains mathematical definitions and explicitly synthetic examples, not a
second paper. The final research AGENTS, assignment and goal attachment were
then read in full, with the goal attachment last, immediately before numerical
interpretation and writing.

The parent assignment further restricted this worker to one primary source,
required source-grounded numerical rows and exact denominators, prohibited
invented S/B values and single-substitution function probabilities, and requested
completion coordination by filenames and inspection status only. Those
constraints were retained; no paper facts were sent in a parent message.

## Task-specific reset summary

Exactly three responsibilities remain: investigation prompt, numerical sheet,
and separate readers that populate it. This workload concerns the sheet.
Measurements are mapped into actual numerical cells and combined explicitly
where operands are known. Comparability outside the intended variable and
isolation of the effect stay separate. Missing uncertainty and source-score
operands stay unknown. A105 concerns molecular conversion, transport and
binding; engineered-mutant causality belongs to A106. The paper does not define
the user's scoring template or its weights. This source review does not
complete a scoring sheet or change the ten-axis completion count.

## Verification actually performed

Executed with Python 3 standard library:

```
python3 research/experimental_scoring_review_2026-10-23/a105_tria_case_006/check_arithmetic_001.py
```

Successful result: 16 substrate rows, all six pairs of four positive rates,
seven inhibition rows, sequence count/denominator checks, pmol-to-nmol limit
conversion and convention arithmetic. It preserves null statistical/source-score
outputs. The script writes `arithmetic_checked_001.json`. This is an arithmetic
checker over a manual primary-source transcription, not a reader implementation
or an independent scientific validation of the measurements.

No production tests or scientific jobs were run. No extra paper, calibration
dataset, target homology analysis, protein structure, sequence tool score,
likelihood fit or annotation probability was generated. The absence of a Git
repository at this working directory was reported by a scoped `git status`
attempt; no repository status or diff verification is claimed. All write
operations were restricted to the assigned new directory.
