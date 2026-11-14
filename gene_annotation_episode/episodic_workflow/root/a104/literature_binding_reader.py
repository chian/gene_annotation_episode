"""Parse retained binding-parameter tokens without interpreting an experiment.

The caller supplies a selected, already acquired JSON table. This finite reader
validates that representation and preserves every matching source location; it
does not acquire sources, interpret image pixels, identify biological subjects,
infer a statistical model, calculate contrasts or populate evidence scores.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .literature_experimental_contracts import ExperimentalContractError


VERSION = "binding_parameter_extraction_v1"
TABLE_VERSION = "binding_parameter_table_v1"
_KINDS = ("ic50", "reported_hill_kd")
_REPRESENTATIONS = ("retained_visual_transcription", "primary_table", "synthetic_fixture")
_BASES = ("fit_to_averaged_curve", "between_independent_fitted_parameters", "unknown")
_SCALES = {"nM": 1.0, "uM": 1000.0, "µM": 1000.0, "μM": 1000.0, "mM": 1000000.0}
_DECIMAL = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
_EXPRESSION = re.compile(
    rf"\s*(?P<relation>>=|<=|>|<|≥|≤)?\s*(?P<value>{_DECIMAL})"
    rf"(?:\s*±\s*(?P<spread>{_DECIMAL}))?\s*"
)
_RELATIONS = {None: "eq", ">": "gt", ">=": "ge", "≥": "ge", "<": "lt", "<=": "le", "≤": "le"}
_ORIGINS = {"retained_visual_transcription": "visual_transcription",
            "primary_table": "reported", "synthetic_fixture": "synthetic"}


def _fail(code, field):
    raise ExperimentalContractError(code, field)


def _keys(value, names, field):
    if not isinstance(value, dict) or set(value) != set(names):
        _fail("closed_fields_required", field)


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        _fail("nonempty_source_token_required", field)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("duplicate_json_key", "source.text")
        result[key] = value
    return result


def _json_constant(_token):
    _fail("nonfinite_json_constant", "source.text")


def _number(token, scale, field, *, spread=False):
    value = float(token)
    if not math.isfinite(value):
        _fail("finite_number_required", field)
    # A mathematically nonzero decimal cannot silently become float zero.
    mantissa = token.lower().split("e", 1)[0]
    if value == 0 and any(character in "123456789" for character in mantissa):
        _fail("numerical_model_range", field)
    if spread:
        if value < 0:
            _fail("nonnegative_reported_spread_required", field)
    elif value <= 0:
        _fail("positive_binding_parameter_required", field)
    normalized = value * scale
    if not math.isfinite(normalized) or normalized == 0 and value != 0:
        _fail("numerical_model_range", field)
    return normalized


def _measurement(expression, scale, field):
    _text(expression, field)
    if expression.strip() == "n.d.":
        return None, "unreported", None
    match = _EXPRESSION.fullmatch(expression)
    if match is None:
        _fail("invalid_binding_parameter_token", field)
    relation = _RELATIONS[match["relation"]]
    if relation != "eq" and match["spread"] is not None:
        _fail("censored_parameter_has_spread", field)
    value = _number(match["value"], scale, field)
    spread = (_number(match["spread"], scale, field + ".spread", spread=True)
              if match["spread"] is not None else None)
    return value, relation, spread


def _locator(value, representation, field):
    if representation != "retained_visual_transcription":
        _keys(value, ("row_index", "column"), field)
        if type(value["row_index"]) is not int or value["row_index"] < 0:
            _fail("nonnegative_row_index_required", field + ".row_index")
        _text(value["column"], field + ".column")
        return
    _keys(value, ("original_source_ref", "original_artifact_ref", "image_region"), field)
    for name in ("original_source_ref", "original_artifact_ref"):
        _text(value[name], field + "." + name)
    box = value["image_region"]
    if (not isinstance(box, list) or len(box) != 4
            or any(type(coordinate) is not int or coordinate < 0 for coordinate in box)
            or box[2] <= box[0] or box[3] <= box[1]):
        _fail("positive_integer_image_region_required", field + ".image_region")


def read_binding_parameter_table(source, *, expected_subject, expected_state,
                                 expected_experiment, reference_ligand,
                                 test_ligand, parameter_kind):
    """Read exact subject/state/experiment/ligand matches into canonical nM.

    The table and every row must be well formed, including unselected rows.
    Selection uses literal labels without alias inference. A mismatched table
    parameter kind is an error; absent requested labels leave an empty arm.
    ``source.row_index`` is the zero-based position in the supplied JSON rows;
    ``source.locator`` retains the original table or image location separately.
    Minimum experiment count and reported uncertainty basis are retained without
    upgrading either to independent preparations, exact n, SD or SEM.
    """
    _keys(source, ("source_ref", "artifact_ref", "text", "representation"), "source")
    for name in ("source_ref", "artifact_ref", "text"):
        _text(source[name], "source." + name)
    representation = source["representation"]
    if representation not in _REPRESENTATIONS:
        _fail("unknown_source_representation", "source.representation")
    for name, value in (("expected_subject", expected_subject), ("expected_state", expected_state),
                        ("expected_experiment", expected_experiment),
                        ("reference_ligand", reference_ligand), ("test_ligand", test_ligand)):
        _text(value, name)
    if parameter_kind not in _KINDS:
        _fail("unsupported_binding_parameter_kind", "parameter_kind")
    try:
        table = json.loads(source["text"], object_pairs_hook=_json_object,
                           parse_constant=_json_constant)
    except ExperimentalContractError:
        raise
    except (ValueError, RecursionError) as error:
        raise ExperimentalContractError("malformed_binding_parameter_table", "source.text") from error
    _keys(table, ("version", "table_id", "parameter_kind", "unit", "uncertainty_basis",
                  "minimum_experiment_count", "rows"), "table")
    if table["version"] != TABLE_VERSION:
        _fail("unsupported_binding_table_version", "table.version")
    _text(table["table_id"], "table.table_id")
    if table["parameter_kind"] not in _KINDS:
        _fail("unsupported_binding_parameter_kind", "table.parameter_kind")
    if table["parameter_kind"] != parameter_kind:
        _fail("binding_parameter_kind_mismatch", "table.parameter_kind")
    if not isinstance(table["unit"], str) or table["unit"] not in _SCALES:
        _fail("unsupported_concentration_unit", "table.unit")
    if table["uncertainty_basis"] not in _BASES:
        _fail("unsupported_binding_uncertainty_basis", "table.uncertainty_basis")
    count = table["minimum_experiment_count"]
    if count is not None and (type(count) is not int or count < 1):
        _fail("positive_integer_count_required", "table.minimum_experiment_count")
    if not isinstance(table["rows"], list):
        _fail("rows_required", "table.rows")
    reference_rows, test_rows = [], []
    for index, row in enumerate(table["rows"]):
        path = f"table.rows[{index}]"
        _keys(row, ("subject", "state", "experiment", "ligand", "expression", "locator"), path)
        for name in ("subject", "state", "experiment", "ligand"):
            _text(row[name], path + "." + name)
        value, relation, spread = _measurement(row["expression"], _SCALES[table["unit"]],
                                                path + ".expression")
        _locator(row["locator"], representation, path + ".locator")
        if (row["subject"], row["state"], row["experiment"]) != (
                expected_subject, expected_state, expected_experiment):
            continue
        normalized = {
            "value": value, "relation": relation, "reported_spread": spread,
            "origin": _ORIGINS[representation],
            "source": {"source_ref": source["source_ref"], "artifact_ref": source["artifact_ref"],
                       "representation": representation, "table_id": table["table_id"],
                       "row_index": index, "locator": deepcopy(row["locator"]),
                       "expression": row["expression"]},
            **{name: row[name] for name in ("subject", "state", "experiment", "ligand")},
        }
        if row["ligand"] == reference_ligand:
            reference_rows.append(deepcopy(normalized))
        if row["ligand"] == test_ligand:
            test_rows.append(deepcopy(normalized))
    return {"version": VERSION, "parameter_kind": parameter_kind, "unit": "nM",
            "uncertainty_basis": table["uncertainty_basis"], "minimum_experiment_count": count,
            "reference_rows": reference_rows, "test_rows": test_rows}


__all__ = ["VERSION", "TABLE_VERSION", "read_binding_parameter_table"]
