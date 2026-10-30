# Explicit original-occurrence to feature/genome associations

Accepted additive interface extension, 2026-10-25. Root found a real omission
after worker142 traced the frozen provider records: OriginalMember had feature
and genome arrays, but no common input declaration explicitly supplied their
relationship. The original three frozen association records remain unchanged
as historical documents; this extension is part of the implementation contract.

Add the mandatory field `member_entities:[MemberEntityAssociation]` to BOTH
CommonAssociationDeclarations and AssociationSet. An empty list means no such
relationship is supplied. No existing host InputBinding/MemberFact, native
document, calculator or external function signature changes.

```text
MemberEntityAssociation = {
  member_key:MemberKey,
  subject:Subject,
  evidence:[Evidence]
}
```

The record is closed. MemberKey, Subject and Evidence retain their exact frozen
definitions. Here subject.kind is exactly feature or genome. subject.id is the
explicit biological entity identifier; subject.source_record_id resolves to a
declared SourceRecord with the corresponding feature/genome kind. member_key
resolves to an actual OriginalMember occurrence in this AssociationSet. Evidence
must be nonempty for an accepted identity link. Duplicate relationship records
with the same occurrence, subject kind/id and source_record_id are caller misuse;
do not silently select or merge them. Multiple different explicit links remain
distinct, including several features sharing the same sequence occurrence.

The extractor retains the complete supplied records in member_entities. It
populates OriginalMember.feature_ids/genome_ids/source_record_ids only from
explicit relationships, preserving first declaration order and unique scalar
IDs in these derived arrays. An explicit member-to-feature link can join a
FeatureGenomeAssociation with the exact same feature_id to supply a genome;
retain both original link records/evidence. Several explicit genome relationships
remain several relationships, never an arbitrary choice of one. Ordinary source
record provenance alone can populate source_record_ids but cannot prove an
entity identity. Array validators cross-check every populated feature/genome ID
against this explicit relation graph.

Equal FASTA labels, equal sequence strings, a shared source record/container, or
equal SourceEvidence objects alone never establish a feature/genome identity.
In particular an empty JSON pointer often denotes an entire response, not a
particular entity. Do not use evidence equality as an identity join.

AutoGroupEntry.feature_id plus its explicit member_keys is a separate explicit
feature-to-occurrence relation after adapter authentication of the original
input (clarification012). MetaCATS may consume that relation without requiring
OriginalMember.feature_ids to be prefilled. It preserves AutoGroupEntry rather
than mutating the common association object or inferring a label-based join.

Consumers: validate_alignment_association_declarations and
extract_alignment_associations accept the new common field;
validate_association_set validates and retains it; extract_msa_sheet and
extract_metacats_sheet retain the whole AssociationSet; bundle commissioning
and resolution pass explicit member_entities through without invention.
The MetaCATS extractor uses actual declared relation records where needed.

Verification must include explicit occurrence-to-feature/genome links, two
features sharing a sequence, repeated labels with distinct occurrences, unknown
occurrences/source records, wrong SourceRecord kinds, empty evidence, duplicate
relations and unrelated shared source/evidence that must not populate identity.
Revalidated saved arrays cannot claim additional feature/genome IDs absent from
the explicit relationship graph. These are supplied scientific associations,
not calibration scores or autonomous decisions.
