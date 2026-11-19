"""Custody on the documented operations of ``ctx.store`` and ``records`` (third audit, T4, T6 to T8, T11 to T13):
a write names only what its unit can read, parsing is a receipted write, scope arithmetic and coverage read only
held records, the read-only reader has the inventories credit needs, a run id is claimed in the Store, an inventory
has no silent page, and an artifact is opened without its path. Real Store, journal and runner."""
import asyncio
import json

import pytest

from episode_runtime import JournalError, LinkError, RecordReader, RunJournal, TableDeclaration, link
from episode_runtime.recording import Custody, UnitPosition
from episode_runtime.store_ledger import StoreLedger
from episode_runtime.store_scope import named_references
from episode_runtime.work_tables import WorkRows
from method_loop import EpisodeRef

from .probe_world import (again, collaborators, entry, outcomes, probe_path, registry, run, tool,  # noqa: F401
                          world)
from .test_scoped_store import problem  # noqa: F401 - a fixture

FASTA = '>s1 first\nMKTAYIAKQRQISFVKSHFSRQ\n>s2 second\nMKKLLPTAAAGLLLLAAQPAMA\n'
REFUSED = 'CustodyError: record_not_held'


def reader(world, run_id, path):
    """The read-only reader of the Episode at ``path``, built as the runner builds it."""
    rows = WorkRows(world['store'])
    custody = Custody(world['journal'], StoreLedger(world['store'], rows), run_id, path,
                      EpisodeRef(run_id, path).episode_id, UnitPosition(world['journal'], run_id, path))
    return RecordReader(world['store'], custody, rows)


def test_a_write_may_name_only_records_its_unit_can_read(world):
    """A unit that cannot read an artifact cannot write a source record naming it, nor register material from a
    source it does not hold: the write raises and leaves nothing behind."""
    store = world['store']
    foreign = store.put('source', {'provider': 'test', 'accession': 'F1', 'uri': None,
                                   'artifact_ref': world['unrelated'], 'text_ref': world['unrelated'],
                                   'request_ref': None, 'version': None, 'retrieved_at': None},
                        origin='external')['id']
    run(world, 'names', [tool('name_unheld', unheld=world['unrelated'], unheld_source=foreign)])
    outcome = outcomes(world, 'names')[0]
    done = outcome['outcome']
    for call in ('read', 'put', 'register'):
        assert done[call]['raised'].startswith(REFUSED), (call, done[call])
    assert done['holds_after'] is False and done['put_naming_its_own_artifact'] == {'ok': True}
    assert [row['id'] for row in store.list('source') if row['artifact_ref'] == world['unrelated']] == [foreign]
    assert store.list('material') == []
    assert [store.get(ref)['record_type'] for ref in outcome['produced']] == ['artifact', 'source']


def test_a_reasoning_commit_may_name_only_held_records(world, problem):  # noqa: F811
    """An Episode that holds the problem subject but not the source cannot commit a term anchored in that source
    (the commit would read the quoted span of the source's artifact for it)."""
    store, payload = world['store'], problem['payload']
    step = [tool('reason_plain', payload=payload, input_refs=[problem['target']])]
    run(world, 'unheld_source', step, assignment={'input_refs': [problem['target']]})
    outcome = outcomes(world, 'unheld_source')[0]
    assert outcome['outcome']['raised'].startswith(REFUSED) and outcome['produced'] == []
    assert {row['id'] for row in store.list('term')} == {problem['foreign']}
    run(world, 'held_source', step, assignment={'input_refs': [problem['target']],
                                                'held_refs': [problem['source'], problem['artifact']]})
    done = outcomes(world, 'held_source')[0]
    assert done['outcome']['status'] == 'completed' and done['produced'] == done['outcome']['record_refs']
    assert store.get(done['produced'][0])['anchor']['quote'] == 'protein binds zinc'


def test_the_references_a_record_names_follow_the_stores_own_rule(world, problem):  # noqa: F811
    """``named_references`` (what a write must hold) names what the Store's own walk names, for stored records."""
    store = world['store']
    rows = [store.get(problem['source']), store.get(problem['foreign']), store.problem(),
            store.get_input(problem['target']), problem['payload']]
    for row in rows:
        assert list(named_references(row)) == list(store._refs(row))
    assert list(named_references({'source_ref': None, 'context_refs': 'abc', 'x': [{'ref': 7}]})) == []


def test_parsing_material_is_a_receipted_write_and_the_episode_reads_what_it_parsed(world):
    run(world, 'parse', [tool('parse', fasta=FASTA)])
    outcome, store = outcomes(world, 'parse')[0], world['store']
    done = outcome['outcome']
    assert (done['status'], done['valid_records'], done['errors'], done['members']) == ('completed', 2, 0, 2)
    assert done['holds'] == [True, True] and done['got_parse'] == 'parse_attempt'
    assert done['member_sequence'] == 'MKTAYIAKQRQISFVKSHFSRQ'
    assert done['header_text'] == done['header_artifact_text'] and 's1' in done['header_text']
    assert done['reference_sequence'] == 'MKKLLPTAAAGLLLLAAQPAMA'
    assert done['listed'] == {'parse_attempt': [done['parse_ref']], 'collection': [done['collection_ref']],
                              'reference': [done['reference']]}
    assert done['parsed_again_is_the_same'] is True
    kinds = [store.get(ref)['record_type'] for ref in outcome['produced']]
    assert {'material', 'source', 'artifact', 'parse_attempt', 'collection', 'reference', 'context',
            'collection_member'} == set(kinds)
    receipts = [row['ref'] for row in world['journal'].receipts('parse', probe_path('parse'))
                if row['how'] == 'produced']
    assert receipts == outcome['produced']
    assert [ref for ref, _, abandoned in StoreLedger(store, WorkRows(store)).receipts('parse', probe_path('parse'))
            if not abandoned] == receipts


def test_a_passed_material_is_parsed_with_the_records_it_names_and_a_collection_gives_its_members(world):
    store = world['store']
    material = store.register_material(data=FASTA.encode(), name='passed', format='fasta', molecule='protein')
    parsed = store.parse_material(material['id'])
    member = store.material_members(parsed['collection_ref'])['members'][0]['id']

    def tried(run_id, held, **arguments):
        run(world, run_id, [tool('parse_passed', material=material['id'], **arguments)],
            assignment={'held_refs': held})
        return outcomes(world, run_id)[0]
    alone = tried('material_alone', [material['id']])
    assert alone['outcome']['parse']['raised'].startswith(REFUSED) and alone['produced'] == []
    named = tried('material_and_source', [material['id'], material['source_ref']])
    assert named['outcome']['parse'] == {'ok': parsed['id']}
    assert named['produced'][:2] == [parsed['id'], parsed['collection_ref']]
    nothing = tried('no_collection', [material['id']], member=member)
    assert nothing['outcome']['member']['raised'].startswith(REFUSED)
    collection = tried('collection_alone', [parsed['collection_ref']], member=member)
    assert collection['outcome']['member'] == {'ok': 'MKTAYIAKQRQISFVKSHFSRQ'}
    assert collection['outcome']['reference']['raised'].startswith(REFUSED)     # the collection names its material
    whole = tried('collection_and_names', [parsed['collection_ref'], material['id'], material['source_ref']],
                  member=member)
    assert store.get(whole['outcome']['reference']['ok'])['record_type'] == 'reference'


def test_scope_arithmetic_coverage_and_the_reference_filter_read_only_held_records(world, problem):  # noqa: F811
    arguments = {'unheld_input': problem['target'], 'unheld_record': problem['source']}
    run(world, 'unheld', [tool('scope_reads', held=world['subject'], held_inputs=[], **arguments)])
    done = outcomes(world, 'unheld')[0]['outcome']
    for call in ('validate_scope', 'validate_scope_segment', 'scope_contains', 'scope_covers',
                 'query_naming_an_unheld_record', 'query_naming_a_missing_record'):
        assert done[call]['raised'].startswith(REFUSED), (call, done[call])
    # The row the caller built is not trusted: the coverage is that of the stored record (an artifact has none).
    assert done['record_coverage_of_a_built_row'] == {'ok': []}
    run(world, 'held', [tool('scope_reads', held=problem['target'], held_inputs=[problem['target']], **arguments)],
        assignment={'input_refs': [problem['target']]})
    done = outcomes(world, 'held')[0]['outcome']
    assert done['validate_scope'] == {'ok': {'subject_refs': [problem['target']]}}
    assert done['scope_contains'] == {'ok': True}
    assert done['record_coverage_of_a_built_row']['ok'] == world['store'].coverage(problem['target']) != []
    # A reference the Episode does not hold is refused whether or not it exists.
    assert done['query_naming_an_unheld_record']['raised'].startswith(REFUSED)
    assert done['query_naming_a_missing_record']['raised'].startswith(REFUSED)


def test_credit_reads_the_current_inventories_through_the_read_only_reader(world, problem):  # noqa: F811
    """Credit asks, through ``records`` only, which interpretation accounts it holds are current
    (``iter_current_accounts``, ``is_current``, ``list``, ``count``, ``current_assessments``)."""
    store, target = world['store'], problem['target']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='reasoning')['id']

    def account(kind, revision):
        return {**problem['payload'], 'terms': [], 'hypotheses': [], 'interpretation_accounts': [{
            'alias': 'account', 'subject_ref': target, 'footprint_kind': kind,
            'coherent_sets': [{'interpretations': [{'hypothesis_ref': hypothesis, 'disposition': 'unresolved',
                                                    'assessment_refs': []}], 'context_refs': []}],
            'alternative_refs': [], 'resolution': 'unresolved', 'expected_revision': revision}]}
    plan = [tool('reason', input_refs=[target], payload=account('localized', 0), unheld=problem['foreign']),
            tool('reason', input_refs=[target], payload=account('whole_input_context', 1),
                 unheld=problem['foreign'])]
    run(world, 'current', plan, assignment={'input_refs': [target], 'held_refs': [hypothesis]},
        credit={'rule': 'current_accounts', 'per_step': 1}, controller={'kind': 'completion', 'target': 3.5})
    first, second = outcomes(world, 'current')
    assert first['outcome']['status'] == second['outcome']['status'] == 'completed', (first, second)
    old, new = first['outcome']['record_refs'][0], second['outcome']['record_refs'][0]
    assert [store.get(ref)['revision'] for ref in (old, new)] == [1, 2]
    # One current account and one held hypothesis after each unit (1.5): the superseded revision does not count.
    # (The rule adds one per plan step, toward the commissioner's target.)
    assert [value['credit'] for _, value, _, _ in world['journal'].units('current', probe_path('current'))] == [
        2.5, 3.5]
    records = reader(world, 'current', probe_path('current'))
    assert (records.is_current(old), records.is_current(new)) == (False, True)
    assert [row['id'] for row in records.list('interpretation_account')] == sorted([old, new])
    with pytest.raises(ValueError, match='revisioned_record_required'):
        records.is_current(hypothesis)
    assert records.reasoning_schema() == store.reasoning_schema()
    assert [name for name in ('put', 'artifact', 'commit_reasoning', 'register_material', 'create_problem',
                              'parse_material', 'material_header', 'material_reference', 'reclaim', 'transaction',
                              'read_snapshot', 'db', 'path', 'artifact_path') if hasattr(records, name)] == []
    assert not hasattr(records.table(TableDeclaration('t', ('a',), ('a',))), 'put')


def test_one_run_id_in_two_journals_over_one_store_is_refused(world):
    store, first = world['store'], world['journal']
    run(world, 'same', [tool('row_write', k='x', v=1)])
    row = outcomes(world, 'same')[0]['outcome']['row']
    other = RunJournal(world['tmp'] / 'journal_b.sqlite3')
    assert other.identity != first.identity
    with pytest.raises(LinkError, match='run_id_claimed_in_this_store_by_another_journal:same'):
        link(registry(), 'probe', entry(world, [tool('row_write', k='x', v=2)]), run_id='same', journal=other,
             collaborators=collaborators(world))
    with pytest.raises(JournalError, match='run_not_recorded:same'):
        other.entry('same')                                         # refused before the run was recorded
    stored = WorkRows(store).row(row)
    assert (stored['v'], stored['revision']) == (1, 1)
    # Another run id in the second journal is its own run with its own row; the first journal still resumes.
    asyncio.run(link(registry(), 'probe', entry(world, [tool('row_write', k='x', v=2)]), run_id='second',
                     journal=other, collaborators=collaborators(world)).run())
    theirs = other.units('second', probe_path('second'))[0][2]['outcome']
    assert theirs['row'] != row and theirs['before'] == [] and theirs['revision'] == 1
    assert again(world, 'same')['record'].units_consumed == 1
    assert RunJournal(world['tmp'] / 'journal_b.sqlite3').identity == other.identity


def test_an_inventory_returns_every_held_record_unless_a_page_is_asked_for(world):
    run(world, 'many', [tool('many', n=120)])
    assert outcomes(world, 'many')[0]['outcome'] == {'listed': 120, 'counted': 120, 'page': 10}


def test_a_read_that_follows_a_reference_needs_the_followed_record_held_too(world, problem):  # noqa: F811
    """Holding a record does not hold the records it names (owner decision T5, provisional). The Store's own read
    operations follow such names: a feature's parent subject, a reference's sequence artifact, an assessment's
    hypothesis and the subjects it names, a material's source and its artifact, a parse's material. Under custody
    each of those reads is refused unless the followed records are held too, and answers as the Store does when
    they are."""
    store, target = world['store'], problem['target']
    feature = store.put('feature', {'subject_ref': target, 'kind': 'protein_domain',
                                    'segments': [{'start': 2, 'end': 12}], 'strand': '+', 'context_refs': []},
                        origin='tool')['id']
    sequence = store.artifact('MKTAYIAKQR', 'text/x-sequence')
    reference = store.put('reference', {
        'reference_type': 'protein', 'source_ref': problem['source'], 'accession': 'R1', 'label': 'a reference',
        'sequence_ref': sequence, 'molecule': 'protein', 'length': 10, 'term_refs': [], 'context_refs': []},
        origin='external')['id']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='reasoning')['id']
    observation = store.put('observation', {
        'subject_refs': [target], 'source_subject_refs': [], 'kind': 'source_content', 'source_ref': problem['source'],
        'measurements': [], 'dependencies': [], 'anchor': None}, origin='external')['id']
    assessment = store.put('assessment', {
        'hypothesis_ref': hypothesis, 'observation_ref': observation, 'relation': 'strengthens',
        'applicability': 'direct', 'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
        'expected_revision': 0}, origin='reasoning')['id']
    material = store.register_material(data=FASTA.encode(), name='followed', format='fasta', molecule='protein')
    parsed = store.parse_material(material['id'])
    source = store.get(material['source_ref'])
    whole = [{'start': 0, 'end': 10}]
    calls = {'subject_length': ['subject_length', reference], 'reference_mapping': ['sequence_mapping', reference],
             'reference_segments': ['map_segments', reference, whole],
             'subject_unit': ['subject_unit', feature], 'subject_molecule': ['subject_molecule', feature],
             'coverage': ['coverage', feature], 'feature_mapping': ['sequence_mapping', feature],
             'has_exact_mapping': ['has_exact_mapping', feature], 'feature_segments': ['map_segments', feature, whole],
             'hypothesis_coverage': ['record_coverage', {'id': hypothesis}],
             'assessment_coverage': ['record_coverage', {'id': assessment}],
             'material_annotations': ['material_annotations', parsed['id']]}
    named = [feature, reference, hypothesis, assessment, parsed['id']]

    def tried(run_id, held, wanted, inputs=()):
        run(world, run_id, [tool('follow', calls=wanted)],
            assignment={'held_refs': held, 'input_refs': list(inputs)})
        return outcomes(world, run_id)[0]['outcome']
    # The named records alone: every read is refused at the first record it would follow.
    alone = tried('named_alone', named, calls)
    for label in calls:
        assert alone[label]['raised'].startswith(REFUSED), (label, alone[label])
    # The assessment was refused there for the subject its (held) hypothesis names; held alone it is refused for
    # the hypothesis.
    assert alone['assessment_coverage']['raised'].endswith(':' + target)
    lone = tried('assessment_alone', [assessment], {'assessment_coverage': calls['assessment_coverage']})
    assert lone['assessment_coverage']['raised'].startswith(REFUSED)
    assert lone['assessment_coverage']['raised'].endswith(':' + hypothesis)
    # A material without its source, and with its source but without the source's artifact.
    reading = {'material_read': ['material_read', material['id']]}
    assert tried('material_alone_read', [material['id']], reading)['material_read']['raised'].startswith(REFUSED)
    assert tried('material_and_source_read', [material['id'], source['id']],
                 reading)['material_read']['raised'].startswith(REFUSED)
    # With every followed record named as well, each read answers as the Store does.
    done = tried('named_and_followed', [*named, sequence, material['id'], source['id'], source['artifact_ref']],
                 {**calls, **reading}, inputs=[target])
    for label, (operation, *arguments) in {**calls, **reading}.items():
        assert done[label] == {'ok': json.loads(json.dumps(getattr(store, operation)(*(
            [store.get(arguments[0]['id'])] if operation == 'record_coverage' else arguments))))}, label
    assert done['subject_length'] == {'ok': 10} and done['subject_unit'] == {'ok': 'aa'}
    assert done['assessment_coverage'] == done['hypothesis_coverage'] == {'ok': store.coverage(target)}
    # A member is read through its collection: the one exception, because members are rows of the collection.
    member = store.material_members(parsed['collection_ref'])['members'][0]['id']
    through = tried('through_the_collection', [parsed['collection_ref']],
                    {'member': ['material_member', member], 'members': ['material_members', parsed['collection_ref']]})
    assert through['member']['ok']['sequence'] == 'MKTAYIAKQRQISFVKSHFSRQ' and through['members']['ok']['total'] == 2


def test_arithmetic_over_a_caller_built_value_reads_only_the_held_records_it_names(world, problem):  # noqa: F811
    """A context mask, a span and a mapping are values the caller builds; the Store reads the subjects they name to
    answer. Each named subject must be held."""
    target = problem['target']
    mask = {'subject_refs': [target]}
    calls = {'normalize_context_mask': ['normalize_context_mask', mask],
             'context_mask_identity': ['context_mask_identity', mask],
             'context_mask_subset': ['context_mask_subset', mask, mask],
             'context_mask_overlap': ['context_mask_overlap', mask, mask],
             'footprint_dimension': ['footprint_dimension', {'target_ref': target, 'start': 0, 'end': 5, 'unit': 'aa'}],
             'footprint_from_mapping': ['footprint_from_mapping', world['store'].sequence_mapping(target)]}
    run(world, 'unheld_values', [tool('follow', calls=calls)])
    refused = outcomes(world, 'unheld_values')[0]['outcome']
    for label in calls:
        assert refused[label]['raised'].startswith(REFUSED), (label, refused[label])
    run(world, 'held_values', [tool('follow', calls=calls)], assignment={'input_refs': [target]})
    answered = outcomes(world, 'held_values')[0]['outcome']
    assert answered['normalize_context_mask'] == {'ok': mask} and answered['context_mask_subset'] == {'ok': True}
    assert answered['footprint_dimension']['ok']['id'] == target
    assert answered['footprint_from_mapping'] == {'ok': world['store'].coverage(target)}
    assert all('ok' in answered[label] for label in calls), answered
