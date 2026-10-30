"""Independent fixed-example checks of the proposed A102 sheet, not production."""
from fractions import Fraction as F
import json
import math
from pathlib import Path


def kernel(r, scale):
    return 1 / (1 + (r / scale) ** 2)


def base(n, lt, lr, rmsd):
    return 2 * n / (lt + lr) * kernel(rmsd, 2)


def geometry(distances):
    return sum(kernel(d, 1) for d in distances) / len(distances)


checks = []


def near(name, actual, expected):
    assert math.isclose(actual, float(expected), rel_tol=1e-12, abs_tol=1e-12), name
    checks.append({"name": name, "value": actual, "passed": True})


near("AF equal-length coverage", base(209,252,252,1.5), F(836,1575))
near("MJ0226 1ADJ", base(76,193,421,2.7), F(152,614)*F(400,1129))
near("MJ0226 1ATI", base(75,193,505,3.1), F(150,698)*F(400,1361))
near("MJ1 rounded RMSD squared sum", 76*2.7**2, F(55404,100))
near("MJ2 rounded RMSD squared sum", 75*3.1**2, F(72075,100))
near("unequal-length symmetric extent", 2*100/(100+200), F(2,3))
near("unequal-length max-denominator extent differs", 100/max(100,200), F(1,2))

bs, bo = base(90,100,100,1), base(80,100,100,2)
fs, fo = geometry([0,1,1,2]), geometry([1,2,2,3])
es, eo = bs*fs, bo*fo
near("support global geometry", bs, F(18,25))
near("opposing global geometry", bo, F(2,5))
near("support features", fs, F(11,20))
near("opposing features", fo, F(1,4))
near("support product", es, F(99,250))
near("opposing product", eo, F(1,10))
near("margin", max(0,es-eo), F(37,125))
near("duplicate row neutrality", max(es,es)-eo, F(37,125))
near("unresolved site lower", bs*F(1,2)-eo, F(13,50))
near("unresolved site upper", bs*F(3,4)-eo, F(11,25))

def bounds(n,r,distances,u):
    b=[n/100*kernel(r+u,2),n/100*kernel(max(0,r-u),2)]
    f=[geometry([d+u for d in distances]),geometry([max(0,d-u) for d in distances])]
    return [b[0]*f[0],b[1]*f[1]]

sb=bounds(90,1,[0,1,1,2],.2)
ob=bounds(80,2,[1,2,2,3],.2)
margin_bounds=[max(0,sb[0]-ob[1]),max(0,sb[1]-ob[0])]
exact_lower = F(45,68)*(F(25,26)+2*F(25,61)+F(25,146))/4 - F(80,181)*(F(25,41)+2*F(25,106)+F(25,221))/4
exact_upper = F(45,58)*(1+2*F(25,41)+F(25,106))/4 - F(80,221)*(F(25,61)+2*F(25,146)+F(25,281))/4
near("hard-bound lower", margin_bounds[0], exact_lower)
near("hard-bound upper", margin_bounds[1], exact_upper)

result={"status":"research_only", "check_count":len(checks), "checks":checks,
        "synthetic_margin":es-eo,"synthetic_hard_bounds":margin_bounds,
        "not_verified":["biological calibration","required feature definitions","native mixed-profile compilation","published functional point scores","production implementation"]}
target=Path(__file__).with_name("parent_arithmetic_002.json")
with target.open("x") as stream:
    json.dump(result,stream,indent=2)
    stream.write("\n")
print(json.dumps({"passed":len(checks),"margin":es-eo,"bounds":margin_bounds}))
