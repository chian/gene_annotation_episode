"""Private A110 Launch input versions"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import canonical
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class LaunchInputVersions:

    def _versions(self, versions, scope, *, context, flux_balance_assignments=()):
        from gene_annotation_episode.episodic_workflow.root.a110.execution_input_versions import validate_execution_input_versions
        return validate_execution_input_versions(self, versions, scope, context=context, flux_balance_assignments=flux_balance_assignments)

    def _flux_balance_inputs(self, context, assignment, *, input_versions=None):
        if 'native_flux_balance' not in assignment.get('requested_job', {}):
            return []
        from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
        if input_versions is None:
            if context.role == 'launch':
                input_versions = plain(context.assignment)['immutable_input_versions']
            else:
                _, input_versions = self.flux_balance_inputs._original(context)
        frozen = self.flux_balance_inputs.received(context, required=False) if context.role == 'launch_local' and self._matches_flux_balance_assignment(context, assignment) else None
        binding = frozen['receipt']['binding'] if frozen is not None else self.flux_balance_inputs.validate_selected(context, assignment, input_versions=input_versions)
        if not EpisodeReturnRecords._equal(binding['input_versions'], list(input_versions)):
            raise ValueError('flux_balance_execution_input_original_versions_conflict')
        return list(dict.fromkeys((row['reference'] for row in binding['input_versions'])))
