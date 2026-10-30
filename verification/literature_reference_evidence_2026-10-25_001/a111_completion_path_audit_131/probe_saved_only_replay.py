"""Reopen the synthetic probe and prohibit every original scientific read."""
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_structure_storage import LiteratureStructureRepository
import gene_annotation_episode.literature_structure_storage as structural
from gene_annotation_episode.state import Store

output = Path(__file__).resolve().parent
with Store(output / 'synthetic_probe_state_003') as store:
    operation = store.db.execute('SELECT * FROM literature_structure_operations').fetchone()
    run_id, owner = operation['run_id'], operation['episode_id']
    outcome = json.loads(operation['outcome'])
    repo = LiteratureStructureRepository(store, run_id)
    sheet_ref = outcome['result']['sheet_ref']
    source = store.get(sheet_ref)
    request = json.loads(store.get_artifact(source['request_ref']))
    before = repo.read(sheet_ref)
    rows = repo.project_cells([sheet_ref], permitted_record_refs=outcome['record_refs'],
        components=['source_geometry_positive'])
    context = BindingContext(run_id, owner, 'literature_strategy',
        (('literature_strategy', 'synthetic_probe'),), request['scope'], {}, {},
        tuple(before['direct_input_source_refs']))
    allowed = {source['artifact_ref'], source['request_ref']}
    artifact_read = store.get_artifact
    read_refs = []
    def saved_only(reference):
        assert reference in allowed, 'attempted original scientific source read'
        read_refs.append(reference)
        return artifact_read(reference)
    def forbidden(*args, **kwargs):
        raise AssertionError('replay attempted parsing or calculation')
    structural.read_structure_inputs = forbidden
    structural.populate_source_geometry = forbidden
    store.get_artifact = saved_only
    store.db.execute('PRAGMA query_only=ON')
    changes = store.db.total_changes
    assert repo.populate(context, request['arguments'], operation['operation_key']) == outcome
    assert repo.read(sheet_ref) == before
    assert repo.project_cells([sheet_ref], permitted_record_refs=outcome['record_refs'],
        components=['source_geometry_positive']) == rows
    receiver_rows = []
    for episode, in store.db.execute('SELECT DISTINCT episode_id FROM literature_structure_received'):
        receiver = replace(context, episode_id=episode)
        received = repo.received_cells(receiver)
        assert received == rows
        receiver_rows.append({'count': len(received), 'exact_original_subset': True})
    assert len(receiver_rows) == 2
    result = {'origin': 'synthetic_fixture', 'actual_model_inference': False,
        'primary_paper_read': False, 'original_scientific_reads_allowed': False,
        'parser_or_calculator_allowed': False, 'operation_replay_identical': True,
        'saved_payload_identical': True, 'selected_projection_identical': True,
        'typed_receivers': receiver_rows, 'saved_artifact_read_count': len(read_refs),
        'query_only': 1, 'changes_during_replay': store.db.total_changes - changes}
    assert result['changes_during_replay'] == 0
(output / 'SYNTHETIC_SAVED_ONLY_REPLAY.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
