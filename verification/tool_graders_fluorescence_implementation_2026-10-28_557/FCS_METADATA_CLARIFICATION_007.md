# Metadata required for encoded values

The parser in006 returns FlowIO.events without applying any preprocessing.
An absent PnE must therefore not, by itself, discard otherwise decodable encoded
values. FlowIO internally uses a linear default for its channel-metadata object,
but this reader preserves the actual TEXT with PnE absent; it does not publish
that default as an observed parameter or claim a transformation occurred.

Require actual positional PnN/PnB/PnR and the structural version/type/width/count/
offset relationships needed by this selected decoder. Optional PnS/PnG remain
absent when absent. If malformed supplied metadata makes the actual constructor
fail, retain established metadata and the native failure; do not repair the file
or substitute parameters. A later requested preprocessing path must define its
own required parameter evidence. This clarification does not implement it.
