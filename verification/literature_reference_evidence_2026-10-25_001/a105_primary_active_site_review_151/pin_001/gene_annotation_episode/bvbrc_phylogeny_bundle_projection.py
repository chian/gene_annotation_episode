"""Pure provider composition and finite projection of saved numerical cells.

The provider readers and calculators own scientific interpretation/arithmetic.
This module invokes them once at publication, retains every selected analysis,
and copies only the original requested values. Saved-fact readers import the
separate contracts module and do not invoke this calculation path.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from . import bvbrc_phylogeny_bundle_contracts as c
from . import bvbrc_phylogeny_bundle_resolution as r
from .bvbrc_appservice_contracts import ContractValidationError, _finite_json, _same, _Validator, validate_contract
from .phylogeny_calculation_contracts import scope as quantity_scope


DIAGNOSTIC_CODES = frozenset({
    "phylogeny_requested_component_unavailable", "phylogeny_requested_member_unavailable",
    "phylogeny_quantity_denominator_empty", "phylogeny_quantity_missing", "phylogeny_quantity_not_measured",
    "phylogeny_quantity_failed", "phylogeny_quantity_truncated", "phylogeny_quantity_incompatible",
    "phylogeny_branch_unit_unresolved", "phylogeny_bootstrap_counts_unavailable", "phylogeny_bootstrap_population_incomplete",
    "phylogeny_native_support_unavailable", "phylogeny_native_support_conflict",
    "phylogeny_family_membership_incomplete", "phylogeny_alignment_row_association_required",
    "phylogeny_provider_extraction_invalid", "phylogeny_provider_calculation_invalid",
    "phylogeny_adapter_operands_invalid", "phylogeny_unregistered_diagnostic",
})
_DEPENDENCIES = (
    "bvbrc_phylogeny_bundle_contracts.py", "bvbrc_phylogeny_bundle_resolution.py", "bvbrc_phylogeny_bundle_projection.py",
    "bvbrc_gene_tree_bundle_adapter.py", "bvbrc_codon_tree_bundle_adapter.py",
    "bvbrc_phylogeny_common_inputs.py", "bvbrc_phylogeny_common_contracts.py", "bvbrc_phylogeny_common_grader.py",
    "bvbrc_gene_tree_inputs.py", "bvbrc_gene_tree_grader.py", "bvbrc_codon_tree_inputs.py", "bvbrc_codon_tree_grader.py",
    "phylogeny_formats.py", "phylogeny_format_contracts.py", "phylogeny_raxml_inputs.py",
    "phylogeny_calculation_contracts.py", "phylogeny_calculators.py", "bvbrc_codon_tree_native.py",
    "bvbrc_codon_tree_calculators.py", "bvbrc_appservice_contracts.py", "bvbrc_appservice_schemas.json",
)


def implementation_sha256():
    """Configuration-only hash of actual code/assets with length framing."""
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        content = Path(__file__).with_name(name).read_bytes()
        result.update(name.encode() + b"\0" + str(len(content)).encode() + b"\0" + content)
    return result.hexdigest()


def _one(rows, **keys):
    found = [row for row in rows if all(_same(row.get(k), v) for k, v in keys.items())]
    c.require(len(found) <= 1, "phylogeny_component_identity_ambiguous")
    return found[0] if found else None


def _selected_populations(plan, scientific):
    result = {key: set() for key in c.POPULATION_KEYS}
    for key, rows in scientific["assembly"]["caller_populations"].items():
        result[key].update(row["population_id"] for row in rows)
    for row in plan["population_plans"]:
        kind = row["kind"]
        collection = ("alignments" if kind in ("whole_alignment", "alignment_subset") else "leaves" if kind == "whole_tree"
                      else "bootstraps" if kind == "bootstrap_forest" else row["population_type"])
        result[collection].add(row["population"]["population_id"] if kind == "explicit" else row["population_id"])
    return result


def _validate_selected_form(form, resolution):
    """Reject undeclared or wrong-mode selections before looking up values."""
    plans = {p["analysis"]["analysis_id"]: p for p in resolution.parameters["analyses"]}
    for node in form["properties"].values():
        selection = node["x-phylogeny-fact"]; metric = selection["metric"]
        if metric == "missing_requirements":
            continue
        aid = selection["analysis_id"]
        c.require(aid in plans, "phylogeny_selected_analysis_unknown")
        plan = plans[aid]; params = plan["calculation_parameters"]
        if aid in resolution.invalid_scientific:
            continue  # This analysis has no usable provider operands or facts.
        spec = c.SCALAR_CATALOG.get(metric)
        if resolution.provider == "gene_tree":
            c.require(metric != "family_membership_rows" and (spec is None or spec["collection"] not in ("literal_statistics", "family_populations", "worst_sequence_ratios")), "phylogeny_fact_provider_conflict")
        if "tree" in selection:
            c.require((aid, selection["tree"]["slot_id"]) in resolution.selections, "phylogeny_slot_not_declared")
        if metric == "qualifications":
            c.require(selection["slot_id"] is None or (aid, selection["slot_id"]) in resolution.selections, "phylogeny_slot_not_declared")
            continue
        if metric == "family_membership_rows":
            continue
        collection = spec["collection"] if spec else {"branch_rows": "trees", "site_rows": "alignments", "function_composition_rows": "composition", "relationship_comparison": "comparisons"}[metric]
        pid = selection.get("population_id")
        if collection in ("alignments", "trees", "taxonomy"):
            key = {"alignments": "alignment_requests", "trees": "tree_requests", "taxonomy": "taxon_requests"}[collection]
            c.require(any(row["population_id"] == pid and (collection != "taxonomy" or row["rank"] == selection["rank"]) for row in params[key]), "phylogeny_calculation_not_selected")
        elif collection in ("original_coverage", "composition", "literal_statistics"):
            key = {"original_coverage": "original_coverage_population_ids", "composition": "composition_population_ids", "literal_statistics": "literal_statistic_population_ids"}[collection]
            c.require(pid in params[key], "phylogeny_calculation_not_selected")
        elif collection == "bootstrap":
            c.require(any(row["replicate_population_id"] == pid and _same(row["reference_tree_id"], selection["tree"]) for row in params["bootstrap_requests"]), "phylogeny_calculation_not_selected")
        elif collection == "comparisons":
            c.require(any(row["comparison_id"] == selection["comparison_id"] for row in params["comparisons"]), "phylogeny_calculation_not_selected")
        elif collection == "family_populations":
            c.require({key: selection[key] for key in ("family_population_id", "genome_population_id")} in params["family_population_requests"], "phylogeny_calculation_not_selected")
        elif collection == "worst_sequence_ratios":
            c.require(selection["family_population_id"] == params["worst_sequence_population_id"], "phylogeny_calculation_not_selected")
        populations = _selected_populations(plan, resolution.scientific[aid])
        for key in ("population_id", "family_population_id", "genome_population_id"):
            if key in selection and collection != "worst_sequence_ratios":
                c.require(selection[key] in set().union(*populations.values()), "phylogeny_population_not_selected")


class Projection:
    def __init__(self, resolution, plan, analysis, components):
        self.resolution, self.plan, self.analysis, self.components = resolution, plan, analysis, components
        self.aid = analysis["analysis_id"]; self.sheet = analysis["sheet"]
        self.requirements, self.diagnostics = [], []
        registries = [analysis["missing_requirements"]]
        if self.sheet is not None:
            registries.append(self.sheet["missing_requirements"])
        if components is not None:
            registries.append(components["missing_requirements"])
        self.registry = {row["requirement_id"]: row for row in r.merge_requirements(*registries)}

    def ref(self, kind, identifier):
        return c.encode_reference(kind, self.aid, identifier)

    def need(self, reason, selection, *, role=None, kind="scientific_metadata", refs=()):
        req = r.requirement(reason, analysis_id=self.aid, role=role, kind=kind,
                            identity=json.dumps(selection, sort_keys=True), refs=refs)
        self.requirements = r.merge_requirements(self.requirements, [req])
        self.diagnostics.append(r.diagnostic(reason, phase="return", refs=refs))
        return None

    def dependencies(self, selection):
        """Copy exact selected-slot failures; unrelated omitted slots stay local."""
        if self.aid in self.resolution.invalid_scientific:
            self.requirements = r.merge_requirements(self.requirements,
                [row for row in self.registry.values() if row["reason_code"] in (
                    "phylogeny_supplied_inputs_invalid", "phylogeny_supplied_document_invalid")])
        refs = []
        if "tree" in selection:
            refs.append(selection["tree"])
        pid = selection.get("population_id")
        for plan in self.plan["population_plans"]:
            if plan.get("population_id") == pid:
                for key in ("alignment", "tree", "forest"):
                    if key in plan:
                        refs.append(plan[key])
        if "comparison_id" in selection:
            for request in self.plan["calculation_parameters"]["comparisons"]:
                if request["comparison_id"] == selection["comparison_id"]:
                    refs += [request["gene_tree_id"], request["organismal_tree_id"]]
        for ref in refs:
            row = self.resolution.selections[(self.aid, ref["slot_id"])]
            for rid in row["requirement_ids"]:
                c.require(rid in self.registry, "phylogeny_quantity_requirement_unbound")
                self.requirements = r.merge_requirements(self.requirements, [self.registry[rid]])

    def quantity(self, cell, selection, *, unit=None):
        c.shape(cell, ("value", "state", "unit", "origin", "numerator", "denominator", "population_ref", "method", "evidence", "requirement_ids"), "phylogeny_quantity_invalid")
        c.require(cell["state"] in ("available", "missing", "not_measured", "failed", "truncated", "incompatible"), "phylogeny_quantity_invalid")
        c.require((cell["value"] is not None) == (cell["state"] == "available"), "phylogeny_quantity_state_conflict")
        if unit is not None and unit != "native_unknown" and cell["unit"] != unit:
            for reason in ("branch_unit_conflict", "branch_unit_unresolved"):
                req = self.registry.get(quantity_scope(selection["population_id"]) + "/" + reason)
                if req is not None:
                    self.requirements = r.merge_requirements(self.requirements, [req])
            return self.need("phylogeny_branch_unit_unresolved", selection, role="branch_model_units")
        # Requirement IDs can also qualify a conditional available component.
        for rid in cell["requirement_ids"]:
            c.require(rid in self.registry, "phylogeny_quantity_requirement_unbound")
            self.requirements = r.merge_requirements(self.requirements, [self.registry[rid]])
        if cell["value"] is None and not cell["requirement_ids"]:
            reason = "phylogeny_quantity_denominator_empty" if cell["denominator"] == 0 else "phylogeny_quantity_" + cell["state"]
            self.need(reason, selection)
        return cell["value"]

    def component(self, collection, selection):
        if self.components is None:
            self.dependencies(selection)
            return self.need("phylogeny_requested_component_unavailable", selection)
        rows = self.components.get(collection)
        if collection == "worst_sequence_ratios":
            row = rows if rows is not None and rows["family_population_id"] == selection["family_population_id"] else None
        else:
            c.require(type(rows) is list, "phylogeny_component_collection_invalid")
            keys = ("comparison_id",) if collection == "comparisons" else ("family_population_id", "genome_population_id") if collection == "family_populations" else ("population_id", "rank") if collection == "taxonomy" else ("population_id",)
            row = _one(rows, **{key: selection[key] for key in keys})
        if row is not None and "tree" in selection:
            try:
                tid = self.resolution.identifier(selection["tree"], tree=True)
            except r._Unavailable:
                row = None
            else:
                c.require(row["reference_tree_id" if collection == "bootstrap" else "tree_id"] == tid, "phylogeny_requested_tree_population_conflict")
        if row is None:
            self.dependencies(selection)
            if collection == "bootstrap":
                for reason in ("bootstrap_method_unresolved", "bootstrap_method_conflict"):
                    req = self.registry.get(quantity_scope(selection["population_id"]) + "/" + reason)
                    if req is not None:
                        self.requirements = r.merge_requirements(self.requirements, [req])
            self.need("phylogeny_requested_component_unavailable", selection)
        return row

    def scalar(self, selection):
        spec = c.SCALAR_CATALOG[selection["metric"]]
        component = self.component(spec["collection"], selection)
        if component is None:
            return None
        row = component
        if spec["nested"] is not None:
            rows = component[spec["nested"]]
            keys = {}
            for key in ("column_0based", "row_index", "row_a", "row_b", "node_index", "node_a", "node_b", "function_key", "taxon_id", "family_id", "feature_id", "genome_id"):
                if key in selection:
                    keys[key] = selection[key]
            if spec["collection"] == "bootstrap":
                tree_rows = [t for t in self.components["trees"] if t["tree_id"] == component["reference_tree_id"]]
                split_ids = {branch["split_id"] for tree in tree_rows for branch in tree["branches"] if branch["node_index"] == selection["node_index"]}
                c.require(len(split_ids) <= 1, "phylogeny_component_identity_ambiguous")
                keys = {"split_id": next(iter(split_ids))} if split_ids else {"split_id": None}
            if spec["collection"] == "original_coverage":
                keys["member"] = {k: selection[k] for k in ("input_binding_id", "member_id")}
            row = _one(rows, **keys)
            if row is None:
                if spec["collection"] == "original_coverage":
                    self.requirements = r.merge_requirements(self.requirements, component["missing_requirements"])
                return self.need("phylogeny_requested_member_unavailable", selection)
        unit = None
        if spec["collection"] == "trees" and (spec["field"] in ("branch_length_sum", "known_branch_length_sum", "length") or spec["nested"] == "distances"):
            request = _one(self.plan["calculation_parameters"]["tree_requests"], population_id=selection["population_id"])
            unit = request["branch_unit"]
        if spec["collection"] == "bootstrap" and spec["field"] == "frequency" and row[spec["field"]]["method"] in (
                "conditional_rapid_bootstrap_frequency", "conditional_rell_bootstrap_frequency"):
            self.need("phylogeny_bootstrap_population_incomplete", selection, role="bootstrap_replicates", kind="output_bytes")
        return self.quantity(row[spec["field"]], selection, unit=unit)

    def _native_support(self, branch, selection):
        observations = {row["observation_id"]: row for row in self.sheet["native_measurements"]}
        values = [observations[oid] for oid in branch["native_support_observation_ids"]]
        if not values or any(v["value"] is None for v in values):
            return self.need("phylogeny_native_support_unavailable", selection, role="branch_support")
        if len({(v["value"], v["unit"], v["method"]) for v in values}) != 1:
            return self.need("phylogeny_native_support_conflict", selection, role="branch_support")
        return values[0]["value"]

    def branches(self, selection):
        tree = self.component("trees", selection)
        if tree is None:
            return None
        rows = []
        for index in selection["node_indices"]:
            branch = _one(tree["branches"], node_index=index)
            if branch is None:
                return self.need("phylogeny_requested_member_unavailable", selection)
            sel = {**selection, "node_index": index}
            length = self.quantity(branch["length"], sel)
            support = self._native_support(branch, sel)
            bootstraps = [row for component in self.components["bootstrap"] if component["reference_tree_id"] == tree["tree_id"]
                          for row in component["rows"] if row["split_id"] == branch["split_id"]]
            if len(bootstraps) == 1:
                matches = self.quantity(bootstraps[0]["matches"], sel)
                denominator = self.quantity(bootstraps[0]["denominator"], sel)
            else:
                matches = denominator = self.need("phylogeny_bootstrap_counts_unavailable", sel, role="bootstrap_replicates", kind="output_bytes")
            rows.append({"tree_ref": self.ref("tree", tree["tree_id"]), "node_index": index,
                "split_ref": None if branch["split_id"] is None else self.ref("split", branch["split_id"]),
                "length": length, "length_unit": branch["length"]["unit"], "support_value": support,
                "support_method": branch["support_method"], "support_scale": branch["support_scale"],
                "bootstrap_matches": matches, "bootstrap_replicates": denominator})
        return rows

    def sites(self, selection):
        component = self.component("alignments", selection)
        if component is None:
            return None
        count = self.quantity(component["member_count"], selection)
        if count is None:
            return None
        result = []
        for column in selection["columns_0based"]:
            site = _one(component["sites"], column_0based=column)
            if site is None:
                return self.need("phylogeny_requested_member_unavailable", selection)
            values = {k: self.quantity(site[k], {**selection, "column_0based": column}) for k in (
                "gap_count", "canonical_count", "ambiguity_count", "canonical_majority_fraction", "canonical_entropy_bits")}
            if values["gap_count"] is None:
                return None
            result.append({"alignment_ref": self.ref("alignment", component["alignment_id"]), "column_0based": column,
                           "n_rows": count, **values})
        return result

    def families(self, selection):
        if self.sheet is None:
            return self.need("phylogeny_requested_component_unavailable", selection)
        result = []
        for fid in selection["family_ids"]:
            family = _one(self.sheet["families"], family_id=fid)
            if family is None or not family["memberships"]:
                return self.need("phylogeny_family_membership_incomplete", selection, role="family_membership")
            for membership in family["memberships"]:
                table = _one(self.sheet["documents"]["store"]["native_tables"], table_id=membership["source_table_id"])
                if table is None or table["completeness"] != "complete":
                    return self.need("phylogeny_family_membership_incomplete", selection, role="family_membership")
                for feature in membership["feature_ids"]:
                    join = _one(self.sheet["joins"]["feature_genomes"], feature_id=feature)
                    genome = None if join is None else join["genome_id"]
                    indices = set()
                    for block in (self.sheet["joins"]["family_blocks"][i] for i in family["final_block_indices"]):
                        if block["representation"] != membership["representation"]:
                            continue
                        for g in self.sheet["genomes"]:
                            if g["genome_id"] == genome:
                                indices.update((row["alignment_id"], row["row_index"]) for row in g["final_alignment_rows"] if row["alignment_id"] == block["alignment_id"] and row["row_index"] in block["member_row_indices"])
                    row_index = next(iter(indices))[1] if len(indices) == 1 else None
                    if genome is None:
                        self.need("phylogeny_alignment_row_association_required", {**selection, "feature_id": feature}, role="feature_genome_membership")
                    if row_index is None:
                        self.need("phylogeny_alignment_row_association_required", {**selection, "feature_id": feature}, role="final_family_coordinates")
                    result.append({"family_ref": self.ref("family", fid), "representation": membership["representation"],
                        "feature_ref": self.ref("feature", feature), "genome_ref": None if genome is None else self.ref("genome", genome),
                        "alignment_row_index": row_index, "inclusion_stage": "final_" + membership["representation"]})
        return result

    def functions(self, selection):
        component = self.component("composition", selection)
        if component is None:
            return None
        total = self.quantity(component["total_members"], selection)
        assigned = self.quantity(component["members_with_recorded_assignment"], selection)
        if total is None or assigned is None:
            return None
        result = []
        for row in component["rows"]:
            count = self.quantity(row["assigned_members"], selection)
            if count is None:
                return None
            result.append({"population_ref": self.ref("population", component["population_id"]),
                "function_ref": self.ref("function", row["function_key"]), "assigned_members": count,
                "total_members": total, "members_with_recorded_assignment": assigned,
                "fraction_all": self.quantity(row["fraction_all"], selection),
                "fraction_recorded": self.quantity(row["fraction_recorded"], selection)})
        return result

    def comparisons(self, selection):
        component = self.component("comparisons", selection)
        if component is None:
            return None
        values = {key: self.quantity(component[key], selection) for key in ("matched_tips", "gene_splits", "organismal_splits", "shared_splits", "rf", "rf_fraction")}
        if any(values[key] is None for key in values if key != "rf_fraction"):
            return None
        return [{"comparison_ref": self.ref("comparison", component["comparison_id"]), **values}]

    def qualifications(self, selection):
        slots = [row for row in self.resolution.selections.values() if row["analysis_id"] == self.aid and (selection["slot_id"] is None or row["slot_id"] == selection["slot_id"])]
        sources = {ref["source_ref"] for slot in slots for ref in slot["artifact_refs"]}
        diagnostics = r.unique([*self.analysis["diagnostics"], *(self.components["diagnostics"] if self.components is not None else [])])
        result = []
        for row in diagnostics:
            if selection["slot_id"] is not None and not sources.intersection(row["evidence_refs"]):
                continue
            roles = [slot["role"] for slot in slots if {ref["source_ref"] for ref in slot["artifact_refs"]}.intersection(row["evidence_refs"])]
            code = row["code"] if row["code"] in c.QUALIFICATION_CODES else "phylogeny_unregistered_diagnostic"
            reqs = [self.ref("requirement", req["requirement_id"]) for req in self.registry.values()
                    if req["reason_code"] in (row["code"], row["code"].removeprefix("bvbrc_phylogeny_"), row["code"].removeprefix("codon_provider_"), row["code"].removeprefix("phylogeny_"))]
            result.append({"code": code, "phase": row["phase"], "severity": row["severity"],
                "role_ref": self.ref("role", roles[0]) if len(set(roles)) == 1 else None, "requirement_refs": reqs})
        return r.unique(result)

    def fact(self, selection):
        metric = selection["metric"]
        if metric in c.SCALAR_CATALOG:
            return self.scalar(selection)
        return {"branch_rows": self.branches, "site_rows": self.sites, "family_membership_rows": self.families,
                "function_composition_rows": self.functions, "relationship_comparison": self.comparisons,
                "qualifications": self.qualifications}[metric](selection)


def consume_bundle(bundle, *, artifact_bytes, supplied_values, requested_form, parameters, provider):
    """Compose actual providers and save all analyses, including invalid members."""
    tool = "C-L194-GeneTree" if provider == "gene_tree" else "C-L193-CodonTree"
    output = {"adapter_id": "bvbrc_" + provider, "adapter_version": "1", "status": "invalid",
        "sheet": {"schema_version": "bvbrc_phylogeny_sheet_set_v1", "tool": tool, "selections": [], "analyses": []},
        "components": {"schema_version": "bvbrc_phylogeny_component_set_v1", "analyses": []},
        "facts": {}, "missing_requirements": [], "diagnostics": []}
    try:
        parameters = c.validate_parameters(parameters, provider=provider)
        form = c.validate_requested_form(requested_form)
        for plan in parameters["analyses"]:
            aid = plan["analysis"]["analysis_id"]
            output["sheet"]["analyses"].append({"analysis_id": aid, "status": "invalid", "sheet": None, "diagnostics": [], "missing_requirements": []})
            output["components"]["analyses"].append({"analysis_id": aid, "components": None})
        resolution = r.resolve_bundle(bundle, artifact_bytes=artifact_bytes, supplied_values=supplied_values, parameters=parameters, provider=provider)
        _validate_selected_form(form, resolution)
        if provider == "gene_tree":
            from .bvbrc_gene_tree_inputs import extract_gene_tree_sheet as extract
            from .bvbrc_gene_tree_grader import calculate_gene_tree as calculate
        else:
            from .bvbrc_codon_tree_inputs import extract_codon_tree_sheet as extract
            from .bvbrc_codon_tree_grader import calculate_codon_tree as calculate
        for plan, analysis, component in zip(parameters["analyses"], output["sheet"]["analyses"], output["components"]["analyses"]):
            aid = analysis["analysis_id"]
            try:
                operands = resolution.analysis_operands(plan)
                calculation = operands.pop("calculation_parameters")
                parsed = extract(**operands)
                analysis.update(status=parsed["status"], sheet=parsed["value"], diagnostics=r.unique([*resolution.diagnostics[aid], *parsed["diagnostics"]]),
                    missing_requirements=r.merge_requirements(resolution.requirements[aid], parsed["value"]["missing_requirements"] if parsed["value"] is not None else []))
                if parsed["value"] is not None:
                    sheet = analysis["sheet"]
                    sheet["qualifications"] = r.unique([*sheet["qualifications"], *resolution.diagnostics[aid]])
                    sheet["missing_requirements"] = r.merge_requirements(sheet["missing_requirements"], resolution.requirements[aid])
                    try:
                        component["components"] = calculate(sheet, calculation)
                    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
                        analysis["diagnostics"].append(r.diagnostic("phylogeny_provider_calculation_invalid"))
                        analysis["status"] = "partial"
                else:
                    analysis["diagnostics"].append(r.diagnostic("phylogeny_provider_extraction_invalid"))
            except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
                analysis["diagnostics"] = r.unique([*resolution.diagnostics[aid], r.diagnostic("phylogeny_provider_extraction_invalid")])
                analysis["missing_requirements"] = r.merge_requirements(resolution.requirements[aid])
                analysis["status"] = "invalid"
        output["sheet"]["selections"] = deepcopy(list(resolution.selections.values()))
        output["diagnostics"] = r.unique([*resolution.bundle["diagnostics"], *(d for a in output["sheet"]["analyses"] for d in a["diagnostics"])])
        output["missing_requirements"] = r.merge_requirements(resolution.bundle["missing_requirements"], resolution.mandatory)
        projectors = {a["analysis_id"]: Projection(resolution, p, a, co["components"])
                      for p, a, co in zip(parameters["analyses"], output["sheet"]["analyses"], output["components"]["analyses"])}
        for name, node in form["properties"].items():
            selection = node["x-phylogeny-fact"]
            if selection["metric"] != "missing_requirements":
                output["facts"][name] = projectors[selection["analysis_id"]].fact(selection)
        for projector in projectors.values():
            output["missing_requirements"] = r.merge_requirements(output["missing_requirements"], projector.requirements)
            output["diagnostics"] = r.unique([*output["diagnostics"], *projector.diagnostics])
        for name, node in form["properties"].items():
            if node["x-phylogeny-fact"]["metric"] == "missing_requirements":
                output["facts"][name] = deepcopy(output["missing_requirements"])
        c.require(next(_Validator(form).iter_errors(output["facts"]), None) is None, "phylogeny_projected_fact_type_conflict")
        output["status"] = "partial" if output["missing_requirements"] else "ok"
        usable = any(node["x-phylogeny-fact"]["metric"] not in ("missing_requirements", "qualifications")
                     and output["facts"][name] is not None for name, node in form["properties"].items())
        if resolution.bundle["status"] == "failed" and not usable:
            output["status"] = "failed"
    except ContractValidationError as error:
        output["diagnostics"].extend(r.diagnostic(row["code"], row["path"], phase="publication") for row in error.diagnostics)
        output["status"] = "invalid"
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError, RecursionError):
        output["diagnostics"].append(r.diagnostic("phylogeny_adapter_operands_invalid", phase="publication"))
        output["status"] = "invalid"
    output["diagnostics"] = r.unique(output["diagnostics"])
    for row in output["diagnostics"]:
        validate_contract("Diagnostic", row)
    _finite_json(output)
    return output


__all__ = ["consume_bundle", "implementation_sha256"]
