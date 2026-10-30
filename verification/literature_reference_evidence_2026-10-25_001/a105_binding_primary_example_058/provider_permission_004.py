"""Actual provider presentation of the original derived-only C4 receipt.

This is an engineering presentation probe from an actually admitted original
form, not another Episode or experiment and not a configured model call.
It imports the immutable native003 pin and never changes the closed C4 state.
"""
import asyncio
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PIN = HERE / 'pin_003'
sys.path.insert(0, str(PIN))
import run_primary_003 as h

def load(path): return json.loads(path.read_bytes())

def main():
    assert Path(__file__).stat().st_mode & 0o222 == 0, 'Seal this additive probe before execution'
    h.verify_pin()
    out = HERE / 'provider_permission_run_004'; out.mkdir(exist_ok=False)
    c4 = HERE / 'run_003'
    spec = load(c4 / 'C4_ORIGINAL_COMMISSION.json')
    admitted = load(c4 / 'C4_ADMISSION.json')
    returned = load(c4 / 'C4_ORIGINAL_RETURN.json')
    assert spec['child']['request']['message']['episode_assignment']['requested_binding_interaction_components'] == ['interaction_ratio']
    assert admitted['report'] == returned['form']
    rows = admitted['report']['numbers']
    assert len(rows) == 1 and rows[0]['component'] == 'interaction_ratio'
    for role in h.ROLES:
        assert rows[0]['roles'][role]['values']['delivery_status'] == 'not_requested'
        assert all(value is None for key, value in rows[0]['roles'][role]['values'].items() if key != 'delivery_status')
    store = h.Store.__new__(h.Store); store.path = c4 / 'c4_state'; store._savepoint = 0
    store.db = sqlite3.connect((store.path / 'state.sqlite3').resolve().as_uri()+'?mode=ro', uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    try:
        before = list(store.db.iterdump())
        try: store.db.execute('CREATE TABLE forbidden004(n)')
        except sqlite3.OperationalError as exc: assert 'readonly' in str(exc).lower()
        else: raise AssertionError('Expected read-only connection')
        row = store.db.execute('SELECT * FROM runtime_episodes WHERE episode_id=?', (spec['parent']['episode_id'],)).fetchone()
        refs = spec['child']['request']['message']['episode_assignment']['source_refs']
        known = list(dict.fromkeys([*refs, *admitted['received_record_refs']]))
        parent = h.context_from_saved(store, spec['run_id'], row, known)
        artifacts = {store.get(ref)[key] for ref in refs for key in ('artifact_ref', 'text_ref') if store.get(ref).get(key)}
        original_get = store.get_artifact
        original_open = Path.open
        denied = {(PIN / 'inputs' / name).resolve() for name in ('primary.html', 'primary_text.txt', 'table3.jpg')}
        denied.update((store.path / 'artifacts' / ref.removeprefix('artifact_')[:2] / ref.removeprefix('artifact_')).resolve() for ref in artifacts)
        def guarded_open(path, *args, **kwargs):
            if path.resolve() in denied: return h.forbidden()
            return original_open(path, *args, **kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'open', guarded_open))
            stack.enter_context(patch.object(store, 'get_artifact', lambda ref: h.forbidden() if ref in artifacts else original_get(ref)))
            for name in ('read_binding_interaction_inputs', 'populate_binding_interaction'):
                stack.enter_context(patch('gene_annotation_episode.literature_binding_interaction_storage.'+name, h.forbidden))
            stack.enter_context(patch.object(h.Image, 'open', h.forbidden))
            stack.enter_context(patch.object(h.LiteratureBindingInteractionRepository, 'receive_cells', h.forbidden))
            stack.enter_context(patch.object(h.ScientificFindingProgress, '__call__', h.forbidden))
            services, _ = h.service_binding(store, parent)
            binding = h.LiteratureEpisodes(services, rate_population=True, reference_parent_sources=refs)
            facts = binding.received_report_facts(parent)['literature_binding_interaction_cells']
            assert facts == rows
            state = {'goal': json.loads(row['request'])['goal'], 'scope': h.plain(parent.scope),
                **binding.initial_decision_context(parent), 'child_reports': [admitted['report']],
                'working_state': {'references': [store.get(ref) for ref in known if store.get(ref)['record_type'] == 'reference']},
                'available_report_facts': binding.received_report_sources('annotation'),
                'requested_form': {}, 'current_report_update': {}, 'current_report_basis_refs': [],
                'current_credit': 0, 'last_local_outcome': None, 'feedback': None}
            wire = h.LiteratureWire(out / 'wire')
            asyncio.run(wire.complete(parent.episode_id, 'REASONING',
                'Inspect the original admitted source evidence in its assigned scope.\n'+h.INSTRUCTIONS,
                h.state_frame(state), h.obj({'fixture': {'const': True}})))
            rendered = wire.turns[0]['input'][0]['text']
            assert 'Admitted requested binding interaction components' in rendered and '10.3125' in rendered
            for value in ('32 ± 2', '17 ± 3', '11 ± 1', '>510', '>740', '36.339285714285715'):
                assert value not in rendered, value
            (out / 'ACTUAL_PROVIDER_TEXT.txt').write_text(rendered)
            assert list(store.db.iterdump()) == before
        receipt = {'passed': True, 'scope': 'Original C4 derived-only permission/presentation engineering probe',
            'original_assignment_components': ['interaction_ratio'], 'original_admitted_native_rows': 1,
            'unrequested_raw_fields_null': True, 'actual_complete_and_turn_boundary': True,
            'mode_ro_before_first_projection': True, 'whole_sql_unchanged': True,
            'original_source_image_reader_calculator_receive_reprice_forbidden': True,
            'provider_raw_numeric_witnesses_masked': True, 'actual_configured_model_called': False,
            'new_episodes': 0, 'new_observations': 0, 'probe_code_sha256': h.sha(Path(__file__)),
            'native_pin_manifest_sha256': h.sha(PIN / 'PIN_MANIFEST.json'),
            'original_commission_sha256': h.sha(c4 / 'C4_ORIGINAL_COMMISSION.json'),
            'original_return_sha256': h.sha(c4 / 'C4_ORIGINAL_RETURN.json'),
            'text_sha256': hashlib.sha256(rendered.encode()).hexdigest(),
            'limit': 'Raw source documents remain available for later explicit selected access; numeric-return withholding is not permanent source secrecy. The main sixteen-row parent has already received raw cells; its filtered probe demonstrates presentation formatting only.'}
        (out / 'RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
        print(json.dumps(receipt))
    finally: store.db.close()

if __name__ == '__main__':
    main()
