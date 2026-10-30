# Additive exact-schema clarification

The current exact draft is `EXACT_SCHEMA_PROPOSAL_002.json`. It preserves001 and adds required `source_kind` to the return row, retaining primary_source/retained_extraction/synthetic_fixture separately from the calculated scalar's derived origin and input_origins. The plan's scalar return description must include this field. Its three Draft202012 schemas validate; this is a proposal artifact, not an installed or registered operation/return.

Two root review choices remain explicit in the plan: only the named concentration coordinate(s) may accompany a point/sensitivity/cross-concentration scalar as scientific context; and the additional recurring fixed-concentration scope paragraph must be printed/reviewed before coding. These are concrete implementation choices for review, not a user permission request or a runtime gate.

Root233 has now independently accepted228's final pure code and291-cell example with its documented fixed-concentration and finite-domain scope.231 still makes no selected integration claim and has made no production/test edits.
