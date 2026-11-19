"""The nine evidence axes attached to the root annotation episode, named in one place.

Each attachment binds one root child slot (the axis head's role, which is also
that head's ``binding_path``) to the axis head's binding class and the axis's
home factory. Each loader imports exactly those two names from the axis folder
when the attachment is loaded; an axis whose port cannot be imported raises its
own import error there. Nothing here discovers, defaults or substitutes an axis.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AxisAttachment:
    """One root child slot: the axis head bound to it and the factory that builds that axis's bindings."""
    role: str
    axis: str
    load: object  # () -> (head binding class, home factory)

    def entry_points(self):
        """The axis's head binding class and home factory, imported now."""
        head, factory = self.load()
        if not isinstance(head, type) or not callable(factory):
            raise TypeError('axis_attachment_entry_points_invalid:' + self.role)
        return head, factory


def _a101():
    from .a101.sequence_homology_evidence.episode import SequenceHomologyEvidenceEpisode
    from .a101.sequence_homology_evidence.home_factory import a101_home_factory
    return SequenceHomologyEvidenceEpisode, a101_home_factory


def _a102():
    from .a102.structural_homology_evidence.episode import StructuralHomologyEvidenceEpisode
    from .a102.structural_homology_evidence.contract_binding import a102_home_factory
    return StructuralHomologyEvidenceEpisode, a102_home_factory


def _a103():
    from .a103.gene_context_evidence.episode import GeneContextEvidenceEpisode
    from .a103.gene_context_evidence.home import factory
    return GeneContextEvidenceEpisode, factory


def _a104():
    from .a104.evolutionary_history_evidence.runtime_bindings import HeadBinding, a104_home
    return HeadBinding, a104_home


def _a105():
    from .a105.experimental_activity_evidence.episode import ExperimentalActivityEvidenceEpisode
    from .a105.experimental_activity_evidence.runtime_binding import a105_home_factory
    return ExperimentalActivityEvidenceEpisode, a105_home_factory


def _a106():
    from .a106.perturbation_evidence.episode import PerturbationEvidenceEpisode
    from .a106.perturbation_evidence.episode_contract import home
    return PerturbationEvidenceEpisode, home


def _a107():
    from .a107.partner_presence_evidence.episode import PartnerPresenceEvidenceEpisode, home_factory
    return PartnerPresenceEvidenceEpisode, home_factory


def _a108():
    from .a108.sample_context_evidence.episode import SampleContextEvidenceEpisode
    from .a108.sample_context_evidence.runtime_contract import a108_home_factory
    return SampleContextEvidenceEpisode, a108_home_factory


def _a110():
    from .a110.biochemical_feasibility_evidence.episode import BiochemicalFeasibilityEvidenceEpisode
    from .a110.biochemical_feasibility_evidence.home import home_factory
    return BiochemicalFeasibilityEvidenceEpisode, home_factory


ATTACHMENTS = (
    AxisAttachment('sequence_homology_evidence', 'A101', _a101),
    AxisAttachment('structural_homology_evidence', 'A102', _a102),
    AxisAttachment('gene_context_evidence', 'A103', _a103),
    AxisAttachment('evolutionary_history_evidence', 'A104', _a104),
    AxisAttachment('experimental_activity_evidence', 'A105', _a105),
    AxisAttachment('perturbation_evidence', 'A106', _a106),
    AxisAttachment('partner_presence_evidence', 'A107', _a107),
    AxisAttachment('sample_context_evidence', 'A108', _a108),
    AxisAttachment('biochemical_feasibility_evidence', 'A110', _a110),
)

AXIS_ROLES = tuple(attachment.role for attachment in ATTACHMENTS)

__all__ = ['ATTACHMENTS', 'AXIS_ROLES', 'AxisAttachment']
