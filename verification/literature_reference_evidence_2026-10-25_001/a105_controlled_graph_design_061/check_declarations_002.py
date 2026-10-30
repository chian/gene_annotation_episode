"""Proposal declaration checks only; no counter/decoder/core call or production test."""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from jsonschema import Draft202012Validator
HERE=Path(__file__).resolve().parent
sealed=[]
for line in (HERE/'SHA256SUMS_001.txt').read_text().splitlines():
 digest,name=line.split('  ',1);assert sha256((HERE/name).read_bytes()).hexdigest()==digest,name;sealed.append(name)
old=json.loads((HERE/'GRAPH_RESULT_SCHEMA_001.json').read_text());new=json.loads((HERE/'GRAPH_RESULT_SCHEMA_002.json').read_text())
Draft202012Validator.check_schema(new)
p=new['$defs']['PixelResult']['properties'];assert p['counter_version']=={'const':'controlled_response_bar_runs_v1'};assert not any(x in p for x in ['core_version','core_sha256','core_counting_calibration'])
restored=deepcopy(new);r=restored['$defs']['PixelResult'];r['properties'].pop('counter_version');r['properties'].pop('counter_module_sha256')
for name in ['core_version','core_sha256','core_counting_calibration']:r['properties'][name]=deepcopy(old['$defs']['PixelResult']['properties'][name])
r['required']=old['$defs']['PixelResult']['required'];assert restored==old
schema=json.loads((HERE/'COUNT_RESULT_SCHEMA_002.json').read_text());Draft202012Validator.check_schema(schema)
validator=Draft202012Validator(schema)
f=Fraction(.1);assert (f.numerator,f.denominator)==(3602879701896397,36028797018963968)
assert not (1*f.denominator>=10*f.numerator);assert 2*f.denominator>=10*f.numerator
# Actual CONSTRUCTED raw RGB bytes; manually specified expected shape, not helper output.
rows=[]
for n in [1,0,2,2]:rows.append(bytes([0,0,0])*n+bytes([255,255,255])*(10-n))
rgb=b''.join(rows);assert len(rgb)==3*10*4
(HERE/'synthetic_count_raster_002.rgb').write_bytes(rgb)
example={'version':'controlled_response_bar_runs_v1','raster_rgb_sha256':sha256(rgb).hexdigest(),'image_size':{'width':10,'height':4},'selection':{'roi':{'left':0,'top':0,'right':10,'bottom':4},'rgb_min':[0,0,0],'rgb_max':[30,30,30],'minimum_row_fraction':.1,'minimum_run_rows':1},'row_fraction_exact':{'numerator':str(f.numerator),'denominator':str(f.denominator)},'qualifying_runs':[{'top':2,'bottom':4}],'status':'single_run'}
validator.validate(example)
rejections=[]
for label,modify in [('scientific_value',lambda d:d.update(value=1)),('scientific_unit',lambda d:d.update(unit='umol/min')),('calibration_input',lambda d:d['selection'].update(calibration={})),('terminal_edge_input',lambda d:d['selection'].update(terminal_edge='lower')),('negative_fraction',lambda d:d['row_fraction_exact'].update(numerator='-1')),('mismatched_status_cardinality',lambda d:d.update(status='multiple_runs'))]:
 bad=deepcopy(example);modify(bad);assert list(validator.iter_errors(bad)),label;rejections.append(label)
(HERE/'COUNT_EXPECTED_SHAPE_002.json').write_text(json.dumps(example,indent=2)+'\n')
receipt={'version':'controlled_response_count_declaration_check_002','kind':'schema_and_exact_arithmetic_checks_only','sealed001_files_verified':len(sealed),'sealed001_unchanged':True,'new_schemas_well_formed':2,'public_graph_delta_exact':True,'private_output_schema_example':'hand_constructed_expected_record_not_counter_output','raw_rgb_fixture':'synthetic_count_raster_002.rgb','raw_rgb_constructed_matching_pixels_by_row':[1,0,2,2],'binary_fraction_checked':{'numerator':str(f.numerator),'denominator':str(f.denominator),'one_of_ten_qualifies':False,'two_of_ten_qualifies':True},'schema_rejections':rejections,'new_count_helper_implemented_or_called':False,'new_decoder_implemented_or_called':False,'old_calibrated_core_called':False,'production_tests_run':False,'new_primary_or_scientific_source_reads':0,'new_model_calls':0,'implementation_identity_placeholder_created':False,'overall_schema_or_implementation_release':False}
(HERE/'DECLARATION_CHECK_002.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
