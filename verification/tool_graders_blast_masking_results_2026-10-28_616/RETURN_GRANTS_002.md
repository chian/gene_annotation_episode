# Additive return-grant and multi-source corrections

Root approved these before host adapters were implemented.001 otherwise remains
the frozen contract. No prompt text or new scientific score is introduced.

Projection.status and Publication.status remain one Status object. The fact source
execution.masking_status is array[Status]. Own-result facts wrap the object once;
receiving parents retain exact admitted rows, deduplicating exact equal values
only. They never select a latest status or collapse different selectors by source.

masking_fact_sources returns the existing fact catalogue shape
{source_name:{type,meaning,report_schema}}, with x-source on each report_schema.
It does not return bare JSON schemas. All seven sources use arrays in their forms.

Selector gains required saved_data, a unique list of sheet, calculations or
parsed_statistics. Projection and Publication gain required saved_data, a list of:

```text
{source_ref:string, kind:"sheet"|"calculations"|"parsed_statistics",
 artifact_ref:string, sha256:64 lowercase hex, size_bytes:integer>=0,
 schema:"sequence_masking_sheet_v1"|"sequence_masking_components_v1"|
        "windowmasker_statistics_v1"}
```

Kinds match the schema names in that order and the exact corresponding Prepared
artifact. Mask operations allow sheet/calculations; WindowMasker also allows
parsed_statistics; create_counts allows parsed_statistics only. A missing
requested artifact produces requested_saved_<kind>_unavailable. Expose
SAVED_DATA_SCHEMA and execution.masking_saved_data as the seventh fact source.
The pure projector gains required saved_data input: the already authenticated
descriptors. It only selects them. These are derived immutable artifacts, never
native Occurrences; no source_grading envelope is granted by this selection.

record_refs extends source and explicitly selected native artifact grants with
only these explicitly selected saved artifact refs, deduplicated in order.
Returning source or scalar measurements alone grants no saved data. Later
saved_recalculation admission requires the original exact received/supplied
authenticated sheet. No independent externally supplied sheet substitutes for
the original path; an original child can now explicitly return that sheet.

The internal retained grading envelope additionally holds original_plan, allowing
pure Bundle/compiler validation without the removed native working paths. Worker
output role/schema assertions are established by the bounded writer using613
validators; byte-authenticated output descriptors and the original worker manifest
authenticate those assertions on replay. Recalculated components are retained as
a separate worker output; saved_data.calculations still identifies the original
Prepared calculations, preserving historical original measurements.
