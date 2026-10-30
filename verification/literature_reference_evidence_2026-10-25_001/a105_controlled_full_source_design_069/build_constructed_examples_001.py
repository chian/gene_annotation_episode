"""Constructed sources + HAND projections, then actual accepted068 arithmetic.

No full-v2 reader exists here. The hand projection is not source execution,
model extraction, primary evidence, native operation or typed-return coverage.
"""
from copy import deepcopy as cp
from fractions import Fraction
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys

from PIL import Image, ImageDraw
from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.domain import identity
from gene_annotation_episode.literature_controlled_response_owner_calculations import populate_controlled_response_owner
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

def put(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

def h(raw): return hashlib.sha256(raw).hexdigest()
def source_id(name): return "source_" + h(name.encode())[:24]
main, cov, img, scale_ref = [source_id(n) for n in ("fresh069_text", "fresh069_C", "fresh069_image", "fresh069_scale_only")]
text = "\n".join("<p>" + x + "</p>" for x in [
    "Engineering fixture; no paper or biological observation.", "Organism: constructed system.", "Genotype: constructed genotype.",
    "Construct: protein X.", "Construct: no protein.", "Preparation: constructed preparation.", "System: purified fixture assay.",
    "Endpoint: product formation.", "Normalization: identical reaction volume.", "Protein present.", "Protein-free B reference.",
    "Condition one.", "Condition zero.", "Reference condition.", "Physical A.", "Physical B.", "Physical C.",
    "The same B reference is applied to both conditions with stated invariance.", "Only the intended factor differs.",
    "A mean: 10 nmol/min.", "B mean: 4 nmol/min.", "B alternate mean: 5 nmol/min.", "C mean: 8 nmol/min.",
    "B numerical operand is unreadable.", "Reported SD: 1.2 nmol/min.", "n = 3 biological preparations.",
    "Reported CI: [8, 12] nmol/min at 95% confidence.", "Plot first tick: 0.", "Plot second tick: 20.",
    "Plot unit: nmol/min.", "Physical identity is conflicting between these source statements.",
    "A range mean: 1e309 nmol/min.",
    "The text and plot describe the same experimental means; either listed representation assignment is source-compatible.",
]) + "\n"
source_bytes = {main: text.encode(), scale_ref: b"<p>linear scale</p>\n"}
im = Image.new("RGB", (100, 220), "white")
draw = ImageDraw.Draw(im)
draw.rectangle((20, 159, 29, 199), fill="black")  # B=4.05 [3.95,4.15]
draw.rectangle((50, 99, 59, 199), fill="black")   # A=10.05 [9.95,10.15]
out = BytesIO(); im.save(out, format="PNG"); im.close()
source_bytes[img] = out.getvalue()
(HERE / "CONSTRUCTED_GRAPH_001.png").write_bytes(source_bytes[img])

def witness(quote, source=main, tagged=True):
    data = source_bytes[source]
    start = data.index(quote.encode())
    w = dict(source_ref=source, representation="original", start=start, end=start+len(quote.encode()), quote=quote)
    return dict(kind="text", **w) if tagged else w

def interp(value, quote=None, source=main):
    return dict(value=value, witnesses=[] if quote is None else [witness(quote, source)])

def meaning(quote, status="known"):
    w = witness(quote)
    return dict(status=status, label=quote, witnesses=[] if status=="unknown" else [w], canonical_witness=w if status=="known" else None,
                canonical_correspondence=interp("same", quote) if status=="known" else interp("unknown"))

def number(quote, token):
    at = quote.index(token)
    return dict(witness=witness(quote, tagged=False), number_start=at, number_end=at+len(token))

def token_witness(quote, token):
    w=witness(quote); at=quote.index(token)
    w.update(start=w["start"]+len(quote[:at].encode()),end=w["start"]+len(quote[:at+len(token)].encode()),quote=token)
    return w

def literal(role, value):
    quote = role + " mean: " + str(value) + " nmol/min."
    return dict(kind="source_literal", literal=dict(status="exact", candidates=[number(quote,str(value))], fragments=[]),
                unit=witness("nmol/min", tagged=False))

def unknown_unc():
    return dict(statistic=interp("unreported"), magnitude=None, interval=None, unit=None,
        unit_relationship=interp("unknown"), confidence_level=None, count=None, repetition_basis=interp("unknown"), estimate_basis=interp("unknown"))

def arm(role, condition, protein):
    return dict(source_kind="synthetic_fixture", context={
        "subject": witness("Construct: protein X." if protein else "Construct: no protein."),
        "organism": witness("Organism: constructed system."), "genotype": witness("Genotype: constructed genotype."),
        "construct": witness("Construct: protein X." if protein else "Construct: no protein."),
        "preparation": witness("Preparation: constructed preparation."), "experimental_system": witness("System: purified fixture assay.")},
        protein_arrangement=interp("protein_present" if protein else "protein_free_control", "Protein present." if protein else "Protein-free B reference."),
        subject_construct=meaning("Construct: protein X." if protein else "Construct: no protein."), condition=meaning(condition),
        endpoint=meaning("Endpoint: product formation."), normalization=meaning("Normalization: identical reaction volume."),
        physical_observation=meaning("Physical " + role + "."), intended_factor_level=witness(condition),
        measurement=literal(role, {"A":10,"B":4,"C":8}[role]), reported_uncertainty=unknown_unc())

def graph(role="B"):
    left = 20 if role=="B" else 50
    return dict(kind="linear_bar", image_id="constructed", terminal_edge="upper",
        bar_selection=dict(roi=dict(left=left,top=10,right=left+10,bottom=205),rgb_min=[0]*3,rgb_max=[0]*3,
            minimum_row_fraction=1,minimum_run_rows=2,edge_tolerance_pixels=.5),
        axis=dict(first=dict(pixel=200,tick=dict(status="exact",candidates=[token_witness("Plot first tick: 0.","0")],fragments=[])),
                  second=dict(pixel=0,tick=dict(status="exact",candidates=[token_witness("Plot second tick: 20.","20")],fragments=[])),
                  unit=dict(status="exact",candidates=[witness("nmol/min")],fragments=[]),
                  scale=dict(status="known",kind="linear",basis="source_text_literal",witnesses=[witness("linear scale",scale_ref)])))

roles = ["protein_condition1", "empty_condition1", "protein_condition0", "empty_condition0"]
args = dict(version="controlled_response_source_selection_v2",source_ref=main,
    images=[dict(image_id="constructed",source_ref=img,original_source_ref=img,mapping=None)],
    arms={r:arm(x,c,p) for r,x,c,p in zip(roles,"ABCB",["Condition one.","Reference condition.","Condition zero.","Reference condition."],[True,False,True,False])},
    relationships=dict(condition1_target=meaning("Condition one."),condition0_target=meaning("Condition zero."),
        condition_levels_relation=interp("different","Only the intended factor differs."),
        subject_construct_across_conditions=interp("same","Construct: protein X."),
        condition1_control_application=interp("shared_reference_assumption","The same B reference is applied to both conditions with stated invariance."),
        condition0_control_application=interp("shared_reference_assumption","The same B reference is applied to both conditions with stated invariance."),
        control_reference_reuse=interp("same_reference_with_stated_invariance","The same B reference is applied to both conditions with stated invariance."),
        nonintended_conditions=interp("matched","Only the intended factor differs."),intended_factor=witness("Only the intended factor differs.")),
    covariance=None,variance_status=interp("known"),model_kind=interp("known_joint_normal_source_means"))
args["arms"][roles[3]]["measurement"] = graph()
doc = dict(version="controlled_response_covariance_source_v1",variables=[
    dict(label="duplicate",unit="nmol/min",description="Physical B."),
    dict(label="duplicate",unit="nmol/min",description="Physical C."),
    dict(label="A",unit="nmol/min",description="Physical A."),
    dict(label="unused",unit="nmol/min",description="Unused source variable.")],
    covariance=[[.25,0,0,0],[0,.20,.03,0],[0,.03,.16,0],[0,0,0,.1]],
    origin="synthetic",variance_status="known",model_kind="known_joint_normal_source_means")

def bind_cov(a, document, mapping):
    source_bytes[cov] = (json.dumps(document,indent=2)+"\n").encode()
    data = source_bytes[cov]
    labels = list(re.finditer(rb'"label":\s*("(?:[^"\\]|\\.)*")',data))
    bindings = {}
    for role, index in zip(roles,mapping):
        if index is None: bindings[role] = None; continue
        start,end = labels[index].span(1)
        w = dict(source_ref=cov,representation="original",start=start,end=end,quote=data[start:end].decode())
        bindings[role] = dict(variable_index=index,label_witness=w,owner_witness=cp(a["arms"][role]["physical_observation"]["canonical_witness"]),
            correspondence=dict(value="same",witnesses=[dict(kind="text",**w)]))
    a["covariance"] = dict(source_ref=cov,bindings=bindings)
    for key in ("variance_status","model_kind"):
        a[key] = dict(value=document[key],witnesses=[witness(json.dumps(document[key]),cov)])
    return cp(data.decode())

def canonical(meaning, name):
    w = meaning["canonical_witness"]
    if w is None or meaning["status"] != "known": return None
    raw = source_bytes[w["source_ref"]]
    loc = dict(kind="text",source_ref=w["source_ref"],artifact_ref="artifact_"+h(raw),byte_sha256=h(raw),start=w["start"],end=w["end"])
    return identity("controlled_"+name,loc)

def pure_arm(a, role):
    m = a["measurement"]
    state,value,unit,origin,relation,interval,source = "point",None,"nmol/min","synthetic","eq",None,"hand_reading_"+role
    if m is None:
        state,unit,relation,source = "missing",None,"none",None
    elif m["kind"] == "linear_bar":
        value = 4.05 if m["bar_selection"]["roi"]["left"]==20 else 10.05
        origin,relation,interval = "graph_derived","interval",dict(lower=value-.1,upper=value+.1)
        # Use decimal strings to state exact intended hand domain, not binary +-.
        interval = dict(lower=3.95,upper=4.15) if value==4.05 else dict(lower=9.95,upper=10.15)
    elif m["literal"]["status"]=="unreadable":
        state,relation,value = "unsupported","none",None
        unit = None if m["unit"] is None else "nmol/min"
    else:
        n = m["literal"]["candidates"][0]
        value = float(n["witness"]["quote"][n["number_start"]:n["number_end"]])
        if not math.isfinite(value): state,relation,value="unsupported","none",None
        if m["unit"] is None: unit=None
    meanings = ["endpoint","normalization","subject_construct","condition","physical_observation"]
    return dict(value=value,threshold=None,relation=relation,approximate=origin=="graph_derived",unit=unit,status=state,
        **{k+"_id":canonical(a[k],k) for k in meanings},source_observation_id=source,origin=origin,digitization_interval=interval,
        protein_arrangement=a["protein_arrangement"]["value"],meaning_statuses={k:a[k]["status"] for k in meanings})

def hand_projection(a, document):
    arms = {r:pure_arm(a["arms"][r],r) for r in roles}
    relationship = {k:(dict(status=v["status"],canonical_id=canonical(v,"condition")) if k.endswith("_target") else
        "hand_intended_factor" if k=="intended_factor" else v["value"]) for k,v in a["relationships"].items()}
    by_owner = {}
    for role in roles:
        b = a["covariance"]["bindings"][role]
        if b is None: continue
        owner = arms[role]["physical_observation_id"]
        if owner is not None: by_owner.setdefault(owner,b["variable_index"])
    ordered = sorted(by_owner,key=by_owner.get)
    indices = [by_owner[o] for o in ordered]
    return dict(version="controlled_response_owner_inputs_v2",arms=arms,relationships=relationship,
        covariance=dict(physical_observation_ids=ordered,units=[document["variables"][i]["unit"] for i in indices],
                        matrix=[[document["covariance"][i][j] for j in indices] for i in indices]) if ordered else None,
        variance_status=document["variance_status"] if ordered else "unknown",model_kind=document["model_kind"])

cases=[]
def case(name, a, document=None, mapping=(2,0,1,0), *, source_invalid=False, expected_uncertainty=None):
    document = cp(doc if document is None else document)
    raw = bind_cov(a,document,mapping)
    p = hand_projection(a,document)
    # The authoritative source validation is not implemented/executed. The
    # expected invalid-source handling is specified by hand BEFORE068 sees data.
    if source_invalid: p.update(covariance=None,variance_status="unknown",model_kind="none")
    result = populate_controlled_response_owner(p)
    cases.append(dict(name=name,kind="constructed_sources_hand_projection_actual068_arithmetic",selection=a,
        source_covariance_text=raw,hand_calculation_inputs=p,actual_068_sheet=result,
        source_reader_executed=False,source_validation_expected="invalid" if source_invalid else "valid",
        expected_reported_uncertainty=expected_uncertainty))

case("same_B_text_graph",cp(args))
a=cp(args)
for r in (roles[1],roles[3]): a["arms"][r]["measurement"] = None
case("both_B_numbers_units_absent_with_AC_from_full_source",a,mapping=(2,None,1,None))
a=cp(args)
a["arms"][roles[1]]["measurement"] = dict(kind="source_literal",literal=dict(status="unreadable",candidates=[],fragments=[witness("B numerical operand is unreadable.")]),unit=None)
a["arms"][roles[3]]["measurement"] = None
case("unreadable_B_retained_science",a,mapping=(2,None,1,None))
a=cp(args); a["arms"][roles[3]]["measurement"]=literal("B alternate",5)
case("canceled_B_4_vs_5_numeric_conflict",a)
a=cp(args); a["arms"][roles[3]]["physical_observation"]=meaning("Physical B.","unknown")
a["relationships"]["control_reference_reuse"]=interp("unknown")
case("unknown_active_owner_equal_known_required_provided",a,mapping=(2,0,1,None))
a=cp(args); m=a["arms"][roles[3]]["physical_observation"]
m.update(status="conflicting",canonical_witness=None,canonical_correspondence=interp("unknown"),witnesses=[witness("Physical B."),witness("Physical identity is conflicting between these source statements.")])
case("actual_scientific_owner_conflict",a,mapping=(2,0,1,None))
for statistic in ("sd","ci"):
    a=cp(args); a["arms"][roles[0]]["measurement"]=graph("A")
    u=a["arms"][roles[0]]["reported_uncertainty"]
    u.update(statistic=interp(statistic,"Reported SD: 1.2 nmol/min." if statistic=="sd" else "Reported CI: [8, 12] nmol/min at 95% confidence."),
        unit_relationship=interp("same_as_response","Plot unit: nmol/min."),
        count=number("n = 3 biological preparations.","3"),repetition_basis=interp("biological_preparations","n = 3 biological preparations."))
    if statistic=="sd": u["magnitude"]=number("Reported SD: 1.2 nmol/min.","1.2")
    else:
        q="Reported CI: [8, 12] nmol/min at 95% confidence."
        u.update(interval=dict(witness=witness(q,tagged=False),lower_start=q.index("8"),lower_end=q.index("8")+1,
            upper_start=q.index("12"),upper_end=q.index("12")+2),confidence_level=witness("95%",tagged=False))
    case("active_graph_physical_unit_with_"+statistic,a,expected_uncertainty=dict(canonical_unit="umol/min",magnitude=.0012 if statistic=="sd" else None,
        interval=[.008,.012] if statistic=="ci" else None,count=3,repetition_basis="biological_preparations",computed_from_source_C=False))
small=cp(doc); small["variables"]=[small["variables"][2],small["variables"][1]];small["covariance"]=[[.16,.03],[.03,.20]]
case("legitimate_actual_AC_only_source_matrix",cp(args),small,mapping=(0,None,1,None))
bad=cp(doc);bad["covariance"][0][0]=-.25
case("full_invalid_source_C_no_favorable_submatrix",cp(args),bad,mapping=(2,None,1,None),source_invalid=True)
a=cp(args);a["relationships"]["condition1_control_application"]=interp("unknown")
case("unknown_actual_control_application",a)
a=cp(args);big=cp(doc);big["covariance"][2][2]=0;big["covariance"][2][1]=big["covariance"][1][2]=0;big["covariance"][1][1]=0
case("zero_active_V",a,big,mapping=(2,None,1,None))
a=cp(args);a["arms"][roles[0]]["measurement"]=literal("A range","1e309")
case("authentic_active_scalar_outside_float_range",a)
tiny=cp(doc);tiny["covariance"][2][2]=tiny["covariance"][1][1]=1e-320;tiny["covariance"][2][1]=tiny["covariance"][1][2]=0
case("variance_cell_underflow_retains_representable_SE",cp(args),tiny,mapping=(2,None,1,None))

selection_schema=json.loads((BASE/"a105_controlled_graph_design_061/SELECTION_SCHEMA_V2_001.json").read_text())
owner_schema=json.loads((BASE/"a105_controlled_adapter_design_065/OWNER_INPUT_SCHEMA_004.json").read_text())
sheet_schema=json.loads((BASE/"a105_controlled_adapter_design_065/OWNER_OUTPUT_SCHEMA_004.json").read_text())
for c in cases:
    Draft202012Validator(selection_schema).validate(c["selection"])
    Draft202012Validator(owner_schema).validate(c["hand_calculation_inputs"])
    Draft202012Validator(sheet_schema).validate(c["actual_068_sheet"])

# The v3 proposal retains an actual independently nominated active companion.
a=cp(args);bind_cov(a,doc,(2,0,1,0));a["version"]="controlled_response_source_selection_v3"
reading=cp(a["arms"][roles[0]]);reading["measurement"]=graph("A")
a["companion_readings"]=[dict(reading_key="active_A_graph_companion",primary_role=roles[0],reading=reading)]
a["joint_reading_assignments"]=[dict(assignment={r:key if r==roles[0] else None for r in roles},admissibility=interp("compatible",
    "The text and plot describe the same experimental means; either listed representation assignment is source-compatible.")) for key in (None,"active_A_graph_companion")]
Draft202012Validator(json.loads((HERE/"COMPANION_SELECTION_SCHEMA_V3_PROPOSAL_001.json").read_text())).validate(a)
put("ACTIVE_COMPANION_REQUEST_V3_PROPOSAL_001.json",dict(selection=a,expected_projection_status="unresolved_active_reconciliation",
    expected_calculation_inputs=None,primary_A=10,graph_A_hand_domain=[9.95,10.15],
    limitation="A reported point lies in a graph digitization domain, but no active-reconciliation model is adopted or executed."))
primary=cp(cases[0]["hand_calculation_inputs"])
companion=cp(primary); companion["arms"][roles[0]]=pure_arm(reading,roles[0])
companion["arms"][roles[0]]["source_observation_id"]="hand_reading_active_A_graph_companion"
alternative_inputs=[dict(reading_assignment={r:None for r in roles},calculation_inputs=primary),
    dict(reading_assignment={r:"active_A_graph_companion" if r==roles[0] else None for r in roles},calculation_inputs=companion)]
alternatives=[dict(reading_assignment=x["reading_assignment"],sheet=populate_controlled_response_owner(x["calculation_inputs"])) for x in alternative_inputs]
masked=cp(primary)
masked["arms"][roles[0]].update(value=None,threshold=None,relation="none",approximate=True,status="ambiguous",origin="graph_derived",digitization_interval=None,
    source_observation_id="HAND_retained_active_A_nomination_group")
partial_sheet=populate_controlled_response_owner(masked)
unaffected={};conditional=[]
final_sensitive={"controlled_response_difference","source_profile_log_ratio","source_signed_index"}
dependencies={}
components=list(alternatives[0]["sheet"]["cells"])
for i,component in enumerate(components):
    dependencies[component]=dict(scientific_roles=[] if i<4 else roles[:2] if i==4 else roles[2:] if i==5 else roles,
        numeric_roles=[roles[i]] if i<4 else roles[:2] if i==4 else roles[2:] if i==5 else partial_sheet["contrast_dependencies"]["active_roles"],
        covariance_owner_ids=partial_sheet["contrast_dependencies"]["required_covariance_owner_ids"] if i>=7 else [],
        model_active_roles=partial_sheet["contrast_dependencies"]["model_active_roles"] if i>=10 else [])
    first=alternatives[0]["sheet"]["cells"][component]
    unaffected_dependency=roles[0] not in dependencies[component]["numeric_roles"] and roles[0] not in dependencies[component]["scientific_roles"]
    same=unaffected_dependency and all(x["sheet"]["cells"][component]==first for x in alternatives[1:]) and component not in final_sensitive and first==partial_sheet["cells"][component]
    unaffected[component]=first if same else None
    if not same:
        conditional.extend(dict(alternative_index=i,component=component,cell=x["sheet"]["cells"][component]) for i,x in enumerate(alternatives))
partial=dict(version="controlled_response_conditional_population_v3",projection_status="unresolved_active_reconciliation",
    final_sheet=None,partial_sheet=partial_sheet,unresolved_roles=[roles[0]],component_dependencies=dependencies,
    alternatives=alternatives,unaffected_cells=unaffected,conditional_cells=conditional)
Draft202012Validator(json.loads((HERE/"CONDITIONAL_POPULATION_SCHEMA_V3_PROPOSAL_001.json").read_text())).validate(partial)
put("ACTIVE_COMPANION_CONDITIONAL_PROJECTION_001.json",dict(kind="HAND_SOURCE_PROJECTIONS_WITH_ACTUAL068_ALTERNATIVE_ARITHMETIC",
    source_reader_executed=False,scientific_reconciliation_adopted=False,partial_calculation_inputs=masked,alternative_inputs=alternative_inputs,population=partial))
no_joint=cp(a)
for row in no_joint["joint_reading_assignments"]: row["admissibility"]=interp("unknown")
no_joint_population=cp(partial);no_joint_population.update(alternatives=[],conditional_cells=[])
Draft202012Validator(json.loads((HERE/"CONDITIONAL_POPULATION_SCHEMA_V3_PROPOSAL_001.json").read_text())).validate(no_joint_population)
put("ACTIVE_COMPANION_NO_JOINT_PROJECTION_001.json",dict(kind="HAND_SOURCE_PROJECTION_ACTUAL068_PARTIAL_ARITHMETIC",
    selection=no_joint,source_reader_executed=False,scientific_reconciliation_adopted=False,
    partial_calculation_inputs=masked,alternative_inputs=[],population=no_joint_population))
put("CONSTRUCTED_SOURCE_CASES_001.json",cases)
put("CONSTRUCTED_SOURCE_ROSTER_001.json",[
    dict(source_ref=k,representation="original",artifact_ref="artifact_"+h(v),sha256=h(v),
         content_utf8=v.decode() if k!=img else None,encoded_image_file="CONSTRUCTED_GRAPH_001.png" if k==img else None)
    for k,v in source_bytes.items() if k!=cov])
put("NUMERICAL_TABLE_001.json",[dict(name=c["name"],source_reader_executed=False,
    cells={k:c["actual_068_sheet"]["cells"][k] for k in ("condition1_controlled_response","condition0_controlled_response", "controlled_response_difference",
        "contrast_variance","contrast_standard_uncertainty","contrast_precision","source_profile_log_ratio","source_signed_index")},
    dependencies=c["actual_068_sheet"]["contrast_dependencies"]) for c in cases])
put("SOURCE_TO_INPUT_TRACE_001.json",[dict(name=c["name"],projection_kind="HAND_expected_source_projection_not_reader_execution",
    role_trace={r:dict(source_meaning_witnesses={k:c["selection"]["arms"][r][k]["canonical_witness"] for k in
        ("endpoint","normalization","subject_construct","condition","physical_observation")},
        selected_measurement=c["selection"]["arms"][r]["measurement"],
        source_covariance_binding=c["selection"]["covariance"]["bindings"][r],
        hand_calculation_operand=c["hand_calculation_inputs"]["arms"][r]) for r in roles},
    original_source_C=json.loads(c["source_covariance_text"]),provided_owner_covariance=c["hand_calculation_inputs"]["covariance"],
    actual_contrast_dependencies=c["actual_068_sheet"]["contrast_dependencies"]) for c in cases])
print(json.dumps(dict(constructed_cases=len(cases),selected_source_schemas_valid=True,actual068_outputs_valid=True,
                     new_reader_execution=False,native_execution=False,model_execution=False)))
