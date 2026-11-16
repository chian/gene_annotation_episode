# crt: test coverage for the live (v3) controlled-response code (16 November 2026)

Area: new test files under `gene_annotation_episode/episodic_workflow/root/a105/tests/` only. No product code was
edited, no existing test was changed, nothing was committed. Slot `crt`, runs `runs/claude_crt_001`-`038`.
Scratch: `<scratchpad>/crt/` (`t.sh` recorder run, `g.sh` gate run, `py.sh`, `sites.py` site measurement, `probe.py`).

## Tests added (205 tests in 5 files, all pass; none xfail)

All of them build on the existing v3 `Fixture` / `CONSTRUCTED_SOURCE_SELECTIONS.json`, the stage helpers in
`test_literature_controlled_response_v3_stages.py` and the owner-input builders in
`test_literature_controlled_response_owner_calculations.py`. Each test edits the input or saved record in the test
itself. Nothing was captured from a run. Every successful live read in these files is also revalidated through
`validate_controlled_response_v3_extraction`.

| file | tests | what it covers |
|---|---|---|
| `test_literature_controlled_response_v3_graph_refusals.py` | 46 | 37 single-field tampers of a saved graph reading, each asserting its exact code (`_validate_graph`, `_saved_images`, `_check_witness`); an image-transcribed tick (`saved_image_identity_mismatch`, `saved_image_geometry_mismatch`, `saved_image_authentication_mismatch`); a scale phrase that does not match the axis kind; pixel bounds outside the image; a bar that cannot be read; a conflicting axis scale (live `conflicting` and saved); a graph arm whose `graph_details` disagrees with its measurement; positive cases: ordinate and slope computed by hand from the pixel rows, a canonical display that overflows while the native operand stays (4.05e305 mmol/min), and an ordinate beyond double range that becomes `unsupported` |
| `test_literature_controlled_response_v3_covariance.py` | 46 | strict JSON (all 11 `_JSON.parse` sites plus 2 in `load`); document shape, origin, version and fields; asymmetric and non-PSD matrices; every `_project_owner_covariance` refusal (conflicting binding, two owners on one row, unregistered unit, dimension conflict, rows of different dimension, unequal shared rows, unresolved, 1e400 range, exact rank-one matrix that is not PSD after rounding to doubles, dimension conflict of an unbound reading); a rounding diagnostic disabling the normal model; every `_effective_model` gate; index out of bounds, label token mismatch, owner witness not in role; positive: one owner bound to two proportional rows in nmol/min and umol/min, projected once, with the effect 0.002 and the variance 3e-7 computed by hand |
| `test_literature_controlled_response_v3_saved_tamper.py` | 65 | 43 single-field tampers of a valid saved extraction (schema, selection, roster, witnesses, scope documents, meanings, interpretations, text measurement, number, unit, uncertainty, operand, covariance raw text and document, final projection); companion roster; an unnominated arm; an unselected measurement; an absent unit; 9 tampers of a saved CI (interval, confidence, count, magnitude); uncertainty pieces that were not nominated; a source-defined unit (2 U/mg = 0.004 umol/min/mg by hand) and its scale tamper; an unavailable defined unit (`saved_unavailable_definition_mismatch`); a non-UTF-8 covariance document state; witness-to-nomination order; an unsupported complete expression saved as `parsed` |
| `test_literature_controlled_response_v3_reading_refusals.py` | 22 | artifact alias conflict; closed or unselected context reads; an image witness whose image is unavailable; staged-call misuse (endpoint read in another context, the reader for the wrong measurement kind, scope reading roster and order, an unnominated arm, a document without a nomination, finish roster); the saved context (`unselected_source_read`, `saved_witness_missing`, nomination mismatch, closed); four live-and-saved uncertainty unit conflicts; CI bounds that collapse in double precision; a display overflow at 1e306 mmol/min; the source-reader result contract; an SD statistic with an interval |
| `test_literature_controlled_response_v3_owner_refusals.py` | 26 | 14 parsed owner-input contract failures (`unsupported_value`, `nonempty_identity_required`, `boolean_required`, `meaning_identity_mismatch`, `unsupported_input_version`, `covariance_order_mismatch`, bound/missing contracts); shared-measurement context; alias `conflicting_source_literal`; pair unit dimension; different condition correspondence; `unknown_control_reuse` and `estimated_covariance` (effect 0.006 and variance 1.7e-6 by hand); raw and bound `numeric_range_failure`; `uninformative_bounds`; `canceled_unit_unknown`; a one-sided effect with `unresolved_censoring_model`; all `_reading_dependencies` qualifications |

## Coverage: sites reached before and after

Measured with the cr2 method: the same site definition and the same `sys.monitoring` line recorder plugin. "Before"
is the cr2 recorder runs `claude_cr2_035`-`048` (the 14 existing files; the family library is unchanged since then).
"After" adds the recorder runs of the final contents of the 5 new files: `claude_crt_006`, `013`, `014`, `016`, `017`.
The final computation ran through the launcher as `claude_crt_038`.

| theme | functions | lines before → after | sites before → after |
|---|---|---|---|
| graph reading and saved graph checks | 36 | 536 → 598 / 685 | 22 → 70 / 111 |
| covariance source and projection | 12 | 268 → 313 / 317 | 11 → **52 / 52** |
| saved-record checks (tampering) | 15 | 313 → 397 / 400 | 8 → 68 / 69 |
| other family functions | 192 | 2220 → 2338 / 2588 | 96 → 155 / 270 |
| **overall** | 255 | 3337 → 3646 / 3990 | **137 → 345 / 502** |

- Codes in column `of_those_named_in_deleted_tests`: **47 of 48 sites reached**. The one left is unreachable (below).
- Priority-2 functions: `_validate_graph` 1 → 36/37; `_project_owner_covariance` 2 → 11/11; `_JSON.parse` 1 → 11/11;
  `_saved_uncertainty` 0 → 13/13; `_saved_roster` 5/5, `_saved_images` 4/4, `_validate_text` 5/5, `_saved_unit` 8/8,
  `_saved_witness` 6/6, `_saved_number` 6/6, `_SavedV3SourceContext.*` all sites;
  `validate_controlled_response_saved_science` 11/12.
- Not targeted: the remaining 41 graph-theme sites are in `figure_inputs` (`_validate` of the figure request,
  `_strict_decode`, `_count_recipe`, `_literal`, `_pixels`). They are reachable through v3 selections and remain
  open work. The `storage` repository sites in "other" were also not targeted.

## Unreachable sites (not tested)

1. `v3_inputs._read_graph:143` `unselected_source_read` (one of the named codes). `cached()` only receives references
   from the figure request built from the same arguments, and the context prefetched their whole closure (every
   image and text witness reference), so no live input can reach it. It is a defensive check.
2. `v3_inputs._validate_graph:385` `saved_graph_projection_mismatch`. A `point` projection already requires
   `expected_status == graph_digitized`, which in turn requires measured pixels and a matching `reading_status`
   (lines 374/376). So this branch can never be true.
3. `inputs._uncertainty:476` `saved_selection_mismatch`. The saved path sets `context.saved_uncertainty` from the
   same nomination immediately before the call (`inputs.py:1767`).
4. `inputs.validate_controlled_response_saved_science:1720` `saved_dependency_contract_mismatch`. The extraction
   schema fixes both `implementation_dependencies` fields as `const`, so a tampered value fails earlier as
   `saved_extraction_schema_invalid` (tested).

## Defects found

None. Every invalid input or tampered record tried was refused with its specific code, and every valid live input
was accepted and round-tripped. One suspected defect was probed (`probe.py`, run `037`) and is **not** a defect: a
saved graph image record whose width, format or Pillow version disagrees with the outer image record, even with
`image_size` changed to match, is refused, by `saved_graph_identity_mismatch`. One observation for the owner:
`_validate_graph`'s `images=` keyword is unused (it checks `result['images']`); the identity hash is what binds the
graph image record.

## Gate (exact isolated form from BRIEF.md, one file per launcher run, `claude_crt_018`-`036`)

| file | result | earlier (cr2 recorder runs) |
|---|---|---|
| v3_graph_refusals (new) | 46 passed, 3.35 s | — |
| v3_covariance (new) | 46 passed, 20.76 s | — |
| v3_saved_tamper (new) | 65 passed, 15.12 s | — |
| v3_reading_refusals (new) | 22 passed, 6.29 s | — |
| v3_owner_refusals (new) | 26 passed, 0.11 s | — |
| owner_calculations | 49 passed | 49 passed |
| v3_inputs | 22 passed | 22 passed |
| v3_stages | 37 passed | 37 passed |
| saved_local_witnesses | 17 passed | 17 passed |
| local_calculations | 18 passed | 18 passed |
| v3_population | 8 passed | 8 passed |
| figure_inputs | 35 passed | 35 passed |
| communication | 6 passed | 6 passed |
| render_v3 | 3 passed | 3 passed |
| runtime_custody_v3 | 5 passed | 5 passed |
| uncertainty_units_v3 | 2 passed | 2 passed |
| unavailable_joint_storage_v3 | 6 passed | 6 passed |
| scope_context_storage_v3 | 7 passed | 7 passed |
| storage_v3 | 13 passed | 13 passed |

The existing files are unchanged in result: 228 passed. Gate wall time was 307 s (expected about 305 s).

## Deviation

While writing the tests I ran the site-count script (`sites.py`: AST and JSON only, no project import) and three
one-off file-edit helpers with the host `python3`, outside the launcher. All test runs, probes and the final
measurement (`038`) went through the launcher.

## Addendum (16 November 2026): the rest of the graph theme in `figure_inputs`

Asked by the coordinator after my first five files were committed. Same rules, plus one new one: every Python command
goes through the launcher, including AST/JSON-only scripts. All runs in this addendum did so (`claude_crt_040`-`064`).

### New file: `test_literature_controlled_response_v3_figure_refusals.py`

41 tests pass and 1 is a strict xfail. They drive `read_controlled_response_rate_figure` with the figure-reader test
fixture: constructed pixels and labels, request version `controlled_response_rate_figure_selection_v1`. This is the
live reader that every v3 graph nomination goes through.

- **Request refusals, before any source read (19 tests).** Each asserts its code and that the reader was never called:
  - `unsupported_value`
  - the five `_count_recipe` codes
  - `list_required` ×3, `invalid_source_reference` ×2, `unmapped_original_source_mismatch`
  - `nonnegative_tolerance_required`, `nonnegative_pixel_required`, `unreadable_has_no_candidate`
  - `text_scale_witness_required`, `image_scale_witness_required`, `unresolved_scale_contract_required`
  - `undeclared_image_id`
- **Source reader not callable:** `source_reader_required`.
- **Images that cannot be decoded (7 tests):** GIF, palette mode, two frames, trailing bytes, EXIF rotation, bytes that
  are not an image, a corrupt chunk. Each is retained as the image's error code and gives an `unsupported` reading
  with no ordinate.
- **Ticks:** a word tick, an "about 9" context and a 1e309 text tick are each unsupported; an image-transcribed 1e309
  tick stays exact and makes the ordinate `unsupported`; a tick with more digits than a double holds stays exact with
  `graph_tick_projection_rounded`.
- **Logarithmic axis:** read, but `graph_scale_unsupported`.
- **Power-of-ten multiplier on the unit (text and image):** `graph_axis_multiplier_unsupported`.
- **Pixels:** a transparent pixel in the region of interest (`graph_nonopaque_roi`); terminal-edge and opposite-edge
  clipping; a degenerate axis.
- **Hand-computed ordinates:** -39/20 (= -1.95) for the base fixture, and -59/15 with
  `graph_ordinate_projection_rounded` when the second tick sits at pixel 50.

### Coverage (cr2 method; after = the earlier five runs plus `claude_crt_042`; computed in run `043`)

| theme | sites before → after the first five files → now |
|---|---|
| graph reading and saved graph checks | 22 → 70 → **106 / 111** |
| covariance source and projection | 11 → 52 → 52 / 52 |
| saved-record checks | 8 → 68 → 68 / 69 |
| **overall** | **137 → 345 → 381 / 502** |

Per function, `figure_inputs` now reaches:

| function | sites |
|---|---|
| `_validate` | 19/19 |
| `_count_recipe` | 6/6 |
| `_pixels` | 7/7 |
| `_strict_decode` | 6/7 |
| `_literal` | 2/4 |
| `_scale` | 3/3 |
| `_graph_unit` | 3/3 |
| `_Context.__init__` | 4/4 |
| `read_controlled_response_rate_figure` | 5/5 |

### Graph-theme sites not reached

1. `_strict_decode:146` `image_decode_failed`. The bytes are re-opened and compared with what the first open of the
   same immutable bytes reported (size, mode, format, frame count). I could not construct any bytes that disagree,
   so I believe it is unreachable.
2. `_literal:388` `graph_tick_literal_unsupported` and `_literal:396` `graph_tick_literal_numeric_range`. Run `044`
   tried 11 tick contexts ("~9", "≈9", "< 9", "<9", "about 9", "approx. 9", ">= 9", "9e308",
   "1.7976931348623159e308", "9?", "ca. 9"). In every case the shared number reader (role `condition`) either raised
   its own refusal first, which the except branch turns into the same code, or returned an exact point. So I believe
   these two lines are unreachable. The codes themselves are still emitted, by the except branch, and are tested.
3. `v3_inputs._validate_graph:385`, unreachable, as listed above.

### Defect found (strict xfail)

- **"ca. 9" is read as the exact tick 9.** "about 9", "approx. 9" and "~9" are refused as approximate
  (`graph_tick_literal_unsupported`). Test: `test_circa_tick_is_approximate_like_about`, `xfail(strict=True)`. Run
  `044` showed the shared number reader returns an exact point for "ca. 9", so the fix belongs in
  `literature_rate_native_inputs._number`, not in this family. Not fixed.
- "9?" is also read as an exact tick 9. I left it unrecorded because the question mark's meaning is ambiguous.

### Gate (runs `claude_crt_045`-`064`, exact isolated form, one file per run)

- New figure file: 41 passed, 1 xfailed.
- The other five new files: 46 + 46 + 65 + 22 + 26 = 205 passed.
- The 14 existing family files: 228 passed, unchanged per file.
- All 20 runs exited 0.
