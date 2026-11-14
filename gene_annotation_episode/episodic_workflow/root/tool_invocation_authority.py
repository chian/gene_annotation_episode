"""Original substantive ordinary-tool methods: tool_invocation_authority."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical

class ToolInvocationAuthority:
    def _execution_owner_identity(self, owner):
        """Validate an existing live owner without establishing input authority."""
        from .execution_episodes import ExecutionEpisodes
        if (type(owner) is not ExecutionEpisodes or getattr(owner, 'services', None) is None
                or getattr(owner, 'store', None) is not self.store
                or getattr(owner, 'tool_registry', None) is not self
                or type(getattr(owner, 'run_id', None)) is not str or not owner.run_id
                or not isinstance(getattr(owner, 'directory', None), Path)):
            raise ContractError('execution_owner_conflict')
        molecular = self._molecular_sequence_results_by_run.get(owner.run_id)
        capture = self._macs2_peak_capture_readers_by_run.get(owner.run_id)
        if (molecular is not None and molecular.owner is not owner
                or capture is not None and getattr(capture, '__self__', None) is not owner):
            raise ContractError('execution_owner_attachment_conflict')
        return canonical(owner.as_record()), owner.directory.resolve()

    def bind_execution_owner(self, owner):
        """Attach this run's actual services-backed execution owner."""
        declaration, directory = self._execution_owner_identity(owner)
        previous = self._execution_owners_by_run.get(owner.run_id)
        if previous is not None and (previous[1] != declaration or previous[2] != directory):
            raise ContractError('execution_owner_changed')
        self._execution_owners_by_run[owner.run_id] = (owner, declaration, directory)

    def execution_owner_for(self, run_id):
        """Resolve a bound run; its tool still authenticates the actual action."""
        if type(run_id) is not str or not run_id or run_id not in self._execution_owners_by_run:
            raise ContractError('execution_owner_unavailable')
        owner, declaration, directory = self._execution_owners_by_run[run_id]
        if self._execution_owner_identity(owner) != (declaration, directory) or owner.run_id != run_id:
            raise ContractError('execution_owner_changed')
        return owner

    def bind_molecular_sequence_results(self, result_owner):
        """Attach the actual services-backed owner independently for each run."""
        from .molecular_sequence_results import MolecularSequenceResults
        if type(result_owner) is not MolecularSequenceResults:
            raise ContractError('molecular_sequence_result_owner_required')
        owner = result_owner.owner
        if (result_owner.store is not self.store or owner.store is not self.store
                or owner.tool_registry is not self or owner.services is None
                or type(result_owner.run_id) is not str or not result_owner.run_id
                or owner.run_id != result_owner.run_id):
            raise ContractError('molecular_sequence_result_owner_conflict')
        previous = self._molecular_sequence_results_by_run.get(result_owner.run_id)
        if previous is not None and (
                canonical(previous.owner.as_record()) != canonical(owner.as_record())
                or Path(previous.owner.directory).resolve() != Path(owner.directory).resolve()):
            raise ContractError('molecular_sequence_result_owner_changed')
        self._molecular_sequence_results_by_run[result_owner.run_id] = result_owner

    def molecular_sequence_results_for(self, run_id):
        """Resolve a run's owner; its operation ports authenticate actual context."""
        if type(run_id) is not str or run_id not in self._molecular_sequence_results_by_run:
            raise ContractError('molecular_sequence_result_owner_unavailable')
        return self._molecular_sequence_results_by_run[run_id]

    def bind_macs2_peak_capture_reader(self, run_id, callback):
        """Bind the actual services-backed capture authority for this run."""
        from .execution_episodes import ExecutionEpisodes
        owner = getattr(callback, '__self__', None)
        if (type(owner) is not ExecutionEpisodes or owner.store is not self.store
                or owner.tool_registry is not self or owner.services is None or owner.run_id != run_id
                or getattr(callback, '__func__', None) is not ExecutionEpisodes.read_macs2_peak_capture_selection):
            raise ContractError('macs2_peak_capture_owner_conflict')
        previous = self._macs2_peak_capture_readers_by_run.get(run_id)
        if previous is not None and (canonical(previous.__self__.as_record()) != canonical(owner.as_record())
                or Path(previous.__self__.directory).resolve() != Path(owner.directory).resolve()):
            raise ContractError('macs2_peak_capture_owner_changed')
        self._macs2_peak_capture_readers_by_run[run_id] = callback

    def macs2_peak_capture_reader_for(self, run_id):
        if type(run_id) is not str or run_id not in self._macs2_peak_capture_readers_by_run:
            raise ContractError('macs2_peak_capture_owner_unavailable')
        return self._macs2_peak_capture_readers_by_run[run_id]

    @contextmanager
    def protein_structure_invocation(self, input_authority):
        """Carry the real receiving authority alongside the selected action."""
        token = self._protein_structure_input_authority.set(input_authority)
        try:
            yield
        finally:
            self._protein_structure_input_authority.reset(token)

    @property
    def _written(self) -> list[str]:
        publications = self._publications.get()
        if publications is None:
            raise ContractError("publication_outside_tool_operation")
        return publications

    @contextmanager
    def current_invocation(self, context, *, read_received, tool_name, arguments, operation_key):
        """Host-only current action port; each participating tool authenticates it."""
        token = self._current_invocation.set((context, read_received, tool_name, arguments, operation_key))
        try:
            yield
        finally:
            self._current_invocation.reset(token)

    def retained_molecular_reference_access(self, context, reference, namespace, *, initial_record_refs=()):
        """Actual finite publication owner; this port grants no new receipt."""
        from gene_annotation_episode.enrichr_reference_privacy import enrichr_reference_restriction
        from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
        restriction = enrichr_reference_restriction(self.store, context, reference, namespace,
            initial_record_refs=initial_record_refs)
        if restriction is not None:
            return restriction
        return molecular_reference_restriction(self.store, context, reference, namespace)

