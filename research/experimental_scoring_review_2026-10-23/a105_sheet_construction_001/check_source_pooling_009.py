"""Source-free checks of an unadopted A105 source-pooling proposal."""
import itertools
import json
import math
from pathlib import Path


def difference(ds):
    if not ds:
        return None
    return max(0,max(ds))-max(0,max(-d for d in ds))


def accumulate(ds):
    return math.tanh(sum(math.atanh(d) for d in ds))


checks=[]


def check(name, condition):
    assert condition, name
    checks.append({"check":name,"passed":True})


def near(a,b):
    return math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)


p=.8*math.tanh(2)
w=.4*math.tanh(1)
scenarios=[("one",[p]),("weaker positive",[p,w]),("contrary",[p,-w]),
           ("ten positive plus contrary",[p]*10+[-w]),("equal opposed",[p,-p]),
           ("zero append",[p,0])]
rows=[{"scenario":name,"indexes":ds,"difference":difference(ds),"unit_accumulation":accumulate(ds)} for name,ds in scenarios]
check("single source unchanged",near(difference([p]),p))
check("negative singleton unchanged before projection",near(difference([-w]),-w))
check("weaker positive not counted",near(difference([p,w]),p))
check("opposition retained",near(difference([p,-w]),p-w))
check("duplicate representation cannot change maximum",near(difference([p,p,-w]),difference([p,-w])))
check("many equal homolog indexes do not amplify",near(difference([p]*10+[-w]),p-w))
check("zero append neutral",near(difference([p,0]),p))
check("equal opposite cancellation",difference([p,-p])==0)
check("empty evidence remains unknown",difference([]) is None)
check("current source correction replaces old maximum",near(difference([.2,-w]),.2-w))
new_repeat=.8*math.tanh(3)
check("independent repeat inside original source can improve contribution",new_repeat>p and near(difference([new_repeat,-w])-difference([p,-w]),new_repeat-p))

intervals=[(-.9,.3),(.2,.8),(-.4,.1)]
lo=difference([a for a,b in intervals]); hi=difference([b for a,b in intervals])
for values in itertools.product(*[(a,(a+b)/2,b) for a,b in intervals]):
    check("rectangular missingness bound",lo<=difference(list(values))<=hi)
for ds in itertools.product([-.9,-.3,0,.2,.8],repeat=3):
    score=difference(list(ds))
    check("bounded signed index",-1<=score<=1)
    for i,d in enumerate(ds):
        changed=list(ds); changed[i]=min(1,d+.1)
        check("coordinatewise monotonicity",difference(changed)>=score-1e-15)

record={"kind":"unadopted_research_arithmetic","check_count":len(checks),"checks":checks,
        "scenarios":rows,"independent_repeat_source_index":new_repeat,
        "rectangular_example_bounds":[lo,hi],
        "limits":["not a calibrated probability","no independent-homolog accumulation","max pooling does not correct selection bias","user choice unanswered"]}
target=Path(__file__).with_name('source_pooling_parent_arithmetic_009.json')
with target.open('x') as stream:
    json.dump(record,stream,indent=2);stream.write('\n')
print(json.dumps({"passed":len(checks),"scenarios":rows,"independent_repeat_source_index":new_repeat}))
