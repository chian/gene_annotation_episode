"""Private A110 Results from_parent"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.resource_records import INPUT_VERSION_SCHEMA
from .binding_roles import KINDS
from .received_launch_records import LAUNCH_VERSION
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import SELECTOR_SCHEMA as LOCAL_FILE_SOURCE_SELECTOR_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.library.execution_result_contract import RESULTS_SCHEMA
from .binding_roles import ROLE_KINDS
from gene_annotation_episode.episodic_workflow.root.a110.launch_instructions import SELECTION_SCHEMA
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a110.local_file_capture_results import is_file_source_selector
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import obj
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain

class ResultsFromParent:

    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        if parent is not None and parent.path[-1][0] == 'scientific_process' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_result_refs',)
        return ()

    def child_assignment_schema(self, parent, role):
        if parent.role == 'launch' and False:
            pass
        return self.assignment_schema(role)

    def assignment_schema(self, role, *, internal=False):
        self.credit_kind(role)
        schema = deepcopy(RESULTS_SCHEMA)
        schema['properties']['selector'].setdefault('allOf', []).append({'if': {'required': ['version'], 'properties': {'version': {'const': 'local_file_source_selector_v1'}}}, 'then': deepcopy(LOCAL_FILE_SOURCE_SELECTOR_SCHEMA)})
        if self.native_flux_balance_results is not None:
            from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_result_selection import FBA_RESULT_SELECTOR_SCHEMA
            schema['properties']['selector']['allOf'].append({'if': {'required': ['version'], 'properties': {'version': {'const': 'flux_balance_result_selector_v1'}}}, 'then': deepcopy(FBA_RESULT_SELECTOR_SCHEMA)})
        return schema

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        selected = checked(selection, self.assignment_schema(role, internal=True), 'invalid_execution_assignment')
        if parent.role in ('hpc', 'hpc_execution') and False:
            pass
        recorded = self._recorded_results_assignment(parent, selected, scope, operation_key)
        if recorded is not None:
            return recorded
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if False and is_compact_launch(selected):
            pass
        if False and is_compact_assignment(selected):
            pass
        target = self._retained_flux_balance_target(parent, selected, scope)
        if target is None:
            target = self.job_progress_provider.targets.read_target(selected['handoff_ref'], scope)
        self._selector(selected, target)
        if is_file_source_selector(selected.get('selector')):
            self.local_file_sources.admit(parent, selected, target)
        return selected

    def initial_references(self, context):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_assignment(plain(context.assignment)) or is_compact_launch(plain(context.assignment)):
            control = read_request_binding(self.store, self.run_id, context.episode_id)
            return list(dict.fromkeys((version['reference'] for row in control['requests'] for version in row['input_versions'])))
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            for request in requests:
                references.extend(self._flux_balance_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        selected = [assignment['handoff_ref']]
        target = self._target(context)
        if self.native_flux_balance_results is not None and self.native_flux_balance_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_flux_balance_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
        return list(dict.fromkeys(selected))
