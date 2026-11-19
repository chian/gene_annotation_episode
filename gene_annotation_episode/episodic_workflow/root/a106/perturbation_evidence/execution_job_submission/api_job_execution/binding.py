"""The A106 API job-execution binding (role ``launch_api``) on ``episode_runtime``.

Both A106 API job bindings (under ``execution_job_submission`` of the head and of
``published_evidence_assessment``) derive from ``ApiJobBinding``:

- its tools are its own BV-BRC AppService services (A106's only API primitive), one per configured
  ``resources`` entry (``{resource_id: AppService ServiceConfiguration}``), built by the A106 home
  factory over the binding's own ``ToolRegistry`` on the run's shared store;
- its commission chooses one of those resources and supplies the original ``AppServiceRequest``;
- its decisions are ``runtime_source.ApiJobExecutionSource`` (model-selected AppService launch
  operations over ``bound.recorder``, ``store`` and ``model_provider``);
- its continuation is the completion yield controller toward one usable handoff, with its
  ``{'cutoff', 'parameters'}`` from the standard ``continuation`` collaborator under its binding path.

Credit is never bounded, clamped or rescaled.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from episode_runtime import ChoiceField, Field, RecordForm

from gene_annotation_episode.domain import ContractError

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import plain
from ...episode_contract import MODEL_PROVIDER, SCOPE, STORE, EpisodeContract

CONTINUATION = 'continuation'
TARGET = 1.0


class ApiJobBinding(EpisodeContract):
    """One assigned AppService job carried to its usable handoff."""
    required_collaborators = (STORE, MODEL_PROVIDER, CONTINUATION)

    def __init__(self, services, *, tool_registry, resources):
        from gene_annotation_episode.episodic_workflow.episode_support.acquisition.service_calls.perturbation_evidence.api_services import build_service
        if not isinstance(resources, Mapping) or not resources:
            raise ContractError('a106_api_job_resources_required:' + self.binding_path)
        built = {}
        for resource_id, configuration in resources.items():
            if not isinstance(resource_id, str) or not resource_id or not isinstance(configuration, Mapping):
                raise ContractError('a106_api_job_resource_invalid:' + str(resource_id))
            try:
                built[resource_id] = build_service(configuration.get('service'), dict(configuration), tool_registry)
            except ValueError as error:
                raise ContractError('a106_api_job_resource_not_admitted:' + resource_id + ':' + str(error)) from error
        self.tool_registry = tool_registry
        self.services = MappingProxyType(built)
        self.assignment_form = RecordForm({
            'scope': SCOPE,
            'resource_id': ChoiceField('text', 'The configured BV-BRC AppService resource that runs the job',
                                       tuple(sorted(self.services))),
            'request': Field('record', "The original job in AppService request form (bvbrc_appservice_request_v1)"),
        })

    def contract_credit_unit(self, assignment):
        """One usable handoff of the assigned job; the request must be admitted by the chosen service."""
        try:
            self.services[assignment['resource_id']].validate_request(plain(assignment['request']), None)
        except ValueError as error:
            raise ContractError('a106_api_job_request_not_admitted:' + str(error)) from error
        return TARGET

    def build_controller(self, bound, collaborators):
        from yield_control import CompletionYieldController, YieldParameters
        continuation = collaborators[CONTINUATION]
        settings = continuation.get(self.binding_path) if isinstance(continuation, Mapping) else None
        if not isinstance(settings, Mapping) or set(settings) != {'cutoff', 'parameters'}:
            raise ContractError('a106_api_job_continuation_settings_require_cutoff_and_parameters:' + self.binding_path)
        return CompletionYieldController(bound.episode_id, 0.0, settings['cutoff'], TARGET,
                                         YieldParameters(**settings['parameters']))

    def build_episode(self, grain, bound, collaborators, child_builders):
        from method_loop import Episode
        from .runtime_source import ApiJobExecutionSource
        source = ApiJobExecutionSource(self, bound, collaborators)
        return Episode(grain, bound.key, source, bound.request, source.result)


__all__ = ['ApiJobBinding', 'CONTINUATION', 'TARGET']
