# Case034: original-source defined-unit verification

The existing pin030 native reader works on this paper's actual unit-definition syntax. Both the Table 2 multi-endpoint definition and Methods NADH-specific definition populate the same five numerical rate components. No production correction is justified by these witnesses. This is A105 source experimental evidence; exactly ten axes remain, and A101, target correspondence, W05 and final annotation credit are outside this verification.

The organism is C. kluyveri DSM 555; the measured preparation is purified butyryl-CoA dehydrogenase/Etf complex. The chosen comparison is Table 2 **Fd + Hyd versus Hyd**, within the NADH oxidation section. Both arms contain the assayed complex; these are assay additions, not replacement of one protein by another. The intended difference is added ferredoxin while hydrogenase remains present. Physical observation/preparation replicate identities, statistical independence and sampling uncertainty are not established.

This differs deliberately from 031's retained **no-addition** wording: the source table has separate `No addition` and `Hyd` rows, each printed as 0.1. Comparing Fd+Hyd with no addition changes both partners. Comparing Fd+Hyd with Hyd keeps hydrogenase and changes ferredoxin. Equal printed values do not make those experiments interchangeable. No historical031 file was edited or its interpretation silently replaced.

Common Table 2 NADH-assay conditions are 1 ml, 25°C, 50 mM Tris-HCl pH7.5, 0.1 mM NADH, 0.1 mM crotonyl-CoA, 5 μM FAD, 2 mM DTT and 0.01 mg purified complex. The additions are 20 μM ferredoxin and 0.4 U C. pasteurianum hydrogenase where indicated; methyl viologen is absent in these selected row labels. Reaction starts with crotonyl-CoA. The rate mass denominator is mg of the assayed complex preparation, not molar enzyme amount or an isolated Bcd subunit.

The measured endpoint is photometric NADH oxidation. It is neither direct ferredoxin quantification nor isolated product formation. Ferredoxin can change this preparation endpoint while the larger mechanistic conclusion still requires the paper's other experiments. The source reports preparation variability, lability, lag periods and rates not always proportional to enzyme amount. Those qualifications survive the numerical contrast. This verification does not fabricate quantitative calibration, contaminant subtraction or uncertainty from them.

| Existing sheet cell | Value | Meaning |
|---|---:|---|
| reference_rate | 7 μmol/min/mg | NADH oxidation with Fd+Hyd |
| test_rate | 0.1 μmol/min/mg | NADH oxidation with Hyd |
| rate_difference | 6.9 μmol/min/mg | reference minus test preparation endpoint |
| retained_fraction | 0.014285714285714287 | test/reference |
| fractional_decrease | 0.9857142857142858 | 1−test/reference |
| reference_mean_se | null | mean_uncertainty_unreported |
| test_mean_se | null | mean_uncertainty_unreported |
| difference_se | null | dependence_unknown |
| signed_profile_log_ratio | null | observation_model_unspecified |
| source_signed_index | null | observation_model_unspecified |

The exact source amount is 1 μmol NADH oxidized per minute per activity unit. The existing definition validator produces 1,000,000 pmol/min per unit; the native rate adapter divides by 1,000,000 to the existing μmol/min/mg sheet basis. It parses the coefficient from the source. No universal U conversion is introduced. The header supplies U/mg; the footnote identifies the preparation mass and assay conditions. The parenthesized 14 is the 37°C activity and is not selected as the 25°C arm.

`SELECTION_TABLE.json`, `SELECTION_METHODS.json` and their saved extractions retain exact original-source byte witnesses for both rows, endpoint header, U/mg header, common condition footnote, intended change and complete definition bridge/clause/amount/entity/time associations. These source selectors use the run024 retained **text representation**, SHA256 `7944c5568b1ee0f8ff343be2a7f57c1b28e2e71d4e480fd984ac668136e0357f`; they do not reuse031 offsets from a different deterministic text rendering.

# Executed behavior

Seven direct cases passed their assertions: Table 2 definition, Methods definition, undefined U/mg, foreign-branch entity, wrong endpoint entity, changed quote and censored test. The undefined-U case preserves all ten nulls with `source_defined_unit_definition_required`. Foreign-branch selection fails `defined_unit_containment_required`; wrong entity fails `defined_unit_entity_mismatch`; changed quote fails `source_quote_mismatch`. A source `<0.01` test preserves threshold 0.01 and bound `lt`; it does not yield an observed zero or a point contrast. The final censored selector explicitly sets the intended change to crotonyl-CoA omission (`CENSORED_SELECTION_002.json`); the first direct pass was only a scalar-qualification probe with its old intended-change field, not a scientific claim about that pair. Its numerical outputs are unchanged.

An ordinary selected `literature.rate.source.populate` action ran in existing LiteratureEpisodes/shared method_loop, using scripted choices and test continuation controllers. The child returned seven requested cells through the closed `literature_rate_source_cells` source under the parent-selected field `requested_source_rate_cells`. The source numbers and definitions were real retained paper bytes; the choices/controllers and tiny target sequence used only to initialize the Store are test fixtures. This is **not actual model-backed success**.

The owned controlled store contains three actions and three observations: one child population, the parent's commission completed by that return, and the parent's own source-subject reasoning action. Their credit deltas are all zero. Extraction, definition validation, arithmetic, fact construction, delivery and reopen create no extra controller observations. One rate operation, one native received subset and one report attempt exist; the legacy received subset is empty. All ten cells remain in the child sheet while only seven requested cells cross the boundary. No scientific observation/assessment or target annotation is asserted.

The process then reopened its own saved state and recovered the original sheet and typed projection. `SAVED_ONLY_RECHECK_002.json` is the stronger saved-only verification: source artifact reads, native parsing and population calculation were forbidden, seven public tables remained equal, and 137 imported code files matched the original imported pin. The earlier recheck helper loaded paper bytes at import before its guard; its receipt is preserved and explicitly corrected by002. Its first guard alone did not prove a source-free process.

No model was launched, resumed or closed. No pin, actual model-run arguments, live history, controller or production file was modified. Actual run024's missing numerical delivery is not repaired or repriced by this new test. The full active goal and actual-model nonnull numerical delivery remain unfinished.

# Narrow proposed instruction refinement, draft only

For a requested native source-rate comparison, first identify the actual measured endpoint and both table arms. When the header uses U/mg, locate the source's definition for that endpoint. Select its exact definition bridge and the matching amount, amount unit, analyte and time clause; keep the complete original clause rather than rewriting its syntax. Bind that same endpoint witness in the arm and definition. Distinguish alternate endpoint clauses and temperature-qualified numbers. Retain the common assay conditions and each arm's additions, mass denominator and deliberately changed variable. Equal numbers in different rows do not make their interventions equivalent. Leave uncertainty and statistical assumptions unknown when unreported; let the existing reader/calculator parse and calculate the requested cells.

This is a printable draft for running feedback. It is not wired into a prompt, an accepted new template, a new scoring sheet or a runtime requirement.
