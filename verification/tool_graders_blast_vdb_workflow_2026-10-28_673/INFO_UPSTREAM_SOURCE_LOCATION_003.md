# Upstream formatting-source handoff

This additive record supplies the source location requested by root without
changing the original info finding, stdout, CASE, Store, receipt, or history.
Owner 678 separately acquired and investigated the exact release source; 673
did not run that acquisition or repeat its analysis.

Owner `/root/vdb_info_wrapping_678` reports terminal/quiescent rc0 for the
source-only bounded attempt
`verification/tool_graders_hmmer_map_verification_2026-10-28_529/check141_vdb_info_source678`.
Its source archive SHA256 is
`502057a88e9990e34e62758be21ea474cc0ad68d6a63a2e37b2372af1e5ea147`,
and that owner reports an official MD5 match. No native helper was executed.

The formatting implementation locations beneath that attempt are:

- `release_source/c++/src/app/blastvdb/blast_vdb_cmd.cpp`, lines 450–595.
- `release_source/c++/src/corelib/ncbistr.cpp`, lines 5088–5359.

Owner 678 reports that info uses `NStr::Wrap` with flags 0, which can split at
punctuation, spaces, or forced boundaries without an inserted marker. The
authentic rendered block can therefore represent one long token or two tokens;
a generic unique inversion is unavailable. Its proposed narrow behavior is
null plus `ambiguous_population` for both wrapped list fields while retaining
the raw lexeme, the original operands in request context, and native numeric
fields 20 / 5,000 / 250 / 250. That proposal requires root's concrete-contract
review and was not production code when this handoff arrived. It is not a
verified info repair or an operation completion claim by 673.

The exact authentic stdout remains at the `_info_text` location in
`INFO_NATIVE_TEXT_EVIDENCE_002.md`. The upstream investigation is independently
owned evidence; its future implementation and tests must retain the original
info record as the observed historical behavior.
