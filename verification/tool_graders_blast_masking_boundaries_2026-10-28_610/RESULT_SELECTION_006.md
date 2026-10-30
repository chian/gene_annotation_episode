# Additive result-selection correction before implementation

This changes only the proposed, not-yet-implemented result selector in HANDOFF001.
A parent must be able to select original input records and output materials before
a future capture creates host record/occurrence identities. The durable internal
record_key and Occurrence definitions remain unchanged. This is an implementation
boundary correction, not a goal change or a new episode/tool.

Replace selector.record_keys with the following required field:

```text
records:
  {mode: "all"}
  | {mode: "selected", entries: list[{
      operand_role: "sequences", operand_ordinal: 0,
      record_ordinal: integer>=0
    }]}
```

Entries are unique original input positions. They identify the supplied FASTA
occurrence and original record ordinal, not a header match, result rank or generated
hash. Empty selected entries request no sequence quantities. The pure projector
resolves them against actual sheet input occurrences and retains original identities
internally. Missing, malformed and unavailable records stay distinguishable; a
missing requested ordinal is not silently dropped or replaced with another record.
Counts generation has no mask quantities and no sequence records to project.

Replace include_artifacts with the required field:

```text
artifacts: list[{
  direction: "input"|"output",
  role: "sequences"|"reference_sequences"|"statistics"|"mask"|"stdout"|"stderr",
  ordinal: 0
}]
```

Selectors are unique and compatible with the selected operation. An empty list
requests none. They select only exact original occurrences: for example output
mask, or output statistics from create_counts. They never implicitly grant all
input/reference/statistics artifacts because one output was requested. A requested
absent occurrence produces a typed qualification/failure, not a fabricated artifact.

All other selector fields from HANDOFF001 remain: version, mode, quantities,
statistics_fields, statistics_unit_codes, include_checks, saved_sheet_ref.
For include_checks=true, return relevant global checks plus checks belonging to the
selected records/statistics; do not append unrelated records' details. Native source
and artifact identities remain internal typed operands and custody, outside model-
facing decision text. The separate prompt/material-operand presentation still
requires its own trace and feedback before implementation; this correction does
not claim that presentation is already solved.

Pure project_masking_result keeps its signature. It must not reparse native bytes,
recalculate mask counts, create grants beyond selected returned artifacts, or start
acquisition. It selects exact common-sheet component values and requested native
statistics fields/rows. Missing requested unit codes remain unreported, not zero.
Both generated counts thresholds and original requested clipping parameters retain
the distinct meanings established by the612 native oracle.

Typed schema validation and receipt admission use the exact selected projection.
Actual practical completion follows the original requested result meanings and
existing endpoint/controller path; a numerical mask threshold or validation-quality
score is not a completion criterion. No extra observation is created by projection,
parsing, reply construction or saved-return replay.
