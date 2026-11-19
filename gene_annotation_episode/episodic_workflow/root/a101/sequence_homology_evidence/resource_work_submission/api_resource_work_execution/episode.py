"""The A101 ``sequence_homology_evidence/resource_work_submission/api_resource_work_execution`` binding.

It runs the commissioned resource work through one of its own configured API services: its services
(``execution_job_submission/api_job_execution/configuration.ApiJobConfiguration``, built by
``a101_home_factory`` from ``services['a101']['api_resource_work_execution']`` over its own A101
``ToolRegistry`` on the run's shared store), its model-selected service operations
(``runtime_source.ApiJobExecutionSource``) and its completion continuation toward one usable handoff
(``runtime_credit``).
"""
from __future__ import annotations

from types import MappingProxyType

from episode_runtime import ChoiceField, Field, RecordForm

from ...contract_binding import SCOPE, A101ContractBinding
from ...execution_job_submission.api_job_execution.configuration import ApiJobConfiguration


class ApiResourceWorkExecutionEpisode(A101ContractBinding, ApiJobConfiguration):
    """Get the resource work executing through the selected remote API service."""
    binding_path = 'sequence_homology_evidence/resource_work_submission/api_resource_work_execution'
    goal = 'Get the resource work executing through the selected remote API service'
    unit = 'One API resource action'
    result = 'The API resource handle and its received status'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence/resource_work_submission'

    @property
    def assignment_form(self):
        """The commissioner chooses one of this binding's API resources and supplies that service's request."""
        return RecordForm({
            'scope': SCOPE,
            'resource_id': ChoiceField('text', 'The configured API resource that runs the resource work',
                                       tuple(sorted(self.services))),
            'request': Field('record', "The resource work request in the chosen resource's service request form"),
        })

    def build_controller(self, bound, collaborators):
        from ...execution_job_submission.api_job_execution.runtime_credit import completion_controller
        return completion_controller(bound.episode_id, 0.0, self.continuation)

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        from ...execution_job_submission.api_job_execution.runtime_source import ApiJobExecutionSource
        source = ApiJobExecutionSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)
