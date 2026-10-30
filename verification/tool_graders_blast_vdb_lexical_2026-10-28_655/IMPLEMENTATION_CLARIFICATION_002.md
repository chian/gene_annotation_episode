# Integer conversion availability in the shared lexical reader

Implementation clarification from the lead agent on 2026-10-28. The frozen
`IMPLEMENTATION_PORT_001.md` remains unchanged. This clarifies an exceptional
conversion case; it does not change scientific scoring or episode behavior.

Python can reject an otherwise valid, all-ASCII decimal integer spelling when
its digit count exceeds the interpreter's configured conversion limit. The
old specific-entry parser skipped width/empty/N/A rows before calling
`_native_integer`, and propagated its `ValueError` for otherwise eligible rows.
The new lexical reader must inspect lengths even in rows with another missing
field, so it needs an explicit representation of that unavailable conversion.

- Catch `ValueError` from the existing `_native_integer` in the lexical reader.
  Retain the entire original length lexeme and row, set
  `native_reported_length` to null, and append exactly
  `{code: integer_conversion_unavailable, field: length_lexeme}` after the
  existing field checks. Do not call the spelling invalid or discard the row.
- The old wrapper still skips width/empty/N/A rows first. Only an otherwise
  eligible row with `integer_conversion_unavailable` delegates that same
  length lexeme to the existing `_native_integer` again, preserving its
  original exception. This exceptional delegation adds no numerical policy.
- Do not change `_native_integer` or the process's integer conversion limit.
- Verify lexical retention and both legacy behaviors under bounded529. Keep
  the earlier prechange observations and their source pins unchanged. The
  additional edge-case expectations follow the inspected prechange control
  flow and unchanged integer conversion function; they are not observations
  from executing historical snapshot code after the edit.
