"""A real run at the A110 head (``biochemical_feasibility_evidence``) that calls the model, then its resume.

Real pieces only: the A110 home factory's bindings composed over one shared Store, each binding's own tool
registry, the runner's journal and linker, and the run's one ``ModelProvider`` over the Codex app-server
(``[models]`` of the packaged ``defaults.toml``). The subject is the repository's known protein sequence
(``tests/fixtures/a108/known_sequence.txt``; only its raw residues enter the Store). The head's assignment is
filled the way the root fills it (``root/decisions.axis_assignment``): the held subject scope, the head's
declared evidence task, and its ``tools`` subset chosen from the operations the head declares.

The run ends only by the head's own continuation. Outside services other than the model are blocked by the
command's proxy settings, and the HPC resource names a host that cannot resolve, so a tool or child that needs
them returns its own failed outcome, which enters the iterator like any other.

Run with ``-m model_run`` through ``tools/one_workflow.sh`` (see the task's command form); the default
selection deselects it.
"""
import asyncio
import json
import math
from pathlib import Path

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import (
    LIBRARY_ROOT, LaunchInstructions)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.home import (
    a110_progress_provider, home_factory)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.hpc_work_planning.hpc_runtime import (
    HPCServices)
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment
from gene_annotation_episode.episodic_workflow.root.goal import axis_objective
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

pytestmark = pytest.mark.model_run

HEAD = 'biochemical_feasibility_evidence'
RUN_ID = 'a110-head-model-run'
SEQUENCE = Path(__file__).resolve().parents[6] / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
# The head's continuation settings as its link tests declare them (test_head_runtime), for every A110 binding.
CONTINUATION = {'cutoff': 0.25, 'parameters': {'uncertainty_alpha': 0.05}}
MONITOR = {'information_unit': 1.0, 'yield_settings': {'kind': 'information_accumulation', 'cutoff': 0.25,
                                                       'uncertainty_alpha': 0.1}}
# The configured pbs_ssh resource. Its transport reads no user configuration and names a host that cannot
# resolve (RFC 2606 ``.invalid``): HPC is an outside service and stays blocked like the proxied ones.
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': '/lus/flare/projects/BioReason-Aurora-Test/chian/runs',
                'ssh_argv': ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'ControlPath=none',
                             'aurora.invalid'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}


def frozen_launch_instructions(directory):
    """The frozen launch instruction library in ``directory``; frozen once, reopened afterwards."""
    if directory.exists():
        return LaunchInstructions(directory)
    return LaunchInstructions.freeze(directory, source=LIBRARY_ROOT)


def compose(store, root):
    """The A110 registry from its real home factory over the shared Store, with its construction services."""
    for name in ('resource', 'coordinator'):
        (root / 'local_jobs' / name).mkdir(parents=True, exist_ok=True)
    frozen_launch_instructions(root / 'local_jobs' / 'launch')
    return BindingRegistry.compose([home_factory], {
        'store': store,
        'a110': {'tool_registry': {}},
        'a110_local_job_execution': {
            'resource': {'kind': 'local', 'workspace': str(root / 'local_jobs' / 'resource'),
                         'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
            'coordinator_workspace': root / 'local_jobs' / 'coordinator',
            'state_directory': root / 'local_jobs' / 'practical',
            'launch_instruction_directory': root / 'local_jobs' / 'launch'},
        'a110_hpc_job_execution': {
            'resource': HPC_RESOURCE, 'directory': root / 'hpc_jobs' / 'hpc',
            'launch_instructions': frozen_launch_instructions(root / 'hpc_jobs' / 'hpc_launch')},
        'a110_progress_monitor': MONITOR})


def runtime_collaborators(registry, store, provider, root):
    """Every runtime collaborator the A110 subtree declares: the standard three and A110's own two."""
    return {'store': store, 'model_provider': provider,
            'continuation': {path: CONTINUATION for path in registry.subtree(HEAD)},
            'a110_hpc': HPCServices(resources={'aurora': HPC_RESOURCE}, directory=root / 'hpc_planning',
                                    shared_execution_memory=None),
            'a110_progress_provider': a110_progress_provider(store, run_id=RUN_ID)}


def head_entry_input(registry, scope):
    """The head's commission as the root fills it: held scope, declared evidence task, chosen tools subset."""
    head = registry.binding(HEAD)
    offered = list(head.assignment_form.fields['tools'].options)
    assignment = axis_assignment(HEAD, head, {'scope': scope, 'evidence_refs': []}, {'tools': offered})
    return {'objective': axis_objective(HEAD), 'assignment': assignment}


def decisions(journal, run_id):
    """Every recorded decision of the run as ``(episode path, name, value)``, in recording order."""
    return [(json.loads(path), name, json.loads(value)) for path, name, value in journal.db.execute(
        'SELECT path, name, value FROM decisions WHERE run_id=? ORDER BY rowid', (run_id,))]


def test_head_run_calls_the_model_and_ends_by_its_own_continuation_then_resumes_identically(tmp_path):
    root = tmp_path / 'services'
    model_cwd = tmp_path / 'model_cwd'
    model_cwd.mkdir()
    sequence = SEQUENCE.read_text().strip()
    head_path = [[HEAD, RUN_ID]]

    # -- the run -------------------------------------------------------------------------------------------------
    with Store(tmp_path / 'workspace') as store:
        subject_refs = list(store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs'])
        scope = store.validate_scope({'subject_refs': subject_refs})
        registry = compose(store, root)
        head = registry.binding(HEAD)
        entry_input = head_entry_input(registry, scope)
        assert entry_input['assignment']['evidence_task'] == head.assignment_form.declared['evidence_task']
        provider = ModelProvider(load_config(), tmp_path / 'model_calls', model_cwd)
        journal = RunJournal(tmp_path / 'journal.sqlite3')
        run = link(registry, HEAD, entry_input, run_id=RUN_ID, journal=journal,
                   collaborators=runtime_collaborators(registry, store, provider, root))
        outcome = asyncio.run(run.run())
        record, result = outcome['record'], outcome['result'].as_record()

        # The run ended by the head's own continuation, with the journal closed on that end.
        assert record.ended_by == 'yield_stop'
        assert record.controller_state.stop is True
        state, closed = journal.run_state(RUN_ID)
        assert state == 'closed'
        assert closed == {'ended_by': 'yield_stop', 'units': record.units_consumed, 'result': result}

        # At least one model decision was recorded, each by a real provider call.
        recorded = decisions(journal, RUN_ID)
        own = {name: value for path, name, value in recorded if path == head_path}
        model_decisions = sorted(name for name in own if name.startswith('a110.decision.'))
        assert model_decisions
        calls = sorted(path.name for path in (tmp_path / 'model_calls').glob('call-*'))
        assert calls and all((tmp_path / 'model_calls' / call / 'response.json').is_file() for call in calls)
        all_model_decisions = [name for _, name, _ in recorded if '.decision.' in name or name.startswith('decision.')]
        assert len(calls) >= len(model_decisions)
        assert len(calls) == len(all_model_decisions)

        # At least one unit executed; every unit's outcome is recorded and the controller observed it.
        units = journal.units(RUN_ID, head_path)
        assert record.units_consumed == len(units) >= 1
        assert len(record.controller_state.history) == len(units)
        for position, (label, controller_input) in enumerate(units):
            entry = own['a110.unit.' + str(position)]
            assert entry['position'] == position and entry['history']['label'] == label
            assert entry['history']['status'] and entry['outcome'] is not None
            if entry['history']['kind'] in ('tool', 'reason'):
                assert own['a110.outcome.' + str(position)] == entry['outcome']
            assert controller_input['credit'] == entry['credit']
            assert controller_input['status'] == entry['history']['status']
            receipt = controller_input['estimation_context']['progress_time']
            assert receipt['position'] == position and receipt['status'] == 'available'
        assert record.controller_state.current_credit == units[-1][1]['credit']

        # The result is admitted by the head's return form, with a numeric credit and a finding.
        assert head.return_form.admit(result, 'a110_head_result') == result
        assert type(result['credit']) in (int, float) and math.isfinite(result['credit'])
        assert result['credit'] == record.controller_state.current_credit
        assert isinstance(result['finding'], str) and result['finding'].strip()
        for ref in result['assessment_refs']:
            assert store.get(ref)['record_type'] == 'assessment'
        episodes = journal.episodes(RUN_ID)
        assert episodes[0] == {'path': head_path, 'binding_path': HEAD, 'state': 'closed'}
        journal.db.close()

    # -- its resume from the journal -------------------------------------------------------------------------------
    with Store(tmp_path / 'workspace') as store:
        registry = compose(store, root)
        resumed_provider = ModelProvider(load_config(), tmp_path / 'model_calls_resumed', model_cwd)
        journal = RunJournal(tmp_path / 'journal.sqlite3')
        resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal, collaborators=runtime_collaborators(
            registry, store, resumed_provider, root)).run())
        assert resumed['result'].as_record() == result
        assert resumed['record'].ended_by == 'yield_stop'
        assert resumed['record'].units_consumed == record.units_consumed
        assert resumed['record'].controller_state.as_record() == record.controller_state.as_record()
        # No new model call: the resumed provider was never asked, and nothing new was recorded.
        assert not list((tmp_path / 'model_calls_resumed').glob('call-*'))
        assert decisions(journal, RUN_ID) == recorded
        assert journal.episodes(RUN_ID) == episodes
        assert journal.run_state(RUN_ID) == ('closed', closed)
        journal.db.close()
