"""Private job_launch binding with exact original identity/configuration."""
from __future__ import annotations
from .binding_record import HomologySubmissionBindingRecord
from .goal import HomologySubmissionGoal
from .credit import HomologySubmissionCredit
from .from_parent import HomologySubmissionFromParent
from .to_parent import HomologySubmissionToParent
from .task import HomologySubmissionTask
from .presentation import present_job_context
from importlib import import_module
from gene_annotation_episode.episodic_workflow.root.a104.library.homology_family_resources import HomologyFamilyResources

class HomologyEpisode(HomologyFamilyResources, HomologySubmissionBindingRecord, HomologySubmissionGoal, HomologySubmissionCredit, HomologySubmissionFromParent, HomologySubmissionToParent):
    binding_path = 'homology_job_submission'
    commissioning_parent = 'legacy_annotation'
    entry_roles = ('job_launch',)
    roles = ('job_launch',)
    decision_source_type = HomologySubmissionTask
    decision_prompt_renderer = staticmethod(present_job_context)
    controller_selection = staticmethod(import_module('.yield_estimator', __package__).select_controller)

import sys as _homology_binding_sys
_original_controller_descriptor = vars(HomologyEpisode)['controller_selection']
_original_controller_owner = _homology_binding_sys.modules[__package__ + '.yield_estimator']

def _bind_homology_controller_alias(namespace):
    _original_controller_owner._bind_preserved_runtime_providers(namespace)
    current = vars(HomologyEpisode)['controller_selection']
    if current is _original_controller_descriptor:
        HomologyEpisode.controller_selection = staticmethod(_original_controller_owner.select_controller)

from gene_annotation_episode.episodic_workflow.root.a104.library.homology_runtime_binding import complete_owner as _complete_runtime_owner
_complete_runtime_owner(__name__, _bind_homology_controller_alias)
