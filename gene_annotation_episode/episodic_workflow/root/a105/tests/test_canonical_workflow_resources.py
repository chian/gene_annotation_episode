"""Real launcher authentication and offline constructors preserve resource checks.

Run through the existing one-workflow launcher. No native worker, provider or
nested workflow is started. The checker uses the actual current owner/cgroup.
"""
from importlib import import_module,util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from gene_annotation_episode import workflow_budget as canonical

PACKAGE=__package__.rsplit('.tests',1)[0]

def selected_checker():
    original=PACKAGE+'.workflow_budget'
    return import_module(original) if util.find_spec(original) is not None else canonical


def test_actual_live_owner_matches_canonical_machine_bounds():
    actual=selected_checker().active_budget()
    assert actual==canonical.active_budget()
    assert actual['environment_bounds']=={'cpu_percent':100,'memory_bytes':5*1024**3,'swap_bytes':0}
    assert actual['window_id']==canonical.WINDOW_ID
    assert actual['unit']==canonical.UNIT and actual['slice']==canonical.SLICE


def test_actual_registry_constructor_uses_authenticated_run_resources(tmp_path,monkeypatch):
    local=import_module(PACKAGE+'.local_resources')
    monkeypatch.delenv(local.DIRECTORY_ENV,raising=False)
    budget=canonical.active_budget()
    store=import_module(PACKAGE+'.state').Store(tmp_path/'state')
    try:
        registry=import_module(PACKAGE+'.tools').ToolRegistry(store,clients=SimpleNamespace())
        record=registry.local_resources.as_record()
        assert record['directory']==str(Path(budget['run_directory'])/'local-resources')
        assert record['workflow_slice']==budget['slice']
        assert registry.local_job_policy.memory_bytes<=budget['environment_bounds']['memory_bytes']
        assert store.db.execute("SELECT name FROM sqlite_master WHERE name='tool_operations'").fetchone() is not None
    finally:store.close()


def test_original_owner_identity_rejection_remains_active(tmp_path,monkeypatch):
    checker=selected_checker();value=checker.active_budget()
    directory=tmp_path/'invalid-owner';directory.mkdir()
    bad={**value,'run_directory':str(directory),'supervisor_start_ticks':'invalid-original-owner-start'}
    selected=directory/'workflow-budget.json';selected.write_text(json.dumps(bad))
    monkeypatch.setenv(checker.ENV,str(selected))
    with pytest.raises(ValueError,match='workflow_budget_owner_not_active'):checker.active_budget()


def test_original_native_memory_bound_rejects_oversized_request_without_launch(tmp_path):
    checker=selected_checker();value=checker.active_budget()
    memory=value['environment_bounds']['memory_bytes']+1
    with pytest.raises(ValueError,match='native_request_exceeds_environment_bounds'):
        checker.native_budget(SimpleNamespace(memory_bytes=memory),1,tmp_path)
