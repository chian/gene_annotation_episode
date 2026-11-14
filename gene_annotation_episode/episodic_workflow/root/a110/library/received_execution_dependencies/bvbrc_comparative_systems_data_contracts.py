from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_comparative_systems_handoff_contracts import validate_shape
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.bvbrc_data_fields import FIELD_REGISTRY
_ROLES = {'genome': {'genome_records', 'original_genome_population'}, 'genome_feature': {'family_feature_records'}, 'pathway': {'pathway_records'}, 'subsystem': {'subsystem_records'}, 'protein_family_ref': {'family_reference'}, 'pathway_ref': {'pathway_reference', 'reference_membership'}, 'subsystem_ref': {'subsystem_reference', 'reference_membership'}}

def _require(condition, code):
    if not condition:
        raise ValueError('comparative_systems_data_' + code)

def _count(cell, *, population_id, unit, value=None):
    _require(cell['population_id'] == population_id and cell['unit'] == unit, 'count_population_mismatch')
    if cell['state'] == 'available':
        _require(type(cell['value']) is int and cell['value'] >= 0, 'count_integer_required')
        if value is not None:
            _require(cell['value'] == value, 'count_value_mismatch')

def _population(population, *, genome=False):
    pid = population['population_id']
    _require(population['member_kind'] == ('genome_id' if genome else 'record_id'), 'population_member_kind_mismatch')
    if genome:
        _require(population['kind'] in {'declared_query_genomes', 'requested_direct_genomes', 'executed_genomes'}, 'genome_population_kind_mismatch')
    else:
        _require(population['kind'] == 'supplied_data_records', 'record_population_kind_mismatch')
    unit = 'genome' if genome else 'record'
    _count(population['raw_occurrence_count'], population_id=pid, unit=unit, value=len(population['members']) if genome else None)
    _count(population['distinct_valid_member_count'], population_id=pid, unit=unit, value=len(set(population['members'])))
    _require(not set(population['members']) & set(population['missing_members']), 'population_missing_member_conflict')
    if population['completeness'] == 'complete_for_declared_population':
        _require(not population['missing_members'] and (not population['unresolved_members']), 'complete_population_unresolved')
        _require(all((population[key]['state'] == 'available' for key in ('raw_occurrence_count', 'distinct_valid_member_count'))), 'complete_population_count_missing')

def validate_data_population_selection(value: object) -> dict:
    """Validate finite selected IDs and meanings, without claiming evidence."""
    result = validate_shape('DataPopulationSelectionV1', value)
    ids, genomes = (set(), {})
    for selected in result['record_sets']:
        rid, collection = (selected['record_set_id'], selected['collection'])
        _require(rid not in ids, 'duplicate_record_set_id')
        ids.add(rid)
        population = selected['declared_genome_population']
        _population(population, genome=True)
        pid = population['population_id']
        _require(pid not in genomes or genomes[pid] == population, 'population_id_collision')
        genomes[pid] = population
        registry = FIELD_REGISTRY[collection]
        _require(all((field in registry['fields'] and registry['fields'][field]['stored'] for field in selected['selected_fields'])), 'selected_field_unavailable')
        _require(registry['unique_key'] in selected['selected_fields'], 'selected_unique_key_required')
        sort = selected['sort']
        _require(len({item['field'] for item in sort}) == len(sort), 'duplicate_sort_field')
        _require(all((item['field'] in registry['fields'] and registry['fields'][item['field']]['sort_supported'] for item in sort)), 'sort_field_unavailable')
        _require(registry['unique_key'] in {item['field'] for item in sort}, 'stable_sort_required')
        _require(set(selected['roles']) <= _ROLES[collection], 'role_collection_mismatch')
        _require(selected['annotation_filter'] == 'none' or 'annotation' in registry['fields'], 'annotation_filter_collection_mismatch')
        evidence = selected['snapshot_evidence']
        _require(evidence['kind'] != 'single_complete_response' or evidence['snapshot_id'] is None, 'single_response_snapshot_id_invalid')
        for location in evidence['source_locations']:
            _require(location['source_ref'] in selected['source_refs'], 'snapshot_source_not_selected')
    _require(not ids & genomes.keys(), 'population_id_collision')
    return result
