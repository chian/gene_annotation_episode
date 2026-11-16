"""Root host ports defined by WorkflowProgressServices."""
from __future__ import annotations
from .communication import plain
from .episode_bindings import native_observation_options

class WorkflowProgressServices:

    def capabilities(self):
        return tuple(getattr(self.workflow, 'resource_capabilities', ()))

    def observe_progress(self, target_handle, requested_fields, scope, *, permitted_committed_record_types=(), operation_key=None, native_operation=None, observation_context=None):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return provider.observe(target_handle, requested_fields, plain(scope), permitted_committed_record_types=permitted_committed_record_types, operation_key=operation_key, **native_observation_options(native_operation, observation_context))

    def describe_progress_target(self, target_handle, scope):
        provider = getattr(self.workflow, 'progress_provider', None)
        return None if provider is None else provider.describe_target(target_handle, plain(scope))

    def dependencies(self, target_handle, scope):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return tuple(provider.direct_dependencies(target_handle, plain(scope)))

    def read_progress(self, reference, scope):
        provider = getattr(self.workflow, 'progress_provider', None)
        if provider is None:
            raise ValueError('episode_progress_provider_not_bound')
        return provider.read_progress(reference, plain(scope))

    def received_progress_refs(self, episode_id):
        provider = getattr(self.workflow, 'progress_provider', None)
        return [] if provider is None else provider.received_progress_refs(episode_id)

    def progress_selection(self, context):
        if context.run_id != self.workflow.run_id:
            raise ValueError('progress_selection_receiver_identity_mismatch')
        return self.workflow.progress_selection(context)

