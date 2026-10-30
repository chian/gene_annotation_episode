from pathlib import Path
p=Path('tests/test_bvbrc_comparative_systems_tool_info.py')
s=p.read_text().replace("assert all(item['name'] != row['name'] for item in registry.catalog())", "assert row['name'] not in registry.catalog()")
p.write_text(s)
p=Path('tests/test_bvbrc_comparative_systems_returns.py')
s=p.read_text().replace("    args['requested_form'] = requested_form()", "    args['requested_form'] = requested_form()\n    args['parameters']['producer_evidence_selections'] = []\n    args['qualified_producer_evidence'] = ()\n    for document in args['parameters']['document_selection']['documents']:\n        document['producer_evidence_id'] = None")
s=s.replace("['components'][0]['output']['value']=.5", "['components'][0]['ratio']['output']['value']=.5")
p.write_text(s)
p=Path('tests/test_bvbrc_comparative_systems_host_inputs.py')
s=p.read_text().replace('import json\n','import json\nimport hashlib\n')
s=s.replace('collect_comparative_systems_inputs, _SelectedDataHost', 'collect_comparative_systems_inputs, _SelectedDataHost, _materialize_producers')
s=s.replace('requested_form, parameters', 'requested_form, parameters, FIXTURES')
s=s.replace("['record_sets'][0]['records']", "['record_sets'][0]['rows']")
s=s.replace('    d.data_qualified,d.data_content,d.data_raw,d.data_calls = qualified,content,raw,calls', '''    d.data_qualified,d.data_content,d.data_raw,d.data_calls = qualified,content,raw,calls
    producer_input(d)


def producer_input(d):
    commit = '670b3b6dd09509ebc62fb6f1b1caf3e38c33bd33'
    repository = 'https://github.com/BV-BRC/comparative_systems_service'
    raw = (FIXTURES/'compare_systems_lib.py.txt').read_bytes()
    code = d.saved.source(raw,uri=repository+'/blob/'+commit+'/lib/compare_systems_lib.py')
    d.saved.own(d.parent,code['source_ref'],index=2)
    evidence = {'evidence_id':'examined_source','identity_kind':'source_examined','repository_url':repository,
        'commit':commit,'source_sha256':hashlib.sha256(raw).hexdigest(),'runtime_version':None,
        'dependency_version':None,'reference_release':None,'source_locations':[{
            'source_ref':code['source_ref'],'raw_artifact_ref':code['artifact_ref'],'document_id':None,
            'json_pointer':'','table':None,'row_ordinal':None,'column_ordinal':None,'native_field':None}]}
    content = d.saved.source(canonical({'producer':evidence}).encode(),accession='retained-source-description')
    d.saved.own(d.parent,content['source_ref'],index=3)
    selection = {'evidence_id':'examined_source','source_ref':content['source_ref'],
        'raw_artifact_ref':content['artifact_ref'],'record_path':'/producer'}
    d.selected['adapter']['parameters']['producer_evidence_selections'] = [selection]
    d.selected['adapter']['parameters']['document_selection']['documents'][0]['producer_evidence_id']='examined_source'
    d.selected['supplied_contents'].append(code)
    d.selected['supplied_metadata'].append({'content':content,'pointer':'/producer'})
    # Explicitly retained false claims remain available for hostile selection
    # tests; they cannot attest any producing execution or remote task.
    d.false_producers=[]
    for index,kind in enumerate(('source_executed','deployed_attested'),4):
        false=deepcopy(evidence)
        false['identity_kind']=kind
        value=d.saved.source(canonical({'producer':false}).encode(),accession='false-'+kind)
        d.saved.own(d.parent,value['source_ref'],index=index)
        d.selected['supplied_metadata'].append({'content':value,'pointer':'/producer'})
        d.false_producers.append({**selection,'source_ref':value['source_ref'],'raw_artifact_ref':value['artifact_ref']})
    d.producer_evidence=evidence''')
s=s.replace("assert len(d.data_calls)==1 and producers==()", "assert len(d.data_calls)==1 and len(producers)==1\n        assert producers[0]['evidence']==d.producer_evidence\n        assert producers[0]['qualification']['basis']=='source_only'\n        assert producers[0]['qualification']['original_task_ref'] is None\n        assert 'producer_version_unverified' in d.sheet['source_documents'][0]['qualification_codes']")
s=s.replace("d.saved.own(d.parent,fake['source_ref'],index=2)", "d.saved.own(d.parent,fake['source_ref'],index=6)")
s=s.replace("        before=store.db.execute", '''        all_bindings=[*d.body['bundle']['supplied_contents'],*(row['content'] for row in d.body['bundle']['supplied_scientific_metadata'])]
        receipt=d.records.read(d.body['bundle']['acquisition_receipt_refs'][-1])
        index=int(receipt['value']['origin']['operation_key'].rsplit(':',1)[1])
        for selected in d.false_producers:
            altered=deepcopy(d.selected['adapter']['parameters'])
            altered['producer_evidence_selections']=[selected]
            with pytest.raises(ValueError,match='producer_execution_attestation_unbound'):
                _materialize_producers(d.api.appservice.publications,d.context,altered,d.body['bundle'],all_bindings,raw,index)
        before=store.db.execute''')
p.write_text(s)
