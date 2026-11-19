"""A real run at the A105 head (``experimental_activity_evidence``), calling the model, to its own end.

Real pieces only: the A105 home factory, composed by ``BindingRegistry.compose``, builds the head and its
seven published-evidence bindings over the run's one shared ``Store``, each binding with its own
``A105ToolRegistry``; the frozen experimental-activity library of the repository's slotted process
library; a real ``RunJournal``; the one ``ModelProvider`` over the packaged ``[models]`` configuration,
calling the real model. The subject is the repository's known protein sequence
(``tests/fixtures/a108/known_sequence.txt``; UniProt Q04507 per its provenance file, which is not shown
to the episode). The head's assignment is filled the way the root fills it
(``root.decisions.axis_assignment``): the scope the root holds, the head's own declared evidence task,
one offered thought pattern and a subset of the offered tools.

Nothing limits the run: it ends when the head's own accumulation yield controller stops it. Services
other than the model are unreachable under the model-run command (proxy settings), so a tool that needs
one returns its real failed outcome, which enters the iterator like every other outcome.
"""
import asyncio
import json
from pathlib import Path
import shutil
import sqlite3
import tomllib

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from yield_control import YieldState

from gene_annotation_episode.model_provider import ModelProvider, default_config_path, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.configuration.experimental_activity_evidence.process_options import (
    ExperimentalActivityEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.findings.experimental_activity_evidence.investigation_progress import (
    FindingProgressPolicy, ScientificFindingProgress)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_populations import OPTIONAL
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.published_evidence_assessment.literature_credit import (
    YIELD_TASKS)
from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence.runtime_binding import (
    HEAD, ROLE_PATHS, TASK_KEY, a105_home_factory)
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
KNOWN_SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
RUN_ID = 'a105_head_model_run'
DEFAULTS = tomllib.loads(default_config_path().read_text())
# The packaged continuation and credit settings (``defaults.toml`` [controller] and [scientific_progress]).
CUTOFF = DEFAULTS['controller']['cost']
ALPHA = DEFAULTS['controller']['uncertainty_alpha']
FINDING_UNIT = DEFAULTS['scientific_progress']['finding_unit']
LOSS_PREVIEW_SIZE = DEFAULTS['scientific_progress']['loss_preview_size']
OUTCOME_PAGE_SIZE = DEFAULTS['restoration']['preview_size']
JOB_LIMITS = DEFAULTS['local_jobs']


def services(store, root):
    """The A105 home factory's construction services over the run's shared Store."""
    library = ExperimentalActivityEvidenceLibrary.freeze(root / 'library', source=LIBRARY_SOURCE)
    projector = ScientificFindingProgress(FindingProgressPolicy(FINDING_UNIT), LOSS_PREVIEW_SIZE)
    return {'store': store, 'a105': {
        'tool_settings': {'pdfinfo_executable': shutil.which('pdfinfo'),
                          'pdftotext_executable': shutil.which('pdftotext'),
                          'pdftoppm_executable': shutil.which('pdftoppm'), 'job_limits': dict(JOB_LIMITS)},
        'head': {'library': library, 'child_roles': (HEAD, 'literature'), 'yield_bindings': {TASK_KEY: {
            'kind': projector.yield_method, 'cutoff': CUTOFF, 'parameters': {'uncertainty_alpha': ALPHA},
            'credit_definition': projector.as_record()}}},
        'literature': {
            'yield_bindings': {task: {
                'credit_unit': FINDING_UNIT, 'cutoff': CUTOFF, 'uncertainty_alpha': ALPHA,
                'kind': 'accumulation' if task.endswith(':verified_source_leads')
                else 'remaining_commissioned_credit'} for task in sorted(YIELD_TASKS)},
            'outcome_page_size': OUTCOME_PAGE_SIZE,
            'populations': {family: True for family in OPTIONAL}}}}


def head_entry(scope, head):
    """The head's commission as the root fills it: its held scope and one value for each declared choice."""
    form = head.assignment_form
    assert set(form.declared) == {'evidence_task'} and set(form.choices) == {'thought_pattern', 'tools'}
    # The first offered thought pattern; every offered tool.
    assignment = axis_assignment(HEAD, head, {'scope': scope}, {
        'thought_pattern': form.choices['thought_pattern'][0], 'tools': list(form.choices['tools'])})
    form.admit(assignment, 'a105_head_assignment')
    # The head's entry request copies its own declared fields; the entry caller supplies the rest.
    return {name: value for name, value in assignment.items() if name not in form.declared}


def journal_rows(path, table, columns):
    with sqlite3.connect(path) as db:
        return [dict(zip(columns, row)) for row in db.execute(
            'SELECT ' + ','.join(columns) + ' FROM ' + table + ' WHERE run_id=? ORDER BY rowid', (RUN_ID,))]


def model_calls(directory):
    return sorted(path.name for path in Path(directory).glob('call-*'))


def run_summary(journal_path, head_path, record, result, calls):
    """What the run did, in numbers, from its journal (written beside the journal for the reader)."""
    episodes = journal_rows(journal_path, 'episodes', ('path', 'binding_path', 'state', 'completion'))
    decisions = journal_rows(journal_path, 'decisions', ('path', 'name', 'value'))
    units = journal_rows(journal_path, 'units', ('path', 'unit_index', 'label', 'controller_input'))
    summary = {'model_calls': len(calls), 'ended_by': record.ended_by, 'units': record.units_consumed,
               'credit': result['credit'], 'episodes': []}
    for episode in episodes:
        own = [row for row in decisions if row['path'] == episode['path']]
        model = [row['name'] for row in own if row['name'].startswith('decision.')]
        outcomes = [json.loads(row['value']) for row in own if row['name'].startswith('outcome.')]
        count = len([row for row in units if row['path'] == episode['path']])
        kinds = {}
        for outcome in outcomes:
            key = outcome['kind'] + ':' + outcome['status']
            kinds[key] = kinds.get(key, 0) + 1
        summary['episodes'].append({
            'path': json.loads(episode['path']), 'binding_path': episode['binding_path'], 'state': episode['state'],
            'completion': None if episode['completion'] is None else json.loads(episode['completion']),
            'head': episode['path'] == head_path, 'model_decisions': len(model),
            'rejected_responses': len(model) - len({name.split('.')[1] for name in model}),
            'units': count, 'outcomes': kinds})
    return summary


@pytest.mark.model_run
def test_head_run_calls_the_model_and_ends_by_its_own_continuation(tmp_path):
    journal_path = tmp_path / 'journal.sqlite'
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a105_home_factory], services(store, tmp_path))
        assert set(registry.paths) == set(ROLE_PATHS.values())
        head = registry.binding(HEAD)
        assert dict(head.child_slots) == {HEAD: HEAD, 'literature': ROLE_PATHS['literature']}
        target, = store.create_problem(raw_sequence=KNOWN_SEQUENCE.read_text().strip(),
                                       molecule='protein')['subject_refs']
        entry = head_entry(store.validate_scope({'subject_refs': [target]}), head)
        provider = ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)
        run = link(registry, HEAD, entry, run_id=RUN_ID, journal=RunJournal(journal_path),
                   collaborators={'store': store, 'model_provider': provider})
        outcome = asyncio.run(run.run())
        record, result = outcome['record'], outcome['result'].as_record()
        calls = model_calls(tmp_path / 'model_calls')
        head_path = json.dumps([[head.grain_name, RUN_ID]], separators=(',', ':'))
        summary = run_summary(journal_path, head_path, record, result, calls)
        (tmp_path / 'run_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')

        # The run ended by its own continuation, not by an exception or an exhausted source.
        assert record.ended_by == 'yield_stop'
        controller = record.controller_state
        assert isinstance(controller, YieldState) and controller.stop is True
        assert record.units_consumed >= 1

        # What the journal holds of the head Episode.
        decisions = {row['name']: json.loads(row['value'])
                     for row in journal_rows(journal_path, 'decisions', ('path', 'name', 'value'))
                     if row['path'] == head_path}
        units = [row for row in journal_rows(journal_path, 'units', ('path', 'unit_index', 'label',
                                                                    'controller_input'))
                 if row['path'] == head_path]
        # At least one model decision was recorded; every model call of the run is one recorded decision.
        model_decisions = [name for name in decisions if name.startswith('decision.')]
        assert model_decisions and all(set(decisions[name]) == {'selection'} for name in model_decisions)
        every_decision = [row for row in journal_rows(journal_path, 'decisions', ('path', 'name'))
                          if row['name'].startswith('decision.')]
        assert len(calls) == len(every_decision) >= len(model_decisions)
        # Each unit is one admitted decision; every further decision of a position was a rejected response.
        assert len(units) == record.units_consumed
        assert {name.split('.')[1] for name in model_decisions} == {str(index) for index in range(len(units))}
        # Each executed unit recorded its outcome (a failed one included) and the controller observed it.
        for index, unit in enumerate(units):
            observed = json.loads(unit['controller_input'])
            executed = decisions['outcome.' + str(index)]
            assert unit['unit_index'] == index
            assert observed['unit'] == {'position': index, 'kind': executed['kind'], 'status': executed['status']}
            assert executed['kind'] in ('reason', 'tool', 'child')
            assert type(observed['credit']) is float
            assert observed['estimation_context']['progress_time']['position'] == index
            assert observed['estimation_context']['progress_time']['status'] == 'available'
        assert len(controller.history) == len(units)
        assert controller.current_credit == json.loads(units[-1]['controller_input'])['credit']
        assert controller.initial_credit == decisions['a105.head.initial_credit']

        # The result is admitted by the head's return form: a numeric credit and a finding.
        admitted = head.return_form.admit(result, 'return:' + HEAD)
        assert type(admitted['credit']) in (int, float)
        assert admitted['credit'] == controller.current_credit - controller.initial_credit
        finding = admitted['finding']
        assert isinstance(finding, dict) and isinstance(finding['known_assessment_refs'], list)
        assert finding['ended_by'] == 'yield_stop' and finding['units'] == len(units)
        assert finding['scope'] == entry['scope']
        state, closed = RunJournal(journal_path).run_state(RUN_ID)
        assert state == 'closed' and closed == {'ended_by': 'yield_stop', 'units': len(units), 'result': admitted}
        episodes = journal_rows(journal_path, 'episodes', ('path', 'state'))
        assert {row['path']: row['state'] for row in episodes}[head_path] == 'closed'

    # Resuming the finished run from its journal, over the reopened Store and newly constructed bindings,
    # returns the identical result without a model call.
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a105_home_factory], services(store, tmp_path))
        resumed_provider = ModelProvider(load_config(), tmp_path / 'model_calls_resumed', tmp_path)
        resumed = resume(registry, run_id=RUN_ID, journal=RunJournal(journal_path),
                         collaborators={'store': store, 'model_provider': resumed_provider})
        again = asyncio.run(resumed.run())
        assert again['result'].as_record() == result
        assert again['record'].ended_by == 'yield_stop' and again['record'].units_consumed == len(units)
        assert model_calls(tmp_path / 'model_calls_resumed') == []
        assert model_calls(tmp_path / 'model_calls') == calls
        assert RunJournal(journal_path).run_state(RUN_ID) == ('closed', closed)
