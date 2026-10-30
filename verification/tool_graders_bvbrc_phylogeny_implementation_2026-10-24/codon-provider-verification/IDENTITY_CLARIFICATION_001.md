# Exact original-member identity fallback

Root approved this narrow correction on 2026-10-24 after the concrete
`aggregate-member-before.json` probe. The original frozen schemas and native
reader/calculator contracts remain unchanged.

Sharing an Evidence object or a source container does not establish that an
original member is a specific genome or feature. The provider's source fallback
requires a retained-bytes InputBinding, identical original ContentRef in the
MemberFact evidence, and exact equality of MemberFact.member_pointer,
Evidence.pointer and SourceRecord.pointer. The SourceRecord artifact must match
that original content; when artifact is null its exact evidence target must
match instead. A supported SourceRecord genome subject supplies the genome;
a supported feature subject may use its explicit FeatureGenomeJoin.

The distinct direct inline genome-ID route, validated group membership route
and actually forwarded optional-input route remain available. Unrelated
aggregate context cannot contradict those identities. A bare member label and
shared FeatureGenomeJoin evidence do not establish an original identity.

Unsupported mappings remain unknown and produce
`member_genome_association_required`. Independent alignment/tree quantities
remain usable. Two conflicting exact supported original identities are still
a structural error.

This fallback does not claim to establish a sequence-to-genome relationship
through different source objects without a declared exact relationship. It
adds no network request, native parser, numerical formula or episode action.
