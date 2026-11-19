"""A real run at the A106 head (``perturbation_evidence``) that calls the model, then its resume.

Real pieces only: the A106 home factory's fifteen bindings composed over one shared Store, each binding's own
A106 tool registry, the frozen perturbation-evidence library (the repository's published slotted process
library) and the frozen tool library of the head's own registry, the runner's journal and linker, and the
run's one ``ModelProvider`` over the Codex app-server (``[models]`` of the packaged ``defaults.toml``).

The subject is the repository's known protein sequence (``tests/fixtures/a108/known_sequence.txt``; only its
raw residues enter the Store). The head's assignment is filled the way the root fills it
(``root/decisions.axis_assignment``): the held subject scope, the proposed annotation the entry supplies (an
unresolved biological role of the subject: no candidate function is assumed), the held constraints and
evidence references, the head's declared evidence task, and the two choices the head offers (one library
thought pattern and a subset of its tools).

Continuation settings are the packaged A106 defaults (``episode_support/configuration/perturbation_evidence/
defaults.toml``: ``[controller]`` and ``[scientific_progress]``). The run ends only by the head's own
continuation. Outside services other than the model are blocked by the command's proxy settings, so a tool or
child that needs them returns its own failed outcome, which enters the iterator like any other.

Run with ``-m model_run`` through ``tools/one_workflow.sh``; the default selection deselects it.
"""
import asyncio
import json
import math
from pathlib import Path
import tomllib

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume

from gene_annotation_episode.episodic_workflow.episode_support.configuration.perturbation_evidence.process_options import (
    PerturbationEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import (
    OPTIONAL_POPULATIONS)
from gene_annotation_episode.episodic_workflow.episode_support.tools.perturbation_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.credit import original_task_projector
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.episode_contract import (
    API_JOB_PATHS, CHILD_SLOTS, H, L, a106_progress_provider, home)
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.literature_binding import (
    ROLE_PATHS)
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.published_evidence_assessment.literature_credit import (
    YIELD_TASKS)
from gene_annotation_episode.episodic_workflow.root.a106.perturbation_evidence.yield_estimator import TASK
from gene_annotation_episode.episodic_workflow.root.decisions import axis_assignment
from gene_annotation_episode.episodic_workflow.root.goal import axis_objective
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

pytestmark = pytest.mark.model_run

HEAD = H
RUN_ID = 'a106-head-model-run'
REPOSITORY = Path(__file__).resolve().parents[6]
SEQUENCE = REPOSITORY / 'tests' / 'fixtures' / 'a108' / 'known_sequence.txt'
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
DEFAULTS = (REPOSITORY / 'gene_annotation_episode' / 'episodic_workflow' / 'episode_support' / 'configuration'
            / 'perturbation_evidence' / 'defaults.toml')
# The thought pattern this commission investigates with: restoration against bypass, compensation and reduced
# function, the published pattern about perturbation and restoration evidence.
THOUGHT_PATTERN = 'P07'
# The BV-BRC AppService resource of the API job and results bindings, at the service's documented endpoints.
APPSERVICE = {'kind': 'api', 'service': 'bvbrc_appservice', 'execution_contract': 'bvbrc_appservice_execution_v1',
              'endpoints': {'AppService': 'https://p3.theseed.org/services/app_service',
                            'Workspace': 'https://p3.theseed.org/services/Workspace'},
              'scientific_adapters': []}
RESOURCES = {'bvbrc': APPSERVICE}
RESULT_PATHS = (H + '/execution_result_acquisition', L + '/execution_result_acquisition')
SUBMISSION_PATHS = (H + '/execution_job_submission', L + '/execution_job_submission')
MONITOR_PATH = H + '/execution_progress_assessment'


def packaged_settings():
    """The packaged A106 continuation cost, uncertainty and finding unit."""
    defaults = tomllib.loads(DEFAULTS.read_text())
    return (defaults['controller']['cost'], defaults['controller']['uncertainty_alpha'],
            float(defaults['scientific_progress']['finding_unit']), defaults['restoration']['preview_size'])


def compose(store, root):
    """The A106 registry from its real home factory over the shared Store, with every binding's configuration."""
    cost, alpha, unit, page = packaged_settings()
    library = PerturbationEvidenceLibrary.freeze(root / 'library', source=LIBRARY_SOURCE)
    # The frozen tool library holds the contracts of the head's own registry (same Store, same settings).
    tool_library = ScientificToolLibrary.freeze(root / 'tool_library', catalog=ToolRegistry(store).catalog(None))
    evidence_task = {'version': 'evidence_axis_task_v1', 'kind': 'whole_axis_findings', 'evidence_axis': 'A106',
                     'credit_unit': unit}
    head = {'library': library, 'tool_library': tool_library, 'tools': {},
            'child_roles': tuple(CHILD_SLOTS[H]),
            'yield_bindings': {TASK: {
                'kind': 'accumulation', 'cutoff': cost, 'parameters': {'uncertainty_alpha': alpha},
                'credit_definition': original_task_projector({'context': {'evidence_task': evidence_task}}).as_record()}}}
    literature_yield = {task: {'credit_unit': unit, 'cutoff': cost, 'uncertainty_alpha': alpha,
                               'kind': 'accumulation' if task.endswith(':verified_source_leads')
                               else 'remaining_commissioned_credit'} for task in sorted(YIELD_TASKS)}
    origins = {name: 'reported_source' for name in ('ratio_source', 'controlled_response', 'gel')}
    configuration = {path: {} for path in SUBMISSION_PATHS}
    configuration[H] = head
    configuration[MONITOR_PATH] = {'tools': {}, 'information_unit': unit, 'yield_settings': {
        'kind': 'information_accumulation', 'cutoff': cost, 'uncertainty_alpha': alpha}}
    for path in (*API_JOB_PATHS, *RESULT_PATHS):
        configuration[path] = {'tools': {}, 'resources': RESOURCES}
    for role, path in ROLE_PATHS.items():
        configuration[path] = {'tools': {}, 'yield_bindings': literature_yield, 'outcome_page_size': page,
                               'populations': OPTIONAL_POPULATIONS, 'evidence_origins': origins,
                               'analysis_children': role == 'literature'}
    return BindingRegistry.compose([home], {'store': store, 'perturbation_evidence': configuration})


def runtime_collaborators(store, provider):
    """Every runtime collaborator the A106 subtree declares: the standard three and its progress provider."""
    cost, alpha, _, _ = packaged_settings()
    completion = {'cutoff': cost, 'parameters': {'uncertainty_alpha': alpha}}
    return {'store': store, 'model_provider': provider,
            'continuation': {path: completion for path in (*SUBMISSION_PATHS, *API_JOB_PATHS, *RESULT_PATHS)},
            'a106_progress_provider': a106_progress_provider(store, run_id=RUN_ID)}


def head_entry_input(registry, scope, proposed_annotation_ref):
    """The head's commission as the root fills it: held values, the declared task and the offered choices."""
    head = registry.binding(HEAD)
    held = {'scope': scope, 'proposed_annotation_ref': proposed_annotation_ref, 'constraints': {},
            'evidence_refs': []}
    choices = {'thought_pattern': THOUGHT_PATTERN, 'tools': list(head.assignment_form.fields['tools'].options)}
    return {'objective': axis_objective(HEAD), 'assignment': axis_assignment(HEAD, head, held, choices)}


def decisions(journal, run_id):
    """Every recorded decision of the run as ``(episode path, name, value)``, in recording order."""
    return [(json.loads(path), name, json.loads(value)) for path, name, value in journal.db.execute(
        'SELECT path, name, value FROM decisions WHERE run_id=? ORDER BY rowid', (run_id,))]


def test_head_run_calls_the_model_and_ends_by_its_own_continuation_then_resumes_identically(tmp_path):
    root = tmp_path / 'services'
    model_cwd = tmp_path / 'model_cwd'
    model_cwd.mkdir()
    sequence = SEQUENCE.read_text().strip()
    head_path = [[HEAD.replace('/', '__'), RUN_ID]]

    # -- the run -------------------------------------------------------------------------------------------------
    with Store(tmp_path / 'workspace') as store:
        subject_refs = list(store.create_problem(raw_sequence=sequence, molecule='protein')['subject_refs'])
        scope = store.validate_scope({'subject_refs': subject_refs})
        proposed = store.put('hypothesis', {'subject_refs': subject_refs, 'predicate': 'biological_role',
                                            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []},
                             origin='caller')['id']
        registry = compose(store, root)
        head = registry.binding(HEAD)
        assert len(registry.subtree(HEAD)) == len(CHILD_SLOTS) == 15
        entry_input = head_entry_input(registry, scope, proposed)
        assert entry_input['assignment']['evidence_task'] == head.assignment_form.declared['evidence_task']
        provider = ModelProvider(load_config(), tmp_path / 'model_calls', model_cwd)
        journal = RunJournal(tmp_path / 'journal.sqlite3')
        run = link(registry, HEAD, entry_input, run_id=RUN_ID, journal=journal,
                   collaborators=runtime_collaborators(store, provider))
        outcome = asyncio.run(run.run())
        record, result = outcome['record'], outcome['result'].as_record()

        # The run ended by the head's own continuation, with the journal closed on that end.
        assert record.ended_by == 'yield_stop'
        assert record.controller_state.stop is True
        state, closed = journal.run_state(RUN_ID)
        assert state == 'closed'
        assert closed == {'ended_by': 'yield_stop', 'units': record.units_consumed, 'result': result}

        # At least one model decision was recorded, and every recorded decision is one real provider call.
        recorded = decisions(journal, RUN_ID)
        own = {name: value for path, name, value in recorded if path == head_path}
        model_decisions = [name for name in own if name.startswith('decision.')]
        assert model_decisions
        calls = sorted(path.name for path in (tmp_path / 'model_calls').glob('call-*'))
        assert calls and all((tmp_path / 'model_calls' / call / 'response.json').is_file() for call in calls)
        assert len(calls) == len([name for _, name, _ in recorded if name.startswith('decision.')])

        # At least one unit executed; every unit's outcome is recorded and the controller observed it.
        units = journal.units(RUN_ID, head_path)
        assert record.units_consumed == len(units) >= 1
        assert len(record.controller_state.history) == len(units)
        for position, (label, controller_input) in enumerate(units):
            executed = own['outcome.' + str(position)]
            assert executed['kind'] in ('reason', 'tool', 'child') and executed['status']
            assert isinstance(label, str) and label
            assert controller_input['unit'] == {'position': position, 'kind': executed['kind'],
                                                'status': executed['status']}
            assert type(controller_input['credit']) in (int, float) and math.isfinite(controller_input['credit'])
            receipt = controller_input['estimation_context']['progress_time']
            assert receipt['position'] == position and receipt['status'] == 'available'
            # Each unit is the admitted selection of its last recorded decision attempt.
            assert any(name.startswith('decision.' + str(position) + '.') for name in model_decisions)
        assert record.controller_state.current_credit == units[-1][1]['credit']

        # The result is admitted by the head's return form, with a numeric credit and a finding.
        assert head.return_form.admit(result, 'a106_head_result') == result
        assert type(result['credit']) in (int, float) and math.isfinite(result['credit'])
        assert result['credit'] == record.controller_state.current_credit
        finding = result['finding']
        assert isinstance(finding, dict) and finding['proposed_annotation_ref'] == proposed
        assert finding['scope'] == scope and finding['ended_by'] == 'yield_stop'
        assert finding['units'] == record.units_consumed
        assert result['credit'] == finding['policy']['finding_unit'] * finding['retained_finding_count']
        for ref in finding['known_assessment_refs']:
            assert store.get(ref)['record_type'] == 'assessment'
        episodes = journal.episodes(RUN_ID)
        assert episodes[0] == {'path': head_path, 'binding_path': HEAD, 'state': 'closed'}
        assert all(episode['state'] == 'closed' for episode in episodes)
        journal.db.close()

    # -- its resume from the journal -------------------------------------------------------------------------------
    with Store(tmp_path / 'workspace') as store:
        registry = compose(store, root)
        resumed_provider = ModelProvider(load_config(), tmp_path / 'model_calls_resumed', model_cwd)
        journal = RunJournal(tmp_path / 'journal.sqlite3')
        resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                     collaborators=runtime_collaborators(store, resumed_provider)).run())
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
