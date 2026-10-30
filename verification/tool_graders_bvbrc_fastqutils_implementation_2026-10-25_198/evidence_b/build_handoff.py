"""Retain actual B function outputs and explicit independent numerical oracles."""
from pathlib import Path
from copy import deepcopy
import hashlib, inspect, io, json, sys, zipfile
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base/'candidate'))
from gene_annotation_episode.bvbrc_fastqutils_fastqc_reader import parse_fastqc_data,parse_fastqc_html,parse_fastqc_zip
from gene_annotation_episode.bvbrc_fastqutils_trim_reader import parse_trim_galore_report
from gene_annotation_episode.bvbrc_fastqutils_pair_report_reader import parse_fastq_pair_stderr
from gene_annotation_episode.bvbrc_fastqutils_hostile_reader import parse_hostile_json
from gene_annotation_episode.bvbrc_fastqutils_retention import calculate_retention
from gene_annotation_episode.bvbrc_fastqutils_consistency import calculate_report_consistency
from gene_annotation_episode.bvbrc_fastqutils_contracts import json_sha256,validate_native_document
fixtures=base/'candidate/tests/fixtures/bvbrc_fastqutils/reports'
evidence=base/'evidence_b'
sheet=json.loads((fixtures/'saved_native_sheet.json').read_text())
zip_buffer=io.BytesIO()
with zipfile.ZipFile(zip_buffer,'w',compression=zipfile.ZIP_DEFLATED) as writer:
 for member, filename in [('all/fastqc_report.html','fastqc_tables_graph.html'),('all/fastqc_data.txt','fastqc_all_modules.txt')]:
  info=zipfile.ZipInfo(member,date_time=(2026,10,25,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
  writer.writestr(info,(fixtures/filename).read_bytes())
(fixtures/'fastqc_native_members.zip').write_bytes(zip_buffer.getvalue())
entries=[('fastqc_data','fastqc_all_modules.txt','fastqc_data_0_12_1','0.12.1',parse_fastqc_data),
 ('fastqc_html','fastqc_tables_graph.html','fastqc_html_0_12_1','0.12.1',parse_fastqc_html),
 ('fastqc_zip','fastqc_native_members.zip','fastqc_zip_0_12_1','0.12.1',parse_fastqc_zip),
 ('trim_first','trim_first.txt','trim_galore_report_0_6_10','0.6.10',parse_trim_galore_report),
 ('trim_second','trim_second.txt','trim_galore_report_0_6_10','0.6.10',parse_trim_galore_report),
 ('trim_single','trim_single.txt','trim_galore_report_0_6_10','0.6.10',parse_trim_galore_report),
 ('pair_report','pair_stderr.txt','fastq_pair_stderr_0_3','0.3',parse_fastq_pair_stderr),
 ('hostile','hostile_source_executed_synthetic.json','hostile_json_1_1_0','1.1.0',parse_hostile_json)]
documents=[];contexts=[];summaries=[]
for docid,filename,fmt,version,function in entries:
 raw=(fixtures/filename).read_bytes()
 context={'analysis_id':sheet['analysis_id'],'document_id':docid,'task_ref':sheet['task_ref'],
 'content':{'source_ref':'source_b_'+docid,'artifact_field':'artifact_ref','artifact_ref':'artifact_b_'+docid,
 'sha256':hashlib.sha256(raw).hexdigest(),'byte_count':len(raw)},'native_name':filename,'declared_format':fmt,
 'producer_version':version,'transfer_scope':'complete','identity':'source_executed_synthetic' if docid=='hostile' else 'handcrafted_synthetic'}
 doc=function(raw,context=context);validate_native_document(doc);documents.append(doc);contexts.append(context)
 summaries.append({'document_id':docid,'parser':function.__name__,'fixture':str((fixtures/filename).relative_to(base)),
 'identity':context['identity'],'cells':len(doc['cells']),'populations':len(doc['populations']),
 'categories':len(doc['categories']),'lineages':len(doc['native_lineage']),'parse_scope':doc['parse_scope'],
 'document_sha256':json_sha256(doc)})
(evidence/'ACTUAL_NATIVE_DOCUMENTS.json').write_text(json.dumps(documents,indent=2,ensure_ascii=False)+'\n')
(evidence/'PARSE_CONTEXTS.json').write_text(json.dumps(contexts,indent=2)+'\n')
(evidence/'PARSER_SUMMARIES.json').write_text(json.dumps(summaries,indent=2)+'\n')
oracles=[]
for name,metric in [('native','native_report_retention_fraction'),('assumed','read_retention_fraction')]:
 s=json.loads((fixtures/f'saved_{name}_sheet.json').read_text());params=json.loads((fixtures/f'saved_{name}_components.json').read_text())['parameters']
 job=next(j for j in params['calculations'] if j['method']=='retention_v1')
 actual=calculate_retention(s,job=job,parameters_sha256=json_sha256(params))
 expected={metric:.75,'removed_count':2,'removed_fraction':.25}
 assert {r['metric']:r['value'] for r in actual}==expected
 oracles.append({'name':name,'fixture_identity':'handcrafted_synthetic_contract_oracle',
 'sheet_file':str((fixtures/f'saved_{name}_sheet.json').relative_to(base)), 'sheet_sha256':json_sha256(s),
 'parameters':params,'job':job,'expected_values_written_independently':expected,'actual_components':actual})
(evidence/'SAVED_SHEET_ORACLES.json').write_text(json.dumps(oracles,indent=2)+'\n')
exports=[]
for function in [parse_fastqc_html,parse_fastqc_data,parse_fastqc_zip,parse_trim_galore_report,parse_fastq_pair_stderr,parse_hostile_json,calculate_retention,calculate_report_consistency]:
 path=Path(inspect.getfile(function));exports.append({'module':function.__module__,'export':function.__name__,'signature':str(inspect.signature(function)),
 'path':str(path.relative_to(base)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(evidence/'EXPORT_MANIFEST.json').write_text(json.dumps(exports,indent=2)+'\n')
print(json.dumps({'parsers':summaries,'oracles':[{k:r[k] for k in ('name','expected_values_written_independently')} for r in oracles]},indent=2))
