# Actual read coverage

The initial authority read was completed through terminal output in sequential
complete portions; no output was truncated. The first attempted metadata count
used unavailable `python`; it read nothing. It was repeated using `python3`.

| Authority | Complete coverage in initial read |
|---|---:|
| Attached pasted-text-1.txt | 1–15 |
| Root AGENTS.md | 1–188 |
| GOAL.md | 1–94 |
| docs/EPISODE_STRUCTURE.md | 1–180, 181–351 |
| docs/TIME_AWARE_ESTIMATION.md | 1–194, 195–388 |
| docs/TOOL_KNOWLEDGE.md | 1–224 |
| docs/TASK_AND_STEERING.md | 1–157 |
| TASK_AND_STEERING amendment 001 | 1–31 |
| EVIDENCE_AXIS_REVIEW amendment 001 | 1–9 |
| VERBATIM_DIRECTION.md publication 2026-10-23-002 | 1–27 |
| VERBATIM_RECOVERY_002.md, same publication | 1–110, 111–215 |
| EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS amendment 001 | 1–150, 151–288 |
| scoring_sheet_numeric_review_002.md | 1–55 |
| Local research AGENTS.md | 1–148, read last among files |
| SOURCE_CORRECTIONS.md | 1–36 |
| A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md | 1–118 |

The latest human direction in GOAL_AND_CRITERIA_001.md was displayed after the
file read. The parent task brief is retained in the conversation and reviewed
with that direction.

Additional design inspection: NUMERICAL_SHEET_001.md lines 1–255, complete
SHEET_QUALIFICATIONS_002.md, READER_CONTRACTS_001.md and
A108_PARENT_NUMERICAL_REVIEW_001.md. The joined draft's paper-specific section
was deliberately not opened. These definitions and synthetic examples are not
claimed as fresh primary-paper inspection.

An initial JSON shape inspection also displayed the retained AF2372 record,
including its abstract-only evidence summary (DOI 10.1074/jbc.M201042200).
It is not a selected case, and no scoring inference is made from it. This
incidental packet inspection is counted as requiring its own complete reset
before another case is opened. The reset will be recorded additively below.

## Reset R0: after incidental AF2372 packet

All 16 authorities in the initial table were reloaded and read in full. The
combined first output omitted approximately 190 tokens at the beginning of
EPISODE_STRUCTURE; that entire 351-line file was reread in the next call.
A later combined output omitted approximately 58 tokens in the numerical
review table; its complete 55-line file was reread. TIME_AWARE_ESTIMATION was
read as 1–194 and 195–388. Other files were complete. Latest human direction was
displayed again after the repair. AF2372 is not used for a scoring conversion.

## Primary inspection P1 and reset R1

DOI 10.1073/pnas.1211002109: online metadata confirmed the source identity;
the initial PMC open returned a browser check. The retained primary text was
then read at lines 1–160, 161–450 and 451–730. These portions include complete
main Results, Discussion and Methods, but not the supplement or all references.
No existing paper-specific conversion packet was used.

All 16 authorities were reloaded after P1. A large combined output was truncated
inside EPISODE_STRUCTURE through the beginning of TIME_AWARE_ESTIMATION; the
entire EPISODE_STRUCTURE file and TIME_AWARE_ESTIMATION lines 1–25 were reread
to repair that exact gap. The remaining time-awareness text was present in the
combined output. All remaining files were read completely in smaller calls.
Latest human direction was displayed last, immediately before writing
PAPER01_PORPHYRAN_001.md. No new paper was opened during this reset.

## Primary inspection P2 and reset R2

DOI 10.1073/pnas.0809467105: the web PMC endpoint returned a browser check;
Europe PMC fullTextXML returned HTTP 500. A direct PMC HTML response with the
`?pdf=1` query supplied the article. The first text extraction attempted an
unavailable bs4 import after saving the HTML; a standard-library HTMLParser then
extracted the text. No failed response was interpreted as article content.

Main primary text was read at 124–307, 308–500 and 501–529, covering the complete
main Results, Discussion and Methods. A targeted search had previously located
the relevant sections. No supplementary figures, original microarray dataset,
second cellular_cdv paper or existing conversion packet was read.

All 16 authorities in the initial table were then read completely. The episode
structure file was split 1–180 and 181–351; other files were complete. There was
no truncation in this reset. Latest human direction was displayed last,
immediately before writing PAPER02_CDV_001.md.
