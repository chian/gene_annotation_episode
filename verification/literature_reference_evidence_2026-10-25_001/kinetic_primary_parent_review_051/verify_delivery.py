"""Independent mechanical audit of the already interpreted051 example.

No harness rerun, scientific conversion, provider history or source reacquisition.
All executable repository reads use the original immutable execution pin.
"""
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
OWNER = BASE / 'a105_kinetic_primary_example_051'
RUN = OWNER / 'controlled_005'
PIN = RUN / 'pin'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def main():
    manifest = load(OWNER / 'FINAL_MANIFEST_001.json')
    for relative, row in manifest.items():
        assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
        path = OWNER / relative
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], relative
    pin_manifest = load(RUN / 'PIN_MANIFEST.json')
    names = set(pin_manifest['files'])
    for relative, row in pin_manifest['files'].items():
        path = PIN / relative
        assert path.stat().st_size == row['bytes'] and digest(path) == row['sha256'], relative
    assert {p.relative_to(PIN).as_posix() for p in PIN.rglob('*') if p.is_file()} == names
    for name in ('run_example.py', 'launch_example.py'):
        assert digest(OWNER / name) == digest(PIN / name)
    terminal = load(RUN / 'TERMINAL_RECEIPT.json')
    assert terminal['exit_code'] == 0 and terminal['pin_unchanged']
    assert terminal['pin_manifest_sha256'] == digest(RUN / 'PIN_MANIFEST.json')
    assert terminal['configured_model_run'] is False
    custody = load(RUN / 'SOURCE_CUSTODY.json')
    original = BASE / 'a105_specificity_case_038'
    assert {p.relative_to(original).as_posix(): digest(p) for p in original.rglob('*') if p.is_file()} == custody['original_sources']

    sys.path.insert(0, str(PIN))
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
    from gene_annotation_episode.episode_services import WorkflowServices
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.tools import ToolRegistry
    from types import SimpleNamespace
    import gene_annotation_episode.literature_kinetic_storage as storage
    assert Path(storage.__file__).resolve() == PIN / 'gene_annotation_episode/literature_kinetic_storage.py'
    # Construct only the read facade. Avoid the ordinary writable Store initializer.
    store = Store.__new__(Store)
    store.path = RUN / 'state'
    store._savepoint = 0
    store.db = sqlite3.connect((store.path / 'state.sqlite3').resolve().as_uri() + '?mode=ro', uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    store.db.create_function('library_scope_record', 2, store._scope_filter_record)
    before = list(store.db.iterdump())
    source_artifacts = {custody[name]['artifact_ref'] for name in ('primary', 'decoded_primary_table')}
    get_artifact = store.get_artifact
    forbidden_calls = []
    def forbidden(*args, **kwargs):
        forbidden_calls.append(True)
        raise AssertionError('Forbidden primary artifact, scientific recomputation or new receipt')
    store.get_artifact = lambda ref: forbidden() if ref in source_artifacts else get_artifact(ref)
    storage.read_kinetic_inputs = storage.populate_kinetic_contrast = forbidden
    result = load(RUN / 'RESULT.json')
    repo = storage.LiteratureKineticRepository(store, result['run_id'])
    repo.populate = repo.receive_cells = forbidden
    operations = [dict(r) for r in store.db.execute('SELECT * FROM literature_kinetic_operations ORDER BY rowid')]
    assert len(operations) == 2
    outcomes = [json.loads(r['outcome']) for r in operations]
    sheets = [repo.read(o['result']['sheet_ref']) for o in outcomes]
    assert sheets == [load(RUN / ('SHEET_' + alternative + '.json')) for alternative in ('IMP', 'FBP')]
    typed = load(RUN / 'TYPED_PARENT_RETURN.json')
    admission, = [dict(r) for r in store.db.execute('SELECT * FROM literature_kinetic_received')]
    assert json.loads(admission['cells']) == typed['numbers']
    parent = BindingContext(result['run_id'], admission['episode_id'], 'annotation',
        (('annotation', 'root'),), store.validate_scope(), {}, {}, tuple(dict.fromkeys(
        [custody['primary']['id'], custody['decoded_primary_table']['id'],
         *(ref for outcome in outcomes for ref in outcome['record_refs'])])))
    assert repo.received_cells(parent) == typed['numbers']
    host = SimpleNamespace(store=store, run_id=result['run_id'], tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    assert binding.received_report_facts(parent)['literature_kinetic_cells'] == typed['numbers']
    actions = [json.loads(r[0]) for r in store.db.execute('SELECT action FROM runtime_actions ORDER BY rowid')]
    observation_count = store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0]
    assert len(actions) == observation_count == 4
    assert [a['kind'] for a in actions].count('tool') == 2
    assert {a.get('tool') for a in actions if a['kind'] == 'tool'} == {'literature.kinetic.populate'}
    assert result['actual_credit'] == 0.0 and len(typed['numbers']) == 10
    for sheet, denominator in zip(sheets, (.0027, .025)):
        cells = sheet['cells']
        assert cells['numerator_parameter']['value'] == 42
        assert cells['denominator_parameter']['value'] == denominator
        assert math.isclose(cells['parameter_ratio']['value'], 42 / denominator)
        assert math.isclose(cells['log_parameter_contrast']['value'], math.log(42 / denominator))
        assert sheet['calculation']['model'] is None
        assert sheet['extraction']['comparison']['nonintended_conditions_relationship']['value'] == 'different'
    assert sheets[0]['calculation']['inputs']['numerator'] == sheets[1]['calculation']['inputs']['numerator']
    assert list(store.db.iterdump()) == before and not forbidden_calls
    store.close()
    receipt = {'passed': True, 'owner_manifest_entries': len(manifest), 'execution_pin_files': len(names),
        'original038_files_unchanged': True, 'saved_sheets': len(sheets), 'typed_rows': len(typed['numbers']),
        'actual_observations': observation_count, 'actual_credit': result['actual_credit'],
        'direct_sqlite_mode_ro_before_any_repository_read': True,
        'primary_artifact_reader_calculator_receive_forbidden': True, 'whole_sql_unchanged': True,
        'shared_numerator_operand_preserved': True, 'configured_model_run': False,
        'scope': 'Mechanical same-case audit; no new paper interpretation or full A105 completion',
        'owner_manifest_sha256': digest(OWNER / 'FINAL_MANIFEST_001.json'),
        'pin_manifest_sha256': digest(RUN / 'PIN_MANIFEST.json')}
    with (OUT / 'RECEIPT_001.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
