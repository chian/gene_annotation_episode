"""Pure master-sequence metadata from saved BLAST PSSM input sheets.

The master decoder and structural checks are shared with the numerical PSSM
calculator. This port retains all record identities and parser issues, decodes
only the native master relation, and performs no scoring, I/O or execution.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .blast_pssm_inputs import ISSUE_CODES, _issue


# Native code-index table; source pinned in the 306 PSSM contract.
_STDAA = "-ABCDEFGHIKLMNPQRSTVWXYZU*OJ"


def _finite_json(value):
    if type(value) is dict:
        return all(type(k) is str and _finite_json(v) for k, v in value.items())
    if type(value) is list:
        return all(_finite_json(v) for v in value)
    return value is None or type(value) in {str, int, bool} or type(value) is float and math.isfinite(value)


def _validate_sheet(sheet):
    keys = {"schema", "artifact_key", "source_ref", "format", "input_identity", "status", "native_text", "pssms", "issues"}
    records = {"record_ordinal", "pssm_key", "character_span", "native_type", "native_record", "native_pssm", "native_params", "issues"}
    if not _finite_json(sheet) or type(sheet) is not dict or set(sheet) != keys or sheet["schema"] != "blast_pssm_sheet_v1":
        raise ValueError("blast_pssm_sheet_invalid")
    if type(sheet["pssms"]) is not list or type(sheet["issues"]) is not list:
        raise ValueError("blast_pssm_sheet_invalid")
    seen = set()
    for row in sheet["pssms"]:
        if type(row) is not dict or set(row) != records or type(row["native_pssm"]) is not dict:
            raise ValueError("blast_pssm_record_invalid")
        ordinal = row["record_ordinal"]
        if type(ordinal) is not int or ordinal < 0 or ordinal in seen:
            raise ValueError("blast_pssm_record_identity_invalid")
        seen.add(ordinal)
        if row["pssm_key"] != json.dumps([sheet["artifact_key"], ordinal], ensure_ascii=False, separators=(",", ":")):
            raise ValueError("blast_pssm_record_identity_invalid")
        if type(row["native_record"]) is not dict or row["native_params"] is not None and type(row["native_params"]) is not dict:
            raise ValueError("blast_pssm_record_invalid")
        if type(row["issues"]) is not list or any(type(i) is not dict or i.get("code") not in ISSUE_CODES for i in row["issues"]):
            raise ValueError("blast_pssm_record_issues_invalid")


def _node_at(row, path):
    parts = re.findall(r"[^.\[\]]+", path)
    if row["native_type"] == "Pssm" and parts[:1] == ["pssm"]:
        parts.pop(0)
    node = row["native_record"]
    for part in parts:
        if node.get("kind") == "choice":
            if node.get("name") != part:
                return None
            node = node["value"]
        elif node.get("kind") == "group":
            if part.isdigit():
                items = node.get("items", [])
                if int(part) >= len(items):
                    return None
                node = items[int(part)]
            else:
                found = [v for v in node.get("items", []) if v.get("kind") == "choice" and v.get("name") == part]
                if len(found) != 1:
                    return None
                node = found[0]["value"]
        else:
            return None
    return node


def _add(row, issues, code, path):
    node = _node_at(row, path)
    issues.append(_issue(code, row["record_ordinal"], path,
                         node.get("character_span") if node is not None else None))


def _bad_field(row, path):
    # A malformed ancestor blocks its descendants, while independent siblings
    # survive. A truncated outer record alone does not erase complete arrays.
    for issue in row["issues"]:
        field = issue.get("field")
        if issue["code"] in {"asn_duplicate_field", "asn_field_type_invalid", "asn_field_truncated"} and field:
            if path == field or path.startswith(field + ".") or path.startswith(field + "["):
                return True
    return False


def _dimension(row, native):
    value = row["native_pssm"].get(native)
    return value if type(value) is int and value > 0 and not _bad_field(row, "pssm." + native) else None


def _protein(row):
    value = row["native_pssm"].get("isProtein", True)
    return value if type(value) is bool and not _bad_field(row, "pssm.isProtein") else None


def _plain_fields(value):
    if type(value) is not list or any(type(v) is not dict or len(v) != 1 for v in value):
        return None
    names = [next(iter(v)) for v in value]
    if len(set(names)) != len(names):
        return None
    return {k: v for item in value for k, v in item.items()}


def _master(row, result, columns, is_protein):
    master = {"status": "unavailable", "encoding": None, "reported_length": None,
              "decoded_length": None, "sequence": None, "column_to_residue": None}
    pssm, path = row["native_pssm"], "pssm.query"
    def fail(code, field=path, state="incompatible"):
        master["status"] = state
        _add(row, result["issues"], code, field)
        return master
    if "query" not in pssm:
        return fail("master_missing", state="unavailable")
    query = pssm["query"]
    if _bad_field(row, path) or type(query) is not dict or len(query) != 1:
        return fail("master_shape_invalid")
    if "set" in query:
        return fail("master_compound_unsupported", state="unavailable")
    if "seq" not in query:
        return fail("master_shape_invalid")
    seq = _plain_fields(query["seq"])
    inst = _plain_fields(seq.get("inst")) if seq is not None else None
    if inst is None or _bad_field(row, path + ".seq.inst"):
        return fail("master_shape_invalid", path + ".seq.inst")
    path += ".seq.inst"
    length = inst.get("length")
    if type(length) is int and length >= 0:
        master["reported_length"] = length
    if "repr" in inst and inst["repr"] != "raw":
        return fail("master_representation_unsupported", path + ".repr", "unavailable")
    if is_protein is not True or "mol" in inst and inst["mol"] != "aa":
        return fail("master_molecule_incompatible", path + ".mol")
    data = inst.get("seq-data")
    if type(data) is not dict or len(data) != 1:
        return fail("master_shape_invalid", path + ".seq-data")
    encoding, encoded = next(iter(data.items()))
    master["encoding"] = encoding
    if encoding == "ncbistdaa":
        if type(encoded) is not dict or encoded.get("encoding") != "hex" or type(encoded.get("token")) is not str:
            return fail("master_encoding_unsupported", path + ".seq-data", "unavailable")
        token = encoded["token"]
        if re.fullmatch(r"'[0-9A-Fa-f\s]*'[Hh]", token) is None:
            return fail("master_code_invalid", path + ".seq-data")
        try:
            codes = bytes.fromhex(token[1:-2])
        except ValueError:
            return fail("master_code_invalid", path + ".seq-data")
        if any(code >= len(_STDAA) for code in codes):
            return fail("master_code_invalid", path + ".seq-data")
        sequence = "".join(_STDAA[code] for code in codes)
    elif encoding in {"iupacaa", "ncbieaa"}:
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ" + ("-*" if encoding == "ncbieaa" else ""))
        if type(encoded) is not str or not set(encoded) <= allowed:
            return fail("master_code_invalid", path + ".seq-data")
        sequence = encoded
    else:
        return fail("master_encoding_unsupported", path + ".seq-data", "unavailable")
    master.update(sequence=sequence, decoded_length=len(sequence))
    if master["reported_length"] is None:
        return fail("master_length_missing", path + ".length", "unavailable")
    if _bad_field(row, path + ".length") or len(sequence) != length or columns != length:
        return fail("master_length_incompatible", path + ".length")
    master.update(status="complete", column_to_residue=[
        {"column": p, "master_position": None if symbol == "-" else p, "symbol": symbol}
        for p, symbol in enumerate(sequence)])
    return master


def extract_blast_pssm_master_metadata(sheet: dict) -> dict:
    """Extract each retained master without calculating model quantities.

    Record order and original ordinals remain unchanged. A decoded sequence is
    retained when lengths conflict, but only a complete native column relation
    has a map. Missing/unsupported native fields remain qualified records;
    malformed saved-sheet structure raises the calculator's existing ValueError.
    Every mutable output value is detached from the supplied saved sheet.
    """
    _validate_sheet(sheet)
    records, issues = [], deepcopy(sheet["issues"])
    for row in sheet["pssms"]:
        record = {"pssm_key": row["pssm_key"], "record_ordinal": row["record_ordinal"],
                  "master": None, "issues": deepcopy(row["issues"])}
        record["master"] = _master(row, record, _dimension(row, "numColumns"), _protein(row))
        records.append(record)
        for problem in record["issues"]:
            if problem not in issues:
                issues.append(deepcopy(problem))
    return {"schema": "blast_pssm_master_metadata_v1", "artifact_key": deepcopy(sheet["artifact_key"]),
            "source_ref": deepcopy(sheet["source_ref"]), "input_identity": deepcopy(sheet["input_identity"]),
            "records": records, "issues": issues}


__all__ = ["extract_blast_pssm_master_metadata"]
