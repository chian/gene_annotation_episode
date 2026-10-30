# A110 source coverage, authority resets and seven-criterion assessment

This workload consolidates the current numerical sheet and closes its missing
full-isotope equation/example join. It makes no axis-completion or goal-completion
decision. The parent reported A105 delivered first and 1/10 recorded at
progress011; historical 0/10 statements in the retained records are preserved,
not copied as current accounting. A109 remains removed; A110 remains separate.

## What was inspected by whom

| Reader/workload | Actual inspection | What is not claimed |
|---|---|---|
| Original `a110_chemical_sheet_016` worker | Recorded primary NfnAB main Abstract/Introduction, complete Methods/Results/Table 1/all six figure captions/Discussion; full separate correction | NfnAB plot-point digitization or reference-paper reading |
| Original worker, UbiUV | Recorded complete main text/captions, main Fig. 4 image, SI pages 1–9, rendered Fig. S3 on SI page 5 | SI pages 10 onward, raw isotope replicates/covariance, or a measured intracellular donor fraction |
| Earlier parent `a110_sheet_construction_001` | Full joined sheet, print-ready summary, reader IO, and 20 arithmetic relations | Independent primary-source/figure/chemistry validation or inspection of either paper-specific packet in that review |
| Current `a110_complete_deliverable_026` | Complete joined sheet, exact IO, print-ready/handoff/source/authority records, both check scripts and receipts; full retained UbiUV packet once; then full retained NfnAB packet once | No new primary paper, source figure, supplement, source dataset or existing scientific-run inspection |

The retained packet reads were necessary for two concrete joins: UbiUV's full
baseline-convolution operator was referenced but absent from the cross-case
sheet; NfnAB's exact reaction, readout mapping and experimental subject definitions
were needed for a self-contained example. Neither read is counted as a newly
discovered paper or independent primary revalidation. The original primary
coverage is attributed to its worker, not to the parent or this consolidator.

The original worker preserved `PMC10990095_SI.pdf` as a failed HTML retrieval;
`PMC10990095_SI_valid.pdf` is the valid inspected PDF. Neither was opened in this
workload. The affiliation correction is not another biological experiment.

## Numerical component/source trace

| Current component/cell | Source/location and retained path | Source fact or model supplied | Current inspection extent and use |
|---|---|---|---|
| NfnAB y_reverse | [Wang et al. 10.1128/JB.00612-10](https://doi.org/10.1128/JB.00612-10), Fig. 3B/caption; `../a110_chemical_sheet_016/paper_01_nfnab.md` | ≈1 µmol H2 and ≈2.2 µmol NADPH supplied | Retained packet read; derived 5/11 ratio stays supplied-denominator and approximate |
| NfnAB y_forward | Same, Fig. 4A/caption | ≈.10 µmol net NAD(P)H increase per ≈.11 µmol NADH supplied | Retained packet read; derived 10/11 is net signal, not NADPH formation alone |
| NfnAB model predictions and D | Same, overall reaction, reaction Methods and discussion | Coupled redox equation; Fd/hydrogenase reporter; two NADPH formed minus one NADH consumed; 4 donated/accepted e− | Retained packet read; explicit atom-skeleton/relative-charge/electron algebra; D=0 only on stated formal basis |
| Other NfnAB diagnostics | Same, Figs. 3A/4B, Table 1 | 1/1.1 and .10/.22 companion ratios; 8 versus 23 U/mg with interference noted | Retained packet read; no extra replicate count or A110 rate-magnitude score |
| NfnAB reagent budget | Same, Fig. 3B | Supplied 2.2 µmol versus reported 1 µmol H2 endpoint | Derived z=1.1, f=1, s=1; zero added weight because same observation |
| Native allocation/energy diagnostics | Same, Fig. 6/Discussion | Author allocation 5−(2+2.5+.5)=0; scenario 100 kJ/mol and 60–80 kJ/mol ATP | Retained packet read; no measured native capacities or measured energy credit inferred |
| NfnAB correction | [10.1128/JB.02550-14](https://doi.org/10.1128/JB.02550-14), complete affiliation correction | Affiliation change only according to original full read | Current coverage is retained packet/report only; no experiment number changed |
| UbiUV precursor fraction | [Kazemzadeh Ferizhendi et al. 10.1073/pnas.2321242121](https://doi.org/10.1073/pnas.2321242121), isotope Methods; `../a110_chemical_sheet_016/paper_02_ubiuv.md` | p_supplied=A175/(A175+A173)=.64±.012, two technical injections | Retained packet read; ± type not converted to SD/CI and p_pool not equated |
| UbiUV theoretical labels | Same, SI Fig. S3 E–G and Methods | Binomial donor-count construction for m=2,3,4 | Retained packet read; conditional predicted arrays, not product observations |
| UbiUV reduced statistic | Same, main Fig. 4D, matched FBE748/no-added-4-HB means | Worker extraction intervals B727 [43,47], B729 [8,11], L727 [3,5], L729 [14,17] pmol/mg | Current packet read only; no new image measurement. Diagnostic ratios and signed comparisons retain extraction/pool limitations |
| UbiUV replication/calibration/comparability | Same, Fig. 4 caption, Methods, SI Table S1 | n=3 independent experiments; mean/SD; UQ10 standard; UQ8 6.25–50 pmol calibration; FBE748 MG1655-derived ΔaroD ΔubiIH; 10 µM shikimate | Retained packet read; exact raw arrays/covariance/recovery not retrieved. Separate WT/4-HB arms not substituted as baseline |
| UbiUV full-pattern measurement operator | Retained packet's full-pattern section, based on the stated label-count model and measured baseline design | Normalize B/L; convolve baseline b with f_m; renormalize over selected window; squared vector errors | Entire equation now joined into current sheet. This is a proposed measurement-model calculation, not a source-reported native score or new empirical fit |
| UbiUV net redox/resources | Same, Fig. 5/Discussion and retained symbolic conversion | Proposed donor half-reaction, two-electron oxidation obligation, unidentified acceptor | Retained packet read; complete-net D and native capacity/demand remain missing |
| Signed contrast, alternative minimum and weights | Earlier joined proposal and parent numerical review | Explicit proposed arithmetic conventions | Complete documents read; no source claimed to supply these scores |
| Resource transform and conservation penalty | Earlier joined proposal and parent numerical review | f=min(1,z/v_star), 2f−1, C=(1−D)sum(w*s)−D | Definitions preserved; no native pathway-model score was obtained or discarded |
| Nontrivial corrections, full isotope dataset, closed acceptor, resource LP and censoring examples | `WORKED_EXAMPLES_026.md`, `check_final_joins_026.py` | Entirely synthetic quantities and stipulated chemical accounts | New bounded arithmetic only; never source measurements or target annotation evidence |

Source weaknesses are tied to explicit missing operands. NfnAB needs actual
consumption/recovery and replicate statistics for an unconditional reaction fit;
its native flux/energy questions remain missing. UbiUV needs full per-experiment
B/L amounts, donor enrichment/exchange, recovery/covariance and a complete
electron/resource account. The synthetic Q acceptor is deliberately fictional;
it cannot be read as the missing published acceptor.

## Complete authority-read provenance

The complete set below was actually read in each of three cycles: initial,
after the retained UbiUV packet and before its interpretation, and after the
retained NfnAB packet and before its interpretation. The two packet reads were
sequential. Each post-packet cycle completed before any further source packet
or task-specific interpretation. This is research provenance, not a runtime gate.

1. `AGENTS.md` and `GOAL.md`.
2. `docs/EPISODE_STRUCTURE.md`.
3. `docs/TIME_AWARE_ESTIMATION.md`.
4. `docs/TOOL_KNOWLEDGE.md`.
5. `docs/TASK_AND_STEERING.md`.
6. `docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md`.
7. `docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`.
8. `research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md`.
9. The same directory's complete `VERBATIM_RECOVERY_002.md`.
10. `docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md` including its leading correction and preserved original.
11. `verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md`.
12. `research/experimental_scoring_review_2026-10-23/AGENTS.md` in full, including user quotations.
13. The same directory's `SOURCE_CORRECTIONS.md`.
14. The same directory's `A105_REVIEW_ASSIGNMENTS_2026-10-23_001.md` in full.
15. `/home/chia/.codex/attachments/9a858f85-d1dc-4f59-b574-9988cc09dee2/pasted-text-1.txt`.
16. The current bounded parent assignment and latest human reminder last:
    “Remember a goal is a goal - so you have to set the goal and the goal criteria more than the instructions.”

Initial large aggregate outputs truncated. The affected authority documents
were subsequently reread in full, separately: AGENTS/GOAL, EPISODE_STRUCTURE,
TIME_AWARE_ESTIMATION, VERBATIM_DIRECTION/RECOVERY, and EVIDENCE_AXIS_LIBRARY/
numeric example. Both post-packet cycles used complete bounded outputs without
truncation. The joined A110 proposal's first combined read also truncated and
was repaired by sequential complete 1–110 and 111–end reads. Reader IO was
subsequently read completely. No headings, hashes or summaries substituted for
the required full reads. No new paper was opened after the last reset.

## Seven-criterion assessment for the parent

| Criterion | Delivered evidence | Remaining distinction |
|---|---|---|
| 1. Numerical inputs/units/denominators/uncertainty/missingness | Current sheet numerical table and Eqs. 1–10; exact Quantity/domain/status fields; reported/supplied/consumed/net quantities kept distinct | Real native inputs can remain missing. Unmeasured corrections are not exact zero; no fabricated CI |
| 2. Every component sum/multiplier to candidate contribution | Corrections precede ratio/vector construction; error contrast/minimum; measured budget/LP; atom/charge/electron D; fixed weighted sum and conservation penalty with bounds | The mathematical conventions are explicit and unadopted, not undefined or source-native confidence |
| 3. Contrasting published cells and checked full examples | NfnAB complete conditional reaction chain; UbiUV contrasting measured-label/reduced-statistic cells and full empirical unknowns; fully populated synthetic scalar and isotope/resource/conservation chains | No full empirical UbiUV/native pathway score is claimed. Synthetic inputs remain synthetic |
| 4. Dependence/replication/contradiction/nondetection | Main sheet handling table; per-unit residual identity; fixed observation refs; zero-weight NfnAB duplicate budget; m2 contradictory reduced statistic; censored and opposing synthetic observations | W05 must consume shared-axis references before global credit; no cross-axis independence assumed here |
| 5. Component/source and actual coverage | Detailed table above, separate original-worker/parent/current coverage, full reset record | Current source review is of retained packets, not new independent primary inspection |
| 6. Exact targeted population fields | READER_CROSSWALK_026 defines quantity types, all input/output fields and exact per-function numerical dependencies, with filled output crosswalk | All application readers/scorers are UNIMPLEMENTED; implementation is outside this scoring-sheet goal |
| 7. Printable formulas/examples/choices and feedback | PRINT_READY_026 supplies the material to print; current sheet and examples implement the known feedback listed below | Parent must print the useful content and retain new human feedback; this worker does not presume acceptance or mark the axis complete |

The current declared numerical paths have no intentionally deferred essential
calculation. The full isotope operator, alternative set handling, capacity LP,
normalization, interval edges and final combination are defined. Missing source
values/relations and undefined equations are not conflated: an actually absent
measurement remains null/bounded, while a newly proposed unsupported measurement
model would require its equation before becoming another sheet operator.
Biological validation across new assay families is not claimed.

Known human feedback incorporated:

- Components combine numerically by actual sums/divisions/multipliers; no
  rejected category ladder or paper-level confidence appears.
- The sheet scores meaningful quantities; source metadata is separate.
- Experimental comparability and effect isolation use separate measured operands.
- Papers are converted into the user's template, not treated as scoring policy.
- Investigation starts with supplied material and can discover possible functions.
- A105 owns direct activity, A106 owns perturbation; A110 remains distinct.
- Measured isotope fractions, theoretical count distributions and readout-model
  predictions are explicitly different arrays.
- Missing native observations and unadopted numerical conventions are reported
  without treating them as an automatic ban on a usable numerical sheet.
- The goal and seven criteria lead the deliverable; source-review counts do not.

## What was run and what was written

Only `python3 .../a110_complete_deliverable_026/check_final_joins_026.py` was run
for arithmetic, producing `final_join_receipt_026.json` with 29 passing checks.
These are necessary new complete chains and final joins, not a rerun of the
old 150-check grid or its separate five-check budget record. The earlier parent
20-check receipt and worker receipts were read, not overwritten or re-executed.
Counts overlap in purpose and are not added into a unique-coverage total.

All written artifacts are new files under the assigned
`a110_complete_deliverable_026/` directory. No production tests, source dataset
analysis, scientific/native/HPC job, target annotation, prompt/library edit or
global scoring/continuation change occurred. No goal or axis was marked complete.
