"""CodonTree-specific sheet construction from supplied, retained reader values.

This module neither acquires data nor parses bytes. Shared source/format checks
belong to the common provider; these checks establish the additional family,
genome, stage and model relationships. They do not authenticate C4 custody.
"""
from __future__ import annotations

from copy import deepcopy
from urllib.parse import quote

from . import phylogeny_calculation_contracts as c
from .bvbrc_phylogeny_common_inputs import extract_common_fields, input_member_subject_id
from .bvbrc_phylogeny_common_contracts import validate_shared_fields


__all__ = ["extract_codon_tree_sheet", "validate_codon_tree_sheet"]

_HEADER = {"schema_version": "bvbrc_codon_tree_sheet_v1", "tool": "C-L193-CodonTree",
           "mode": "core_genome_codon_protein"}
_FAMILY_KEYS = {"family_id", "namespace", "matrix", "matrix_completeness", "memberships", "inclusion",
                "native_statistic_observation_ids", "final_block_indices"}
_GENOME_KEYS = {"genome_id", "input_members", "final_alignment_rows", "final_tree_tips", "inclusion",
                "native_count_observation_ids"}
_MODEL_KEYS = {"analysis_id", "partition_name", "model_token", "datatype", "branch_optimization", "parameters",
               "model_selection_command_id", "sample_alignment_id", "sample_column_map", "evidence"}
_MEMBERSHIP_KEYS = {"representation", "feature_ids", "genome_ids", "deleted_feature_ids",
                    "missing_codon_feature_ids", "source_table_id", "source_row_index"}
_STAGES = {"requested", "returned", "eligible", "evaluated_pretrim", "selected", "final_protein",
           "final_coding_nucleotide", "final_matrix", "final_tree"}
_REASONS = {"zero_family_records", "deleted_paralog", "missing_codon_alignment", "native_bad_sequence",
            "native_low_alignment_score", "native_gap_filter", "missing_locus_gap_fill", "other_native_reason", None}
_NEEDS = {
    "family_namespace_required": ("scientific_metadata", "family_namespace"),
    "feature_genome_association_required": ("scientific_metadata", "feature_genome_membership"),
    "final_family_coordinates_required": ("scientific_metadata", "final_family_coordinates"),
    "genome_row_association_required": ("scientific_metadata", "genome_alignment_rows"),
    "genome_tip_association_required": ("scientific_metadata", "genome_tree_tips"),
    "partition_model_association_required": ("scientific_metadata", "partition_model"),
    "model_sample_correspondence_required": ("scientific_metadata", "model_sample_columns"),
    "native_membership_conflict": ("scientific_metadata", "family_membership_resolution"),
    "requested_genome_membership_required": ("input_metadata", "requested_genome_population"),
    "member_genome_association_required": ("scientific_metadata", "original_member_genome"),
    "optional_forwarding_required": ("original_task", "actual_optional_genome_input"),
}
DIAGNOSTIC_CODES = frozenset("codon_provider_" + key for key in _NEEDS) | frozenset({
    "codon_provider_operand_invalid", "codon_provider_native_stage_conflict",
    "codon_provider_native_membership_unique_projection",
    "codon_provider_model_record_conflict",
})


def _need(ok, code):
    if not ok:
        raise ValueError("codon_provider_" + code)


def _shape(value, keys, code):
    _need(type(value) is dict and set(value) == set(keys), code)


def _unique(rows, key, code):
    c.sequence(rows, stored=True)
    result = {}
    for row in rows:
        _need(type(row) is dict and key in row, code)
        ident = row[key]
        c.text(ident)
        _need(ident not in result, code)
        result[ident] = row
    return result


def _diagnostic(code, path, refs=(), severity="qualification"):
    full = "codon_provider_" + code
    _need(full in DIAGNOSTIC_CODES, "diagnostic_code_invalid")
    return {"code": full, "phase": "association", "path": path, "severity": severity,
            "evidence_refs": list(dict.fromkeys(refs))}


def _missing(sheet, reason, scope, *, path="", refs=(), severity="qualification"):
    kind, role = _NEEDS[reason]
    req = {"requirement_id": "phylogeny/codon_provider/" + quote(scope, safe="") + "/" + reason,
           "kind": kind, "role": role, "source_refs": list(dict.fromkeys(refs)), "reason_code": reason}
    old = next((r for r in sheet["missing_requirements"] if r["requirement_id"] == req["requirement_id"]), None)
    _need(old is None or old == req, "requirement_conflict")
    if old is None:
        sheet["missing_requirements"].append(req)
    diagnostic = _diagnostic(reason, path, refs, severity)
    if diagnostic not in sheet["qualifications"]:
        sheet["qualifications"].append(diagnostic)


def _included(subject, stage, *, state="included", reason=None, location=None, evidence=()):
    return {"subject_id": subject, "stage": stage, "state": state, "reason": reason,
            "native_reason_location": deepcopy(location), "evidence": deepcopy(list(evidence))}


def _inclusions(rows):
    c.sequence(rows, stored=True)
    for row in rows:
        _shape(row, {"subject_id", "stage", "state", "reason", "native_reason_location", "evidence"},
               "inclusion_shape_invalid")
        c.text(row["subject_id"])
        _need(row["stage"] in _STAGES and row["state"] in {"included", "excluded", "unknown"}
              and row["reason"] in _REASONS, "inclusion_invalid")
        c.evidence(row["evidence"])
        if row["native_reason_location"] is not None:
            c.location(row["native_reason_location"])


def _at(value, pointer):
    """Resolve an already supplied member pointer; never load its evidence."""
    if pointer is None:
        return None
    if pointer == "":
        return value
    try:
        for part in pointer[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if type(value) is list:
                if not part.isdigit() or str(int(part)) != part:
                    return None
                value = value[int(part)]
            else:
                value = value[part]
        return value
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def _member_genomes(sheet):
    """Use original inline operands or exact source-evidence identity joins."""
    result = {}
    source = sheet["documents"]["store"]["source_records"]
    feature_map = {r["feature_id"]: r for r in sheet["joins"]["feature_genomes"]}
    for binding in sheet["inputs"]:
        for member in binding["members"]:
            possible = set()
            raw = _at(binding["inline_value"], member["member_pointer"])
            pointer = binding["parameter_pointer"]
            if type(raw) is str and any(pointer == p or pointer.startswith(p + "/") for p in
                    ("/genome_ids", "/optional_genome_ids")):
                possible.add(raw)
            evidence, content = member["evidence"], binding["content"]
            # Evidence at a shared container does not identify its individual
            # members. This fallback supports only an exact original object and
            # pointer, not a link through a different source object or a label.
            if (binding["kind"] == "retained_bytes" and evidence is not None and content is not None
                and evidence["content"] == content and member["member_pointer"] is not None
                and evidence["pointer"] == member["member_pointer"]):
                for record in source:
                    artifact = record["artifact"]
                    same_artifact = artifact is not None and (
                        artifact["source_ref"], artifact["raw_artifact_ref"], artifact["sha256"]) == (
                        content["source_ref"], content["artifact_ref"], content["sha256"])
                    target_matches = same_artifact if artifact is not None else evidence in record["evidence"]
                    if record["pointer"] == member["member_pointer"] and target_matches:
                        subject = record["subject"]
                        if subject["kind"] == "genome":
                            possible.add(subject["id"])
                        elif subject["kind"] == "feature" and subject["id"] in feature_map:
                            possible.add(feature_map[subject["id"]]["genome_id"])
            _need(len(possible) <= 1, "member_genome_conflict")
            if possible:
                result[(binding["binding_id"], member["member_id"])] = next(iter(possible))
    # Actual group/forwarded-input MemberFacts, unlike paths, supply identities.
    for group in sheet["assembly"]["genome_request_sets"]:
        if group["kind"] not in {"group_members", "actually_forwarded_optional"}:
            continue
        ids = set(group["population"]["genome_ids"])
        for binding in sheet["inputs"]:
            if binding["binding_id"] not in group["input_binding_ids"]:
                continue
            for member in binding["members"]:
                if member["member_id"] in ids and member["evidence"] is not None:
                    key = (binding["binding_id"], member["member_id"])
                    _need(key not in result or result[key] == member["member_id"], "member_genome_conflict")
                    result[key] = member["member_id"]
    return result


def _trees(sheet):
    store = sheet["documents"]["store"]
    return {t["tree_id"]: t for d in store["tree_documents"] for t in d["trees"]} | {
        x["tree"]["tree_id"]: x["tree"] for d in store["phyloxml"] for x in d["trees"]}


def _row_genomes(sheet):
    members = _member_genomes(sheet)
    result = {}
    for row in sheet["joins"]["input_rows"]:
        genome = members.get((row["input_binding_id"], row["member_id"]))
        if genome is not None:
            key = (row["alignment_id"], row["row_index"])
            _need(key not in result or result[key] == genome, "row_genome_conflict")
            result[key] = genome
    return members, result


def _validate_requests(sheet):
    assembly = sheet["assembly"]
    inputs = {r["binding_id"]: r for r in sheet["inputs"]}
    populations = {r["population_id"]: r for r in assembly["caller_populations"]["genomes"]}
    sets = _unique(assembly["genome_request_sets"], "set_id", "duplicate_genome_request_set")
    for item in sets.values():
        _shape(item, {"set_id", "kind", "input_binding_ids", "group_id", "derived_from_set_ids", "population"},
               "genome_request_set_shape_invalid")
        c.text(item["set_id"])
        c.strings(item["input_binding_ids"])
        c.strings(item["derived_from_set_ids"])
        kind, pop = item["kind"], item["population"]
        _need(kind in {"main_ids", "optional_ids", "group_members", "main_union", "actually_forwarded_optional"},
              "genome_request_kind_invalid")
        _need(populations.get(pop["population_id"]) == pop, "request_population_conflict")
        _need(all(i in inputs for i in item["input_binding_ids"]), "request_input_missing")
        expected_stage = "requested_optional" if kind == "optional_ids" else (
            "actually_forwarded_optional" if kind == "actually_forwarded_optional" else "requested_main")
        _need(pop["stage"] == expected_stage, "request_stage_conflict")
        _need((item["group_id"] is not None) == (kind == "group_members"), "request_group_conflict")
        _need(bool(item["derived_from_set_ids"]) == (kind == "main_union"), "request_union_invalid")
        if kind == "main_union":
            _need(not item["input_binding_ids"], "request_union_invalid")
            parents = [sets.get(i) for i in item["derived_from_set_ids"]]
            _need(all(p is not None and p["kind"] in {"main_ids", "group_members"} for p in parents),
                  "request_union_invalid")
            _need(set(pop["genome_ids"]) == set().union(*(set(p["population"]["genome_ids"]) for p in parents)),
                  "request_union_membership_conflict")
            _need(pop["completeness"] != "complete" or all(p["population"]["completeness"] == "complete" for p in parents),
                  "request_union_completeness_conflict")
            continue
        _need(bool(item["input_binding_ids"]), "request_input_missing")
        selected = [inputs[i] for i in item["input_binding_ids"]]
        if kind in {"main_ids", "optional_ids"}:
            root = "/genome_ids" if kind == "main_ids" else "/optional_genome_ids"
            values, known = [], True
            for binding in selected:
                _need(binding["parameter_pointer"] == root or binding["parameter_pointer"].startswith(root + "/"),
                      "request_parameter_conflict")
                val = binding["inline_value"]
                if type(val) is str:
                    values.append(val)
                elif type(val) is list and all(type(v) is str and v for v in val):
                    values.extend(val)
                else:
                    known = False
            _need(len(values) == len(set(values)), "duplicate_requested_genome")
            _need(not known or set(values) == set(pop["genome_ids"]), "request_membership_conflict")
            _need(known or pop["completeness"] != "complete", "request_membership_unknown")
        elif kind == "group_members":
            c.text(item["group_id"])
            members = []
            _need(bool(pop["evidence"]) or pop["completeness"] != "complete", "group_response_evidence_missing")
            for binding in selected:
                val = binding["inline_value"]
                _need(binding["workspace_path"] == item["group_id"] or val == item["group_id"] or
                      type(val) is list and item["group_id"] in val, "request_group_binding_conflict")
                members.extend(m["member_id"] for m in binding["members"] if m["evidence"] is not None
                    and any(m["evidence"]["content"] == ev["content"] for ev in pop["evidence"]))
            _need(set(pop["genome_ids"]) <= set(members), "group_membership_evidence_missing")
            _need(pop["completeness"] != "complete" or set(pop["genome_ids"]) == set(members),
                  "group_membership_conflict")
        else:
            _need(bool(pop["evidence"]), "forwarded_optional_evidence_missing")
            # A requested optional parameter or wrapper source is not evidence
            # that the deployed invocation actually forwarded it.
            witnessed = False
            for ev in pop["evidence"]:
                for command in sheet["observed_run"]["commands"]:
                    if command["origin"] != "observed":
                        continue
                    loc = command["location"]
                    content = ev["content"]
                    artifact = None if loc is None else loc["artifact"]
                    related = ev in command["evidence"] or artifact is not None and (
                        artifact["source_ref"], artifact["raw_artifact_ref"], artifact["sha256"]) == (
                        content["source_ref"], content["artifact_ref"], content["sha256"])
                    argv = command["argv"] or []
                    operands = [argv[i + 1] for i, token in enumerate(argv[:-1])
                                if token == "--optionalGenomeIdsFile"]
                    operands += [token.split("=", 1)[1] for token in argv
                                 if token.startswith("--optionalGenomeIdsFile=")]
                    if related and any(binding["workspace_path"] in operands
                        and set(pop["genome_ids"]) == {m["member_id"] for m in binding["members"]
                            if m["evidence"] is not None and m["evidence"]["content"] == binding["content"]} for binding in selected
                        if binding["kind"] == "retained_bytes"):
                        witnessed = True
            _need(witnessed, "forwarded_optional_actual_input_required")


def _validate_matrices(sheet):
    assembly = sheet["assembly"]
    fps = {p["population_id"]: p for p in assembly["caller_populations"]["families"]}
    gps = {p["population_id"]: p for p in assembly["caller_populations"]["genomes"]}
    joins = {r["feature_id"]: r for r in sheet["joins"]["feature_genomes"]}
    matrices = _unique(assembly["family_matrices"], "matrix_id", "duplicate_matrix_id")
    for matrix in matrices.values():
        _shape(matrix, {"matrix_id", "namespace", "family_population_id", "genome_population_id", "rows",
                        "completeness", "evidence"}, "matrix_shape_invalid")
        c.text(matrix["matrix_id"])
        _need(matrix["namespace"] in {"PGFam", "PLFam"}, "matrix_namespace_invalid")
        _need(matrix["completeness"] in c.COMPLETENESS, "matrix_completeness_invalid")
        c.evidence(matrix["evidence"])
        c.sequence(matrix["rows"], stored=True)
        fp, gp = fps.get(matrix["family_population_id"]), gps.get(matrix["genome_population_id"])
        _need(fp is not None and gp is not None, "matrix_population_missing")
        cells, features = set(), set()
        for row in matrix["rows"]:
            _shape(row, {"family_id", "genome_id", "feature_ids", "evidence"}, "matrix_row_shape_invalid")
            c.strings(row["feature_ids"])
            c.evidence(row["evidence"])
            key = (row["family_id"], row["genome_id"])
            _need(key not in cells, "duplicate_matrix_cell")
            cells.add(key)
            _need(key[0] in fp["family_ids"] and key[1] in gp["genome_ids"], "matrix_member_outside_population")
            for fid in row["feature_ids"]:
                _need(fid not in features, "duplicate_matrix_feature")
                features.add(fid)
                join = joins.get(fid)
                _need(join is not None, "matrix_feature_join_missing")
                _need((join["family_id"], join["genome_id"], join["family_namespace"]) ==
                      (key[0], key[1], matrix["namespace"]), "matrix_feature_join_conflict")
        if matrix["completeness"] == "complete":
            _need(fp["completeness"] == gp["completeness"] == "complete", "matrix_population_incomplete")
            _need(cells == {(f, g) for f in fp["family_ids"] for g in gp["genome_ids"]}, "matrix_incomplete_cartesian_population")
    chosen = sheet["documents"]["analyses"][0]["explicit_family_matrix_id"]
    _need(chosen is None or chosen in matrices, "analysis_matrix_missing")
    return matrices.get(chosen)


def _validate_historical(sheet):
    fps = {p["population_id"]: p for p in sheet["populations"]["families"]}
    native = {p["population_id"]: p for p in sheet["populations"]["native"]}
    aps = {p["population_id"]: p for p in sheet["populations"]["alignments"]}
    analysis = sheet["documents"]["analyses"][0]
    final = {analysis["final_alignment_id"], *analysis["per_family_final_alignment_ids"]}
    joins = {r["feature_id"]: r for r in sheet["joins"]["feature_genomes"]}
    seen = set()
    for history in sheet["assembly"]["historical_frequencies"]:
        _shape(history, {"evaluated_family_population", "pretrim_sequence_rows"}, "history_shape_invalid")
        ep = history["evaluated_family_population"]
        _shape(ep, {"population", "expected_sequence_memberships", "completeness"}, "history_population_shape_invalid")
        pop = ep["population"]
        _need(pop["stage"] == "evaluated_pretrim" and fps.get(pop["population_id"]) == pop, "history_stage_population_conflict")
        _need(pop["population_id"] not in seen, "duplicate_history_population")
        seen.add(pop["population_id"])
        _need(ep["completeness"] in c.COMPLETENESS, "history_completeness_invalid")
        c.sequence(ep["expected_sequence_memberships"], stored=True)
        expected, all_features = {}, set()
        for item in ep["expected_sequence_memberships"]:
            _shape(item, {"family_id", "feature_ids"}, "history_expected_shape_invalid")
            c.strings(item["feature_ids"])
            fid = item["family_id"]
            _need(fid in pop["family_ids"] and fid not in expected, "history_family_conflict")
            _need(not all_features.intersection(item["feature_ids"]), "history_feature_conflict")
            expected[fid] = item["feature_ids"]
            all_features.update(item["feature_ids"])
        c.sequence(history["pretrim_sequence_rows"], stored=True)
        seen_features = set()
        for row in history["pretrim_sequence_rows"]:
            _shape(row, {"family_id", "feature_id", "genome_id", "value"}, "history_row_shape_invalid")
            fid, feature = row["family_id"], row["feature_id"]
            for key in ("family_id", "feature_id", "genome_id"):
                c.text(row[key])
            _need(fid in pop["family_ids"] and (fid not in expected or feature in expected[fid]), "history_member_conflict")
            _need(feature not in seen_features, "history_duplicate_feature")
            seen_features.add(feature)
            join = joins.get(feature)
            _need(join is not None and join["family_id"] == fid and join["genome_id"] == row["genome_id"],
                  "history_feature_join_conflict")
            q = row["value"]
            _shape(q, {"value", "state", "unit", "origin", "numerator", "denominator", "population_ref", "method", "evidence", "requirement_ids"},
                   "history_quantity_shape_invalid")
            _need(q["unit"] == "bits_per_column" and q["origin"] in {"native_observed", "derived"}
                  and q["state"] in c.STATES, "history_quantity_invalid")
            for key in ("value", "numerator", "denominator"):
                c.number(q[key], nullable=True)
            _need((q["value"] is not None) == (q["state"] == "available"), "history_quantity_state_conflict")
            c.text(q["method"])
            c.evidence(q["evidence"])
            c.strings(q["requirement_ids"])
            np, ap = native.get(q["population_ref"]), aps.get(q["population_ref"])
            _need(np is not None and np["kind"] == "native_pretrim_alignment" or
                  ap is not None and ap["alignment_id"] not in final and bool(q["evidence"]),
                  "history_original_population_required")


def _namespace(sheet, fid, matrix):
    values = {r["family_namespace"] for r in sheet["joins"]["feature_genomes"]
              if r["family_id"] == fid and r["family_namespace"] is not None}
    if matrix is not None and fid in next(p["family_ids"] for p in sheet["assembly"]["caller_populations"]["families"]
                                         if p["population_id"] == matrix["family_population_id"]):
        values.add(matrix["namespace"])
    values.update(s["value"] for s in sheet["observed_run"]["settings"]
                  if s["name"] == "family_namespace" and s["origin"] == "observed" and s["value"] is not None)
    _need(len(values) <= 1, "family_namespace_conflict")
    return next(iter(values)) if values else None


def _add_population(sheet, collection, value):
    for category in sheet["populations"].values():
        for old in category:
            _need(old["population_id"] != value["population_id"], "generated_population_collision")
    sheet["populations"][collection].append(value)


def _population_id(sheet, *parts):
    return "analysis/" + quote(sheet["assembly"]["analysis_id"], safe="") + "/codon/" + "/".join(quote(str(p), safe="") for p in parts)


def _selected(values, table_id):
    matches = [r for r in values if r["table"]["table_id"] == table_id]
    _need(len(matches) <= 1 or all(x == matches[0] for x in matches), "native_table_conflict")
    return matches[0] if matches else None


def _selected_tables(sheet):
    analysis = sheet["documents"]["analyses"][0]
    tables = {t["table_id"]: t for t in sheet["documents"]["store"]["native_tables"]}
    result = {}
    for field, suffix in (("membership_document_id", "codon_membership"),
                          ("family_stats_document_id", "codon_family_statistics"),
                          ("genome_counts_document_id", "codon_genome_counts"),
                          ("analysis_stats_document_id", "codon_analysis_statistics")):
        table = tables.get(analysis[field])
        _need(analysis[field] is None or table is not None and
              table["table_id"] == table["artifact"]["raw_artifact_ref"] + "#" + suffix,
              "analysis_native_table_kind_conflict")
        result[field] = table
    return result


def _tip_genomes(sheet, rows):
    result = {}
    for join in sheet["joins"]["tip_rows"]:
        gid = rows.get((join["alignment_id"], join["row_index"]))
        if gid is not None:
            key = (join["tree_id"], join["node_index"])
            _need(key not in result or result[key] == gid, "tip_genome_conflict")
            result[key] = gid
    for join in sheet["joins"]["display_tips"]:
        gid = result.get((join["raw_tree_id"], join["raw_node_index"]))
        if gid is not None:
            key = (join["display_tree_id"], join["display_node_index"])
            _need(key not in result or result[key] == gid, "tip_genome_conflict")
            result[key] = gid
    return result


def _primary_tree_ids(sheet):
    analysis = sheet["documents"]["analyses"][0]
    return list(dict.fromkeys(analysis[k] for k in ("raw_tree_id", "supported_tree_id",
        "rooted_derivative_tree_id", "display_tree_id", "phyloxml_tree_id") if analysis[k] is not None))


def _returned_genome_populations(sheet):
    """Native positive family counts establish this separately named scope."""
    table = _selected_tables(sheet)["genome_counts_document_id"]
    if table is None:
        return []
    counts = [o for o in sheet["native_measurements"] if o["field"] == "genome_native_all_families"
              and o["location"] is not None and o["location"]["artifact"] == table["artifact"]]
    return [{"population_id": _population_id(sheet, table["table_id"], "returned_family_records"),
        "genome_ids": list(dict.fromkeys(o["subject_id"] for o in counts if o["value"] is not None and o["value"] > 0)),
        "stage": "returned_family_records", "completeness": table["completeness"] if all(
            o["state"] == "available" for o in counts) else "partial", "evidence": []}]


def _validate_biological_populations(sheet):
    """Check each saved stage registry against its declared original source."""
    analysis = sheet["documents"]["analyses"][0]
    tables = _selected_tables(sheet)
    expected = {k: deepcopy(sheet["assembly"]["caller_populations"][k]) for k in ("families", "genomes")}
    for field, stage in (("membership_document_id", "selected"), ("family_stats_document_id", "evaluated_pretrim")):
        table = tables[field]
        if table is None:
            continue
        ids = list(dict.fromkeys(r["family_id"] for r in table["rows"]
                  if r["record_kind"] in {"data", "missing_codon_alignment"} and r["family_id"] is not None))
        expected["families"].append({"population_id": _population_id(sheet, table["table_id"], stage),
            "family_ids": ids, "stage": stage, "completeness": table["completeness"], "evidence": []})
    _, rows = _row_genomes(sheet)
    alignment = next((a for a in sheet["documents"]["store"]["alignments"]
                      if a["alignment_id"] == analysis["final_alignment_id"]), None)
    if alignment is not None:
        gids = [rows[(alignment["alignment_id"], row["row_index"])] for row in alignment["rows"]
                if (alignment["alignment_id"], row["row_index"]) in rows]
        expected["genomes"].append({"population_id": _population_id(sheet, alignment["alignment_id"], "genomes"),
            "genome_ids": list(dict.fromkeys(gids)), "stage": "used_final_alignment",
            "completeness": alignment["completeness"] if len(gids) == len(alignment["rows"]) else "partial", "evidence": []})
    tips, trees = _tip_genomes(sheet, rows), _trees(sheet)
    for tid in _primary_tree_ids(sheet):
        nodes = [n for n in trees[tid]["nodes"] if not n["child_indices"]]
        gids = [tips[(tid, n["node_index"])] for n in nodes if (tid, n["node_index"]) in tips]
        expected["genomes"].append({"population_id": _population_id(sheet, tid, "genomes"),
            "genome_ids": list(dict.fromkeys(gids)), "stage": "used_final_tree",
            "completeness": "complete" if len(gids) == len(nodes) else "partial", "evidence": []})
    expected["genomes"].extend(_returned_genome_populations(sheet))
    for category in expected:
        _need({p["population_id"]: p for p in sheet["populations"][category]} ==
              {p["population_id"]: p for p in expected[category]}, "biological_population_source_conflict")


def _build_families(sheet, documents, matrix):
    analysis = sheet["documents"]["analyses"][0]
    membership = _selected(documents["membership"], analysis["membership_document_id"])
    stats = _selected(documents["family_statistics"], analysis["family_stats_document_id"])
    joins = {r["feature_id"]: r for r in sheet["joins"]["feature_genomes"]}
    ids = list(dict.fromkeys([r["family_id"] for r in matrix["rows"]] if matrix else []))
    ids += [r["family_id"] for r in sheet["joins"]["feature_genomes"] if r["family_id"] is not None]
    ids += [f for p in sheet["populations"]["families"] for f in p["family_ids"]]
    if membership:
        ids += [r["family_id"] for r in membership["rows"]] + membership["missing_codon_family_ids"]
    if stats:
        ids += [r["family_id"] for r in stats["rows"]]
    ids += [r["family_id"] for r in sheet["joins"]["family_blocks"]]
    records = {}
    for fid in dict.fromkeys(ids):
        namespace = _namespace(sheet, fid, matrix)
        if namespace is None:
            _missing(sheet, "family_namespace_required", fid, path="/families")
            continue
        rows = [{"genome_id": r["genome_id"], "feature_ids": deepcopy(r["feature_ids"])}
                for r in matrix["rows"] if r["family_id"] == fid] if matrix else []
        records[fid] = {"family_id": fid, "namespace": namespace, "matrix": rows,
            "matrix_completeness": matrix["completeness"] if matrix is not None and
                fid in next(p["family_ids"] for p in sheet["assembly"]["caller_populations"]["families"]
                            if p["population_id"] == matrix["family_population_id"]) else "unknown",
            "memberships": [], "inclusion": [], "native_statistic_observation_ids": [],
            "final_block_indices": [i for i, b in enumerate(sheet["joins"]["family_blocks"]) if b["family_id"] == fid]}
    for population in sheet["populations"]["families"]:
        for fid in population["family_ids"]:
            if fid in records:
                records[fid]["inclusion"].append(_included(fid, population["stage"], evidence=population["evidence"]))
    if membership:
        table = membership["table"]
        for row in membership["rows"]:
            fid = row["family_id"]
            if fid not in records:
                continue
            lists = [row[k] for k in ("included_feature_ids", "deleted_feature_ids", "missing_codon_feature_ids")]
            if set(lists[0]).intersection(lists[1] + lists[2]):
                _missing(sheet, "native_membership_conflict", table["table_id"] + "/" + str(row["source_row_index"]),
                         path="/families", refs=[table["artifact"]["source_ref"]], severity="error")
                continue
            if any(len(v) != len(set(v)) for v in lists):
                sheet["qualifications"].append(_diagnostic("native_membership_unique_projection",
                    "/documents/store/native_tables", [table["artifact"]["source_ref"]]))
                lists = [list(dict.fromkeys(v)) for v in lists]
            genomes = []
            for feature in lists[0] + lists[1] + lists[2]:
                join = joins.get(feature)
                if join is None or join["family_id"] is None or join["family_namespace"] is None:
                    _missing(sheet, "feature_genome_association_required", feature, path="/joins/feature_genomes")
                else:
                    _need((join["family_id"], join["family_namespace"]) == (fid, records[fid]["namespace"]),
                          "membership_feature_join_conflict")
                    if feature in lists[0] and join["genome_id"] not in genomes:
                        genomes.append(join["genome_id"])
            records[fid]["memberships"].append({"representation": row["representation"],
                "feature_ids": deepcopy(lists[0]), "genome_ids": genomes,
                "deleted_feature_ids": deepcopy(lists[1]), "missing_codon_feature_ids": deepcopy(lists[2]),
                "source_table_id": table["table_id"], "source_row_index": row["source_row_index"]})
            loc = table["rows"][row["source_row_index"]]["location"]
            stage = "final_" + row["representation"]
            records[fid]["inclusion"].append(_included(fid, stage, location=loc))
            records[fid]["inclusion"].extend(_included(f, stage, state="excluded", reason="deleted_paralog", location=loc) for f in lists[1])
            records[fid]["inclusion"].extend(_included(f, "final_coding_nucleotide", state="excluded",
                reason="missing_codon_alignment", location=loc) for f in lists[2])
        for fid in membership["missing_codon_family_ids"]:
            if fid in records:
                loc = next(r["location"] for r in table["rows"] if r["family_id"] == fid and r["record_kind"] == "missing_codon_alignment")
                records[fid]["inclusion"].append(_included(fid, "final_coding_nucleotide", state="excluded",
                    reason="missing_codon_alignment", location=loc))
        _add_population(sheet, "families", {"population_id": _population_id(sheet, table["table_id"], "selected"),
            "family_ids": list(dict.fromkeys([r["family_id"] for r in membership["rows"]] + membership["missing_codon_family_ids"])),
            "stage": "selected", "completeness": table["completeness"], "evidence": []})
    if stats:
        table = stats["table"]
        for row in stats["rows"]:
            fid = row["family_id"]
            if fid not in records:
                continue
            records[fid]["native_statistic_observation_ids"].extend(row["observation_ids"])
            loc = table["rows"][row["source_row_indices"][0]]["location"]
            records[fid]["inclusion"].append(_included(fid, "evaluated_pretrim", location=loc))
            reason = {"bad seqs": "native_bad_sequence", "low alignment score": "native_low_alignment_score"}.get(row["disqualification"])
            records[fid]["inclusion"].append(_included(fid, "selected", state="unknown" if row["used_in_tree"] is None
                else "included" if row["used_in_tree"] else "excluded", reason=reason, location=loc))
            if row["used_in_tree"] is False and records[fid]["memberships"]:
                sheet["qualifications"].append(_diagnostic("native_stage_conflict", "/families",
                    [table["artifact"]["source_ref"]], severity="error"))
        _add_population(sheet, "families", {"population_id": _population_id(sheet, table["table_id"], "evaluated_pretrim"),
            "family_ids": list(dict.fromkeys(r["family_id"] for r in stats["rows"])), "stage": "evaluated_pretrim",
            "completeness": table["completeness"], "evidence": []})
    for family in records.values():
        for row in family["memberships"]:
            if not any(sheet["joins"]["family_blocks"][i]["representation"] == row["representation"] for i in family["final_block_indices"]):
                _missing(sheet, "final_family_coordinates_required", family["family_id"] + "/" + row["representation"], path="/joins/family_blocks")
        protein = {f for r in family["memberships"] if r["representation"] == "protein" for f in r["feature_ids"]}
        codons = {f for r in family["memberships"] if r["representation"] == "coding_nucleotide" for f in r["feature_ids"]}
        if protein & codons:
            sheet["dependence_groups"].append({"group_id": _population_id(sheet, "dependence", family["family_id"]),
                "kind": "protein_and_coding_nucleotide", "subject_ids": [
                    r["source_table_id"] + "/row/" + str(r["source_row_index"]) for r in family["memberships"]
                    if set(r["feature_ids"]) & protein & codons], "evidence": []})
    sheet["families"] = list(records.values())


def _build_genomes(sheet, documents):
    analysis = sheet["documents"]["analyses"][0]
    members, rows = _row_genomes(sheet)
    records = {}
    for binding in sheet["inputs"]:
        for member in binding["members"]:
            if (binding["binding_id"], member["member_id"]) not in members:
                _missing(sheet, "member_genome_association_required",
                    input_member_subject_id(binding["binding_id"], member["member_id"]), path="/inputs")
    requested_optional = [r for r in sheet["assembly"]["genome_request_sets"] if r["kind"] == "optional_ids"]
    for request in sheet["assembly"]["genome_request_sets"]:
        if request["population"]["completeness"] != "complete":
            _missing(sheet, "requested_genome_membership_required", request["set_id"], path="/assembly/genome_request_sets")
    if requested_optional and not any(r["kind"] == "actually_forwarded_optional"
                                     for r in sheet["assembly"]["genome_request_sets"]):
        for request in requested_optional:
            _missing(sheet, "optional_forwarding_required", request["set_id"], path="/assembly/genome_request_sets")
    def get(gid):
        return records.setdefault(gid, {"genome_id": gid, "input_members": [], "final_alignment_rows": [],
            "final_tree_tips": [], "inclusion": [], "native_count_observation_ids": []})
    for pop in sheet["populations"]["genomes"]:
        for gid in pop["genome_ids"]:
            stage = {"requested_main": "requested", "requested_optional": "requested", "actually_forwarded_optional": "requested",
                     "returned_family_records": "returned", "used_final_alignment": "final_matrix", "used_final_tree": "final_tree"}[pop["stage"]]
            get(gid)["inclusion"].append(_included(gid, stage, evidence=pop["evidence"]))
    for join in sheet["joins"]["feature_genomes"]:
        get(join["genome_id"])
    for (binding_id, member_id), gid in members.items():
        get(gid)["input_members"].append({"input_binding_id": binding_id, "member_id": member_id})
    alignment = next((a for a in sheet["documents"]["store"]["alignments"] if a["alignment_id"] == analysis["final_alignment_id"]), None)
    if alignment is not None:
        gids = []
        for row in alignment["rows"]:
            gid = rows.get((alignment["alignment_id"], row["row_index"]))
            if gid is None:
                _missing(sheet, "genome_row_association_required", alignment["alignment_id"] + "/" + str(row["row_index"]), path="/joins/input_rows")
                continue
            get(gid)["final_alignment_rows"].append({"alignment_id": alignment["alignment_id"], "row_index": row["row_index"]})
            get(gid)["inclusion"].append(_included(gid, "final_matrix", location=row["source_location"]))
            gids.append(gid)
        _add_population(sheet, "genomes", {"population_id": _population_id(sheet, alignment["alignment_id"], "genomes"),
            "genome_ids": list(dict.fromkeys(gids)), "stage": "used_final_alignment", "completeness":
            alignment["completeness"] if len(gids) == len(alignment["rows"]) else "partial", "evidence": []})
    trees = _trees(sheet)
    tip_genomes = _tip_genomes(sheet, rows)
    tree_ids = _primary_tree_ids(sheet)
    for tid in tree_ids:
        tips = [n for n in trees[tid]["nodes"] if not n["child_indices"]]
        gids = []
        for tip in tips:
            gid = tip_genomes.get((tid, tip["node_index"]))
            if gid is None:
                _missing(sheet, "genome_tip_association_required", tid + "/" + str(tip["node_index"]), path="/joins/tip_rows")
                continue
            get(gid)["final_tree_tips"].append({"tree_id": tid, "node_index": tip["node_index"]})
            get(gid)["inclusion"].append(_included(gid, "final_tree", location=tip["source_location"]))
            gids.append(gid)
        _add_population(sheet, "genomes", {"population_id": _population_id(sheet, tid, "genomes"),
            "genome_ids": list(dict.fromkeys(gids)), "stage": "used_final_tree",
            "completeness": "complete" if len(gids) == len(tips) else "partial", "evidence": []})
    counts = _selected(documents["genome_counts"], analysis["genome_counts_document_id"])
    if counts:
        observations = {o["observation_id"]: o for o in counts["observations"]}
        for row in counts["rows"]:
            genome = get(row["genome_id"])
            genome["native_count_observation_ids"].extend(row[k] for k in ("all_families_observation_id", "single_copy_observation_id", "filtered_single_copy_observation_id"))
            count = observations[row["all_families_observation_id"]]
            if count["value"] == 0:
                genome["inclusion"].append(_included(row["genome_id"], "returned", state="excluded",
                    reason="zero_family_records", location=count["location"]))
            elif count["value"] is not None:
                genome["inclusion"].append(_included(row["genome_id"], "returned", location=count["location"]))
    for population in _returned_genome_populations(sheet):
        _add_population(sheet, "genomes", population)
    sheet["genomes"] = list(records.values())


def _build_models(sheet, documents):
    analysis = sheet["documents"]["analyses"][0]
    partitions = {d["document_id"]: d for d in sheet["documents"]["store"]["partitions"]}
    reads = {r["read_id"]: r for r in documents["reads"]}
    models, covered = [], set()
    for assoc in sheet["assembly"]["model_associations"]:
        read = reads.get(assoc["read_id"])
        _need(read is not None and read["reader"]["reader"] == "raxml_run_log" and read["result"]["value"] is not None,
              "model_read_missing")
        index = assoc["log_model_index"]
        c.integer(index)
        native = read["result"]["value"]["models"]
        _need(index < len(native), "model_index_outside_read")
        model = native[index]
        did, pi = assoc["partition_document_id"], assoc["partition_index"]
        _need((did is None) == (pi is None), "model_partition_pair_invalid")
        partition = None
        if did is not None:
            _need(did == analysis["partition_document_id"] and did in partitions, "model_partition_document_conflict")
            partition = next((p for p in partitions[did]["partitions"] if p["partition_index"] == pi), None)
            _need(partition is not None, "model_partition_index_missing")
            _need(model["partition_index"] == pi and model["partition_name"] == partition["name"], "model_partition_identity_conflict")
            # RAxML's partition F suffix requests empirical frequencies. Its
            # log reports the base substitution matrix separately (LGF -> LG),
            # so retain the partition token and the actual fitted parameters.
            compatible = (partition["model_token"] == "DNA" and model["datatype"] in {"dna", "unknown"}
                or partition["model_token"] == model["model_token"]
                or model["datatype"] == "protein" and model["model_token"] is not None
                   and partition["model_token"] == model["model_token"] + "F")
            _need(compatible, "model_partition_token_conflict")
            covered.add(pi)
        name = partition["name"] if partition else model["partition_name"]
        token = partition["model_token"] if partition else model["model_token"]
        if name is None or token is None:
            _missing(sheet, "partition_model_association_required", assoc["read_id"] + "/" + str(index), path="/models")
            continue
        models.append({"analysis_id": analysis["analysis_id"], "partition_name": name, "model_token": token,
            "datatype": model["datatype"], "branch_optimization": model["branch_optimization"],
            "parameters": deepcopy(model["parameters"]), "model_selection_command_id": assoc["model_selection_command_id"],
            "sample_alignment_id": assoc["sample_alignment_id"], "sample_column_map": deepcopy(assoc["sample_column_map"]),
            "evidence": deepcopy(assoc["evidence"])})
        if assoc["sample_alignment_id"] is not None and assoc["sample_column_map"] is None:
            _missing(sheet, "model_sample_correspondence_required", assoc["sample_alignment_id"], path="/models")
    if analysis["partition_document_id"] is not None:
        for partition in partitions[analysis["partition_document_id"]]["partitions"]:
            if partition["partition_index"] in covered:
                continue
            models.append({"analysis_id": analysis["analysis_id"], "partition_name": partition["name"],
                "model_token": partition["model_token"], "datatype": "dna" if partition["model_token"] == "DNA" else "unknown",
                "branch_optimization": "unknown", "parameters": [], "model_selection_command_id": None,
                "sample_alignment_id": None, "sample_column_map": None, "evidence": []})
            _missing(sheet, "partition_model_association_required", analysis["partition_document_id"] + "/" + str(partition["partition_index"]), path="/models")
    sheet["models"] = models
    for i, model in enumerate(models):
        for other in models[:i]:
            if _models_conflict(model, other):
                refs = [p["native_location"]["artifact"]["source_ref"]
                        for m in (model, other) for p in m["parameters"]]
                diagnostic = _diagnostic("model_record_conflict", "/models", refs, severity="error")
                if diagnostic not in sheet["qualifications"]:
                    sheet["qualifications"].append(diagnostic)


def _models_conflict(left, right):
    if left["partition_name"] != right["partition_name"]:
        return False
    keys = ("model_token", "datatype", "branch_optimization")
    return any(left[k] != right[k] for k in keys) or [
        (p["name"], p["value"]) for p in left["parameters"]] != [
        (p["name"], p["value"]) for p in right["parameters"]]


def _validate_models(sheet):
    analysis = sheet["documents"]["analyses"][0]
    reads = {r["read_id"]: r for r in sheet["read_outcomes"]}
    alignments = {r["alignment_id"]: r for r in sheet["documents"]["store"]["alignments"]}
    partitions = {d["document_id"]: d for d in sheet["documents"]["store"]["partitions"]}
    commands = {r["command_id"]: r for r in sheet["observed_run"]["commands"]}
    seen = set()
    for assoc in sheet["assembly"]["model_associations"]:
        _shape(assoc, {"read_id", "log_model_index", "partition_document_id", "partition_index", "model_selection_command_id",
                       "sample_alignment_id", "sample_column_map", "evidence"}, "model_association_shape_invalid")
        c.integer(assoc["log_model_index"])
        c.evidence(assoc["evidence"])
        key = (assoc["read_id"], assoc["log_model_index"], assoc["partition_document_id"], assoc["partition_index"])
        _need(key not in seen, "duplicate_model_association")
        seen.add(key)
        read = reads.get(assoc["read_id"])
        _need(read is not None and read["reader"]["reader"] == "raxml_run_log" and read["value_present"], "model_read_missing")
        did, pi = assoc["partition_document_id"], assoc["partition_index"]
        _need((did is None) == (pi is None), "model_partition_pair_invalid")
        if did is not None:
            _need(did == analysis["partition_document_id"] and did in partitions, "model_partition_document_conflict")
            _need(any(p["partition_index"] == pi for p in partitions[did]["partitions"]), "model_partition_index_missing")
        if assoc["model_selection_command_id"] is not None:
            command = commands.get(assoc["model_selection_command_id"])
            _need(command is not None and command["origin"] == "observed" and command["role"] == "model_selection",
                  "model_selection_command_conflict")
        sid, mapping = assoc["sample_alignment_id"], assoc["sample_column_map"]
        _need(sid is not None or mapping is None, "model_sample_map_without_sample")
        if sid is not None:
            _need(sid in alignments and sid != analysis["final_alignment_id"], "model_sample_alignment_conflict")
        if mapping is not None:
            c.unique_indices(mapping)
            final = alignments.get(analysis["final_alignment_id"])
            _need(final is not None and final["observed_column_count"] is not None
                  and alignments[sid]["completeness"] == "complete"
                  and alignments[sid]["observed_column_count"] == len(mapping)
                  and all(col < final["observed_column_count"] for col in mapping)
                  and bool(assoc["evidence"]), "model_sample_map_conflict")
    for model in sheet["models"]:
        _shape(model, _MODEL_KEYS, "model_shape_invalid")
        _need(model["analysis_id"] == analysis["analysis_id"], "model_analysis_conflict")
        c.text(model["partition_name"])
        c.text(model["model_token"])
        _need(model["datatype"] in {"dna", "rna", "protein", "unknown", "mixed"}
              and model["branch_optimization"] in {"joint", "separate", "unknown"}, "model_value_invalid")
        c.sequence(model["parameters"], stored=True)
        c.evidence(model["evidence"])
        possible = []
        for assoc in sheet["assembly"]["model_associations"]:
            if all(model[k] == assoc[k] for k in ("model_selection_command_id", "sample_alignment_id", "sample_column_map", "evidence")):
                if assoc["partition_document_id"] is None or any(p["partition_index"] == assoc["partition_index"] and
                    p["name"] == model["partition_name"] and p["model_token"] == model["model_token"]
                    for p in partitions[assoc["partition_document_id"]]["partitions"]):
                    possible.append(reads[assoc["read_id"]]["artifact"])
        for param in model["parameters"]:
            _shape(param, {"name", "value", "native_location"}, "model_parameter_shape_invalid")
            c.text(param["name"])
            c.number(param["value"])
            c.location(param["native_location"])
            _need(param["native_location"]["artifact"] in possible, "model_parameter_source_conflict")
        if not possible:
            _need(not model["parameters"] and model["branch_optimization"] == "unknown" and
                  model["model_selection_command_id"] is None and model["sample_alignment_id"] is None and
                  model["sample_column_map"] is None, "model_native_association_missing")
            _need(any(p["name"] == model["partition_name"] and p["model_token"] == model["model_token"]
                  for d in partitions.values() if d["document_id"] == analysis["partition_document_id"] for p in d["partitions"]),
                  "model_partition_missing")
    for i, model in enumerate(sheet["models"]):
        _need(not any(_models_conflict(model, other) for other in sheet["models"][:i]) or any(
            d["code"] == "codon_provider_model_record_conflict" and d["severity"] == "error"
            for d in sheet["qualifications"]), "model_conflict_qualification_missing")
    if analysis["partition_document_id"] is not None:
        for partition in partitions[analysis["partition_document_id"]]["partitions"]:
            _need(any(model["partition_name"] == partition["name"] and model["model_token"] == partition["model_token"]
                      for model in sheet["models"]), "model_partition_records_incomplete")


def _validate_family_inclusions(sheet, family, tables):
    fid = family["family_id"]
    allowed = [_included(fid, p["stage"], evidence=p["evidence"])
               for p in sheet["assembly"]["caller_populations"]["families"] if fid in p["family_ids"]]
    membership = tables["membership_document_id"]
    if membership is not None:
        for row in family["memberships"]:
            loc = membership["rows"][row["source_row_index"]]["location"]
            stage = "final_" + row["representation"]
            allowed.append(_included(fid, stage, location=loc))
            allowed.extend(_included(f, stage, state="excluded", reason="deleted_paralog", location=loc)
                           for f in row["deleted_feature_ids"])
            allowed.extend(_included(f, "final_coding_nucleotide", state="excluded",
                reason="missing_codon_alignment", location=loc) for f in row["missing_codon_feature_ids"])
        # Some producer records span a bare family line and its message. Both
        # positions remain saved; the typed inclusion points at the first one.
        missing = [r for r in membership["rows"] if r["family_id"] == fid and r["record_kind"] == "missing_codon_alignment"]
        if missing:
            allowed.append(_included(fid, "final_coding_nucleotide", state="excluded",
                reason="missing_codon_alignment", location=missing[0]["location"]))
    stats = tables["family_stats_document_id"]
    if stats is not None:
        for i, row in enumerate(stats["rows"]):
            if row["record_kind"] != "data" or row["family_id"] != fid:
                continue
            allowed.append(_included(fid, "evaluated_pretrim", location=row["location"]))
            following = []
            for other in stats["rows"][i + 1:]:
                if other["record_kind"] == "data":
                    break
                if other["family_id"] == fid and other["record_kind"] == "disqualification":
                    following.append(other)
            qualifiers = {other["raw_text"] for other in following
                          if other["raw_text"].startswith("disqualification: ")}
            reason = {"disqualification: bad seqs": "native_bad_sequence",
                "disqualification: low alignment score": "native_low_alignment_score"}.get(
                    next(iter(qualifiers))) if len(qualifiers) == 1 else None
            token = row["fields"][7]
            state = "included" if token == "True" else "excluded" if token == "False" else "unknown"
            allowed.append(_included(fid, "selected", state=state, reason=reason, location=row["location"]))
    _need(all(item in allowed for item in family["inclusion"]) and
          all(item in family["inclusion"] for item in allowed), "family_inclusion_source_conflict")


def _validate_genome_inclusions(sheet, genome, alignments, trees, observations):
    gid = genome["genome_id"]
    stages = {"requested_main": "requested", "requested_optional": "requested", "actually_forwarded_optional": "requested",
              "returned_family_records": "returned", "used_final_alignment": "final_matrix", "used_final_tree": "final_tree"}
    allowed = [_included(gid, stages[p["stage"]], evidence=p["evidence"])
               for p in sheet["assembly"]["caller_populations"]["genomes"] if gid in p["genome_ids"]]
    allowed.extend(_included(gid, "final_matrix", location=alignments[r["alignment_id"]]["rows"][r["row_index"]]["source_location"])
                   for r in genome["final_alignment_rows"])
    allowed.extend(_included(gid, "final_tree", location=trees[t["tree_id"]]["nodes"][t["node_index"]]["source_location"])
                   for t in genome["final_tree_tips"])
    for oid in genome["native_count_observation_ids"]:
        obs = observations[oid]
        if obs["field"] == "genome_native_all_families" and obs["value"] is not None:
            allowed.append(_included(gid, "returned", state="excluded" if obs["value"] == 0 else "included",
                reason="zero_family_records" if obs["value"] == 0 else None, location=obs["location"]))
    _need(all(item in allowed for item in genome["inclusion"]) and
          all(item in genome["inclusion"] for item in allowed), "genome_inclusion_source_conflict")


def _validate_arrays(sheet, matrix):
    tables = {t["table_id"]: t for t in sheet["documents"]["store"]["native_tables"]}
    observations = {o["observation_id"]: o for o in sheet["native_measurements"]}
    joins = {j["feature_id"]: j for j in sheet["joins"]["feature_genomes"]}
    families = _unique(sheet["families"], "family_id", "duplicate_family_id")
    selected_tables = _selected_tables(sheet)
    blocks = sheet["joins"]["family_blocks"]
    analysis = sheet["documents"]["analyses"][0]
    alignments = {a["alignment_id"]: a for a in sheet["documents"]["store"]["alignments"]}
    required_families = {fid for p in sheet["populations"]["families"] for fid in p["family_ids"]}
    required_families.update(j["family_id"] for j in joins.values() if j["family_id"] is not None)
    required_families.update(b["family_id"] for b in blocks)
    _need(set(families) == {fid for fid in required_families if _namespace(sheet, fid, matrix) is not None},
          "family_records_incomplete")
    for i, block in enumerate(blocks):
        _shape(block, {"alignment_id", "family_id", "representation", "columns_0based", "member_row_indices", "evidence"}, "family_block_shape_invalid")
        _need(block["representation"] in {"protein", "coding_nucleotide"}, "family_block_representation_invalid")
        c.unique_indices(block["columns_0based"])
        c.unique_indices(block["member_row_indices"])
        c.evidence(block["evidence"])
        _need(block["alignment_id"] in {analysis["final_alignment_id"], *analysis["per_family_final_alignment_ids"]}, "family_block_final_stage_required")
        alignment = alignments[block["alignment_id"]]
        bound = alignment["observed_column_count"]
        _need(bound is not None and all(x < bound for x in block["columns_0based"])
              and all(x < len(alignment["rows"]) for x in block["member_row_indices"]), "family_block_outside_alignment")
        for previous in blocks[:i]:
            _need(previous["alignment_id"] != block["alignment_id"] or
                  not set(previous["columns_0based"]).intersection(block["columns_0based"]), "family_blocks_overlap")
    for fid, family in families.items():
        _shape(family, _FAMILY_KEYS, "family_shape_invalid")
        c.text(fid)
        _need(family["namespace"] == _namespace(sheet, fid, matrix) and family["namespace"] in {"PGFam", "PLFam"}, "family_namespace_conflict")
        _need(family["matrix_completeness"] in c.COMPLETENESS, "matrix_completeness_invalid")
        c.sequence(family["matrix"], stored=True)
        expected = [{"genome_id": r["genome_id"], "feature_ids": r["feature_ids"]} for r in matrix["rows"] if r["family_id"] == fid] if matrix else []
        _need(family["matrix"] == expected, "family_matrix_source_conflict")
        source_complete = matrix["completeness"] if matrix is not None and (expected or fid in next(
            p["family_ids"] for p in sheet["assembly"]["caller_populations"]["families"] if p["population_id"] == matrix["family_population_id"])) else "unknown"
        _need(family["matrix_completeness"] == source_complete, "family_matrix_completeness_conflict")
        _inclusions(family["inclusion"])
        c.strings(family["native_statistic_observation_ids"])
        c.sequence(family["memberships"], stored=True)
        stats_table = selected_tables["family_stats_document_id"]
        expected_observations = [o["observation_id"] for o in sheet["native_measurements"]
            if stats_table is not None and o["location"] is not None and
            o["location"]["artifact"] == stats_table["artifact"] and o["subject_id"] == fid
            and o["field"].startswith("family_native_")]
        for oid in family["native_statistic_observation_ids"]:
            o = observations.get(oid)
            _need(o is not None and o["subject_id"] == fid and o["field"].startswith("family_native_"), "family_statistic_reference_conflict")
        _need(family["native_statistic_observation_ids"] == expected_observations, "family_statistic_source_conflict")
        c.unique_indices(family["final_block_indices"])
        _need(family["final_block_indices"] == [i for i, b in enumerate(blocks) if b["family_id"] == fid], "family_block_reference_conflict")
        seen = set()
        for membership in family["memberships"]:
            _shape(membership, _MEMBERSHIP_KEYS, "membership_shape_invalid")
            _need(membership["representation"] in {"protein", "coding_nucleotide"}, "membership_representation_invalid")
            for key in ("feature_ids", "genome_ids", "deleted_feature_ids", "missing_codon_feature_ids"):
                c.strings(membership[key])
            key = (membership["source_table_id"], membership["source_row_index"])
            _need(key not in seen, "duplicate_membership_reference")
            seen.add(key)
            table = tables.get(key[0])
            c.integer(key[1])
            _need(table is not None and table["table_id"] == analysis["membership_document_id"] and key[1] < len(table["rows"]), "membership_source_missing")
            row = table["rows"][key[1]]
            _need(row["family_id"] == fid and row["record_kind"] == "data", "membership_source_family_conflict")
            fields = [fid, "Proteins" if membership["representation"] == "protein" else "Codons", ""] + membership["feature_ids"]
            if membership["deleted_feature_ids"]:
                _need(membership["representation"] == "protein", "membership_marker_conflict")
                fields += ["deletedParalogs: "] + membership["deleted_feature_ids"]
            if membership["missing_codon_feature_ids"]:
                _need(membership["representation"] == "coding_nucleotide", "membership_marker_conflict")
                fields += [f"lacking CodonAlignment for {fid}: "] + membership["missing_codon_feature_ids"]
            native_fields = row["fields"]
            marker = "deletedParalogs: " if membership["representation"] == "protein" else f"lacking CodonAlignment for {fid}: "
            if marker in native_fields[3:]:
                where = native_fields.index(marker, 3)
                projected = native_fields[:3] + list(dict.fromkeys(native_fields[3:where])) + [marker] + list(dict.fromkeys(native_fields[where + 1:]))
            else:
                projected = native_fields[:3] + list(dict.fromkeys(native_fields[3:]))
            _need(fields == projected, "membership_native_fields_conflict")
            if projected != native_fields:
                _need(any(d["code"] == "codon_provider_native_membership_unique_projection" and
                      table["artifact"]["source_ref"] in d["evidence_refs"] for d in sheet["qualifications"]),
                      "membership_projection_qualification_missing")
            _need(not set(membership["feature_ids"]).intersection(membership["deleted_feature_ids"] + membership["missing_codon_feature_ids"]), "membership_feature_overlap")
            genomes = list(dict.fromkeys(joins[f]["genome_id"] for f in membership["feature_ids"] if f in joins and
                joins[f]["family_id"] is not None and joins[f]["family_namespace"] is not None))
            _need(membership["genome_ids"] == genomes, "membership_genome_conflict")
            for f in membership["feature_ids"] + membership["deleted_feature_ids"] + membership["missing_codon_feature_ids"]:
                if f in joins and joins[f]["family_id"] is not None and joins[f]["family_namespace"] is not None:
                    _need((joins[f]["family_id"], joins[f]["family_namespace"]) == (fid, family["namespace"]), "membership_feature_join_conflict")
                    if matrix is not None and family["matrix_completeness"] == "complete":
                        scope = next(p["genome_ids"] for p in sheet["assembly"]["caller_populations"]["genomes"]
                                     if p["population_id"] == matrix["genome_population_id"])
                        if joins[f]["genome_id"] in scope:
                            _need(any(r["genome_id"] == joins[f]["genome_id"] and f in r["feature_ids"]
                                      for r in family["matrix"]), "membership_feature_missing_from_complete_matrix")
        table = selected_tables["membership_document_id"]
        if table is not None:
            for native_row in table["rows"]:
                if native_row["family_id"] != fid or native_row["record_kind"] != "data":
                    continue
                fields = native_row["fields"]
                marker = "deletedParalogs: " if fields[1] == "Proteins" else f"lacking CodonAlignment for {fid}: "
                where = fields.index(marker, 3) if marker in fields[3:] else len(fields)
                contradiction = bool(set(fields[3:where]).intersection(fields[where + 1:]))
                source = (table["table_id"], native_row["row_index"])
                _need((source in seen) != contradiction, "membership_records_incomplete")
                if contradiction:
                    _need(any(r["requirement_id"] == "phylogeny/codon_provider/" + quote(
                        table["table_id"] + "/" + str(native_row["row_index"]), safe="") + "/native_membership_conflict"
                        for r in sheet["missing_requirements"]), "membership_conflict_requirement_missing")
        _validate_family_inclusions(sheet, family, selected_tables)
    members, rows = _row_genomes(sheet)
    genomes = _unique(sheet["genomes"], "genome_id", "duplicate_genome_id")
    required_genomes = {gid for p in sheet["populations"]["genomes"] for gid in p["genome_ids"]}
    required_genomes.update(j["genome_id"] for j in joins.values())
    required_genomes.update(members.values())
    count_table = selected_tables["genome_counts_document_id"]
    if count_table is not None:
        required_genomes.update(r["fields"][0] for r in count_table["rows"] if r["record_kind"] == "data")
    _need(set(genomes) == required_genomes, "genome_records_incomplete")
    tip_genomes, trees = _tip_genomes(sheet, rows), _trees(sheet)
    primary_trees = set(_primary_tree_ids(sheet))
    for gid, genome in genomes.items():
        _shape(genome, _GENOME_KEYS, "genome_shape_invalid")
        c.text(gid)
        _inclusions(genome["inclusion"])
        for key in ("input_members", "final_alignment_rows", "final_tree_tips"):
            c.sequence(genome[key], stored=True)
        seen = set()
        for m in genome["input_members"]:
            key = c.member(m)
            _need(key not in seen and members.get(key) == gid, "genome_input_member_conflict")
            seen.add(key)
        _need(seen == {key for key, mapped in members.items() if mapped == gid}, "genome_input_members_incomplete")
        for row in genome["final_alignment_rows"]:
            _shape(row, {"alignment_id", "row_index"}, "genome_row_shape_invalid")
            _need(row["alignment_id"] == analysis["final_alignment_id"] and rows.get((row["alignment_id"], row["row_index"])) == gid,
                  "genome_row_conflict")
        expected_rows = [{"alignment_id": aid, "row_index": i} for (aid, i), mapped in sorted(rows.items())
                         if aid == analysis["final_alignment_id"] and mapped == gid]
        _need(genome["final_alignment_rows"] == expected_rows, "genome_rows_incomplete")
        for tip in genome["final_tree_tips"]:
            _shape(tip, {"tree_id", "node_index"}, "genome_tip_shape_invalid")
            direct = [j for j in sheet["joins"]["tip_rows"] if (j["tree_id"], j["node_index"]) == (tip["tree_id"], tip["node_index"])]
            mapped = any(rows.get((j["alignment_id"], j["row_index"])) == gid for j in direct)
            if not mapped:
                mapped = any(any(t["tree_id"] == d["raw_tree_id"] and t["node_index"] == d["raw_node_index"]
                    for t in genome["final_tree_tips"]) for d in sheet["joins"]["display_tips"]
                    if d["display_tree_id"] == tip["tree_id"] and d["display_node_index"] == tip["node_index"])
            _need(mapped, "genome_tip_conflict")
        expected_tips = {(tid, index) for (tid, index), mapped in tip_genomes.items() if tid in primary_trees and mapped == gid}
        actual_tips = [(tip["tree_id"], tip["node_index"]) for tip in genome["final_tree_tips"]]
        _need(len(actual_tips) == len(set(actual_tips)) and set(actual_tips) == expected_tips, "genome_tips_incomplete")
        c.strings(genome["native_count_observation_ids"])
        for oid in genome["native_count_observation_ids"]:
            o = observations.get(oid)
            _need(o is not None and o["subject_id"] == gid and o["field"].startswith("genome_native_"), "genome_count_reference_conflict")
        expected_observations = [o["observation_id"] for o in sheet["native_measurements"]
            if count_table is not None and o["location"] is not None and o["location"]["artifact"] == count_table["artifact"]
            and o["subject_id"] == gid and o["field"].startswith("genome_native_")]
        _need(genome["native_count_observation_ids"] == expected_observations, "genome_count_source_conflict")
        _validate_genome_inclusions(sheet, genome, alignments, trees, observations)
    for group in sheet["dependence_groups"]:
        if group["kind"] == "protein_and_coding_nucleotide":
            possible = False
            for family in families.values():
                members = [m for m in family["memberships"] if
                    m["source_table_id"] + "/row/" + str(m["source_row_index"]) in group["subject_ids"]]
                represented = {m["source_table_id"] + "/row/" + str(m["source_row_index"]) for m in members}
                protein = {f for m in members if m["representation"] == "protein" for f in m["feature_ids"]}
                codons = {f for m in members if m["representation"] == "coding_nucleotide" for f in m["feature_ids"]}
                possible |= represented == set(group["subject_ids"]) and bool(protein & codons)
            _need(possible, "protein_codon_dependence_conflict")
    for family in families.values():
        protein = {f for m in family["memberships"] if m["representation"] == "protein" for f in m["feature_ids"]}
        codons = {f for m in family["memberships"] if m["representation"] == "coding_nucleotide" for f in m["feature_ids"]}
        if protein & codons:
            expected = {"group_id": _population_id(sheet, "dependence", family["family_id"]),
                "kind": "protein_and_coding_nucleotide", "subject_ids": [
                    m["source_table_id"] + "/row/" + str(m["source_row_index"]) for m in family["memberships"]
                    if set(m["feature_ids"]) & protein & codons], "evidence": []}
            _need(expected in sheet["dependence_groups"], "protein_codon_dependence_missing")


def validate_codon_tree_sheet(sheet: dict) -> dict:
    """Validate the saved sheet, without bytes, acquisition or calculator calls."""
    try:
        validate_shared_fields(sheet, provider="codon_tree")
        _need(all(sheet[k] == v for k, v in _HEADER.items()), "sheet_identity_conflict")
        _need(len(sheet["documents"]["analyses"]) == 1 and
              sheet["documents"]["analyses"][0]["analysis_id"] == sheet["assembly"]["analysis_id"], "primary_analysis_conflict")
        _need(sheet["assembly"]["locus_bindings"] == [], "codon_locus_bindings_forbidden")
        _validate_requests(sheet)
        matrix = _validate_matrices(sheet)
        _validate_biological_populations(sheet)
        _validate_historical(sheet)
        _validate_arrays(sheet, matrix)
        _validate_models(sheet)
    except (KeyError, TypeError, IndexError, StopIteration) as error:
        raise ValueError("codon_provider_operand_invalid") from error
    return deepcopy(sheet)


def extract_codon_tree_sheet(*, documents: dict, inputs: tuple[dict, ...], observed_run: dict,
                             joins: dict, assembly: dict, parameters: dict) -> dict:
    """Populate one explicit CodonTree analysis and preserve independent outcomes."""
    result = extract_common_fields(provider="codon_tree", documents=documents, inputs=inputs,
        observed_run=observed_run, joins=joins, assembly=assembly, parameters=parameters)
    if result["value"] is None:
        return result
    sheet = {**_HEADER, **result["value"], "genomes": [], "families": [], "models": []}
    try:
        _validate_requests(sheet)
        matrix = _validate_matrices(sheet)
        _selected_tables(sheet)
        _build_families(sheet, documents, matrix)
        _build_genomes(sheet, documents)
        _build_models(sheet, documents)
        sheet = validate_codon_tree_sheet(sheet)
    except (ValueError, KeyError, TypeError, IndexError, StopIteration) as error:
        # Structural caller conflicts do not manufacture a partially coherent
        # sheet. Original reader results remain with the supplying caller.
        code = str(error) if isinstance(error, ValueError) and str(error).startswith(
            ("codon_provider_", "phylogeny_", "bvbrc_phylogeny_")) else "codon_provider_operand_invalid"
        return {"status": "invalid", "value": None, "diagnostics": deepcopy(result["diagnostics"]) +
                [{"code": code, "phase": "association", "path": "", "severity": "error", "evidence_refs": []}]}
    diagnostics = deepcopy(sheet["qualifications"])
    partial = result["status"] != "ok" or any(d["severity"] == "error" for d in diagnostics)
    return {"status": "partial" if partial else "ok", "value": sheet, "diagnostics": diagnostics}
