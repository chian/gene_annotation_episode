# Controlled-response source fixture

`controlled_response_source_case.json` is a reusable engineering input for A106
reader tests, not a scientific observation or a saved execution result.

It holds one `same_B_text_graph` selection in the current selection form, the
three source bodies that selection cites (including the constructed graph
image) and the covariance source text. Source bodies are hex encoded to
preserve their exact bytes and witness offsets.

The test helper registers those sources and remaps their references. It then
calls the actual reader and repository. The resulting score components must
remain inference results when selected through scoped keys such as `final:...`.
