"""Branch runs of the A110 head with the real model on a held world (the reaction world of the literature grading
plus a proposed reaction hypothesis): the head alone (1a), the head with the literature child subtree (1b) and the
head offered every child slot while only the literature subtree is registered (1). Public API only: ``link(...).run()``
with the standard ``ModelProvider``, a real Store and journal, then ``resume``. Selected only with ``-m model_run``."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.tests.reaction_world import (
    held_world)

from ..credit import projector
from ..episode import BiochemicalFeasibilityEvidence as HEAD
from ..goal import BINDING_PATH

LIT = 'gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.published_evidence_assessment'
CHAIN = (('', 'PublishedEvidenceAssessment'),
         ('.evidence_search_strategy_improvement', 'EvidenceSearchStrategyImprovement'),
         ('.evidence_search_strategy_improvement.source_relevance_assessment', 'SourceRelevanceAssessment'),
         ('.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination',
          'SourceEvidenceExamination'),
         ('.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.'
          'source_coverage_improvement', 'SourceCoverageImprovement'),
         ('.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.'
          'passage_evidence_extraction', 'PassageEvidenceExtraction'),
         ('.evidence_search_strategy_improvement.source_relevance_assessment.source_evidence_examination.'
          'table_evidence_extraction', 'TableEvidenceExtraction'))
SHA = 'a' * 64
OPTION = {'version': 'biochemical_feasibility_evidence_option_ref_v1', 'library_id': SHA, 'entry_sha256': SHA}
TASK = 'A110:received_scientific_finding_progress'
LEAF_SETTINGS = {'cost': 0.02, 'parameters': {'uncertainty_alpha': 0.05}}


def world(tmp_path):
    store, entry, _, paper = held_world(tmp_path)
    scope = entry['assignment']['scope']
    held = list(entry['assignment']['received_record_refs'])
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'oxidase_reaction', 'label': 'Oxidase reaction',
                                  'term_type': 'reaction', 'source_ref': paper['id'], 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': scope['subject_refs'], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='caller')['id']
    held = [*held, reaction, proposed]
    selection = {'version': 'selection_v1', 'evidence_axis': {**OPTION, 'slot': 'evidence_axis', 'option_id': 'A110'},
                 'thought_pattern': {**OPTION, 'slot': 'thought_pattern', 'option_id': 'P1'},
                 'child_tool_info': [{'name': 'source.read', 'resources': 'local'}]}
    assignment = {'selection': selection, 'proposed_annotation_ref': [proposed], 'evidence_refs': held,
                  'constraints': {}, 'context': {'evidence_task': {'version': 'evidence_axis_task_v1',
                                                                   'kind': 'whole_axis_findings',
                                                                   'evidence_axis': 'A110', 'credit_unit': 1}},
                  'scope': scope, 'received_record_refs': held}
    return store, {'assignment': assignment, 'message': {'objective': 'Assess whether the proposed reaction is '
                   'chemically feasible; the held paper reports the measurements.'}, 'selection': []}, paper['id']


def settings(entry, roles, with_literature):
    parent = HEAD.read_from_parent(HEAD.assignment_form.admit(entry['assignment'], 'assignment'), entry['message'])
    declaration = {'kind': 'accumulation', 'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.05},
                   'credit_definition': projector(parent).as_record()}
    value = {BINDING_PATH: {'child_roles': roles, 'handoff_unit': 1.0, 'acquired_record_unit': 1.0,
                            'information_unit': 1.0, 'tool_registry': {},
                            'yield_bindings': {TASK: declaration}}}
    if with_literature:
        value.update({LIT.split('episodic_workflow.root.a110.')[1].replace('.', '/') + path.replace('.', '/'):
                      LEAF_SETTINGS for path, _ in CHAIN})
    return value


def bindings(with_literature):
    found = [HEAD()]
    if with_literature:
        found += [getattr(importlib.import_module(LIT + path + '.episode'), name)() for path, name in CHAIN]
    return found


def run_branch(tmp_path, run_id, roles, with_literature):
    store, entry, paper = world(tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry(bindings(with_literature))
    continuation = settings(entry, roles, with_literature)
    collaborators = {'store': store, 'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path),
                     'continuation': continuation, 'services': {}}
    try:
        outcome = asyncio.run(link(registry, BINDING_PATH, entry, run_id=run_id, journal=journal,
                                   collaborators=collaborators).run())
    finally:
        print('HEAD_RUN_STATE', json.dumps(journal.run_state(run_id), default=str))
        path = ((BINDING_PATH.replace('/', '__'), run_id),)
        for index, unit in enumerate(journal.units(run_id, path)):
            body = unit[2]
            print('HEAD_UNIT', index, json.dumps(body, default=str, sort_keys=True)[:1500])
        print('HEAD_FAILURE', journal.run_failure(run_id))
    first = outcome['result'].as_record()
    print('HEAD_RESULT', json.dumps(first, sort_keys=True, default=str))
    assert set(first) >= {'credit', 'finding'}
    assert HEAD.return_form.select(()).admit(first, 'return') == first
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    assert asked > 0
    resumed = asyncio.run(resume(registry, run_id=run_id, journal=journal, collaborators=collaborators).run())
    assert resumed['result'].as_record() == first
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    store.close()


@pytest.mark.model_run
def test_branch_head_with_every_slot_offered_and_only_the_literature_subtree(tmp_path):
    run_branch(tmp_path, 'a110_head_all', ['launch', 'monitor', 'results', 'hpc', 'literature', BINDING_PATH], True)


@pytest.mark.model_run
def test_branch_head_with_its_own_tools_only(tmp_path):
    run_branch(tmp_path, 'a110_head_alone', [BINDING_PATH], False)


@pytest.mark.model_run
def test_branch_head_with_the_literature_child(tmp_path):
    run_branch(tmp_path, 'a110_head_literature', ['literature', BINDING_PATH], True)
