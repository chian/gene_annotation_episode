# A105 figure and plot extraction: what exists, where, and what is missing

Date of check: 2026-11-19. Read-only survey. Current tree = the RAM copy; old tree = commit 97308b94c.
Terms: a "model-selected tool" is something the language model chooses to call in an episode; a "grader" is one of the
eight scoring routines for an assay; "digitizing" means reading a number off a picture by measuring pixels (for example the
height of a bar against a calibrated axis); a "region of interest" (ROI) is the rectangle of pixel coordinates in an image that
a digitizing call is told to measure; "image.view" is the old tool that showed the actual image pixels to the model on its
next reasoning call.

## Short answer

The owner remembers correctly. In the old A105 episodes the model could call `image.view`, which put a figure in front of it,
and it could then call population operations that measure bars (and gel bands) in the image. In the current A105 episodes the
measuring half survives as library code and as population operations, but the looking half (`image.view`) is gone, and nothing
else lets the model see pixels. The only current figure-related model tool is `source.pdf.page`, which renders a PDF page to a
PNG file but, in its own words, "does not by itself supply image input to a model". So the model can produce an image but
cannot look at it, and the digitizing operations need it to name pixel coordinates and colour thresholds from what it saw.

## Table

Columns: Era = current tree or old tree (97308b94c). Used by = model-selected tool, grader input, or library-only.
All current paths are under /tmp/ramrepo/gene_annotation_episode/episodic_workflow/ . "lit" = episode_support/literature.

| File | Name | What it does | Era | Used by |
|---|---|---|---|---|
| episode_support/tools/experimental_activity_evidence/tools.py (line 67) | `source.pdf.page` | Renders one chosen PDF page to a PNG source file with pdftoppm. Does not show it to a model or interpret it. | Current | Model-selected tool (offered in the head and every A105 child task.py, including the table leaf) |
| (not present) | `image.view` | Showed one image frame to the model on its next reasoning call. | Current: absent from A105 tools.py and every A105 tool list. Other axes (evolutionary_history, biochemical_feasibility, perturbation, sample_context) still implement it in their own tools.py. | Model-selected tool (other axes only) |
| lit/forms/experimental_activity_evidence/literature_figure_measurements.py | `read_bar_ordinate`, `compare_ordinate_cells` | Measures the top edge of a coloured bar in a PNG/JPEG inside a given ROI, using a caller-given colour range and axis calibration; returns the value plus a pixel-tolerance range. Second function subtracts two such values. | Current (also in old A105 library) | Library function, called by the figure population operation |
| lit/inputs/experimental_activity_evidence/literature_figure_inputs.py | `read_figure_inputs`, `figure_population_schema` | Checks the request for the bar-reading operation, fetches the retained image bytes, runs the bar reader on the first and second bar, records the meaning the model supplied (which molecules, which endpoint, repeats, spread kind). | Current | Library, called by the operation below |
| lit/storage/experimental_activity_evidence/literature_figure_storage.py | `LiteratureFigureRepository` (operation `literature.figure.populate`) | Saves the bar values (first, second, difference) as a sheet of cells with conditional-digitization bounds; "mean-bar" version, plus an "endpoint-signal" version. | Current (old: scoring/literature_figure_storage.py in the old source_evidence_examination folder) | Model-selected tool: `literature_figure_populate` in published_evidence_assessment, evidence_search_strategy_improvement, source_relevance_assessment, source_evidence_examination, passage_evidence_extraction, source_coverage_improvement task.py. NOT in the head and NOT in the table leaf. Only offered when settings `rate_population` is true (other flags per operation). |
| lit/inputs/experimental_activity_evidence/literature_controlled_response_figure_inputs.py | linear-bar rate operands (`controlled_response_rate_figure_selection_v1`) | Same bar measurement for protein-present versus protein-free (or empty vector) responses, with the model nominating the axis and bar region. | Current | Library, inside operation `literature.controlled_response.source_v3.populate` (flag-gated) |
| lit/inputs/experimental_activity_evidence/literature_controlled_response_v3_inputs.py (and _v3_population.py) | graph measurements and pixel result | Pixel-measured values are labelled `graph_digitized` and carried with a digitization interval and the qualification `conditional_digitization_not_sampling`. | Current | Library inside the controlled-response v3 operation |
| lit/calculations/experimental_activity_evidence/literature_controlled_response_*calculations.py (calculations, local_calculations, owner_calculations) | controlled-response calculations | Arithmetic on the operands above (differences, variances, contrasts), including figure-derived ones (the word "digitiz" appears in all three). | Current | Library, feeding the controlled-response sheet |
| lit/inputs/experimental_activity_evidence/literature_binding_visual_inputs.py | `read_binding_visual_inputs` | Checks binding values the model transcribed from images (IC50, Hill-fit Kd): it verifies image bytes and geometry, not the transcribed text. No OCR (automatic text recognition). | Current | Library, inside `literature.binding.populate` and `literature.binding.interaction.populate` |
| lit/inputs/experimental_activity_evidence/literature_gel_inputs.py, lit/calculations/.../literature_gel_calculations.py, lit/storage/.../literature_gel_storage.py | `literature.gel.populate` | Measures band darkness in selected lane/band/background regions of a grayscale gel image. Not graph axes. | Current | Model-selected operation (flag `gel_population`), result goes to the protein_signal grader |
| lit/inputs/experimental_activity_evidence/literature_endpoint_signal_inputs.py, lit/storage/.../literature_endpoint_signal_storage.py | endpoint-signal population (a version of `literature.figure.populate`) | Reads selected points from a trace image for amplitudes and correction fractions. | Current | Model-selected operation (same tool as the bar one) |
| lit/readers/experimental_activity_evidence/literature_summary_figure_reader.py, lit/grading/.../literature_perturbation_summary.py | `read_summary_figure` | Digitizes a summary-graph bar and attaches `digitization` (lower, upper) to a perturbation summary entry. Wired to the perturbation summary storage; no A105 episode task.py calls it. | Current | Library (perturbation summary route); relation to A105 not determinable |
| lit/prompts/literature_figure_prompt.py | `FIGURE_TASK` | Instruction text for figure work: identify mean fill edge, axis, units; use the bar reader only for a linear axis with explicit calibration; keep digitization bounds separate from SD/SEM. | Current (wired in lit/readers/.../literature_task_families.py) | Prompt text |
| lit/prompts/experimental_activity_evidence/literature_controlled_response_prompt.py, literature_gel_prompt.py | operation descriptions | Tell the model the image reader is for "nominated linear mean-bar images", "not OCR, gels or arbitrary graph types" (controlled response) and "no graph-axis extraction" (gel). | Current | Tool descriptions the model reads |
| lit/forms/experimental_activity_evidence/literature_population_catalog.py | `population_catalog` | Lists the operations the model may be offered; the entries for figure, binding, ratio, binding.interaction mention images or pixels. | Current | Builds the model's tool list |
| lit/inputs/experimental_activity_evidence/literature_assay_grading_inputs.py (lines 201-202, 293-295) | origin `graph_derived` | If any input came from digitizing, the grader input is tagged `graph_derived` and the qualification `contains_graph_derived_inputs` is added. | Current (old: same file under source_evidence_examination/grading/) | Grader input |
| lit/grading/experimental_activity_evidence/literature_assay_grading.py (line 26) and lit/readers/.../literature_assay_grading_features.py (lines 42, 90) | `ORIGINS`, feature `effect_origin` | The grading sheet records where the effect value came from, including `graph_derived`, and passes it to the parent as a controlled feature. | Current | Grader, and the features code reads from the sheet |
| docs/IMAGE_EVIDENCE.md, docs/LITERATURE_ASSETS.md (lines 78-95, 176-191) | `image.view` and `source.pdf.page` documentation | Describes `image.view` as the tool that binds the PNG to model image input on its next call, and `source.pdf.page` as rendering only. | Docs | Documentation |
| root/a105/.../decision_inputs.py and the old episodes' task.py (e.g. source_evidence_examination/table_evidence_extraction/task.py line 137, passage_evidence_extraction/task.py line 137) | `image.view` handling, `visual_evidence` | The decision step looked up the last completed `image.view` action and put its pixels (`visual_inputs`) into the model's next reasoning input. | Old (97308b94c) | Model-selected tool |
| Old episode files `source_contracts.py` in published_evidence_assessment, evidence_search_strategy_improvement, source_relevance_assessment, source_evidence_examination (and its table, passage and coverage children) | `_ACCESS_TOOLS` and `_READ_TOOLS` | Both tuples name `image.view`, so every old A105 episode that read sources was offered it. | Old | Model-selected tool |
| Old episode folder source_evidence_examination/{tools,scoring,prompts}/: literature_figure_measurements.py, _figure_inputs.py, _figure_storage.py, _figure_prompt.py, _summary_figure_reader.py, _controlled_response_figure_inputs.py, _binding_visual_inputs.py, _gel_inputs.py, _gel_calculations.py, _gel_storage.py, _gel_render.py, _gel_prompt.py, _ratio_source_* | the same code as the library files above | The original owners of the figure, gel and ratio code. | Old | Same roles as above |
| Old root/a105/library/ (names only; shared, not an episode file): literature_figure_inputs.py, _figure_measurements.py, _figure_prompt.py, _figure_storage.py, _summary_figure_reader.py, _controlled_response_figure_inputs.py, _binding_visual_inputs.py, _gel_*.py (calculations, inputs, native_contracts, prompt, render, storage), _ratio_source_inputs.py, _ratio_source_storage.py | figure and plot related names | Named only. `literature_ratio_source_storage.py` requires an `image_view` record made by `image.view` before an image transcription is accepted. | Old | Library |

Nothing in the current A105 episode folders (root/a105/**) mentions `image.view` as an offered tool. Two files only say it is
dropped: the table leaf docstring ("`image.view` and `source.xlsx.*` have no A105 implementation and are not offered") and the
head's decision docstring ("Not carried: ... the visual evidence of `image.view`").

## Docs

- A105_EPISODE_COMMUNICATION.md (line 94): the access catalog "contains ... images, archives, XLSX and PDF operations". No statement on plots or digitizing. Line 228 says the gel cells request "does not grant the full source image or all band measurements".
- LITERATURE_ASSETS.md (lines 78-95): `source.pdf.page` renders a PNG; "no measurement of bands, labels or plotted values implied by rendering"; `image.view` binds the PNG to the next reasoning call; rendering alone does not interpret pixels. Lines 176-191: a regression followed a PDF page through `image.view`; it was not a biological result.
- a105-database-integration.md: only "graph" in the sense of BRENDA's database graph; nothing about figures.
- REMAINING_EXPERIMENTAL_AXES_COMPLETION.md (line 30): mentions "figure/summary evidence" for A106 only; nothing for A105.
- Also IMAGE_EVIDENCE.md describes `image.view` fully, and EVIDENCE_AXIS_LEDGER.md records old live A105 runs that used it (for example 2026-11-06, an A105 episode "successfully render and view PDF physical page 30/Figure S24"; and the 2026-11-05 A106 episode that viewed an original Figure 6 image).

## Which graders can take a figure-derived value

The grader input (literature_assay_grading_inputs.py) has no `figure` or `digitized` kind of operand. Each of the eight
quantities (roles) is one of three kinds only: `received_component` (a cell from a saved reader sheet, named by sheet and
component), `source_number` (a number printed in the text with its unit), or `database_measurement` (effect role only).
A digitized value therefore reaches a grader only as a `received_component` from a sheet whose cell already says it was
digitized. When it does, the input is tagged origin `graph_derived`, which the grading sheet and the features keep.

The registered sheet namespaces (SOURCE_SCHEMAS) include `literature_controlled_response_component_cells`,
`literature_endpoint_signal_cells`, `literature_gel_component_cells`, `literature_binding_cells` and
`literature_binding_interaction_cells`, which can hold figure-derived numbers. The bar sheet from `literature.figure.populate`
(provider `literature.experimental.figure`, namespace `literature_figure_*`) is NOT in that list, so its first, second and
difference ordinates cannot be passed to a grader directly. Whether the endpoint-signal version of the same operation
saves into `literature_endpoint_signal_cells` is read from the route code (literature_population_route.py line 104) but I did not
confirm the full path: not determinable.

By grader (assay type), from the fixed routing table EFFECT_ROUTES and the namespace list:

| Grader | Can take a figure-derived value? |
|---|---|
| ligand_binding | Yes, in principle: binding cells (IC50/Kd read from images by the model, bytes verified) and binding interaction cells are routed to it. |
| protein_signal | Yes: gel band cells (`literature_gel_component_cells`) are routed to it. These are gel image measurements, not plots. |
| activity_rate | Yes, in principle: controlled-response bar cells and optical, partner and kinetic cells are not blocked for it; kinetic summary precision allows an origin `graph_derived`. |
| endpoint_conversion | Not blocked by the route table for endpoint-signal cells; not determinable whether any saved figure sheet is routed to it. |
| product_distribution, reaction_coupling | Only the partition and coupling namespaces are routed to them; no figure namespace is. Not determinable that figure values reach them. |
| transport_response | Channel and ion-discrimination namespaces are routed to it and allow `graph_derived` or "graph extraction" origins; the transport route itself is not figure-specific. |
| protein_amount | Amount and active-site cells only; no figure source found. |

I could not determine, without running the code, which of these paths work end to end today.

## How a figure's values would reach a grader (as designed in the library)

1. The model finds a figure (from the paper's XML, a PMC asset, or an archive member).
2. In the old runner the model called `image.view` and saw the picture. Today the model can only call `source.pdf.page` to
   make a PNG file; it cannot see it. No other current A105 tool puts pixels in front of the model, and the generic runner
   (episode_runtime, method_loop) has no image-input code. How the model would choose ROI coordinates without seeing the
   image is therefore not determinable.
3. The model calls a population operation, for example `literature.figure.populate` or the controlled-response v3 operation,
   giving the source, the ROI, the colour range, the axis calibration and its own statement of what the bars mean.
   Code measures pixels, adds the pixel tolerance as a bound, and saves a sheet of cells in the episode that made it.
4. The model then calls the assay grading population, naming a saved sheet and component as a `received_component`.
   Code reads the cell, notices the digitized origin, tags the input `graph_derived`, and adds the qualification.
5. The grader produces the subscoring sheet. The parent receives only the controlled features and the sheet reference.
   The bound from step 3 stays a digitization range; it is never presented as a confidence interval.

## Tests that exercise it

All under /tmp/ramrepo/gene_annotation_episode/episodic_workflow/episode_support/literature/ and all exercise the library, none exercise an episode:
- forms/experimental_activity_evidence/tests/test_literature_figure_measurements.py (bar reader)
- inputs/experimental_activity_evidence/tests/: test_literature_figure_inputs.py, test_literature_binding_visual_inputs.py, test_literature_controlled_response_figure_inputs.py, test_literature_controlled_response_v3_figure_refusals.py, test_literature_controlled_response_v3_graph_refusals.py, test_literature_controlled_response_v3_population.py, test_literature_controlled_response_v3_stages.py, test_literature_gel_inputs.py; fixture .../tests/fixtures/retained_reference/primary_f420_partner_013/NATIVE_BAR_SELECTIONS_001.json
- storage/experimental_activity_evidence/tests/test_literature_figure_storage.py, test_literature_gel_storage.py
- calculations/experimental_activity_evidence/tests/: test_literature_controlled_response_local_calculations.py, test_literature_controlled_response_owner_calculations.py, test_literature_gel_calculations.py
- grading/experimental_activity_evidence/tests/test_literature_assay_grading_primary.py mentions graph/figure/digit (3 hits); no grading-input test of a `graph_derived` operand was found.
- Episode tests under root/a105/** (tests/ folders, 34 files): none mention image, figure, digitizing or `source.pdf.page`. No test of `source.pdf.page` was found in tools or acquisition tests.

## What is missing from the current A105 episodes

1. `image.view` is not implemented in A105's tool registry and not listed in any A105 episode's tools. The old episodes listed it
   in their access tool tuples and their decision step fed its pixels to the model. The current head and decision code say it is
   "not carried".
2. No image input path exists in the runner or the A105 decision code, so even a restored tool would have nothing to hand the
   picture to the model with.
3. The table leaf (source_evidence_examination/table_evidence_extraction) has `source.pdf.page` but neither `image.view` nor
   `literature_figure_populate`. The head has `source.pdf.page` only. The other six A105 task.py files offer both.
4. The bar-sheet namespace of `literature.figure.populate` is not among the namespaces the assay grading input accepts, and the
   input has no `figure` operand kind, so the model cannot hand a bar ordinate to a grader from that sheet.
5. All of the digitizing operations are flag-gated (`rate_population` and per-operation flags); I did not find which are on in
   the current settings: not determinable.
6. No episode-level test covers any of it.
