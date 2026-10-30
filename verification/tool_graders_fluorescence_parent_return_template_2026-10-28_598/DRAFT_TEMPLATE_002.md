# Shorter draft: fluorescence results child to scientific parent steering

Additive presentation revision after coordinator feedback, 2026-10-28. Preserve DRAFT_TEMPLATE_001.md as the earlier draft and its field/receipt trace. This remains one proposed boundary and has not been approved by the user or implemented. The parent's complete TASK and its real own-action yield/expectation/uncertainty table remain in their existing locations.

The following subsection uses illustrative synthetic fixture expectations only. This worker has not inspected actual check049 returns and does not claim that the full Workflow passed. It is not a new annotation or experimental measurement.

BEGIN ILLUSTRATIVE MODEL-FACING SUBSECTION

Requested fluorescence results: partial; 10 of 10 requested cells returned.

Sample α; condition and biological/technical replicates unknown. Pass-all gate over all declared primary events. Channel A analyte unknown.

| Requested quantity | Value | Unit | Representation |
| --- | --- | --- | --- |
| Retained event count | 2 | events | Primary encoded events |
| Selected event count | 2 | events | Pass-all gate |
| Selected fraction | 1 | dimensionless | Calculated gate selection |
| Selected percentage | 100 | percent | Calculated gate selection |
| Mean A | 130 | instrument_units | Encoded |
| Mean A | 65 | instrument_units | Scaled from encoded |
| Mean A | Unavailable | instrument_units | Requested compensation of scaled values |
| Mean Time | 1.5 | seconds | Scaled from encoded |
| Supplied report value | 100 | percent | Reported number |
| Report minus associated calculated value | 0 | percent | Saved calculated difference |

Fractions use the confirmed parent population; intensity means use selected finite values. Their numerical denominator counts were not requested.

Compensated-domain values are unavailable; compensation state is unknown. The unavailable mean has population extent “confirmed subset.” A requested prepared-data artifact was unavailable during capture; its association with a particular domain was not returned.

The report's sample/population association and precision were not returned. Its zero difference does not establish producer execution. Observation-versus-prediction provenance and numerical uncertainty are not supplied by these returned fields.

END ILLUSTRATIVE MODEL-FACING SUBSECTION

## Retained selection rules

Use the original admitted form's x-source contracts. Keep projection and context paired through the same authenticated result receipt, with equal selection; never zip independently deduplicated arrays or infer pairing from equal selectors. Render actual page rows once, in request order, without recalculation.

Within that paired context, ordinary cells join sample by `population.sample_key`; intensity joins domain/channel by the exact request keys; gate cells join the requested gate and its declared ancestors. Domain state, scale kind and preparation states determine the representation label. No wrapper-name inference, event arrays, raw report, IDs, hashes or runtime tracking enter the text.

The prepared fixture returns samples/channels/domains/populations/gates, but no native-report definitions. Native-comparison cell populations have null sample/gate/domain/channel and denominator `none`. Therefore a matching nearby percentage does not establish the report association. Without requested native-report context the metric, number, literal unit, state/extent and issues remain known, while sample, condition, linked component and report precision remain unspecified.

If no context was requested, keep the numerical metric/unit/state, denominator kind, extent and issues, use neutral labels, and say the sample/domain definitions were not requested. Do not fetch them. Negative values, signed differences, unavailable rows and material conflicts remain visible. Selection-wide status/issues must not be mislabeled as page-only or row-specific findings.

## Missing fields and implementation limits

Per-event `observed`/`supplied_predicted` state and supplied-report producer-execution provenance do not appear in the current numerical/context return contracts. Report association can be requested through the existing native_reports context family; it must not be fetched when unrequested. Numerical denominator counts require the corresponding selected count cells. The current cell contract supplies no sampling uncertainty.

The proposed read-only host grouping, existing `ExecutionEpisodes.initial_decision_context` port, pure presentation selector/renderer, and `scientific_process_prompt.render_episode_steering` ownership remain as described in draft001. No calculation, execution, typed return, credit, continuation or historical record change is proposed. User feedback, implementation and exact provider-text verification remain unfinished.

This shorter subsection omits context-family inventories, repeated present/complete labels and duplicate domain/availability tables. Saved-sheet availability and generic completion status remain in their existing typed return owners; they do not need a duplicate fluorescence numerical table row.
