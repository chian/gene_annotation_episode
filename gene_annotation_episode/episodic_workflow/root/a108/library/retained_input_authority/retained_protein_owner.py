import json
from pathlib import Path

class RetainedProteinReader:

    @classmethod
    def retained_protein_structure_reader(cls, store, *, run_id, directory):
        """Construct only this owner's unchanged legacy protein read authority.

        No resource, client, progress, registry or execution state is created.
        The caller supplies metadata sealed from the actual original owner;
        original receipts and typed delivery remain authoritative on every read.
        """
        from gene_annotation_episode.episodic_workflow.root.a108.state import Store
        if not isinstance(store, Store) or type(run_id) is not str or (not run_id) or (not isinstance(directory, (str, Path))):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        value = str(directory)
        path = Path(value)
        if not value or '\x00' in value or (not path.is_absolute()) or ('..' in path.parts) or (value != str(path)):
            raise ValueError('protein_structure_retained_reader_metadata_invalid')
        if store.db.execute('SELECT 1 FROM runtime_episodes WHERE run_id=? LIMIT 1', (run_id,)).fetchone() is None:
            raise ValueError('protein_structure_retained_reader_run_missing')
        owner = cls.__new__(cls)
        owner.store, owner.run_id, owner.directory = (store, run_id, path)
        from .native_protein_structure_results import NativeProteinStructureResults
        from .native_protein_structure_returns import NativeProteinStructureReturns
        owner.native_protein_structure_results = NativeProteinStructureResults(owner)
        owner.native_protein_structure_returns = NativeProteinStructureReturns(owner)
        return owner.native_protein_structure_returns

    def _selected_result_action(self, episode_id, key, name, arguments):
        prefix = self.run_id + ':' + episode_id + ':'
        suffix = key.removeprefix(prefix)
        if not key.startswith(prefix) or not suffix.isdecimal() or str(int(suffix)) != suffix:
            raise ValueError('execution_result_selected_action_missing')
        row = self.store.db.execute('SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?', (self.run_id, episode_id, int(suffix))).fetchone()
        if row is None:
            raise ValueError('execution_result_selected_action_missing')
        action = json.loads(row['action'])
        if action.get('kind') != 'tool' or action.get('tool') != name or action.get('arguments') != arguments:
            raise ValueError('execution_result_selected_action_conflict')
        return row

def reader_from_bound_owner(workflow, bound_owner):
    """Transfer only actual workflow/selected-owner metadata to the read factory.

    The service selects bound_owner from its own registry. No user-provided
    directory, run identity or replacement receiving authority is accepted.
    """
    from .native_protein_structure_results import NativeProteinStructureResults
    from .native_protein_structure_returns import NativeProteinStructureReturns
    if bound_owner is None:
        raise ValueError('protein_structure_retained_reader_missing')
    original = getattr(bound_owner, 'native_protein_structure_returns', None)
    results = getattr(bound_owner, 'native_protein_structure_results', None)
    if original is None or results is None:
        raise ValueError('protein_structure_retained_reader_missing')
    if type(original) is not NativeProteinStructureReturns or type(results) is not NativeProteinStructureResults or original.owner is not bound_owner or (original.results is not results) or (results.owner is not bound_owner) or (bound_owner.store is not workflow.store) or (original.store is not workflow.store) or (results.store is not workflow.store) or (bound_owner.run_id != workflow.run_id) or (original.run_id != workflow.run_id):
        raise ValueError('protein_structure_retained_reader_metadata_invalid')
    return RetainedProteinReader.retained_protein_structure_reader(workflow.store, run_id=workflow.run_id, directory=bound_owner.directory)
