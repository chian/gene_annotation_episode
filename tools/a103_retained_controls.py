"""Recheck local versus incomplete-record detection on retained real output."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3

from gene_annotation_episode.workflow_budget import active_budget


def main():
    directory=Path(active_budget()['run_directory'])
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    args=parser.parse_args()
    original=args.case.resolve()/'state'
    state=directory/'control-state';state.mkdir()
    with closing(sqlite3.connect((original/'state.sqlite3').as_uri()+'?mode=ro',uri=True)) as reader:
        with closing(sqlite3.connect(state/'state.sqlite3')) as writer:reader.backup(writer)
    shutil.copytree(original/'artifacts',state/'artifacts')
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.a103_detection import detect,search_receipt
    from gene_annotation_episode.a103_publication import binding_body,received_measurement
    with Store(state) as store:
        known={row[0] for row in store.db.execute('SELECT DISTINCT record_ref FROM runtime_record_receipts')}
        candidates=[]
        for ref in known:
            native=received_measurement(store,ref)
            if native is not None and native['body']['schema']=='a103_detection_v1' and native['body']['present'] is False:
                body=native['body']
                if len(body['binding_refs'])==1 and body.get('neighborhood_ref'):candidates.append(body)
        if not candidates:raise ValueError('real_complete_local_nondetection_required')
        body=candidates[0]
        binding=binding_body(store,body['binding_refs'][0],known)
        neighborhood=received_measurement(store,body['neighborhood_ref'])['body']
        metadata,query=search_receipt(store,body['snapshot_ref'],body['native_source_ref'],body['component_ref'],known)
        native=store.get(body['native_source_ref'])
        database=store.get(body['database_source_ref'])
        native_path=directory/'retained-native.stdout';database_path=directory/'retained-database.faa'
        native_path.write_bytes(store.get_artifact(native['artifact_ref']))
        database_path.write_bytes(store.get_artifact(database['artifact_ref']))
        request={**{key:body[key] for key in ('component_ref','snapshot_ref','native_source_ref','database_source_ref')},
            'native_path':str(native_path),'database_path':str(database_path),'search_metadata':metadata,
            'query_sequence':query,'bindings':[binding],'neighborhood':neighborhood,
            'neighborhood_ref':body['neighborhood_ref']}
        before=store.db.total_changes
        local=detect(request)
        whole=detect({**request,'neighborhood':None,'neighborhood_ref':None})
        assert local['present'] is False and local['all_actual_cds_in_search'] is True
        assert whole['present'] is None and whole['uncertain_cds']
        assert store.db.total_changes==before
        result={'decision_mode':'scripted_scope_control_on_retained_real_native_search',
            'accession':binding['accession'],'local_present':local['present'],
            'local_cds':local['searched_cds'],'local_complete':local['all_actual_cds_in_search'],
            'expanded_record_present':whole['present'],'expanded_uncertain_cds':whole['uncertain_cds'],
            'new_homology_jobs':0,'scope_parser_runs':2,'new_context_measurements':0}
    (directory/'RETAINED_SCOPE_CONTROL.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
