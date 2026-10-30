# Accepted B2/B3 construction workload

Root owns new `bvbrc_proteome_joins.py`, `bvbrc_proteome_sheet.py`, their separate
test files, and a new construction verification directory. A native parsing,
B0/B1 input extraction, B4 calculation and shared saved-sheet validation have
separate owners. No shared execution, registry, prompt or scoring file belongs
to these constructors.

Implement the exact `build_native_joins` and `build_native_sheet` signatures in
proposal001, with correction002 and B1_PARAMETER_SOURCES_002 authoritative for
their respective corrections. Inputs are validated A/B1 values and explicit
closed link shapes from DATA_SHAPES_PROPOSAL_002. Output envelopes are exactly
NativeJoinsResult and NativeSheetResult. The functions call the shared data
validators; B4 consumes the resulting NativeSheet. They do no acquisition,
execution, Store/custody access, LLM work or aggregate score calculation.

Construction decisions, made explicit before coding:

1. Preserve every raw requested execution/native/metadata link. Malformed global
   contract data returns invalid with a fixed failure. A well-formed but wrong
   link has a local conflict/unmatched result and scoped diagnostic, preserving
   other usable input and native measurements.
2. Track-input bindings derive only from the original indexed parameter slots
   and supplied explicit links. No label, sorted list or matching taxon supplies
   a join. Missing/skipped native track indices keep their original identity.
   Conflicting input/inventory links cannot produce an admitted inventory.
3. Native ID links require the correct source/digest/selector and original
   track inventory, exact case-sensitive native/header ID, one matching record
   occurrence in that inventory, and no colliding ID among participating input
   occurrences. Duplicate requests for the same proved relation do not create
   multiple biological occurrences. Preserve rejected link indices and candidates
   through raw requests, joined-result fields and scoped diagnostics.
4. A known identifier may link an incomplete or invalid-sequence occurrence.
   The link describes identity, not complete sequence validity. Compare native
   length only with a complete valid stop-free supplied sequence when both
   quantities are available. A missing native length does not invalidate ID.
   Do not guess how native length treats a supplied stop symbol.
5. Metadata links use the explicitly selected rows and relevant identity,
   genome-ID, MD5 and actual sequence relationships. A bad unrelated numeric
   field does not erase a sound identity relation. Multiple source assignments
   stay distinct. Missing requested sequence/genome relationships remain local
   missing/conflict outcomes, not inferred metadata.
6. Complete normalized sequence equality creates full-sequence groups only
   among valid complete occurrences. IDs/MD5 labels alone are insufficient.
   Complete invalid or empty strings still have known input symbol counts;
   copy those counts as input symbol counts, never call them protein lengths or
   use them for native-length comparison or executed denominators.
7. Correction002 remains in force: locator-only exact-execution and producer
   occurrence claims remain unqualified. Actual executed denominators and
   complete executed membership are unavailable until the missing decoded
   witness interface exists. Native values, descriptive counts and valid ID
   joins remain usable. This is not the final intended capability.
8. B3 selects only the caller's exact primary source. Keep alternate projections
   separately, with explicit ordinal/association correspondence. Compare actual
   cells under those mappings; do not merge or replace primary values. Preserve
   conflicts and incomplete correspondence without calling two representations
   independent evidence. A nonprimary invalid artifact remains retained.
9. B3 copies numeric/native cells exactly, attaches coherent declared joins,
   known input symbol counts and explicit missing states. An uncertain TSV
   column layout cannot supply trustworthy semantic numeric cells. A bad
   neighboring scalar in JSON does not erase other located values.
10. New code retains full report/witness requirements. Full directional reports,
    real native service data, application/library integration and whole-episode
    verification remain separate required work, not silently completed by
    useful legacy summary arithmetic.

Verification uses actual A/B1 functions over explicitly synthetic supplied
fixtures, independent exact count/identity expectations, malformed links,
duplicates/collisions, incomplete inputs, conflicting lengths/metadata,
representation mismatch/reordering, source mutation and pure no-IO construction.
Then compose B3 with the separately implemented B4 calculator and confirm that
changing parameters preserves native/source data. No full tool completion is
claimed from this constructor workload.
