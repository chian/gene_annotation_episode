"""Constructed pixels and synthetic labels only; no paper or runtime coverage."""
from copy import deepcopy
import errno
from fractions import Fraction
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator
from PIL import Image
import pytest

from gene_annotation_episode import literature_controlled_response_figure_inputs as reader
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError

ROOT = Path(__file__).resolve().parents[1]
DECLARATIONS = ROOT / "verification/literature_reference_evidence_2026-10-25_001/a105_controlled_graph_design_061"
IMAGE_REF = "source_" + "a" * 24
TEXT_REF = "source_" + "b" * 24
CROP_REF = "source_" + "c" * 24
EXTRA_REF = "source_" + "d" * 24
SCHEMAS = {kind: Draft202012Validator(json.loads((DECLARATIONS / name).read_text())) for kind, name in (
    ("request", "GRAPH_REQUEST_SCHEMA_001.json"), ("result", "GRAPH_RESULT_SCHEMA_002.json"),
    ("count", "COUNT_RESULT_SCHEMA_002.json"))}


def encode(image, fmt="PNG", **kwargs):
    stream = BytesIO()
    image.save(stream, format=fmt, **kwargs)
    return stream.getvalue()


def raster(counts, width=10, *, low=(0, 0, 0), high=(255, 255, 255)):
    return b"".join(bytes(low) * n + bytes(high) * (width - n) for n in counts)


def count_recipe(width=10, height=4, **kwargs):
    return {"roi": {"left": 0, "top": 0, "right": width, "bottom": height},
        "rgb_min": [0, 0, 0], "rgb_max": [30, 30, 30],
        "minimum_row_fraction": 0.1, "minimum_run_rows": 1, **kwargs}


def count(data, width, height, selection):
    result = reader._count_bar_runs(rgb_bytes=data, width=width, height=height, selection=selection)
    SCHEMAS["count"].validate(result)
    return result


def fixture(*, runs=((60, 80),), ticks=("4", "0"), unit="µmol/min", mode="RGB", size=(30, 110)):
    image = Image.new(mode, size, (255, 255, 255, 255) if mode == "RGBA" else 255 if mode == "L" else "white")
    for top, bottom in runs:
        for y in range(top, bottom):
            for x in range(10, 20):
                image.putpixel((x, y), (0, 0, 0, 255) if mode == "RGBA" else 0 if mode == "L" else (0, 0, 0))
    labels = "<td>" + ticks[0] + "</td><td>" + ticks[1] + "</td><td>" + unit + "</td><td>linear axis</td>"
    raw = labels.encode()
    def text(quote):
        # Exact complete field, not a matching digit inside an earlier label.
        start = raw.index(b"<td>" + quote.encode() + b"</td>") + 4
        return {"kind": "text", "source_ref": TEXT_REF, "representation": "text",
                "start": start, "end": start + len(quote.encode()), "quote": quote}
    def literal(quote):
        return {"status": "exact", "candidates": [text(quote)], "fragments": []}
    arguments = {"version": "controlled_response_rate_figure_selection_v1", "images": [
        {"image_id": "panel", "source_ref": IMAGE_REF, "original_source_ref": IMAGE_REF, "mapping": None}],
        "measurement": {"kind": "linear_bar", "image_id": "panel", "terminal_edge": "lower",
            "bar_selection": {"roi": {"left": 10, "top": 5, "right": 20, "bottom": 105},
                "rgb_min": [0, 0, 0], "rgb_max": [30, 30, 30], "minimum_row_fraction": 0.5,
                "minimum_run_rows": 2, "edge_tolerance_pixels": 0.5},
            "axis": {"first": {"pixel": 20, "tick": literal(ticks[0])},
                "second": {"pixel": 60, "tick": literal(ticks[1])}, "unit": literal(unit),
                "scale": {"status": "known", "kind": "linear", "basis": "source_text_literal",
                    "witnesses": [text("linear axis")]}}}}
    sources = {(IMAGE_REF, "original"): {"artifact_ref": "artifact-original", "content": encode(image)},
               (TEXT_REF, "text"): {"artifact_ref": "artifact-labels", "content": raw}}
    image.close()
    return arguments, sources


def run(arguments, sources, callback=None):
    SCHEMAS["request"].validate(arguments)
    calls = []
    def read(ref, representation):
        calls.append((ref, representation))
        value = sources[(ref, representation)]
        if isinstance(value, Exception):
            raise value
        return value
    result = reader.read_controlled_response_rate_figure(arguments, read_source=callback or read)
    SCHEMAS["result"].validate(result)
    json.dumps(result, allow_nan=False)
    assert result["selection"] == arguments
    return result, calls


def codes(result):
    return {d["code"] for d in result["diagnostics"]}


def rat(value):
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def test_binary_fraction_threshold_and_single_row():
    result = count(raster([1, 0, 2, 2]), 10, 4, count_recipe())
    assert result["row_fraction_exact"] == {"numerator": "3602879701896397", "denominator": "36028797018963968"}
    assert result["qualifying_runs"] == [{"top": 2, "bottom": 4}]
    assert result["raster_rgb_sha256"] == sha256(raster([1, 0, 2, 2])).hexdigest()
    assert count(raster([10]), 10, 1, count_recipe(height=1))["qualifying_runs"] == [{"top": 0, "bottom": 1}]
    assert set(result) == {"version", "raster_rgb_sha256", "image_size", "selection", "row_fraction_exact", "qualifying_runs", "status"}


@pytest.mark.parametrize("fraction,counts,expected", [(0.5, [1, 2, 4], [{"top": 1, "bottom": 3}]), (1, [1, 2, 4], [{"top": 2, "bottom": 3}])])
def test_exact_equality(fraction, counts, expected):
    result = count(raster(counts, 4), 4, 3, count_recipe(width=4, height=3, minimum_row_fraction=fraction))
    assert result["qualifying_runs"] == expected


def test_inclusive_channels_and_roi_isolation():
    low, high = (10, 20, 30), (40, 50, 60)
    pixels = [low, high, (9, 20, 30), (10, 51, 30), (10, 20, 61)]
    data = bytes(sum(([0, 0, 0] for _ in range(5)), [])) + b"".join(bytes(p) for p in pixels) + bytes(low) * 5
    recipe = count_recipe(width=5, height=3, rgb_min=list(low), rgb_max=list(high), minimum_row_fraction=0.5)
    recipe["roi"] = {"left": 0, "top": 1, "right": 4, "bottom": 2}
    assert count(data, 5, 3, recipe)["qualifying_runs"] == [{"top": 1, "bottom": 2}]
    recipe["roi"]["right"] = 5
    assert count(data, 5, 3, recipe)["status"] == "no_run"


def test_maximal_runs_and_length_filter():
    data = raster([10, 0, 10, 10, 0, 10, 10, 10])
    result = count(data, 10, 8, count_recipe(height=8, minimum_run_rows=2))
    assert result["qualifying_runs"] == [{"top": 2, "bottom": 4}, {"top": 5, "bottom": 8}]
    assert result["status"] == "multiple_runs"


@pytest.mark.parametrize("changes,code", [
    ({"width": True}, "invalid_count_dimensions"), ({"height": 0}, "invalid_count_dimensions"),
    ({"rgb_bytes": bytearray(120)}, "immutable_rgb_bytes_required"),
    ({"rgb_bytes": bytes(121)}, "count_raster_length_mismatch"),
    ({"rgb_bytes": bytes(119)}, "count_raster_length_mismatch")])
def test_bad_raster(changes, code):
    kwargs = {"rgb_bytes": bytes(120), "width": 10, "height": 4, "selection": count_recipe(), **changes}
    with pytest.raises(ExperimentalContractError) as error:
        reader._count_bar_runs(**kwargs)
    assert error.value.code == code


@pytest.mark.parametrize("name,value", [("minimum_row_fraction", True), ("minimum_row_fraction", float("nan")),
    ("minimum_row_fraction", float("inf")), ("minimum_row_fraction", 0), ("minimum_row_fraction", 1.1),
    ("minimum_run_rows", True), ("minimum_run_rows", 0), ("rgb_min", [False, 0, 0]),
    ("rgb_max", [-1, 30, 30]), ("roi", {"left": 0, "top": 0, "right": 11, "bottom": 4})])
def test_bad_count_recipe(name, value):
    with pytest.raises(ExperimentalContractError):
        count(bytes(120), 10, 4, count_recipe(**{name: value}))


@pytest.mark.parametrize("extra", ["terminal_edge", "edge_tolerance_pixels", "calibration", "unit", "value"])
def test_counter_rejects_science_and_edge_fields(extra):
    with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
        count(bytes(120), 10, 4, count_recipe(**{extra: 1}))
    with pytest.raises(TypeError):
        reader._count_bar_runs(rgb_bytes=bytes(120), width=10, height=4, selection=count_recipe(), value=1)


@pytest.mark.parametrize("ticks,edge,run_rows,value,bounds", [
    (("4", "0"), "lower", ((60, 80),), Fraction(-39, 20), (Fraction(-41, 20), Fraction(-37, 20))),
    (("−4", "0"), "lower", ((60, 80),), Fraction(39, 20), (Fraction(37, 20), Fraction(41, 20))),
    (("4", "0"), "upper", ((20, 60),), Fraction(79, 20), (Fraction(77, 20), Fraction(81, 20))),
    (("−4", "0"), "upper", ((20, 60),), Fraction(-79, 20), (Fraction(-81, 20), Fraction(-77, 20)))])
def test_signed_exact_edges(ticks, edge, run_rows, value, bounds):
    arguments, sources = fixture(ticks=ticks, runs=run_rows)
    original = deepcopy(arguments)
    arguments["measurement"]["terminal_edge"] = edge
    result, calls = run(arguments, sources)
    pixels = result["measurement"]["pixel_result"]
    assert rat(pixels["native_ordinate"]) == value
    assert tuple(rat(pixels["native_bounds"][s]) for s in ("lower", "upper")) == bounds
    projection = result["operand_projection"]
    assert projection["value"] == float(value)
    assert Fraction(str(projection["digitization_interval"]["lower"])) <= bounds[0]
    assert Fraction(str(projection["digitization_interval"]["upper"])) >= bounds[1]
    assert calls == [(IMAGE_REF, "original"), (TEXT_REF, "text")]
    assert pixels["counter_module_sha256"] == sha256(Path(reader.__file__).read_bytes()).hexdigest()
    assert not any(k.startswith("core_") for k in pixels)
    assert result["measurement"]["source_observation_id"]
    assert original["measurement"]["bar_selection"] == arguments["measurement"]["bar_selection"]


@pytest.mark.parametrize("mode", ["L", "RGBA", "RGB"])
def test_accepted_native_modes(mode):
    arguments, sources = fixture(mode=mode)
    result, _ = run(arguments, sources)
    assert result["operand_projection"]["value"] == -1.95
    assert result["images"][0]["actual_mode"] == mode


@pytest.mark.parametrize("error", [ContractError("source_access_denied"), ExperimentalContractError("source_read_failed", "authorization"),
    PermissionError(errno.EACCES, "denied"), OSError(errno.EPERM, "denied"), RuntimeError("unexpected")])
def test_caller_denial_and_unexpected_errors_precede_helpers(monkeypatch, error):
    arguments, sources = fixture()
    # The late text dependency proves the entire closure precedes even image decode.
    def callback(ref, representation):
        if ref == TEXT_REF:
            raise error
        return sources[(ref, representation)]
    def forbidden(*args, **kwargs):
        pytest.fail("helper called before actual callback closure was authorized")
    monkeypatch.setattr(reader, "_strict_decode", forbidden)
    monkeypatch.setattr(reader, "_Inputs", forbidden)
    monkeypatch.setattr(reader, "_count_bar_runs", forbidden)
    with pytest.raises(type(error)) as raised:
        reader.read_controlled_response_rate_figure(arguments, read_source=callback)
    assert raised.value is error


@pytest.mark.parametrize("bad", [None, {}, {"artifact_ref": "x", "content": bytearray()},
    {"artifact_ref": "", "content": b""}, {"artifact_ref": "x", "content": b"", "extra": 1}])
def test_malformed_callback_precedes_helpers(monkeypatch, bad):
    arguments, _ = fixture()
    monkeypatch.setattr(reader, "_Inputs", lambda *a: pytest.fail("broad catch entered"))
    with pytest.raises(ExperimentalContractError):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *args: bad)


@pytest.mark.parametrize("error", [FileNotFoundError(errno.ENOENT, "missing"), OSError(errno.EIO, "read failed"), TimeoutError(errno.ETIMEDOUT, "timeout")])
def test_explicit_unavailable_image_keeps_labels_and_units(error):
    arguments, sources = fixture()
    sources[(IMAGE_REF, "original")] = error
    result, _ = run(arguments, sources)
    assert result["measurement"]["reading_status"] == "dependency_unavailable"
    assert result["axis_literals"]["first"]["exact_value"] == {"numerator": "4", "denominator": "1"}
    assert result["measurement"]["unit"]["native_registry_unit"] == "umol/min"
    assert result["operand_projection"]["status"] == "missing"
    assert result["measurement"]["source_observation_id"] is None


def test_unavailable_tick_keeps_pixels_other_tick_and_unit():
    arguments, sources = fixture()
    tick = arguments["measurement"]["axis"]["first"]["tick"]["candidates"][0]
    tick["source_ref"] = EXTRA_REF
    sources[(EXTRA_REF, "text")] = FileNotFoundError(errno.ENOENT, "missing")
    result, _ = run(arguments, sources)
    assert result["axis_literals"]["first"]["raw_literal"] is None
    assert result["axis_literals"]["first"]["candidates"][0]["authentication"] == "unavailable"
    assert result["axis_literals"]["second"]["exact_value"] == {"numerator": "0", "denominator": "1"}
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == [{"top": 60, "bottom": 80}]
    assert result["measurement"]["unit"]["status"] == "supported"


@pytest.mark.parametrize("change,code", [("quote", "source_quote_mismatch"), ("extent", "source_span_out_of_bounds"), ("utf8", "source_span_utf8_boundary_required")])
def test_text_authentication_errors_propagate(change, code):
    arguments, sources = fixture()
    witness = arguments["measurement"]["axis"]["unit"]["candidates"][0]
    if change == "quote":
        witness["quote"] = "nmol/min"
    elif change == "extent":
        witness["end"] = 10000
    else:
        witness["start"] += 1
    with pytest.raises(ExperimentalContractError) as error:
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    assert error.value.code == code


def crop_fixture(*, hidden_alpha=False, transparent_outside=False):
    arguments, sources = fixture(mode="RGBA")
    with Image.open(BytesIO(sources[(IMAGE_REF, "original")]["content"])) as source:
        original = source.copy()
    if hidden_alpha:
        original.putpixel((12, 65), (0, 0, 0, 0))
    if transparent_outside:
        original.putpixel((0, 0), (0, 0, 0, 0))
    with original.crop((5, 0, 25, 110)) as cropped:
        with cropped.convert("RGB") as rgb:
            cropped_bytes = encode(rgb)
    sources[(IMAGE_REF, "original")]["content"] = encode(original)
    sources[(CROP_REF, "original")] = {"artifact_ref": "artifact-crop", "content": cropped_bytes}
    original.close()
    arguments["images"][0].update(source_ref=CROP_REF, mapping={"original_region": [5, 0, 25, 110], "colour_conversion": "rgb"})
    arguments["measurement"]["bar_selection"]["roi"].update(left=5, right=15)
    return arguments, sources


def test_actual_crop_original_bytes_and_mapping():
    arguments, sources = crop_fixture()
    result, calls = run(arguments, sources)
    pixels = result["measurement"]["pixel_result"]
    assert pixels["image_sha256"] == sha256(sources[(CROP_REF, "original")]["content"]).hexdigest()
    assert pixels["original_image_sha256"] == sha256(sources[(IMAGE_REF, "original")]["content"]).hexdigest()
    assert pixels["mapped_roi"]["region"] == [10, 5, 20, 105]
    assert calls == [(CROP_REF, "original"), (IMAGE_REF, "original"), (TEXT_REF, "text")]
    assert result["operand_projection"]["value"] == -1.95


@pytest.mark.parametrize("hidden", [False, True])
def test_selected_and_original_roi_opacity_before_counter(monkeypatch, hidden):
    if hidden:
        arguments, sources = crop_fixture(hidden_alpha=True)
    else:
        arguments, sources = fixture(mode="RGBA")
        with Image.open(BytesIO(sources[(IMAGE_REF, "original")]["content"])) as image:
            frame = image.copy()
        frame.putpixel((12, 65), (0, 0, 0, 128))
        sources[(IMAGE_REF, "original")]["content"] = encode(frame)
        frame.close()
    monkeypatch.setattr(reader, "_count_bar_runs", lambda **kwargs: pytest.fail("nonopaque pixels counted"))
    result, _ = run(arguments, sources)
    assert "graph_nonopaque_roi" in codes(result)
    assert result["operand_projection"]["value"] is None
    assert result["images"][0]["byte_sha256"]


def test_nonopaque_pixels_outside_both_rois_do_not_block():
    arguments, sources = crop_fixture(transparent_outside=True)
    assert run(arguments, sources)[0]["operand_projection"]["value"] == -1.95


def test_wrong_crop_pixels_and_region_are_repairable():
    arguments, sources = crop_fixture()
    with Image.open(BytesIO(sources[(CROP_REF, "original")]["content"])) as image:
        frame = image.copy()
    frame.putpixel((0, 0), (1, 2, 3))
    sources[(CROP_REF, "original")]["content"] = encode(frame)
    frame.close()
    with pytest.raises(ExperimentalContractError, match="image_mapping_pixels_mismatch"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments["images"][0]["mapping"]["original_region"][2] = 300
    with pytest.raises(ExperimentalContractError, match="image_region_out_of_bounds"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])


@pytest.mark.parametrize("case", ["truncated_iend", "corrupt_idat", "orientation", "palette", "gif", "frames", "garbage"])
def test_strict_encoded_dependencies_are_scoped(case):
    arguments, sources = fixture()
    raw = sources[(IMAGE_REF, "original")]["content"]
    if case == "truncated_iend":
        raw = raw[:-1]
    elif case == "corrupt_idat":
        data = bytearray(raw)
        position = data.index(b"IDAT") + 5
        data[position] ^= 255
        raw = bytes(data)
    elif case == "orientation":
        with Image.open(BytesIO(raw)) as image:
            exif = Image.Exif(); exif[274] = 6
            raw = encode(image, exif=exif)
    elif case == "palette":
        with Image.new("P", (30, 110)) as image:
            raw = encode(image)
    elif case == "gif":
        with Image.new("RGB", (30, 110)) as image:
            raw = encode(image, "GIF")
    elif case == "frames":
        with Image.new("RGB", (30, 110), "white") as image, Image.new("RGB", (30, 110), "black") as second:
            raw = encode(image, save_all=True, append_images=[second])
    else:
        raw = b"not an image"
    sources[(IMAGE_REF, "original")]["content"] = raw
    result, _ = run(arguments, sources)
    assert "graph_image_unsupported" in codes(result)
    assert result["axis_literals"]["first"]["status"] == "parsed"
    assert result["images"][0]["byte_sha256"] == sha256(raw).hexdigest()


def test_original_orientation_cannot_be_hidden_by_crop():
    arguments, sources = crop_fixture()
    with Image.open(BytesIO(sources[(IMAGE_REF, "original")]["content"])) as image:
        exif = Image.Exif(); exif[274] = 6
        sources[(IMAGE_REF, "original")]["content"] = encode(image, exif=exif)
    result, _ = run(arguments, sources)
    assert result["images"][0]["error"]["code"] == "unsupported_image_orientation"
    assert result["images"][0]["original_byte_sha256"]
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == []


@pytest.mark.parametrize("rows,edge,expected", [(((60, 105),), "lower", "unreadable"),
    (((5, 80),), "lower", "graph_digitized"), (((5, 80),), "upper", "unreadable"),
    (((60, 105),), "upper", "graph_digitized"), ((), "lower", "unreadable"),
    (((30, 34), (60, 80)), "lower", "ambiguous")])
def test_clipping_and_run_cardinality(rows, edge, expected):
    arguments, sources = fixture(runs=rows)
    arguments["measurement"]["terminal_edge"] = edge
    result, _ = run(arguments, sources)
    assert result["measurement"]["reading_status"] == expected
    if expected == "graph_digitized":
        assert "graph_opposite_edge_clipped" in codes(result)
    else:
        assert result["operand_projection"]["value"] is None


def test_connected_stem_is_counted_without_scientific_object_inference():
    arguments, sources = fixture()
    with Image.open(BytesIO(sources[(IMAGE_REF, "original")]["content"])) as image:
        frame = image.copy()
    for y in range(40, 60):
        frame.putpixel((14, y), (0, 0, 0))
    sources[(IMAGE_REF, "original")]["content"] = encode(frame)
    frame.close()
    arguments["measurement"]["bar_selection"]["roi"].update(left=14, right=15)
    arguments["measurement"]["terminal_edge"] = "upper"
    result, _ = run(arguments, sources)
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == [{"top": 40, "bottom": 80}]
    assert result["operand_projection"]["value"] == 1.95
    assert "graph_conditional_digitization" in codes(result)


def test_thin_cap_filtered_only_by_selected_run_length():
    arguments, sources = fixture(runs=((30, 31), (60, 80)))
    result, _ = run(arguments, sources)
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == [{"top": 60, "bottom": 80}]


@pytest.mark.parametrize("kind", ["unknown", "conflicting", "logarithmic", "nonlinear"])
def test_scale_states_keep_pixels_and_labels(kind):
    arguments, sources = fixture()
    scale = arguments["measurement"]["axis"]["scale"]
    if kind in ("unknown", "conflicting"):
        scale.update(status=kind, kind=None, basis="unresolved")
        if kind == "conflicting":
            scale["witnesses"].append(arguments["measurement"]["axis"]["first"]["tick"]["candidates"][0])
    else:
        scale.update(kind=kind, basis="image_episode_interpretation", witnesses=[
            {"kind": "image", "image_id": "panel", "region": [0, 0, 5, 5], "quote": kind + " axis"}])
    result, _ = run(arguments, sources)
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == [{"top": 60, "bottom": 80}]
    assert result["measurement"]["pixel_result"]["axis"] is None
    assert result["operand_projection"]["value"] is None
    assert result["measurement"]["reading_status"] == ("conflicting" if kind == "conflicting" else "unsupported")


def test_image_quotations_are_attributed_and_map_to_original():
    arguments, sources = crop_fixture()
    axis = arguments["measurement"]["axis"]
    for n, quote, region in (("first", "4", [0, 18, 4, 22]), ("second", "0", [0, 58, 4, 62])):
        axis[n]["tick"]["candidates"] = [{"kind": "image", "image_id": "panel", "region": region, "quote": quote}]
    axis["scale"].update(basis="image_episode_interpretation", witnesses=[
        {"kind": "image", "image_id": "panel", "region": [0, 0, 5, 10], "quote": "linear layout interpreted"}])
    result, _ = run(arguments, sources)
    record = result["axis_literals"]["first"]
    assert record["qualification"] == "episode_image_transcription"
    assert record["candidates"][0]["attribution"] == "investigating_episode_interpretation"
    assert record["candidates"][0]["canonical_locator"]["region"] == [5, 18, 9, 22]
    assert result["operand_projection"]["value"] == -1.95
    assert "graph_image_label_interpretation" in codes(result)


@pytest.mark.parametrize("unit,native,scale", [("nmol/min", "nmol/min", Fraction(1, 1000)),
    ("mmol min−1", "mmol/min", Fraction(1000)), ("nM/min", "nM/min", Fraction(1, 1000)),
    ("µM min⁻¹", "uM/min", Fraction(1)), ("s^-1", "per_s", Fraction(60)),
    ("min−1", "per_min", Fraction(1)), ("nmol min−1 mg−1", "nmol/min/mg", Fraction(1, 1000)),
    ("µmol/min/mg", "umol/min/mg", Fraction(1))])
def test_native_unit_dimensions_and_exact_scales(unit, native, scale):
    arguments, sources = fixture(unit=unit)
    result, _ = run(arguments, sources)
    assert result["operand_projection"]["unit"] == native
    assert result["operand_projection"]["value"] == -1.95
    assert rat(result["measurement"]["unit"]["exact_scale"]) == scale
    assert result["measurement"]["canonical_display"]["value"] == float(Fraction(-39, 20) * scale)


@pytest.mark.parametrize("unit,code", [("U/mg", "graph_unit_defined_bridge_unselected"), ("%", "graph_unit_unsupported"),
    ("arbitrary signal", "graph_unit_unsupported"), ("×10³ µmol/min", "graph_axis_multiplier_unsupported")])
def test_unsupported_units_keep_native_ticks_pixels(unit, code):
    arguments, sources = fixture(unit=unit)
    result, _ = run(arguments, sources)
    assert code in codes(result)
    assert result["operand_projection"]["unit"] is None
    assert result["axis_literals"]["first"]["status"] == "parsed"
    assert result["measurement"]["pixel_result"]["qualifying_runs"]


def test_omitted_printed_multiplier_context_is_not_ignored():
    arguments, sources = fixture(unit="µmol/min ×10³")
    unit = arguments["measurement"]["axis"]["unit"]["candidates"][0]
    unit.update(quote="µmol/min", end=unit["start"] + len("µmol/min".encode()))
    result, _ = run(arguments, sources)
    assert "graph_axis_multiplier_unsupported" in codes(result)
    assert result["operand_projection"]["value"] is None


def test_partial_unit_is_repairable():
    arguments, sources = fixture(unit="µmol/min/mg")
    unit = arguments["measurement"]["axis"]["unit"]["candidates"][0]
    unit.update(quote="µmol/min", end=unit["start"] + len("µmol/min".encode()))
    with pytest.raises(ExperimentalContractError, match="partial_source_rate_unit"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])


@pytest.mark.parametrize("status", ["ambiguous", "conflicting", "unreadable"])
def test_all_literal_cardinalities_keep_nominations(status):
    arguments, sources = fixture()
    axis = arguments["measurement"]["axis"]
    first = axis["first"]["tick"]
    first["status"] = status
    if status == "unreadable":
        first["fragments"], first["candidates"] = first["candidates"], []
    else:
        first["candidates"].append(deepcopy(axis["second"]["tick"]["candidates"][0]))
    result, _ = run(arguments, sources)
    assert result["measurement"]["reading_status"] == status
    assert result["axis_literals"]["first"]["selection"] == first
    assert result["measurement"]["pixel_result"]["qualifying_runs"]


@pytest.mark.parametrize("token", ["~4", "4%", "1,000", "4–5", "4 ×10³", "4 umol/min", "Ⅳ"])
def test_complete_unsupported_tick_literals_are_partials(token):
    arguments, sources = fixture(ticks=(token, "0"))
    result, _ = run(arguments, sources)
    assert result["axis_literals"]["first"]["raw_literal"] == token
    assert result["axis_literals"]["first"]["exact_value"] is None
    assert "graph_tick_literal_unsupported" in codes(result)
    assert result["measurement"]["pixel_result"]["qualifying_runs"]


def test_native_range_failure_keeps_exact_pixels_and_canonical_failure_keeps_native():
    arguments, sources = fixture(ticks=("1e308", "0"), unit="mmol/min")
    result, _ = run(arguments, sources)
    assert result["operand_projection"]["status"] == "point"
    assert result["measurement"]["canonical_display"]["value"] is None
    assert "graph_canonical_display_range" in codes(result)
    arguments, sources = fixture(ticks=("1e308", "-1e308"))
    arguments["measurement"]["axis"]["first"]["pixel"] = 20
    arguments["measurement"]["axis"]["second"]["pixel"] = 21
    result, _ = run(arguments, sources)
    assert result["measurement"]["pixel_result"]["status"] == "measured"
    assert result["measurement"]["pixel_result"]["native_ordinate"]
    assert result["operand_projection"]["value"] is None
    assert "graph_numerical_model_range" in codes(result)


def test_nonzero_underflow_and_outward_decimal_semantics():
    arguments, sources = fixture(ticks=("1e-323", "0"))
    arguments["measurement"]["terminal_edge"] = "upper"
    result, _ = run(arguments, sources)
    assert result["operand_projection"]["value"] is None
    assert result["measurement"]["pixel_result"]["native_ordinate"]
    assert "graph_numerical_model_range" in codes(result)
    exact = Fraction(1, 10) + Fraction(1, 10**20)
    assert reader._outward(exact, -1) == 0.1
    assert reader._outward(exact, 1) == math.nextafter(0.1, math.inf)


@pytest.mark.parametrize("change", ["extra_root", "extra_tick_value", "bool_pixel", "nan_pixel", "infinite_tolerance",
    "unknown_image", "duplicate_image", "empty_box", "bad_cardinality", "scale_without_witness", "malformed_witness", "injected_calibration"])
def test_malformed_requests_reject_before_callback(change):
    arguments, _ = fixture()
    measurement = arguments["measurement"]
    if change == "extra_root": arguments["ordinate"] = 1
    elif change == "extra_tick_value": measurement["axis"]["first"]["value"] = 4
    elif change == "bool_pixel": measurement["axis"]["first"]["pixel"] = True
    elif change == "nan_pixel": measurement["axis"]["first"]["pixel"] = float("nan")
    elif change == "infinite_tolerance": measurement["bar_selection"]["edge_tolerance_pixels"] = math.inf
    elif change == "unknown_image": measurement["image_id"] = "missing"
    elif change == "duplicate_image": arguments["images"].append(deepcopy(arguments["images"][0]))
    elif change == "empty_box": measurement["bar_selection"]["roi"]["right"] = 10
    elif change == "bad_cardinality": measurement["axis"]["first"]["tick"]["candidates"] = []
    elif change == "scale_without_witness": measurement["axis"]["scale"]["witnesses"] = []
    elif change == "malformed_witness": measurement["axis"]["first"]["tick"]["candidates"] = [{"kind": "other"}]
    else: measurement["bar_selection"]["calibration"] = {}
    with pytest.raises(ExperimentalContractError):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *a: pytest.fail("callback reached"))


def test_degenerate_axis_and_outside_bounds_do_not_clamp():
    arguments, sources = fixture()
    arguments["measurement"]["axis"]["second"]["pixel"] = 20
    result, _ = run(arguments, sources)
    assert "graph_axis_degenerate" in codes(result)
    arguments["measurement"]["bar_selection"]["edge_tolerance_pixels"] = 100
    result, _ = run(arguments, sources)
    assert "graph_pixel_bounds_outside_image" in codes(result)
    assert result["measurement"]["pixel_result"]["pixel_edge"]
    assert result["operand_projection"]["value"] is None


def test_reading_identity_changes_with_actual_recipe_not_biological_independence():
    arguments, sources = fixture()
    first, _ = run(arguments, sources)
    arguments["measurement"]["bar_selection"]["minimum_row_fraction"] = 1
    second, _ = run(arguments, sources)
    assert first["operand_projection"] == second["operand_projection"]
    assert first["measurement"]["source_observation_id"] != second["measurement"]["source_observation_id"]


def test_full_declared_dependency_closure_authorized_before_decode(monkeypatch):
    arguments, sources = fixture()
    arguments["images"].append({"image_id": "unselected", "source_ref": EXTRA_REF,
                               "original_source_ref": EXTRA_REF, "mapping": None})
    denied = PermissionError(errno.EACCES, "unselected declared image denied")
    def read(ref, representation):
        if ref == EXTRA_REF:
            raise denied
        return sources[(ref, representation)]
    monkeypatch.setattr(reader, "_strict_decode", lambda *args: pytest.fail("closure not authorized"))
    with pytest.raises(PermissionError) as error:
        reader.read_controlled_response_rate_figure(arguments, read_source=read)
    assert error.value is denied


@pytest.mark.parametrize("piece", ["unit", "scale"])
def test_independent_unavailable_axis_dependency(piece):
    arguments, sources = fixture()
    axis = arguments["measurement"]["axis"]
    witness = axis["unit"]["candidates"][0] if piece == "unit" else axis["scale"]["witnesses"][0]
    witness["source_ref"] = EXTRA_REF
    sources[(EXTRA_REF, "text")] = OSError(errno.EIO, "unavailable")
    result, _ = run(arguments, sources)
    assert result["measurement"]["reading_status"] == "dependency_unavailable"
    assert result["axis_literals"]["first"]["status"] == "parsed"
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == [{"top": 60, "bottom": 80}]
    assert result["operand_projection"]["value"] is None


@pytest.mark.parametrize("prefix,suffix", [("not ", ""), ("not a ", ""), ("non", ""), ("", " is not used"), ("", "s")])
def test_scale_literal_context_does_not_promote_negation_or_partial_phrase(prefix, suffix):
    arguments, sources = fixture()
    before = sources[(TEXT_REF, "text")]["content"]
    sources[(TEXT_REF, "text")]["content"] = before.replace(b"linear axis", (prefix + "linear axis" + suffix).encode())
    witness = arguments["measurement"]["axis"]["scale"]["witnesses"][0]
    witness["start"] += len(prefix.encode())
    witness["end"] = witness["start"] + len(b"linear axis")
    result, _ = run(arguments, sources)
    assert "graph_scale_literal_unsupported" in codes(result)
    assert result["operand_projection"]["value"] is None
    assert result["measurement"]["pixel_result"]["qualifying_runs"]


def test_partial_numeric_tick_and_actual_geometry_reject():
    arguments, sources = fixture(ticks=("14", "0"))
    witness = arguments["measurement"]["axis"]["first"]["tick"]["candidates"][0]
    witness.update(start=witness["start"] + 1, quote="4")
    with pytest.raises(ExperimentalContractError, match="partial_source_numeric_token"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments, sources = fixture()
    arguments["measurement"]["axis"]["first"]["pixel"] = 110
    with pytest.raises(ExperimentalContractError, match="calibration_outside_image"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments["measurement"]["axis"]["first"]["pixel"] = 20
    arguments["measurement"]["bar_selection"]["roi"]["right"] = 31
    with pytest.raises(ExperimentalContractError, match="invalid_count_roi_bounds"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])


def test_image_label_region_and_scale_nomination_cardinalities():
    arguments, sources = fixture()
    arguments["measurement"]["axis"]["first"]["tick"]["candidates"] = [
        {"kind": "image", "image_id": "panel", "region": [0, 0, 31, 5], "quote": "4"}]
    with pytest.raises(ExperimentalContractError, match="image_region_out_of_bounds"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    for value in ("ambiguous", "conflicting"):
        arguments, sources = fixture()
        literal = arguments["measurement"]["axis"]["unit"]
        literal.update(status=value, candidates=literal["candidates"] * 2)
        with pytest.raises(ExperimentalContractError, match="distinct_transcription_candidates_required"):
            reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])
    arguments, sources = fixture()
    scale = arguments["measurement"]["axis"]["scale"]
    scale.update(status="conflicting", kind=None, basis="unresolved")
    with pytest.raises(ExperimentalContractError, match="distinct_scale_witnesses_required"):
        reader.read_controlled_response_rate_figure(arguments, read_source=lambda *key: sources[key])


def test_one_row_wrapper_counts_and_reports_clipped_terminal():
    arguments, sources = fixture(runs=((0, 1),), size=(30, 1))
    measurement = arguments["measurement"]
    measurement["bar_selection"]["roi"].update(top=0, bottom=1)
    measurement["bar_selection"]["minimum_run_rows"] = 1
    for name in ("first", "second"):
        measurement["axis"][name]["pixel"] = 0
    result, _ = run(arguments, sources)
    assert result["measurement"]["pixel_result"]["image_size"] == {"width": 30, "height": 1}
    assert result["measurement"]["pixel_result"]["qualifying_runs"] == [{"top": 0, "bottom": 1}]
    assert "graph_terminal_edge_clipped" in codes(result)


def test_accepted_jpeg_bytes_keep_original_hash_and_native_geometry():
    arguments, sources = fixture()
    with Image.open(BytesIO(sources[(IMAGE_REF, "original")]["content"])) as image:
        raw = encode(image, "JPEG", quality=100, subsampling=0)
    sources[(IMAGE_REF, "original")]["content"] = raw
    result, _ = run(arguments, sources)
    assert result["images"][0]["actual_format"] == "JPEG"
    assert result["measurement"]["pixel_result"]["image_sha256"] == sha256(raw).hexdigest()
    assert result["operand_projection"]["value"] == -1.95


def test_native_number_range_partial_and_image_exact_lexeme():
    arguments, sources = fixture(ticks=("1e500", "0"))
    result, _ = run(arguments, sources)
    assert "graph_tick_literal_numeric_range" in codes(result)
    assert result["axis_literals"]["first"]["raw_literal"] == "1e500"
    assert result["axis_literals"]["first"]["exact_value"] is None
    arguments["measurement"]["axis"]["first"]["tick"]["candidates"] = [
        {"kind": "image", "image_id": "panel", "region": [0, 18, 4, 22], "quote": "0.10000000000000000001"}]
    result, _ = run(arguments, sources)
    assert rat(result["axis_literals"]["first"]["exact_value"]) == Fraction("0.10000000000000000001")
    assert "graph_tick_projection_rounded" in codes(result)
    assert result["axis_literals"]["first"]["qualification"] == "episode_image_transcription"


@pytest.mark.parametrize("prefix,suffix", [("", " approximately"), ("", " or more"), ("", " or less"), ("LOD ", ""), ("about ", ""), ("", "%")])
def test_authenticated_tick_qualification_is_a_capability_partial(prefix, suffix):
    arguments, sources = fixture()
    raw = sources[(TEXT_REF, "text")]["content"]
    sources[(TEXT_REF, "text")]["content"] = raw.replace(b"<td>4</td>", ("<td>" + prefix + "4" + suffix + "</td>").encode())
    axis = arguments["measurement"]["axis"]
    first = axis["first"]["tick"]["candidates"][0]
    first["start"] += len(prefix.encode()); first["end"] = first["start"] + 1
    delta = len((prefix + suffix).encode())
    for witness in [axis["second"]["tick"]["candidates"][0], axis["unit"]["candidates"][0], axis["scale"]["witnesses"][0]]:
        witness["start"] += delta; witness["end"] += delta
    result, _ = run(arguments, sources)
    assert result["axis_literals"]["first"]["raw_literal"] == "4"
    assert result["axis_literals"]["first"]["exact_value"] is None
    assert "graph_tick_literal_unsupported" in codes(result)
    assert result["measurement"]["pixel_result"]["qualifying_runs"]
    assert result["operand_projection"]["value"] is None
