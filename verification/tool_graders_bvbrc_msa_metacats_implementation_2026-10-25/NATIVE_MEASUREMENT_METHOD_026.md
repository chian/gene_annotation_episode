# Native observations without recorded method identities

Root accepts this additional correction on 2026-10-25. It qualifies the available
measurement statement in `MISSING_MEASUREMENT_METHOD_025.md`; both records remain
permanent.

The frozen `NativeObservation` has its exact field, native token, numerical
state, unit and population association, but no method identity. An available
native value therefore also has `MeasurementFact.method_ref=null` when selected
through `native_measurement`. This means that no method identity was recorded
in that observation. It does not mean the measured value is missing, and does
not justify inventing a requirement for an otherwise satisfied requested value.

Do not manufacture a method name from the field name, reader name or observation
ID. These identify different things. Calculated cells retain their actual saved
method IDs, including unavailable calculated cells that record one. A selected
native observation preserves its original value/state/unit and
`origin=native_observation`, with null method and the actual population if known.

Agent147 implements this exact distinction and tests it. The nullable schema
change accepted in025 already represents both cases. No native/provider schema
or numerical calculation changes.
