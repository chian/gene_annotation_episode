# D5 BV-BRC selected return values

Implemented the six frozen pure functions in `bvbrc_data_views.py`: source
descriptors, selector validation, selected fact projection, exact identifier
membership, whole-return validation, and receiver materialization. All frozen
exports are present. The additive supplied-metadata correction002 and explicit
unavailable-return correction003 are applied; the original planning JSON was
not rewritten. Production imports code-owned schemas and reads no verification
or documentation files.

The module requires host-qualified inputs. JSON qualification flags in these
tests are explicitly hypothetical host fixtures, not proof of acquisition,
input custody, receiver possession, or a successful child-delivery attempt.
The module checks exact selector and input bindings, selected row/cell membership,
native-number relationships, supplied JSON Pointer locations, automatic units,
and whole requested fact arrays. Fact `collection` identifies the publishing
source; materialized cells identify their actual input source and collection.

`python3 -m pytest -q tests/test_bvbrc_data_views.py` passed 85 tests in 5.96 s.
The schema owner also ran the combined schema, D1–D5, and existing communication
suite: 651 tests passed in 14.63 s. Its actual output was inspected at
`../tool_graders_bvbrc_unavailable_facts_2026-10-24/PYTEST_MODULES.txt`.
No live request, job, model call, new observation or credit was created by D5.

Filled examples in `FILLED_RETURNS.json` include:

- Native-derived count 2 with zero returned document rows, facet fractions
  0.5/0.5 and a native missing-term bucket of count 0.
- Four feature/sequence relations across two distinct feature IDs, with AA
  length 253 and lowercase NA length 762.
- Native-derived log2 fold change −0.129 and z-score −0.556, preserving
  `glucose`, the exact empty bioset duration string, and `Microarray`.
- A clearly synthetic supplied Unicode unit delivered automatically with its
  requested number, plus exact supplied null and empty-list values.
- Explicit failed no-sheet page/count results, without invented zeros.

The facet fixture uses the frozen native-derived sheet. The count test parses
retained native response bytes. Feature and molecular tests copy retained native
array values into explicitly synthetic Solr envelopes, then use the actual pure
readers/extractors. None of these fixtures establishes a new v2 network request.
Malformed/partial data, missing requested IDs and ordinals, wrong relationships,
duplicate occurrences, bad selectors, altered returns, unsupported references,
and no-I/O/input-immutability behavior are tested separately.

Root-owned host qualification, durable admission, replay/receipt accounting and
actual receiving episode inputs remain integration responsibilities. No saved
provider request was produced by this workload. `render_bvbrc_received_values`
is expressly absent: model-facing rendering and steering insertion await the
user's feedback on the draft. No placeholder renderer was installed.
