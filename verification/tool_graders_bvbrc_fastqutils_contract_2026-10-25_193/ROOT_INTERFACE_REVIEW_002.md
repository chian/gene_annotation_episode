# Root review: close concrete FastqUtils interfaces before coding

The original193 packet remains unchanged. Its source findings and numerical
definitions are useful, but the following interfaces are not yet ready for
independent coding. This review changes no goal, scientific formula or runtime.

1. `ProviderParameters.artifact_bindings` accepts only a `content_ref`, and
   `FactSelection` requires an existing generated record reference. A results
   episode receives its immutable assignment before it downloads the output.
   That parent cannot supply a future artifact hash or parser-generated ID.
   Define both explicit requirement-based selection before acquisition and
   exact possessed-artifact selection. Define stable caller-selected document
   identities and finite measurement/population/component selectors that can
   be commissioned before output exists. Later exact saved-record selection
   can remain available. No discovery by guessed basename or arbitrary first
   match. Include one complete actual `ResultSelector` example constructed
   before download and the exact requested post-download facts.

2. `extract_fastqutils_metadata(original_task, supplied_metadata, documents)`
   needs a declared input object for every argument. The generic AppService
   `OriginalTask` contains identity, not the full original submitted arrays and
   recipe needed for library/stage construction. Specify the actual source of
   those request operands, how the host authenticates them against its original
   commission, and the exact pure handoff. Likewise define supplied metadata
   wrappers and the source/field relationships that distinguish requested,
   explicitly asserted and observed execution lineage. Existing source custody
   alone does not prove that any arbitrary source supports a stage-completed
   flag. Do not invent stronger evidence than supplied records provide, and do
   not make missing stage evidence erase independent artifact-local counts.

3. Unavailable category, population and association facts currently require
   values that may not exist. `CategoryFact.value`, for example, cannot represent
   a missing category without fabricating pass/warn/fail/unrecognized. Define a
   typed absent-value representation, exact availability requirements and
   cardinality rules. Preserve the difference between requesting a truthful
   missing state and requesting an available number. Do not turn the latter
   into an automatic scientific acceptance gate.

4. Freeze identity construction and all shared helper signatures before
   delegation. The proposed canonical encoding mentions an analysis ID absent
   from the provider parameters. State the actual known identity operands,
   original-pointer conventions and strict encoder/decoder ports. A/B/C must
   not independently invent incompatible cell, population or component IDs.
   Saved validation checks relationships without reparsing or recalculating.

5. A currently owns nearly every native format plus metadata and sheet
   construction. Split independent FASTQ/SAM-BAM parsing from FastQC/report
   parsing when their shared NativeDocument port is frozen. Assign common
   schema/identity helpers to exactly one owner. Define concrete format-level
   parser signatures and fixture handoffs, then balance remaining metadata,
   sheet, calculator and provider work against those ports. Required native
   data and calculations remain unchanged; no tool disappears from scope.

The revised packet must be additive, with complete schemas, semantic invariants,
before-acquisition and saved-result examples, current consumer names and
exclusive files for each proposed worker. Source inspection is evidence about
the producer, not evidence that a local validator or remote deployment exists.

## Additive correction after inspecting the actual generic schema

The statement in item2 that generic `OriginalTask` contains identity but not
the submitted arrays/recipe is wrong. Both the current production schema and
candidate186 contain `submitted_parameters` and `submitted_start_parameters`.
Those are the existing operands for requested library and recipe construction.
Do not create another full-request handoff solely because this review asserted
they were missing. Additional input/source bindings are needed only where a
concrete observed-lineage or custody consumer requires fields outside that
existing object. Specify the actual missing field and consumer first. The
remaining item2 requirement is to define supplied-metadata shapes, provenance
and requested/asserted/observed semantics precisely. The other four interface
findings remain unaffected.
