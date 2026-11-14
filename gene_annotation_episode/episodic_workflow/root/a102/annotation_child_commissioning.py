"""This existing annotation root's private published-evidence commission."""
from .published_evidence_assessment.episode import LiteratureEpisode
from .to_child_published_evidence_assessment import assemble_request
from .from_child_published_evidence_assessment import select_report_receiver as literature_report_receiver

def literature_request_assembler(source, child_binding):
    if (len(source.path) == 1 and source.path[0][0] == 'annotation'
            and type(child_binding) is LiteratureEpisode
            and child_binding.binding_path == 'published_evidence_assessment'
            and child_binding.commissioning_parent == 'legacy_annotation'):
        return assemble_request
    return None
