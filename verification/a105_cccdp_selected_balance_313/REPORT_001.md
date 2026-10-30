# A105 CcCdP Figure 2D selected balance implementation

This is one new numerical section in the existing A105 worksheet, not a new
evidence axis, a separate completed general grader, or annotation credit.
The immutable user-supplied literature goal remains the authority; no
repository goal file was read or changed.

## Original source and selected experiment

- Article: Klimacek, Zhong and Nidetzky (2021), DOI
  10.1186/s13068-021-01982-2. The retained original article HTML has SHA256
  `bed5ff3b157dae8567f9d810fe292fa573a3bf54ebcd9a819a259686362f03a6`.
- Authors' Figure 2 XLSX from Zenodo 4555807, SHA256
  `7d5fbe5b3eb18aa18417bcd8f151951e021e7619f306c1dd11b6e508b3e972af`.
  The selected `Data` sheet is relationship `rId2`; panel D starts at row 50,
  headers are row 51, time zero is row 52, and selected time 90 min is row 61.
- Workbook `Metadata!F4:F9` gives nominal 100 mM αGlc1-P donor, 25 mM G2,
  1 U/mL cellodextrin phosphorylase from *Clostridium cellulosi*, 50 mM MES,
  pH 7.0 and 45 °C. Workbook `A16` says duplicate reactions. `A22` states
  authentic-standard HPLC ranges; `A23` says Pi is measured separately by
  colorimetry; `A29` supplies the Pi-equals-converted-donor model premise.
  The reader verifies all four numeric calibration intervals in `A22` before
  using their Decimal bounds. In-range status is eligibility only: no
  calibration recovery, curve error or method-validity multiplier is inferred.
- `Data!B52` is 25 mM and matches nominal `Metadata!F5`. The source does not
  establish that B52 is a distinct measured time-zero mean. `D52`, `F52`,
  `H52`, `J52` and `N52` print zero for initial G3–G6 and Pi, without a
  detection limit or demonstrated measurement status. The finite balance is
  conditional on those source time-zero entries, not a nondetection analysis.

The selected means are `B61=3.0467840000000002`,
`D61=5.5448360000000001`, `F61=6.6495870000000004`,
`H61=3.7561990000000001`, `J61=1.9335089999999999` and
`N61=43.291423000000002` mM. SD cells are `C61`, `E61`, `G61`, `I61`,
`K61` and `O61`; they remain distinct source-reported SD components. The
source does not supply same-reaction covariance or an independent protein
preparation count.

## Numerical sheet cells

The reader captures original lexemes and addresses. Exact Decimal arithmetic
populates 13 source numeric components and eight derived components. The
derived values are:

| Component | Formula | Exact Decimal value | Meaning |
| --- | --- | ---: | --- |
| G2 loss | `G2_0-G2_t` | 21.9532159999999998 mM | Conditional on B52 nominal-matching time-zero input |
| Soluble-product molecules | `G3+G4+G5+G6` | 17.8841310000000005 mM | Selected soluble concentrations; printed-zero baseline is conditional |
| Acceptor accounting ratio | `M/L` | 0.81464743024438882498716753157613740954553111103300 | Descriptive molecule account; shares products with the Pi account |
| Acceptor remainder | `L-M` | 4.0690849999999993 mM | Inferred balance remainder |
| Soluble added-glucosyl equivalents | `G3+2G4+3G5+4G6` | 37.8466430000000008 mM | Chain-length weighted soluble account |
| Soluble glucosyl accounting ratio | `W/Pi` | 0.87422959046645334461611065700227296219342769110302 | Descriptive soluble accounting under sourced one-Pi-per-transfer interpretation; not an assay-validity multiplier |
| Glucosyl remainder | `Pi-W` | 5.4447800000000012 mM | Inferred remainder, not measured insoluble product |
| Nominal donor-to-soluble yield | `W/100` | 0.378466430000000008 | Soluble added-glucosyl equivalents per nominal donor; source-lexeme precision retained |

`W/100 = (Pi/100) × (W/Pi)` is one dependent expression, not two
independent corroborations. The G2 and Pi accounts reuse G3–G6. Ratio SD,
SE and confidence intervals are null because joint covariance is unavailable.
The matched no-enzyme arm, molecule-specific attribution, independent
preparation count, assay-validity multiplier and annotation credit remain null.
The source's inferred missing-equivalent destination is not promoted to a
direct measurement of insoluble product.

## Implementation and selected path

- `literature_stoichiometric_balance_inputs.py` reads exact selected XLSX
  cells via the existing `Workbook.rows`, checks hash, sheet/panel/time,
  metadata labels, time-zero entries, native numeric lexemes, SD sign and
  source-stated calibration intervals.
- `literature_stoichiometric_balance_calculations.py` defines the component
  roster, dependency keys, formulas, meanings and Decimal calculations.
- `literature_stoichiometric_balance_storage.py` saves the original selection,
  extraction and calculated sheet as a source record. Its typed projection
  contains only selected requested components and source context. Cold reads
  validate the saved record/operation binding and project saved rows without
  reopening the original workbook or recalculating.
- `literature_stoichiometric_balance_prompt.py` supplies recurring,
  aspect-specific TASK and an operation description; numerical sheet
  definitions remain separate. `literature_stoichiometric_balance_render.py`
  displays admitted cells and their dependence/limits as parent STEERING.
- The selected operation is `literature.stoichiometric_balance.populate` in
  the ordinary `LiteratureEpisodes` path. The same source is registered in
  A105 worksheet, numerical contract, communication boundary and task
  selection. Existing V1 worksheet and P205/Pa paths were preserved.

## Verification and limits

The focused new test uses the original authors' workbook and scripted
LiteratureEpisodes decisions. It checks exact values, source labels, wrong
hash/panel/time, out-of-range chosen row and altered below-range G6, missing
selected quantity, changed calibration statement, and nonzero initial-product
entry. It checks a typed 21-cell child return, complete recurring child TASK,
parent rendering, one selected population action, matching action/observation
counts, and read-only cold projection while original workbook access and
reader/calculator calls are forbidden.

Final connected invocation:

```text
.venv/bin/python -m pytest -q tests/test_literature_cccdp_balance_313.py tests/test_literature_p205_parent_depletion_308.py tests/test_literature_pa0142_kinetic_original_303.py tests/test_literature_a105_worksheet.py
68 passed in 53.31s
```

This invocation ran on the final tree after the source-baseline and
subject-context refinements. The tests use a scripted provider and fixture
controller, not configured-model literature reasoning.
The source's separate protein preparation count, matched no-enzyme control,
joint uncertainty, independent insoluble-product measurement, and overall
A105 compilation remain unresolved. W05 target correspondence and final
annotation credit were not changed.
The operation binds only the authors' workbook. The article reports a
construct detail such as an N-terminal His tag, but that detail is not
cross-validated into these numerical rows; the workbook itself does not
report the construct. Source-to-functional-assertion linkage remains the
literature episode's interpretation, not an inference from workbook labels.

## Post-paper authority reset

After inspecting the original article/workbook and the retained case packet,
I reread the complete user-supplied goal attachment, root `AGENTS.md`,
`docs/EPISODE_STRUCTURE.md`, `docs/TIME_AWARE_ESTIMATION.md`,
`docs/TOOL_KNOWLEDGE.md`, `docs/TASK_AND_STEERING.md`,
`docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md`,
`docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md`,
both `VERBATIM_DIRECTION.md` and `VERBATIM_RECOVERY_002.md` in the
2026-10-23-002 publication, the full evidence-axis library instructions,
the earlier A105 numerical review, and
`research/experimental_scoring_review_2026-10-23/AGENTS.md`. I then reread
the complete current A105 worksheet and extraction contract and the latest
user-provided root instructions. I also read the practical execution records
applicable to episode work. The article/workbook supply source facts; these
records do not replace the goal or turn the ratio into an adopted grade.
