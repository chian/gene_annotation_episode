"""Resolve explicitly selected artifact roles into the frozen provider operands.

All inputs are supplied values. There is no Store, filesystem, transport,
callback, resource selection, new analysis or scientific arithmetic here.
Only the declared semantic fields are compiled; JSON is never recursively
searched for strings that resemble identifiers.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from . import bvbrc_phylogeny_bundle_contracts as c
from .bvbrc_appservice_contracts import ContractValidationError, _at, _finite_json, _same, validate_contract
from . import phylogeny_formats as formats
from .phylogeny_raxml_inputs import parse_raxml_run_log
from . import bvbrc_codon_tree_native as codon_native


DIAGNOSTIC_CODES = frozenset({
    "phylogeny_artifact_missing", "phylogeny_artifact_ambiguous", "phylogeny_artifact_bytes_missing",
    "phylogeny_artifact_bytes_conflict", "phylogeny_complete_object_required", "phylogeny_declared_format_conflict",
    "phylogeny_parser_declaration_conflict", "phylogeny_selected_document_unavailable", "phylogeny_selected_tree_unavailable",
    "phylogeny_partition_alignment_required", "phylogeny_analysis_output_association_required",
    "phylogeny_original_input_conflict", "phylogeny_original_task_conflict", "phylogeny_population_unavailable",
    "phylogeny_join_dependency_unavailable", "phylogeny_calculation_dependency_unavailable",
    "supplemental_native_content_required", "supplemental_native_content_conflict", "supplemental_parsed_claim_conflict",
    "output_association_unproven", "output_version_unproven", "duplicate_artifact_representation",
    "phylogeny_scientific_inputs_required", "phylogeny_supplied_document_invalid", "phylogeny_supplied_inputs_invalid",
})


def diagnostic(code, path="", *, severity="error", refs=(), phase="association"):
    return {"code": code, "phase": phase, "path": path, "severity": severity,
            "evidence_refs": list(dict.fromkeys(refs))}


def requirement(reason, *, analysis_id, role=None, kind="scientific_metadata", identity="", refs=()):
    token = hashlib.sha256(json.dumps([analysis_id, reason, role, identity], separators=(",", ":")).encode()).hexdigest()
    return {"requirement_id": "phylogeny-bundle/" + token, "kind": kind, "role": role,
            "source_refs": list(dict.fromkeys(refs)), "reason_code": reason}


def merge_requirements(*registries):
    result = {}
    for registry in registries:
        for row in registry:
            validate_contract("AcquisitionRequirement", row)
            key = row["requirement_id"]
            c.require(key not in result or _same(result[key], row), "phylogeny_requirement_meaning_conflict")
            result[key] = deepcopy(row)
    return list(result.values())


def unique(rows):
    result = []
    for row in rows:
        if not any(_same(row, prior) for prior in result):
            result.append(deepcopy(row))
    return result


def parse_reader(data, *, artifact, spec):
    """Call one of the ten existing readers, without format inference."""
    c.validate_reader_spec(spec, planned=False)
    readers = {
        "newick": formats.parse_newick, "aligned_fasta": formats.parse_aligned_fasta,
        "relaxed_phylip": formats.parse_relaxed_phylip, "raxml_partitions": formats.parse_raxml_partitions,
        "phyloxml": formats.parse_phyloxml, "raxml_run_log": parse_raxml_run_log,
        "codon_membership": codon_native.parse_codon_membership,
        "codon_family_statistics": codon_native.parse_codon_family_statistics,
        "codon_genome_counts": codon_native.parse_codon_genome_counts,
        "codon_analysis_statistics": codon_native.parse_codon_analysis_statistics,
    }
    return readers[spec["reader"]](data, artifact=artifact, **{k: v for k, v in spec.items() if k != "reader"})


def _empty_scientific(analysis_id, provider):
    return {"version": c.SUPPLIED_VERSION,
        "assembly": {"version": "bvbrc_phylogeny_assembly_v1", "analysis_id": analysis_id,
            "caller_populations": {key: [] for key in c.POPULATION_KEYS}, "locus_bindings": [],
            "genome_request_sets": [], "family_matrices": [], "historical_frequencies": [], "model_associations": []},
        "joins": {key: [] for key in (*c.JOIN_KEYS, *(("family_blocks",) if provider == "codon_tree" else ()))},
        "observed_run": {"original_task_id": None, "source_revision": None, "settings": [], "commands": [],
            "engines": [], "conflicts": [], "completeness": "unknown"}, "source_records": [], "supplemental_documents": []}


def _supplied(bundle, supplied_values, parameters, provider):
    _finite_json(supplied_values); c.require(type(supplied_values) is list, "phylogeny_supplied_values_invalid")
    seen = []
    for row in supplied_values:
        c.shape(row, ("evidence", "value"), "phylogeny_supplied_values_invalid")
        validate_contract("SourceEvidence", row["evidence"])
        c.require(any(_same(row["evidence"], e) for e in bundle["supplied_scientific_metadata"]), "phylogeny_supplied_evidence_not_selected")
        c.require(not any(_same(row["evidence"], e) for e in seen), "phylogeny_supplied_evidence_ambiguous")
        seen.append(row["evidence"])
    result, invalid = {}, set()
    for plan in parameters["analyses"]:
        aid = plan["analysis"]["analysis_id"]
        if plan["scientific_inputs"] is None:
            result[aid] = _empty_scientific(aid, provider)
            continue
        try:
            rows = [r for r in supplied_values if _same(r["evidence"], plan["scientific_inputs"])]
            c.require(len(rows) == 1, "phylogeny_scientific_inputs_required")
            value = deepcopy(rows[0]["value"])
            c.shape(value, ("version", "assembly", "joins", "observed_run", "source_records", "supplemental_documents"), "phylogeny_supplied_inputs_invalid")
            c.require(value["version"] == c.SUPPLIED_VERSION, "phylogeny_supplied_inputs_invalid")
            c.shape(value["assembly"], ("version", "analysis_id", "caller_populations", "locus_bindings", "genome_request_sets", "family_matrices", "historical_frequencies", "model_associations"))
            c.require(value["assembly"]["analysis_id"] == aid, "phylogeny_cross_analysis_reference")
            c.shape(value["assembly"]["caller_populations"], c.POPULATION_KEYS)
            c.shape(value["joins"], (*c.JOIN_KEYS, *(("family_blocks",) if provider == "codon_tree" else ())))
            c.require(all(type(v) is list for v in value["joins"].values()))
            c.require(type(value["source_records"]) is list and type(value["supplemental_documents"]) is list)
            result[aid] = value
        except (ContractValidationError, TypeError, KeyError, IndexError, AttributeError):
            # Retain the malformed selected source at the host, but never feed
            # an invented replacement into a provider or lose other analyses.
            result[aid] = _empty_scientific(aid, provider)
            invalid.add(aid)
    return result, invalid


def _artifact_ref(artifact):
    return {key: artifact[key] for key in ("raw_artifact_ref", "source_ref", "sha256")}


def _representation(artifact):
    return {"role": artifact["role"], "task_id": artifact["task_association"]["task_id"],
        "object": {k: artifact["workspace_object"][k] for k in ("path", "uuid", "type")},
        "sha256": artifact["sha256"], "byte_count": artifact["byte_count"],
        "transfer": {k: v for k, v in artifact["transfer"].items() if k != "receipt_ref"},
        "declared_format": artifact["declared_format"]}


def _trees(read):
    value = read["result"]["value"]
    if value is None or read["reader"]["reader"] not in ("newick", "phyloxml"):
        return []
    return value["trees"] if read["reader"]["reader"] == "newick" else [r["tree"] for r in value["trees"]]


def _document_id(read):
    value = read["result"]["value"]
    if value is None:
        return None
    return value.get("alignment_id", value.get("document_id", value.get("table", {}).get("table_id")))


class _Unavailable(Exception):
    pass


class Resolution:
    """One publication's finite operand table, never a service or callback."""
    def __init__(self, bundle, content, parameters, provider, scientific, invalid_scientific):
        self.bundle, self.content, self.parameters, self.provider = bundle, content, parameters, provider
        self.scientific = scientific
        self.invalid_scientific = invalid_scientific
        self.selections, self.reads, self.requirements, self.diagnostics = {}, {}, {}, {}
        self.mandatory = []
        self.cache = {}
        self.raw_specs = {}
        self.content_specs = {}
        self.conflicted_contents = set()
        self.plans = {(r["analysis_id"], r["slot_id"]): r for r in parameters["artifact_selection"]}
        self.modes = {r["analysis"]["analysis_id"]: r["analysis"]["mode"] for r in parameters["analyses"]}
        for aid in self.modes:
            self.requirements[aid], self.diagnostics[aid] = [], []
        for aid in sorted(invalid_scientific):
            self.issue(aid, "phylogeny_supplied_inputs_invalid", identity=aid)

    def issue(self, aid, reason, *, role=None, slot=None, kind="scientific_metadata", identity="", severity="error", refs=(), mandatory=False):
        req = requirement(reason, analysis_id=aid, role=role, kind=kind, identity=identity, refs=refs)
        self.requirements[aid] = merge_requirements(self.requirements[aid], [req])
        self.diagnostics[aid].append(diagnostic(reason, severity=severity, refs=refs))
        if slot is not None:
            row = self.selections[(aid, slot)]
            if req["requirement_id"] not in row["requirement_ids"]:
                row["requirement_ids"].append(req["requirement_id"])
        if mandatory:
            self.mandatory = merge_requirements(self.mandatory, [req])
        return req

    def _selection(self, aid, sid, role, artifacts=(), receipts=()):
        row = {"analysis_id": aid, "slot_id": sid, "role": role, "state": "missing",
               "artifact_refs": unique(list(artifacts)), "acquisition_receipt_refs": sorted(set(receipts)),
               "read_id": None, "document_id": None, "tree_ids": [], "requirement_ids": []}
        c.require((aid, sid) not in self.selections, "phylogeny_slot_identity_conflict")
        self.selections[(aid, sid)] = row
        return row

    def _accept_read(self, key, read):
        selection = self.selections[key]
        selection.update(state="resolved" if read["result"]["value"] is not None else "invalid",
            read_id=read["read_id"], document_id=_document_id(read), tree_ids=[t["tree_id"] for t in _trees(read)])
        self.reads[key] = read
        if read["result"]["value"] is None:
            self.issue(key[0], "phylogeny_selected_document_unavailable", role=selection["role"], slot=key[1],
                       kind="output_bytes", identity=key[1], refs=[read["artifact"]["source_ref"]])

    def _read(self, raw, artifact, spec):
        identity = artifact["raw_artifact_ref"]
        previous = self.raw_specs.get(identity)
        prior_spec = self.content_specs.get(raw)
        if (previous is not None and not _same(previous, (artifact, spec))) or (prior_spec is not None and not _same(prior_spec, spec)):
            self.conflicted_contents.add(raw)
            # A conflict applies to every declaration of those exact bytes.
            # Keeping the first accepted parse would make order select policy.
            for key, read in list(self.reads.items()):
                if self.content.get(read["artifact"]["raw_artifact_ref"]) == raw:
                    selected = self.selections[key]
                    selected.update(state="invalid", read_id=None, document_id=None, tree_ids=[])
                    self.issue(key[0], "phylogeny_parser_declaration_conflict", role=selected["role"],
                        slot=key[1], kind="parser_binding", identity=key[1], refs=[read["artifact"]["source_ref"]])
                    del self.reads[key]
        c.require(raw not in self.conflicted_contents, "phylogeny_parser_declaration_conflict")
        self.content_specs[raw] = deepcopy(spec)
        self.raw_specs[identity] = (deepcopy(artifact), deepcopy(spec))
        key = json.dumps([artifact, spec], sort_keys=True)
        if key not in self.cache:
            self.cache[key] = parse_reader(raw, artifact=artifact, spec=spec)
        return deepcopy(self.cache[key])

    def acquired(self, *, partitions=False):
        # Resolve independent native documents before partition readers which
        # explicitly require their selected alignment's column count.
        slots = [row for row in self.parameters["artifact_selection"]
                 if (row["reader"]["reader"] == "raxml_partitions") == partitions]
        for plan in slots:
            aid, sid = plan["analysis_id"], plan["slot_id"]
            candidates = [a for a in self.bundle["artifacts"] if a["role"] == plan["role"]]
            row = self._selection(aid, sid, plan["role"], [_artifact_ref(a) for a in candidates], [a["transfer"]["receipt_ref"] for a in candidates])
            if not candidates:
                self.issue(aid, "phylogeny_artifact_missing", role=plan["role"], slot=sid, kind="output_bytes", identity=sid)
                continue
            if len(unique([_representation(a) for a in candidates])) != 1:
                row["state"] = "ambiguous"
                self.issue(aid, "phylogeny_artifact_ambiguous", role=plan["role"], slot=sid, kind="parser_binding", identity=sid, refs=[a["source_ref"] for a in candidates])
                continue
            artifact = min(candidates, key=lambda a: a["transfer"]["receipt_ref"])
            ref = _artifact_ref(artifact); raw = self.content.get(ref["raw_artifact_ref"])
            reason, kind = None, "output_bytes"
            for candidate in candidates:
                candidate_raw = self.content.get(candidate["raw_artifact_ref"])
                if candidate_raw is None:
                    reason = "phylogeny_artifact_bytes_missing"
                    break
                if hashlib.sha256(candidate_raw).hexdigest() != candidate["sha256"] or len(candidate_raw) != candidate["byte_count"]:
                    reason = "phylogeny_artifact_bytes_conflict"
                    break
                if not candidate["transfer"]["body_complete"] or candidate["transfer"]["object_complete"] != "yes":
                    reason = "phylogeny_complete_object_required"
                    break
            declared, spec = artifact["declared_format"], deepcopy(plan["reader"])
            if declared["format"] != spec["reader"] or declared["mode"] not in (None, self.modes[aid]) or declared["version"] not in (None, spec.get("dialect")):
                reason, kind = "phylogeny_declared_format_conflict", "parser_binding"
            if reason:
                row["state"] = "invalid"
                self.issue(aid, reason, role=plan["role"], slot=sid, kind=kind, identity=sid, refs=[a["source_ref"] for a in candidates])
                continue
            if len(candidates) > 1:
                self.diagnostics[aid].append(diagnostic("duplicate_artifact_representation", severity="qualification", refs=[a["source_ref"] for a in candidates]))
            for candidate in candidates:
                association = candidate["task_association"]
                if association["kind"] in ("unverified_original_path", "task_info_folder_member"):
                    self.diagnostics[aid].append(diagnostic("output_association_unproven", severity="qualification", refs=[candidate["source_ref"]]))
                if association["byte_version_status"] != "producer_bytes_bound":
                    self.diagnostics[aid].append(diagnostic("output_version_unproven", severity="qualification", refs=[candidate["source_ref"]]))
            try:
                if spec["reader"] == "raxml_partitions":
                    document = self.value(spec.pop("alignment"), expected="alignment")
                    count = document["observed_column_count"]
                    if count is None:
                        raise _Unavailable()
                    spec["alignment_column_count"] = count
                result = self._read(raw, ref, spec)
                self._accept_read((aid, sid), {"read_id": ref["raw_artifact_ref"] + "#read", "artifact": ref, "reader": spec, "result": result})
            except _Unavailable:
                self.issue(aid, "phylogeny_partition_alignment_required", role=plan["role"], slot=sid, kind="output_bytes", identity=sid, refs=[ref["source_ref"]])
            except ContractValidationError as error:
                row["state"] = "invalid"
                self.issue(aid, "phylogeny_parser_declaration_conflict", role=plan["role"], slot=sid, kind="parser_binding", identity=sid, refs=[ref["source_ref"]])

    def supplemental(self):
        for aid, scientific in self.scientific.items():
            for supplied in scientific["supplemental_documents"]:
                try:
                    self._supplemental_document(aid, supplied)
                except (ContractValidationError, TypeError, KeyError, IndexError, AttributeError):
                    sid = supplied.get("slot_id") if type(supplied) is dict else None
                    role = supplied.get("role") if type(supplied) is dict else None
                    if type(sid) is str and sid and type(role) is str and role and (aid, sid) not in self.selections:
                        self._selection(aid, sid, role)["state"] = "invalid"
                        self.issue(aid, "phylogeny_supplied_document_invalid", role=role, slot=sid, kind="input_bytes", identity=sid)
                    else:
                        self.invalid_scientific.add(aid)
                        self.issue(aid, "phylogeny_supplied_document_invalid", identity=aid)

    def _supplemental_document(self, aid, supplied):
        c.shape(supplied, ("slot_id", "role", "read", "evidence"), "phylogeny_supplied_document_invalid")
        c.string(supplied["slot_id"]); c.string(supplied["role"]); c.evidences(supplied["evidence"])
        read = supplied["read"]; c.shape(read, ("read_id", "artifact", "reader", "result"), "phylogeny_supplied_document_invalid")
        c.string(read["read_id"]); c.validate_reader_spec(read["reader"], planned=False)
        c.require(self.provider == "codon_tree" or not read["reader"]["reader"].startswith("codon_"), "phylogeny_reader_provider_conflict")
        artifact = read["artifact"]; c.shape(artifact, ("raw_artifact_ref", "source_ref", "sha256"))
        sid = supplied["slot_id"]; row = self._selection(aid, sid, supplied["role"], [artifact])
        matches = [b for b in self.bundle.get("supplied_contents", []) if all(_same(b[k], artifact[a]) for k, a in (("artifact_ref", "raw_artifact_ref"), ("source_ref", "source_ref"), ("sha256", "sha256")))]
        raw = self.content.get(artifact["raw_artifact_ref"])
        reason = None
        if not matches or raw is None:
            reason = "supplemental_native_content_required"
        elif any(b["byte_count"] != len(raw) for b in matches) or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            reason = "supplemental_native_content_conflict"
        else:
            try:
                actual = self._read(raw, artifact, read["reader"])
                if not _same(actual, read["result"]):
                    reason = "supplemental_parsed_claim_conflict"
            except ContractValidationError:
                reason = "phylogeny_parser_declaration_conflict"
        if reason:
            row["state"] = "missing" if reason == "supplemental_native_content_required" else "invalid"
            self.issue(aid, reason, role=supplied["role"], slot=sid, kind="input_bytes", identity=sid, refs=[artifact["source_ref"]])
            return
        self._accept_read((aid, sid), deepcopy(read))

    def value(self, ref, *, expected=None, tree=False):
        c.slot_ref(ref, tree=tree)
        key = ref["analysis_id"], ref["slot_id"]
        c.require(key in self.selections, "phylogeny_slot_not_declared")
        read = self.reads.get(key)
        if read is None or read["result"]["value"] is None:
            raise _Unavailable()
        if tree:
            matches = [t for t in _trees(read) if t["tree_index"] == ref["tree_index"]]
            if len(matches) != 1:
                row = self.selections[key]
                self.issue(key[0], "phylogeny_selected_tree_unavailable", role=row["role"], slot=key[1], kind="output_bytes", identity=str(ref["tree_index"]))
                raise _Unavailable()
            return matches[0]
        value = read["result"]["value"]
        if expected == "alignment":
            c.require(read["reader"]["reader"] in ("aligned_fasta", "relaxed_phylip"), "phylogeny_selected_format_conflict")
        return value

    def identifier(self, ref, *, tree=False, read=False, nullable=False, expected=None):
        if nullable and ref is None:
            return None
        value = self.value(ref, expected=expected, tree=tree)
        if tree:
            return value["tree_id"]
        r = self.reads[(ref["analysis_id"], ref["slot_id"])]
        return r["read_id"] if read else _document_id(r)

    def compile_row(self, aid, row, fields, *, kind="join"):
        result = deepcopy(row)
        try:
            for field, target in fields.items():
                ref = result[field]
                c.slot_ref(ref, tree=target == "tree", nullable=True, analysis_id=aid)
                result[field] = self.identifier(ref, tree=target == "tree", read=target == "read", nullable=True, expected="alignment" if target == "alignment" else None)
            return result
        except _Unavailable:
            self.issue(aid, "phylogeny_" + kind + "_dependency_unavailable", identity=json.dumps(row, sort_keys=True))
            return None

    def _analysis(self, plan):
        row = deepcopy(plan["analysis"]); aid = row["analysis_id"]
        for name in c.CODON_DOCUMENT_FIELDS if self.provider == "codon_tree" else c.GENE_DOCUMENT_FIELDS:
            try:
                row[name] = self.identifier(row[name], nullable=True)
            except _Unavailable:
                row[name] = None
        for name in c.CODON_TREE_FIELDS if self.provider == "codon_tree" else c.GENE_TREE_FIELDS:
            try:
                row[name] = self.identifier(row[name], tree=True, nullable=True)
            except _Unavailable:
                row[name] = None
        if self.provider == "codon_tree":
            resolved = []
            for ref in row["per_family_final_alignment_ids"]:
                try:
                    resolved.append(self.identifier(ref, expected="alignment"))
                except _Unavailable:
                    pass
            row["per_family_final_alignment_ids"] = list(dict.fromkeys(resolved))
        observations = []
        for ref in row.pop("native_engine_slots"):
            try:
                value = self.value(ref)
                c.require(self.reads[(ref["analysis_id"], ref["slot_id"])]["reader"]["reader"] == "raxml_run_log", "phylogeny_engine_slot_wrong_format")
                observations += [o["observation_id"] for o in value["observations"]]
            except _Unavailable:
                pass
        row["native_engine_observation_ids"] = list(dict.fromkeys(observations))
        if not row["output_role_evidence"]:
            # Qualified current-byte dimensions/topology remain usable. The
            # requirement is used only by joint original-analysis claims.
            self.issue(aid, "phylogeny_analysis_output_association_required", identity=aid, severity="qualification")
        return row

    def _populations(self, aid, scientific, plans):
        result = {key: [] for key in c.POPULATION_KEYS}
        original = scientific["assembly"]["caller_populations"]
        for kind, rows in original.items():
            c.require(type(rows) is list)
            for row in rows:
                if kind == "alignments":
                    value = self.compile_row(aid, row, {"alignment_id": "alignment"}, kind="population")
                elif kind == "leaves":
                    value = self.compile_row(aid, row, {"tree_id": "tree"}, kind="population")
                elif kind == "bootstraps":
                    value = deepcopy(row); kept = []
                    for ref in row["tree_ids"]:
                        c.slot_ref(ref, tree=True, analysis_id=aid)
                        try:
                            kept.append(self.identifier(ref, tree=True))
                        except _Unavailable:
                            value["completeness"] = "partial"
                    value["tree_ids"] = kept
                else:
                    value = deepcopy(row)
                if value is not None:
                    result[kind].append(value)
        for plan in plans:
            kind = plan["kind"]
            try:
                if kind == "explicit":
                    collection, value = plan["population_type"], deepcopy(plan["population"])
                elif kind in ("whole_alignment", "alignment_subset"):
                    alignment = self.value(plan["alignment"], expected="alignment")
                    columns = alignment["observed_column_count"]
                    if columns is None:
                        columns = alignment["declared_column_count"]
                    if columns is None:
                        columns = max((len(r["sequence"]) for r in alignment["rows"]), default=0)
                    collection = "alignments"
                    value = {"population_id": plan["population_id"], "alignment_id": alignment["alignment_id"],
                        "row_indices": [r["row_index"] for r in alignment["rows"]], "columns_0based": list(range(columns)),
                        "completeness": alignment["completeness"], "evidence": []}
                    if kind == "alignment_subset":
                        value.update({k: deepcopy(plan[k]) for k in ("row_indices", "columns_0based", "completeness", "evidence")})
                        c.require(value["completeness"] != "complete" or alignment["completeness"] == "complete", "phylogeny_population_completeness_conflict")
                elif kind == "whole_tree":
                    tree = self.value(plan["tree"], tree=True); collection = "leaves"
                    value = {"population_id": plan["population_id"], "tree_id": tree["tree_id"],
                        "node_indices": [n["node_index"] for n in tree["nodes"] if not n["child_indices"]],
                        "completeness": "complete", "evidence": []}
                else:
                    document = self.value(plan["forest"])
                    read = self.reads[(aid, plan["forest"]["slot_id"])]; c.require(read["reader"]["reader"] == "newick", "phylogeny_bootstrap_format_conflict")
                    collection = "bootstraps"; value = {"population_id": plan["population_id"], "tree_ids": [t["tree_id"] for t in document["trees"]],
                        "completeness": document["completeness"], "expected_replicates": plan["expected_replicates"],
                        "expected_count_evidence": deepcopy(plan["expected_count_evidence"])}
                prior = [p for p in result[collection] if p["population_id"] == value["population_id"]]
                c.require(not prior or len(prior) == 1 and _same(prior[0], value), "phylogeny_population_definition_conflict")
                if not prior:
                    result[collection].append(value)
            except _Unavailable:
                self.issue(aid, "phylogeny_population_unavailable", identity=plan["population_id"])
        return result

    def _joins(self, aid, original):
        result = deepcopy(original)
        maps = {"input_rows": {"alignment_id": "alignment"}, "tip_rows": {"tree_id": "tree", "alignment_id": "alignment"},
            "display_tips": {"raw_tree_id": "tree", "display_tree_id": "tree"}, "residues": {"alignment_id": "alignment"},
            "organismal_tips": {"gene_tree_id": "tree", "organismal_tree_id": "tree"}, "family_blocks": {"alignment_id": "alignment"}}
        for field, fields in maps.items():
            if field in result:
                result[field] = [compiled for row in original[field] if (compiled := self.compile_row(aid, row, fields)) is not None]
        result["transformations"] = []
        for row in original["transformations"]:
            copied = deepcopy(row)
            outputs = [self.compile_row(aid, r, {"alignment_id": "alignment"}) for r in row["output_rows"]]
            if any(r is None for r in outputs):
                continue
            copied["output_rows"] = outputs; result["transformations"].append(copied)
        return result

    def _calculations(self, aid, original, populations, assembly):
        result = deepcopy(original); known = {key: {p["population_id"] for p in rows} for key, rows in populations.items()}
        requests = (("alignment_requests", "alignments"), ("tree_requests", "leaves"), ("taxon_requests", "taxonomy"))
        for key, kind in requests:
            result[key] = []
            for row in original[key]:
                if row["population_id"] in known[kind]:
                    copied = deepcopy(row)
                    if key == "alignment_requests":
                        population = next(p for p in populations[kind] if p["population_id"] == row["population_id"])
                        if population["completeness"] != "complete":
                            copied["pairs"] = [pair for pair in row["pairs"] if set(pair) <= set(population["row_indices"])]
                            if copied["pairs"] != row["pairs"]:
                                self.issue(aid, "phylogeny_calculation_dependency_unavailable", identity=json.dumps(row, sort_keys=True))
                    result[key].append(copied)
                else:
                    self.issue(aid, "phylogeny_calculation_dependency_unavailable", identity=row["population_id"])
        for key, kind in (("original_coverage_population_ids", "alignments"), ("composition_population_ids", "composition"), ("literal_statistic_population_ids", "alignments")):
            if key in result:
                result[key] = [pid for pid in original[key] if pid in known[kind]]
                for pid in set(original[key]) - known[kind]:
                    self.issue(aid, "phylogeny_calculation_dependency_unavailable", identity=pid)
        result["comparisons"] = []
        for row in original["comparisons"]:
            copied = self.compile_row(aid, row, {"gene_tree_id": "tree", "organismal_tree_id": "tree"}, kind="calculation")
            if copied is not None:
                pairs = [self.compile_row(aid, r, {"gene_tree_id": "tree", "organismal_tree_id": "tree"}, kind="calculation") for r in row["tip_pairs"]]
                if all(p is not None for p in pairs):
                    copied["tip_pairs"] = pairs; result["comparisons"].append(copied)
        result["bootstrap_requests"] = []
        for row in original["bootstrap_requests"]:
            if row["replicate_population_id"] not in known["bootstraps"]:
                self.issue(aid, "phylogeny_calculation_dependency_unavailable", identity=row["replicate_population_id"]); continue
            copied = self.compile_row(aid, row, {"reference_tree_id": "tree"}, kind="calculation")
            if copied is None:
                continue
            joined = self.compile_row(aid, row["tip_join"], {"reference_tree_id": "tree"}, kind="calculation")
            if joined is None:
                continue
            joined["mappings"] = [m for r in row["tip_join"]["mappings"] if (m := self.compile_row(aid, r, {"replicate_tree_id": "tree"}, kind="calculation")) is not None]
            copied["tip_join"] = joined; result["bootstrap_requests"].append(copied)
        if self.provider == "codon_tree":
            result["family_population_requests"] = []
            for row in original["family_population_requests"]:
                if row["family_population_id"] in known["families"] and row["genome_population_id"] in known["genomes"]:
                    result["family_population_requests"].append(deepcopy(row))
                else:
                    self.issue(aid, "phylogeny_calculation_dependency_unavailable", identity=json.dumps(row, sort_keys=True))
            pid = original["worst_sequence_population_id"]
            if pid is not None and not any(h["evaluated_family_population"]["population"]["population_id"] == pid for h in assembly["historical_frequencies"]):
                result["worst_sequence_population_id"] = None
                self.issue(aid, "phylogeny_calculation_dependency_unavailable", identity=pid)
        return result

    def analysis_operands(self, plan):
        aid = plan["analysis"]["analysis_id"]; scientific = self.scientific[aid]
        c.require(aid not in self.invalid_scientific, "phylogeny_supplied_inputs_invalid")
        parsed = {"store": {key: [] for key in ("alignments", "tree_documents", "partitions", "phyloxml", "source_records", "native_tables")}, "analyses": [self._analysis(plan)]}
        parsed["store"]["source_records"] = deepcopy(scientific["source_records"])
        envelope = {"parsed": parsed, "reads": [], "raxml_runs": []}
        if self.provider == "codon_tree":
            envelope.update(membership=[], family_statistics=[], genome_counts=[], analysis_statistics=[])
        fields = {"aligned_fasta": "alignments", "relaxed_phylip": "alignments", "newick": "tree_documents", "phyloxml": "phyloxml", "raxml_partitions": "partitions"}
        native = {"raxml_run_log": "raxml_runs", "codon_membership": "membership", "codon_family_statistics": "family_statistics", "codon_genome_counts": "genome_counts", "codon_analysis_statistics": "analysis_statistics"}
        for key, read in self.reads.items():
            if key[0] != aid:
                continue
            envelope["reads"].append(deepcopy(read)); value = read["result"]["value"]
            if value is None:
                continue
            reader = read["reader"]["reader"]
            if reader in fields:
                parsed["store"][fields[reader]].append(deepcopy(value))
            else:
                envelope[native[reader]].append(deepcopy(value))
                if "table" in value:
                    parsed["store"]["native_tables"].append(deepcopy(value["table"]))
        assembly = deepcopy(scientific["assembly"])
        assembly["caller_populations"] = self._populations(aid, scientific, plan["population_plans"])
        assembly["model_associations"] = [r for row in scientific["assembly"]["model_associations"] if (r := self.compile_row(aid, row, {"read_id": "read", "partition_document_id": "document", "sample_alignment_id": "alignment"})) is not None]
        joins = self._joins(aid, scientific["joins"])
        run = deepcopy(scientific["observed_run"])
        c.require(run.get("original_task_id") in (None, self.bundle["original_task"]["task_id"]), "phylogeny_original_task_conflict")
        calculation = self._calculations(aid, plan["calculation_parameters"], assembly["caller_populations"], assembly)
        return {"documents": envelope, "inputs": tuple(deepcopy(self.bundle["input_bindings"])), "observed_run": run,
                "joins": joins, "assembly": assembly, "parameters": deepcopy(plan["read_parameters"]),
                "calculation_parameters": calculation}


def resolve_bundle(bundle, *, artifact_bytes, supplied_values, parameters, provider):
    """Validate original selection and materialize every originally selected slot."""
    bundle = validate_contract("ArtifactBundle", bundle)
    parameters = c.validate_parameters(parameters, provider=provider)
    expected = "GeneTree" if provider == "gene_tree" else "CodonTree"
    c.require(bundle["original_task"]["required_application_id"] == expected and bundle["original_task"]["native_application_id"] == expected, "phylogeny_original_task_conflict")
    allowed = {a["raw_artifact_ref"] for a in bundle["artifacts"]} | {b["artifact_ref"] for b in bundle.get("supplied_contents", [])}
    c.require(type(artifact_bytes) is dict and all(type(k) is str and type(v) is bytes for k, v in artifact_bytes.items()) and set(artifact_bytes) <= allowed, "phylogeny_artifact_bytes_map_invalid")
    for binding in bundle["input_bindings"]:
        value = _at(bundle["original_task"]["submitted_parameters"], binding["parameter_pointer"])
        original = binding["workspace_path"] if binding["kind"] in ("retained_bytes", "workspace_object") else binding["inline_value"]
        c.require(_same(value, original), "phylogeny_original_input_conflict")
    scientific, invalid = _supplied(bundle, supplied_values, parameters, provider)
    result = Resolution(bundle, artifact_bytes, parameters, provider, scientific, invalid)
    result.acquired(); result.supplemental(); result.acquired(partitions=True)
    return result


__all__ = ["resolve_bundle", "parse_reader", "diagnostic", "requirement", "merge_requirements", "DIAGNOSTIC_CODES"]
