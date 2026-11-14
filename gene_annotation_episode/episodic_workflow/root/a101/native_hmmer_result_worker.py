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

from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_graders import grade_hmmer_native_artifacts
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_native_result_views import NATIVE_HMMER_METRICS, family_for_program, projected_measurements, validate_native_hmmer_result_selector
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmalign_inputs import parse_hmmalign_stockholm
from gene_annotation_episode.episodic_workflow.root.a101.library.native_hmmer_worker_values import _alphabet, _digest, _fasta, _join_multiple_queries, _meta, _operands, _profiles, _query_role, _stockholm


COLLECTIONS = {"protein_domain": "domains", "nucleotide_locus": "loci", "alignment_sequence": "sequences"}


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".writing")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, allow_nan=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
    temporary.replace(path)












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
