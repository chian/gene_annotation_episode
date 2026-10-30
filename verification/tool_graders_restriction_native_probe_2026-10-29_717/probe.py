"""One explicit five-context native-format probe; no production binding.

All scientific imports and calls happen inside the selected bounded529 check.
No matching algorithm, numerical grader, acquisition or episode loop lives here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import warnings


def file_pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": path.stat().st_size}


def _json_value(value):
    """Preserve native tuple/pattern types rather than invent scientific values."""
    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, tuple):
        return {"native_type": "tuple", "items": [_json_value(v) for v in value]}
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if hasattr(value, "pattern") and hasattr(value, "flags"):
        return {"native_type": type(value).__name__, "pattern": value.pattern, "flags": value.flags}
    raise TypeError("unretained_native_catalog_type:" + type(value).__name__)


def _catalog_row(enzyme, dictionary):
    # Fields retain native meanings, including unknown/null cut geometry and
    # a diagram string that is explicitly separate from the recognition motif.
    values = {name: _json_value(getattr(enzyme, name, None)) for name in (
        "site", "size", "fst5", "fst3", "scd5", "scd3", "ovhg", "ovhgseq",
        "id", "uri", "charac", "suppl", "freq", "substrat", "compsite")}
    diagram, error = None, None
    try:
        diagram = enzyme.elucidate()
    except Exception as failure:
        error = {"class": type(failure).__name__, "message": str(failure)}
    return {"name": str(enzyme), "native_attributes": values,
        "cut_diagram": diagram, "cut_diagram_failure": error,
        "native_class_bases": [base.__name__ for base in enzyme.__bases__],
        "native_class_mro": [base.__name__ for base in enzyme.__mro__],
        "dictionary_entry": _json_value(dictionary[str(enzyme)])}


def _write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def run_probe(destination):
    """Execute the five already specified contexts, once, saving each outcome.

    A nonempty destination is refused. All five contexts are selected in
    advance; later assertions cannot trigger another native call.
    """
    from Bio import Restriction, __version__ as biopython_version
    from Bio.Restriction import Restriction_Dictionary
    from Bio.Seq import Seq

    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    native_module = __import__("Bio.Restriction.Restriction", fromlist=["RestrictionBatch"])
    dictionary = Restriction_Dictionary.rest_dict
    motif = Restriction.BcgI.site
    constructed = "A" * 50 + motif.replace("N", "A") + "A" * 50
    inputs = [
        ("ecori_linear_internal", "AAAAGAATTCTTTT", True, "explicit", ["EcoRI"]),
        ("ecori_linear_origin", "AATTCAAAAG", True, "explicit", ["EcoRI"]),
        ("ecori_circular_origin", "AATTCAAAAG", False, "explicit", ["EcoRI"]),
        ("bcgi_linear_two_cuts", constructed, True, "explicit", ["BcgI"]),
        ("commercial_linear_internal", "AAAAGAATTCTTTT", True, "commercial_native_batch", None),
    ]
    report = {"version": "restriction_native_probe_v1", "biopython_version": biopython_version,
        "dictionary_file": file_pin(Restriction_Dictionary.__file__),
        "native_module_file": file_pin(native_module.__file__),
        "interpretation": "native_sequence_predictions_conditional_on_selected_input_catalog_and_topology",
        "batch_search_call_count": 0, "additional_finditer_call_count": 0,
        "new_matching_implementation": False, "cases": []}
    _write_new(destination / "selected-inputs.json", {"inputs": inputs,
        "bcgi_construction": {"native_motif": motif, "replacement": {"N": "A"},
            "left_flank": "A" * 50, "right_flank": "A" * 50}})
    for ordinal, (name, sequence, linear, population, names) in enumerate(inputs):
        batch = Restriction.RestrictionBatch(names) if names is not None else Restriction.CommOnly
        members = list(batch)
        raw = sequence.encode("utf-8")
        case = {"case_ordinal": ordinal, "case_name": name,
            "selected_sequence": {"sequence": sequence, "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw), "length_nt": len(sequence), "normalization": "none_input_already_uppercase"},
            "topology": "linear" if linear else "circular", "linear_argument": linear,
            "population_kind": population, "requested_enzyme_names": names,
            "resolved_enzyme_names": sorted(str(enzyme) for enzyme in members),
            "native_batch_member_order": [str(enzyme) for enzyme in members],
            "native_batch_already_mapped_before": _json_value(batch.already_mapped),
            "catalog": [], "warnings": [], "exception": None, "result": None}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            case["catalog"] = [_catalog_row(enzyme, dictionary) for enzyme in members]
            try:
                report["batch_search_call_count"] += 1
                native = batch.search(Seq(sequence), linear=linear)
                case["result"] = {"native_mapping_order": [str(enzyme) for enzyme in native],
                    "rows": [{"enzyme_name": str(enzyme),
                        "native_cut_positions_1based": list(positions),
                        "native_position_meaning": "native_search_positions_cut_geometry_unknown"
                            if "NoCut" in [base.__name__ for base in enzyme.__mro__]
                            else "native_first_base_after_cut_1based",
                        "native_on_minus_before_drop": list(enzyme.on_minus)
                            if "NonPalindromic" in [base.__name__ for base in enzyme.__mro__]
                                and hasattr(enzyme, "on_minus") else None}
                        for enzyme, positions in native.items()],
                    "native_batch_already_mapped_after": _json_value(batch.already_mapped)}
            except Exception as failure:
                case["exception"] = {"class": type(failure).__name__, "message": str(failure)}
            case["warnings"] = [{"category_module": warning.category.__module__,
                "category_name": warning.category.__name__, "message": str(warning.message),
                "filename": warning.filename, "lineno": warning.lineno} for warning in caught]
        _write_new(destination / f"case-{ordinal:02d}.json", case)
        report["cases"].append(case)
    _write_new(destination / "native-probe.json", report)
    return report
