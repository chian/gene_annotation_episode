# Missing measurement method: additive correction

Root accepts this correction on 2026-10-25 while implementing the original
MSA/MetaCATS requested-fact boundary. Earlier records remain unchanged.

The frozen `MeasurementFact` required a nonnull `method_ref` even when its
selected scientific dependency was unavailable and no saved measurement cell
existed. A request ID is not a measured method, and a made-up method identifier
would violate the goal's requirement to preserve unknown information.

`MeasurementFact.method_ref` therefore becomes `id|null`. All other fields and
selection meanings remain unchanged. An available saved measurement must retain
its actual method reference. A missing dependency without a saved cell has
`value=null`, its actual unavailable state, `method_ref=null`, and the exact
dependency requirement references. It may retain statically defined metric units
and origin; unknown native units remain `native_unknown`. A saved native missing
token or unavailable calculated cell with a known actual method retains that
method rather than erasing it. No placeholder method, guessed population or
replacement numerical value is introduced.

This is a correction to the declared information contract, not a numerical
formula, scientific grading rule, new episode type or extra action. Agent146
owns the shared closed schema change. Agent147 owns projection and saved-value
checks, including rejection of null methods for available saved measurements.
Root's later return owner uses that exact schema and authenticates saved content.
