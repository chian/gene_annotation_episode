# Headerless rows and reported counts

The declared contiguous ChannelBinding ordinals define expected width for a
headerless CSV. An extra field in one data row is invalid_event_row; retain valid
bound cells at their original positions and keep the complete original bytes.
Do not infer another channel, change position bindings, or silently treat the
row as conforming. Complete headers and snapshot column arrays still require
bindings for every actual column, as clarification002 states.

Neither the declared CSV grammar nor `fluorescence_event_table_v1` has a native
total-event count field. Their Source.native_event_count is null, including for
a successfully parsed complete source. The calculator derives retained population
counts from actual Event rows. Native count means an actual reported quantity,
such as FCS $TOT; it is not another name for the parser's calculated row count.

Unrecoverable CSV quoting preserves the complete parsed prefix with partial
extent and unknown total. It does not assert that the prefix is the whole source.
These are clarifications of the existing parser contract, not scope changes.
