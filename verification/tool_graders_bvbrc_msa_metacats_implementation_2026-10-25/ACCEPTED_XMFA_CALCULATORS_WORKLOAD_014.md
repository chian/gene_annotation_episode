# Accepted pure XMFA coordinates and numerical components workload

Accepted for a fresh coding worker, 2026-10-25. The complete frozen boundary is
`../tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/PROPOSED_CONTRACT.md`,
SHA256 f6ebf5348d260c2f84b6cf3d245a050a329b0fd670aa237a4a769f340943f701.
Read that entire contract and accepted root records008,009,010 before coding.
The parser and source binder are independent supplied dependencies, not owned
files. No provider, adapter, episode, credit or resource behavior is in scope.

Own only new production files `gene_annotation_episode/xmfa_coordinates.py`,
`gene_annotation_episode/xmfa_calculators.py`,
`gene_annotation_episode/xmfa_calculation_contracts.py`; tests
`tests/test_xmfa_coordinates.py`, `tests/test_xmfa_calculators.py`;
and new additive verification directory
`verification/tool_graders_bvbrc_xmfa_calculators_2026-10-25/`.

Implement all four exact signatures from section4:

```python
xmfa_column_coordinates(document: dict, *, cells: tuple[dict,...],
    bindings: dict | None) -> dict
xmfa_source_positions(document: dict, *, queries: tuple[dict,...],
    bindings: dict | None) -> dict
xmfa_alignment_components(document: dict, *, selection: dict,
    selected_pairs: tuple[tuple[int,int],...], case_policy: str) -> dict
xmfa_interval_coverage(document: dict, *, selection: dict,
    bindings: dict | None, basis: str) -> dict
```

The first two belong in xmfa_coordinates; the last two in xmfa_calculators.
Implement detached validators `validate_xmfa_coordinates(value)`,
`validate_xmfa_inverse_coordinates(value)`, `validate_xmfa_selection(value)`,
`validate_xmfa_alignment_components(value)` and
`validate_xmfa_coverage_components(value)` in xmfa_calculation_contracts.
Caller functions also cross-check operands against the supplied native document
and `validate_xmfa_bindings_for_document` before consuming saved source matches.
Do not duplicate native parsing or source association. Any additional helper
fits the same owned files and performs no I/O, model call or native execution.

Exact records, formulas, method IDs, diagnostics, failure states and test cases
remain sections4–6 of the frozen contract. This additive serialization
clarification fixes coverage units: source_length, original_length,
known_union_bases, multiply_represented_bases and complement_bases use
`nucleotides`; placement_bases and excess_placement_bases use
`nucleotide_placements`; all fractions use `fraction`. Alignment width/pair
counts use `columns`, member counts `members`, literal site-symbol/gap/nongap/
canonical/ambiguity/other counts `characters`, entropy `bits`. Population and
method IDs follow the frozen contract; these are not confidence scores.

Preserve the four levels: literal aligned cells; native member coordinates;
validated supplied source-record coordinates; optional original occurrence
coordinates. Missing source maps do not erase native/literal measurements.
Unusable or duplicate selected rows cannot improve a denominator by disappearing.
Original-map conflicts stay qualified, and distinct original occurrences never
collapse. Repeated placements retain their individual records before union.

Numerical examples include all six combined native blocks and separate native
files, the first-block 39 identical/7 substituted canonical positions out of46,
the three distinct coverage bases, subset-column invariance, all inverse
placements, plus/minus endpoints, concatenated-record/original-map boundaries,
zero/omitted members, conflicting records/maps, repeated/triple overlap,
partial/truncated documents and unknown source lengths. Preserve complete saved
operands/results and demonstrate exact recalculation with native parsing and
I/O disabled. The producer and service are not rerun. Final provider integration
will consume these exact records and copy only requested typed facts.
