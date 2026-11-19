# HMMER API result measurements

Acquire the originally requested phmmer or hmmscan result page through
`api.hmmer.result`. The result assignment fixes the original search and selected
page; this operation takes no new query, database or threshold. Another page
requires another explicit results assignment. The service's complete raw page
is retained, including all supplied hit identifiers, linked metadata, domain
arrays, alignment displays, reporting/inclusion flags and search statistics.

For phmmer, model coordinates describe the query and sequence coordinates
describe a matched reference protein. For hmmscan, model coordinates describe
the profile and sequence coordinates describe the query protein. A profile's
consensus is not a measured reference protein. Coordinates are retained in their
native one-based inclusive form and interpreted through zero-based half-open
intervals. Query length must agree with the actual submitted sequence.

The tool preserves separate full-sequence and domain scores, conditional and
independent E-values, bias, alignment spans, envelopes, paired positions,
insertions/deletions and coverage denominators. A domain's span coverage uses
the span and the full corresponding model/sequence length. Paired coverage uses
only columns containing both a model position and a sequence residue. These can
differ in a gapped alignment. Missing alignment displays or operand metadata
leave their dependent measurements unavailable; native scores can remain useful.

Identity quantities have different meanings. `api_identity_fraction` retains
the provider's identity count divided by the smaller ungapped display length.
`consensus_identity_fraction` uses matching consensus/residue columns divided by
paired columns; `alignment_identity_fraction` uses all alignment columns.
`sequence_identity_fraction` is available only when supplied actual sequence
operands establish that correspondence. None is a probability of correct gene
function. A profile-consensus match must not be described as sequence identity.

Native domain bias is supplied in nats by this API; its separately named bits
value divides by ln(2). Local native tables already report bias in bits.
`native_accuracy` and the PP display concern alignment posterior accuracy, not
identity or gene-function confidence. PP symbols supply probability intervals;
the reported lower/upper means retain those bounds instead of inventing an
exact probability. Printed zero E-values remain zero with their native meaning.

The numerical sheet and calculators retain the original hit-array and
domain-array positions. These are distinct from provider hit indices or native
domain ordinals. Invalid domains preserve valid siblings and raw bytes with
specific failure information. Repeated accessions, overlapping domains or
multiple representations do not establish independent evidence. Linked UniProt
metadata and the actual native target name remain separate identities.

A completed page does not establish a complete hit population. Pagination and
native search statistics remain explicit, and a no-hit page does not establish
biological absence. These measurements do not assign a function or lineage.
Full sheets and alignments remain retained data; the parent receives its
requested typed facts. Grading makes no additional service requests, model
calls or completed actions. Search timing remains separate from these
scientific measurements.
