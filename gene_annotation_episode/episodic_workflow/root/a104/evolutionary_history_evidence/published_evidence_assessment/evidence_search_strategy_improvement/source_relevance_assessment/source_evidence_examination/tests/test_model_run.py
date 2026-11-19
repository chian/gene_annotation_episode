"""A real run of this episode, the parent of the grading leaf, with the real model, through the public runner only.

The entry assignment is the page of a source that reports one assay (the world of the passage leaf's own grading
test: its effect, variance, controls and fixed predictions, each a number with its printed unit), the anchored assay
reference, the reaction term and the proposed annotation; the commission is a source answer about that source. The
registry holds this episode and its three children, so the model may examine the page itself or commission a child
(the passage reading is the child that grades). ``link(...).run()`` runs it with the standard ``ModelProvider``; the
run ends through the yield controller; the parent receives each child's credit and controlled finding only; and a
resume replays the recorded answers without a new model call.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
CHILDREN = {'passage_evidence_extraction': 'PassageEvidenceExtraction',
            'table_evidence_extraction': 'TableEvidenceExtraction',
            'source_coverage_improvement': 'SourceCoverageImprovement'}
RUN_ID = 'real104_examination'
REGISTRY_SETTINGS = {'pdfinfo_executable': None, 'pdftotext_executable': None, 'pdftoppm_executable': None,
                     'job_limits': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}}
LINES = ['Experiment A: purified enzyme hydrolysis rate assay with a known normal fixed-prediction model.',
         'effect 12.5 U/mg; variance 0.25 U/mg_squared;',
         'recovery 0.9 fraction; attributed 0.6 fraction; total 0.8 fraction;',
         'condition test 0.8 fraction; condition reference 1 fraction;',
         'assertion prediction 12 U/mg; alternative prediction 0 U/mg.']
TEXT = '\n'.join(LINES)


def world(directory):
    store = Store(directory / 'store')
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    target = store.problem()['subject_refs'][0]
    scope = {'subject_refs': [target]}
    artifact = store.artifact(TEXT, 'text/plain')
    source = store.put('source', {'provider': 'synthetic_a104_passage', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']
    assay = store.put('reference', {'reference_type': 'assay', 'source_ref': source, 'accession': 'synthetic_assay_a',
                                    'label': 'Experiment A', 'sequence_ref': None, 'molecule': None, 'length': None,
                                    'term_refs': [], 'context_refs': [],
                                    'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0,
                                               'end': len(LINES[0]), 'quote': LINES[0]}}, origin='caller')['id']
    reaction = store.put('term', {'namespace': 'synthetic', 'accession': 'hydrolysis', 'label': 'Hydrolysis',
                                  'term_type': 'reaction', 'source_ref': source, 'anchor': None},
                         origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': reaction}, 'context_refs': []},
                         origin='reasoning')['id']
    task = {'kind': 'source_answer', 'answer_kind': 'assessment', 'evidence_axis': 'A104', 'credit_unit': 1.0,
            'source_refs': [source]}
    assignment = {'version': 'page_assignment_v1', 'source_ref': source, 'representation': 'original',
                  'artifact_ref': artifact, 'question_context_refs': [], 'prior_delivery_refs': [],
                  'literature_task': task, 'proposed_annotation_ref': proposed, 'scope': scope,
                  'received_record_refs': [target, source, artifact, assay, reaction, proposed]}
    return {'store': store, 'input': {'assignment': assignment, 'message': {'objective': 'grade the assay'},
                                      'selection': []}}


def bindings():
    episodes = [EPISODE()]
    for name, cls in CHILDREN.items():
        episodes.append(getattr(importlib.import_module(PACKAGE + '.' + name + '.episode'), cls)())
    return episodes


def collaborators(state, directory):
    settings = {'cost': 0.1, 'parameters': {'uncertainty_alpha': 0.05}, 'knowledge_library_directory': None,
                'tool_registry': {**REGISTRY_SETTINGS, 'minimap2_cache_dir': str(directory / 'minimap2-cache')}}
    return {'store': state['store'], 'model_provider': state['provider'],
            'continuation': {episode.binding_path: {**settings, 'cost': 0.02 if episode.binding_path == EPISODE.binding_path
                                                     else 0.1} for episode in bindings()}, 'services': {}}


@pytest.mark.model_run
def test_the_model_examines_the_page_and_the_run_ends_by_its_yield_controller(tmp_path):
    state = world(tmp_path)
    state['provider'] = ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    registry = BindingRegistry(bindings())
    closed = asyncio.run(link(registry, EPISODE.binding_path, state['input'], run_id=RUN_ID, journal=journal,
                              collaborators=collaborators(state, tmp_path)).run())
    result = closed['result'].as_record()
    assert journal.run_state(RUN_ID)[1]['ended_by'] == 'yield_stop'
    rows = list(journal.episodes(RUN_ID))
    entry = min(rows, key=lambda row: len(row['path']))
    units = journal.units(RUN_ID, entry['path'])
    print('EPISODES', [row['path'] for row in rows])
    print('UNITS', json.dumps([unit[2]['tool'] if unit[2]['kind'] == 'tool' else 'child:' + unit[2]['slot']
                               for unit in units]))
    for unit in units:
        if unit[2]['kind'] == 'child':
            report = unit[2]['report']
            assert set(report) <= {'slot', 'credit', 'finding', 'literature_screening_answers',
                                   'literature_source_lead_dispositions'}
            print('CHILD_REPORT', json.dumps({'slot': report['slot'], 'credit': report['credit'],
                                              'sheets': len(report['finding']['assay_sheets']),
                                              'assessments': len(report['finding']['assessments'])}))
    print('RESULT', json.dumps(result)[:3000])
    assert EPISODE.return_form.select(()).admit(result, 'return') == result
    asked = len(list((tmp_path / 'model_calls').glob('call-*')))
    resumed = asyncio.run(resume(registry, run_id=RUN_ID, journal=journal,
                                 collaborators=collaborators(state, tmp_path)).run())['result'].as_record()
    assert resumed == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == asked
    state['store'].close()
