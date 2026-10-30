"""Fixed synthetic A106 arithmetic and shared-input bounds; no production work."""
from fractions import Fraction as F
from itertools import product
import json
import math
from pathlib import Path

C=F(9,10)
H=F(54,100)*F(8,10)


def point(W,K,R,bp,br=7):
    W,K,R,bp,br=map(F,(W,K,R,bp,br))
    d=W-K
    restoration=max(F(0),min(F(1),1-abs(R-W)/abs(d)))
    isolation=min(max(F(0),1-bp/abs(d)),max(F(0),1-br/abs(R-K)))
    return d/(W+K)*restoration*C*isolation*H


def reduced(W,K,R,bp):
    W,K,R,bp=map(F,(W,K,R,bp))
    return C*H/(W+K)*min((R-K)*(1-bp/(W-K)),R-K-7)


checks=[]


def check(name,condition):
    assert condition,name
    checks.append({'check':name,'passed':True})


central=point(100,20,90,8)
low=point(102,22,88,10)
high=point(98,18,92,6)
check('complete point',central==F(5103,25000))
check('tight rectangular lower',low==F(56133,310000))
check('tight rectangular upper',high==F(16281,72500))
check('interval contains point',low<central<high)
check('worker outer enclosure remains valid',F('0.176418')<=low and high<=F('0.233766'))
check('derivative root below entire W range',32+math.sqrt(540)<98)
for values in product([98,100,102],[18,20,22],[88,90,92],[6,8,10]):
    q=point(*values)
    check('same shared operands simplify exactly',q==reduced(*values))
    check('declared box enclosure',low<=q<=high)
check('mirrored effect reverses sign',point(20,100,30,8)==-central)
check('endpoint unit scaling does not change score',point(1000,200,900,80,70)==central)
check('amount ratio is a component not the final score',C!=central)

deficit=F(1,3)-F(3,197)
negative=-deficit*F(95,100)*F(9,10)
negative_bounds=[-(F(1,3)+F(2,100))*F(95,100)*F(9,10),-(F(1,3)-F(5,100))*F(95,100)*F(9,10)]
check('necessity point',negative==-F(2679,9850))
check('necessity bounds',negative_bounds==[F('-0.3021'),F('-0.24225')])
check('necessity interval contains point',negative_bounds[0]<negative<negative_bounds[1])
check('equal opposite groups cancel signed points',(central-central)/2==0)
check('new zero group dilutes the proposed design average',(central+0)/2==central/2)

record={'scope':'source-free proposed research calculation', 'check_count':len(checks),'checks':checks,
        'point':float(central),'point_exact':str(central),'tight_box_bounds':[float(low),float(high)],
        'tight_box_bounds_exact':[str(low),str(high)],'necessity_point':float(negative),
        'necessity_bounds':[float(x) for x in negative_bounds],
        'limitations':['synthetic input bounds, not confidence intervals','no primary-source inspection','no adopted scoring policy','no implemented reader or scorer']}
out=Path(__file__).with_name('parent_arithmetic_001.json')
with out.open('x') as f:
    json.dump(record,f,indent=2);f.write('\n')
print(json.dumps({'passed':len(checks),'point':float(central),'bounds':record['tight_box_bounds'],'necessity_point':float(negative)}))
