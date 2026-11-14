"""Exact reported-point selectors for A108 context observations.

This finite reader identifies source numbers, never biological truth, operating
ranges, independent sampling or habitat exposure from a nominal culture setting.
"""
from copy import deepcopy
from fractions import Fraction
import html
import math
import re

from .domain import identity
from .literature_assay_inputs import _fail, _keys, _text
from .literature_partner_source_fields import read_source_number, _contexts

DATA_VERSION = "a108_source_context_selection_v1"
TRACE_VERSION = "a108_context_native_evidence_v1"
VALUE_BASES = ("source_reported_measurement", "source_reported_setting",
    "source_supported_inference", "conditional_assumption", "unresolved", "source_value_not_extracted")
_SETTINGS = ("question_kind", "origin", "scope_status", "frame_status", "pairing", "weight_basis",
    "sampling_design", "alpha", "permitted_remainder")
_OBS_FIELDS = ("requirement_key", "measurement_identity", "unit", "value", "value_basis", "basis_witness",
    "reported_sd", "reported_sem", "reported_plusminus", "reported_count", "count_relation", "replicate_kind")


def _choice(value, allowed, field):
    if not isinstance(value,str) or value not in allowed:
        _fail("unsupported_context_native_meaning",field)


def _witness(value, sources, field):
    return None if value is None else sources.witness(value,field)


def _unit(value, expected, sources, field):
    selected=sources.witness(value,field)
    raw=html.unescape(re.sub(r"</?[A-Za-z_][^<>]*>","",selected["quote"]))
    raw=re.sub(r"\s+","",raw).replace("µ","u").replace("μ","u")
    prefix,suffix=_contexts(sources,selected,0,len(selected["quote"]))
    if (prefix[-1:] and (prefix[-1:].isalpha() or prefix[-1:] in "_/µμ")) or (
            suffix[:1] and (suffix[:1].isalnum() or suffix[:1] in "/_^−-⁻%")):
        _fail("partial_context_native_unit",field)
    if re.match(r"\s*(?:/|\^|[-−⁻]\s*[0-9¹])",suffix):
        _fail("partial_context_native_unit",field)
    simple={"mM":("mM",1),"uM":("uM",1),"nm":("nm",1),"min":("minutes",1),"minutes":("minutes",1)}
    if raw in simple:
        canonical,multiplier=simple[raw]
        if canonical=="uM" and expected=="mM": canonical,multiplier="mM",Fraction(1,1000)
        elif canonical=="mM" and expected=="uM": canonical,multiplier="uM",1000
    elif raw in ("ppbv","ppb"):
        canonical,multiplier="ppbv_H2_gas",1
    elif raw in ("ppmv","ppm"):
        canonical,multiplier="ppmv_H2_gas",1
    elif raw in ("%","percent") and expected in ("percent_O2_gas","percent_O2_saturation_solution"):
        # Physical phase and chemical meaning are explicit source interpretations,
        # retained with each requirement/observation, never inferred from '%'.
        canonical,multiplier=expected,1
    else:
        _fail("unsupported_context_native_unit",field)
    if canonical!=expected:
        _fail("context_native_unit_mismatch",field)
    return {"witness":selected,"raw_unit":raw,"unit":canonical,"multiplier":float(multiplier)}


def _quantity(value, expected, sources, field, *, spread=False):
    if value is None:
        return None
    _keys(value,("number","unit_witness"),field)
    parsed=read_source_number(value["number"],sources=sources,role="spread" if spread else "rate")
    if parsed["relation"]!="point":
        _fail("context_native_exact_point_required",field)
    unit=_unit(value["unit_witness"],expected,sources,field+".unit_witness")
    selected=parsed["selector"]
    _,suffix=_contexts(sources,selected["witness"],selected["number_start"],selected["number_end"])
    visible=html.unescape(re.sub(r"</?[A-Za-z_][^<>]*>","",suffix)).replace("µ","u").replace("μ","u")
    printed=re.match(r"\s*(mM|uM|nm|minutes|min|ppbv|ppb|ppmv|ppm|percent|%)(?=$|[^A-Za-z])",visible)
    if printed is not None:
        tail=visible[printed.end():]
        if re.match(r"\s*(?:[/^]|[-−⁻]\s*[0-9¹])",tail):
            _fail("unsupported_explicit_context_native_unit",field)
        aliases={"min":"minutes","ppb":"ppbv","ppm":"ppmv","percent":"%"}
        actual=aliases.get(printed.group(1),printed.group(1));declared=aliases.get(unit["raw_unit"],unit["raw_unit"])
        if actual!=declared:
            _fail("context_native_explicit_unit_mismatch",field)
    exact=Fraction(parsed["raw_number"].replace("−","-"))*Fraction(str(unit["multiplier"]))
    try: converted=float(exact)
    except (OverflowError,ValueError): _fail("numerical_model_range",field)
    if not math.isfinite(converted) or converted==0 and exact!=0:
        _fail("numerical_model_range",field)
    return {"number":parsed,"unit":unit,"value":converted,"relation":"point"}


def _point(value):
    return None if value is None else {"lower":value,"upper":value,"lower_closed":True,"upper_closed":True}


def _key(kind,witness,fallback):
    return identity("context_native_"+kind,witness if witness is not None else fallback)


def _source_refs(value):
    result=[]
    def visit(item):
        if isinstance(item,dict):
            if "source_ref" in item and "artifact_ref" in item:
                result.append(item["source_ref"])
            for child in item.values():visit(child)
        elif isinstance(item,list):
            for child in item:visit(child)
    visit(value)
    return list(dict.fromkeys(result))


def native_direct_references(extraction,initial):
    trace=extraction.get("native_evidence")
    return list(dict.fromkeys([*initial,*(trace["source_refs"] if trace is not None else [])]))


def read_native_selection(data, *, sources, reference, artifact_ref):
    """Normalize one exact source recipe to the unchanged v2 numerical inputs.

    All native values/spreads/counts are selected in authorized source bytes.
    Equal-unit weight1 and alpha are declared method parameters, not readings.
    Only discrete tested-point domains are supported by this first route.
    """
    from .literature_context_inputs import _validate_inputs, NATIVE_UNITS
    _keys(data,("version","selection","meanings"),"native_data_source")
    if data["version"]!=DATA_VERSION:
        _fail("unsupported_context_native_version","native_data_source.version")
    selection=data["selection"]
    _keys(selection,(*_SETTINGS,"requirements","routes","contexts"),"native_selection")
    inputs={name:deepcopy(selection[name]) for name in _SETTINGS}
    if inputs["pairing"] not in ("paired","unknown"):
        _fail("context_native_unpaired_reader_unimplemented","native_selection.pairing")
    if inputs["weight_basis"]!="equal_units":
        _fail("context_native_weight_reader_unimplemented","native_selection.weight_basis")
    inputs.update(requirements=[],routes=deepcopy(selection["routes"]),contexts=[],marginals=[])
    req_trace=[]
    if not isinstance(selection["requirements"],list):_fail("array_required","native_selection.requirements")
    for i,req in enumerate(selection["requirements"]):
        path=f"native_selection.requirements[{i}]"
        _keys(req,("key","unit","supported","incompatible"),path)
        _choice(req["unit"],tuple(u for u in NATIVE_UNITS if u!="state"),path+".unit")
        core={"key":req["key"],"unit":req["unit"]}; evidence={"key":req["key"],"unit":req["unit"]}
        for name in ("supported","incompatible"):
            if not isinstance(req[name],list):_fail("array_required",path+"."+name)
            points=[_quantity(v,req["unit"],sources,f"{path}.{name}[{j}]") for j,v in enumerate(req[name])]
            if any(p is None for p in points):_fail("context_native_domain_point_required",path+"."+name)
            core[name]=[_point(p["value"]) for p in points];evidence[name]=points
        inputs["requirements"].append(core);req_trace.append(evidence)
    reqs={r["key"]:r for r in inputs["requirements"]}
    contexts=[]
    if not isinstance(selection["contexts"],list):_fail("array_required","native_selection.contexts")
    for i,context in enumerate(selection["contexts"]):
        path=f"native_selection.contexts[{i}]"
        _keys(context,("key","identity","setting","setting_kind","sample_unit","cluster","weight","scope_match","observations"),path)
        _choice(context["setting_kind"],("sample","environment","growth_condition","assay_condition","organism"),path+".setting_kind")
        witnesses={field:_witness(context[field],sources,path+"."+field) for field in ("identity","setting","sample_unit","cluster")}
        context_key=_key("context",witnesses["identity"],{"source_ref":reference,"artifact_ref":artifact_ref,"key":context["key"]})
        cluster_key=None if witnesses["cluster"] is None else _key("cluster",witnesses["cluster"],None)
        weight=context["weight"]
        if weight not in (None,"equal_unit"):
            _fail("context_native_equal_unit_weight_required",path+".weight")
        core={"key":context_key,"weight":None if weight is None else 1,"cluster_key":cluster_key,
            "scope_match":context["scope_match"],"observations":[]}
        trace={"key":context_key,"setting_kind":context["setting_kind"],**witnesses,"observations":[]}
        if not isinstance(context["observations"],list):_fail("array_required",path+".observations")
        for j,obs in enumerate(context["observations"]):
            opath=f"{path}.observations[{j}]";_keys(obs,_OBS_FIELDS,opath)
            if obs["requirement_key"] not in reqs:_fail("unknown_requirement_reference",opath+".requirement_key")
            _choice(obs["unit"],NATIVE_UNITS,opath+".unit")
            _choice(obs["value_basis"],VALUE_BASES,opath+".value_basis")
            reading=_quantity(obs["value"],obs["unit"],sources,opath+".value")
            if reading is not None and obs["value_basis"]=="source_value_not_extracted":
                _fail("context_native_unextracted_value_present",opath+".value_basis")
            physical=_witness(obs["measurement_identity"],sources,opath+".measurement_identity")
            basis=_witness(obs["basis_witness"],sources,opath+".basis_witness")
            fallback={"source_ref":reference,"artifact_ref":artifact_ref,"context_key":context_key,"requirement_key":obs["requirement_key"]}
            if reading is not None:
                number=reading["number"];w=number["selector"]["witness"]
                fallback={"source_ref":w["source_ref"],"artifact_ref":w["artifact_ref"],
                    "start":w["start"]+len(w["quote"][:number["selector"]["number_start"]].encode()),
                    "end":w["start"]+len(w["quote"][:number["selector"]["number_end"]].encode()),"unit":obs["unit"]}
            measurement_key=_key("measurement",physical,fallback)
            spreads={name:_quantity(obs[name],obs["unit"],sources,opath+"."+name,spread=True)
                for name in ("reported_sd","reported_sem","reported_plusminus")}
            count=None if obs["reported_count"] is None else read_source_number(obs["reported_count"],sources=sources,role="condition")
            if count is not None:
                exact=Fraction(count["raw_number"].replace("−","-"))
                if exact.denominator!=1 or exact<0:_fail("context_native_integer_count_required",opath+".reported_count")
                reported_count=int(exact)
            else:reported_count=None
            _choice(obs["count_relation"],("exact","unknown"),opath+".count_relation")
            if count is not None and obs["count_relation"]!="exact":
                _fail("context_native_exact_count_relation_required",opath+".count_relation")
            item={"requirement_key":obs["requirement_key"],"measurement_key":measurement_key,"unit":obs["unit"],
                "interval":_point(None if reading is None else reading["value"]),"relation":"numeric",
                **{name:None if value is None else value["value"] for name,value in spreads.items()},
                "reported_count":reported_count,"count_relation":obs["count_relation"],"replicate_kind":obs["replicate_kind"]}
            core["observations"].append(item)
            trace["observations"].append({"requirement_key":obs["requirement_key"],"measurement_key":measurement_key,
                "measurement_identity":physical,"value":reading,"value_basis":obs["value_basis"],"basis_witness":basis,
                **spreads,"reported_count":count})
        inputs["contexts"].append(core);contexts.append(trace)
    # Apply the exact established scientific numeric/roster validation before
    # returning any extraction. It supplies no new scoring gate.
    _validate_inputs(inputs)
    evidence={"version":TRACE_VERSION,"recipe":deepcopy(data),"requirements":req_trace,"contexts":contexts}
    evidence["source_refs"]=_source_refs({"requirements":req_trace,"contexts":contexts})
    normalized={"version":"a108_source_context_measurements_v2","inputs":inputs,"meanings":deepcopy(data["meanings"])}
    return normalized,evidence
