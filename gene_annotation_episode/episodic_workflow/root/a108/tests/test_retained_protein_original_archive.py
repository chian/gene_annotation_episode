"""Actual original336 receipt/typed authority read with closed physical transport."""
from copy import deepcopy
from importlib import import_module
import json

import pytest

from .retained_protein_archive import LOGICAL,RetainedProteinArchive


@pytest.fixture(scope='module')
def archive():
    case=RetainedProteinArchive()
    yield case
    case.verify_unchanged()


@pytest.mark.parametrize('axis',['a101','a105','a106','a108'])
def test_original_receipts_and_earlier_denials_survive_relocated_reader(axis,monkeypatch,archive):
    prefix='gene_annotation_episode.episodic_workflow.root.'+axis+'.'
    owner_class=import_module(prefix+'library.retained_input_authority.retained_protein_owner').RetainedProteinReader
    error=import_module(prefix+'library.retained_input_authority.protein_structure_authority').ProteinStructureOperandError
    with archive.control_transport(monkeypatch,axis),archive.open_store(axis) as store:
        runs=store.db.execute('SELECT DISTINCT run_id FROM runtime_episodes').fetchall()
        assert len(runs)==1
        run=runs[0]['run_id']
        returns=owner_class.retained_protein_structure_reader(store,run_id=run,directory=LOGICAL/'run')
        results=returns.results
        rows=store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND result IS NOT NULL "
             "AND json_extract(result,'$.result.version')='native_protein_structure_acquired_result_v1' ORDER BY rowid",(run,)).fetchall()
        receipts=[json.loads(row['result'])['result'] for row in rows]
        assert len(receipts)==3
        for receipt in receipts:
            intent=receipt['body']['intent']
            actual=results.receipts.read_completed(episode_id=intent['episode_id'],operation_key=intent['operation_key'],scope=intent['scope'])
            assert actual==receipt
            assert results.read_result_authority(receipt['publication']['custody'],scope=intent['scope'])['custody']==receipt['publication']['custody']
        contexts=[returns.context(row['episode_id']) for row in store.db.execute(
                  'SELECT episode_id FROM runtime_episodes WHERE run_id=?',(run,))]
        science={context.assignment['context']['fixture_phase']:context for context in contexts if context.role=='scientific_process'}
        assert {'earlier','align_compare'}<=set(science)
        late,early=science['align_compare'],science['earlier']
        sequence_fact=import_module(prefix+'library.retained_input_authority.native_protein_structure_returns').SEQUENCE_SOURCE
        descriptors=[value for receipt in receipts for value in receipt['publication']['facts'][sequence_fact]]
        assert descriptors
        for descriptor in descriptors:
            assert returns.authenticate_received_sequence(late,descriptor,required_use='sequence_align')['custody']==descriptor['custody']
            with pytest.raises(error):returns.authenticate_received_sequence(early,descriptor,required_use='sequence_align')
            changed=deepcopy(descriptor);changed['custody']['result_operation_key']+='9'
            with pytest.raises(error):returns.authenticate_received_sequence(late,changed,required_use='sequence_align')
        assert store.db.total_changes==0
    assert archive.transported
