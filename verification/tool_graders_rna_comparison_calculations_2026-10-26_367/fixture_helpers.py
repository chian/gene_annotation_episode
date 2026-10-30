"""Invented arithmetic fixtures only: no native execution or measurements.

The recognized identities simulate already-authenticated software inputs for
testing the accepted versioned proof. They do not authenticate these fixtures.
"""
from copy import deepcopy
import importlib

_inputs = importlib.import_module("verification.tool_graders_rna_comparison_inputs_2026-10-26_366.fixture_helpers")
from gene_annotation_episode.rna_structure_comparison_contracts import (
    OTHER_SCALAR_SETTING_NAMES, ARRAY_SETTING_NAMES, comparison_digest,
)
from gene_annotation_episode.rna_structure_comparison_inputs import populate_rna_comparison_sheet

parameters = _inputs.parameters
member = _inputs.member
descriptor = _inputs.descriptor
absent = _inputs.absent
failure = _inputs.failure
site = _inputs.site
comparison = _inputs.comparison
energy_request = _inputs.energy_request
selector = _inputs.selector
scan_request = _inputs.scan_request


def feature(key="WT", sequence="GGGAAACCC", structure="(((...)))", *, energy=None, **kwargs):
    result = _inputs.feature(key, sequence, structure, energy=energy, **kwargs)
    if result["model"] is not None:
        result["model"]["other_observed_settings"] = [
            {"name": name, "state": "observed", "value": "F" if name == "backtrack_type" else
                "" if name == "nonstandards" else 0} for name in OTHER_SCALAR_SETTING_NAMES
        ] + [{"name": name, "state": "unavailable", "value": None} for name in ARRAY_SETTING_NAMES]
    return result


def software():
    return {"python_executable": "/invented/fixture/python", "python_sha256": "0" * 64,
        "python_version": "invented-fixture", "worker_module": "gene_annotation_episode.native_rna_structure_worker",
        "worker_source_sha256": "d1c2e045856aa235e14ef5e7807139243e4e184d26d5978ce046726269f9d0c7",
        "rna_module_sha256": "3d136533fd55f2ca6bb4cbb7428004b5da2e79c8cee53aef76c6662624d91946",
        "rna_extension_sha256": "451e5ac69fba96b9d9a0640d1311b844962a1f97143d050446ebd459dfd0494d",
        "viennarna_distribution_version": "2.7.0"}


def supplied(sheet, *, pins=True):
    return {"original_sheet": sheet, "original_bundle_software": software() if pins else None, "received_failure": None}


def blank():
    return {"original_sheet": None, "original_bundle_software": None, "received_failure": None}


def pair(a=None, b=None, *, correspondence="auto", selections=None, pairs=True, energy=None):
    a = feature() if a is None else a
    b = feature("V", "GGGAAAUCC") if b is None else b
    if correspondence == "auto":
        aa = a["analysis_sequence"]["analysis_sequence"]
        bb = b["analysis_sequence"]["analysis_sequence"]
        correspondence = {"kind": "substitution_only", "substitutions": [
            {"index": i, "baseline_symbol": left, "variant_symbol": right}
            for i, (left, right) in enumerate(zip(aa, bb)) if left != right]}
    if selections is None:
        selections = [site(member_id=a["record_key"], intervals=[(0, len(a["structure"]["dot_bracket"]))])]
    selected = selector([member(a), member(b)], [comparison(b["record_key"], correspondence=correspondence,
        selections=selections, pairs=pairs, energy=energy)], baseline=a["record_key"])
    return populate_rna_comparison_sheet(selected, operands={a["record_key"]: supplied(a), b["record_key"]: supplied(b)})


def complete(columns):
    return {"kind": "supplied_complete_alignment", "authority": {"kind": "parent_assignment", "source_ref": None},
        "columns": [{"column": i, "baseline_index": a, "variant_index": b} for i, (a, b) in enumerate(columns)]}


def partial(matches):
    return {"kind": "supplied_partial_correspondence", "authority": {"kind": "parent_assignment", "source_ref": None},
        "matches": [{"baseline_index": a, "variant_index": b} for a, b in matches]}


def scan(energies=(-4.0, -5.0, -4.0, -3.0), *, failed=True, aliases=True, tolerance=None,
        normalization="none", extra_members=(), extra_operands=None):
    names = ["WT", "A", "B", "C"][:len(energies)]
    sequences = ["GGGAAACCC", "GGGAAAUCC", "GGGAAACCU", "GGGAAUCCC"]
    sheets = [feature(name, seq, energy=energy) for name, seq, energy in zip(names, sequences, energies)]
    members = [member(s) for s in sheets]
    operands = {s["record_key"]: supplied(s) for s in sheets}
    if failed:
        failed_row = failure("D")
        members.append({"member_id": "D", "kind": "received_failure", "failure": failed_row})
        operands["D"] = {**blank(), "received_failure": failed_row}
    if aliases and "A" in names:
        members.append({"member_id": "AliasA", "kind": "alias", "canonical_member_id": "A"})
    members.extend(deepcopy(extra_members))
    operands.update(deepcopy(extra_operands or {}))
    energy = energy_request(tolerance, normalization)
    comparisons = [comparison(m["member_id"], energy=energy) for m in members if m["member_id"] != "WT" and m["kind"] != "alias"]
    return populate_rna_comparison_sheet(selector(members, comparisons, scan=scan_request(energy)), operands=operands)


def rebuild(sheet, *, operands=None, question=None):
    if operands is None:
        operands = {o["member_id"]: {k: deepcopy(o[k]) for k in ("original_sheet", "original_bundle_software", "received_failure")}
            for o in sheet["operands"] if o["state"] != "alias"}
    q = deepcopy(sheet["selected_question"] if question is None else question)
    # Retain a matching synthetic descriptor after deliberately changing input.
    for m in q["membership"]:
        if m["kind"] == "saved_sheet":
            m["saved_input"] = descriptor(operands[m["member_id"]]["original_sheet"])
    selected = {"version": "native_rna_structure_comparison_selector_v1", "acquisition": "retained_inputs_only",
        "question": q, "parameters": deepcopy(sheet["parameters"]), "projections": [{"projection_id": "structure",
            "family": "structures", "member_ids": [q["baseline_member_id"]], "fields": ["dot_bracket"]}]}
    return populate_rna_comparison_sheet(selected, operands=operands)


def cells(rows, selection=None):
    return {c["metric"]: c for c in rows if c["selection_id"] == selection}


def values(rows, selection=None):
    return {name: cell["value"] for name, cell in cells(rows, selection).items()}
