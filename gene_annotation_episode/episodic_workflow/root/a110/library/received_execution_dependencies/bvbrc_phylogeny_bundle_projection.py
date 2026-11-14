from __future__ import annotations
import hashlib
from pathlib import Path
_DEPENDENCIES = ('bvbrc_phylogeny_bundle_contracts.py', 'bvbrc_phylogeny_bundle_resolution.py', 'bvbrc_phylogeny_bundle_projection.py', 'bvbrc_gene_tree_bundle_adapter.py', 'bvbrc_codon_tree_bundle_adapter.py', 'bvbrc_phylogeny_common_inputs.py', 'bvbrc_phylogeny_common_contracts.py', 'bvbrc_phylogeny_common_grader.py', 'bvbrc_gene_tree_inputs.py', 'bvbrc_gene_tree_grader.py', 'bvbrc_codon_tree_inputs.py', 'bvbrc_codon_tree_grader.py', 'phylogeny_formats.py', 'phylogeny_format_contracts.py', 'phylogeny_raxml_inputs.py', 'phylogeny_calculation_contracts.py', 'phylogeny_calculators.py', 'bvbrc_codon_tree_native.py', 'bvbrc_codon_tree_calculators.py', 'bvbrc_appservice_contracts.py', 'bvbrc_appservice_schemas.json')

def implementation_sha256():
    """Actual installed A110 reader identity; retained epochs are authenticated separately."""
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.adapter_source_identity import current_implementation_sha256
    return current_implementation_sha256('bvbrc_phylogeny_bundle_projection')
