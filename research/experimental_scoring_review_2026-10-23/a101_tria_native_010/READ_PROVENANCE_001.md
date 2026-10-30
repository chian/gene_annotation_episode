# Inspection and check provenance

Owned output directory: `research/experimental_scoring_review_2026-10-23/a101_tria_native_010/`.

The deliverable is a bounded A101 paper-component packet. The active goal remains usable numerical sheets for all ten retained axes, beginning with A105; this packet neither settles the A105 policy nor completes A101. Goal criteria, formulas, limitations and remaining A101 work are stated in `A101_NUMERICAL_COMPONENT_PACKET_001.md`. No goal-status change was made by this worker.

## Source inspection

- Primary: DOI `10.1128/JB.183.8.2405-2410.2001`, PMC95154. Fresh web inspection covered the complete article text: abstract/introduction, every Methods subsection, every Results subsection, Table 1, Discussion, acknowledgments and all 45 references. The web opens overlapped; no article section was omitted by the first result's endpoint.
- Figures 1–4 were visually inspected using retained primary-image bytes. Figure 3 was inspected as a complete alignment display and with six existing enlarged crops covering its boxed substitutions. No new alignment, sequence search, mutation simulation or scientific episode was run.
- The retained article HTML was inspected for source-image, PDF and supplementary links. No separate supplementary alignment was linked there. The current live Figure 3 page returned a browser-check page; the retained Figure 3 image was usable. No claim is made that the current live figure page or a PDF was successfully opened.
- The retained `figure3_zoom.html` was inspected for a larger image link; none was recovered. No raw sequence database record was opened. GenBank accession/version details not given by the paper remain unverified.
- Existing case scope was read from `research/slotted_process_library/corpus/sequence/verified_cases.jsonl` and the corresponding case-index record. The complete retained A101 descriptor at `research/slotted_process_library/publications/2026-10-23-002/entries/A101.json` was read as background, not as adopted scoring authority.
- The earlier A105 paper's source files were reused. Its numerical policy or component packet was not imported. This is not a new paper discovery and no second primary paper was opened.

The image/file hashes are in `source_manifest_001.json`. Those records identify retained source bytes and inspection coverage; they are not score components.

## Authority reset after this paper

Every file below was read completely after the primary-source inspection and before the numerical packet was interpreted/written. The local review AGENTS file was also initially read for its required reset procedure. Original user quotations and subsequent corrections were included, rather than treating headings or summaries as the authority.

| Complete file read | Coverage |
|---|---|
| `AGENTS.md` | 188 lines |
| `GOAL.md` | 94 lines |
| `docs/EPISODE_STRUCTURE.md` | 351 lines |
| `docs/TIME_AWARE_ESTIMATION.md` | 388 lines |
| `docs/TOOL_KNOWLEDGE.md` | 224 lines |
| `docs/TASK_AND_STEERING.md` | 157 lines |
| `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md` | 31 lines |
| `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md` | 9 lines |
| `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md` | 27 lines |
| `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md` | 215 lines |
| `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md` | 288 lines |
| `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md` | 55 lines |
| `research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md` | Complete; no YeaG endpoint was imported |
| `research/experimental_scoring_review_2026-10-23/AGENTS.md` | Complete, including all subsequent verbatim instructions |
| `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt` | Complete, read last among files |

The supplied latest human instruction was then reread last: “Remember a goal is a goal - so you have to set the goal and the goal criteria more than the instructions”. The all-ten goal and the parent's bounded A101 assignment supersede the older A105-only allocation language. No research document is treated as a new runtime approval gate.

Two combined outputs exceeded the execution wrapper's output budget. `EPISODE_STRUCTURE.md` and `TIME_AWARE_ESTIMATION.md` were each reprinted alone in full, repairing the omitted portions. The supplementary A101 descriptor was likewise reprinted alone in full. Untruncated individual reads, not the truncated combined outputs, establish the stated coverage. Per-file hashes and line counts are in `authority_manifest_001.json`.

## Checks and precise scope

Executed once: `python3 research/experimental_scoring_review_2026-10-23/a101_tria_native_010/check_arithmetic_001.py`.

Result: **217 arithmetic/cell-consistency assertions passed**. The retained receipt is `arithmetic_checked_001.json`. It checks integer count reconciliation, all nine coordinate pairs, sums over disjoint printed intervals, exact rational forms, declared fractions and complements, source-percent consistency, missing-value preservation and absence of invented raw/bit/E/profile scores. It does not reread a sequence or run an alignment. It does not establish biological validation, independent replication, production-reader correctness or annotation-credit integration.

Source-access preparation first attempted `python` (not installed) and then `python3` with BeautifulSoup (not installed); standard-library HTML parsing completed the intended link inspection. Neither failed attempt modified source records or required installation.

Only new files in this owned directory were written. Prior packets, production code, prompts, readers, library publications and saved runs were not modified by this worker. No supplemental primary paper, service job or scientific episode was started.

## Read-before-use qualifications

The two `reported_rounding_only` uncertainty labels in `cells_001.json` denote the precision of the paper's integer percentage display. They do **not** assert that the paper disclosed its rounding rule, that rounding is the only biological uncertainty, or that sequence base calls are error-free. The count-derived percentages are consistent with the display; the numerical sequence-error distribution remains unreported.

The source provides strain names and the DH5α host designation, not complete genotype specifications for each native strain or an independently checked full genotype of the expression host. Those unknowns do not affect the displayed sequence counts and must not be invented for experimental comparability scoring.
