# Accepted XMFA source-binding workload and handoff correction

Additive record, 2026-10-25. Root owns new `xmfa_sources.py`,
`xmfa_source_contracts.py`, `tests/test_xmfa_sources.py`, and
`verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/`. No existing
production files, parser-owned files, or permanent records are changed.

Root's message telling the parser coder to omit `XMFAMetadata.integer_value`
was wrong and is retracted. It was based on a draft read before final freezing.
The accepted contract SHA256
`f6ebf5348d260c2f84b6cf3d245a050a329b0fd670aa237a4a769f340943f701`
includes both `value_token:str` and `integer_value:NativeNumber|null`.
The seven-key metadata schema remains unchanged. Root subsequently reread the
entire hash-matching frozen contract. Add native diagnostic
`xmfa_metadata_integer_invalid` for an invalid SequenceNEntry value. This
supplements clarification009; it does not overwrite any earlier instruction.

Implement `bind_xmfa_sources(document, *, inputs, source_comparison)` and the
matching detached validators for XMFASourceInputs, XMFASourceBindings and
XMFAOriginalMap exactly as frozen. Inputs are the accepted native XMFADocument
and explicitly supplied source records/invocation/path evidence. Outputs retain
all native members, physical-record source checks, exact source strings,
component intervals and supplied original maps. No file/network/native I/O is
performed. Source comparison is exactly case_insensitive_iupac_exact, preserving
the original text and returning the actual mismatch columns. A source interval
outside the supplied source is not clipped or compared partially.

Consumers are the four accepted XMFA coordinate/statistics/coverage functions
and the MSA sheet extractor. Coordinate consumers must cross-check saved source
checks against the current supplied document and stored source sequence; a
saved match label is insufficient. Additional `validate_xmfa_bindings_for_document`
performs that ordinary deterministic relationship check without acquisition.
Original map lengths and evidence remain independent from native coordinate
facts. Known source membership is not a calibrated annotation probability.

Missing exact File/Entry/path/invocation/ordered-record information retains a
missing/conflicting member and an explicit requirement. It never chooses a
basename/header/taxon match. Original maps are optional; their absence alone
does not invalidate native member/source binding. Their conflicting overlapping
mappings to the same original occurrence remain recorded and qualified; distinct
original occurrences remain distinct. Partial source record populations cannot
be promoted to complete source denominators. Known input failures and malformed
closed operands stay different failure channels.

Verification uses the accepted combined/separate native examples and supplied
original FASTA data; checks source lengths50/41/49, every plus/minus source span,
zero records, mismatches, exact path/Entry relationships, duplicate/conflicting
metadata, unknown invocation/partial inputs, source concatenation boundaries,
repeated original occurrences and invalid/partial original maps. Saved bindings
must validate/replay with I/O and native parsing disabled. These checks do not
claim original live BV-BRC task custody or complete episode integration.
