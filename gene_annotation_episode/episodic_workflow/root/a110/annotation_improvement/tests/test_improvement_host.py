"""Private improvement task, report, credit, continuation and saved state."""
import pytest
from ...tests import test_implicit_annotation_parent as original
from .host_checks import (paired, construction, mutable_default, nested_refusal,
    returned_outcome, report, continuation, credit, live_report, instructions)


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    monkeypatch.setattr('subprocess.Popen', original.forbidden)
    monkeypatch.setattr('socket.socket.connect', original.forbidden)
    monkeypatch.setattr('socket.socket.connect_ex', original.forbidden)


def test_actual_improvement_state_saved_request_and_reconstruction(tmp_path):
    paired(tmp_path, construction)


@pytest.mark.parametrize('raises', (False, True))
def test_original_mutable_default_precedes_private_improvement_selection(tmp_path, raises):
    paired(tmp_path, mutable_default, raises)


@pytest.mark.parametrize('parent_role', ('annotation', 'improvement'))
def test_default_nested_improvement_retains_missing_projector_error(tmp_path, parent_role):
    paired(tmp_path, nested_refusal, parent_role)


@pytest.mark.parametrize('status', ('completed', 'failed', 'invalid', 'unavailable'))
def test_actual_returned_and_replayed_outcomes_keep_original_observation(tmp_path, status):
    paired(tmp_path, returned_outcome, status)


@pytest.mark.parametrize('mode', ('root', 'typed', 'saved'))
def test_improvement_original_report_projection_and_saved_reuse(tmp_path, mode):
    paired(tmp_path, report, mode)


@pytest.mark.parametrize('nested', (False, True))
def test_original_task_aware_continuation_and_nested_refusal(tmp_path, nested):
    paired(tmp_path, continuation, nested)


def test_improvement_uses_actual_projector_and_signed_credit(tmp_path):
    paired(tmp_path, credit)


def test_improvement_report_reads_mutable_original_record_after_import(tmp_path):
    paired(tmp_path, live_report)


def test_improvement_instructions_keep_late_job_specialist_and_text_callbacks(tmp_path):
    paired(tmp_path, instructions)



def test_actual_unbound_improvement_selects_private_source_with_original_state(tmp_path):
    runtime = original.module('runtime')
    with original.actual_workflow(tmp_path) as workflow:
        episode = workflow.build('improvement', 'standalone', 'Retain original fallback',
                                 workflow.store.validate_scope())
        assert type(episode.source) is original.module('annotation_improvement.task').ImprovementTask
        assert isinstance(episode.source, runtime.DecisionSource)
        before = original.predecessor_source(workflow, episode.source)
        assert vars(before) == vars(episode.source)
        assert before.request.as_record() == episode.request.as_record()
