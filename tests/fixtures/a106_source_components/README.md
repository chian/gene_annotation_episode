# Controlled-response source fixture

`controlled_response_source_case.json` is a reusable engineering input for A106
reader tests, not a scientific observation or a saved execution result.

It retains the `same_B_text_graph` selection from case 0 of
`verification/literature_reference_evidence_2026-10-25_001/a105_controlled_full_source_design_069/CONSTRUCTED_SOURCE_CASES_001.json`,
the three source bodies from that directory's `CONSTRUCTED_SOURCE_ROSTER_001.json`
(including `CONSTRUCTED_GRAPH_001.png`), and that case's covariance source text.
Source bodies are hex encoded to preserve their exact bytes and witness offsets.
The tests use only this fixture; they do not require the historical directory.

The test helper registers those sources, remaps their references, and adds the
empty collections required by the current v3 selection schema. It then calls
the actual reader and repository. The resulting score components must remain
inference results when selected through scoped keys such as `final:...`.
