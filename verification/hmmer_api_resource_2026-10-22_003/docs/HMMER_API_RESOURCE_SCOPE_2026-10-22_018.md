# Controlled API timing timestamp meaning, scope018

This additive pre-integration clarification retains016/017 unchanged. Root read
the complete actual communication validator, resource handoff contracts and
assembled-service helpers. Parent forms do not accept an unrestricted UTC
string or date-time format. Existing handoff checked_at already uses a declared
identifier namespace whose value is validated against original recorded facts.
No generic communication/generation schema change is required.

ApiTimingFactV1 from016 retains its exact field names and values. Its closed
parent-form item schema is:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["receipt_ref", "job_ref", "duration_measure", "observation_unit", "elapsed_seconds", "observed_at"],
  "properties": {
    "receipt_ref": {"type": "string", "format": "reference", "x-reference-namespace": "source"},
    "job_ref": {"type": "string", "format": "reference", "x-reference-namespace": "resource_execution"},
    "duration_measure": {"type": "string", "const": "hmmer_reported_search_elapsed_seconds"},
    "observation_unit": {"type": "string", "const": "logical_provider_job_reported_result"},
    "elapsed_seconds": {"type": "number", "minimum": 0},
    "observed_at": {"type": "string", "format": "identifier", "x-reference-namespace": "api_timing_observation_timestamp"}
  }
}
```

C supplies the top-level requested source api_execution_measurements as an array
of exactly this item, with x-source on the top-level array only. The timestamp
namespace resolves only exact original UTC observation timestamps of qualified
API timing sources actually received within the current episode's scope.
Factual validation additionally ties every item's timestamp, elapsed value,
unit, job and receipt identity to that SAME original source/witness. Resolving
a timestamp from another known fact is insufficient to alter a row. Original
UTC validation and the source's original first acquisition time remain required;
no fresh clock read, unrestricted explanation string or extra model call.

The existing native/source/handoff validators and their namespace meanings are
unchanged. C owns this source-specific resolver/fact path under016's file list;
A/B's witness/statistic formats are unchanged. Typed source/metadata records
remain local facts, not another score or synthetic completed action.
