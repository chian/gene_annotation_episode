# Proteome saved-data validation workload

Root owns new `gene_annotation_episode/bvbrc_proteome_data_contracts.py`,
`bvbrc_proteome_data_schemas.json`, its dedicated tests, and this verification
directory. This workload does not edit the accepted native parser or any
existing execution, registration, prompt, scoring or controller path.

Public interfaces are `proteome_data_schema(name: str) -> dict` and
`validate_proteome_data(name: str, value: dict) -> dict`. Both return detached
copies. Validation failures are `ProteomeDataError(ValueError)` with fixed
`code` and JSON Pointer `path`, without interpolating supplied values.

The source design is contract proposal001 from worker165. Its independently
usable input/snapshot subset will be frozen with the additive B1 clarification;
no unfinished witness or directional-report interface is accepted by this note.
The common implementation may be developed before that freeze, but it must not
be exposed as a complete validator until the accepted shapes and semantic tests
are installed. Unknown names are rejected. No scientific tool completion is
claimed by this workload.

Responsibilities: plain finite JSON; exact closed shapes; numeric lexeme/value
agreement; missing versus zero; canonical record ordinals; byte bounds;
source-location agreement; saved sequence/count/digest and membership
relationships; metadata field domains; original selected-input order. These
checks consume saved data only. They neither authenticate a remote task nor
rerun parsing, alignment, calculations, acquisition or execution. Actual source
custody remains with the existing host.

Consumers are the separately owned five B1 extraction functions and later
B2/B3/B4 functions after their specific contracts are frozen. The extractors
must not repair a failed saved-data validation by silently changing the source
or substituting a measurement. Invalid neighbors are retained according to
the accepted extraction contract.

Verification must include valid populated examples and mutations of values,
counts, ordinals, digests, byte/source locations and null states. Duplicate
identifiers and duplicate sequences remain distinct occurrences. No native
or live execution claim follows from these synthetic contract examples.
