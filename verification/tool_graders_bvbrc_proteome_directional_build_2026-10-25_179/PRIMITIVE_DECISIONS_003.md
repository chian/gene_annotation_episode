# Primitive error and coordinate-state decisions

Root resolved two exact A/B handoffs before final verification.

B defines DirectionalNumericalContractError(ValueError), with `.code` and
`.pointer` strings; A imports and reexports that same class. This supersedes
the implication that A itself defines the class. B has no dependency on A/C,
and A's geometry-based semantic checks do not create an import cycle.

When otherwise valid native endpoints disagree with the number of nongap
symbols, trace geometry has state `conflict` and reason
`coordinate_span_conflict`. The independent native reported interval can stay
available. The generic word invalid in177's explanatory example did not define
this precise state distinction. Missing coordinates remain missing; malformed,
zero, reverse protein coordinates and out-of-range coordinates remain invalid.
Neither observation is overwritten. The unaffected axis and valid symbol
counts remain independently usable.
