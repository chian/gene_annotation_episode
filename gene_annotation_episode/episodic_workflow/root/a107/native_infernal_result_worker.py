"""Grade one already captured Infernal bundle, without acquisition or execution.

Only the paths in the capture plan are read. Native readers populate complete
sheets; independent calculators consume those sheets. Selection projects stored
quantities in native order and never changes the original grading parameters.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from .cmalign_inputs import parse_cmalign_stockholm, populate_cmalign_sheet
from .cmalign_grader import calculate_cmalign_scores
from .infernal_search_inputs import populate_infernal_search_sheet
from .infernal_search_grader import calculate_infernal_search_scores
from .infernal_search_contracts import validate_infernal_search_scores
from .infernal_native_result_views import (COLLECTIONS, NATIVE_INFERNAL_METRICS,
    projected_measurements, validate_native_infernal_result_selector)
from .native_infernal_contracts import (finite_json_copy, native_options,
    validate_native_infernal_job)


_BASES = frozenset("ACGTURYSWKMBDHVNXI")
_COMPACT = ("operand_role", "record_ordinal", "artifact_ref", "name", "accession",
    "kind", "alphabet", "length", "sequence_sha256", "locator")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False,
        allow_nan=False) + "\n", encoding="utf-8")


def _diagnostic(diagnostics, stage, code, record_key=None, *, incomplete=True, **detail):
    diagnostics.append({"stage": stage, "code": code, "record_key": record_key,
        "affects_completion": incomplete, **detail})


def _normal(sequence):
    return sequence.upper().replace("T", "U").replace("X", "N").replace("I", "A")


def _sequence_record(sequence, *, name, accession=None, **fields):
    return {"name": name, "accession": accession, "sequence": sequence,
        "sequence_sha256": hashlib.sha256(sequence.upper().encode("ascii")).hexdigest(),
        "length": len(sequence), "kind": "nucleotide_sequence",
        "alphabet": "rna" if "U" in sequence.upper() else "dna", **fields}


def _fasta(text):
    rows, current, offset = [], None, 0
    for number, raw in enumerate(text.splitlines(keepends=True), 1):
        line, end = raw.strip(), offset + len(raw.encode("utf-8"))
        if line.startswith(">"):
            if current is not None:
                rows.append(current)
            header = line[1:].strip()
            if not header:
                raise ValueError("native_infernal_fasta_name_missing")
            current = {"name": header.split()[0], "header": header, "sequence": "",
                "locator": {"line": number, "byte_start": offset, "byte_end": end}}
        elif line:
            if current is None:
                raise ValueError("native_infernal_fasta_header_required")
            sequence = "".join(line.split())
            if not set(sequence.upper()) <= _BASES:
                raise ValueError("native_infernal_fasta_symbols_invalid")
            current["sequence"] += sequence
            current["locator"]["byte_end"] = end
        offset = end
    if current is not None:
        rows.append(current)
    if not rows or any(not row["sequence"] for row in rows):
        raise ValueError("native_infernal_fasta_sequence_missing")
    return [_sequence_record(**row) for row in rows]


def _models(text):
    """Read CM/filter pairs, never counting the HMM filter as another CM."""
    rows, state, active, offset = [], "cm_header", None, 0
    for number, raw in enumerate(text.splitlines(keepends=True), 1):
        line, end = raw.strip(), offset + len(raw.encode("utf-8"))
        if not line or line.startswith("#"):
            offset = end
            continue
        token = line.split()[0]
        if state == "cm_header":
            if token != "INFERNAL1/a":
                raise ValueError("native_infernal_cm_header_required")
            active = {"fields": {}, "native_header": raw, "filter_header": "",
                "locator": {"line": number, "byte_start": offset}, "header_open": True}
            state = "cm_body"
        elif state == "filter_header":
            if re.fullmatch(r"HMMER3/[a-f]", token) is None:
                raise ValueError("native_infernal_cm_filter_required")
            active["filter_header"] = raw
            state = "filter_body"
        elif line == "//":
            if state == "cm_body":
                state = "filter_header"
            else:
                fields = active["fields"]
                if (not fields.get("NAME") or not re.fullmatch(r"[1-9][0-9]*", fields.get("CLEN", ""))
                        or fields.get("ALPH") not in {"RNA", "DNA"}):
                    raise ValueError("native_infernal_cm_identity_invalid")
                active["locator"]["byte_end"] = end
                rows.append({"name": fields["NAME"], "accession": fields.get("ACC"),
                    "length": int(fields["CLEN"]), "consensus_length": int(fields["CLEN"]),
                    "kind": "covariance_model", "alphabet": fields["ALPH"].lower(),
                    "sequence_sha256": None, "native_header": active["native_header"],
                    "filter_header": active["filter_header"], "locator": active["locator"]})
                state = "cm_header"
        elif token.startswith(("INFERNAL", "HMMER")) or "\0" in line:
            raise ValueError("native_infernal_model_block_unterminated")
        elif state == "cm_body" and active["header_open"]:
            if line == "CM":
                active["header_open"] = False
            else:
                active["native_header"] += raw
                parts = line.split(None, 1)
                if len(parts) == 2 and parts[0] in {"NAME", "ACC", "CLEN", "ALPH"}:
                    if parts[0] in active["fields"]:
                        raise ValueError("native_infernal_cm_duplicate_identity_field")
                    active["fields"][parts[0]] = parts[1].strip()
        elif state == "filter_body" and not line.startswith("HMM ") and not line.startswith("COMPO"):
            if token in {"NAME", "ACC", "LENG", "ALPH"}:
                active["filter_header"] += raw
        offset = end
    if not rows or state != "cm_header":
        raise ValueError("native_infernal_model_input_incomplete")
    return rows


def _stockholm_inputs(artifact):
    alignments = parse_cmalign_stockholm(artifact)
    if (len(alignments) != 1 or not alignments[0]["header_valid"] or not alignments[0]["complete"]
            or alignments[0]["issues"]):
        raise ValueError("native_infernal_mapali_input_invalid")
    rows = []
    for row in alignments[0]["rows"]:
        if not all(row[k] for k in ("geometry_valid", "symbols_valid", "identity_unambiguous")):
            raise ValueError("native_infernal_mapali_row_invalid")
        sequence = "".join(c for c in row["aligned_sequence"] if c.upper() in _BASES)
        accessions = {a["value"] for a in row["sequence_annotations"] if a["tag"] == "AC"}
        if len(accessions) > 1:
            raise ValueError("native_infernal_mapali_accession_ambiguous")
        rows.append(_sequence_record(sequence, name=row["name"],
            accession=next(iter(accessions)) if accessions else None,
            locator=deepcopy(row["locator"]), seed_record_key=row["record_key"],
            aligned_sequence=row["aligned_sequence"]))
    return rows


def _input_records(captured, text, diagnostics):
    records = []
    for descriptor in captured:
        if descriptor["kind"] != "input" or descriptor["role"] not in {"sequences", "models", "mapali"}:
            continue
        role, ref = descriptor["role"], descriptor["artifact_ref"]
        try:
            content = text[("input", role)]
            rows = (_fasta(content) if role == "sequences" else _models(content) if role == "models" else
                _stockholm_inputs({"artifact_id": ref, "format": "stockholm", "content": content, "complete": True}))
        except (KeyError, ValueError) as error:
            _diagnostic(diagnostics, "inputs", str(error) if isinstance(error, ValueError) else
                "native_infernal_captured_input_unreadable", operand_role=role, artifact_ref=ref)
            continue
        for ordinal, record in enumerate(rows):
            record.update(operand_role=role, record_ordinal=ordinal, artifact_ref=ref)
            record["locator"] = {**record["locator"], "artifact_id": ref, "record_ordinal": ordinal}
            records.append(record)
    return records


def _compare_metadata(job, records, diagnostics):
    """Actual captured bytes supply identity; contradictory assertions survive."""
    metadata = job["metadata"]
    for key, role in (("sequence_metadata", "sequences"), ("sequences", "sequences"),
            ("model_metadata", "models"), ("models", "models"), ("model", "models"),
            ("mapali_sequences", "mapali")):
        if key not in metadata:
            continue
        supplied = [metadata[key]] if key == "model" else metadata[key]
        if type(supplied) is not list:
            _diagnostic(diagnostics, "metadata", "native_infernal_metadata_list_required", metadata_key=key)
            continue
        for index, row in enumerate(supplied):
            context = {"metadata_key": key, "metadata_index": index}
            if type(row) is not dict:
                _diagnostic(diagnostics, "metadata", "native_infernal_metadata_object_required", **context)
                continue
            candidates = [r for r in records if r["operand_role"] == role]
            if "record_ordinal" in row:
                candidates = [r for r in candidates if type(row["record_ordinal"]) is int
                    and r["record_ordinal"] == row["record_ordinal"]]
            else:
                candidates = [r for r in candidates if row.get("name") == r["name"]
                    and (row.get("accession") is None or row["accession"] == r["accession"])]
            if len(candidates) != 1:
                _diagnostic(diagnostics, "metadata", "native_infernal_metadata_association_unresolved",
                    candidate_ordinals=[r["record_ordinal"] for r in candidates], **context)
                continue
            actual = candidates[0]
            for field in ("name", "accession", "sequence", "sequence_sha256", "length",
                    "consensus_length", "kind", "alphabet"):
                if field not in row:
                    continue
                left, right = row[field], actual.get(field)
                # Input metadata is checked against original sequence identity,
                # without applying native T/U, X/N or I/A digitization.
                if field == "sequence" and type(left) is str and type(right) is str:
                    left, right = left.upper(), right.upper()
                if field == "alphabet" and type(left) is str:
                    left = left.lower()
                if type(left) is not type(right) or left != right:
                    _diagnostic(diagnostics, "metadata", "native_infernal_supplied_metadata_conflict",
                        field=field, supplied=row[field], actual=actual.get(field),
                        operand_role=role, record_ordinal=actual["record_ordinal"], **context)


def _binding_map(job, records, diagnostics):
    result = {}
    for binding in job["operand_bindings"]:
        key = (binding["operand_role"], binding["record_ordinal"])
        matches = [r for r in records if (r["operand_role"], r["record_ordinal"]) == key]
        code = None
        if len(matches) != 1:
            code = "native_infernal_operand_binding_record_unavailable"
        elif binding["native_name"] is None and binding["native_accession"] is None:
            code = "native_infernal_operand_binding_identity_missing"
        elif any(binding[b] is not None and binding[b] != matches[0][r]
                for b, r in (("native_name", "name"), ("native_accession", "accession"))):
            code = "native_infernal_operand_binding_identity_conflict"
        if code:
            _diagnostic(diagnostics, "association", code, binding=deepcopy(binding))
        else:
            result[key] = deepcopy(binding)
    return result


def _compact(record, bindings, diagnostics, key):
    if record is None:
        return None
    result = {field: deepcopy(record.get(field)) for field in _COMPACT}
    result["binding"] = deepcopy(bindings.get((record["operand_role"], record["record_ordinal"])))
    if result["binding"] is None:
        _diagnostic(diagnostics, "association", "native_infernal_operand_binding_unavailable", key,
            incomplete=False, operand_role=record["operand_role"], record_ordinal=record["record_ordinal"])
    return result


def _operation(job):
    options = native_options(job)
    settings = {key: True if value is None else value for key, value in options.items()}
    settings["native_options"] = deepcopy(job["options"])
    settings["declared_engine_version"] = job["software"]["engine_version"]
    if job["program"] == "cmalign":
        settings.update({key: flag in options for key, flag in (("matchonly", "--matchonly"),
            ("global", "-g"), ("notrunc", "--notrunc"), ("sub", "--sub"),
            ("noprob", "--noprob"), ("miss", "--miss"))})
        settings["mapali"] = any(row["role"] == "mapali" for row in job["operands"])
        settings["algorithm"] = "sample" if "--sample" in options else "cyk" if "--cyk" in options else "optacc"
    version = job["software"]["engine_version"]
    if version is not None:
        match = re.match(r"^(\d+\.\d+\.\d+)(?:\s|$)", version)
        if match:
            version = match[1]
    return {"program": job["program"], "native_version": version, "settings": settings}


def _metadata(record):
    keys = ("name", "accession", "sequence", "length") if record["kind"] == "nucleotide_sequence" else (
        "name", "accession", "consensus_length", "native_header")
    return {k: deepcopy(record[k]) for k in keys if k in record}


def _alignment_metadata(records):
    # cmalign prepends mapali rows, then preserves new input order. The reader
    # checks sequence identity and sidecar associations before these are used.
    result, occurrences = [], Counter()
    for role in ("mapali", "sequences"):
        for record in records:
            if record["operand_role"] != role:
                continue
            result.append({**_metadata(record), "occurrence": occurrences[record["name"]],
                "origin": "inherited" if role == "mapali" else "newly_aligned"})
            occurrences[record["name"]] += 1
    return result


def _search_association(entity, records, role, diagnostics, key):
    join = (entity or {}).get("metadata_join") or {}
    rows = [r for r in records if r["operand_role"] == role]
    index = join.get("metadata_index")
    if (join.get("status") != "matched" or type(index) is not int or not 0 <= index < len(rows)):
        _diagnostic(diagnostics, "association", "native_infernal_search_input_association_unresolved", key,
            operand_role=role, native_identity=deepcopy(entity))
        return None
    record = rows[index]
    if (record["name"] != entity.get("name") or entity.get("accession") is not None
            and record["accession"] != entity["accession"]):
        _diagnostic(diagnostics, "association", "native_infernal_search_input_identity_conflict", key,
            operand_role=role, native_identity=deepcopy(entity))
        return None
    return record


def _alignment_association(row, records, diagnostics):
    key = row["record_key"]
    role = "mapali" if row.get("origin") == "inherited" else "sequences"
    candidates = [r for r in records if r["operand_role"] == role]
    raw = row.get("native") or {}
    index = raw.get("row_index")
    if type(index) is int and role == "sequences":
        index -= sum(r["operand_role"] == "mapali" for r in records)
    score, mapping = row.get("native_scores") or {}, row.get("mapping") or {}
    record = candidates[index] if type(index) is int and 0 <= index < len(candidates) else None
    valid = (record is not None and row.get("origin") in {"inherited", "newly_aligned"}
        and row.get("availability", {}).get("original_mapping") is True
        and row.get("name") == record["name"] and mapping.get("original_length") == record["length"])
    if valid and role == "sequences" and score.get("native_index") is not None:
        valid = score["native_index"] == record["record_ordinal"] + 1
    if valid and role == "mapali":
        join = row.get("inherited_join") or {}
        valid = (join.get("status") == "sequence_identity_verified"
            and join.get("seed_record_key") == record["seed_record_key"])
    if valid:
        positions = mapping.get("positions")
        retained = "".join(c for c in raw.get("aligned_sequence", "") if c.upper() in _BASES)
        valid = (type(positions) is list and all(type(p) is int and 1 <= p <= record["length"] for p in positions)
            and _normal(retained) == _normal("".join(record["sequence"][p-1] for p in positions)))
    if not valid:
        _diagnostic(diagnostics, "association", "native_infernal_alignment_input_association_unresolved", key,
            operand_role=role, output_row_index=raw.get("row_index"), native_index=score.get("native_index"))
        return None
    return record


def _intervals(positions):
    result = []
    for position in sorted(set(positions)):
        if result and result[-1][1] == position - 1:
            result[-1][1] = position
        else:
            result.append([position - 1, position])
    return result


def _selected_row(score, ordinal, family, metrics, sheet, records, bindings, diagnostics):
    key = score[{"search_hit": "hit_id", "search_sequence": "aggregate_id"}.get(family, "record_key")]
    measured, unavailable = projected_measurements(score, metrics, family=family)
    observation, _ = projected_measurements(score, NATIVE_INFERNAL_METRICS[family], family=family)
    result = {"version": "native_infernal_selected_row_v1", "family": family,
        "native_ordinal": ordinal, "record_key": key, "locator": deepcopy(score.get("locator")),
        "sequence_name": None, "model_name": None, "strand": score.get("strand"),
        "origin": score.get("origin"), "population": score.get("population"),
        "column_index": score.get("column_index"), "pair_columns": None,
        "invalid": score.get("status") == "invalid", "measurements": measured,
        "unavailable": unavailable, "observation_measurements": observation,
        "subject_operand": None, "subject_intervals": [], "related_operands": []}
    subject, related = None, []
    if family == "search_hit":
        subject = _search_association(score.get("sequence"), records, "sequences", diagnostics, key)
        model = _search_association(score.get("model"), records, "models", diagnostics, key)
        related = [model] if model else []
        result.update(sequence_name=score["sequence"]["name"], model_name=score["model"]["name"])
        if subject and score.get("sequence_interval") is not None:
            result["subject_intervals"] = [deepcopy(score["sequence_interval"])]
    elif family == "search_sequence":
        identity = score.get("sequence_identity") or {}
        rows = [r for r in records if r["operand_role"] == "sequences"]
        index = identity.get("metadata_index")
        if identity.get("kind") == "supplied_sequence_metadata" and type(index) is int and 0 <= index < len(rows):
            subject = rows[index]
        else:
            _diagnostic(diagnostics, "association", "native_infernal_aggregate_input_association_unresolved", key)
        hit_ids = set(score["hit_ids"])
        members = [r for r in sheet["hits"] if r["hit_id"] in hit_ids]
        result["locator"] = {"member_locators": [deepcopy(r["locator"]) for r in members]}
        result["sequence_name"] = subject["name"] if subject else (score["sequence_names"][0]
            if len(score["sequence_names"]) == 1 else None)
        result["population"] = score["hit_scope"]
        for hit in members:
            model = _search_association(hit["model"], records, "models", diagnostics, key)
            if model is not None and model not in related:
                related.append(model)
        if subject:
            result["subject_intervals"] = deepcopy(score["union_intervals"])
    else:
        models = [r for r in records if r["operand_role"] == "models"]
        if len(models) == 1 and sheet["model"]["valid"]:
            related = models
            result["model_name"] = models[0]["name"]
        if family == "alignment_sequence":
            row = next(r for r in sheet["sequences"] if r["record_key"] == key)
            subject = _alignment_association(row, records, diagnostics)
            result["sequence_name"] = score.get("name")
            if subject:
                result["subject_intervals"] = _intervals(row["mapping"]["positions"])
        else:
            alignment = next(r for r in sheet["alignments"] if r["record_key"] == score["alignment_key"])
            result["locator"] = {"artifact_id": alignment["artifact_id"],
                "alignment_index": alignment["alignment_index"], "column_index": score.get("column_index")}
            if family == "alignment_pair":
                result["pair_columns"] = [score["left_column"], score["right_column"]]
                result["locator"]["pair_columns"] = list(result["pair_columns"])
    result["subject_operand"] = _compact(subject, bindings, diagnostics, key)
    result["related_operands"] = [_compact(r, bindings, diagnostics, key) for r in related]
    return result


def run(plan):
    """Write a complete saved sheet, separate scores and exact requested rows."""
    plan = finite_json_copy(plan)
    if (type(plan) is not dict or set(plan) != {"version", "bundle", "artifacts", "directory", "selector", "failures"}
            or plan["version"] != "native_infernal_grading_plan_v1"):
        raise ValueError("native_infernal_grading_plan_required")
    directory = Path(plan["directory"])
    directory.mkdir(parents=True, exist_ok=True)
    diagnostics = deepcopy(plan["failures"])
    if type(diagnostics) is not list or any(type(r) is not dict for r in diagnostics):
        raise ValueError("native_infernal_plan_failures_invalid")
    manifest = {"version": "native_infernal_worker_result_v1", "sheet_schema": None,
        "scores_schema": None, "numerical_complete": False, "failures": []}
    sheet, scores, selected = None, None, []
    try:
        bundle = plan["bundle"]
        job = validate_native_infernal_job(bundle["requested_job"]["native_infernal"])
        if (bundle["program"] != job["program"] or bundle["table_format"] != job["table_format"]
                or bundle["operand_bindings"] != job["operand_bindings"]):
            raise ValueError("native_infernal_worker_bundle_request_conflict")
        selector = validate_native_infernal_result_selector(plan["selector"], program=job["program"])
        captured, text, seen = plan["artifacts"], {}, set()
        source_descriptors = {}
        if type(captured) is not list:
            raise ValueError("native_infernal_captured_artifacts_required")
        for row in captured:
            if (type(row) is not dict or set(row) != {"role", "format", "relative_path", "artifact_ref", "kind", "path"}
                    or row["kind"] not in {"input", "output"} or
                    any(type(row[k]) is not str or not row[k] for k in ("role", "format", "relative_path", "artifact_ref", "path"))):
                raise ValueError("native_infernal_captured_artifact_invalid")
            key = row["kind"], row["role"]
            if key in seen:
                raise ValueError("native_infernal_captured_role_duplicate")
            seen.add(key)
            originals = job["operands"] if row["kind"] == "input" else job["outputs"]
            matches = [r for r in originals if r["role"] == row["role"] and r["format"] == row["format"]]
            if len(matches) != 1 or row["kind"] == "output" and row["relative_path"] != matches[0]["relative_path"]:
                raise ValueError("native_infernal_captured_role_format_conflict")
            if row["format"].startswith("infernal_i1"):
                continue  # Already hash-validated binary input, not a numerical text source.
            try:
                raw = Path(row["path"]).read_bytes()
                if row["kind"] == "output" and row["format"] == "infernal_tblout":
                    original = [item for item in bundle["artifacts"]
                        if all(item.get(field) == row[field]
                            for field in ("role", "format", "relative_path"))]
                    actual_sha256 = hashlib.sha256(raw).hexdigest()
                    if (len(original) != 1 or original[0].get("sha256") != actual_sha256
                            or original[0].get("size_bytes") != len(raw)
                            or row["artifact_ref"].startswith("artifact_")
                            and row["artifact_ref"] != "artifact_" + actual_sha256):
                        _diagnostic(diagnostics, "reading", "native_infernal_captured_search_bytes_mismatch",
                            role=row["role"], kind=row["kind"])
                        continue
                    source_descriptors[key] = {"profile": "infernal_tblout", "source_ref": None,
                        "artifact_ref": row["artifact_ref"], "source_sha256": actual_sha256,
                        "source_byte_length": len(raw), "byte_hash_verified": True}
                text[key] = raw.decode("utf-8")
            except (OSError, UnicodeError) as error:
                _diagnostic(diagnostics, "reading", "native_infernal_captured_text_unreadable",
                    role=row["role"], kind=row["kind"], error_type=type(error).__name__)
        for row in [*job["operands"], *job["outputs"]]:
            kind = "input" if row in job["operands"] else "output"
            if (kind, row["role"]) not in seen:
                _diagnostic(diagnostics, "inputs" if kind == "input" else "outputs",
                    "native_infernal_captured_artifact_missing", role=row["role"], kind=kind)
        for failure in bundle.get("failures", []):
            _diagnostic(diagnostics, failure["stage"], failure["code"], **{
                k: deepcopy(v) for k, v in failure.items() if k not in {"stage", "code", "record_key"}})
        records = _input_records(captured, text, diagnostics)
        _compare_metadata(job, records, diagnostics)
        bindings = _binding_map(job, records, diagnostics)
        operation = _operation(job)
        artifacts = []
        for row in captured:
            if row["kind"] != "output" or ("output", row["role"]) not in text:
                continue
            if row["format"] not in {"infernal_tblout", "stockholm", "cmalign_sfile", "cmalign_ifile", "cmalign_elfile"}:
                continue
            if row["role"] == "included_msa":
                continue  # Retained descriptor; search spans do not become an alignment grader.
            artifact = {"artifact_id": row["artifact_ref"], "format": row["format"],
                "content": text[("output", row["role"])], "complete": bundle.get("returncode") == 0}
            if row["format"] == "infernal_tblout":
                artifact["table_format"] = job["table_format"]
                artifact["source_descriptor"] = source_descriptors[("output", row["role"])]
            artifacts.append(artifact)
        if job["program"] == "cmalign":
            models = [r for r in records if r["operand_role"] == "models"]
            if len(models) != 1:
                _diagnostic(diagnostics, "inputs", "native_infernal_cmalign_single_model_unavailable")
            inherited = next(({"artifact_id": r["artifact_ref"], "format": "stockholm",
                "content": text[("input", "mapali")], "complete": True} for r in captured
                if r["kind"] == "input" and r["role"] == "mapali" and ("input", "mapali") in text), None)
            sheet = populate_cmalign_sheet(artifacts, operation=operation,
                sequences=_alignment_metadata(records), model=_metadata(models[0]) if len(models) == 1 else None,
                inherited_alignment=inherited)
            calculator = calculate_cmalign_scores
        else:
            sheet = populate_infernal_search_sheet(artifacts, operation=operation,
                sequence_metadata=[{k: v for k, v in _metadata(r).items() if k != "sequence"}
                    for r in records if r["operand_role"] == "sequences"],
                model_metadata=[_metadata(r) for r in records if r["operand_role"] == "models"])
            calculator = calculate_infernal_search_scores
        sheet["publication_inputs"] = {"supplied_metadata": deepcopy(job["metadata"]),
            "parsed_records": records, "operand_bindings": deepcopy(job["operand_bindings"]),
            "captured_artifacts": [{k: deepcopy(v) for k, v in r.items() if k != "path"} for r in captured]}
        scores = calculator(sheet, parameters=deepcopy(job["grading_parameters"]))
        if job["program"] != "cmalign":
            validate_infernal_search_scores(scores, sheet=sheet)
        for stage, value in (("parsing", sheet), ("calculation", scores)):
            for issue in value["issues"]:
                qualified = (issue.get("severity") == "warning" or issue["code"] in {
                    "cmalign_insert_native_model_header_absent_supplied_mapali_association",
                    "cmalign_native_version_not_verified", "cmalign_duplicate_native_representation",
                    "aggregate_population_incomplete", "aggregate_denominator_unavailable",
                    "score_denominator_unavailable", "native_score_cell_unavailable",
                    "cmalign_ss_cons_unavailable"})
                _diagnostic(diagnostics, stage, issue["code"], issue.get("record_key", issue.get("hit_id")),
                    incomplete=not qualified, detail=deepcopy(issue))
            if value["status"] in {"missing", "invalid"}:
                _diagnostic(diagnostics, stage, "native_infernal_" + value["status"] + "_numerical_data")
        projection = selector["projection"]
        family, choice = projection["family"], projection["rows"]
        key_field = {"search_hit": "hit_id", "search_sequence": "aggregate_id"}.get(family, "record_key")
        candidates = scores[COLLECTIONS[family]]
        keys = {row[key_field] for row in candidates}
        if "record_keys" in choice:
            for key in choice["record_keys"]:
                if key not in keys:
                    _diagnostic(diagnostics, "selection", "native_infernal_requested_record_key_missing", key)
        for ordinal, score in enumerate(candidates):
            include = score[key_field] in choice["record_keys"] if "record_keys" in choice else (
                choice["offset"] <= ordinal < choice["offset"] + choice["limit"])
            if include:
                selected.append(_selected_row(score, ordinal, family, projection["metrics"],
                    sheet, records, bindings, diagnostics))
        manifest.update(sheet_schema=sheet["schema"], scores_schema=scores["schema"],
            numerical_complete=not any(r.get("affects_completion", True) for r in diagnostics))
    except (ValueError, KeyError, TypeError, IndexError) as error:
        _diagnostic(diagnostics, "worker", str(error) if isinstance(error, ValueError)
            else "native_infernal_worker_input_contract_invalid", error_type=type(error).__name__)
    # Keep a successfully populated sheet if a later calculation/selection fails.
    manifest["sheet_schema"] = sheet.get("schema") if sheet else None
    manifest["scores_schema"] = scores.get("schema") if scores else None
    manifest["failures"] = [{"stage": r.get("stage", "capture"), "code": r.get("code", "native_infernal_capture_failure"),
        "record_key": r.get("record_key")} for r in diagnostics if r.get("affects_completion", True)]
    write_json(directory / "sheet.json", sheet)
    write_json(directory / "scores.json", scores)
    with (directory / "selected-rows.ndjson").open("w", encoding="utf-8") as stream:
        for row in selected:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    write_json(directory / "diagnostics.json", diagnostics)
    write_json(directory / "worker-result.json", manifest)
    return manifest


def main(argv=None):
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise ValueError("native_infernal_exact_grading_plan_required")
    with Path(arguments[0]).open(encoding="utf-8") as stream:
        result = run(json.load(stream))
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
