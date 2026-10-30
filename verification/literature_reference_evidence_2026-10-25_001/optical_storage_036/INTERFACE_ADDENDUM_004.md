# Optical004: bounded missing-record custody and exact saved associations

Root accepted and released this additive interface refinement after reviewing
checkpoint003. Earlier proposal/checkpoint artifacts remain unchanged. No033,
035,037, scientific TASK or existing operation/schema is changed.

The closed optical operand metadata object D gains exactly one required field:

    measurement_source_ref: {
      type: [string, null],
      format: reference,
      x-reference-namespace: source
    }

It is the original saved numerical observation's
row.number.selector.witness.source_ref, or null when there is no number and no
measurement_ref. It supplies no scalar, source body or new numerical meaning.
Deterministic binding reconstruction compares this field against the original
validated035 extraction using exact JSON equality. The normal closed-form
reference resolver admits it as an actual source reference. No source or
artifact access is added to rendering; artifact-reference transport is not
needed. Existing local physical/semantic identity and independence meanings
remain unchanged.

The receiving working-record page can omit a numerical measurement reference
while retaining a broad condition/meaning record that includes that operand.
The renderer cannot recover an off-page token location from its opaque reference.
Checkpoint003's conservative fallback hid every anchored record when any such
anchor was missing. Root correctly identified that as too broad: it could hide
unrelated-source scientific information, including other evidence families.
That fallback is replaced, not shipped as complete.

For an off-page/missing optical token anchor, withholding now applies only to
anchored automatic expansions whose actual anchor.source_ref equals that
operand's measurement_source_ref. A record-level source field cannot broaden
that match. Other-source anchored facts and scientific labels remain visible.
When the token anchor is known, the exact source/artifact overlap check applies,
including partial overlap. The dedicated optical view follows the same source
boundary when deciding whether a scientific label can be expanded. Original
records remain intact and explicitly selected scoped source reads remain allowed.

The additional metadata is necessary for bounded automatic subset transport,
not a new axis, score, source interpretation, episode, gate or scientific TASK.
Actual provider checks cover an off-page optical token mixed with an admitted
typed reference to an unrelated source; raw/canonical and unrequested derived
numeric sentinels must be absent while the unrelated scientific label remains.
The existing closed-form admission test now checks the source namespace field.

Root's exact-association review also identified Python bool/number equivalence
in saved snapshot, binding and outcome comparisons, and incidental failures on
huge/nonfinite saved values. Optical004 uses canonical/type-sensitive JSON
comparison for those whole saved associations, checks returned immutable binding
record IDs, and guards finite numerical validation before serialization. The
typed schema and numerical model meanings do not change. Synthetic adversarial
checks include False versus0.0,1 versus True, wrong immutable binding IDs,
10**400, NaN and infinity. Failures are deliberate ContractError results; source
parsing and historical cell recalculation remain forbidden.

The source scope fixture is reported narrowly: ordinary Store scientific sources
are reusable; actual receipt and assigned-page ancestry checks authorize source
work. An explicitly injected reference-subset scope guard verifies the adapter's
scope rejection port. It is not presented as proof of target-root restrictions
that the current Store does not assign to source records.

004 tests, hashes and final terminal results will be recorded separately. This
engineering work has no configured-model or primary-paper execution claim and
does not complete A105 or the full literature goal.
