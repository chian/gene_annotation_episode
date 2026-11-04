"""Deterministic database BLAST sheets and replaceable function calculations.

This module reads supplied results and metadata only. It performs no searches,
metadata requests, episode decisions or annotation-credit updates. Reported
functions are supplied by source readers, never inferred from hit titles.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import json
import math
import re

from .blast_search import PROGRAM_UNITS


SHEET_SCHEMA = "blast_database_sheet_v1"
MODEL_NAME = "conditional_reference_kernel_v1"
QUALITY_FIELDS = ("completeness_fraction", "contamination_fraction",
                  "contig_count", "contig_n50", "total_sequence_length")
_DESCRIPTION_BINDING_FIELDS = {"report_index", "hit_index", "description_index",
    "metadata_index", "native_description", "metadata_identifier", "metadata_source_ref",
    "metadata_pointer", "linkage_source_ref", "linkage_pointer"}
_SEQUENCE_BINDING_FIELDS = {"report_index", "hit_index", "kind", "sequence_group",
    "algorithm", "digest", "molecule", "sequence_length", "source_ref", "pointer",
    "linkage_source_ref", "linkage_pointer"}
_NATIVE_DESCRIPTION_FIELDS = {"id", "accession", "title", "taxid"}


def _number(value, *, minimum=None, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or minimum is not None and value < minimum
            or maximum is not None and value > maximum):
        return None
    return value


def _taxid(value):
    return value if type(value) is int and value > 0 else None


def _text(value):
    return value if isinstance(value, str) and value else None


def _json_copy(value):
    # No untracked arbitrary Python values, NaNs or infinities in saved sheets.
    json.dumps(value, allow_nan=False)
    return deepcopy(value)


def _unique(rows):
    result, seen = [], set()
    for row in rows:
        key = json.dumps(row, sort_keys=True, allow_nan=False)
        if key not in seen:
            seen.add(key)
            result.append(deepcopy(row))
    return result


def _numeric_summary(values):
    values = [value for value in values if _number(value) is not None]
    return {"count": len(values), "minimum": min(values) if values else None,
            "maximum": max(values) if values else None,
            "mean": math.fsum(values) / len(values) if values else None}


def _lineage(row, issues, locator):
    nodes = row.get("lineage") or []
    if not isinstance(nodes, list):
        issues.append({"code": "lineage_array_required", **locator})
        return []
    valid = []
    for index, node in enumerate(nodes):
        if (not isinstance(node, dict) or _taxid(node.get("taxid")) is None
                or _text(node.get("rank")) is None):
            issues.append({"code": "lineage_node_invalid", "lineage_index": index, **locator})
            continue
        valid.append(deepcopy(node))
    return _unique(valid)


def _quality(assembly, issues, locator):
    if not isinstance(assembly, dict):
        issues.append({"code": "assembly_object_required", **locator})
        return {}
    values = {}
    for field in QUALITY_FIELDS:
        raw = assembly.get(field)
        value = _number(raw, minimum=0,
                        maximum=1 if field == "completeness_fraction" else None)
        if raw is not None and value is None:
            issues.append({"code": "assembly_measurement_invalid", "field": field, **locator})
        values[field] = value
    return values


def _functions(metadata, issues, locator):
    rows = metadata.get("functions") or []
    if not isinstance(rows, list):
        issues.append({"code": "function_array_required", **locator})
        return []
    valid = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or _text(row.get("function")) is None:
            issues.append({"code": "function_identifier_required", "function_index": index, **locator})
            continue
        # Keep the source's exact assignment and evidence. Its identifier is not
        # a measured confidence or an experimentally established status.
        valid.append(deepcopy(row))
    return _unique(valid)


def _attach_metadata(hit, metadata, matched_indices, issues):
    associations = []
    descriptions = hit.get("descriptions") or []
    if not isinstance(descriptions, list):
        raise ValueError("blast_descriptions_array_required")
    for description_index, description in enumerate(descriptions):
        locator = {"hit_index": hit["hit_index"], "description_index": description_index}
        if not isinstance(description, dict):
            issues.append({"code": "description_object_required", **locator})
            continue
        accession = _text(description.get("accession")) or _text(description.get("id"))
        native_taxon = _taxid(description.get("taxid"))
        matches = []
        for metadata_index, row in enumerate(metadata):
            if not isinstance(row, dict) or not accession or row.get("accession") != accession:
                continue
            meta_taxon = _taxid(row.get("taxid"))
            if row.get("taxid") is not None and meta_taxon is None:
                issues.append({"code": "metadata_taxid_invalid", "metadata_index": metadata_index, **locator})
                continue
            if native_taxon is not None and meta_taxon is not None and native_taxon != meta_taxon:
                issues.append({"code": "metadata_taxon_conflicts_with_native",
                               "metadata_index": metadata_index, **locator})
                continue
            matches.append((metadata_index, row))
            matched_indices.add(metadata_index)
        for metadata_index, row in matches or [(None, {})]:
            source_locator = {**locator, "metadata_index": metadata_index}
            assembly = row.get("assembly") or {}
            origin = row.get("origin") or {}
            if not isinstance(origin, dict):
                issues.append({"code": "origin_object_required", **source_locator})
                origin = {}
            association = {"description_index": description_index,
                "native_description": deepcopy(description), "accession": accession,
                "metadata_index": metadata_index, "source": row.get("source"),
                "taxid": native_taxon if native_taxon is not None else _taxid(row.get("taxid")),
                "lineage": _lineage(row, issues, source_locator),
                "functions": _functions(row, issues, source_locator),
                "origin": deepcopy(origin), "assembly": deepcopy(assembly),
                "quality_measurements": _quality(assembly, issues, source_locator),
                "sequence_group": _text(row.get("sequence_group")),
                "study_groups": sorted({value for value in row.get("study_groups", [])
                                        if _text(value) is not None})
                    if isinstance(row.get("study_groups", []), list) else []}
            associations.append(association)
    return associations


def _index(value):
    return type(value) is int and value >= 0


def _pointer(value):
    # RFC 6901 string form. Empty denotes the whole supplied JSON document.
    return (isinstance(value, str) and (value == "" or value.startswith("/"))
            and re.search(r"~(?![01])", value) is None)


def _source_locator(value, *, report, hit_index=None, description_index=None):
    if (not isinstance(value, dict) or _text(value.get("artifact_ref")) is None
            or not _index(value.get("report_index")) or not _pointer(value.get("pointer"))):
        return False
    if report is not None and any(value[key] != report[key]
                                  for key in ("artifact_ref", "report_index")):
        return False
    return all(type(value.get(key)) is int and value[key] == index
               for key, index in (("hit_index", hit_index),
                                  ("description_index", description_index)) if index is not None)


def _native_identity(value):
    if not isinstance(value, dict):
        return None
    snapshot = {key: value.get(key) for key in _NATIVE_DESCRIPTION_FIELDS}
    if (any(snapshot[key] is not None and not isinstance(snapshot[key], str)
            for key in ("id", "accession", "title"))
            or snapshot["taxid"] is not None and _taxid(snapshot["taxid"]) is None):
        return None
    return snapshot


def _binding_issue(issues, code, kind, index, row, **details):
    locator = {key: row[key] for key in ("report_index", "hit_index", "description_index", "metadata_index")
               if isinstance(row, dict) and _index(row.get(key))}
    issues.append({"code": code, "binding_kind": kind, "binding_index": index,
                   **locator, **details})


def _explicit_inputs(normalized, description_bindings, sequence_identity_bindings, issues):
    """Validate the opt-in envelope and index original, never compacted, rows."""
    if not isinstance(description_bindings, list) or not isinstance(sequence_identity_bindings, list):
        raise ValueError("blast_explicit_binding_lists_required")
    try:
        description_bindings = _json_copy(description_bindings)
        sequence_identity_bindings = _json_copy(sequence_identity_bindings)
    except (TypeError, ValueError) as error:
        raise ValueError("blast_explicit_bindings_finite_json_required") from error
    report = normalized.get("source_locator")
    if not _source_locator(report, report=None):
        raise ValueError("blast_explicit_report_source_locator_required")
    hits, descriptions = {}, {}
    for hit in normalized.get("hits", []):
        if not isinstance(hit, dict) or not _index(hit.get("hit_index")):
            raise ValueError("blast_hit_index_required")
        hit_index = hit["hit_index"]
        if hit_index in hits:
            raise ValueError("duplicate_native_hit_index")
        valid_hit = _source_locator(hit.get("source_locator"), report=report, hit_index=hit_index)
        hits[hit_index] = hit if valid_hit else None
        if not valid_hit:
            issues.append({"code": "blast_explicit_hit_source_locator_invalid", "hit_index": hit_index})
        rows = hit.get("descriptions") or []
        if not isinstance(rows, list):
            raise ValueError("blast_descriptions_array_required")
        for description in rows:
            locator = description.get("source_locator") if isinstance(description, dict) else None
            ordinal = locator.get("description_index") if isinstance(locator, dict) else None
            if (not valid_hit or not _index(ordinal) or not _source_locator(
                    locator, report=report, hit_index=hit_index, description_index=ordinal)):
                issues.append({"code": "blast_explicit_description_source_locator_invalid",
                               "hit_index": hit_index, "source_locator": deepcopy(locator)})
                continue
            key = (hit_index, ordinal)
            if key in descriptions:
                descriptions[key] = None
                issues.append({"code": "blast_explicit_description_locator_ambiguous",
                               "hit_index": hit_index, "description_index": ordinal})
            else:
                descriptions[key] = description
    return report, hits, descriptions, description_bindings, sequence_identity_bindings


def _description_links(bindings, metadata, report, hits, descriptions, issues):
    """Check exact supplied relationships, without an accession matching pass."""
    links, seen = defaultdict(list), set()
    # A source/pointer denotes one retained record, not a last-row-wins key.
    # Partial projections of the same identity are allowed; incompatible
    # identities or observed taxa cannot both describe that exact record.
    record_ids, record_taxa = defaultdict(set), defaultdict(set)
    for row in metadata:
        if (not isinstance(row, dict) or _text(row.get("source")) is None
                or not _pointer(row.get("native_pointer"))):
            continue
        key = (row["source"], row["native_pointer"])
        if _text(row.get("identifier_namespace")) and _text(row.get("accession")):
            record_ids[key].add((row["identifier_namespace"], row["accession"]))
        if _taxid(row.get("taxid")) is not None:
            record_taxa[key].add(row["taxid"])
    for index, binding in enumerate(bindings):
        code = None
        if not isinstance(binding, dict) or set(binding) != _DESCRIPTION_BINDING_FIELDS:
            code = "blast_description_binding_fields_invalid"
        elif not all(_index(binding[key]) for key in
                     ("report_index", "hit_index", "description_index", "metadata_index")):
            code = "blast_description_binding_index_invalid"
        elif (not isinstance(binding["native_description"], dict)
              or set(binding["native_description"]) != _NATIVE_DESCRIPTION_FIELDS
              or _native_identity(binding["native_description"]) is None):
            code = "blast_description_binding_native_identity_invalid"
        elif (not isinstance(binding["metadata_identifier"], dict)
              or set(binding["metadata_identifier"]) != {"namespace", "value"}
              or any(_text(binding["metadata_identifier"][key]) is None for key in ("namespace", "value"))):
            code = "blast_description_binding_metadata_identifier_invalid"
        elif (any(_text(binding[key]) is None for key in ("metadata_source_ref", "linkage_source_ref"))
              or any(not _pointer(binding[key]) for key in ("metadata_pointer", "linkage_pointer"))):
            code = "blast_description_binding_provenance_invalid"
        elif binding["report_index"] != report["report_index"]:
            code = "blast_description_binding_report_mismatch"
        elif hits.get(binding["hit_index"]) is None:
            code = "blast_description_binding_hit_unavailable"
        elif descriptions.get((binding["hit_index"], binding["description_index"])) is None:
            code = "blast_description_binding_description_unavailable"
        elif binding["metadata_index"] >= len(metadata) or not isinstance(metadata[binding["metadata_index"]], dict):
            code = "blast_description_binding_metadata_unavailable"
        else:
            description = descriptions[(binding["hit_index"], binding["description_index"])]
            row = metadata[binding["metadata_index"]]
            native = _native_identity(description)
            if native is None or native != binding["native_description"]:
                code = "blast_description_binding_native_identity_mismatch"
            elif binding["metadata_identifier"] != {
                    "namespace": row.get("identifier_namespace"), "value": row.get("accession")}:
                code = "blast_description_binding_metadata_identity_mismatch"
            elif (binding["metadata_source_ref"] != row.get("source")
                  or binding["metadata_pointer"] != row.get("native_pointer")):
                code = "blast_description_binding_metadata_provenance_mismatch"
            elif (len(record_ids[(row["source"], row["native_pointer"])]) > 1
                  or len(record_taxa[(row["source"], row["native_pointer"])]) > 1):
                code = "blast_description_binding_metadata_record_conflict"
            elif row.get("taxid") is not None and _taxid(row["taxid"]) is None:
                code = "metadata_taxid_invalid"
            elif (native["taxid"] is not None and row.get("taxid") is not None
                  and native["taxid"] != row["taxid"]):
                code = "metadata_taxon_conflicts_with_native"
        if code is not None:
            _binding_issue(issues, code, "description", index, binding)
            continue
        key = json.dumps(binding, sort_keys=True)
        if key not in seen:
            seen.add(key)
            links[(binding["hit_index"], binding["description_index"])].append((index, binding))
    return links


def _attach_explicit_metadata(hit, metadata, descriptions, links, matched, issues):
    associations = []
    for (hit_index, ordinal), description in descriptions.items():
        if hit_index != hit["hit_index"] or description is None:
            continue
        for binding_index, binding in links.get((hit_index, ordinal)) or [(None, None)]:
            metadata_index = binding["metadata_index"] if binding is not None else None
            row = metadata[metadata_index] if metadata_index is not None else {}
            locator = {"report_index": description["source_locator"]["report_index"],
                       "hit_index": hit_index, "description_index": ordinal,
                       "metadata_index": metadata_index}
            assembly, origin = row.get("assembly") or {}, row.get("origin") or {}
            quality = _quality(assembly, issues, locator)
            if not isinstance(assembly, dict):
                assembly = {}  # The invalid supplied value remains in reference_metadata.
            if not isinstance(origin, dict):
                issues.append({"code": "origin_object_required", **locator})
                origin = {}
            native_identifier = _text(description.get("accession")) or _text(description.get("id"))
            associations.append({**locator, "native_description": deepcopy(description),
                "source_locator": deepcopy(description["source_locator"]),
                "native_identifier": native_identifier,
                "accession": row.get("accession") if binding is not None else native_identifier,
                "metadata_identifier": deepcopy(binding["metadata_identifier"]) if binding is not None else None,
                "description_binding": deepcopy(binding), "binding_index": binding_index,
                "source": row.get("source"),
                "taxid": _taxid(description.get("taxid")) or _taxid(row.get("taxid")),
                "lineage": _lineage(row, issues, locator), "functions": _functions(row, issues, locator),
                "origin": deepcopy(origin), "assembly": deepcopy(assembly), "quality_measurements": quality,
                # Unverified metadata labels never enter the explicit grouping path.
                "sequence_group": None, "reported_sequence_group": deepcopy(row.get("sequence_group")),
                "study_groups": sorted({value for value in row.get("study_groups", []) if _text(value) is not None})
                    if isinstance(row.get("study_groups", []), list) else []})
            if metadata_index is not None:
                matched.add(metadata_index)
    return associations


def _sequence_links(bindings, normalized, report, hits, issues):
    accepted, seen = defaultdict(list), set()
    program = normalized.get("search", {}).get("program")
    units = PROGRAM_UNITS.get(program) if isinstance(program, str) else None
    for index, binding in enumerate(bindings):
        code = None
        if not isinstance(binding, dict) or set(binding) != _SEQUENCE_BINDING_FIELDS:
            code = "blast_sequence_binding_fields_invalid"
        elif not all(_index(binding[key]) for key in ("report_index", "hit_index")):
            code = "blast_sequence_binding_index_invalid"
        elif (binding["kind"] != "full_sequence_digest" or binding["algorithm"] != "sha256"
              or not isinstance(binding["digest"], str)
              or re.fullmatch(r"[0-9a-f]{64}", binding["digest"]) is None
              or binding["sequence_group"] != "sha256:" + binding["digest"]):
            code = "blast_sequence_binding_digest_invalid"
        elif (binding["molecule"] not in ("aa", "nt")
              or type(binding["sequence_length"]) is not int or binding["sequence_length"] <= 0):
            code = "blast_sequence_binding_operand_invalid"
        elif (any(_text(binding[key]) is None for key in ("source_ref", "linkage_source_ref"))
              or any(not _pointer(binding[key]) for key in ("pointer", "linkage_pointer"))):
            code = "blast_sequence_binding_provenance_invalid"
        elif binding["report_index"] != report["report_index"]:
            code = "blast_sequence_binding_report_mismatch"
        elif hits.get(binding["hit_index"]) is None:
            code = "blast_sequence_binding_hit_unavailable"
        elif units is None or binding["molecule"] != units[1]:
            code = "blast_sequence_binding_reference_molecule_mismatch"
        else:
            length = hits[binding["hit_index"]].get("length")
            if length is not None and (type(length) is not int or length <= 0
                                       or length != binding["sequence_length"]):
                code = "blast_sequence_binding_reference_length_mismatch"
        if code is not None:
            _binding_issue(issues, code, "sequence_identity", index, binding)
            continue
        key = json.dumps(binding, sort_keys=True)
        if key not in seen:
            seen.add(key)
            accepted[binding["hit_index"]].append((index, binding))
    record_identities = defaultdict(set)
    for rows in accepted.values():
        for _, binding in rows:
            record_identities[(binding["source_ref"], binding["pointer"])].add(
                (binding["digest"], binding["molecule"], binding["sequence_length"]))
    for hit_index, rows in accepted.items():
        valid = []
        for index, binding in rows:
            if len(record_identities[(binding["source_ref"], binding["pointer"])]) > 1:
                _binding_issue(issues, "blast_sequence_binding_source_identity_conflict",
                               "sequence_identity", index, binding)
            else:
                valid.append((index, binding))
        accepted[hit_index] = valid
    return accepted


def _union_length(intervals):
    end, total = None, 0
    for start, stop in sorted(intervals):
        if end is None or start > end:
            total += stop - start
        else:
            total += max(0, stop - end)
        end = max(end, stop) if end is not None else stop
    return total


def _hit_measurements(components, query_length, reference_length):
    pairs = [pair for component in components for pair in component.get("pairs", [])]
    paired_query = _union_length((pair["query_start"], pair["query_end"]) for pair in pairs)
    paired_reference = _union_length((pair["reference_start"], pair["reference_end"]) for pair in pairs)
    complete = bool(components) and all(
        component.get("geometry_available") is True for component in components)
    bit_scores = [component["native_scores"].get("bit_score") for component in components]
    bit_scores = [value for value in bit_scores if _number(value) is not None]
    evalues = [component["native_scores"].get("evalue") for component in components]
    evalues = [value for value in evalues if _number(value, minimum=0) is not None]
    unique_pairs = {(pair["query_start"], pair["query_end"], pair["reference_start"],
                     pair["reference_end"], pair["identical"]) for pair in pairs}
    return {"maximum_bit_score": max(bit_scores) if bit_scores else None,
        "minimum_evalue": min(evalues) if evalues else None,
        "hsp_count": len(components), "traceback_complete": complete,
        "observed_paired_query_positions": paired_query if pairs or complete else None,
        "observed_paired_reference_positions": paired_reference if pairs or complete else None,
        "query_paired_coverage": paired_query / query_length
            if complete and _number(query_length, minimum=1) is not None else None,
        "reference_paired_coverage": paired_reference / reference_length
            if complete and _number(reference_length, minimum=1) is not None else None,
        "unique_pair_count": len(unique_pairs) if pairs or complete else None,
        "identical_unique_pair_count": sum(pair[-1] for pair in unique_pairs)
            if pairs or complete else None,
        "overlap_pair_representations": len(pairs) - len(unique_pairs) if pairs or complete else None}


def _sequence_groups(hits, issues):
    # A native hit represents one sequence. Only actual accession identity or
    # supplied full-sequence group identity joins hits; equal local alignments do not.
    parents = list(range(len(hits)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    seen = defaultdict(list)
    tokens_per_hit = []
    signatures = []
    for hit in hits:
        accessions = defaultdict(set)
        explicit = set()
        for association in hit["associations"]:
            if association["accession"] is not None and association["taxid"] is not None:
                accessions[association["accession"]].add(association["taxid"])
            if association["sequence_group"] is not None:
                explicit.add(association["sequence_group"])
        signatures.append((accessions, explicit))
        if len(explicit) > 1:
            issues.append({"code": "conflicting_sequence_group_metadata", "hit_index": hit["hit_index"]})

    def compatible(left, right):
        left_members = [i for i in range(len(hits)) if root(i) == root(left)]
        right_members = [i for i in range(len(hits)) if root(i) == root(right)]
        explicit = set().union(*(signatures[i][1] for i in left_members + right_members))
        if len(explicit) > 1:
            return False
        for i in left_members:
            for j in right_members:
                a, b = signatures[i][0], signatures[j][0]
                for accession in set(a) & set(b):
                    if a[accession] and b[accession] and a[accession] != b[accession]:
                        return False
        return True

    for index, hit in enumerate(hits):
        tokens = set()
        for association in hit["associations"]:
            if association["accession"] is not None:
                tokens.add(("accession", association["accession"]))
            if association["sequence_group"] is not None:
                tokens.add(("sequence_group", association["sequence_group"]))
        tokens_per_hit.append(tokens)
        for token in sorted(tokens):
            for previous in seen[token]:
                if root(index) == root(previous):
                    continue
                if compatible(index, previous):
                    parents[root(index)] = root(previous)
                else:
                    issues.append({"code": "sequence_identity_conflict",
                        "hit_indices": [hits[previous]["hit_index"], hit["hit_index"]],
                        "identity_kind": token[0], "identity_value": token[1]})
            seen[token].append(index)
    groups = defaultdict(list)
    for index in range(len(hits)):
        groups[root(index)].append(index)
    return _summarize_sequence_groups(hits, groups.values(), tokens_per_hit)


def _summarize_sequence_groups(hits, membership, tokens_per_hit):
    """Keep the existing once-per-sequence numerical summaries for both paths."""
    result = []
    for group_index, indices in enumerate(sorted(membership, key=lambda values: min(values))):
        rows = [hits[index] for index in indices]
        scores = [row["measurements"]["maximum_bit_score"] for row in rows]
        scores = [value for value in scores if value is not None]
        functions = sorted({function["function"] for row in rows for association in row["associations"]
                            for function in association["functions"]})
        assignments = _unique([{"function": function["function"], "accession": association["accession"],
            "taxid": association["taxid"], "source": function.get("source") or association["source"],
            "evidence": function.get("evidence", [])}
            for row in rows for association in row["associations"] for function in association["functions"]])
        result.append({"group_index": group_index, "hit_indices": [row["hit_index"] for row in rows],
            "identity_basis": [{"kind": kind, "value": value}
                               for kind, value in sorted(set().union(*(tokens_per_hit[i] for i in indices)))],
            "functions": functions, "function_assignments": assignments,
            "maximum_bit_score": max(scores) if scores else None,
            "taxids": sorted({association["taxid"] for row in rows for association in row["associations"]
                              if association["taxid"] is not None}),
            "study_groups": sorted({study for row in rows for association in row["associations"]
                                    for study in association["study_groups"]})})
        for row in rows:
            row["sequence_group_index"] = group_index
    return result


def _explicit_sequence_groups(hits, sequence_links, issues):
    signatures, digest_operands = {}, defaultdict(set)
    for hit in hits:
        rows = sequence_links.get(hit["hit_index"], [])
        hit["sequence_identity_bindings"] = [deepcopy(binding) for _, binding in rows]
        keys = {(binding["digest"], binding["molecule"], binding["sequence_length"])
                for _, binding in rows}
        for digest, molecule, length in keys:
            digest_operands[digest].add((molecule, length))
        if len(keys) > 1:
            issues.append({"code": "blast_sequence_identity_conflict", "hit_index": hit["hit_index"],
                           "binding_indices": [index for index, _ in rows]})
        elif keys:
            signatures[hit["hit_index"]] = next(iter(keys))
    conflicts = {digest for digest, operands in digest_operands.items() if len(operands) > 1}
    for digest in sorted(conflicts):
        issues.append({"code": "blast_sequence_identity_operand_conflict", "sequence_group": "sha256:" + digest,
            "hit_indices": [hit["hit_index"] for hit in hits if any(
                binding["digest"] == digest for binding in hit["sequence_identity_bindings"])]})
    membership, tokens = defaultdict(list), []
    for index, hit in enumerate(hits):
        signature = signatures.get(hit["hit_index"])
        if signature is not None and signature[0] not in conflicts:
            key = ("full_sequence_digest", *signature)
            tokens.append({("sequence_group", "sha256:" + signature[0])})
        else:
            # This unique key preserves an unresolved native hit; it is not
            # evidence of a different full sequence or an independent experiment.
            key = ("unresolved_native_hit", hit["hit_index"])
            tokens.append(set())
        membership[key].append(index)
    return _summarize_sequence_groups(hits, membership.values(), tokens)


def _taxonomy_summary(hits, groups, target):
    taxon_groups, rank_groups, source_groups, origin_groups = defaultdict(set), defaultdict(lambda: defaultdict(set)), defaultdict(set), defaultdict(set)
    target_rank_members = defaultdict(set)
    for row in target["lineage"]:
        target_rank_members[row["rank"]].add(row["taxid"])
    target_ranks = {rank: next(iter(members)) for rank, members in target_rank_members.items()
                    if len(members) == 1}
    rows_by_group = defaultdict(list)
    for hit in hits:
        group = hit["sequence_group_index"]
        for association in hit["associations"]:
            rows_by_group[group].append(association)
            if association["taxid"] is not None:
                taxon_groups[association["taxid"]].add(group)
            if association["source"] is not None:
                source_groups[str(association["source"])].add(group)
            for key, value in association["origin"].items():
                if isinstance(value, (str, bool, int, float)):
                    origin_groups[(key, json.dumps(value, sort_keys=True))].add(group)
            for node in association["lineage"]:
                rank_groups[node["rank"]][group].add(node["taxid"])
    ranks = []
    for rank in sorted(set(rank_groups) | set(target_rank_members)):
        by_group = rank_groups[rank]
        counts = defaultdict(int)
        ambiguous = 0
        matching = conflicting = target_ambiguous = 0
        for members in by_group.values():
            if len(members) == 1:
                counts[next(iter(members))] += 1
            elif len(members) > 1:
                ambiguous += 1
            if rank in target_ranks:
                if members == {target_ranks[rank]}:
                    matching += 1
                elif target_ranks[rank] in members:
                    target_ambiguous += 1
                else:
                    conflicting += 1
        known_single = sum(counts.values())
        same_pairs = sum(count * (count - 1) // 2 for count in counts.values())
        total_pairs = known_single * (known_single - 1) // 2
        ranks.append({"rank": rank, "taxon_group_counts": {str(key): value for key, value in sorted(counts.items())},
            "unambiguous_group_count": known_single, "ambiguous_group_count": ambiguous,
            "unknown_group_count": len(groups) - len(by_group),
            "same_taxon_pair_count": same_pairs, "comparable_pair_count": total_pairs,
            "same_taxon_pair_fraction": same_pairs / total_pairs if total_pairs else None,
            "target_taxid_at_rank": target_ranks.get(rank),
            "target_matching_groups": matching if rank in target_ranks else None,
            "target_conflicting_groups": conflicting if rank in target_ranks else None,
            "target_ambiguous_groups": target_ambiguous if rank in target_ranks else None,
            "target_matching_fraction": matching / (matching + conflicting)
                if rank in target_ranks and matching + conflicting else None})
    return {"taxa": [{"taxid": taxid, "sequence_group_count": len(members),
                      "sequence_group_indices": sorted(members)} for taxid, members in sorted(taxon_groups.items())],
        "ranks": ranks, "target_independent_of_search": target["independent_of_search"],
        "ambiguous_target_ranks": [{"rank": rank, "taxids": sorted(members)}
            for rank, members in sorted(target_rank_members.items()) if len(members) > 1],
        "counts_meaning": "taxon memberships; one sequence may occur in more than one taxon",
        "sources": [{"source": source, "sequence_group_count": len(members),
                     "sequence_group_indices": sorted(members)} for source, members in sorted(source_groups.items())],
        "origins": [{"field": key, "value": json.loads(value), "sequence_group_count": len(members)}
                    for (key, value), members in sorted(origin_groups.items())]}


def _quality_summary(hits):
    rows = []
    for hit in hits:
        for association in hit["associations"]:
            if not association["assembly"]:
                continue
            assembly = association["assembly"]
            rows.append({"assembly_accession": assembly.get("accession"),
                "source": association["source"], "quality_method": assembly.get("quality_method"),
                "measurement_methods": deepcopy(assembly.get("measurement_methods") or {}),
                "accession": association["accession"] if not assembly.get("accession") else None,
                "measurements": deepcopy(association["quality_measurements"])})
    rows = _unique(rows)
    summaries = []
    def method_for(row, field):
        methods = row["measurement_methods"]
        value = methods.get(field) if isinstance(methods, dict) else None
        if value is None and field in {"completeness_fraction", "contamination_fraction"}:
            value = row["quality_method"]
        return str(value) if value is not None else ""
    for field in QUALITY_FIELDS:
        methods = sorted({method_for(row, field)
                          for row in rows if row["measurements"].get(field) is not None})
        for method in methods:
            values = [row["measurements"][field] for row in rows
                      if method_for(row, field) == method]
            summaries.append({"field": field, "quality_method": method or None,
                              **_numeric_summary(values)})
    return {"assembly_measurements": rows, "numerical_summaries": summaries,
            "meaning": "reported measurements, separated by method; not category-derived reliability grades"}


def _database_profile(profile, search, groups, issues):
    if profile is None:
        return {"available_for_adjustment": False, "reasons": ["database_profile_not_supplied"],
                "function_representation": []}
    reasons = []
    if not isinstance(profile, dict):
        raise ValueError("database_profile_object_required")
    database = search.get("database")
    request = search.get("request") or {}
    if not database or profile.get("database") != database:
        reasons.append("database_profile_identity_mismatch")
    release = request.get("database_release") or search.get("database_release")
    if (release is not None or profile.get("release") is not None) and profile.get("release") != release:
        reasons.append("database_profile_release_unmatched")
    if profile.get("count_unit") not in {"unique_sequences", "sequence_groups"}:
        reasons.append("database_profile_requires_sequence_count_unit")
    expected_scope = request.get("database_scope", "searched_database")
    if profile.get("scope") != expected_scope:
        reasons.append("database_profile_scope_mismatch")
    if not _text(profile.get("source")):
        reasons.append("database_profile_source_required")
    total = profile.get("total_count")
    if type(total) is not int or total <= 0:
        reasons.append("database_profile_total_count_invalid")
        total = None
    counts = profile.get("function_counts")
    if not isinstance(counts, dict):
        reasons.append("database_profile_function_counts_required")
        counts = {}
    elif any(_text(key) is None for key in counts):
        reasons.append("database_profile_function_identifiers_invalid")
        counts = {key: value for key, value in counts.items() if _text(key) is not None}
    observed = defaultdict(int)
    for group in groups:
        for function in group["functions"]:
            observed[function] += 1
    representation = []
    for function in sorted(set(counts) | set(observed)):
        count = counts.get(function)
        valid = type(count) is int and count >= 0 and total is not None and count <= total
        if not valid:
            reasons.append("database_function_count_unavailable_or_invalid:" + str(function))
            count = None
        elif count < observed.get(function, 0):
            reasons.append("database_function_count_below_observed_groups:" + str(function))
        representation.append({"function": function, "database_sequence_count": count,
            "database_total_sequence_count": total,
            "database_fraction": count / total if count is not None and total else None,
            "observed_sequence_group_count": observed.get(function, 0)})
    reasons = sorted(set(reasons))
    for reason in reasons:
        issues.append({"code": reason})
    return {"available_for_adjustment": not reasons, "reasons": reasons,
            "function_representation": representation}


def build_database_sheet(result: dict, *, reference_metadata: list[dict] | None = None,
                         target_context: dict | None = None,
                         database_profile: dict | None = None,
                         description_bindings: list[dict] | None = None,
                         sequence_identity_bindings: list[dict] | None = None) -> dict:
    """Populate a tool-facing numerical sheet without choosing an annotation.

    Supplied metadata stays attached to its exact accession/taxon. Conflicting
    records remain visible. Derived summaries count native sequence groups;
    aliases and overlapping HSPs are never independent replicates.

    Both binding arguments omitted preserves the legacy matcher and grouping.
    Supplying both lists selects exact original-ordinal metadata links and only
    supplied full-sequence identities for cross-hit grouping. These functions
    check the supplied relationships; the caller owns artifact/episode custody
    and validating each full-sequence record's relation to the actual operand.
    """
    from .blast_pairwise_grader import alignment_components

    if not isinstance(result, dict) or result.get("schema") != "blast_normalized_result_v1":
        raise ValueError("normalized_blast_result_required")
    if result.get("mode") != "database":
        raise ValueError("database_blast_mode_required")
    if (description_bindings is None) != (sequence_identity_bindings is None):
        raise ValueError("blast_explicit_binding_pair_required")
    explicit = description_bindings is not None
    normalized = _json_copy(result)
    metadata = _json_copy(reference_metadata if reference_metadata is not None else [])
    target_input = _json_copy(target_context if target_context is not None else {})
    profile = _json_copy(database_profile)
    if not isinstance(metadata, list) or not isinstance(target_input, dict):
        raise ValueError("blast_metadata_list_and_target_object_required")
    issues = deepcopy(normalized.get("issues") or [])
    if explicit:
        report, indexed_hits, descriptions, description_bindings, sequence_identity_bindings = _explicit_inputs(
            normalized, description_bindings, sequence_identity_bindings, issues)
        description_links = _description_links(description_bindings, metadata, report, indexed_hits, descriptions, issues)
        sequence_links = _sequence_links(sequence_identity_bindings, normalized, report, indexed_hits, issues)
    target = {"taxid": _taxid(target_input.get("taxid")),
        "lineage": _lineage(target_input, issues, {"context": "target"}),
        "source": target_input.get("source"),
        "independent_of_search": target_input.get("independent_of_search")
            if type(target_input.get("independent_of_search")) is bool else None}
    if target_input.get("taxid") is not None and target["taxid"] is None:
        issues.append({"code": "target_taxid_invalid"})
    matched, hits = set(), []
    seen_indices = set()
    for native_hit in normalized.get("hits", []):
        if not isinstance(native_hit, dict) or type(native_hit.get("hit_index")) is not int:
            raise ValueError("blast_hit_index_required")
        if native_hit["hit_index"] in seen_indices:
            raise ValueError("duplicate_native_hit_index")
        seen_indices.add(native_hit["hit_index"])
        components = []
        for hsp_index, hsp in enumerate(native_hit.get("hsps", [])):
            try:
                component = alignment_components(hsp, program=normalized["search"]["program"],
                    query_length=normalized["query"].get("length"),
                    reference_length=native_hit.get("length"))
            except (ValueError, TypeError, KeyError) as error:
                issues.append({"code": "alignment_components_unavailable", "hit_index": native_hit["hit_index"],
                               "hsp_index": hsp_index, "detail": str(error)[:200]})
                component = {"native_scores": {key: _number(hsp.get(key), minimum=0 if key == "evalue" else None)
                                               for key in ("bit_score", "score", "evalue")}
                    if isinstance(hsp, dict) else dict.fromkeys(("bit_score", "score", "evalue")),
                    "counts": {}, "fractions": {}, "pairs": [],
                    "issues": [{"code": "alignment_components_unavailable"}]}
            components.append(component)
        associations = (_attach_explicit_metadata(native_hit, metadata, descriptions, description_links, matched, issues)
                        if explicit else _attach_metadata(native_hit, metadata, matched, issues))
        hits.append({"hit_index": native_hit["hit_index"], "length": native_hit.get("length"),
            "associations": associations,
            "unpaired_metadata": deepcopy(native_hit.get("unpaired_metadata") or {}),
            "hsp_components": components,
            "measurements": _hit_measurements(components, normalized["query"].get("length"), native_hit.get("length"))})
        if explicit:
            hits[-1]["source_locator"] = deepcopy(native_hit.get("source_locator"))
    groups = _explicit_sequence_groups(hits, sequence_links, issues) if explicit else _sequence_groups(hits, issues)
    all_functions = sorted({function for group in groups for function in group["functions"]})
    by_function = []
    for function in all_functions:
        relevant_groups = [group for group in groups if function in group["functions"]]
        relevant_indices = {group["group_index"] for group in relevant_groups}
        relevant_hits = [deepcopy(hit) for hit in hits if hit["sequence_group_index"] in relevant_indices]
        # Taxonomy and source quality remain jointly attached to this function
        # assignment. Another alias's different function/taxon is not silently
        # transferred to this row merely because it shares a native hit.
        for hit in relevant_hits:
            assigned = [association for association in hit["associations"]
                if any(row["function"] == function for row in association["functions"])]
            # Different source records can describe the function and assembly
            # of the SAME reference. Keep that exact association, without
            # moving a function to another alias/taxon of this native hit.
            known_taxa = defaultdict(set)
            for association in hit["associations"]:
                if association["taxid"] is not None:
                    known_taxa[association["description_index"]].add(association["taxid"])
            def belongs(association):
                for assignment in assigned:
                    if association["description_index"] != assignment["description_index"]:
                        continue
                    a, b = association["taxid"], assignment["taxid"]
                    if a == b or ((a is None or b is None)
                                  and len(known_taxa[association["description_index"]]) <= 1):
                        return True
                return False
            hit["associations"] = [association for association in hit["associations"] if belongs(association)]
        scores = [group["maximum_bit_score"] for group in relevant_groups]
        by_function.append({"function": function, "sequence_group_count": len(relevant_groups),
            "native_hit_count": len(relevant_hits), "bit_score": _numeric_summary(scores),
            "query_paired_coverage": _numeric_summary([hit["measurements"]["query_paired_coverage"] for hit in relevant_hits]),
            "reference_paired_coverage": _numeric_summary([hit["measurements"]["reference_paired_coverage"] for hit in relevant_hits]),
            "taxonomy": _taxonomy_summary(relevant_hits, relevant_groups, target),
            "source_quality": _quality_summary(relevant_hits)})
    search_request = normalized["search"].get("request") or {}
    limit = search_request.get("hitlist_size", search_request.get("max_target_seqs"))
    if type(limit) is not int or limit <= 0:
        limit = None
    reported_count = normalized["search"].get("reported_hit_count")
    if type(reported_count) is not int or reported_count < 0:
        reported_count = None
    studies = defaultdict(set)
    for group in groups:
        for study in group["study_groups"]:
            studies[study].add(group["group_index"])
    output = {"schema": SHEET_SCHEMA, "normalized_result": normalized,
        "reference_metadata": metadata, "target_context": target_input,
        "database_profile": profile, "hits": hits, "sequence_groups": groups,
        "functions": by_function, "taxonomy": _taxonomy_summary(hits, groups, target),
        "source_quality": _quality_summary(hits),
        "dependence": {"group_count": len(groups),
            "duplicate_native_hit_count": len(hits) - len(groups),
            "shared_studies": [{"study": study, "sequence_group_indices": sorted(members)}
                               for study, members in sorted(studies.items())],
            "unknown_cross_hit_sequence_identity": len(groups) > 1 and any(
                not any(basis["kind"] == "sequence_group" for basis in group["identity_basis"])
                for group in groups),
            "meaning": "groups collapse demonstrated sequence identity; distinct groups are not claimed independent experiments"},
        "database_representation": _database_profile(profile, normalized["search"], groups, issues),
        "coverage": {"native_hit_count": len(hits), "sequence_group_count": len(groups),
            "groups_with_explicit_function": sum(bool(group["functions"]) for group in groups),
            "groups_without_explicit_function": sum(not group["functions"] for group in groups),
            "groups_with_native_bit_score": sum(group["maximum_bit_score"] is not None for group in groups),
            "metadata_row_count": len(metadata), "matched_metadata_row_count": len(matched),
            "unmatched_metadata_indices": sorted(set(range(len(metadata))) - matched)},
        "search_limits": {"requested_hit_limit": limit, "reported_hit_count": reported_count,
            "limit_reached": reported_count >= limit if reported_count is not None and limit is not None else None,
            "hit_array_present": normalized["search"].get("hit_array_present"),
            "whole_database_result_complete": None,
            "meaning": "all supplied hit rows retained; hitting a limit can censor evidence, fewer hits do not establish database completeness"},
        "issues": issues}
    if explicit:
        output.update(association_mode="explicit_bindings_v1",
                      description_bindings=description_bindings,
                      sequence_identity_bindings=sequence_identity_bindings)
    _json_copy(output)
    return output


def calculate_database_probabilities(sheet: dict, *, model: dict | None = None) -> dict:
    """Calculate conditional function probabilities from stored components.

    For sequence group g, b_g is its maximum HSP bit score, used once. The
    declared reference kernel is w_g = 2**((b_g - max(b))/temperature_bits),
    using the largest scored annotated-group score for conditional function
    masses. A separate all-group baseline measures unannotated reference mass
    without underflowing the conditional comparison when an unannotated hit is
    much stronger than every annotated hit.
    If a group has k distinct explicit functions, each receives w_g/k. Summing
    these masses gives M_f. The unadjusted output is proportional to pi_f*M_f;
    the representation-adjusted output is proportional to pi_f*M_f/N_f using
    actual database sequence counts. The latter approximates an average
    reference-kernel likelihood per function over reported matches only.

    These are model-conditional numbers, not calibrated probabilities of a
    correct annotation. Unknown-function and unscored groups are reported
    separately. Taxonomy and source-quality measurements are retained in the
    sheet but this initial model does not invent weighting rules for them.
    """
    if not isinstance(sheet, dict) or sheet.get("schema") != SHEET_SCHEMA:
        raise ValueError("blast_database_sheet_required")
    options = _json_copy(model if model is not None else {})
    if not isinstance(options, dict) or set(options) - {"temperature_bits", "function_priors"}:
        raise ValueError("blast_probability_model_parameters_invalid")
    temperature = options.get("temperature_bits", 1.0)
    if _number(temperature, minimum=0) is None or temperature <= 0:
        raise ValueError("positive_finite_temperature_bits_required")
    groups = sheet.get("sequence_groups")
    if not isinstance(groups, list):
        raise ValueError("blast_sequence_groups_required")
    measured = [group for group in groups if _number(group.get("maximum_bit_score")) is not None]
    functions = sorted({function for group in measured for function in group["functions"]})
    all_functions = {function for group in groups for function in group["functions"]}
    priors = options.get("function_priors")
    if priors is None:
        priors = {function: 1 / len(functions) for function in functions}
    elif (not isinstance(priors, dict) or set(priors) != set(functions)
          or any(_number(value, minimum=0) is None for value in priors.values())
          or not math.fsum(priors.values()) > 0):
        raise ValueError("complete_nonnegative_function_priors_required")
    else:
        total_prior = math.fsum(priors.values())
        priors = {function: value / total_prior for function, value in priors.items()}
    baseline = max((group["maximum_bit_score"] for group in measured), default=None)
    function_baseline = max((group["maximum_bit_score"] for group in measured if group["functions"]), default=None)
    masses = dict.fromkeys(functions, 0.0)
    contributions = []
    unassigned, assigned_global = 0.0, 0.0
    for group in groups:
        score = _number(group.get("maximum_bit_score"))
        weight = 2 ** ((score - baseline) / temperature) if score is not None and baseline is not None else None
        assigned = sorted(set(group["functions"]))
        function_weight = 2 ** ((score - function_baseline) / temperature) if (
            assigned and score is not None and function_baseline is not None) else None
        if weight is not None:
            if assigned:
                assigned_global += weight
                for function in assigned:
                    masses[function] += function_weight / len(assigned)
            else:
                unassigned += weight
        contributions.append({"group_index": group["group_index"], "bit_score": score,
            "kernel_weight": weight, "function_kernel_weight": function_weight, "functions": assigned,
            "mass_per_function": function_weight / len(assigned) if function_weight is not None else None})
    weighted = {function: priors[function] * masses[function] for function in functions}
    denominator = math.fsum(weighted.values())
    unadjusted = {function: value / denominator for function, value in weighted.items()} if denominator else None
    representation = sheet["database_representation"]
    counts = {row["function"]: row["database_sequence_count"]
              for row in representation["function_representation"]}
    adjustment_reasons = list(representation["reasons"])
    if any(counts.get(function) is None or counts.get(function, 0) <= 0 for function in functions):
        adjustment_reasons.append("positive_database_count_required_for_each_function")
    adjusted = None
    if representation["available_for_adjustment"] and not adjustment_reasons and denominator:
        corrected = {function: weighted[function] / counts[function] for function in functions}
        corrected_denominator = math.fsum(corrected.values())
        if corrected_denominator:
            adjusted = {function: value / corrected_denominator for function, value in corrected.items()}
    total_mass = assigned_global + unassigned
    result = {"schema": "blast_database_probabilities_v1", "model": MODEL_NAME,
        "parameters": {"temperature_bits": temperature, "function_priors": priors},
        "formula": {"sequence_group_weight": "2 ** ((maximum_bit_score - largest_scored_function_group_bit_score) / temperature_bits)",
            "all_reference_kernel_weight": "2 ** ((maximum_bit_score - largest_group_bit_score) / temperature_bits)",
            "function_mass": "sum(group_weight / distinct_function_count_for_group)",
            "unadjusted": "prior[function] * function_mass / sum(prior * function_mass)",
            "representation_adjusted": "(prior[function] * function_mass / database_function_sequence_count) / sum(prior * function_mass / database_function_sequence_count)"},
        "conditioning": "explicit function assignments among the supplied scored reference sequence groups",
        "calibrated_annotation_probability": False,
        "largest_group_bit_score": baseline, "largest_scored_function_group_bit_score": function_baseline,
        "sequence_group_contributions": contributions,
        "function_masses": masses, "unadjusted_probabilities": unadjusted,
        "representation_adjusted_probabilities": adjusted,
        "representation_adjustment_unavailable_reasons": sorted(set(adjustment_reasons)),
        "unannotated_reference_kernel_mass": unassigned,
        "unannotated_reference_kernel_fraction": unassigned / total_mass if total_mass else None,
        "unscored_sequence_group_count": len(groups) - len(measured),
        "functions_without_measured_bit_scores": sorted(all_functions - set(functions)),
        "search_limits": deepcopy(sheet["search_limits"]),
        "retained_measurements_not_used_by_this_model": ["taxonomy", "target_taxonomy_agreement",
            "source_quality", "annotation_evidence_codes", "alignment_coverage", "identity", "shared_studies"],
        "assumptions": ["Native bit score differences define a chosen reference-similarity kernel, not a measured functional likelihood.",
            "A native hit or demonstrated duplicate sequence group contributes once using its strongest HSP.",
            "Distinct explicit function labels within a sequence group divide its mass equally; this is not a claim that multifunctional proteins have only one function.",
            "Probabilities are conditional on the supplied candidate functions and returned matches; unreported or unannotated functions remain outside that distribution.",
            "Representation correction uses independently supplied matching database sequence counts; it is not inferred from returned-hit counts."]}
    if (sheet.get("association_mode") == "explicit_bindings_v1"
            and sheet.get("dependence", {}).get("unknown_cross_hit_sequence_identity") is True):
        result["assumptions"].append(
            "Unresolved returned native-hit groups are counted as separate model components; "
            "this modeling choice is not measured sequence identity or evidence of independent experiments.")
    _json_copy(result)
    return result


__all__ = ["build_database_sheet", "calculate_database_probabilities", "SHEET_SCHEMA", "MODEL_NAME"]
