# Literal alignment values and closed XMFA return selections

Additive correction accepted by root on 2026-10-25 after reading the complete
application communication validator and the actual outward fact schemas.
Previous frozen records remain unchanged.

The existing parent form grammar requires explicit closed objects, required
fields and semantically restricted strings. It cannot represent arbitrary
strings, literal `+`/`-` as its code-enum strings, or a union of differently
shaped objects. Do not open that grammar to arbitrary prose or general unions.

Root adds two literal semantic string formats to the application communication
validator: `alignment_symbol` is exactly one printable nonwhitespace ASCII
character (code points33 through126); `alignment_strand` is exactly `+`, `-`, or
`unknown`. Nullable instances retain ordinary null semantics. These describe
actual characters/strands, not record identifiers. Saved-value validation still
requires equality to the exact selected native or calculated value. Multiple
characters, whitespace and arbitrary prose remain invalid.

Agent147 confirmed that outward group-count symbols, consensus characters,
reference-difference characters and XMFA aligned/forward symbols are single
characters. Native protein detail labels do not cross these fields. Root maps
those specific outward fields to the literal semantic formats when constructing
report schemas; underlying native records remain unchanged.

The commissioning `XMFA_METRIC_SCHEMA` union remains unchanged. Its four
selection shapes are useful for choosing the measurement. Only the outward
`XMFAMeasurementFact.selection` becomes the following closed record:

```
{metric: the existing finite union of metric tokens,
 block_index: index,
 column_0based: index|null,
 symbol: one alignment character|null,
 member_a: positive integer|null,
 member_b: positive integer|null}
```

All six keys are required. Values present in the original selected metric are
copied exactly; all other fields are null, meaning not applicable to that
measurement. Agent147 validates this exact relationship to the original
commissioning selector. There are no new measurements, silently supplied
coordinates or changed scientific formulas. The adapter saves this closed fact;
the return owner copies it exactly rather than changing its shape in transit.

Agent146 owns the shared outward schema adjustment. Agent147 owns projection
and exact saved-value validation. Root owns report-schema conversion, the two
bounded application string formats, and integration tests. No shared
method_loop, prompt template, credit or continuation change is required.
