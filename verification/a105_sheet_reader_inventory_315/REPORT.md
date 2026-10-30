# A105 numerical subscoring sheets and readers: code inventory

Existing implementation contains **36 numerical subscoring sheets and 55 named reader functions**. The recovered earlier roster contains **eight experiment types**. These counts describe the existing implementation; they do not authorize 36 experiment types or establish 36 completed assay grades.

A subscoring sheet is counted when it holds numerical components used for scoring a hierarchically higher sheet later. A final grade is not required. Reused readers and schema aliases do not create additional sheets. Each reader function definition is counted once. Standard-library/Pillow dependencies, private lexical helpers, schema validators, storage retrieval methods, source acquisition metadata parsers and other-axis-only readers are excluded. `Workbook.rows` is included because bespoke XLSX input readers call it.

The 55 reader functions comprise 39 direct population readers, 13 shared source readers beneath them, and three retained standalone/older readers. These are descriptions of functions in the one reader count, not additional experiment categories.

## Mapping to the eight recovered experiment types

The type names are recovered in [PRIOR_CONVERSATION_ROSTER.md](PRIOR_CONVERSATION_ROSTER.md). Assignments below are primary mappings for this inventory, not recovered historical assignments of every later sheet. Broad controlled-response, compiled-assay, concentration-window and electrical-channel sheets may overlap other existing types. Six sheets remain shared across these eight; they do not constitute a ninth type.

| Earlier experiment type | Existing numerical sheets | Distinct direct reader functions |
|---|---:|---:|
| 1. Biochemical activity/rate assays | 13 | 14 |
| 2. Enzyme kinetics and substrate specificity | 4 | 4 |
| 3. Ligand binding and binding discrimination | 4 | 4 |
| 4. Transport/substrate-response comparisons | 3 | 3 |
| 5. NADH optical-rate assays | 1 | 1 |
| 6. Partner-removal/addback experiments | 1 | 1 |
| 7. Reported protein-signal/band ratios | 2 | 3 |
| 8. Protein amount/preparation composition | 2 | 2 |
| Shared across the eight existing types | 6 | 7 |
| **Total** | **36** | **39** |

## All numerical subscoring sheets

Links below identify actual numerical schema and reader definitions. [INVENTORY.json](INVENTORY.json) also supplies population locations; [SHEETS.tsv](SHEETS.tsv) is the flat sheet inventory. All 36 have implemented LiteratureEpisodes population routes. That is static call-route evidence, not a claim that every route was executed during this inventory. The A105 overall scoring sheet is the hierarchy parent and is not added to this subscoring-sheet total.

| # | Numerical subscoring sheet | Primary earlier type | Schema definition | Direct readers |
|---:|---|---|---|---|
| 1 | Corrected preparation endpoint activity | 1 | [assay_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_assay_storage.py:240) | [read_assay_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_assay_inputs.py:326) |
| 2 | Source rate contrast | 1 | [rate_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_storage.py:808) | [read_rate_table](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_reader.py:58); [read_rate_source_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_native_inputs.py:325) |
| 3 | Single reported quantity | Shared | [quantity_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_quantity_storage.py:172) | [read_jats_quantity](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_prose_reader.py:109); [read_html_quantity](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_html_quantity_reader.py:190) |
| 4 | Reported relative protein signal | 7 | [ratio_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ratio_storage.py:227) | [read_jats_relative_percent](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ratio_reader.py:56); [read_relative_signal_source_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ratio_source_inputs.py:395) |
| 5 | Binding parameter contrast | 3 | [binding_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_storage.py:219) | [read_binding_parameter_table](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_reader.py:113) |
| 6 | Binding statistical model | 3 | [binding_model_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_model_storage.py:216) | [read_binding_model](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_model_inputs.py:71) |
| 7 | Transport substrate response | 4 | [transport_response_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_transport_storage.py:285) | [read_transport_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_transport_inputs.py:147) |
| 8 | Figure ordinate measurement | Shared | [figure_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_figure_storage.py:433) | [read_figure_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_figure_inputs.py:133) |
| 9 | Partner omission and addback | 6 | [partner_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_storage.py:937) | [read_partner_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_inputs.py:60) |
| 10 | Protein amount and composition | 8 | [amount_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_amount_storage.py:237) | [read_amount_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_amount_inputs.py:375) |
| 11 | NADH optical rate | 5 | [optical_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_optical_storage.py:495) | [read_optical_rate_operands](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_optical_inputs.py:342) |
| 12 | Kinetic parameter contrast | 2 | [kinetic_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_storage.py:410) | [read_kinetic_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_inputs.py:576) |
| 13 | Binding discrimination interaction | 3 | [binding_interaction_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_interaction_storage.py:438) | [read_binding_interaction_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_interaction_inputs.py:683) |
| 14 | Kinetic statistical model | 2 | [kinetic_model_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_model_storage.py:362) | [read_kinetic_model](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_model_inputs.py:18) |
| 15 | Binding interaction statistical model | 3 | [binding_interaction_model_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_interaction_model_storage.py:478) | [read_binding_interaction_model](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_interaction_model_inputs.py:21) |
| 16 | Controlled response contrast | 1 | [controlled_response_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_storage.py:62) | [read_controlled_response_v3_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_v3_inputs.py:310) |
| 17 | Gel band and lane measurements | 7 | [gel_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_gel_native_contracts.py:74) | [read_gel_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_gel_inputs.py:324) |
| 18 | Reaction completion time | 1 | [completion_time_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_completion_time_storage.py:233) | [read_completion_time_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_completion_time_inputs.py:126) |
| 19 | Active-site titration amount | 8 | [active_site_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_active_site_storage.py:380) | [read_active_site_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_active_site_inputs.py:146) |
| 20 | Product partition | 1 | [product_partition_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_product_partition_storage.py:269) | [read_product_partition_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_product_partition_inputs.py:159) |
| 21 | Reported rate observations | 1 | [rate_observation_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_observation_storage.py:107) | [read_rate_observations](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_observation_inputs.py:90) |
| 22 | Reported concentration-rate curve precision | 2 | [rate_grid_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_observation_storage.py:361) | [read_reported_rate_grid](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_observation_inputs.py:349) |
| 23 | Raw rate replicate contrast | 1 | [rate_replicate_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_replicate_storage.py:178) | [read_rate_replicate_table](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_replicate_inputs.py:39) |
| 24 | Calibration recovery | Shared | [calibration_recovery_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_calibration_recovery_storage.py:67) | [read_calibration_recovery_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_calibration_recovery_inputs.py:245) |
| 25 | Measurement precision and control separation | Shared | [measurement_validation_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_measurement_validation_storage.py:62) | [read_measurement_validation_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_measurement_validation_inputs.py:419) |
| 26 | Product and reporter coupling | 1 | [product_coupling_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_product_coupling_storage.py:77) | [read_product_coupling_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_product_coupling_inputs.py:284) |
| 27 | Compiled within-assay correction (v1/v2) | 1 | [compiled_assay_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_compiled_assay_storage.py:164) | [read_compiled_assay_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_compiled_assay_inputs.py:391) |
| 28 | Common functional assertion contrast (compiled v3) | Shared | [compiled_assay_v3_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_compiled_assay_storage.py:47) | [read_common_assessment_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_compiled_assay_inputs.py:909) |
| 29 | Finite endpoint signal correction | 1 | [endpoint_signal_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_endpoint_signal_storage.py:35) | [read_endpoint_signal_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_endpoint_signal_inputs.py:321) |
| 30 | Kinetic summary precision | 2 | [summary_precision_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_summary_precision_storage.py:34) | [read_kinetic_summary_precision_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_summary_precision_inputs.py:717) |
| 31 | Measurement-method comparison | Shared | [measurement_comparison_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_measurement_comparison_storage.py:36) | [read_measurement_comparison_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_measurement_comparison_inputs.py:397) |
| 32 | Concentration-window and product-fate measurements | 1 | [concentration_window_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_concentration_window_storage.py:33) | [read_concentration_window_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_concentration_window_inputs.py:526) |
| 33 | Electrical channel measurements | 4 | [channel_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_channel_storage.py:128) | [read_channel_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_channel_inputs.py:294) |
| 34 | Ion discrimination | 4 | [ion_discrimination_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ion_discrimination_storage.py:61) | [read_ion_discrimination_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ion_discrimination_inputs.py:775) |
| 35 | Parent-compound depletion | 1 | [parent_depletion_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_parent_depletion_storage.py:23) | [read_parent_depletion_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_parent_depletion_inputs.py:49) |
| 36 | Soluble-product stoichiometric balance | 1 | [stoichiometric_balance_cells_schema](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_stoichiometric_balance_storage.py:22) | [read_stoichiometric_balance_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_stoichiometric_balance_inputs.py:69) |

## All named reader functions

[READERS.tsv](READERS.tsv) provides these function names, source paths, lines and wiring status.

| # | Reader definition | Wiring status |
|---:|---|---|
| 1 | [read_active_site_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_active_site_inputs.py:146) | direct selected population reader |
| 2 | [read_amount_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_amount_inputs.py:375) | direct selected population reader |
| 3 | [read_assay_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_assay_inputs.py:326) | direct selected population reader |
| 4 | [read_bar_ordinate](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_figure_measurements.py:120) | shared: read_figure_inputs pixel ordinate reader |
| 5 | [read_binding_interaction_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_interaction_inputs.py:683) | direct selected population reader |
| 6 | [read_binding_interaction_model](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_interaction_model_inputs.py:21) | direct selected population reader |
| 7 | [read_binding_model](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_model_inputs.py:71) | direct selected population reader |
| 8 | [read_binding_parameter_table](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_reader.py:113) | direct selected population reader |
| 9 | [read_binding_visual_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_binding_visual_inputs.py:371) | standalone: no current LiteratureEpisodes caller found |
| 10 | [read_calibration_recovery_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_calibration_recovery_inputs.py:245) | direct selected population reader |
| 11 | [read_channel_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_channel_inputs.py:294) | direct selected population reader |
| 12 | [read_common_assessment_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_compiled_assay_inputs.py:909) | direct selected population reader |
| 13 | [read_compiled_assay_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_compiled_assay_inputs.py:391) | direct selected population reader |
| 14 | [read_completion_time_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_completion_time_inputs.py:126) | direct selected population reader |
| 15 | [read_concentration_window_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_concentration_window_inputs.py:526) | direct selected population reader |
| 16 | [read_controlled_response_arm_science](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_inputs.py:1913) | shared: called by read_controlled_response_v3_inputs |
| 17 | [read_controlled_response_covariance_document](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_inputs.py:2646) | shared: called by read_controlled_response_v3_inputs |
| 18 | [read_controlled_response_graph_measurement](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_inputs.py:2601) | shared: called by read_controlled_response_v3_inputs |
| 19 | [read_controlled_response_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_inputs.py:1209) | retained v1: current selected population uses v3 |
| 20 | [read_controlled_response_rate_figure](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_figure_inputs.py:641) | shared: v2._read_graph, reached by current v3 graph reader |
| 21 | [read_controlled_response_text_measurement](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_inputs.py:1968) | shared: called by read_controlled_response_v3_inputs |
| 22 | [read_controlled_response_v2_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_v2_inputs.py:484) | retained v2: current selected population uses v3 |
| 23 | [read_controlled_response_v3_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_controlled_response_v3_inputs.py:310) | direct selected population reader |
| 24 | [read_defined_rate_unit](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_defined_units.py:223) | shared: native partner defined-U rate unit reader |
| 25 | [read_endpoint_signal_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_endpoint_signal_inputs.py:321) | direct selected population reader |
| 26 | [read_figure_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_figure_inputs.py:133) | direct selected population reader |
| 27 | [read_gel_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_gel_inputs.py:324) | direct selected population reader |
| 28 | [read_html_quantity](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_html_quantity_reader.py:190) | direct selected population reader |
| 29 | [read_ion_discrimination_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ion_discrimination_inputs.py:775) | direct selected population reader |
| 30 | [read_ion_number](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ion_discrimination_numbers.py:69) | shared: read_ion_discrimination_inputs |
| 31 | [read_ion_unit](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ion_discrimination_numbers.py:156) | shared: read_ion_discrimination_inputs |
| 32 | [read_jats_quantity](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_prose_reader.py:109) | direct selected population reader |
| 33 | [read_jats_relative_percent](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ratio_reader.py:56) | direct selected population reader |
| 34 | [read_kinetic_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_inputs.py:576) | direct selected population reader |
| 35 | [read_kinetic_model](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_model_inputs.py:18) | direct selected population reader |
| 36 | [read_kinetic_summary_precision_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_kinetic_summary_precision_inputs.py:717) | direct selected population reader |
| 37 | [read_measurement_comparison_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_measurement_comparison_inputs.py:397) | direct selected population reader |
| 38 | [read_measurement_validation_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_measurement_validation_inputs.py:419) | direct selected population reader |
| 39 | [read_optical_rate_operands](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_optical_inputs.py:342) | direct selected population reader |
| 40 | [read_parent_depletion_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_parent_depletion_inputs.py:49) | direct selected population reader |
| 41 | [read_partner_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_inputs.py:60) | direct selected population reader |
| 42 | [read_partner_native_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_native_inputs.py:251) | shared: called by read_partner_inputs |
| 43 | [read_product_coupling_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_product_coupling_inputs.py:284) | direct selected population reader |
| 44 | [read_product_partition_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_product_partition_inputs.py:159) | direct selected population reader |
| 45 | [read_rate_observations](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_observation_inputs.py:90) | direct selected population reader |
| 46 | [read_rate_replicate_table](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_replicate_inputs.py:39) | direct selected population reader |
| 47 | [read_rate_source_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_native_inputs.py:325) | direct selected population reader |
| 48 | [read_rate_table](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_reader.py:58) | direct selected population reader |
| 49 | [read_relative_signal_source_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_ratio_source_inputs.py:395) | direct selected population reader |
| 50 | [read_reported_rate_grid](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_rate_observation_inputs.py:349) | direct selected population reader |
| 51 | [read_source_number](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_source_fields.py:267) | shared: native partner, rate, calibration and channel input readers |
| 52 | [read_source_rate_unit](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_partner_source_fields.py:347) | shared: native partner, rate and product coupling readers |
| 53 | [read_stoichiometric_balance_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_stoichiometric_balance_inputs.py:69) | direct selected population reader |
| 54 | [read_transport_inputs](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/literature_transport_inputs.py:147) | direct selected population reader |
| 55 | [Workbook.rows](/home/chia/repos/gene_annotation_episode/gene_annotation_episode/spreadsheet_tools.py:155) | shared: original XLSX row parser used by P205/CcCdP input readers |

## Version and alias treatment

- Source-rate legacy/native readers populate the same rate-component sheet. The `literature_rate_cells`, `literature_rate_source_cells`, `literature_rate_source_domain_cells` and `literature_rate_source_meaning_cells` namespaces are not four independent numerical sheets.
- Relative-signal legacy/source readers reuse the same seven numerical component meanings. `relative_signal_sheet_v2` in `literature_ratio_source_calculations.py` explicitly preserves the v1 meanings. These are one sheet and two readers.
- Compiled-assay v2 invokes the v1 population and extends that within-assay sheet with uncertainty cells. They count as one versioned sheet. Compiled-assay v3 has distinct common-assessment formulas and is a separate sheet.
- Kinetic, binding and binding-interaction model results have distinct persisted numerical schemas. They count as sheets even though they consume underlying parameter measurements.
- `literature_a105_worksheet.FAMILIES` contains 13 registered definitions. It does not enumerate every numerical subscoring sheet implemented in storage/population routes.

## Verification limits

This inventory used actual storage schemas, population methods, public reader definitions and LiteratureEpisodes routes, rather than counting documentation titles alone. It does not assess scientific correctness of every calculation, read every byte of every large reader, execute every population path, or establish that the current arrangement meets the newly fixed eight-type sheet requirement. No implementation, goal, experiment type, reader or scientific dataset was changed.
