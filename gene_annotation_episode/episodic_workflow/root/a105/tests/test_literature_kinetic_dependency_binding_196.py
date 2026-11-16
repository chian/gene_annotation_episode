"""Generation-bound kinetics and authentic original-release reconstruction.

All sources are synthetic. The original-v2 states were selected with intact
archived production code before this repair, never relabelled from new results.
"""
import hashlib
import sqlite3
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_storage import LiteratureKineticRepository
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_model_storage import LiteratureKineticModelRepository
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_kinetic_inputs import fixture
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_kinetic_storage import setup

def hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}

def readonly(path):
    store = Store.__new__(Store)
    store.path, store._savepoint = (path.resolve(), 0)
    store.db = sqlite3.connect(f"file:{store.path / 'state.sqlite3'}?mode=ro&immutable=1", uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    store.db.execute('PRAGMA query_only=ON')
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    return store





def test_discovery_does_not_install_optional_tables_on_readonly_state(tmp_path):
    store, context, _ = setup(tmp_path)
    store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    store.close()
    before = hashes(tmp_path)
    with readonly(tmp_path) as restored:
        for factory in (LiteratureKineticRepository, LiteratureKineticModelRepository):
            repo = factory(restored, context.run_id)
            assert repo.received_cells(context) == []
            assert not repo._installed(repo.operations_table)
        assert restored.db.total_changes == 0
    assert hashes(tmp_path) == before



@pytest.mark.parametrize('token', ['-8', '18', '8e3', 'between 8 and 9', 'SD 8', '8/2'])
def test_called_scalar_contract_rejects_clipping_and_wrong_scientific_role(token):
    source, selection = fixture(n=token)
    number = selection['numerator']['measurement']['number']
    number.update(witness=source.witness('8'), number_start=0, number_end=1)
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)

@pytest.mark.parametrize('unit', ['M^-1</td><td>s^-1', 'uM^-1min^-1/mg'])
def test_selected_compound_unit_cannot_cross_cells_or_omit_factor(unit):
    source, selection = fixture(unit=unit)
    if '/mg' in unit:
        selection['numerator']['measurement']['unit'] = source.witness('uM^-1min^-1')
    with pytest.raises(ExperimentalContractError):
        read_kinetic_inputs(selection, read_source=source.read)


