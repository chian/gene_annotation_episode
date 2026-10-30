# Correct generic text custody before final070/071 implementation

Root review found a real006 declaration defect. AUTH_WITNESS.locator allowed
only JATS-paragraph or image-region locators, while generic text meanings are
selected by exact UTF8 source spans. The provisional070 implementation encoded
these as kind=jats,section_id=exact_utf8_witness,paragraph_index=0. Those are
invented paragraph facts, not actual source records. This must not be accepted
or frozen as successful source custody. No numerical source meaning changes.

The new normative declarations are text_locator_declarations_008/INTERFACE_008
and its four SCHEMA_008 files, built by build_text_locator_008.py. Original067
and all previous root/prototype outputs remain unchanged. This is additive
pre-acceptance correction, not migration of a genuine deployed native workflow.

The exact new generic locator is a CLOSED object with ALL fields:

    kind = text_span
    source_ref, artifact_ref
    representation = original | text
    start, end = actual nonempty half-open UTF8 byte span
    quote = exact decoded source bytes at that span

It is an additional alternative ONLY for authenticated witness locators.
Selection witnesses already contain their actual coordinates; enrich them with
the real artifact from the callback. Preserve representation/start/end/quote
exactly. No fabricated section_id, paragraph_index, paragraph_text or offsets.
authentication=exact_utf8_span and attribution=literal_source_record retain
their existing meanings. Actual source availability still governs nullable
locator/authentication/diagnostics. Source row/hash consistency and byte-span
length/order must be validated on saved reads without reacquisition.

Advance extraction to relative_signal_source_extraction_v3 and the native
payload/source version to literature_relative_signal_source_record_v3. Request
selection stays v2; numerical sheet stays v2; typed return remains EXACT006.
The calculation artifact's numerical version stays v2 with the actual input
extraction hash. The operation/provider/namespace/components, public APIs,
constructor fixture-origin binding and closed payload field names stay exact.
No genuine older native v2 deployment is claimed; earlier070/071 prototype
fixtures and recorded failures stay historical and are not rewritten in place.
Existing original ratio-v1 behavior and all frozen scientific runs remain intact.

The root builder proves that reversing ONLY the new locator alternatives and
extraction version reproduces006 exactly. REQUEST/SHEET/RETURN are byte-identical
to006; all4 schemas are meta-checked. No whole old schema is silently simplified.
070's compact production-owned constructors must match new008 exactly and must
not import root verification artifacts.071 must bind the new saved version and
use actual final070; no mock or pre-correction pin can establish the final path.

Root also clarified candidate distinctness before acceptance: compare COMPLETE
nominated numerator/reference witness pairs. Identical numbers at distinct
regions are distinct nominations; equal numbers neither establish physical
identity nor remove an explicitly ambiguous/conflicting reading state. Exact
duplicate pairs cannot satisfy alternate-candidate cardinality. Preserve all
original candidate geometry and source associations.

070/071 retain exclusive production ownership under their original releases.
Preserve meaningful earlier source identities/test results. Add targeted tests
for genuine generic spans from HTML/text (including Unicode byte coordinates),
unchanged actual JATS paragraph locators, invalid invented JATS fallback in a
generic witness, wrong artifact/representation/span/quote and source-free saved
validation. Re-run affected joined tests from ONE coherent final generation.
No source science, model result, new axis/episode, observation, target transfer
or W05 credit is created by this correction. All broader goal work remains.
