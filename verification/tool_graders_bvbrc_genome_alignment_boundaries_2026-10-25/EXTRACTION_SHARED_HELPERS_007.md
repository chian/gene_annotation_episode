# Shared C extraction preflight clarification

Additive to accepted006; no A/B/C output changes.

C1's new retained_records module exports
validate_retained_record_arguments(original_task, *, retained_records,
supplied_bytes) -> None. This checks whole-call types, closed wrappers and
existing receipt schemas, before data-dependent per-record recovery.
RETAINED_RECORD_ERRORS is the finite set of exact prefixed semantic error
strings content_missing, content_digest_conflict, metadata_record_unverified
and metadata_task_conflict. C2 imports these shared functions and constants.

C1's inputs module also exports
validate_genome_alignment_supplied_value_shapes(supplied_values: tuple) -> None.
It strictly validates each SourceEvidence/value wrapper and finite JSON. A value
with a recognized one of the six MetadataValue kinds must satisfy that exact
closed shape; malformed recognized-kind values are caller errors.

Other retained JSON stays uninterpreted and produces metadata_type_unsupported.
This includes a raw TaskInfoReceipt value selected at /value so the host can
collect its authenticated receipt. Such a receipt supplies scientific facts
only through the independently admitted retained_records input. It is not
promoted into a MetadataValue, and arbitrary stored JSON does not certify a
scientific relationship. This corrects the input wrapper ambiguity in001/002
without admitting a new positive witness or changing any output schema.
