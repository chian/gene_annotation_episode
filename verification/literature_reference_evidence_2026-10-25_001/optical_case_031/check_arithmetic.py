"""Research-only arithmetic on named source line tokens; no production imports."""
from pathlib import Path
from decimal import Decimal as D
import json, hashlib
base=Path(__file__).resolve().parent
source=base.parents[2]/'research/experimental_scoring_review_2026-10-23/a105_optical_case_031/primary.txt'
raw=source.read_bytes();lines=raw.decode().splitlines()
def number(n):return D(lines[n-1])
h2_full=number(208);h2_mv=number(216)
nadh_full=D(lines[181].split()[0]);nadh_mv=number(190);nadh_without=number(176)
assert lines[206]=='Fd + Hyd' and lines[214]=='Fd + Hyd + methyl viologen'
assert lines[180]=='Fd + Hyd' and lines[188]=='Fd + Hyd + methyl viologen'
assert lines[209]=='<0.01'
results={
 'H2_difference':h2_full-h2_mv,'H2_retained':h2_mv/h2_full,
 'H2_fractional_decrease':1-h2_mv/h2_full,
 'NADH_difference':nadh_full-nadh_mv,'NADH_retained':nadh_mv/nadh_full,
 'NADH_fractional_decrease':1-nadh_mv/nadh_full,
 'NADH_no_addition_difference':nadh_full-nadh_without,
 'NADH_no_addition_retained':nadh_without/nadh_full,
 'H2_omission_ratio_upper':D('.01')/h2_full,
 'H2_omission_difference_lower':h2_full-D('.01')}
assert results['H2_difference']==D('4.98')
assert results['H2_retained']==D('.004')
assert results['H2_fractional_decrease']==D('.996')
assert results['NADH_difference']==2
assert results['NADH_no_addition_difference']==D('6.9')
assert results['H2_omission_ratio_upper']==D('.002')
assert results['H2_omission_difference_lower']==D('4.99')
result={'kind':'research_arithmetic_not_runtime_sheet','source_sha256':hashlib.sha256(raw).hexdigest(),
 'input_source_lines':[176,182,190,208,210,216],
 'numeric_results_decimal':{k:str(v) for k,v in results.items()},
 'bound_qualification':'strict source upper limit; nonnegative rate domain proposed; printed full rate held fixed; no sampling confidence bound',
 'unavailable':{'optical_reconstructed_rate':'raw sample/blank slopes and path unreported','recovery_k':'standard measured/reference pair unreported','source_likelihood':'uncertainty, dependence and applicable observation model unreported'},
 'checks':'source arm/threshold linkage and seven exact expected arithmetic assertions passed'}
(base/'arithmetic_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
