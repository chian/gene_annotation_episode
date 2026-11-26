"""The value of one claim a ranked hit list makes. Every BLAST hit list is read this way, by three things: (1) the top
hit that makes the claim, (2) how long its block runs down the ranking before a hit says something different, (3)
whether the taxa of that block sit together in the tree. The constants are tuning."""
from gene_annotation_episode.episodic_workflow.episode_support.grading.taxonomic_classification.ncbi_taxonomy import (
    prepared_taxonomy)

# The rank at which the taxa of a block are compared: the family of the top hit.
TAXA_RANK = 'F'
# The taxa factor of a block whose top hit cannot be placed, or none of whose other hits are of its family.
TAXA_FLOOR = 0.5


def taxa_share(taxon_ids):
    """The share of a block's hits (``taxon_ids`` in rank order, the top hit first) that are of the top hit's family; 0
    when the top hit's family is not in the prepared taxonomy."""
    nodes = prepared_taxonomy()['nodes']

    def family(taxon):
        for _ in range(200):
            if taxon not in nodes:
                return None
            if nodes[taxon]['rank_code'] == TAXA_RANK:
                return taxon
            taxon = nodes[taxon]['parent']
        return None
    families = [family(taxon) for taxon in taxon_ids]
    if families[0] is None:
        return 0.0
    return sum(1 for found in families if found == families[0]) / len(families)


def claim_value(top, run, share):
    """``top x run / (run + 1) x (TAXA_FLOOR + (1 - TAXA_FLOOR) x share)``: ``top`` the top hit's own value (0 to 1),
    ``run`` the hits of its block before the first hit that says something different, ``share`` their ``taxa_share``."""
    return top * run / (run + 1) * (TAXA_FLOOR + (1 - TAXA_FLOOR) * share)
