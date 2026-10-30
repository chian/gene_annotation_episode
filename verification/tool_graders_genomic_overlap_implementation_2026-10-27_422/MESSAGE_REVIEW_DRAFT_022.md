# Results message draft printed for human review

Additive 2026-10-27. This is a draft, not an approved template or an implemented
renderer. The user was shown the text and example below directly in the
conversation. An asynchronous request for wording/information feedback remains
pending. Other tool implementation and verification continue.

## Confirmed current gap

`providers._SessionConnection._presentation` has no overlap-results recognizer
and reaches its final `json.dumps(presented, allow_nan=False)` fallback.
`ExecutionEpisodes.instructions` supplies generic results text describing
bounded file/page reads, while the overlap catalog has only selected status
and collect operations. Scripted Workflow verification does not exercise a
correct model-facing TASK/STEERING boundary.

## Recurring results TASK, as printed

Obtain the measurements requested by the parent for **{assigned computation or
saved-sheet calculation}**. Keep the assigned inputs, comparisons, resource,
calculation parameters and requested return fixed.

Use the operation information below to choose the next action. Observe status
when execution or output availability is unknown. Collect results when the
available output can answer the request. Collection retains the complete data
and invokes the deterministic parser and calculators; report their recorded
measurements and qualifications.

Preserve useful partial results. Distinguish measured zero, missing input,
incomplete output and incompatible references. Report the specific affected
comparisons and missing requirements. Do not replace unavailable measurements
with zero or judge annotation confidence.

For an assigned saved-sheet calculation, use the supplied sheet and parameters.
Preserve the earlier calculation. Return only the requested fields and any
explicitly requested reusable sheet. Validated completion ends this practical
assignment through the existing controller.

## Separate tool-library information example

| Item | Example |
|---|---|
| Computation | Genomic interval overlap using `bedtools intersect` |
| Assigned comparisons | A–B, A–C, B–C |
| Coordinates | Zero-based, half-open; lengths in base pairs |
| Available operations | Observe original execution status; collect and calculate requested results |
| Requested measurements | Unique intersection, combined union, Jaccard fraction |

The example selects native-result mode. Saved mode must describe retained
sheet status and calculation, never advertise a fresh native status probe.
Actual names, operation meanings and parameters come from the selected job
and the pure 438 information port. This is information under an existing
results episode, not a new task or monitoring judge for each tool.

## Parent STEERING example, as printed

These verified fixture values illustrate a parent request for this subset.
They are not a new gene annotation or a replacement for other requested fields.

| Comparison | Unique intersection, bp | Combined union, bp | Jaccard |
|---|---:|---:|---:|
| A–B | 5 | 15 | 5/15 |
| A–C | 5 | 20 | 5/20 |
| B–C | 2 | 13 | 2/13 |

Qualification: same supplied reference; complete results. The receiving parent
keeps its own task. Missing values retain their actual reason; no default zero,
unrequested full sheet, child history or host tracking belongs in this display.

## Implementation boundary still to define

Before coding, incorporate the user's feedback and define exact model-input
consumers for results iteration, scientific reception and root reception.
Reuse existing decision-frame reconstruction and typed response contracts.
Detailed recurring instructions, selected tool information, terse own-action
yield tables and requested child-return measurements remain separate inputs.
Each mathematical quantity is copied from the selected validated projection;
rendering performs no new interval calculation or scientific judgment.
Saved-sheet operand delivery must remain explicit and usable, without exposing
unrequested private child artifacts. Existing scripted operand construction
does not prove a model can make that selection. No model-presentation
completion is claimed by this draft or the seven Workflow tests.
