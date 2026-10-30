"""Requested phylogeny facts from original saved publications and child forms.

The host authenticates the saved sheet as identity proof. Only original saved
AdapterResult.facts cross this boundary; no parser, calculator, acquisition,
model call, new action, observation or credit is produced by these reads.
"""
from __future__ import annotations

from copy import deepcopy
import json
import re

from .bvbrc_appservice_contracts import _finite_json, _Validator, validate_contract
from .bvbrc_appservice_custody import _references
from .bvbrc_appservice_publication import DATA_PROVIDER, RESULT_VERSION
from .bvbrc_phylogeny_bundle_contracts import (
    REFERENCE_KINDS, SCALAR_CATALOG, decode_reference,
    requested_form_schema, selector_kind, validate_parameters, validate_requested_form,
)
from .communication import plain, validate_form
from .episode_return_records import EpisodeReturnRecords, _same
from .execution_contracts import canonical, digest


_KINDS = ("measurements", "branches", "sites", "family_membership",
          "function_composition", "relationship_comparisons", "requirements", "qualifications")
FACT_SOURCES = tuple("bvbrc_phylogeny_" + kind for kind in _KINDS)
IDENTIFIER_NAMESPACES = ("bvbrc_phylogeny_field", *("bvbrc_phylogeny_" + kind for kind in REFERENCE_KINDS))
_VALUE_KEYS = dict(zip(_KINDS, ("value", "branches", "sites", "members", "functions",
                               "comparisons", "requirements", "qualifications")))
_PREFIX = "bvbrc_phylogeny_return_"
_SOURCE_ID = re.compile(r"source_[a-f0-9]{24,64}\Z")
_ADAPTERS = {"bvbrc_gene_tree": "C-L194-GeneTree", "bvbrc_codon_tree": "C-L193-CodonTree"}
_EXAMPLES = {
    "branches": {"metric": "branch_rows", "analysis_id": "a", "population_id": "p",
                 "tree": {"analysis_id": "a", "slot_id": "t", "tree_index": 0}, "node_indices": []},
    "sites": {"metric": "site_rows", "analysis_id": "a", "population_id": "p", "columns_0based": []},
    "family_membership": {"metric": "family_membership_rows", "analysis_id": "a", "family_ids": []},
    "function_composition": {"metric": "function_composition_rows", "analysis_id": "a", "population_id": "p"},
    "relationship_comparisons": {"metric": "relationship_comparison", "analysis_id": "a", "comparison_id": "c"},
    "requirements": {"metric": "missing_requirements"},
    "qualifications": {"metric": "qualifications", "analysis_id": "a", "slot_id": None},
}
_REFERENCE_FIELDS = {
    "tree_ref": "tree", "split_ref": "split", "alignment_ref": "alignment",
    "family_ref": "family", "feature_ref": "feature", "genome_ref": "genome",
    "population_ref": "population", "function_ref": "function",
    "comparison_ref": "comparison", "role_ref": "role",
}


def _object(properties):
    return {"type": "object", "properties": properties, "required": list(properties),
            "additionalProperties": False}


def _identifier(kind, *, nullable=False):
    return {"type": ["string", "null"] if nullable else "string", "format": "identifier",
            "x-reference-namespace": "bvbrc_phylogeny_" + kind}


def _require(condition, code):
    if not condition:
        raise ValueError(_PREFIX + code)


def _report_node(node):
    """Convert the static adapter schema to the existing closed report grammar."""
    node = deepcopy(node)
    node.pop("minLength", None)
    node.pop("x-phylogeny-fact", None)
    if "enum" in node and "type" not in node:
        node["type"] = "string"
    if "properties" in node:
        node["properties"] = {key: _report_node(value) for key, value in node["properties"].items()}
    if "items" in node:
        node["items"] = _report_node(node["items"])
    return node


def phylogeny_fact_sources():
    """Eight closed families, with original source/field and scoped identifiers."""
    source = {"type": "string", "format": "reference", "x-reference-namespace": "execution_result"}
    nodes = requested_form_schema(_EXAMPLES)["properties"]
    values = {"measurements": {"type": ["number", "null"]}}
    for kind, node in nodes.items():
        node = _report_node(node)
        properties = node["items"]["properties"]
        for field, namespace in _REFERENCE_FIELDS.items():
            if field in properties:
                properties[field] = _identifier(namespace, nullable="null" in properties[field].get("type", []))
        if kind == "requirements":
            properties["requirement_id"] = _identifier("requirement")
            properties["role"] = _identifier("role", nullable=True)
            properties["reason_code"] = _identifier("reason")
            properties["source_refs"] = {"type": "array", "uniqueItems": True, "items": {
                "type": "string", "format": "reference", "x-reference-namespace": "source"}}
        elif kind == "qualifications":
            properties["requirement_refs"] = {"type": "array", "items": _identifier("requirement")}
        values[kind] = node
    meanings = (
        "Original requested numerical cells; each field retains its selected quantity, units, population and missing meaning.",
        "Original selected tree edges, native signed lengths, support methods/scales and measured bootstrap counts.",
        "Original selected alignment columns and population counts; unknown canonical measurements remain null.",
        "Original selected family, feature, genome and representation memberships with their recorded inclusion stages.",
        "Original requested function composition of the declared member population; these fractions are not annotation probabilities.",
        "Original requested comparison with supplied organismal relationships, with exact comparison identity and split counts.",
        "Only original explicitly requested unresolved acquisition requirements, with their actual source relationships.",
        "Only original requested finite qualifications and their scoped roles/dependencies; no raw diagnostic text or sheet.",
    )
    return {source_name: {"type": "array", "meaning": meaning, "report_schema": {
        "type": "array", "items": _object({"source_ref": deepcopy(source), "field": _identifier("field"),
            _VALUE_KEYS[kind]: values[kind]}), "x-source": source_name}}
        for source_name, kind, meaning in zip(FACT_SOURCES, _KINDS, meanings)}


def requested_sources(schema):
    return tuple(dict.fromkeys(node["x-source"] for node in plain(schema).get("properties", {}).values()
        if node.get("x-source") in FACT_SOURCES))


def _one(rows, **keys):
    _require(type(rows) is list and all(type(row) is dict for row in rows), "saved_identity_table_invalid")
    matches = [row for row in rows if all(_same(row.get(key), value) for key, value in keys.items())]
    _require(len(matches) == 1, "saved_identity_required")
    return matches[0]


class _SavedIdentities:
    """Read only supplied identity tables; never construct new scientific values."""
    def __init__(self, parameters, sheet_set, adapter_id):
        self.parameters, self.sheet_set = parameters, sheet_set
        self.plans = {row["analysis"]["analysis_id"]: row for row in parameters["analyses"]}
        if sheet_set is not None:
            _require(type(sheet_set) is dict and set(sheet_set) == {"schema_version", "tool", "selections", "analyses"}
                and sheet_set["schema_version"] == "bvbrc_phylogeny_sheet_set_v1"
                and sheet_set["tool"] == _ADAPTERS[adapter_id], "saved_sheet_identity_conflict")
            _require(type(sheet_set["analyses"]) is list and type(sheet_set["selections"]) is list,
                "saved_sheet_identity_conflict")
            ids = [row.get("analysis_id") for row in sheet_set["analyses"] if type(row) is dict]
            _require(len(ids) == len(sheet_set["analyses"]) and len(ids) == len(set(ids))
                and set(ids) == set(self.plans), "saved_analysis_conflict")
            slots = [(row.get("analysis_id"), row.get("slot_id")) for row in sheet_set["selections"]]
            _require(len(slots) == len(set(slots)) and all(aid in self.plans for aid, _ in slots),
                "saved_slot_conflict")
            for aid, sid in slots:
                self.slot(aid, sid)

    def plan(self, aid):
        _require(aid in self.plans, "original_analysis_required")
        return self.plans[aid]

    def sheet(self, aid):
        _require(self.sheet_set is not None, "saved_sheet_required")
        row = _one(self.sheet_set["analyses"], analysis_id=aid)
        sheet = row["sheet"]
        provider = "gene_tree" if self.sheet_set["tool"] == "C-L194-GeneTree" else "codon_tree"
        _require(type(sheet) is dict and sheet.get("tool") == self.sheet_set["tool"],
            "saved_analysis_sheet_required")
        _require(sheet.get("schema_version") == "bvbrc_" + provider + "_sheet_v1"
            and sheet.get("mode") == self.plan(aid)["analysis"]["mode"]
            and len(sheet["documents"]["analyses"]) == 1, "saved_analysis_sheet_identity_conflict")
        _one(sheet["documents"]["analyses"], analysis_id=aid)
        return sheet

    def slot(self, aid, sid):
        _require(self.sheet_set is not None, "saved_sheet_required")
        row = _one(self.sheet_set["selections"], analysis_id=aid, slot_id=sid)
        planned = [item for item in self.parameters["artifact_selection"]
            if item["analysis_id"] == aid and item["slot_id"] == sid]
        if planned:
            _require(len(planned) == 1 and planned[0]["role"] == row["role"], "saved_original_slot_conflict")
        else:
            # Supplemental documents are originally supplied through the one
            # selected scientific-input binding, never a new task acquisition.
            _require(self.plan(aid)["scientific_inputs"] is not None
                and row["acquisition_receipt_refs"] == [], "saved_original_slot_conflict")
        return row

    def tree(self, aid, ref):
        slot = self.slot(aid, ref["slot_id"])
        _require(slot["state"] == "resolved", "saved_tree_unresolved")
        store = self.sheet(aid)["documents"]["store"]
        document = _one([*store["tree_documents"], *store["phyloxml"]], document_id=slot["document_id"])
        _require(any(_same(document["artifact"], artifact) for artifact in slot["artifact_refs"]),
            "saved_tree_artifact_conflict")
        trees = [row.get("tree", row) for row in document["trees"]]
        tree = _one([tree for tree in trees if tree["tree_id"] in slot["tree_ids"]],
                    tree_index=ref["tree_index"])
        _require(tree["document_id"] == slot["document_id"], "saved_tree_slot_conflict")
        return tree

    def population(self, aid, pid, kind):
        return _one(self.sheet(aid)["populations"][kind], population_id=pid)

    def alignment(self, aid, pid):
        population = self.population(aid, pid, "alignments")
        alignment = _one(self.sheet(aid)["documents"]["store"]["alignments"],
                         alignment_id=population["alignment_id"])
        planned = [row for row in self.plan(aid)["population_plans"] if row.get("population_id") == pid
            and row["kind"] in {"whole_alignment", "alignment_subset"}]
        if planned:
            slot = self.slot(aid, planned[0]["alignment"]["slot_id"])
            _require(slot["state"] == "resolved" and slot["document_id"] == alignment["alignment_id"],
                "saved_alignment_slot_conflict")
            _require(any(_same(alignment["artifact"], artifact) for artifact in slot["artifact_refs"]),
                "saved_alignment_artifact_conflict")
        return population, alignment

    def decode(self, value, kind, aid):
        decoded = decode_reference(value, expected_kind=kind)
        _require(decoded[1] == aid, "saved_reference_analysis_conflict")
        return decoded[2]

    def selected(self, selection, *, provider):
        kind = selector_kind(selection)
        metric = selection["metric"]
        if kind == "requirements":
            return kind
        aid = selection["analysis_id"]
        plan = self.plan(aid)
        params = plan["calculation_parameters"]
        spec = SCALAR_CATALOG.get(metric)
        collection = spec["collection"] if spec else {
            "branches": "trees", "sites": "alignments", "family_membership": "families",
            "function_composition": "composition", "relationship_comparisons": "comparisons",
            "qualifications": "qualifications"}[kind]
        _require(provider != "gene_tree" or collection not in {
            "families", "literal_statistics", "family_populations", "worst_sequence_ratios"}, "original_provider_conflict")
        if "tree" in selection:
            self.slot(aid, selection["tree"]["slot_id"])
        if kind == "qualifications":
            if selection["slot_id"] is not None:
                self.slot(aid, selection["slot_id"])
        elif collection in ("alignments", "trees", "taxonomy"):
            key = {"alignments": "alignment_requests", "trees": "tree_requests", "taxonomy": "taxon_requests"}[collection]
            _require(any(row["population_id"] == selection["population_id"]
                and (collection != "taxonomy" or row["rank"] == selection["rank"])
                for row in params[key]), "original_calculation_required")
        elif collection in ("original_coverage", "composition", "literal_statistics"):
            key = {"original_coverage": "original_coverage_population_ids", "composition": "composition_population_ids",
                   "literal_statistics": "literal_statistic_population_ids"}[collection]
            _require(selection["population_id"] in params[key], "original_calculation_required")
        elif collection == "bootstrap":
            _require(any(row["replicate_population_id"] == selection["population_id"]
                and _same(row["reference_tree_id"], selection["tree"])
                for row in params["bootstrap_requests"]), "original_calculation_required")
        elif collection == "comparisons":
            _require(any(row["comparison_id"] == selection["comparison_id"] for row in params["comparisons"]),
                "original_calculation_required")
        elif collection == "family_populations":
            _require({key: selection[key] for key in ("family_population_id", "genome_population_id")}
                in params["family_population_requests"], "original_calculation_required")
        elif collection == "worst_sequence_ratios":
            _require(selection["family_population_id"] == params["worst_sequence_population_id"],
                "original_calculation_required")
        return kind

    def scalar(self, selection, value):
        if value is None:
            return
        aid, metric = selection["analysis_id"], selection["metric"]
        self.sheet(aid)
        spec = SCALAR_CATALOG[metric]
        collection = spec["collection"]
        if "tree" in selection:
            tree = self.tree(aid, selection["tree"])
            if collection == "trees":
                population = self.population(aid, selection["population_id"], "leaves")
                _require(population["tree_id"] == tree["tree_id"], "saved_tree_population_conflict")
            indices = {row["node_index"] for row in tree["nodes"]}
            for key in ("node_index", "node_a", "node_b"):
                _require(key not in selection or selection[key] in indices, "saved_node_outside_tree")
        if collection in ("alignments", "original_coverage", "literal_statistics"):
            population, _ = self.alignment(aid, selection["population_id"])
            for key in ("row_index", "row_a", "row_b"):
                _require(key not in selection or selection[key] in population["row_indices"], "saved_row_outside_population")
            _require("column_0based" not in selection or selection["column_0based"] in population["columns_0based"],
                "saved_column_outside_population")

    def array(self, kind, selection, value):
        if value is None:
            return
        aid = selection["analysis_id"]
        sheet = None if kind == "qualifications" else self.sheet(aid)
        for row in value:
            for field, namespace in _REFERENCE_FIELDS.items():
                if field in row and row[field] is not None:
                    self.decode(row[field], namespace, aid)
            for reference in row.get("requirement_refs", []):
                self.decode(reference, "requirement", aid)
        if kind == "branches":
            tree = self.tree(aid, selection["tree"])
            population = self.population(aid, selection["population_id"], "leaves")
            _require(population["tree_id"] == tree["tree_id"], "saved_tree_population_conflict")
            _require([row["node_index"] for row in value] == selection["node_indices"], "saved_branch_selection_conflict")
            for row in value:
                _require(self.decode(row["tree_ref"], "tree", aid) == tree["tree_id"], "saved_tree_reference_conflict")
                node = _one(tree["nodes"], node_index=row["node_index"])
                _require(node["parent_index"] is not None, "saved_branch_not_edge")
                _require(_same(row["length"], node["branch_length"]), "saved_branch_length_conflict")
                if row["split_ref"] is not None:
                    self.split(self.decode(row["split_ref"], "split", aid), tree, node)
                _require(all(row[k] is None or row[k] >= 0 for k in ("bootstrap_matches", "bootstrap_replicates")),
                    "saved_bootstrap_count_conflict")
                _require(row["bootstrap_matches"] is None or row["bootstrap_replicates"] is None
                    or row["bootstrap_matches"] <= row["bootstrap_replicates"], "saved_bootstrap_count_conflict")
        elif kind == "sites":
            population, alignment = self.alignment(aid, selection["population_id"])
            _require([row["column_0based"] for row in value] == selection["columns_0based"], "saved_site_selection_conflict")
            for row in value:
                _require(self.decode(row["alignment_ref"], "alignment", aid) == alignment["alignment_id"],
                    "saved_alignment_reference_conflict")
                _require(row["column_0based"] in population["columns_0based"]
                    and 0 <= row["column_0based"] < alignment["observed_column_count"], "saved_column_outside_population")
                _require(row["n_rows"] == len(population["row_indices"]), "saved_site_population_conflict")
                _require(0 <= row["gap_count"] <= row["n_rows"]
                    and all(row[k] is None or 0 <= row[k] <= row["n_rows"] for k in ("canonical_count", "ambiguity_count")),
                    "saved_site_count_conflict")
        elif kind == "family_membership":
            for row in value:
                fid = self.decode(row["family_ref"], "family", aid)
                feature = self.decode(row["feature_ref"], "feature", aid)
                _require(fid in selection["family_ids"], "saved_family_selection_conflict")
                family = _one(sheet["families"], family_id=fid)
                _require(any(member["representation"] == row["representation"] and feature in member["feature_ids"]
                    for member in family["memberships"]), "saved_family_feature_conflict")
                if row["genome_ref"] is not None:
                    genome = self.decode(row["genome_ref"], "genome", aid)
                    _require(any(join["feature_id"] == feature and join["genome_id"] == genome
                        and join["family_id"] in (None, fid) for join in sheet["joins"]["feature_genomes"]),
                        "saved_feature_genome_conflict")
                if row["alignment_row_index"] is not None:
                    rows = set()
                    for index in family["final_block_indices"]:
                        block = sheet["joins"]["family_blocks"][index]
                        _require(block["family_id"] == fid, "saved_family_block_conflict")
                        if block["representation"] != row["representation"]:
                            continue
                        if row["genome_ref"] is not None:
                            rows.update((join["alignment_id"], join["row_index"]) for member in sheet["genomes"]
                                if member["genome_id"] == genome for join in member["final_alignment_rows"]
                                if join["alignment_id"] == block["alignment_id"] and join["row_index"] in block["member_row_indices"])
                    _require(len(rows) == 1 and next(iter(rows))[1] == row["alignment_row_index"],
                        "saved_family_row_conflict")
        elif kind == "function_composition":
            population = self.population(aid, selection["population_id"], "composition")
            functions = {row["function_key"] for row in sheet["joins"]["functions"]}
            functions |= {row["canonical_function_key"] for row in sheet["joins"]["function_equivalences"]}
            identities = []
            for row in value:
                _require(self.decode(row["population_ref"], "population", aid) == population["population_id"],
                    "saved_function_population_conflict")
                function = self.decode(row["function_ref"], "function", aid)
                _require(function in functions, "saved_function_reference_conflict")
                identities.append(function)
                _require(0 <= row["assigned_members"] <= row["members_with_recorded_assignment"] <= row["total_members"]
                    and row["total_members"] == len(population["member_subjects"]), "saved_function_count_conflict")
            _require(len(identities) == len(set(identities)), "saved_duplicate_function")
        elif kind == "relationship_comparisons":
            _require(len(value) <= 1, "saved_comparison_count_conflict")
            for row in value:
                _require(self.decode(row["comparison_ref"], "comparison", aid) == selection["comparison_id"],
                    "saved_comparison_reference_conflict")
                _require(all(row[key] >= 0 for key in ("matched_tips", "gene_splits", "organismal_splits", "shared_splits", "rf"))
                    and row["shared_splits"] <= min(row["gene_splits"], row["organismal_splits"]),
                    "saved_comparison_count_conflict")
        elif kind == "qualifications":
            slots = [row for row in self.sheet_set["selections"] if row["analysis_id"] == aid
                and (selection["slot_id"] is None or row["slot_id"] == selection["slot_id"])]
            roles = {row["role"] for row in slots}
            for row in value:
                _require(row["role_ref"] is None or self.decode(row["role_ref"], "role", aid) in roles,
                    "saved_qualification_role_conflict")
                # Calculator-origin requirement IDs need not occur in the
                # provider sheet; the publication fact itself retains them.
                _require(len(row["requirement_refs"]) == len(set(row["requirement_refs"])),
                    "saved_qualification_requirement_conflict")

    @staticmethod
    def split(identifier, tree, edge):
        # This is an identity relationship check against saved topology. It
        # neither computes split statistics nor replaces a saved fact value.
        prefix = tree["tree_id"] + "/split/"
        _require(identifier.startswith(prefix), "saved_split_tree_conflict")
        suffix = identifier[len(prefix):]
        _require(re.fullmatch(r"(0|[1-9][0-9]*)(,(0|[1-9][0-9]*))*", suffix) is not None,
            "saved_split_identity_conflict")
        side = [int(item) for item in suffix.split(",")]
        _require(side == sorted(set(side)), "saved_split_identity_conflict")
        nodes = {node["node_index"]: node for node in tree["nodes"]}
        tips = {i for i, node in nodes.items() if not node["child_indices"]}
        descendants, pending, seen = set(), [edge["node_index"]], set()
        while pending:
            index = pending.pop()
            _require(index in nodes and index not in seen, "saved_tree_topology_conflict")
            seen.add(index)
            children = nodes[index]["child_indices"]
            if children:
                pending.extend(children)
            else:
                descendants.add(index)
        _require(set(side) in (descendants, tips - descendants)
            and len(side) >= 2 and len(tips - set(side)) >= 2, "saved_split_edge_conflict")
        complement = sorted(tips - set(side))
        _require((len(side), side) <= (len(complement), complement), "saved_split_identity_conflict")


def _saved_facts(body, sheet_set):
    _require(type(body) is dict and body.get("version") == RESULT_VERSION, "publication_required")
    source = body.get("source_ref")
    _require(type(source) is str and _SOURCE_ID.fullmatch(source) is not None
        and body.get("reference") == source, "result_source_conflict")
    publication, inputs = body.get("publication"), body.get("publication_inputs")
    _require(type(publication) is dict and type(inputs) is dict, "publication_required")
    _require(publication.get("bundle_content", {}).get("source_ref") == source
        and source in publication.get("result_record_refs", []) and source in body.get("record_refs", []),
        "result_source_conflict")
    saved = validate_contract("AdapterResult", publication.get("adapter_result"))
    _require(saved["adapter_id"] in _ADAPTERS and saved["adapter_version"] == "1", "phylogeny_adapter_required")
    selector = inputs.get("selector")
    _require(type(selector) is dict and type(selector.get("adapter")) is dict
        and all(selector["adapter"].get(key) == saved[key] for key in ("adapter_id", "adapter_version"))
        and _same(inputs.get("adapter"), selector["adapter"]), "original_adapter_conflict")
    schema = validate_requested_form(selector.get("requested_schema"))
    provider = saved["adapter_id"].removeprefix("bvbrc_")
    parameters = validate_parameters(selector["adapter"].get("parameters"), provider=provider)
    _finite_json(sheet_set)
    binding = saved["sheet_content"]
    _require((sheet_set is None) == (binding is None), "saved_sheet_binding_conflict")
    if binding is not None:
        _require(binding["sha256"] == digest(sheet_set)
            and binding["byte_count"] == len(canonical(sheet_set).encode("utf-8")), "saved_sheet_content_conflict")
    properties, facts = schema["properties"], saved["facts"]
    _require(set(facts) <= set(properties), "unrequested_saved_fact")
    if saved["status"] in {"ok", "partial"}:
        _require(set(facts) == set(properties), "requested_saved_fact_missing")
    rows = {name: [] for name in FACT_SOURCES}
    if not facts:
        return rows
    proof = _SavedIdentities(parameters, sheet_set, saved["adapter_id"])
    for field, node in properties.items():
        if field not in facts:
            continue
        selection, value = node["x-phylogeny-fact"], facts[field]
        kind = proof.selected(selection, provider=provider)
        _require(_Validator(node).is_valid(value), "saved_fact_type_conflict")
        if kind == "requirements":
            _require(_same(value, saved["missing_requirements"]), "saved_requirement_conflict")
            for requirement in value:
                validate_contract("AcquisitionRequirement", requirement)
        elif kind in ("integer", "number"):
            proof.scalar(selection, value)
            kind = "measurements"
        else:
            proof.array(kind, selection, value)
        rows["bvbrc_phylogeny_" + kind].append(
            {"source_ref": source, "field": field, _VALUE_KEYS[kind]: deepcopy(value)})
    return rows


def project_phylogeny_facts(body, *, requested_sources, sheet_set):
    """Copy only saved requested values, using supplied saved identity proof.

    The caller authenticates publication and sheet bytes. This pure function
    grants no custody and reads no files, native output, service or calculator.
    """
    _require(type(requested_sources) in (tuple, list, set, frozenset)
        and all(type(name) is str and name in FACT_SOURCES for name in requested_sources)
        and len(set(requested_sources)) == len(requested_sources), "requested_sources_invalid")
    try:
        rows = _saved_facts(body, sheet_set)
    except (KeyError, TypeError, IndexError, AttributeError, RecursionError) as error:
        raise ValueError(_PREFIX + "saved_identity_structure_invalid") from error
    return {name: rows[name] for name in requested_sources}


class BVBRCPhylogenyReturns(EpisodeReturnRecords):
    def __init__(self, execution):
        super().__init__(execution.store, execution.run_id, failure_prefix=_PREFIX)
        self.api = execution

    def _latest(self, context):
        self.authenticate(context, allow_unsaved=True)
        if context.role != "results":
            return None
        publications = self.api.appservice.publications
        # own_results follows original numerical operation order, not hashed
        # directory names; its reader authenticates original completed custody.
        for reference in reversed(publications.own_results(context)):
            body = publications.read(reference, context.scope, episode_id=context.episode_id)
            saved = body.get("publication", {}).get("adapter_result")
            if saved is None or saved.get("adapter_id") not in _ADAPTERS:
                continue
            self._require(body.get("run_id") == self.run_id and body.get("episode_id") == context.episode_id
                and self._equal(body.get("scope"), context.scope)
                and self._equal(body.get("assignment"), context.assignment)
                and self._equal(body["publication_inputs"].get("selector"), context.assignment.get("selector")),
                "publication_owner_conflict")
            binding = saved["sheet_content"]
            sheet = None if binding is None else publications.read_content_source(binding["source_ref"], context.scope)
            return body, sheet
        return None

    def facts(self, context, schema):
        sources = requested_sources(schema)
        latest = self._latest(context) if sources else None
        facts = ({name: [] for name in sources} if latest is None else
                 project_phylogeny_facts(latest[0], requested_sources=sources, sheet_set=latest[1]))
        for row in facts.get(FACT_SOURCES[6], []):
            for requirement in row["requirements"]:
                for reference in requirement["source_refs"]:
                    self._require(self.store.get(reference).get("record_type") == "source",
                        "requirement_source_required")
                    self.api.appservice.custody.possession(context, reference)
        return facts

    def _attempts(self, context):
        self.authenticate(context, allow_unsaved=True)
        return self.db.execute("SELECT decision_index,contract FROM runtime_report_attempts "
            "WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL "
            "ORDER BY decision_index", (self.run_id, context.episode_id)).fetchall()

    def _attempt(self, context, index):
        # Custody uses the common EpisodeReturnRecords checks, plus the original
        # commission/scope/inputs and full or compact forms authenticated from
        # the original decision's frozen fact catalog. No lifecycle-state gate
        # is added: admission may precede the runtime row's closed-state update.
        child, form, schema = self.api.appservice.custody._attempt(context, index)
        validate_form(form, schema, lambda *_: True)
        self.store.validate_scope(plain(child.scope), parent_scope=plain(context.scope))
        original_index = int(child.path[-1][1].removeprefix("child_"))
        row = self.db.execute("SELECT action FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "AND decision_index=?", (self.run_id, context.episode_id, original_index)).fetchone()
        self._require(row is not None, "original_commission_required")
        selected = json.loads(row["action"])
        original = plain(child.request)["report_contract"]
        if selected.get("kind") in {"episode_child", "child", "job_child"}:
            self._require(self._equal(selected.get("scope"), child.scope)
                and selected.get("purpose") == original["decision"], "original_commission_conflict")
        if self._equal(schema, original["measurements"]["schema"]):
            frozen = self.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (self.run_id, child.episode_id)).fetchone()
            self._require(frozen is not None and frozen["form"] is not None
                and self._equal(json.loads(frozen["form"]), form), "frozen_form_conflict")
        return child, form, schema

    def _validate_values(self, context, form, schema):
        validate_form(form, schema, lambda *_: True)
        if context.role == "results":
            expected = self.facts(context, schema)
        elif context.role in {"annotation", "scientific_process"}:
            expected = self.received_facts(context, schema)
        else:
            raise ValueError(_PREFIX + "unsupported_return_owner")
        for name, node in schema.get("properties", {}).items():
            source = node.get("x-source")
            if source in FACT_SOURCES:
                self._require(name in form and self._equal(form[name], expected[source]), "returned_facts_conflict")
        frozen = self.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (self.run_id, context.episode_id)).fetchone()
        if frozen is not None:
            saved = json.loads(frozen["facts"])
            self._require(all(source in saved and self._equal(saved[source], expected[source])
                for source in requested_sources(schema)), "frozen_facts_conflict")

    def received_context(self, context):
        grouped, seen = {}, {}
        for attempt in self._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if not requested_sources(schema):
                continue
            child, form, original = self._attempt(context, attempt["decision_index"])
            self._validate_values(child, form, original)
            for name, node in original["properties"].items():
                source = node.get("x-source")
                if source not in FACT_SOURCES:
                    continue
                rows, identities = grouped.setdefault(source, []), seen.setdefault(source, set())
                for row in form[name]:
                    key = canonical(row)
                    if key not in identities:
                        rows.append(deepcopy(row))
                        identities.add(key)
        return [{"fact_source": source, "facts": rows} for source, rows in grouped.items()]

    def received_facts(self, context, schema):
        sources = requested_sources(schema)
        facts = {name: [] for name in sources}
        for value in self.received_context(context) if sources else ():
            if value["fact_source"] in facts:
                facts[value["fact_source"]] = value["facts"]
        return facts

    def validate_received_report(self, context, form, schema):
        if requested_sources(schema):
            self._validate_values(context, plain(form), plain(schema))

    def record_admission(self, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, saved_form, saved_schema = self._attempt(context, self._admission_index(context, operation_key))
        self._require(self._equal(form, saved_form) and self._equal(schema, saved_schema), "admitted_form_conflict")
        self._validate_values(child, saved_form, saved_schema)
        # Source references embedded in requested requirements are also actual
        # received dependencies. Semantic labels do not become Store receipts.
        return list(dict.fromkeys(reference for name, node in saved_schema["properties"].items()
            if node.get("x-source") in FACT_SOURCES for reference, namespace in _references(saved_form[name], node)
            if namespace in {"execution_result", "source"}))

    @staticmethod
    def _has_reference(facts, reference, namespace):
        schemas = phylogeny_fact_sources()
        return any(value == reference and kind == namespace for source, rows in facts.items()
            for value, kind in _references(rows, schemas[source]["report_schema"]))

    def resolve_own(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        facts = self.facts(context, schema)
        target_namespace = "source" if namespace is None else namespace
        found = self._has_reference(facts, reference, target_namespace)
        if namespace is None:
            found = found or self._has_reference(facts, reference, "execution_result")
        if found and namespace in {None, "source"}:
            source = self.store.get(reference)
            self._require(source.get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)
        return found if namespace in IDENTIFIER_NAMESPACES or found else None

    def resolve_received(self, context, reference, namespace):
        if namespace not in (*IDENTIFIER_NAMESPACES, "source", "execution_result", None):
            return None
        facts = {value["fact_source"]: value["facts"] for value in self.received_context(context)}
        found = self._has_reference(facts, reference, "source" if namespace is None else namespace)
        if namespace is None:
            found = found or self._has_reference(facts, reference, "execution_result")
        if found and namespace in {None, "source"}:
            self._require(self.store.get(reference).get("record_type") == "source", "requirement_source_required")
            self.api.appservice.custody.possession(context, reference)
        if namespace in IDENTIFIER_NAMESPACES or found:
            return found
        try:
            if self.store.get(reference).get("provider") == DATA_PROVIDER:
                # An unreceived bundle never qualifies merely because it exists.
                # Opaque references use the existing AppService custody resolver.
                return self.api.appservice.resolve(context, reference, namespace)
        except (ValueError, KeyError):
            return False
        return None


__all__ = ["BVBRCPhylogenyReturns", "FACT_SOURCES", "IDENTIFIER_NAMESPACES",
           "phylogeny_fact_sources", "requested_sources", "project_phylogeny_facts"]

