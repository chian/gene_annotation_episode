"""A107 HPC planning and allocation execution under a parent's commissioned report form (C5).

Each Episode is a real ``BoundEpisode`` of the real binding, journaled in a real ``RunJournal``
and admitted against a test-written report form. No model, network or HPC job is used.
"""
import pytest

from episode_runtime import Field, RecordForm, RunJournal
from episode_runtime.journal import EpisodeRecorder
from episode_runtime.progress import ProgressClock
from episode_runtime.runner import BoundEpisode
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning import hpc_runtime
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.episode import \
    HPCEpisode as PlanningEpisode
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning \
    .hpc_allocation_execution import allocation_runtime
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning \
    .hpc_allocation_execution.episode import HPCEpisode as AllocationEpisode
from method_loop import EpisodeRef

RUN = 'a107-commissioned-report-run'


def _form(return_form, **added):
    return RecordForm({**return_form.fields, **added})


def _bound(binding, tmp_path, name, report_form):
    journal = RunJournal(tmp_path / (name + '.sqlite'))
    commission = binding.entry_request({'objective': 'Plan the work', 'scope': {'subject_refs': ['s']},
                                        'assignment': {}}, {}, parent_goal=None)
    path = ((binding.grain_name, 'k'),)
    journal.open_run(RUN, {'entry_path': binding.binding_path})
    journal.open_episode(RUN, path, binding.binding_path, commission.as_record())
    recorder = EpisodeRecorder(journal, RUN, path)
    episode_id = EpisodeRef(RUN, path).episode_id
    return BoundEpisode(run_id=RUN, binding_path=binding.binding_path, path=path, key='k', episode_id=episode_id,
                        request=commission.request, assignment=commission.assignment, recorder=recorder,
                        progress=ProgressClock(recorder, run_id=RUN, episode_id=episode_id), report_form=report_form)


@pytest.mark.parametrize('binding, held', [(PlanningEpisode(), hpc_runtime.PLANNING_REPORT_FIELDS),
                                           (AllocationEpisode(), allocation_runtime.EXECUTION_REPORT_FIELDS)])
def test_commissioned_report_form_adds_only_held_finding_fields(binding, held, tmp_path):
    own = _bound(binding, tmp_path, 'own', binding.return_form)
    assert hpc_runtime.commissioned_report_fields(binding, own, held) == ()
    form = _form(binding.return_form, hpc_credit=Field('record', 'The HPC credit view'),
                 ended_by=Field('text', 'How the Episode ended', required=False))
    assert hpc_runtime.commissioned_report_fields(binding, _bound(binding, tmp_path, 'added', form), held) == (
        'hpc_credit', 'ended_by')
    wrong = _bound(binding, tmp_path, 'wrong', _form(binding.return_form, summary=Field('text', 'Never recorded')))
    with pytest.raises(hpc_runtime.HPCRuntimeError,
                       match='a107_hpc_commissioned_report_field_not_held:' + binding.binding_path + ':summary'):
        hpc_runtime.commissioned_report_fields(binding, wrong, held)


def test_result_record_lifts_added_fields_and_leaves_unknown_ones_absent():
    finding = {'hpc_credit': {'credit': 2.0}, 'hpc_job_id': None, 'ended_by': 'controller'}
    record = hpc_runtime.result_record(2.0, finding, ('hpc_credit', 'hpc_job_id')).as_record()
    assert record == {'credit': 2.0, 'finding': finding, 'hpc_credit': {'credit': 2.0}}
