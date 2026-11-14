"""Root-owned credit_projection.py"""
from __future__ import annotations
from .receiving_context import BindingContext
from collections.abc import Mapping
from .task_values import _plain
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical
import json
import math

class CreditProjection:

    def source_credit_view(self, source, *, binding_snapshot=None):
        if source.path[-1][0] == 'improvement' and 'improvement' not in self.episode_bindings.roles:
            from .legacy_annotation.credit import source_credit_view
            return source_credit_view(self, source, binding_snapshot=binding_snapshot)
        if binding_snapshot is not None and type(binding_snapshot) is not dict:
            raise TypeError('credit_binding_snapshot_must_be_dict')
        if self.is_job_source(source):
            result = self.job_implementation(path=source.path).credit_view(source)
        elif self.specialist(source) is not None:
            selection = {**self.record_selection(source.episode_id), **self.progress_selection(source)}
            result = self.specialist(source).credit_view(self.binding_context(source), selection)
            if binding_snapshot is not None:
                binding_snapshot.update(view=json.loads(canonical(_plain(result))), selection=json.loads(canonical(_plain(selection))))
        else:
            projector = self.scientific_projector_for_context(self.binding_context(source))
            result = self.projection_view(projector, source.scope, **self.projection_arguments(source))
        if self.native_timing_information is not None:
            native = self.native_timing_information(self.store, source.scope, **self.native_timing_arguments(source))
            previous = result.get('monitoring_information_credit')
            previous_binding = result.get('monitoring_information_binding')
            if previous is None and self.is_job_source(source) and (source.path[-1][0] == 'job_monitor'):
                previous = result['credit']
                previous_binding = self.job_implementation(path=source.path).binding_for('job_monitor')
            binding = native['monitoring_information_binding']
            if previous is not None:
                binding = {'kind': 'execution_information_components', 'selected_observations': previous_binding, 'received_native_durations': binding}
            result.update(monitoring_information_credit=(previous or 0) + native['monitoring_information_credit'], monitoring_information_binding=binding)
            if self.is_job_source(source) and source.path[-1][0] == 'job_monitor':
                result['credit'] += native['monitoring_information_credit']
        return result

    def source_credit_binding(self, source):
        if source.path[-1][0] == 'improvement' and 'improvement' not in self.episode_bindings.roles:
            from .legacy_annotation.credit import source_credit_binding
            return source_credit_binding(self, source)
        specialist = self.specialist(source)
        if specialist is not None and specialist.credit_kind(source.path[-1][0]) != 'scientific':
            return _plain(self.role_credit_definitions.get(source.path[-1][0]))
        if self.is_job_source(source):
            binding = self.job_implementation(path=source.path).binding_for(source.path[-1][0])
            if source.path[-1][0] == 'job_monitor' and self.native_timing_information is not None:
                return {'kind': 'monitoring_information_components', 'selected_observations': binding, 'received_native_durations': self.native_timing_information.as_record()}
            return binding
        if specialist is not None:
            context = source if isinstance(source, BindingContext) else self.binding_context(source)
            return _plain(self.scientific_projector_for_context(context).as_record())
        if len(source.path) == 1:
            return self.credit_binding
        raise ValueError('scientific_task_credit_not_declared:' + source.path[-1][0])

    def source_controller_credit(self, source):
        """Declare the actual local scalar's meaning without projecting it."""
        role = source.path[-1][0]
        specialist = self.specialist(source)
        if specialist is not None:
            kind = specialist.credit_kind(role)
        elif self.is_job_source(source):
            kind = self.job_implementation(path=source.path).credit_kind(role)
        else:
            kind = 'scientific'
        binding = self.source_credit_binding(source)
        if not isinstance(binding, Mapping) or not binding:
            return None
        context = source if isinstance(source, BindingContext) else self.binding_context(source)
        annotation = self.services.proposed_annotation_for(context)
        if annotation is not None:
            binding = {**_plain(binding), 'proposed_annotation_ref': annotation}
        return {'credit_kind': kind, 'credit_binding': _plain(binding)}

    def credit_view(self, scope):
        """Return the scalar and available components from ONE actual projection.

        Components inform the scientific episode; the numerical controller still
        receives the same scalar. No history/source payload or extra observation
        is materialized, and custom projectors acquire no invented default axes.
        """
        return self.projection_view(self.project_credit, scope)

    def projection_view(self, projector, scope, *, annotation_collection=False, **arguments):
        with self.store.read_snapshot():
            projected = projector(self.store, _plain(scope), **arguments)
        if isinstance(projected, Mapping) and isinstance(projected.get('credit'), Mapping) and (projected['credit'].get('mode') == 'annotation_axis_credit'):
            from .numerical import validate_task_credit
            return {**_plain(projected), 'credit': validate_task_credit(projected['credit'])}
        if annotation_collection and isinstance(projected, Mapping) and (projected.get('mode') == 'proposed_annotation_collection') and ('credit' not in projected):
            return {key: _plain(projected[key]) for key in ('mode', 'proposed_annotations', 'comparisons', 'scalar_mapping_version', 'aggregation_version')}
        if hasattr(projected, 'credit'):
            value, axes = (float(projected.credit), getattr(projected, 'axis_components', None))
        elif isinstance(projected, Mapping):
            value, axes = (float(projected['credit']), projected.get('axis_components'))
        else:
            value, axes = (float(projected), None)
        if not math.isfinite(value):
            raise ValueError('finite_scientific_credit_required')
        result = {'credit': value}
        if isinstance(axes, Mapping):
            result['axis_components'] = _plain(axes)
        if isinstance(projected, Mapping):
            for key in ('retained_finding_count', 'inactive_dependencies', 'detail_pages', 'a101_sheet', 'interpretation', 'axis_status', 'scalar_mapping_version', 'support', 'opposition', 'aggregation_version'):
                if key in projected:
                    result[key] = _plain(projected[key])
        return result

    def credit(self, scope):
        return self.credit_view(scope)['credit']

    def credit_detail_projector(self, source):
        """The Store/scope detail port belongs to the actual scientific binding.

        Operational specialist projections use their own context/receipt port.
        They do not acquire a scientific detail reader from the root projector.
        """
        if source is not None:
            if self.is_job_source(source):
                return None
            specialist = self.specialist(source)
            if specialist is not None and specialist.credit_kind(source.path[-1][0]) != 'scientific':
                return None
        return self.scientific_projector_for_context(self.binding_context(source)) if source is not None else self.project_credit

    def credit_read(self, source, arguments):
        """Read declared projection details without choosing another score binding.

        A caller-injected projector must explicitly declare this capability;
        the runtime cannot replace it with the application's default policy.
        Scientific state is unchanged and ordinary action accounting remains
        in DecisionSource.execute, rather than inside this read helper.
        """
        projector = self.credit_detail_projector(source)
        return self.projection_read(source, arguments, projector, projector_arguments=self.projection_arguments(source) if projector is not None else {})

    def annotation_score_read(self, source, arguments):
        projector_arguments = self.projector_receipt_arguments(self.project_annotation_score, source.episode_id) if self.project_annotation_score is not None else {}
        result = self.projection_read(source, arguments, self.project_annotation_score, channel='annotation_score', projector_arguments=projector_arguments)
        if result['status'] == 'completed':
            details = result['result']
            if 'credit' in details:
                details['annotation_score'] = details.pop('credit')
            details['interpretation'] = 'annotation_support_not_investigation_progress'
            details['annotation_score_binding'] = _plain(self.annotation_score_binding)
        return result

    def projection_read(self, source, arguments, projector, *, channel='credit', projector_arguments=None):
        """One detail-read path for a declared projector, with no score fallback."""
        reader = getattr(projector, 'read_details', None)
        if not callable(reader):
            return {'status': 'unavailable', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': channel + '_details_not_declared'}}
        try:
            with self.store.read_snapshot():
                result = _plain(reader(self.store, source.scope, details_limit=arguments['limit'], details_offset=arguments['offset'], **projector_arguments or {}))
            collection = channel == 'annotation_score' and isinstance(result, dict) and (result.get('mode') == 'proposed_annotation_collection') and isinstance(result.get('proposed_annotations'), list) and isinstance(result.get('comparisons'), list) and ('credit' not in result)
            if not isinstance(result, dict) or ('credit' not in result and (not collection)):
                raise ValueError(channel + '_details_record_required')
        except Exception as error:
            return {'status': 'failed', 'record_refs': [], 'changed_record_refs': [], 'result': None, 'feedback': {'code': channel + '_details_read_failed', 'exception_type': type(error).__name__, 'detail': str(error)}}
        return {'status': 'completed', 'record_refs': [], 'changed_record_refs': [], 'result': result, 'feedback': None}
