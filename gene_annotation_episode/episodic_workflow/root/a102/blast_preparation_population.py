"""Pure population of selected native preparation facts; no scoring or I/O.

The selected operation owns dependencies. Parsed documents own located native
facts. Materialization receipts own original/realized custody. None supplies a
default for the others. Saved validation checks these same relationships.
"""
from __future__ import annotations

from pathlib import PurePosixPath
import re

from .blast_utility_contracts import (
    _binding, _diagnostics, _fields, _occurrences, _operation, _outcome, _pointer,
    _require, validate_blast_utility_operation, validate_blast_utility_record as core,
)
from .blast_preparation_contracts import validate_blast_preparation_document
from .blast_database_preparation import _check, _failure, _native_file_path
from .native_blast_standard_database_contracts import _absolute, _copy

_KINDS = {"convert_gi_list": "identifier_list", "convert_seqid_list": "identifier_list",
    "create_subset_alias": "database_alias", "aggregate_databases": "database_alias",
    "aggregate_volumes": "database_alias", "create_megablast_index": "megablast_index",
    "create_profile_database": "profile_database"}
_FAMILY_ROLES = {"identifier_list", "alias_file", "index_file", "profile_file", "database_file", "database_metadata", "statistics"}
_PROFILE_COMPONENTS = {".rps": "rps", ".loo": "lookup", ".aux": "auxiliary", ".freq": "frequency",
    ".wcounts": "delta_weights", ".obsr": "delta_observations", ".blocks": "cobalt_blocks", ".pal": "alias"}


def _unique(rows):
    result = []
    for row in rows:
        if row not in result:
            result.append(row)
    return result


def _problem(record, code, *, stage="association", occurrence_id=None):
    return _failure(code, stage=stage, occurrence_id=occurrence_id)


def _selected_lists(operation):
    p, mode = operation["parameters"], operation["mode"]
    if mode == "create_profile_database":
        return [(p["profile_list_occurrence_id"], "profile_whitespace_tokens", [
            {"ordinal": e["ordinal"], "line_number": e["line_number"], "token_ordinal": e["token_ordinal"],
             "original_token": e["native_reference"], "target": {"kind": "input", "input_key": e["input_occurrence_id"]}}
            for e in p["profile_entries"]])]
    result = []
    if mode == "aggregate_databases":
        for selected in (p["classic_list"], p["vdb_list"]):
            if selected is None or selected["source"] != "file":
                continue
            result.append((selected["input_occurrence_id"], "blast_database_lines", [
                {"ordinal": e["ordinal"], "line_number": e["line_number"], "token_ordinal": 0,
                 "original_token": e["native_reference"], "target": {"kind": "database",
                     "database_key": e["database_key"], "native_path_index": e["native_path_index"]}}
                for e in selected["entries"]]))
    return result


def _dependencies(operation, bindings):
    p, mode = operation["parameters"], operation["mode"]
    result, by_key = [], {b["database_key"]: b for b in bindings}

    def file(oid, purpose):
        row = {"role": "input_file", "occurrence_id": oid, "purpose": purpose}
        if row not in result:
            result.append(row)

    def database(entry, source, list_id=None):
        result.append({"role": "database", "ordinal": sum(r["role"] == "database" for r in result),
            **{k: entry[k] for k in ("database_key", "native_path_index", "native_reference")},
            "source": source, "list_occurrence_id": list_id,
            "list_entry_ordinal": entry["ordinal"] if list_id is not None else None})

    if mode == "aggregate_databases":
        for field, source in (("classic_list", "dblist"), ("vdb_list", "vdblist")):
            selected = p[field]
            if selected is None:
                continue
            oid = selected.get("input_occurrence_id")
            if oid is not None:
                file(oid, "database_list")
            for entry in selected["entries"]:
                database(entry, source + ("_file" if oid is not None else ""), oid)
    elif mode == "aggregate_volumes":
        for entry in p["volume_entries"]:
            database(entry, "num_volumes")
    elif operation["database_key"] is not None:
        key = operation["database_key"]
        if key in by_key:
            # These modes accept exactly one explicit native prefix; multiple
            # volume operands belong to aggregate_volumes, not a guessed first DB.
            _require(len(by_key[key]["native_paths"]) == 1, "single_database_path_required")
            database({"database_key": key, "native_path_index": 0,
                      "native_reference": by_key[key]["native_paths"][0]}, "db")
    if mode == "create_subset_alias" and p["restriction"]["kind"] != "oid_masks":
        restriction = p["restriction"]
        file(restriction["occurrence_id"], {"gi_list": "gi_restriction", "seqid_list": "seqid_restriction",
                                            "taxid_list": "taxid_restriction"}[restriction["kind"]])
    if mode == "create_profile_database":
        file(p["profile_list_occurrence_id"], "profile_list")
        for entry in p["profile_entries"]:
            file(entry["input_occurrence_id"], "profile_input")
        if p["taxid_map_occurrence_id"] is not None:
            file(p["taxid_map_occurrence_id"], "taxid_map")
    return result


def _input_requirements(op):
    p, mode = op["parameters"], op["mode"]
    result = {}
    if mode.startswith("convert_"):
        result[p["input_occurrence_id"]] = ("identifier_list", "text")
    elif mode == "create_subset_alias" and p["restriction"]["kind"] != "oid_masks":
        result[p["restriction"]["occurrence_id"]] = ("identifier_list", p["restriction"]["format"])
    elif mode == "create_megablast_index" and p["input_format"] == "fasta":
        result[p["input_occurrence_id"]] = ("sequence_input", "fasta")
    for oid, grammar, _ in _selected_lists(op):
        result[oid] = ("profile_list" if grammar == "profile_whitespace_tokens" else "database_list", "text")
    if mode == "create_profile_database":
        result.update({e["input_occurrence_id"]: ("profile_input", p["input_format"]) for e in p["profile_entries"]})
        if p["taxid_map_occurrence_id"] is not None:
            result[p["taxid_map_occurrence_id"]] = ("taxid_map", "text")
    return result


def _materialized_occurrence(record, receipt):
    original_ids = {o for b in record["database_bindings"] for o in b["occurrence_ids"]}
    original_ids.update(record["operation"]["input_occurrence_ids"])
    original = next((r for r in record["inputs"] if r["occurrence_id"] == receipt.get("input_key")), None)
    role = ("database_file" if receipt["kind"] == "database_copy" else "materialized_list"
            if receipt["kind"] == "list_rewrite" else _input_requirements(record["operation"]).get(receipt["input_key"], (None,))[0]
            if original is None else original["role"])
    matches = [r for r in record["inputs"] if r["role"] == role and r["native_path"] is not None
               and r["occurrence_id"] not in original_ids
               and r["native_path"].endswith("/" + receipt["relative_path"])]
    _require(len(matches) <= 1, "materialization_occurrence_ambiguous")
    return matches[0] if matches else None


def _database_references(record, dependency):
    """Explicit selected and file-by-file realized native-prefix references."""
    binding = next((r for r in record["database_bindings"] if r["database_key"] == dependency["database_key"]), None)
    if binding is None or dependency["native_path_index"] >= len(binding["native_paths"]):
        return set()
    source = binding["native_paths"][dependency["native_path_index"]]
    references = {source}
    for receipt in record["materializations"]:
        if receipt["kind"] == "list_rewrite":
            for entry in receipt["entries"]:
                if entry["target"] == {"kind": "database", "database_key": binding["database_key"],
                                        "native_path_index": dependency["native_path_index"]}:
                    references.add(entry["realized_token"])
        elif receipt["kind"] == "database_copy" and receipt["database_key"] == binding["database_key"]:
            # Remove only the exact suffix shared with this selected source
            # prefix; this uses explicit file mappings, never basename matching.
            path = receipt["source_path"]
            row = _materialized_occurrence(record, receipt)
            if row is not None and path.startswith(source + "."):
                suffix = path[len(source):]
                if row["native_path"].endswith(suffix):
                    references.add(row["native_path"][:-len(suffix)])
    return references


def _profile_component(row):
    if row["role"] == "database_file" or row["role"] == "database_metadata":
        return "sequence_database"
    if row["role"] == "alias_file":
        return "alias"
    if row["role"] != "profile_file" or row["native_path"] is None:
        return "unknown"
    return _PROFILE_COMPONENTS.get(PurePosixPath(row["native_path"]).suffix, "unknown")


def _profile_volumes(record, documents):
    members = [r for r in record["outputs"] if r["role"] in {"profile_file", "database_file", "database_metadata", "alias_file"}]
    groups = {}
    for row in members:
        path = row["native_path"]
        if path is None or _profile_component(row) in {"unknown", "alias", "sequence_database"}:
            continue
        prefix = str(PurePosixPath(path).with_suffix(""))
        groups.setdefault(prefix, [])
    for prefix in groups:
        groups[prefix] = [r["occurrence_id"] for r in members if r["native_path"] is not None
            and str(PurePosixPath(r["native_path"]).with_suffix("")) == prefix
            and _profile_component(r) not in {"unknown", "alias"}]
    result = []
    for prefix, oids in groups.items():
        auxiliary = [d for d in documents if d["kind"] == "profile_aux" and d["occurrence_id"] in oids]
        result.append({"volume_key": prefix, "native_prefix": prefix, "occurrence_ids": oids,
            "parameter_observations": [v for d in auxiliary for v in d["parameter_observations"]],
            "auxiliary_documents": auxiliary, "profile_entry_ordinals": None})
    return result


def _detail(record, documents):
    op, p = record["operation"], record["operation"]["parameters"]
    mode, kind = op["mode"], record["kind"]
    metadata = [f for d in documents for f in d["native_fields"]]
    if kind == "identifier_list":
        return {"list_kind": "gi" if mode == "convert_gi_list" else "seqid",
            "input_occurrence_id": p["input_occurrence_id"],
            "output_occurrence_ids": [r["occurrence_id"] for r in record["outputs"] if r["role"] == "identifier_list"],
            "database_key": op["database_key"], "native_fields": metadata}
    if kind == "database_alias":
        detail = {"alias_kind": {"create_subset_alias": "subset", "aggregate_databases": "aggregate", "aggregate_volumes": "volumes"}[mode],
            "database_dependencies": [r for r in record["dependencies"] if r["role"] == "database"],
            "alias_documents": [d for d in documents if d["kind"] == "alias"]}
        if mode == "create_subset_alias":
            detail["restriction"] = p["restriction"]
        return detail
    if kind == "megablast_index":
        members = []
        for row in record["outputs"]:
            if row["role"] != "index_file":
                continue
            # Native ordinals do not identify a source volume. A direct .idx
            # member can join one explicitly supplied source-volume prefix;
            # otherwise retain unknown association (including inferred .00).
            matches = []
            path = row["native_path"]
            for dep in record["dependencies"]:
                if dep["role"] != "database" or path is None:
                    continue
                for ref in _database_references(record, dep):
                    if path == ref + ".idx":
                        binding = next(b for b in record["database_bindings"] if b["database_key"] == dep["database_key"])
                        source = binding["native_paths"][dep["native_path_index"]]
                        ids = [r["occurrence_id"] for r in record["inputs"] if r["occurrence_id"] in binding["occurrence_ids"]
                               and r["native_path"] is not None and r["native_path"].startswith(source + ".")]
                        matches.append((dep["database_key"], source, ids))
            match = matches[0] if len(matches) == 1 else None
            members.append({"ordinal": len(members), "occurrence_id": row["occurrence_id"],
                "database_key": None if match is None else match[0], "source_volume_reference": None if match is None else match[1],
                "source_volume_occurrence_ids": [] if match is None else match[2],
                "association": "unresolved" if match is None else "explicit"})
        return {**{k: p[k] for k in ("input_format", "source_database_key", "input_occurrence_id", "old_style_index", "legacy")},
            "index_members": members, "parameter_observations": [r["parameter_observation"] for d in documents
                if d["kind"] == "index_diagnostics" for r in d["rows"] if r["parameter_observation"] is not None]}
    profiles = [{"entry_ordinal": e["ordinal"], "input_occurrence_id": e["input_occurrence_id"],
        "disposition": "unknown", "reason": "native_disposition_unavailable", "evidence_occurrence_id": None,
        "evidence_line_number": None, "volume_key": None, "native_profile_ordinal": None} for e in p["profile_entries"]]
    refs = {e["ordinal"]: {e["native_reference"]} for e in p["profile_entries"]}
    for receipt in record["materializations"]:
        if receipt["kind"] == "list_rewrite" and receipt["input_key"] == p["profile_list_occurrence_id"]:
            for entry in receipt["entries"]:
                refs[entry["ordinal"]].add(entry["realized_token"])
    for doc in documents:
        if doc["kind"] != "profile_diagnostics":
            continue
        for row in doc["rows"]:
            matches = [ordinal for ordinal, values in refs.items() if row["native_reference"] in values]
            if len(matches) != 1 or row["category"] == "unknown":
                continue
            target = profiles[matches[0]]
            category = row["category"]
            disposition = "excluded" if category.startswith("excluded_") else "failed"
            reason = {"excluded_low_observations": "native_excluded_low_observations",
                      "excluded_invalid": "native_excluded_invalid"}.get(category, "native_failed_input")
            if target["disposition"] != "unknown" and (target["disposition"], target["reason"]) != (disposition, reason):
                target.update(disposition="unknown", reason="native_disposition_unavailable",
                              evidence_occurrence_id=None, evidence_line_number=None)
                continue
            target.update(disposition=disposition, reason=reason, evidence_occurrence_id=doc["occurrence_id"],
                          evidence_line_number=row["line_number"])
    return {"profile_type": p["profile_type"], "profile_list_occurrence_id": p["profile_list_occurrence_id"],
        "profile_entries": p["profile_entries"], "profiles": profiles, "volumes": _profile_volumes(record, documents),
        "profile_members": [{"occurrence_id": r["occurrence_id"], "component": _profile_component(r)}
            for r in record["outputs"] if r["role"] in {"database_file", "database_metadata", "profile_file", "alias_file"}]}


def _facts(record):
    """Derive mandatory checks and qualifications from retained structured facts."""
    checks, failures = [], []
    op, outcome, key = record["operation"], record["original_outcome"], record["database_key"]
    inputs = {r["occurrence_id"]: r for r in record["inputs"]}
    outputs = {r["occurrence_id"]: r for r in record["outputs"]}
    bindings = {r["database_key"]: r for r in record["database_bindings"]}
    streams = [r["occurrence_id"] for r in record["outputs"] if r["role"] in {"stdout", "stderr", "diagnostics"}]
    if outcome["state"] == "succeeded":
        checks.append(_check("native_execution", "pass", subject_refs=[key], method="native_execution_outcome", occurrences=streams))
    else:
        code = ("native_nonzero_exit" if outcome["returncode"] not in (None, 0) else
                "native_start_failed" if not outcome["started"] and outcome["state"] == "failed" else "preparation_not_successful")
        failures.append(_failure(code, stage="native", native_returncode=outcome["returncode"]))
        checks.append(_check("native_execution", "fail" if outcome["state"] == "failed" else "unknown",
            subject_refs=[key], method="native_execution_outcome", reason=code, occurrences=streams))
    for oid, (role, fmt) in _input_requirements(op).items():
        if oid not in inputs:
            failures.append(_problem(record, "input_population_unavailable", stage="input"))
        else:
            _require(inputs[oid]["role"] == role and inputs[oid]["native_format"] == fmt, "preparation_input_binding")
            if inputs[oid]["completeness"] != "complete":
                failures.append(_problem(record, "input_population_unavailable", stage="input", occurrence_id=oid))
    expected_keys = {r["database_key"] for r in record["dependencies"] if r["role"] == "database"}
    if op["database_key"] is not None:
        expected_keys.add(op["database_key"])
    for key_ in expected_keys:
        if (key_ not in bindings or not bindings[key_]["inventory_complete"] or
                any(inputs[oid]["completeness"] != "complete" or inputs[oid]["native_path"] is None
                    for oid in bindings[key_]["occurrence_ids"] if oid in inputs)):
            failures.append(_problem(record, "dependency_unavailable", stage="input"))
    _require(set(bindings) <= expected_keys, "unselected_database_binding")
    for dep in record["dependencies"]:
        if dep["role"] != "database" or dep["database_key"] not in bindings:
            continue
        b = bindings[dep["database_key"]]
        _require(dep["native_path_index"] < len(b["native_paths"]), "database_path_index")
        vdb = dep["source"] in {"vdblist", "vdblist_file"}
        if b["kind"] != ("vdb" if vdb else "blast_nucleotide_sequence" if op["molecule"] == "dna" else "blast_protein_sequence"):
            failures.append(_problem(record, "database_kind_conflict", stage="input"))
        if b["molecule"] != op["molecule"]:
            failures.append(_problem(record, "database_kind_conflict", stage="input"))
        if vdb and not any(inputs[o]["role"] == "offline_configuration" for o in b["occurrence_ids"] if o in inputs):
            failures.append(_problem(record, "dependency_unavailable", stage="input"))
    for receipt in record["materializations"]:
        if receipt["kind"] in {"list_rewrite", "input_copy"}:
            original = inputs.get(receipt["input_key"])
        else:
            originals = [r for r in record["inputs"] if r["role"] == "database_file"
                         and r["native_path"] == receipt["source_path"]
                         and r["occurrence_id"] in bindings.get(receipt["database_key"], {}).get("occurrence_ids", [])]
            _require(len(originals) <= 1, "materialization_original_ambiguous")
            original = originals[0] if originals else None
        realized = _materialized_occurrence(record, receipt)
        if original is None or realized is None:
            failures.append(_problem(record, "dependency_unavailable", stage="input"))
            continue
        identity = {k: original[k] for k in ("sha256", "size_bytes")}
        if receipt["kind"] in {"database_copy", "input_copy"}:
            if receipt["kind"] == "input_copy":
                _require(original["native_path"] == receipt["source_path"], "materialization_original_path")
            _require(identity == receipt["expected"], "materialization_original_identity")
            if receipt["staged"] != identity or receipt["final"] != identity:
                failures.append(_problem(record, "input_identity_mismatch", stage="input", occurrence_id=realized["occurrence_id"]))
            _require({k: realized[k] for k in identity} == receipt["final"], "materialization_final_identity")
        else:
            _require(original["sha256"] == receipt["original_sha256"], "materialization_original_identity")
            _require(all(realized[k] == receipt[k] for k in ("sha256", "size_bytes")), "materialization_final_identity")
    copied_keys = {r["database_key"] for r in record["materializations"] if r["kind"] == "database_copy"}
    if op["mode"] == "aggregate_volumes" or (op["mode"] == "create_megablast_index"
            and not op["parameters"]["old_style_index"]):
        copied_keys |= expected_keys
    for database_key in copied_keys:
        binding = bindings.get(database_key)
        if binding is None:
            failures.append(_problem(record, "dependency_unavailable", stage="input"))
            continue
        source_paths = {inputs[o]["native_path"] for o in binding["occurrence_ids"]
                        if o in inputs and inputs[o]["role"] == "database_file"}
        copied_paths = {r["source_path"] for r in record["materializations"]
                        if r["kind"] == "database_copy" and r["database_key"] == database_key}
        if not source_paths or source_paths != copied_paths:
            failures.append(_problem(record, "dependency_unavailable", stage="input"))
    family = [r for r in record["outputs"] if r["role"] in _FAMILY_ROLES]
    family_reasons = []
    if not record["inventory_complete"]:
        family_reasons.append("output_inventory_incomplete")
    if not family:
        family_reasons.append("output_missing")
    if any(r["completeness"] != "complete" or r["native_path"] is None for r in family):
        family_reasons.append("output_family_incomplete")
    detail, kind = record["detail"], record["kind"]
    if kind == "identifier_list":
        listed = [outputs[k] for k in detail["output_occurrence_ids"]]
        fmt = "gi_list_binary" if detail["list_kind"] == "gi" else "seqid_list_binary"
        if len(listed) != 1 or any(r["native_format"] != fmt for r in listed):
            family_reasons.append("output_family_incomplete")
    elif kind == "database_alias":
        aliases = [r for r in family if r["role"] == "alias_file"]
        if not aliases or {r["occurrence_id"] for r in aliases} != {d["occurrence_id"] for d in detail["alias_documents"]}:
            family_reasons.append("output_family_incomplete")
        for doc in detail["alias_documents"]:
            source = outputs[doc["occurrence_id"]]
            for native_key, sources in (("DBLIST", {"db", "dblist", "dblist_file", "num_volumes"}), ("VDBLIST", {"vdblist", "vdblist_file"})):
                selected = [d for d in detail["database_dependencies"] if d["source"] in sources]
                tokens = [t["value"] for row in doc["rows"] if row["native_key"] == native_key for t in row["tokens"]]
                if len(tokens) != len(selected) or any(
                        _native_file_path(token, source) not in _database_references(record, dep)
                        and token not in _database_references(record, dep) for token, dep in zip(tokens, selected)):
                    failures.append(_problem(record, "record_association_unresolved", occurrence_id=doc["occurrence_id"]))
            if detail["alias_kind"] == "subset" and detail["restriction"]["kind"] != "oid_masks":
                restriction = detail["restriction"]
                name = {"gi_list": "GILIST", "seqid_list": "SEQIDLIST", "taxid_list": "TAXIDLIST"}[restriction["kind"]]
                tokens = [t["value"] for row in doc["rows"] if row["native_key"] == name for t in row["tokens"]]
                # Native staging of an ordinary selected input is authenticated
                # by the producer. The literal restriction must at least name
                # the exact selected original path, or a retained realized path.
                known = {r["native_path"] for r in record["inputs"] if r["occurrence_id"] == restriction["occurrence_id"]}
                known.update(r["native_path"] for receipt in record["materializations"]
                    if receipt["kind"] == "input_copy" and receipt["input_key"] == restriction["occurrence_id"]
                    and (r := _materialized_occurrence(record, receipt)) is not None)
                if len(tokens) != 1 or not any(token in known or _native_file_path(token, source) in known for token in tokens):
                    failures.append(_problem(record, "record_association_unresolved", occurrence_id=doc["occurrence_id"]))
    elif kind == "megablast_index":
        if not detail["index_members"]:
            family_reasons.append("output_family_incomplete")
    else:
        required = {"rps", "lookup", "auxiliary", "frequency"}
        required |= {"delta_weights", "delta_observations"} if detail["profile_type"] == "delta" else {"cobalt_blocks"} if detail["profile_type"] == "cobalt" else set()
        members = {r["occurrence_id"]: r["component"] for r in detail["profile_members"]}
        if not detail["volumes"] or any(not required <= {members[o] for o in v["occurrence_ids"]}
                                         for v in detail["volumes"]):
            family_reasons.append("output_family_incomplete")
        for volume in detail["volumes"]:
            if any(members[o] == "auxiliary" for o in volume["occurrence_ids"]) and not volume["auxiliary_documents"]:
                failures.append(_problem(record, "semantic_validation_unavailable", stage="parse"))
    for code in dict.fromkeys(family_reasons):
        failures.append(_problem(record, code, stage="capture" if code == "output_inventory_incomplete" else "validation"))
    checks.append(_check("database_inventory", "fail" if family_reasons else "pass", subject_refs=[key],
        method="family_inventory", reason=family_reasons[0] if family_reasons else None,
        occurrences=[r["occurrence_id"] for r in family]))
    return checks, _unique(failures)


def _validate_preparation_record(record):
    """Shared semantic validator, called after the exact common v2 shape check."""
    op, outcome = record["operation"], record["original_outcome"]
    _operation(op); _outcome(outcome)
    _require(op["version"] == "blast_utility_operation_v2" and _KINDS.get(op["mode"]) == record["kind"], "artifact_set_operation")
    _pointer(record["identity"]["source"]["pointer"])
    for path in record["native_paths"]:
        _absolute(path)
    occurrences = _occurrences(record["inputs"] + record["outputs"])
    inputs = {r["occurrence_id"]: r for r in record["inputs"]}
    outputs = {r["occurrence_id"]: r for r in record["outputs"]}
    _require(all(r["direction"] == "input" for r in inputs.values()) and all(r["direction"] == "output" for r in outputs.values()), "artifact_set_direction")
    bindings = record["database_bindings"]
    _require(len({b["database_key"] for b in bindings}) == len(bindings), "duplicate_database_key")
    for b in bindings:
        _binding(b)
        _require(set(b["occurrence_ids"]) <= inputs.keys(), "database_occurrence_reference")
    by_path, by_ref = {}, {}
    for row in occurrences.values():
        identity = row["sha256"], row["size_bytes"]
        for key, table in ((row["native_path"], by_path), (row["artifact_ref"], by_ref)):
            if key is not None:
                _require(key not in table or table[key] == identity, "artifact_path_identity_conflict")
                table[key] = identity
    _require(record["dependencies"] == _dependencies(op, bindings), "artifact_set_dependency_population")
    receipts = record["materializations"]
    receipt_keys = [(r["kind"], r.get("database_key"), r.get("source_path"), r.get("input_key")) for r in receipts]
    _require(len(receipt_keys) == len(set(receipt_keys)), "duplicate_materialization")
    _require(len({r["relative_path"] for r in receipts}) == len(receipts), "duplicate_materialization_path")
    for receipt in receipts:
        core("MaterializationReceipt", receipt)
        if receipt["kind"] == "database_copy":
            _require(receipt["database_key"] in {b["database_key"] for b in bindings}, "materialization_database_reference")
        elif receipt["kind"] == "input_copy":
            _require(receipt["input_key"] in op["input_occurrence_ids"], "materialization_input_reference")
    selected_lists = {oid: (grammar, entries) for oid, grammar, entries in _selected_lists(op)}
    for receipt in receipts:
        if receipt["kind"] != "list_rewrite":
            continue
        _require(receipt["input_key"] in selected_lists, "materialization_unselected_list")
        grammar, entries = selected_lists[receipt["input_key"]]
        _require(receipt["grammar"] == grammar and [{k: v for k, v in e.items() if k != "realized_token"}
                 for e in receipt["entries"]] == entries, "materialization_list_binding")
    realized_ids = {r["occurrence_id"] for receipt in receipts if (r := _materialized_occurrence(record, receipt)) is not None}
    allowed_inputs = set(op["input_occurrence_ids"]) | realized_ids | {o for b in bindings for o in b["occurrence_ids"]}
    _require(set(inputs) <= allowed_inputs, "unselected_input_occurrence")
    if record["inventory_complete"]:
        _require(outcome["writer_closed"] and outcome["inventory_complete"] and all(r["completeness"] == "complete"
                 and r["native_path"] is not None for r in outputs.values()), "artifact_set_inventory_completeness")
    _fields(record["native_metadata"], set(occurrences))
    detail, kind, p = record["detail"], record["kind"], op["parameters"]
    if kind == "identifier_list":
        _require(detail == _detail(record, [{"native_fields": record["native_metadata"]}]), "artifact_set_detail")
    elif kind == "database_alias":
        docs = [validate_blast_preparation_document(d) for d in detail["alias_documents"]]
        _require(all(d["occurrence_id"] in outputs and outputs[d["occurrence_id"]]["role"] == "alias_file" for d in docs), "alias_document_reference")
        _require(detail == _detail(record, docs), "artifact_set_detail")
        _require(all(f in record["native_metadata"] for d in docs for f in d["native_fields"]), "alias_native_field_projection")
    elif kind == "megablast_index":
        _require(all(detail[k] == p[k] for k in ("input_format", "source_database_key", "input_occurrence_id", "old_style_index", "legacy")), "artifact_set_detail")
        _require(detail["index_members"] == _detail(record, [])["index_members"], "index_member_association")
        for observation in detail["parameter_observations"]:
            core("ParameterObservation", observation)
            _require(observation["scope_key"] in occurrences and observation["occurrence_id"] in {None, observation["scope_key"]}, "parameter_document_scope")
            _require(observation["parameter"] in {"nmer", "ws_hint", "stride", "legacy", "old_style_index", "output_prefix"}, "parameter_document_kind")
    else:
        _require(all(detail[k] == p[k] for k in ("profile_type", "profile_list_occurrence_id", "profile_entries")), "artifact_set_detail")
        _require([(r["entry_ordinal"], r["input_occurrence_id"]) for r in detail["profiles"]] ==
                 [(e["ordinal"], e["input_occurrence_id"]) for e in p["profile_entries"]], "profile_disposition_population")
        docs = [validate_blast_preparation_document(d) for v in detail["volumes"] for d in v["auxiliary_documents"]]
        expected = _detail(record, docs)
        _require(detail["profile_members"] == expected["profile_members"] and detail["volumes"] == expected["volumes"], "profile_volume_association")
        for r in detail["profiles"]:
            if r["disposition"] == "unknown":
                _require(r["reason"] == "native_disposition_unavailable" and r["evidence_occurrence_id"] is None
                    and r["evidence_line_number"] is None and r["volume_key"] is None and r["native_profile_ordinal"] is None, "profile_unknown_disposition")
            else:
                # This initial port has exclusion/error text, but no authoritative
                # included-input membership source. Aux order alone cannot supply it.
                _require(r["disposition"] in {"excluded", "failed"} and r["evidence_occurrence_id"] in outputs
                    and outputs[r["evidence_occurrence_id"]]["role"] in {"stdout", "stderr", "diagnostics"}
                    and r["evidence_line_number"] is not None and r["volume_key"] is None
                    and r["native_profile_ordinal"] is None, "profile_disposition_evidence")
                _require(r["reason"] in ({"native_excluded_invalid", "native_excluded_low_observations"}
                    if r["disposition"] == "excluded" else {"native_failed_input"}), "profile_disposition_reason")
    expected_type = ("sequence_database" if kind == "database_alias" and not any(b["kind"] == "vdb" for b in bindings)
        else p["profile_type"] if kind == "profile_database" and p["profile_type"] in {"rps", "delta"} else "unknown")
    _require(record["identity"]["preparation_type"] == expected_type, "preparation_identity_type")
    _require(record["database_key"] not in {b["database_key"] for b in bindings}, "prepared_source_identity_conflict")
    _diagnostics(record, occurrences=set(occurrences), subjects=set(occurrences) | {record["database_key"]}
                 | {b["database_key"] for b in bindings}, outcome=outcome)
    checks, failures = _facts(record)
    _require(all(c in record["checks"] for c in checks), "preparation_observation_conflict")
    _require(all(f in record["failures"] for f in failures), "preparation_failure_missing")
    # The branch currently has no authentic compatible validator attachment.
    _require(record["compatibility"] != "validated", "database_compatibility_evidence")


def populate_blast_preparation_artifact_set(*, operation: dict, inputs: list,
        outputs: list, database_bindings: list, materializations: list,
        database_key: str, identity: dict, software: dict, argv: list,
        native_paths: list, documents: list, outcome: dict) -> dict:
    operation = validate_blast_utility_operation(operation)
    _require(operation["version"] == "blast_utility_operation_v2" and operation["mode"] in _KINDS, "preparation_operation_required")
    _require(all(type(x) is list for x in (inputs, outputs, database_bindings, materializations, documents)), "preparation_lists_required")
    inputs = [core("ArtifactOccurrence", r) for r in inputs]
    outputs = [core("ArtifactOccurrence", r) for r in outputs]
    bindings = [core("DatabaseBinding", r) for r in database_bindings]
    receipts = [core("MaterializationReceipt", r) for r in materializations]
    outcome = core("NativeOutcome", outcome)
    documents = [validate_blast_preparation_document(d) for d in documents]
    allowed_document_kinds = ({"list", "alias", "aliastool_diagnostics"} if operation["program"] == "blastdb_aliastool"
        else {"index_diagnostics"} if operation["program"] == "makembindex" else {"list", "profile_aux", "profile_diagnostics"})
    _require(all(d["kind"] in allowed_document_kinds for d in documents), "preparation_document_operation")
    by_id = _occurrences(inputs + outputs)
    _require(len({(d["kind"], d["occurrence_id"]) for d in documents}) == len(documents), "duplicate_preparation_document")
    for doc in documents:
        _require(doc["occurrence_id"] in by_id, "preparation_document_reference")
        row = by_id[doc["occurrence_id"]]
        expected = {"list": ("input", {"database_list", "profile_list", "materialized_list"}),
            "alias": ("output", {"alias_file"}), "profile_aux": ("output", {"profile_file"}),
            "aliastool_diagnostics": ("output", {"stdout", "stderr", "diagnostics"}),
            "index_diagnostics": ("output", {"stdout", "stderr", "diagnostics"}),
            "profile_diagnostics": ("output", {"stdout", "stderr", "diagnostics"})}
        _require(doc["kind"] in expected and row["direction"] == expected[doc["kind"]][0]
                 and row["role"] in expected[doc["kind"]][1], "preparation_document_kind")
        if doc["kind"] == "profile_aux":
            _require(row["native_format"] == "blast_profile_aux_text", "preparation_document_format")
        if doc["kind"] == "alias":
            _require(row["native_format"] == "blast_alias_text", "preparation_document_format")
    checks = [r for d in documents for r in d["checks"]]
    failures = [r for d in documents for r in d["failures"]]
    for oid, grammar, entries in _selected_lists(operation):
        document = next((d for d in documents if d["kind"] == "list" and d["occurrence_id"] == oid), None)
        if document is None:
            failures.append(_failure("input_population_unavailable", stage="parse", occurrence_id=oid if oid in by_id else None))
        else:
            actual = [{k: row[k] for k in ("ordinal", "line_number", "token_ordinal", "original_token")} for row in document["rows"]]
            expected = [{k: row[k] for k in ("ordinal", "line_number", "token_ordinal", "original_token")} for row in entries]
            if actual != expected:
                failures.append(_failure("supplied_binding_conflict", stage="association", occurrence_id=oid))
        if not any(r["kind"] == "list_rewrite" and r["input_key"] == oid for r in receipts):
            failures.append(_failure("dependency_unavailable", stage="input", occurrence_id=oid if oid in by_id else None))
    record = {"version": "blast_database_artifact_set_v2", "kind": _KINDS[operation["mode"]],
        "operation": operation, "original_outcome": outcome, "database_key": database_key, "identity": identity,
        "software": software, "argv": argv, "native_paths": native_paths, "inputs": inputs, "outputs": outputs,
        "database_bindings": bindings, "materializations": receipts,
        "dependencies": _dependencies(operation, bindings), "inventory_complete": outcome["writer_closed"]
            and outcome["inventory_complete"] and all(r["completeness"] == "complete" and r["native_path"] is not None for r in outputs),
        "native_metadata": [f for d in documents for f in d["native_fields"]],
        "detail": {}, "compatibility": "unverified", "checks": checks, "failures": failures}
    record["detail"] = _detail(record, documents)
    derived_checks, derived_failures = _facts(record)
    record["checks"] = _unique([*checks, *derived_checks])
    record["failures"] = _unique([*failures, *derived_failures])
    return validate_blast_preparation_relationships(record)


def validate_blast_preparation_relationships(record: dict) -> dict:
    _require(type(record) is dict and record.get("version") == "blast_database_artifact_set_v2", "preparation_result_version")
    return core("DatabaseArtifactSet", record)


__all__ = ["populate_blast_preparation_artifact_set", "validate_blast_preparation_relationships"]
