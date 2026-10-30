# Surviving population headers and selected output directories

Additive correction,2026-10-27. C3 traced two concrete omissions before joining
its implementation. Frozen439 and earlier441 records remain unchanged.

## Complete metadata survives with each sealed population

PopulationSeal adds required `native: NativeSheetHeader`, using the existing
closed `{metadata,chromosomes}` record already used by ContactSheet.native.
Population/table records are not duplicated in another ContactExtraction field.

An earlier sealed population must retain the observed native header and
chromosome assertions needed to construct its numerical sheet when execution
ends before the final bundle. A valid complete population seal has nonnull
observed native metadata, consistent with its original request/input and actual
population. Multiple surviving seals must agree on their observed header;
conflicts remain explicit failures. A digest or caller label does not fabricate
missing header measurements.

C1 owns the amended schema/types. C3 writes the actual header when sealing and
reconstructs ContactExtraction from the authenticated surviving seals when the
bundle is unavailable. Root capture checks seals against the original plan and
closed writer evidence. Any needed elements/metadata can be parsed from already
retained input bytes through C1 with the original request. No original HDF5
reopening or new acquisition is used to recover omitted header information.

## output_prefix is an actual selected directory

ChromatinRequest.output_prefix is a safe relative directory under the original
attempt directory. Prepend it to every fixed role path in439 section8:

- `{output_prefix}/inputs/contact.native`
- `{output_prefix}/inputs/elements.bed`
- `{output_prefix}/inputs/metadata.json`
- `{output_prefix}/populations/pN/{bins.tsv,contacts.npy,weights.npy,cell-states.npy,dense-values.npy,manifest.json}`
- `{output_prefix}/bundle.json`

Do not ignore this selected field as descriptive metadata. No absolute path,
parent traversal or alternate resource directory is inferred. The old unprefixed
symbolic execution fixtures remain planning history; actual producer and worker
plans use the amended exact paths. C1/C2 scientific record meanings and formulas
are unchanged.

C3 exports `chromatin_output_files(request)` and
`validate_chromatin_run_plan(value)` as pure ports. Original request, plan,
declarations, seals, capture and worker all compare the same complete fixed role
inventory and paths. Root does not reproduce a separate path-construction rule.

The remaining C3 named pure request/binding/schema/argv/environment exports and
explicit `freeze_chromatin_software_binding` preparation helper are accepted
within its existing exclusive files. That helper records an explicitly selected
source/dependency snapshot; it does not install packages, select a resource or
create an autonomous preparation workflow.
