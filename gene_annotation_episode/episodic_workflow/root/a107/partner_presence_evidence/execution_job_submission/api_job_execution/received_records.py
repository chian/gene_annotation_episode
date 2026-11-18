from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _appservice_sources
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _comparison_selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _has_appservice
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _has_rfam
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _has_uniprot
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _read_result
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _result_directory
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _selection
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _selector
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _validate_result_body
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_information.received_result_readers import _windows
from gene_annotation_episode.episodic_workflow.root.a107.library.received_execution_targets import received_execution_target
from .execution_contracts import BLAST_GRADED_REQUEST_VERSION
from .execution_contracts import RESULT_PROVIDER
from .execution_contracts import ROLE_KINDS
from .execution_contracts import canonical
from .execution_contracts import hashlib
from .execution_contracts import is_native_blast_database_target
from .execution_contracts import is_native_rna_structure_target
from .execution_contracts import is_standard_blast_database_target
from .execution_contracts import plain

class NativeReceivedRecords:
    _target = received_execution_target
    _comparison_selector = staticmethod(_comparison_selector)
    _selector = _selector
    _result_directory = _result_directory
    _windows = _windows
    _validate_result_body = _validate_result_body
    _read_result = _read_result
    _selection = _selection

    def _context_target(self, context, target):
        if context.role == 'launch':
            launch = self._launch(plain(context.assignment), scope=context.scope)
            selected = target['assignment']
            resource_id = target['resource_id']
            request = launch['requests'].get(resource_id)
            if request is not None and request.get('version') == BLAST_GRADED_REQUEST_VERSION:
                self._validate_blast_launch_selection(launch, selected, context.scope)
                handoff = self.api_execution._read_handoff(target['handle'], plain(context.scope))
                subject_ref = selected['request']['subject_ref']
                sequence = self.tool_registry._sequence(subject_ref, molecule_model=self.store.subject_molecule(subject_ref))
                expected = hashlib.sha256(f'>{subject_ref}\n{sequence}'.encode()).hexdigest()
                if handoff['snapshot']['request'].get('query_sha256') != expected:
                    raise ValueError('blast_grader_submitted_query_conflict')
        elif context.role in ROLE_KINDS:
            if canonical(target['assignment']) != canonical(context.assignment):
                raise ValueError('execution_handoff_assignment_conflict')
        elif context.role == 'results' and target != self._target(context):
            raise ValueError('execution_result_target_conflict')
        return target
    _has_rfam = _has_rfam
    _has_appservice = _has_appservice
    _has_uniprot = _has_uniprot
    _appservice_sources = staticmethod(_appservice_sources)

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
                if source.get('provider') != 'episode.practical_receipt' and (not (self.api_execution is not None and self.api_execution.is_handoff_source(reference))):
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
        if context.role != 'results':
            assignment = plain(context.assignment)
            requests = assignment.get('requests', {}).values() if context.role == 'launch' else [assignment] if context.role == 'launch_local' else []
            references = []
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_job_inputs
            for request in requests:
                references.extend(validate_rna_structure_job_inputs(self.store, context, request))
                references.extend(self._masking_inputs(context, request))
                references.extend(self._utility_inputs(context, request))
                references.extend(self._expression_nmf_inputs(context, request))
            return list(dict.fromkeys(references))
        assignment = plain(context.assignment)
        target = self._target(context)
        if self.native_blast_masking_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_masking_results.validate_selected_inputs(context, assignment)
        if self.native_blast_utility_results.applies(context):
            self._selector(assignment, target)
            return self.native_blast_utility_results.validate_selected_inputs(context, assignment)
        selected = [assignment['handoff_ref']]
        if self.native_expression_nmf_results is not None and self.native_expression_nmf_results.applies(context):
            selector = self._selector(assignment, target)
            if selector['mode'] == 'saved_sheet_recalculation':
                self.native_expression_nmf_returns.authenticate_received_saved_sheet(context, selector['saved_sheet_file'])
                selected.append(selector['saved_sheet_file']['artifact_ref'])
            return list(dict.fromkeys(selected))
        if self._comparison_selector(assignment):
            from gene_annotation_episode.episodic_workflow.root.a107.rna_structure_comparison_operands import validate_rna_comparison_selected_inputs
            selected.extend(validate_rna_comparison_selected_inputs(self.store, context, assignment['selector'], anchor_handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        elif is_native_rna_structure_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_rna_structure_result_publication import validate_rna_structure_selected_inputs
            selected.extend(validate_rna_structure_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref'], returns=self.native_rna_structure_returns))
        if is_standard_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_standard_database_result_publication import validate_standard_blast_selected_inputs
            selected.extend(validate_standard_blast_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        if is_native_blast_database_target(target):
            from gene_annotation_episode.episodic_workflow.root.a107.native_blast_database_result_publication import validate_selected_inputs
            selected.extend(validate_selected_inputs(self.store, context, assignment['selector'], handoff_ref=assignment['handoff_ref']))
        return list(dict.fromkeys(selected))
