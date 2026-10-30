# E native-version and unrepresentable-symbol corrections

Additive to E001, accepted009 and DECLARED_FORMAT_BINDING_010. Root inspected the actual E resolution/projection functions, XMFA parser/version and coordinate branches, v4 header/version handling, and D slot-resolution invariants. Preserve the two original failing fixtures recorded by worker157.

## Actual native version

A nonnull parsed document is not proof of supported format. An XMFA document whose effective `format_version_token` is not `Mauve1`, or a v4 document whose effective native format-version declaration is not 4, stays retained with its native diagnostics but cannot resolve a supported-format slot. Use the existing `artifact_format_conflict` requirement/diagnostic, incompatible slot and null resolved `document_id`, matching D's existing invariant. Preserve the ParsedArtifact and all native content. Do not infer a missing version, try another parser, or discard independent supported slots. A structurally partial document with the supported version can still supply independently valid measurements.

## Selected malformed native symbol

The native XMFA document and D coordinate correctly preserve `?` from a malformed input as an incompatible coordinate. E's existing outward DNA-symbol grammar cannot represent that character. Do not rewrite it, widen the grammar, discard other requested facts, or raise a whole-publication schema failure for this known local native defect.

For this precise selected native-coordinate case, return `SelectedFact.state=incompatible`, `value=null`, retaining original request/document identities and requirement references. Add the finite E diagnostic/requirement reason `bvbrc_genome_alignment_bundle_projection_target_incompatible` with `kind=parser_binding`. Use this distinct reason rather than saying the present malformed target is missing. Native text and the full D coordinate remain unchanged in the saved sheet. Other coordinate selectors and independent numeric selections retain their own values and qualifications. Status remains partial when a requested scientific target is incompatible.

The test is the explicit symbol-domain incompatibility in a saved native-coordinate target, not a blanket catch of schema, identity or programming errors. Saved projection validation must reproduce the same finite result without native parsing or scientific calculations. Test the unsupported/missing/conflicting version cases, the malformed-symbol case beside an independent valid requested field, exact original value retention, and rejection of unrelated saved-value corruption.
