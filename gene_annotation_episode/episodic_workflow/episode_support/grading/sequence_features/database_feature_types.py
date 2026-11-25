"""The feature types of outside databases matched to the feature types of this code base (``feature_types.KINDS``): one
table per database, from the database's own value of a feature's type to one of our types.

THIS TABLE IS TO BE EXTENDED (the owner, 2026-11-25: "things will have to be matched and that is fine. we will have to
build that mapping"). It holds only the values that plainly match one of our types by name and that were confirmed as
a value the database really uses; a value is added when it is confirmed and its type decided. A database value that is
not in its table has no type of ours yet: ``bvbrc_feature_kind`` gives ``None`` for it, the value itself stays in the
stored records exactly as the database gave it, and whoever counts features by type counts it as not matched yet
(never as absent, and never under a guessed type).

BV-BRC (``BVBRC_FEATURE_TYPE``): the ``feature_type`` field of the ``genome_feature`` collection of the data service
(``readers/sequence_and_context_sources/sequence_homology_evidence/bvbrc_data_fields.py``), which the hit metadata of a
BV-BRC search asks for (``tools/similarity_search/sequence_homology_evidence/bvbrc_hit_metadata.py``). What each entry
stands on:

* ``CDS``: BV-BRC's own client code filters on it (``eq(feature_type,CDS)``, the copy under
  ``readers/phylogeny/tests/fixtures/bvbrc/.../codon_trees/lib/patric_api.py``), and the service's own ``feature_id`` of
  every hit of a stored real search (200 hits, 2026-11-25) carries it as its type component
  (``PATRIC.<genome id>.<accession>.CDS.<start>.<end>.<fwd|rev>``).

No other BV-BRC value could be confirmed from this repository or its stored real data when the table was written: the
request had never asked for ``feature_type``, so no stored real response holds one. This module holds data and one
lookup."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_features.feature_types import CODING

# BV-BRC ``genome_feature.feature_type`` -> one of ``feature_types.KINDS``.
BVBRC_FEATURE_TYPE = {
    'CDS': CODING,
}


def bvbrc_feature_kind(feature_type):
    """Our feature type (one of ``feature_types.KINDS``) of BV-BRC's ``feature_type`` value, or ``None`` when the value
    is not in the table yet."""
    return BVBRC_FEATURE_TYPE.get(feature_type)


__all__ = ['BVBRC_FEATURE_TYPE', 'bvbrc_feature_kind']
