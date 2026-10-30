# Independent native endpoint disagreement

For adjacent HSP blocks, individually valid reported intervals on either axis
can establish that next_start differs from previous_end+1 even when strings
are missing. Preserve that known discontinuity as HSP.contiguous_blocks=`no`
and an HSP block_continuity_conflict Issue with exact endpoint FieldRefs.
Check it before returning `unknown` for unavailable strings or trace geometry.
Otherwise unavailable geometry/strings still yields unknown, and yes requires
the reviewed usable continuation (one usable block has no boundary to test).

This does not create a graph mapping conflict from native intervals alone.
Graph boundary conflicts require actual column witnesses on both sides. When
those do not exist, the graph remains incomplete_geometry and the independently
known HSP endpoint disagreement remains visible. Native strings/coordinates,
per-axis coverage and all unrelated valid quantities remain retained.
