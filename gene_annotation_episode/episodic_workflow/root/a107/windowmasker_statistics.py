"""Offline reader and validator for complete retained ASCII WindowMasker counts.

Unit counts retain native integer meaning and clipping; missing codes are not
zeros. Native metadata/trailer thresholds are compared only to one another,
never to requested CLI thresholds or to the range of emitted unit-count rows.
"""
from __future__ import annotations

import math
import re

from .domain import ContractError
from .sequence_masking_contracts import validate_sequence_masking_record
from .sequence_masking_inputs import _bytes, _check, _failure, _unreadable


_THRESHOLDS = ("t_low", "t_extend", "t_threshold", "t_high")
_VERSION_PREFIX = "##windowmasker-statistics-format-version:"
_ALGORITHM_PREFIX = "##windowmasker-statistics-algorithm-version:"


def _decimal(text):
    """A syntactically decimal native token can exceed interpreter conversion limits."""
    try:
        return int(text)
    except ValueError:
        return None


def parse_windowmasker_statistics(content: bytes, *, occurrence: dict, format: str,
        reference_binding: dict | None) -> dict:
    """Retain every valid row plus typed diagnostics for malformed native text."""
    occurrence = validate_sequence_masking_record("Occurrence", occurrence)
    if occurrence["role"] != "statistics":
        raise ContractError("sequence_masking_statistics_occurrence")
    if format != "ascii_statistics":
        raise ContractError("sequence_masking_statistics_format")
    if reference_binding is not None:
        reference_binding = validate_sequence_masking_record("StatisticsBinding", reference_binding)
        if reference_binding["statistics_occurrence_id"] != occurrence["occurrence_id"]:
            raise ContractError("sequence_masking_statistics_occurrence_reference")
    _bytes(content, occurrence)
    result = {"version": "windowmasker_statistics_v1", "occurrence": occurrence,
        "format": format, "reference_binding": reference_binding, "format_version": None,
        "algorithm_version": None, "unit_length": None, "metadata_lines": [], "unit_counts": [],
        "thresholds": dict.fromkeys(_THRESHOLDS), "percentiles": [], "checks": [], "failures": []}
    oid, unit_declarations = occurrence["occurrence_id"], 0
    def fail(code, line=None):
        result["failures"].append(_failure("statistics", code, oid, line_number=line))
    for number, raw in enumerate(content.splitlines(), 1):
        line = raw.decode("utf-8", errors="surrogateescape")
        stripped = line.strip()
        if not stripped:
            continue
        if _unreadable(line):
            fail("statistics_not_utf8", number)
        if stripped.startswith(("#", ">")):
            result["metadata_lines"].append({"line_number": number, "text": line})
        if stripped.startswith(_VERSION_PREFIX):
            token = stripped[len(_VERSION_PREFIX):].strip()
            match = re.fullmatch(r"ascii\s+(\S+)", token)
            if match is None:
                fail("statistics_format_version_syntax", number)
            elif result["format_version"] is not None:
                fail("duplicate_statistics_format_version", number)
            else:
                result["format_version"] = match.group(1)
        elif stripped.startswith(_ALGORITHM_PREFIX):
            token = stripped[len(_ALGORITHM_PREFIX):].strip()
            if not token:
                fail("statistics_algorithm_version_syntax", number)
            elif result["algorithm_version"] is not None:
                fail("duplicate_statistics_algorithm_version", number)
            else:
                result["algorithm_version"] = token
        elif stripped.startswith("##pct"):
            match = re.fullmatch(r"##pct:\s*([0-9]+)\s+(\S+)\s*", stripped)
            if match is None:
                fail("statistics_percentile_syntax", number); continue
            try:
                percentage = float(match.group(2))
            except ValueError:
                fail("statistics_percentile_syntax", number); continue
            if not math.isfinite(percentage):
                fail("statistics_percentile_nonfinite", number); continue
            count = _decimal(match.group(1))
            if count is None:
                fail("statistics_percentile_syntax", number); continue
            result["percentiles"].append({"line_number": number, "count": count,
                "percentage": percentage, "percentage_lexeme": match.group(2)})
        elif stripped.startswith("#"):
            # Unknown metadata remains native data; it does not set defaults.
            continue
        elif stripped.startswith(">"):
            match = re.fullmatch(r">(t_low|t_extend|t_threshold|t_high)\s+(-?[0-9]+)\s*", stripped)
            if match is None:
                fail("statistics_threshold_syntax", number)
            elif result["thresholds"][match.group(1)] is not None:
                fail("duplicate_statistics_threshold", number)
            else:
                count = _decimal(match.group(2))
                if count is None:
                    fail("statistics_threshold_syntax", number)
                else:
                    result["thresholds"][match.group(1)] = count
        elif re.fullmatch(r"[0-9]+", stripped):
            unit_declarations += 1
            if unit_declarations > 1:
                fail("duplicate_statistics_unit_length", number)
            elif (unit := _decimal(stripped)) is None or not 1 <= unit <= 16:
                fail("statistics_unit_length_range", number)
            else:
                result["unit_length"] = unit
        else:
            match = re.fullmatch(r"([0-9a-fA-F]+)\s+([0-9]+)\s*", stripped)
            if match is None:
                fail("statistics_unit_row_syntax", number); continue
            if result["unit_length"] is None:
                fail("statistics_unit_row_before_length", number)
            if any(v is not None for v in result["thresholds"].values()):
                fail("statistics_unit_row_after_threshold", number)
            count = _decimal(match.group(2))
            if count is None:
                fail("statistics_unit_row_syntax", number); continue
            result["unit_counts"].append({"line_number": number, "unit_code_hex": match.group(1),
                "unit_code": int(match.group(1), 16), "native_count": count})
    result["checks"] = validate_windowmasker_statistics(result)
    for check in result["checks"]:
        if check["status"] == "fail" and check["reason"] not in {f["code"] for f in result["failures"]}:
            fail(check["reason"])
    return validate_sequence_masking_record("WindowMaskerStatistics", result)


def _metadata_parameters(statistics):
    """Extract native metadata parameter declarations for native-to-native checks."""
    recorded, invalid = {}, False
    for row in statistics["metadata_lines"]:
        text = row["text"].strip()
        if not text.startswith("##parameters:"):
            continue
        for token in text[len("##parameters:"):].split():
            match = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)=(-?[0-9]+)", token)
            if match is None:
                invalid = True; continue
            key, value = match.group(1), _decimal(match.group(2))
            if value is None:
                invalid = True; continue
            if key in recorded and recorded[key] != value:
                invalid = True
            recorded[key] = value
    return recorded, invalid


def validate_windowmasker_statistics(statistics: dict) -> list[dict]:
    """Re-evaluate native validity/provenance checks from a saved typed artifact.

    This is validation, not a probability or a scientific acceptance gate. A
    caller declaration stays caller-declared, and unknown provenance stays so.
    """
    statistics = validate_sequence_masking_record("WindowMaskerStatistics", statistics)
    checks = []
    def check(name, valid, reason):
        checks.append(_check(name, "pass" if valid else "fail", reason=None if valid else reason))
    syntax_codes = {"statistics_not_utf8", "statistics_format_version_syntax", "statistics_algorithm_version_syntax",
        "statistics_percentile_syntax", "statistics_percentile_nonfinite", "statistics_threshold_syntax",
        "statistics_unit_row_syntax", "statistics_unit_row_before_length", "statistics_unit_row_after_threshold"}
    check("statistics_syntax", not any(f["code"] in syntax_codes for f in statistics["failures"]),
          "malformed_statistics_content")
    check("statistics_one_unit_length", statistics["unit_length"] is not None and
          not any(f["code"] == "duplicate_statistics_unit_length" for f in statistics["failures"]),
          "statistics_unit_length_missing_or_duplicate")
    codes = [r["unit_code"] for r in statistics["unit_counts"]]
    check("statistics_unique_units", len(codes) == len(set(codes)), "duplicate_statistics_unit_code")
    check("statistics_native_unit_order", all(a <= b for a, b in zip(codes, codes[1:])), "statistics_unit_order")
    if statistics["unit_length"] is None:
        checks.append(_check("statistics_unit_code_range", "unknown", reason="statistics_unit_length_unavailable"))
    else:
        check("statistics_unit_code_range", all(c < 4**statistics["unit_length"] for c in codes), "statistics_unit_code_out_of_range")
    check("statistics_integer_counts", all(type(r["native_count"]) is int and r["native_count"] >= 0
          for r in statistics["unit_counts"]), "statistics_invalid_unit_count")
    check("statistics_threshold_presence", all(v is not None for v in statistics["thresholds"].values()),
          "statistics_threshold_missing")
    check("statistics_threshold_values", all(v is None or v >= (0 if k == "t_extend" else 1)
          for k, v in statistics["thresholds"].items()), "statistics_threshold_range")
    metadata, invalid = _metadata_parameters(statistics)
    observed = {"unit": statistics["unit_length"], **statistics["thresholds"]}
    comparable = {k: v for k, v in metadata.items() if k in observed}
    if invalid or any(observed[k] is not None and observed[k] != v for k, v in comparable.items()):
        checks.append(_check("statistics_metadata_agreement", "fail", reason="statistics_metadata_parameter_conflict"))
    elif comparable:
        checks.append(_check("statistics_metadata_agreement", "pass"))
    else:
        checks.append(_check("statistics_metadata_agreement", "unknown", reason="native_parameter_metadata_unavailable"))
    percentiles = statistics["percentiles"]
    if percentiles:
        check("statistics_percentile_range", all(0 <= r["percentage"] <= 100 for r in percentiles), "statistics_percentile_out_of_range")
        counts = [r["count"] for r in percentiles]
        check("statistics_percentile_count_order", all(a < b for a, b in zip(counts, counts[1:])), "statistics_percentile_count_order")
    else:
        checks.append(_check("statistics_percentile_range", "not_applicable", reason="percentile_metadata_absent"))
    checks.append(_check("statistics_output_completeness", "pass" if statistics["occurrence"]["completeness"] == "complete" else "unknown",
        reason=None if statistics["occurrence"]["completeness"] == "complete" else "statistics_artifact_incomplete"))
    binding = statistics["reference_binding"]
    if binding is None or binding["provenance"] == "unknown":
        checks.append(_check("statistics_reference_relationship", "unknown", reason="reference_provenance_unknown"))
    elif binding["provenance"] == "caller_declared":
        checks.append(_check("statistics_reference_relationship", "unknown", reason="reference_caller_declared"))
    else:
        checks.append(_check("statistics_reference_relationship", "pass"))
    for field in ("format_version", "algorithm_version"):
        checks.append(_check("statistics_" + field, "pass" if statistics[field] is not None else "unknown",
                             reason=None if statistics[field] is not None else "native_version_unavailable"))
    return checks
