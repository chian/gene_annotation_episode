# Model sample-column correspondence clarification

Additive clarification of ModelAssociation.sample_column_map. The original
contracts and historical outputs remain unchanged.

For this closed shape, sample_column_map[i] is the zero-based column in the
current CodonAnalysis.final_alignment_id corresponding to column i of the
sample_alignment_id. This is the only target alignment identified by this
shape. A different preparation-stage protein concatenation cannot silently
become that target.

A non-null map requires the actual primary alignment, complete sample width,
unique in-range target columns, and explicit supplied correspondence evidence.
The map has one entry per sample column. Missing primary alignment or missing
correspondence leaves the map null and retains the sample artifact and precise
missing information. Native sampling code or a random seed does not establish
the correspondence. No partition-subset constraint is inferred merely because
the model was subsequently associated with a partition.

This states the meaning of an existing field. It adds no numerical formula,
scientific assumption, acquisition, episode action or new schema field.
