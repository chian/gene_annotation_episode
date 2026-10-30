# Interpretation basis references

`visible_record_refs` identifies semantic handles actually visible to a decision
and eligible under its existing scientific report boundary. An admitted report
update records that same list as `interpretation_basis_refs`. This is provenance
metadata, not a claim that every referenced record or source body was read.

The basis includes actual typed record projections, declared reference positions
in the supplied working state and host outcomes, selected source-window custody,
and schema-declared reference fields in the current report update and admitted
direct-child forms. A child form conveys its requested values and handles; it
does not implicitly convey the child's private context or referenced bodies.
Reference fields may have any parent-chosen name: their admitted form schema
defines the semantic type.

The collector checks candidate identities through indexed Store lookups. It does
not parse text/quotes/examples for IDs or accept an untyped provider `id` field
as a scientific record. Native collection-member handles, audit identities and
unregistered IDs are not promoted into scientific form references.

`Store.reference_subset(candidates, scope)` applies the same existing membership
as `Store.references(scope)` to the supplied candidates. Its artifact ownership
projection is shared with `references()`: actual declared record references,
original input sequence artifacts, already registered member-reference artifacts,
and problem artifact references. Candidate filtering happens on SQLite metadata;
the reference walker still distinguishes actual reference fields from text
mentions. Ownership resolution can scan authoritative metadata in SQLite; there
is no new global artifact-owner index. Candidate filtering keeps unrelated rows
out of Python. Referenced source/artifact contents and archived contexts are not loaded.
There is no new graph, resource registration or scientific assessment.

An explicit `source.read` result therefore contributes its actual source and
selected artifact even when the source lies beyond the automatic 24-record page.
By contrast, `material.header` does not itself register its native member/header
as a scientific entity. Unattached operational artifacts remain outside the form
registry even when supplied under a key such as `response_ref`.

The existing scoped form resolver can exclude a foreign-target hypothesis while
ordinary scientific context can still refer to or explicitly read it. This slice
preserves both behaviors: the actual context remains readable and unchanged,
while the basis fact lists only handles available at the existing return boundary.
It adds neither a read prohibition nor broader report/credit scope.

Reading, reporting and basis refresh create no extra completed action or yield
observation. Credit, current scientific state, report value admission and numerical
continuation are unchanged.
