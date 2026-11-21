"""The real model on the table leaf (selected only with ``-m model_run``): the episode is linked directly on a real
published binding table and run to its yield stop.

The table is Table 2 of Rajagopalan et al., 'Studies of IscR reveal a unique mechanism for metal-dependent regulation of
DNA binding specificity', Nat Struct Mol Biol 2013;20(6):740-747 (PMC3676455, doi 10.1038/nsmb.2568), as the PMC text in
``research/.../template_a105_binding_002/iscr_3676455_primary.txt`` gives it (the folder of the real PopZ paper the chunk
test reads): the title, the column headings (IscR variant; Binding affinity (Kd) nM; Hill slope; Maximum anisotropy; %
wild-type binding activity), one row per variant with its Kd and standard deviation, and the footnotes (fluorescence
anisotropy isotherms, a four-parameter Hill fit, the average of at least three independent experiments). The source is
the whole primary text; the commissioned window is the table, from 'Table 2.' to the end of its footnote d. The
experiment type is ``fp`` (the Kd values come from fluorescence anisotropy binding isotherms).

Pass: the run ends by the yield estimator; no rejection is left unrecovered (a refused answer asked again and accepted is
normal); there is a standing leaf record of the table's window; every stated quote of the type form and of the identity
block occurs exactly once in the table; the table names IscR, so the identity target is stated and is IscR."""
import asyncio
import json

import pytest

from episode_runtime import BindingRegistry, RunJournal, link
from gene_annotation_episode.episodic_workflow.episode_support.literature.forms.experimental_activity_evidence.tests import (
    spr_passages)
from gene_annotation_episode.model_provider import ModelProvider, load_config

from ...chunk.tests.leaf_world import SETTINGS, held_world
from ...chunk.tests.test_extraction_model_run import (
    check_identity, check_named, fill_calls, no_unrecovered_rejection, quote_span, rejection_counts, type_answer)
from ..episode import TableEvidenceExtraction
from ..task import TEXT

PATH = TableEvidenceExtraction.binding_path
SOURCE = spr_passages.PRIMARY.parent / 'iscr_3676455_primary.txt'
TABLE_FIRST, TABLE_LAST = 'Table 2.\nAlanine substitutions', 'for each variant.'
EXPECTED_TARGET = 'iscr'


def iscr_table_world(directory):
    """The Store holding the real primary text as the source's text, and the table's entry input: the byte window of
    Table 2, read from the 'text' representation."""
    text = SOURCE.read_text(encoding='utf-8')
    start = text.index(TABLE_FIRST)
    end = text.index(TABLE_LAST, start) + len(TABLE_LAST)
    offset = len(text[:start].encode('utf-8'))
    world = held_world(directory, text, offset, len(text[start:end].encode('utf-8')), name='table', experiment_type='fp')
    world['input']['assignment']['representation'] = 'text'
    return world, text[start:end]


@pytest.mark.model_run
def test_the_real_iscr_kd_table_is_read_by_the_table_leaf(tmp_path):
    world, table = iscr_table_world(tmp_path)
    run_id = 'a105-table-iscr-real'
    journal = RunJournal(world['directory'] / 'journal.sqlite3')
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), world['directory'] / 'model_calls', world['directory']),
                     'continuation': {PATH: SETTINGS}, 'services': {}}
    run = link(BindingRegistry([TableEvidenceExtraction()]), PATH, world['input'], run_id=run_id, journal=journal,
               collaborators=collaborators)
    result = asyncio.run(run.run())['result'].as_record()
    path = tuple(tuple(step) for step in journal.episodes(run_id)[0]['path'])
    every_call = journal.model_calls(run_id, path)
    calls = fill_calls(every_call)             # the unit's fills; the naming calls are checked by check_named
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
    assert TableEvidenceExtraction.return_form.select(('record_refs',)).admit(result, 'return') == result
    accepted = no_unrecovered_rejection(calls, units)
    for call in accepted:
        assert call['request']['context'][TEXT] == table          # the model was shown exactly the commissioned table
        answer = type_answer(call)
        stated = sorted(name for name in answer if answer[name]['status'] == 'stated')
        print('STATED FIELDS', call['position'], stated)
        for name in stated:
            item = answer[name]
            print('STATED', name, item.get('value'), item.get('unit'), 'SUPPORT=' + str(item.get('support')), repr(item['quote']))
            assert quote_span(table, item['quote']) is not None, (name, 'the quote must occur exactly once in the table')
        keys = check_identity(world, call)                         # identity quotes occur once, vocabulary, names in quotes
        assert keys['target_id'] is not None and EXPECTED_TARGET in keys['target_id'], ('the table names IscR', keys['target_id'])
    records = [json.loads(world['store'].get_artifact(ref)) for ref in result['record_refs']]
    window = str(world['input']['assignment']['offset']) + '-' + str(world['input']['assignment']['offset'] + len(table.encode('utf-8')))
    check_named(world, every_call, records)                        # the leaf was handed the sheet class and named fp
    for record in records:
        print('LEAF RECORD', record['experiment_ref'], 'TARGET', record.get('target_id'), 'PARTNER', record.get('partner_id'))
    assert [record['experiment_ref'].rsplit(':', 1)[1] for record in records] == [window]   # one standing record of the table
    world['store'].close()
