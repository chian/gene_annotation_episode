"""Independent research check of arithmetic, not experimental-value validation."""
from pathlib import Path
import json,math,statistics
P=Path(__file__).parent
e=json.loads((P/'EXTRACTION_001.json').read_text());a=json.loads((P/'ARITHMETIC_001.json').read_text())
checks=[]
for name,g in e['groups'].items():
 v=[float(x['value']) for x in g['observations']];mean=math.fsum(v)/len(v);sd=statistics.stdev(v)
 for cell,value in [('mean',mean),('sample_sd',sd),('cv',sd/mean)]:
  expected=float(a['summaries'][name][cell]);ok=math.isclose(value,expected,rel_tol=2e-15,abs_tol=1e-17)
  checks.append({'group':name,'component':cell,'independent_binary_result':value,'decimal_result':a['summaries'][name][cell],'pass':ok});assert ok
for name,c in a['contrasts'].items():
 d=math.fsum(float(x['value']) for x in e['groups'][c['reference_substrate']]['observations'])/3
 t=math.fsum(float(x['value']) for x in e['groups'][c['test_substrate']]['observations'])/3
 for cell,value in [('difference',d-t),('test_over_reference',t/d),('fractional_decrease',1-t/d),('reference_over_test',d/t)]:
  ok=math.isclose(value,float(c[cell]),rel_tol=2e-15,abs_tol=1e-17);assert ok
  checks.append({'contrast':name,'component':cell,'independent_binary_result':value,'decimal_result':c[cell],'pass':ok})
summary_cells=json.loads((P/'S1Table.xlsx.cells.json').read_text())[0]['cells'];lookup={x['cell']:x for x in summary_cells}
cross=[]
for name,cell in [('DHA','H7'),('L-EUS','H8'),('D-EUS','H9')]:
 token=lookup[cell]['value'];v,s=token.split('±');mean=float(a['summaries'][name]['mean'])
 cross.append({'substrate':name,'source':'originals/S1Table.xlsx','sheet':'Sheet1','cell':cell,'reported_token':token,'reported_spread_kind':'unspecified','derived_raw_mean':mean,'rounded_raw_mean_4dp':format(mean,'.4f'),'central_matches_4dp':format(mean,'.4f')==v,'reported_central_minus_raw_mean':float(v)-mean,'arithmetic_agreement_does_not_establish_uncertainty_type':True})
result={'arithmetic_checks':checks,'all_17_arithmetic_checks_pass':all(x['pass'] for x in checks),'summary_crosscheck':cross,'scope':'Independent arithmetic only; no confirmation of scientific measurements, reporter calibration, U conversion, independent preparations or production integration.'}
(P/'ARITHMETIC_VERIFICATION_001.json').write_text(json.dumps(result,indent=2));print(json.dumps({'checks':len(checks),'all_pass':all(x['pass'] for x in checks),'summary_crosscheck':cross},indent=2))
