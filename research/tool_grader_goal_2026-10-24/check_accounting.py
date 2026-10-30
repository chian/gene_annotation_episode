"""Read-only inventory integrity checks; no goal or scientific runtime validation."""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
s = json.loads((HERE / 'SCOPE.json').read_text())
w = json.loads((HERE / 'WORK_STATUS.json').read_text())
a = json.loads((HERE / 'SOURCE_ALIASES.json').read_text())
c = json.loads((HERE / 'COVERAGE.json').read_text())

rows = {x['id']: x for x in s['rows']}
assert len(rows) == len(s['rows']) == len(w['rows'])
assert set(rows) == {x['id'] for x in w['rows']}
assert {x['id'] for x in s['resource_bindings']} == {x['id'] for x in w['resource_bindings']}
assert len({x['id'] for x in a['rows']}) == len(a['rows'])
alias = {x['id']: x for x in a['rows']}
for r in rows.values():
    for id in r['source_alias_ids']:
        assert r['id'] in alias[id]['requirement_row_ids']
    if r['parent_row_id']:
        assert r['parent_row_id'] in rows
for r in a['rows']:
    for id in r['requirement_row_ids']:
        assert r['id'] in rows[id]['source_alias_ids']
for b in s['resource_bindings']:
    r = rows[b['requirement_row_id']]
    assert b['id'] in r['resource_binding_ids']
    assert not (b['resource_route'] == 'local' and r['scientific_mode'] == 'database_identification')
for r in w['rows']:
    assert set(w['columns']) <= r.keys()

b_expected = c['explicit_B_function_names']
assert set(b_expected) == {r['name'] for r in rows.values() if r['section'] == 'B'}
d_expected = c['explicit_D_collection_names']
assert set(d_expected) == {r['name'] for r in rows.values() if r['kind'] == 'bvbrc_data_collection'}
assert set(c['explicit_C_service_identifiers']) == {name for r in rows.values()
    if r['kind'] == 'bvbrc_service_family' for name in r['source_names']}
assert len([r for r in rows.values() if r['kind'] == 'bvbrc_service_family']) == 25
wrapper_expected = {r['name'] for r in rows.values() if r['kind'] in {
    'named_acquisition_wrapper_contract', 'restricted_entrez_wrapper_contract'}}
assert wrapper_expected == set(c['explicit_E_wrapper_names'])
assert {r['scientific_mode'] for r in rows.values() if r['requirement']['line'] == 63} == {'map-ont', 'map-pb', 'map-hifi', 'lr:hq', 'map-iclr', 'sr'}
assert len([r for r in rows.values() if r['requirement']['line'] == 61]) == 6
assert len([r for r in rows.values() if r['requirement']['line'] == 62]) == 2
assert len([r for r in rows.values() if r['scientific_mode'] == 'two_sequence_correspondence']) == 5
assert len([r for r in rows.values() if r['scientific_mode'] == 'database_identification']) == 11
assert len([r for r in rows.values() if r['kind'] == 'bounded_molecular_data_provider']) == 47
assert len(c['scope_bullet_coverage']) == 154
assert all(x['covered'] and x['requirement_row_ids'] for x in c['scope_bullet_coverage'])
assert c['counts']['rows_by_kind'] == dict(Counter(r['kind'] for r in rows.values()))
assert c['counts']['rows_by_section'] == dict(Counter(r['section'] for r in rows.values()))
assert c['counts']['rows_by_scope_disposition'] == dict(Counter(r['scope_disposition'] for r in rows.values()))
assert c['counts']['scope_rows_total'] == len(rows)
assert c['counts']['source_alias_observations'] == len(a['rows'])
assert c['counts']['intended_resource_binding_rows'] == len(s['resource_bindings'])
assert len(a['rows']) == a['historical_index_observation_count'] + a['added_collection_source_rows'] + a['added_group_source_rows'] + a['expanded_literal_source_alias_rows']
listing = c['active_listing']
for group, identities in listing['entries'].items():
    assert len(identities) == len(set(identities)) == listing['counts'][group]
    assert all(identity in rows for identity in identities)
    assert all(rows[identity]['scope_disposition'] in {'required', 'required_when_needed'} for identity in identities)
for row in rows.values():
    for identity in row.get('canonical_row_ids', []):
        assert identity in rows and identity != row['id']
    if row['scope_disposition'] == 'alias_of_existing_operation':
        assert row.get('canonical_row_ids')
history = Counter()
for m in s['source_manifest']:
    source = ROOT / m['path']
    if source.suffix.lower() not in {'.json', '.py'}:
        continue
    if not source.is_file():
        history['unavailable'] += 1
    elif hashlib.sha256(source.read_bytes()).hexdigest() == m['sha256']:
        history['matches'] += 1
    else:
        history['differs'] += 1
print(f"PASS: stable inventory identities, source backlinks, resource relationships and reconciled listing counts. "
      f"Historical code/data hashes: {dict(history)}. Scientific completion was not tested.")
