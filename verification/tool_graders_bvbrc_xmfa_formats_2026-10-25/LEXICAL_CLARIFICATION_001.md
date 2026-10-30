# Native metadata payload separator clarification

Additive clarification accepted by root on 2026-10-25 before the parser handoff
was frozen. No fields or permanent contract text changed.

For a recognized metadata key, consume exactly the first horizontal whitespace
separator character. The native Mauve writer supplies one tab. Everything after
that separator belongs to the retained `value_token`, including leading spaces
or tabs, internal spaces and trailing whitespace. Do not consume a whitespace
run or strip the payload. `raw_line` continues to preserve the complete line.

For example, the source line `#Sequence1File\t  source with spaces.fa` has the
value token `  source with spaces.fa`, including its two leading spaces. Here
`\t` denotes the actual native tab. A SequenceNEntry payload containing leading
whitespace retains that whitespace in both `value_token` and the separate
`integer_value.raw_token`; it is not ordinary decimal digit syntax and receives
`xmfa_metadata_integer_invalid`.

The tests include the native-tab/leading-space filename case, additional tab
payloads, a first-space separator, exact byte locations, and the preserved
malformed integer payload. This is format interpretation, not a source binding,
filename normalization, source acquisition or scientific confidence rule.
