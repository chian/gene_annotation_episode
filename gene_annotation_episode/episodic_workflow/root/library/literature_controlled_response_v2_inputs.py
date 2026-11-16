"""Full source-bound A105 controlled-response extraction.

Text science is shared with v1. Actual signed graph reading is delegated to063;
owner covariance and actual068 parsed inputs retain source scope. No sheet,
model, acquisition, runtime action or annotation-credit calculation occurs here.
"""
from __future__ import annotations

from copy import deepcopy as cp
from fractions import Fraction
import errno
import hashlib
import json
import math
import re

from jsonschema import Draft202012Validator
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_inputs as shared
from gene_annotation_episode.episodic_workflow.root.library import literature_controlled_response_figure_inputs as graph_reader
from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_owner_contracts import controlled_response_owner_arguments_schema
from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_owner_calculations import validate_controlled_response_owner_inputs
from gene_annotation_episode.episodic_workflow.root.library.literature_experimental_contracts import ExperimentalContractError

from gene_annotation_episode.episodic_workflow.root.library.literature_controlled_response_v2_contracts import (
    obj, ref, null, T, N, I, B, SHA, arr, enum, embed, controlled_response_v2_arguments_schema, _graph_schema, _sheet_schema, _extraction_schema
)

def validate_controlled_response_v2_selection(arguments):
    selected = shared._validate_selection(arguments, controlled_response_v2_arguments_schema())
    for arm in selected["arms"].values():
        if arm and arm["measurement"] and arm["measurement"]["kind"] == "linear_bar":
            graph_reader._validate(_graph_request(selected, arm["measurement"]))
    return selected


def _graph_request(selected, measurement):
    return {"version": "controlled_response_rate_figure_selection_v1", "images": cp(selected["images"]), "measurement": cp(measurement)}


def _read_graph(context, selected):
    def cached(reference, representation):
        key = reference, representation
        context._active()
        if key not in context.cache:
            shared._fail("unselected_source_read", "source_ref")
        error = context.unavailable_errors.get(key)
        if error is not None:
            if isinstance(error, EOFError):
                raise OSError(errno.EIO, str(error)) from error
            raise error
        return context.read_source(reference, representation)
    result = graph_reader.read_controlled_response_rate_figure(_graph_request(context.arguments, selected), read_source=cached)
    return _graph_reading(context, selected, result)


def _graph_reading(context, selected, result):
    measurement = result["measurement"]
    return shared._StageValue(context, {"selection": selected, "extraction": measurement,
        "operand_projection": result["operand_projection"], "unit_semantics": {"kind": "graph", "record": measurement["unit"]},
        "exact_response": shared._exact_response(measurement, graph=True),
        "source_observation_id": measurement["source_observation_id"], "graph_details": result})


def read_controlled_response_v2_inputs(arguments, *, read_source):
    if not isinstance(arguments, dict) or arguments.get("version") != "controlled_response_source_selection_v2":
        validate_controlled_response_v2_selection(arguments)
    with shared.open_controlled_response_sources(arguments, read_source=read_source) as context:
        if context.profile != "v2":
            shared._fail("controlled_selection_schema_invalid", "arguments")
        arms = {}
        for role in shared.PRIMITIVE_ORDER:
            selected = context.arguments["arms"][role]
            if selected is None:
                arms[role] = None
                continue
            science = shared.read_controlled_response_arm_science(context, selected)
            nomination = selected["measurement"]
            measurement = (_read_graph(context, nomination) if nomination and nomination["kind"] == "linear_bar" else
                shared.read_controlled_response_text_measurement(context, nomination, endpoint=science["meanings"]["endpoint"]))
            arms[role] = shared.finish_controlled_response_arm(context, science, measurement=measurement)
        return shared.finish_controlled_response_inputs(context, arms=arms)


def validate_controlled_response_v2_extraction(arguments, extraction):
    def validate_measurement(selected, saved_measurement, *, source_records, image_records):
        if selected and selected["kind"] == "linear_bar":
            arms = extraction.get("arms", {})
            candidates = [arm for arm in arms.values() if arm is not None and arm["selection"]["measurement"] == selected and arm["measurement"] == saved_measurement]
            if not candidates or candidates[0]["graph_details"] is None or candidates[0]["graph_details"]["measurement"] != saved_measurement:
                shared._fail("saved_graph_measurement_mismatch", "measurement")
            sources = {(s["source_ref"],s["representation"]):s for s in source_records}
            return _validate_graph(selected, candidates[0]["graph_details"], sources=sources, images=image_records, request=arguments)
        return _validate_measurement(selected, saved_measurement, source_records=source_records, image_records=image_records)
    return shared.validate_controlled_response_saved_science(arguments, extraction, measurement_checks=validate_measurement)


__all__ = ["controlled_response_v2_arguments_schema", "validate_controlled_response_v2_selection",
    "read_controlled_response_v2_inputs", "validate_controlled_response_v2_extraction"]


def _saved_roster(selected, extraction):
    sources = {}
    artifacts = {}
    for source in extraction["sources"]:
        key = source["source_ref"], source["representation"]
        if key in sources:
            shared._fail("saved_duplicate_source", "sources")
        sources[key] = source
        if source["state"] == "available":
            if not source["artifact_ref"].strip() or not source["byte_sha256"]:
                shared._fail("saved_source_identity_mismatch", "sources")
            if source["artifact_ref"] in artifacts and artifacts[source["artifact_ref"]] != source["byte_sha256"]:
                shared._fail("artifact_content_conflict", "sources")
            artifacts[source["artifact_ref"]] = source["byte_sha256"]
        elif source["artifact_ref"] is not None or source["byte_sha256"] is not None:
            shared._fail("saved_source_state_mismatch", "sources")
    if list(sources) != shared._reference_closure(selected):
        shared._fail("saved_source_roster_mismatch", "sources")
    _saved_images(selected["images"], extraction["images"], sources)
    return sources


def _saved_images(nominated, images, sources):
    if len(images) != len(nominated):
        shared._fail("saved_image_roster_mismatch", "images")
    for spec,record in zip(nominated, images):
        if any(spec[k] != record[k] for k in ("image_id", "source_ref", "original_source_ref", "mapping")):
            shared._fail("saved_image_selection_mismatch", "images")
        for prefix, ref_key in (("", "source_ref"), ("original_", "original_source_ref")):
            source = sources[(spec[ref_key], "original")]
            # Original008 geometry may lose unavailable/decode-failed metadata;
            # independently retained graph records keep those bytes explicitly.
            if record[prefix+"artifact_ref"] is not None and (
                    record[prefix+"artifact_ref"] != source["artifact_ref"] or record[prefix+"byte_sha256"] != source["byte_sha256"]):
                shared._fail("saved_image_source_mismatch", "images")
        if not record["error"] and (not record["width"] or not record["height"] or record["frame_count"] != 1):
            shared._fail("saved_image_geometry_mismatch", "images")


def _check_witness(record, nominated, sources, images, field):
    shared._saved_witness(record, nominated, sources, field)
    if record is None or record["canonical_locator"] is None or record["selection"]["kind"] != "image":
        return
    selected = record["selection"]
    image = next(i for i in images if i["image_id"] == selected["image_id"])
    region = selected["region"]
    if image["error"] or not (0 <= region[0] < region[2] <= image["width"] and 0 <= region[1] < region[3] <= image["height"]):
        shared._fail("saved_image_geometry_mismatch", field)
    if image["mapping"]:
        original = image["mapping"]["original_region"]
        region = [region[0]+original[0], region[1]+original[1], region[2]+original[0], region[3]+original[1]]
    wanted = {"kind": "image", "original_source_ref": image["original_source_ref"],
        "original_artifact_ref": image["original_artifact_ref"], "original_byte_sha256": image["original_byte_sha256"], "region": region}
    if record["canonical_locator"] != wanted or record["artifact_ref"] != image["artifact_ref"] or record["byte_sha256"] != image["byte_sha256"]:
        shared._fail("saved_image_identity_mismatch", field)


def _validate_text(selected, measurement, sources, images):
    if measurement["selection"] != selected:
        shared._fail("saved_selection_mismatch", "measurement")
    if selected is None:
        expected = {"selection": None, "candidates": [], "fragments": [], "unit": None, "graph_witnesses": [],
            "reading_status": "not_selected", "source_observation_id": None,
            "canonical_display": shared._display(None, None), "pixel_result": None}
        if any(measurement[k] != v for k,v in expected.items()):
            shared._fail("saved_measurement_projection_mismatch", "measurement")
        return
    literal = selected["literal"]
    if len(measurement["candidates"]) != len(literal["candidates"]) or len(measurement["fragments"]) != len(literal["fragments"]):
        shared._fail("saved_selection_mismatch", "measurement")
    for record,nominated in zip(measurement["candidates"], literal["candidates"]):
        shared._saved_number(record, nominated, sources, "measurement.candidates")
    for record,nominated in zip(measurement["fragments"], literal["fragments"]):
        _check_witness(record, nominated, sources, images, "measurement.fragments")
    shared._saved_unit(measurement["unit"], selected["unit"], sources, "measurement.unit")
    state = literal["status"]
    if any(n["status"] == "dependency_unavailable" for n in measurement["candidates"]) or any(w["canonical_locator"] is None for w in measurement["fragments"]):
        state = "dependency_unavailable"
    elif state == "exact" and measurement["candidates"][0]["status"] != "parsed":
        state = "unsupported"
    locators = [n["source_locator"] for n in measurement["candidates"] if n["source_locator"] is not None]
    locators += [w["canonical_locator"] for w in measurement["fragments"] if w["canonical_locator"] is not None]
    reading_id = shared.identity("controlled_source_token", locators[0] if len(locators) == 1 else locators) if state != "dependency_unavailable" and locators else None
    if measurement["reading_status"] != state or measurement["source_observation_id"] != reading_id:
        shared._fail("saved_measurement_identity_mismatch", "measurement")
    number = measurement["candidates"][0] if state == "exact" else None
    expected_display = shared._display(number, measurement["unit"]) if state == "exact" else shared._display(None,None)
    if measurement["canonical_display"] != expected_display:
        shared._fail("saved_canonical_display_mismatch", "measurement")


def _validate_measurement(selected, saved_measurement, *, source_records, image_records):
    """Closed text check; graph checks additionally retain the complete063 result."""
    sources = {(s["source_ref"],s["representation"]):s for s in source_records}
    _validate_text(selected, saved_measurement, sources, image_records)
    return shared._reading_from_text(None, selected, saved_measurement)


def _validate_graph(selected, result, *, sources, images, request):
    Draft202012Validator(_graph_schema()).validate(result)
    if result["selection"] != _graph_request(request, selected) or result["version"] != "controlled_response_rate_figure_extraction_v1":
        shared._fail("saved_graph_selection_mismatch", "graph_details")
    closure = []
    for image in request["images"]:
        closure.extend([(image["source_ref"], "original"), (image["original_source_ref"], "original")])
    closure += [(w["source_ref"],w["representation"]) for w in graph_reader._witnesses(selected) if w["kind"] == "text"]
    closure = list(dict.fromkeys(closure))
    actual_closure = [(s["source_ref"],s["representation"]) for s in result["sources"]]
    if len(actual_closure) != len(set(actual_closure)) or set(actual_closure) != set(closure):
        shared._fail("saved_graph_source_roster_mismatch", "graph_details.sources")
    for source in result["sources"]:
        original = sources[(source["source_ref"], source["representation"])]
        if any(source[k] != original[k] for k in ("artifact_ref", "byte_sha256", "state")):
            shared._fail("saved_graph_source_identity_mismatch", "graph_details.sources")
    _saved_images(request["images"], result["images"], sources)
    actual_images = result["images"]
    for name,literal in result["axis_literals"].items():
        nominated = selected["axis"][name] if name == "unit" else selected["axis"][name]["tick"]
        if literal["selection"] != nominated:
            shared._fail("saved_graph_literal_selection_mismatch", "axis."+name)
        for part in ("candidates", "fragments"):
            if len(literal[part]) != len(nominated[part]):
                shared._fail("saved_graph_literal_selection_mismatch", "axis."+name)
            for saved,witness in zip(literal[part], nominated[part]):
                _check_witness(saved, witness, sources, actual_images, "axis."+name)
        available = all(w["canonical_locator"] is not None for part in ("candidates", "fragments") for w in literal[part])
        if literal["status"] == "parsed":
            if nominated["status"] != "exact" or not available or literal["raw_literal"] != nominated["candidates"][0]["quote"]:
                shared._fail("saved_graph_literal_mismatch", "axis."+name)
            witness = nominated["candidates"][0]
            qualification = "source_text_literal" if witness["kind"] == "text" else "episode_image_transcription"
            if literal["qualification"] != qualification:
                shared._fail("saved_graph_literal_mismatch", "axis."+name)
            if name != "unit":
                token = literal["raw_literal"].strip().replace("−", "-")
                if not graph_reader._LITERAL.fullmatch(literal["raw_literal"].strip()) or literal["exact_value"] != shared._rational(Fraction(token)):
                    shared._fail("saved_graph_tick_mismatch", "axis."+name)
        elif not available and literal["status"] != "dependency_unavailable" and nominated["status"] == "exact":
            shared._fail("saved_graph_literal_availability_mismatch", "axis."+name)
    scale = result["axis_scale"]
    if scale["selection"] != selected["axis"]["scale"] or len(scale["witnesses"]) != len(scale["selection"]["witnesses"]):
        shared._fail("saved_graph_scale_mismatch", "axis.scale")
    for saved,witness in zip(scale["witnesses"], scale["selection"]["witnesses"]):
        _check_witness(saved, witness, sources, actual_images, "axis.scale")
    if scale["support"] in ("literal_source_text", "episode_image_interpretation"):
        expected_support = "literal_source_text" if scale["selection"]["basis"] == "source_text_literal" else "episode_image_interpretation"
        if scale["support"] != expected_support:
            shared._fail("saved_graph_scale_mismatch", "axis.scale")
        if scale["selection"]["status"] != "known" or scale["effective_kind"] != scale["selection"]["kind"] or any(w["canonical_locator"] is None for w in scale["witnesses"]):
            shared._fail("saved_graph_scale_mismatch", "axis.scale")
        if scale["support"] == "literal_source_text" and any(graph_reader._SCALE_PHRASES.get(w["selection"]["quote"].strip().lower()) != scale["effective_kind"] for w in scale["witnesses"]):
            shared._fail("saved_graph_scale_literal_mismatch", "axis.scale")
    unit = result["measurement"]["unit"]
    literal = result["axis_literals"]["unit"]
    if unit["selection"] != selected["axis"]["unit"] or unit["raw_unit"] != literal["raw_literal"]:
        shared._fail("saved_graph_unit_mismatch", "axis.unit")
    if unit["status"] == "supported":
        parsed = shared._plain_unit(unit["raw_unit"])
        if parsed is None or parsed != (unit["canonical_unit"],shared._fraction(unit["exact_scale"])):
            shared._fail("saved_graph_unit_mismatch", "axis.unit")
        native = next((k for k in shared.RATE_UNITS if shared._plain_unit(k) == parsed), None)
        if native != unit["native_registry_unit"] or unit["witness"] != literal["candidates"][0]:
            shared._fail("saved_graph_unit_mismatch", "axis.unit")
    pixels = result["measurement"]["pixel_result"]
    spec = next(i for i in actual_images if i["image_id"] == selected["image_id"])
    if pixels["recipe"] != selected["bar_selection"] or pixels["terminal_edge"] != selected["terminal_edge"] or pixels["image_id"] != selected["image_id"]:
        shared._fail("saved_graph_recipe_mismatch", "pixels")
    if pixels["image_sha256"] != spec["byte_sha256"] or pixels["original_image_sha256"] != spec["original_byte_sha256"]:
        shared._fail("saved_graph_image_identity_mismatch", "pixels")
    recipe,edge = selected["bar_selection"],selected["terminal_edge"]
    roi = recipe["roi"]
    runs = pixels["qualifying_runs"]
    for i,run in enumerate(runs):
        if not roi["top"] <= run["top"] < run["bottom"] <= roi["bottom"] or run["bottom"]-run["top"] < recipe["minimum_run_rows"] or i and runs[i-1]["bottom"] >= run["top"]:
            shared._fail("saved_graph_runs_mismatch", "pixels.qualifying_runs")
    if pixels["mapped_roi"]:
        region = [roi[k] for k in ("left", "top", "right", "bottom")]
        if spec["mapping"]:
            ox,oy = spec["mapping"]["original_region"][:2]
            region = [region[0]+ox,region[1]+oy,region[2]+ox,region[3]+oy]
        wanted = {"kind":"image", "original_source_ref":spec["original_source_ref"], "original_artifact_ref":spec["original_artifact_ref"],
            "original_byte_sha256":spec["original_byte_sha256"], "region":region}
        if pixels["mapped_roi"] != wanted or pixels["image_size"] != {"width":spec["width"], "height":spec["height"]}:
            shared._fail("saved_graph_mapping_mismatch", "pixels")
    if pixels["pixel_edge"] is not None:
        if len(runs) != 1:
            shared._fail("saved_graph_edge_mismatch", "pixels")
        run = runs[0]
        clipped = run["top"] == roi["top"] if edge == "upper" else run["bottom"] == roi["bottom"]
        if clipped:
            shared._fail("saved_graph_terminal_clipping_mismatch", "pixels")
        tolerance = Fraction(recipe["edge_tolerance_pixels"])
        if edge == "upper":
            point,lo,hi = Fraction(run["top"])+Fraction(1,2), Fraction(run["top"])-tolerance, Fraction(run["top"]+1)+tolerance
        else:
            point,lo,hi = Fraction(run["bottom"])-Fraction(1,2), Fraction(run["bottom"]-1)-tolerance, Fraction(run["bottom"])+tolerance
        wanted = {"terminal_edge":edge, "nominal":shared._rational(point), "bounds":{"lower":shared._rational(lo),"upper":shared._rational(hi)}}
        if pixels["pixel_edge"] != wanted:
            shared._fail("saved_graph_edge_mismatch", "pixels")
    if pixels["status"] == "measured":
        if pixels["pixel_edge"] is None or scale["effective_kind"] != "linear" or scale["support"] not in ("literal_source_text", "episode_image_interpretation") or unit["status"] != "supported":
            shared._fail("saved_graph_calibration_mismatch", "pixels")
        p1,p2 = (Fraction(selected["axis"][k]["pixel"]) for k in ("first", "second"))
        v1,v2 = (shared._fraction(result["axis_literals"][k]["exact_value"]) for k in ("first", "second"))
        if p1 == p2 or v1 == v2 or not (0 <= lo <= hi < spec["height"]):
            shared._fail("saved_graph_calibration_mismatch", "pixels")
        slope = (v2-v1)/(p2-p1)
        axis = {"first_pixel":shared._rational(p1),"second_pixel":shared._rational(p2),
            "first_value":shared._rational(v1),"second_value":shared._rational(v2),"unit":unit["native_registry_unit"],"slope":shared._rational(slope)}
        ordinate = lambda p:v1+(p-p1)*slope
        lower,upper = sorted((ordinate(lo),ordinate(hi)))
        if pixels["axis"] != axis or pixels["native_ordinate"] != shared._rational(ordinate(point)) or pixels["native_bounds"] != {"lower":shared._rational(lower),"upper":shared._rational(upper)}:
            shared._fail("saved_graph_ordinate_mismatch", "pixels")
    measurement,projection = result["measurement"], result["operand_projection"]
    states = []
    if any(s["state"] == "unavailable" for s in result["sources"]) or any(w["authentication"] == "unavailable" for w in scale["witnesses"]):
        states.append("dependency_unavailable")
    states += [literal["status"] for literal in result["axis_literals"].values() if literal["status"] != "parsed"]
    if selected["axis"]["scale"]["status"] == "conflicting":
        states.append("conflicting")
    states.append("graph_digitized" if pixels["status"] == "measured" else pixels["status"])
    expected_status = next(status for status in ("dependency_unavailable","conflicting","ambiguous","unreadable","unsupported","graph_digitized") if status in states)
    if expected_status == "graph_digitized":
        try:
            graph_reader._finite_float(shared._fraction(pixels["native_ordinate"]))
            for side,direction in (("lower",-1),("upper",1)):
                graph_reader._outward(shared._fraction(pixels["native_bounds"][side]),direction)
        except OverflowError:
            expected_status = "unsupported"
    if measurement["reading_status"] != expected_status:
        shared._fail("saved_graph_status_mismatch", "measurement")
    expected_projection_status = "point" if expected_status == "graph_digitized" else "missing" if expected_status in ("dependency_unavailable","unreadable") else expected_status
    if projection["status"] != expected_projection_status or projection["approximate"] is not True or projection["unit"] != unit["native_registry_unit"]:
        shared._fail("saved_graph_projection_mismatch", "operand_projection")
    ordered_literals = [result["axis_literals"][name] for name in ("first","second","unit")]
    fragments = [w for literal in ordered_literals for w in literal["fragments"]]
    witnesses = [w for literal in ordered_literals for part in ("candidates", "fragments") for w in literal[part]] + scale["witnesses"]
    if measurement["selection"] != selected or measurement["fragments"] != fragments or measurement["graph_witnesses"] != witnesses or measurement["candidates"]:
        shared._fail("saved_graph_measurement_mismatch", "measurement")
    if projection["status"] == "point":
        if pixels["status"] != "measured" or measurement["reading_status"] != "graph_digitized":
            shared._fail("saved_graph_projection_mismatch", "measurement")
        native = shared._fraction(pixels["native_ordinate"])
        lower,upper = (shared._fraction(pixels["native_bounds"][s]) for s in ("lower","upper"))
        value = graph_reader._finite_float(native)
        interval = {"lower":min(graph_reader._outward(lower,-1),value), "upper":max(graph_reader._outward(upper,1),value)}
        expected = {"value":value,"threshold":None,"relation":"interval","approximate":True,"unit":unit["native_registry_unit"],"status":"point","origin":"graph_derived","digitization_interval":interval}
        if projection != expected:
            shared._fail("saved_graph_projection_mismatch", "operand_projection")
        identity_record = {"version":result["version"],"selection":result["selection"],"images":result["images"],
            "literals":result["axis_literals"],"scale":scale,"unit":unit,"pixels":pixels}
        expected_id = "controlled_response_graph_" + hashlib.sha256(json.dumps(identity_record,sort_keys=True,ensure_ascii=True,allow_nan=False).encode()).hexdigest()
        if measurement["source_observation_id"] != expected_id:
            shared._fail("saved_graph_identity_mismatch", "measurement.source_observation_id")
        display = {"value":None,"threshold":None,"unit":unit["canonical_unit"],"relation":"none","approximate":True,"diagnostics":[]}
        try:
            display["value"] = graph_reader._finite_float(native*shared._fraction(unit["exact_scale"]))
        except OverflowError:
            display["diagnostics"] = [graph_reader._diagnostic("graph_canonical_display_range","measurement.canonical_display")]
        else:
            display["relation"] = "eq"
        if measurement["canonical_display"] != display:
            shared._fail("saved_graph_display_mismatch", "measurement.canonical_display")
    elif any(projection[k] is not None for k in ("value","threshold","digitization_interval")) or projection["relation"] != "none" or measurement["source_observation_id"] is not None:
        shared._fail("saved_graph_projection_mismatch", "operand_projection")
    return _graph_reading(None, selected, result)
