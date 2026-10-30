# Additive arithmetic clarifications

This accompanies the initial A111 sheet before handoff. It corrects possible ambiguity without overwriting the earlier proposal or source packets. No policy is adopted.

## Multiple elementary questions within one feature family

The initial sheet declares fixed elementary-question weights and prints the simpler one-question-per-family equations. The exact expansion for multiple questions is:

For family f and question j with fixed `β_fj≥0`, `Σ_j β_fj=1`, first average copies within each dataset; then average the canonical dataset/state rows within a dependence cluster c; then average eligible independent clusters for that same question. Call the resulting positive and opposing means `P_fj` and `O_fj`. Then

\[
P_f=\sum_j\beta_{fj}P_{fj},\qquad
O_f=\sum_j\beta_{fj}O_{fj},\qquad Z_f=P_f-O_f.
\]

The original final formulas `P111=Σα_fP_f`, `O111=Σα_fO_f`, `Z111=P111−O111`, `A111=max(0,Z111)` then apply without change. Missing required question results are bounded intervals using their fixed β, not dropped/reweighted. If a required question has no experiments yet, its point is null and its signed range [−1,1]; that is different from a nonexistent extra experiment being excluded from an observed question's cluster count. The two-family worked example has exactly one question in each family (β=1), so its arithmetic is unchanged. Six contact predicates combined inside G are not six independently weighted questions.

`reduce_a111_sheet_v1` consumes these β weights from the existing declared elementary/family weight input. The exact output family means use this equation, and their `source_to_cell_refs` include the elementary-question intermediate results. This clarifies the already specified IO without adding a production function.

## Nondetection local fit

In the synthetic calibrated nondetection row, RSCC .90 is the **observed surrounding protein/site marker fit**, not an RSCC assigned to an absent ligand. The independently supplied calibrated q_U establishes the ligand detection bound. The feature definition lists those actual observed site endpoints for D. It must not request or fabricate a missing ligand's RSCC. If the inspected region or its map quality is unestablished, D remains null.

## Native-input calculation audit

The research script now recalculates the 1MJH oxygen neighborhoods and angles directly from retained coordinates, and derives the printed ATP fit mean from retained validation values. It also checks the quoted 4KK3/4KK4 ligand RSCC values against their retained XML fields. Invalid native RSCC values are rejected rather than clamped; negative RSCC values inside the valid [−1,1] domain yield the explicitly proposed zero fit index. The exact script results, rather than this text's check count, are authoritative for the final run.

The source-local ATP index is limited as stated in `SOURCE_TO_CELL_001.md`: the full coordination endpoint validation panel was not populated, so its geometric predicates are separate partial cells. “Known missing target feature” in the worked example means known absent from the complete supplied material, not an unread or unresolved target region. Unread regions retain null role values and fixed denominators.
