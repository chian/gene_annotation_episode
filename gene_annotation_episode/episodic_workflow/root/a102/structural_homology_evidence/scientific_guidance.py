"""The A102 head's scientific guidance, prefixed to its model instructions (``runtime_head.instructions``)."""
from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import is_merged_entry


def scientific_guidance(entry):
    if is_merged_entry(entry):
        return ('A102 owns comparative and experimental structural evidence. '
            'Scientific descendants remain A102. Use either path or both as useful, '
            'and return their separate scientific quantities and shared dependencies.\n\n')
    return ("A102 owns structural work only. Scientific descendants remain A102. "
        "Use available shared operations to send the immediate parent specific missing operands or useful "
        "received evidence. That parent chooses within its own options or relays the need upward. "
        "Reuse qualified retained alignments. "
        "Native comparison results automatically populate the A102 numerical sheet before credit inspection; "
        "unknown functional features do not erase measured native correspondence. "
        "Follow up for missing structural cells, preserve original scope and model uncertainty, "
        "and distinguish fold resemblance from exact function. Novel folding requires an explicit configured "
        "remote/API/HPC binding.\n\n")
