"""Window isolation without starting a second local workflow."""
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_lifecycle, workflow_budget
from gene_annotation_episode.local_resources import LocalResources


def test_window_identity_is_stable_and_separates_services_and_slices():
    first = workflow_budget.window_units('00000000-0000-0000-0000-000000000001')
    second = workflow_budget.window_units('00000000-0000-0000-0000-000000000002')
    assert first == workflow_budget.window_units('00000000-0000-0000-0000-000000000001')
    assert first[0] != second[0] and first[1] != second[1]
    # A hyphenated slice would inherit the old global parent's aggregate cap.
    assert '-' not in first[1]
    with pytest.raises(ValueError, match='stable_codex_window_identity_required'):
        workflow_budget.window_units('')


def test_cleanup_leaves_other_windows_native_workers_alone(monkeypatch):
    own = 'gene-local-job-own.service'
    other = 'gene-local-job-other.service'
    calls = []

    def control(*args):
        calls.append(args)
        return SimpleNamespace(stdout=f'{own} loaded inactive dead\n{other} loaded active running\n')

    monkeypatch.setattr(workflow_budget, '_control', control)
    monkeypatch.setattr(workflow_budget, '_properties', lambda unit: {
        'Slice': workflow_budget.SLICE if unit == own else 'anotherwindow.slice',
        'ActiveState': 'inactive' if unit == own else 'active', 'LoadState': 'loaded'})
    workflow_budget.cleanup()
    assert ('--no-block', 'stop', own) in calls
    assert ('reset-failed', own) in calls
    assert all(other not in args for args in calls)


def test_capacity_counts_only_the_configured_window_slice(tmp_path, monkeypatch):
    own = 'gene-local-job-own.service'
    other = 'gene-local-job-other.service'
    monkeypatch.setattr(native_lifecycle, '_control', lambda _: SimpleNamespace(
        returncode=0, stdout=f'{own} loaded active running\n{other} loaded active running\n'))
    monkeypatch.setattr(native_lifecycle, '_properties', lambda unit: {
        'Slice': workflow_budget.SLICE if unit == own else 'anotherwindow.slice'})
    resources = LocalResources(tmp_path/'capacity', workflow_slice=workflow_budget.SLICE)
    assert LocalResources.reopen(resources.as_record()).as_record() == resources.as_record()
    view = resources.snapshot()
    assert [job['execution_handle'] for job in view['jobs']] == [own]
    assert view['reserved']['job_slots'] == 1
