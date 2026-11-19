"""The Store under custody: what a tool's ``ctx.store`` offers and refuses, transactions and their receipts, the
reasoning commit and the inventories limited to held records, and work tables. Real Store, journal and runner."""
import json

import pytest

from episode_runtime import CustodyError, TableDeclaration, WorkTableError
from episode_runtime.work_tables import WorkRows

from .probe_world import again, child, outcomes, probe_path, run, tool, world  # noqa: F401 - ``world`` is the fixture
from .sheet_library import SHEET


def test_the_scoped_store_reads_held_records_refuses_the_rest_and_receipts_its_writes(world):
    run(world, 'store', [tool('scoped', held=world['subject'], unheld=world['unrelated'])])
    outcome = outcomes(world, 'store')[0]
    assert outcome['outcome']['held'] == 'GeneX' and outcome['outcome']['unheld'] == 'refused'
    assert outcome['outcome']['opened_artifact'] == {'name': 'GeneX', 'carries_a_path': False, 'writable': False}
    assert outcome['outcome']['raw_store_offered'] == [] and outcome['outcome']['admission_offered'] == []
    assert outcome['outcome']['context_has_records'] is False     # one operation set, under ``ctx.store``
    written = outcome['outcome']['written']
    assert outcome['produced'] == [written]
    receipt = [row for row in world['journal'].receipts('store', probe_path('store')) if row['ref'] == written][0]
    assert receipt['how'] == 'produced' and receipt['unit'] == 0


def test_a_rolled_back_transaction_leaves_no_receipt_and_a_committed_one_is_receipted_on_commit(world):
    result = run(world, 'rollback', [tool('transactions')])
    outcome = outcomes(world, 'rollback')[0]
    done = outcome['outcome']
    assert done['held_inside'] == [True, True] and done['read_inside'] == 'probe'
    assert done['held_after_rollback'] == [False, False] and done['read_after_rollback'] == 'refused'
    assert done['inner_held_before_outer_ends'] is True and done['inner_held_after_outer_rollback'] is False
    assert done['kept_record_artifact'] == done['kept'][0]
    assert done['kept_listed'] == [done['kept'][1]] and done['kept_count'] == 1
    # Only what was committed is produced, receipted and in the unit's produced list.
    assert outcome['produced'] == done['kept']
    produced = [row['ref'] for row in world['journal'].receipts('rollback', probe_path('rollback'))
                if row['how'] == 'produced']
    assert produced == done['kept']
    assert result['result'].as_record()['produced'] == [done['kept']]
    store = world['store']
    assert store.get(done['kept'][1])['record_type'] == 'source'
    for ref in (done['lost'][1], done['inner']):                # the Store rolled these back
        with pytest.raises(Exception, match='unknown'):
            store.get(ref)


@pytest.fixture
def problem(world):
    """A real problem in the Store, a source held by the Episode, and a reasoning payload citing it."""
    store = world['store']
    target, = store.create_problem(raw_sequence='MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ', molecule='protein')['subject_refs']
    text = 'The protein binds zinc. The assay was positive.'
    artifact = store.artifact(text, 'text/plain')
    source = store.put('source', {'provider': 'test', 'accession': 'X1', 'uri': None, 'artifact_ref': artifact,
                                  'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None},
                       origin='external')
    quote = 'protein binds zinc'
    anchor = {'source_ref': source['id'], 'artifact_ref': artifact, 'start': text.index(quote),
              'end': text.index(quote) + len(quote)}
    payload = {name: [] for name in ('structural_proposals', 'terms', 'source_subjects', 'observations',
                                     'hypotheses', 'assessments', 'annotation_updates')}
    payload['terms'] = [{'alias': 'zinc', 'label': 'zinc', 'term_type': 'chemical', 'source_ref': source['id'],
                         'anchor': anchor}]
    payload['hypotheses'] = [{'alias': 'h', 'subject_refs': [target], 'predicate': 'binds',
                              'value': {'type': 'term_ref', 'ref': '@zinc'}, 'context_refs': []}]
    # A term another Episode would have committed: in the Store and in scope, but not held by the probe.
    other = 'assay was positive'
    foreign = {**payload, 'hypotheses': [], 'terms': [{
        'alias': 'assay', 'label': 'assay', 'term_type': 'chemical', 'source_ref': source['id'],
        'anchor': {**anchor, 'start': text.index(other), 'end': text.index(other) + len(other)}}]}
    committed = store.commit_reasoning(foreign, {'subject_refs': [target]}, 'committed-by-another-episode')
    assert committed['status'] == 'completed', committed
    return {'target': target, 'source': source['id'], 'artifact': artifact, 'payload': payload,
            'foreign': committed['record_refs'][0]}


def test_a_reasoning_commit_and_the_inventories_through_the_scoped_store(world, problem):
    held = {'input_refs': [problem['target']], 'held_refs': [problem['source'], problem['artifact']]}
    run(world, 'reason', [tool('reason', input_refs=[problem['target']], payload=problem['payload'],
                               unheld=problem['foreign'])], assignment=held)
    outcome = outcomes(world, 'reason')[0]
    done, store = outcome['outcome'], world['store']
    assert done['status'] == 'completed' and done['errors'] == [] and done['same_again'] is True
    term, hypothesis = done['record_refs']
    assert [store.get(ref)['record_type'] for ref in done['record_refs']] == ['term', 'hypothesis']
    assert outcome['produced'] == done['record_refs']             # every record the commit created is held
    # The Store has two terms in scope; the Episode is shown only the one it holds, by every route.
    assert {row['id'] for row in store.list('term')} == {term, problem['foreign']}
    assert done['queried_terms'] == done['view_terms'] == done['listed_terms'] == [term]
    assert done['query_total'] == 1
    assert done['subset'] == done['record_refs'] and problem['foreign'] not in done['subset']
    assert done['view_subjects'] == done['problem_subjects'] == done['targets'] == [problem['target']]
    assert done['subjects'] == [problem['target']]
    assert done['referenced_terms'] == [term] and done['counted_terms'] == 1 and store.count('term') == 2
    assert done['in_scope'] == [True, True] and done['required_kinds'] == ['term', 'hypothesis']
    assert done['current_accounts'] == [] and done['current_account_count'] == 0
    assert done['current_assessments'] == []


def test_registering_material_is_a_receipted_write(world, problem):
    held = {'held_refs': [problem['source'], problem['artifact']]}
    other = world['store'].put('source', {'provider': 'test', 'accession': 'X2', 'uri': None,
                                          'artifact_ref': problem['artifact'], 'text_ref': problem['artifact'],
                                          'request_ref': None, 'version': None, 'retrieved_at': None},
                               origin='external')['id']
    run(world, 'material', [tool('material', source_ref=problem['source'], text='a new note', unheld=other)],
        assignment=held)
    outcome = outcomes(world, 'material')[0]
    done = outcome['outcome']
    assert done['reused_source'] == problem['source'] and done['fresh_bytes'] == 'a new note'
    assert done['unheld_source'] == 'refused'
    # Held as produced: both material records, and the source and artifact the second call created.
    assert outcome['produced'] == [done['reused'], done['fresh'], done['fresh_source'], done['fresh_artifact']]
    assert done['materials'] == sorted([done['reused'], done['fresh']])


def test_the_account_owner_of_a_reasoning_commit_is_the_run_and_the_episode(world, problem):
    """Two Episodes of the same binding under the same key (the child ``nested_0`` of two runs that share the Store)
    commit an interpretation account for the same subject and scope: each gets its own account lineage, at
    revision 1."""
    store = world['store']
    hypothesis = store.put('hypothesis', {'subject_refs': [problem['target']], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='reasoning')['id']
    payload = {**problem['payload'], 'terms': [], 'hypotheses': [], 'interpretation_accounts': [{
        'alias': 'account', 'subject_ref': problem['target'], 'footprint_kind': 'localized',
        'coherent_sets': [{'interpretations': [{'hypothesis_ref': hypothesis, 'disposition': 'unresolved',
                                                'assessment_refs': []}], 'context_refs': []}],
        'alternative_refs': [], 'resolution': 'unresolved', 'expected_revision': 0}]}
    held = {'input_refs': [problem['target']], 'held_refs': [hypothesis]}
    accounts = []
    for run_id in ('owner_a', 'owner_b'):
        run(world, run_id, [child('nested', plan=[tool('reason', input_refs=[problem['target']], payload=payload,
                                                       unheld=problem['foreign'])])], assignment=held)
        done = outcomes(world, run_id, (*probe_path(run_id), ('probe', 'nested_0')))[0]['outcome']
        assert done['status'] == 'completed' and done['errors'] == [], done
        accounts.append(store.get(done['record_refs'][0]))
    assert [row['record_type'] for row in accounts] == ['interpretation_account'] * 2
    assert [row['revision'] for row in accounts] == [1, 1] and accounts[0]['id'] != accounts[1]['id']


def test_a_scope_over_a_subject_the_episode_does_not_hold_is_refused(world, problem):
    run(world, 'unheld_scope', [tool('unheld_scope', input_refs=[problem['target']])])
    assert outcomes(world, 'unheld_scope')[0]['outcome'] == {
        'reasoning_view': 'refused', 'query_records': 'refused', 'scope_dimension_segments': 'refused',
        'get_input': 'refused', 'problem_subjects': []}


def test_a_sheet_kept_as_a_work_table_is_produced_held_passed_and_credited_under_custody(world):
    """A child Episode writes two cells through a library function; it holds the rows as produced, returns them in
    its result, and the parent then holds them, reads them and is credited for them; a third Episode does not.
    (Credit here is the held cells of the sheet plus one per plan step, toward the target each commissioner names:
    2 cells and 2 steps for the child, 2 cells and 3 steps for the parent.)"""
    subject = world['subject']
    cells = [['a1', 3], ['a2', 5]]
    rule = {'rule': 'cells', 'sheet': 's', 'per_step': 1}
    inner = [tool('sheet', sheet='s', cells=cells, source_ref=subject), tool('read_cells', sheet='s')]
    plan = [tool('read_cells', sheet='s'),
            child('nested', plan=inner, credit=rule, controller={'kind': 'completion', 'target': 4}),
            tool('read_cells', sheet='s')]
    result = run(world, 'sheet', plan, credit=rule, controller={'kind': 'completion', 'target': 5})
    journal, top = world['journal'], probe_path('sheet')
    nested = (*top, ('probe', 'nested_1'))
    written = journal.units('sheet', nested)[0][2]
    rows = written['outcome']['rows']
    assert [(row['cell'], row['value'], row['revision'], row['unit']) for row in rows] == [('a1', 3, 1, 0),
                                                                                           ('a2', 5, 1, 0)]
    assert all(row['id'].startswith('row_') for row in rows) and written['outcome']['read_by_get'] == 'probe_sheet'
    assert written['produced'] == [row['id'] for row in rows]
    assert rows[0]['operation_key'] == journal.attempts('sheet', nested)[0][2]
    # Credit of the writing Episode counts the cells it holds: 2 after its first unit (plus one per step).
    assert [value['credit'] for _, value, _, _ in journal.units('sheet', nested)] == [3.0, 4.0]
    assert [(row['ref'], row['how']) for row in journal.receipts('sheet', nested) if row['ref'].startswith('row_')] \
        == [(rows[0]['id'], 'produced'), (rows[1]['id'], 'produced')]
    before, returned, after = outcomes(world, 'sheet')
    assert before['outcome']['cells'] == []                       # not held before the child returned them
    assert returned['report'] == {'slot': 'nested', 'n': 2, 'returned_cells': [3, 5]}
    assert after['outcome']['cells'] == [['a1', 3, False], ['a2', 5, False]]   # held now; written by the child
    assert [value['credit'] for _, value, _, _ in journal.units('sheet', top)] == [1.0, 4.0, 5.0]
    assert returned['result']['credit'] == 4.0 and result['result'].as_record()['credit'] == 5.0
    assert [(row['how'], row['from']) for row in journal.receipts('sheet', top) if row['ref'].startswith('row_')] \
        == [('returned', nested), ('returned', nested)]
    assert result['result'].as_record()['row_refs'] == []          # the parent wrote none itself
    # Another run does not hold them: it sees no cell, and a named row is refused.
    run(world, 'other', [tool('read_cells', sheet='s', unheld=[rows[0]['id']])])
    assert outcomes(world, 'other')[0]['outcome'] == {'cells': [], 'unheld': 'refused'}


def test_a_sheet_write_that_rolls_back_leaves_no_row_and_a_rewrite_makes_the_next_revision(world):
    subject = world['subject']
    plan = [tool('sheet', sheet='s', cells=[['a1', 1]], source_ref=subject, abort=True),
            tool('sheet', sheet='s', cells=[['a1', 1]], source_ref=subject),
            tool('sheet', sheet='s', cells=[['a1', 1]], source_ref=subject),
            tool('sheet', sheet='s', cells=[['a1', 2]], source_ref=subject)]
    run(world, 'revisions', plan)
    aborted, first, same, changed = outcomes(world, 'revisions')
    assert aborted['outcome'] == {'aborted': True, 'held_cells': [], 'held_refs': [False]}
    assert aborted['produced'] == []
    row = first['outcome']['rows'][0]
    assert (row['revision'], row['unit']) == (1, 1) and first['produced'] == [row['id']]
    assert same['outcome']['rows'][0] == row                       # equal values: the same row, unchanged
    newer = changed['outcome']['rows'][0]
    assert (newer['id'], newer['revision'], newer['unit'], newer['value']) == (row['id'], 2, 3, 2)
    assert changed['outcome']['held_cells'] == [['a1', 2]]
    assert WorkRows(world['store']).row(row['id'])['value'] == 2


def test_a_sheet_row_may_name_only_records_the_writer_holds_and_must_match_its_declaration(world):
    with pytest.raises(CustodyError, match='record_not_held'):
        run(world, 'unheld_ref', [tool('sheet', sheet='s', cells=[['a1', 1]], source_ref=world['unrelated'])])
    rows = WorkRows(world['store'])
    rows.declare(SHEET)
    with pytest.raises(WorkTableError, match='work_table_declaration_differs:probe_sheet'):
        rows.declare(TableDeclaration('probe_sheet', ('sheet', 'cell'), ('sheet',)))
    with pytest.raises(WorkTableError, match='work_table_row_must_have_exactly_its_columns'):
        rows.write(SHEET, ('run', 'episode'), 0, 'op', {'sheet': 's'})
    with pytest.raises(WorkTableError, match='work_table_columns_are_system_columns:bad:id'):
        TableDeclaration('bad', ('id', 'value'), ('id',))
    with pytest.raises(WorkTableError, match='work_table_key_and_record_refs_must_be_columns'):
        TableDeclaration('bad', ('value',), ('other',))


def test_a_row_named_in_the_entry_assignment_must_exist(world):
    with pytest.raises(CustodyError, match='entry_record_not_in_store:row_missing'):
        run(world, 'missing_row', [], assignment={'held_refs': ['row_missing']})
    with pytest.raises(CustodyError, match='entry_record_not_in_store:artifact_missing'):
        run(world, 'missing_record', [], assignment={'held_refs': ['artifact_missing']})
