"""Supplied-byte scoremat ASN text and CLUSTAL master readers.

No search, conversion, model construction or acquisition happens here. The
scoremat grammar is NCBI's scoremat.asn at d4d56d4aa4fe16964e54c8c101fb1ec631ec6c05.
``native_record`` is an ordered syntax tree, including scalar tokens and
zero-based half-open *character* spans. A group is never guessed to be a dict:
SEQUENCE OF choices can legally repeat names (notably Bioseq.descr.source).
Only schema-known typed SEQUENCE parents are projected to field dictionaries.
REAL triples remain triples; decimal REAL tokens remain {"real_token": text}.
Unknown fields and unsupported encodings remain in the tree and native text.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
from io import StringIO
import json
import re

from Bio.AlignIO.ClustalIO import ClustalIterator


ISSUE_CODES = frozenset({
    "unsupported_format", "text_encoding_invalid", "empty_input",
    "asn_type_unsupported", "asn_syntax_invalid", "asn_truncated",
    "asn_trailing_data", "asn_field_type_invalid", "asn_duplicate_field",
    "asn_required_field_missing", "asn_data_missing", "asn_field_truncated",
    "msa_header_invalid", "msa_alignment_missing", "msa_multiple_alignments",
    "msa_row_invalid", "msa_inconsistent_widths", "msa_block_membership_invalid",
    "msa_invalid_alignment", "msa_duplicate_identifier", "msa_symbol_unsupported",
    "msa_master_out_of_range", "msa_master_empty",
    "sheet_invalid", "dimensions_invalid", "alphabet_unavailable",
    "row_labels_incompatible", "array_missing", "array_type_invalid",
    "array_length_incompatible", "array_order_unavailable", "integer_invalid",
    "real_invalid", "real_nonfinite", "real_unrepresentable", "real_underflow",
    "statistic_missing", "master_missing", "master_compound_unsupported",
    "master_shape_invalid", "master_encoding_unsupported", "master_code_invalid",
    "master_length_missing", "master_length_incompatible", "master_molecule_incompatible",
    "master_representation_unsupported",
})


def _issue(code, record_ordinal=None, field=None, span=None):
    if code not in ISSUE_CODES:
        raise ValueError("unknown_blast_pssm_issue")
    return {"code": code, "record_ordinal": record_ordinal, "field": field,
            "character_span": deepcopy(span)}


def _input(contents, format, artifact_key, source_ref):
    if type(contents) is not bytes:
        raise TypeError("blast_pssm_contents_bytes_required")
    if any(type(v) is not str or not v for v in (format, artifact_key, source_ref)):
        raise ValueError("blast_pssm_input_identity_invalid")
    identity = {"sha256": hashlib.sha256(contents).hexdigest(), "size_bytes": len(contents)}
    try:
        return identity, contents.decode("utf-8"), []
    except UnicodeError:
        return identity, None, [_issue("text_encoding_invalid")]


_LEXEME = re.compile(r'::=|[{},]|"(?:[^\"]|\"\")*"|\'[^\']*\'[HhBb]|'
                    r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?|'
                    r'[A-Za-z][A-Za-z0-9_-]*')


def _tokens(text):
    result, pos = [], 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        if text.startswith("--", pos):
            end = text.find("\n", pos + 2)
            end = len(text) if end < 0 else end
            closed = text.find("--", pos + 2, end)
            pos = closed + 2 if closed >= 0 else end
            continue
        match = _LEXEME.match(text, pos)
        if not match:
            # Keep complete preceding records, and diagnose the exact bad token.
            end = len(text) if text[pos] in "\"'" else pos + 1
            result.append(("invalid", text[pos:end], pos, end))
            pos = end
            continue
        raw = match[0]
        kind = (raw if raw in ("{", "}", ",", "::=") else
                "string" if raw.startswith('"') else "encoded" if raw.startswith("'") else
                "integer" if re.fullmatch(r"[+-]?[0-9]+", raw) else
                "real" if re.match(r"[+\-.0-9]", raw) else "identifier")
        result.append((kind, raw, pos, match.end()))
        pos = match.end()
    return result


class _Syntax(ValueError):
    def __init__(self, code, span, partial=None):
        self.code, self.span, self.partial = code, span, partial


class _Reader:
    def __init__(self, tokens, end):
        self.tokens, self.end, self.i = tokens, end, 0

    def value(self):
        if self.i == len(self.tokens):
            raise _Syntax("asn_truncated", [self.end, self.end])
        kind, raw, start, end = self.tokens[self.i]
        self.i += 1
        if kind == "{":
            node = {"kind": "group", "items": [], "complete": False,
                    "character_span": [start, self.end]}
            try:
                if self.i < len(self.tokens) and self.tokens[self.i][0] == "}":
                    node["complete"] = True
                    node["character_span"][1] = self.tokens[self.i][3]
                    self.i += 1
                    return node
                while True:
                    try:
                        node["items"].append(self.value())
                    except _Syntax as error:
                        if error.partial is not None:
                            node["items"].append(error.partial)
                        raise
                    if self.i == len(self.tokens):
                        raise _Syntax("asn_truncated", [self.end, self.end])
                    token = self.tokens[self.i]
                    self.i += 1
                    if token[0] == "}":
                        node["complete"] = True
                        node["character_span"][1] = token[3]
                        return node
                    if token[0] != ",":
                        raise _Syntax("asn_syntax_invalid", [token[2], token[3]])
            except _Syntax as error:
                raise _Syntax(error.code, error.span, node) from None
        if kind == "identifier" and raw not in {"TRUE", "FALSE", "NULL"}:
            if self.i < len(self.tokens) and self.tokens[self.i][0] not in {",", "}", "::="}:
                try:
                    child = self.value()
                except _Syntax as error:
                    partial = None if error.partial is None else {
                        "kind": "choice", "name": raw, "value": error.partial,
                        "character_span": [start, error.partial["character_span"][1]]}
                    raise _Syntax(error.code, error.span, partial) from None
                return {"kind": "choice", "name": raw, "value": child,
                        "character_span": [start, child["character_span"][1]]}
        if kind in {"}", ",", "::=", "invalid"}:
            code = "asn_truncated" if kind == "invalid" and raw.startswith(('"', "'")) else "asn_syntax_invalid"
            raise _Syntax(code, [start, end])
        value = raw
        if kind == "integer":
            try:
                value = int(raw)
            except ValueError:
                raise _Syntax("asn_syntax_invalid", [start, end]) from None
        elif kind == "string":
            value = raw[1:-1].replace('""', '"')
        elif raw in {"TRUE", "FALSE"}:
            kind, value = "boolean", raw == "TRUE"
        elif raw == "NULL":
            kind, value = "null", None
        return {"kind": kind, "value": value, "token": raw, "character_span": [start, end]}


def _native_value(node):
    """Lossless ordering for untyped groups; no repeated-choice collapse."""
    if node["kind"] == "group":
        return [_native_value(v) for v in node["items"]]
    if node["kind"] == "choice":
        return {node["name"]: _native_value(node["value"])}
    if node["kind"] == "real":
        return {"real_token": node["token"]}
    if node["kind"] == "encoded":
        return {"encoding": "hex" if node["token"][-1].upper() == "H" else "bits",
                "token": node["token"]}
    return node["value"]


# Every entry describes a real typed SEQUENCE from scoremat.asn. These are
# decoding types, not grading rules. Unlisted extension fields remain retained.
_TYPES = {
    "envelope": {"pssm": "pssm", "params": "params"},
    "pssm": {"isProtein": "boolean", "identifier": "any", "numRows": "integer",
             "numColumns": "integer", "rowLabels": "array:string", "byRow": "boolean",
             "query": "any", "finalData": "final", "intermediateData": "intermediate"},
    "final": {"scores": "array:integer", "lambda": "real", "kappa": "real", "h": "real",
              "scalingFactor": "integer", "lambdaUngapped": "real", "kappaUngapped": "real",
              "hUngapped": "real", "wordScoreThreshold": "real"},
    "intermediate": {"resFreqsPerPos": "array:integer", "weightedResFreqsPerPos": "array:real",
                     "freqRatios": "array:real", "informationContent": "array:real",
                     "gaplessColumnWeights": "array:real", "sigma": "array:real",
                     "intervalSizes": "array:integer", "numMatchingSeqs": "array:integer",
                     "numIndeptObsr": "array:real"},
    "params": {"pseudocount": "integer", "rpsdbparams": "rps", "constraints": "core",
               "bitScoreThresh": "real", "bitScoreReportingThresh": "real",
               "annotatedSites": "array:site"},
    "rps": {"matrixName": "string", "gapOpen": "integer", "gapExtend": "integer"},
    "core": {"nblocks": "integer", "blocks": "array:block", "loops": "array:loop",
             "isDiscontinuous": "boolean", "insertions": "array:integer"},
    "block": {"start": "integer", "stop": "integer", "minstart": "integer",
              "maxstop": "integer", "property": "array:property"},
    "property": {"type": "any", "intvalue": "integer", "textvalue": "string"},
    "loop": {"minlength": "integer", "maxlength": "integer"},
    "site": {"startPosition": "integer", "stopPosition": "integer", "description": "string",
             "type": "integer", "aliases": "array:string", "motif": "string", "motifuse": "integer"},
    "bioseq": {"id": "any", "descr": "any", "inst": "inst", "annot": "any"},
    "inst": {"repr": "any", "mol": "any", "length": "integer", "fuzz": "any",
             "topology": "any", "strand": "any", "seq-data": "any", "ext": "any", "hist": "any"},
    "bioseq-set": {"id": "any", "coll": "any", "level": "integer", "class": "any",
                   "release": "string", "date": "any", "descr": "any", "seq-set": "any", "annot": "any"},
}
_REQUIRED = {"envelope": ("pssm",), "pssm": ("numRows", "numColumns"),
             "final": ("scores", "lambda", "kappa", "h"), "intermediate": ("freqRatios",)}


def _fields(node, typename, ordinal, path, issues):
    if node["kind"] != "group":
        issues.append(_issue("asn_field_type_invalid", ordinal, path, node["character_span"]))
        return {}
    values, occurrences = {}, {}
    for entry in node["items"]:
        if entry["kind"] != "choice":
            issues.append(_issue("asn_field_type_invalid", ordinal, path, entry["character_span"]))
            continue
        name = entry["name"]
        field = f"{path}.{name}" if path else name
        value = _typed_value(entry["value"], _TYPES[typename].get(name, "any"), ordinal, field, issues)
        occurrences.setdefault(name, []).append(value)
        if len(occurrences[name]) > 1:
            issues.append(_issue("asn_duplicate_field", ordinal, field, entry["character_span"]))
            values[name] = {"duplicate_fields": deepcopy(occurrences[name])}
        else:
            values[name] = value
    for name in _REQUIRED.get(typename, ()):
        if name not in values:
            issues.append(_issue("asn_required_field_missing", ordinal,
                                 f"{path}.{name}" if path else name, node["character_span"]))
    if typename == "pssm":
        if "finalData" not in values and "intermediateData" not in values:
            issues.append(_issue("asn_data_missing", ordinal, path, node["character_span"]))
        for entry in node["items"]:
            if entry.get("name") == "query":
                _check_query(entry["value"], ordinal, f"{path}.query", issues)
    return values


def _typed_value(node, typename, ordinal, path, issues):
    if typename in _TYPES:
        return _fields(node, typename, ordinal, path, issues)
    if typename.startswith("array:"):
        if node["kind"] == "group":
            if not node["complete"]:
                issues.append(_issue("asn_field_truncated", ordinal, path, node["character_span"]))
            return [_typed_value(v, typename[6:], ordinal, f"{path}[{i}]", issues)
                    for i, v in enumerate(node["items"])]
    elif typename == "any":
        return _native_value(node)
    elif typename == "real":
        # Numerical validation/conversion belongs to the separate calculator.
        return _native_value(node)
    elif node["kind"] == typename:
        return node["value"]
    issues.append(_issue("asn_field_type_invalid", ordinal, path, node["character_span"]))
    return _native_value(node)


def _check_query(node, ordinal, path, issues):
    if node["kind"] != "choice":
        issues.append(_issue("asn_field_type_invalid", ordinal, path, node["character_span"]))
        return
    if node["name"] in {"seq", "set"}:
        _fields(node["value"], "bioseq" if node["name"] == "seq" else "bioseq-set",
                ordinal, path + "." + node["name"], issues)
        if node["name"] == "set" and node["value"]["kind"] == "group":
            for field in node["value"]["items"]:
                if field.get("name") == "seq-set" and field["value"]["kind"] == "group":
                    for i, item in enumerate(field["value"]["items"]):
                        _check_query(item, ordinal, f"{path}.set.seq-set[{i}]", issues)


def read_blast_pssm(contents: bytes, *, format: str, artifact_key: str, source_ref: str) -> dict:
    """Retain supplied scoremat text; populate native measurements, without defaults."""
    identity, text, issues = _input(contents, format, artifact_key, source_ref)
    sheet = {"schema": "blast_pssm_sheet_v1", "artifact_key": artifact_key, "source_ref": source_ref,
             "format": format, "input_identity": identity, "status": "unavailable",
             "native_text": text, "pssms": [], "issues": issues}
    if format != "scoremat_asn_text":
        issues.append(_issue("unsupported_format", field="format"))
        return sheet
    if text is None:
        return sheet
    tokens = _tokens(text)
    if not tokens:
        issues.append(_issue("empty_input"))
        return sheet
    starts = [i for i, t in enumerate(tokens[:-1]) if t[0] == "identifier" and tokens[i + 1][0] == "::="]
    if not starts:
        issues.append(_issue("asn_syntax_invalid", span=[tokens[0][2], tokens[-1][3]]))
        sheet["status"] = "incompatible"
        return sheet
    if starts[0]:
        issues.append(_issue("asn_trailing_data", span=[tokens[0][2], tokens[starts[0]][2]]))
    for ordinal, first in enumerate(starts):
        last = starts[ordinal + 1] if ordinal + 1 < len(starts) else len(tokens)
        stop = tokens[last][2] if last < len(tokens) else len(text)
        native_type = tokens[first][1]
        if native_type not in {"PssmWithParameters", "Pssm"}:
            issues.append(_issue("asn_type_unsupported", ordinal, "$record", [tokens[first][2], stop]))
            continue
        local = []
        reader = _Reader(tokens[first + 2:last], stop)
        try:
            node = reader.value()
        except _Syntax as error:
            node = error.partial
            local.append(_issue(error.code, ordinal, "$record", error.span))
        else:
            if reader.i < len(reader.tokens):
                local.append(_issue("asn_trailing_data", ordinal, "$record",
                                    [reader.tokens[reader.i][2], stop]))
        if node is None:
            issues.extend(local)
            continue
        decoded = _fields(node, "envelope" if native_type == "PssmWithParameters" else "pssm",
                          ordinal, "" if native_type == "PssmWithParameters" else "pssm", local)
        pssm = decoded.get("pssm", {}) if native_type == "PssmWithParameters" else decoded
        sheet["pssms"].append({"record_ordinal": ordinal,
            "pssm_key": json.dumps([artifact_key, ordinal], ensure_ascii=False, separators=(",", ":")),
            "character_span": [tokens[first][2], node["character_span"][1]],
            "native_type": native_type, "native_record": node,
            "native_pssm": pssm if type(pssm) is dict else {},
            "native_params": decoded.get("params") if native_type == "PssmWithParameters" else None,
            "issues": local})
        issues.extend(deepcopy(local))
    sheet["status"] = ("partial" if issues else "complete") if sheet["pssms"] else "incompatible"
    return sheet


def _clustal_checks(text, issues):
    """Validate block geometry before the existing iterator; never assemble rows."""
    lines = text.splitlines(keepends=True)
    if not lines or not re.match(r"^CLUSTAL(?:\s|$)", lines[0]):
        issues.append(_issue("msa_header_invalid", field="header", span=[0, len(lines[0]) if lines else 0]))
        return False
    blocks, active, offset = [], [], len(lines[0])
    for line in lines[1:]:
        span = [offset, offset + len(line)]
        offset += len(line)
        if line.startswith("CLUSTAL"):
            issues.append(_issue("msa_multiple_alignments", field="records", span=span))
            return False
        if not line.strip():
            if active:
                blocks.append(active)
                active = []
            continue
        if line[0].isspace() and set(line.strip()) <= set("*:. \t"):
            continue
        parts = line.split()
        if len(parts) not in {2, 3} or len(parts) == 3 and not parts[2].isdigit():
            issues.append(_issue("msa_row_invalid", field="records", span=span))
            continue
        active.append((parts[0], len(parts[1]), span))
    if active:
        blocks.append(active)
    if not blocks:
        issues.append(_issue("msa_alignment_missing", field="records"))
        return False  # ClustalIterator's empty-header loop must not be entered.
    members = [v[0] for v in blocks[0]]
    for block in blocks:
        if len({v[1] for v in block}) != 1:
            issues.append(_issue("msa_inconsistent_widths", field="records", span=block[0][2]))
        if [v[0] for v in block] != members:
            issues.append(_issue("msa_block_membership_invalid", field="records", span=block[0][2]))
    return not issues


def read_blast_msa_master(contents: bytes, *, format: str, artifact_key: str,
                          source_ref: str, master_record_ordinal: int,
                          ignore_master_for_profile: bool) -> dict:
    """Preserve CLUSTAL row membership and map every original master column.

The selected ordinal is zero-based and resolved by the caller. Only '-' is a
gap in the retained native PSI master contract. Case never alters coordinates.
The ignore flag is retained; it does not remove the master or emulate weighting.
"""
    if type(master_record_ordinal) is not int or master_record_ordinal < 0:
        raise ValueError("blast_msa_nonnegative_master_ordinal_required")
    if type(ignore_master_for_profile) is not bool:
        raise ValueError("blast_msa_boolean_ignore_flag_required")
    identity, text, issues = _input(contents, format, artifact_key, source_ref)
    sheet = {"schema": "blast_msa_master_sheet_v1", "artifact_key": artifact_key,
             "source_ref": source_ref, "format": format, "input_identity": identity,
             "status": "unavailable", "native_text": text, "records": [],
             "master_record_ordinal": master_record_ordinal,
             "ignore_master_for_profile": ignore_master_for_profile,
             "alignment_columns": None, "master_column_map": [], "issues": issues}
    if format != "clustal":
        issues.append(_issue("unsupported_format", field="format"))
        return sheet
    if text is None:
        return sheet
    if not _clustal_checks(text, issues):
        sheet["status"] = "incompatible"
        return sheet
    try:
        alignments = list(ClustalIterator(StringIO(text)))
    except (ValueError, AssertionError, IndexError, StopIteration):
        issues.append(_issue("msa_invalid_alignment", field="records"))
        sheet["status"] = "incompatible"
        return sheet
    if len(alignments) != 1:
        issues.append(_issue("msa_alignment_missing" if not alignments else "msa_multiple_alignments", field="records"))
        sheet["status"] = "incompatible"
        return sheet
    for ordinal, record in enumerate(alignments[0]):
        sequence = str(record.seq)
        sheet["records"].append({"record_ordinal": ordinal, "identifier": record.id,
            "aligned_sequence": sequence, "ungapped_sequence": sequence.replace("-", "")})
        if re.fullmatch(r"[A-Za-z-]+", sequence) is None:
            issues.append(_issue("msa_symbol_unsupported", ordinal, "aligned_sequence"))
    counts = Counter(r["identifier"] for r in sheet["records"])
    for record in sheet["records"]:
        if counts[record["identifier"]] > 1:
            issues.append(_issue("msa_duplicate_identifier", record["record_ordinal"], "identifier"))
    sheet["alignment_columns"] = alignments[0].get_alignment_length()
    if master_record_ordinal >= len(sheet["records"]):
        issues.append(_issue("msa_master_out_of_range", master_record_ordinal, "master_record_ordinal"))
    else:
        master = sheet["records"][master_record_ordinal]["aligned_sequence"]
        position = 0
        for column, symbol in enumerate(master):
            sheet["master_column_map"].append({"alignment_column": column,
                "master_position": None if symbol == "-" else position,
                "symbol": symbol, "uppercase_selected": "A" <= symbol <= "Z"})
            position += symbol != "-"
        if not position:
            issues.append(_issue("msa_master_empty", master_record_ordinal, "aligned_sequence"))
    sheet["status"] = "incompatible" if issues else "complete"
    return sheet


__all__ = ["read_blast_pssm", "read_blast_msa_master"]
