# Rfam displayed correspondence verification — workload 236

This workload implements the pure `parse_rfam_alignment_display` function in
`gene_annotation_episode/rfam_batch_alignment.py` and its focused tests. It does
not mark the Rfam fixed row complete. No network request, process, storage write,
resource selection, timing/credit observation, prompt or episode is hidden in
the parser. Source acquisition for research was separate from parsing.

## Authority and interface

The entire immutable original goal was read from
`/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt`,
SHA256 `11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7`.
Its objective and all sixteen principles were reread verbatim after substantive
source/native examination before coding, and again at closure. AGENTS.md, the
tool-grader direction record and Rfam work-status row, full workload boundaries,
full contract, source audit and expected examples were read. No permanent
direction or historical receipt was edited.

The exact signature and closed result record are those in
`../tool_graders_rfam_contract_2026-10-26_232/CONTRACT.md` section 3. The shared
contracts owner added the explicit issue code
`rfam_alignment_correspondence_unrepresented`; this distinguishes understood
native abbreviation from `rfam_alignment_unsupported` (grammar not implemented)
and invalid/conflicting source data. This is a validation detail, not a new
scientific scoring model or completion criterion.

The returned source binding is exactly the supplied artifact, original hit row
key, query occurrence, family accession, strand and `/alignment` pointer. The
consumer's bundle additionally contains the exact source SHA256. The display
function cannot authenticate a caller's artifact custody or establish a new
report-to-JSON join. Those responsibilities remain with the actual publisher
and source-aware sheet consumer.

## Source observations

Read the installed Infernal 1.1.5 `cm_alidisplay_Create` rendering branches and
complete `cm_alidisplay_Print`, its PP encoding definition, and relevant complete
guide sections on consensus, gaps, posterior placement, wrapped displays,
truncation and local ends. Primary-source URLs checked separately:

- https://raw.githubusercontent.com/EddyRivasLab/infernal/infernal-1.1.5/src/cm_alidisplay.c
- https://raw.githubusercontent.com/EddyRivasLab/infernal/infernal-1.1.5/documentation/userguide/tutorial.tex

The installed upstream tutorial output is the actual supplied file, rather than
a recreation from a prose example. Its Cobalamin display has a 31-position 5′
truncation and terminal model coordinate 191; the separate tutorial prose
example has 30 and 190. They were not silently treated as identical outputs.

Native artifacts acquired by transport workload 234 were read from
`../tool_graders_rfam_transport_2026-10-26_234/live/`:

- `single/003-fetch-json/response.body`: actual labelled six-string display.
- `multi/005-fetch-out/response.body` and `multi/input-manifest.json`: six
  uniquely named original query occurrences, including repeated sequence under
  a distinct name, reverse complement, prefix, insertion and deletion.
- The real batch JSON lacks per-query attribution and alignments. Its order is
  never used to assign any of the report displays to a batch JSON row.

The remote report explicitly has unlimited text width. Long/wrapped remote JSON
serialization, missing-PP remote JSON serialization and remote local-end JSON
remain unobserved. The implemented labelled block grammar is exercised against
the supplied upstream wrapped/local-end display and synthetic absent PP. It is
not presented as proof that the current service emits those JSON shapes.

`prepare_fixtures.py` makes seven **derived native report display fixtures**.
It preserves original line ranges, exact native lines, source SHA256, input
source, original occurrence and the transformation (labels/indentation only).
Their fixture artifact IDs belong to those derived objects. They are not
native Rfam JSON captures or production text/JSON correlation records.

## Numerical meaning

| Result | Measurement and calculation |
|---|---|
| Paired positions | Each explicit model nucleotide opposite an explicit query nucleotide, with both zero-based indices and exact displayed symbols. The `match` segment kind means a paired column, not necessarily equal symbols. |
| Physical query positions | Ascend on `+`, descend on `-`. Intervals remain increasing zero-based half-open physical coordinates in the supplied original sequence. Display symbols must equal that sequence after explicit IUPAC RNA complement and case/T/U display equivalence. |
| Model intervals | Union of explicitly displayed consensus positions, including explicit deletion columns. Local-end/truncated model counts are excluded from this represented union. |
| Query intervals | Union of explicitly displayed query residues, including insertions. Omitted local-end query residues do not gain an invented symbol map. |
| Compared/equal counts | Only paired canonical A/C/G/U symbols contribute, after case/T/U display equivalence. Equal count compares those symbols, not the match line. Ambiguous pairs are retained but excluded from this denominator. |
| Query insertions | Count of explicit query nucleotide columns opposite a model `.`. Local-end inserted counts are separate. |
| Model deletions | Count of explicit model nucleotide columns opposite query `-`. Local-end omitted and truncated model counts are separate. |
| 5′/3′ truncation | Native integer in boundary `<[n]*` or `*[n]>` model shorthand, consuming model positions but zero query residues. Orientation is along the model; reverse query orientation does not swap model 5′/3′. |
| Local end | Separate exact native integers `*[m]*` and `*[q]*`; exact coordinate spans are retained. Omitted consensus/query symbols and individual pair mapping remain unavailable. |
| PP residue bins | `0=[0,.05)`, digits `d=1..9` have bounds `[(d-.5)/10,(d+.5)/10)`, `*=[.95,1]`. Bounds are retained; no midpoint or annotation probability is fabricated. |
| PP local-end bins | One span-mean placement bin applies to the native local-end span, not identical per-residue posterior values. Zero query residue spans create no PP record. |

Every omitted segment has `correspondence_represented:false`, source token text,
counts and known intervals. Understood abbreviation returns `partial` with the
specific unrepresented issue. Invalid optional NC/SS/match/PP tracks preserve
independently validated geometry. Invalid hit/query attribution or contradictory
geometry produces an invalid result with unavailable measurements and retained
raw source reference. Unknown core grammar returns unsupported. Neither model
endpoints nor represented intervals establish a full searched-model denominator.

## Executed checks and complete examples

`run_verification.py` uses the existing local runner with 20 GiB memory, 4 GiB
scratch and no wall-time budget. The receipts show cgroup MemoryMax and zero
swap, process-group containment, per-file scratch-size limit, monitored visible
allocated scratch (possible monitoring overshoot), and RuntimeMax=infinity.
This is not described as a filesystem sandbox.

- `fixtures_001`: seven labelled native-display test operands produced.
- `tests_001`: 57 passed, one erroneous expected coordinate failed. The native
  insertion is physical query position 102, zero-based `[101,102)`. The parser
  was correct; only that test expectation was corrected. The original failure
  log and receipt are retained.
- `tests_002`: **58 passed**. Native documentation/current JSON, six actual
  report displays, upstream wrapped reverse/local-end display, all posterior
  bins, IUPAC orientation, endpoint conflicts, unknown/malformed grammar,
  optional track failures, all-deletion/all-insertion wrapped blocks, huge
  shorthand without expansion, exact identities and no-I/O operation checked.
- `tests_003`: **64 passed** after adding malformed shorthand boundary/count/
  kind cases and a structured failure for a decimal token rejected by Python's
  integer parser. Valid native numerical results were unchanged. This run also
  used the updated shared validator for monotonic unique pairs and exact PP
  bounds.
- `examples_001`: full closed component JSON and provenance written for all
  nine examples. The independent current-JSON column check derives coordinates
  by prefix gap counts and agrees exactly with all 118 parsed pairs, 75
  canonical equal pairs, insertion query index 101 and model deletion indices
  40 and 109. These full results are not replaced by the table below.

| Example | Model represented | Query represented | Compared / equal | Insert / delete | Native omitted counts |
|---|---:|---:|---:|---:|---|
| Official documentation JSON | 119 | 119 | 119 / 79 | 0 / 0 | none |
| Actual current single JSON | 120 | 119 | 118 / 75 | 1 / 2 | none |
| Actual original / repeat / reverse report displays | 120 each | 119 each | 118 / 75 each | 1 / 2 each | none |
| Actual prefix70 report display | 71 | 70 | 70 / 43 | 0 / 1 | 49 model positions truncated at 3′ |
| Actual insertion report display | 120 | 120 | 118 / 75 | 2 / 2 | none |
| Actual deletion report display | 120 | 118 | 117 / 75 | 1 / 3 | none |
| Supplied upstream wrapped Cobalamin report display | 99 | 99 | 98 / 49 | 1 / 1 | 31 model positions truncated at 5′; local end omits 61 model positions and includes 4 query residues |

`examples_001/examples/live-single.components.json` is the exact-source example
bundle to pass as `alignment_components`, after the caller uses its own actual
artifact and occurrence refs in the parser invocation. Report-extraction output
is intentionally not mixed into that JSON bundle.

The complete current shared component validator, JSON reader and calculator
consumers were inspected. Workload 235 independently exercised this parser →
exact-source bundle → sheet → calculator/view composition, source/identity
misbindings and saved-sheet no-I/O recalculation; its own receipts establish
those checks. No production episode-path verification is claimed by workload
236. The root integration owner must verify actual selected API publication
and both receiving episode boundaries. Full batch attribution/report binding
also remains distinct unfinished work. Missing native information stays missing.
