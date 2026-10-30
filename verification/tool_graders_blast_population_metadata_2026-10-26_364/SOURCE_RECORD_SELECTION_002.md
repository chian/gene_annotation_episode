# Final saved-source checks and selection handoff

This adds to SOURCE_RECORD_SELECTION_001 without replacing that record. The
public ports and closed records remain exactly those accepted in packet 361.

The private `_population_search_units(search, prepared, records)` is shared by
native-six population, standard population, standard saved validation and C's
saved iteration validator. It identifies original selected v3 search units even
when an unrelated unavailable reference field caused ordinary normalization to
omit the unit. All original member/report/pointer fields must match. With the
original bundle present, its output manifest must identify the exact artifact.
Only when that original bundle record is unavailable can the already retained
normalization mapping identify the artifact; selected_database remains null.
An explicit empty list still selects v3 and establishes no new equivalence.

Saved validation now also checks the supplied database_profile against the
original unique normalized sequence profile, preserving the standard adapter's
existing unavailable-search behavior. This compares saved facts; it does not
populate metadata or calculate a distribution.

For selected assertion/census documents, saved normalized identities are checked
against their original wire declarations. A received declaration must keep its
literal source_ref, artifact_ref, digest and byte count. Captured input, output,
manifest, database metadata manifest and sidecar declarations must retain their
exact original selected/captured artifact key, slot, digest and byte count from
the original bundle and requested job. Replacing a normalized document with a
different genuine retained source is rejected. C remains responsible for
independently authenticating the actual original captured source/artifact
identities and bytes against its sealed request; no identity is manufactured.

Every retained pointed value is checked against the same original identity's
root. A resolved valid JSON document cannot disappear while its association is
replaced by a null record. A document whose original JSON cannot be decoded has
no finite JSON value; its existing source_record_invalid diagnostic and null
record remain explicit. A valid JSON scalar with an impossible pointer retains
its scalar root and the null pointed record. An unresolved wire token is never
treated as received-source authority.

`final_007` includes a native saved-source-redirection forgery that changes the
normalized source, retained root/pointer records and association together. The
validator rejects that change against the original wire received declaration.

Worker validation must still check completeness and original authority using its
sealed source capture. Internal equality of a supplied standalone dictionary
does not prove an original episode receipt or permit a new interpretation to
masquerade as parameter-only recalculation.
