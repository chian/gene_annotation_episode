"""The attachment names exactly the nine evidence-axis children of the root."""
from gene_annotation_episode.episodic_workflow.root.axes import ATTACHMENTS, AXIS_ROLES

EXPECTED = {
    'sequence_homology_evidence': 'A101', 'structural_homology_evidence': 'A102', 'gene_context_evidence': 'A103',
    'evolutionary_history_evidence': 'A104', 'experimental_activity_evidence': 'A105',
    'perturbation_evidence': 'A106', 'partner_presence_evidence': 'A107', 'sample_context_evidence': 'A108',
    'biochemical_feasibility_evidence': 'A110',
}


def test_exactly_nine_attachments_each_role_to_its_axis():
    assert len(ATTACHMENTS) == 9
    assert {attachment.role: attachment.axis for attachment in ATTACHMENTS} == EXPECTED
    assert len(set(AXIS_ROLES)) == 9 and set(AXIS_ROLES) == set(EXPECTED)
