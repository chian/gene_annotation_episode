"""Original native_hmmer_result_worker scientific values and explicit received-record contracts."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_native_result_views import family_for_program
import hashlib
import math
from gene_annotation_episode.episodic_workflow.root.a101.library.hmmalign_inputs import parse_hmmalign_stockholm
import re

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
    from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_search_inputs import build_hmmer_search_sheet
    from gene_annotation_episode.episodic_workflow.root.a101.library.nhmmer_inputs import build_nhmmer_sheet
    from gene_annotation_episode.episodic_workflow.root.a101.library.hmmer_search_grader import calculate_hmmer_search_scores
    from gene_annotation_episode.episodic_workflow.root.a101.library.nhmmer_grader import calculate_nhmmer_scores
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
