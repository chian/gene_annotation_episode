"""A108 observation revision selection and current aggregation."""
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.sample_context_evidence.literature_sheet_updates import VERSION, _rows, _adapter

def a108_revision_context(store, context, source_cells):
    """Freeze actual publication order, not model order or a later live view."""
    known = {row['sheet_ref']: row for row in _rows(store, context)}
    if any((row['sheet_ref'] not in known for row in source_cells)):
        return None
    versions = []
    for cell in source_cells:
        ref = cell['sheet_ref']
        row = known[ref]
        native = _adapter(store, context.run_id, row['adapter'])
        source = store.get(ref)
        request = json.loads(store.get_artifact(source['request_ref']))
        owner = native._sheet_owner(ref)
        original = store.db.execute(f'SELECT rowid FROM {native.operations_table} WHERE run_id=? AND episode_id=? AND operation_key=?', (context.run_id, owner, request['operation_key'])).fetchone()
        versions.append({'sheet_ref': ref, 'owner': owner, 'publication_order': original[0]})
    return {'version': VERSION, 'source_versions': versions, 'revision_identity': 'same_owner_original_observation_context_claim_and_domain'}

def aggregate_current_a108(arguments, source_cells, revision_context):
    """Apply the existing union calculator to current observation revisions.

    A multi-observation sheet may be followed by a correction of just one of its
    observations.  Only that scientific use is replaced; its other observations
    survive.  Competing assessments from different owners remain competing,
    rather than being silently resolved by arrival order.
    """
    from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.sample_context_evidence.literature_aggregation import aggregate_a108
    from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.literature_grading import count_sets, relation_metadata, sets_from_relations
    if not isinstance(revision_context, dict) or revision_context.get('version') != VERSION or set(revision_context) != {'version', 'source_versions', 'revision_identity'}:
        raise ContractError('a108_current_revision_context_invalid')
    versions = {row['sheet_ref']: row for row in revision_context['source_versions']}
    if set(versions) != {row['sheet_ref'] for row in source_cells}:
        raise ContractError('a108_current_revision_sources_mismatch')
    latest = {}
    for cell in source_cells:
        version = versions[cell['sheet_ref']]
        if type(version['publication_order']) is not int:
            raise ContractError('a108_current_revision_order_invalid')
        for relation in cell['relations']:
            key = (version['owner'], cell['domain'], relation['original_observation_key'], relation['context_claim_ref'])
            prior = latest.get(key)
            if prior is None or version['publication_order'] > versions[prior]['publication_order']:
                latest[key] = cell['sheet_ref']
    projected = []
    for original in source_cells:
        row = deepcopy(original)
        owner = versions[row['sheet_ref']]['owner']
        row['relations'] = [relation for relation in row['relations'] if latest[owner, row['domain'], relation['original_observation_key'], relation['context_claim_ref']] == row['sheet_ref']]
        if original['relations'] and (not row['relations']):
            continue
        if row['relations']:
            row['observation_sets'] = sets_from_relations(row['relations'])
            counts = count_sets(row['observation_sets'])
            row.update(relation_metadata(row['relations']))
            row['value'] = row['available_value'] = counts['evidence_amount']
            keys = {(relation['original_observation_key'], relation['context_claim_ref']) for relation in row['relations']}
            row['missing_inputs'] = [item for item in row['missing_inputs'] if (item['original_observation_key'], item['context_claim_ref']) in keys]
            row['status'] = 'partial' if row['missing_inputs'] else 'conditional' if any((relation['target_relationship'] != 'direct' for relation in row['relations'])) else 'populated'
        projected.append(row)
    selected = deepcopy(arguments)
    retained = {row['sheet_ref'] for row in projected}
    selected['contributions'] = [item for item in selected['contributions'] if item['sheet_ref'] in retained]
    return aggregate_a108(selected, projected)
