# Scientific parent masking-return trace

This is implementation evidence for one receiving boundary and its proposed
text. The original user attachment remains authoritative. No goal/scope file,
production prompt, calculation, schema, credit policy or continuation rule was
created or changed.

## Actual received route

1. The original scientific parent's selected results action supplies
   `execution_results_assignment_v1` with its selected handoff and selector,
   plus the original direct-child typed return schema. In the saved DUST case,
   this schema requests the seven `execution.masking_*` arrays plus the
   existing practical `execution_completed` boolean. The scientific parent's
   upstream schema requests only status, quantities and statistics. Static
   comparison of the exact extracted action, child's episode request and
   frozen returned form confirms their equality; these are not inferred from
   the present-day test fixture.
2. `NativeBLASTMaskingResults.execute` retains the actual capture, preparation
   and selected publication. `facts` (native_blast_masking_results.py:406)
   copies only the original results episode's requested sources from its
   authenticated own receipts. Internal scalar status is wrapped into one
   array row. Quantities are the selected shared-sheet components, not a new
   calculation by the message layer.
3. `NativeBLASTMaskingReturns._attempt` (line 107) authenticates the original
   immediate-child commission, exact schema, scope, role, assignment and frozen
   form. `_validate_historical` (line 154) checks values against the actual own
   result facts. `_received` (line 199) visits successful direct-child returns,
   keeps the declared sources and deduplicates only exact equal rows. It does
   not collapse distinct selectors into a latest status or open unrequested
   scientific content.
4. `Workflow.receive_form` / `_receive_form` (runtime.py:2655/2659) admits the
   selected returned references through
   `ExecutionEpisodes.received_form_references` (line 2498), which invokes the
   masking adapter's `record_admission` (line 264). A source reference or
   numerical record relationship grants no auxiliary file. Explicit artifact
   and saved-data rows provide the only masking-specific file grants.
5. Before an ordinary later own decision, `DecisionSource.next`
   (runtime.py:1397 onward) passes `view.child_reports` to
   `view.model_inputs(..., reports=view.child_reports)` (line 1489).
   `EpisodeView.child_reports` and `_model_inputs`
   (method_loop/episode.py:1033/1041) return each admitted `ParentReport`'s
   values. `ParentReport.as_record` (method_loop/communication.py:105) thaws
   exactly those values. This path is independent of the scientific parent's
   upstream return schema.
6. `DecisionSource.call` preserves the actual task/context and adds bound
   initial information. The optional exchange path uses
   `decision_context.model_snapshot`, state frames and restoration; its
   instruction projection does not remove these masking returns. The legacy
   path also supplies the admitted child reports. Neither path turns the
   upstream closure schema into a filter on the direct report.
7. `providers._SessionConnection._presentation` (providers.py:308) chooses
   `render_scientific_process_prompt` for a published scientific context. The
   renderer (scientific_process_prompt.py:495) emits the full `_task` and then
   `render_episode_steering`. The intervening Infernal and RNA presentation
   functions select their own recognized facts; they do not strip this
   masking report.
8. `_steering` (scientific_process_prompt.py:394) sends each `child_reports`
   entry through `alignment_report_presentation`, which leaves this
   nonalignment report intact. `_values` recursively renders the raw fields.
   Consequently the ordinary direct report is not wholly omitted: its current
   fallback prints custody references, hashes, identifiers and every selected
   check using generic field paths. The demonstrated presentation gap is the
   lack of concise masking-specific factual text.

`ExecutionEpisodes.initial_decision_context` (line 981) does not currently call
`native_blast_masking_returns.received_context`. Thus the adapter's independent
authenticated received-context port has no named prompt-state hook. That
absence is not proof that the ordinary `child_reports` route is missing.
`ExecutionEpisodes.received_report_facts` (line 2000) calls
`received_facts(context, schema)` using the scientific parent's upstream
schema, but only while constructing its outgoing closure facts through
`Workflow.facts` (runtime.py:3987). Reusing that closure projection as the
scientific parent's own received STEERING would incorrectly drop its selected
artifact, saved-data, check and failure fields in this concrete case.

## Field-to-decision trace

| Exact received source | Selected presentation and meaning | What it changes for the parent's next choice |
| --- | --- | --- |
| execution.masking_status | Requested fulfillment, native execution state and native output completeness are distinct. Retain each material selected result's status; do not choose a latest row by source. | Distinguishes a fulfilled preparation request from a missing deliverable, and a usable diagnostic-only return from successful execution. It neither establishes gene-function evidence nor stops the parent. |
| execution.masking_quantities | Only requested quantities at selected original operand/record positions. Copy values, units, numerator, denominator and missing reason. Ordinals are original positions, never header matches or result ranks. | Establishes how much of each supplied record was masked under the selected job, including an actual zero. The parent can assess whether to inspect the mask, retain or change sequence preparation, or gather a missing measurement. No action is selected for it. |
| execution.masking_artifacts | Only explicitly returned direction/role/ordinal material and completeness. Describe the file's role without hashes or an automatic content preview. | Identifies which native mask, sequence, reference-statistics or diagnostic file is actually available for a subsequent selected read or child input. Scalar measurements do not supply missing file bytes. |
| execution.masking_saved_data | Only explicit saved sheet, calculated components or parsed-statistics grants. | Makes later saved-data investigation possible without implying that every internal numerical artifact was delivered. Saved recalculation requires the exact explicitly received original sheet and original handoff. A calculations-only or source-only return does not authorize it. |
| execution.masking_statistics | Only requested native fields and unit-code rows, with their selected reference relationship and missing-unit qualifications. Preserve native unit lengths, thresholds, percentiles and lexemes where requested. | Distinguishes supplied/unknown from authenticated generated reference statistics and permits comparison or a targeted provenance repair. Native statistics thresholds are distinct from invocation clipping parameters. Counts generation supplies reference statistics, not a masked fraction. |
| execution.masking_checks | Only relevant selected-record/global qualifications that affect use or repair. In this DUST case every returned check passed, so no checks table is printed. | The Window-mask case's unknown reference provenance is consequential even though requested fulfillment is complete. Passing custody or syntax checks are not gene-function evidence. No check becomes an acceptance gate. |
| execution.masking_failures | Concrete selected failure stage/code and original record/file association; include native line locations only when needed to repair the requested input. Preserve valid rows beside failures. | Identifies a specific missing input, unavailable artifact, malformed native output or mapping issue, allowing the parent to choose a meaningful repair. It does not authorize a substitute record, invented zero, automatic retry or cancellation. |

The printed DUST table copies the nine selected quantities into three rows.
`masked_fraction` values remain `1.0`, `0.0` and `1.0`, with the exact returned
numerators and denominators. No aggregate fraction or percentage is newly
computed. The SEG return similarly retains `32/72 = 0.4444444444444444` at
ordinal 2 in amino-acid units. The Window-mask return retains
`reference_provenance_unknown` as a meaningful qualification.

## Selection and ownership requirements for this draft

- Read the exact original direct-child contract and admitted form. Resolve
  caller-chosen field names through their declared `x-source`; do not guess
  semantics from keys such as `status` or `values`.
- Preserve the original selected population and quantity/statistics names.
  `records={mode:selected, entries:[]}` means no sequence quantities, even if
  a quantity-name list is nonempty. It is different from a missing requested
  all-record population. No default top-N bound or automatic all-file display
  is introduced.
- Use the declared original position semantics after authentication, without
  loading the full saved sheet merely to prettify a label. A header can repeat.
  Missing/invalid positions remain distinguishable and cannot be replaced.
- Include the actual negative/unknown qualifications needed to decide whether
  a value or material can be used. A qualified nullable hard-mask result can
  fulfill the request; an unavailable denominator is different. Zero, null,
  failed execution, partial output and empty selection remain distinct.
- Keep source, artifact, record, occurrence, producer-attempt and receipt
  identities in host validation and typed operand bindings. A named semantic
  material binding is still needed for hash-free model-facing action
  selection; a prose label is not authorization or a working alias.
- A return with source references only cannot expand the source's auxiliary
  artifacts or internal grading envelope. A later child may use only files or
  saved data explicitly delivered to its parent and then explicitly supplied
  through the selected child's original input boundary.
- Parent TASK remains the parent's detailed recurring work. This return is
  factual STEERING. It introduces no candidate-annotation prerequisite, new
  TASK, LLM report-composition call, private child history or scientific score.
- Preserve the parent's own yield/expectation/uncertainty table from its
  actual controller information. No child's operational credit, per-interval
  score, number of checks or artifact count enters that table as a new
  observation. Rendering supplies no observation. The ordinary controller
  owns the next choice and continuation.

## Verification performed and remaining evidence

Read the full original user attachment and all ten operating principles;
AGENTS.md; TASK_AND_STEERING.md; 610 RESULT_SELECTION_006; 616 INTERFACES_001,
RETURN_GRANTS_002, FULFILLMENT_003 and EMPTY_SELECTION_004; and 617 HANDOFF_004.
Read the complete masking return adapter, result host and pure result projector,
the scientific text renderer, the decision-context framing module, actual
provider selection path, method-loop report boundary and relevant complete
runtime/host consumer functions. Source pins identify this reviewed version.

Only static stdlib source/JSON reads and evidence-file writes were performed by
622. No application imports, tests, database reads, model calls, native masking
runs, API/HPC operations or production edits were performed here.

Reused root's actual bounded results:

- check074 retained completed native DUST, SEG and Window-mask workflows.
  Its full invocation exited 1 because the numerical assertion incorrectly
  looked for Operation in Components. The retained actual paths and values
  remain evidence; check074 is not reported as an all-pass check.
- check080 finished with 6 passing checks in 51.36 seconds; its collected
  process exited 0, terminal/quiescent, with all four pin closures unchanged.
  It verified the retained three mask numerical results without rerunning
  them, and completed the native WindowMasker counts workflow.
- 621's shared check081 read-only extraction passed one check in 0.45 seconds,
  exited 0 terminal/quiescent, and preserved source DB/CASE bytes. It used the
  529 runner with 20 GiB RAM, 4 GiB scratch, zero swap and no wall-time cap.
  Exact original DUST selected schema, assignment and frozen form were
  compared here using only that JSON extraction.

The original DUST evidence has exactly two scientific model requests and no
post-results scientific request. Therefore this review does not claim an
actually dispatched third prompt, live model decision, or implemented masking
renderer. A later approved implementation still needs exact receiver rendering
verification, including original/upstream form separation, no raw host
identities, valid partial/missing/empty selections, exact requested native
statistics, explicit artifact grants and unchanged TASK. The present files
are a concrete review draft and trace, not runtime completion evidence for
that unimplemented message presentation.
