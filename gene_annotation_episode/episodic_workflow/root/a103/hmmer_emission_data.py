"""Pure hmmemit generated-data sheet, frozen 261/E1.

Inputs are supplied bytes and the exact M1 extraction of the supplied model
occurrence. No acquisition, native execution, biological observations or scores
are created. FASTA has no observed model coordinates. Stockholm coordinates are
one-based alignment columns and ungapped residue ordinals; byte locators are
zero-based half-open and line locators one-based inclusive.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import re

from .hmmer_model_data import ALPHABETS, _occurrence_valid, extract_hmmer_models
from .hmmalign_inputs import iter_hmmalign_stockholm_records


SCHEMA = "hmmer_emission_sheet_v1"
MODES = frozenset({"sample_core_unaligned", "sample_core_aligned",
                   "consensus_simple", "consensus_thresholded", "sample_profile"})
ISSUE_CODES = frozenset({
    "operation_invalid", "payload_map_invalid", "payload_invalid",
    "occurrence_invalid", "occurrence_role_mismatch", "occurrence_duplicate",
    "occurrence_size_mismatch", "occurrence_digest_mismatch", "capture_incomplete",
    "models_payload_count", "model_extraction_mismatch", "model_population_unavailable",
    "model_name_unavailable", "generated_output_missing", "output_role_incompatible",
    "text_encoding_invalid", "fasta_orphan_line", "fasta_header_invalid",
    "sequence_symbols_invalid", "sequence_incomplete", "stockholm_invalid",
    "association_unresolved", "association_conflicting", "population_incomplete",
    "setting_invalid",
})
_SEQUENCE = re.compile(r"[A-Za-z.*_~\-]*\Z")


def _issue(code, *, occurrence_id=None, record_key=None, field=None, details=None):
    assert code in ISSUE_CODES
    return {"code": code, "stage": "extraction", "occurrence_id": occurrence_id,
            "record_key": record_key, "field": field, "details": details or {}}


def _name(model):
    headers = [h for h in model.get("headers", []) if h.get("tag") == "NAME"]
    if len(headers) == 1 and len(headers[0].get("tokens", [])) == 1:
        return headers[0]["value"]
    return None


def _locator(occurrence, start, end, line_start, line_end, ordinal):
    return {"artifact_ref": occurrence["artifact_ref"], "byte_start": start,
            "byte_end": end, "line_start": line_start, "line_end": line_end,
            "record_ordinal": ordinal}


def _lines(content, occurrence):
    offset = 0
    rows = []
    for ordinal, raw in enumerate(content.splitlines(keepends=True)):
        text = raw.decode("utf-8", errors="surrogateescape")
        rows.append({"record_key": f'{occurrence["occurrence_id"]}#native/{ordinal}',
                     "occurrence_id": occurrence["occurrence_id"], "kind": "line",
                     "raw": text, "locator": _locator(occurrence, offset, offset+len(raw),
                                                       ordinal+1, ordinal+1, ordinal)})
        offset += len(raw)
    return rows


def _record(occurrence, kind, ordinal, locator, basis):
    return {"record_key": f'{occurrence["occurrence_id"]}#{kind}/{ordinal}',
            "kind": kind, "basis": basis, "occurrence_id": occurrence["occurrence_id"],
            "locator": locator, "name": None, "description": None,
            "sequence": None, "alphabet": None, "model_record_key": None,
            "sample_ordinal": None, "alignment_record_key": None,
            "fragments": [], "state": "complete", "native": {}}


def _fasta(content, occurrence, basis, native, issues):
    records, active = [], None
    def close(end, line_end):
        if active is None:
            return
        active["locator"].update(byte_end=end, line_end=line_end)
        active["sequence"] = "".join(piece["value"] for piece in active["fragments"])
        if not active["fragments"]:
            active["state"] = "incomplete"
            issues.append(_issue("sequence_incomplete", record_key=active["record_key"]))
        if occurrence["completeness"] != "complete" and end == len(content):
            active["state"] = "incomplete"
        if not _SEQUENCE.fullmatch(active["sequence"]) or any(c in "-._*~" for c in active["sequence"]):
            active["state"] = "invalid"
            issues.append(_issue("sequence_symbols_invalid", record_key=active["record_key"]))
    for line in native:
        text = line["raw"].rstrip("\r\n")
        if text.startswith(">"):
            close(line["locator"]["byte_start"], line["locator"]["line_start"]-1)
            ordinal = len(records)
            loc = deepcopy(line["locator"])
            loc["record_ordinal"] = ordinal
            active = _record(occurrence, "fasta", ordinal, loc, basis)
            parts = text[1:].split(None, 1)
            active["name"] = parts[0] if parts else None
            active["description"] = parts[1] if len(parts) == 2 else None
            active["native"]["header"] = text[1:]
            if not parts:
                active["state"] = "invalid"
                issues.append(_issue("fasta_header_invalid", record_key=active["record_key"]))
            records.append(active)
            line.update(kind="fasta_header", output_record_key=active["record_key"])
        elif active is None:
            if text.strip():
                issues.append(_issue("fasta_orphan_line", occurrence_id=occurrence["occurrence_id"],
                                     details={"line": line["locator"]["line_start"]}))
        else:
            # Whitespace is formatting; every original byte remains in native_rows.
            value = "".join(text.split())
            active["fragments"].append({"native_row_key": line["record_key"],
                                         "value": value, "locator": deepcopy(line["locator"])})
            line.update(kind="fasta_sequence", output_record_key=active["record_key"], value=value)
    close(len(content), len(native))
    return records


def _stockholm(content, occurrence, basis, native, issues, engine_version):
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        issues.append(_issue("text_encoding_invalid", occurrence_id=occurrence["occurrence_id"]))
        # A reversible surrogate string cannot pass the shared UTF-8 parser.
        # ASCII-compatible replacement keeps earlier complete records available;
        # exact invalid bytes remain in native_rows and invalidate the affected row.
        text = content.decode("utf-8", errors="replace")
    records, row_ordinal = [], 0
    for parsed in iter_hmmalign_stockholm_records(text, artifact_ref=occurrence["artifact_ref"],
                                                 engine_version=engine_version):
        events = parsed["original_events"]
        # Use original byte offsets even after replacement of malformed UTF-8.
        for event in events:
            line_index = event["locator"]["line"]-1
            original = native[line_index]
            original.update(kind=event["kind"])
            for key in ("name", "tag", "value", "version"):
                if key in event:
                    original[key] = event[key]
        first, last = native[events[0]["locator"]["line"]-1], native[events[-1]["locator"]["line"]-1]
        ordinal = parsed["alignment_index"]
        loc = _locator(occurrence, first["locator"]["byte_start"], last["locator"]["byte_end"],
                       first["locator"]["line_start"], last["locator"]["line_end"], ordinal)
        alignment = _record(occurrence, "alignment", ordinal, loc, basis)
        alignment["state"] = ("invalid" if not parsed["header_valid"] or parsed["issues"]
                              else "complete" if parsed["complete"] else "incomplete")
        alignment["native"] = {"column_count": parsed["column_count"],
            "block_count": parsed["block_count"], "terminated": parsed["complete"],
            "column_annotations": deepcopy(parsed["column_annotations"]),
            "row_record_keys": [], "parser_issues": deepcopy(parsed["issues"])}
        records.append(alignment)
        for parsed_row in parsed["rows"]:
            pieces = []
            for fragment in parsed_row["fragments"]:
                source = native[fragment["locator"]["line"]-1]
                pieces.append({"native_row_key": source["record_key"], "value": fragment["value"],
                               "locator": deepcopy(source["locator"]),
                               "block_index": fragment["block_index"]})
            start, end = pieces[0]["locator"], pieces[-1]["locator"]
            loc = _locator(occurrence, start["byte_start"], end["byte_end"],
                           start["line_start"], end["line_end"], row_ordinal)
            row = _record(occurrence, "alignment_row", row_ordinal, loc, basis)
            row_ordinal += 1
            row.update(name=parsed_row["name"], sequence=parsed_row["aligned_sequence"],
                       alignment_record_key=alignment["record_key"], fragments=pieces)
            row["native"] = {"name_occurrence": parsed_row["occurrence"],
                "identity_unambiguous": parsed_row["identity_unambiguous"],
                "geometry_valid": parsed_row["geometry_valid"],
                "column_annotations": deepcopy(parsed_row["column_annotations"]),
                "sequence_annotations": deepcopy(parsed_row["sequence_annotations"]),
                "sequence_annotations_joined": parsed_row["sequence_annotations_joined"],
                "parser_issues": deepcopy(parsed_row["issues"])}
            descriptions = [e["value"] for e in parsed_row["sequence_annotations"] if e["tag"] == "DE"]
            if len(descriptions) == 1 and parsed_row["sequence_annotations_joined"]:
                row["description"] = descriptions[0]
            if parsed_row["issues"] or not parsed_row["symbols_valid"]:
                row["state"] = "invalid"
            elif not parsed["complete"]:
                row["state"] = "incomplete"
            alignment["native"]["row_record_keys"].append(row["record_key"])
            records.append(row)
        if parsed["issues"] or any(r["issues"] for r in parsed["rows"]):
            issues.append(_issue("stockholm_invalid", record_key=alignment["record_key"],
                                 details={"parser_issues": deepcopy(parsed["issues"])}))
    return records


def _associate(sheet, binding_valid, output_valid):
    models = sheet["model_extraction"].get("records", []) if binding_valid else []
    names = [_name(model) for model in models]
    mode, settings = sheet["operation"]["mode"], sheet["operation"]["settings"]
    consensus = mode.startswith("consensus_")
    n = 1 if consensus else settings.get("-N")
    n = n if type(n) is int and n > 0 else None
    rows = [r for r in sheet["output_records"] if r["kind"] != "alignment"]
    alignments = [r for r in sheet["output_records"] if r["kind"] == "alignment"]
    repeated = {name for name, count in Counter(names).items() if count > 1}
    def expected(name, sample):
        return f"{name}-consensus" if consensus else f"{name}-sample{sample}"
    # Full ordered populations provide an occurrence witness for repeated source
    # names. A missing or malformed row disables that witness; never shift slots.
    full_order = bool(binding_valid and output_valid and n is not None and
                      sheet["model_extraction"].get("population", {}).get("complete") and
                      all(o["completeness"] == "complete" for o in sheet["artifact_occurrences"]
                          if o["direction"] == "output" and o["role"] in {"generated_sequences", "generated_alignment"}) and
                      len(rows) == len(models)*n and all(r["state"] == "complete" for r in rows))
    if full_order:
        full_order = all(row["name"] == expected(names[i//n], i % n+1) for i, row in enumerate(rows))
        if mode == "sample_core_aligned":
            full_order = full_order and len(alignments) == len(models) and all(
                a["native"]["row_record_keys"] == [r["record_key"] for r in rows[i*n:(i+1)*n]]
                and a["state"] == "complete" for i, a in enumerate(alignments))
    associations = []
    for ordinal, row in enumerate(rows):
        candidates = []
        for index, name in enumerate(names):
            if name is None or not isinstance(row["name"], str):
                continue
            if consensus:
                sample = 1 if row["name"] == expected(name, 1) else None
            else:
                prefix = name + "-sample"
                suffix = row["name"][len(prefix):] if row["name"].startswith(prefix) else ""
                sample = int(suffix) if re.fullmatch(r"[1-9][0-9]*", suffix) else None
            if sample is not None:
                candidates.append((index, sample))
        candidate_keys = [models[i]["record_key"] for i, _ in candidates]
        state, chosen = "unresolved", None
        if not binding_valid or not output_valid:
            state = "conflicting"
        elif full_order:
            chosen = (ordinal//n, ordinal % n+1)
        elif len(candidates) == 1 and names[candidates[0][0]] not in repeated:
            chosen = candidates[0]
        if chosen and n is not None and chosen[1] > n:
            chosen, state = None, "conflicting"
        if chosen:
            index, sample = chosen
            row.update(model_record_key=models[index]["record_key"], sample_ordinal=sample,
                       alphabet=deepcopy(models[index]["alphabet"]))
            state = "resolved"
        associations.append({"kind": "record", "record_key": row["record_key"],
            "state": state, "model_record_key": row["model_record_key"],
            "sample_ordinal": row["sample_ordinal"], "candidate_model_record_keys": candidate_keys,
            "basis": "ordered_complete_population" if chosen and full_order else
                     "native_name_suffix_and_order" if chosen else None})
    # Duplicate samples within the same model occurrence cannot be interpreted as
    # distinct native samples. Expected duplicate labels across proven repeated
    # model occurrences have distinct (model, sample) identities.
    multiplicities = Counter((a["model_record_key"], a["sample_ordinal"])
                             for a in associations if a["state"] == "resolved")
    by_key = {r["record_key"]: r for r in rows}
    model_indices = {m["record_key"]: i for i, m in enumerate(models)}
    previous = None
    for association in associations:
        if association["state"] != "resolved":
            continue
        identity = association["model_record_key"], association["sample_ordinal"]
        order = model_indices[identity[0]], identity[1]
        if multiplicities[identity] > 1 or (previous is not None and order < previous):
            association["state"] = "conflicting"
            row = by_key[association["record_key"]]
            row.update(model_record_key=None, sample_ordinal=None, alphabet=None)
            association.update(model_record_key=None, sample_ordinal=None)
        previous = order
    for a in alignments:
        children = [x for x in associations if x["record_key"] in a["native"]["row_record_keys"]]
        keys = {x["model_record_key"] for x in children if x["state"] == "resolved"}
        resolved = bool(children and len(keys) == 1 and all(x["state"] == "resolved" for x in children))
        key = next(iter(keys)) if resolved else None
        a["model_record_key"] = key
        if key:
            a["alphabet"] = deepcopy(models[model_indices[key]]["alphabet"])
        associations.append({"kind": "record", "record_key": a["record_key"],
            "state": "resolved" if resolved else "unresolved", "model_record_key": key,
            "sample_ordinal": None, "candidate_model_record_keys": list(sorted(keys)),
            "basis": "alignment_row_population" if resolved else None})
    for a in associations:
        if a["state"] != "resolved":
            sheet["issues"].append(_issue("association_"+a["state"], record_key=a["record_key"]))
    for model in models:
        key = model["record_key"]
        linked = [a["record_key"] for a in associations if a.get("kind") == "record" and a["model_record_key"] == key
                  and by_key.get(a["record_key"]) is not None]
        conflicted = any(key in a.get("candidate_model_record_keys", []) and a["state"] != "resolved"
                         for a in associations)
        output_complete = output_valid and all(o["completeness"] == "complete"
            for o in sheet["artifact_occurrences"] if o["direction"] == "output" and
            o["role"] in {"generated_sequences", "generated_alignment"})
        complete = (output_complete and not conflicted and n is not None and len(linked) == n
                    and all(by_key[k]["state"] == "complete" for k in linked))
        state = "conflicting" if conflicted or not binding_valid else "complete" if complete else "incomplete"
        associations.append({"kind": "model_population", "model_record_key": key,
            "state": state, "record_keys": linked, "expected_count": n,
            "captured_count": len(linked), "output_available": bool(output_valid),
            "output_complete": output_complete})
        if state != "complete":
            sheet["issues"].append(_issue("population_incomplete", record_key=key,
                                         details={"state": state}))
    sheet["associations"] = associations


def populate_hmmemit_sheet(*, operation, inputs, outputs, model_extraction):
    """Populate E1 from payload maps without reading paths or choosing work.

    Exact supplied operation/settings and M1 extraction are retained. M1 is
    decoded again from the supplied model bytes solely to validate the supplied
    extraction binding; no conversion or native invocation occurs.
    """
    sheet = {"schema": SCHEMA, "operation": deepcopy(operation), "artifact_occurrences": [],
             "model_extraction": deepcopy(model_extraction), "output_records": [],
             "native_rows": [], "associations": [], "issues": []}
    issues = sheet["issues"]
    op_valid = (isinstance(operation, dict) and set(operation) == {"program", "mode", "engine_version", "settings"}
        and operation.get("program") == "hmmemit" and isinstance(operation.get("mode"), str) and operation.get("mode") in MODES
        and (operation.get("engine_version") is None or isinstance(operation.get("engine_version"), str))
        and isinstance(operation.get("settings"), dict))
    if not op_valid:
        issues.append(_issue("operation_invalid", field="operation"))
    payloads, seen_ids, seen_slots = [], set(), set()
    for direction, mapping in (("input", inputs), ("output", outputs)):
        if not isinstance(mapping, dict):
            issues.append(_issue("payload_map_invalid", field=direction))
            continue
        for role, values in mapping.items():
            if not isinstance(role, str) or not isinstance(values, list):
                issues.append(_issue("payload_map_invalid", field=direction))
                continue
            for payload in values:
                if not isinstance(payload, dict) or set(payload) != {"occurrence", "content"} or not isinstance(payload.get("content"), bytes):
                    issues.append(_issue("payload_invalid", field=role))
                    continue
                occurrence, content = payload["occurrence"], payload["content"]
                if not _occurrence_valid(occurrence):
                    issues.append(_issue("occurrence_invalid", field=role))
                    continue
                sheet["artifact_occurrences"].append(deepcopy(occurrence))
                valid = True
                occurrence_id = occurrence["occurrence_id"]
                for condition, code in (
                    (occurrence["direction"] != direction or occurrence["role"] != role, "occurrence_role_mismatch"),
                    (len(content) != occurrence["size_bytes"], "occurrence_size_mismatch"),
                    (hashlib.sha256(content).hexdigest() != occurrence["sha256"].lower(), "occurrence_digest_mismatch"),
                    (occurrence_id in seen_ids or (direction, role, occurrence["ordinal"]) in seen_slots, "occurrence_duplicate"),
                ):
                    if condition:
                        issues.append(_issue(code, occurrence_id=occurrence_id, field=role))
                        valid = False
                seen_ids.add(occurrence_id)
                seen_slots.add((direction, role, occurrence["ordinal"]))
                if occurrence["completeness"] != "complete":
                    issues.append(_issue("capture_incomplete", occurrence_id=occurrence_id))
                payloads.append((direction, role, occurrence, content, valid))
    model_payloads = [p for p in payloads if p[:2] == ("input", "models")]
    binding_valid = False
    if len(model_payloads) != 1:
        issues.append(_issue("models_payload_count", details={"actual": len(model_payloads)}))
    elif isinstance(model_extraction, dict):
        _, _, occurrence, content, valid = model_payloads[0]
        extracted = extract_hmmer_models(content, occurrence=occurrence, format=model_extraction.get("format"))
        binding_valid = valid and extracted == model_extraction
    if not binding_valid:
        issues.append(_issue("model_extraction_mismatch", field="model_extraction"))
    elif model_extraction.get("population", {}).get("decoded_count") is None:
        issues.append(_issue("model_population_unavailable", field="model_extraction.population"))
    if op_valid:
        for key in ("-N", "--seed", "-L"):
            value = operation["settings"].get(key)
            if value is not None and (type(value) is not int or value < (1 if key == "-N" else 0)):
                issues.append(_issue("setting_invalid", field="operation.settings."+key))
        expected_role = "generated_alignment" if operation["mode"] == "sample_core_aligned" else "generated_sequences"
        basis = "model_derived" if operation["mode"].startswith("consensus_") else "generated"
        selected = [p for p in payloads if p[:2] == ("output", expected_role)]
        output_valid = bool(selected) and all(p[-1] for p in selected)
        if not selected:
            issues.append(_issue("generated_output_missing", field=expected_role))
    for direction, role, occurrence, content, valid in payloads:
        if direction != "output":
            continue
        native = _lines(content, occurrence)
        sheet["native_rows"].extend(native)
        if op_valid and role == expected_role:
            if any(0xDC80 <= ord(c) <= 0xDCFF for line in native for c in line["raw"]):
                issues.append(_issue("text_encoding_invalid", occurrence_id=occurrence["occurrence_id"]))
            parsed = (_stockholm(content, occurrence, basis, native, issues, operation["engine_version"])
                      if role == "generated_alignment" else _fasta(content, occurrence, basis, native, issues))
            sheet["output_records"].extend(parsed)
        elif op_valid and role in {"generated_alignment", "generated_sequences"}:
            issues.append(_issue("output_role_incompatible", occurrence_id=occurrence["occurrence_id"], field=role))
    if op_valid:
        _associate(sheet, binding_valid, output_valid)
    return sheet
