"""Read only explicit source/engineering receipt paths; write this audit receipt.
No primary scientific packet, provider/model history, live DB or source acquisition.
"""
import hashlib
import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = HERE.parent

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

source_names = [
 'literature_activity_calculations.py','literature_experimental_contracts.py',
 'literature_rate_reader.py','literature_rate_native_inputs.py','literature_rate_calculations.py','literature_rate_storage.py',
 'literature_assay_inputs.py','literature_assay_storage.py','literature_assay_prompt.py',
 'literature_ratio_reader.py','literature_ratio_calculations.py','literature_ratio_storage.py',
 'literature_binding_reader.py','literature_binding_calculations.py','literature_binding_storage.py',
 'literature_binding_model_inputs.py','literature_binding_models.py','literature_binding_model_storage.py','literature_binding_prompt.py',
 'literature_transport_inputs.py','literature_transport_calculations.py','literature_transport_storage.py','literature_transport_prompt.py',
 'literature_partner_inputs.py','literature_partner_native_inputs.py','literature_partner_defined_units.py','literature_partner_source_fields.py','literature_partner_calculations.py','literature_partner_storage.py','literature_partner_prompt.py',
 'literature_amount_inputs.py','literature_amount_calculations.py','literature_amount_storage.py','literature_amount_prompt.py',
 'literature_optical_inputs.py','literature_optical_calculations.py','literature_optical_storage.py','literature_optical_validation.py',
 'literature_quantity_storage.py','literature_prose_reader.py','literature_html_quantity_reader.py',
 'literature_figure_measurements.py','literature_figure_inputs.py','literature_figure_storage.py','literature_figure_prompt.py',
 'literature_episodes.py','episode_services.py','literature_experimental_prompt.py','literature_reference_parent_prompt.py']
paths = [ROOT/'gene_annotation_episode'/name for name in source_names]
before = {str(p.relative_to(ROOT)):sha(p) for p in paths}
from gene_annotation_episode.literature_episodes import _population_catalog
catalog = _population_catalog()
substantive = {
 'corrected_endpoint_activity':['literature.assay.populate'],
 'source_preparation_rate':['literature.rate.populate','literature.rate.source.populate'],
 'relative_signal':['literature.ratio.populate'],
 'binding_parameter_and_model':['literature.binding.populate','literature.binding.model.populate'],
 'conditional_transport_response':['literature.transport.response.populate'],
 'partner_removal_addback':['literature.partner.populate','literature.partner.source.populate']}
support = ['literature.amount.populate','literature.optical.populate']
extract = ['literature.quantity.populate','literature.figure.populate']
other = ['literature.perturbation.populate','literature.structure.populate','literature.reaction.populate','literature.context.populate']
assert len(catalog) == 17
assert set(e['name'] for e in catalog) == {*[n for v in substantive.values() for n in v],*support,*extract,*other}
components = {}
for name in ['assay_storage','rate_storage','ratio_calculations','binding_calculations','binding_models','transport_calculations','partner_calculations','amount_calculations','optical_storage','quantity_storage','figure_inputs']:
    module = importlib.import_module('gene_annotation_episode.literature_'+name)
    components['literature_'+name] = list(module.COMPONENTS)

receipt_paths = [
 'partner_examples_001/EXAMPLES_RECEIPT.json','partner_examples_001/REOPEN_RECEIPT.json',
 'partner_native_examples_001/EXAMPLES_RECEIPT.json','partner_native_examples_001/REOPEN_RECEIPT.json',
 'partner_defined_examples_001/EXAMPLES_RECEIPT.json','partner_defined_examples_001/REOPEN_RECEIPT.json',
 'transport_response_examples_001/EXAMPLES_RECEIPT.json','transport_response_examples_001/REOPEN_RECEIPT.json',
 'binding_model_examples_001/REOPEN_MODEL_RECEIPT.json',
 'figure_examples_001/EXAMPLES_RECEIPT.json','figure_examples_001/REOPEN_RECEIPT.json',
 'optical_calculations_033/receipt.json','optical_inputs_035/FINAL_RECEIPT.json','optical_storage_036/FINAL_RECEIPT_004.json']
case_allowed={'case','status','model_backed','cells','observations','population_operations','parent_receipts',
 'selected_outcome_equals_saved','frozen_form_equals_saved','admitted_subset_equals_saved',
 'all_SQL_tables_and_histories_unchanged','SQL_query_only','original_input_bytes_read','counts_before_and_after'}
top_allowed={'status','model_backed','scope','original_input_bytes_read','parser_calculator_disabled',
 'replay_SQL_query_only','synthetic_only','production_integration','model_inference','primary_packet_reads',
 'generation','terminal_result','test_terminal_result','exit_code','test_exit_code','connected_group_total',
 'new_reader_checks','existing_calculator_checks'}
receipts=[]
for relative in receipt_paths:
    p=BASE/relative
    data=json.loads(p.read_text())
    receipts.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),
       'metadata':{k:v for k,v in data.items() if k in top_allowed},
       'cases':[{k:v for k,v in case.items() if k in case_allowed} for case in data.get('cases',[])]})
frozen={}
for relative in ['optical_calculations_033/receipt.json','optical_inputs_035/FINAL_RECEIPT.json','optical_storage_036/FINAL_RECEIPT_004.json']:
    d=json.loads((BASE/relative).read_text())
    for group in ['sha256','frozen_dependencies_sha256']:
        for name, expected in d.get(group,{}).items():
            p=ROOT/name
            frozen[name]={'expected':expected,'actual':sha(p),'matches':sha(p)==expected}
assert all(v['matches'] for v in frozen.values())
after={str(p.relative_to(ROOT)):sha(p) for p in paths}
assert before == after
result={'audit':'a105_grader_coverage_041','production_edits':False,'paper_reads':False,'model_calls':0,
 'catalog_count':len(catalog),'substantive_families':substantive,'substantive_operations':9,
 'support_calculation_operations':support,'support_extraction_operations':extract,'other_axis_operations':other,
 'A105_relevant_operations':13,'A105_typed_namespaces':12,'A105_nonoptical_typed_namespaces':11,
 'complete_universal_experimental_graders':0,'complete_A105_axis_sheet':False,
 'future_required_family_count':'unknown; case coverage determines variants',
 'actual_catalog_names':[e['name'] for e in catalog],
 'declared_component_vocabulary_not_coverage_counts':components,
 'current_source_sha256':after,'source_hashes_unchanged_during_receipt_script':before==after,
 'frozen_receipt_hash_checks':frozen,'historical_engineering_receipt_metadata':receipts,
 'new_execution':json.loads((HERE/'SUBSET_EXPANSION_RECEIPT.json').read_text()),
 'read_limits':['No actual_observations, paper-specific review/packet, provider history or live024/030 state inspected.',
 'Historical controlled receipts do not independently verify source interpretation or current broad runtime/model science.',
 'Optical037 final receipt/limits and complete storage consumer inspected; not an independent branch audit of its entire validator.',
 'No broad test suite repeated; only new isolated adapter/form synthetic subset reproduction executed.'],
 'packet_file_sha256':{p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name != 'AUDIT_RECEIPT.json'}}
(HERE/'AUDIT_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'catalog':len(catalog),'A105_relevant':13,'family_grouping':6,'frozen_hash_checks':len(frozen),'all_frozen_match':True,'subset_repro':'reproduced','shared_hashes_unchanged':before==after},indent=2))
