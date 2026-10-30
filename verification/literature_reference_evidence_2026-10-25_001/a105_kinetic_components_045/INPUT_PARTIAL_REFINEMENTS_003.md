# Released045/046 partial-input interface003

Parent explicitly approved these additive refinements to001/002. Operand keys
add exactly `unavailable_reason`, null or one of this finite vocabulary:

- `source_measurement_unreported`
- `source_kinetic_unit_unreported`
- `unsupported_source_kinetic_unit`
- `source_operand_qualification_unknown`
- `source_operand_qualification_conflicting`
- `source_numeric_range`

Point/censored operands require unavailable_reason=null and the correct
canonical unit for their parameter kind. Missing/conflicting operands have
value=null and relation=none, may have unit=null or the correct canonical unit,
and may carry a specific unavailable_reason. Unit-unreported/unsupported reasons
require unit=null. Their native source values, expressions and qualifiers stay
in the reader's separate retained extraction and are not fabricated as canonical
points. An unknown parameter kind yields a null calculator operand plus the
reader's explicit native unresolved-kind reason; no fourth parameter kind is
invented here.

Each raw numerical cell and downstream unavailable contrast/model cell preserves
the operand's concrete unavailable_reason before generic status fallback.
Consequently a missing source unit stays missing source unit even if no model
was supplied. Both row.unit and raw-cell unit can be null. All other001/002
fields/meanings remain; exact estimate-key material includes this new field.

The calculator exports `INPUT_UNAVAILABLE_REASONS` and
`validate_kinetic_inputs` in addition to the previously proposed API/constants.
The latter returns a detached validated input, performs no source reads and
does not populate scientific interpretations. No other input expansion.
