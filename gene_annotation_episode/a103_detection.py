"""Detection-limited presence/absence from an actual complete native search.

The caller must deliver the actual parsed-search receipt, its native output
Source and the exact searched FASTA. Metadata references alone grant no files.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

from Bio import SearchIO,SeqIO

from .a103_scoring import _translation, digest, require


def search_receipt(store,snapshot_ref,native_source_ref,component_ref,known):
    require({snapshot_ref,native_source_ref,component_ref}<=set(known),'a103_native_search_inputs_not_received')
    exists = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='homology_result_snapshots'").fetchone()
    row = store.db.execute('SELECT body FROM homology_result_snapshots WHERE source_ref=?',(snapshot_ref,)).fetchone() if exists else None
    require(row is not None,'a103_registered_native_search_required')
    source,native = store.get(snapshot_ref),store.get(native_source_ref)
    body = json.loads(row[0])
    require(source['origin']=='tool' and source.get('provider')=='native.phmmer.parsed_snapshot'
        and json.loads(store.get_artifact(source['artifact_ref']))==body,'a103_search_snapshot_custody_conflict')
    require(body['native_source_ref']==native_source_ref and native['origin']=='tool'
        and native.get('provider')=='native.phmmer.snapshot'
        and native['artifact_ref']==body['native_text_artifact'],'a103_native_output_custody_conflict')
    inventory = body['parse_inventory']
    require(body['native_termination_seen'] and inventory['parser_finished']
        and inventory['native_error_count']==0 and inventory.get('grading_error_count',0)==0
        and body['parse_execution']['failure'] is None,'a103_complete_error_free_native_search_required')
    component = store.get(component_ref)
    require(component.get('sequence_ref') is not None,'a103_detection_query_sequence_required')
    sequence = store.get_artifact(component['sequence_ref']).decode().strip().upper()
    require(hashlib.sha256(sequence.encode()).hexdigest()==body['query_sequence_sha256'],
            'a103_detection_actual_query_conflict')
    return body,sequence


def detect(request):
    native_path,database_path = Path(request['native_path']),Path(request['database_path'])
    metadata = request['search_metadata']
    database_bytes = database_path.read_bytes()
    require(hashlib.sha256(database_bytes).hexdigest()==metadata['database_sha256'],
            'a103_searched_database_identity_conflict')
    query = SearchIO.read(native_path,'hmmer3-text')
    require(query.program=='phmmer' and query.seq_len==len(request['query_sequence']),
            'a103_native_query_or_program_conflict')
    raw = native_path.read_text()
    require(raw.rstrip().endswith('[ok]'),'a103_native_search_termination_missing')
    entries = list(SeqIO.parse(io.StringIO(database_bytes.decode()),'fasta'))
    require(entries and len({r.id for r in entries})==len(entries),'a103_actual_unique_searched_records_required')
    database = {r.id:hashlib.sha256(str(r.seq).upper().encode()).hexdigest() for r in entries}
    known_hashes = set(database.values())
    features = []
    uncertain = []
    canonical_records = []
    scopes = []
    for binding in request['bindings']:
        record = next(SeqIO.parse(io.StringIO(binding['genbank_projection']),'genbank'))
        canonical_records.append(binding['accession'].split('.')[0])
        scopes.append({'accession':binding['accession'],'source_request':binding.get('source_request'),
            'record_length':binding['record_length'],'source_file_sha256':binding['source_file_sha256']})
        for index,feature in enumerate(record.features):
            if feature.type!='CDS':continue
            neighborhood = request.get('neighborhood')
            if neighborhood is not None and index not in {r['source_feature_index'] for r in neighborhood['cds']}:
                continue
            tr = _translation(record,feature)
            if tr['status']!='verified':
                uncertain.append({'accession':record.id,'feature_index':index,'reason':tr['qualification']})
                continue
            sha = hashlib.sha256(tr['sequence'].encode()).hexdigest()
            features.append({'accession':record.id,'feature_index':index,'sequence_sha256':sha,
                             'in_searched_database':sha in known_hashes})
    complete = bool(features) and not uncertain and all(f['in_searched_database'] for f in features)
    feature_hashes = {f['sequence_sha256'] for f in features}
    hits = []
    for hit in query:
        require(hit.id in database,'a103_native_hit_outside_actual_database')
        if database[hit.id] not in feature_hashes:continue
        hits.append({'native_target_id':hit.id,'sequence_sha256':database[hit.id],
            'bitscore':hit.bitscore,'evalue':hit.evalue,'native_included':hit.is_included,
            'domains':[{'bitscore':h.bitscore,'evalue':h.evalue,'native_included':h.is_included,
                        'query_start':h.query_start,'query_end':h.query_end,'hit_start':h.hit_start,'hit_end':h.hit_end}
                       for h in hit.hsps]})
    present = any(h['native_included'] for h in hits)
    if not present and not complete:present=None
    return {'schema':'a103_detection_v1','producer_operation':'context.detection_inventory',
        'component_ref':request['component_ref'],'genome_key':'records:'+digest(sorted(set(canonical_records))),
        'present':present,'scope':'examined_annotated_CDS_in_explicit_acquired_records',
        'absence_meaning':'no_included_native_hit_in_covered_CDS_inventory; not_absence_from_unexamined_genome_or_replicons',
        'searched_cds':len(features),'uncertain_cds':uncertain,'all_actual_cds_in_search':complete,
        'native_hits':hits,'native_method':'phmmer_native_inclusion_criterion',
        'native_parameters':metadata['native_parameters'],'native_program_version':query.version,
        'native_search_complete':True,'native_database_sha256':metadata['database_sha256'],
        'record_scopes':scopes,'snapshot_ref':request['snapshot_ref'],'native_source_ref':request['native_source_ref'],
        'neighborhood_ref':request.get('neighborhood_ref'),
        'database_source_ref':request['database_source_ref'],
        'interpretation':'detection_state_at_its_recorded_scope; no_gene_family_or_genome_absence_beyond_that_scope'}
