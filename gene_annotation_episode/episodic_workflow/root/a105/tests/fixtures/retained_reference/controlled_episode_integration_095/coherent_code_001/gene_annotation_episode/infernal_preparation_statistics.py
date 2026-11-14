"""Pure native readers for cmbuild, cmcalibrate and cmstat (Infernal 1.1).

Native tokens, complete sidecar series, fit algorithms and source locators remain
separate from saved-data calculations. Inputs are supplied bytes/text, never
paths. Generated command text is inert. Model preparation has no annotation
confidence interpretation.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import math
import re
import shlex

from .infernal_preparation_schema import (
    field_input, issue, locator, new_sheet, record_key, validate_artifact,
    validate_common_sheet, validate_operation, value,
)


CM_ALGORITHMS = ("cm_glocal_cyk", "cm_glocal_inside", "cm_local_cyk", "cm_local_inside")
STAT_CM_ALGORITHMS = ("cm_local_inside", "cm_local_cyk", "cm_glocal_inside", "cm_glocal_cyk")
STAT_HMM_ALGORITHMS = ("hmm_local_forward", "hmm_local_viterbi", "hmm_glocal_forward", "hmm_glocal_viterbi")
CALIBRATION_TAGS = {"ECMLC": "cm_local_cyk", "ECMGC": "cm_glocal_cyk",
                    "ECMLI": "cm_local_inside", "ECMGI": "cm_glocal_inside"}
IDENTITY_FIELDS = {
    "build": frozenset({"native_index", "name", "description"}),
    "build_refinement": frozenset({"name", "input_alignment_index", "native_index", "iteration"}),
    "calibration": frozenset({"algorithm", "source", "name"}),
    "calibration_series": frozenset({"algorithm", "series_kind", "model_ordinal"}),
    "resource_estimate": frozenset({"estimate_kind", "name"}),
    "partition": frozenset({"partition_index", "partition_count", "algorithm", "model_ordinal"}),
    "model_statistic": frozenset({"native_index", "name", "accession", "model_family", "algorithm", "mode"}),
}
VALUE_UNITS = {
    "build": {"nseq": "count", "eff_nseq": "count", "alignment_length": "column",
        "consensus_length": "nt", "base_pairs": "count", "bifurcations": "count",
        "cm_relative_entropy": "bit_per_position", "hmm_relative_entropy": "bit_per_position"},
    "build_refinement": {"bit_score_sum": "bit", "fractional_difference": "fraction"},
    "calibration": {"lambda": "inverse_bit", "mu_orig": "bit", "mu_extrap": "bit",
        "calibration_dbsize_nt": "nt", "random_hit_count": "count", "tail_probability_mass": "fraction"},
    "calibration_series": {"tail_probability_mass": "fraction", "lambda": "inverse_bit",
        "mu_orig": "bit", "tail_hit_count": "count"},
    "resource_estimate": {"predicted_seconds": "second", "predicted_mb": "MB",
        "cpu_count": "count", "command_count": "count"},
    "partition": {"score_count": "count", "requested_megabases": "Mnt",
        "total_chunks": "count", "partition_chunks": "count"},
    "model_statistic": {"nseq": "count", "eff_nseq": "count", "consensus_length": "nt",
        "max_hit_length": "nt", "base_pairs": "count", "bifurcations": "count",
        "cm_relative_entropy": "bit_per_position", "hmm_relative_entropy": "bit_per_position",
        "threshold_bits": "bit", "evalue": "expected_count", "pvalue": "fraction", "search_space_nt": "nt"},
    "training_alignment": {"row_count": "count", "column_count": "column", "checksum": "dimensionless",
        "rf_column_count": "column"},
}
ROW_FIELDS = {kind: frozenset({"kind", "record_key", "locator", "model_keys", "identity", "values", "series"})
              for kind in IDENTITY_FIELDS}
ROW_FIELDS["training_alignment"] = frozenset({"kind", "record_key", "locator", "format", "name", "accession",
                                             "content_validation", "sequence_names", "values"})
VALUE_FIELDS = {kind: frozenset(fields) for kind, fields in VALUE_UNITS.items()}
COMPONENT_NAMES = frozenset()
CHECK_NAMES = frozenset()
ISSUE_CODES = frozenset("infernal_statistics_" + code for code in (
    "encoding_invalid", "format_mismatch", "version_unsupported", "native_version_mismatch", "native_failure",
    "number_invalid", "row_malformed", "header_missing", "capture_incomplete", "no_rows",
    "series_unterminated", "series_count_mismatch", "series_delimiter_invalid", "series_model_ambiguous",
    "series_header_invalid", "partition_count_mismatch", "partition_command_invalid", "commands_script_unparsed",
    "model_population_incomplete", "model_association_unresolved", "model_attribute_mismatch", "model_population_mismatch",
    "duplicate_native_index", "alignment_format_unsupported", "alignment_invalid", "alignment_partial",
    "alignment_rf_missing", "alignment_structure_missing", "alignment_checksum_unavailable", "alignment_identity_ambiguous",
    "clustering_association_unverified", "operation_parameter_mismatch", "unexpected_output_role",
))
_FLOAT = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
_MISSING = {"-", "?", "N/A", "<not-set>"}
_MODEL_FORMATS = {"infernal_cm_ascii", "infernal_cm_legacy_ascii", "infernal_cm_binary", "hmmer_hmm_ascii"}
_SIDECAR_FORMATS = {k: "infernal_calibration_"+k for k in ("hfile", "sfile", "qqfile", "ffile", "xfile")}
_SIDECAR_FORMATS.update(partition_scores="infernal_partition_scores", commands="infernal_commands")
SERIES_KINDS = {
    "hfile": ("observed_bin_count", "fitted_expected_bin_count"),
    "sfile": ("empirical_tail_fraction", "fitted_tail_fraction", "comparison_exponential_survival"),
    "qqfile": ("fitted_quantile", "identity_reference"),
    "xfile": ("fitted_tail_scores",),
}


def _problem(issues, code, artifact, *, key=None, field=None, stage="extraction", severity="error"):
    code = "infernal_statistics_"+code
    if code not in ISSUE_CODES:
        raise ValueError("undeclared_infernal_statistics_issue")
    issues.append(issue(code, artifact_ref=artifact["artifact_ref"], record_key=key, field=field,
                        stage=stage, severity=severity))


def _text(content, artifact, issues):
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            _problem(issues, "encoding_invalid", artifact, stage="format")
            return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict) or content is None:
        raise TypeError("infernal_statistics_supplied_text_required")
    try:
        parts = list(content)
    except TypeError as error:
        raise TypeError("infernal_statistics_supplied_text_required") from error
    if any(type(part) is not str for part in parts):
        raise TypeError("infernal_statistics_text_lines_required")
    return "".join(parts)


def _lines(text, artifact):
    offset = 0
    for i, raw in enumerate(text.splitlines(keepends=True), 1):
        size = len(raw.encode("utf-8"))
        yield raw.strip(), locator(artifact["artifact_ref"], line_start=i, line_end=i,
                                   byte_start=offset, byte_end=offset+size)
        offset += size


def _begin(content, operation, artifact, program, expected_format="infernal_stdout"):
    validate_operation(operation)
    validate_artifact(artifact)
    if operation["program"] != program:
        raise ValueError("infernal_statistics_program_mismatch")
    issues = []
    text = _text(content, artifact, issues)
    if artifact["format"] != expected_format:
        _problem(issues, "format_mismatch", artifact, stage="format")
        text = ""
    version = operation["engine_version"]
    if version is not None and not re.search(r"\b1\.1\.[1-5]\b", version):
        _problem(issues, "version_unsupported", artifact, stage="format")
        text = ""
    native_version = re.search(r"^# INFERNAL (\S+)", text, re.MULTILINE)
    if native_version and version is not None and native_version[1] not in version:
        _problem(issues, "native_version_mismatch", artifact, stage="format")
    if artifact["completeness"] != "complete":
        _problem(issues, "capture_incomplete", artifact, severity="warning", stage="format")
    if text.startswith(("Failed to parse", "Incorrect number", "Error:", "FATAL:")):
        _problem(issues, "native_failure", artifact, stage="format")
    return text, issues


def _row(kind, artifact, ordinal, loc, **identity):
    if set(identity) != IDENTITY_FIELDS[kind]:
        raise ValueError("infernal_statistics_identity_fields")
    return {"kind": kind, "record_key": record_key(artifact["artifact_ref"], kind, ordinal),
            "locator": {**loc, "record_ordinal": ordinal}, "model_keys": [], "identity": identity,
            "values": {k: value(state="not_measured", unit=u) for k, u in VALUE_UNITS[kind].items()}, "series": []}


def _number(token, *, loc, field, unit, issues, artifact, key=None, integer=False,
            nonnegative=False, basis="native_reported", missing="missing"):
    inputs = [field_input(loc, field)]
    if token in _MISSING or token is None:
        return value(state=missing, basis=basis, unit=unit, inputs=inputs, native_token=token)
    try:
        if type(token) is not str or _FLOAT.fullmatch(token) is None:
            raise ValueError
        if integer:
            if re.fullmatch(r"[+-]?\d+", token) is None:
                raise ValueError
            number = int(token)
        else:
            number = float(token)
        if not math.isfinite(number) or (nonnegative and number < 0):
            raise ValueError
    except (ValueError, OverflowError):
        _problem(issues, "number_invalid", artifact, key=key, field=field)
        return value(state="invalid", basis=basis, unit=unit, inputs=inputs, native_token=token)
    return value(number, basis=basis, unit=unit, inputs=inputs, native_token=token)


def _set(row, name, token, issues, artifact, **kwargs):
    algorithm = row["identity"].get("algorithm")
    field = algorithm+"."+name if algorithm is not None else name
    row["values"][name] = _number(token, loc=row["locator"], field=field,
        unit=VALUE_UNITS[row["kind"]][name], issues=issues, artifact=artifact, key=row["record_key"], **kwargs)


def parse_cmbuild_summary(text, *, operation, artifact):
    """Read final native build rows and every printed native refine iteration."""
    text, issues = _begin(text, operation, artifact, "cmbuild")
    rows, heading, refine = [], False, None
    seen = set()
    for line, loc in _lines(text, artifact):
        m = re.fullmatch(r"# Refining MSA for CM: (\S+) \(aln:\s*(\d+) cm:\s*(\d+)\)", line)
        if m:
            refine = (m[1], int(m[2]), int(m[3]))
            heading = False
        if line.startswith("# idx") and all(s in line for s in ("nseq", "eff_nseq", "alen", "clen", "bps", "bifs")):
            heading, refine = True, None
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 10)
        if refine is not None and parts and parts[0].isdigit():
            row = _row("build_refinement", artifact, len(rows), loc, name=refine[0],
                       input_alignment_index=refine[1], native_index=refine[2], iteration=int(parts[0]))
            if len(parts) != 3:
                _problem(issues, "row_malformed", artifact, key=row["record_key"])
            for name, token in zip(("bit_score_sum", "fractional_difference"), parts[1:3]):
                _set(row, name, token, issues, artifact)
            rows.append(row)
        elif heading and parts and parts[0].isdigit():
            if len(parts) < 10:
                _problem(issues, "row_malformed", artifact)
                continue
            idx = int(parts[0])
            row = _row("build", artifact, len(rows), loc, native_index=idx, name=parts[1],
                       description=parts[10] if len(parts) == 11 else None)
            if idx in seen or idx < 1:
                _problem(issues, "duplicate_native_index", artifact, key=row["record_key"])
            seen.add(idx)
            for name, token in zip(VALUE_UNITS["build"], parts[2:10]):
                _set(row, name, token, issues, artifact, integer=name not in
                     {"eff_nseq", "cm_relative_entropy", "hmm_relative_entropy"}, nonnegative=True)
            rows.append(row)
    if not heading:
        _problem(issues, "header_missing", artifact, stage="format")
    if not rows:
        _problem(issues, "no_rows", artifact)
    return {"rows": rows, "issues": issues}


def _time_cell(token, loc, artifact, issues):
    if token == "?":
        return value(state="not_measured", basis="native_prediction", unit="second",
                     inputs=[field_input(loc, "predicted_running_time")], native_token=token)
    m = re.fullmatch(r"(\d+):(\d\d):(\d\d)", token)
    if m is None or int(m[2]) > 59 or int(m[3]) > 59:
        _problem(issues, "number_invalid", artifact, field="predicted_seconds")
        return value(state="invalid", basis="native_prediction", unit="second", native_token=token)
    return value(int(m[1])*3600+int(m[2])*60+int(m[3]), basis="native_prediction", unit="second",
                 inputs=[field_input(loc, "predicted_running_time")], native_token=token)


def parse_cmcalibrate_output(text, *, operation, artifact):
    """Read calibration summaries and native predictions without timing learning."""
    text, issues = _begin(text, operation, artifact, "cmcalibrate")
    rows, summary, cpus, memory_cpus, partition_count = [], False, None, None, None
    columns, prediction_header, memory_header = None, False, False
    pair_algorithms = {("glc", "cyk"): "cm_glocal_cyk", ("glc", "ins"): "cm_glocal_inside",
                       ("loc", "cyk"): "cm_local_cyk", ("loc", "ins"): "cm_local_inside"}
    mode = operation["mode"]
    for line, loc in _lines(text, artifact):
        if line.startswith("# Calibration summary statistics:"):
            summary = True
        if summary and line.startswith("# model name"):
            tokens = line.split()[3:]
            algorithms = [pair_algorithms.get(tuple(tokens[i:i+2])) for i in range(0, len(tokens), 2)]
            columns = [algorithms[i:i+4] for i in (0, 4, 8)]
            if len(algorithms) != 12 or any(set(c) != set(CM_ALGORITHMS) for c in columns):
                _problem(issues, "header_missing", artifact, stage="format")
                columns = None
        if line.startswith("# model name") and "(hr:min:sec)" in line:
            prediction_header = True
        if line.startswith("# Predicting required memory for calibration:"):
            memory_header = True
        m = re.search(r"calibration\(s\) on (\d+) cpus:", line)
        if m:
            cpus = (m[1], loc)
        m = re.search(r"single CPU\s+(\d+) CPUs", line)
        if m:
            memory_cpus = (m[1], loc)
        m = re.match(r"# total number of partitions:\s+(\d+)$", line)
        if m:
            partition_count = (m[1], loc)
        if not line or line.startswith("#") or line == "[ok]":
            continue
        parts = line.split()
        if summary:
            if len(parts) != 13 or columns is None:
                _problem(issues, "row_malformed", artifact)
                continue
            for algorithm in CM_ALGORITHMS:
                row = _row("calibration", artifact, len(rows), loc, algorithm=algorithm, source="stdout", name=parts[0])
                _set(row, "mu_orig", parts[1+columns[0].index(algorithm)], issues, artifact)
                _set(row, "lambda", parts[5+columns[1].index(algorithm)], issues, artifact, nonnegative=True)
                _set(row, "random_hit_count", parts[9+columns[2].index(algorithm)], issues, artifact, integer=True, nonnegative=True)
                for name in ("mu_extrap", "calibration_dbsize_nt", "tail_probability_mass"):
                    row["values"][name] = value(state="not_measured", unit=VALUE_UNITS["calibration"][name])
                rows.append(row)
        elif mode == "memory_estimate" and memory_header and len(parts) in {2, 3} and _FLOAT.fullmatch(parts[1]):
            for j, token in enumerate(parts[1:]):
                row = _row("resource_estimate", artifact, len(rows), loc,
                    estimate_kind="memory_single_cpu" if j == 0 else "memory_multiple_cpu", name=parts[0])
                _set(row, "predicted_mb", token, issues, artifact, basis="native_prediction", nonnegative=True)
                if j == 0:
                    row["values"]["cpu_count"] = value(1, basis="native_prediction", unit="count",
                        inputs=[field_input(loc, "single_CPU_column")])
                elif memory_cpus:
                    row["values"]["cpu_count"] = _number(memory_cpus[0], loc=memory_cpus[1], field="CPU_column",
                        unit="count", issues=issues, artifact=artifact, integer=True, basis="native_prediction")
                rows.append(row)
        elif prediction_header and len(parts) >= 2 and (re.fullmatch(r"\d+:\d\d:\d\d", parts[1]) or parts[1] == "?"):
            row = _row("resource_estimate", artifact, len(rows), loc, estimate_kind="running_time", name=parts[0])
            row["values"]["predicted_seconds"] = _time_cell(parts[1], loc, artifact, issues)
            if cpus:
                row["values"]["cpu_count"] = _number(cpus[0], loc=cpus[1], field="forecast_CPUs", unit="count",
                    issues=issues, artifact=artifact, integer=True, basis="native_prediction")
            elif "--nforecast" in operation["settings"]:
                row["values"]["cpu_count"] = value(operation["settings"]["--nforecast"], basis="native_prediction", unit="count")
            rows.append(row)
    if mode == "split_commands" and partition_count:
        row = _row("resource_estimate", artifact, len(rows), partition_count[1], estimate_kind="partition_command_count", name=None)
        _set(row, "command_count", partition_count[0], issues, artifact, integer=True, nonnegative=True)
        rows.append(row)
    if not rows:
        _problem(issues, "no_rows", artifact)
    return {"rows": rows, "issues": issues}


def parse_cmstat_output(text, *, operation, artifact):
    """Retain each CM/HMM algorithm, with unavailable printed cells explicit."""
    text, issues = _begin(text, operation, artifact, "cmstat")
    rows, heading, printed, seen, declared_mode = [], False, {}, set(), None
    mode = operation["mode"]
    for line, loc in _lines(text, artifact):
        if line.startswith("# idx") and "accession" in line and "model" in line:
            heading = True
            if "eff_nseq" in line:
                declared_mode = "summary"
        if line.startswith("# Printing"):
            if "E-value of" in line:
                declared_mode = "scores_at_evalue"
            elif "P-value of" in line:
                declared_mode = "scores_at_pvalue"
            elif "a bit score of" in line:
                declared_mode = "evalues_at_score"
            else:
                for tag in ("GA", "NC", "TC"):
                    if tag+" bit score thresholds" in line:
                        declared_mode = "evalues_at_"+tag.lower()
        for pattern, field in ((r"E-value of (\S+)", "evalue"), (r"P-value of (\S+)", "pvalue"),
                               (r"a bit score of (\S+)", "threshold_bits"), (r"size (\S+) Mb", "search_space_nt")):
            m = re.search(pattern, line)
            if m:
                cell = _number(m[1], loc=loc, field=field, unit=VALUE_UNITS["model_statistic"][field],
                               issues=issues, artifact=artifact)
                if field == "search_space_nt" and cell["state"] == "present":
                    cell["value"] *= 1e6
                    cell["basis"] = "derived"
                printed[field] = cell
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not heading or not parts or not parts[0].isdigit():
            continue
        cutoff = mode in {"evalues_at_ga", "evalues_at_nc", "evalues_at_tc"}
        needed = 12 if mode == "summary" else 9 if cutoff else 8
        if len(parts) != needed:
            _problem(issues, "row_malformed", artifact)
            continue
        idx, name, accession = int(parts[0]), parts[1], None if parts[2] == "-" else parts[2]
        family = parts[9] if mode == "summary" else parts[-1]
        if family not in {"cm", "hmm"}:
            _problem(issues, "row_malformed", artifact, field="model_family")
            continue
        if idx in seen or idx < 1:
            _problem(issues, "duplicate_native_index", artifact)
        seen.add(idx)
        algorithms = (None,) if mode == "summary" else STAT_CM_ALGORITHMS if family == "cm" else STAT_HMM_ALGORITHMS
        for j, algorithm in enumerate(algorithms):
            row = _row("model_statistic", artifact, len(rows), loc, native_index=idx, name=name,
                accession=accession, model_family=family, algorithm=algorithm, mode=mode)
            if mode == "summary":
                fields = ("nseq", "eff_nseq", "consensus_length", "max_hit_length", "base_pairs", "bifurcations",
                          "cm_relative_entropy", "hmm_relative_entropy")
                for field, token in zip(fields, parts[3:9]+parts[10:12]):
                    _set(row, field, token, issues, artifact, integer=field in {"nseq", "consensus_length", "max_hit_length", "base_pairs", "bifurcations"},
                        nonnegative=True, missing="incompatible" if family == "hmm" and field == "cm_relative_entropy" else "missing")
            else:
                row["values"].update(deepcopy(printed))
                field = "threshold_bits" if mode in {"scores_at_evalue", "scores_at_pvalue"} else "evalue"
                token = parts[4+j] if cutoff else parts[3+j]
                compatible = family == "cm" or j == 0 or (mode == "scores_at_pvalue" and j < 3)
                _set(row, field, token, issues, artifact, missing="missing" if compatible else "incompatible")
                if cutoff:
                    _set(row, "threshold_bits", parts[3], issues, artifact)
                if not compatible and token != "-":
                    _problem(issues, "row_malformed", artifact, key=row["record_key"], field=field)
            rows.append(row)
    if not heading:
        _problem(issues, "header_missing", artifact, stage="format")
    if declared_mode is not None and declared_mode != mode:
        _problem(issues, "operation_parameter_mismatch", artifact, field="mode", stage="validation")
    if not rows:
        _problem(issues, "no_rows", artifact)
    return {"rows": rows, "issues": issues}


def _model_ok(model):
    return model.get("kind") == "model" and model.get("content_validation") == "parsed_headers_and_boundaries"


def _model_order(model_order):
    if type(model_order) is not list or any(type(m) is not dict or m.get("kind") != "model" for m in model_order):
        raise ValueError("infernal_statistics_model_order_required")
    keys = [m.get("record_key") for m in model_order]
    if any(type(k) is not str for k in keys) or len(set(keys)) != len(keys):
        raise ValueError("infernal_statistics_model_order_keys_invalid")


def _blocks(text, artifact, delimiter, issues):
    blocks, active, start = [], [], None
    for line, loc in _lines(text, artifact):
        if not line:
            continue
        if start is None:
            start = loc
        if line in {"&", "//"}:
            valid = line == delimiter
            if not valid:
                _problem(issues, "series_delimiter_invalid", artifact, stage="format")
            combined = {**start, "line_end": loc["line_end"], "byte_end": loc["byte_end"]}
            blocks.append((active, combined, valid))
            active, start = [], None
        else:
            active.append((line, loc))
    if active:
        _problem(issues, "series_unterminated", artifact, stage="format")
        combined = {**start, "line_end": active[-1][1]["line_end"], "byte_end": active[-1][1]["byte_end"]}
        blocks.append((active, combined, False))
    return blocks


def _partition_command(line):
    """Decode selected scalar tokens only; never evaluate or execute text."""
    try:
        tokens = shlex.split(line, posix=True)
    except ValueError:
        return None
    if not tokens or tokens[0].rsplit("/", 1)[-1] != "cmcalibrate":
        return None
    result = {}
    for flag in ("--part", "--ptot", "-L", "--seed"):
        positions = [i for i, t in enumerate(tokens) if t == flag]
        if len(positions) > 1 or (positions and positions[0]+1 >= len(tokens)):
            return None
        if positions:
            result[flag] = tokens[positions[0]+1]
    return result


def _partition_rows(text, artifact, operation, model_order, issues):
    lines = [(s, loc) for s, loc in _lines(text, artifact) if s and not s.startswith("#")]
    complete = (artifact["completeness"] == "complete" and len(lines) == 5*len(model_order)
                and all(_model_ok(m) for m in model_order))
    if len(lines) != 5*len(model_order):
        _problem(issues, "series_count_mismatch", artifact, stage="association")
    rows = []
    for group in range((len(lines)+4)//5):
        batch = lines[group*5:(group+1)*5]
        command = _partition_command(batch[0][0])
        if command is None:
            _problem(issues, "partition_command_invalid", artifact, stage="format")
            command = {}
        p = command.get("--part")
        total = command.get("--ptot")
        p = int(p) if p is not None and p.isdigit() and int(p) > 0 else None
        total = int(total) if total is not None and total.isdigit() and int(total) > 0 else None
        if p is None or total is None or p > total:
            _problem(issues, "partition_command_invalid", artifact, field="partition_index")
        if operation["mode"] == "partition_scores":
            for flag, actual in (("--part", p), ("--ptot", total)):
                if flag in operation["settings"] and operation["settings"][flag] != actual:
                    _problem(issues, "operation_parameter_mismatch", artifact, field=flag, stage="validation")
        for j, (line, loc) in enumerate(batch[1:]):
            tokens = line.split()
            row = _row("partition", artifact, len(rows), loc, partition_index=p, partition_count=total,
                algorithm=CM_ALGORITHMS[j] if complete else None, model_ordinal=group if complete else None)
            if complete:
                row["model_keys"] = [model_order[group]["record_key"]]
            _set(row, "score_count", tokens[0] if tokens else None, issues, artifact, integer=True, nonnegative=True)
            row["values"]["requested_megabases"] = _number(command.get("-L"), loc=batch[0][1], field="-L",
                unit="Mnt", issues=issues, artifact=artifact, nonnegative=True)
            for k, token in enumerate(tokens[1:]):
                row["series"].append({"index": k,
                    "x": _number(token, loc=loc, field=f"score[{k}]", unit="bit", issues=issues, artifact=artifact,
                                 key=row["record_key"]), "y": value(state="not_measured", unit="dimensionless")})
            if row["values"]["score_count"]["value"] != len(row["series"]):
                _problem(issues, "partition_count_mismatch", artifact, key=row["record_key"], field="score_count")
            rows.append(row)
    return rows


def parse_cmcalibrate_sidecar(content, *, kind, operation, artifact, model_order):
    """Read all native sidecar points, retaining native block boundaries/order.

    Anonymous series bind only when the complete block population matches the
    supplied ordered model population. A missing block never shifts later joins.
    Partition request provenance is validated separately from embedded commands.
    """
    if kind not in _SIDECAR_FORMATS:
        raise ValueError("infernal_statistics_sidecar_kind_invalid")
    _model_order(model_order)
    text, issues = _begin(content, operation, artifact, "cmcalibrate", _SIDECAR_FORMATS[kind])
    if kind == "partition_scores":
        return {"rows": _partition_rows(text, artifact, operation, model_order, issues), "issues": issues}
    if kind == "commands":
        lines = [(s, loc) for s, loc in _lines(text, artifact) if s and not s.startswith("#")]
        loc = locator(artifact["artifact_ref"]) if not lines else {**lines[0][1], "line_end": lines[-1][1]["line_end"],
                                                                 "byte_end": lines[-1][1]["byte_end"]}
        row = _row("resource_estimate", artifact, 0, loc, estimate_kind="partition_command_count", name=None)
        commands = [_partition_command(s) for s, _ in lines]
        if lines and all(c is not None and "--part" in c for c in commands):
            row["values"]["command_count"] = value(len(lines), basis="derived", unit="count",
                inputs=[field_input(loc, "command_lines")])
        else:
            _problem(issues, "commands_script_unparsed", artifact, severity="warning")
        return {"rows": [row], "issues": issues}
    blocks = _blocks(text, artifact, "//" if kind == "ffile" else "&", issues)
    multiplier = 1 if kind == "ffile" else len(SERIES_KINDS[kind])
    complete = (artifact["completeness"] == "complete" and len(blocks) == len(model_order)*4*multiplier
                and all(b[2] for b in blocks) and all(_model_ok(m) for m in model_order))
    if not complete:
        _problem(issues, "series_count_mismatch", artifact, stage="association", severity="warning")
    rows = []
    mode_tokens = {"cm glc cyk": "cm_glocal_cyk", "cm glc ins": "cm_glocal_inside",
                   "cm loc cyk": "cm_local_cyk", "cm loc ins": "cm_local_inside"}
    for b, (points, loc, terminated) in enumerate(blocks):
        model_ordinal = b//(4*multiplier) if complete else None
        model = model_order[model_ordinal] if model_ordinal is not None else None
        algorithm = CM_ALGORITHMS[(b//multiplier) % 4] if complete else None
        if kind == "ffile":
            names = [s.split(":", 1)[1].strip() for s, _ in points if s.startswith("# CM:")]
            modes = [mode_tokens.get(" ".join(s.split(":", 1)[1].split())) for s, _ in points if s.startswith("# mode:")]
            native_algorithm = modes[0] if len(modes) == 1 else None
            if len(names) != 1 or native_algorithm is None:
                _problem(issues, "series_header_invalid", artifact)
                model, model_ordinal, algorithm = None, None, native_algorithm
            else:
                if model is not None and (model["name"] != names[0] or algorithm != native_algorithm):
                    _problem(issues, "series_model_ambiguous", artifact, stage="association")
                    model, model_ordinal = None, None
                if not complete:
                    candidates = [(i, m) for i, m in enumerate(model_order) if m["name"] == names[0] and _model_ok(m)]
                    if len(candidates) == 1:
                        model_ordinal, model = candidates[0]
                algorithm = native_algorithm
            for line, point_loc in points:
                if line.startswith("#"):
                    continue
                tokens = line.split()
                row = _row("calibration_series", artifact, len(rows), point_loc, algorithm=algorithm,
                    series_kind="fit_grid", model_ordinal=model_ordinal)
                if model:
                    row["model_keys"] = [model["record_key"]]
                if len(tokens) != 4:
                    _problem(issues, "row_malformed", artifact, key=row["record_key"])
                for field, token in zip(VALUE_UNITS["calibration_series"], tokens[:4]):
                    _set(row, field, token, issues, artifact, integer=field == "tail_hit_count", nonnegative=field != "mu_orig")
                rows.append(row)
            continue
        series_kind = SERIES_KINDS[kind][b % multiplier] if complete else kind+"_unresolved"
        row = _row("calibration_series", artifact, len(rows), loc, algorithm=algorithm,
                   series_kind=series_kind, model_ordinal=model_ordinal)
        if model:
            row["model_keys"] = [model["record_key"]]
        for line, point_loc in points:
            if line.startswith("#"):
                continue
            tokens = line.split()
            expected = 1 if kind == "xfile" else 2
            if len(tokens) != expected:
                _problem(issues, "row_malformed", artifact, key=row["record_key"])
            x = _number(tokens[0] if tokens else None, loc=point_loc, field="score" if kind == "xfile" else "x",
                        unit="bit", issues=issues, artifact=artifact, key=row["record_key"])
            yunit = "bit" if kind == "qqfile" else "fraction" if kind == "sfile" else "count" if series_kind == "observed_bin_count" else "expected_count"
            y = value(state="not_measured", unit="dimensionless") if kind == "xfile" else _number(
                tokens[1] if len(tokens) > 1 else None, loc=point_loc, field="y", unit=yunit,
                issues=issues, artifact=artifact, key=row["record_key"], integer=series_kind == "observed_bin_count",
                nonnegative=kind in {"hfile", "sfile"})
            row["series"].append({"index": len(row["series"]), "x": x, "y": y})
        if not row["series"]:
            _problem(issues, "row_malformed", artifact, key=row["record_key"], field="series")
        rows.append(row)
    return {"rows": rows, "issues": issues}


def _alignment_records(content, *, artifact, operation, alphabet, issues):
    from .hmmalign_inputs import iter_hmmalign_stockholm_records, stockholm_digital_checksum

    if artifact["format"] != "stockholm":
        _problem(issues, "alignment_format_unsupported", artifact, stage="format")
        return []
    text = _text(content, artifact, issues)
    result = []
    for original in iter_hmmalign_stockholm_records(text, artifact_ref=artifact["artifact_ref"], engine_version=operation["engine_version"]):
        events = original["original_events"]
        first, last = events[0]["locator"], events[-1]["locator"]
        ordinal = original["alignment_index"]
        loc = locator(artifact["artifact_ref"], ordinal, line_start=first["line"], line_end=last["line"],
                      byte_start=first["byte_start"], byte_end=last["byte_end"])
        key = record_key(artifact["artifact_ref"], "training_alignment", ordinal)
        valid = (original["header_valid"] and not original["issues"] and bool(original["rows"])
                 and all(r["geometry_valid"] and r["symbols_valid"] and not r["issues"] for r in original["rows"]))
        complete = original["complete"] and artifact["completeness"] == "complete"
        attrs = {}
        for tag, attr in (("ID", "name"), ("AC", "accession")):
            matching = [e["value"] for e in events if e["kind"] == "GF" and e["tag"] == tag]
            attrs[attr] = matching[0] if len(matching) == 1 else None
            if len(matching) > 1:
                _problem(issues, "alignment_identity_ambiguous", artifact, key=key, field=tag, stage="association")
        names = [r["name"] for r in original["rows"]]
        if len(set(names)) != len(names):
            _problem(issues, "alignment_identity_ambiguous", artifact, key=key, stage="association")
        row = {"kind": "training_alignment", "record_key": key, "locator": loc, "format": artifact["format"],
            **attrs, "content_validation": "invalid" if not valid else "parsed" if complete else "partial",
            "sequence_names": names, "values": {k: value(state="missing", unit=u) for k, u in VALUE_UNITS["training_alignment"].items()}}
        row["values"]["row_count"] = value(len(original["rows"]), basis="derived", unit="count", inputs=[field_input(loc, "sequence_rows")])
        if original["column_count"] is not None:
            row["values"]["column_count"] = value(original["column_count"], basis="derived", unit="column",
                                                   inputs=[field_input(loc, "aligned_sequences")])
        rf = original["column_annotations"].get("RF")
        ss = original["column_annotations"].get("SS_cons")
        if rf and rf["valid"]:
            row["values"]["rf_column_count"] = value(sum(c not in ".-_~" for c in rf["text"]), basis="derived", unit="column",
                                                      inputs=[field_input(loc, "#=GC RF")])
        elif operation["settings"].get("--hand"):
            _problem(issues, "alignment_rf_missing", artifact, key=key, field="RF", stage="validation")
        if (not ss or not ss["valid"]) and not operation["settings"].get("--noss"):
            _problem(issues, "alignment_structure_missing", artifact, key=key, field="SS_cons", stage="validation")
        if valid and alphabet in {"RNA", "DNA", "rna", "dna"}:
            try:
                checksum = stockholm_digital_checksum([r["aligned_sequence"] for r in original["rows"]], alphabet=alphabet)
                row["values"]["checksum"] = value(checksum, basis="derived", unit="dimensionless",
                    inputs=[field_input(loc, "aligned_sequences")])
            except ValueError:
                _problem(issues, "alignment_checksum_unavailable", artifact, key=key)
        else:
            _problem(issues, "alignment_checksum_unavailable", artifact, key=key, severity="warning")
        if not valid:
            _problem(issues, "alignment_invalid", artifact, key=key, stage="format")
        elif not complete:
            _problem(issues, "alignment_partial", artifact, key=key, stage="format", severity="warning")
        result.append(row)
    return result


def _same_field(left, right):
    return left["state"] == right["state"] == "present" and left["value"] == right["value"]


def _same_model(left, right):
    return (_model_ok(left) and _model_ok(right) and
        all(left[k] == right[k] for k in ("name", "accession", "alphabet", "model_type")) and
        all(_same_field(left["fields"][k], right["fields"][k]) for k in ("CLEN", "NSEQ", "CKSUM")))


def _add_association(sheet, relation, inputs, outputs, status):
    sheet["associations"].append({"relation": relation, "input_keys": inputs, "output_keys": outputs, "status": status})


def _bind_native_rows(sheet, models, artifacts):
    operation = sheet["operation"]
    groups = {}
    indexed = [r for r in sheet["native_rows"] if r["kind"] in {"build", "model_statistic"}]
    occurrence = Counter((r["locator"]["artifact_ref"], r["identity"]["native_index"], r["identity"].get("algorithm")) for r in indexed)
    for row in sheet["native_rows"]:
        kind = row["kind"]
        if kind not in {"build", "build_refinement", "calibration", "model_statistic", "resource_estimate"}:
            continue
        if kind == "calibration" and row["identity"]["source"] == "model_header":
            continue
        name = row["identity"].get("name")
        if name is None:
            continue
        artifact = artifacts[row["locator"]["artifact_ref"]]
        candidate = None
        if kind in {"build", "build_refinement", "model_statistic"}:
            idx = row["identity"]["native_index"]
            selected = operation["settings"].get("--key") if kind == "model_statistic" else None
            if selected is not None:
                hits = [m for m in models if selected in {m["name"], m["accession"]}]
                if idx == 1 and len(hits) == 1:
                    candidate = hits[0]
            elif idx is not None and 0 < idx <= len(models):
                candidate = models[idx-1]
            if kind != "build_refinement" and occurrence[(artifact["artifact_ref"], idx, row["identity"].get("algorithm"))] != 1:
                candidate = None
        else:
            # Four algorithm columns and two memory columns share one native row.
            group = (artifact["artifact_ref"], row["locator"]["line_start"])
            family_groups = groups.setdefault((artifact["artifact_ref"], kind), [])
            if group not in family_groups:
                family_groups.append(group)
            pos = family_groups.index(group)
            if pos < len(models):
                candidate = models[pos]
        matched = (candidate is not None and _model_ok(candidate) and candidate["name"] == name)
        if matched and kind == "model_statistic":
            matched = candidate["accession"] == row["identity"]["accession"]
        if matched:
            row["model_keys"] = [candidate["record_key"]]
            _add_association(sheet, "inspected", [candidate["record_key"]], [row["record_key"]], "validated")
        else:
            _problem(sheet["issues"], "model_association_unresolved", artifact, key=row["record_key"], stage="association", severity="warning")
            _add_association(sheet, "inspected", [], [row["record_key"]], "unresolved")


def populate_infernal_statistics_sheet(*, operation, artifacts, inputs, outputs):
    """Populate a retained supporting sheet from explicit artifact-role lists."""
    from .infernal_preparation_models import extract_infernal_models

    if operation.get("program") not in {"cmbuild", "cmcalibrate", "cmstat"}:
        raise ValueError("infernal_statistics_program_mismatch")
    sheet = new_sheet(operation, artifacts)
    by_ref = {a["artifact_ref"]: a for a in artifacts}
    if len(by_ref) != len(artifacts):
        raise ValueError("infernal_statistics_duplicate_artifact")
    for mapping in (inputs, outputs):
        if type(mapping) is not dict:
            raise ValueError("infernal_statistics_role_map_required")
        for role, payloads in mapping.items():
            if type(role) is not str or type(payloads) is not list:
                raise ValueError("infernal_statistics_role_list_required")
            for payload in payloads:
                if type(payload) is not dict or set(payload) != {"artifact", "content"}:
                    raise ValueError("infernal_statistics_payload_required")
                a = payload["artifact"]
                validate_artifact(a)
                if a["role"] != role or by_ref.get(a["artifact_ref"]) != a:
                    raise ValueError("infernal_statistics_payload_artifact_mismatch")
    model_sets, complete = {}, {}
    for direction, mapping, roles in (("input_records", inputs, ("models",)),
                                      ("output_records", outputs, ("built_models", "calibrated_models"))):
        for role in roles:
            records, population_complete = [], bool(mapping.get(role))
            for payload in mapping.get(role, []):
                a = payload["artifact"]
                extracted = extract_infernal_models(payload["content"], artifact=a, format=a["format"], engine_version=operation["engine_version"])
                records.extend(extracted["records"])
                sheet["issues"].extend(extracted["issues"])
                population_complete &= extracted["population_complete"]
                if not extracted["population_complete"]:
                    _problem(sheet["issues"], "model_population_incomplete", a, stage="association", severity="warning")
            model_sets[role], complete[role] = records, population_complete
            sheet[direction].extend(records)
    program = operation["program"]
    if program == "cmbuild":
        models = model_sets["built_models"]
    elif program == "cmcalibrate" and operation["mode"] in {"calibrate", "merge_scores"}:
        models = model_sets["calibrated_models"] or model_sets["models"]
    else:
        models = model_sets["models"]
    if program == "cmbuild":
        alphabets = {m["alphabet"] for m in models if _model_ok(m)}
        alphabet = next(iter(alphabets)) if len(alphabets) == 1 else None
        for direction, mapping, roles in (("input_records", inputs, ("alignment",)),
                                          ("output_records", outputs, ("processed_alignment", "refined_alignment"))):
            for role in roles:
                for payload in mapping.get(role, []):
                    sheet[direction].extend(_alignment_records(payload["content"], artifact=payload["artifact"],
                        operation=operation, alphabet=alphabet, issues=sheet["issues"]))
    parser = {"cmbuild": parse_cmbuild_summary, "cmcalibrate": parse_cmcalibrate_output, "cmstat": parse_cmstat_output}[program]
    for payload in outputs.get("stdout", []):
        parsed = parser(payload["content"], operation=operation, artifact=payload["artifact"])
        sheet["native_rows"].extend(parsed["rows"])
        sheet["issues"].extend(parsed["issues"])
    _bind_native_rows(sheet, models, by_ref)
    if program == "cmcalibrate":
        for model in model_sets["calibrated_models"]:
            for tag in CALIBRATION_TAGS:
                fit = model["calibration"][tag]
                if fit is None:
                    continue
                a = by_ref[model["locator"]["artifact_ref"]]
                ordinal = sum(r["kind"] == "calibration" and r["locator"]["artifact_ref"] == a["artifact_ref"] for r in sheet["native_rows"])
                row = _row("calibration", a, ordinal, fit["locator"], algorithm=fit["algorithm"], source="model_header", name=model["name"])
                row["values"] = {field: deepcopy(fit[field]) for field in VALUE_UNITS["calibration"]}
                row["model_keys"] = [model["record_key"]]
                sheet["native_rows"].append(row)
                _add_association(sheet, "inspected", [model["record_key"]], [row["record_key"]], "validated" if _model_ok(model) else "unresolved")
        source_models = model_sets["models"]
        for mapping in (inputs, outputs):
            for role in _SIDECAR_FORMATS:
                for payload in mapping.get(role, []):
                    parsed = parse_cmcalibrate_sidecar(payload["content"], kind=role, operation=operation, artifact=payload["artifact"],
                        model_order=source_models if complete["models"] else [])
                    sheet["native_rows"].extend(parsed["rows"])
                    sheet["issues"].extend(parsed["issues"])
        targets = model_sets["calibrated_models"]
        for i, target in enumerate(targets):
            source = source_models[i] if i < len(source_models) else None
            status = "validated" if source is not None and _same_model(source, target) else "unresolved"
            _add_association(sheet, "calibrated_from", [] if source is None else [source["record_key"]], [target["record_key"]], status)
            if status != "validated":
                _problem(sheet["issues"], "model_attribute_mismatch", by_ref[target["locator"]["artifact_ref"]], key=target["record_key"], stage="association")
        if targets and len(targets) != len(source_models):
            _problem(sheet["issues"], "model_population_mismatch", by_ref[targets[0]["locator"]["artifact_ref"]], stage="association")
    if program == "cmbuild":
        alignments = [r for r in sheet["input_records"] if r["kind"] == "training_alignment"]
        refined = [r for r in sheet["output_records"] if r["kind"] == "training_alignment" and
                   by_ref[r["locator"]["artifact_ref"]]["role"] == "refined_alignment"]
        selected = refined if operation["mode"] == "refine" else alignments
        cluster = any(operation["settings"].get(k) for k in ("--ctarget", "--cmaxid", "--call", "--corig"))
        for i, model in enumerate(models):
            source = selected[i] if i < len(selected) and not cluster else None
            valid = (source is not None and source["content_validation"] == "parsed" and _model_ok(model)
                     and (source["name"] in {None, model["name"]} or operation["settings"].get("-n") == model["name"])
                     and _same_field(source["values"]["checksum"], model["fields"]["CKSUM"])
                     and _same_field(source["values"]["row_count"], model["fields"]["NSEQ"]))
            _add_association(sheet, "built_from", [] if source is None else [source["record_key"]], [model["record_key"]], "validated" if valid else "unresolved")
            if not valid:
                _problem(sheet["issues"], "clustering_association_unverified" if cluster else "model_association_unresolved",
                    by_ref[model["locator"]["artifact_ref"]], key=model["record_key"], stage="association", severity="warning")
    validate_common_sheet(sheet)
    return sheet


__all__ = ["parse_cmbuild_summary", "parse_cmcalibrate_output", "parse_cmcalibrate_sidecar",
           "parse_cmstat_output", "populate_infernal_statistics_sheet", "ISSUE_CODES", "CHECK_NAMES",
           "COMPONENT_NAMES", "ROW_FIELDS", "IDENTITY_FIELDS", "VALUE_FIELDS"]
