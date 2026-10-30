# Reader/grader selection audit

This scoped audit follows the user's reusable-protocol requirement and subsequent hierarchy: **A105 experimental evidence subscore → subscoring grader → subscoring reader**. Information returns upward through that hierarchy. This report is evidence and a bounded correction record, not a goal, amendment, new scoring policy or claim that missing graders are implemented. The initial audit was read-only. Following the user's “Great. DO it” and the parent's explicit file assignment, the bounded recurring TASK guidance was implemented as recorded below.

## Finding

The actual operation-selection infrastructure does **not** dispatch on paper IDs, named proteins or chemical pairs. It advertises operations by their supported measurement and representation, and inserts detailed scientific instructions when a corresponding operation/return is actually selected. However, the recurring parent/child TASKs do not explicitly teach the required separation between assay-type grading and reader selection. Some narrow adapters really are source-specific, and the current A105 numerical composer does not accept all the outputs needed by the four biochemical type groupings. Improving selection wording is warranted; wording alone does not complete that implementation.

The four current biochemical groupings supplied by the parent from the latest user steering are:

1. Enzyme activity/rate comparisons.
2. Reaction progress/endpoint conversion.
3. Product distribution/equilibrium.
4. Reaction coupling/stoichiometric balance.

These are the type-level considerations under review. The fourteen existing reader entrypoints and their arithmetic are not fourteen additional assay graders. This audit neither changes the previously agreed experiment-type rows nor creates another layer between the user's three levels.

The four protocol groupings are **not four scoring axes**. They supply evidence for the same assessment purposes discussed with the user: reliability, validity and relevance. Attribution asks whether the measured effect is isolated to the assayed molecule; it is not a synonym for relevance to the functional claim. Existing `ASSAY_TASK` explicitly separates nuisance-condition comparability, effect isolation and the actually measured endpoint. Existing compiled-assay `SECTIONS` likewise separates recovery/validity, attributed rate/attribution, condition response/comparability and uncertainty. Signal strength, uncertainty, independent replication/dependence and contradictions must retain their actual meanings within the assessment; protocol-type routing does not replace these purposes.

## Actual selection path inspected

- `gene_annotation_episode/literature_episodes.py:69`, `_population_catalog`: constructs operation descriptions and input schemas. `instructions`, at line 820, supplies iterative reading instructions. The descriptors preserve the subject, conditions, source representation and exact anchors, but do not state the three-level hierarchy.
- `gene_annotation_episode/literature_experimental_prompt.py:82`, `EXPERIMENTAL_TASK`, and `_task` at line 366: supply recurring experimental instructions and list available operation descriptions/schemas. `_task` calls `selected_literature_task_sections`.
- `gene_annotation_episode/literature_reference_parent_prompt.py`: recurring `REFERENCE_PARENT_TASK`, `_task`, and renderer expose the child's available population operations and use the same selected-insert function.
- `gene_annotation_episode/literature_task_selection.py`, read completely: `_selected_operation_sources` chooses detailed inserts by operation/version; `_form_sources` uses requested return sources; `_row_source` identifies admitted numerical rows by scope/version; `selected_literature_task_sections` combines actual requested/owned/attempted work. None uses protein, chemical or paper identifiers as dispatch keys. Capability catalogs alone deliberately do not activate every method's detailed instructions.
- `gene_annotation_episode/knowledge/index.json`, the complete `source-representations.md` and `source-tables.md`: source reading is selected by retained text/PDF/image/XLSX representation and source context. The current library has no dedicated biochemical assay-type selection entry. Its instructions are not a hidden alternative grader router.

The pure selected-insert function should remain pure. A shared recurring instruction added to both parent and child TASK construction is a bounded correction. It should not activate every assay-specific insert merely because tools exist.

## Concrete before/after selection examples

| Current supported wording/code | Appropriate scientific selection and invocation |
|---|---|
| `EXPERIMENTAL_TASK`: “Select ordinary searches, source reads, neighboring context, tables, figures or the permitted narrower literature investigations when they can resolve this question.” This leaves the grader/reader distinction implicit. | Start with the requested A105 field and applicable reusable assay type. The selected grader determines needed quantities and scientific criteria. It chooses among supported readers by representation/layout. Interpret/calculates the supported outputs and returns them to A105 with their meaning, uncertainty and limits. |
| `COMPLETION_TIME_OPERATION_DESCRIPTION`: completion/equilibration time operands, same-endpoint ratios and explicit limitations. `completion_time_arguments_schema` supplies generic numerator/denominator meanings and exact source spans. | Use the endpoint-conversion type when reported time to a defined endpoint is informative. Put molecule, construct, preparation, endpoint, intended/other changes and time spans into the existing arguments. The HFP/Ru5P/R5P example is not a required key. A completion-time ratio remains a preparation timing comparison, not automatically an intrinsic rate ratio. |
| `product_partition_arguments_schema` accepts `quantities.a/b.meanings`, including compound, endpoint, denominator, basis and stage; relationships include same preparation/endpoint and shared denominator. | Use product-distribution/equilibrium considerations for compatible composition fractions. Supply actual compound identities as witnesses in `meanings.compound`, with actual fraction spans, basis and stage. Neither R5P nor Ru5P is built into this schema. |
| `read_product_coupling_inputs` reads `context`, product/cofactor `quantities`, source-backed `relationships` and `nu_cofactor_per_product`. | Use coupling/stoichiometric considerations when the question compares identified product with consumed cofactor under a justified reaction account. The particular product/protein appears in source context; stoichiometry and scientific compatibility remain explicit inputs. The P450cam example does not define the type. |
| `RATE_REPLICATE_OPERATION_DESCRIPTION` says “Select exact subject/experiment and reference/test groups”; its mapped table is not an arbitrary publisher parser. | These labels select the relevant rows *after* choosing a supported rate/replicate measurement path. They identify the observation population, not a new assay class. Sampling-unit fields choose valid averaging and conditional uncertainty. |
| `PARENT_DEPLETION_OPERATION_DESCRIPTION` says “one selected original XLSX analyte/time/submixture row” without naming its fixed column restriction. | Scientifically this is substrate-depletion endpoint evidence with active/inactive/abiotic controls. The current adapter is eligible only for its actual fixed header/column layout. `compound`, `submix`, `time_hours` and `sheet_name` are row-selection arguments. Do not call it a general depletion-assay parser. |
| `STOICHIOMETRIC_BALANCE_OPERATION_DESCRIPTION` truthfully says “Figure 2D XLSX” and G2/glucosyl/Pi. | Select a reusable reaction-accounting type upstream. This specific adapter can serve it only when the retained workbook matches the implemented Figure 2D layout and chemistry. It cannot currently process arbitrary enzyme stoichiometry merely by changing a name. |

Chemical identity is not irrelevant. A reporter's chemistry, calibration or stoichiometry can be an applicability requirement. The error is treating a named protein–substrate example or paper as the assay type, not checking whether the actual chemicals support the method's assumptions.

## Actual adapter restrictions

`literature_parent_depletion_inputs.py` was read completely. `HEADERS` fixes Time/Bio/Stdev1/Ab/Stdev2/inactive_enzyme/Stdev3/Compound/Submix/Difference columns. The reader filters literal compound, submix and time and validates those fixed headers. It does not hardcode capecitabine or P205, but it is still a restricted source-layout adapter. Its calculator produces the two endpoint-control differences and preserves their shared active observation; it is not a complete reliability grader.

`literature_stoichiometric_balance_inputs.py` was read completely. It fixes Data/Metadata, panel D, experiment marker row 50, header row 51, baseline row 52, G2–G6/Pi columns, calibration ranges, specific Metadata labels including the assayed enzyme and donor, and a source-specific Pi premise. Its returned molecule is hardcoded. This is more than a layout restriction: the current reader and associated arithmetic embed specific chemistry. General reaction-accounting capability is absent from that entrypoint. Its narrow tool description must remain honest until implementation changes.

The existing generic completion-time/product-partition/coupling schemas show that source identities can already be passed as arguments where the implementation is actually reusable. Those examples provide the appropriate pattern; they do not prove all fourteen operations are general.

## A105 numerical return binding

Both `literature_a105_worksheet.py` and `literature_a105_worksheet_render.py` were read completely. The former explicitly composes existing numerical fields without scientific inference or a new grade. `a105_worksheet_template` accepts an allowlist of sources and rejects others with `a105_worksheet_section_unimplemented`. That is a binding limitation distinct from reader capability.

| Current biochemical type | Existing numerical outputs relevant to the type | Current composer binding |
|---|---|---|
| Enzyme activity/rate comparisons | Compiled outputs include net/contaminant rate, recovery, amount, nuisance-control rates, attributed/corrected activity and conditional uncertainty. Source rate paths also return reported rates, differences/retained fractions; replicate paths supply descriptive/conditional sampling summaries. | Compiled v2/v3 and native kinetic/summary precision are accepted. Rate/rate-source, rate-observation, rate-replicate, simple-assay and controlled-response sources are absent from this composer's allowlist. This does not mean they cannot be returned in ordinary typed forms. |
| Reaction progress/endpoint conversion | Concentration differences, depletion fraction, supported interval-average rates; endpoint-signal components; active-minus-inactive/abiotic removal; `numerator_time`, `denominator_time`, `completion_time_ratio`, `inverse_completion_time_ratio`. | Concentration-window, endpoint-signal and parent-depletion sources are accepted. Completion-time is absent. |
| Product distribution/equilibrium | `partition_a_fraction`, `partition_b_fraction`, `selected_fraction_sum`, `selected_closure_deviation`, `partition_a_over_b`, plus witnessed stage/basis/denominator. | Product-partition is absent. No renderer branch compensates for this. |
| Reaction coupling/stoichiometric balance | Product/cofactor ratios, productive fraction subject to applicability and uncertainty; measured stoichiometric quantities and dependent accounting ratios/remainders; concentration-window chemical accounting. | Product-coupling, concentration-window and the narrow stoichiometric-balance source are accepted. The accepted narrow branch does not establish general chain/chemical accounting. |

The composer can preserve assertion relationships (`measures_asserted_endpoint`, `addresses_named_weakness`, etc.) and measurement-dependence links. These relationships do not supply an implemented four-type assay-grading transformation. The compiled activity model already has substantive corrections and applicability checks, but it is not a comprehensive numerical conversion of all four consideration lists.

## Bounded correction proposed to parent

Add common selection guidance to both recurring TASK surfaces, using the existing hierarchy. Keep the existing operation/return selection mechanism, schemas and actual capabilities unchanged. The guidance should say:

> For A105, follow A105 experimental evidence subscore → subscoring grader → subscoring reader. Choose the reusable assay-type grader from protocol, measured quantity, intended contrast and scientific applicability. Within that assessment, choose readers by the required measurements and actual supported source representation/layout. A named paper, case or protein–substrate example does not define a grader type. Actual identities, conditions, calibration and controls remain source-bound operands and may determine applicability. Shared calculations and alternate readers do not create additional graders. Interpret the recovered measurements against the selected type's considerations and return the requested numerical A105 fields with uncertainty, dependence and unresolved reasons. Reader extraction alone does not complete that assessment. Preserve an unavailable implementation/binding as unavailable rather than claiming completion.

The guidance must connect those type-specific considerations to reliability, validity and relevance without conflating attribution with relevance. Preserve the distinct questions of nuisance-condition comparability, isolation to the assayed molecule, and whether the endpoint resolves the functional assertion; retain signal/uncertainty, replication/dependence and contradictions. The four protocol types select the appropriate scientific considerations feeding those purposes, rather than becoming four new score axes.

Make the parent-depletion operation's fixed-layout restriction explicit; retain the truthful Figure 2D limitation of the stoichiometric operation. Do not rename either restricted implementation as general.

Prompt correction is not authorization to add four implementations or silently expand the worksheet. The actual missing bindings above require a separate bounded implementation decision by the parent within the user's task. Parent was informed before any production edit.

## Read ledger and limitations

Current root AGENTS.md, docs/TASK_AND_STEERING.md and docs/EPISODE_STRUCTURE.md are absent; docs/TOOL_KNOWLEDGE.md exists and was read fully. GOAL.md was not read. No goals, amendments or instruction files were changed. This child also received an explicit user revocation of earlier AGENTS instructions; its exact text was sent to the parent, which reported a different visible context.

Complete current reads: the two prior reports `verification/biochemical_assay_guides_318/REPORT.md` and `verification/biochemical_fourteen_graders_319/REPORT.md` (the latter's truncated middle was reread); `literature_task_selection.py`; `literature_reference_parent_prompt.py`; `literature_a105_worksheet.py`; `literature_a105_worksheet_render.py`; `literature_assay_prompt.py`; `literature_completion_time_prompt.py`; `literature_product_partition_prompt.py`; `literature_controlled_response_prompt.py`; `literature_product_coupling_prompt.py`; `literature_compiled_assay_prompt.py`; `literature_endpoint_signal_prompt.py`; `literature_concentration_window_prompt.py`; `literature_parent_depletion_prompt.py`; `literature_stoichiometric_balance_prompt.py`; `literature_rate_replicate_prompt.py`; the two narrow adapter input modules; `literature_parent_depletion_calculations.py`; current knowledge index and the two source-reading sections.

Complete relevant definitions read in larger files: `_population_catalog` and `LiteratureEpisodes.instructions`; `EXPERIMENTAL_TASK` and experimental `_task`; original `RATE_OBSERVATION_TASK`, operation description and its selected rate-curve TASK text (later rendering helpers were not audited); completion-time and product-partition argument-schema definitions; product-coupling argument schema and complete `read_product_coupling_inputs` entrypoint. Calculation component rosters/formula/meaning constants were inspected for compiled-assay, completion-time, product-partition and stoichiometric-balance, without claiming a fresh full numerical audit of those larger modules. Agent319 supplies the broader fourteen-entry calculation audit.

No tests were run during the initial read-only audit. Existing prompt tests were located. In particular, `tests/test_literature_gel_prompt.py` locks exact historical base TASK strings; directly rewriting those constants would affect that test. A shared standalone recurring TASK insert preserves existing scientific task text while adding the user's selection instruction.

## Authorized bounded implementation and validation

Production edits after the parent's explicit assignment:

- `literature_task_selection.py:49`: added `A105_ASSAY_SELECTION_TASK`, a shared string describing the hierarchy, four protocol groups, common reliability/validity/relevance/attribution purposes, explicit nuisance comparability, protocol-first selection and actual reader limits. All selected-operation and requested-source dispatch functions are unchanged.
- `literature_experimental_prompt.py:371`: its existing `_task` adds that shared insert once unless caller instructions already include it.
- `literature_reference_parent_prompt.py:63`: its existing `_task` adds the same insert once and removes a duplicate from caller-supplied additional instructions.
- `literature_parent_depletion_prompt.py:5`: operation description now explicitly identifies the fixed column layout and distinguishes row-selection operands from assay types. Its schema and implementation are unchanged. The already truthful Figure 2D operation description is unchanged.
- `tests/test_literature_assay_selection_guidance_320.py`: ten parametrized checks exercise both real prompt renderers, direct and contract-lookup profiles, recurring and deduplicated TASK placement, separation from factual STEERING, unchanged method selection when case/molecule identities change, catalog-only nonselection and visibility of both narrow-reader restrictions.

No original base TASK string, numerical formula, schema, operation identifier, worksheet binding, goal or amendment was changed. The sole added importable interface is the shared `A105_ASSAY_SELECTION_TASK` string. The report's audited missing numerical bindings remain findings for the separately assigned implementation work; this prompt patch does not claim to implement them.

Validation used `/tmp/gene-annotation-literature-py314-20261029/bin/python`:

1. New selection guidance tests plus complete experimental and reference-parent prompt tests: **41 passed**. An additional historical gel-baseline check in the same invocation failed on the **unchanged** `SAVED_NUMERICAL_RETURN_TASK`: the old fixture expects literal `x-source` copying while the code already used `episode-fact` references in the pre-edit read. The unchanged `EXPERIMENTAL_TASK` assertion immediately before it passed. This unrelated old fixture was not rewritten.
2. Existing selected-task/parent-capability checks: **8 passed**, covering `test_recurring_full_task_from_actual_sources_not_capabilities`, `test_full_recurring_task_both_directions_preserves_base_caller_and_steering` and `test_projection_renders_only_names_and_descriptions_and_preserves_task_dedup`.

Total observed: **49 passed, one historical baseline failure outside the changed guidance**. No failing numerical or reader behavior was observed. The workspace is not a Git checkout, so Git diff/status were unavailable; edits were bounded by the explicit patch paths above.
