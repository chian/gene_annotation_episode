"""Native TnSeq/RNASeq tables; no inference of intervention or function.

The output retains original lines and locations, declared native scales and
missing values. Only DESeq2's reported lfcSE is squared to obtain its estimate
variance. A p-value never supplies a variance or an experimental subscore.
"""
from copy import deepcopy
import hashlib
import math
import re
from decimal import Decimal

from .bvbrc_annotation_native import _canonical, _content, _finite_json


DOCUMENT_VERSION = "intervention_analysis_native_v1"
COMPONENTS_VERSION = "intervention_analysis_components_v1"
REPRESENTATIONS = ("transit_resampling", "transit_table", "deseq2", "count_matrix",
                   "sample_metadata", "quality_report")
_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
_MISSING = {"", "NA", "NaN", "nan", "N/A", "."}
_RESAMPLING = {
    "feature_id": (("Orf", "ORF"), "identifier"),
    "sites": (("Sites",), "insertion_sites"),
    "reference_mean": (("Mean Ctrl",), "mean_insertion_count"),
    "intervention_mean": (("Mean Exp",), "mean_insertion_count"),
    "log2_fold_change": (("log2FC",), "log2_ratio"),
    "reference_sum": (("Sum Ctrl",), "insertion_count"),
    "intervention_sum": (("Sum Exp",), "insertion_count"),
    "mean_difference": (("Delta Mean",), "mean_insertion_count"),
    "p_value": (("p-value",), "probability"),
    "adjusted_p_value": (("Adj. p-value", "q-value"), "probability"),
}
_DESEQ = {
    "feature_id": (("Gene_Name", "gene", "gene_id", ""), "identifier"),
    "base_mean": (("baseMean",), "normalized_count"),
    "log2_fold_change": (("log2FoldChange",), "log2_ratio"),
    "standard_error": (("lfcSE",), "log2_ratio"),
    "test_statistic": (("stat",), "native_statistic"),
    "p_value": (("pvalue",), "probability"),
    "adjusted_p_value": (("padj",), "probability"),
}


def _require(condition, code="intervention_analysis_document_invalid"):
    if not condition:
        raise ValueError(code)


def _issue(code, path, severity="qualification"):
    return dict(code=code, path=path, severity=severity)


def _physical_lines(raw):
    result, start = [], 0
    # Split only actual text line endings, not other Unicode control codes.
    for ordinal, match in enumerate(re.finditer(rb"[^\r\n]*(?:\r\n|\r|\n|$)", raw)):
        piece = match.group()
        if not piece:
            continue
        ending = "\r\n" if piece.endswith(b"\r\n") else "\n" if piece.endswith(b"\n") else "\r" if piece.endswith(b"\r") else ""
        text = piece.decode("utf-8")
        result.append(dict(text=text[:-len(ending)] if ending else text, ending=ending,
            byte_start=start, byte_end=start + len(piece), line=ordinal + 1))
        start += len(piece)
    return result


def _table(lines, representation):
    if representation == "quality_report":
        return dict(header=None, header_line=None, rows=[], comments=list(range(len(lines))))
    header, header_line, rows, comments = None, None, [], []
    transit = representation.startswith("transit_")
    for i, line in enumerate(lines):
        text = line["text"]
        candidate = text[1:] if transit and text.startswith("#") else text
        fields = candidate.split("\t")
        if header is None:
            if not text.strip() or text.startswith("#") and not (transit and fields[0] in {"Orf", "ORF"}):
                comments.append(i)
                continue
            header, header_line = fields, i
        elif text.startswith("#") or not text.strip():
            comments.append(i)
        else:
            rows.append(dict(row_ordinal=len(rows), line_index=i, cells=text.split("\t")))
    return dict(header=header, header_line=header_line, rows=rows, comments=comments)


def _issues(table, representation, complete):
    issues = []
    if not complete:
        issues.append(_issue("native_capture_incomplete", "/capture_complete"))
    if representation == "quality_report":
        return issues
    header = table["header"]
    if header is None:
        return issues + [_issue("native_table_header_missing", "/native_document/table/header", "error")]
    if len(set(header)) != len(header):
        issues.append(_issue("native_table_duplicate_columns", "/native_document/table/header", "error"))
    fields = _RESAMPLING if representation == "transit_resampling" else _DESEQ if representation == "deseq2" else {}
    for name, (aliases, _) in fields.items():
        if sum(h in aliases for h in header) != 1:
            issues.append(_issue("native_column_missing_or_ambiguous", "/columns/" + name, "error"))
    for row in table["rows"]:
        if len(row["cells"]) != len(header):
            issues.append(_issue("native_table_row_width_conflict", "/rows/" + str(row["row_ordinal"]), "error"))
    return issues


def parse_intervention_artifact(raw, *, content, representation, capture_complete, expected_task_id):
    content = _content(content)
    _require(type(raw) is bytes and len(raw) == content["byte_count"]
        and hashlib.sha256(raw).hexdigest() == content["sha256"], "intervention_analysis_bytes_conflict")
    _require(representation in REPRESENTATIONS and type(capture_complete) is bool
        and type(expected_task_id) is str and bool(expected_task_id))
    try:
        lines = _physical_lines(raw)
        table = _table(lines, representation)
        native = dict(lines=lines, table=table)
        issues = _issues(table, representation, capture_complete)
    except UnicodeError:
        native = None
        issues = [_issue("invalid_native_utf8", "/native_document", "error")]
        if not capture_complete:
            issues.append(_issue("native_capture_incomplete", "/capture_complete"))
    return dict(version=DOCUMENT_VERSION, representation=representation, content=content,
        capture_complete=capture_complete, expected_task_id=expected_task_id,
        native_document=native, issues=issues)


def validate_intervention_document(value):
    """Authenticate saved locations and tables without re-reading the input file."""
    _finite_json(value)
    _require(type(value) is dict and set(value) == {"version", "representation", "content",
        "capture_complete", "expected_task_id", "native_document", "issues"}
        and value["version"] == DOCUMENT_VERSION and value["representation"] in REPRESENTATIONS
        and type(value["capture_complete"]) is bool
        and type(value["expected_task_id"]) is str and bool(value["expected_task_id"]))
    content = _content(value["content"])
    native = value["native_document"]
    if native is None:
        expected = [_issue("invalid_native_utf8", "/native_document", "error")]
        if not value["capture_complete"]:
            expected.append(_issue("native_capture_incomplete", "/capture_complete"))
    else:
        _require(type(native) is dict and set(native) == {"lines", "table"} and type(native["lines"]) is list)
        digest, start = hashlib.sha256(), 0
        for i, line in enumerate(native["lines"]):
            _require(type(line) is dict and set(line) == {"text", "ending", "byte_start", "byte_end", "line"}
                and type(line["text"]) is str and "\r" not in line["text"] and "\n" not in line["text"]
                and line["ending"] in {"\r", "\n", "\r\n", ""}
                and (line["ending"] or i == len(native["lines"]) - 1)
                and type(line["line"]) is int and line["line"] == i + 1
                and type(line["byte_start"]) is int and line["byte_start"] == start)
            raw = (line["text"] + line["ending"]).encode("utf-8")
            start += len(raw)
            _require(type(line["byte_end"]) is int and line["byte_end"] == start)
            digest.update(raw)
        _require(start == content["byte_count"] and digest.hexdigest() == content["sha256"],
            "intervention_analysis_saved_bytes_conflict")
        _require(native["table"] == _table(native["lines"], value["representation"]))
        expected = _issues(native["table"], value["representation"], value["capture_complete"])
    _require(value["issues"] == expected)
    return deepcopy(value)


def _metric(row, header, aliases, unit):
    indices = [i for i, name in enumerate(header) if name in aliases]
    tokens = [row["cells"][i] if i < len(row["cells"]) else None for i in indices]
    state = "column_missing" if not indices else "column_ambiguous" if len(indices) != 1 else "available"
    value = None
    if state == "available":
        token = tokens[0]
        if len(row["cells"]) != len(header):
            state = "row_width_conflict"
        elif token is None or token in _MISSING:
            state = "missing"
        elif unit == "identifier":
            value = token
        elif not _NUMBER.fullmatch(token) or not math.isfinite(float(token)):
            state = "invalid_number"
        else:
            value = float(token)
            if value == 0 and Decimal(token) != 0:
                state, value = "numerical_range", None
            elif (unit == "probability" and not 0 <= value <= 1
                    or unit in {"insertion_sites", "insertion_count", "mean_insertion_count", "normalized_count"}
                    and aliases != ("Delta Mean",) and value < 0
                    or unit == "insertion_sites" and not value.is_integer()):
                state, value = "outside_native_range", None
    return dict(state=state, value=value, unit=unit, column_ordinals=indices, tokens=tokens)


def calculate_intervention_components(document):
    document = validate_intervention_document(document)
    native, representation = document["native_document"], document["representation"]
    fields = _RESAMPLING if representation == "transit_resampling" else _DESEQ if representation == "deseq2" else {}
    rows, issues = [], deepcopy(document["issues"])
    if native is not None:
        table = native["table"]
        for row in table["rows"]:
            metrics = {name: _metric(row, table["header"], aliases, unit)
                       for name, (aliases, unit) in fields.items()}
            if "standard_error" in metrics:
                se = metrics["standard_error"]
                if se["value"] is not None and se["value"] < 0:
                    se.update(value=None, state="outside_native_range")
                variance = None if se["state"] != "available" else se["value"] * se["value"]
                state = se["state"]
                if variance is not None and (not math.isfinite(variance) or variance == 0 and se["value"] != 0):
                    state, variance = "numerical_range", None
                metrics["effect_variance"] = dict(state=state, value=variance, unit="log2_ratio_squared",
                    column_ordinals=deepcopy(se["column_ordinals"]), tokens=deepcopy(se["tokens"]), formula="lfcSE^2")
            for name, metric in metrics.items():
                if metric["state"] != "available":
                    issues.append(_issue("native_metric_" + metric["state"], "/rows/" + str(row["row_ordinal"]) + "/" + name))
            rows.append(dict(row_ordinal=row["row_ordinal"], line_index=row["line_index"], metrics=metrics))
    return dict(version=COMPONENTS_VERSION, document_sha256=hashlib.sha256(_canonical(document)).hexdigest(),
        representation=representation, rows=rows, issues=issues,
        definitions=dict(effect="Native signed log2 ratio; retain the documented numerator, reference and pseudocount/normalization.",
            variance="DESeq2 lfcSE squared is estimated variance on the reported log2 scale; model applicability requires assessment.",
            probability="Native p and adjusted p are one contrast's related statistics, not independent evidence, variance or a function probability.",
            design="Feature identifiers do not identify the supplied sequence or establish the intervention. Join study, sample and contrast evidence explicitly.",
            other_tables="Other TRANSIT recipes, count matrices, sample metadata and quality reports retain native fields without inferred numerical meanings."))


def validate_intervention_components(value, document):
    """Read saved components; publication ContentBindings authenticate results.

    Validate associations and exact native operands without invoking the source
    parser or numerical calculator. This is not authority to publish new values.
    """
    _finite_json(value)
    _require(type(value) is dict and set(value) == {"version", "document_sha256", "representation", "rows", "issues", "definitions"}
        and value["version"] == COMPONENTS_VERSION and value["representation"] == document["representation"]
        and value["document_sha256"] == hashlib.sha256(_canonical(document)).hexdigest()
        and type(value["issues"]) is list and type(value["definitions"]) is dict)
    native = document["native_document"]
    rows = [] if native is None else native["table"]["rows"]
    _require(type(value["rows"]) is list and len(value["rows"]) == len(rows))
    fields = _RESAMPLING if document["representation"] == "transit_resampling" else _DESEQ if document["representation"] == "deseq2" else {}
    for saved, original in zip(value["rows"], rows, strict=True):
        _require(type(saved) is dict and set(saved) == {"row_ordinal", "line_index", "metrics"}
            and type(saved["row_ordinal"]) is int and saved["row_ordinal"] == original["row_ordinal"]
            and type(saved["line_index"]) is int and saved["line_index"] == original["line_index"]
            and type(saved["metrics"]) is dict
            and set(saved["metrics"]) == set(fields) | ({"effect_variance"} if "standard_error" in fields else set()))
        for name, metric in saved["metrics"].items():
            derived = name == "effect_variance"
            aliases, unit = fields["standard_error" if derived else name]
            indices = [i for i, col in enumerate(native["table"]["header"]) if col in aliases]
            tokens = [original["cells"][i] if i < len(original["cells"]) else None for i in indices]
            _require(type(metric) is dict and set(metric) == {"state", "value", "unit", "column_ordinals", "tokens"} | ({"formula"} if derived else set())
                and metric["column_ordinals"] == indices and metric["tokens"] == tokens
                and metric["unit"] == ("log2_ratio_squared" if derived else unit)
                and metric["state"] in {"available", "column_missing", "column_ambiguous", "missing", "invalid_number",
                    "row_width_conflict", "outside_native_range", "numerical_range"})
            _require((metric["value"] is None) == (metric["state"] != "available"))
            if derived:
                _require(metric["formula"] == "lfcSE^2")
            elif metric["state"] == "available":
                _require(len(tokens) == 1 and metric["value"] == (tokens[0] if unit == "identifier" else float(tokens[0])))
    return deepcopy(value)
