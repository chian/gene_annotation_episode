"""The real model on the report leaf (selected only with ``-m model_run``): the episode is linked directly on a real
published passage read in document order, window after window, and run to its yield stop.

The source is the real SPR paragraph of Bowman et al., Cell 2008 (PMC2745220; ``spr_passages.popz_chunk``, the one the
chunk and the page tests read) padded by its real neighbours in the paper: the paragraph before it (the three approaches,
the E. coli expression system) and the paragraph after it (the mobility shift assays), joined by the newlines of the
paper's text ``spr_passages.PRIMARY``. The page test pads the same paragraph with placeholder text; here the padding is
the paper's own. The commission names the windows to read in document order (``windows``): from byte 0, ``WINDOW`` bytes
each (``fixed_windows``), which makes two windows: the first
holds the paragraph before and the start of the SPR paragraph, the second the rest of the SPR paragraph (its KD sentence
whole) and the paragraph after. The experiment type is ``spr``.

Pass: the run ends by the yield estimator; no rejection is left unrecovered (a refused answer asked again and accepted is
normal); every accepted call was shown the text of its window, in order, each once; there is a standing leaf record of every
window; every stated quote of the type form and of the identity block occurs exactly once in its window; the window that
holds the SPR result names PopZ as the molecule tested, so its identity target is stated and is PopZ."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import (
    spr_passages)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from ...chunk.tests.leaf_world import SETTINGS, held_world
from ...chunk.tests.test_extraction_model_run import (
    check_identity, no_unrecovered_rejection, quote_span, rejection_counts, type_answer)
from ..episode import SourceCoverageImprovement
from ..task import TEXT

PATH = SourceCoverageImprovement.binding_path
WINDOW = 2200
KD_SENTENCE = 'we determined the equilibrium dissociation constant for the interaction between ParB and PopZ to be 20 nanomolar'


def popz_report_world(directory):
    """The Store holding the SPR paragraph between its real neighbouring paragraphs as the source's text, and the report's
    entry input: reading from byte 0 in windows of ``WINDOW`` bytes of the 'text' representation."""
    paper = spr_passages.PRIMARY.read_text(encoding='utf-8')
    paragraph = spr_passages.popz_chunk()[0]
    start = paper.index(paragraph)
    before = paper.rindex('\n', 0, start - 1) + 1                       # the start of the paragraph before
    after = paper.index('\n', start + len(paragraph) + 1)               # the end of the paragraph after
    text = paper[before:after]
    world = held_world(directory, text, 0, WINDOW, name='report', experiment_type='spr')
    assignment = world['input']['assignment']
    del assignment['offset'], assignment['limit']
    assignment.update({'representation': 'text', 'windows': fixed_windows(text.encode('utf-8'), WINDOW)})
    return world, text


def fixed_windows(content, limit):
    """Consecutive windows of ``limit`` bytes from byte 0 to the end of ``content``, each end moved forward out of a UTF-8
    character it would cut: ``[[start, end], ...]``."""
    windows, start = [], 0
    while start < len(content):
        end = min(start + limit, len(content))
        while end < len(content) and content[end] & 0xC0 == 0x80:
            end += 1
        windows.append([start, end])
        start = end
    return windows


@pytest.mark.model_run
def test_the_real_popz_paragraph_with_its_neighbours_is_read_window_by_window(tmp_path):
    world, text = popz_report_world(tmp_path)
    content = text.encode('utf-8')
    spans = [tuple(window) for window in world['input']['assignment']['windows']]
    kd_at = content.index(KD_SENTENCE.encode())
    kd_window = [index for index, (start, end) in enumerate(spans) if start <= kd_at and kd_at + len(KD_SENTENCE) <= end]
    print('SOURCE BYTES', len(content), 'WINDOWS', spans, 'KD SENTENCE IN WINDOW', kd_window)
    assert len(spans) >= 2 and len(kd_window) == 1                     # the precondition of the test's design
    run_id = 'a105-report-popz-real'
    journal = RunJournal(world['directory'] / 'journal.sqlite3')
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), world['directory'] / 'model_calls', world['directory']),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    run = link(BindingRegistry([SourceCoverageImprovement()]), PATH, world['input'], run_id=run_id, journal=journal,
               collaborators=collaborators)
    result = asyncio.run(run.run())['result'].as_record()
    path = tuple(tuple(step) for step in journal.episodes(run_id)[0]['path'])
    calls = journal.model_calls(run_id, path)
    units = [row[2] for row in journal.units(run_id, path)]
    state = journal.run_state(run_id)[1]
    print('ENDED', state)
    print('MODEL CALLS', len(calls), 'UNITS', len(units))
    retried, failed, details = rejection_counts(calls, units)
    print('REJECTED_RETRIED', retried, 'REJECTED_FAILED', failed)
    for detail in details:
        print('REJECTED DETAIL', json.dumps(detail)[:600])
    print('RETURN', json.dumps(result))
    print('CREDIT', result['credit'], 'FINDING', result['finding'])
    assert state['ended_by'] == 'yield_stop'
    assert SourceCoverageImprovement.return_form.select(('record_refs',)).admit(result, 'return') == result
    accepted = no_unrecovered_rejection(calls, units)
    for index, call in enumerate(accepted):                            # accepted call k is unit k, the k-th window
        start, end = spans[index]
        window = content[start:end].decode('utf-8')
        assert call['request']['context'][TEXT] == window              # the model was shown the text of its window
        answer = type_answer(call)
        stated = sorted(name for name in answer if answer[name]['status'] == 'stated')
        print('WINDOW', index, (start, end), 'STATED FIELDS', stated)
        for name in stated:
            item = answer[name]
            print('STATED', name, item.get('value'), item.get('unit'), 'SUPPORT=' + str(item.get('support')), repr(item['quote']))
            assert quote_span(window, item['quote']) is not None, (index, name, 'the quote must occur exactly once in the window')
        shown = {**world, 'input': {**world['input'], 'assignment': {**world['input']['assignment'],
                                                                     'offset': start, 'limit': end - start}}}
        keys = check_identity(shown, call)                             # identity quotes occur once in the window, vocabulary
        if (start, end) == spans[kd_window[0]]:
            assert keys['target_id'] == spr_passages.REAL_EXPECTED_TARGET, ('the SPR window names PopZ', keys['target_id'])
    records = [json.loads(world['store'].get_artifact(ref)) for ref in result['record_refs']]
    for record in records:
        print('LEAF RECORD', record['experiment_ref'], 'TARGET', record.get('target_id'), 'PARTNER', record.get('partner_id'))
    assert sorted(record['experiment_ref'].rsplit(':', 1)[1] for record in records) == sorted(
        str(start) + '-' + str(end) for start, end in spans)            # one standing leaf record per window
    world['store'].close()
