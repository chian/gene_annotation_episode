# Selection-policy conflict cleanup087

The assistant-added source-selection-independence prerequisite was removed from
the unfinished v3 schema implementation and its active design/build inputs. It
was not a user instruction. The prior proposal required positive authenticated
source evidence that choosing a reported mean was independent of numerical or
graphical agreement before retaining model eligibility. Unknown evidence could
disable the model. That extra prerequisite is deleted, with no replacement gate.

## Modified files

* `gene_annotation_episode/literature_controlled_response_v3_inputs.py`: removed
  `AuthoritySelectionBasis`, mandatory `Authority.selection_basis`, extracted
  assessments, population/native assessment fields, and the selection-policy
  exclusion/unavailability states. The surviving model states are
  `original_source_model`, `none`, and `unresolved`. Removed the broad docstring
  assertion that the host functions were not experimental analyses.
* `a105_controlled_v3_partial_design_078/build_declarations_007.py`: made the same
  schema deletions and removed the API's selection-basis policy declaration.
  This current constructor remains available; its outputs were captured in memory
  for verification rather than overwriting historical expanded JSON files.
* `a105_controlled_v3_partial_design_078/API_007.json`: removed
  `authority_selection_basis_contract`.
* `a105_controlled_v3_partial_design_078/PROPOSAL_003.md`: deleted the additional
  authority-selection model gate; retained the narrow mathematical scope of its
  particular known-normal statistic. Replaced references to the old003 schema
  generator as authoritative with the current constructors, and described old
  expanded schemas as historical review artifacts.
* `a105_controlled_v3_partial_design_078/TASK_AND_STEERING_004.md`: deleted the
  source-designation independence prerequisite and the blanket phrase forbidding
  new variances. The prohibition on fabricated measurements remains.
* `a105_controlled_v3_partial_design_078/AUTHORITY_SELECTION_AND_ABSENT_ARM_CORRECTION_009.md`:
  deleted the selection-basis policy, model-premise table, corresponding task
  correction, and old verification claims. The file now contains only the valid
  absent-arm/source-kind semantics. Its old filename is retained to avoid losing
  existing references; its content does not impose the removed policy.
* `progress_parent_review_056/CONTROLLED_IMPLEMENTATION_RELEASE_080_081_056.md`:
  removed GOAL-file authority, the old009 task/handoff mandate, the old007 schema
  and009 seals as authoritative build requirements, and all source-selection
  independence requirements. It points to the cleaned current constructor and
  TASK004. Other implementation ownership, scientific scope, and paper-reset
  requirements remain.

The design and release paths above are relative to
`verification/literature_reference_evidence_2026-10-25_001/`.

## Deleted files

Under `a105_controlled_v3_partial_design_078/`:

* `TASK_AND_STEERING_009.md`
* `FINAL_HANDOFF_009.md`
* `construct_generation_007.py`
* `construct_task_009.py`
* `make_verifier_007.py`
* `verify_correction_009.py`
* `verify_design_007.py`

These were policy-bearing task instructions or generators/verifiers that would
recreate or require the removed policy. The current007 schema constructor was
cleaned, not deleted.

## Preserved facts and scientific requirements

The v3 source-read/population path was not implemented when the restriction was
added. This cleanup changes unfinished schemas and drafts; it does not undo
recorded scientific calculations or claim that a completed experiment was
rescored. Genuine source identities, actual source-designated representation,
reconciliation, units, complete supplied covariance validation and model meanings
remain. Selecting a favorable reading and assuming observation independence are
not authorized by deletion of this extra gate.

The nullable absent local-arm/source-kind and raw-origin fixes remain. A selected
but numerically missing reading still retains its actual nonnull arm and source
kind. Unrelated available components are not replaced with dummy whole sheets.

No legacy calculator, original source-input module, runtime, closed run, paper
record, scoring-sheet score, or user-fixed goal was edited by087. In particular,
the existing narrow006/076 known-normal formula checks and existing standard-error,
likelihood-fit and estimated-covariance calculations remain outside these edits.
Ordinary extraction, summary statistics and appropriate model fitting are not
forbidden by the cleaned drafts. This report records cleanup, not a new goal or
governing amendment.

## Historical artifacts

Old expanded schema JSON, constructed examples, verification results, manifests,
hash lists, seals, previous001–006 constructors and historical review receipts
remain as evidence of what was previously generated. Some contain the rejected
policy or earlier model-state vocabulary. They are not current schema authority.
Historical hashes and manifests were not rewritten to pretend they describe the
modified active files. The parent's old056 replay script references removed009
verification inputs and is historical rather than a reusable current build spec.

## Verification

Executed `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. .venv/bin/python
verification/literature_reference_evidence_2026-10-25_001/model_policy_conflict_cleanup_087/verify_cleanup.py`.
All12 recorded checks passed; details are in `VERIFICATION.json`.

* All seven live schemas pass Draft202012 meta-validation and have complete local
  references. None contains the removed selection-basis definitions/fields or
  reading-selection exclusion state.
* The entire original v2 selection schema is exactly preserved after removing
  additive v3 fields/definitions and restoring the v2 version.
* In-memory generation from cleaned `build_declarations_007.py` exactly matches all
  seven live schemas. Its API exactly matches the cleaned API007 file.
* An existing explicitly constructed v3 request with no selection-basis field
  passes the actual selection validator, with no source callback or source IO.
* A local null arm with null source kind and `not_selected` method is valid.
  Fabricated nonnull source kind on an absent arm, a text method on an absent arm,
  and null source kind on a selected arm are rejected. Nullable local-cell origin
  remains available for genuine source absence.
* All seven listed policy-build files are absent.

No paper acquisition, model call, live database operation, workflow, source-read
experiment, statistical fit, or scientific reanalysis was run. The unfinished v3
reader/population functions and future statistical behavior are not validated by
these schema-only checks. Parent root separately reported exact comparison of
the five legacy statistical calculator files against accepted017;087 did not
repeat that independent byte comparison.
