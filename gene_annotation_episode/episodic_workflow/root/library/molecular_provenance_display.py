"""Original molecular provenance display for supplied decision information."""
from __future__ import annotations
from copy import deepcopy
import json


def _molecular_literal(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _molecular_provenance_role(reference, packet):
    if packet.get("version") == "ordinary_arsenic_speciation_values_v1":
        return "unavailable" if reference is None else "retained provenance"
    values = packet["values"]
    if reference is None:
        return "unavailable"
    for role in ("components", "sheet"):
        if reference == values["source_" + role + "_ref"]:
            return role
    return "retained provenance"


def _molecular_stored_view(cell, packet):
    """Replace only a declared provenance address, never a scientific value."""
    result = {key: deepcopy(value) for key, value in cell.items() if key not in ("source_ref", "unit_sources")}
    result["source_role"] = _molecular_provenance_role(cell["source_ref"], packet)
    if "unit_sources" in cell:
        result["unit_sources"] = [_molecular_stored_view(value, packet) for value in cell["unit_sources"]]
    return result


def _molecular_failure_view(issue, packet):
    result = {key: deepcopy(value) for key, value in issue.items() if key != "source_ref"}
    if issue.get("source_ref") is not None:
        result["source_role"] = issue.get("role") or _molecular_provenance_role(issue["source_ref"], packet)
    if (packet.get("version") in {"ordinary_protease_kinetics_values_v1", "ordinary_arsenic_speciation_values_v1",
            "ordinary_primer_placement_values_v1"}
            and result.get("diagnostic_ref") is not None):
        result.pop("diagnostic_ref")
        result["diagnostic_role"] = "retained diagnostic association"
    return result


