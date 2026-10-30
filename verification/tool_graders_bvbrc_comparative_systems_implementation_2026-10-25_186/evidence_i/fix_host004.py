from pathlib import Path
p=Path('tests/test_bvbrc_comparative_systems_host_inputs.py')
s=p.read_text().replace('from test_api_bvbrc_data_v2 import selector as data_selector, snapshot','from gene_annotation_episode.acquisition import SourceSnapshot')
s=s.replace("['prepared']['population_key']", "['prepared']['query_population']['population_key']")
s=s.replace("d.sheet['supplied_record_sets'][0]['records']", "d.sheet['supplied_record_sets']['record_sets'][0]['records']")
pos=s.index('\ndef execute(')
s=s[:pos]+'''
def data_selector():
    return {'version':'bvbrc_data_result_selector_v2','page':None,'projection':{'family':'query_metadata'},
        'inputs':[],'supplied_metadata':[]}


def snapshot(prepared,body):
    native=prepared['native_request']
    return SourceSnapshot('bvbrc_data',native['url'],deepcopy(prepared['effective_request']),
        '2026-10-24T20:00:00+00:00',body,'application/solr+json',{
            'status':200,'body_complete':True,'automatic_redirects':False,'effective_url':native['url'],
            'request':{key:deepcopy(native[key]) for key in ('method','url','headers','body')},'header_items':[]})

''' + s[pos:]
p.write_text(s)
