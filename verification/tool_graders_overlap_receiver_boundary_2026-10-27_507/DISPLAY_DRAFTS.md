# Proposed displays for user feedback

These are unsatisfied review proposals, not implemented prompts. The receiving
parent keeps its own full TASK, including its gene question, scope, constraints
and substantive problem-solving guidance. Only the following requested facts
are added to STEERING. Its existing own action-category yield/expectation/
uncertainty table stays separate and is never borrowed from a child.

Numerical examples reuse 437 check003's retained actual calculations on
explicitly synthetic interval inputs. A narrower field selection described
below is a proposed display scenario, not a claim that this narrower template
was run. No numbers were recalculated in this packet.

## Parent display A: requested shared-union and Jaccard only

Request for this illustration: `unfiltered.intersection_union_bp` and
`unfiltered.jaccard_bp` for AB, AC and BC. The existing ratio carries its own
numerator and denominator. No native pair count or summed pair width is added.

> Overlap of the supplied interval sets. Coordinates are zero-based, half-open;
> geometry uses unstranded outer spans. All three comparisons are complete.
>
> | Comparison | Intersection of the two input-set unions, bp | Jaccard: intersection / union across both input sets |
> | --- | ---: | ---: |
> | A–B | 5 | 5/15 = 0.3333333333333333 |
> | A–C | 5 | 5/20 = 0.25 |
> | B–C | 2 | 2/13 = 0.15384615384615385 |
>
> Reference: the same supplied versioned identity, `synthetic-overlap437.1`,
> for all three input sets; chr1 length supplied as 100 bp. No independent
> reference validation is recorded.

Decision supported: the parent can compare genomic coverage and judge whether
it answers its assigned question, without mistaking duplicated interval pairs
for unique genomic bases. A reference identity is scientific qualification,
not the saved-sheet input-selection handle.

If the parent explicitly asks for the additional AB quantities, their meanings
can be rendered as separate rows, never under a common “all returned pairs”
denominator heading:

| Requested quantity and population | Retained value |
| --- | ---: |
| Overlapping A–B occurrence pairs | 2 |
| Sum of overlap widths over those occurrence pairs | 8 bp |
| Intersection of A's genomic union and B's genomic union | 5 bp |
| Genomic union across every region in input sets A and B | 15 bp |

The sum can count a shared base once per occurrence pair. Genomic unions count
covered bases once. This explanation changes no value or denominator.

## Parent display B: selected-pair result after a saved calculation

Request for this illustration: selected.selected_pair_count and
selected.selected_pairwise_bp_sum for AB, AC and BC. The compared earlier
minimum1 values must already have been admitted if displayed alongside these.
Otherwise show the newly returned minimum4 table alone.

> Calculation from the explicitly received overlap sheet. Selected pairs must
> overlap by at least 4 bp, cover at least 0/1 of the A occurrence span and at
> least 0/1 of the B occurrence span. All three comparisons are complete.
>
> | Comparison | Selected occurrence pairs | Sum of selected pair widths, bp |
> | --- | ---: | ---: |
> | A–B | 1 | 5 |
> | A–C | 1 | 5 |
> | B–C | 0 | 0 |
>
> Reference: same supplied versioned identity, `synthetic-overlap437.1`.

Decision supported: the parent can judge the effect of its own selected
threshold. The 0 for B–C is an exact empty selected-pair population, not missing
native data. If unfiltered Jaccard was also requested, show its unchanged value
in a separately labeled unfiltered column. Do not derive it from this table or
call a selected shared-union fraction “selected Jaccard.”

An explicitly received saved sheet may be described as available for another
selected calculation. Its exact descriptor and historical handoff remain
internal. A model-selectable semantic sheet label is not claimed operational
until root's shared input-choice adapter binds it to those fields. A
projection-only parent must not receive that availability statement.

## Parent display C: a useful valid pair beside an unavailable comparison

Retained 437 missing-AC-stdout case. Requested subset for this proposed display:
unfiltered.jaccard_bp and relevant failures. No fresh native observation occurred
here.

> | Comparison | Jaccard | Result extent |
> | --- | --- | --- |
> | A–B | 5/15 = 0.3333333333333333 | Complete |
> | A–C | Unavailable: original overlap output unavailable | Unavailable |
> | B–C | 2/13 = 0.15384615384615385 | Complete |
>
> A–C requires its original retained overlap output. Its numerator and
> denominator are unknown. A–B and B–C retain their complete measurements.
> Reference: same supplied versioned identity, `synthetic-overlap437.1`.

Decision supported: the parent can use the valid information and decide whether
to repair/reacquire the affected original result, pursue another investigation,
or continue with the qualified evidence. The renderer selects no repair and
does not turn the missing result into zero overlap. If only AB had been
requested, no AC/BC row or C-specific failure would be included.

## Results child's recurring TASK draft

This refines 422/022 only for review. It belongs to an existing results episode;
it is not the scientific receiving parent's TASK.

> Obtain the overlap measurements requested by the parent for the assigned
> interval sets and comparisons. Keep the selected input sets, resource,
> calculation parameters, requested fields, occurrence selection and page fixed.
> Use the supplied operation information and actual preceding outcomes to
> choose the next available status or collection action.
>
> For original results, collect the selected execution's complete retained
> outputs and use the recorded parser and calculator results. For a saved
> calculation, use only the explicitly received sheet with the assigned
> parameters. Status in that mode concerns the retained assignment and does not
> observe or repeat the original bedtools work.
>
> Interpret coordinates as zero-based, half-open outer spans. Strand and BED
> block fields do not change this unstranded mode. Distinguish occurrence-pair
> counts and summed pair widths from genomic-union lengths. Preserve each
> requested ratio's recorded numerator, denominator and missing reason, the
> selected threshold population, and the supplied reference qualification.
>
> Preserve valid partial results and return the recorded facts in the parent's
> requested typed form. Distinguish measured zero, an undefined zero-denominator
> ratio, incomplete input, unavailable output and incompatible reference
> declarations. Report only relevant located failures. Reusable sheet delivery
> requires the parent's explicit saved-sheet return field. The existing
> controller governs continuation and validated practical completion.

The complete recurring TASK also renders the actual assigned sets/comparisons,
reference declarations, threshold values, requested measurements/page and their
meanings, actual selected tool instructions and callable operation meanings.
This text is not a substitute for those inputs. Their exact field-to-text trace
is in CONTRACT_DRAFT.md. Own prior outcomes and yield tables remain STEERING.

## Feedback incorporated in this draft

Root correctly identified that a heading “All returned pairs” could attach the
15 bp combined-union denominator to the wrong population. The displayed
quantities now name their own populations. This is a correction to the draft
sent during source inspection, not user acceptance of this template. User
feedback and implementation remain outstanding.
