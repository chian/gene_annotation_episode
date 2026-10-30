"""Constructed engineering fixtures joined to actual Store/ToolRegistry and070 APIs.

Inserted journal/context/receipt data do NOT establish selected LiteratureEpisode
execution, model interpretation, genuine paper measurements or connected C1/C4.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

from gene_annotation_episode.communication import form_with_facts, validate_form, plain
from gene_annotation_episode.domain import ContractError, canonical, identity, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.literature_ratio_source_storage import (
    LiteratureRatioSourceRepository, ratio_source_cells_schema, ratio_source_population_schema)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


def source(store, data, *, parents=(), name='synthetic_engineering_fixture'):
    artifact = store.artifact(data)
    return store.put('source', {'provider': name, 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')['id']


def native_case(path, *, known=False, frame=1, conversion='preserve'):
    store = Store(path)
    store.create_problem(raw_sequence='MKWAA', molecule='protein')
    text = b'Synthetic enzyme. Variant V. Reference WT. Engineering organism. Genotype D. Construct V. Construct WT. Prep V. Prep WT. Experiment E. Condition C. Protein signal. WT scale.'
    root = source(store, text)
    first = Image.new('RGB', (240, 100), 'white')
    second = Image.new('RGB', (240, 100), 'white')
    draw = ImageDraw.Draw(second); draw.text((10, 40), '0.64', fill='black'); draw.text((110, 40), '1.00', fill='black')
    if conversion == 'rgb':
        first, second = first.convert('CMYK'), second.convert('CMYK')
    buffer = BytesIO(); first.save(buffer, format='TIFF', save_all=True, append_images=[second])
    image = source(store, buffer.getvalue(), parents=[root])
    scope = store.validate_scope()
    args = {'source_ref': image, 'frame': frame, 'colour_conversion': conversion}
    native = ToolRegistry(store).execute('image.view', args, scope=scope, operation_key='fixture-run:fixture-child:4')
    assert native['status'] == 'completed', native
    view = native['result']['view']
    journal = Journal(store, 'fixture-run')
    journal.save('runtime_actions', {'episode_id': 'fixture-child', 'decision_index': 4,
        'action': canonical({'kind': 'tool', 'tool': 'image.view', 'arguments': args}),
        'result': canonical(native), 'credit': None, 'timing': None})
    # A later own action is allowed: no mandatory immediately previous image view.
    journal.save('runtime_actions', {'episode_id': 'fixture-child', 'decision_index': 9,
        'action': canonical({'kind': 'tool', 'tool': 'state.query', 'arguments': {'refs': [root]}}),
        'result': canonical({'status': 'completed', 'record_refs': [root]}), 'credit': None, 'timing': None})
    received = (root, image, view['id'], view['source_ref'])
    context = BindingContext('fixture-run', 'fixture-child', 'literature_page',
        (('literature_page', 'synthetic'),), scope, {'source_ref': root}, {}, received)
    meaning_names = ('subject', 'variant', 'reference', 'organism', 'genotype', 'construct_variant',
        'construct_reference', 'preparation_variant', 'preparation_reference', 'experiment', 'condition',
        'endpoint', 'normalization', 'signal_kind', 'reference_role', 'arrangement', 'signal_use')
    comparison = {name: {'status': 'unknown', 'value': None, 'witnesses': []} for name in meaning_names}
    numerator = {'kind': 'image', 'view_ref': view['id'], 'region': [10, 40, 80, 65], 'quote': '0.64'}
    denominator = {'kind': 'image', 'view_ref': view['id'], 'region': [110, 40, 180, 65], 'quote': '1.00'}
    if known:
        labels = ['Synthetic enzyme', 'V', 'WT', 'Engineering organism', 'D', 'Construct V', 'Construct WT',
            'Prep V', 'Prep WT', 'Experiment E', 'Condition C', 'Protein signal', 'WT scale']
        for name, label in zip(meaning_names, labels):
            start = text.index(label.encode())
            comparison[name] = {'status': 'known', 'value': label, 'witnesses': [{
                'kind': 'text', 'source_ref': root, 'representation': 'original',
                'start': start, 'end': start + len(label), 'quote': label}]}
        for name, value in [('signal_kind', 'protein_band'), ('reference_role', 'tagged_wt_complementation'),
                ('arrangement', 'replacement'), ('signal_use', 'experimental_comparability')]:
            comparison[name] = {'status': 'known', 'value': value, 'witnesses': [deepcopy(numerator)]}
    selection = {'version': 'relative_signal_source_selection_v2', 'source_ref': root,
        'comparison': comparison, 'representations': [{
            'representation_id': 'printed-pair', 'kind': 'visual_signal_pair',
            'selection': {'reading_state': 'exact', 'candidates': [{'numerator': numerator, 'denominator': denominator}],
                'fragments': [], 'signal_scale': {'value': 'supported', 'witnesses': [deepcopy(numerator)]}},
            'comparison_relation': {'value': 'supported', 'witnesses': [deepcopy(numerator)]},
            'physical_measurement': {'status': 'unknown', 'value': None, 'witnesses': []},
            'reference_measurement': {'status': 'unknown', 'value': None, 'witnesses': []}}]}
    return store, context, selection, native


def repository(store, context):
    return LiteratureRatioSourceRepository(store, context.run_id, evidence_origin='synthetic_fixture')


def owned(context, outcome):
    return replace(context, received_record_refs=(*context.received_record_refs, *outcome['record_refs']))


def test_joined_native_sheet_original_meanings_and_exact_typed_schema(tmp_path):
    store, context, selection, native = native_case(tmp_path, known=True)
    try:
        repo = repository(store, context)
        outcome = repo.populate(context, selection, 'selected')
        sheet_ref = outcome['result']['sheet_ref']
        saved = repo.read(sheet_ref)
        assert saved['extraction']['evidence_origin'] == 'synthetic_fixture'
        assert saved['sheet']['cells']['reported_ratio']['value'] == .64
        assert saved['sheet']['cells']['difference_from_reference']['value'] == -.36
        assert saved['sheet']['cells']['log_reported_ratio']['value'] == pytest.approx(-.4462871026284195)
        rows = repo.fact_cells(owned(context, outcome), [sheet_ref], components=['reported_ratio', 'calibrated_amount_ratio'])
        assert rows[0]['source_origins'] == ['synthetic']
        assert rows[0]['signal_use'] == 'experimental_comparability'
        assert rows[0]['physical_identity_states'] == ['unknown']
        assert rows[0]['input_measurement_refs'] == []
        assert store.get(rows[0]['subject_ref'])['label'] == 'Synthetic enzyme'
        assert rows[0]['variant_ref'] != rows[0]['reference_ref']
        assert store.get(rows[0]['condition_ref'])['record_type'] == 'context'
        assert rows[1]['value'] is None and rows[1]['unavailable_reason'] == 'calibrated_amount_conversion_unimplemented'
        schema = obj({'caller_named_components': ratio_source_cells_schema()})
        form = form_with_facts({}, schema, {'literature_ratio_source_cells': rows})
        validate_form(form, schema, lambda ref, namespace: ref in (*outcome['record_refs'], *context.received_record_refs)
            and store.get(ref)['record_type'] == namespace)
        assert saved['extraction']['views'][0]['own_action_receipt']['result_sha256'] == hashlib.sha256(canonical(native).encode()).hexdigest()
        assert len(saved['input_view_refs']) == 1
        assert set(saved['direct_input_source_refs']) == set(context.received_record_refs) - {native['result']['view_ref']}
        assert not store.list('observation') and store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 0
    finally:
        store.close()


@pytest.mark.parametrize('conversion', ['preserve', 'rgb'])
def test_actual_multiframe_native_publication_and_conversion(tmp_path, conversion):
    store, context, selection, native = native_case(tmp_path, conversion=conversion)
    try:
        result = repository(store, context).populate(context, selection, 'native-frame')
        payload = repository(store, context).read(result['result']['sheet_ref'])
        metadata = payload['extraction']['views'][0]['metadata']
        assert metadata['native_format'] == 'TIFF' and metadata['frame'] == 1 and metadata['frame_count'] == 2
        assert metadata['colour_conversion'] == conversion
        assert native['result']['view'] == metadata
    finally:
        store.close()


@pytest.mark.parametrize('missing', ['view', 'original', 'display', 'root'])
def test_direct_custody_is_not_ancestry_possession_before_any_byte_access(tmp_path, monkeypatch, missing):
    store, context, selection, native = native_case(tmp_path)
    try:
        view = native['result']['view']
        ref = {'view': view['id'], 'original': view['input_source_ref'], 'display': view['source_ref'],
            'root': selection['source_ref']}[missing]
        context = replace(context, received_record_refs=tuple(r for r in context.received_record_refs if r != ref))
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('unauthorized byte access'))
        with pytest.raises(ContractError, match='not_received'):
            repository(store, context).populate(context, selection, 'no-custody')
    finally:
        store.close()


@pytest.mark.parametrize('mismatch', ['other_episode', 'no_action', 'wrong_arguments', 'wrong_result', 'wrong_tool', 'wrong_scope', 'wrong_frame', 'wrong_conversion'])
def test_own_completed_action_must_match_actual_toolregistry_result(tmp_path, mismatch):
    store, context, selection, native = native_case(tmp_path)
    try:
        if mismatch == 'other_episode':
            context = replace(context, episode_id='other')
        elif mismatch == 'no_action':
            store.db.execute('DELETE FROM runtime_actions WHERE decision_index=4')
        elif mismatch in ('wrong_arguments', 'wrong_frame', 'wrong_conversion'):
            row = store.db.execute('SELECT action FROM runtime_actions WHERE decision_index=4').fetchone()
            action = json.loads(row[0]); action['arguments'][{'wrong_arguments': 'source_ref', 'wrong_frame': 'frame', 'wrong_conversion': 'colour_conversion'}[mismatch]] = {
                'wrong_arguments': selection['source_ref'], 'wrong_frame': 0, 'wrong_conversion': 'rgb'}[mismatch]
            store.db.execute('UPDATE runtime_actions SET action=? WHERE decision_index=4', (canonical(action),))
        elif mismatch == 'wrong_result':
            result = deepcopy(native); result['visual_inputs'] = []
            store.db.execute('UPDATE runtime_actions SET result=? WHERE decision_index=4', (canonical(result),))
        elif mismatch == 'wrong_tool':
            store.db.execute("UPDATE tool_operations SET name='state.query'")
        elif mismatch == 'wrong_scope':
            store.db.execute("UPDATE tool_operations SET scope='null'")
        with pytest.raises(ContractError, match='own_view_action'):
            repository(store, context).populate(context, selection, 'bad-action')
        assert store.db.execute('SELECT count(*) FROM literature_ratio_source_operations').fetchone()[0] == 0
    finally:
        store.close()


def test_scope_and_page_ancestry_reject_unrelated_sources(tmp_path, monkeypatch):
    store, context, selection, _ = native_case(tmp_path)
    try:
        unrelated = source(store, b'Unrelated synthetic material')
        context = replace(context, assignment={'source_ref': unrelated})
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('unauthorized byte access'))
        with pytest.raises(ContractError, match='outside_assigned_source'):
            repository(store, context).populate(context, selection, 'wrong-page')
        context = replace(context, assignment={}, scope={'subject_refs': []})
        with pytest.raises(ContractError):
            repository(store, context).populate(context, selection, 'wrong-scope')
    finally:
        store.close()


def test_metadata_only_replay_key_conflicts_origin_and_saved_output(tmp_path, monkeypatch):
    store, context, selection, _ = native_case(tmp_path)
    try:
        repo = repository(store, context)
        outcome = repo.populate(context, selection, 'stable')
        original = repo.read(outcome['result']['sheet_ref'])
        reads = []
        get = store.get_artifact
        banned = {store.get(ref)['artifact_ref'] for ref in original['input_source_refs']}
        def saved_only(reference):
            assert reference not in banned
            reads.append(reference)
            return get(reference)
        monkeypatch.setattr(store, 'get_artifact', saved_only)
        import gene_annotation_episode.literature_ratio_source_inputs as inputs
        import gene_annotation_episode.literature_ratio_source_calculations as calc
        monkeypatch.setattr(inputs, 'read_relative_signal_source_inputs', lambda *_a, **_k: pytest.fail('reader replay'))
        monkeypatch.setattr(calc, 'populate_relative_signal_v2', lambda *_a, **_k: pytest.fail('calculator replay'))
        before = store.db.total_changes
        assert repo.populate(context, selection, 'stable') == outcome
        assert store.db.total_changes == before and reads
        wrong = deepcopy(selection); wrong['representations'][0]['representation_id'] = 'changed'
        with pytest.raises(ContractError, match='different_work'):
            repo.populate(context, wrong, 'stable')
        with pytest.raises(ContractError, match='different_work'):
            LiteratureRatioSourceRepository(store, context.run_id).populate(context, selection, 'stable')
    finally:
        store.close()


def test_atomic_rollback_preserves_no_selected_output_or_entities(tmp_path, monkeypatch):
    store, context, selection, _ = native_case(tmp_path, known=True)
    try:
        repo = repository(store, context)
        before = list(store.db.execute('SELECT id FROM records ORDER BY id'))
        artifacts = list(store.db.execute('SELECT id FROM artifacts ORDER BY id'))
        put = store.put
        def fail(kind, value, **kwargs):
            if kind == 'source' and value.get('provider') == repo.provider:
                raise ContractError('injected_atomic_failure')
            return put(kind, value, **kwargs)
        monkeypatch.setattr(store, 'put', fail)
        with pytest.raises(ContractError, match='injected_atomic_failure'):
            repo.populate(context, selection, 'fails')
        assert list(store.db.execute('SELECT id FROM records ORDER BY id')) == before
        assert list(store.db.execute('SELECT id FROM artifacts ORDER BY id')) == artifacts
        assert store.db.execute('SELECT count(*) FROM literature_ratio_source_operations').fetchone()[0] == 0
    finally:
        store.close()


@pytest.mark.parametrize('mode', ['unknown_association', 'different_association', 'unknown_scale', 'different_scale', 'nd', 'zero', 'censor', 'ambiguous', 'unreadable', 'linked_conflict'])
def test_authentic_partial_conflicting_numerical_results_are_not_empty_success(tmp_path, mode):
    store, context, selection, _ = native_case(tmp_path)
    try:
        row = selection['representations'][0]
        if mode.endswith('association'):
            row['comparison_relation']['value'] = mode.split('_')[0]
        elif mode.endswith('scale'):
            row['selection']['signal_scale']['value'] = mode.split('_')[0]
        elif mode in ('nd', 'zero', 'censor'):
            row['selection']['candidates'][0]['numerator']['quote'] = {'nd': 'ND', 'zero': '0', 'censor': '<0.64'}[mode]
        elif mode in ('ambiguous', 'linked_conflict'):
            if mode == 'linked_conflict':
                other = deepcopy(row); other['representation_id'] = 'contradicting-printed-pair'
                other['selection']['candidates'][0]['numerator']['region'] = [10, 10, 80, 30]
                other['selection']['candidates'][0]['numerator']['quote'] = '1.12'
                selection['representations'].append(other)
            else:
                row['selection']['reading_state'] = 'ambiguous'
                other = deepcopy(row['selection']['candidates'][0]); other['numerator']['quote'] = '0.84'
                row['selection']['candidates'].append(other)
        elif mode == 'unreadable':
            row['selection']['reading_state'] = 'unreadable'; row['selection']['candidates'] = []
            row['selection']['fragments'] = [{'view_ref': context.received_record_refs[2], 'region': [10, 40, 80, 65], 'raw_fragment': '0.?'}]
        repo = repository(store, context); outcome = repo.populate(context, selection, 'partial')
        saved = repo.read(outcome['result']['sheet_ref']); cells = saved['sheet']['cells']
        assert len(cells) == 7
        if mode == 'zero':
            assert cells['reported_ratio']['value'] == 0 and cells['log_reported_ratio']['value'] is None
        else:
            assert cells['reported_ratio']['value'] is None
        if mode == 'linked_conflict':
            assert saved['sheet']['known_source_conflict']
            assert cells['reported_ratio']['value_candidates'] == [.64, 1.12]
        if mode == 'censor':
            assert cells['reported_ratio']['reported_domains']
        assert not store.list('observation')
    finally:
        store.close()


def test_original_owner_inherited_subset_empty_and_unchanged_delivery(tmp_path):
    store, context, selection, _ = native_case(tmp_path)
    try:
        repo = repository(store, context); outcome = repo.populate(context, selection, 'owned')
        owner = owned(context, outcome); sheet = outcome['result']['sheet_ref']
        all_cells = repo.fact_cells(owner, [sheet], components=list(repo.components))
        parent = replace(owner, episode_id='fixture-parent', role='literature', path=(('literature', 'synthetic-parent'),), assignment={})
        # Source/sheet possession alone does not authorize private child cells.
        assert repo.fact_cells(parent, [sheet], components=list(repo.components)) == []
        repo.receive_cells(parent, all_cells[:1], 'manual-engineering-fixture-receipt')
        before = store.db.total_changes
        repo.receive_cells(parent, all_cells[:1], 'manual-engineering-fixture-receipt')
        assert store.db.total_changes == before
        assert repo.fact_cells(parent, [sheet], components=list(repo.components)) == all_cells[:1]
        assert repo.fact_cells(parent, [sheet], components=[]) == []
        repo.validate_fact_values(parent, all_cells[:1])
        with pytest.raises(ContractError, match='cell_not_received'):
            repo.validate_fact_values(parent, all_cells[1:2])
        with pytest.raises(ContractError, match='component_selection_invalid'):
            repo.fact_cells(owner, [sheet], components=['not-a-component'])
        bad = deepcopy(all_cells[:1]); bad[0]['value'] = .9
        with pytest.raises(ContractError, match='differs_from_saved'):
            repo.receive_cells(parent, bad, 'forged')
        assert repo.received_cells(parent) == all_cells[:1]
    finally:
        store.close()


def test_request_and_return_schema_exact_detached_and_no_model_origin():
    directory = Path(__file__).resolve().parents[1] / 'verification/literature_reference_evidence_2026-10-25_001/visual_signal_parent_review_067/text_locator_declarations_008'
    assert ratio_source_population_schema() == json.loads((directory / 'REQUEST_SCHEMA_008.json').read_text())
    assert ratio_source_cells_schema() == json.loads((directory / 'RETURN_SCHEMA_008.json').read_text())
    request = ratio_source_population_schema(); request['properties'].clear()
    returned = ratio_source_cells_schema(); returned['items'].clear()
    assert 'source_ref' in ratio_source_population_schema()['properties']
    assert 'origin' in ratio_source_cells_schema()['items']['properties']
    assert 'evidence_origin' not in ratio_source_population_schema()['properties']


def test_authorized_availability_partial_survives_saved_read_without_repair(tmp_path, monkeypatch):
    import errno
    store, context, selection, native = native_case(tmp_path)
    try:
        repo = repository(store, context)
        unavailable = native['result']['view']['original_artifact_ref']
        get = store.get_artifact
        def missing(ref):
            if ref == unavailable:
                raise FileNotFoundError(errno.ENOENT, 'synthetic missing native bytes')
            return get(ref)
        monkeypatch.setattr(store, 'get_artifact', missing)
        outcome = repo.populate(context, selection, 'missing-native')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['extraction']['views'][0]['state'] == 'unavailable'
        assert saved['sheet']['cells']['reported_ratio']['value'] is None
        assert saved['extraction']['views'][0]['diagnostics'][0]['code'] == 'source_dependency_unavailable'
        assert saved['sheet']['cells']['reported_ratio']['unavailable_reason'] == 'comparison_association_unresolved'
        monkeypatch.setattr(store, 'get_artifact', get)
        assert repo.populate(context, selection, 'missing-native') == outcome
        assert repo.read(outcome['result']['sheet_ref']) == saved
    finally:
        store.close()


@pytest.mark.parametrize('fault', ['payload_value', 'payload_origin', 'payload_reason', 'payload_domain', 'owner', 'reference', 'roster', 'source_identity', 'operation_ref', 'request_owner', 'request_selection', 'calculation'])
def test_saved_valid_shape_forgery_is_rejected(tmp_path, fault):
    store, context, selection, _ = native_case(tmp_path, known=True)
    try:
        repo = repository(store, context); outcome = repo.populate(context, selection, 'original')
        reference = outcome['result']['sheet_ref']; row = store.get(reference)
        if fault == 'source_identity':
            row['provider'] = 'forged.provider'
            store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(row), reference))
        elif fault == 'operation_ref':
            outcome['operation_ref'] = identity('operation', {'forged': True})
            store.db.execute('UPDATE literature_ratio_source_operations SET outcome=?', (canonical(outcome),))
        elif fault.startswith('request_'):
            request = json.loads(store.get_artifact(row['request_ref']))
            if fault == 'request_owner': request['episode_id'] = 'different-owner'
            else: request['arguments']['representations'][0]['representation_id'] = 'different-request'
            row['request_ref'] = store.artifact(canonical(request), 'application/json')
            store.db.execute('UPDATE records SET data=? WHERE id=?', (canonical(row), reference))
        else:
            payload = repo.read(reference)
            if fault.startswith('payload_'):
                cell = payload['sheet']['cells']['reported_ratio']
                if fault == 'payload_value': cell['value'] = .9
                if fault == 'payload_origin': cell['origin'] = 'reported'
                if fault == 'payload_reason': cell['unavailable_reason'] = 'reported_limit_not_point'
                if fault == 'payload_domain': cell['reported_domains'][0]['upper'] = .9
            elif fault == 'owner': payload['experimental_bindings']['subject_ref'] = payload['experimental_bindings']['variant_ref']
            elif fault == 'reference': payload['measurement_bindings'][0]['reference_measurement_ref'] = payload['experimental_bindings']['reference_ref']
            elif fault == 'roster': payload['direct_input_source_refs'].reverse()
            elif fault == 'calculation':
                calc = json.loads(store.get_artifact(payload['calculation_artifact_ref']))
                calc['input_extraction_sha256'] = 'a' * 64
                payload['calculation_artifact_ref'] = store.artifact(canonical(calc), 'application/json')
            # Create a correctly content-addressed but forged output and alter
            # the fixture's selected-output pointer as well. Deep association
            # checks must reject it, rather than only spotting an old record ID.
            body = {key: value for key, value in row.items() if key not in ('id', 'record_type', 'origin')}
            body['artifact_ref'] = store.artifact(canonical(payload), 'application/json')
            body['text_ref'] = body['artifact_ref']
            forged = store.put('source', body, origin='tool', scope=plain(context.scope))['id']
            outcome['record_refs'] = [forged if ref == reference else ref for ref in outcome['record_refs']]
            outcome['changed_record_refs'] = [forged if ref == reference else ref for ref in outcome['changed_record_refs']]
            outcome['result']['sheet_ref'] = forged
            outcome['result']['cells'] = payload['sheet']['cells']
            store.db.execute('UPDATE literature_ratio_source_operations SET outcome=?', (canonical(outcome),))
            reference = forged
        with pytest.raises((ContractError, ValueError)):
            repo.read(reference)
    finally:
        store.close()


def test_constructed_runtime_receipt_schema_digest_and_child_contract_relationships(tmp_path):
    """Inserted form records are explicit engineering fixtures, not connected C4."""
    store, context, selection, _ = native_case(tmp_path)
    try:
        repo = repository(store, context); outcome = repo.populate(context, selection, 'original')
        reference = outcome['result']['sheet_ref']; owner = owned(context, outcome)
        cells = repo.fact_cells(owner, [reference], components=['reported_ratio'])
        parent = replace(owner, episode_id='fixture-parent', role='literature', path=(('literature', 'synthetic-parent'),), assignment={})
        schema = obj({'requested_only': ratio_source_cells_schema()})
        contract = {'decision': 'Return exactly requested engineering components', 'measurements': {'schema': schema}}
        journal = Journal(store, context.run_id)
        journal.save('runtime_episodes', {'episode_id': context.episode_id, 'path': '[]',
            'request': canonical({'report_contract': contract}), 'initial_credit': 0, 'state': 'closed',
            'completion': None, 'archive': None})
        journal.save('runtime_report_attempts', {'parent_episode_id': parent.episode_id, 'decision_index': 12,
            'delivery_ref': 'engineering-delivery', 'child_episode_id': context.episode_id,
            'contract': canonical(contract), 'form': canonical({'requested_only': cells}), 'failure': None,
            'timing_receipts': None})
        key = 'fixture-run:fixture-parent:12:typed_form'
        repo.receive_cells(parent, cells, key)
        assert repo.received_cells(parent) == cells
        before = store.db.total_changes
        repo.receive_cells(parent, cells, key)
        assert store.db.total_changes == before
        with pytest.raises(ContractError, match='delivery_binding_mismatch'):
            repo.receive_cells(parent, [], key)
        store.db.execute("UPDATE literature_ratio_source_delivery_bindings SET cells_digest='forged'")
        with pytest.raises(ContractError, match='delivery_binding_mismatch'):
            repo.received_cells(parent)
    finally:
        store.close()


def test_provenance_ancestor_is_separate_from_direct_scientific_possession(tmp_path, monkeypatch):
    store, context, selection, native = native_case(tmp_path)
    try:
        ancestor = selection['source_ref']; image = native['result']['view']['input_source_ref']
        selection['source_ref'] = image
        context = replace(context, received_record_refs=tuple(ref for ref in context.received_record_refs if ref != ancestor))
        repo = repository(store, context); outcome = repo.populate(context, selection, 'descendant-only')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert ancestor in saved['input_source_refs']
        assert ancestor not in saved['direct_input_source_refs']
        assert saved['extraction']['sources'] == []
        selection['comparison']['subject'] = {'status': 'known', 'value': 'Synthetic enzyme', 'witnesses': [{
            'kind': 'text', 'source_ref': ancestor, 'representation': 'original',
            'start': 0, 'end': 16, 'quote': 'Synthetic enzyme'}]}
        monkeypatch.setattr(store, 'get_artifact', lambda *_: pytest.fail('ancestor bytes not possessed'))
        with pytest.raises(ContractError, match='not_received'):
            repo.populate(context, selection, 'unreceived-witness')
    finally:
        store.close()


def test_source_qualified_measurement_identity_is_not_equal_numeric_identity(tmp_path):
    store, context, selection, _ = native_case(tmp_path)
    try:
        row = selection['representations'][0]
        second = deepcopy(row); second['representation_id'] = 'same-value-different-locator'
        second['selection']['candidates'][0]['numerator']['region'] = [10, 10, 80, 30]
        for current in (row, second):
            candidate = current['selection']['candidates'][0]
            current['physical_measurement'] = {'status': 'known', 'value': 'source measurement',
                'witnesses': [deepcopy(candidate['numerator'])]}
            current['reference_measurement'] = {'status': 'known', 'value': 'shared reference',
                'witnesses': [deepcopy(candidate['denominator'])]}
        selection['representations'].append(second)
        repo = repository(store, context); outcome = repo.populate(context, selection, 'physical-identities')
        saved = repo.read(outcome['result']['sheet_ref']); measurements = saved['measurement_bindings']
        assert measurements[0]['input_measurement_ref'] != measurements[1]['input_measurement_ref']
        assert measurements[0]['reference_measurement_ref'] == measurements[1]['reference_measurement_ref']
        rows = repo.fact_cells(owned(context, outcome), [outcome['result']['sheet_ref']], components=['reported_ratio'])
        assert len(rows[0]['input_measurement_refs']) == 2 and len(rows[0]['reference_measurement_refs']) == 1
        assert rows[0]['independent_preparation_count'] is None
        assert rows[0]['value_candidates'] == [.64]
    finally:
        store.close()


def test_empty_subset_receipt_is_explicit_and_crossrun_context_rejects(tmp_path):
    store, context, selection, _ = native_case(tmp_path)
    try:
        repo = repository(store, context)
        repo.receive_cells(context, [], 'empty-engineering-receipt')
        assert repo.received_cells(context) == []
        assert store.db.execute('SELECT cells FROM literature_ratio_source_received').fetchone()[0] == '[]'
        with pytest.raises(ContractError, match='run_mismatch'):
            repo.validate_fact_values(replace(context, run_id='different-run'), [])
    finally:
        store.close()


@pytest.mark.parametrize('representation', ['original', 'text'])
def test_truthful_unicode_generic_text_locator_joins_native_v3(tmp_path, representation):
    store, context, selection, _ = native_case(tmp_path)
    try:
        raw = '<html><body>Engineering β enzyme</body></html>'.encode()
        projected = 'Engineering β enzyme'.encode()
        witness_source = store.put('source', {'provider': 'synthetic_engineering_html', 'accession': None,
            'uri': None, 'artifact_ref': store.artifact(raw), 'text_ref': store.artifact(projected),
            'request_ref': None, 'version': None, 'retrieved_at': None,
            'parent_source_refs': [selection['source_ref']]}, origin='caller')['id']
        data = raw if representation == 'original' else projected
        quote = 'β enzyme'; start = data.index(quote.encode())
        selection['comparison']['subject'] = {'status': 'known', 'value': quote, 'witnesses': [{
            'kind': 'text', 'source_ref': witness_source, 'representation': representation,
            'start': start, 'end': start + len(quote.encode()), 'quote': quote}]}
        context = replace(context, received_record_refs=(*context.received_record_refs, witness_source))
        repo = repository(store, context); outcome = repo.populate(context, selection, 'generic-span')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['version'] == 'literature_relative_signal_source_record_v3'
        assert saved['extraction']['version'] == 'relative_signal_source_extraction_v3'
        witness = saved['extraction']['comparison']['subject']['witnesses'][0]
        actual_source = store.get(witness_source)
        assert witness['authentication'] == 'exact_utf8_span'
        assert witness['locator'] == {'kind': 'text_span', 'source_ref': witness_source,
            'artifact_ref': actual_source['artifact_ref' if representation == 'original' else 'text_ref'],
            'representation': representation, 'start': start, 'end': start + len(quote.encode()), 'quote': quote}
        assert len(quote) != len(quote.encode())
        assert not {'section_id', 'paragraph_index', 'paragraph_text'} & witness['locator'].keys()
    finally:
        store.close()


def test_actual_jats_paragraph_locator_remains_distinct_from_generic_span(tmp_path):
    store, context, selection, _ = native_case(tmp_path)
    try:
        xml = b'<article><body><sec id="s1"><p>SyntheticProtein was expressed at 64% (V) of WT levels.</p></sec></body></article>'
        article = source(store, xml, parents=[selection['source_ref']], name='synthetic_engineering_jats')
        row = deepcopy(selection['representations'][0])
        row.update(representation_id='actual-jats-fixture-paragraph', kind='jats_percent', selection={
            'source_ref': article, 'section_id': 's1', 'paragraph_index': 0,
            'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'})
        selection['representations'].append(row)
        context = replace(context, received_record_refs=(*context.received_record_refs, article))
        repo = repository(store, context); outcome = repo.populate(context, selection, 'mixed-jats')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['sheet']['cells']['reported_ratio']['value'] == .64
        locator = saved['extraction']['representations'][1]['readings'][0]['numerator']['locator']
        assert locator['kind'] == 'jats' and locator['section_id'] == 's1' and locator['paragraph_index'] == 0
        assert locator['source_ref'] == article
        assert locator['paragraph_text'] == 'SyntheticProtein was expressed at 64% (V) of WT levels.'
    finally:
        store.close()


def test_actual_artifact_id_must_match_source_bytes_before_population(tmp_path):
    store, context, selection, _ = native_case(tmp_path, known=True)
    try:
        repo = repository(store, context)
        original = store.get(selection['source_ref'])['artifact_ref']
        original_bytes = store.get_artifact(original)
        replacement = store.artifact(original_bytes + b' Synthetic corruption preserving selected quoted spans.')
        replacement_row = store.get(replacement)
        store.db.execute('UPDATE artifacts SET sha256=?,size=? WHERE id=?',
            (replacement_row['sha256'], replacement_row['size'], original))
        with pytest.raises(ContractError, match='artifact_identity_mismatch'):
            repo.populate(context, selection, 'corrupt-input-bytes')
        assert store.db.execute('SELECT count(*) FROM literature_ratio_source_operations').fetchone()[0] == 0
        assert not store.list('observation')
    finally:
        store.close()


def test_saved_read_checks_original_artifact_metadata_without_source_bytes(tmp_path, monkeypatch):
    store, context, selection, _ = native_case(tmp_path, known=True)
    try:
        repo = repository(store, context); outcome = repo.populate(context, selection, 'saved-before-corruption')
        original = store.get(selection['source_ref'])['artifact_ref']
        store.db.execute('UPDATE artifacts SET sha256=? WHERE id=?', ('a' * 64, original))
        get = store.get_artifact
        def no_scientific_bytes(reference):
            assert reference != original
            return get(reference)
        monkeypatch.setattr(store, 'get_artifact', no_scientific_bytes)
        with pytest.raises(ContractError, match='artifact_identity_mismatch'):
            repo.read(outcome['result']['sheet_ref'])
    finally:
        store.close()


def test_calculation_identity_binds_all_three_actual_pure_modules_and_saved_history(tmp_path, monkeypatch):
    from gene_annotation_episode import literature_ratio_source_storage as storage
    store, context, selection, _ = native_case(tmp_path)
    try:
        repo = repository(store, context); outcome = repo.populate(context, selection, 'implementation-bound')
        saved = repo.read(outcome['result']['sheet_ref'])
        actual = json.loads(store.get_artifact(saved['calculation_artifact_ref']))
        modules = ('literature_ratio_source_inputs.py', 'literature_ratio_source_calculations.py',
            'literature_ratio_source_validation.py')
        descriptor = {'version': 'relative_signal_calculator_implementation_v1', 'modules': {
            name: hashlib.sha256(Path(storage.__file__).with_name(name).read_bytes()).hexdigest() for name in modules}}
        assert actual['calculator_implementation_sha256'] == hashlib.sha256(canonical(descriptor).encode()).hexdigest()
        assert actual['calculator_implementation_sha256'] != descriptor['modules']['literature_ratio_source_calculations.py']
        monkeypatch.setattr(storage, '_calculator_implementation_descriptor', lambda: pytest.fail('historical current-code rehash'))
        assert repo.read(outcome['result']['sheet_ref']) == saved
        assert repo.populate(context, selection, 'implementation-bound') == outcome
    finally:
        store.close()


def multi_source_view_case(path):
    """Engineering-only multiple sources/views; original arrays intentionally unsorted."""
    store, context, selection, first = native_case(path)
    root = selection['source_ref']
    witnesses = sorted([source(store, b'Synthetic subject witness', parents=[root]),
        source(store, b'Synthetic genotype witness', parents=[root])])
    received = list(context.received_record_refs) + witnesses
    for key, reference in [('subject', witnesses[1]), ('genotype', witnesses[0])]:
        raw = store.get_artifact(store.get(reference)['artifact_ref'])
        quote = raw.decode()
        selection['comparison'][key] = {'status': 'known', 'value': quote,
            'witnesses': [{'kind': 'text', 'source_ref': reference, 'representation': 'original',
                'start': 0, 'end': len(raw), 'quote': quote}]}
    image = Image.new('RGB', (240, 100), 'white')
    draw = ImageDraw.Draw(image); draw.text((10, 40), '0.64', fill='black'); draw.text((110, 40), '1.00', fill='black')
    draw.rectangle((5, 5, 7, 7), fill='blue')
    buffer = BytesIO(); image.save(buffer, format='PNG')
    second_source = source(store, buffer.getvalue(), parents=[root])
    args = {'source_ref': second_source}
    second = ToolRegistry(store).execute('image.view', args, scope=plain(context.scope),
        operation_key='fixture-run:fixture-child:6')
    assert second['status'] == 'completed', second
    second_view = second['result']['view']
    Journal(store, context.run_id).save('runtime_actions', {'episode_id': context.episode_id,
        'decision_index': 6, 'action': canonical({'kind': 'tool', 'tool': 'image.view', 'arguments': args}),
        'result': canonical(second), 'credit': None, 'timing': None})
    received.extend((second_source, second_view['id'], second_view['source_ref']))
    original_row = selection['representations'][0]
    extra = deepcopy(original_row); extra['representation_id'] = 'z-second-view'
    def rebind(value):
        if isinstance(value, dict):
            return {key: second_view['id'] if key == 'view_ref' else rebind(child) for key, child in value.items()}
        if isinstance(value, list): return [rebind(child) for child in value]
        return value
    extra = rebind(extra)
    xml = b'<article><body><sec id="s1"><p>SyntheticProtein was expressed at 64% (V) of WT levels.</p></sec></body></article>'
    article = source(store, xml, parents=[root], name='synthetic_engineering_jats')
    received.append(article)
    prose = deepcopy(original_row)
    prose.update(representation_id='m-jats', kind='jats_percent', selection={
        'source_ref': article, 'section_id': 's1', 'paragraph_index': 0,
        'expected_subject': 'SyntheticProtein', 'variant': 'V', 'reference_literal': 'WT levels'})
    alias = deepcopy(original_row); alias['representation_id'] = 'a-shared-custody-alias'
    # Array order is scientific selection order, not a dependency-sort request.
    selection['representations'] = [extra, prose, original_row, alias]
    context = replace(context, received_record_refs=tuple(dict.fromkeys(received)))
    return store, context, selection, (first, second)


def reverse_object_keys(value):
    if isinstance(value, dict):
        return {key: reverse_object_keys(child) for key, child in reversed(list(value.items()))}
    if isinstance(value, list): return [reverse_object_keys(child) for child in value]
    return value


def test_multisource_multiview_canonical_store_read_replay_preserves_scientific_arrays(tmp_path, monkeypatch):
    store, context, selection, views = multi_source_view_case(tmp_path)
    try:
        repo = repository(store, context)
        original_order = [row['representation_id'] for row in selection['representations']]
        outcome = repo.populate(context, selection, 'multi-source-view')
        saved = repo.read(outcome['result']['sheet_ref'])
        assert saved['sheet']['cells']['reported_ratio']['value'] == .64
        assert [row['representation_id'] for row in saved['extraction']['representations']] == original_order
        assert [row['representation_id'] for row in saved['selection']['representations']] == original_order
        dependencies = [(row['source_ref'], row['representation']) for row in saved['extraction']['sources']]
        assert len(dependencies) == 3 and dependencies == sorted(set(dependencies))
        view_refs = [row['view_ref'] for row in saved['extraction']['views']]
        assert len(view_refs) == 2 and view_refs == sorted(set(view_refs))
        assert set(saved['input_view_refs']) == {view['result']['view_ref'] for view in views}
        assert set(saved['direct_input_source_refs']) <= set(saved['input_source_refs'])
        expected_sources = {selection['source_ref'], *(source_ref for source_ref, _ in dependencies),
            *(view['result']['view']['source_ref'] for view in views),
            *(view['result']['view']['input_source_ref'] for view in views)}
        assert set(saved['direct_input_source_refs']) == expected_sources
        assert saved['sheet']['independent_preparation_count'] is None
        reordered = repo.populate(context, reverse_object_keys(selection), 'object-reordered-new-work')
        reordered_saved = repo.read(reordered['result']['sheet_ref'])
        assert reordered_saved['extraction'] == saved['extraction']
        assert reordered_saved['sheet'] == saved['sheet']
        reordered_array = deepcopy(selection)
        reordered_array['representations'].reverse()
        changed_array = repo.populate(context, reordered_array, 'array-reordered-new-work')
        changed_saved = repo.read(changed_array['result']['sheet_ref'])
        assert [row['representation_id'] for row in changed_saved['extraction']['representations']] == original_order[::-1]
        assert changed_saved['extraction']['sources'] == saved['extraction']['sources']
        assert changed_saved['extraction']['views'] == saved['extraction']['views']
        # Canonical publication changes object order; it must not change arrays,
        # source/view custody, meanings, native readings or the original outcome.
        roundtrip = json.loads(canonical(saved))
        assert roundtrip == saved
        allowed = {store.get(outcome['result']['sheet_ref'])['artifact_ref'],
            store.get(outcome['result']['sheet_ref'])['request_ref'], saved['calculation_artifact_ref'],
            *(store.get(view['result']['view']['source_ref'])['request_ref'] for view in views)}
        get = store.get_artifact
        def saved_artifacts_only(reference):
            assert reference in allowed
            return get(reference)
        monkeypatch.setattr(store, 'get_artifact', saved_artifacts_only)
        import gene_annotation_episode.literature_ratio_source_inputs as inputs
        import gene_annotation_episode.literature_ratio_source_calculations as calculations
        monkeypatch.setattr(inputs, 'read_relative_signal_source_inputs', lambda *_a, **_k: pytest.fail('reader replay'))
        monkeypatch.setattr(calculations, 'populate_relative_signal_v2', lambda *_a, **_k: pytest.fail('calculator replay'))
        before = store.db.total_changes
        assert repo.populate(context, reverse_object_keys(selection), 'multi-source-view') == outcome
        assert repo.read(outcome['result']['sheet_ref']) == saved
        assert store.db.total_changes == before
    finally:
        store.close()
