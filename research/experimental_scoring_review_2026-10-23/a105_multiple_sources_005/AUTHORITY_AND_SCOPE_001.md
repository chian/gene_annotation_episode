# Calculation provenance

2026-10-23. No primary paper, paper-specific packet, existing lane report or production implementation was read.

Only the five assigned mathematical proposals were read as research inputs:

| Full input, under the local research directory | Use |
|---|---|
| `a105_contribution_math_003/CONTRIBUTION_PROPOSAL_001.md`, lines 1-630 | Corrected effects, known-normal S/B, joint fit before profiling, duplicate/shared-data handling and source scope |
| `a105_contribution_math_003/ANNOTATION_INTERFACE_ADDENDUM_001.md`, lines 1-49 | Signed B is not directly a nonnegative annotation coordinate |
| `a105_target_relevance_003/TARGET_RELEVANCE_INTERFACE_002.md`, lines 1-254 | Distinction between actual response mapping and uncalibrated correspondence; shared transfer errors |
| `a105_target_relevance_003/UNCALIBRATED_CORRESPONDENCE_CONVENTION_002.md`, lines 1-114 | Component definitions, R arithmetic, missing-family bounds and D=R*B |
| `a105_annotation_coordinate_004/ANNOTATION_COORDINATE_PROPOSAL_001.md`, lines 1-391 | Proposed F handoff, unknown-versus-zero, compound claims and explicit remaining multiple-homolog gap |

The correspondence convention's middle portion was reread separately after
visible output elision, restoring its full functional-site/evolutionary/system
instructions. References to implementation or earlier papers inside these
mathematical documents were not followed. This assignment makes no new source
inspection or implementation-verification claim about those referenced items.

Arithmetic was first explored with a short standard-library Python 3 command,
then checked by `check_multiple_source_arithmetic_001.py`, which successfully
wrote `arithmetic_001.json`. The command name `python` was unavailable; `python3`
was used. Checks cover both formulas, same-source GLS, sign reversal, singleton
preservation, declared duplicate identity, conflicting representation handling,
shared covariance, propagated score sensitivity, missing-component intervals,
partial snippets and density/dilution behavior. They test the stated synthetic
models, not real assay validity or a reader implementation. One draft-table
transcription error found by execution is corrected additively in addendum 002.

No production tests, scientific runs, model calls, empirical fitting, prompt
edits, reader changes, adoption or sheet completion are claimed. All outputs are
new files in the assigned directory.
