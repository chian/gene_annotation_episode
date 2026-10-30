"""Research arithmetic on explicit proposal inputs; no source or production reader."""
from fractions import Fraction as F
from pathlib import Path
import json
import math

checks = []


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def contrast(y, c, a):
    ec, ea = (y-c)**2, (y-a)**2
    return (ea-ec)/(ea+ec) if ea+ec else F(0)


def contrast_bounds(a, c):
    lower = (a[0]-c[1])/(a[0]+c[1]) if a[0]+c[1] else F(0)
    upper = (a[1]-c[0])/(a[1]+c[0]) if a[1]+c[0] else F(0)
    return lower, upper


reverse = contrast(F(5,11),F(1,2),F(1))
forward = contrast(F(10,11),F(1),F(0))
check("reverse exact contrast",reverse == F(143,145))
check("forward exact contrast",forward == F(99,101))
combined = (reverse+forward)/2
check("reaction account exact compilation",combined == F(14399,14645))
check("identical fitted predictions do not discriminate",contrast(F(1),F(1),F(1)) == 0)
check("identical wrong predictions do not discriminate",contrast(F(2),F(1),F(1)) == 0)
check("scalar unit rescaling preserves contrast",contrast(F(50,11),F(5),F(10)) == reverse)
check("swapping predictions reverses sign",contrast(F(5,11),F(1),F(1,2)) == -reverse)
pathway_bounds = [(combined-2)/3,(combined+2)/3]
check("pathway bounds ordered",-1 <= pathway_bounds[0] <= pathway_bounds[1] <= 1)
supplied_capacity = F(22,10)/2
coverage = min(F(1),supplied_capacity/F(1))
check("supplied-reagent capacity",supplied_capacity == F(11,10))
check("supplied-reagent coverage",coverage == 1)
check("same observation gets no added weighted score",combined + 0*(2*coverage-1) == combined)
p=F(16,25)
predicted=[math.comb(3,k)*p**k*(1-p)**(3-k) for k in range(4)]
check("isotope distribution normalization",sum(predicted) == 1)
check("isotope expectation",sum(k*v for k,v in enumerate(predicted)) == F(48,25))
check("isotope exact bins",predicted == [F(729,15625),F(3888,15625),F(6912,15625),F(4096,15625)])
check("zero-error interval",contrast_bounds((F(0),F(0)),(F(0),F(0))) == (0,0))
check("one exactly matching account interval",contrast_bounds((F(0),F(1)),(F(0),F(0))) == (0,1))
check("one exactly matching alternative interval",contrast_bounds((F(0),F(0)),(F(0),F(1))) == (-1,0))

# General compilation corners: these are synthetic mathematical inputs.
s_range=(F(-1,3),F(3,4)); d_range=(F(1,10),F(2,5))
compiled_bounds=((1-d_range[1])*s_range[0]-d_range[1],(1-d_range[0])*s_range[1]-d_range[0])
corners=[(1-d)*s-d for s in s_range for d in d_range]
check("compilation monotone corner bounds",compiled_bounds == (min(corners),max(corners)))
check("maximal bookkeeping deficit yields minus one",all((1-F(1))*s-F(1) == -1 for s in s_range))
check("balance alone supplies no positive score",(1-F(0))*F(0)-F(0) == 0)

result={
    "scope":"arithmetic on joined research proposal; source-filled approximate ratios remain conditional; no independent source inspection",
    "reverse_contrast":float(reverse),"forward_contrast":float(forward),
    "conditional_reaction_account":float(combined),"conditional_native_pathway_bounds":list(map(float,pathway_bounds)),
    "supplied_reagent_capacity_micromol_H2":float(supplied_capacity),"same_observation_extra_weight":0,
    "isotope_model_predicted_fractions":list(map(float,predicted)),"model_expected_labeled_oxygen_count":1.92,
    "synthetic_compilation_corner_bounds":list(map(float,compiled_bounds)),
    "assertions_passed":len(checks),"checks":checks,
}
with Path(__file__).with_name("parent_arithmetic_001.json").open("x") as stream:
    json.dump(result,stream,indent=2,allow_nan=False)
    stream.write("\n")
print(json.dumps(result,indent=2))
