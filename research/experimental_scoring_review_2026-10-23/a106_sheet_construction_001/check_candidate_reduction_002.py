"""Research-only independent check of the proposed A106 candidate reduction."""
from fractions import Fraction as F
from pathlib import Path
from statistics import NormalDist
import json
import math

HERE = Path(__file__).resolve().parent
checks = []


def check(name, value):
    assert value, name
    checks.append(name)


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-13)


def pool(groups):
    return sum(h*a for h,a in groups)/max(1, sum(h for h,a in groups))


h = F(54,100)*F(8,10)
effect_a = F(2,3)*F(7,8)*F(9,10)*F(9,10)
effect_b = effect_a/2
q_a, q_b = h*effect_a, h*effect_b
check('source row factored exactly', q_a == F(5103,25000) and q_b == F(5103,50000))
other_h, other_effect = F(8,10), -F(15,100)
statement_a = pool([(h,effect_a),(other_h,other_effect)])
candidate = min(statement_a,q_b)
check('one candidate nominal', candidate == F(2103,30800))
check('zero correspondence group is neutral', pool([(h,effect_a),(other_h,other_effect),(F(0),F(1))]) == statement_a)
check('measured zero with positive correspondence changes denominator', pool([(h,effect_a),(other_h,F(0))]) == F(5103,30800))

z = NormalDist().inv_cdf(.975)
def candidate_value(h, delta):
    qa = 56.7*h/(120+2*delta)
    qb = 28.35*h/(120+2*delta)
    return min((qa-.12)/max(1,h+.8),qb)


results = {}
for n in (3,6):
    radius = z*2/math.sqrt(n)
    lower, upper = candidate_value(.378,radius), candidate_value(.486,-radius)
    results[str(n)] = {'sample_mean_covariance_entry':4/n,'common_error_radius':radius,
                      'candidate_lower':lower,'candidate_upper':upper,'coordinate':max(0,lower)}
check('three-block lower bound',close(results['3']['candidate_lower'],.04423852311606068))
check('three-block upper bound',close(results['3']['candidate_upper'],.09225213507719301))
check('six-block lower bound',close(results['6']['candidate_lower'],.04581073927568406))
check('six-block upper bound',close(results['6']['candidate_upper'],.09014587678339729))
check('actual replication narrows stipulated interval',results['6']['candidate_lower']>results['3']['candidate_lower'] and results['6']['candidate_upper']<results['3']['candidate_upper'])
before = 28.35*.378/(120+2*z*2/math.sqrt(3))
check('before-opposition contribution',close(before,.08605649011535974))
check('contrary evidence lowers candidate',results['3']['coordinate']<before)

# An interior breakpoint matters: a=(+1,-1), H1 in [.8,1.2], H2 fixed .1.
# Cap each H in [0,1] as specified; H1 in [.8,1] is enough to cross sum H=1.
# Minimum/maximum over this example are at box endpoints; a constant-positive
# example shows the kink explicitly, rather than assuming a smooth ratio.
for hx in (.8,.9,1):
    actual=pool([(hx,1),(.1,1)])
    check('floor-one branch at H='+str(hx),close(actual,min(hx+.1,1)))

# A fully relevant source retains its influence; weak correspondences can
# accumulate under this proposed rule. This is a convention, not calibration.
weak_single=pool([(.1,.8)])
weak_ten=pool([(.1,.8)]*10)
check('explicit weak-source accumulation consequence',close(weak_single,.08) and close(weak_ten,.8))

result={'checks_passed':len(checks),'checks':checks,'nominal':float(candidate),
        'before_contrary':before,'joint_bounds':results,
        'weak_source_convention':{'one':weak_single,'ten_distinct':weak_ten}}
with (HERE/'candidate_reduction_parent_arithmetic_002.json').open('x') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
