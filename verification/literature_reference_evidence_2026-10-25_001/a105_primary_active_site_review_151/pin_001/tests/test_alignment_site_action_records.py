"""Actual tool publications joined to saved own actions, without a model run.

Biopython/minimap2 fixtures execute tiny native jobs once per module and clone
their closed Store afterward. BLAST inputs are explicit offline synthetic API
documents published through the actual service binding. Journal calls construct
the host-boundary fixture; complete Workflow commissioning is tested separately.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.alignment_site_action_records import AlignmentSiteActionRecords
from gene_annotation_episode.alignment_site_returns import (
    alignment_site_fact_sources, requested_site_projections,
    project_site_action_return, validate_frozen_site_return,
)
from gene_annotation_episode.communication import plain, ReportBoundaryError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import MEDIA_TYPE, retain_tool_grading
from gene_annotation_episode.tools import ToolRegistry
from test_blast_result_views import published


REFERENCE = 'reference_site_rows'
BLAST = 'blast_hsp_column_rows'
RUN = 'alignment-custody-288'


def requested(source=REFERENCE, policy='all_own_completed_results', *, alignment=None,
              positions=None, window=None):
    fields = alignment_site_fact_sources()[source]['report_schema']
    group = fields['items']['properties']
    group['selection_policy'] = {'type': 'string', 'const': policy}
    if policy != 'all_own_completed_results':
        group['alignment_ref']['const'] = alignment
    selected = group['selection']['properties']
    if policy == 'matching_alignment_window':
        if source == REFERENCE:
            selected['kind'] = {'type': 'string', 'const': 'reference_window'}
        for key, value in window.items():
            selected[key]['const'] = value
    elif policy == 'matching_alignment_position_set':
        selected['kind'] = {'type': 'string', 'const': 'reference_positions'}
        selected['positions']['items']['enum'] = list(positions)
    return {'type': 'object', 'additionalProperties': False, 'required': ['selected'],
            'properties': {'selected': fields}}


def saved_context(case, schema, *, name='child_0', parent=None, role='scientific_process'):
    path = (('root', 'root'), (role, name))
    episode = EpisodeRef(RUN, path).episode_id
    request = {'message': {'scope': case.scope, 'episode_assignment': {}},
               'report_contract': {'measurements': {'schema': schema}}}
    case.journal.save('runtime_episodes', {'episode_id': episode,
        'path': canonical(path), 'request': canonical(request), 'initial_credit': 0., 'state': 'active'})
    case.receipts.bind(episode, parent)
    return BindingContext(RUN, episode, role, path, case.scope, {}, request)


def setup_case(store, tools, *, scope=None):
    journal = Journal(store, RUN)
    receipts = EpisodeReceipts(store, RUN)
    return SimpleNamespace(store=store, tools=tools, journal=journal, receipts=receipts,
        scope=store.validate_scope(scope),
        service=AlignmentSiteActionRecords(store, RUN, sequence_reader=tools._sequence))


def perform(case, context, index, tool, arguments, *, permitted=None, runtime_extra=None):
    key = f'{RUN}:{context.episode_id}:{index}'
    outcome = case.tools.execute(tool, arguments, scope=plain(context.scope),
        operation_key=key, permitted_record_refs=permitted)
    assert outcome['status'] in {'completed', 'partial'}, outcome
    case.journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
        'action': canonical({'kind': 'tool', 'tool': tool, 'arguments': arguments}),
        'result': canonical({**outcome, **(runtime_extra or {})}), 'credit': 0.})
    return outcome


def page(case, context, source=REFERENCE, *, after=None, limit=64, selection=None):
    projection = requested_site_projections(plain(context.request)['report_contract']['measurements']['schema'])[source]
    return case.service.own_action_results(context, source=source,
        selection=projection['selection'] if selection is None else selection,
        after_decision_index=after, limit=limit)


def project(case, context, source=REFERENCE):
    schema = plain(context.request)['report_contract']['measurements']['schema']
    fields = requested_site_projections(schema)[source]['fields']
    return [project_site_action_return(record, fields) for record in page(case, context, source)['records']]


def change_outcome(case, context, index, mutate):
    key = f'{RUN}:{context.episode_id}:{index}'
    saved = json.loads(case.store.db.execute('SELECT result FROM tool_operations WHERE operation_key=?', (key,)).fetchone()[0])
    mutate(saved)
    case.store.db.execute('UPDATE tool_operations SET result=? WHERE operation_key=?', (canonical(saved), key))
    case.store.db.execute('UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?',
        (canonical(saved), RUN, context.episode_id, index))
    return saved


def change_grading(case, context, index, source, mutate):
    """Explicit corruption fixture: create valid artifact hashes with wrong joins."""
    def rewrite(outcome):
        result = outcome['result']
        if source == BLAST:
            pointer = result['site_grading_artifact_ref']
            envelope = json.loads(case.store.get_artifact(pointer))
            mutate(envelope['grading'])
            result['site_grading_artifact_ref'] = retain_tool_grading(case.store,
                provider=envelope['provider'], native_artifact_ref=envelope['native_artifact_ref'],
                grading=envelope['grading'])
            return
        old_source = case.store.get(result['source_ref'])
        pointer, = [p for p in old_source['auxiliary_artifact_refs']
                    if case.store.get(p)['media_type'] == MEDIA_TYPE]
        envelope = json.loads(case.store.get_artifact(pointer))
        mutate(envelope['grading'])
        new_pointer = retain_tool_grading(case.store, provider=envelope['provider'],
            native_artifact_ref=envelope['native_artifact_ref'], grading=envelope['grading'])
        payload = {k:v for k,v in old_source.items() if k not in {'id', 'origin', 'record_type'}}
        payload['auxiliary_artifact_refs'] = [new_pointer if p == pointer else p
                                            for p in payload['auxiliary_artifact_refs']]
        new_source = case.store.put('source', payload, origin=old_source['origin'])
        old_observation = case.store.get(result['observation_ref'])
        observed = {k:v for k,v in old_observation.items() if k not in {'id', 'origin', 'record_type'}}
        observed['source_ref'] = new_source['id']
        new_observation = case.store.put('observation', observed, origin=old_observation['origin'])
        replacements = {old_source['id']: new_source['id'], old_observation['id']: new_observation['id']}
        outcome['record_refs'] = [replacements.get(p, p) for p in outcome['record_refs']]
        result.update(source_ref=new_source['id'], complete_result_source_ref=new_source['id'],
                      observation_ref=new_observation['id'])
    return change_outcome(case, context, index, rewrite)


@pytest.fixture(scope='module')
def reference_base(tmp_path_factory):
    directory = tmp_path_factory.mktemp('native_pairwise_base')
    fasta = directory / 'sequences.fa'
    fasta.write_text('>query\nACGTTGCA\n>reference\nACGTAGCA\n>other\nTCGTTGCA\n')
    with Store(directory / 'state') as store:
        query, reference, other = store.create_problem(fasta, molecule='dna')['subject_refs']
        tools = ToolRegistry(store)
        alignments = []
        for index, query_ref in enumerate((query, other)):
            outcome = tools.execute('sequence.align', {'query_ref': query_ref, 'reference_ref': reference,
                'molecule': 'dna', 'mode': 'global'}, operation_key=f'base-align-{index}')
            assert outcome['status'] == 'completed', outcome
            alignments.append(outcome['result']['observation_ref'])
    return directory / 'state', alignments


@pytest.fixture
def reference_case(tmp_path, reference_base):
    original, alignments = reference_base
    shutil.copytree(original, tmp_path / 'state')
    with Store(tmp_path / 'state') as store:
        case = setup_case(store, ToolRegistry(store))
        case.alignments = alignments
        yield case


@pytest.fixture(scope='module')
def blast_base(tmp_path_factory):
    directory = tmp_path_factory.mktemp('offline_blast_base')
    store, _, target, alignment, _ = published(directory)
    path = store.path
    store.close()
    return path, target, alignment


@pytest.fixture
def blast_case(tmp_path, blast_base):
    original, target, alignment = blast_base
    shutil.copytree(original, tmp_path / 'store')
    store = Store(tmp_path / 'store')
    tools = ToolRegistry(store)
    with store:
        case = setup_case(store, tools)
        case.alignment, case.target = alignment, target
        yield case


def blast_read(case, context, index=3, offset=2, limit=4):
    return perform(case, context, index, 'result.blast.hsp',
        {'observation_ref': case.alignment, 'column_offset': offset, 'column_limit': limit},
        permitted=[case.alignment])


def test_reference_position_set_filters_before_hydration_and_limit(reference_case):
    case = reference_case
    first, second = case.alignments
    context = saved_context(case, requested(policy='matching_alignment_position_set',
        alignment=first, positions=[0, 2]))
    for index, alignment, selection in [(0, first, {'positions': [1]}),
            (1, first, {'positions': [2, 0, 2]}), (2, second, {'positions': [0, 2]}),
            (3, first, {'positions': [0, 2]}), (4, first, {'window': {'start': 0, 'end': 3}})]:
        perform(case, context, index, 'sequence.sites', {'alignment_ref': alignment, **selection})
    # A nonselected operation is deliberately unavailable: no selected-site
    # query may hydrate it or let it consume the requested page limit.
    case.store.db.execute('DELETE FROM tool_operations WHERE operation_key=?', (f'{RUN}:{context.episode_id}:0',))
    before = case.store.count('source'), case.store.count('observation'), case.store.db.total_changes
    one = page(case, context, limit=1)
    assert [r['decision_index'] for r in one['records']] == [1]
    assert one['next_after_decision_index'] == 1
    two = page(case, context, limit=1, after=one['next_after_decision_index'])
    assert [r['decision_index'] for r in two['records']] == [3]
    assert two['next_after_decision_index'] is None
    assert one['records'][0]['grading']['sheet']['requested_positions'] == [2, 0, 2]
    assert one['records'][0]['grading']['scores']['summary']['paired_positions'] == 2
    assert (case.store.count('source'), case.store.count('observation'), case.store.db.total_changes) == before


@pytest.mark.parametrize('policy', ['all_own_completed_results', 'matching_alignment', 'matching_alignment_window'])
def test_reference_selection_and_own_episode_isolation(reference_case, policy):
    case = reference_case
    first, second = case.alignments
    schema = requested(policy=policy, alignment=first, window={'start': 1, 'end': 3})
    context = saved_context(case, schema)
    sibling = saved_context(case, schema, name='child_1')
    for index, alignment, window in [(1, first, {'start': 0, 'end': 2}),
                                    (2, first, {'start': 1, 'end': 3}),
                                    (3, second, {'start': 1, 'end': 3})]:
        perform(case, context, index, 'sequence.sites', {'alignment_ref': alignment, 'window': window})
    perform(case, sibling, 0, 'sequence.sites', {'alignment_ref': first, 'window': {'start': 1, 'end': 3}})
    expected = {'all_own_completed_results': [1, 2, 3], 'matching_alignment': [1, 2],
                'matching_alignment_window': [2]}[policy]
    assert [r['decision_index'] for r in page(case, context)['records']] == expected


@pytest.mark.parametrize('change', ['run', 'episode', 'scope', 'request', 'unsaved'])
def test_context_is_original_saved_assignment(reference_case, change):
    case = reference_case
    context = saved_context(case, requested())
    if change == 'run':
        forged = replace(context, run_id='foreign-run')
    elif change == 'episode':
        forged = replace(context, episode_id='foreign-episode')
    elif change == 'scope':
        forged = replace(context, scope={'subject_refs': []})
    elif change == 'request':
        request = plain(context.request)
        request['report_contract']['unexpected_replacement'] = True
        forged = replace(context, request=request)
    else:
        case.store.db.execute('DELETE FROM runtime_episodes WHERE episode_id=?', (context.episode_id,))
        forged = context
    with pytest.raises(ValueError, match='alignment_site_return_.*context'):
        page(case, forged)


@pytest.mark.parametrize('limit,after', [(True, None), (0, None), (-1, None), (1, True), (1, -1)])
def test_page_parameters_are_explicit_integer_bounds(reference_case, limit, after):
    case = reference_case
    context = saved_context(case, requested())
    with pytest.raises(ValueError, match='explicit_page_required'):
        page(case, context, limit=limit, after=after)


def test_caller_cannot_broaden_original_selection_or_request_another_source(reference_case):
    case = reference_case
    context = saved_context(case, requested(policy='matching_alignment', alignment=case.alignments[0]))
    selection = {'policy': 'all_own_completed_results', 'alignment_refs': None, 'positions': None, 'window': None}
    with pytest.raises(ValueError, match='selection_conflict'):
        page(case, context, selection=selection)
    with pytest.raises(ValueError, match='requested_source_required'):
        case.service.own_action_results(context, source=BLAST, selection=selection, after_decision_index=None, limit=1)


@pytest.mark.parametrize('field', ['missing', 'id', 'name', 'arguments', 'scope'])
def test_completed_action_requires_exact_saved_operation(reference_case, field):
    case = reference_case
    context = saved_context(case, requested())
    perform(case, context, 0, 'sequence.sites', {'alignment_ref': case.alignments[0], 'positions': [0]})
    key = f'{RUN}:{context.episode_id}:0'
    if field == 'missing':
        case.store.db.execute('DELETE FROM tool_operations WHERE operation_key=?', (key,))
    else:
        value = {'id': 'operation_' + '0' * 24, 'name': 'result.blast.hsp',
                 'arguments': canonical({'alignment_ref': case.alignments[0], 'positions': [1]}),
                 'scope': canonical({'subject_refs': []})}[field]
        case.store.db.execute(f'UPDATE tool_operations SET {field}=? WHERE operation_key=?', (value, key))
    with pytest.raises(ValueError, match='alignment_site_return_(completed_operation_missing|operation_identity_conflict)'):
        page(case, context)


def test_runtime_only_pending_metadata_allowed_but_tool_result_type_change_rejected(reference_case):
    case = reference_case
    context = saved_context(case, requested())
    outcome = perform(case, context, 0, 'sequence.sites',
        {'alignment_ref': case.alignments[0], 'positions': [0]},
        runtime_extra={'pending_work_after_action': {'unfinished': True}})
    assert page(case, context)['records'][0]['grading']['scores']['summary']['paired_positions'] == 1
    changed = deepcopy(outcome)
    changed['result']['site_count'] = True  # bool equals 1 in Python, but is not a count.
    case.store.db.execute('UPDATE runtime_actions SET result=? WHERE episode_id=?', (canonical(changed), context.episode_id))
    with pytest.raises(ValueError, match='operation_outcome_conflict'):
        page(case, context)


@pytest.mark.parametrize('kind,index,allowed', [('initial', None, True), ('decision_input', 3, True),
    ('decision_input', 4, False), ('own_action', 2, True), ('own_action', 3, False),
    ('child_form', 2, True), ('child_form', 4, False), ('report_redelivery', 2, True)])
def test_blast_original_receipt_must_precede_selected_read(blast_case, kind, index, allowed):
    case = blast_case
    context = saved_context(case, requested(BLAST))
    blast_read(case, context)
    case.receipts.receive(context.episode_id, [case.alignment], kind=kind, source_index=index)
    if allowed:
        record, = page(case, context, BLAST)['records']
        assert record['grading']['scores']['summary']['paired_columns'] == 2
        assert record['binding']['result_source_ref'] is None
    else:
        with pytest.raises(ValueError, match='original_hsp_receipt_required'):
            page(case, context, BLAST)


@pytest.mark.parametrize('inherited_before', [True, False])
def test_blast_frozen_parent_receipt_prefix(blast_case, inherited_before):
    case = blast_case
    schema = requested(BLAST)
    parent = saved_context(case, schema, name='parent')
    if inherited_before:
        case.receipts.receive(parent.episode_id, [case.alignment], kind='child_form', source_index=1)
    child = saved_context(case, schema, name='descendant', parent=parent.episode_id)
    if not inherited_before:
        case.receipts.receive(parent.episode_id, [case.alignment], kind='child_form', source_index=2)
    blast_read(case, child)
    if inherited_before:
        assert len(page(case, child, BLAST)['records']) == 1
    else:
        with pytest.raises(ValueError, match='original_hsp_receipt_required'):
            page(case, child, BLAST)


def test_context_received_handles_do_not_replace_missing_receipt_history(blast_case):
    case = blast_case
    context = saved_context(case, requested(BLAST))
    blast_read(case, context)
    forged = replace(context, received_record_refs=(case.alignment,))
    with pytest.raises(ValueError, match='original_hsp_receipt_required'):
        page(case, forged, BLAST)
    case.store.db.execute('DELETE FROM runtime_receipt_inheritance WHERE episode_id=?', (context.episode_id,))
    with pytest.raises(ValueError, match='receipt_history_unbound'):
        page(case, forged, BLAST)


@pytest.mark.parametrize('tamper', ['locator', 'window', 'native_input', 'operand', 'mapping', 'alignment_unit'])
def test_blast_sheet_is_bound_to_original_native_hsp_and_coordinates(blast_case, tamper):
    case = blast_case
    context = saved_context(case, requested(BLAST))
    case.receipts.receive(context.episode_id, [case.alignment], kind='initial')
    blast_read(case, context)
    def corrupt(grading):
        sheet = grading['sheet']
        if tamper == 'locator':
            sheet['source']['native_locator']['hsp_ordinal'] += 1
        elif tamper == 'window':
            sheet['requested_window']['column_offset'] += 1
        elif tamper == 'native_input':
            sheet['native_input']['hit_from'] += 1
        elif tamper == 'operand':
            original = case.store.get(sheet['operands']['reference']['subject_ref'])
            payload = {k:v for k,v in original.items() if k not in {'id', 'origin', 'record_type'}}
            payload['accession'] = 'DIFFERENT_SAME_LENGTH.1'
            replacement = case.store.put('reference', payload, origin=original['origin'])
            assert replacement['length'] == original['length']
            sheet['operands']['reference']['subject_ref'] = replacement['id']
        elif tamper == 'mapping':
            sheet['original_mapping_inputs']['query'] = None
        else:
            sheet['operands']['query']['alignment_unit'] = 'aa'
    change_grading(case, context, 3, BLAST, corrupt)
    with pytest.raises(ValueError, match='(sheet_.*conflict|native_hsp_sheet_conflict)'):
        page(case, context, BLAST)


def test_blast_empty_window_and_legacy_grading_stay_distinct(blast_case, monkeypatch):
    case = blast_case
    context = saved_context(case, requested(BLAST))
    case.receipts.receive(context.episode_id, [case.alignment], kind='initial')
    blast_read(case, context, index=1, offset=8)
    blast_read(case, context, index=2)
    # Simulate the original older read shape without the new grading pointer.
    change_outcome(case, context, 2, lambda outcome: outcome['result'].pop('site_grading_artifact_ref'))
    def forbidden(*args, **kwargs):
        pytest.fail('Closing a saved result reran scientific grading')
    import gene_annotation_episode.alignment_site_native as native
    monkeypatch.setattr(native, 'blast_grading', forbidden)
    groups = project(case, context, BLAST)
    assert groups[0]['rows'] == [] and groups[0]['components']['paired_columns'] == 0
    assert groups[0]['components']['paired_identity']['value'] is None
    assert groups[1]['rows'] is None and groups[1]['components'] is None
    assert groups[1]['data_status'] == 'unavailable'
    assert 'site_legacy_result_ungraded' in groups[1]['issue_codes']


def test_actual_retained_grader_failure_is_partial_and_not_legacy(reference_case, monkeypatch):
    case = reference_case
    context = saved_context(case, requested())
    import gene_annotation_episode.alignment_site_inputs as inputs
    def reject(*args, **kwargs):
        raise ValueError('site_native_geometry_conflict')
    monkeypatch.setattr(inputs, 'extract_biopython_reference_sites', reject)
    outcome = perform(case, context, 0, 'sequence.sites',
        {'alignment_ref': case.alignments[0], 'positions': [0]})
    assert outcome['status'] == 'partial'
    record, = page(case, context)['records']
    assert record['availability'] == 'grading_unavailable'
    assert record['grading']['failure']['code'] == 'site_native_geometry_conflict'
    group, = project(case, context)
    assert group['operation_status'] == 'partial' and group['rows'] is None
    assert group['components'] is None
    assert 'site_native_geometry_conflict' in group['issue_codes']


def test_frozen_facts_distinguish_absent_closure_absent_source_and_actual_empty(reference_case):
    case = reference_case
    context = saved_context(case, requested())
    sources = (REFERENCE,)
    assert case.service.frozen_facts(context, sources=sources) is None
    case.journal.save('runtime_forms', {'episode_id': context.episode_id,
        'facts': canonical({'unrequested': ['private', {'count': 999}]}), 'form': None})
    assert case.service.frozen_facts(context, sources=sources) == {}
    case.journal.save('runtime_forms', {'episode_id': context.episode_id,
        'facts': canonical({REFERENCE: [], BLAST: ['never-requested']}), 'form': canonical({'selected': []})})
    assert case.service.frozen_facts(context, sources=sources) == {REFERENCE: []}
    assert case.service.frozen_facts(context, sources=()) == {}
    with pytest.raises(ValueError, match='requested_source_required'):
        case.service.frozen_facts(context, sources=(BLAST,))


@pytest.mark.parametrize('value', [None, {}, 0, False, '[]'])
def test_frozen_source_must_be_actual_array(reference_case, value):
    case = reference_case
    context = saved_context(case, requested())
    case.journal.save('runtime_forms', {'episode_id': context.episode_id,
        'facts': canonical({REFERENCE: value}), 'form': None})
    with pytest.raises(ValueError, match='frozen_source_invalid'):
        case.service.frozen_facts(context, sources=(REFERENCE,))


def test_frozen_values_remain_exact_after_later_actions_and_source_disappearance(reference_case, monkeypatch):
    case = reference_case
    schema = requested()
    context = saved_context(case, schema)
    perform(case, context, 1, 'sequence.sites', {'alignment_ref': case.alignments[0], 'positions': [2, 0, 2]})
    expected = project(case, context)
    case.journal.save('runtime_forms', {'episode_id': context.episode_id,
        'facts': canonical({REFERENCE: expected}), 'form': canonical({'selected': expected})})
    perform(case, context, 2, 'sequence.sites', {'alignment_ref': case.alignments[0], 'positions': [4]})
    def forbidden(*args, **kwargs):
        pytest.fail('Frozen return accessed live tool records or artifact bytes')
    monkeypatch.setattr(case.service, 'own_action_results', forbidden)
    monkeypatch.setattr(case.store, 'get_artifact', forbidden)
    frozen = case.service.frozen_facts(context, sources=(REFERENCE,))
    assert frozen == {REFERENCE: expected}
    validate_frozen_site_return({'selected': deepcopy(expected)}, schema, frozen)
    changed = deepcopy(expected)
    changed[0]['rows'].reverse()
    with pytest.raises(ReportBoundaryError, match='.*'):
        validate_frozen_site_return({'selected': changed}, schema, frozen)
    assert case.service.frozen_facts(context, sources=(REFERENCE,)) == frozen


def test_non_scientific_owner_cannot_request_site_results(reference_case):
    case = reference_case
    context = saved_context(case, requested(), role='root')
    with pytest.raises(ValueError, match='scientific_owner_required'):
        page(case, context)


def test_blast_matching_window_omits_other_own_windows_before_page_limit(blast_case):
    case = blast_case
    context = saved_context(case, requested(BLAST, 'matching_alignment_window',
        alignment=case.alignment, window={'column_offset': 2, 'column_limit': 4}))
    case.receipts.receive(context.episode_id, [case.alignment], kind='initial')
    blast_read(case, context, index=0, offset=0, limit=4)
    blast_read(case, context, index=1, offset=2, limit=4)
    blast_read(case, context, index=2, offset=2, limit=2)
    blast_read(case, context, index=3, offset=2, limit=4)
    first = page(case, context, BLAST, limit=1)
    second = page(case, context, BLAST, limit=1, after=first['next_after_decision_index'])
    assert [r['decision_index'] for r in first['records']] == [1]
    assert [r['decision_index'] for r in second['records']] == [3]
    assert second['next_after_decision_index'] is None


def test_missing_native_blast_strings_remain_unknown_in_saved_return(tmp_path):
    store, tools, _, alignment, _ = published(tmp_path, alignment=False)
    with store:
        case = setup_case(store, tools)
        case.alignment = alignment
        context = saved_context(case, requested(BLAST))
        case.receipts.receive(context.episode_id, [alignment], kind='initial')
        blast_read(case, context)
        group, = project(case, context, BLAST)
        assert group['data_status'] == 'unavailable'
        assert group['selection']['column_offset'] == 2
        assert group['selection']['column_end'] is None
        assert group['rows'] is None
        assert group['components']['paired_columns'] is None


@pytest.fixture(scope='module')
def mapping_base(tmp_path_factory):
    from test_native_read_mapping import fixture
    directory = tmp_path_factory.mktemp('native_minimap2_base')
    store, tools, _, selected, args = fixture(directory)
    with store:
        result = tools.execute('reads.map', args, scope=selected['scope'], operation_key='native-map-288')
        assert result['status'] == 'completed', result
        alignments = {row['strand']: row['observation_ref'] for row in result['result']['records']}
        assert set(alignments) == {'+', '-'}
        source = store.get(result['result']['source_ref'])
        assert source['version']
        path = store.path
    return path, selected['scope'], alignments


@pytest.fixture
def mapping_case(tmp_path, mapping_base):
    original, scope, alignments = mapping_base
    shutil.copytree(original, tmp_path / 'state')
    with Store(tmp_path / 'state') as store:
        case = setup_case(store, ToolRegistry(store), scope=scope)
        case.alignments = alignments
        yield case


@pytest.mark.parametrize('strand', ['+', '-'])
def test_actual_mapping_read_preserves_native_row_member_quality_and_scope(mapping_case, strand):
    case = mapping_case
    context = saved_context(case, requested())
    positions = [2099, 2100, 3600] if strand == '+' else [500, 5499]
    outcome = perform(case, context, 0, 'sequence.sites',
        {'alignment_ref': case.alignments[strand], 'positions': positions})
    before = case.store.count('source'), case.store.count('observation'), case.store.db.total_changes
    record, = page(case, context)['records']
    sheet, scores = record['grading']['sheet'], record['grading']['scores']
    assert sheet['mode'] == 'minimap2_placement'
    assert sheet['native_parameters']['preset'] == 'map-ont'
    assert sheet['native_input']['quality_encoding'] == 'unspecified'
    assert sheet['native_input']['quality'] == ('I' * 5001 if strand == '+' else '?' * 5000)
    assert all(row['query_quality_score'] is None for row in sheet['sites'])
    if strand == '+':
        assert scores['summary']['paired_positions'] == 2
        assert scores['summary']['query_gap_positions'] == 1
        assert scores['summary']['inserted_query_positions'] == 3
        assert sheet['insertions'][0]['query_quality_characters'] == 'III'
    else:
        assert [row['query_position'] for row in sheet['sites']] == [4999, 0]
        assert [row['query_quality_character'] for row in sheet['sites']] == ['?', '?']
    source = case.store.get(sheet['source']['source_ref'])
    assert record['binding']['native_artifact_ref'] == source['stdout_ref']
    assert record['binding']['result_source_ref'] == outcome['result']['source_ref']
    assert (case.store.count('source'), case.store.count('observation'), case.store.db.total_changes) == before


@pytest.mark.parametrize('tamper', ['quality', 'quality_encoding', 'sequence', 'length',
    'parsed_row', 'preset', 'version', 'locator', 'alignment_unit'])
def test_mapping_sheet_requires_actual_quality_geometry_and_processing_model(mapping_case, tamper):
    case = mapping_case
    context = saved_context(case, requested())
    perform(case, context, 0, 'sequence.sites',
        {'alignment_ref': case.alignments['+'], 'positions': [2099, 2100, 3600]})
    def corrupt(grading):
        sheet = grading['sheet']
        native = sheet['native_input']
        if tamper == 'quality':
            native['quality'] = '?' + native['quality'][1:]
        elif tamper == 'quality_encoding':
            native['quality_encoding'] = 'phred33'
        elif tamper == 'sequence':
            old = native['query_metadata']['sequence']
            native['query_metadata']['sequence'] = ('A' if old[0] != 'A' else 'C') + old[1:]
        elif tamper == 'length':
            native['query_metadata']['length'] += 1
        elif tamper == 'parsed_row':
            native['native_row']['mapping_quality'] += 1
        elif tamper == 'preset':
            sheet['native_parameters']['preset'] = 'map-pb'
        elif tamper == 'version':
            sheet['native_parameters']['native_version'] = 'wrong-version'
        elif tamper == 'locator':
            sheet['source']['native_locator']['row_start'] += 1
        else:
            sheet['operands']['query']['alignment_unit'] = 'aa'
    change_grading(case, context, 0, REFERENCE, corrupt)
    with pytest.raises(ValueError, match='alignment_site_return_.*conflict'):
        page(case, context)


@pytest.mark.parametrize('role', ['query', 'reference'])
def test_native_pairwise_source_cannot_be_reassigned_to_same_length_other_operand(reference_case, role):
    case = reference_case
    original = case.store.get(case.alignments[0])
    replacement = case.store.get(case.alignments[1])['subject_refs'][0]
    field = 'subject_refs' if role == 'query' else 'source_subject_refs'
    assert replacement != original[field][0]
    assert case.store.subject_length(replacement) == case.store.subject_length(original[field][0])
    payload = {k:deepcopy(v) for k,v in original.items() if k not in {'id', 'record_type', 'origin'}}
    old = payload[field][0]
    payload[field] = [replacement]
    payload['dependencies'] = [replacement if value == old else value for value in payload['dependencies']]
    for interval in payload['operand_intervals']:
        if interval['role'] == role:
            interval['subject_ref'] = replacement
    if role == 'reference':
        for measurement in payload['measurements']:
            if measurement['name'] == 'reference_ref':
                measurement['value']['ref'] = replacement
    # This is a newly valid observation identity, not a mutated row with a
    # stale hash. Its native source still belongs to the original actual pair.
    forged = case.store.put('observation', payload, origin='tool')
    assert forged['id'] != original['id'] and forged['source_ref'] == original['source_ref']
    result = case.tools.execute('sequence.sites', {'alignment_ref': forged['id'], 'positions': [0, 4]},
        scope=case.scope, operation_key='reassigned-source-' + role)
    assert result['status'] == 'invalid', result
    assert result['record_refs'] == []


@pytest.mark.parametrize('keep_original_operation', [True, False])
def test_legacy_pairwise_source_uses_actual_producer_arguments(reference_case, monkeypatch, keep_original_operation):
    case = reference_case
    original = case.store.get(case.alignments[0])
    arguments = {'query_ref': original['subject_refs'][0],
        'reference_ref': original['source_subject_refs'][0], 'molecule': 'dna', 'mode': 'global'}
    save_source = case.tools._source
    def legacy_source(provider, body, **options):
        # Explicit old-source-shape fixture. Native work, actual operation
        # arguments, publication and the resulting tool-operation row are real.
        if provider == 'biopython.alignment':
            options.pop('operand_refs', None)
        return save_source(provider, body, **options)
    with monkeypatch.context() as legacy:
        legacy.setattr(case.tools, '_source', legacy_source)
        produced = case.tools.execute('sequence.align', arguments,
            scope=case.scope, operation_key='legacy-original-288')
    assert produced['status'] == 'completed', produced
    alignment = produced['result']['observation_ref']
    source = case.store.get(produced['result']['source_ref'])
    assert 'operand_refs' not in source
    if not keep_original_operation:
        case.store.db.execute('DELETE FROM tool_operations WHERE operation_key=?', ('legacy-original-288',))
    context = saved_context(case, requested())
    if keep_original_operation:
        perform(case, context, 0, 'sequence.sites', {'alignment_ref': alignment, 'positions': [0, 4]})
        record, = page(case, context)['records']
        assert record['grading']['scores']['summary']['paired_positions'] == 2
        assert record['grading']['scores']['summary']['identical_positions'] == 1
    else:
        result = case.tools.execute('sequence.sites', {'alignment_ref': alignment, 'positions': [0, 4]},
            scope=case.scope, operation_key='orphan-legacy-source')
        assert result['status'] == 'invalid', result
        assert result['record_refs'] == []
