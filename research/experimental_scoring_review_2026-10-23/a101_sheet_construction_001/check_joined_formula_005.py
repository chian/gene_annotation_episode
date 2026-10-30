"""Independent synthetic A101 calculation; no source or production imports."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
checks = []
rows = [
    ("blast", "F", 80., 1, 60, 1., .8),
    ("blast", "F", 60., 41, 100, 1., .7),
    ("blast", "G", 65., 1, 60, 1., .75),
    ("hmmer", "F", 50., 1, 50, 50/60, None),
    ("hmmer", "F", 70., 51, 100, 1., None),
    ("hmmer", "F", 45., 1, 50, 50/60, None),
    ("hmmer", "G", 60., 1, 50, 1., None),
]


def check(name, actual, expected):
    if not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12):
        raise AssertionError((name, actual, expected))
    checks.append(name)


def calculate(comparisons, regions=((1,100),), scale=1., identity_mix=.5, tools=("blast","hmmer")):
    arrays = {tool: {label: [0.]*100 for label in ("F","G")} for tool in tools}
    for tool, label, bits, start, end, reference_fraction, identity in comparisons:
        if tool not in tools:
            continue
        coefficient = {"blast": .025, "hmmer": .020}[tool]
        weight = -math.expm1(-coefficient*scale*max(0., bits))*reference_fraction
        if tool == "blast":
            weight *= (1-identity_mix) + identity_mix*identity
        for position in range(start-1,end):
            arrays[tool][label][position] = max(arrays[tool][label][position],weight)
    by_region = []
    for start,end in regions:
        tool_rows = {}
        for tool in tools:
            support = arrays[tool]["F"][start-1:end]
            opposition = arrays[tool]["G"][start-1:end]
            correspondence = math.fsum(support)/len(support)
            penalty = math.fsum(s*o for s,o in zip(support,opposition))/len(support)
            direct = math.fsum(s*(1-o) for s,o in zip(support,opposition))/len(support)
            check(f"equivalent subtraction/direct form {tool}/{start}:{end}/{scale}/{identity_mix}", correspondence-penalty,direct)
            tool_rows[tool] = {"correspondence":correspondence,"opposition_penalty":penalty,"remaining":direct}
        combined = math.fsum(row["remaining"] for row in tool_rows.values())/len(tools)
        by_region.append({"start":start,"end":end,"tools":tool_rows,"combined":combined})
    native = math.prod(region["combined"] for region in by_region)**(1/len(by_region))
    return {"regions":by_region,"native":native,"qualified":native*.8}


base = calculate(rows)
check("complete synthetic native",base["native"],.42949040282429574)
check("complete synthetic qualified",base["qualified"],.3435923222594366)
check("duplicate representation unchanged",calculate(rows+[rows[0]])["qualified"],base["qualified"])
check("weaker profile unchanged",calculate([r for i,r in enumerate(rows) if i!=5])["qualified"],base["qualified"])
without_opposition = calculate([r for r in rows if r[1]=="F"])
check("no recorded opposition fixture",without_opposition["qualified"],.5484559107238102)
two_regions = calculate(rows,regions=((1,50),(51,100)))
check("two required regions",two_regions["qualified"],.28786658623399014)
single_tools = {tool: calculate(rows,tools=(tool,))["qualified"] for tool in ("blast","hmmer")}
check("BLAST-only named profile",single_tools["blast"],.322359745578893)
check("HMMER-only named profile",single_tools["hmmer"],.364824898939980)
scales = {str(scale):calculate(rows,scale=scale)["qualified"] for scale in (.5,1.,2.)}
check("half native scales",scales["0.5"],.278513274974905)
check("double native scales",scales["2.0"],.363839961812128)
feature_missing_bounds = [base["native"]*factor for factor in (.8,.9)]
check("feature bound lower",feature_missing_bounds[0],.3435923222594366)
check("feature bound upper",feature_missing_bounds[1],.3865413625418662)
included_missing = [.5*.6*.8,(.5*.6+.5)*.8]
check("included missing tool lower",included_missing[0],.24)
check("included missing tool upper",included_missing[1],.64)
ambiguous_membership = [.4*(1-.7),.7]
check("ambiguous F-or-G lower",ambiguous_membership[0],.12)
check("ambiguous F-or-G upper",ambiguous_membership[1],.7)

result = {
    "origin":"fully_synthetic_no_native_run",
    "inspection_scope":"complete current joined numerical sheet, IO and worked example; no new paper-specific packet",
    "base":base,"without_recorded_opposition":without_opposition,
    "two_required_regions":two_regions,"single_tool_profiles":single_tools,
    "inverse_bit_scale_sensitivity":scales,"feature_missing_bounds":feature_missing_bounds,
    "included_missing_channel_bounds":included_missing,"ambiguous_membership_bounds":ambiguous_membership,
    "assertions_passed":len(checks),"checks":checks,
}
with (ROOT/"joined_formula_parent_arithmetic_005.json").open("x") as stream:
    json.dump(result,stream,indent=2,allow_nan=False)
    stream.write("\n")
print(json.dumps({"assertions_passed":len(checks),"base":base,"scale_sensitivity":scales},indent=2))
