"""Private A102 API retained protein reader."""
from __future__ import annotations
from .execution_contracts import Path, RESULTS_SCHEMA, checked, confined, is_native_protein_structure_target, plain

class APIRetainedProteinReader:

    @classmethod
    def retained_protein_structure_reader(cls, store, *, run_id, directory):
        """Construct the retained A102 protein structure read authority.

        No resource, client, progress, registry or execution state is created.
        The caller supplies metadata sealed by the original episode;
        original receipts and typed delivery remain authoritative on every read.
        """
        from gene_annotation_episode.episodic_workflow.root.a102.state import Store
        if not isinstance(store, Store) or type(run_id) is not str or (not run_id) or (not isinstance(directory, (str, Path))):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        value = str(directory)
        path = Path(value)
        if not value or '\x00' in value or (not path.is_absolute()) or ('..' in path.parts) or (value != str(path)):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        if store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? LIMIT 1', (run_id,)).fetchone() is None:
            raise ValueError('protein_structure_retained_reader_run_missing')
        reader = cls.__new__(cls)
        reader.store, reader.run_id, reader.directory = (store, run_id, path)
        from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_results import NativeProteinStructureResults
        from gene_annotation_episode.episodic_workflow.root.a102.native_protein_structure_returns import NativeProteinStructureReturns
        reader.native_protein_structure_results = NativeProteinStructureResults(reader)
        reader.native_protein_structure_returns = NativeProteinStructureReturns(reader)
        return reader.native_protein_structure_returns

    def _protein_reference_access(self, context, reference, namespace):
        """Classify before ordinary resolution; a protected denial cannot fall through."""
        if isinstance(reference, str) and reference.startswith('protein_structure_result_receipt:') or (isinstance(namespace, str) and namespace.startswith('protein_structure_')):
            return False
        if namespace in {'execution', 'execution_handle'}:
            return None
        try:
            record = self.store.get(reference)
        except (ValueError, KeyError):
            return None
        if record['record_type'] in {'feature', 'product'}:
            from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_operands import is_protein_structure_sequence_operand
            if is_protein_structure_sequence_operand(self.store, reference):
                return False
        if self.native_protein_structure_results.owns_reference(reference):
            return self.native_protein_structure_returns.resolve_received(context, reference, namespace)
        return None

    def _retained_protein_result(self, context, assignment, scope):
        """Recover target metadata only from received or own completed authority.

        Scientific operand bytes retain their separate selected-use checks. A
        private staged receipt cannot replace a completed original action here.
        """
        assignment = checked(assignment, RESULTS_SCHEMA, 'invalid_execution_results_assignment')
        if assignment['selector'].get('version') != 'protein_structure_result_selector_v1':
            return None
        from gene_annotation_episode.episodic_workflow.root.a102.execution_contracts import validate_target
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_contracts import same
        from gene_annotation_episode.episodic_workflow.root.a102.protein_structure_selection import validate_protein_structure_result_selector
        selector = validate_protein_structure_result_selector(assignment['selector'])
        receipts = self.native_protein_structure_results.receipts
        if selector['acquisition'] == 'retained_sheet_only':
            descriptor = selector['saved_sheet']
            received = self.native_protein_structure_returns.authenticate_received_saved_sheet(context, descriptor, required_use='recalculate')
            custody = descriptor['custody']
            retained = receipts.read_completed(episode_id=custody['result_episode_id'], operation_key=custody['result_operation_key'], scope=plain(scope))
            if not same(received['custody'], custody) or not same(retained['publication']['custody'], custody) or custody['handoff_ref'] != assignment['handoff_ref']:
                raise ValueError('original_commission_mismatch')
        elif context.role == 'results' and same(assignment, plain(context.assignment)):
            completed = receipts.completed_receipts(context)
            qualified = [receipt for receipt in completed if receipt['body']['handoff_proof'] is not None]
            if not qualified:
                return None
            retained = qualified[0]
            if any((not same(receipt['body']['intent']['target'], retained['body']['intent']['target']) for receipt in qualified)):
                raise ValueError('execution_result_original_target_conflict')
        else:
            return None
        target = validate_target(retained['body']['intent']['target'])
        if context.run_id != self.run_id or target['run_id'] != self.run_id or target['handle'] != assignment['handoff_ref'] or (target['resource_kind'] != 'local') or (not is_native_protein_structure_target(target)) or (retained['body']['handoff_proof'] is None):
            raise ValueError('original_commission_mismatch')
        self.store.validate_scope(plain(scope), parent_scope=plain(context.scope))
        self.store.validate_scope(target['scope'], parent_scope=plain(scope))
        reader = self.job_progress_provider.targets
        resource_id = target['resource_id']
        configuration = self.resources.get(resource_id)
        if configuration is None or configuration['kind'] != 'local' or (not same(reader.resources.get(resource_id), configuration)) or (resource_id not in reader.operations):
            raise ValueError('practical_execution_resource_identity_conflict')
        confined(target['assignment']['workspace'], configuration['workspace'])
        reader.operations[resource_id].validate_assignment(target['assignment'])
        self._selector(assignment, target)
        return retained
