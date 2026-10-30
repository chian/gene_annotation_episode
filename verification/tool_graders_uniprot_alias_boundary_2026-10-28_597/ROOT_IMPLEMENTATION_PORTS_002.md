# UniProtKB parser and publication implementation ports

Additive implementation contract, 2026-10-28. The original user-entered goal is
unchanged. BOUNDARY_001.md and PROPOSED_CONTRACTS_001.json are preserved proposals.
This review freezes only the P/B implementation handoff below. The broader R6
provider and alias obligations remain open.

## Authorized increment and independent ownership

P owns new `gene_annotation_episode/uniprot_native.py` and
`gene_annotation_episode/uniprot_native_contracts.py`, only the existing
`parse_uniprot` and `uniprot_pagination` compatibility functions in
`acquisition.py`, and new parser tests. The contract module contains the native
parser and publication schemas required by P/B, not the proposed return facts.

B owns `api_uniprot.py`, the UniProt-specific acquisition/publication and partial
result handling in `tools.py`, new `uniprot_publication.py`, and focused
service/publication tests. B may correct relevant existing UniProt test fixture
inputs when they omit actual transport/request fields; do not weaken assertions
to hide a production defect. B does not edit `acquisition.py` or P's modules.

P and B can code concurrently against these ports. P performs no acquisition,
Store writes, model calls, or scoring. B reuses the existing PublicClients and
`publish_existing_acquisition` path. Root owns integration verification.

The alias remains an API resource-child operation. Its substantive capability
description/instructions must reach the existing operation-contract discovery
route. Do not add a direct root acquisition tool, a natural-language query
generator, an automatic page loop, or another execution layer.

## Frozen function signatures

P exports:

```python
normalize_query_uniprot(endpoint: str, *, max_results: int | None = None) -> dict
parse_uniprot_native(content: bytes, *, request: dict | None,
                     response_headers: dict | None) -> dict
validate_uniprot_projection(parsed: dict) -> None
legacy_uniprot_records(parsed: dict, content: bytes) -> list[dict]
```

B exports from `uniprot_publication.py`:

```python
bind_uniprot_publication(parsed: dict, *, source_ref: str,
                        native_artifact_ref: str,
                        references_by_ordinal: dict[int, dict]) -> dict
```

`references_by_ordinal` maps each publishable original row ordinal to the actual
stored reference record created by B. B verifies the stored sequence artifact
bytes against P's full sequence value before binding. The pure binding function
checks identity, source, accession, sequence presence/length and ordinal
relationships; it neither reads artifacts nor invents missing references.

## Native shape corrections to the preserved proposal

Use the proposed ParsedPage, NativeRecord, field, feature, evidence, cross-reference
and Publication shapes with these explicit corrections:

1. `Page.effective_request` also permits null. `request=None` means the original
   request is unknown. Never fabricate a query/accession from the response.
   `Page.operation` additionally permits `unknown`, and `selection_extent`
   permits `not_established`, for an unusable envelope without a known request.
   A valid envelope can establish record/search shape without proving the
   original request. Such rows retain unverified correspondence and the existing
   `native_request_unverified` qualification. B always supplies the actual
   canonical effective request for new bound acquisitions.
2. `NativeRecord` additionally requires `legacy_projection`, a closed object
   with `source_name: TextField` and `source_ec_numbers: array[TextField]`.
   These are native source labels, not proposed annotations for the target.
   P alone selects the existing recommended-name then submission-name source
   order used by the current parser, retaining exact source pointers and values.
   This preserves current reference/term publication while the full original
   proteinDescription, including alternative names, remains retained.
3. `legacy_uniprot_records` checks content_sha256 before resolving native
   section pointers. It returns the existing parse_uniprot keys using P's
   parsed identity/sequence/taxon/legacy values and verbatim native section
   contents. It does not independently re-evaluate field types, accession
   correspondence or numerical meaning. Valid records survive malformed
   siblings; their native ordinals remain in the canonical parsed output.
4. Complete native sequence/text stays in internal storage. No arbitrary
   truncation is permitted. This does not authorize returning a full sequence
   or unrestricted text in an episode form or prompt.

Expose the native/publication schema constants from the P-owned contract
module as `PARSED_PAGE_SCHEMA` and `PUBLICATION_SCHEMA`. B imports those and
P's functions rather than copying a schema/parser. P must supply complete local
definitions needed to resolve each schema. Do not install the proposed
fact_source_schemas, example_parent_form, or new communication namespaces.

## Required semantics and verification

The exact endpoint, alias, selected size/cursor, one-page semantics, native
field-state meanings, coordinate conversion and partial-row rules in
BOUNDARY_001.md apply. `max_results=None` is omission; a supplied 1..500 value
means selected search page size, not post-response truncation. Conflicting
explicit sizes fail before transport. Unsupported endpoint/format/parameter
variants remain explicit unfinished modes, never silently substituted.

Primary/secondary correspondence compares exact native values. A secondary
accession match is not globally unique: separate returned primary entries can
share it after a split. Preserve all original record/feature/evidence/xref
ordinals and native pointer relationships. Missing transport evidence remains
unknown. A later page or short page is not proof of whole-query completion.

Only valid full sequence bytes can create a sequence artifact. Preserve a
reported-length conflict. Native coordinates remain 1-based inclusive; a
derived zero-based half-open interval requires exact compatible sequence and
endpoints. Invalid/fuzzy/alternative-sequence locations are preserved without
inventing an interval. Citation/ECO repetitions are not independent experiments
or confidence scores.

B retains the original source before projection and publishes valid rows from
a partial page. Attach `result.uniprot_publication` to the existing outcome;
surface structured projection errors through the existing partial-result
mechanism. No parallel publication store, new acquisition receipt, added action,
changed credit formula, or retrospective rewrite of closed outcomes.

Verify primary and secondary matches; unmatched and unknown requests;
malformed later records; field-level invalid/missing/null/empty values;
full sequence and length conflicts; exact/fuzzy/other-sequence features;
nested evidence ownership; xref properties; selected-page headers and malformed
links; alias size/URL failures; no implicit calls/pagination; publication equality;
original operation replay; and existing source/sequence consumer compatibility.
Use the retained authentic P0AAW1 response and clearly labelled controlled
fixtures. No new API/HPC/auth requests in this increment.

## Boundaries still requiring work

R typed return integration is not frozen by this contract. The proposed fact
schemas reuse unrestricted TextField and full SequenceData values. They must be
replaced by explicit selected return projections before implementation, while
complete native data remains retained. Do not call valid long source text
invalid merely to fit a display. Existing acquired-result receipt custody and
requested-only admission remain mandatory. A separately reviewed model-facing
template is also still required; no prompt changes are authorized here.

UniRef, UniParc, the other endpoint/format variants listed in BOUNDARY_001.md,
typed child/parent delivery and any required live-resource verification remain
unfinished. This increment does not complete the UniProt provider row or R6.

All application imports, tests and native computation run through root's
existing bounded 529 runner (20 GiB RAM, 4 GiB scratch, zero swap, no wall cap).
Workers may inspect source and use stdlib AST/JSON on the host. Before work read
the original user attachment in full. After substantive source/native-document
work or each logical tool implementation, reread its objective and all ten
operating principles verbatim; reread this contract before handoff. Never read
GOAL.md or create a goal/scope-amendment file.
