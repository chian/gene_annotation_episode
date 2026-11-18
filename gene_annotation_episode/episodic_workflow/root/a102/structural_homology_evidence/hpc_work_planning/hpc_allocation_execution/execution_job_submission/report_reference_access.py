"""Original outgoing/receiving A102 reference resolution, protected protein custody and native receipt access."""
from __future__ import annotations
from .execution_contracts import LOCAL_FILE_SOURCE_PROVIDER, NATIVE_RESULT_ORIGIN, NATIVE_RESULT_ORIGIN_SCHEMA, PracticalReceiptInformation, RESULT_PROVIDER, ROLE_KINDS, TerminalExecutionBehavior, deepcopy, plain, validate_form

class LaunchReportReferenceAccess:

    def resolve(self, context, reference, namespace):
        try:
            access = self._protein_reference_access(context, reference, namespace)
            if access is not None:
                return access
            if namespace in {'execution_handle', 'execution'}:
                from gene_annotation_episode.episodic_workflow.root.a102.episode_bindings import reference_in_context
                return bool(self.services is not None and reference_in_context(self.services, context, reference, namespace))
            if context.role in {'launch_local', 'launch_hpc'} and namespace == 'practical_receipt' and (not reference.startswith('source_')):
                return self._delegate(context).resolve(context, reference, namespace)
            source = self.store.get(reference)
            if source.get('provider') == LOCAL_FILE_SOURCE_PROVIDER:
                return namespace in {None, 'source'} and self.local_file_sources.read_source(reference, context.scope) is not None
            if source.get('provider') == RESULT_PROVIDER:
                if source.get('version') == 'native_protein_structure_bundle_v1':
                    return False
                if namespace not in {None, 'source', 'execution_result'}:
                    return False
                body = self._read_result(reference, context.scope)
                return bool(body['windows']) if namespace == 'execution_result' else True
            if namespace in {None, 'source', 'execution_handoff'}:
                try:
                    target = self.job_progress_provider.targets.read_target(reference, context.scope)
                    return namespace != 'execution_handoff' or self.job_progress_provider.targets.returnable_handoff(target)
                except ValueError:
                    if namespace == 'execution_handoff':
                        return False
            if PracticalReceiptInformation(self.store, self.run_id).resolve(context, reference, namespace):
                return True
            if self.api_execution is not None and self.api_execution.resolve(context, reference, namespace):
                return True
            if self.services is not None:
                from gene_annotation_episode.episodic_workflow.root.a102.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

