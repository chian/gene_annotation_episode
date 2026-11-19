"""The hooks of the three A107 API job-execution bindings on ``episode_runtime``.

Each binding runs one assigned API job: its own API services
(``configuration.ApiJobConfiguration``, built by ``episode.home_factory`` over its own
``A107ToolRegistry`` on the run's shared store), its model-selected operations
(``appservice_source.AppServiceJobExecutionSource`` for a BV-BRC AppService resource,
``runtime_source.ApiJobExecutionSource`` for every other service) and its completion
continuation toward one usable handoff (``runtime_credit``). Its assignment is the A107
descendant form: ``scope`` and ``assignment`` = ``{'resource_id', 'request'}``.
"""
from __future__ import annotations

from episode_runtime import ChoiceField, Field, RecordForm

from ...runtime_binding import DESCENDANT_ASSIGNMENT_FORM
from .configuration import ApiJobConfiguration


class ApiJobExecutionBinding(ApiJobConfiguration):
    """Mixed in before ``DescendantBinding`` by each API job-execution binding."""

    @property
    def assignment_form(self):
        """The A107 descendant form, its ``assignment`` typed as one configured resource and its request."""
        return RecordForm({
            'scope': DESCENDANT_ASSIGNMENT_FORM.fields['scope'],
            'assignment': Field('record', 'The API job: one configured resource and its service request', form=RecordForm({
                'resource_id': ChoiceField('text', 'The configured API resource that runs the job',
                                           tuple(sorted(self.services))),
                'request': Field('record', "The job request in the chosen resource's service request form")}))})

    def build_controller(self, bound, collaborators):
        from .runtime_credit import completion_controller, continuation_settings
        return completion_controller(bound.episode_id, 0.0, continuation_settings(self.binding_path, collaborators))

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        from .runtime_credit import continuation_settings
        continuation_settings(self.binding_path, collaborators)
        if self.services[bound.assignment['assignment']['resource_id']].service == 'bvbrc_appservice':
            from .appservice_source import AppServiceJobExecutionSource as Source
        else:
            from .runtime_source import ApiJobExecutionSource as Source
        source = Source(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)
