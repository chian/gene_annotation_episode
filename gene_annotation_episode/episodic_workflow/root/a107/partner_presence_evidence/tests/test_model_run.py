"""A real run at the A107 head (``partner_presence_evidence``), calling the model, to its own end.

Real pieces only: the A107 home factory builds the head and its 28 descendants over the run's one
shared ``Store``, each with its own tool registry; the frozen A107 scientific library and launch
instruction library; a real ``RunJournal``; the one ``ModelProvider`` over the packaged ``[models]``
configuration, calling the real model. The subject is the repository's known protein sequence
(``tests/fixtures/a108/known_sequence.txt``; UniProt Q04507 per its provenance file, which is not
shown to the episode). The head's assignment is filled the way the root fills it: the scope the root
holds, the head's declared evidence axis, one offered thought pattern and a subset of the offered tools.

Nothing limits the run: it ends when the head's own accumulation yield controller stops it. Services
other than the model are unreachable under the model-run command (proxy settings; the HPC transport
is the ``false`` command of the head's other tests), so a tool that needs one returns its real failed
outcome, which enters the iterator like every other outcome.
"""
import asyncio
import json
from pathlib import Path
import sqlite3

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from episode_runtime.journal import canonical

from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.partner_presence_evidence.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.episode_support.configuration.partner_presence_evidence.process_options import (
    PartnerPresenceEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.episode import (
    DESCENDANT_PATHS, LITERATURE_PATH, ROLE, a107_progress_provider, home_factory)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.hpc_work_planning.hpc_runtime import (
    HPCServices)

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
KNOWN_SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
RUN_ID = 'a107_head_model_run'
OBJECTIVE = ('Establish, with retained source-grounded evidence, which partner components the possible function '
             'of the submitted protein requires and whether they are present and expressed in the relevant '
             'genome, organism and conditions')
# The library thought pattern this commission investigates with:
# P08, "Test the missing prerequisite behind conditional function".
THOUGHT_PATTERN = 'P08'
# The continuation and credit settings of the head's literature link test (the same finding-progress
# credit): the controller's cost in finding units, its uncertainty level, and one unit per retained finding.
CUTOFF, ALPHA, FINDING_UNIT = 0.5, 0.05, 1
# The PBS resource of the head's other tests: its transport is the ``false`` command, so no HPC is reached.
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': '/lus/flare/projects/contract-fixture', 'account': 'fixture',
                'python_executable': '/not-an-executable-contract-fixture', 'ssh_argv': ['false'],
                'scheduler': {'kind': 'pbs'}}


@pytest.fixture(autouse=True)
def _own_local_resources(tmp_path, monkeypatch):
    """The run binds its registries to its own local-resource directory, not the machine-wide one."""
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))


def tool_settings(root):
    """Every required A107 tool registry setting, declared explicitly (no native executables configured)."""
    return {'a107_work_directory': root / 'a107_work', 'a107_detection_bindings': [], 'clients': PublicClients(),
            'cmsearch_executable': None, 'minimap2_executable': None, 'minimap2_cache_dir': root / 'minimap2-cache',
            'pdfinfo_executable': None, 'pdftotext_executable': None, 'pdftoppm_executable': None}


def services(store, root):
    """The A107 home factory's construction services over the run's shared Store."""
    library = PartnerPresenceEvidenceLibrary.freeze(root / 'library', source=LIBRARY_SOURCE)
    launch = LaunchInstructions.freeze(root / 'launch', source=LIBRARY_ROOT / ROLE)
    for name in ('resource', 'coordinator'):
        (root / name).mkdir(parents=True, exist_ok=True)
    tools = tool_settings(root)
    monitor_tools = {name: value for name, value in tools.items() if not name.startswith('a107_')}
    return {
        'store': store,
        ROLE: {'library': library, 'tools': tools},
        'a107_local_job_execution': {
            'resource': {'kind': 'local', 'workspace': str(root / 'resource'),
                         'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
            'coordinator_workspace': root / 'coordinator', 'state_directory': root / 'practical',
            'launch_instruction_directory': root / 'launch'},
        'a107_hpc_job_execution': {'resource': HPC_RESOURCE, 'directory': root / 'hpc_job',
                                   'launch_instructions': launch},
        'a107_progress_monitor': {'information_unit': 1.0, 'tools': monitor_tools,
                                  'yield_settings': {'kind': 'information_accumulation', 'cutoff': CUTOFF,
                                                     'uncertainty_alpha': ALPHA}},
        'a107_api_job_execution': {'resources': {'blast': {'kind': 'api', 'service': 'ncbi_blast'}}},
    }


def continuation_settings():
    """The ``continuation`` collaborator: each A107 binding's settings, keyed by its binding path."""
    parameters = {'uncertainty_alpha': ALPHA}
    finding_progress = {'cutoff': CUTOFF, 'parameters': parameters, 'finding_unit': FINDING_UNIT}
    settings = {path: (finding_progress if path.startswith(LITERATURE_PATH)
                       else {'cutoff': CUTOFF, 'parameters': parameters}) for path in DESCENDANT_PATHS}
    return {**settings, ROLE: finding_progress}


def collaborators(store, root, provider):
    return {'store': store, 'model_provider': provider, 'continuation': continuation_settings(),
            'a107_progress_provider': a107_progress_provider(store, run_id=RUN_ID),
            'a107_hpc': HPCServices(resources={'aurora': HPC_RESOURCE}, directory=root / 'hpc',
                                    shared_execution_memory=None)}


def head_entry(store, head):
    """The head's commission as the root fills it: its held scope and one value for each declared choice."""
    target, = store.create_problem(raw_sequence=KNOWN_SEQUENCE.read_text().strip(), molecule='protein')['subject_refs']
    form = head.assignment_form
    assert form.declared == {'evidence_axis': 'A107'} and set(form.choices) == {'thought_pattern', 'tools'}
    assert THOUGHT_PATTERN in form.choices['thought_pattern']
    # The subset of tools: every tool the head offers.
    return {'objective': OBJECTIVE, 'scope': store.validate_scope({'subject_refs': [target]}),
            'thought_pattern': THOUGHT_PATTERN, 'tools': list(form.choices['tools'])}


def recorded(journal_path, table, columns, episode_path):
    """The journal's rows of one Episode of this run, in recording order."""
    with sqlite3.connect(journal_path) as db:
        return [dict(zip(columns, row)) for row in db.execute(
            'SELECT ' + ','.join(columns) + ' FROM ' + table + ' WHERE run_id=? AND path=? ORDER BY rowid',
            (RUN_ID, episode_path))]


def model_calls(directory):
    return sorted(path.name for path in Path(directory).glob('call-*'))


@pytest.mark.model_run
def test_head_run_calls_the_model_and_ends_by_its_own_continuation(tmp_path):
    journal_path = tmp_path / 'journal.sqlite'
    with Store(tmp_path / 'state') as store:
        registry = BindingRegistry.compose([home_factory], services(store, tmp_path))
        assert set(registry.paths) == {ROLE, *DESCENDANT_PATHS}
        head = registry.binding(ROLE)
        entry = head_entry(store, head)
        provider = ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)
        run = link(registry, ROLE, entry, run_id=RUN_ID, journal=RunJournal(journal_path),
                   collaborators=collaborators(store, tmp_path, provider))
        outcome = asyncio.run(run.run())
        record, result = outcome['record'], outcome['result'].as_record()

        # The run ended by its own continuation: the head's controller stopped it after at least one unit.
        assert record.ended_by == 'yield_stop' and record.controller_state.stop is True
        assert record.units_consumed >= 1

        # What the journal holds of the head Episode.
        head_path = canonical([[head.grain_name, RUN_ID]])
        decisions = {row['name']: json.loads(row['value'])
                     for row in recorded(journal_path, 'decisions', ('name', 'value'), head_path)}
        units = [{'index': row['unit_index'], 'label': row['label'], **json.loads(row['controller_input'])}
                 for row in recorded(journal_path, 'units', ('unit_index', 'label', 'controller_input'), head_path)]
        assert [unit['index'] for unit in units] == list(range(record.units_consumed))

        # Model decisions: every recorded response came from one real model call; each unit is the admitted
        # decision of its position (any earlier attempt of that position was a rejected response: no unit).
        model_decisions = sorted(name for name in decisions if name.startswith('a107_decision_'))
        assert model_decisions and all('selection' in decisions[name] for name in model_decisions)
        calls = model_calls(tmp_path / 'model_calls')
        assert len(calls) >= len(model_decisions)
        assert all((tmp_path / 'model_calls' / call / 'response.json').is_file() for call in calls)
        assert {name.split('_')[2] for name in model_decisions} == {str(unit['index']) for unit in units}

        # Every unit executed, recorded its outcome and entered the controller with the measured credit.
        for unit in units:
            assert unit['kind'] in ('tool', 'reason', 'child')
            assert type(unit['credit']) in (int, float)
            assert unit['estimation_context']['progress_time']['position'] == unit['index']
            assert 'a107_state_' + str(unit['index']) in decisions
            if unit['kind'] != 'child':
                executed = decisions['a107_outcome_' + str(unit['index'])]
                assert executed['kind'] == unit['kind'] and executed['outcome']['status'] == unit['status']
        controller = record.controller_state
        assert len(controller.history) == len(units)
        assert controller.current_credit == units[-1]['credit']

        # The result is admitted by the head's return form: a numeric credit and a finding.
        admitted = head.return_form.admit(result, 'return:' + ROLE)
        assert type(admitted['credit']) in (int, float)
        assert isinstance(admitted['finding'], dict)
        assert isinstance(admitted['finding']['known_assessment_refs'], list)
        assert admitted['credit'] == controller.current_credit - controller.initial_credit
        assert RunJournal(journal_path).run_state(RUN_ID) == (
            'closed', json.loads(canonical({'ended_by': 'yield_stop', 'units': len(units), 'result': admitted})))

        # Resuming the finished run from its journal returns the identical result without a model call.
        resumed_provider = ModelProvider(load_config(), tmp_path / 'model_calls_resumed', tmp_path)
        resumed = resume(registry, run_id=RUN_ID, journal=RunJournal(journal_path),
                         collaborators=collaborators(store, tmp_path, resumed_provider))
        again = asyncio.run(resumed.run())
        assert again['result'].as_record() == result
        assert again['record'].ended_by == 'yield_stop' and again['record'].units_consumed == len(units)
        assert model_calls(tmp_path / 'model_calls_resumed') == []
        assert model_calls(tmp_path / 'model_calls') == calls
