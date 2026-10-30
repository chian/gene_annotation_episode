# Explicit additive correction to frozen002

Root and A identified three concrete input-representation defects after freezing
002. `SCHEMAS_003.json` is the full corrected schema; frozen002, PORTS_002 and
WORKLOADS_002 remain unchanged. Apart from `$id` revision003, the only schema
changes are:

1. `Artifact.native_name` is nullable, matching ParseContext.native_name.
   A possessed artifact may have no native filename. Readers retain null and
   never invent one from an internal artifact ID.
2. `EncodingBasis.basis` additionally admits `native_sam_phred`. For this basis,
   encoding is exactly `phred33`, native_locator names the native QUAL field,
   and metadata_id/evidence/declaration are null. SAM1.6 specifies QUAL as
   Phred+33; this is a native format representation, not a caller assumption.
   Preserve `native_bam_phred` with encoding `bam_phred` for numeric BAM bytes.
3. `AlignmentRecord.native_quality_symbols` is required nullable string: SAM
   retains its exact QUAL token, including `*`; BAM supplies null. Original
   bytes and locator remain authoritative. `phred_values` remains decoded
   numeric qualities or null where absent. Missing QUAL does not make the
   specified encoding unknown or turn missing values into zero qualities.

`Artifact.content_ref` is exactly `ParseContext.content.artifact_ref`, not a
nonexistent ContentBinding.content_ref. Artifact.source_ref/sha256/byte_count
equal the corresponding content fields. Artifact.content_binding is a detached
copy of that complete binding. Native artifact IDs use that binding's hash.
`checked_bytes` binds exact bytes and length; it does not establish host custody.

Quality calculators can consume native SAM decoded Q/histograms using
native_sam_phred without supplied encoding metadata. An explicit FASTQ encoding
declaration remains an assumption; FastQC's inferred Encoding remains distinct.
All four quality-derived outputs carry their exact basis. These changes add no
calibration score, confidence category or attestation gate.

Source: retained193 `sources/hts-specs/SAMv1.tex`, mandatory QUAL definition and
BAM QUAL representation. Root explicitly accepted the three changes and A was
notified before implementing against003. Other identities/signatures stay as
in PORTS_002. This is a contract correction, not a parser test claim.

Two registry interpretations are made explicit without editing frozen registries:

- METRIC_SPECS_002 already limits phred_histogram_count to SAM/BAM and identifies
  SAM's specified Phred+33. Its exact basis token is now native_sam_phred.
- COMPONENT_SPECS_002's removed_count/removed_fraction have conditional meaning:
  native_report_retention jobs use native_report_derived and
  native_reporting_precision, as the original193 definitions and002 examples
  require; read/base/pair retention uses derived_descriptive and not_estimated.
  This changes no number or formula. `NUMERICAL_CORRECTIONS_003.json` provides
  the exact machine-readable overrides for common component_spec consumers.
