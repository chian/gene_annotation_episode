"""Finite validation of this contract evidence; no production grader execution."""
from pathlib import Path
import copy, hashlib, json, math
from jsonschema import Draft202012Validator
from jsonschema.validators import extend
from gene_annotation_episode.communication import validate_closed_schema

BASE=Path(__file__).resolve().parent
schema=json.loads((BASE/'HANDOFF_SCHEMAS_001.json').read_text())
filled=json.loads((BASE/'FILLED_EXAMPLES_001.json').read_text())
checks=[]
def check(name,condition):
    assert condition,name
    checks.append(name)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def finite(v):
    if isinstance(v,float):return math.isfinite(v)
    if isinstance(v,dict):return all(finite(x) for x in v.values())
    if isinstance(v,list):return all(finite(x) for x in v)
    return type(v) in (type(None),str,int,bool)
types=Draft202012Validator.TYPE_CHECKER.redefine_many({'integer':lambda _,v:type(v) is int,
    'number':lambda _,v:type(v) in (int,float) and (type(v) is int or math.isfinite(v))})
Validator=extend(Draft202012Validator,type_checker=types)
Draft202012Validator.check_schema(schema)
check('schema_is_Draft202012',True)
examples={x['example_id']:x for x in filled['examples']}
check('example_ids_unique',len(examples)==len(filled['examples']))
for x in filled['examples']:
    v=Validator({**schema,'$ref':'#/$defs/'+x['schema_name']})
    v.validate(x['value']);check('shape:'+x['example_id'],finite(x['value']))
def val(name):return examples[name]['value']
main=val('pathway_subsystem_sheet');fam=val('families_sheet');overflow=val('hex_256_sheet')
source_files={sha(p.read_bytes()):(p,len(p.read_bytes())) for p in (BASE/'source_executed_synthetic').rglob('*') if p.is_file()}
for sh in (main,fam,overflow):
    for d in sh['source_documents']:
        check('document_bytes:'+sh['analysis_id']+':'+d['document_id'],d['sha256'] in source_files and source_files[d['sha256']][1]==d['byte_count'])
    check('document_identity:'+sh['analysis_id'],len({d['document_id'] for d in sh['source_documents']})==len(sh['source_documents']))
    assignments=sh['population_assignments']['assignments']
    declared={a['population_id'] for a in assignments}
    if sh['supplied_record_sets'] is not None:
        declared|={x['declared_genome_population']['population_id'] for x in sh['supplied_record_sets']['selection']['record_sets']}
        declared|={x['record_set_id'] for x in sh['supplied_record_sets']['selection']['record_sets']}
    check('all_population_ids_explicit:'+sh['analysis_id'],declared=={p['population_id'] for p in sh['populations']})
    views={v['view_id'] for v in sh['document_selection']['authoritative_views']}
    check('assignment_views_resolve:'+sh['analysis_id'],all(a['view_id'] is None or a['view_id'] in views for a in assignments))
    for nd in sh['native_documents']:
        check('native_document_binding:'+sh['analysis_id']+':'+nd['document']['document_id'],nd['document'] in sh['source_documents'])
    selected={d['document_id']:d for d in sh['document_selection']['documents']}
    check('explicit_document_producer_mapping:'+sh['analysis_id'],all(d['producer_evidence_id']==selected[d['document_id']]['producer_evidence_id'] for d in sh['source_documents']))
component_sets=['pathway_subsystem_components','saved_sheet_recalculation','families_components','hex_256_components']
sheets={s['analysis_id']:s for s in (main,fam,overflow)}
for name in component_sets:
    cs=val(name);sh=sheets[cs['analysis_id']]
    check('saved_sheet_hash:'+name,cs['sheet_sha256']==sha(canonical(sh)))
    requested={r['component_id']:r for r in cs['parameters']['requests']}
    check('one_component_per_request:'+name,set(requested)=={c['component_id'] for c in cs['components']})
    for c in cs['components']:
        check('population_binding:'+name+':'+c['component_id'],set(c['population_ids']) <= {p['population_id'] for p in sh['populations']})
        if c['ratio'] is not None:
            r=c['ratio']; n=r['numerator']['value'];d=r['denominator']['value']
            check('ratio:'+name+':'+c['component_id'],d>0 and math.isclose(c['value']['value'],r['scale']*n/d,rel_tol=1e-14,abs_tol=1e-14) and c['value']==r['output'])
            if r['component_population_id'] is not None:
                check('component_population_binding:'+name+':'+c['component_id'],r['component_population_id'] in {p['population_id'] for p in sh['populations']}|{m['membership_id'] for m in sh['reference_memberships']})

inp=json.loads((BASE/'source_executed_synthetic/discard_and_dependence/inputs.json').read_text())
raw=inp['pathway_response'];retained=raw[1:]
def occupancy(rows):
    return 100*len({(r['genome_id'],r['ec_number']) for r in rows})/(len({r['ec_number'] for r in rows})*len({r['genome_id'] for r in rows}))
check('independent_retained_occupancy_75',occupancy(retained)==75)
check('independent_full_input_occupancy_400_over_9',math.isclose(occupancy(raw),400/9))
cc={c['component_id']:c for c in val('pathway_subsystem_components')['components']}
check('reported_and_derived_75_same_retained_scope',main['pathway_rows'][0]['reported_ec_conservation_percent']['value']==75==cc['retained_pathway_percent']['value']['value'])
check('later_population_is_separate',cc['later_pathway_percent']['population_ids']!=cc['retained_pathway_percent']['population_ids'] and math.isclose(cc['later_pathway_percent']['value']['value'],400/9))
cats={}
for r in inp['subsystem_response'][1:]:cats.setdefault(r['genome_id'],set()).add(r['active'])
check('unambiguous_active_is_zero',sum(v=={'active'} for v in cats.values())==cc['unambiguous_active_genomes']['value']['value']==0)
check('unambiguous_likely_is_one',sum(v=={'likely'} for v in cats.values())==cc['unambiguous_likely_genomes']['value']['value']==1)
check('record_fraction_is_not_category',main['subsystem_rows'][0]['reported_record_genome_fraction']['value']==1)
lengths=[100,200,300];mean=sum(lengths)/len(lengths);sd=math.sqrt(sum((v-mean)**2 for v in lengths)/len(lengths))
check('population_SD_independent',math.isclose(fam['family_rows'][0]['reported_length_population_sd']['value'],sd,rel_tol=1e-15))
fcs={c['quantity']:c['value']['value'] for c in val('families_components')['components']}
check('family_three_ratios',fcs['family_returned_genome_occupancy']==2/3 and fcs['family_occurrences_per_positive_genome']==1.5 and math.isclose(fcs['family_length_cv'],sd/mean))
check('reported_zero_is_not_population_absence',fam['family_rows'][0]['genome_counts'][2]['reported_occurrences']['value']==0 and fam['family_rows'][0]['genome_counts'][2]['presence_state']=='no_record_completeness_unknown')
of=overflow['family_rows'][0]
check('overflow_unrepaired',of['raw_hex_counts']=='10001' and of['reported_feature_occurrences']['value']==257 and all(c['reported_occurrences']['state']=='incompatible' and c['reported_occurrences']['value'] is None for c in of['genome_counts']))
check('overflow_membership_preserved',of['positive_genome_count_from_list']['value']==2)
check('malformed_variant_raw_shape_preserved',main['variant_rows'][0]['header_field_count']==9 and main['variant_rows'][0]['data_field_count']==10)
w=val('qualified_data_wrapper');q=w['qualified_result'];b=w['raw_binding'];content=(BASE/'SYNTHETIC_DATA_RESPONSE_001.json').read_bytes()
check('Data_exact_value_byte_wrapper',b['source_ref']==q['binding']['source_ref'] and b['raw_artifact_ref']==q['binding']['native_artifact_ref']==b['bytes_key'] and b['sha256']==q['binding']['native_sha256']==q['grading']['parse_result']['retained_native_sha256']==q['grading']['parse_result']['sheet']['custody']['native_sha256']==sha(content) and b['byte_count']==len(content))
check('Data_synthetic_unique_ids_five',len(json.loads(content)['response']['docs'])==len({r['id'] for r in json.loads(content)['response']['docs']})==5)
check('Data_existing_reader_complete_synthetic_page',q['grading']['parse_result']['status']=='complete' and q['grading']['parse_result']['sheet']['page']['population_coverage']=='complete')
check('saved_recalculation_same_sheet_new_parameters',val('saved_sheet_recalculation')['sheet_sha256']==val('pathway_subsystem_components')['sheet_sha256'] and val('saved_sheet_recalculation')['components'][0]['value']['value']==.75 and cc['synthetic_reference_representation']['value']['value']==.5)
for state in ['available','missing','not_measured','failed','truncated','incompatible','invalid']:
    c=val('numeric_state_'+state);check('state_value:'+state,c['value']==0 if state=='available' else c['value'] is None)
nv=Validator({**schema,'$ref':'#/$defs/NumericCellV1'})
bad=copy.deepcopy(val('numeric_state_available'));bad['value']=True
check('boolean_rejected_as_number',not nv.is_valid(bad))
bad=copy.deepcopy(val('numeric_state_missing'));bad['value']=0
check('missing_zero_rejected',not nv.is_valid(bad))
bad=copy.deepcopy(val('numeric_state_available'));bad['invented_confidence']=.9
check('undeclared_field_rejected',not nv.is_valid(bad))
selector_validator=Validator({**schema,'$ref':'#/$defs/FactSelectorV1'})
selected=val('requested_selection')['fields']
check('computed_scalar_selector_exists',selected[1]['selector']=={'kind':'computed_measurement','component_id':'unambiguous_active_genomes'} and selector_validator.is_valid(selected[1]['selector']))
bad=copy.deepcopy(selected[2]['selector']);del bad['view_id']
check('native_measurement_requires_view',not selector_validator.is_valid(bad))
parent_schema=json.loads((BASE/'PARENT_RATIO_FORM_EXAMPLE_001.json').read_text())
parent_fact=json.loads((BASE/'PARENT_RATIO_FACT_EXAMPLE_001.json').read_text())
validate_closed_schema(parent_schema);Draft202012Validator(parent_schema).validate(parent_fact)
check('parent_form_existing_closed_schema_and_synthetic_shape',True)
check('examples_network_attempts_empty',filled['network_attempts']==[])
witness=json.loads((BASE/'SOURCE_WITNESS_RESULTS_001.json').read_text())
check('source_witness_eight_cases_and_no_network',witness['cases']==8 and witness['assertions_passed'] is True and witness['network_attempts']==[])
result=dict(classification='contract_shapes_and_independent_arithmetic_validation_not_production_grader_test',
    schema_definitions=len(schema['$defs']),conforming_examples=len(filled['examples']),passed_checks=len(checks),checks=checks,
    source_executed_synthetic_cases=8,production_comparative_systems_parser_executed=False,production_comparative_systems_calculator_executed=False,
    live_service_job=False,actual_episode_communication=False,real_Data_host_admission=False,all_passed=True)
(BASE/'CONTRACT_VALIDATION_001.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
