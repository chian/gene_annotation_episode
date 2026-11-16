"""Scientific edge applicability."""
import importlib
from types import SimpleNamespace
import pytest

AXIS='a107'
def own(name):return importlib.import_module('gene_annotation_episode.episodic_workflow.root.'+AXIS+'.'+name)


@pytest.mark.parametrize('child',['scientific_process','hpc_work_planning','published_evidence_assessment'])
def test_no_receipts_short_circuits_original_job_predicate(child,monkeypatch):
    module=own('scientific_process.from_child_'+child)
    def forbidden(*args):raise AssertionError('scientific parent is already known')
    workflow=SimpleNamespace(receipts=None,progress_provider=None,is_job_source=forbidden)
    assert module.receive_report(workflow,object(),{}, {},0)==[]
