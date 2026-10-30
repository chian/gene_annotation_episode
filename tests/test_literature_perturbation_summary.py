"""Constructed v2 summaries; no paper, model service or live database reads."""
from copy import deepcopy
from fractions import Fraction
import io
import json
import math
from decimal import Decimal, localcontext

from PIL import Image, ImageDraw
import pytest

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_perturbation_inputs import LITERAL_FIELDS, read_perturbation_inputs
from gene_annotation_episode.literature_perturbation_summary import DATA_VERSION, ROLES, populate_summary_restoration, covariance_variance_enclosure
from gene_annotation_episode.literature_summary_figure_reader import read_summary_figure

SOURCE="source_"+"1"*24
DATA="source_"+"2"*24
IMAGE="source_"+"3"*24
TEXT=b"Constructed matched endpoint in reference, perturbed and restored arms; independent matched blocks. Means and SD, n=4."


def entry(value=None, *, sd=None, sem=None, n=None, independence="unknown", unit_kind="unknown", raw=None):
    return {"value":value,"measurement_id":None if value is None and raw is None else "measurement",
        "value_scale":"endpoint","summary_kind":"arithmetic_mean","summary_scale":"endpoint",
        "uncertainty":{"kind":"sd" if sd is not None else "sem" if sem is not None else "unreported",
            "value":sd if sd is not None else sem,"lower":None,"upper":None,"coverage":None,
            "scale":"endpoint","variance_status":"estimated"},
        "count":{"n":n,"unit_kind":unit_kind,"independence":independence},
        "raw_units":raw,"graph":None,"digitization":None,"meaning_witnesses":[]}


def source_data():
    measurements={role:entry() for role in ROLES}
    for role,value,sd in (("W",12,2),("K",3,1),("R",11,2)):
        measurements[role]=entry(value,sd=sd,n=4,independence="independent",unit_kind="culture")
        measurements[role]["measurement_id"]=role
    return {"version":DATA_VERSION,"endpoint_unit":"CFU_per_mL","exposure_unit":"molecules_per_cell",
        "origin":"synthetic","uncertainty_basis":"per_measurement","measurements":measurements,"covariances":[]}


def arguments():
    quote="matched endpoint"
    start=TEXT.index(quote.encode())
    witness={"source_ref":SOURCE,"representation":"original","start":start,"end":start+len(quote),"quote":quote}
    return {"source_ref":SOURCE,"data_source_ref":DATA,"source_kind":"synthetic_fixture",
        "literals":dict.fromkeys(LITERAL_FIELDS),"design":"selective_perturbation_restoration",
        "measurement_status":"validated_ratio_scale","same_endpoint_scope":"yes","amount_role":"unknown",
        "orientation":1,"interpretation_witnesses":[witness]}


def extract(data=None, images=None):
    data=source_data() if data is None else data
    bodies={SOURCE:TEXT, DATA:json.dumps(data,allow_nan=False).encode(), **(images or {})}
    calls=[]
    def read(ref,rep):
        calls.append((ref,rep))
        return {"artifact_ref":"artifact_"+ref.split("_")[1],"content":bodies[ref]}
    result=read_perturbation_inputs(arguments(),read_source=read)
    return result,calls


def calculate(data=None, images=None):
    result,_=extract(data,images)
    return populate_summary_restoration(result,origin="synthetic")


def covariance(a,b,kind="uncorrelated",value=None):
    return {"first":a,"second":b,"kind":kind,"value":value,"variance_status":"estimated","witnesses":[]}


def paired_data(*, independence="independent", unit_kind="preparation"):
    data=source_data()
    for role,values in (("W",[10,12,14]),("K",[2,3,4]),("R",[8,10,12])):
        raw=[{"unit_id":"block_"+str(i),"values":[v-1,v+1]} for i,v in enumerate(values)]
        data["measurements"][role]=entry(raw=raw,n=3,independence=independence,unit_kind=unit_kind)
        data["measurements"][role]["measurement_id"]=role
    data["covariances"]=[covariance(a,b,"paired_units") for a,b in (("W","K"),("W","R"),("K","R"))]
    return data


def test_reported_sd_and_unknown_covariance_keep_point_and_conditional_enclosure():
    out=calculate()["cells"]
    assert out["perturbation_difference"]["value"]==9
    assert out["W_mean_variance"]["value"]==1
    assert out["K_mean_variance"]["value"]==.25
    assert out["perturbation_mean_variance"]["value"] is None
    assert out["perturbation_mean_variance"]["variance_status"]=="unknown"
    assert out["perturbation_variance_lower"]["value"]==pytest.approx(.25)
    assert out["perturbation_variance_upper"]["value"]==pytest.approx(2.25)
    assert out["perturbation_variance_upper"]["bound_kind"]=="covariance_enclosure_not_confidence_interval"
    assert out["reference_restoration_index"]["value"] is None
    assert out["reference_index_lower"]["value"] is None


def test_reported_sem_is_not_divided_by_n_again_and_design_unknown_does_not_erase_it():
    data=source_data(); e=data["measurements"]["W"]
    e["uncertainty"].update(kind="sem",value=2)
    e["count"].update(n=None,independence="unknown",unit_kind="unknown")
    out=calculate(data)["cells"]
    assert out["W_mean_variance"]["value"]==4
    assert out["W_mean_se"]["value"]==2
    assert out["W_mean_variance"]["statistic_method"]=="reported_sem_squared"


def test_unknown_spread_scale_retains_number_without_claiming_physical_variance_unit():
    data=source_data(); e=data["measurements"]["W"]
    e["uncertainty"].update(kind="sem",value=2,scale="unknown")
    out=calculate(data)["cells"]
    assert out["W_reported_spread"]["value"]==2
    assert out["W_reported_spread"]["unit"]=="unreported"
    assert out["W_mean_variance"]["value"]==4
    assert out["W_mean_variance"]["unit"]=="unreported_squared"
    assert out["perturbation_variance_upper"]["value"] is None
    assert out["perturbation_difference"]["value"]==9


def test_explicit_covariance_and_shared_K_are_used_once():
    data=source_data()
    data["covariances"]=[covariance(a,b) for a,b in (("W","K"),("W","R"),("K","R"))]
    out=calculate(data)["cells"]
    assert out["perturbation_mean_variance"]["value"]==1.25
    assert out["restoration_mean_variance"]["value"]==1.25
    assert out["shared_contrast_covariance"]["value"]==.25


def test_paired_raw_units_use_block_means_and_sample_covariance_of_mean():
    out=calculate(paired_data())["cells"]
    for name,value in (("W_summary_value",12),("K_summary_value",3),("R_summary_value",10),
        ("W_sample_sd",2),("K_sample_sd",1),("W_reported_count",3),
        ("W_mean_variance",4/3),("perturbation_mean_variance",1/3),
        ("restoration_mean_variance",1/3),("shared_contrast_covariance",1/3)):
        assert out[name]["value"]==pytest.approx(value)
    assert out["W_mean_variance"]["variance_status"]=="estimated"


@pytest.mark.parametrize("independence,unit_kind",[("unknown","culture"),("not_independent","culture")])
def test_descriptive_raw_summary_survives_without_sampling_assumptions(independence,unit_kind):
    data=paired_data(independence=independence,unit_kind=unit_kind);data["covariances"]=[]
    out=calculate(data)["cells"]
    assert out["W_summary_value"]["value"]==12
    assert out["W_sample_sd"]["value"]==2
    assert out["W_reported_count"]["value"]==3
    assert out["W_mean_se"]["value"] is None
    assert out["W_mean_variance"]["value"] is None


def test_supported_technical_mean_precision_is_available_with_its_actual_scope():
    data=paired_data(unit_kind="technical_reading")
    out=calculate(data)["cells"]
    assert out["W_mean_variance"]["value"]==pytest.approx(4/3)
    assert out["W_mean_se"]["value"]==pytest.approx(math.sqrt(4/3))
    assert out["W_mean_variance"]["variance_scope"]=="technical_mean_within_studied_unit"
    assert out["perturbation_mean_variance"]["variance_scope"]=="technical_mean_within_studied_unit"
    assert out["W_reported_count"]["value"]==3


def test_mixed_technical_and_biological_estimator_scopes_are_not_relabelled():
    data=source_data();data["covariances"]=[covariance("W","K")]
    data["measurements"]["K"]["count"]["unit_kind"]="technical_reading"
    out=calculate(data)["cells"]
    assert out["perturbation_mean_variance"]["value"]==1.25
    assert out["perturbation_mean_variance"]["variance_scope"]=="mixed_estimator_scopes"


def test_reported_sem_does_not_create_independence_for_other_units():
    data=source_data();e=data["measurements"]["W"]
    e["uncertainty"].update(kind="sem",value=2)
    e["count"].update(unit_kind="other",independence="unknown")
    out=calculate(data)["cells"]
    assert out["W_mean_variance"]["value"]==4
    assert out["W_mean_variance"]["variance_scope"]=="other_unit_mean"


def test_missing_graph_ink_is_a_reader_limitation_not_claim_of_unreported_paper_value():
    data,images=graph_data()
    data["measurements"]["W"]["graph"]["selection"]["mean"]["rgb_min"]=[255,0,0]
    data["measurements"]["W"]["graph"]["selection"]["mean"]["rgb_max"]=[255,0,0]
    out=calculate(data,images)["cells"]
    assert out["W_summary_value"]["value"] is None
    assert out["W_summary_value"]["unavailable_reason"]=="no_bar_pixels"
    assert out["reference_endpoint"]["unavailable_reason"]=="no_bar_pixels"


@pytest.mark.parametrize("missing_W",[True,False])
def test_R_minus_K_and_its_variance_survive_unusable_W_restoration_denominator(missing_W):
    data=source_data()
    data["measurements"]["W"]["value"]=None if missing_W else 3
    data["covariances"]=[covariance("R","K")]
    out=calculate(data)["cells"]
    assert out["restoration_fraction_raw"]["value"] is None
    assert out["restoration_difference"]["value"]==8
    assert out["restoration_mean_variance"]["value"]==1.25


def test_full_covariance_psd_detects_inconsistent_three_arm_covariance():
    data=source_data()
    for e in data["measurements"].values():
        if e["value"] is not None:e["uncertainty"].update(kind="sem",value=1)
    data["covariances"]=[covariance("W","K","mean_covariance",.9),
                         covariance("W","R","mean_covariance",.9),
                         covariance("K","R","mean_covariance",-.9)]
    with pytest.raises(ExperimentalContractError,match="not_psd"):
        calculate(data)


@pytest.mark.parametrize("kind",["confidence_interval","detection_limit","untyped_pm"])
def test_nonvariance_uncertainty_keeps_reported_numbers_and_mean_point(kind):
    data=source_data();e=data["measurements"]["W"]
    e["uncertainty"].update(kind=kind,value=.4 if kind=="untyped_pm" else None,
        lower=None if kind=="untyped_pm" else 10,upper=None if kind=="untyped_pm" else 14,
        coverage=.95 if kind=="confidence_interval" else None)
    out=calculate(data)["cells"]
    assert out["W_summary_value"]["value"]==12
    assert out["W_mean_variance"]["value"] is None
    assert out["W_reported_spread"]["lower"]==(None if kind=="untyped_pm" else 10)


@pytest.mark.parametrize("mutation",[
    lambda d:d["measurements"]["W"]["count"].update(n=True),
    lambda d:d["measurements"]["W"]["count"].update(n=0),
    lambda d:d["measurements"]["W"]["uncertainty"].update(value=-1),
    lambda d:d["measurements"]["W"].update(extra=1),
    lambda d:d["measurements"]["W"].update(summary_scale="guess"),
    lambda d:d["measurements"]["W"].update(meaning_witnesses=[{"invented":"quote"}]),
    lambda d:d["covariances"].extend([covariance("W","K"),covariance("K","W")]),
])
def test_invalid_summary_inputs_do_not_become_observations(mutation):
    data=source_data();mutation(data)
    with pytest.raises((ExperimentalContractError,ContractError)):
        calculate(data)


def figure_fixture(*,lower=False):
    im=Image.new("RGB",(100,500),"white");draw=ImageDraw.Draw(im)
    draw.rectangle((10,200,39,349),fill="black")
    draw.line((55,170,84,170),fill="black",width=1)
    if lower:draw.line((55,230,84,230),fill="black",width=1)
    buf=io.BytesIO();im.save(buf,format="PNG");im.close()
    def feature(left,top,right,bottom,kind):
        return {"kind":kind,"roi":{"left":left,"top":top,"right":right,"bottom":bottom},
            "rgb_min":[0,0,0],"rgb_max":[30,30,30],"minimum_row_fraction":.8,
            "minimum_run_rows":1,"edge_tolerance_pixels":.5}
    selection={"calibration":{"scale":"log10","first":{"pixel":400.5,"value":1},
        "second":{"pixel":100.5,"value":1000},"unit":"CFU_per_mL"},
        "mean":feature(10,190,40,350,"top_edge"),"upper_error":feature(55,165,85,176,"run_center"),
        "lower_error":feature(55,225,85,236,"run_center") if lower else None}
    return buf.getvalue(),selection


def graph_data(*,scale="endpoint",lower=False,kind="sd"):
    data=source_data();raw,selection=figure_fixture(lower=lower)
    e=data["measurements"]["W"]
    e["value"]=None;e["graph"]={"source_ref":IMAGE,"selection":selection}
    e["uncertainty"].update(kind=kind,value=None,scale=scale,coverage=.95 if kind=="confidence_interval" else None)
    return data,{IMAGE:raw}


def test_log_display_reader_extracts_native_point_and_preserves_statistical_scale_choice():
    data,images=graph_data()
    result,calls=extract(data,images)
    assert calls.count((IMAGE,"original"))==1
    assert result["values"]["W"]==pytest.approx(100)
    out=populate_summary_restoration(result,origin="graph_derived")["cells"]
    assert out["W_reported_spread"]["value"]==pytest.approx(10**2.3-100)
    assert out["W_reported_spread"]["bound_kind"]=="conditional_digitization_not_confidence_interval"
    data,images=graph_data(scale="log10_endpoint")
    out=calculate(data,images)["cells"]
    assert out["W_summary_value"]["value"]==pytest.approx(100)
    assert out["W_reported_spread"]["value"]==pytest.approx(.3)
    assert out["W_reported_spread"]["unit"]=="log10_CFU_per_mL"
    assert out["W_mean_variance"]["value"] is None


def test_two_caps_keep_asymmetry_instead_of_dropping_selected_numbers():
    data,images=graph_data(lower=True)
    out=calculate(data,images)["cells"]["W_reported_spread"]
    assert out["value"] is None
    assert out["lower_error_cap"]==pytest.approx(10**1.7)
    assert out["upper_error_cap"]==pytest.approx(10**2.3)
    assert out["lower"]<50<out["upper"]
    assert out["spread_reading"]=="asymmetric_readings"
    data,images=graph_data(lower=True,scale="log10_endpoint")
    out=calculate(data,images)["cells"]["W_reported_spread"]
    assert out["value"]==pytest.approx(.3)
    assert out["spread_reading"]=="symmetric_compatible"


def test_graph_CI_is_transformed_to_its_declared_statistical_scale():
    data,images=graph_data(lower=True,scale="log10_endpoint",kind="confidence_interval")
    out=calculate(data,images)["cells"]["W_reported_spread"]
    assert out["lower"]==pytest.approx(1.7)
    assert out["upper"]==pytest.approx(2.3)
    assert out["unit"]=="log10_CFU_per_mL"
    assert out["bound_kind"]=="reported_confidence_interval"


@pytest.mark.parametrize("mutation",[
    lambda s:s["calibration"]["first"].update(value=0),
    lambda s:s["calibration"]["first"].update(value=10**400),
    lambda s:s["calibration"]["first"].update(pixel=True),
    lambda s:s["mean"]["roi"].update(right=101),
    lambda s:s.update(extra=True),
])
def test_figure_invalid_selections_have_structured_failure(mutation):
    raw,selection=figure_fixture();mutation(selection)
    with pytest.raises(ContractError):read_summary_figure(raw,selection)


def test_cap_clipping_is_unknown_while_mean_fill_may_end_at_roi_bottom():
    raw,selection=figure_fixture()
    selection["upper_error"]["roi"]["bottom"]=171
    result=read_summary_figure(raw,selection)
    assert result["features"]["mean"]["value"]==pytest.approx(100)
    assert result["features"]["upper_error"]["value"] is None
    assert result["features"]["upper_error"]["unavailable_reason"]=="truncated_error_cap"


def test_graph_wrong_upper_cap_is_rejected_without_reinterpreting_it():
    data,images=graph_data(lower=True)
    data["measurements"]["W"]["graph"]["selection"]["upper_error"]=deepcopy(data["measurements"]["W"]["graph"]["selection"]["lower_error"])
    with pytest.raises(ExperimentalContractError,match="error_cap_direction_mismatch"):
        calculate(data,images)


@pytest.mark.parametrize("first,second",[(1e300,1e308),(1e-300,1e-308)])
def test_log_extrapolation_range_failure_does_not_manufacture_finite_or_zero_value(first,second):
    raw,selection=figure_fixture()
    selection["calibration"].update(first={"pixel":350,"value":first},second={"pixel":300,"value":second})
    out=read_summary_figure(raw,selection)["features"]["mean"]
    assert out["value"] is None
    assert out["status"]=="unavailable"
    assert out["unavailable_reason"]=="numerical_model_range"


def test_log_axis_reversed_direction_uses_supplied_tick_calibration():
    raw,selection=figure_fixture();selection["upper_error"]=None
    selection["calibration"].update(first={"pixel":100.5,"value":1},second={"pixel":400.5,"value":1000})
    out=read_summary_figure(raw,selection)["features"]["mean"]
    assert out["value"]==pytest.approx(10)
    assert out["lower"]<10<out["upper"]


@pytest.mark.parametrize("first,second",[
    (Fraction(1,10**95-19),Fraction(1,10**95-18)),
    (Fraction(1),Fraction(1,4)),(Fraction(1),Fraction(2)),
    (Fraction(0),Fraction(0)),(Fraction(0),Fraction(3)),
    (Fraction(10**300),Fraction(10**300)),
    (Fraction(1,10**300),Fraction(1,2*10**300)),
    (Fraction(1,10**1000),Fraction(1,2*10**1000)),
])
def test_covariance_variance_enclosure_contains_high_precision_extrema(first,second):
    lower,upper=covariance_variance_enclosure(first,second)
    with localcontext() as context:
        context.prec=600
        a=Decimal(first.numerator)/Decimal(first.denominator)
        b=Decimal(second.numerator)/Decimal(second.denominator)
        actual_lower=(a.sqrt()-b.sqrt())**2
        actual_upper=(a.sqrt()+b.sqrt())**2
        assert lower is not None and Decimal.from_float(lower)<=actual_lower
        assert upper is not None and Decimal.from_float(upper)>=actual_upper
    if first==second:assert lower==0


def test_covariance_bound_overflow_keeps_finite_lower_without_fabricating_upper():
    lower,upper=covariance_variance_enclosure(Fraction(10**1000),Fraction(0))
    assert lower==math.nextafter(math.inf,0.)
    assert upper is None


def test_large_reported_counts_use_sound_enclosure_through_actual_source_reader():
    data=source_data();n=10**95-19
    data["measurements"]["W"]["uncertainty"].update(value=1)
    data["measurements"]["K"]["uncertainty"].update(value=1)
    data["measurements"]["W"]["count"].update(n=n)
    data["measurements"]["K"]["count"].update(n=n+1)
    out=calculate(data)["cells"]
    with localcontext() as context:
        context.prec=600
        expected=(Decimal(1)/Decimal(n)).sqrt()-(Decimal(1)/Decimal(n+1)).sqrt()
        assert Decimal.from_float(out["perturbation_variance_lower"]["value"])<=expected**2
