"""A real run started at the A102 head (``structural_homology_evidence``), calling the model, to its own end.

Real pieces only: the A102 home factory (``contract_binding.a102_home_factory``) composed by
``BindingRegistry.compose`` over the run's one ``Store`` (the head and its 33 descendants, each with its
own tools), the repository's slotted process library and launch-instruction library frozen for the run,
a real ``RunJournal`` and the standard ``ModelProvider`` over the packaged ``[models]`` configuration (the
Codex app-server). The subject is the repository's known protein sequence
(``tests/fixtures/a108/known_sequence.txt``; only its raw residues enter the run, its provenance file is
read for the checksum alone).

The head's assignment is filled the way the root fills it (``root/decisions.axis_assignment``): the held
subject scope and proposed annotation, the head's own declared ``evidence_axis``, and the three choices
the head declares (``a102_task``, ``thought_pattern``, ``tools``). The proposed annotation is an open
hypothesis on the subject (its functional family, value unknown): it names no function. The run is
started with ``episode_runtime.link`` and awaited. Nothing limits it: it ends when the head's own
bounded-quality yield controller stops it. The test then reads what the run did from the journal and the
result, and resumes the finished run from its journal over a reopened store with a second model provider
that must receive no call.

Outside services other than the model are closed for this run by the command that starts it (the HTTP
proxy settings), so a tool that needs one returns its real failed outcome, which enters the iterator like
every other outcome. The HPC transport configured here is a real ``ssh`` client that cannot open a
connection (no configuration file, no master, a false proxy command): an HPC operation fails; none
reaches the cluster or asks for a login.
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

from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.configuration.structural_homology_evidence import (
    process_options)
from gene_annotation_episode.episodic_workflow.episode_support.forms.protein_structure.structural_evidence import TASKS
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.credit import (
    A102StructuralCredit)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LIBRARY_ROOT, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import (
    HEAD, PATHS, a102_home_factory, a102_progress_provider)
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.hpc_work_planning.hpc_runtime import (
    HPCServices)
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.runtime_continuation import (
    A102Continuation)
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.runtime_head import task_projector
from yield_control import BoundedQualityYieldController

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
SEQUENCE_PROVENANCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence_provenance.json'
RUN_ID = 'a102_head_model_run'
# The root's three choices for this commission, each among the options the head declares.
A102_TASK = 'structural_discovery'
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
# A real ssh client that cannot connect: it reads no configuration, reuses no master and its proxy
# command is false. Every HPC operation over it fails; none reaches the cluster or asks for a login.
CLOSED_SSH = ['/usr/bin/ssh', '-F', '/dev/null', '-T', '-o', 'BatchMode=yes', '-o', 'ControlMaster=no',
              '-o', 'ControlPath=none', '-o', 'ControlPersist=no', '-o', 'ProxyCommand=/bin/false',
              '-o', 'StrictHostKeyChecking=yes', '-o', 'NumberOfPasswordPrompts=0', 'chian@aurora.alcf.anl.gov']
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': CLOSED_SSH,
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
# Bindings that read their continuation settings from the ``continuation`` collaborator, keyed by path.
CONTINUATION_KINDS = ('execution_job_submission', 'resource_work_submission', 'hpc_job_execution',
                      'hpc_resource_work_execution', 'execution_result_acquisition')


def _controller_settings():
    """A102's packaged continuation settings (``[controller]``: the continuation cost and the alpha)."""
    table = tomllib.loads(Path(process_options.__file__).with_name('defaults.toml').read_text())['controller']
    return table['cost'], table['uncertainty_alpha']


def _services(tmp_path, store):
    """The A102 home factory's construction services over the run's shared Store."""
    cutoff, alpha = _controller_settings()
    library = process_options.StructuralHomologyEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    launch = LaunchInstructions.freeze(tmp_path / 'launch', source=LIBRARY_ROOT)
    for name in ('resource', 'coordinator'):
        (tmp_path / name).mkdir(exist_ok=True)
    completion = {'cutoff': cutoff, 'uncertainty_alpha': alpha}

    def local(state):
        return {'resource': {'kind': 'local', 'workspace': str(tmp_path / 'resource'),
                             'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
                'coordinator_workspace': tmp_path / 'coordinator', 'state_directory': tmp_path / state,
                'launch_instruction_directory': tmp_path / 'launch', 'continuation': completion}

    def hpc(directory):
        return {'resource': HPC_RESOURCE, 'directory': tmp_path / directory, 'launch_instructions': launch}
    api = {'resources': {'blast': {'service': 'ncbi_blast', 'kind': 'api'}}, 'continuation': completion}
    yield_bindings = {}
    for task in TASKS:
        projector = task_projector(library, task)
        yield_bindings['A102:' + task] = {'kind': projector.yield_method, 'cutoff': cutoff,
                                          'parameters': {'uncertainty_alpha': alpha},
                                          'credit_definition': projector.as_record()}
    return {'store': store, 'a102': {
        'library': library, 'tools': {}, 'yield_bindings': yield_bindings,
        'monitor': {'information_unit': 1.0, 'yield_settings': {
            'kind': 'information_accumulation', 'cutoff': cutoff, 'uncertainty_alpha': alpha}},
        'hpc_job_execution': hpc('hpc_job'), 'api_job_execution': api,
        'local_job_execution': local('local_practical'),
        'hpc_resource_work_execution': hpc('hpc_resource_work'), 'api_resource_work_execution': api,
        'local_resource_work_execution': local('resource_practical'),
        'resource_result_acquisition': local('result_practical'),
        'literature': {'kind': A102StructuralCredit.yield_method, 'cutoff': cutoff,
                       'parameters': {'uncertainty_alpha': alpha},
                       'credit_definition': A102StructuralCredit().as_record()}}}


def _collaborators(tmp_path, store, provider):
    cutoff, alpha = _controller_settings()
    return {'store': store, 'model_provider': provider,
            'continuation': {path: {'cutoff': cutoff, 'parameters': {'uncertainty_alpha': alpha}}
                             for path in PATHS if path.rsplit('/', 1)[-1] in CONTINUATION_KINDS},
            'a102_hpc': HPCServices(resources={'aurora': HPC_RESOURCE}, directory=tmp_path / 'hpc_services',
                                    shared_execution_memory=None),
            'a102_progress_provider': a102_progress_provider(store, run_id=RUN_ID)}


def _subject(store):
    """The run's subject on the shared Store: the known protein sequence, checked against its provenance."""
    sequence = SEQUENCE.read_text().strip()
    provenance = json.loads(SEQUENCE_PROVENANCE.read_text())
    assert hashlib.sha256(sequence.encode()).hexdigest() == provenance['sequence_sha256']
    assert len(sequence) == provenance['sequence_length']
    target, = store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs']
    return target, store.validate_scope({'subject_refs': [target]})


def _proposed_annotation(store, target, scope):
    """The proposed annotation the root holds for this subject: an open hypothesis that names no function."""
    commit = {name: [] for name in store.reasoning_schema()['properties']}
    commit['hypotheses'] = [{'alias': 'proposed', 'subject_refs': [target], 'predicate': 'functional_family',
                             'value': {'type': 'enum', 'value': 'unknown'}, 'context_refs': []}]
    committed = store.commit_reasoning(commit, scope, RUN_ID + ':proposed_annotation')
    assert committed['status'] == 'completed', committed
    return committed['aliases']['proposed']


def _assignment(head, scope, proposed):
    """The root's own filling of the head's declared assignment: held values, declared axis, three choices."""
    choices = {'a102_task': A102_TASK, 'thought_pattern': sorted(head.thought_patterns)[0],
               'tools': list(head.selectable_tools)}
    assignment = axis_assignment(HEAD, head, {'scope': scope, 'proposed_annotation_ref': proposed}, choices)
    assert assignment == head.assignment_form.admit(assignment, 'a102_model_run_assignment')
    assert assignment['evidence_axis'] == 'A102'
    return assignment


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
    by_episode = []
    for path, binding, state, completion, result in episodes:
        own = [(name, value) for where, name, value in decisions if where == path]
        outcomes = [value for name, value in own if name.startswith('outcome.')]
        responses = [name for name, _ in own if not name.startswith(('outcome.', 'episode_runtime.'))]
        attempts = {}
        for name in responses:
            parts = name.split('.')
            if len(parts) == 3 and parts[2].isdigit():
                attempts[parts[1]] = max(attempts.get(parts[1], 0), int(parts[2]))
        kinds, statuses, tools = {}, {}, {}
        for outcome in outcomes:
            if isinstance(outcome, dict):
                kinds[str(outcome.get('kind'))] = kinds.get(str(outcome.get('kind')), 0) + 1
                statuses[str(outcome.get('status'))] = statuses.get(str(outcome.get('status')), 0) + 1
        for name, value in own:
            selection = value.get('selection') if isinstance(value, dict) else None
            if name.startswith('decision.') and isinstance(selection, dict) and selection.get('kind') == 'tool':
                tools[str(selection.get('tool'))] = tools.get(str(selection.get('tool')), 0) + 1
        by_episode.append({
            'path': path, 'binding_path': binding, 'state': state, 'completion': completion,
            'credit': None if result is None else result.get('credit'),
            'recorded_model_responses': len(responses), 'rejected_model_responses': sum(attempts.values()),
            'units': sum(1 for where, *_ in units if where == path),
            'outcomes': len(outcomes), 'outcomes_by_kind': kinds, 'outcomes_by_status': statuses,
            'selected_tools_in_recorded_responses': tools})
    return {'run_id': RUN_ID, 'seconds': seconds, 'model_calls': len(calls), 'episodes': by_episode,
            'children': [{'path': path, 'binding_path': binding, 'state': state, 'completion': completion}
                         for path, binding, state, completion, _ in episodes[1:]]}


@pytest.mark.model_run
def test_head_run_calls_the_model_and_ends_by_its_own_continuation(tmp_path, monkeypatch):
    # The registries bind to this run's own local-resource directory, not the machine-wide one.
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))
    models = load_config()
    journal_path = tmp_path / 'journal.sqlite'

    started = time.monotonic()
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a102_home_factory], _services(tmp_path, store))
        assert sorted(registry.paths) == sorted(PATHS)
        head = registry.binding(HEAD)
        target, scope = _subject(store)
        proposed = _proposed_annotation(store, target, scope)
        assignment = _assignment(head, scope, proposed)
        entry = {name: assignment[name] for name in ('scope', 'a102_task', 'proposed_annotation_ref',
                                                    'thought_pattern', 'tools')}
        provider = ModelProvider(models, tmp_path / 'model_calls', tmp_path)
        journal = RunJournal(journal_path)
        run = link(registry, HEAD, entry, run_id=RUN_ID, journal=journal,
                   collaborators=_collaborators(tmp_path, store, provider))
        finished = asyncio.run(run.run())
        seconds = time.monotonic() - started
        record, result = finished['record'], finished['result'].as_record()
        calls = _calls(tmp_path / 'model_calls')
        summary = _summary(journal, calls, seconds)
        summary.update(ended_by=record.ended_by, units=record.units_consumed, credit=result['credit'],
                       controller=record.controller_state.as_record()['yield_state']['decision'])
        (tmp_path / 'run_summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')

        decisions, units, episodes = _journal_rows(journal)
        entry_path = episodes[0][0]
        assert episodes[0][1] == HEAD and entry_path == [[head.grain_name, RUN_ID]]
        own = {name: value for where, name, value in decisions if where == entry_path}
        # The admitted commission is the root-filled assignment.
        commission, = journal.db.execute('SELECT commission FROM episodes WHERE run_id=? AND binding_path=? '
                                         'ORDER BY rowid LIMIT 1', (RUN_ID, HEAD)).fetchone()
        assert json.loads(commission)['assignment'] == json.loads(json.dumps(assignment))

        # At least one model decision was made by the real model and recorded.
        model_decisions = [name for name in own if name.startswith('decision.')]
        assert model_decisions and calls
        assert len(calls) == sum(1 for _, name, _ in decisions if not name.startswith(('outcome.', 'episode_runtime.')))
        for call in calls:
            assert (tmp_path / 'model_calls' / call / 'response.json').is_file()
            assert not (tmp_path / 'model_calls' / call / 'error.json').exists()
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
        received = [proposed]
        for (index, label, value), unit, outcome in zip(own_units, record.unit_records, outcomes):
            assert unit.unit_label == label
            assert label.split(':')[0] == ('reason' if outcome['kind'] == 'reason' else
                                           'tool' if outcome['kind'] == 'tool' else label.split(':')[0])
            assert unit.controller_input.as_record() == value
            assert value['estimation_context']['progress_time']['status'] == 'available'
            assert value['estimation_context']['progress_time']['position'] == index
            received.extend(ref for ref in outcome['record_refs'] if ref not in received)
            assert value['received_record_refs'] == received
            assert unit.controller_step.credit == value['credit']
        controller_state = record.controller_state
        assert len(controller_state.yield_state.history) == record.units_consumed

        # The run ended by its own continuation.
        assert record.ended_by == 'yield_stop'
        assert controller_state.stop is True and controller_state.yield_state.decision.stop is True
        assert record.unit_records[-1].controller_step.stop is True
        assert all(not unit.controller_step.stop for unit in record.unit_records[:-1])
        opened = registry.binding(HEAD).build_controller(run.episode.source._bound, {'store': store})
        assert isinstance(opened, A102Continuation) and isinstance(opened.controller, BoundedQualityYieldController)
        state, closed = journal.run_state(RUN_ID)
        assert state == 'closed' and closed['ended_by'] == 'yield_stop' and closed['units'] == record.units_consumed
        assert all(row[2] == 'closed' for row in episodes)

        # The result is admitted by the head's return form, with a numeric credit and a finding.
        assert head.return_form.admit(result, 'a102_model_run_result') == result
        assert closed['result'] == result
        credit = result['credit']
        assert not isinstance(credit, bool) and isinstance(credit, (int, float)) and math.isfinite(credit)
        assert credit == controller_state.yield_state.current_credit
        finding = result['finding']
        assert isinstance(finding, dict) and finding['scope'] == scope and finding['a102_task'] == A102_TASK
        assert finding['proposed_annotation_ref'] == proposed and finding['record_refs'] == received
        assert finding['ended_by'] == 'yield_stop' and finding['units'] == record.units_consumed
        journal.db.close()

    # Resume the finished run from its journal over the reopened store: the same result, no model call.
    before = (decisions, units, episodes)
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([a102_home_factory], _services(tmp_path, store))
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
