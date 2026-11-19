"""The A101 ``sequence_homology_evidence/execution_job_submission/api_job_execution`` binding.

It runs one assigned API job on ``episode_runtime``: its own API services
(``configuration.ApiJobConfiguration``, built by ``a101_home_factory`` over its
own tool registry on the run's shared store), its model-selected operations
(``runtime_source.ApiJobExecutionSource``) and its completion continuation
toward one usable handoff (``runtime_credit``).
"""
from __future__ import annotations

from types import MappingProxyType

from episode_runtime import ChoiceField, Field, RecordForm

from ...contract_binding import SCOPE, A101ContractBinding
from .configuration import ApiJobConfiguration


class ApiJobExecutionEpisode(A101ContractBinding, ApiJobConfiguration):
    """Get the submitted computation executing through the selected remote API service."""
    binding_path = 'sequence_homology_evidence/execution_job_submission/api_job_execution'
    goal = 'Get the submitted computation executing through the selected remote API service'
    unit = 'One API submission or status action'
    result = 'The API execution handle and its received status'
    child_slots = MappingProxyType({})
    commissioning_parent = 'sequence_homology_evidence/execution_job_submission'

    @property
    def assignment_form(self):
        """The commissioner chooses one of this binding's API resources and supplies that service's request."""
        return RecordForm({
            'scope': SCOPE,
            'resource_id': ChoiceField('text', 'The configured API resource that runs the job',
                                       tuple(sorted(self.services))),
            'request': Field('record', "The job request in the chosen resource's service request form"),
        })

    def build_controller(self, bound, collaborators):
        from .runtime_credit import completion_controller
        return completion_controller(bound.episode_id, 0.0, self.continuation)

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        from .runtime_source import ApiJobExecutionSource
        source = ApiJobExecutionSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)
