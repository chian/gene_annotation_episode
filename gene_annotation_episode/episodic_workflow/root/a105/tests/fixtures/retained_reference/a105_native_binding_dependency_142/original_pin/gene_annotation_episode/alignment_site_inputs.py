"""Reference-position sheets from supplied, checked alignment results.

The host binds one actual observation and its operands. These readers neither
select a placement nor execute an aligner. Full input and requested row order
are retained; duplicated requests do not enlarge the measurement population.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re

from .alignment_site_mapping import _validate_operand, map_operand_interval
from .biopython_pairwise_grader import build_biopython_pairwise_sheet
from .minimap2_grading_inputs import build_minimap2_placement_sheet, require_finite_json


SHEET_SCHEMA = "reference_site_comparison_sheet_v1"
RELATIONSHIP_COUNTS = {
    "identical": "identical_positions", "substituted": "substituted_positions",
    "query_gap": "query_gap_positions", "reference_skip": "reference_skip_positions",
    "outside_alignment": "outside_alignment_positions", "unavailable": "unavailable_positions",
}
COUNT_NAMES = (
    "requested_position_count", "unique_requested_position_count", "duplicate_requested_position_count",
    "identical_positions", "substituted_positions", "paired_positions", "query_gap_positions",
    "reference_skip_positions", "outside_alignment_positions", "unavailable_positions",
    "aligned_reference_positions", "selected_insertion_events", "inserted_query_positions",
    "selected_query_paired_units", "selected_reference_paired_units",
)
_COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVNacgtryswkmbdhvn", "TGCAYRSWMKVHDBNtgcayrswmkvhdbn")
_SOURCE_KEYS = {"alignment_ref", "source_ref", "native_artifact_ref", "provider", "format",
                "native_version", "native_locator"}


def _source(source, provider, format_):
    if (type(source) is not dict or set(source) != _SOURCE_KEYS
            or any(type(source[key]) is not str or not source[key]
                   for key in _SOURCE_KEYS - {"native_version", "native_locator"})
            or source["provider"] != provider or source["format"] != format_
            or source["native_version"] is not None and type(source["native_version"]) is not str
            or type(source["native_locator"]) is not dict):
        raise ValueError("site_source_invalid")
    locator = source["native_locator"]
    if format_ == "minimap2_paf_row":
        if (set(locator) != {"line_number", "row_start", "row_end"}
                or any(type(v) is not int for v in locator.values())
                or locator["line_number"] < 1 or not 0 <= locator["row_start"] < locator["row_end"]):
            raise ValueError("site_native_locator_invalid")
    elif locator:
        raise ValueError("site_native_locator_invalid")


def _selection(selection, length):
    if type(selection) is not dict:
        raise ValueError("site_selection_invalid")
    if selection.get("kind") == "reference_positions":
        if set(selection) != {"kind", "positions"} or type(selection["positions"]) is not list or not selection["positions"]:
            raise ValueError("site_selection_invalid")
        positions = selection["positions"]
    elif selection.get("kind") == "reference_window":
        if (set(selection) != {"kind", "start", "end"}
                or type(selection["start"]) is not int or type(selection["end"]) is not int
                or not 0 <= selection["start"] < selection["end"]):
            raise ValueError("site_selection_invalid")
        if length is not None and selection["end"] > length:
            raise ValueError("site_reference_position_outside_operand")
        positions = list(range(selection["start"], selection["end"]))
    else:
        raise ValueError("site_selection_invalid")
    if any(type(p) is not int or p < 0 for p in positions):
        raise ValueError("site_selection_invalid")
    if length is not None and any(p >= length for p in positions):
        raise ValueError("site_reference_position_outside_operand")
    return list(positions), list(dict.fromkeys(positions))


def _inputs(native, operands, source, selection, mappings, *, provider, format_, model):
    require_finite_json([native, operands, source, selection, mappings], "site_finite_json_required")
    if type(native) is not dict:
        raise ValueError("site_native_object_required")
    if type(operands) is not dict or set(operands) != {"query", "reference"}:
        raise ValueError("site_operands_invalid")
    for role, operand in operands.items():
        _validate_operand(operand)
        if (operand["alignment_unit"] != ("aa" if model == "protein" else "nt")
                or operand["unit"] not in (operand["alignment_unit"], "symbol")
                or operand["molecule"] not in (model, "unknown")):
            raise ValueError("site_operand_identity_conflict")
        length = native.get(role + "_length")
        if type(length) is int and length >= 0 and operand["length"] is not None and length != operand["length"]:
            raise ValueError("site_operand_identity_conflict")
    if mappings is not None and (type(mappings) is not dict or set(mappings) != {"query", "reference"}
            or any(value is not None and type(value) is not dict for value in mappings.values())):
        raise ValueError("site_original_mappings_invalid")
    _source(source, provider, format_)
    reference_length = operands["reference"]["length"]
    if reference_length is None and type(native.get("reference_length")) is int and native["reference_length"] >= 0:
        reference_length = native["reference_length"]
    return _selection(selection, reference_length)


def _issue(issues, code, **location):
    row = {"code": code, **location}
    if row not in issues:
        issues.append(row)


def _attach(row, role, interval, operands, mappings, issues, *, unknown=False):
    result = ({"status": "unavailable", "intervals": None, "reason": "site_original_mapping_unavailable"}
              if unknown else map_operand_interval(operands[role], (mappings or {}).get(role), interval))
    row[role + "_original_intervals"] = result["intervals"]
    row[role + "_mapping_status"] = result["status"]
    row[role + "_mapping_reason"] = result["reason"]
    if result["reason"]:
        _issue(issues, result["reason"], role=role)


def _quality(quality, encoding, length, issues):
    if encoding not in ("unspecified", "phred33", "phred64", "solexa64"):
        raise ValueError("site_quality_encoding_invalid")
    if quality is not None and type(quality) is not str:
        raise ValueError("site_quality_invalid")
    if quality is None:
        return None, "unavailable"
    if len(quality) != length:
        _issue(issues, "site_quality_length_conflict")
        return None, "incompatible"
    low = {"unspecified": 33, "phred33": 33, "phred64": 64, "solexa64": 59}[encoding]
    if any(not low <= ord(char) <= 126 for char in quality):
        _issue(issues, "site_quality_character_conflict")
        return quality, "incompatible"
    if encoding == "unspecified":
        _issue(issues, "site_quality_encoding_unspecified")
    return quality, "available" if encoding != "unspecified" else "unavailable"


def _quality_fields(quality, encoding, status, position):
    char = quality[position] if quality is not None and position is not None else None
    score = ord(char) - (33 if encoding == "phred33" else 64) if char is not None and status == "available" else None
    return {"query_quality_character": char, "query_quality_score": score,
            "quality_encoding": encoding,
            "quality_scale": "solexa_log_odds" if encoding == "solexa64" else
                             "phred" if encoding in ("phred33", "phred64") else None}


def _site_row(position, data, *, ordinal, strand, operands, mappings, issues,
              quality=None, encoding="unspecified", quality_status="unavailable", unavailable_reason=None):
    data = data or {}
    qpos = data.get("query_position")
    relation = data.get("relationship", "unavailable" if unavailable_reason else "outside_alignment")
    row = {"request_ordinal": ordinal, "reference_position": position,
        "reference_interval": [position, position + 1],
        "query_interval": [qpos, qpos + 1] if qpos is not None else None,
        "query_position": qpos, "reference_symbol": data.get("reference_symbol"),
        "query_symbol": data.get("query_symbol"), "query_original_symbol": data.get("query_original_symbol"),
        "relationship": relation, "alignment_column": data.get("alignment_column"),
        "native_operation": data.get("native_operation"), "query_strand": strand,
        **_quality_fields(quality, encoding, quality_status, qpos),
        "unavailable_reason": unavailable_reason if relation == "unavailable" else None}
    _attach(row, "reference", row["reference_interval"], operands, mappings, issues)
    _attach(row, "query", row["query_interval"], operands, mappings, issues, unknown=relation == "unavailable")
    return row


def _insertion(event, *, operands, mappings, issues):
    row = deepcopy(event)
    _attach(row, "query", row["query_interval"], operands, mappings, issues)
    return row


def _union_size(intervals):
    end, total = -1, 0
    for left, right in sorted(intervals):
        total += max(0, right - max(end, left))
        end = max(end, right)
    return total


def _observed_counts(sites, insertions):
    unique = {row["reference_position"]: row for row in sites}
    counts = Counter(row["relationship"] for row in unique.values())
    result = {name: counts[relation] for relation, name in RELATIONSHIP_COUNTS.items()}
    result.update(requested_position_count=len(sites), unique_requested_position_count=len(unique),
        duplicate_requested_position_count=len(sites)-len(unique),
        paired_positions=counts["identical"]+counts["substituted"],
        aligned_reference_positions=counts["identical"]+counts["substituted"]+counts["query_gap"],
        selected_insertion_events=len(insertions),
        inserted_query_positions=sum(row["query_interval"][1]-row["query_interval"][0] for row in insertions))
    paired = [row for row in unique.values() if row["relationship"] in ("identical", "substituted")]
    for role in ("query", "reference"):
        result["selected_"+role+"_paired_units"] = _union_size([row[role+"_interval"] for row in paired])
    return {name: result[name] for name in COUNT_NAMES}


def _counts(sites, insertions, insertion_available):
    counts = _observed_counts(sites, insertions)
    if counts["unavailable_positions"]:
        for name in COUNT_NAMES:
            if name not in {"requested_position_count", "unique_requested_position_count",
                            "duplicate_requested_position_count", "unavailable_positions"}:
                counts[name] = None
    if not insertion_available:
        counts["selected_insertion_events"] = counts["inserted_query_positions"] = None
    return counts


def _finish(*, mode, native, parameters, measurements, symbols, source, operands, selection,
            requested, unique, found, insertions, mappings, geometry, issues, strand,
            no_alignment=False, reason=None, quality=None, encoding="unspecified", quality_status="unavailable",
            extra_availability=None):
    sites = [_site_row(position, found.get(position), ordinal=ordinal, strand=strand,
        operands=operands, mappings=mappings, issues=issues, quality=quality, encoding=encoding,
        quality_status=quality_status, unavailable_reason=reason if not geometry and not no_alignment else None)
        for ordinal, position in enumerate(requested)]
    wanted = set(unique)
    selected = [_insertion(row, operands=operands, mappings=mappings, issues=issues)
                for row in insertions if row["reference_boundary"] in wanted or row["reference_boundary"]-1 in wanted]
    counts = _counts(sites, selected, geometry or no_alignment)
    return {"schema": SHEET_SCHEMA, "mode": mode,
        "status": "no_alignment" if no_alignment else "unavailable" if not geometry else "partial" if issues else "complete",
        "source": deepcopy(source), "operands": deepcopy(operands), "selection": deepcopy(selection),
        "requested_positions": requested, "unique_requested_positions": unique,
        "native_input": deepcopy(native), "native_parameters": deepcopy(parameters),
        "inherited_native_measurements": deepcopy(measurements), "symbol_interpretation": deepcopy(symbols),
        "original_mapping_inputs": deepcopy(mappings), "sites": sites, "insertions": selected,
        "measured_counts": counts,
        "availability": {"local_correspondence": geometry or no_alignment,
            "insertion_correspondence": geometry or no_alignment, "quality": quality_status,
            **(extra_availability or {})}, "issues": issues}


def _gapped_columns(columns, *, reference_start, original_symbols):
    found, events, boundary = {}, [], reference_start
    for column in columns:
        q, r = column["query_position"], column["reference_position"]
        if r is None:
            if events and events[-1]["alignment_column_interval"][1] == column["column"]:
                event = events[-1]
                event["query_interval"][1] = q+1
                event["query_sequence"] += column["query_symbol"]
                event["alignment_column_interval"][1] += 1
            else:
                events.append({"event_ordinal": len(events), "reference_boundary": boundary,
                    "query_interval": [q, q+1], "query_strand": "+", "query_sequence": column["query_symbol"],
                    "query_quality_characters": None, "alignment_column_interval": [column["column"], column["column"]+1]})
        else:
            found[r] = {"query_position": q, "query_symbol": column["query_symbol"],
                "query_original_symbol": column["query_symbol"] if original_symbols else None,
                "reference_symbol": column["reference_symbol"], "relationship": column["relationship"],
                "alignment_column": column["column"], "native_operation": None}
            boundary = r+1
    return found, events


def extract_biopython_reference_sites(native: dict, *, molecule: str, selection: dict,
        operands: dict, source: dict, original_mappings: dict | None = None) -> dict:
    """Use the existing complete checked Biopython residue correspondence."""
    if molecule not in ("protein", "dna", "rna"):
        raise ValueError("site_molecule_invalid")
    requested, unique = _inputs(native, operands, source, selection, original_mappings,
        provider="biopython.alignment", format_="biopython_pairwise_json", model=molecule)
    upstream = build_biopython_pairwise_sheet(native, molecule=molecule)
    if (native.get("biopython_version") is not None and source["native_version"] is not None
            and native["biopython_version"] != source["native_version"]):
        raise ValueError("site_native_version_conflict")
    geometry = upstream["geometry"]["available"]
    no_alignment = upstream["alignment_state"] == "no_alignment"
    issues, found, events = [], {}, []
    reason = None
    if geometry:
        # The upstream path checks native lengths; also check authenticated host
        # lengths when a native length was absent.
        if any(operands[role]["length"] is not None and upstream["geometry"][role+"_interval"] is not None
               and upstream["geometry"][role+"_interval"][1] > operands[role]["length"] for role in operands):
            geometry = False
    if geometry:
        found, events = _gapped_columns(upstream["residue_correspondence"],
            reference_start=upstream["geometry"]["coordinates"][1][0], original_symbols=molecule == "protein")
    elif not no_alignment:
        reason = "site_native_geometry_unavailable" if upstream["traceback"]["status"] == "unavailable" or native.get("coordinates") is None else "site_native_geometry_conflict"
        _issue(issues, reason)
    if upstream["issues"] and geometry:
        _issue(issues, "site_native_measurement_unavailable")
    return _finish(mode="biopython_pairwise", native=native,
        parameters={"molecule": molecule, "mode": upstream["mode"], **upstream["native_parameters"]},
        measurements={"native_score": upstream["native_score"], **upstream["reported_measurements"]},
        symbols=upstream["symbol_interpretation"], source=source, operands=operands, selection=selection,
        requested=requested, unique=unique, found=found, insertions=events, mappings=original_mappings,
        geometry=geometry, issues=issues, strand="+" if geometry or no_alignment else None,
        no_alignment=no_alignment, reason=reason)


def extract_phmmer_reference_sites(native: dict, *, selection: dict, operands: dict,
        source: dict, original_mappings: dict | None = None) -> dict:
    """Read the actual phmmer sequence alignment, not generic profile consensus."""
    requested, unique = _inputs(native, operands, source, selection, original_mappings,
        provider="native.phmmer.alignment", format_="native_phmmer_alignment_json", model="protein")
    issues, columns, found, events = [], [], {}, []
    q, r = native.get("query_aligned"), native.get("reference_aligned")
    geometry = True
    reason = "site_native_geometry_unavailable" if q is None or r is None else "site_native_geometry_conflict"
    if (type(q) is not str or type(r) is not str or not q or len(q) != len(r)
            or re.fullmatch(r"[A-Za-z.*-]+", q) is None or re.fullmatch(r"[A-Za-z.*-]+", r) is None):
        geometry = False
    intervals = {role: native.get(role+"_interval_aa_zero_based_half_open") for role in operands}
    if geometry:
        q, r = q.upper().replace(".", "-"), r.upper().replace(".", "-")
        if any(a == b == "-" for a, b in zip(q, r)):
            geometry = False
        for role, string in (("query", q), ("reference", r)):
            interval, length = intervals[role], native.get(role+"_length")
            if (type(interval) is not list or len(interval) != 2 or any(type(v) is not int for v in interval)
                    or type(length) is not int or not 0 <= interval[0] < interval[1] <= length
                    or interval[1]-interval[0] != len(string.replace("-", ""))
                    or operands[role]["length"] is not None and interval[1] > operands[role]["length"]):
                geometry = False
    if geometry:
        qp, rp = intervals["query"][0], intervals["reference"][0]
        for index, (a, b) in enumerate(zip(q, r)):
            columns.append({"column": index, "query_position": qp if a != "-" else None,
                "reference_position": rp if b != "-" else None, "query_symbol": a if a != "-" else None,
                "reference_symbol": b if b != "-" else None,
                "relationship": "query_gap" if a == "-" else "reference_gap" if b == "-" else "identical" if a == b else "substituted"})
            qp += a != "-"
            rp += b != "-"
        if "paired_intervals" in native:
            paired = {role: [] for role in operands}
            for col in columns:
                if col["relationship"] not in ("identical", "substituted"):
                    continue
                for role in paired:
                    position = col[role+"_position"]
                    if paired[role] and paired[role][-1][1] == position:
                        paired[role][-1][1] += 1
                    else:
                        paired[role].append([position, position+1])
            geometry = native["paired_intervals"] == paired
        if geometry:
            found, events = _gapped_columns(columns, reference_start=intervals["reference"][0], original_symbols=True)
    if not geometry:
        _issue(issues, reason)
    measurements = {key: deepcopy(native.get(key)) for key in (
        "sequence_evalue", "sequence_bitscore", "domain_bitscore", "conditional_domain_evalue",
        "independent_domain_evalue", "native_inclusion_flag", "native_sequence_inclusion_flag",
        "paired_residues", "identical_paired_residues")}
    for key, value in measurements.items():
        if value is None:
            continue
        expected_types = ((bool,) if key.endswith("flag") else (int,) if key.endswith("residues") else (int, float))
        if type(value) not in expected_types or (key.endswith(("evalue", "residues")) and value < 0):
            measurements[key] = None
            _issue(issues, "site_native_measurement_unavailable", field=key)
    return _finish(mode="native_phmmer_sequence_alignment", native=native, parameters={"program": "phmmer"},
        measurements=measurements, symbols={"reader_normalization": "uppercase_native_symbols_dot_to_gap",
            "identity": "literal_normalized_symbol_equality_without_ambiguity_resolution",
            "query_meaning": "actual_phmmer_query_sequence_not_generic_profile_consensus"},
        source=source, operands=operands, selection=selection, requested=requested, unique=unique,
        found=found, insertions=events, mappings=original_mappings, geometry=geometry,
        issues=issues, strand="+" if geometry else None, reason=reason)


def extract_minimap2_reference_sites(native_row: dict, *, preset: str, native_version: str | None,
        selection: dict, query_metadata: dict, reference_metadata: dict, source: dict,
        quality: str | None = None, quality_encoding: str = "unspecified",
        original_mappings: dict | None = None) -> dict:
    """Read one retained PAF placement with actual joined original sequences."""
    require_finite_json([native_row, query_metadata, reference_metadata, quality, quality_encoding], "site_finite_json_required")
    metadata = {"query": query_metadata, "reference": reference_metadata}
    operands = {}
    for role, meta in metadata.items():
        if (type(meta) is not dict or set(meta) != {"subject_ref", "name", "length", "sequence"}
                or type(meta["subject_ref"]) is not str or not meta["subject_ref"]
                or type(meta["name"]) is not str or not meta["name"]
                or type(meta["length"]) is not int or meta["length"] < 0
                or type(meta["sequence"]) is not str or len(meta["sequence"]) != meta["length"]
                or re.fullmatch(r"[ACGTRYSWKMBDHVNacgtryswkmbdhvn]*", meta["sequence"]) is None):
            raise ValueError("site_operand_metadata_invalid")
        operands[role] = {"subject_ref": meta["subject_ref"], "length": meta["length"],
            "unit": "nt", "alignment_unit": "nt", "molecule": "dna"}
    requested, unique = _inputs(native_row, operands, source, selection, original_mappings,
        provider="minimap2.mapping", format_="minimap2_paf_row", model="dna")
    if source["native_version"] != native_version:
        raise ValueError("site_native_version_conflict")
    if any(meta["name"] != native_row.get(role+"_name") for role, meta in metadata.items()):
        raise ValueError("site_operand_identity_conflict")
    # Only this adapter's custody field is stripped. Native metadata validation
    # receives the exact name, length and original sequence supplied by the host.
    upstream = build_minimap2_placement_sheet(native_row, preset=preset, native_version=native_version,
        query_metadata={k: v for k, v in query_metadata.items() if k != "subject_ref"},
        reference_metadata={k: v for k, v in reference_metadata.items() if k != "subject_ref"})
    issues, found, events = [], {}, []
    geometry = upstream["availability"]["geometry"]
    reason = None
    if not geometry:
        reason = "site_native_geometry_conflict" if not upstream["native_valid"] else "site_native_geometry_unavailable"
    elif any(meta["status"] != "valid" or meta["sequence_status"] != "valid" for meta in upstream["metadata"].values()):
        geometry, reason = False, "site_operand_identity_conflict"
    if reason:
        _issue(issues, reason)
    quality_value, quality_status = _quality(quality, quality_encoding, query_metadata["length"], issues)
    if not upstream["availability"]["cs_equality"]:
        _issue(issues, "site_native_cs_unavailable")
    if upstream["issues"] and geometry:
        _issue(issues, "site_native_measurement_unavailable")
    strand = upstream["native_facts"]["strand"]
    if geometry:
        query, reference = query_metadata["sequence"], reference_metadata["sequence"]
        wanted = set(unique)
        native_operations = []
        for part in upstream["cg_operations"]:
            native_operations.extend([part["operation"]] * (0 if part["operation"] == "N" else part["length"]))
        for part in upstream["correspondence"]:
            op, size = part["operation"], part["length"]
            rs = part["reference_interval"][0]
            start_column = part["column_interval"][0]
            if op == "I":
                indices = [part["query_first"]+part["query_step"]*i for i in range(size)]
                symbols = "".join(query[p] if strand == "+" else query[p].translate(_COMPLEMENT) for p in indices)
                events.append({"event_ordinal": len(events), "reference_boundary": rs,
                    "query_interval": deepcopy(part["query_interval"]), "query_strand": strand,
                    "query_sequence": symbols, "query_quality_characters": "".join(quality_value[p] for p in indices) if quality_value is not None else None,
                    "alignment_column_interval": deepcopy(part["column_interval"])})
                continue
            for position in sorted(p for p in wanted if rs <= p < rs+size):
                offset = position-rs
                qp = part["query_first"]+part["query_step"]*offset if op == "M" else None
                original = query[qp] if qp is not None else None
                symbol = original if strand == "+" or original is None else original.translate(_COMPLEMENT)
                column = start_column+offset if op != "N" else None
                found[position] = {"query_position": qp, "query_symbol": symbol,
                    "query_original_symbol": original, "reference_symbol": reference[position],
                    "relationship": "query_gap" if op == "D" else "reference_skip" if op == "N" else
                                    "identical" if symbol.upper() == reference[position].upper() else "substituted",
                    "alignment_column": column,
                    "native_operation": "N" if op == "N" else native_operations[column] if native_operations else op}
    facts = upstream["native_facts"]
    measurements = {key: facts[key] for key in ("matching_bases", "block_length", "mapping_quality")}
    measurements.update(mapping_quality_available=facts["mapping_quality"] is not None and facts["mapping_quality"] != 255,
        usable_mapping_quality=facts["mapping_quality"] if facts["mapping_quality"] != 255 else None,
        native_tag_quantities=upstream["native_tag_quantities"], native_alignment_type=upstream["native_alignment_type"])
    return _finish(mode="minimap2_placement",
        native={"native_row": native_row, "query_metadata": query_metadata, "reference_metadata": reference_metadata,
                "quality": quality, "quality_encoding": quality_encoding},
        parameters={"preset": preset, "native_version": native_version, "native_parameters": upstream["native_parameters"]},
        measurements=measurements, symbols={"reader_normalization": "uppercase_original_IUPAC_symbols_query_complemented_on_reverse_strand",
            "native_cs_symbols": "normalized_ACGTN_not_original_IUPAC_identity",
            "identity": "literal_normalized_original_symbol_equality_without_ambiguity_resolution"},
        source=source, operands=operands, selection=selection, requested=requested, unique=unique,
        found=found, insertions=events, mappings=original_mappings, geometry=geometry, issues=issues,
        strand=strand, reason=reason, quality=quality_value, encoding=quality_encoding, quality_status=quality_status,
        extra_availability={"native_cs_equality": upstream["availability"]["cs_equality"]})


def _same_json(left, right):
    """Storage comparison must not equate bool/int or integer/float geometry."""
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same_json(value, right[key]) for key, value in left.items())
    if type(left) is list:
        return len(left) == len(right) and all(_same_json(a, b) for a, b in zip(left, right))
    return left == right


def _validate_saved_sheet(sheet):
    """Revalidate saved rows against retained pure inputs, never external state."""
    if type(sheet) is not dict or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("reference_site_sheet_required")
    require_finite_json(sheet, "site_finite_json_required")
    try:
        common = {"selection": sheet["selection"], "source": sheet["source"],
                  "original_mappings": sheet["original_mapping_inputs"]}
        mode = sheet["mode"]
        if mode == "biopython_pairwise":
            rebuilt = extract_biopython_reference_sites(sheet["native_input"], molecule=sheet["native_parameters"]["molecule"],
                operands=sheet["operands"], **common)
        elif mode == "native_phmmer_sequence_alignment":
            rebuilt = extract_phmmer_reference_sites(sheet["native_input"], operands=sheet["operands"], **common)
        elif mode == "minimap2_placement":
            rebuilt = extract_minimap2_reference_sites(**sheet["native_input"],
                preset=sheet["native_parameters"]["preset"], native_version=sheet["native_parameters"]["native_version"], **common)
        else:
            raise ValueError("reference_site_sheet_components_invalid")
        if not _same_json(rebuilt, sheet):
            raise ValueError("reference_site_sheet_components_invalid")
    except (KeyError, TypeError, AttributeError, IndexError) as error:
        raise ValueError("reference_site_sheet_components_invalid") from error


__all__ = ["extract_biopython_reference_sites", "extract_phmmer_reference_sites", "extract_minimap2_reference_sites"]
