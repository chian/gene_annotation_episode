"""Private A101 job_monitor native event observation."""
from __future__ import annotations
from .execution_contracts import copy

class NativeEventObservation:

    def with_native_events(self, provider):
        """A host-local view; the caller's binding/descriptor stays unchanged."""
        from gene_annotation_episode.episodic_workflow.root.a101.native_events import NativeEventProvider
        if type(provider) is not NativeEventProvider:
            raise TypeError('typed_native_event_provider_required')
        if self.statistics is not None and self.statistics.resource_id != provider.resource_id:
            raise ValueError('native_event_resource_identity_conflict')
        view = copy(self)
        view.native_event_provider = provider
        return view

    def recover_native_events(self):
        summary = {}
        if self.native_event_provider is not None:
            for value in self.jobs.recover_native_events(native_event_provider=self.native_event_provider):
                summary[value['state']] = summary.get(value['state'], 0) + 1
        return summary

    def bind_job_native_events(self, source, job_ref):
        provider = self.native_event_provider
        if provider is None:
            return None
        if source.workflow.run_id != provider.run_id:
            raise ValueError('native_event_run_identity_conflict')
        original = self.jobs.native_event_binding(job_ref)
        if original is None and (self.jobs._handle(job_ref).path.exists() or self.jobs._row(job_ref)['submission_requested']):
            return None
        return provider.for_job(owner_episode_id=source.episode_id, job_ref=job_ref, registry_ref=self.jobs.config['registry_ref'], original_binding=original)

    def recover_statistics(self):
        summary = {}
        if self.statistics is not None:
            for value in self.jobs.recover_statistics():
                summary[value['state']] = summary.get(value['state'], 0) + 1
        return summary
