"""Root-owned credit_projection.py"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from collections.abc import Mapping
from gene_annotation_episode.episodic_workflow.root.task_values import _plain
from gene_annotation_episode.episodic_workflow.root.method_loop.durable import canonical
import json
import math

def source_credit_view(self, source, *, binding_snapshot=None):
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

