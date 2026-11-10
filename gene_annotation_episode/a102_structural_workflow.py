"""Explicit merged A102 composition over the configured execution services.

The old a102_investigation entry points are unchanged. Selecting this factory
and subtree opts a new run into the broader scientific contract.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import json
from pathlib import Path

from .a102_investigation import A102ServiceFactory, A102Subtree
from .a102_structural_evidence import VERSION, is_merged_entry, task_context, finding_progress
from .a102_structural_report import report_schema, initial_report
from .communication import interpretation_schema, plain, validate_closed_schema, validate_form
from .domain import ContractError
from .scientific_process_library import ScientificProcessLibrary
from .scientific_tool_library import ScientificToolLibrary


def _require_merged_library(library):
    if (not is_merged_entry(library.resolve(library.reference('A102')))
            or any(row['option_ref']['option_id'] == 'A111' for row in library.headers())):
        raise ContractError('a102_merged_structural_evidence_catalog_required')


class A102StructuralEvidenceSubtree(A102Subtree):
    """Commission either structural path under the same published A102 owner."""

    def __init__(self, run_directory):
        directory = Path(run_directory)
        self.library = ScientificProcessLibrary(directory / 'scientific-process-library')
        self.tools = ScientificToolLibrary(directory / 'scientific-tool-library')
        _require_merged_library(self.library)
        self.axis = self.library.reference('A102')

    def commission(self, store, *, target_ref, scope, completeness, child_tool_info,
                   question, task='synthesis', thought_id='P01', evidence_refs=(),
                   constraints=None, context=None, schema=None, initial=None):
        selected_task = task_context(task)
        if completeness not in {'complete', 'fragment', 'unknown'}:
            raise ContractError('a102_material_completeness_required')
        if type(question) is not str or not question.strip():
            raise ContractError('a102_question_required')
        scope = store.validate_scope(plain(scope))
        target = store.get(target_ref)
        if (target['record_type'] not in {'input', 'feature', 'product', 'read_subject'}
                or store.subject_molecule(target_ref) != 'protein'
                or not store.scope_covers(store.coverage(target_ref), scope)):
            raise ContractError('a102_material_outside_scope_or_not_protein')
        refs = list(dict.fromkeys([target_ref, *evidence_refs]))
        if set(store.reference_subset(refs, scope)) != set(refs):
            raise ContractError('a102_evidence_outside_scope')
        supplied = plain(context or {})
        if 'a102_material' in supplied or 'a102_task' in supplied:
            raise ContractError('a102_material_context_reserved')
        supplied['a102_material'] = {'version': VERSION, 'subject_ref': target_ref,
            'supplied_length': store.subject_length(target_ref), 'completeness': completeness,
            'original_intervals': store.coverage(target_ref)}
        supplied['a102_task'] = selected_task
        schema = report_schema() if schema is None else deepcopy(schema)
        validate_closed_schema(schema)
        initial = initial_report() if initial is None else deepcopy(initial)
        validate_form(initial, interpretation_schema(schema), lambda ref, namespace:
            ref in store.reference_subset([ref], scope)
            and (namespace is None or store.get(ref)['record_type'] == namespace))
        return {'kind': 'episode_child', 'role': 'scientific_process', 'goal': question,
            'scope': scope, 'purpose': 'Return structural findings, applicable comparative records '
                'and experimental numerical cells with their original meanings, scope and dependencies.',
            'schema_json': json.dumps(schema, allow_nan=False),
            'initial_report_json': json.dumps(initial, allow_nan=False),
            'assignment': {'selection': self.selection(child_tool_info=child_tool_info, thought_id=thought_id),
                'evidence_refs': refs, 'constraints': plain(constraints or {}), 'context': supplied}}


@dataclass(frozen=True)
class A102StructuralEvidenceServiceFactory(A102ServiceFactory):
    """Add experimental readers/delivery around the current native service factory.

    Native tools and resource operations stay with their configured factories.
    An explicit ExecutionServiceFactory supplies the current execution/HPC
    composition; otherwise the original A102 factory remains the entry point.
    """

    execution_service_factory: object | None = None

    def _execution_services(self, store, *, run_id, directory, tool_catalog,
                            job_episodes, resource_estimator, tool_registry):
        from .episode_application_services import EpisodeApplicationServices
        from .execution_service_setup import ExecutionServiceFactory
        from .execution_episodes import ExecutionEpisodes
        from .episode_monitoring import MonitorEpisodes
        from .literature_episodes import LiteratureEpisodes
        from .scientific_process_setup import prepare_scientific_binding
        factory = self.execution_service_factory
        if not isinstance(factory, ExecutionServiceFactory):
            raise TypeError('a102_explicit_execution_service_factory_required')
        # This existing public factory owns resource configuration, HPC sister
        # branches, result readers, monitoring, and execution-memory wiring.
        execution = factory(store, run_id=run_id, directory=directory,
            tool_catalog=tool_catalog, tool_registry=tool_registry,
            job_episodes=job_episodes, resource_estimator=resource_estimator)
        configure_hpc = getattr(tool_registry, 'configure_a102_hpc', None)
        if factory.hpc_commissions is not None:
            if not callable(configure_hpc):
                raise ContractError('a102_hpc_requires_actual_structural_tool_registry')
            configure_hpc(factory.resources)
        descriptors = (*execution.episode_binding_descriptors, *self.additional_descriptors)
        ids = [descriptor['binding_id'] for descriptor in descriptors]
        if len(ids) != len(set(ids)) or {'scientific_process', 'literature'}.intersection(ids):
            raise ContractError('a102_execution_binding_conflict')
        bindings = dict(self.additional_role_credit_bindings or {})
        if set(bindings).intersection(execution.role_credit_bindings):
            raise ContractError('a102_execution_role_credit_conflict')
        bindings.update(execution.role_credit_bindings)
        if self.job_progress_provider is not None:
            raise ContractError('a102_execution_progress_provider_already_configured')
        catalogs = deepcopy(self.resource_tool_catalogs or {})
        for resource, rows in (execution.resource_tool_catalogs or {}).items():
            if resource in catalogs and catalogs[resource] != rows:
                raise ContractError('a102_execution_resource_catalog_conflict')
            catalogs[resource] = deepcopy(rows)
        roles = ['scientific_process', 'literature',
            *ExecutionEpisodes.entry_roles, *MonitorEpisodes.entry_roles]
        if factory.hpc_commissions is not None:
            from .hpc_episodes import HPCEpisodes
            roles.extend(HPCEpisodes.entry_roles)
        for descriptor in self.additional_descriptors:
            roles.extend(descriptor.get('roles', ()))
        scientific = prepare_scientific_binding(run_directory=directory,
            source_directory=self.source_directory,
            tool_catalog=tool_registry.catalog() if tool_registry is not None else tool_catalog,
            child_roles=tuple(dict.fromkeys(roles)), tool_retrieval=self.tool_retrieval,
            resource_catalogs=catalogs)
        return EpisodeApplicationServices((scientific, LiteratureEpisodes(None).as_record(), *descriptors),
            bindings, execution.job_progress_provider, resource_tool_catalogs=catalogs)

    def __call__(self, store, *, run_id, directory, tool_catalog,
                 job_episodes=None, resource_estimator=None, tool_registry=None):
        from .a102_structural_catalog import prepare_catalog
        from .literature_episodes import LiteratureEpisodes
        directory = Path(directory)
        frozen = directory / 'scientific-process-library'
        if (frozen / 'index.json').is_file():
            # Reconstruction uses the authoritative run snapshot; original
            # publication files need not still exist or have remained current.
            _require_merged_library(ScientificProcessLibrary(frozen))
            configured = self
        else:
            source = prepare_catalog(self.source_directory, directory / 'structural-evidence-catalog')
            configured = replace(self, source_directory=str(source))
        arguments = {'run_id': run_id, 'directory': directory, 'tool_catalog': tool_catalog,
            'job_episodes': job_episodes, 'resource_estimator': resource_estimator,
            'tool_registry': tool_registry}
        if configured.execution_service_factory is None:
            services = A102ServiceFactory.__call__(configured, store, **arguments)
        else:
            services = configured._execution_services(store, **arguments)
        descriptors = list(services.episode_binding_descriptors)
        matches = [i for i, descriptor in enumerate(descriptors) if descriptor['binding_id'] == 'literature']
        if len(matches) != 1:
            raise ContractError('a102_single_literature_binding_required')
        # This existing option enables the structural population operation and
        # the same authenticated cross-role cell delivery used by other axes.
        configuration = deepcopy(descriptors[matches[0]]['configuration'])
        configuration['rate_population'] = True
        descriptors[matches[0]] = LiteratureEpisodes(None, **configuration).as_record()
        return replace(services, episode_binding_descriptors=tuple(descriptors))


def create_a102_structural_evidence_workflow(store, tools, provider, directory, run_id,
        controller_factory, *, initial_known_record_refs, **options):
    """Give the shared parent finding progress; children bind their task units."""
    from .runtime import Workflow
    if any(name in options for name in ('project_credit', 'credit_binding',
            'project_child_credit', 'child_credit_binding')):
        raise ValueError('a102_structural_evidence_progress_is_host_owned')
    if options.get('episode_record_receipts', True) is not True:
        raise ValueError('a102_structural_evidence_requires_episode_receipts')
    if not isinstance(options.get('episode_service_factory'), A102StructuralEvidenceServiceFactory):
        raise ValueError('a102_structural_evidence_service_factory_required')
    progress = finding_progress()
    options['episode_record_receipts'] = True
    return Workflow(store, tools, provider, directory, run_id, controller_factory, progress,
        credit_binding=progress.as_record(), initial_known_record_refs=initial_known_record_refs,
        **options)
