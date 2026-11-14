from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _read_result
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _result_directory
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _selection
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _selector
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _target
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _validate_result_body
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.received_result_readers import _windows
from .execution_contracts import RESULT_PROVIDER
from .execution_contracts import ROLE_KINDS
from .execution_contracts import canonical
from .execution_contracts import plain

class NativeReceivedRecords:
    _target = _target
    _selector = _selector
    _result_directory = _result_directory
    _windows = _windows
    _validate_result_body = _validate_result_body
    _read_result = _read_result
    _selection = _selection

    def _context_target(self, context, target):
        from gene_annotation_episode.episodic_workflow.root.a110.flux_balance_request_binding import is_compact_assignment, is_compact_launch, read_request_binding
        if is_compact_launch(plain(context.assignment)) or is_compact_assignment(plain(context.assignment)):
            own = read_request_binding(self.store, self.run_id, context.episode_id)
            original = read_request_binding(self.store, self.run_id, target['origin_episode_id'])
            if not any((row['assignment'] == target['assignment'] for row in own['requests'])) or target['assignment'] != original['requests'][0]['assignment'] or (context.role == 'launch' and original['parent_file'] != own['file']):
                raise ValueError('execution_handoff_assignment_conflict')
            return target
        if context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target

    def _received(self, context, selection=None, *, _handoff_read=None):
        with self.store.read_snapshot():
            selection = self._selection(context, selection)
            read = self.job_progress_provider.targets._handoff_reader() if _handoff_read is None else _handoff_read
            handoffs, results = ({}, {})
            for reference in dict.fromkeys(selection['known_record_refs']):
                source = self.store.get(reference)
                if source.get('provider') == RESULT_PROVIDER:
                    if source.get('version') in {'native_blast_utility_bundle_v1', 'native_blast_masking_bundle_v1', 'native_hmmer_bundle_v1', 'native_blast_bundle_v1', 'native_blast_database_bundle_v1', 'native_blast_standard_database_bundle_v1', 'native_infernal_bundle_v1', 'native_infernal_preparation_bundle_v1', 'native_hmmer_preparation_bundle_v1', 'native_protein_structure_bundle_v1', 'native_rna_structure_bundle_v1'}:
                        continue
                    body = self._read_result(reference, context.scope)
                    if context.role == 'results' and body['assignment'] != plain(context.assignment):
                        continue
                    results[reference] = body
                    continue
                if source.get('provider') != 'episode.practical_receipt':
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                except (ValueError, KeyError):
                    continue
                try:
                    self._context_target(context, target)
                except ValueError:
                    continue
                if returnable:
                    handoffs[reference] = target
            return (selection, handoffs, results)

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
