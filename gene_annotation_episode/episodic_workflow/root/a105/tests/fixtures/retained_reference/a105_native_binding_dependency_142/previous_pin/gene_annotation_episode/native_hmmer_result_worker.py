"""Bounded, Store-free parsing of an already acquired native HMMER bundle.

Only captured custody paths are read. This worker invokes the B003 readers and
calculators; it never invokes HMMER, a service, a model or an execution decision.
Large native text and full sheets are confined to the caller-limited process.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import sys

from .hmmer_graders import grade_hmmer_native_artifacts
from .hmmer_native_result_views import (NATIVE_HMMER_METRICS, family_for_program,
    projected_measurements, validate_native_hmmer_result_selector)
from .hmmalign_inputs import parse_hmmalign_stockholm


COLLECTIONS = {"protein_domain": "domains", "nucleotide_locus": "loci", "alignment_sequence": "sequences"}


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".writing")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, allow_nan=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
    temporary.replace(path)


def _alphabet(value):
    value = value.lower() if isinstance(value, str) else value
    return "amino" if value == "protein" else value


def _digest(sequence):
    return hashlib.sha256(sequence.upper().encode("ascii")).hexdigest()


def _fasta(text):
    records, current = [], None
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        end = offset + len(line.encode("utf-8"))
        if line.startswith(">"):
            name = line[1:].split()
            current = {"name": name[0] if name else None, "accession": None, "sequence": "",
                       "locator": {"line_number": number, "byte_start": offset, "byte_end": end}}
            records.append(current)
        elif line.strip():
            if current is None:
                raise ValueError("native_hmmer_input_fasta_header_missing")
            current["sequence"] += "".join(line.split()).upper()
        if current is not None:
            current["locator"]["byte_end"] = end
        offset = end
    for record in records:
        sequence = record["sequence"]
        record["valid"] = bool(record["name"] and sequence and re.fullmatch(r"[A-Z*]+", sequence))
        record["length"] = len(sequence)
    return records


def _profiles(text):
    records, current, offset = [], None, 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        fields = line.split()
        end = offset + len(line.encode("utf-8"))
        if line.startswith("HMMER3/"):
            current = {"name": None, "accession": None, "kind": "profile", "map": [],
                "locator": {"line_number": number, "byte_start": offset, "byte_end": end},
                "complete": False, "native_header": line.strip()}
            records.append(current)
        elif current is not None and fields:
            names = {"NAME": "name", "ACC": "accession", "LENG": "length", "ALPH": "alphabet",
                     "CKSUM": "checksum", "MAP": "map_declared"}
            if fields[0] in names and len(fields) > 1:
                key = names[fields[0]]
                try:
                    current[key] = int(fields[1]) if key in {"length", "checksum"} else fields[1]
                    if key == "alphabet":
                        current["native_alphabet"] = fields[1]
                        current[key] = _alphabet(fields[1])
                except ValueError:
                    current[key] = None
            elif fields[0] == "HMM":
                current["emission_columns"] = len(fields) - 1
            elif fields[0].isdigit() and "emission_columns" in current:
                k = current["emission_columns"] + 1
                if current.get("map_declared") == "yes" and len(fields) > k:
                    try:
                        current["map"].append(int(fields[k]))
                    except ValueError:
                        current["map"].append(None)
            elif fields[0] in {"GA", "TC", "NC"}:
                try:
                    cutoff = {"sequence_bits": float(fields[1].rstrip(";")),
                        **({"domain_bits": float(fields[2].rstrip(";"))} if len(fields) > 2 else {})}
                    if all(math.isfinite(v) for v in cutoff.values()):
                        current[fields[0]] = cutoff
                except (ValueError, IndexError):
                    pass
            elif fields[0] == "//":
                current["complete"] = True
        if current is not None:
            current["locator"]["byte_end"] = end
            if line.strip() == "//":
                current = None
        offset = end
    for record in records:
        record["valid"] = bool(record["complete"] and record["name"] and
            type(record.get("length")) is int and record["length"] > 0 and
            record.get("alphabet") in {"amino", "dna", "rna"})
        if record.get("map_declared") != "yes":
            record.pop("map")
    return records


def _stockholm(text, role, ref):
    native = parse_hmmalign_stockholm(text, artifact_ref=ref, engine_version=None)
    records = []
    for alignment in native["alignments"]:
        if role == "query_alignment":
            ids = [event["value"] for event in alignment["original_events"]
                   if event["kind"] == "GF" and event["tag"] == "ID"]
            records.append({"name": ids[0] if len(ids) == 1 else None, "accession": None, "kind": "msa",
                "length": alignment["column_count"], "locator": alignment["locator"],
                "valid": alignment["header_valid"] and alignment["complete"], "alignment": alignment})
            continue
        for row in alignment["rows"]:
            sequence = "".join(c for c in row["aligned_sequence"] if c.isascii() and c.isalpha()).upper()
            records.append({"name": row["name"], "accession": None, "sequence": sequence,
                "length": len(sequence), "locator": row["locator"],
                "valid": row["geometry_valid"] and row["symbols_valid"] and row["identity_unambiguous"]})
    return records


def _input_records(bundle, paths, diagnostics):
    records = {}
    alphabet = "dna" if bundle["program"] in {"nhmmer", "nhmmscan"} else "amino"
    for item in paths:
        if item["kind"] != "input" or item["format"].startswith("hmmer_h3"):
            continue
        try:
            text = Path(item["path"]).read_text(encoding="utf-8")
            parsed = (_fasta(text) if item["format"] == "fasta" else
                      _profiles(text) if item["format"] == "hmmer3_ascii" else
                      _stockholm(text, item["role"], item["artifact_ref"]))
            seen = Counter()
            for ordinal, record in enumerate(parsed):
                record.update(operand_role=item["role"], record_ordinal=ordinal,
                              artifact_ref=item["artifact_ref"], name_occurrence=seen[record["name"]])
                seen[record["name"]] += 1
                record.setdefault("alphabet", alphabet)
                record.setdefault("kind", "protein_sequence" if record["alphabet"] == "amino" else "nucleotide_sequence")
                if "sequence" in record:
                    record["sequence_sha256"] = _digest(record["sequence"])
                if not record["valid"]:
                    diagnostics.append({"stage": "inputs", "code": "native_hmmer_input_record_invalid",
                                        "record_key": None, "role": item["role"], "ordinal": ordinal})
            records[item["role"]] = parsed
        except (ValueError, OSError, UnicodeError) as error:
            diagnostics.append({"stage": "inputs", "code": "native_hmmer_input_parse_failed",
                                "record_key": None, "role": item["role"], "detail": str(error)})
    for binding in bundle["operand_bindings"]:
        matches = [row for row in records.get(binding["operand_role"], [])
                   if row["record_ordinal"] == binding["record_ordinal"]]
        if len(matches) != 1:
            diagnostics.append({"stage": "binding", "code": "native_hmmer_operand_binding_record_missing",
                                "record_key": None, "supplied_binding": binding})
    return records


def _meta(record):
    if record is None or not record.get("valid"):
        return None
    return {key: deepcopy(record[key]) for key in ("name", "accession", "kind", "alphabet", "length",
        "sequence", "sequence_sha256", "map", "checksum", "operand_role", "record_ordinal", "artifact_ref") if key in record}


def _query_role(bundle):
    return ("query_profile" if bundle["program"] == "hmmsearch" or bundle["program"] == "nhmmer" and bundle["mode"] == "profile"
        else "query_alignment" if bundle["program"] == "nhmmer" and bundle["mode"] == "alignment" else "query_sequence")


def _match(records, name, accession=None, *, ordinal=None):
    matches = [row for row in records if row.get("valid") and
        (name is None or name in {row.get("name"), row.get("accession")}) and
        (accession is None or accession == row.get("accession")) and
        (name is not None or accession is not None)]
    if ordinal is not None:
        matches = [row for row in matches if row["record_ordinal"] == ordinal]
    return matches[0] if len(matches) == 1 else None


def _metadata_inputs(bundle, records, paths, diagnostics):
    supplied = bundle["requested_job"]["native_hmmer"]["metadata"]
    inputs = deepcopy(supplied)
    for name, kind in (("database", dict), ("model_cutoffs", list)):
        if inputs.get(name) is not None and type(inputs[name]) is not kind:
            diagnostics.append({"stage": "metadata", "code": "native_hmmer_supplied_metadata_invalid",
                                "record_key": None, "input_field": name, "supplied": inputs.pop(name)})
    for key in ("query", "targets", "profile", "sequences", "mapali", "trim"):
        inputs.pop(key, None)
    options = bundle["requested_job"]["native_hmmer"]["options"]
    native_parameters = inputs.get("native_parameters")
    inputs["native_parameters"] = {**(native_parameters if isinstance(native_parameters, dict) else {}),
        "selected_options": deepcopy(options), "query_construction_mode": bundle["mode"]}
    # Acquisition declarations never override the actual producer outcome.
    inputs["acquisition"] = {"output_complete": bundle.get("returncode") == 0 and not bundle.get("failures"),
                             "hit_population_complete": bundle.get("returncode") == 0 and not bundle.get("failures")}
    if bundle["program"] == "hmmalign":
        profiles = records.get("profile", [])
        inputs["profile"] = _meta(profiles[0]) if len(profiles) == 1 else {}
        inputs["trim"] = "--trim" in options
        inputs["sequences"] = []
        counts = Counter()
        for role in ("mapali", "sequences"):
            for record in records.get(role, []):
                metadata = _meta(record)
                if metadata is not None:
                    metadata.update(occurrence=counts[record["name"]],
                        origin="inherited" if role == "mapali" else "newly_aligned")
                    counts[record["name"]] += 1
                    inputs["sequences"].append(metadata)
        mapali = [row for row in paths if row["kind"] == "input" and row["role"] == "mapali"]
        if mapali:
            inputs["mapali"] = {"artifact_ref": mapali[0]["artifact_ref"],
                                "stockholm": Path(mapali[0]["path"]).read_text(encoding="utf-8")}
    else:
        queries = records.get(_query_role(bundle), [])
        inputs["query"] = _meta(queries[0]) if len(queries) == 1 else None
        targets = records.get("profile_database" if bundle["program"] in {"hmmscan", "nhmmscan"} else "sequence_database", [])
        inputs["targets"] = [m for row in targets if (m := _meta(row)) is not None]
    # Keep supplied values and actual bytes distinct, including conflicts. Extra
    # annotation metadata may join only an exactly identified unique input.
    for key in ("query", "profile", "targets", "sequences"):
        actual = inputs.get(key)
        actual_rows = actual if isinstance(actual, list) else [actual] if isinstance(actual, dict) else []
        given = supplied.get(key)
        supplied_rows = given if isinstance(given, list) else [given] if isinstance(given, dict) else []
        for row in actual_rows:
            matches = [m for m in supplied_rows if isinstance(m, dict) and m.get("name") == row.get("name")
                and (m.get("accession") is None or m["accession"] == row.get("accession"))]
            if len(matches) != 1:
                continue
            for field, value in matches[0].items():
                if field in row and value is not None:
                    equal = (_alphabet(value) == _alphabet(row[field]) if field == "alphabet" else
                             {"new": "newly_aligned", "mapali": "inherited"}.get(value, value) == row[field] if field == "origin" and isinstance(value, str) else
                             value.upper() == row[field].upper() if field == "sequence" and isinstance(value, str) else value == row[field])
                    if not equal:
                        diagnostics.append({"stage": "metadata", "code": "native_hmmer_supplied_metadata_conflict",
                            "record_key": None, "input_field": key + "." + field,
                            "record_ordinal": row["record_ordinal"], "supplied": value, "parsed": row[field]})
                elif field not in row and field not in {"sequence", "length", "kind", "occurrence", "origin", "map", "checksum"}:
                    row[field] = deepcopy(value)
    return inputs


def _binding(record, bundle, diagnostics, record_key):
    if record is None:
        return None
    compact = {key: deepcopy(record.get(key)) for key in ("operand_role", "record_ordinal", "artifact_ref",
        "name", "accession", "kind", "alphabet", "length", "sequence_sha256", "locator")}
    bindings = [row for row in bundle["operand_bindings"] if row["operand_role"] == record["operand_role"]
                and row["record_ordinal"] == record["record_ordinal"]]
    compact["binding"] = None
    if len(bindings) == 1:
        binding = bindings[0]
        if ((binding.get("native_name") is None and binding.get("native_accession") is None) or
                binding.get("native_name") is not None and binding["native_name"] != record.get("name") or
                binding.get("native_accession") is not None and binding["native_accession"] != record.get("accession")):
            diagnostics.append({"stage": "binding", "code": "native_hmmer_operand_binding_identity_mismatch",
                                "record_key": record_key, "supplied_binding": binding, "parsed_operand": compact})
        else:
            compact["binding"] = deepcopy(binding)
    return compact


def _join_multiple_queries(grading, bundle, records, inputs):
    """Supply B003's single-query input slot separately for each actual query.

    Query ordinals follow the native query stream, never the sorted hit list.
    The complete original native population remains in the saved sheet, while
    its extracted rows receive their own validated input record metadata.
    """
    choices = records.get(_query_role(bundle), [])
    if bundle["program"] == "hmmalign" or len(choices) <= 1:
        return grading
    sheet = grading["sheet"]
    nucleotide = bundle["program"] in {"nhmmer", "nhmmscan"}
    from .hmmer_search_inputs import build_hmmer_search_sheet
    from .nhmmer_inputs import build_nhmmer_sheet
    from .hmmer_search_grader import calculate_hmmer_search_scores
    from .nhmmer_grader import calculate_nhmmer_scores
    collection = "loci" if nucleotide else "domains"
    replacement = {collection: {}, "hits": {}, "queries": {}}
    supplied_queries = []
    for query in sheet["queries"]:
        occurrence = query.get("occurrence")
        ordinal = occurrence - 1 if nucleotide and type(occurrence) is int else occurrence
        actual = _match(choices, query.get("name"), query.get("accession"), ordinal=ordinal)
        meta = _meta(actual)
        if meta is None:
            continue
        meta["occurrence"] = occurrence
        supplied_queries.append(meta)
        selected_inputs = {**inputs, "query": meta}
        qkey = query["record_key"]
        if nucleotide:
            native = deepcopy(sheet["native"])
            keys = {representation["record_key"] for row in sheet["loci"]
                    if row.get("query_record_key") == qkey for representation in row["source_records"]}
            for name in ("table_rows", "stdout_loci"):
                native[name] = [row for row in native[name] if row["record_key"] in keys]
            native["queries"] = [q for q in native["queries"] if q["record_key"] == qkey]
            rebuilt = build_nhmmer_sheet(native, inputs=selected_inputs)
        else:
            native = {**sheet, "schema": "hmmer_search_native_v1"}
            for name in ("hits", "domains", "iterations"):
                native[name] = [row for row in sheet[name] if row.get("query_record_key") == qkey]
            native["queries"] = [q for q in sheet["queries"] if q["record_key"] == qkey]
            rebuilt = build_hmmer_search_sheet(native, inputs=selected_inputs)
        for name in replacement:
            replacement[name].update({row["record_key"]: row for row in rebuilt.get(name, [])})
    for name, rows in replacement.items():
        if name in sheet:
            sheet[name] = [rows.get(row["record_key"], row) for row in sheet[name]]
    sheet["inputs"]["queries"] = supplied_queries
    calculate = calculate_nhmmer_scores if nucleotide else calculate_hmmer_search_scores
    grading["scores"] = calculate(sheet, parameters=bundle["requested_job"]["native_hmmer"]["grading_parameters"])
    return grading


def _operands(bundle, records, sheet_row, score, diagnostics):
    program, family = bundle["program"], family_for_program(bundle["program"])
    key = score["record_key"]
    if family == "alignment_sequence":
        role = "mapali" if sheet_row.get("origin") == "inherited" else "sequences"
        metadata = (sheet_row.get("metadata_join") or {}).get("supplied") or {}
        ordinal = metadata.get("record_ordinal")
        row = _match(records.get(role, []), score.get("name"), ordinal=ordinal)
        if role == "mapali" and (sheet_row.get("inherited_join") or {}).get("status") != "verified":
            row = None
        if (sheet_row.get("mapping") or {}).get("status") != "unique":
            row = None
        result = _binding(row, bundle, diagnostics, key)
        interval = (sheet_row.get("mapping") or {}).get("original_interval")
        return {"subject_operand": result, "subject_interval": interval if result else None,
                "related_operands": [_binding(r, bundle, diagnostics, key) for r in records.get("profile", [])]}
    facts = sheet_row.get("native", {})
    name = sheet_row.get("query_name", facts.get("query_name"))
    accession = sheet_row.get("query_accession", facts.get("query_accession"))
    occurrence = sheet_row.get("query_occurrence")
    ordinal = (occurrence - 1 if family == "nucleotide_locus" else occurrence) if type(occurrence) is int else None
    query = _match(records.get(_query_role(bundle), []), name, accession, ordinal=ordinal)
    target = _match(records.get("profile_database" if program in {"hmmscan", "nhmmscan"} else "sequence_database", []),
                    sheet_row.get("target_name", facts.get("target_name")), sheet_row.get("target_accession", facts.get("target_accession")))
    subject, other, axis = (query, target, "sequence") if program in {"hmmscan", "nhmmscan"} else (target, query, "sequence")
    if program == "jackhmmer" and score.get("iteration") == 1 and not any(
            b.get("subject_ref") and b["operand_role"] == "sequence_database" and target is not None
            and b["record_ordinal"] == target["record_ordinal"] for b in bundle["operand_bindings"]):
        subject, other, axis = query, target, "model"
    interval = (sheet_row.get("intervals") or {}).get(axis) if family == "protein_domain" else (
        sheet_row.get("coordinates") or {}).get("sequence_interval")
    # Original sequence input bytes must agree with the displayed native segment.
    # A learned/model consensus never proves an original query segment.
    valid = subject is not None and subject.get("sequence") is not None and interval is not None
    if valid:
        aligned = sheet_row.get("alignment") or {}
        display = aligned.get("model" if axis == "model" else "aseq") if family == "protein_domain" else aligned.get("sequence_aligned")
        if display is not None:
            actual = subject["sequence"][interval[0]:interval[1]].upper()
            if facts.get("strand") == "-" and axis == "sequence":
                actual = actual.replace("U", "T").translate(str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN"))[::-1]
            displayed = "".join(c for c in display if c.isalpha() or c == "*").upper()
            if family == "nucleotide_locus":
                displayed, actual = displayed.replace("U", "T"), actual.replace("U", "T")
            valid = displayed == actual
        if interval[1] > subject["length"]:
            valid = False
    if program == "jackhmmer" and axis == "model" and not sheet_row.get("quantities", {}).get("actual_sequence_correspondence"):
        valid = False
    if subject is not None and not valid:
        diagnostics.append({"stage": "binding", "code": "native_hmmer_native_sequence_correspondence_invalid",
                            "record_key": key})
    return {"subject_operand": _binding(subject, bundle, diagnostics, key) if valid else None,
            "subject_interval": interval if valid else None,
            "related_operands": [_binding(other, bundle, diagnostics, key)] if other is not None else []}


def run(plan):
    directory = Path(plan["directory"])
    bundle, paths = plan["bundle"], plan["artifacts"]
    selector = validate_native_hmmer_result_selector(plan["selector"], program=bundle["program"])
    diagnostics = deepcopy(plan.get("failures", []))
    manifest = {"version": "native_hmmer_worker_result_v1", "sheet_schema": None, "scores_schema": None,
                "numerical_complete": False, "failures": []}
    try:
        records = _input_records(bundle, paths, diagnostics)
        inputs = _metadata_inputs(bundle, records, paths, diagnostics)
        artifacts, refs, checkpoints = {}, {}, []
        for item in paths:
            if item["kind"] != "output" or item["role"] == "stderr":
                continue
            try:
                text = Path(item["path"]).read_text(encoding="utf-8")
            except (UnicodeError, OSError) as error:
                diagnostics.append({"stage": "parse", "code": "native_hmmer_native_text_unreadable",
                    "record_key": None, "artifact_ref": item["artifact_ref"], "detail": str(error)})
                continue
            role = item["role"]
            if role in {"checkpoint_hmm", "checkpoint_msa"}:
                checkpoints.append({"role": "chkhmm" if role == "checkpoint_hmm" else "chkali",
                    "text": text, "artifact_ref": item["artifact_ref"]})
            elif role == "constructed_hmm" or role == "included_msa" and bundle["program"] in {"nhmmer", "nhmmscan"}:
                continue  # Complete custody remains in the bundle; no invented round join.
            else:
                artifacts[role], refs[role] = text, item["artifact_ref"]
        grading = grade_hmmer_native_artifacts(program=bundle["program"], artifacts=artifacts,
            artifact_refs=refs, engine_version=bundle["software"].get("declared_engine_version"),
            inputs=inputs, parameters=bundle["requested_job"]["native_hmmer"]["grading_parameters"], checkpoints=checkpoints)
        grading = _join_multiple_queries(grading, bundle, records, inputs)
        sheet, scores = grading["sheet"], grading["scores"]
        sheet["publication_inputs"] = {"supplied_metadata": deepcopy(bundle["requested_job"]["native_hmmer"]["metadata"]),
            "parsed_records": records, "bindings": deepcopy(bundle["operand_bindings"]),
            "captured_artifacts": [{k: v for k, v in row.items() if k != "path"} for row in paths]}
        family = selector["projection"]["family"]
        collection = COLLECTIONS[family]
        source_rows = {row["record_key"]: row for row in sheet[collection]}
        selection = selector["projection"]["rows"]
        wanted = selection.get("record_keys")
        found = set()
        with (directory / "selected-rows.ndjson").open("w", encoding="utf-8") as output:
            for ordinal, score in enumerate(scores[collection]):
                key = score.get("record_key")
                selected = key in wanted if wanted is not None else selection["offset"] <= ordinal < selection["offset"] + selection["limit"]
                if not selected:
                    continue
                found.add(key)
                sheet_row = source_rows[key]
                values, unavailable = projected_measurements(score, selector["projection"]["metrics"])
                all_values, _ = projected_measurements(score, NATIVE_HMMER_METRICS[family])
                try:
                    operands = _operands(bundle, records, sheet_row, score, diagnostics)
                except (ValueError, KeyError, TypeError) as error:
                    diagnostics.append({"stage": "binding", "code": "native_hmmer_operand_association_failed",
                        "record_key": key, "exception_type": type(error).__name__, "detail": str(error)})
                    operands = {"subject_operand": None, "subject_interval": None, "related_operands": []}
                row = {"version": "native_hmmer_selected_row_v1", "family": family, "native_ordinal": ordinal,
                    "record_key": key, "locator": deepcopy(score.get("locator")),
                    "query_occurrence": score.get("query_occurrence"), "target_occurrence": score.get("target_occurrence"),
                    "iteration": score.get("iteration"), "strand": score.get("strand"),
                    "invalid": score.get("status") == "invalid" or any(issue.get("code") in {
                        "hmmer_native_program_mismatch", "nhmmer_program_mismatch"} for issue in scores.get("issues", [])),
                    "measurements": values, "unavailable": unavailable,
                    "observation_measurements": all_values,
                    **operands}
                if family == "alignment_sequence":
                    row["target_occurrence"] = score.get("occurrence")
                output.write(json.dumps(row, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n")
        for missing in (wanted or []):
            if missing not in found:
                diagnostics.append({"stage": "selection", "code": "native_hmmer_selected_record_missing", "record_key": missing})
        for issue in scores.get("issues", []):
            diagnostics.append({"stage": "grading", "code": issue.get("code", "native_hmmer_grading_issue"),
                                "record_key": issue.get("record_key"), "detail": issue})
        for row in scores[collection]:
            for issue in row.get("issues", []):
                diagnostics.append({"stage": "grading", "code": issue.get("code", "native_hmmer_grading_issue"),
                                    "record_key": row["record_key"], "detail": issue})
        write_json(directory / "sheet.json", sheet)
        write_json(directory / "scores.json", scores)
        manifest.update(sheet_schema=sheet["schema"], scores_schema=scores["schema"], numerical_complete=not diagnostics)
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
        diagnostics.append({"stage": "grading", "code": "native_hmmer_grading_failed", "record_key": None,
                            "exception_type": type(error).__name__, "detail": str(error)})
    # Raw details stay on disk; only finite failure codes are returned to host.
    write_json(directory / "diagnostics.json", diagnostics)
    manifest["failures"] = list({(row["stage"], row["code"], row.get("record_key")):
        {"stage": row["stage"], "code": row["code"], "record_key": row.get("record_key")} for row in diagnostics}.values())
    write_json(directory / "worker-result.json", manifest)
    return manifest


def main():
    if len(sys.argv) != 2:
        raise SystemExit("native_hmmer_result_worker requires one retained plan path")
    with Path(sys.argv[1]).open(encoding="utf-8") as stream:
        run(json.load(stream))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
