"""Assemble a root Workflow from its recorded caller bindings."""
from __future__ import annotations
from collections.abc import Mapping
from .episode_journal import WorkflowError
from .episode_application_services import service_binding
from .episode_bindings import native_job_event_configuration
from .runtime import Workflow
from .workflow_values import _annotation_child_roles, _decision_protocol, EPISODE_BRANCH_LIFECYCLE
from .saved_run_configuration import _credit_binding_from_settings, _recorded_annotation_child_roles

_DEFAULT_DECISION_PROTOCOL = object()

def assemble_workflow(store, tools, provider, directory, run_id, settings, *,
                      controller_factory, project_credit, project_child_credit=None,
                      project_annotation_score=None, job_episodes=None,
                      execution_expectations=None, resource_estimator=None,
                      native_timing_information=None, initial_known_record_refs=None,
                      episode_binding_factories=None, episode_binding_descriptors=None,
                      role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                      episode_service_factory=None, episode_service_binding=None,
                      episode_record_receipts=False, native_job_events=None,
                      episode_service_inputs=None, annotation_child_roles=None,
                      decision_protocol=_DEFAULT_DECISION_PROTOCOL, episode_binding_owners=None):
    """Compose the same binding for a root or one independently placed child.

    Configuration validation belongs to the caller's recorded binding/factory.
    This function starts no episode, provider process, native job or controller.
    """
    from .saved_private_binding_catalogue import validate_saved_catalogue
    owned = validate_saved_catalogue(settings)
    if owned is not None and tuple(episode_binding_owners or ()) != tuple(row['owner'] for row in owned[1]):
        raise WorkflowError('resumption_requires_original_episode_binding_owners')
    bindings, versions = settings['bindings'], settings['binding_versions']
    saved_protocol = _decision_protocol(settings.get('decision_protocol'))
    if decision_protocol is _DEFAULT_DECISION_PROTOCOL:
        decision_protocol = saved_protocol
    elif _decision_protocol(decision_protocol) != saved_protocol:
        raise WorkflowError('resumption_requires_original_decision_protocol')
    annotation_child_roles = _annotation_child_roles(annotation_child_roles)
    if annotation_child_roles != _recorded_annotation_child_roles(settings):
        raise WorkflowError('resumption_requires_original_annotation_child_roles')
    saved_services = settings.get('episode_application_services')
    if (episode_service_inputs is not None or isinstance(saved_services, Mapping)
            and saved_services.get('version') == 'episode_application_services_v2') and service_binding(
            episode_service_factory, episode_service_binding, inputs=episode_service_inputs) != saved_services:
        raise WorkflowError('resumption_requires_original_episode_application_services')
    native_job_events = native_job_event_configuration(native_job_events)
    if settings.get('native_job_events') != native_job_events:
        raise WorkflowError('resumption_requires_original_native_job_events')
    if type(episode_record_receipts) is not bool:
        raise TypeError('episode_record_receipts_must_be_bool')
    expected_receipts = ({'version': 'explicit_store_record_receipts_v1', 'enabled': True}
                        if episode_record_receipts else None)
    if settings.get('episode_record_receipts') != expected_receipts:
        raise WorkflowError('resumption_requires_original_episode_record_receipts')
    if settings.get('wait_inputs') != {'version': 'wait_inputs_binding_v2'}:
        raise WorkflowError('unsupported_wait_inputs_binding')
    wait_inputs_version = settings['wait_inputs']['version']
    if settings.get('completed_action_inputs') != {'version': 'completed_action_inputs_binding_v1'}:
        raise WorkflowError('unsupported_completed_action_inputs_binding')
    completed_action_inputs_version = settings['completed_action_inputs']['version']
    episode_branch_lifecycle = None
    if 'episode_branch_lifecycle' in settings:
        if settings['episode_branch_lifecycle'] != {'version': EPISODE_BRANCH_LIFECYCLE}:
            raise WorkflowError('unsupported_episode_branch_lifecycle')
        episode_branch_lifecycle = EPISODE_BRANCH_LIFECYCLE
    return Workflow(store, tools, provider, directory, run_id, controller_factory, project_credit,
                        credit_binding=_credit_binding_from_settings(settings),
                        restoration_settings=settings["restoration"],
                        execution_expectations=execution_expectations, job_episodes=job_episodes,
                        resource_estimator=resource_estimator,
                        native_timing_information=native_timing_information,
                        initial_known_record_refs=initial_known_record_refs,
                        episode_binding_factories=episode_binding_factories,
                        episode_binding_descriptors=episode_binding_descriptors,
                        episode_binding_owners=episode_binding_owners,
                        role_credit_bindings=role_credit_bindings,
                        job_progress_provider=job_progress_provider,
                        execution_binding=execution_binding,
                        episode_service_factory=episode_service_factory,
                        episode_service_binding=episode_service_binding,
                        episode_service_inputs=episode_service_inputs,
                        annotation_child_roles=annotation_child_roles,
                        decision_protocol=decision_protocol,
                        root_action_boundary=settings.get('root_action_boundary'),
                        episode_branch_lifecycle=episode_branch_lifecycle,
                        episode_record_receipts=episode_record_receipts,
                        native_job_events=native_job_events,
                        progress_receipt_order=settings.get('episode_progress_receipts', {}).get('version'),
                        wait_inputs_version=wait_inputs_version,
                        completed_action_inputs_version=completed_action_inputs_version,
                        project_annotation_score=project_annotation_score,
                        annotation_score_binding=({'projector': bindings['annotation_score'],
                            'versions': versions['annotation_score'],
                            'definition': settings.get('binding_definitions', {}).get('annotation_score'),
                            'scope_source': 'context.scope',
                            'meaning': 'Annotation support, separately bound from investigation progress and numerical yield.'}
                            if project_annotation_score is not None else None),
                        project_child_credit=project_child_credit,
                        child_credit_binding=({"kind": "custom",
                            "projector": settings["bindings"]["scientific_child_credit"],
                            "versions": settings["binding_versions"]["scientific_child_credit"],
                            "definition": settings.get("binding_definitions", {}).get("scientific_child_credit"),
                            "scope_source": "context.scope", "assignment_source": "original_parent_commission",
                            "meaning": "Local scientific investigation credit; not an additive parent task score."}
                            if project_child_credit is not None else None),
                        controller_binding={"factory": settings["bindings"]["controller"],
                            "versions": settings["binding_versions"]["controller"],
                            "definition": (settings.get("binding_definitions", {}).get("controller")
                                if settings["controller"] is None else settings["controller"])})


