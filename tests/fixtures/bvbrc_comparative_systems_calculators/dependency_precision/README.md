This is source-executed synthetic evidence, not a live BV-BRC result.

`joined_metadata_subsystems_tables.json` was emitted by the unchanged retained
`compare_systems_lib.py` at commit
`670b3b6dd09509ebc62fb6f1b1caf3e38c33bd33`, SHA256
`052f74f971ee149bf5e07d1f6a6f965f9233d6a8f1795daae7a7b182b47b747f`.
The reproduction script, complete supplied inputs, stdout/stderr and receipt are
in `186/evidence_c_review/source_join_witness_001.py`,
`source_executed_synthetic/`, and `SOURCE_JOIN_WITNESS_001.json`.
Network/authentication routes were blocked; zero calls were attempted.

The feature input repeats `(genome_id=1.1, feature_id=f1)` with different
product, accession and PATRIC metadata. The producer drops those fields from
the subsystem side, then inner-joins on genome/feature (lines 60–80, 637–645).
The two joined `ss_f1` occurrences retain the same subsystem, hierarchy, genome
and role. Six joined occurrences still contain three distinct genome/role
pairs. Native role conservation remains `100 × 3 / (2 × 2) = 75` percent;
its formula-check discrepancy is zero. Feature-side metadata differences remain
in the native artifact and N sheet, including `inner_join_many_to_many`.

The fixture SHA256 is
`2eb9b9c6af077c963914c900e9017e1cd76550666aed1a683a5f7f2a78cfbe96`.
The calculator tests also apply clearly labelled synthetic malformed and
contradictory edits to retained fixtures through the actual N parser/builder.
Those edited documents use `synthetic_fixture` with no claimed executed producer.
