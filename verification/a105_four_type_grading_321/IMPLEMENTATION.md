# Four reusable biochemical grading paths into A105

Implemented on 2026-10-29 under the user's existing goal and latest steering.

The hierarchy is **A105 experimental evidence subscore → subscoring grader → subscoring reader**. The four biochemical protocol types use the SAME A105 numerical fields. Different source papers, chemicals, reader layouts and arithmetic components do not create additional assay types or subscoring sheets.

| Assay type | Specific considerations governing its use |
|---|---|
| Enzyme activity/rate comparisons | Time and concentration regime, actual amount normalization, and kinetic-model applicability when a fitted kinetic quantity is claimed. |
| Reaction progress/endpoint conversion | Endpoint and time alignment, conversion denominator where relevant, and product identity when product formation is claimed. Disappearance and completion time retain their narrower meanings. |
| Product distribution/equilibrium | Species identity, response factors, common denominator/species coverage, and evidence of equilibrium when equilibrium is claimed. |
| Reaction coupling/stoichiometric balance | Product identity, reaction coefficients, matched measurement windows/preparations, and reporter specificity. |

All four also consider measurement identity, calibration/sensitivity, matrix interference, spontaneous or competing chemistry, attribution, functional relevance, biological/chemical conditions, sampling and uncertainty. Interpretation statuses describe source-supported applicability; they are not converted into numerical checklist weights.

## Numerical output and combination

The shared `grade_assay` implementation selects the applicable type criteria and produces the following numerical cells. Existing readers/calculators supply the native estimate and any corrections already included in it.

| Cell | Calculation and meaning |
|---|---|
| `measured_effect` | The selected native estimate, retaining its units and provenance. |
| `effect_variance` | Supplied variance for that exact estimate and squared unit scale; its correspondence must be established. |
| `effect_precision` | `1 / effect_variance`; scale-dependent precision, not a probability. |
| `recovery_deviation` | `recovery - 1`; measured calibration diagnostic. |
| `attributed_fraction` | `attributed_signal / total_signal`, with a supported common endpoint and denominator. |
| `condition_response` | `condition_test / condition_reference`, for nuisance conditions outside the intended experimental change. |
| `assertion_prediction_error` | `effect - assertion_prediction`, subject to scientific applicability. |
| `alternative_prediction_error` | `effect - alternative_prediction`, with the same quantity and conditions. |
| `source_log_evidence_ratio` | `[(effect-alternative)^2 - (effect-assertion)^2] / (2*variance)`, conditional on two explicit fixed predictions and the supported known-variance normal model. |

These cells are components of the shared assessment, not separate scoring sheets. The diagnostics are not multiplied into an already corrected effect a second time. The signed likelihood comparison can favor or contradict the asserted function. It is not a calibrated probability of function or final annotation credit. No combination of A101 with A105 or aggregation across axes is implemented here.

The original **synthetic** numerical example is reproduced: effect `0.68`, variance `0.11124225`, fixed predictions `1` versus `0` give precision approximately `8.98939027` and log evidence approximately `1.618090249`. Synthetic tests exercise all four types, negative evidence, applicability failures, source dependencies, and missing/estimated variance.

## Implementation and selected execution

- `gene_annotation_episode/literature_assay_grading.py`: four type definitions, interpretation questions, numerical schemas and deterministic grading.
- `gene_annotation_episode/literature_assay_grading_inputs.py`: shared adapter for possessed existing reader components and authenticated adjacent number/unit spans. Shared table headers use the existing typed readers. It retains source uncertainty, physical dependencies, censoring/nondetection and synthetic origins.
- `gene_annotation_episode/literature_assay_grading_prompt.py`: full recurring scientific TASK for selected grading.
- `gene_annotation_episode/literature_assay_grading_storage.py`: selected execution, persisted inputs/results, exact requested numerical returns and reconstruction without rerunning science.
- `gene_annotation_episode/literature_assay_grading_render.py`: presentation of delivered numerical components and their scientific qualifications.

The existing `LiteratureEpisodes` binding exposes `literature.assay_grading.populate` when configured with `rate_population=True, assay_grading_population=True`. Existing readers retain their own capability flags and actual format limitations. The parent requests components through `requested_assay_grading_components`; `literature_assay_grading_cells` is registered in the numerical return contract and A105 worksheet. Reader selection is based on the reusable assay protocol and required measurements, followed by the actual source representation capability.

The A105 composer also now admits existing completion-time and product-partition returns. Rates can reach A105 through their grader's `measured_effect` and assessment components. No separate raw-rate composer section was added.

## Verification and limits

Final focused command:

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q \
  tests/test_literature_assay_grading.py \
  tests/test_literature_assay_grading_inputs.py \
  tests/test_literature_assay_grading_primary.py \
  tests/test_literature_assay_selection_guidance_320.py \
  tests/test_literature_a105_assay_type_binding_322.py
```

Result: **101 passed in 18.20 seconds**. This includes all four types through actual parent/child `method_loop` execution using controlled episode choices, exact typed return, parent receipt, binding reconstruction, and cold replay with readers/calculators disabled. It also covers actual existing-reader consumption, narrowed numerical scope, mutated contract rejection, source-unit borrowing, original-source nondetection, and selected uncertainty/dependency preservation.

A separate regression command covering `test_literature_numerical_declarations_203.py`, `test_communication.py` and `test_literature_rate_episode_integration.py` passed **254 tests in 70.71 seconds**. The declaration test's exhaustive capability fixture was updated to enable the new grading capability and two pre-existing optional capabilities that it had omitted. Existing worksheet suites also passed during the integration run. Exact integration commands and coverage are recorded in [the binding report](../a105_grader_binding_322/REPORT.md).

Four retained-paper demonstrations and their actual numbers are documented in [PRIMARY_EXAMPLES.md](PRIMARY_EXAMPLES.md). They exercise actual readers/calculators and the grader core. The selected original evidence does not supply a complete justified variance/prediction model, so those overall likelihood cells remain unavailable with specific reasons. Their native measurements remain populated. These are partial scientific assessments, not completed primary-source overall grades.

The implemented overall score currently supports the explicit fixed-prediction known-variance normal model. Estimated variance, censoring, unresolved applicability and other likelihood models do not acquire an invented overall score. The existing narrow workbook adapters remain narrow. Autonomous model-based interpretation was not run in this task; the selected execution tests use controlled decisions. This work does not declare all of A105 or the larger literature goal complete.

An earlier separate historical gel-prompt baseline assertion expects obsolete saved-return wording (`x-source` rather than the existing `episode-fact:` instruction). It failed on unchanged `SAVED_NUMERICAL_RETURN_TASK`; it was not rewritten to hide that mismatch. The focused implementation suite above passes. The selection audit records that separate failure in `verification/assay_selection_instructions_320/REPORT.md`.
