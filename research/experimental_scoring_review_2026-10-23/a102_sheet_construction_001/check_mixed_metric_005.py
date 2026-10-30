"""Synthetic arithmetic for additive A102 proposal 005; no native execution."""
from fractions import Fraction as F
from pathlib import Path
import json

checks=[]


def check(name,condition):
    if not condition:
        raise AssertionError(name)
    checks.append(name)


def positive(x):
    return max(F(0),x)


def compile_profiles(profile_rows):
    return positive(sum(w*(s-o) for w,s,o in profile_rows))


rmsd_support=F(72,100)*F(55,100)
rmsd_opposition=F(40,100)*F(25,100)
# Equal normalization lengths and same map/transform require equal native scores.
tm_support_native=(F(70,100),F(70,100))
tm_opposition_native=(F(50,100),F(50,100))
tm_support=min(tm_support_native)*F(55,100)
tm_opposition=min(tm_opposition_native)*F(25,100)
check("RMSD supporting contribution",rmsd_support == F(396,1000))
check("RMSD opposing contribution",rmsd_opposition == F(1,10))
check("TM supporting contribution",tm_support == F(385,1000))
check("TM opposing contribution",tm_opposition == F(125,1000))
mixed=compile_profiles([(F(1,2),rmsd_support,rmsd_opposition),(F(1,2),tm_support,tm_opposition)])
check("complete mixed contribution",mixed == F(278,1000))
no_recorded_opposition=(rmsd_support+tm_support)/2
check("no recorded opposition contribution",no_recorded_opposition == F(3905,10000))
margin_rmsd=rmsd_support-rmsd_opposition
missing_tm_alternative=[positive((margin_rmsd+tm_support-o)/2) for o in (F(1),F(0))]
check("included missing alternative bounds",missing_tm_alternative == [0,F(3405,10000)])
missing_channel=[positive((margin_rmsd+delta)/2) for delta in (F(-1),F(1))]
check("included missing TM channel bounds",missing_channel == [0,F(648,1000)])
adverse_tm_signed=(margin_rmsd+F(2,10)-F(6,10))/2
check("opposing metric retained before clipping",adverse_tm_signed == F(-52,1000) and positive(adverse_tm_signed)==0)
incorrect_early_clip=(positive(margin_rmsd)+positive(F(2,10)-F(6,10)))/2
check("early clipping would hide opposition",incorrect_early_clip == F(148,1000))
check("necessary contradiction fixes specific function at zero",compile_profiles([(F(1,2),rmsd_support*0,rmsd_opposition),(F(1,2),tm_support*0,tm_opposition)]) == 0)
necessity_bounds=[compile_profiles([(F(1,2),rmsd_support*v,rmsd_opposition),(F(1,2),tm_support*v,tm_opposition)]) for v in (0,1)]
check("shared unknown necessary predicate bounds",necessity_bounds == [0,mixed])
check("duplicate reference maximum unchanged",max(rmsd_support,rmsd_support)==rmsd_support)
check("TM perfect-pair count preserves both normalizations",tm_support_native[0] == tm_support_native[1] == F(70,100))
check("no duplicate coverage multiplier on TM",tm_support == F(70,100)*F(55,100))

result={
    "origin":"fully_synthetic_research_fixture_corrected_TM_pairs",
    "rmsd":{"support":float(rmsd_support),"opposition":float(rmsd_opposition)},
    "tm":{"native_support_pair":list(map(float,tm_support_native)),"native_opposition_pair":list(map(float,tm_opposition_native)),"normalization_lengths":[100,100],"support":float(tm_support),"opposition":float(tm_opposition)},
    "mixed_contribution":float(mixed),"no_recorded_opposition_contribution":float(no_recorded_opposition),
    "included_missing_tm_alternative_bounds":list(map(float,missing_tm_alternative)),
    "included_missing_tm_channel_bounds":list(map(float,missing_channel)),
    "adverse_tm_signed_margin":float(adverse_tm_signed),"incorrect_early_clip_example":float(incorrect_early_clip),
    "shared_necessity_bounds":list(map(float,necessity_bounds)),
    "assertions_passed":len(checks),"checks":checks,
}
with Path(__file__).with_name("mixed_metric_parent_arithmetic_005.json").open("x") as stream:
    json.dump(result,stream,indent=2,allow_nan=False)
    stream.write("\n")
print(json.dumps(result,indent=2))
