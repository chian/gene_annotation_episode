# FASTA record identity must reach assembly-quality row identity

339 identified an additional consumer. Root confirmed the same construction in
both `native_blast_standard_database_calculators._sequence_rows` and
`native_blast_database_result_worker._sequence_taxonomy_quality` (the native
worker's assembly-quality loop): each creates the quality-row assembly source
from only `reference_metadata.source` and `reference_metadata.native_pointer`.
The row identity includes this source and excludes the new record locator.

Thus two distinct v2 FASTA metadata records at one source and empty pointer
cannot remain distinguishable at this row boundary solely through the accepted
record locator. Their complete metadata and numerical components can be retained
upstream while this later identity still loses the original record distinction.
Both result-view modules currently declare the assembly source using their
closed two-field provenance schema.

The I integration workload must address this consumer as well as tuple admission
and worker implementation identities. Before coding that addition, define the
exact new row identity, closed return schema and saved-version behavior. Verify
two distinct original records with different assembly-quality measurements,
both at the overall and function-specific scopes, through real row building and
typed return. Preserve old v1 row identities, exact closed forms and saved
results. Do not invent source aliases, JSON pointers into FASTA, measurements or
new scientific formulas.

This finding does not assign the shared calculators or views to339, C or D.
Root must explicitly extend I's file ownership to the standard calculator and
native result-view module after defining that return contract. The already
accepted metadata/public-association work can proceed independently. No grader
count or completed-capability claim changes here.

This is source evidence, not an executed quality-row collision test. The
original337 contract and records remain unchanged.
