# Selected preparation: time units and inherited preparation records

Additive implementation clarification, 2026-10-28. This resolves two concrete
questions in P589 against proposal573 and contract013; it changes no goal.

## Preserve the actual scope of the selected operation

The compensation restrictions in proposal573 apply to compensation: it requires
known uncompensated, untransformed input in the selected compatible basis.
Scaling instead requires the selected original encoded FCS domain, with scaling
not already applied or unresolved. Do not impose the compensation restrictions
on scaling. Preserve the input's compensation and transformation records exactly
in the output domain; metadata scaling neither establishes nor clears them.
Actual original bytes, selected dataset and metadata must still agree with the
parent parse. No operation inverts or reapplies a declared preparation implicitly.

## Units describe the values actually produced

Compensation preserves each channel's unit. Scaling preserves fluorescence and
other non-Time units, including null. It must not relabel gain correction as
physical calibration. Ordered labels, analytes and native names remain unchanged.

Pinned FlowIO1.4.0 identifies Time by native PnN (case-insensitive exact match)
and applies a supplied TIMESTEP to it. The FCS3.1 normative reference, TIMESTEP
entry on printed page27, defines the time step in seconds:
https://flowcytometry.smhs.gwu.edu/sites/g/files/zaskib311/files/2021-11/Data%20File%20Standard%20for%20Flow%20Cytometry%281%29.pdf
FlowIO then also performs declared positive-decades linearization on that channel.
Therefore the explicit output-unit selection must be checked after actual
metadata resolution, not inferred merely from a caller's label:

* With an actual Time channel, a valid supplied TIMESTEP, and zero Time decades,
  output Time unit may be exactly `seconds` or null. A requested encoded unit
  such as `ticks` is incompatible with the produced values. No silent relabeling.
* With Time TIMESTEP plus positive Time decades, retain the native calculation
  when the selected output unit is null; the resulting physical unit is not
  established by this contract. Do not falsely call that result seconds or add
  an arbitrary numerical acceptance threshold. A requested known unit is an
  incompatible domain selection, not a malformed native number.
* Without an applied TIMESTEP, preserve the original Time unit exactly. Do not
  infer conversion, seconds, or a missing timestep.

The request validator may allow the prospective Time-unit difference for this
one method. The native operation and outcome validator must enforce the rules
above against the retained resolved metadata before accepting complete/partial
prepared data. A semantic mismatch returns the existing `domain_incompatible`
problem with raw input/metadata retained and no mislabeled prepared values.
Other unit changes remain invalid caller contracts. No new recipe field,
independent transform, scoring implementation, prompt or episode type is added.

Verify ticks to seconds, null retained under selected conversion, absent timestep,
nonlinear Time with null versus an incompatible known unit, compensation unit
preservation, and scaling that preserves an original compensation/transformation
record. These are tests of selected preparation semantics, not new runtime gates.
