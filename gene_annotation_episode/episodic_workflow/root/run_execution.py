"""Execute or resume the original recorded root investigation."""
from __future__ import annotations
import asyncio
from collections.abc import Mapping
import json
import uuid
from .episode_journal import Journal, WorkflowError
from .episode_application_services import service_binding
from .episode_bindings import native_job_event_configuration
from .decision_context import PROTOCOL as DECISION_EXCHANGE_PROTOCOL
from .composition_information import ROOT_BOUNDARY_VERSION
from .episode_receipts import RECEIPT_VERSION
from .execution_expectations import ExecutionExpectations
from .resource_estimation import ResourceToolEstimator
from .native_timing_information import NativeTimingInformation
from .task_values import _plain, _json
from .workflow_values import (_now, _annotation_child_roles, _decision_protocol,
    _binding_name, _effective_restoration_configuration, EPISODE_BRANCH_LIFECYCLE)
from .saved_run_configuration import (_recorded_annotation_child_roles, _run_location,
    _has_explicit_model_configuration, _effective_models, _effective_configuration,
    controller_from_settings)
from .saved_run_assembly import assemble_workflow, _DEFAULT_DECISION_PROTOCOL

DEFAULT_GOAL = ("Improve the annotation and biological interpretation of the supplied material "
                "through evidence-linked, context-dependent reasoning. Retain competing explanations, "
                "investigate useful distinctions and revise actual annotation state.")

async def run_workflow(store, tools, *, provider=None, provider_config=None,
                       run_dir=None, resume=False, controller_settings=None,
                       credit_policy=None, controller_factory=None, project_credit=None,
                       goal=None, restoration_settings=None, execution_expectations=None,
                       job_episodes=None, binding_definitions=None, project_child_credit=None,
                       resource_estimator=None, project_annotation_score=None,
                       initial_known_record_refs=None, native_timing_information=None,
                       episode_binding_factories=None, episode_binding_descriptors=None,
                       role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                       episode_service_factory=None, episode_service_binding=None,
                       episode_record_receipts=False, native_job_events=None,
                       episode_service_inputs=None, annotation_child_roles=None,
                       decision_protocol=_DEFAULT_DECISION_PROTOCOL, episode_binding_owners=None):
    """Bind standard scientific channels or execute the caller's explicit policy.

    Standard continuation uses received investigation progress. Annotation
    scoring requires a separate explicit numerical projector; the retired
    categorical credit_policy configuration is not an annotation scorer.
    Both routes execute the same shared runtime below.
    """
    options = dict(provider=provider, provider_config=provider_config, run_dir=run_dir,
        resume=resume, controller_settings=controller_settings, credit_policy=credit_policy,
        controller_factory=controller_factory, project_credit=project_credit, goal=goal,
        restoration_settings=restoration_settings, execution_expectations=execution_expectations,
        job_episodes=job_episodes, binding_definitions=binding_definitions,
        project_child_credit=project_child_credit, resource_estimator=resource_estimator,
        project_annotation_score=project_annotation_score,
        initial_known_record_refs=initial_known_record_refs,
        native_timing_information=native_timing_information,
        episode_binding_factories=episode_binding_factories,
        episode_binding_descriptors=episode_binding_descriptors,
        role_credit_bindings=role_credit_bindings, job_progress_provider=job_progress_provider,
        execution_binding=execution_binding,
        episode_record_receipts=episode_record_receipts,
        native_job_events=native_job_events,
        episode_service_factory=episode_service_factory, episode_service_binding=episode_service_binding,
        episode_service_inputs=episode_service_inputs, annotation_child_roles=annotation_child_roles,
        decision_protocol=decision_protocol, episode_binding_owners=episode_binding_owners)
    if project_credit is None:
        from .default_scientific_binding import bind_default_science
        options.update(bind_default_science(store, run_dir=run_dir, resume=resume,
            provider_config=provider_config, credit_policy=credit_policy,
            initial_known_record_refs=initial_known_record_refs,
            project_child_credit=project_child_credit,
            project_annotation_score=project_annotation_score,
            binding_definitions=binding_definitions))
    return await _run_bound_workflow(store, tools, **options)


async def _run_bound_workflow(store, tools, *, provider=None, provider_config=None,
                       run_dir=None, resume=False, controller_settings=None,
                       credit_policy=None, controller_factory=None, project_credit=None,
                       goal=None, restoration_settings=None, execution_expectations=None,
                       job_episodes=None, binding_definitions=None, project_child_credit=None,
                       resource_estimator=None, project_annotation_score=None,
                       initial_known_record_refs=None, native_timing_information=None,
                       episode_binding_factories=None, episode_binding_descriptors=None,
                       role_credit_bindings=None, job_progress_provider=None, execution_binding=None,
                       episode_service_factory=None, episode_service_binding=None,
                       episode_record_receipts=False, native_job_events=None,
                       episode_service_inputs=None, annotation_child_roles=None,
                       decision_protocol=_DEFAULT_DECISION_PROTOCOL, episode_binding_owners=None):
    """Run or reconstruct one durable method_loop investigation.

    Resumption replays saved selections and committed results through the same
    generic Episode tree. Work with an operation key is recovered idempotently
    if publication preceded the runtime response journal. Controller histories
    are reconstructed from those original cumulative scores, never from a
    freshly remeasured score for historical work.
    """
    if not callable(project_credit):
        raise TypeError('runtime_requires_bound_credit_projector')
    if type(episode_record_receipts) is not bool:
        raise TypeError('episode_record_receipts_must_be_bool')
    requested_receipts = ({'version': 'explicit_store_record_receipts_v1', 'enabled': True}
                          if episode_record_receipts else None)
    requested_native_events = native_job_event_configuration(native_job_events)
    if requested_native_events is not None and job_episodes is None:
        raise ValueError('native_job_events_requires_job_binding')
    annotation_child_roles = _annotation_child_roles(annotation_child_roles)
    requested_services = service_binding(episode_service_factory, episode_service_binding,
        inputs=episode_service_inputs)
    if episode_binding_owners is not None and requested_services is not None:
        raise ValueError('owned_private_bindings_require_explicit_factories')
    if requested_services is not None and any(value is not None for value in
            (episode_binding_factories, episode_binding_descriptors, role_credit_bindings, job_progress_provider)):
        raise ValueError('episode_service_factory_and_direct_services_are_exclusive')
    if episode_binding_descriptors is not None and episode_binding_factories is not None:
        raise ValueError('episode_descriptors_and_factories_are_exclusive')
    from .numerical import YieldController, ESTIMATOR_VERSION, SOURCE_SHA256
    from .providers import ModelConnection

    directory, run_id = _run_location(store, run_dir, resume)
    journal = Journal(store, run_id)
    old = journal.row("runtime_runs")
    if decision_protocol is _DEFAULT_DECISION_PROTOCOL:
        decision_protocol = (json.loads(old['settings']).get('decision_protocol') if old else
            DECISION_EXCHANGE_PROTOCOL if provider is None or isinstance(provider, ModelConnection) else None)
    decision_protocol = _decision_protocol(decision_protocol)
    if old and decision_protocol != json.loads(old['settings']).get('decision_protocol'):
        raise WorkflowError('resumption_requires_original_decision_protocol')
    if native_timing_information is not None and type(native_timing_information) is not NativeTimingInformation:
        raise TypeError('typed_native_timing_information_required')
    saved_native_information = (json.loads(old['settings']).get('native_timing_information') if old else None)
    if old and json.loads(old['settings']).get('episode_record_receipts') != requested_receipts:
        raise WorkflowError('resumption_requires_original_episode_record_receipts')
    if old and json.loads(old['settings']).get('native_job_events') != requested_native_events:
        raise WorkflowError('resumption_requires_original_native_job_events')
    uses_receipts = (episode_record_receipts or native_timing_information is not None or saved_native_information is not None or any(
        getattr(projector, 'requires_episode_receipts', False) for projector in (project_credit, project_child_credit)))
    if initial_known_record_refs is not None:
        if (not uses_receipts or not isinstance(initial_known_record_refs, (list, tuple))
                or not all(isinstance(ref, str) for ref in initial_known_record_refs)):
            raise ValueError('explicit_initial_known_record_references_require_receipt_binding')
        initial_known_record_refs = sorted(set(initial_known_record_refs))
        for reference in initial_known_record_refs:
            store.get(reference)
    if provider_config is not None and not isinstance(provider_config, Mapping):
        raise TypeError("provider_config must be a mapping")
    configured_controller = ({} if provider_config is None else provider_config).get("controller", {})
    if controller_factory is not None and (controller_settings is not None or configured_controller):
        raise ValueError("custom_controller_owns_its_configuration_use_binding_definitions")
    configured_credit = ({} if provider_config is None else provider_config).get("credit")
    if project_credit is not None and (credit_policy is not None or configured_credit is not None):
        raise ValueError("custom_projector_owns_its_configuration_use_binding_definitions")
    if project_child_credit is not None and not callable(project_child_credit):
        raise TypeError("scientific_child_credit_projector_must_be_callable")
    if project_annotation_score is not None and not callable(project_annotation_score):
        raise TypeError("annotation_score_projector_must_be_callable")
    if binding_definitions is not None:
        binding_definitions = _plain(binding_definitions)
        if not isinstance(binding_definitions, dict) or set(binding_definitions) - {"credit", "controller", "scientific_child_credit", "annotation_score"}:
            raise ValueError("invalid_custom_binding_definitions")
        if any(not isinstance(value, dict) or not value for value in binding_definitions.values()):
            raise ValueError("nonempty_binding_definition_required")
        if ("credit" in binding_definitions and project_credit is None or
                "controller" in binding_definitions and controller_factory is None or
                "scientific_child_credit" in binding_definitions and project_child_credit is None or
                "annotation_score" in binding_definitions and project_annotation_score is None):
            raise ValueError("binding_definition_requires_its_custom_executable")
        binding_definitions = json.loads(_json(binding_definitions))
    if job_episodes is not None:
        from .library.homology_episode_family import HomologyEpisodes
        if type(job_episodes) is not HomologyEpisodes:
            raise TypeError("typed_homology_episode_binding_required")
        if controller_factory is None or project_credit is None:
            raise ValueError("job_episode_run_requires_explicit_controller_and_task_credit_bindings")
    if execution_expectations is not None and type(execution_expectations) is not ExecutionExpectations:
        raise TypeError("typed_execution_expectation_binding_required")
    if resource_estimator is not None and type(resource_estimator) is not ResourceToolEstimator:
        raise TypeError("typed_resource_tool_estimator_required")
    problem = _plain(store.problem())
    tool_resources = _plain(tools.resource_binding()) if callable(getattr(tools, "resource_binding", None)) else {}
    bindings = {"controller": _binding_name(controller_factory, "gene_annotation_episode.episodic_workflow.root.numerical.YieldController"),
                "credit": _binding_name(project_credit, "caller_injected")}
    versions = {
        "controller": ({"estimator_version": ESTIMATOR_VERSION, "template_sha256": SOURCE_SHA256}
                       if controller_factory is None else {"requirement": "same_caller_injected_executable"}),
        "credit": {"requirement": "same_caller_injected_executable"},
    }
    if project_child_credit is not None:
        bindings["scientific_child_credit"] = _binding_name(project_child_credit, "caller_injected")
        versions["scientific_child_credit"] = {"requirement": "same_caller_injected_executable"}
    if project_annotation_score is not None:
        bindings['annotation_score'] = _binding_name(project_annotation_score, 'caller_injected')
        versions['annotation_score'] = {'requirement': 'same_caller_injected_executable'}
    if resume:
        if old is None:
            raise WorkflowError("run manifest is not registered in this Store")
        settings = json.loads(old["settings"])
        from .saved_private_binding_catalogue import validate_saved_catalogue, saved_private_factories
        owned = validate_saved_catalogue(settings)
        if owned is None:
            if episode_binding_owners is not None:
                raise WorkflowError('resumption_cannot_add_episode_binding_owners')
        else:
            expected_owners = tuple(row['owner'] for row in owned[1])
            if episode_binding_owners is not None and tuple(episode_binding_owners) != expected_owners:
                raise WorkflowError('resumption_requires_original_episode_binding_owners')
            if requested_services is not None:
                raise WorkflowError('owned_private_service_reconstruction_unavailable')
            if episode_binding_descriptors is not None and _plain(episode_binding_descriptors) != settings['episode_bindings']:
                raise WorkflowError('resumption_requires_original_episode_bindings')
            if episode_binding_factories is None:
                episode_binding_factories, _ = saved_private_factories(settings)
            episode_binding_descriptors = None
            episode_binding_owners = expected_owners
        if annotation_child_roles != _recorded_annotation_child_roles(settings):
            raise WorkflowError('resumption_requires_original_annotation_child_roles')
        if requested_services != settings.get('episode_application_services'):
            raise WorkflowError('resumption_requires_original_episode_application_services')
        if (native_timing_information is not None
                and native_timing_information.as_record() != settings.get('native_timing_information')):
            raise WorkflowError('resumption_cannot_replace_native_timing_information')
        native_timing_information = (NativeTimingInformation.from_record(settings['native_timing_information'])
            if settings.get('native_timing_information') is not None else None)
        saved_knowledge = settings.get('scientific_knowledge')
        if uses_receipts:
            if saved_knowledge is None or saved_knowledge['version'] != RECEIPT_VERSION:
                raise WorkflowError('resumption_requires_original_scientific_receipt_binding')
            if (initial_known_record_refs is not None
                    and initial_known_record_refs != saved_knowledge['initial_known_record_refs']):
                raise WorkflowError('resumption_cannot_change_initial_scientific_knowledge')
            initial_known_record_refs = saved_knowledge['initial_known_record_refs']
        elif saved_knowledge is not None:
            raise WorkflowError('resumption_cannot_remove_scientific_receipt_binding')
        if binding_definitions is not None and binding_definitions != settings.get("binding_definitions", {}):
            raise WorkflowError("resumption cannot replace the run's custom binding definitions")
        saved_jobs = settings.get("job_episodes")
        if (None if job_episodes is None else job_episodes.as_record()) != saved_jobs:
            raise WorkflowError("resumption requires the original job episode resources and scoring binding")
        saved_expectations = settings.get("execution_expectations")
        if execution_expectations is not None and execution_expectations.as_record() != saved_expectations:
            raise WorkflowError("resumption cannot replace the run's execution expectation binding")
        execution_expectations = (ExecutionExpectations.from_record(saved_expectations)
                                  if saved_expectations is not None else None)
        saved_resource_estimator = settings.get("resource_tool_estimator")
        if resource_estimator is not None and resource_estimator.as_record() != saved_resource_estimator:
            raise WorkflowError("resumption cannot replace the run's resource/tool estimator")
        resource_estimator = (ResourceToolEstimator.from_record(saved_resource_estimator)
                              if saved_resource_estimator is not None else None)
        if settings["problem"] != problem or settings["directory"] != str(directory):
            raise WorkflowError("saved run belongs to different immutable material or directory")
        if settings["bindings"] != bindings:
            raise WorkflowError("resumption requires the same controller and credit bindings")
        if settings["binding_versions"] != versions:
            raise WorkflowError("saved scientific score or estimator version differs; history cannot be mixed")
        if "restoration" not in settings:
            raise WorkflowError("saved run requires its original restoration binding and code snapshot")
        _effective_restoration_configuration(base=settings["restoration"])
        if restoration_settings is not None or (provider_config is not None and "restoration" in provider_config):
            requested = _effective_restoration_configuration(provider_config, restoration_settings,
                                                               base=settings["restoration"])
            if requested != settings["restoration"]:
                raise WorkflowError("resumption cannot replace the run's restoration settings")
        if provider_config is not None or controller_settings is not None:
            supplied = {} if provider_config is None else provider_config
            requested_controller = (None if controller_factory is not None else
                {**settings["controller"], **supplied.get("controller", {}),
                 **({} if controller_settings is None else controller_settings)})
            requested_config = settings["models"] if provider_config is None else provider_config
            if provider_config is not None and not _has_explicit_model_configuration(supplied):
                requested_config = {**supplied, "models": settings["models"]}
            if controller_factory is None:
                models, controller = _effective_configuration(requested_config, requested_controller)
            else:
                models, controller = _effective_models(requested_config), None
            if provider_config is not None and models != settings["models"]:
                raise WorkflowError("resumption cannot replace the run's model settings")
            if controller != settings["controller"]:
                raise WorkflowError("resumption cannot replace the run's controller settings")
        if goal is not None and goal != settings["goal"]:
            raise WorkflowError("resumption cannot replace the run's immutable goal")
        if old["state"] in ('yielded', 'yielded_with_pending_work') and old["summary"] is not None:
            # Resuming an already yielded run is inspection, not a new epoch.
            # Its historical score must not be rewritten from a later run's
            # modifications to the same scientific Store.
            return json.loads(old["summary"])
    else:
        if uses_receipts and initial_known_record_refs is None:
            raise ValueError('receipt_binding_requires_explicit_initial_known_record_refs')
        if controller_factory is None:
            models, controller = _effective_configuration(provider_config, controller_settings)
        else:
            models, controller = _effective_models(provider_config), None
        settings = {"schema_version": 1, "directory": str(directory), "problem": problem,
                    "models": models, "controller": controller,
                    "credit_policy": None,
                    "goal": DEFAULT_GOAL if goal is None else goal, "bindings": bindings,
                    "binding_versions": versions,
                    "initial_tool_resources": tool_resources,
                    "restoration": _effective_restoration_configuration(provider_config, restoration_settings)}
        settings['episode_progress_receipts'] = {'version': 'received_progress_order_v1'}
        settings['root_action_boundary'] = ROOT_BOUNDARY_VERSION
        settings['wait_inputs'] = {'version': 'wait_inputs_binding_v2'}
        settings['completed_action_inputs'] = {'version': 'completed_action_inputs_binding_v1'}
        settings['episode_branch_lifecycle'] = {'version': EPISODE_BRANCH_LIFECYCLE}
        if decision_protocol is not None:
            settings['decision_protocol'] = decision_protocol
        if requested_services is not None:
            settings['episode_application_services'] = requested_services
        if annotation_child_roles is not None:
            settings['annotation_child_roles'] = list(annotation_child_roles)
        if requested_receipts is not None:
            settings['episode_record_receipts'] = requested_receipts
        if requested_native_events is not None:
            settings['native_job_events'] = requested_native_events
        if binding_definitions is not None:
            settings["binding_definitions"] = binding_definitions
        if uses_receipts:
            settings['scientific_knowledge'] = {'version': RECEIPT_VERSION,
                'initial_known_record_refs': initial_known_record_refs}
        if execution_expectations is not None:
            settings["execution_expectations"] = execution_expectations.as_record()
        if resource_estimator is not None:
            settings["resource_tool_estimator"] = resource_estimator.as_record()
        if native_timing_information is not None:
            settings['native_timing_information'] = native_timing_information.as_record()
        if job_episodes is not None:
            settings["job_episodes"] = job_episodes.as_record()
        journal.save("runtime_runs", {"settings": _json(settings), "state": "created",
            "summary": None, "started_at": _now(), "updated_at": _now()})
        (directory / "run.json").write_text(_json({"run_id": run_id, **settings}) + "\n")

    if controller_factory is None:
        controller_factory = controller_from_settings(settings)

    # Validate against the actual registered roles during Workflow assembly,
    # including caller-constructed scientific processes. Assembly precedes
    # opening the provider transport below.
    owned_provider = provider is None
    if owned_provider:
        # Each resumption gets a separate transport audit directory. Scientific
        # action identities and the authoritative state remain the same.
        transports = directory / "providers"
        transports.mkdir(exist_ok=True)
        provider = ModelConnection(settings["models"], transports / uuid.uuid4().hex, directory,
            image_resolver=getattr(tools, "resolve_image_input", None))
    recover_service_publication = (resume and requested_services is not None
        and 'episode_bindings' not in settings and old['state'] == 'created'
        and old['summary'] is None and store.db.execute(
            'SELECT 1 FROM runtime_episodes WHERE run_id=? LIMIT 1', (run_id,)).fetchone() is None)
    if resume and 'episode_bindings' not in settings:
        if not recover_service_publication and (episode_binding_factories is not None or episode_binding_descriptors is not None
                or episode_service_factory is not None):
            raise WorkflowError('resumption_cannot_add_episode_bindings')
        if not recover_service_publication:
            episode_binding_factories = ()
    elif resume and episode_binding_factories is None and episode_service_factory is None:
        saved_descriptors = settings['episode_bindings']
        if episode_binding_descriptors is not None and _plain(episode_binding_descriptors) != saved_descriptors:
            raise WorkflowError('resumption_requires_original_episode_bindings')
        episode_binding_descriptors = saved_descriptors
    workflow = assemble_workflow(store, tools, provider, directory, run_id, settings,
        controller_factory=controller_factory, project_credit=project_credit,
        project_child_credit=project_child_credit, project_annotation_score=project_annotation_score,
        job_episodes=job_episodes, execution_expectations=execution_expectations,
        resource_estimator=resource_estimator, native_timing_information=native_timing_information,
        initial_known_record_refs=initial_known_record_refs,
        episode_binding_factories=episode_binding_factories,
        episode_binding_descriptors=episode_binding_descriptors,
        role_credit_bindings=role_credit_bindings, job_progress_provider=job_progress_provider,
        episode_record_receipts=episode_record_receipts,
        native_job_events=requested_native_events,
        episode_service_factory=episode_service_factory, episode_service_binding=episode_service_binding,
        episode_service_inputs=episode_service_inputs, annotation_child_roles=annotation_child_roles,
        decision_protocol=decision_protocol, episode_binding_owners=episode_binding_owners)
    selected_bindings = workflow.episode_bindings.as_record()
    from .saved_private_binding_catalogue import catalogue_for_registry
    selected_owners = workflow.episode_bindings.owner_records()
    selected_catalogue = catalogue_for_registry(workflow.episode_bindings)
    selected_role_bindings = {role: {'definition': _plain(definition),
        'projector': _binding_name(workflow.role_credit_projectors[role], 'caller_injected')}
        for role, definition in workflow.role_credit_definitions.items()}
    if resume and not recover_service_publication:
        if (_json(selected_owners) != _json(settings.get('episode_binding_owners'))
                or _json(selected_catalogue) != _json(settings.get('episode_binding_catalogue'))):
            raise WorkflowError('resumption_requires_original_episode_binding_owners')
        if selected_bindings != settings.get('episode_bindings', []):
            raise WorkflowError('resumption_requires_original_episode_bindings')
        if selected_role_bindings != settings.get('episode_role_credit_bindings', {}):
            raise WorkflowError('resumption_requires_original_episode_role_credit_bindings')
        if (requested_services is not None and workflow.episode_job_progress_provider_binding
                != settings.get('episode_job_progress_provider')):
            raise WorkflowError('resumption_requires_original_episode_job_progress_provider')
    else:
        settings['episode_bindings'] = selected_bindings
        if selected_owners is not None:
            settings['episode_binding_owners'] = selected_owners
            settings['episode_binding_catalogue'] = selected_catalogue
        if selected_role_bindings:
            settings['episode_role_credit_bindings'] = selected_role_bindings
        if requested_services is not None:
            settings['episode_job_progress_provider'] = workflow.episode_job_progress_provider_binding
        previous = journal.row('runtime_runs')
        journal.save('runtime_runs', {'settings': _json(settings), 'state': previous['state'],
            'summary': previous['summary'], 'started_at': previous['started_at'],
            'updated_at': previous['updated_at']})
        (directory / 'run.json').write_text(_json({'run_id': run_id, **settings}) + '\n')
    from .application_execution_binding import bind_episode_execution
    # A model connection supplies decisions, not permission to place each
    # Episode in an independent worker. Ordinary children use the calling
    # process; separate placement requires the caller's execution binding.
    execution = bind_episode_execution(store, directory, settings=settings,
        requested_binding=execution_binding,
        use_saved_runtime=False,
        tool_configuration=getattr(tools, 'reconstruction_configuration', None), resume=resume)
    settings = execution.settings
    workflow.configure_execution(execution.runtime_binding)
    if owned_provider:
        await provider.__aenter__()
    scope = store.validate_scope({"subject_refs": problem["subject_refs"]})
    root = workflow.build("annotation", "root", settings["goal"], scope)
    def save_state(state, summary=None):
        prior = journal.row("runtime_runs")
        journal.save("runtime_runs", {"settings": prior["settings"], "state": state,
            "summary": None if summary is None else _json(summary),
            "started_at": prior["started_at"], "updated_at": _now()})
    save_state("running")
    try:
        record = await root.run_async(workflow.context)
        await root.build_result(record)
        final_credit_view = workflow.source_credit_view(root.source)
        pending_handles = workflow.pending_handles(root.source)
        if pending_handles:
            raise WorkflowError('workflow_cannot_finalize_with_unaccounted_owned_work')
        closed_state = 'yielded'
        summary = {"run_id": run_id, "directory": str(directory), "state": closed_state,
            'pending_handles': pending_handles,
            "ended_by": record.ended_by, "scientific_completion": "not_established_by_termination",
            "completed_actions": record.units_consumed, "credit": final_credit_view['credit'],
            "episode_count": store.db.execute("SELECT COUNT(*) FROM runtime_episodes WHERE run_id=?", (run_id,)).fetchone()[0],
            "pending_report_deliveries": store.db.execute("SELECT COUNT(*) FROM runtime_report_attempts a "
                "WHERE a.run_id=? AND a.failure IS NOT NULL AND a.decision_index=(SELECT MAX(b.decision_index) "
                "FROM runtime_report_attempts b WHERE b.run_id=a.run_id AND b.delivery_ref=a.delivery_ref)", (run_id,)).fetchone()[0]}
        if 'monitoring_information_credit' in final_credit_view:
            summary.update({key: final_credit_view[key] for key in
                ('monitoring_information_credit', 'monitoring_information_binding')})
        if project_annotation_score is not None:
            annotation = workflow.annotation_context(scope, source=root.source)
            for key in ('annotation_score', 'annotation_support', 'annotation_opposition',
                        'proposed_annotations', 'annotation_comparisons'):
                if key in annotation:
                    summary[key] = annotation[key]
        else:
            summary['annotation_score_status'] = 'unavailable_no_scorer_bound'
        save_state(closed_state, summary)
        (directory / "summary.json").write_text(_json(summary) + "\n")
        return summary
    except BaseException as error:
        state = "interrupted" if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else "operational_failure"
        save_state(state, {"error_type": type(error).__name__, "detail": str(error)})
        raise
    finally:
        # Retire every process/conversation including suspended parents when
        # an interruption unwinds the generic tree. Journals stay on disk.
        ids = [row[0] for row in store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=?", (run_id,))]
        for episode_id in ids:
            await workflow.release(episode_id)
        if owned_provider:
            await provider.__aexit__(None, None, None)


