# A102 draft handoff — metadata and completion boundaries

Current complete proposed sheet: `A102_numerical_sheet_draft_002.md`. Revision 001 is preserved. Revision 002 clarifies feature-denominator indexing, normalization/mapping requirements, empty-panel treatment and synthetic raw-input limits, adds checked uncertainty ranges and corrects a skill link; it changes no source number or scoring parameter.

Paper-specific review order for the coordinator is:

1. `AF2372_sheet_conversion_001.md`, with the prior worker's retained packet limitations. Complete authority reset follows that paper-specific read.
2. `MJ0226_sheet_conversion_001.md`, including its appended final-digit transcription correction. Complete authority reset follows that paper-specific read.
3. `A102_numerical_sheet_draft_002.md`, the cross-case sheet and complete mathematical example.

Scientific contents are kept in those files rather than sent through the metadata handoff.

## What is delivered

| Research-draft criterion | Delivered | Boundary |
| --- | --- | --- |
| Typed numerical cells, inputs, units, denominators, maps | Sheet sections 1–3 | Source-side maps and some model operands remain unavailable |
| Explicit bounded sums/products and meaning | Section 4 | Proposed conventions; no adoption or probability calibration |
| Contrasting published rows | Section 6 plus two paper conversions | Published function-specific operands remain null where unreported; no invented full published score |
| Complete numerical compilation | Section 7 and `checked_examples_001.json` | Complete synthetic example, explicitly separated from scientific evidence |
| Uncertainty, contradictions, scope and duplication | Sections 5, 7–8 | Conditional bounds and explicit profiles; no universal cross-profile calibration |
| Source-to-cell trace and coverage | Section 9; `inspection_coverage_001.json` | One retained packet, one new complete primary text, one figure, focused metadata and official score documentation |
| Exact future reader inputs/outputs | Section 10 | Specification only; no reader implementation |
| Conversation feedback and user adoption | Parent work | Printing the useful formulas/examples and incorporating feedback remains necessary; file creation does not satisfy it |

## Actual checks

`python3 check_examples_001.py` completed successfully with 43 research arithmetic and consistency checks. It used fixed declared values and synthetic landmarks; it did not read scientific sources, run alignments, implement a generic scorer, or execute runtime tests. Results are `arithmetic_checks_001.json` and `checked_examples_001.json`. `revision_consistency_002.json` records the clarification checks. Existing authority files matched the read-time hashes during the final preservation check.

Inspection/reset coverage is recorded in `inspection_coverage_001.json`, `authority_reset_001.json` and `authority_reset_002.json`. The first combined output had truncation; its lost JSON tail and authority text were reread in full. A later combined output truncated an unrelated, previously covered code excerpt; the authority output itself was complete. The source access and figure limitations remain explicit.

Focused RCSB queries used [rcsb-pdb-skill](/home/chia/.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills/rcsb-pdb-skill/SKILL.md). No external messages were sent through that skill. The queried metadata and web source extracts are retained under `sources/`.

## Exact incompleteness

No equation remains unspecified **within the proposed RMSD profile and the same-map bidirectional-TM profile**. Missing inputs produce declared nulls and/or bounded results. The remaining missing published calculations require unavailable exact site/atom maps, comparison chains/states, domain denominators and a compatible function-contrast panel; their operands were not invented. The source rows' algebra does not validate true-structure error or functional transfer.

No common calibrated conversion between TM and the proposed RMSD units is supplied. Mixed-profile panels are explicitly left separate with no combined point result. That is a stated scope of the proposal, not a hidden unspecified coefficient. DALI Z is preserved; native DALI RMSD/count data use the RMSD profile, while a Z-only excerpt lacks the requested geometric operands and cannot be given a fabricated geometry score.

The user's judgment remains necessary for the chosen distance scales, feature-set normalization, evidence pooling and contrast margin. No runtime, prompts, readers, permanent instructions, publication, hypervolume or scientific episodes changed. This is a complete research draft with declared source-data limitations, not an accepted or implemented evidence axis. A105 remains first and unfinished; 0/10 completion accounting is unchanged.
