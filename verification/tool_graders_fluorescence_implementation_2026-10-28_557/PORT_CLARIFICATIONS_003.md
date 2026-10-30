# Component identities and native-value comparison

These resolve specific questions from the shared-contract owner. Frozen001 and
clarification002 remain unchanged. This adds no operation or scoring definition.

- Population/fraction Cell.population uses sample_key and gate_key; domain_key
  and channel_key are null. The gate already resolves its own threshold operands.
- Intensity Cell.population uses sample_key, gate_key, domain_key, channel_key,
  and denominator selected_finite.
- Control Cell.population has null sample/gate/domain/channel keys and denominator
  paired_controls. The control request resolves both sample/population operands.
- Native-comparison Cell.population has null sample/gate/domain/channel keys and
  denominator none. The native report and its component_request resolve the
  operands.
- Request identity/order validation may derive which cells the explicit saved
  parameters require, including control operand fractions. It does not recalculate
  gate membership or any numeric answer. Population cells use denominator none;
  fraction cells use their requested parent/evaluable denominator.
- A native_value cell copies the report's actual finite numeric value and unit,
  even if its meaning is unlinked; it is a reported quantity, not a validated
  equivalent of a calculated component. Missing report value remains unavailable.
- native_minus_calculated requires the linked cell to have a finite available
  value and the same known unit as the report. It performs no unit conversion.
  Unknown/mismatched units or an uncomputed operand yield unavailable with
  native_report_uninterpretable. Rounded values never replace exact calculations.
- Retain decimal_places as native formatting metadata. Do not introduce an
  inferred rounding-agreement judgment, tolerance or additional issue code. The
  numeric difference remains the exact reported value minus calculated value.
