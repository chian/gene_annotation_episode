"""The hooks of the three A103 API job-execution bindings on ``episode_runtime``.

Each binding runs one assigned API job: its own API services
(``configuration.ApiJobConfiguration``, built by ``home.factory`` over its own
A103 tool registry on the run's shared store), its model-selected operations
(``appservice_source.AppServiceJobExecutionSource`` for a BV-BRC AppService resource,
``runtime_source.ApiJobExecutionSource`` for every other service) and its completion
continuation toward one usable handoff (``runtime_credit``).
"""
from __future__ import annotations

from episode_runtime import ChoiceField, Field, RecordForm

from ...contract_binding import CHILD_ASSIGNMENT_FORM
from .configuration import ApiJobConfiguration


class ApiJobExecutionBinding(ApiJobConfiguration):
    """Mixed in before ``A103ContractBinding`` by each API job-execution binding."""

    required_collaborators = ('model_provider', 'store')

    @property
    def assignment_form(self):
        """The commissioner chooses one of this binding's API resources and supplies that service's request."""
        return RecordForm({
            'scope': CHILD_ASSIGNMENT_FORM.fields['scope'],
            'resource_id': ChoiceField('text', 'The configured API resource that runs the job',
                                       tuple(sorted(self.services))),
            'request': Field('record', "The job request in the chosen resource's service request form"),
        })

    def build_controller(self, bound, collaborators):
        from .runtime_credit import completion_controller
        return completion_controller(bound.episode_id, 0.0, self.continuation)

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        if self.services[bound.assignment['resource_id']].service == 'bvbrc_appservice':
            from .appservice_source import AppServiceJobExecutionSource as Source
        else:
            from .runtime_source import ApiJobExecutionSource as Source
        source = Source(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)
