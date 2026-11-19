"""A real run started at the A108 head (``sample_context_evidence``), calling the model, to its own end.

Real pieces only: the A108 home factory composed by ``BindingRegistry.compose`` over the run's one
``Store``, the repository's slotted process library frozen for the run, each A108 binding's own
``ToolRegistry`` over that store, a real ``RunJournal`` and the standard ``ModelProvider`` over the
packaged ``[models]`` configuration (the Codex app-server). The subject is the repository's known
protein sequence (``tests/fixtures/a108/known_sequence.txt``; only its raw residues enter the run).

The head's assignment is filled the way the root fills it (``root/decisions.axis_assignment``): the
held subject scope, the head's own declared ``evidence_task`` and the two choices the head declares
(``thought_pattern`` and ``tools``). The run is started with ``episode_runtime.link`` and awaited.
Nothing limits it: every episode in it ends when its own continuation stops it. The continuation and
credit settings are the packaged ones (``defaults.toml``: ``[controller]`` and ``[scientific_progress]``).

The test then reads what the run did from the journal and the result, and resumes the finished run
from its journal over the reopened store with a second model provider that must receive no call.

Outside services other than the model are closed for this run by the command that starts it (the HTTP
proxy settings), so a public acquisition tool returns a failed outcome, which enters the iterator.
"""
import asyncio
import hashlib
import json
import math
from pathlib import Path
import time
import tomllib

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from gene_annotation_episode.model_provider import ModelProvider, default_config_path, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.sample_context_evidence.acquisition import (
    PublicClients)
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sample_context_evidence.process_options import (
    SampleContextEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.published_evidence_assessment.\
    literature_credit import YIELD_TASKS
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.runtime_contract import (
    AXIS, HEAD_PATH, a108_home_factory)
from gene_annotation_episode.episodic_workflow.root.a108.sample_context_evidence.runtime_source import (
    head_credit_projector)

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
SEQUENCE_PROVENANCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence_provenance.json'
RUN_ID = 'a108_head_model_run'
# The library thought pattern this commission investigates with: "Choose a relevant analogue and bound
# what transfers" (the root's model makes this choice per commission; the entry caller makes it here).
THOUGHT_PATTERN = 'P01'


def _services(tmp_path, store):
    """The A108 home factory's construction services, with the packaged continuation and credit settings."""
    packaged = tomllib.loads(default_config_path().read_text())
    cutoff, alpha = packaged['controller']['cost'], packaged['controller']['uncertainty_alpha']
    unit = packaged['scientific_progress']['finding_unit']
    library_directory = tmp_path / 'library'
    library = (SampleContextEvidenceLibrary(library_directory) if library_directory.exists()
               else SampleContextEvidenceLibrary.freeze(library_directory, source=LIBRARY_SOURCE))
    projector = head_credit_projector({'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings',
                                       'evidence_axis': AXIS, 'credit_unit': unit})
    return {'store': store, 'a108': {
        'binding_services': {},
        'head': {'library': library, 'child_roles': ('sample_context_evidence', 'literature'),
                 'yield_bindings': {AXIS + ':whole_axis_findings': {
                     'kind': projector.yield_method, 'cutoff': cutoff, 'parameters': {'uncertainty_alpha': alpha},
                     'credit_definition': projector.as_record()}}},
        # No contact address, skill client directory or PDF executables are configured for this run.
        'tools': {'clients': PublicClients(ncbi_email=None), 'job_limits': {}},
        'literature': {'yield_bindings': {
            task: {'credit_unit': unit, 'cutoff': cutoff, 'uncertainty_alpha': alpha,
                   'kind': 'accumulation' if task.endswith(':verified_source_leads')
                   else 'remaining_commissioned_credit'} for task in sorted(YIELD_TASKS)},
            'outcome_page_size': packaged['restoration']['preview_size']}}}


def _calls(directory):
    return sorted(path.name for path in Path(directory).glob('call-*'))


def _journal_rows(journal):
    """Everything the journal holds for the run, as decoded records."""
    decisions = [(json.loads(path), name, json.loads(value)) for path, name, value in journal.db.execute(
        'SELECT path, name, value FROM decisions WHERE run_id=? ORDER BY rowid', (RUN_ID,))]
    units = [(json.loads(path), index, label, json.loads(value)) for path, index, label, value in journal.db.execute(
        'SELECT path, unit_index, label, controller_input FROM units WHERE run_id=? ORDER BY rowid', (RUN_ID,))]
    episodes = [(json.loads(path), binding, state, json.loads(commission),
                 None if completion is None else json.loads(completion),
                 None if result is None else json.loads(result))
                for path, binding, state, commission, completion, result in journal.db.execute(
                    'SELECT path, binding_path, state, commission, completion, result FROM episodes '
                    'WHERE run_id=? ORDER BY rowid', (RUN_ID,))]
    return decisions, units, episodes


def _summary(journal, model_calls):
    """The run in numbers, from the journal: per episode and in total."""
    decisions, units, episodes = _journal_rows(journal)
    rows, total = [], {'model_decisions': 0, 'rejected_responses': 0, 'units': 0, 'units_by_kind': {},
                       'outcomes_by_status': {}, 'tool_outcomes': {}}
    for path, binding, state, _, completion, result in episodes:
        own = [(name, value) for where, name, value in decisions if where == path]
        responses = [name for name, _ in own if name.startswith('decision.')]
        outcomes = [value for name, value in own if name.startswith('outcome.')]
        own_units = [label for where, _, label, _ in units if where == path]
        kinds, statuses = {}, {}
        for outcome in outcomes:
            kinds[outcome['kind']] = kinds.get(outcome['kind'], 0) + 1
            statuses[outcome['status']] = statuses.get(outcome['status'], 0) + 1
            total['units_by_kind'][outcome['kind']] = total['units_by_kind'].get(outcome['kind'], 0) + 1
            total['outcomes_by_status'][outcome['status']] = total['outcomes_by_status'].get(outcome['status'], 0) + 1
        # A unit is acquired from the last response of its position; every earlier response was rejected.
        accepted = {}
        for name, value in own:
            if name.startswith('decision.'):
                accepted[name.split('.')[1]] = value
        recorded = dict(own)
        for position, value in accepted.items():
            outcome = recorded.get('outcome.' + position)
            selection = value.get('selection') if isinstance(value, dict) else None
            if outcome is not None and outcome['kind'] == 'tool' and isinstance(selection, dict):
                by_status = total['tool_outcomes'].setdefault(str(selection.get('tool')), {})
                by_status[outcome['status']] = by_status.get(outcome['status'], 0) + 1
        rejected = len(responses) - len(accepted)
        rows.append({'path': path, 'binding_path': binding, 'state': state, 'completion': completion,
                     'credit': None if result is None else result['credit'],
                     'model_decisions': len(responses), 'rejected_responses': rejected,
                     'units': len(own_units), 'outcomes_by_kind': kinds, 'outcomes_by_status': statuses})
        total['model_decisions'] += len(responses)
        total['rejected_responses'] += rejected
        total['units'] += len(own_units)
    return {'run_id': RUN_ID, 'model_calls': len(model_calls), 'total': total, 'episodes': rows,
            'children': [{'path': path, 'binding_path': binding, 'state': state, 'completion': completion,
                          'credit': None if result is None else result['credit']}
                         for path, binding, state, _, completion, result in episodes[1:]]}


@pytest.mark.model_run
def test_head_run_calls_the_model_and_ends_by_its_own_continuation(tmp_path):
    sequence = SEQUENCE.read_text().strip()
    provenance = json.loads(SEQUENCE_PROVENANCE.read_text())
    assert hashlib.sha256(sequence.encode()).hexdigest() == provenance['sequence_sha256']
    assert len(sequence) == provenance['sequence_length']
    models = load_config()
    journal_path = tmp_path / 'journal.sqlite'
    (tmp_path / 'model_cwd').mkdir()

    started = time.monotonic()
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a108_home_factory], _services(tmp_path, store))
        head = registry.binding(HEAD_PATH)
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        scope = store.validate_scope({'subject_refs': [target]})
        # The root's own filling of this head's declared assignment: the held scope, the declared
        # evidence task, and the head's two choices (here every tool the head offers).
        choices = {'thought_pattern': THOUGHT_PATTERN, 'tools': list(head.selectable_tools)}
        assignment = axis_assignment(HEAD_PATH, head, {'scope': scope}, choices)
        assert assignment == head.assignment_form.admit(assignment, 'a108_model_run_assignment')
        entry = {name: assignment[name] for name in ('scope', 'thought_pattern', 'tools')}
        provider = ModelProvider(models, tmp_path / 'model_calls', tmp_path / 'model_cwd')
        journal = RunJournal(journal_path)
        collaborators = {'store': store, 'model_provider': provider}
        run = link(registry, HEAD_PATH, entry, run_id=RUN_ID, journal=journal, collaborators=collaborators)
        finished = asyncio.run(run.run())
        seconds = time.monotonic() - started
        record, result = finished['record'], finished['result'].as_record()
        calls = _calls(tmp_path / 'model_calls')
        summary = _summary(journal, calls)
        summary.update(seconds=seconds, ended_by=record.ended_by, units=record.units_consumed,
                       credit=result['credit'], finding=result['finding'],
                       controller=record.controller_state.as_record()['decision'])
        (tmp_path / 'run_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')

        decisions, units, episodes = _journal_rows(journal)
        entry_path, entry_binding, _, commission, _, entry_result = episodes[0]
        assert entry_binding == HEAD_PATH
        # The admitted commission is the root-filled assignment.
        assert commission['assignment'] == json.loads(json.dumps(assignment))
        own = {name: value for where, name, value in decisions if where == entry_path}

        # At least one model decision was made by the real model and recorded; every recorded decision
        # of the run is one answered model call.
        assert [name for name in own if name.startswith('decision.')]
        answered = [name for name in calls if (tmp_path / 'model_calls' / name / 'response.json').is_file()]
        assert answered == calls
        assert len(calls) == sum(1 for _, name, _ in decisions if name.startswith('decision.'))
        assert own['decision.0.0'] == json.loads((tmp_path / 'model_calls' / calls[0] / 'response.json').read_text())

        # At least one unit executed, and every executed unit's outcome was recorded.
        assert record.units_consumed >= 1
        outcomes = [own['outcome.' + str(position)] for position in range(record.units_consumed)]
        assert all(outcome['kind'] in ('reason', 'tool', 'child') and type(outcome['status']) is str
                   for outcome in outcomes)

        # The controller observed each unit: its step is in the record and its input is in the journal.
        own_units = [(index, label, value) for where, index, label, value in units if where == entry_path]
        assert [index for index, _, _ in own_units] == list(range(record.units_consumed))
        assert len(record.unit_records) == record.units_consumed
        for (index, label, value), unit, outcome in zip(own_units, record.unit_records, outcomes):
            assert unit.unit_label == label
            assert unit.controller_input.as_record() == value
            assert value['unit'] == {'position': index, 'kind': outcome['kind'], 'status': outcome['status']}
            assert value['estimation_context']['progress_time']['status'] == 'available'
            assert unit.controller_step.credit == value['credit']
        assert len(record.controller_state.history) == record.units_consumed

        # The run ended by its own continuation, and so did every episode it commissioned.
        assert record.ended_by == 'yield_stop'
        assert record.controller_state.stop is True
        assert record.unit_records[-1].controller_step.stop is True
        assert all(not unit.controller_step.stop for unit in record.unit_records[:-1])
        state, closed = journal.run_state(RUN_ID)
        assert state == 'closed' and closed['ended_by'] == 'yield_stop' and closed['units'] == record.units_consumed
        for _, _, episode_state, _, completion, episode_result in episodes:
            assert episode_state == 'closed' and completion is not None and episode_result is not None
            assert completion['ended_by'] == 'yield_stop'

        # The result is admitted by the head's return form, with a numeric credit and a finding.
        assert head.return_form.admit(result, 'a108_model_run_result') == result
        assert closed['result'] == result and entry_result == result
        credit = result['credit']
        assert not isinstance(credit, bool) and isinstance(credit, (int, float)) and math.isfinite(credit)
        assert credit == record.controller_state.current_credit
        finding = result['finding']
        assert isinstance(finding, dict) and finding['scope'] == scope
        assert finding['ended_by'] == 'yield_stop' and finding['units'] == record.units_consumed
        assert credit == finding['retained_finding_count'] * assignment['evidence_task']['credit_unit']
        assert finding['evidence_refs'] == finding['known_assessment_refs']
        journal.db.close()

    # Resume the finished run from its journal over the reopened store: the same result, no model call.
    before = (decisions, units, episodes)
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a108_home_factory], _services(tmp_path, store))
        second_provider = ModelProvider(models, tmp_path / 'model_calls_resume', tmp_path / 'model_cwd')
        journal = RunJournal(journal_path)
        resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                     collaborators={'store': store, 'model_provider': second_provider}).run())
        assert resumed['result'].as_record() == result
        assert resumed['record'].ended_by == record.ended_by
        assert resumed['record'].units_consumed == record.units_consumed
        assert journal.run_state(RUN_ID) == ('closed', closed)
        assert _journal_rows(journal) == before
        assert _calls(tmp_path / 'model_calls_resume') == []
        assert _calls(tmp_path / 'model_calls') == calls
        journal.db.close()
