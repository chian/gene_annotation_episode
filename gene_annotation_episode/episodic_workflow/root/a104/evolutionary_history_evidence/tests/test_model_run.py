"""A real run started at the A104 head (``evolutionary_history_evidence``), calling the model, to its own end.

Real pieces only: the A104 home factory composed by ``BindingRegistry.compose`` over the run's one
``Store``, the repository's slotted process library and launch-instruction library frozen for the run,
the head's own ``ToolRegistry``, a real ``RunJournal`` and the standard ``ModelProvider`` over the
packaged ``[models]`` configuration (the Codex app-server). The subject is the repository's known
protein sequence (``tests/fixtures/a108/known_sequence.txt``; only its raw residues enter the run).

The head's assignment is filled the way the root fills it (``root/decisions.axis_assignment``): the
held subject scope, the head's own declared ``evidence_task`` and the two choices the head declares
(``thought_pattern``, ``tools``). The run is started with ``episode_runtime.link`` and awaited. Nothing
limits it: it ends when its own continuation stops it. The test then reads what the run did from the
journal and the result, and resumes the finished run from its journal over a reopened store with a
second model provider that must receive no call.

Outside services other than the model are closed for this run by the command that starts it (the HTTP
proxy settings). The HPC transport configured here is a real ``ssh`` client that cannot open a
connection (no configuration file, no master, a false proxy command), so an HPC operation returns a
failed outcome rather than reaching the cluster or attempting a login.
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
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.process_options import (
    EvolutionaryHistoryEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.hpc_work_planning.hpc_runtime import (
    HPCServices)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_bindings import (
    EPISODES, a104_home, a104_progress_provider)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_source import (
    ROLE, head_credit_projector)

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
SEQUENCE_PROVENANCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence_provenance.json'
RUN_ID = 'a104_head_model_run'
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
# A real ssh client that cannot connect: it reads no configuration, reuses no master and its proxy
# command is false. Every HPC operation over it fails; none reaches the cluster or asks for a login.
CLOSED_SSH = ['/usr/bin/ssh', '-F', '/dev/null', '-T', '-o', 'BatchMode=yes', '-o', 'ControlMaster=no',
              '-o', 'ControlPath=none', '-o', 'ControlPersist=no', '-o', 'ProxyCommand=/bin/false',
              '-o', 'StrictHostKeyChecking=yes', '-o', 'NumberOfPasswordPrompts=0', 'chian@aurora.alcf.anl.gov']
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': CLOSED_SSH,
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
# The continuation settings of the head's link test (tests/test_runtime_head_link.py); the head's own are
# the packaged ``[controller]`` table.
LOCAL_CONTINUATION = {'cutoff': 0.25, 'uncertainty_alpha': 0.1}
CONTINUATION = {path: {'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.05}}
                for path, role, _ in EPISODES if role in ('launch', 'launch_hpc', 'results')}


def _services(tmp_path, store):
    controller = tomllib.loads(default_config_path().read_text())['controller']
    projector = head_credit_projector()
    library = EvolutionaryHistoryEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    launch = LaunchInstructions.freeze(tmp_path / 'launch', source=LIBRARY_ROOT / 'evolutionary_history_evidence')
    for name in ('resource', 'coordinator'):
        (tmp_path / name).mkdir(exist_ok=True)
    return {'store': store, 'a104': {
        'head': {'library': library, 'continuation': {
            'kind': projector.yield_method, 'cutoff': controller['cost'],
            'parameters': {'uncertainty_alpha': controller['uncertainty_alpha']},
            'credit_definition': projector.as_record()}},
        'tools': {}, 'monitor': {'information_unit': 1.0, 'yield_settings': {
            'kind': 'information_accumulation', 'cutoff': 0.25, 'uncertainty_alpha': 0.1}},
        'local_job_execution': {'resource': {'kind': 'local', 'workspace': str(tmp_path / 'resource'),
                                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                                'coordinator_workspace': tmp_path / 'coordinator',
                                'state_directory': tmp_path / 'practical',
                                'launch_instruction_directory': tmp_path / 'launch',
                                'continuation': LOCAL_CONTINUATION},
        'hpc_job_execution': {'resource': HPC_RESOURCE, 'directory': tmp_path / 'hpc', 'launch_instructions': launch},
        'api_job_execution': {'resources': {'blast': {'service': 'ncbi_blast', 'kind': 'api'}},
                              'continuation': LOCAL_CONTINUATION}}}


def _collaborators(tmp_path, store, provider):
    return {'store': store, 'model_provider': provider, 'a104_hpc': HPCServices(
        resources={'aurora': HPC_RESOURCE}, directory=tmp_path / 'hpc_services', shared_execution_memory=None),
        'continuation': CONTINUATION, 'a104_progress_provider': a104_progress_provider(store, run_id=RUN_ID)}


def _calls(directory):
    return sorted(path.name for path in Path(directory).glob('call-*'))


def _journal_rows(journal):
    """Everything the journal holds for the run, as decoded records."""
    decisions = [(json.loads(path), name, json.loads(value)) for path, name, value in journal.db.execute(
        'SELECT path, name, value FROM decisions WHERE run_id=? ORDER BY rowid', (RUN_ID,))]
    units = [(json.loads(path), index, label, json.loads(value)) for path, index, label, value in journal.db.execute(
        'SELECT path, unit_index, label, controller_input FROM units WHERE run_id=? ORDER BY rowid', (RUN_ID,))]
    episodes = [(json.loads(path), binding, state, None if completion is None else json.loads(completion),
                 None if result is None else json.loads(result))
                for path, binding, state, completion, result in journal.db.execute(
                    'SELECT path, binding_path, state, completion, result FROM episodes WHERE run_id=? ORDER BY rowid',
                    (RUN_ID,))]
    return decisions, units, episodes


def _summary(journal, calls, seconds):
    """The run in numbers, from the journal."""
    decisions, units, episodes = _journal_rows(journal)
    entry = episodes[0][0]
    by_episode = {}
    for path, binding, state, completion, result in episodes:
        own = [(name, value) for where, name, value in decisions if where == path]
        outcomes = [value for name, value in own if name.startswith('outcome.')]
        responses = [name for name, _ in own if not name.startswith(('outcome.', 'episode_runtime.'))]
        kinds, statuses = {}, {}
        for outcome in outcomes:
            if isinstance(outcome, dict):
                kinds[str(outcome.get('kind'))] = kinds.get(str(outcome.get('kind')), 0) + 1
                statuses[str(outcome.get('status'))] = statuses.get(str(outcome.get('status')), 0) + 1
        by_episode[json.dumps(path)] = {
            'binding_path': binding, 'state': state, 'completion': completion,
            'credit': None if result is None else result.get('credit'),
            'recorded_model_responses': len(responses),
            'units': sum(1 for where, *_ in units if where == path),
            'outcomes': len(outcomes), 'outcomes_by_kind': kinds, 'outcomes_by_status': statuses}
    return {'run_id': RUN_ID, 'seconds': seconds, 'model_calls': len(calls), 'entry': entry,
            'episodes': by_episode,
            'children': [{'path': path, 'binding_path': binding, 'state': state, 'completion': completion}
                         for path, binding, state, completion, _ in episodes[1:]]}


@pytest.mark.model_run
def test_head_run_calls_the_model_and_ends_by_its_own_continuation(tmp_path, monkeypatch):
    # The registries bind to this run's own local-resource directory, not the machine-wide one.
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))
    sequence = SEQUENCE.read_text().strip()
    provenance = json.loads(SEQUENCE_PROVENANCE.read_text())
    assert hashlib.sha256(sequence.encode()).hexdigest() == provenance['sequence_sha256']
    assert len(sequence) == provenance['sequence_length']
    models = load_config()
    journal_path = tmp_path / 'journal.sqlite'

    started = time.monotonic()
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a104_home], _services(tmp_path, store))
        head = registry.binding(ROLE)
        target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
        scope = store.validate_scope({'subject_refs': [target]})
        # The root's own filling of this head's declared assignment: the held scope, the declared
        # evidence task, and the head's two choices (here every tool the head offers).
        choices = {'thought_pattern': sorted(head.thought_patterns)[0], 'tools': list(head.selectable_tools)}
        assignment = axis_assignment(ROLE, head, {'scope': scope}, choices)
        assert assignment == head.assignment_form.admit(assignment, 'a104_model_run_assignment')
        assert assignment['evidence_task'] == head.goal
        entry = {name: assignment[name] for name in ('scope', 'thought_pattern', 'tools')}
        provider = ModelProvider(models, tmp_path / 'model_calls', tmp_path)
        journal = RunJournal(journal_path)
        run = link(registry, ROLE, entry, run_id=RUN_ID, journal=journal,
                   collaborators=_collaborators(tmp_path, store, provider))
        finished = asyncio.run(run.run())
        seconds = time.monotonic() - started
        record, result = finished['record'], finished['result'].as_record()
        calls = _calls(tmp_path / 'model_calls')
        summary = _summary(journal, calls, seconds)
        summary.update(ended_by=record.ended_by, units=record.units_consumed, credit=result['credit'],
                       controller=record.controller_state.as_record()['decision'])
        (tmp_path / 'run_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')

        decisions, units, episodes = _journal_rows(journal)
        entry_path = episodes[0][0]
        assert episodes[0][1] == ROLE
        own = {name: value for where, name, value in decisions if where == entry_path}
        # The admitted commission is the root-filled assignment.
        commission, = journal.db.execute('SELECT commission FROM episodes WHERE run_id=? AND binding_path=? '
                                         'ORDER BY rowid LIMIT 1', (RUN_ID, ROLE)).fetchone()
        assert json.loads(commission)['assignment'] == json.loads(json.dumps(assignment))

        # At least one model decision was made by the real model and recorded.
        model_decisions = [name for name in own if name.startswith('decision.')]
        assert model_decisions and calls
        assert (tmp_path / 'model_calls' / calls[0] / 'response.json').is_file()

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

        # The run ended by its own continuation.
        assert record.ended_by == 'yield_stop'
        assert record.controller_state.stop is True
        assert record.unit_records[-1].controller_step.stop is True
        assert all(not unit.controller_step.stop for unit in record.unit_records[:-1])
        state, closed = journal.run_state(RUN_ID)
        assert state == 'closed' and closed['ended_by'] == 'yield_stop' and closed['units'] == record.units_consumed
        assert all(row[2] == 'closed' for row in episodes)

        # The result is admitted by the head's return form, with a numeric credit and a finding.
        assert head.return_form.admit(result, 'a104_model_run_result') == result
        assert closed['result'] == result
        credit = result['credit']
        assert not isinstance(credit, bool) and isinstance(credit, (int, float)) and math.isfinite(credit)
        assert credit == record.controller_state.current_credit
        finding = result['finding']
        assert isinstance(finding, dict) and finding['scope'] == scope and target in finding['evidence_refs']
        assert finding['ended_by'] == 'yield_stop' and finding['units'] == record.units_consumed
        journal.db.close()

    # Resume the finished run from its journal over the reopened store: the same result, no model call.
    before = (decisions, units, episodes)
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a104_home], _services(tmp_path, store))
        second_provider = ModelProvider(models, tmp_path / 'model_calls_resume', tmp_path)
        journal = RunJournal(journal_path)
        resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                     collaborators=_collaborators(tmp_path, store, second_provider)).run())
        assert resumed['result'].as_record() == result
        assert resumed['record'].ended_by == record.ended_by
        assert resumed['record'].units_consumed == record.units_consumed
        assert journal.run_state(RUN_ID) == ('closed', closed)
        assert _journal_rows(journal) == before
        assert _calls(tmp_path / 'model_calls_resume') == []
        assert _calls(tmp_path / 'model_calls') == calls
        journal.db.close()
