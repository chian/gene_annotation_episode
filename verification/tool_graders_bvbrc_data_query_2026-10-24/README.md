# BV-BRC D1 query preparation verification

This directory records implementation and verification of the frozen D1 pure
query/field interface. It does not establish service execution, scientific
scoring or episode communication integration. No network request or job was
submitted. The original goal and frozen contract remain unchanged.

`REPORT.json` records the exact test commands and outcomes. `SOURCE_HASHES.json`
retains input, implementation and verification hashes. `PREPARED_EXAMPLES.json`
contains seven complete prepared requests. Production imports neither this
directory nor the design documents.

The final focused and legacy command was:

```text
.venv/bin/python -m pytest -q tests/test_bvbrc_data_query.py tests/test_api_bvbrc.py
203 passed in 2.34s
```

A separate fresh Python process passed with an audit hook prohibiting files,
network, native process execution and database connections after import:

```text
.venv/bin/python -m verification.tool_graders_bvbrc_data_query_2026-10-24.verify_fresh_process_purity
```

Examples actually prepared, without execution:

- An omitted-fields `genome` page selects `genome_id`, sorts `genome_id asc`,
  and requests rows 25/start 0. Its population key is
  `da7697ee66e697429992633a107205b30a8ead5c8af8f096d9be6008bebdb948`.
- Selecting `aa_length,product` for `genome_feature` appends `feature_id` for
  custody. Sorting `aa_length desc` appends `feature_id asc`; both additions are
  recorded separately from the original request.
- Membership count and annotation facet URLs equal the retained native requests
  byte for byte. Their historical responses report 2 matching documents, with
  `PATRIC:1`, `RefSeq:1` and missing `null:0` facet buckets. These are old native
  observations used as request oracles, not newly acquired D1 responses.
- Strict lower bound 4,639,675 with no upper bound compiles to
  `genome_length:{4639675 TO *}`. Legacy RQL `gt`/`lt` behavior is untouched.
- Negative expression literal -2.5 compiles to `log2_fc:"\-2.5"`. The stored
  original operand remains numeric -2.5; it is not rescaled or reinterpreted.

All 318 registry entries match the frozen contract and the selected native schema
fields. Native numeric identifiers remain metadata. This is not live verification
of 318 populated measurements. Special-character, mixed/open range, failure and
type cases are labeled synthetic tests. Date ranges and analyzed text equality
remain unsupported. Stable sorting does not establish a snapshot across calls.

Exact production exports:

```text
bvbrc_data_fields:
  FIELD_CONTRACT_VERSION, COLLECTIONS, FIELD_REGISTRY, SELECTABLE_FIELDS,
  NUMERICAL_FIELDS, METADATA_FIELDS, MOLECULAR_MEASUREMENT_FIELDS,
  SUPPLIED_METADATA_FIELDS, UNAVAILABLE_REASONS, ISSUE_CODES
bvbrc_data_query:
  DATA_QUERY_SCHEMA, PREPARED_DATA_QUERY_SCHEMA, COMPILER_VERSION,
  validate_data_query, encode_native_query
```

`validate_data_query(request: dict) -> dict` returns a detached finite original
with omissions, values and order preserved. `encode_native_query(request: dict,
*, base_url: str, page_selector: dict | None = None) -> dict` returns exactly the
frozen PreparedQuery. Public schemas retain the frozen syntax via local `$defs`;
semantic validation adds actual collection membership, capability flags, strict
integer types, bound relationships and mode restrictions. Failure codes are
stable `ContractError` values from the frozen list.
