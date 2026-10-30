# Final004 stabilization

The first unmatched-angle check in hardening003 incorrectly treated an earlier
numeric comparator anywhere in the full source prefix as an unclosed tag. The
original nominal selection consequently failed in two connected tests; that
failure and failed demonstration003 are preserved. FOCUSED_FINAL_TESTS_003.log
records 593 passes and two failures. They are not final passing evidence.

The corrected check recognizes a syntactic partial opening-tag fragment only:
`<(?:[A-Za-z_][^<>\n]*)?$` immediately preceding the nearest `between`.
An earlier `<0.01` is not a tag name and cannot veto the later allocation. A
newline also ends this partial-tag candidate. This changes no source/context
bytes or context-reader function. An additional explicit synthetic regression
checks that earlier-comparator contrast on both routes, alongside the complete
original witness integration checks.

All other hardening002 semantics remain. Final004 supports only its exact full
dependency dictionary and released027's original dictionary. Demonstrations001,
002 and the failed003 state remain intermediate facts; no intermediate
dependency identity is silently accepted as a release.

Final production/test byte identities and the complete owned delta are
SOURCE_MANIFEST_003.json and SOURCE_DELTA_003.patch. Final connected terminal
results are FOCUSED_FINAL_TESTS_004.log. The new successful controlled ordinary
nominal demonstration is CONTROLLED_NOMINAL_DEMO_004.json. The complete
literature goal, actual model amount extraction, supplement reading, active
amount/response correction and final annotation aggregation remain unfinished.
