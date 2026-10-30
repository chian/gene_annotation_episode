# Draft: fluorescence results child to scientific parent steering

Draft for user review, 2026-10-28. No prompt implementation or template approval is claimed. This is one boundary: an admitted `results` child return rendered into the existing `scientific_process` parent's STEERING. It does not define a fluorescence scientific episode or replace the parent's TASK. The original user attachment remains authoritative; this file records a presentation proposal only.

The example below is illustrative. Its values are drawn from the explicit synthetic fixture expectations in `tests/fluorescence_prepared_workflow_support.py` and `tests/test_fluorescence_prepared_workflow.py`; they are not an inspected returned record, a new annotation, or evidence that check049 passed. At the coordinator's last update, check049 was still running. This drafting task ran no application imports, tests, native software, API requests, or Workflow.

## Receiving decision and information trace

The scientific parent already has its assigned gene/sequence question, scope, constraints, evidence-axis instructions, thought pattern, and selected actual tool information. Its next decision may use the requested numbers, recognize a limited population or incompatible comparison, request missing context through an independently selected action, or choose another investigation. The renderer does not make any of those choices.

| Decision-relevant distinction | Exact admitted information | Presentation consequence |
| --- | --- | --- |
| Which sample and condition does a value describe? | Cell population keys and, only when returned, matching sample definitions | Show the supplied label, condition and replicate meanings. Null means unknown. Do not infer CD4 cells, a cytokine, treatment, or gene association from an operation name. |
| Which representation was summarized? | Cell domain/channel keys; returned domain state, scale kind, preparation states and parent lineage | Keep encoded, scaled and compensated values separate. A requested but unavailable preparation remains unavailable. Prepared representations are not additional samples or replicates. |
| Is a number a reported token or a calculation? | `request.kind`, `request.metric`, and optional native-report definition | Label population/fraction/intensity/control statistics as calculated cells; `native_value` is a supplied report value; `native_minus_calculated` is the stored calculated difference. Do not present a report value as native execution proof. |
| What is the denominator? | Cell `population.denominator`, fraction request denominator; optional returned gate/control definitions and explicitly returned count cells | Name parent, evaluable parent, selected finite values, or paired controls exactly. Do not count operand pointers or infer an unrequested denominator number. |
| Does an available number cover the requested population? | Cell state, population extent and located issues | Keep present, qualified and unavailable distinct. A value from a confirmed subset does not establish the complete intended population. |
| Did a report comparison establish agreement? | Requested stored difference, unit, issues; optional report precision and linked component request | Show the signed difference without computing it again or imposing an agreement tolerance. Zero difference does not verify report generation or the underlying experiment. |
| Is missing context recoverable from this return? | Requested fact sources and context field list, not private result artifacts | Show what is unknown or was not requested. Do not open the sheet, acquire metadata, or expand source provenance into unreturned scientific content. |
| What should continue? | Parent's existing own-action yield/expectation/uncertainty table and controller state | Retain that table through the existing parent renderer. Do not insert the child's private history, add observations, infer gain from row count, or turn partial delivery into a stopping rule. |

The durable path is selected child request and return form → authenticated result receipt → exact requested projection/context/failure facts → admitted immediate-child form → deterministic parent presentation. Numerical authority remains `calculate_fluorescence_sheet`; `project_fluorescence_result` copies its cells, and `project_fluorescence_context` copies only requested definitions associated with the actual page. Presentation adds no calculation or model call.

## Exact selection and joins

1. Read the original admitted child form with its original `measurements.schema`. Recognize sources by each field's `x-source`, not a caller's chosen field name. The four existing sources are `fluorescence_measurements`, `fluorescence_contexts`, `fluorescence_saved_sheets`, and `fluorescence_failures`. Preserve the source/contract association internally; do not serialize it as the prompt.
2. Keep each numerical projection associated with context returned from the same authenticated result receipt and present in that admitted form. Check exact selection equality in addition to that receipt relationship. Do not zip independently deduplicated arrays or use equality of selection alone: distinct result acquisitions can have the same selector and different available domains. `contribution_origins` identifies original acquisition-owner episodes for credit; it does not uniquely identify a projection/context pair. If pairing is not established, preserve the numerical page and mark its descriptive join unresolved.
3. Render `projection.rows` in their supplied request order. These already equal `selection.requests[offset:offset+limit]`; do not apply pagination a second time. Use `total_selected_rows`, `returned_row_count`, and `has_more` for coverage. They count selected numerical cells, not events, samples, or independent evidence. `projection.status` and `projection.issues` cover the entire selected request list, including requests outside the current page. Keep that scope explicit; do not attach a selection-wide issue to a particular displayed row without its row-level issue or an exact relevant locator.
4. Index each returned context collection by its `key` within that paired context only. Never join through labels, array position, numeric equality, a name such as `compensated`, or another child's report. Keys remain internal. Render supplied meaningful labels; use local neutral labels such as “sample 1” or “requested population 1” when necessary, and distinguish equal labels without revealing host identifiers.
5. Ordinary population/fraction/intensity cells join `cell.population.sample_key → samples.key`. Read `label`, `condition`, `biological_replicate`, and `technical_replicate` independently. Sample associations may identify relevant molecular relationships only when those associations were actually returned; never follow `file`, `source_key`, or location fields to acquire their contents.
6. For intensity, join `request.domain_key → domains.key` and `request.channel_key → channels.key`; require the represented channel domain and sample relationships to agree with the cell. Use `cell.unit` as the numerical unit, with the matching channel unit as a consistency check. Display channel `native_name`/`label`, and an explicitly returned analyte association when relevant. A missing analyte remains unknown. Sample primary-domain metadata must not replace the specifically requested intensity domain.
7. For population/fraction cells, join `request.gate_key → gates.key`. Follow each returned `gate.parent` through gates to its returned population definition, preserving `pass_all` versus `threshold`, lower/upper values and inclusive/exclusive bounds. A threshold's domain and channel come from that gate, which can differ from an intensity's domain. `population.kind=all` means the declared primary-event universe; a subset definition carries no event membership array in this context. Display the kind and any known ancestry without inventing membership. The sample's `primary_domain_key` supplies the primary representation only if samples and domains were requested and returned.
8. Domain meaning comes from `scale_kind` (`encoded`, `scaled`, or `as_supplied`), `state`, optional `scaling`, `compensation`, `transformation`, and exact `parent_domain_key` joins. Label “compensated” as applied only when the compensation state is `applied`; a declared compensation method with `unknown` state is merely the requested preparation. Omitted scaling metadata means unknown. Human method names may omit software version tokens in display while preserving method semantics; stored definitions remain exact. Parameter file identities do not reveal gain values, matrices, calibration, or transform parameters. Do not read them for this boundary.
9. For a control cell, join `request.control_key → control_pairs.key`, then target/control gate ancestry and sample definitions, and use `control_pairs.denominator`. The row itself carries `paired_controls`, not a single sample. Keep the target-minus-control direction explicit. The shared calculator owns compatibility. A supplied comparison-basis identity permits no inference of its unreturned evidence. If control definitions were not requested, the signed control-difference metric and `paired_controls` remain known, but target/control labels and the parent/evaluable denominator are not supplied.
10. For a native-comparison cell, join `request.native_report_key → native_reports.key` only when that collection was returned. `component_request` provides the exact linked population/domain/control request. If that linked cell is also in the returned page, join by its complete canonical request and display its value once. If not, describe the returned association without fetching its numerical value. `label` and `decimal_places` may qualify the report; do not reproduce the whole raw report. A report association can remain declared yet unsupported (`native_population_unknown`); preserve that qualification and an unavailable comparison while retaining a present native value.
11. Native-comparison rows have null sample/gate/domain/channel fields and denominator `none` in the present calculator. Without `native_reports` context, their exact metric, value, unit, state, extent and issues remain obtainable, and their shared internal report key can group the two requested metrics. Their sample, condition, associated calculated component, and reported precision do not become known from adjacent rows. A native report's `extent=complete` denotes that cell's availability, not verified full experimental population coverage.
12. Render only decision-relevant returned failure codes/stages and their known semantic target. A failure role such as `prepared_data:1` can be described as a requested prepared-data artifact; it cannot be attributed to the compensated domain without an admitted association. Do not infer that association merely because one compensated cell is also unavailable. Preserve exact diagnostics in typed storage. Unrequested failure facts cannot be fetched from the child receipt to decorate the prompt.

## Numerical meanings retained without recalculation

| Existing metric | Meaning to render; numerical authority remains the saved cell |
| --- | --- |
| `retained_event_count` | Number in the declared root population's retained primary-event universe. Prepared representations do not multiply this count. |
| `parent_event_count` / `parent_unknown_count` | Confirmed parent membership / unknown inherited parent membership. |
| `evaluable_event_count` | Confirmed parent events for which this gate predicate is evaluable. |
| `selected_event_count` / `rejected_event_count` / `unknown_gate_event_count` | Confirmed selected events / rejected events within the confirmed parent / confirmed parent events with an unevaluable predicate. Preserve the separate unknown-parent count when selected. |
| `selected_fraction` / `selected_percent` | Saved selected count divided by the declared parent or evaluable-parent count; saved percent is 100 times the saved fraction. Display only requested cells. A null due to empty or unknown denominator is not zero. |
| Intensity count / missing count | Finite selected measurements / selected events without an available valid value in this particular domain and channel. |
| Intensity sum / mean / median | Saved arithmetic summary over finite selected values in the requested domain/channel, with the saved channel unit. The mean's numerical denominator is unknown to this renderer unless its count cell was returned. |
| Control difference fraction / percentage points | Saved target fraction minus control fraction, and its separately calculated percentage-point representation. Preserve negative values. |
| Legacy nonnegative control difference | Separately requested clipped legacy component. Never replace the signed component with it or calculate it in display. |
| Native value / native minus calculated | Supplied report number / saved report-minus-linked-component difference. Keep the literal returned unit, including `percent` for a difference between percent-valued cells; do not silently relabel the stored contract. |

Copy the saved numeric value without rounding to zero, absolute-value conversion, clipping, normalization or new tolerance. A real small negative compensation residue must survive in any requested scalar that contains it; do not fetch event arrays to exhibit one. These contracts contain no sampling confidence interval or gene-function probability. Do not make one from event count, software success, or a finite number. Per-event `observed`/`supplied_predicted`/`derived` state is retained in the sheet but absent from the current returned context. Even with domains, observation-versus-prediction provenance for underlying supplied values can remain unknown at this boundary.

## Full proposed new steering subsection

The following is the entire proposed new subsection for the illustrative partial return. It is inserted once into the parent's existing STEERING. The complete pre-existing parent TASK is still supplied on this and every later decision call. The parent's existing own-action category/total-yield/expected-next-yield/uncertainty table is still rendered from its real state; there is no invented yield table below.

BEGIN ILLUSTRATIVE MODEL-FACING SUBSECTION

Requested fluorescence results

| Returned scope | Value |
| --- | --- |
| Numerical selection | 10 requested cells; 10 returned; no further selected rows |
| Selected results | Partial |
| Requested result delivery | Incomplete |
| Sample | sample α |
| Condition; biological replicate; technical replicate | Unknown; unknown; unknown |
| Population | All declared primary events; pass-all gate |
| Channel A analyte | Unknown |
| Returned definitions | Samples, channels, measurement domains, populations, gates |
| Definitions not requested | Sources, control pairs, native reports |

| Requested quantity | Value | Unit | Representation | Population or denominator | Qualification |
| --- | --- | --- | --- | --- | --- |
| Retained event count | 2 | events | Primary encoded events | Declared root population | Present; complete |
| Selected event count | 2 | events | Primary encoded events | Pass-all gate | Present; complete |
| Selected fraction | 1 | dimensionless | Gate selection | Confirmed parent population; denominator count not requested | Present; complete |
| Selected percentage | 100 | percent | Gate selection | Confirmed parent population; denominator count not requested | Present; complete |
| Mean A | 130 | instrument_units | Encoded | Selected finite values; count not requested | Present; complete |
| Mean A | 65 | instrument_units | Scaled from encoded | Selected finite values; count not requested | Present; complete |
| Mean A, requested compensation | Unavailable | instrument_units | Requested compensation of scaled values | Selected finite values; count not requested | Unavailable; population extent: confirmed subset; measurement domain unavailable |
| Mean Time | 1.5 | seconds | Scaled from encoded | Selected finite values; count not requested | Present; complete |
| Supplied report value | 100 | percent | Supplied report | Sample and population association not returned | Present; producer execution not established by this return |
| Supplied report minus associated calculated value | 0 | percent | Saved calculated difference | Associated component definition not returned | Present; reported precision not returned |

| Measurement domain | Available definition |
| --- | --- |
| Encoded | Available; compensation not applied; transformation not applied |
| Scaled from encoded | Available; scaling applied; compensation not applied; transformation not applied |
| Requested compensation of scaled values | Unavailable; compensation state unknown |

| Requested qualification | Returned fact |
| --- | --- |
| Capture | A requested prepared-data artifact was unavailable |
| Saved numerical sheet | Returned for a separately selected recalculation |
| Underlying supplied-value observation or prediction provenance | Not carried by these numerical rows or requested definitions |
| Numerical uncertainty | Not supplied |

END ILLUSTRATIVE MODEL-FACING SUBSECTION

The example's synthetic status is a drafting qualification above, not a fabricated new fact source. Its parent fixture already supplies synthetic-input status in the TASK. For another real assignment, a renderer must preserve actually supplied observation/prediction/fixture provenance where it is already part of that parent's knowledge, and leave it unknown where it is absent. It must not call this example experimental biology.

This example intentionally does not describe the report as “the pass-all percentage” or say that its zero difference corroborates execution. The prepared Workflow fixture requests no native-report definitions; the association exists in retained child data but is not communicated by the selected context. The separately displayed saved difference remains useful as the requested numerical comparison without its unreturned descriptive link.

## Variations within this same boundary

These are field-selection rules for the same template, not proposed additional episode templates.

- If no context was requested, omit the definition tables. Keep the requested metric, literal unit, value/state, population extent, denominator kind and material issues. Use neutral row labels to retain internal distinctions. Say “sample/condition and measurement-domain definitions not requested”; do not label an opaque domain key as raw, scaled or compensated. For an intensity mean the exact remaining meaning is an arithmetic mean of finite values among events confirmed selected by the requested gate in the requested domain/channel. The biological analyte, domain processing, sample condition and numerical denominator may remain unknown.
- If the saved recalculation page uses the fixture's offset 2 and limit 4, only its four returned cells appear: fraction 1, percent 100, encoded A mean 130, scaled A mean 65. Show 4 of 10 selected cells returned and further selected rows available. Do not add the compensated mean or report rows from another page. A selection-wide partial status/issue can remain even when all four displayed cells are present.
- If context definitions were requested but absent, say “requested definitions unavailable.” Do not mislabel that as “not requested.” If a requested field is present with null, say “unknown.” A returned empty failure list means no failure facts in that requested return; it does not prove successful upstream laboratory work.
- If a control difference or report difference is negative, retain its sign. If a requested native value disagrees with its returned linked component, display each once and the requested saved difference once. Report declared rounding precision if returned; do not add a scientific conflict label or tolerance absent from the facts. Keep an explicit existing conflict issue visible.
- Preserve an unavailable or qualified row beside valid rows. Do not substitute a raw ancestor for a missing prepared value, drop the failed row, or blank the whole page. An empty page is not a measured zero-event population.
- When several returns are relevant, distinguish them by their semantic selection and qualification. Do not merge distinct receipts because numbers match. Do not replay unchanged historical tables merely to fill space. Removing a duplicate display copy is not deletion or repricing of a historical fact.

## Proposed ownership and existing ports, subject to review

1. A narrow read-only method in `fluorescence_returns.py` would prepare presentation groups from actual admitted immediate-child forms, using `_attempts`, `_attempt`, `_values`, `_historical`, and the original completed receipt facts. It would preserve paired projection/context ownership internally and include only sources the parent actually requested and received. It would not read numerical payloads, use the parent's own upward return schema as a proxy for its child request, or expose extra receipt facts. No typed return contract changes are proposed.
2. `ExecutionEpisodes.initial_decision_context` is an existing port for admitted scientific receiver facts, already used by RNA. A fluorescence group can be supplied there for this scientific parent. `runtime.DecisionSource.call` invokes this port for each new call while restoring saved original contexts unchanged. No private decision loop or additional observation is needed.
3. A proposed pure `fluorescence_result_presentation.py` would select the detached view and render these tables. Suggested responsibilities are `select_fluorescence_parent_presentation(state)` and `render_fluorescence_parent_returns(groups)`. They consume supplied records only. Shape/relationship errors preserve independent valid rows and produce a bounded presentation qualification rather than a guessed join; existing admission remains authoritative.
4. `scientific_process_prompt.render_episode_steering` would compose this selector with the existing selectors before `_steering`, then append the fluorescence table once. Remove only exact corresponding fluorescence copies from the detached `child_reports`/other actually rendered return locations; retain mixed unrelated fields. Saved-sheet IDs and file metadata stay internal. Only semantic availability is displayed here; exact typed saved-sheet operands remain governed by existing host/response contracts and must not be replaced with an invented human alias in any action.
5. The published scientific parent is already routed to `render_scientific_process_prompt` by `providers._presentation`. This boundary needs no fluorescence-specific TASK and no new parent episode selector. The provider's bootstrap/update/lookup reconstruction and unchanged complete `_task` need targeted presentation verification after user feedback. Generic legacy scientific or annotation receiver behavior is outside this one proposed template.

Code ownership would therefore be the new pure presentation module plus narrow additions in `fluorescence_returns.py`, `execution_episodes.py`, and `scientific_process_prompt.py`, with focused presentation/provider tests. No implementation is authorized by this draft itself. Existing numerical sheets, calculators, result/context projectors, custody validators, report schemas, provider response schema, controllers, credit, launch and results execution remain their existing owners.

## Evidence and remaining work

Source inspection established that `providers._presentation` recognizes the published scientific parent but has no fluorescence selector; `render_episode_steering` selects RNA-related views but no fluorescence; `_steering` sends `child_reports` through `alignment_report_presentation` and generic `_values` flattening. The alignment renderer leaves nonalignment reports intact. The resulting fluorescence fields therefore lack this selected semantic table path.

Read in full for this draft: fluorescence result/context/return projectors and result contracts/returns; fluorescence calculator; providers; scientific-process prompt; the two new prepared Workflow test files; the prepared synthetic fixture helper; TASK_AND_STEERING; AGENTS; tool-grader principles; EPISODE_STRUCTURE; TIME_AWARE_ESTIMATION; and prepared integration contracts019–021. Also traced the complete pertinent receiver, publication, original-return, initial-context and runtime dispatch functions listed in SOURCE_EVIDENCE.json. No source behavior was changed.

The new Workflow tests script decisions and supply synthetic FCS/recipe/report fixtures while asserting actual native libraries, retained results, scientific/annotation typed delivery, partial preservation, saved-only recalculation and replay. They do not call `providers._presentation` to establish the proposed final text. At drafting time this worker had inspected their source only and had no returned check049 example. The coordinator owns the bounded run and its actual outcome.

Completed here: one boundary analysis, exact admitted field/join rules, one full illustrative proposed subsection, source/stdlib inspection evidence. Unfinished: user review and feedback; any resulting revised draft; implementation; exact provider text capture on a verified admitted return; bootstrap/update/lookup restoration and mixed-return duplicate tests; missing-context, ambiguous-pairing, partial-page, negative/conflict, unknown-provenance and no-acquisition checks. None of these are claimed passed.

Before handoff, reread the original attachment's objective and entire operating-principles block verbatim, then contracts019–021 and TASK_AND_STEERING. This review requirement follows the original user direction; it is not a new runtime approval mechanism.
