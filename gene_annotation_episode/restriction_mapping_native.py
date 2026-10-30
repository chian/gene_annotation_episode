"""One selected Bio.Restriction search with source-observed native records.

This Store-free primitive has no resource, retry or continuation decisions.
Its caller supplies the bounded process and retains the returned native record.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import threading
import warnings

from .restriction_mapping_contracts import (
    restriction_canonical, restriction_issue, validate_restriction_record,
)


_LOCK = threading.RLock()
_ABSENT = object()
_DNA = frozenset("ACGTRYSWKMBDHVN")


def _exception(error):
    return {"module": type(error).__module__, "class": type(error).__name__, "message": str(error)}


def _pin(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        while block := stream.read(1024 * 1024):
            digest.update(block)
        after = os.fstat(stream.fileno())
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if stamp(before) != stamp(after):
        raise ValueError("restriction_native_source_changed")
    return {"path": str(path), "sha256": digest.hexdigest(), "size_bytes": before.st_size}


def _pattern(value):
    return {"text": value.pattern, "flags": value.flags} if hasattr(value, "pattern") else {
        "text": value, "flags": None}


def _json_value(value):
    if value is None or type(value) in (str, int, float, bool):
        return value
    if isinstance(value, tuple):
        return {"native_type": "tuple", "items": [_json_value(v) for v in value]}
    if isinstance(value, list):
        return [_json_value(v) for v in value]
    if isinstance(value, dict) and all(type(k) is str for k in value):
        return {k: _json_value(v) for k, v in value.items()}
    if hasattr(value, "pattern") and hasattr(value, "flags"):
        return {"native_type": type(value).__name__, "pattern": value.pattern, "flags": value.flags}
    raise ValueError("restriction_native_catalog_type_unavailable")


def _match_rows(matches):
    return [{"match_ordinal": i, "native_start_1based": start,
        "groups": [{"name": name, "text": text}
            for name, text in group.__self__.groupdict().items()]}
        for i, (start, group) in enumerate(matches)]


def _catalog_row(enzyme, ordinal, dictionary):
    mro = [base.__name__ for base in enzyme.__mro__]
    cut = next((label for cls, label in (("NoCut", "no_cut"), ("TwoCuts", "two_cuts"),
                ("OneCut", "one_cut")) if cls in mro), "unknown")
    symmetry = next((label for cls, label in (("Palindromic", "palindromic"),
                ("NonPalindromic", "nonpalindromic")) if cls in mro), "unknown")
    meaning = ("recognition_start_1based" if cut == "no_cut" else
               "first_base_after_cut_1based" if cut in ("one_cut", "two_cuts") else "unknown")
    text, error = None, None
    try:
        text = enzyme.elucidate()
    except Exception as failure:
        error = _exception(failure)
    return validate_restriction_record("CatalogRow", dict(ordinal=ordinal, name=str(enzyme),
        native_site=enzyme.site, size_nt=enzyme.size, elucidate_text=text, elucidate_error=error,
        fst5=enzyme.fst5, fst3=enzyme.fst3, scd5=enzyme.scd5, scd3=enzyme.scd3,
        native_ovhg=enzyme.ovhg, native_pattern=_pattern(enzyme.compsite), native_class_mro=mro,
        cut_kind=cut, symmetry=symmetry, position_meaning=meaning, is_commercial=bool(enzyme.is_comm()),
        rebase_id=enzyme.id, rebase_uri=enzyme.uri,
        dictionary_entry_json=restriction_canonical(_json_value(dictionary[str(enzyme)]))))


def _empty(sequence, binding, selection, topology):
    return {"version": "restriction_mapping_native_v1", "request": {
        "sequence": sequence, "normalized_sequence": sequence.upper(), "sequence_binding": binding,
        "enzyme_selection": selection, "topology": topology}, "software": {
        "biopython_version": None, "dictionary_file": None, "native_source_file": None},
        "catalog": None, "formatted_sequence": None, "native_batch_member_order": [],
        "batch_state": "not_started", "native_mapping_order": None, "enzyme_searches": [],
        "match_observations": [], "warnings": [], "issues": [], "exception": None}


def run_restriction_mapping(sequence, *, sequence_binding, enzyme_selection, topology):
    """Observe one original native batch; never repeat it to obtain metadata.

    The lock protects this primitive's use of Bio's mutable enzyme classes.
    It does not serialize episodes, choose resources or impose a time limit.
    """
    binding = validate_restriction_record("SequenceBinding", sequence_binding)
    selection = validate_restriction_record("EnzymeSelection", enzyme_selection)
    if type(sequence) is not str or type(topology) is not str or topology not in ("linear", "circular"):
        raise ValueError("restriction_input_invalid")
    result = _empty(sequence, binding, selection, topology)
    if not sequence or not sequence.isascii() or not set(sequence.upper()) <= _DNA:
        result["issues"].append(restriction_issue("input_invalid", "input"))
        return validate_restriction_record("NativeResult", result)
    if (binding["length_nt"] != len(sequence)
            or binding["content_sha256"] != hashlib.sha256(sequence.encode("utf-8")).hexdigest()):
        result["issues"].append(restriction_issue("sequence_binding_conflict", "input"))
        return validate_restriction_record("NativeResult", result)
    with _LOCK:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                _run(result)
            except Exception as error:
                result["exception"] = _exception(error)
                result["issues"].append(restriction_issue(
                    "native_search_failed" if result["batch_state"] == "failed" else "catalog_unavailable",
                    "search" if result["batch_state"] == "failed" else "catalog"))
            finally:
                result["warnings"] = [{"category_module": row.category.__module__,
                    "category_name": row.category.__name__, "message": str(row.message),
                    "filename": row.filename, "lineno": row.lineno} for row in caught]
    return validate_restriction_record("NativeResult", result)


def _run(result):
    from Bio import Restriction, __version__ as native_version
    from Bio.Restriction import Restriction_Dictionary
    from Bio.Restriction import Restriction as implementation
    from Bio.Seq import Seq

    result["software"].update(biopython_version=native_version,
        dictionary_file=_pin(Restriction_Dictionary.__file__), native_source_file=_pin(implementation.__file__))
    if native_version != "1.88":
        result["issues"].append(restriction_issue("unsupported_native_version", "input"))
        return
    request = result["request"]
    selection = request["enzyme_selection"]
    names = selection["names"] if selection["kind"] == "explicit" else sorted(str(e) for e in Restriction.CommOnly)
    enzymes = []
    for index, name in enumerate(names):
        enzyme = getattr(Restriction, name, None)
        if (name not in Restriction_Dictionary.rest_dict or not isinstance(enzyme, implementation.RestrictionType)
                or str(enzyme) != name):
            result["issues"].append(restriction_issue("enzyme_unknown", "input", enzyme_ordinal=index))
        else:
            enzymes.append(enzyme)
    if result["issues"]:
        return
    rows = [_catalog_row(enzyme, index, Restriction_Dictionary.rest_dict) for index, enzyme in enumerate(enzymes)]
    catalog = validate_restriction_record("Catalog", {
        "version": "restriction_catalog_snapshot_v1", "biopython_version": native_version,
        "dictionary_file": result["software"]["dictionary_file"], "selection": deepcopy(selection),
        "resolved_names": list(names), "enzymes": rows})
    batch = Restriction.RestrictionBatch(enzymes)
    result["catalog"] = catalog
    result["native_batch_member_order"] = [str(e) for e in batch]
    searches = [{"catalog_ordinal": row["ordinal"], "name": row["name"], "search_ordinal": None,
        "state": "not_started", "native_search_positions_1based": None,
        "native_on_minus_before_drop": None, "error": None} for row in rows]
    result["enzyme_searches"] = searches
    owners = {}
    for row in rows:
        key = (row["native_pattern"]["text"], row["native_pattern"]["flags"], row["size_nt"])
        owners.setdefault(key, []).append(row["ordinal"])

    class ObservedSequence(implementation.FormattedSeq):
        def finditer(self, pattern, size):
            identity = _pattern(pattern)
            call = {"call_ordinal": len(result["match_observations"]),
                "owner_ordinals": list(owners.get((identity["text"], identity["flags"], size), [])),
                "native_pattern": identity, "site_size_nt": size, "linear": self.linear,
                "state": "failed", "matches": None, "error": None}
            result["match_observations"].append(call)
            try:
                matches = super().finditer(pattern, size)
            except Exception as error:
                call["error"] = _exception(error)
                raise
            try:
                call["matches"] = _match_rows(matches)
                call["state"] = "returned"
                if len(call["owner_ordinals"]) != 1:
                    result["issues"].append(restriction_issue("match_owner_ambiguous", "capture"))
            except Exception as error:
                call["matches"] = None
                call["state"] = "failed"
                call["error"] = _exception(error)
                result["issues"].append(restriction_issue("match_capture_unavailable", "capture"))
            # An observer failure must not cancel a successful native match.
            return matches

    observed = ObservedSequence(Seq(request["normalized_sequence"]), linear=request["topology"] == "linear")
    result["formatted_sequence"] = observed.data
    restored, call_count = [], 0
    try:
        for index, enzyme in enumerate(enzymes):
            original = enzyme.search
            # Native class dna would otherwise retain the observing closure and
            # its complete result after return. Restore that observer bookkeeping.
            restored.append((enzyme, enzyme.__dict__.get("search", _ABSENT), enzyme.__dict__.get("dna", _ABSENT)))

            def search(cls, dna, linear=True, _original=original, _index=index):
                nonlocal call_count
                row = searches[_index]
                row.update(search_ordinal=call_count, state="failed")
                call_count += 1
                try:
                    positions = _original(dna, linear=linear)
                    row.update(state="returned", native_search_positions_1based=positions)
                    if "NonPalindromic" in rows[_index]["native_class_mro"] and hasattr(cls, "on_minus"):
                        row["native_on_minus_before_drop"] = cls.on_minus
                    return positions
                except Exception as error:
                    row["error"] = _exception(error)
                    raise

            enzyme.search = classmethod(search)
        result["batch_state"] = "failed"
        mapping = batch.search(observed)
        result["native_mapping_order"] = [str(e) for e in mapping]
        for enzyme, positions in mapping.items():
            index = names.index(str(enzyme))
            if list(positions) != searches[index]["native_search_positions_1based"]:
                raise ValueError("restriction_observed_mapping_conflict")
        result["batch_state"] = "returned"
    finally:
        for enzyme, search, dna in reversed(restored):
            for name, saved in (("search", search), ("dna", dna)):
                if saved is _ABSENT:
                    if name in enzyme.__dict__:
                        delattr(enzyme, name)
                else:
                    setattr(enzyme, name, saved)


__all__ = ["run_restriction_mapping"]
