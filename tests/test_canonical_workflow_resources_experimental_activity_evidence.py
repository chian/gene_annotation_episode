"""Real launcher authentication and offline constructors preserve resource checks.

Run through the existing one-workflow launcher. No native worker, provider or
nested workflow is started. The checker uses the actual current owner/cgroup.
"""
from importlib import import_module,util
import json
from pathlib import Path
import pytest
from gene_annotation_episode import workflow_budget as canonical

PACKAGE='gene_annotation_episode.episodic_workflow.root.a105'

def selected_checker():
    original=PACKAGE+'.workflow_budget'
    return import_module(original) if util.find_spec(original) is not None else canonical


def test_actual_live_owner_matches_canonical_machine_bounds():
    actual=selected_checker().active_budget()
    assert actual==canonical.active_budget()
    assert actual['environment_bounds']=={'cpu_percent':100,'memory_bytes':5*1024**3,'swap_bytes':0}
    assert actual['window_id']==canonical.WINDOW_ID
    assert actual['unit']==canonical.UNIT and actual['slice']==canonical.SLICE


def test_original_owner_identity_rejection_remains_active(tmp_path,monkeypatch):
    checker=selected_checker();value=checker.active_budget()
    directory=tmp_path/'invalid-owner';directory.mkdir()
    bad={**value,'run_directory':str(directory),'supervisor_start_ticks':'invalid-original-owner-start'}
    selected=directory/'workflow-budget.json';selected.write_text(json.dumps(bad))
    monkeypatch.setenv(checker.ENV,str(selected))
    with pytest.raises(ValueError,match='workflow_budget_owner_not_active'):checker.active_budget()


