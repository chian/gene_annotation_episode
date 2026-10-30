# A105 four-type grading integration

Implemented one selected operation, `literature.assay_grading.populate`, with the four reusable protocol types defined by the shared grading core: activity/rate, endpoint conversion, product distribution, and reaction coupling. Each type supplies the same A105 numerical dimensions; individual numbers, readers, and paper instances are not additional assay scoring sheets.

The operation reads authenticated source numbers or numerical components already owned or received by the acting episode. Native reader rows are retained in the saved input snapshot, including their qualifications. Grading is performed once at the selected operation. The parent receives only the components requested in the original assignment, with the scientific interpretations relevant to those components. A measured-effect-only return contains neither unrelated criterion support nor a prediction model.

The saved operation binds the input records, original artifact identities, normalized extraction, exact native input rows, calculated sheet, original request, and requested component roster. Cold reconstruction checks these committed identities without reopening scientific input bytes or recalculating values. A receiver holding a sheet identifier cannot obtain unreceived numerical components.

The A105 worksheet composer and renderer admit these grading results, plus the existing completion-time and product-partition reader results. Existing rate-reader results feed the grader through the bound received-cell path. Schema alias registration and communication validation require the exact registered top-level grading contract. Generic model-authored report grammar remains unchanged.

## Files

- `gene_annotation_episode/literature_assay_grading_storage.py`
- `gene_annotation_episode/literature_assay_grading_render.py`
- `gene_annotation_episode/literature_episodes.py`
- `gene_annotation_episode/literature_a105_worksheet.py`
- `gene_annotation_episode/literature_a105_worksheet_render.py`
- `gene_annotation_episode/literature_numerical_contracts.py`
- `gene_annotation_episode/communication.py`
- `tests/test_literature_a105_assay_type_binding_322.py`
- `tests/test_literature_numerical_declarations_203.py` (complete all-facts fixture flags)

The core calculations, input adapter, and task prompts were implemented by the other collaborating agents and are dependencies of this integration.

## Verification

The 14 focused integration tests cover all four protocol types through actual `method_loop` parent/child selection, selected grading, exact requested return, parent receipt, saved binding reconstruction, and unchanged own-action credit accounting. They also cover partial scientific inputs, native rate-reader consumption, rejected unreceived components, read-only cold replay with the reader and grader disabled, original-request idempotency, exact-schema mutation rejection, and rendering only delivered context.

Numerical expectations in these tests are explicitly synthetic engineering fixtures. For example, a fixed known-normal comparison produces conditional log evidence 7.5; it does not establish a scientific claim or a posterior probability. No observation or annotation assessment is fabricated by grading or delivery. Primary-paper demonstrations are reported separately by the other agents.

The initial focused suite passed 12 tests. After adding the schema and renderer checks, a stable combined run passed 128 tests (including all 14 focused tests and the existing worksheet suites) before exposing an outdated all-facts regression fixture. That fixture omitted the new grading flag and two previously registered optional families; its flag list was corrected without changing production behavior.

After the fixture correction, the remaining regression command passed **254 tests in 70.71 seconds**:

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q tests/test_literature_numerical_declarations_203.py tests/test_communication.py tests/test_literature_rate_episode_integration.py -x --tb=short
```

The earlier stable combined command was:

```text
/tmp/gene-annotation-literature-py314-20261029/bin/python -m pytest -q tests/test_literature_a105_assay_type_binding_322.py tests/test_literature_a105_worksheet.py tests/test_literature_a105_worksheet_integration_271.py tests/test_literature_numerical_declarations_203.py tests/test_communication.py tests/test_literature_rate_episode_integration.py -x --tb=short
```

The root agent subsequently ran the final combined grading/core/input/prompt/primary-example suite after its last synthetic-origin input fix: **101 passed in 18.20 seconds**. Its result is separate from the regression counts above; the focused integration tests overlap those 101 and should not be counted twice.

No goal files, amendments, controller scheduling rules, or final annotation-credit formulas were changed by this integration.
