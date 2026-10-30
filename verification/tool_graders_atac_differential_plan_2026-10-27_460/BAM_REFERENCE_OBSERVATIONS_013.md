# Actual BAM reference dictionaries at the ATAC calculation boundary

This additive contract supplies a missing measured input identified while
connecting native execution to the numerical sheet. A caller's matching
reference_id labels do not reveal a conflicting reference length or sequence
dictionary actually present in a BAM. The original goal remains unchanged.

## Native production and retained input

For each selected treatment BAM occurrence, the native producer reads its actual
header through the explicitly bound BAM reader, retains the complete SAM-format
header text, and binds it to the original input byte identity, callpeak run and
zero-based position in that run's treatment_input_refs. The input's before/after
identity must agree with the selected native plan. Do not generate a header from
the caller's reference object, the synthetic BAM generator's intended values,
effective genome size or bedGraph endpoints.

The producer records failed/unavailable inspection honestly and does not choose
a replacement input. This is finite input inspection inside the selected native
operation, not a model call, independent episode or new action observation.

## Pure native parser and sheet port

A fresh workload owns additions to `atac_differential_contracts.py`, one new
`atac_reference_observations.py`, the small sheet assembly extension in
`atac_differential_sheet.py`, and its own tests/packet. Existing464 work is frozen.
It does not modify the existing likelihood/interval/bridge modules or execution.

Add ordinary records:

```
AtacBamReferenceRow = {
  row_ordinal: int, locator: Locator,
  chromosome: str|null, length_bp: int|null, sequence_md5: str|null,
  original_fields: list[str]
}

ParsedAtacBamReference = ParsedEnvelope plus {
  version: atac_bam_reference_parsed_v1,
  callpeak_run_key: str,
  input_ordinal: nonnegative_int,
  input_artifact_ref: str,
  rows: list[AtacBamReferenceRow]
}

parse_atac_bam_reference(
    content: bytes|BinaryIO|None, *, artifact: AtacArtifact,
    callpeak_run_key: str, input_ordinal: int, input_artifact_ref: str
) -> ParsedAtacBamReference
```

The declared artifact format is `sam_header_text`. Use the same supplied-byte,
source-location, hash/extent and partial-read semantics as the existing parsers;
no path opening or BAM execution occurs in this function. `binding_key` is the
exact run key plus `:input:` plus the decimal input ordinal. A dictionary row is
one original @SQ line. Preserve its tab-separated fields and locator. Retain
other SAM header lines as header records, using explicit `sam_header` kind.

SN supplies chromosome, LN supplies integer length in bp, and optional M5
supplies a 32-hex-character sequence MD5. Missing, malformed, negative or repeated
tags remain explicit issues; keep original tokens. Do not select an arbitrary
first repeated SN/LN/M5. Preserve duplicate chromosome rows as distinct source
occurrences and mark the ambiguity. An absent M5 is unknown sequence identity,
not a mismatch or an invented digest. Empty/missing/failed/partial headers and
unsupported declared formats remain distinct. Unsupported format must not be
downgraded to supported-malformed by a later row error.

Extend ordinary parsed-record validation for this exact record type and header
kind. Do not introduce a general JSON scoring language. Header fields are
reference metadata, not annotation-confidence numbers.

`build_atac_differential_sheet` gains the optional keyword
`bam_references: Sequence[ParsedAtacBamReference] = ()`. Every new sheet stores
`bam_references: list[ParsedAtacBamReference]`, preserving all supplied records.
The sheet validates structure and records absent or contradictory run/input
occurrence associations; it does not perform a competing numerical-reference
filter. Explicit supplied-track sheets legitimately have an empty list.
Historical native sheets without actual header observations remain readable
evidence with unavailable reference verification, not silently upgraded inputs.

## Sole calculation consumer

Workload467 extends `prepare_atac_calculation_inputs` to consume these actual
records when a track comes from a native BAM callpeak run. Match by run key,
input_ordinal and exact selected input artifact reference. Require one usable
bound dictionary for each selected treatment-input occurrence. Matching content
can appear under distinct roles, per011; no deduplication by hash.

For every selected comparison chromosome, use the explicit reference aliases
and compare its actual unique @SQ chromosome/length with the corresponding
declared reference contig. Missing/ambiguous chromosomes, length conflicts,
unusable header bytes, wrong input/run associations or conflicting dictionaries
cannot authorize the affected native run's interval joins. Disable the affected
run's numerical track ports with precise issues; retain other independently
usable measurements and all original native tables. Do not rename a reference,
fix its length, clip a conflicting dictionary to fit, or invent coordinates.
An explicit supplied-track input has no native BAM dictionary requirement.

Retain extra actual header contigs outside a narrower selected population; do
not infer that the parent's selected subset is the complete BAM dictionary.
If M5 is present for corresponding contigs across inputs, contradictory M5
values are an actual reference conflict. Matching names/lengths without M5 are
dictionary compatibility under the supplied reference assignment, not proof of
identical genomic sequence. Preserve unknown sequence identity. SHA256 and MD5
are different quantities and must never be compared as interchangeable hashes.

No precomputed `matches_reference` flag substitutes for those actual rows. The
result worker passes saved observations through and calls the bridge; it does
not implement another reference decision. Saved recalculation uses the retained
header bytes/parsed rows and never needs to reopen the original BAM.

## Verification and independence

Obtain the actual header text from both retained460/native001 input BAMs in a
small explicitly bounded native inspection. Use the already prepared isolated
Python/pysam environment, unchanged BAM inputs and retained output identities.
This is read-only input inspection, not a rerun of callpeak/bdgdiff. All imports
and probes run through existing local_jobs/native_lifecycle with20GiB RAM,
4GiB scratch,zero swap,no wall budget and immutable source/input/interpreter pins.

Check actual chrToy length12000 from those BAMs, complete header retention,
typed native parsing and saved-only assembly. Label synthetic counterexamples:
wrong length despite matching reference_id, wrong run/input ordinal/ref, missing
SQ, duplicate names/tags, invalid LN/M5, partial header, unknown M5, two inputs
with conflicting M5, selected-subset versus extra contigs, alias mapping, equal
content in different legitimate input occurrences, and saved recalculation after
the original BAM is absent. No test may use the fixture generator's intended
dictionary as proof of what the BAM contains.

Parser/assembly work and producer implementation can proceed independently
against this signature. Existing explicit-track bridge/calculation tests need
not wait. Native-BAM join acceptance depends specifically on these actual
observation records, not on completion of an entire unrelated workload group.
Do not change tally, prompts, episode behavior or the annotation scorer here.
