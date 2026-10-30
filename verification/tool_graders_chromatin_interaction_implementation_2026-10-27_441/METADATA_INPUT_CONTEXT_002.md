# Explicit original input context for metadata extraction

Additive interface correction,2026-10-27;439 and441/001 remain unchanged.
C1 found an actual missing operand after tracing the closed records:
NativeMetadata has source_file/source_ref but lacks ContactSpec.input_key;
ParsedElements lacks ElementSpec.input_key and its separately supplied reference.
ReferenceAssertion/ReferenceRelation require these original relationships.

The accepted pure port is now:

```python
extract_chromatin_metadata(
    *, request: ChromatinRequest, native: ContactExtraction,
    supplied: MetadataSpec, elements: ParsedElements | None
) -> MetadataRelations
```

The additional request is the original selected request, not a new acquisition
or authority grant. Validate supplied equals request.supplied_metadata. Validate
native file/source relationships against request.contact, parsed element file
against request.elements, and exact input/sample/reference/population keys.
Native and supplied reference assertions remain separate. Shared artifact hashes
do not infer an input role, assembly, sample or biological association.

C1 owns this function and its tests. C3 passes its actual frozen request during
native bundle construction and any applicable retained worker path. C2's sheet,
array and numerical interfaces are unchanged. Root notified all three owners.

The selected reference environment has working NumPy/h5py but no jsonschema
distribution. C1's ordinary closed-data validator uses the repository's existing
Draft202012Validator dependency. C3 must supply and pin its actual required
jsonschema/transitive packages through the existing explicit execution setup,
and verify the resulting loaded NumPy/h5py/validator versions and files. Import
path order must not silently replace the selected numerical libraries. No shared
virtual environment is modified or assumed complete from its description.
