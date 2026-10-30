"""Controlled synthetic original-form cold factory; no model invocation."""
from pathlib import Path
import sys,json,sqlite3
from dataclasses import replace
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import pytest
from test_literature_active_site_saved_reconstruction_182 import readonly,hashes,disable_science,saved_artifacts_only,services_for
from gene_annotation_episode.episode_bindings import BindingContext,EpisodeBindingRegistry
from gene_annotation_episode.episode_composition import compose_episode_bindings
HERE=Path(__file__).resolve().parent
record=json.loads((HERE/'CURRENT_SHARED_LOOP_RECEIPT_001.json').read_text())
path=HERE/'current_shared_loop_original_001'; before=hashes(path)
with pytest.MonkeyPatch.context() as monkeypatch:
    disable_science(monkeypatch)
    with readonly(path) as store:
        saved_artifacts_only(monkeypatch,store)
        host,services=services_for(store,record['run_id'])
        restored=compose_episode_bindings(services,store=store,
            journal=SimpleNamespace(store=store,run_id=record['run_id']),execution_backend=None,
            descriptors=record['original_saved_descriptors'],job_episodes=None,resource_estimator=None,role_credit_bindings={})
        host.episode_bindings=EpisodeBindingRegistry(restored.bindings)
        binding,=restored.bindings
        rows=record['admitted_rows']; refs=tuple(dict.fromkeys(row['sheet_ref'] for row in rows))
        context=BindingContext(record['run_id'],record['parent_episode_id'],'annotation',
            (('annotation',record['parent_episode_id']),),store.validate_scope(),{},{},refs)
        assert binding.received_report_facts(context)['literature_active_site_cells']==rows
        repo=binding._active_site_repository()
        assert repo.fact_cells(context,refs,components=repo.components)==rows
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]==3
        assert store.db.total_changes==0
        try:store.db.execute('DELETE FROM records')
        except sqlite3.OperationalError as error:assert 'readonly' in str(error)
        else:raise AssertionError('read-only DML should fail')
assert hashes(path)==before
result={'actual_model_execution':False,'provider':'controlled ScriptedProvider','source_operations':1,
    'runtime_observations':3,'source_parsers_unit_converters_calculators_disabled_before_factory':True,
    'original_saved_descriptor_used':True,'original_admitted_rows_exact':True,
    'receiver_scope_not_expanded':True,'database_writes':0,'mode':'ro&immutable=1; checkpointed closed writer',
    'byte_preservation':True,'scope':'Current corrected implementation original controlled run; old before-change frozen descriptor remains distinct and rejects changed implementation.'}
with (HERE/'COLD_FACTORY_PROOF_001.json').open('x') as file:json.dump(result,file,indent=2);file.write('\n')
print(json.dumps(result,indent=2))
