"""Independent logical arithmetic for A108; every fixture value is synthetic."""
from pathlib import Path
from fractions import Fraction
import json
import math

HERE=Path(__file__).resolve().parent
checks=[]
def check(name, condition):
    assert condition,name
    checks.append(name)

def capability(rows):
    return [1-math.prod(1-row[k] for row in rows) for k in (0,1)]

def coverage(rows):
    return [sum(Fraction(row[k]) for row in rows)/len(rows) for k in (0,1)]

base=[[1,1]]*9+[[0,0]]*3
check('nine of twelve jointly compatible',coverage(base)==[Fraction(3,4)]*2)
check('one compatible state establishes capability',capability(base)==[1,1])
uncertain=[[0,1]]+base[1:]
check('measurement crossing unknown domain retains coverage bounds',coverage(uncertain)==[Fraction(2,3),Fraction(3,4)])
check('other witnesses retain capability',capability(uncertain)==[1,1])
rare=[[1,1]]+[[0,0]]*11
check('rare witness has distinct capability and frequency',capability(rare)==[1,1] and coverage(rare)==[Fraction(1,12)]*2)
all_negative=[[0,0]]*12
remainder=[0,1]
check('finite negatives do not exclude unexamined states',capability(all_negative+[remainder])==[0,1])
check('no observations leaves unresolved remainder',capability([remainder])==[0,1])
global_exclusion=[0,0]
excluded=[[s[k]*global_exclusion[k] for k in (0,1)] for s in all_negative+[remainder]]
check('a genuine whole-scope necessary exclusion propagates to remainder',capability(excluded)==[0,0])
check('paired fraction differs from product of marginal fractions',Fraction(10,12)*Fraction(11,12)!=Fraction(9,12))

result={'checks_passed':len(checks),'checks':checks,
        'synthetic':{'capability':[1,1],'coverage':[.75,.75],
                     'one_uncertain_coverage':[2/3,3/4],
                     'rare_witness':{'capability':[1,1],'coverage':[1/12,1/12]},
                     'finite_negative_capability':[0,1]}}
with (HERE/'organism_context_parent_arithmetic_002.json').open('x') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
