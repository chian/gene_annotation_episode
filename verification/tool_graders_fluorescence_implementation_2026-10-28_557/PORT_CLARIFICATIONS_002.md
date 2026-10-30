# Clarifications of frozen fluorescence ports

These resolve concrete examples raised while implementing CORE_CONTRACT_001.md.
The frozen original stays unchanged. These are implementation details within the
same two operations and shared analysis, not goal or scope amendments.

1. Malformed arguments to `issue()` raise
   `FluorescenceContractError("invalid_parameters")`. Validation of a malformed
   stored issue uses the enclosing validator's invalid_* code. No new enum is
   required.
2. A derived-domain correspondence must cover every actual prepared source row;
   it need not invent a prepared row for every original event. For original
   ordinals `[0,1,2]`, the map `[{source_ordinal:0,event_ordinal:0},
   {source_ordinal:1,event_ordinal:2}]` is legitimate. Original ordinal1 lacks
   prepared evidence, so its requested derived-domain measurement is unknown.
   If a partial prepared source retains only source row0, the mapped row1 can
   remain unobserved. For a complete prepared source, a mapping entry to a
   nonexistent extra source row is inconsistent. Every map target is a genuine
   primary-domain ordinal, and both map columns remain unique. Domain parents
   are acyclic, stay within the sample, and ultimately reach that sample's sole
   primary domain. A missing prepared cell cannot cause fallback to another domain.
3. An issue's event_ordinal may locate a failed record after the retained prefix.
   Its type is validated, but it need not resolve to an admitted Event. Other
   represented source/sample/domain/channel/gate/control joins still apply where
   those definitions exist.
4. CSV `Value.raw` is the exact decoded field value produced by the explicitly
   selected CSV dialect, before numeric conversion or whitespace handling. It
   is not claimed to include the original enclosing quote or escape characters.
   Exact lexical bytes, separators and quotes remain in the original retained
   source and the Event's byte span. Numeric conversion never overwrites raw.
5. Header/source width and names are data observations. Bindings must select
   positional columns, never infer an analyte or silently drop extra columns.
   If the actual complete header/snapshot column array has an unbound column,
   raise invalid_channel rather than silently narrowing the input. A shorter
   actual header may yield channel_missing and unavailable cells at unchanged
   requested positions. A nonnull requested native_name that disagrees with the
   actual positional header yields native_format_mismatch and no accepted rows,
   not reassignment to some matching-name column. Malformed individual data-row
   widths retain valid supplied cells at original positions with a located issue.
6. A native_report component_request may reference a population cell or an
   explicitly/implicitly requested calculated fraction, intensity or control
   cell. Native comparisons cannot target other native_comparison cells or
   themselves; reject that malformed link as invalid_native_report. A valid but
   uncomputed requested operand stays unavailable; native comparison does not
   silently commission an additional calculation.
