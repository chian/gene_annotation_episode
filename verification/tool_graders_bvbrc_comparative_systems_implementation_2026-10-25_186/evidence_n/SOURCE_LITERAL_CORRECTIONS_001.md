# Additive source-literal clarification

The frozen185 examples are contract illustrations, not parser outputs. This note does not edit them.

1. `source_executed_synthetic/discard_and_dependence/discard_and_dependence_subsystems_tables.json`, JSON pointer `/subsystems`, data row0, column0 (`superclass`) contains literal `SYNTHETIC`. The raw `discard_and_dependence_subsystems.tsv`, column13 (`superclass`) contains `synthetic`. The summary entity retains `superclass_native=SYNTHETIC`, `superclass_aggregation=SYNTHETIC`; raw association fields separately retain `synthetic`. The example summary borrowed lower-case casing from the raw table.
2. `discard_and_dependence_subsystems_variant_mtx.tsv` has two headers, then data row0: `SYNTHETIC`, `Synthetic class`, `Synthetic subclass`, `Synthetic subsystem`, `3`, `2`, `0`, `0`, `active`, `likely`. No column contains a subsystem ID. Its entity has `kind=variant`, `subsystem_id=null`, and literal hierarchy/name. No cross-document ID is guessed. The frozen example's `S_TEST` is not a literal value in this artifact.

Both input artifacts are source-executed synthetic witnesses, not live BV-BRC results.
