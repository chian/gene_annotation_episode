# Exact declared-format interpretation for the E facade

Additive to accepted009 and E001. A reader dialect, an algorithm recipe, a
file-format version and a provider schema revision are different fields. The
inspected backbone/BBCols files have no native format-version marker. Their
explicit parser dialect names do not become native version or mode values.

The currently supported declared-format combinations are:

| format | version | mode |
| --- | --- | --- |
| mauve_v4 | null or "4" | null |
| mauve1_xmfa | null or "Mauve1" | null |
| mauve_backbone | null | null |
| mauve_bbcols | null | null |

The selected DocumentSlot still provides the exact reader/dialect/encoding.
Null declared version does not certify a version: the selected native parser
checks its actual header/grammar. Mauve v4 and XMFA contain the named native
version markers; the two sidecar dialects have their own explicit structural
contract. The original application recipe remains separately in OriginalTask
and recovered invocation information; it is not copied into format.mode.

No accepted nonnull artifact mode vocabulary exists for these four formats.
A different nonnull version or mode is unsupported by this facade: retain the
artifact and original declaration, mark its selected slot incompatible, and
report bvbrc_genome_alignment_bundle_artifact_format_conflict. Do not erase or
rewrite the declaration, try another parser, infer version from suffix, or
pretend that a dialect string is a native version. Independent other slots
remain eligible. Later actual version/mode support requires a concrete source
definition and its own additive contract; it is not silently generalized here.

This controls E reader selection only. It does not change A/B/C stored value
shapes or add a runtime approval/acceptance mechanism.
