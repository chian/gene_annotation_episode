# A110 preparatory research handoff

Status: PROPOSED numerical sheet for feedback. A105 remains first in the ten-sheet completion accounting, still 0/10. No acceptance or implemented-axis claim.

| Deliverable | Path |
|---|---|
| Joined sheet, numerical definitions and explicit compilation | `A110_NUMERICAL_SHEET_PROPOSAL.md` |
| Print-ready formulas, filled examples and choices for feedback | `PRINT_READY.md` |
| Exact targeted future reader IO; all UNIMPLEMENTED | `reader_io.md` |
| Components traced to inspected sources | `component_source_table.md` |
| Separate NfnAB source conversion | `paper_01_nfnab.md` |
| Separate UbiUV source conversion | `paper_02_ubiuv.md` |
| Complete authority/reset read record | `authority_reads.md` |
| Arithmetic verification and machine-readable outputs | `check_arithmetic.py`, `arithmetic_results.json` |

Primary sources: DOI 10.1128/JB.00612-10 (NfnAB); separate affiliation-only correction 10.1128/JB.02550-14; DOI 10.1073/pnas.2321242121 (UbiU/UbiV oxygen donor). Seed case metadata was read, not rejected old grades.

NfnAB coverage: complete main Methods/Results/Table 1/all figure captions/Discussion and full correction; plot pixels not digitized. UbiUV coverage: complete main article/captions, main Fig. 4 image, SI pages 1–9 and rendered Fig. S3 page 5; SI pages 10 onward uninspected. A later retained Fig. 4 check received its own complete authority reset. Each primary/retained packet was followed by full listed authority rereads, latest goal and latest human direction last. Actual read records are preserved.

Missing-input categories: NfnAB actual consumed amounts, gas/readout recovery and between-preparation n/variance; UbiUV raw isotope replicate values/covariance, higher baseline bins, intracellular donor enrichment and isotope-specific recovery; native pathway capacity/demand measurements and a defined UbiUV electron acceptor. Unknowns produce declared conditional points or bounded results, not synthetic measured facts.

Verification: `python3 research/experimental_scoring_review_2026-10-23/a110_chemical_sheet_016/check_arithmetic.py` passed 150 assertions. They check exact source-derived ratios, proposed signed contrasts, isotope prediction distributions and moments, interval enclosures, formal atom/charge/electron arithmetic, normalization, replication identity, repeated-representation invariance and synthetic boundary cases. The script is research arithmetic only; no production tests or target scientific program ran.

The complete conditional NfnAB reaction-account compilation is available for printing. UbiUV contains source-populated numerical cells and explicitly limited plot-derived contrasts, with full-pattern and native-budget operands missing. Neither is an unconditional target annotation score.

Only new files under this assigned directory were written. Raw fetched artifacts are in `sources/`; `PMC10990095_SI.pdf` is a preserved failed HTML retrieval, and `PMC10990095_SI_valid.pdf` is the actual inspected PDF. No production code, scientific/HPC execution, prompt, reader implementation, library publication, existing historical record or goal-completion count was modified.

Additive verification: a supplied-NADPH budget for the same NfnAB reported endpoint is appended to `paper_01_nfnab.md`, with zero extra compilation weight because it is a second representation of Fig. 3B. Five further arithmetic assertions are recorded in `budget_arithmetic_results.json`. A file-presence/JSON check succeeded. A scoped `git status` could not run because this workspace has no Git repository metadata; no Git-based preservation comparison is claimed.
