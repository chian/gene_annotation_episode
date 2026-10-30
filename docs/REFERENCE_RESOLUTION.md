# Resolve actual form references without a full registry inventory

The runtime now resolves each child/parent form reference through the Store's
existing candidate-specific ownership/scope projection, `reference_subset`.
It preserves the same scientific reference membership and namespace meanings
as `references(scope)`. The `subject` namespace remains original scoped inputs,
features and products; external references remain in `reference`. Native custody
handles, out-of-scope scientific claims and unattached diagnostic artifacts do
not become admissible merely because `get` can retrieve them. Existing permitted
source inspection across scopes remains unchanged.

Previously each reference value built the complete registry, decoding every
scoped scientific row and all artifact-owner metadata. That repeated work grows
with the investigation even for a small requested form. The normal runtime now
retrieves only the candidate's semantic metadata and, for artifact candidates,
uses the same existing ownership projection. SQLite may still scan relevant
metadata to establish artifact ownership; this does not establish a global
memory or latency bound. Exact source bytes and archived contexts are not read.

There is no new admission rule, semantic registry, summarizer, scientific
review, annotation, credit projection, action observation or stopping condition.
The full registry remains available for explicit host use. Synthetic runtime
fixture stores implement the same candidate-resolution interface. Current live
run snapshots are not changed.

Focused tests compare actual Store membership and namespace results against the
existing full registry, preserve header-only versus registered-member ownership,
exercise actual constrained-form admission, and prohibit source-body/full-registry
reads and unrelated record hydration. These establish representation behavior,
not biological annotation performance or library-scale resource measurements.
