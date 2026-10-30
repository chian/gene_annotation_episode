"""Independent saved-only audit of the original long051 nominations."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

OUT = Path(__file__).resolve().parent
OWNER = OUT.parent / 'a105_kinetic_primary_example_051'
RUN = OWNER / 'controlled_long_001'
PIN = RUN / 'pin'


def load(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    terminal = load(RUN / 'TERMINAL_RECEIPT.json')
    assert terminal['exit_code'] == 0 and terminal['pin_manifest_sha256'] == digest(RUN / 'PIN_MANIFEST.json')
    manifest = load(RUN / 'PIN_MANIFEST.json')
    for name, row in manifest['files'].items():
        assert (PIN / name).stat().st_size == row['bytes'] and digest(PIN / name) == row['sha256'], name
    assert {p.relative_to(PIN).as_posix() for p in PIN.rglob('*') if p.is_file()} == set(manifest['files'])
    preserved = load(RUN / 'PRESERVATION_BEFORE.json')
    assert all(digest(OWNER / name) == expected for name, expected in preserved.items())
    original = load(OWNER / 'controlled_001/SOURCE_SELECTIONS.json')
    assert load(RUN / 'SOURCE_SELECTIONS.json') == original == load(PIN / 'original_source_selections_001.json')
    custody = load(RUN / 'SOURCE_CUSTODY.json')
    typed, result = load(RUN / 'TYPED_PARENT_RETURN.json'), load(RUN / 'RESULT.json')
    sheets = [load(RUN / ('SHEET_' + alternative + '.json')) for alternative in ('IMP', 'FBP')]
    sys.path.insert(0, str(PIN))
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
    from gene_annotation_episode.episode_services import WorkflowServices
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.tools import ToolRegistry
    import gene_annotation_episode.literature_kinetic_storage as storage
    assert Path(storage.__file__).resolve() == PIN / 'gene_annotation_episode/literature_kinetic_storage.py'
    store = Store.__new__(Store)
    store.path, store._savepoint = RUN / 'state', 0
    store.db = sqlite3.connect((store.path / 'state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    before = list(store.db.iterdump())
    forbidden_calls = []
    def forbidden(*a, **kw):
        forbidden_calls.append(True)
        raise AssertionError('Forbidden source read or scientific recomputation/receipt')
    get = store.get_artifact
    source_artifacts = {custody[name]['artifact_ref'] for name in ('primary', 'decoded_primary_table')}
    store.get_artifact = lambda ref: forbidden() if ref in source_artifacts else get(ref)
    storage.read_kinetic_inputs = storage.populate_kinetic_contrast = forbidden
    repo = storage.LiteratureKineticRepository(store, result['run_id'])
    repo.populate = repo.receive_cells = forbidden
    outcomes = [json.loads(row[0]) for row in store.db.execute('SELECT outcome FROM literature_kinetic_operations ORDER BY rowid')]
    assert len(outcomes) == 2 and [repo.read(o['result']['sheet_ref']) for o in outcomes] == sheets
    admission, = list(store.db.execute('SELECT * FROM literature_kinetic_received'))
    parent = BindingContext(result['run_id'], admission['episode_id'], 'annotation', (('annotation', 'root'),),
        store.validate_scope(), {}, {}, tuple(dict.fromkeys([custody['primary']['id'], custody['decoded_primary_table']['id'],
        *(ref for outcome in outcomes for ref in outcome['record_refs'])])))
    assert repo.received_cells(parent) == typed['numbers'] == json.loads(admission['cells'])
    host = SimpleNamespace(store=store, run_id=result['run_id'], tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    assert binding.received_report_facts(parent)['literature_kinetic_cells'] == typed['numbers']
    anchor_lengths = []
    for alternative, saved in zip(('IMP', 'FBP'), sheets):
        assert saved['selection'] == original[alternative]
        bounded = load(OWNER / 'controlled_005' / ('SHEET_' + alternative + '.json'))
        assert saved['cells'] == bounded['cells']
        assert saved['calculation']['physical_measurement_ids'] == bounded['calculation']['physical_measurement_ids']
        for role in ('numerator', 'denominator'):
            witness = original[alternative][role]['context']['conditions']
            record = store.get(saved['role_bindings'][role]['context']['conditions'])
            anchor = record['anchor']
            assert {k: anchor[k] for k in ('source_ref', 'start', 'end', 'quote')} == {k: witness[k] for k in ('source_ref', 'start', 'end', 'quote')}
            assert len(anchor['quote']) > 512 and len(record['label']) == 512
            assert record['label'].startswith('[source witness preview] ') and record['label'].endswith('…')
            assert saved['calculation']['inputs'][role]['context']['conditions'] == anchor['quote']
            # Mechanical byte check only; no reader or new scientific interpretation.
            sha = anchor['artifact_ref'].removeprefix('artifact_')
            raw = (RUN / 'state/artifacts' / sha[:2] / sha).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == sha
            assert raw[anchor['start']:anchor['end']].decode() == anchor['quote']
            anchor_lengths.append(len(anchor['quote']))
    observations = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
    assert observations == store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 4
    assert len(typed['numbers']) == 10 and result['actual_credit'] == 0.0
    assert list(store.db.iterdump()) == before and not forbidden_calls
    store.close()
    receipt = {'passed': True, 'execution_pin_files': len(manifest['files']), 'historical005_and_manifest_files_preserved': len(preserved),
        'original001_nominations_exact': True, 'full_anchor_lengths': anchor_lengths, 'display_labels_only_bounded': True,
        'original_physical_ids_and_native_cells_preserved': True, 'typed_rows': 10, 'actual_observations': observations,
        'actual_credit': 0.0, 'direct_mode_ro_saved_only_reconstruction': True, 'full_sql_unchanged': True,
        'pin_manifest_sha256': digest(RUN / 'PIN_MANIFEST.json'), 'configured_model_execution': False}
    with (OUT / 'LONG_WITNESS_RECEIPT_002.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
