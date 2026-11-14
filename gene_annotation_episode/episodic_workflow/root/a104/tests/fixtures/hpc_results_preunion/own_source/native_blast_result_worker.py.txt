"""Bounded deterministic grading of complete, captured paired BLAST artifacts.

The worker reads only supplied captured paths. It never launches a scientific
program, contacts a service, selects a resource or invokes a model. The native
collector, numerical sheet population and calculator remain separate functions.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

from Bio.Seq import Seq

from .blast_pairwise_grader import alignment_component_artifacts, validate_blast_correspondence_instance, _axis_geometry
from .alignment_correspondence import ARTIFACT_SCHEMA, validate_correspondence_artifacts, _same
from .blast_pairwise_result_views import (NATIVE_BLAST_METRICS, projected_measurements,
                                         validate_native_blast_result_selector)
from .blast_pairwise_results import populate_blast_pairwise_sheet, calculate_blast_pairwise_components
from .blast_report_collection import parse_blast_report_collection
from .blast_search import PROGRAM_UNITS
from .domain import identity, parse_sequences
from .native_blast_contracts import _options


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".writing")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, allow_nan=False, sort_keys=True, separators=(",", ":"))
        stream.write("\n")
    temporary.replace(path)


def record_key(bundle, search_key, family, hit_ordinal=None, hsp_ordinal=None):
    return identity("native_blast_pairwise_row", {"bundle_identity": bundle["identity"],
        "search_key": search_key, "family": family,
        "hit_ordinal": hit_ordinal, "hsp_ordinal": hsp_ordinal})


def metric_definitions():
    """Document concrete inputs/denominators without a second scoring language."""
    return {
        "native_score_bits": "Exact native HSP bit_score in bits; no HSP summation.",
        "native_raw_score": "Exact native HSP score in the selected program's score units.",
        "native_evalue": "Exact native HSP evalue, expected count; retained and unused as paired relevance.",
        "alignment_columns": "Shared HSP counts.alignment_columns, all reported/traceback alignment columns.",
        "paired_positions": "Shared HSP counts.paired_columns, columns with both residues present.",
        "identical_positions": "Shared HSP counts.identical_pairs, equal paired symbols.",
        "substituted_positions": "paired_columns - identical_pairs when both are established.",
        "query_gap_columns": "Shared HSP counts.query_gap_columns from the actual traceback.",
        "reference_gap_columns": "Shared HSP counts.reference_gap_columns from the actual traceback.",
        "query_aligned_positions": "Shared HSP counts.paired_query_positions in original query units; translated residues span three nt; excludes gaps.",
        "reference_aligned_positions": "Shared HSP counts.paired_reference_positions in original reference units; translated residues span three nt; excludes gaps.",
        "query_length": "Length of the complete captured query FASTA sequence in its original units.",
        "reference_length": "Length of the complete captured reference FASTA sequence in its original units.",
        "paired_identity": "HSP identical_pairs / paired_columns; union identical distinct pairs / distinct pairs, unavailable when mappings conflict or denominator is zero.",
        "alignment_identity": "HSP identical_pairs / alignment_columns; reported percentages stay distinguished in complete components when traceback is absent.",
        "query_paired_coverage": "HSP paired query positions / actual full query length; union of observed paired query positions / actual full query length.",
        "reference_paired_coverage": "HSP paired reference positions / actual full reference length; union of observed paired reference positions / actual full reference length.",
        "observed_distinct_residue_pairs": "Shared union counts.distinct_residue_pairs from usable retained HSP geometry, not an inferred complete global alignment.",
        "observed_identical_residue_pairs": "Shared union counts.identical_residue_pairs; unavailable for conflicted identity or no defined pairs.",
        "observed_paired_query_positions": "Shared union counts.paired_query_positions, merging overlapping original query intervals.",
        "observed_paired_reference_positions": "Shared union counts.paired_reference_positions, merging overlapping original reference intervals.",
        "hsps_with_geometry": "Shared union counts.hsps_with_geometry, number of retained HSPs with validated geometry.",
        "hsps_without_geometry": "Shared union counts.hsps_without_geometry, number of retained HSPs lacking validated geometry.",
        "query_selected_length": "selected_operand_coverage.query.denominator: explicit query_loc width, otherwise full query length.",
        "reference_selected_length": "selected_operand_coverage.reference.denominator: explicit subject_loc width, otherwise full reference length.",
        "query_selected_paired_positions": "selected_operand_coverage.query.numerator; unavailable if the retained reported geometry is incomplete, except established complete zero-hit output gives zero.",
        "reference_selected_paired_positions": "selected_operand_coverage.reference.numerator with the same completeness qualification.",
        "query_selected_paired_coverage": "selected_operand_coverage.query.value = its numerator / its explicit selected denominator.",
        "reference_selected_paired_coverage": "selected_operand_coverage.reference.value = its numerator / its explicit selected denominator.",
        "conflicting_mapping_count": "Length of the shared union.conflicts list; diagnostic mappings, not independent evidence or confidence.",
        "identical_mapping_group_count": "Length of shared union.identical_mapping_hsp_groups; repeated representations, not independent evidence.",
        "missingness": "No uncertainty estimate is inferred. Missing inputs, incompatible inputs, invalid rows and unmeasured quantities retain separate closed reasons. Complete source quantities, original lexemes, geometry and diagnostics remain in the sheet/components.",
    }


def _failure(diagnostics, stage, code, key=None, **details):
    diagnostics.append({"stage": stage, "code": code, "record_key": key, **details})


def _input_records(bundle, paths, snapshots, diagnostics):
    units = PROGRAM_UNITS[bundle["program"]]
    options = _options(bundle["requested_job"]["native_blast"])
    records = {}
    for axis, role, unit, flag in (("query", "query_sequence", units[0], "-query_loc"),
                                   ("reference", "subject_sequence", units[1], "-subject_loc")):
        items = [row for row in paths if row["kind"] == "input" and row["role"] == role]
        if len(items) != 1:
            _failure(diagnostics, "inputs", "native_blast_captured_operand_missing", role=role)
            continue
        item = items[0]
        binding = next((b for b in bundle["operand_bindings"] if b["operand_role"] == role), None)
        snapshot = snapshots.get((binding or {}).get("subject_ref") if axis == "query" else
                                 (binding or {}).get("reference_ref"))
        molecule = "protein" if unit == "aa" else "dna"
        if snapshot and snapshot.get("molecule") in {"dna", "rna"} and unit == "nt":
            molecule = snapshot["molecule"]
        try:
            parsed = parse_sequences(Path(item["path"]).read_bytes(), format="fasta", molecule=molecule)
            if len(parsed) != 1:
                raise ValueError("native_blast_single_fasta_operand_required")
            source = parsed[0]
            if "unexpected_symbol_for_declared_molecule" in source.issues:
                raise ValueError("native_blast_fasta_molecule_conflict")
            interval = options.get(flag)
            interval = [int(interval.split("-")[0]) - 1, int(interval.split("-")[1])] if interval else None
            if interval and interval[1] > len(source.sequence):
                raise ValueError("native_blast_selected_interval_outside_operand")
            native_title = source.name + (" " + source.description if source.description else "")
            row = {"axis": axis, "operand_role": role, "record_ordinal": 0,
                "artifact_ref": item["artifact_ref"], "artifact_key": item["relative_path"],
                "native_id": source.name, "native_title": native_title,
                "sequence": source.sequence, "sequence_sha256": hashlib.sha256(source.sequence.encode("ascii")).hexdigest(),
                "molecule": molecule, "length": len(source.sequence), "selected_interval": interval,
                "binding": binding, "binding_error": None}
            if binding:
                if (binding["native_name"] is None and binding["native_accession"] is None
                        or binding["native_name"] is not None and binding["native_name"] != source.name
                        or binding["native_accession"] is not None and binding["native_accession"] != source.name
                        or axis == "query" and binding["reference_ref"] is not None
                        or axis == "reference" and binding["subject_ref"] is not None):
                    row["binding_error"] = "native_blast_operand_binding_identity_mismatch"
                supplied = binding["subject_ref"] if axis == "query" else binding["reference_ref"]
                if supplied is not None:
                    if not snapshot or snapshot.get("error"):
                        row["binding_error"] = (snapshot or {}).get("error") or "native_blast_store_binding_unavailable"
                    elif (snapshot["length"] != row["length"] or snapshot["molecule"] != molecule
                          or snapshot["sequence_sha256"] != row["sequence_sha256"]):
                        row["binding_error"] = "native_blast_subject_sequence_mismatch"
                    elif axis == "reference" and (snapshot["record_type"] != "reference"
                            or snapshot["accession"] != source.name):
                        row["binding_error"] = "native_blast_reference_binding_identity_mismatch"
            records[axis] = row
            if row["binding_error"]:
                _failure(diagnostics, "binding", row["binding_error"], role=role)
        except (ValueError, OSError, UnicodeError) as error:
            _failure(diagnostics, "inputs", str(error), role=role)
    return records


def _invocation(bundle, records):
    options = _options(bundle["requested_job"]["native_blast"])
    operands, bindings = [], {}
    for axis, row in records.items():
        binding = row["binding"] or {}
        ref = binding.get("subject_ref") if axis == "query" else binding.get("reference_ref")
        descriptor = {"subject_ref": ref, **{key: row[key] for key in
            ("length", "molecule", "artifact_key", "native_id", "selected_interval")}}
        bindings[axis] = descriptor
        operands.append({"role": "query" if axis == "query" else "subject", **descriptor,
            "record_ordinal": 0, "native_title": row["native_title"],
            "identity": {"namespace": "sequence_sha256", "value": row["sequence_sha256"], "version": None}})
    return {"execution_program": bundle["program"], "scientific_mode": "pairwise", "resource_kind": "local",
        "query_kind": "sequence", "reference_kind": "sequence", "request": bundle["requested_job"],
        "effective_options": {**options,
            "requested_hit_limit": int(options["-max_target_seqs"]) if "-max_target_seqs" in options else None,
            "requested_hsp_limit": int(options["-max_hsps"]) if "-max_hsps" in options else None},
        "operands": operands, "completion": {"native_returncode": bundle["returncode"],
            "producer_complete": bundle["returncode"] == 0 and not bundle["failures"]}}, bindings


def _hsp_values(component, common=None, *, archived_values=None):
    if component is None:
        return {}
    if common is None:
        if archived_values is None:
            raise ValueError("native_blast_common_hsp_components_required")
        # Explicit v1 read only: the archived result is already a frozen fact.
        # Legacy component envelopes did not contain this calculated cell.
        counts, scores = component["counts"], component["native_scores"]
        values = {name: scores[source] for name, source in (("native_score_bits", "bit_score"),
            ("native_raw_score", "score"), ("native_evalue", "evalue"))}
        values.update({name: counts.get(source) for name, source in (
            ("alignment_columns", "alignment_columns"), ("paired_positions", "paired_columns"),
            ("identical_positions", "identical_pairs"), ("query_gap_columns", "query_gap_columns"),
            ("reference_gap_columns", "reference_gap_columns"), ("query_aligned_positions", "paired_query_positions"),
            ("reference_aligned_positions", "paired_reference_positions"))})
        values["substituted_positions"] = archived_values["substituted_positions"]
        values.update({name: component["denominators"][name] for name in ("query_length", "reference_length")})
        values.update(component["fractions"])
        return values
    counts, scores = common["counts"], component["native_scores"]
    values = {name: scores[source] for name, source in (("native_score_bits", "bit_score"),
              ("native_raw_score", "score"), ("native_evalue", "evalue"))}
    values.update({name: counts.get(source) for name, source in (
        ("alignment_columns", "alignment_columns"), ("paired_positions", "paired_positions"),
        ("identical_positions", "identical_positions"), ("substituted_positions", "substituted_positions"),
        ("query_gap_columns", "query_gap_columns"), ("reference_gap_columns", "reference_gap_columns"))})
    values.update({axis + "_aligned_positions": common["paired_units"][axis] for axis in ("query", "reference")})
    values.update({name: component["denominators"][name] for name in ("query_length", "reference_length")})
    values.update(component["fractions"])
    return values


def _union_values(components, records, common=None):
    values = {axis + "_length": row["length"] for axis, row in records.items()}
    if components is None:
        return values
    union = components["union"]
    # An unreadable/absent report has no successful observed zero counts.
    if components["status"] != "alignment_report_unavailable":
        values.update({"observed_" + name: union["counts"][name] for name in (
            "distinct_residue_pairs", "identical_residue_pairs", "paired_query_positions", "paired_reference_positions")})
        values.update({name: union["counts"][name] for name in ("hsps_with_geometry", "hsps_without_geometry")})
        values.update({name: common["union"]["counts"][name] for name in
            ("conflicting_mapping_count", "identical_mapping_group_count")})
    values.update(union["fractions"])
    for axis, row in components["selected_operand_coverage"].items():
        values.update({axis + "_selected_" + target: row[source] for target, source in (
            ("length", "denominator"), ("paired_positions", "numerator"), ("paired_coverage", "value"))})
    return values


def _traceback_intervals(native, component, records, program, format_name, options):
    if component is None or not component["geometry_available"]:
        raise ValueError("native_blast_hsp_geometry_unavailable")
    units = PROGRAM_UNITS[program]
    intervals = {}
    for axis, prefix, unit, gencode in (("query", "query", units[0], "-query_gencode"),
                                       ("reference", "hit", units[1], "-db_gencode")):
        row = records[axis]
        geometry = _axis_geometry(native, prefix=prefix, length=row["length"], coordinate_unit=unit,
            alignment_unit=units[2], issues=[], symbols=native["qseq" if axis == "query" else "hseq"],
            coordinate_convention="blast_json2" if format_name == "json2" else "directional")
        if geometry is None:
            raise ValueError("native_blast_hsp_geometry_unavailable")
        start, end, width, direction = geometry
        interval = [min(start, end) - 1, max(start, end)]
        selected = row["selected_interval"] or [0, row["length"]]
        if not selected[0] <= interval[0] < interval[1] <= selected[1]:
            raise ValueError("native_blast_hsp_outside_selected_interval")
        sequence = row["sequence"][interval[0]:interval[1]]
        if direction < 0:
            sequence = str(Seq(sequence).reverse_complement())
        if width == 3:
            sequence = str(Seq(sequence).translate(table=int(options.get(gencode, 1))))
        displayed = native["qseq" if axis == "query" else "hseq"].replace("-", "").upper()
        if unit == "nt" and width == 1:
            sequence, displayed = sequence.replace("U", "T"), displayed.replace("U", "T")
        if sequence != displayed:
            raise ValueError("native_blast_traceback_sequence_mismatch:" + axis)
        intervals[axis] = interval
    return intervals


def _row(bundle, search, family, records, values, *, hit=None, hsp=None,
         native_status="alignment_report_unavailable", invalid=False, intervals=None):
    units = PROGRAM_UNITS[bundle["program"]]
    key = record_key(bundle, search["search_key"], family, hit, hsp)
    missing = {}
    for name in NATIVE_BLAST_METRICS[family]:
        if values.get(name) is None:
            missing[name] = ("invalid_native_row" if invalid else "missing_input"
                if (name.startswith("query_") and "query" not in records or
                    name.startswith("reference_") and "reference" not in records)
                else "incompatible_input" if native_status == "partial" else "not_measured")
    return {"version": "native_blast_complete_row_v1", "family": family,
        "record_key": key, "search_key": search["search_key"], "hit_ordinal": hit, "hsp_ordinal": hsp,
        "program": bundle["program"], "coordinate_units": dict(zip(("query", "reference", "alignment"), units)),
        "native_status": native_status, "invalid": invalid,
        "values": values, "unavailable": missing,
        "operands": {axis: {k: deepcopy(v) for k, v in operand.items() if k != "sequence"}
                     for axis, operand in records.items()}, "intervals": intervals}


def validate_native_blast_correspondence_collections(sheet, scores, *, admission=False):
    """Authenticate the explicit new collection companion without frozen regrading."""
    if (set(sheet) != {"schema", "collection", "searches", "publication_inputs", "correspondence"}
            or sheet["schema"] != "native_blast_sheet_collection_v2"
            or set(scores) != {"schema", "searches", "rows", "metric_definitions", "correspondence", "fallback_hsp_components"}
            or scores["schema"] != "native_blast_scores_collection_v2"
            or not _same(sheet["correspondence"], scores["correspondence"])):
        raise ValueError("native_blast_correspondence_collections_required")
    companion = validate_correspondence_artifacts(scores["correspondence"], admission=admission)
    expected = {}
    for index, entry in enumerate(scores["searches"]):
        if entry["scores"] is not None:
            expected["/searches/" + str(index) + "/scores/components"] = entry["scores"]["components"]
    for index, entry in enumerate(scores["fallback_hsp_components"]):
        expected["/fallback_hsp_components/" + str(index) + "/component"] = entry["component"]
    if {instance["legacy_pointer"] for instance in companion["instances"]} != set(expected):
        raise ValueError("native_blast_correspondence_instances_conflict")
    for instance in companion["instances"]:
        if instance["axis_basis"] != "qualified":
            raise ValueError("native_blast_correspondence_axis_conflict")
        validate_blast_correspondence_instance(expected[instance["legacy_pointer"]], instance)


def run(plan):
    if plan.get("version") != "native_blast_grading_plan_v2":
        raise ValueError("native_blast_grading_plan_v2_required")
    directory = Path(plan["directory"])
    bundle, paths = plan["bundle"], plan["artifacts"]
    selector = validate_native_blast_result_selector(plan["selector"], program=bundle["program"])
    diagnostics = deepcopy(plan.get("failures", []))
    rows = {family: [] for family in NATIVE_BLAST_METRICS}
    correspondence = {"version": ARTIFACT_SCHEMA, "instances": []}
    sheet = {"schema": "native_blast_sheet_collection_v2", "collection": None,
             "searches": [], "publication_inputs": {}, "correspondence": correspondence}
    scores = {"schema": "native_blast_scores_collection_v2", "searches": [], "rows": rows,
              "metric_definitions": metric_definitions(), "correspondence": correspondence,
              "fallback_hsp_components": []}
    try:
        records = _input_records(bundle, paths, plan.get("binding_snapshots", {}), diagnostics)
        for axis, record in records.items():
            (directory / ("sequence-" + axis + ".txt")).write_text(record["sequence"], encoding="ascii")
        invocation, bindings = _invocation(bundle, records)
        contents, artifacts = {}, []
        outputs = {(r["role"], r["relative_path"]): r for r in bundle["requested_job"]["native_blast"]["outputs"]}
        for item in paths:
            if item["kind"] != "output" or item["role"] not in {"primary_report", "tabular_report"}:
                continue
            original = outputs[(item["role"], item["relative_path"])]
            key = item["relative_path"]
            contents[key] = Path(item["path"]).read_bytes()
            artifacts.append({"artifact_key": key, **{field: original[field]
                for field in ("role", "format", "fields", "delimiter")}})
        if not artifacts:
            _failure(diagnostics, "parse", "native_blast_report_unavailable")
        collection = parse_blast_report_collection(contents, artifacts=artifacts, invocation=invocation)
        sheet.update(collection=collection, publication_inputs={"records": records,
            "binding_snapshots": plan.get("binding_snapshots", {}),
            "captured_artifacts": [{k: v for k, v in row.items() if k != "path"} for row in paths]})
        for issue in collection["issues"]:
            _failure(diagnostics, "parse", issue["code"], detail=issue)
        options = _options(bundle["requested_job"]["native_blast"])
        for search in collection["searches"]:
            populated, calculated, error_code = None, None, None
            try:
                populated = populate_blast_pairwise_sheet(search, operand_bindings=bindings)
                calculated = calculate_blast_pairwise_components(populated, _retain_correspondence=True)
                companion = calculated.pop("correspondence")
                validate_correspondence_artifacts(companion, admission=True)
                validate_blast_correspondence_instance(calculated["components"], companion["instances"][0])
                instance = companion["instances"][0]
                instance["legacy_pointer"] = "/searches/" + str(len(scores["searches"])) + "/scores/components"
                correspondence["instances"].append(instance)
            except (ValueError, KeyError, TypeError) as error:
                calculated = None
                error_code = str(error)
                _failure(diagnostics, "grading", error_code)
            sheet["searches"].append({"search_key": search["search_key"], "sheet": populated, "failure": error_code})
            scores["searches"].append({"search_key": search["search_key"], "scores": calculated, "failure": error_code})
            components = calculated["components"] if calculated else None
            common = instance["components"] if calculated else None
            native_status = components["status"] if components else "partial"
            normalized = search["normalized"]
            by_ordinal = {}
            for native_hit, mapping in zip(normalized["hits"], search["row_map"]):
                for index, (native, ordinal) in enumerate(zip(native_hit["hsps"], mapping["hsp_ordinals"])):
                    common_row = None
                    if components:
                        comp, common_row = components["hsps"][index]["components"], common["rows"][index]
                    elif search["program_context"]["geometry_program"] is not None:
                        comp, common_sheet, common_components = alignment_component_artifacts(native, program=bundle["program"],
                            query_length=records.get("query", {}).get("length"),
                            reference_length=records.get("reference", {}).get("length"),
                            coordinate_convention="blast_json2" if normalized["format"] == "json2" else "directional")
                        fallback_index = len(scores["fallback_hsp_components"])
                        scores["fallback_hsp_components"].append({"search_key": search["search_key"],
                            "hit_ordinal": mapping["hit_index"], "hsp_ordinal": ordinal, "component": comp})
                        correspondence["instances"].append({"legacy_pointer": "/fallback_hsp_components/" + str(fallback_index) + "/component",
                            "axis_basis": "qualified", "sheet": common_sheet, "components": common_components})
                        common_row = common_components["rows"][0]
                    else:
                        comp = None
                    by_ordinal[(mapping["hit_index"], ordinal)] = native, comp, common_row
            # Original malformed HSP objects retain their ordinal and local failure.
            if normalized["format"] == "json2":
                native_hits = search["native"]["search"].get("hits")
                for hit_index, hit in enumerate(native_hits if isinstance(native_hits, list) else []):
                    if isinstance(hit, dict) and isinstance(hit.get("hsps"), list):
                        for ordinal, native in enumerate(hit["hsps"]):
                            by_ordinal.setdefault((hit_index, ordinal), (native, None, None))
            for (hit, hsp), (native, comp, common_row) in sorted(by_ordinal.items()):
                key = record_key(bundle, search["search_key"], "pairwise_hsp", hit, hsp)
                intervals, invalid = None, bool(error_code or comp is None or comp["issues"])
                try:
                    intervals = _traceback_intervals(native, comp, records, bundle["program"], normalized["format"], options)
                except (ValueError, KeyError, TypeError) as error:
                    _failure(diagnostics, "binding", str(error), key)
                    invalid = True
                if comp:
                    for issue in comp["issues"]:
                        _failure(diagnostics, "grading", issue["code"], key, detail=issue)
                rows["pairwise_hsp"].append(_row(bundle, search, "pairwise_hsp", records,
                    _hsp_values(comp, common_row), hit=hit, hsp=hsp, native_status=native_status,
                    invalid=invalid, intervals=intervals))
            union_key = record_key(bundle, search["search_key"], "pairwise_union")
            rows["pairwise_union"].append(_row(bundle, search, "pairwise_union", records,
                _union_values(components, records, common), native_status=native_status, invalid=bool(error_code)))
            for issue in (components["issues"] if components else search["issues"]):
                # Alternative correspondences are retained scientific facts,
                # not failures to compute each HSP or observed union counts.
                # An unavailable requested aggregate is qualified below.
                _failure(diagnostics, "grading", issue["code"], union_key, detail=issue,
                    diagnostic_only=issue["code"] in {"alternative_residue_mapping", "identity_at_correspondence_conflicts"})
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
        _failure(diagnostics, "grading", "native_blast_grading_failed", detail=str(error), exception_type=type(error).__name__)
    # Complete artifacts are independent of paging and requested metric choices.
    validate_native_blast_correspondence_collections(sheet, scores, admission=True)
    write_json(directory / "sheet.json", sheet)
    write_json(directory / "scores.json", scores)
    with (directory / "complete-rows.ndjson").open("w", encoding="utf-8") as output:
        for family_rows in rows.values():
            for row in family_rows:
                output.write(json.dumps(row, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n")
    projection = selector["projection"]
    selection, found = projection["rows"], set()
    wanted = selection.get("record_keys")
    with (directory / "selected-rows.ndjson").open("w", encoding="utf-8") as output:
        for ordinal, row in enumerate(rows[projection["family"]]):
            if not (row["record_key"] in wanted if wanted is not None else
                    selection["offset"] <= ordinal < selection["offset"] + selection["limit"]):
                continue
            found.add(row["record_key"])
            values, unavailable = projected_measurements(row, projection["metrics"])
            if unavailable:
                _failure(diagnostics, "selection", "native_blast_requested_measurements_unavailable", row["record_key"])
            selected = {"version": "native_blast_selected_row_v1", "family": projection["family"],
                        "record_key": row["record_key"], "native_ordinal": ordinal,
                        "measurements": values, "unavailable": unavailable}
            output.write(json.dumps(selected, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n")
    for key in wanted or []:
        if key not in found:
            _failure(diagnostics, "selection", "native_blast_selected_record_missing", key)
    write_json(directory / "diagnostics.json", diagnostics)
    failures = list({(r["stage"], r["code"], r["record_key"]):
        {key: r[key] for key in ("stage", "code", "record_key")} for r in diagnostics
        if not r.get("diagnostic_only")}.values())
    manifest = {"version": "native_blast_worker_result_v2", "sheet_schema": sheet["schema"],
                "scores_schema": scores["schema"], "failures": failures,
                "numerical_complete": bool(sheet["collection"] and sheet["collection"]["searches"])
                    and bundle["returncode"] == 0 and not failures}
    write_json(directory / "worker-result.json", manifest)
    return manifest


def main():
    if len(sys.argv) != 2:
        raise SystemExit("native_blast_result_worker requires one retained plan path")
    with Path(sys.argv[1]).open(encoding="utf-8") as stream:
        run(json.load(stream))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
