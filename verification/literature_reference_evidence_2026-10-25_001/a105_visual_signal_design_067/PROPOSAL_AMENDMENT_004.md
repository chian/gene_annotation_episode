# Final reported-quantity association correction004

Final normative schemas are REQUEST_SCHEMA_004, EXTRACTION_SCHEMA_004,
SHEET_SCHEMA_004 and RETURN_SCHEMA_004. Earlier001/002/003 remain intact.004
includes002/003 and corrects an ambiguity in001's phrase "same comparison."

`comparison_relation=supported` means this representation describes the same
single reported signal quantity for the selected numerator/reference. Merely
asking the same variant/reference biological question does not establish that
relationship. `different` explicitly means a different reported quantity or
experiment, while unknown/conflicting retain their ordinary source meanings.
Biological/physical measurement identity and preparation replication remain
separate witnessed fields.

Two linked displays of one reported quantity saying1.00 and1.12 are a source
representation conflict. Separate experiments yielding0.60 and0.80 are not.
Different-quantity rows retain their complete native inputs/results, expose
the explicit association state, withhold this request's aggregate scalar with
different_reported_quantities and permit the child to choose a separately
scoped next comparison. They are not silently discarded, averaged or treated
as contradictory physical measurements. Unknown-linked rows likewise retain
their native information without becoming known evidence for this comparison.

Signal-scale state also gains `different`, which is distinct from contradictory
source evidence. A raw printed pair at known different scales cannot supply a
meaningful normalized ratio. Preserve both parsed primitives and return
signal_scales_differ; unknown scale returns signal_scale_unresolved. Neither
uses a fabricated scale conversion or denominator. Already-normalized printed
ratio/percent can use not_applicable for this raw-pair scale question.

The typed return adds comparison_relation_states and signal_scale_states, so
these qualifications survive C4 even when the scalar is unavailable. A finite
point candidate belonging only to an explicitly different quantity does not
become a candidate for the selected reported quantity; its actual value remains
in its native retained row. A caller needing it requests its proper comparison.
Known numeric source conflict is assessed only among linked representations,
not inferred from unknown or distinct experimental owners.

This is a proposal refinement, not a change to an implemented v2 record or an
existing v1 sheet. No pooling/scientific likelihood, replication bonus, new
axis, experimental grader or W05 calculation is added.
