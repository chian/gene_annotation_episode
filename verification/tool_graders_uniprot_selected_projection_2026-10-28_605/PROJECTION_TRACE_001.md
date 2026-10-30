# Selected UniProt page projection: implementation trace

This records the P increment under `ROOT_CODING_PORTS_003.md` and
`CONTRACT_002.md` in task601. It is implementation evidence, not a goal or scope
amendment. The original supplied user attachment remains authoritative.

## Owned implementation

`gene_annotation_episode/uniprot_return_projection.py` exports the exact frozen
`project_uniprot_page` port. Its only application dependency is C's
`uniprot_return_contracts` schema/selection module. It creates a detached
`PageReply` from an already authenticated publication, retained native bytes,
outer status/count/issues, explicit original page selection and supplied selected
sequence bytes. It calls no native parser, acquisition, Store, receipt, model or
scoring function. Explicit grants are data descriptors; this function performs
no material admission.

The existing native parser supplies integer measurements, sequence lengths and
reported-length conflicts, endpoint values/modifiers, exact feature intervals,
sequence associations, database/identifier pairs and evidence tuples. Retained
native JSON supplies explicitly selected leaves and original collection
membership/positions, including malformed members omitted from the parser's
typed item arrays. Original array ordinals are never replaced with filtered
indices. Unicode text offsets count decoded code points.

## Selection and provenance decisions

- Record all/ordinal/exact-primary selectors retain each original requested
  clause. Distinct overlapping clauses produce distinct replies; page counts
  deduplicate actual ordinals. Duplicate native primary accessions all match.
  A malformed or missing native primary identity produces an explicit
  `unavailable` record reply with `record_selection_indeterminate`, preserving
  its original ordinal. Secondary accessions never satisfy primary selection.
- Native parser-ineligible, binding-omitted and outside-response rows have no
  fabricated reference witness. Their requested fields remain explicit null
  unavailable replies. Page native, parser-eligible and actual binding counts
  preserve their different meanings.
- Feature overlap uses P's exact interval and entry-sequence association.
  Explicit other-sequence and disjoint exact members are excluded; fuzzy,
  unresolved, invalid and malformed candidates remain indeterminate. Missing
  entry sequence and queries beyond its measured length are unavailable.
- Database selection compares the exact native database. Missing/null/invalid
  databases and malformed native members remain indeterminate. Each selected
  property key returns every matching original property and its exact requested
  text window; undecidable native property keys retain a separate count.
- Evidence joins the original owner pointer, local ordinal and complete native
  evidence pointer. Associated evidence includes arrays owned by the selected
  feature/xref or descendants, preserving each actual owner. It does not promote
  property/start-position evidence to the enclosing feature/xref. Valid arrays
  survive another null/invalid container while total membership becomes unknown.
- Native absent collections have zero native members; null/invalid collection
  sizes remain unknown; present empty arrays remain available. Selected ordinal
  requests beyond a present collection create no invented native member.
- Native token syntax failure preserves native `present` while representing
  the token as unavailable. ECO and EC forms retain their specific grammars.
  Feature sequence-ID omission retains P's explicit default-entry meaning.
- Native page issues use their original page-array index; bound native record
  issues use their record-array index; selected unbound issues use the original
  publication issue index. Outer errors and qualifications preserve their own
  origins and indices. Unselected issues contribute only to their count.
- Page digest uses the execution boundary's canonical JSON convention: sorted
  keys, compact separators, UTF-8 without ASCII escaping, finite JSON only.
  Witness IDs have no grant effect. Requested sequence bytes must exactly match
  P's retained entry sequence and actual artifact digest before returning a
  sequence window or full-sequence artifact descriptor.

## Consumer and authority inspection

Read the complete native/parser/publication modules and the actual
`ToolRegistry._import_uniprot` publication path. Read task597 P/B handoff003,
task601 contract002, exact schema002 and coding ports003. Read AGENTS.md, the
original supplied goal, all ten operating principles, grader responsibility
instructions and the relevant fixed UniProt inventory rows. Read C's concrete
selected-value validators while aligning the pure PageReply.

Existing host results, communication wiring, receipt authentication, forwarding,
closed replay, execution, model-facing presentation and access consumers remain
outside P's ownership. This increment is not full UniProt or R6 completion and
does not change completed-tool counts or historical acquisition observations.

## Verification boundary

Host checks performed: stdlib AST parsing, source/JSON inspection, hashes and
whitespace inspection. No application import/test, provider request, native
scientific computation or HPC job ran on the host. Root owns all application
testing in the bounded runner: 20 GiB RAM, 4 GiB scratch, zero swap, no wall cap.

`tests/test_uniprot_return_projection.py` consumes the retained authentic
`tests/fixtures/uniprot_native/P0AAW1.json` (253 residues, 42 cross-references)
and controlled explicitly labelled cases. Ordinary projected fixtures are also
checked by C's aggregate semantic validator. The focused cases cover native
ordinals, Unicode windows, missing/null/invalid/empty states, duplicates, binding
omissions, selected GO properties, feature membership, local evidence owners,
sequence windows, descriptor-only grants, headers and integrity conflicts.

Root's bounded-run outcome is recorded separately when available. This source
trace makes no passing-runtime or integrated-return claim on its own.
