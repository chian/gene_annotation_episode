"""The branch run of the page (A105) with the real model, in the sheet-update paradigm (OWNER_DECISION 10): the page is
commissioned for ONE hypothesis 'PopZ binds ParB' over the real SPR paragraph of Bowman et al., Cell 2008 (PMC2745220),
the one the chunk test uses. The real model of the page chooses its own units; the real model of a ``chunk`` child
extracts the leaf record; the page's ``update_sheet`` groups the leaf records into graders and runs ``page_update`` over
the claim of the hypothesis, persists the row states through custody and returns only credit, scores, features and the
state references. The test asserts on what the page returned. ``link(...).run()`` with the standard ``ModelProvider``,
the real Store and journal; ``resume`` of the closed run replays the recorded answers.

Selected only with ``-m model_run``; it needs the owner's Codex sign-in."""
import asyncio
import importlib
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link, resume
from episode_runtime.estimate_table import EstimateTable
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import (
    spr_passages)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from . import grading_world as gw
from .grading_world import CHILD_PATHS, MODEL_SETTINGS, held_world

PACKAGE = __name__.rsplit('.', 2)[0]
EPISODE = importlib.import_module(PACKAGE + '.episode').SourceEvidenceExamination
PATH = EPISODE.binding_path
CHILD_CLASSES = [getattr(importlib.import_module(PACKAGE + '.' + name + '.episode'), cls) for name, cls in zip(
    CHILD_PATHS, ('TableEvidenceExtraction', 'SourceCoverageImprovement', 'PassageEvidenceExtraction'))]
OBJECTIVE = 'evidence_in_passages'
POPZ_SEQUENCE = ('MSDQSQEPTMEEILASIRRIISEDDAPAEPAAEAAPPPPPEPEPEPVSFDDEVLELTDPIAPEPELPPLETVGDIDVYSPPEPESEPAYTPPPAAPVFDRDEVAEQ'
                 'LVGVSAASAAASAFGSLSSALLMPKDGRTLEDVVRELLRPLLKEWLDQNLPRIVETKVEEEVQRISRGRGA')


def popz_world(directory):
    """The page commissioned for the hypothesis 'PopZ binds ParB': the source is the real paragraph between a lead-in
    and a tail; the hypothesis is the claim (subject PopZ, partner ParB, predicate binds; no prediction pair)."""
    world = held_world(directory)
    store, paragraph = world['store'], spr_passages.popz_chunk()[0]
    text = 'Preceding text. ' + paragraph + ' Following text.'
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'real_a105_popz_paragraph', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']

    def protein(label, sequence=None):
        """PopZ, the claim's subject, holds its real sequence (UniProt A0A0H3C7Y4): the page compares the protein a paper
        identifies with it by pairwise BLAST."""
        return store.put('reference', {'reference_type': 'protein', 'source_ref': source, 'accession': label.lower(),
                                       'label': label, 'anchor': None, 'term_refs': [], 'context_refs': [],
                                       'sequence_ref': None if sequence is None else store.artifact(sequence, 'text/plain'),
                                       'molecule': None if sequence is None else 'protein',
                                       'length': None if sequence is None else len(sequence)}, origin='caller')['id']
    popz, parb = protein('PopZ', POPZ_SEQUENCE), protein('ParB')
    proposed = store.put('hypothesis', {'subject_refs': [popz], 'predicate': 'binds',
                                        'value': {'type': 'reference', 'ref': parb}, 'context_refs': []},
                         origin='reasoning')['id']
    assignment = dict(world['input']['assignment'])
    assignment.update({'source_ref': source, 'artifact_ref': artifact, 'proposed_annotation_ref': proposed,
                       'received_record_refs': [world['target'], source, artifact, popz, store.get(popz)['sequence_ref'], parb,
                                                proposed]})
    world.update({'source': source, 'artifact': artifact, 'proposed': proposed, 'text': text,
                  'input': {'assignment': assignment, 'message': {'objective': OBJECTIVE},
                            'selection': ['sheet_state_refs']}})
    return world


def linked(directory, world, run_id):
    registry = BindingRegistry([EPISODE(), *(cls() for cls in CHILD_CLASSES)])
    continuation = {PATH: MODEL_SETTINGS,
                    **{cls.binding_path: {**MODEL_SETTINGS, 'launch_instruction_directory': None}
                       for cls in CHILD_CLASSES}}
    journal = RunJournal(directory / 'journal.sqlite3')
    world['collaborators'] = {'store': world['store'],
                              'model_provider': ModelProvider(load_config(), directory / 'model_calls', directory),
                              'continuation': continuation, 'services': gw.job_world_services(directory)}
    return registry, journal, link(registry, PATH, world['input'], run_id=run_id, journal=journal,
                                   collaborators=world['collaborators'])


def recorded_requests(tmp_path):
    return [json.loads((call / 'request.json').read_text())
            for call in sorted((tmp_path / 'model_calls').glob('call-*'))]


# Each episode's decision calls and the context key a call carries when it asks again after a refused answer: the page's
# decisions carry the refusal as ``feedback``; the chunk's extraction calls as ``previous_answer_was_rejected_because``.
ASKED_AGAIN_KEYS = {'page': 'feedback', 'chunk': 'previous_answer_was_rejected_because'}


def episode_of(request):
    context = request['context']
    if 'child_options' in context and 'commission' in context:
        return 'page'
    if 'chunk' in context and 'experiment_type' in context:
        return 'chunk'
    return None


def rejection_facts(requests, page_units):
    """(retried, failed, reasons) over the decision calls of the page and of its chunk children (the idea of the chunk
    test's ``no_unrecovered_rejection``). A refused answer that is asked again and then accepted is normal (retried). A
    call is accepted unless the next call of the same episode asks again because of its refusal. Only a refusal never
    followed by an accepted call is a failure: for the page, its accepted decision calls must equal its units (a refused
    last answer leaves an accepted-looking call with no unit), and ``failed`` is the size of any mismatch."""
    retried, reasons, accepted_page = {}, [], 0
    for name, key in ASKED_AGAIN_KEYS.items():
        calls = [request for request in requests if episode_of(request) == name]
        again = [call['context'].get(key) is not None for call in calls]
        accepted = [index for index in range(len(calls)) if index + 1 == len(calls) or not again[index + 1]]
        retried[name] = len(calls) - len(accepted)
        reasons.extend((name, call['context'][key]) for call, asked in zip(calls, again) if asked)
        if name == 'page':
            accepted_page = len(accepted)
    # The page's assess_content and update_sheet units are decided by code (no model call); every other page unit is one
    # accepted call.
    decided = [unit for unit in page_units if unit[2]['kind'] == 'child']
    return retried, abs(accepted_page - len(decided)), reasons


def print_inputs(store, units):
    """The page's input list as the run used it: the needs and candidates with Jev's probabilities (the held assessment
    of the ``assess_content`` unit), the units in order, the candidate or windows each child consumed, and whether a
    byte range was handed to two children."""
    assessed = [unit[2] for unit in units if unit[2]['kind'] == 'tool' and unit[2]['tool'] == 'assess_content']
    assessment = json.loads(store.get_artifact(assessed[0]['outcome']['assessment_ref']))
    for need in assessment['information_needs']:
        print('PAGE_NEED', need['need_id'], need['kind'], json.dumps(need['label']))
    for item in assessment['candidates']:
        print('PAGE_CANDIDATE', item['candidate_id'], item['candidate_type'], item['start_offset'], item['end_offset'],
              json.dumps(item['probabilities']))
    print('PAGE_JEV_REQUESTS', json.dumps(assessment['requests']))
    handed = []
    for index, unit in enumerate(units):
        outcome = unit[2]
        if outcome['kind'] == 'child':
            assignment = outcome['message']['assignment']
            windows = assignment.get('windows') or [[assignment['offset'], assignment['offset'] + assignment['limit']]]
            print('PAGE_UNIT', index, 'child', outcome['slot'], outcome['arguments'].get('candidate_id'), windows,
                  assignment['sheet_class'])
            handed.extend(windows)
        else:
            print('PAGE_UNIT', index, 'tool', outcome['tool'])
    overlaps = [(a, b) for i, a in enumerate(handed) for b in handed[i + 1:] if a[0] < b[1] and b[0] < a[1]]
    print('PAGE_WINDOWS_HANDED_TWICE', overlaps)


@pytest.mark.model_run
def test_the_page_commissioned_for_popz_binds_parb_returns_credit_scores_features_and_state_refs(tmp_path):
    world = popz_world(tmp_path)
    store = world['store']
    run_id = 'a105-page-popz-parb'
    registry, journal, run = linked(tmp_path, world, run_id)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    units = journal.units(run_id, ((EPISODE().grain_name, run_id),))
    trace = [(unit[2]['kind'], unit[2].get('tool') or unit[2].get('slot')) for unit in units]
    print('PAGE_UNITS', trace)
    print_inputs(store, units)
    assert trace[0] == ('tool', 'assess_content')     # Jev measured the candidates before the page planned
    requests = recorded_requests(tmp_path)
    retried, failed, reasons = rejection_facts(requests, units)
    print('PAGE_MODEL_CALLS', len(requests), 'REJECTED_RETRIED', json.dumps(retried), 'REJECTED_FAILED', failed)
    for name, reason in reasons:
        print('PAGE_REJECTION', name, json.dumps(reason)[:400])
    for unit in units:
        if unit[2]['kind'] == 'child':
            print('PAGE_CHILD_REPORT', unit[2]['slot'], json.dumps(unit[2]['report'])[:1500])
        elif unit[2]['tool'] == 'update_sheet':
            print('PAGE_UPDATE_SHEET_OUTCOME', json.dumps(unit[2]['outcome'])[:3000])
    print('PAGE_RETURN', json.dumps(result))
    print('PAGE_CREDIT', result['credit'])
    print('PAGE_SCORES', json.dumps(result['finding']['scores']))
    print('PAGE_FEATURES', json.dumps(result['finding']['features']))
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert failed == 0, ('a refused page answer was never followed by an accepted one', reasons)
    chunks = [unit for unit in units if unit[2]['kind'] == 'child' and unit[2]['slot'] == 'chunk']
    updates = [unit for unit in units if unit[2]['kind'] == 'tool' and unit[2]['tool'] == 'update_sheet']
    assert chunks and updates                  # the page commissioned the chunk child and then updated the sheet
    assert EPISODE.return_form.select(('sheet_state_refs',)).admit(result, 'return') == result
    assert set(result) == {'credit', 'finding', 'sheet_state_refs'}
    assert set(result['finding']) == {'scores', 'features'}      # no raw record, no grader, no leaf record
    assert 0 <= result['credit'] <= 1
    scores = result['finding']['scores']
    assert scores and all(score['target_id'] == 'popz' for score in scores)
    # The return carries no bearing field (the form holds scores and features only): a direct bearing for the claim shows
    # as a subscoring row of the target popz that holds at least one experiment, for the commissioned hypothesis.
    features = result['finding']['features']
    assert any(item['target_id'] == 'popz' and item['assertion_ref'] == world['proposed'] and item['experiments'] >= 1
               for item in features)
    refs = result['sheet_state_refs']
    assert refs and len(set(refs)) == len(refs)
    last = updates[-1][2]['outcome']['sheet_update']
    assert refs == last['sheet_state_refs']
    for ref in refs:                           # the stored states are readable through custody
        held = json.loads(store.get_artifact(ref))
        print('PAGE_STATE', ref, json.dumps(held)[:600])
        assert held['row']['sheet'] and held['row']['assertion_ref'] == world['proposed']
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resume(registry, run_id=run_id, journal=journal,
                               collaborators=world['collaborators']).run())['result'].as_record()
    assert again == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    store.close()


# ---- The first activity_rate type, spectro_direct (SOP step 8): the same page run, commissioned for 'ThdF catalyzes flavin reduction' over the real paragraph of
# J Biol Chem 2025 (PMC11795597, CC BY 4.0) on the kinetics of the flavin reductase ThdF (the paragraph the chunk test uses). The class's predicate is
# catalyzes (subject the enzyme; the claim's partner is null when the value is a reaction term).
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import spectro_direct_passages


def dfra_world(directory):
    """The page commissioned for the hypothesis 'ThdF catalyzes flavin reduction': the source is the real paragraph between a lead-in and a tail; the hypothesis
    is the claim (subject ThdF, predicate catalyzes, the value a reaction term as the existing A105 hypotheses carry, so the claim's partner is null)."""
    world = held_world(directory)
    store, paragraph = world['store'], spectro_direct_passages.REAL
    text = 'Preceding text. ' + paragraph + ' Following text.'
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'real_a105_dfra_paragraph', 'accession': None, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': None, 'retrieved_at': None, 'parent_source_refs': []},
                       origin='caller')['id']

    def reference(kind, label):
        return store.put('reference', {'reference_type': kind, 'source_ref': source, 'accession': label.lower(),
                                       'label': label, 'sequence_ref': None, 'molecule': None, 'length': None,
                                       'term_refs': [], 'context_refs': [], 'anchor': None}, origin='caller')['id']
    dfra = reference('protein', 'ThdF')
    dhf = store.put('term', {'namespace': 'synthetic', 'accession': 'flavin_reduction', 'label': 'Flavin reduction',
                             'term_type': 'reaction', 'source_ref': source, 'anchor': None}, origin='caller')['id']
    proposed = store.put('hypothesis', {'subject_refs': [dfra], 'predicate': 'catalyzes',
                                        'value': {'type': 'term_ref', 'ref': dhf}, 'context_refs': []},
                         origin='reasoning')['id']
    assignment = dict(world['input']['assignment'])
    assignment.update({'source_ref': source, 'artifact_ref': artifact, 'proposed_annotation_ref': proposed,
                       'received_record_refs': [world['target'], source, artifact, dfra, dhf, proposed]})
    world.update({'source': source, 'artifact': artifact, 'proposed': proposed, 'text': text,
                  'input': {'assignment': assignment, 'message': {'objective': OBJECTIVE},
                            'selection': ['sheet_state_refs']}})
    return world


@pytest.mark.model_run
def test_the_page_commissioned_for_thdf_catalyzes_flavin_reduction_returns_credit_scores_features_and_a_directly_bearing_row(tmp_path):
    world = dfra_world(tmp_path)
    store = world['store']
    run_id = 'a105-page-thdf-flavin-reduction'
    registry, journal, run = linked(tmp_path, world, run_id)
    closed = asyncio.run(run.run())
    result = closed['result'].as_record()
    units = journal.units(run_id, ((EPISODE().grain_name, run_id),))
    trace = [(unit[2]['kind'], unit[2].get('tool') or unit[2].get('slot')) for unit in units]
    print('PAGE_UNITS', trace)
    print_inputs(store, units)
    assert trace[0] == ('tool', 'assess_content')
    requests = recorded_requests(tmp_path)
    retried, failed, reasons = rejection_facts(requests, units)
    print('PAGE_MODEL_CALLS', len(requests), 'REJECTED_RETRIED', json.dumps(retried), 'REJECTED_FAILED', failed)
    for name, reason in reasons:
        print('PAGE_REJECTION', name, json.dumps(reason)[:400])
    for unit in units:
        if unit[2]['kind'] == 'child':
            print('PAGE_CHILD_REPORT', unit[2]['slot'], json.dumps(unit[2]['report'])[:1500])
            print('PAGE_CHILD_SHEET_CLASS', unit[2]['message']['assignment']['sheet_class'])
        elif unit[2]['tool'] == 'update_sheet':
            print('PAGE_UPDATE_SHEET_OUTCOME', json.dumps(unit[2]['outcome'])[:3000])
    print('PAGE_RETURN', json.dumps(result))
    print('PAGE_CREDIT', result['credit'])
    print('PAGE_SCORES', json.dumps(result['finding']['scores']))
    print('PAGE_FEATURES', json.dumps(result['finding']['features']))
    assert journal.run_state(run_id)[1]['ended_by'] == 'yield_stop'
    assert failed == 0, ('a refused page answer was never followed by an accepted one', reasons)
    chunks = [unit for unit in units if unit[2]['kind'] == 'child' and unit[2]['slot'] == 'chunk']
    updates = [unit for unit in units if unit[2]['kind'] == 'tool' and unit[2]['tool'] == 'update_sheet']
    assert chunks and updates
    assert all(set(unit[2]['arguments']) == {'candidate_id'} for unit in chunks)      # the page names no type
    assert all(unit[2]['message']['assignment']['sheet_class'] == 'activity_rate' for unit in chunks)      # it hands the claim's class
    assert EPISODE.return_form.select(('sheet_state_refs',)).admit(result, 'return') == result
    assert set(result) == {'credit', 'finding', 'sheet_state_refs'}
    assert set(result['finding']) == {'scores', 'features'}      # no raw record, no grader, no leaf record
    assert 0 <= result['credit'] <= 1
    scores = result['finding']['scores']
    assert scores and all(score['target_id'] == 'thdf' for score in scores)
    features = result['finding']['features']
    assert any(item['target_id'] == 'thdf' and item['assertion_ref'] == world['proposed'] and item['experiments'] >= 1 for item in features)      # bearing direct
    refs = result['sheet_state_refs']
    assert refs and len(set(refs)) == len(refs)
    assert refs == updates[-1][2]['outcome']['sheet_update']['sheet_state_refs']
    for ref in refs:
        held = json.loads(store.get_artifact(ref))
        row = held['row']
        print('PAGE_ROW', json.dumps(row)[:1500])
        for member in held['member_results']:
            print('PAGE_RESULT', json.dumps({name: member[name] for name in ('experiment_type', 'bearing', 'direction', 'log_ratio', 'weight', 'effect_support', 'measured_effect', 'effect_unit', 'direction_field_support', 'statement')}))
            assert member['sheet'] == 'activity_rate' and member['experiment_type'] == 'spectro_direct' and member['bearing'] == 'direct'
            assert member['direction'] in ('supports', 'neutral') and member['direction'] != 'opposes'      # a stated rate never opposes
            assert member['direction'] != 'supports' or 0 < member['log_ratio'] <= 1.2      # QUALITATIVE_LOG_RATIO['spectro_direct']
            assert 0 <= member['weight'] <= 1
        assert row['sheet'] == 'activity_rate' and row['assertion_ref'] == world['proposed']
    calls = len(list((tmp_path / 'model_calls').glob('call-*')))
    again = asyncio.run(resume(registry, run_id=run_id, journal=journal,
                               collaborators=world['collaborators']).run())['result'].as_record()
    assert again == result
    assert len(list((tmp_path / 'model_calls').glob('call-*'))) == calls
    store.close()
