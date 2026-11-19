"""A real run of the A101 head (``sequence_homology_evidence``) on the generic runner, calling the model.

Real pieces only: the A101 home factory composed by ``BindingRegistry.compose`` over the run's one
shared ``Store`` (the composition of ``test_runtime_head_link``), every binding's own tool registry,
a real ``RunJournal`` and the standard ``ModelProvider`` over the packaged ``[models]`` configuration
calling the real model. The subject is the repository's known protein sequence
(``tests/fixtures/a108/known_sequence.txt``); only its raw sequence enters the Store. The head's
assignment is filled the way the root fills it (``root.decisions.axis_assignment``: the held scope,
the head's own declared evidence task and the commissioner's choice of thought pattern and tools).

The run is linked at the head, runs until its own continuation ends it, and is then resumed from its
journal. Nothing here decides, limits or shortens the run: the continuation settings are the packaged
``[controller]`` values. Outside services other than the model are blocked by the caller's proxy
settings, so tools that need them return failed outcomes, which enter the iterator like any other.

Selected only with ``-m model_run`` (see ``pyproject.toml``); it needs the owner's Codex sign-in.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import tomllib

import pytest

from episode_runtime import EpisodeRecorder, RunJournal, link, resume
from episode_runtime.journal import canonical
from method_loop import END_YIELD_STOP

from gene_annotation_episode.model_provider import ModelProvider, default_config_path, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.home_factory import (
    a101_progress_provider)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.native_correspondence_credit import (
    A101SequenceCredit)
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.yield_estimator import HEAD_TASK

from .test_runtime_head_link import CONTINUATION, HEAD, REPOSITORY, YIELD_BINDINGS, _registry

RUN_ID = 'a101_head_model_run'
SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
PROVENANCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence_provenance.json'
# The commissioner's choices among the head's declared options (root: one thought pattern, a subset of tools).
THOUGHT_PATTERN = 'P01'  # "Choose a relevant analogue and bound what transfers"
TOOLS = ('public.blast.collect', 'public.blast.search', 'public.search.jobs', 'public.uniprot.record',
         'public.uniprot.search', 'result.blast.hsp', 'sequence.align', 'sequence.inspect', 'state.query')


def _known_sequence():
    """The repository's known protein sequence; its provenance is checked here and never enters the run."""
    sequence = SEQUENCE.read_text().strip()
    provenance = json.loads(PROVENANCE.read_text())
    assert len(sequence) == provenance['sequence_length']
    assert hashlib.sha256(sequence.encode()).hexdigest() == provenance['sequence_sha256']
    return sequence


def _collaborators(store, provider):
    return {'store': store, 'model_provider': provider, 'continuation': CONTINUATION,
            'a101_progress_provider': a101_progress_provider(store, run_id=RUN_ID)}


def _calls(directory):
    return sorted(path for path in Path(directory).glob('call-*'))


def _decisions(journal, path):
    """Every recorded decision of one Episode, by name."""
    return {name: json.loads(value) for name, value in journal.db.execute(
        'SELECT name, value FROM decisions WHERE run_id=? AND path=?',
        (RUN_ID, canonical([list(part) for part in path])))}


def _admitted(recorded, position):
    """The model response admitted as unit ``position``: its last recorded attempt."""
    prefix = 'decision.' + str(position) + '.'
    attempts = [int(name[len(prefix):]) for name in recorded if name.startswith(prefix)]
    return recorded[prefix + str(max(attempts))]


def _summary(journal, path, record, value, recorded, calls):
    """The run in numbers, read from the journal (retained beside the run's other output)."""
    recorder = EpisodeRecorder(journal, RUN_ID, path)
    units = journal.units(RUN_ID, path)
    outcomes = [recorder.recall('outcome.' + str(position)) for position in range(len(units))]
    decisions = [name for name in recorded if name.startswith('decision.')]
    return {
        'run_id': RUN_ID, 'ended_by': record.ended_by, 'units': len(units), 'credit': value['credit'],
        'model_calls': len(calls), 'head_decisions': len(decisions),
        'head_rejected_responses': len(decisions) - len(units),
        'units_by_kind': {kind: sum(item['kind'] == kind for item in outcomes)
                          for kind in sorted({item['kind'] for item in outcomes})},
        'outcomes_by_status': {status: sum(item['status'] == status for item in outcomes)
                               for status in sorted({item['status'] for item in outcomes})},
        'unit_outcomes': [{'label': label, 'kind': item['kind'], 'status': item['status'],
                           'tool': _admitted(recorded, position)['selection'].get('tool'),
                           'slot': _admitted(recorded, position)['selection'].get('slot'),
                           'credit': observed['credit'],
                           'elapsed_seconds': observed['estimation_context']['progress_time']['elapsed_seconds']}
                          for position, ((label, observed), item) in enumerate(zip(units, outcomes))],
        'episodes': [{'binding_path': item['binding_path'], 'state': item['state'],
                      'units': len(journal.units(RUN_ID, [tuple(part) for part in item['path']]))}
                     for item in journal.episodes(RUN_ID)],
        'finding': value['finding']}


@pytest.mark.model_run
def test_head_run_calls_the_model_and_ends_by_its_own_continuation(tmp_path):
    controller = tomllib.loads(default_config_path().read_text())['controller']
    # The head's continuation declaration is the packaged [controller] setting.
    assert YIELD_BINDINGS == {HEAD_TASK: {
        'kind': 'bounded_quality', 'cutoff': controller['cost'],
        'parameters': {'uncertainty_alpha': controller['uncertainty_alpha']},
        'credit_definition': A101SequenceCredit().as_record()}}
    journal_path = tmp_path / 'journal.sqlite'
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        head = registry.binding(HEAD)
        target, = store.create_problem(raw_sequence=_known_sequence(), molecule='protein')['subject_refs']
        scope = store.validate_scope({'subject_refs': [target]})
        # The assignment as the root fills it: held scope, the head's declared evidence task, chosen options.
        assignment = axis_assignment(HEAD, head, {'scope': scope, 'evidence_refs': []},
                                     {'thought_pattern': THOUGHT_PATTERN, 'tools': list(TOOLS)})
        assert head.assignment_form.admit(assignment, 'assignment') == assignment
        entry = {name: assignment[name] for name in head.entry_fields()}
        provider = ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)
        journal = RunJournal(journal_path)
        run = link(registry, HEAD, entry, run_id=RUN_ID, journal=journal,
                   collaborators=_collaborators(store, provider))
        path = ((head.grain_name, RUN_ID),)

        outcome = asyncio.run(run.run())

        record, value = outcome['record'], outcome['result'].as_record()
        units = journal.units(RUN_ID, path)
        recorded = _decisions(journal, path)
        recorder = EpisodeRecorder(journal, RUN_ID, path)
        decisions = sorted(name for name in recorded if name.startswith('decision.'))
        outcomes = [recorder.recall('outcome.' + str(position)) for position in range(len(units))]
        calls = _calls(tmp_path / 'model_calls')
        (tmp_path / 'run_summary.json').write_text(
            json.dumps(_summary(journal, path, record, value, recorded, calls), indent=2) + '\n')

        # The model decided: every unit position has a recorded decision, each from one real model call.
        assert decisions and {int(name.split('.')[1]) for name in decisions} == set(range(len(units)))
        assert len(calls) >= len(decisions)
        assert all((call / 'response.json').is_file() and not (call / 'error.json').exists() for call in calls)

        # Units executed, their outcomes were recorded, and the controller observed each of them.
        assert len(units) >= 1 and record.units_consumed == len(units) == len(record.unit_records)
        for position, ((label, observed), unit_outcome, unit_record) in enumerate(zip(units, outcomes,
                                                                                    record.unit_records)):
            assert observed['unit'] == {'position': position, 'kind': unit_outcome['kind'],
                                        'status': unit_outcome['status']}
            assert type(observed['credit']) in (int, float)
            assert observed['estimation_context']['progress_time']['status'] == 'available'
            assert unit_record.unit_label == label and unit_record.controller_step.credit == observed['credit']
        state = record.controller_state
        assert len(state.history) == len(units) and state.current_credit == units[-1][1]['credit']

        # The run ended by its own continuation, and the journal holds it closed.
        assert record.ended_by == END_YIELD_STOP and state.stop is True
        assert journal.run_state(RUN_ID) == ('closed', {'ended_by': END_YIELD_STOP, 'units': len(units),
                                                       'result': value})
        episodes = journal.episodes(RUN_ID)
        assert episodes[0]['binding_path'] == HEAD and all(item['state'] == 'closed' for item in episodes)

        # The result is admitted by the head's return form: a numeric credit and a finding.
        assert head.return_form.admit(value, 'return') == value
        assert type(value['credit']) in (int, float) and value['credit'] == state.current_credit
        finding = value['finding']
        assert finding['evidence_axis'] == 'A101' and finding['scope'] == scope
        assert finding['ended_by'] == END_YIELD_STOP and finding['units'] == len(units)

        # Resumed from its journal, the finished run replays: the same result and no new model call.
        resumed_provider = ModelProvider(load_config(), tmp_path / 'model_calls_resumed', tmp_path)
        resumed_journal = RunJournal(journal_path)
        resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=resumed_journal,
                                     collaborators=_collaborators(store, resumed_provider)).run())
        assert resumed['result'].as_record() == value
        assert resumed['record'].ended_by == END_YIELD_STOP and resumed['record'].units_consumed == len(units)
        assert _calls(tmp_path / 'model_calls_resumed') == [] and _calls(tmp_path / 'model_calls') == calls
        assert resumed_journal.units(RUN_ID, path) == units and _decisions(resumed_journal, path) == recorded
        assert resumed_journal.run_state(RUN_ID) == ('closed', {'ended_by': END_YIELD_STOP, 'units': len(units),
                                                               'result': value})
