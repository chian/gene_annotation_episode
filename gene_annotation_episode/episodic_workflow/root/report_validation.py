"""Root-owned report_validation.py"""
from __future__ import annotations
from .receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.method_loop import Episode
from .resource_estimation import FORECAST_REFERENCE_FIELDS
from .task_values import _plain
from .closing_episode_yield import closing_yield
from .workflow_values import common_fact_sources
from dataclasses import field
import json
from .resource_estimation import recorded_estimate
from .resource_estimation import recorded_forecasts
from .resource_estimation import report_source as resource_report_source
from .received_episode_yield import report_sources as runtime_report_sources
from .native_timing_information import validate_native_measurements
from .resource_estimation import validate_recorded_estimates

class ReportValidation:

    def extra_report_sources(self, source):
        return self.report_sources(source.path[-1][0], path=source.path)

    def return_contract_sources(self, grain, *, path=None, parent_path=None):
        """Include common evidence-reference contracts in child discovery."""
        return common_fact_sources() | self.report_sources(grain, path=path, parent_path=parent_path)

    def report_sources(self, grain, *, path=None, parent_path=None, owner=None):
        job_sources = {}
        if self.job_episodes:
            from .library.homology_episode_family import HomologyEpisodes
            if type(self.job_episodes) is HomologyEpisodes:
                if grain in self.job_episodes.roles:
                    job_sources = self.job_implementation(path=path, parent_path=parent_path, role=grain).fact_sources(grain)
            else:
                job_sources = self.job_episodes.fact_sources(grain)
        sources = runtime_report_sources() | job_sources

        if self.native_event_information is not None:
            from .library.native_event_information import report_sources
            sources.update(report_sources())
        sources['pending_handles'] = {'type': 'array', 'meaning': 'Original selected child executions awaiting their outcome and parent receipt. Numerical yield suspends new selection while these owned returns remain; normal branch closure follows their settlement and does not establish scientific completion.', 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'execution_handle'}, 'x-source': 'pending_handles'}}
        if grain in self.episode_bindings.roles:
            binding = self.episode_bindings.for_path(path, owner=owner) if path is not None else self.episode_bindings.for_child(parent_path, grain, owner=owner) if parent_path is not None else self.episode_bindings.for_role(grain, owner=owner)
            sources.update(binding.fact_sources(grain))
        received_sources = self.episode_bindings.received_report_sources(grain, path=path, parent_path=parent_path, owner=owner)
        if set(received_sources).intersection(sources):
            raise ValueError('received_report_source_conflict')
        sources.update(received_sources)
        if self.native_timing_information is not None:
            native_sources = self.native_timing_information.report_sources()
            sources = native_sources | sources
        if self.project_annotation_score is not None and (not (self.job_episodes and grain in self.job_episodes.roles)):
            if getattr(self.project_annotation_score, 'provides_single_annotation_score', True):
                sources['annotation_score'] = {'type': 'number', 'meaning': 'Annotation support for the fixed scope at child closure, separately bound from investigation progress and numerical yield. Redelivery preserves this snapshot.'}
            else:
                sources['proposed_annotations'] = {'type': 'array', 'meaning': 'Received proposed annotations and their separate evidence scores at child closure; unknown scores remain null.'}
                sources['annotation_comparisons'] = {'type': 'array', 'meaning': 'Best scored alternatives and ties for the same subject, region and question at child closure; the episode owns the annotation decision.'}
        if self.resource_estimator is not None:
            sources['resource_tool_estimates'] = resource_report_source()
        return sources

    def validate_report(self, value, scope, *, assignment=None, grain=None, schema=None, source=None, context=None):
        """Validate recorded forecast relationships for any episode's form."""
        if self.native_event_information is not None and schema is not None and any((node.get('x-source') == 'native_event_targets' for node in schema.get('properties', {}).values())):
            native_context = self.binding_context(source) if source is not None else context
            if native_context is None:
                raise ValueError('native_event_report_context_required')
            self.native_event_information.validate_report(native_context, value, schema)
        if assignment is not None:
            from .library.homology_episode_family import HomologyEpisodes
            if type(self.job_episodes) is HomologyEpisodes:
                if grain not in self.job_episodes.roles:
                    raise ValueError('homology_return_role_required')
                actual_path = source.path if source is not None else context.path if context is not None else None
                job_owner = self.job_implementation(path=actual_path, role=grain)
            else:
                job_owner = self.job_episodes
            job_owner.validate_report(value, assignment, role=grain, store=self.store, schema=schema)

        elif self.resource_estimator is not None:
            validate_recorded_estimates(self.store, value, schema=schema, reference_resolver=self.resolver(scope, source=source, grain=grain, context=context))
        if self.native_timing_information is not None and schema is not None:
            validate_native_measurements(self.store, value, schema=schema)
        received_context = self.binding_context(source) if source is not None else context
        if received_context is not None and schema is not None:
            self.episode_bindings.validate_received_report(received_context, value, schema)
        if source is not None and self.specialist(source) is not None:
            self.specialist(source).validate_report(self.binding_context(source), value, schema)
        elif context is not None and context.role in self.episode_bindings.roles:
            self.episode_bindings.for_path(context.path).validate_report(context, value, schema)

    def resolver(self, scope, source=None, assignment=None, grain=None, *, context=None):
        if context is not None and type(context) is not BindingContext:
            raise TypeError('typed_report_binding_context_required')
        if source is not None:
            actual = self.binding_context(source)
            if context is not None and context.as_record() != actual.as_record():
                raise ValueError('report_binding_context_source_mismatch')
            context = actual
        specialist = None
        if context is not None:
            message = context.request.get('message', {})
            if context.run_id != self.run_id or context.role not in self.grains or _plain(context.scope) != _plain(scope) or (_plain(message.get('scope')) != _plain(scope)) or (_plain(context.assignment) != _plain(message.get('episode_assignment', {}))) or (grain is not None and grain != context.role) or (assignment is not None and _plain(assignment) != _plain(message.get('job_assignment'))):
                raise ValueError('report_binding_context_identity_mismatch')
            identity = Episode.identity(self.context, self.grains[context.role], context.path[-1][1], parent_path=context.path[:-1])
            if identity.episode_id != context.episode_id:
                raise ValueError('report_binding_context_identity_mismatch')
            recorded = self.journal.row('runtime_episodes', context.episode_id)
            if recorded is not None and (json.loads(recorded['path']) != _plain(context.path) or json.loads(recorded['request']) != _plain(context.request)):
                raise ValueError('report_binding_context_original_request_mismatch')
            assignment, grain = (message.get('job_assignment'), context.role)
            if grain in self.episode_bindings.roles:
                specialist = self.episode_bindings.for_path(context.path)

        def resolve(reference, namespace=None):
            molecular = getattr(self.tools, 'retained_molecular_reference_access', None)
            if callable(molecular):
                verdict = molecular(context, reference, namespace, initial_record_refs=getattr(self, 'initial_known_record_refs', None) or ())
                if verdict is not None:
                    return verdict
            if context is not None:
                protein = self.services.protein_structure_reference_access(context, reference, namespace)
                if protein is not None:
                    return protein
            if namespace == 'native_event_target':
                return bool(self.native_event_information is not None and context is not None and self.native_event_information.resolve(context, reference, namespace))
            if self.native_event_information is not None and context is not None and self.native_event_information.resolve(context, reference, namespace):
                return True
            if self.scientific_provenance is not None and context is not None and (namespace in {'scientific_invocation', 'scientific_preparation', 'scientific_process_library', 'scientific_option_digest', 'scientific_credit_binding'}):
                return self.services.scientific_reference(context, reference, namespace)
            if context is not None:
                received = self.episode_bindings.resolve_received_reference(context, reference, namespace)
                if received is not None:
                    return received
            if specialist is not None and specialist.resolve(context, reference, namespace):
                return True
            if specialist is None and namespace in {'execution_handle', 'execution'}:
                return bool(self.progress_provider is not None and self.progress_provider.resolve(reference, scope, namespace))
            if not self.store.reference_subset([reference], scope):
                if specialist is None and self.progress_provider is not None and self.progress_provider.resolve(reference, scope, namespace):
                    return True
                if namespace in FORECAST_REFERENCE_FIELDS and assignment is None:
                    estimate = recorded_estimate(self.store, reference, namespace=namespace)
                    if estimate is None:
                        return False
                    native = getattr(self.tools, 'native_statistics', None)
                    if native is not None and native.recorded_class(self.store, estimate['execution_class_ref']) is not None:
                        return True
                    binding = self.execution_expectations
                    if binding is not None and (estimate['job_ref'] is None or namespace != 'job_execution_estimate'):
                        names = (grain,) if grain is not None else binding.by_grain
                        refs = {item.ref for name in names for item in binding.by_grain.get(name, ())}
                        if estimate['execution_class_ref'] in refs:
                            return True
                return bool(self.job_episodes and self.job_episodes.resolve(self.store, scope, reference, namespace, assignment=assignment))
            kind = self.store.get(reference)['record_type']
            return not namespace or namespace == kind or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})
        return resolve

    from .library.report_fact_assembly import facts
