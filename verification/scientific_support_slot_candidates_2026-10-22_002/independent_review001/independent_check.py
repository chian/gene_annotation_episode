"""Independently inspect a sealed review draft; write only to this script's directory."""
from pathlib import Path
import collections, csv, hashlib, json

REPO = Path('/home/chia/repos/gene_annotation_episode')
DRAFT = Path('/tmp/scientific-support-slot-draft-20261022-001')
REPORT = Path(__file__).resolve().parent
assert REPORT != DRAFT

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def read(path):
    return json.loads(path.read_text())

def pointer(value, selector):
    assert selector == '' or selector.startswith('/')
    if not selector:
        return value
    for piece in selector[1:].split('/'):
        piece = piece.replace('~1', '/').replace('~0', '~')
        value = value[int(piece)] if isinstance(value, list) else value[piece]
    return value

def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from all_strings(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from all_strings(child)

def original(source):
    path = REPO / source['corpus_path']
    selector = source['line_or_selector']
    if type(selector) is int:
        document = json.loads(path.read_text().splitlines()[selector - 1])
        return document, document
    document = read(path)
    return document, pointer(document, selector or '')

def files_snapshot():
    return {str(path.relative_to(DRAFT)): {'sha256': sha(path), 'bytes': path.stat().st_size}
            for path in sorted(DRAFT.rglob('*')) if path.is_file()}

baseline = files_snapshot()
manifest = read(DRAFT / 'output_manifest.json')
assert len({item['path'] for item in manifest['files']}) == len(manifest['files'])
assert not any(path.is_symlink() for path in DRAFT.rglob('*'))
expected = {}
for item in manifest['files']:
    relative = Path(item['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    expected[str(relative)] = {'sha256': item['sha256'], 'bytes': item['bytes']}
assert {k: v for k, v in baseline.items() if k != 'output_manifest.json'} == expected

inputs = read(DRAFT / 'input_manifest.json')['files']
assert len({item['path'] for item in inputs}) == len(inputs)
for item in inputs:
    path = Path(item['path'])
    path = path if path.is_absolute() else REPO / path
    assert sha(path) == item['file_sha256'], item['path']
input_paths = {str(Path(item['path']) if Path(item['path']).is_absolute() else REPO / item['path']) for item in inputs}

crosswalk_path = REPO / 'docs/SCIENTIFIC_SUPPORT_CASE_CROSSWALK_2026-10-21_002.json'
crosswalk = read(crosswalk_path)
case_rows = crosswalk['case_rows']
assert len(case_rows) == len({row['case_group'] for row in case_rows}) == 142
records = []
for case_row in case_rows:
    for source in case_row['record_sources']:
        document, record = original(source)
        assert digest(record) == source['original_record_sha256']
        assert str(REPO / source['corpus_path']) in input_paths
        records.append({'case_group': case_row['case_group'], 'case_id': source['case_id'],
                        'path': source['corpus_path'], 'selector': source['line_or_selector'],
                        'sha256': digest(record)})
assert len(records) == 149
contrast_count = sum(len(row['support_contrasts']) for row in case_rows)
assert contrast_count == 163

from gene_annotation_episode.scientific_support_metadata import validate_support_entry
entries = {path.stem: read(path) for path in sorted((DRAFT / 'entries').glob('*.json'))}
assert set(entries) == {f'A{number}' for number in range(101, 112)}
for entry_id, entry in entries.items():
    assert entry['id'] == entry_id and validate_support_entry(entry) == entry
    for operand in entry['support']['operands']:
        assert not ('direct' in operand['applicabilities'] and 'inferred_extent' in operand['extent_bases'])

catalog = read(DRAFT / 'candidate_catalog.json')['entries']
assert {row['id'] for row in catalog} == set(entries) and len(catalog) == len(entries)
for row in catalog:
    entry = entries[row['id']]
    assert digest(entry) == row['canonical_sha256']
    assert sha(DRAFT / row['path']) == row['file_sha256']
    assert len(entry['evidence']) == row['evidence_rows']

mapping = read(DRAFT / 'source_mapping.json')
assert sha(crosswalk_path) == mapping['crosswalk_file_sha256']
assert mapping['crosswalk_path'] == str(crosswalk_path.relative_to(REPO))
rows = mapping['rows']
source_rows = read(DRAFT / 'instruction_sources.json')['rows']
assert len(rows) == len(source_rows) == sum(len(entry['evidence']) for entry in entries.values()) == 306
seen_ids, seen_members, relationships = set(), set(), []
id_counts = collections.Counter()
for mapping_row, table_row in zip(rows, source_rows):
    case_pointer = mapping_row['crosswalk_case_pointer']
    record_pointer = mapping_row['crosswalk_record_pointer']
    assert record_pointer.startswith(case_pointer + '/record_sources/')
    case = pointer(crosswalk, case_pointer)
    source = pointer(crosswalk, record_pointer)
    document, record = original(source)
    assert mapping_row['original_record_sha256'] == source['original_record_sha256'] == digest(record)
    assert mapping_row['original_path'] == source['corpus_path']
    assert mapping_row['original_record_selector'] == source['line_or_selector']
    assert sha(REPO / source['corpus_path']) == mapping_row['original_file_sha256']
    entry_id, index = mapping_row['entry_id'], mapping_row['evidence_index']
    evidence = entries[entry_id]['evidence'][index]
    assert (entry_id, index) not in seen_members
    seen_members.add((entry_id, index))
    assert digest(evidence) == mapping_row['evidence_sha256']
    assert evidence['case_group'] == case['case_group'] and evidence['case_id'] == source['case_id']
    trace_path = mapping_row['observation_document_path']
    trace = None
    if trace_path:
        assert trace_path in case['trace_extensions']
        assert sha(REPO / trace_path) == mapping_row['observation_document_file_sha256']
        assert str(REPO / trace_path) in input_paths
        trace = read(REPO / trace_path)
        assert trace['case_group'] == case['case_group']
        assert source['case_id'] in trace['existing_case_ids']
        assert evidence['source_url'] in set(all_strings(trace['sources']))
    else:
        assert mapping_row['observation_document_file_sha256'] is None
        assert evidence['source_url'] in set(all_strings(source['primary_urls']))
    assert mapping_row['observation_pointer_scope'] in {'record', 'document'}
    container = (trace if trace is not None else document) if mapping_row['observation_pointer_scope'] == 'document' else record
    selected = pointer(container, mapping_row['original_observation_pointer'])
    parent = pointer(container, mapping_row['original_observation_pointer'].rsplit('/', 1)[0])
    assert isinstance(selected, str)
    span = mapping_row['excerpt_character_span']
    if span is not None:
        assert len(span) == 2 and 0 <= span[0] < span[1] <= len(selected)
        selected = selected[span[0]:span[1]]
    assert evidence['observation'] == selected
    selector = source['line_or_selector']
    base = trace_path or source['corpus_path'] + (':' + str(selector) if type(selector) is int else '')
    op = mapping_row['original_observation_pointer']
    if mapping_row['observation_pointer_scope'] == 'record' and type(selector) is not int and selector:
        op = selector + op
    locator = base + '#' + op
    if span is not None:
        locator += f'[characters {span[0]}:{span[1]}]'
    assert evidence['source_locator'] == locator
    assert mapping_row['original_inspection_scope'] == source['inspected_scope'] and evidence['limit'].strip()
    source_id = parent.get('source_id') if isinstance(parent, dict) else None
    source_ids = parent.get('source_ids') if isinstance(parent, dict) else None
    assert source_id == mapping_row['original_source_id']
    assert source_ids == mapping_row['original_source_ids']
    pools = []
    for doc in [record, document]:
        for key in ['sources', 'primary_sources', 'primary_source_urls+DOIs']:
            pool = doc.get(key)
            if isinstance(pool, dict):
                pools.extend(dict(source_id=key, **value) for key, value in pool.items())
            elif isinstance(pool, list):
                pools.extend(pool)
    precisely_resolved = bool(source_id and any(isinstance(item, dict) and item.get('source_id') == source_id and item.get('url') == evidence['source_url'] for item in pools))
    assert mapping_row['precise_original_source_id_url_resolved'] == precisely_resolved
    if source_id and pools:
        assert precisely_resolved
    if mapping_row['observation_pointer_scope'] == 'document' and not trace_path:
        assert isinstance(parent, dict) and parent['observation_id'] in source['preserved_observations']
    if source_ids:
        matching = [item for item in pools if isinstance(item, dict) and item.get('source_id') in source_ids]
        if matching:
            assert evidence['source_url'] in {item['url'] for item in matching if 'url' in item}
    evidence_id = mapping_row['evidence_id']
    assert evidence_id not in seen_ids
    seen_ids.add(evidence_id)
    assert table_row == dict(evidence_id=evidence_id, option_id=entry_id, **evidence)
    assert mapping_row['curation_uses'] and all(use['rationale'].strip() for use in mapping_row['curation_uses'])
    id_counts['precise_single_source_id_url' if precisely_resolved else 'case_or_trace_url_membership'] += 1
    relationships.append({'evidence_id': evidence_id, 'entry_id': entry_id, 'source_locator': locator,
                          'source_url': evidence['source_url'], 'observation_sha256': digest(selected),
                          'source_id': source_id, 'source_ids': source_ids,
                          'precise_single_source_id_url': precisely_resolved})
assert seen_members == {(entry_id, index) for entry_id, entry in entries.items() for index in range(len(entry['evidence']))}
with (DRAFT / 'source_mapping.tsv').open(newline='') as stream:
    tsv_rows = list(csv.DictReader(stream, delimiter='\t'))
assert len(tsv_rows) == len(rows)
for mapping_row, table_row, tsv in zip(rows, source_rows, tsv_rows):
    expected_tsv = {key: table_row[key] for key in 'case_group case_id source_url source_locator observation limit'.split()}
    expected_tsv.update(entry_id=mapping_row['entry_id'], evidence_id=mapping_row['evidence_id'], original_record_sha256=mapping_row['original_record_sha256'])
    assert tsv == expected_tsv

coverage = read(DRAFT / 'review_coverage.json')
assert coverage['source_path'] == str(crosswalk_path.relative_to(REPO))
assert coverage['partitions'] == crosswalk['partitions']
assert len(coverage['groups']) == len({group['case_group'] for group in coverage['groups']}) == 142
assert {group['case_group'] for group in coverage['groups']} == {case['case_group'] for case in case_rows}
for group in coverage['groups']:
    case = pointer(crosswalk, group['crosswalk_case_pointer'])
    assert case['case_group'] == group['case_group'] and case['best_coverage'] == group['best_coverage']
    assert group['records'] == [{key: source[key] for key in ['case_id', 'corpus_path', 'line_or_selector', 'original_record_sha256']} for source in case['record_sources']]
    expected_entries = sorted(entry_id for entry_id, entry in entries.items() if group['case_group'] in {e['case_group'] for e in entry['evidence']})
    assert group['selected_draft_entries'] == expected_entries
    assert expected_entries or (isinstance(group['unassigned_reason'], str) and group['unassigned_reason'].strip())
    assert sorted({judgment['entry_id'] for judgment in group['mapping_judgments']}) == expected_entries
assert coverage['unused_group_ids'] == [group['case_group'] for group in coverage['groups'] if not group['selected_draft_entries']]
assert len(coverage['unused_group_ids']) == 8
assert len([group for group in coverage['groups'] if group['selected_draft_entries']]) == 134
assert coverage['entry_case_index'] == {entry_id: sorted({e['case_group'] for e in entry['evidence']}) for entry_id, entry in entries.items()}
partition_groups = [group for partition in crosswalk['partitions'].values() for group in partition['case_groups']]
assert len(partition_groups) == len(set(partition_groups)) == 142
assert set(partition_groups) == {case['case_group'] for case in case_rows}
policy = read(DRAFT / 'review_policy_reference.json')
assert policy['policy'] == crosswalk['arithmetic_review']['policy']
assert files_snapshot() == baseline

result = {'status': 'passed', 'scope': 'Independent read-only structure/provenance validation; no scientific entailment, source retrieval, scoring, adoption or active execution.',
          'original_draft_path': str(DRAFT), 'original_draft_files_unchanged': True,
          'output_manifest_sha256': sha(DRAFT / 'output_manifest.json'),
          'original_validator_sha256': sha(DRAFT / 'validate_draft.py'),
          'independent_checker_sha256': sha(Path(__file__)),
          'sealed_output_files_excluding_manifest': len(expected), 'sealed_output_files_including_manifest': len(baseline),
          'output_hash_size_and_exact_membership': 'passed', 'symlinks': 0, 'extra_files': 0,
          'input_files': len(inputs), 'input_hashes': 'passed',
          'entry_schemas': len(entries), 'candidate_catalog_hashes': len(catalog),
          'original_record_hashes': len(records), 'original_groups': len(case_rows), 'original_contrasts': contrast_count,
          'exact_source_pointer_clause_url_relationships': len(relationships), 'source_id_relationship_counts': dict(id_counts),
          'source_mapping_tsv_rows': len(tsv_rows), 'group_coverage': 142, 'assigned_groups': 134, 'unassigned_groups': 8,
          'partition_coverage_and_exclusivity': 'passed', 'policy_reference_exact_match': True,
          'loader_round_trip': 'not rerun; sealed validation claim inspected only',
          'no_store_workflow_model_network_active_library_or_scientific_execution': True,
          'per_entry': {entry_id: {'source_rows': len(entry['evidence']), 'groups': len({e['case_group'] for e in entry['evidence']}), 'operands': len(entry['support']['operands'])} for entry_id, entry in entries.items()}}
for name, data in [('verification.json', result), ('verified_original_records.json', records), ('verified_source_relationships.json', relationships), ('sealed_draft_snapshot.json', baseline)]:
    (REPORT / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
print(json.dumps(result, indent=2))
