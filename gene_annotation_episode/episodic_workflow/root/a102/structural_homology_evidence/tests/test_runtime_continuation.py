"""A102 credit and continuation on episode_runtime: real bindings, real Store, real run journal.

Each Episode is bound as the runner binds it (journaled commission, recorder,
progress clock). Controllers are the yield_control controllers;
credits come from A102's own projections over a real Store. No decision
source runs here (the monitors' decision source needs a model provider and an A102 progress provider).
"""
import pytest

from episode_runtime import (BindingRegistry, BoundEpisode, EpisodeRecorder, Field, LinkError, ProgressClock,
                             RecordForm, RunJournal, link)
from gene_annotation_episode.episodic_workflow.episode_support.tools.commissioned_report import (
    CommissionedReportError, added_fields, report_fields)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.service_calls.structural_homology_evidence.monitor_runtime import monitor_facts, report_facts
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import \
    a102_progress_provider
from method_loop import EpisodeRef
from gene_annotation_episode.state import Store
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.credit import A102StructuralCredit
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.publication import publish_comparison
from yield_control import BoundedQualityYieldController, YieldParameters
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.tests.test_a102_scoring import native
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.execution_progress_assessment.episode import \
    MonitorEpisode
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.runtime_continuation import (
    A102Continuation, A102ContinuationState, A102UnitInput, episode_epoch, unit_input)
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.runtime_head import head_credit

MONITOR_SETTINGS = {'kind': 'information_accumulation', 'cutoff': 0.25, 'uncertainty_alpha': 0.05}


def bind(journal, run_id, binding_path, grain_name, commission, form, report_form):
    """Record and bind one entry Episode exactly as episode_runtime does before building it."""
    path = ((grain_name, run_id),)
    assignment = form.admit(commission.assignment, 'assignment:' + binding_path)
    journal.open_run(run_id, {'entry_path': binding_path, 'entry_input': {}, 'ancestors': [], 'key': run_id})
    journal.open_episode(run_id, path, binding_path, {'request': commission.request.as_record(),
                                                      'assignment': dict(assignment)})
    recorder = EpisodeRecorder(journal, run_id, path)
    episode_id = EpisodeRef(run_id, path).episode_id
    return BoundEpisode(run_id, binding_path, path, run_id, episode_id, commission.request, assignment, recorder,
                        ProgressClock(recorder, run_id=run_id, episode_id=episode_id), report_form)


@pytest.fixture
def store(tmp_path):
    with Store(tmp_path / 'state') as value:
        yield value


@pytest.fixture
def journal(tmp_path):
    return RunJournal(tmp_path / 'journal.sqlite')


def monitor_bound(store, journal, binding, run_id='run-monitor', target=None):
    if target is None:
        target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
    commission = binding.entry_request({'scope': {'subject_refs': [target]}, 'target_handle': 'job:structure-align',
                                        'requested_fields': ['execution_status'], 'known_progress_refs': [],
                                        'permitted_committed_record_types': []}, {}, parent_goal=None)
    return bind(journal, run_id, binding.binding_path, binding.grain_name, commission, binding.assignment_form,
                binding.return_form)


def test_monitor_binding_registers_and_requires_its_runtime_collaborators(store, journal):
    monitor = MonitorEpisode(information_unit=2.5, yield_settings=MONITOR_SETTINGS, tool_registry=ToolRegistry(store))
    registry = BindingRegistry([monitor])
    assert registry.paths == (monitor.binding_path,)
    assert monitor.child_slots == {'execution_progress_assessment': monitor.binding_path}
    assert monitor.required_collaborators == ('model_provider', 'store', 'a102_progress_provider')
    assert monitor.assignment_form.declared == {'version': 'monitor_assignment_v1'}
    target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
    with pytest.raises(LinkError, match='collaborator_required:' + monitor.binding_path):
        link(registry, monitor.binding_path, {'scope': {'subject_refs': [target]}, 'target_handle': 'job:x',
                                              'requested_fields': [], 'known_progress_refs': [],
                                              'permitted_committed_record_types': []},
             run_id='unlinked', journal=journal, collaborators={'store': store})


def test_unit_input_journal_round_trip_restores_the_same_controller_input(store, journal):
    monitor = MonitorEpisode(information_unit=2.5, yield_settings=MONITOR_SETTINGS, tool_registry=ToolRegistry(store))
    bound = monitor_bound(store, journal, monitor)
    value = unit_input(bound, 0, 12.5, ('progress:a', 'progress:b'))
    journal.record_unit(bound.run_id, bound.path, 0, 'tool:0', value.as_record())
    (label, recorded), = journal.units(bound.run_id, bound.path)
    restored = A102UnitInput.from_record(recorded)
    assert label == 'tool:0' and restored == value and restored.credit == 12.5
    # The receipt is recorded once: reading it again returns the recorded value.
    assert bound.progress.receipt(0) == recorded['estimation_context']['progress_time']
    with pytest.raises(ValueError, match='a102_unit_input_record_requires'):
        A102UnitInput.from_record({'credit': 1.0})
    with pytest.raises(ValueError, match='a102_unit_credit_must_be_a_finite_number'):
        A102UnitInput(True, recorded['estimation_context']['progress_time'], ())


def test_head_credit_is_its_own_projection_over_the_records_it_received(store, journal):
    target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
    row = native()
    row.update(target_ref=target, producer='synthetic_geometry_fixture')
    published = publish_comparison(store, row)['source_ref']
    scope = store.validate_scope({'subject_refs': [target]})
    projector = A102StructuralCredit()

    # Nothing received: no native correspondence credit.
    assert head_credit(projector, store, scope, None, ())[0] == 0.0
    # A child's admitted finding named the published comparison: the head's own native
    # correspondence over it (a child's own credit on its scale is never summed in).
    credit, view = head_credit(projector, store, scope, None, (published,))
    assert credit == pytest.approx(.72)

    # The head's own bounded-quality A102 controller observes that credit at the recorded receipt.
    monitor = MonitorEpisode(information_unit=2.5, yield_settings=MONITOR_SETTINGS, tool_registry=ToolRegistry(store))
    bound = monitor_bound(store, journal, monitor, run_id='run-head', target=target)
    controller = A102Continuation(BoundedQualityYieldController(episode_epoch(bound), 0.0, 0.01, projector.native_score_maximum,
                                                                YieldParameters(uncertainty_alpha=0.05)))
    step = controller.observe('child:0', unit_input(bound, 0, credit, (published,)), is_root=True)
    assert type(step.stop) is bool
    assert controller.state().yield_state.current_credit == pytest.approx(.72)


def test_monitor_fills_a_commissioned_report_form_from_its_recorded_facts(store):
    """C5: a parent's report form may add the monitor's recorded report facts; anything else raises."""
    monitor = MonitorEpisode(information_unit=2.5, yield_settings=MONITOR_SETTINGS, tool_registry=ToolRegistry(store))
    facts = report_facts()
    assert facts['monitoring_target_handle'] == ('text', False)
    assert facts['monitoring_execution_state'] == ('text', True)
    assert facts['monitoring_progress_refs'] == ('list', False)
    form = RecordForm({**monitor.return_form.fields,
                       'monitoring_target_handle': Field('text', 'The assigned target'),
                       'monitoring_execution_state': Field('text', 'Latest observed state', required=False)})
    names = added_fields(form, monitor.return_form, facts, 'monitor')
    assert names == ('monitoring_execution_state', 'monitoring_target_handle')

    # Nothing received yet: the target is known, its state is unknown and stays absent.
    target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
    scope = store.validate_scope({'subject_refs': [target]})
    assignment = {'version': 'monitor_assignment_v1', 'target_handle': 'job:structure-align',
                  'requested_fields': ['execution_status'], 'known_progress_refs': [],
                  'permitted_committed_record_types': []}
    finding = monitor_facts(a102_progress_provider(store, run_id='run-monitor'), store, assignment, scope, [])
    report = form.admit({'credit': 0.0, 'finding': finding, **report_fields(names, finding, 'monitor')}, 'report')
    assert report['monitoring_target_handle'] == 'job:structure-align'
    assert 'monitoring_execution_state' not in report

    with pytest.raises(CommissionedReportError, match='has_no_fact:monitoring_wall_seconds'):
        added_fields(RecordForm({**monitor.return_form.fields, 'monitoring_wall_seconds': Field('number', 'x')}),
                     monitor.return_form, facts, 'monitor')
    with pytest.raises(CommissionedReportError, match='may_be_unknown_must_be_optional:monitoring_execution_state'):
        added_fields(RecordForm({**monitor.return_form.fields,
                                 'monitoring_execution_state': Field('text', 'Latest observed state')}),
                     monitor.return_form, facts, 'monitor')
