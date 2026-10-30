# Demonstrated failure-location identity gap after005

The123-test run is terminal and passing. A separate actual P saved-validation
probe constructed a null result with an original format_incompatible diagnostic
whose source_ref was synthetic_source_pathways and document_id was pathways,
but whose SourceLocation.raw_artifact_ref was unbound_artifact. The other fields
and original task/parameters/bundle were valid. Current validation accepted it.

This is a005 record-identity gap: source existence alone does not prove the
source/artifact/document relationship. No parser or scientific calculator is
needed to check the original declared pair and document selection.

The bounded correction will build source/artifact pairs from original bundle
artifacts, supplied content/evidence, exact possessed document selections,
producer selections and declared reference source locations. A location must
match an original pair. If it names a document, its pair must belong to that
document's exact original selection (including requirement_id matches).

Explicit missing requested bindings may still support a diagnostic about that
input; this equality check does not grant possession or resolve native bytes.
Existing shape validation still checks JSON-pointer syntax. No saved projection
will read/reparse raw source bytes to perform this identity check.

Regressions will include a valid location; unknown artifact; a different known
artifact paired with the source; and a different selected document paired with
the otherwise valid source/artifact. Existing native/Data diagnostic locations
will be exercised by the full P suite.

Runtime edits are intentionally deferred while I's pin-dependent suite28993 is
live. No test will be killed or restarted because of observation timeout. The
current pin remains58ed93dcf6eafd1b7f4b7590cd21b2610794423b5c022f27db728fda10f9d921
until I reports the terminal receipt. This note does not claim the fix is applied.
