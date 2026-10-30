# Withdrawal of historical category-score proposals

This is an additive correction requested by the user's instruction to fix the
audited violations. It governs the scoring status of the historical proposals
listed below. Their original bytes, source measurements and records remain
preserved. The rejected scoring proposals are **withdrawn**, not accepted rules
and not proposals still awaiting acceptance. This correction supplies no
replacement formula. There are **zero completed scoring sheets out of ten**.

The user's controlling direction is preserved in AGENTS.md and the
[evidence-axis instructions](../../docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md):

> These individual scores need to be multipliers or sum in some way.

> THE PAPERS DO NOT OVERRIDE THE TEMPLATE. THEY GET CONVERTED THOUGHTFULLY

The required work is to identify individual measurable inputs, explain what
each evaluates, define meaningful transformations, and show explicit sums or
products. Placing measurements beside an overall category grade does not do
that work. Experimental comparability concerns conditions other than the
deliberately changed variable. Isolation of the measured effect is a separate
question, including contributions from mixed subjects. Both must remain
visible when designing component calculations.

## Exact withdrawal scope

| Historical location | Withdrawn scoring proposal |
| --- | --- |
| [numeric_rubric_proposal.md](numeric_rubric_proposal.md), preserved original, numerical sheet and anchor sections | Broad `R`, `V`, `A` grades `0/0.25/0.5/1`; `T` grades `0/0.25/0.5/0.75/1`; their worked assignments, grade changes, products and proposed handoff. The existing leading correction already rejects these. |
| [numeric_compilation_proposal.md](numeric_compilation_proposal.md), preserved original | The qualitative `H` fallback `0/0.25/0.50/0.75`, its worked uses, and compilation or sensitivity examples whose operands are rejected overall grades. The historical numerical `H` branch is not a categorical fallback; this withdrawal does not adopt that branch or its policy parameters. |
| [SYNTHESIS.md](SYNTHESIS.md), “Numerical proposals examined” and “Compilation tests and remaining work” | The ordinal relation/validity pair, the reported example grades, and `E=min(relation,validity)` as a candidate scoring sheet. Language presenting these as current review candidates is superseded. |
| [molecular_measurement/summary.md](molecular_measurement/summary.md), proposed sheet, worked contrasts and explicit compilation candidate | `D=0/1/2` as a score, all worked `D` assignments, and downstream selectors or compilation that treat that classification as a numerical scoring component. |
| [molecular_measurement/case_reviews.jsonl](molecular_measurement/case_reviews.jsonl), all 61 rows | Every `D_endpoint_relation` proposal, plus three additional candidate entries that assign `D` in rows 33, 35 and 61. This is 64 category-bearing candidate entries in 61 rows. |
| [perturbation_and_attribution/summary.md](perturbation_and_attribution/summary.md), candidate sheet and worked contrasts | `L/V/T=0–3`, `E=min(L,V)`, the optional `min(E,T)` cap, and their worked numerical grades. Named-weakness status codes are labels, not numerical scoring components. |
| [perturbation_and_attribution/case_reviews.jsonl](perturbation_and_attribution/case_reviews.jsonl), all 32 rows | The `L` and combined `V/E/T` candidate entries in every row: 64 category-bearing entries. Each row's separate magnitude/precision candidate also contains named-weakness codes; those codes must remain status labels rather than scores. The same candidate's measured ratios and precision arithmetic are not withdrawn. |
| [system_and_transfer/summary.md](system_and_transfer/summary.md), claim-specific resolution row | The proposed `0–3` claim-resolution grade as a numerical component. |
| [system_and_transfer/case_reviews.jsonl](system_and_transfer/case_reviews.jsonl), rows 4, 8 and 39 | The claim-relatedness, inferential-resolution and replacement-mechanism `0–3` grades: three category-bearing entries. Measured ratios and counts in other entries are not rejected by association. |
| RESEARCH_SCOPE.md, preserved original, synthesis/completion section and R04 status | Statements treating the `T` ladder or ordinal examples as current proposals are superseded. R04 and R05 remain unfinished; corpus coverage and paper counts are not completed scoring sheets. The existing leading correction already states this. |

The companion [source inventory](category_score_source_inventory_2026-10-23_001.json)
identifies every category-bearing JSON candidate by original file, line and
JSON pointer, and separately identifies the mixed weakness-status fields. It
records hashes of the listed historical files, including hashes of preserved
original sections where correction notices already exist. The inventory covers
131 category-bearing candidate entries in 96 distinct original rows, plus 32
mixed candidate fields whose weakness codes have only categorical meanings.
These counts locate withdrawn text; they are not scientific or scoring credit.

## Measurements and arithmetic remain usable research material

This correction does not prohibit actual numerical signal/uncertainty
calculations, calibration recovery, blank corrections, raw ratios, counts,
sums or products. It also does not accept any particular formula merely
because it uses numbers. Each component still needs defined inputs, experimental
meaning, transformation, uncertainty and combination role. A missing input
remains unknown; it is not replaced by a middle category grade.

Source facts, limitations, factual direction labels and source corrections are
preserved. A categorical label such as an observed outcome direction can be
useful information without becoming a score. Preserve the distinction between
measurement and label when reusing a historical row. Do not reuse a withdrawn
grade as an input to a new formula or describe it as still under consideration.

A105 concerns molecular activity. YeaG recovery/growth/deletion and related
perturbation/restoration scoring remain A106 work; these historical examples do
not complete A105. Apply [SOURCE_CORRECTIONS.md](SOURCE_CORRECTIONS.md) when
using retained source facts, including its endpoint distinctions.

## Reader prototype correction and limits

The files under
[verification/a105_three_parts_review_2026-10-23_001](../../verification/a105_three_parts_review_2026-10-23_001/)
originally supplied an evidence-record example. Its `review_notes.md`,
`sheet_schema.json` and `scoring_sheet_example.json` are preserved historical
artifacts, not a completed numerical scoring sheet. The prototype's names and
`unadopted_review` marker do not make its recordkeeping fields the user's part 2,
and its reader is not completed part 3. The targeted readers for the requested
scoring sheet still depend on defining that sheet.

The repaired `populate_sheet.py` now sets `assayed_subject_is_target` only when
the two complete, nonempty subject-reference sets are equal. Its prior
intersection test incorrectly reported exact identity for a partial overlap,
including an assay containing the target alongside another subject. A false
value now means that exact reference-set identity was not established; it does
not prove that different references represent biologically different things.
Recorded correspondence assessments remain separate. No transfer score is
inferred, and the existing native blank-corrected rate calculation is unchanged.

Five focused prototype tests pass using:

```sh
.venv/bin/python -m unittest discover -s verification/a105_three_parts_review_2026-10-23_001 -p test_populate_sheet.py -v
```

The new regression covers exact single/multiple-subject matches, order changes,
partial overlap, subsets, supersets, disjoint sets and the empty-set boundary
through both synthetic input adapters. Existing checks cover schema compatibility,
source anchors, native arithmetic, unknown uncertainty, censored values and
duplicate-view handling. This verifies the prototype repair only. No paper was
newly read, no scientific investigation ran, and no production scorer or credit
path was implemented in this correction.
