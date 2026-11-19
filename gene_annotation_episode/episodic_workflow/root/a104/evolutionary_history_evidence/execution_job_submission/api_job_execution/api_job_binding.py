"""The three A104 API job-execution bindings (role ``launch_api``) on ``episode_runtime``.

Each runs one assigned API job: its own API services (``configuration.ApiJobConfiguration``,
built by ``runtime_bindings.a104_home`` over its own A104 ``ToolRegistry`` on the run's shared
store), its model-selected operations (``appservice_source.AppServiceJobExecutionSource``
for a BV-BRC AppService resource, ``runtime_source.ApiJobExecutionSource`` for every other
service) and its completion continuation toward one usable handoff (``runtime_credit``). Its
assignment is the A104 descendant form: ``scope`` and ``assignment`` =
``{'resource_id', 'request'}``; it returns ``credit`` and ``report``.
"""
from __future__ import annotations

from episode_runtime import ChoiceField, Field, RecordForm

from ...runtime_bindings import SCOPE, DescendantBinding
from .configuration import ApiJobConfiguration


class ApiJobExecutionBinding(ApiJobConfiguration, DescendantBinding):

    def __init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain, *,
                 tool_registry, configuration):
        if role != 'launch_api':
            raise ValueError('a104_api_job_binding_role_must_be_launch_api:' + binding_path)
        DescendantBinding.__init__(self, binding_path, role, commissioning_parent, child_slots, roles_by_grain)
        ApiJobConfiguration.__init__(self, tool_registry=tool_registry, configuration=configuration)
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'assignment': Field('record', 'The API job: one configured resource and its service request', form=RecordForm({
                'resource_id': ChoiceField('text', 'The configured API resource that runs the job',
                                           tuple(sorted(self.services))),
                'request': Field('record', "The job request in the chosen resource's service request form")}))})

    def build_controller(self, bound, collaborators):
        from .runtime_credit import completion_controller
        if bound.binding_path != self.binding_path:
            raise ValueError('a104_controller_opened_for_another_binding:' + bound.binding_path)
        return completion_controller(bound.episode_id, 0.0, self.continuation)

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        if self.services[bound.assignment['assignment']['resource_id']].service == 'bvbrc_appservice':
            from .appservice_source import AppServiceJobExecutionSource as Source
        else:
            from .runtime_source import ApiJobExecutionSource as Source
        source = Source(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)
