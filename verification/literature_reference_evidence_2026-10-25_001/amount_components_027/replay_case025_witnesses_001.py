"""Mechanical replay of exact previously reviewed025 witnesses; no model/search.

Scientific assignments come from the retained025 review followed by027's full
post-packet reset. This script neither reads new scientific context nor claims
fresh source interpretation. The tiny Store problem is an engineering scope
fixture, not an additional biological annotation target.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_amount_inputs import LITERAL_FIELDS, LEXICAL_DEPENDENCY
from gene_annotation_episode.literature_amount_storage import amount_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
RAW = Path("/tmp/episode-published-cases/specificity/raw")
EXPECTED = {"html": "ccba0fb19356c840512ddcdc05924d00060fc4bcd52e31a79106932e7c6d649e",
    "txt": "cdf6419babae49be1235b38b89370e16346766edf1483614cef3183b85898e12"}


def main():
    data = {suffix: (RAW / f"PMC12051542.{suffix}").read_bytes() for suffix in EXPECTED}
    assert {key: hashlib.sha256(raw).hexdigest() for key, raw in data.items()} == EXPECTED
    helper = ROOT / "gene_annotation_episode/literature_rate_native_inputs.py"
    assert hashlib.sha256(helper.read_bytes()).hexdigest() == LEXICAL_DEPENDENCY["sha256_at_release"]
    state = OUT / "case025_replay_state_001"
    with Store(state) as store:
        if not store.db.execute("SELECT 1 FROM records LIMIT 1").fetchone():
            store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        artifacts = {suffix: store.artifact(raw, "text/html" if suffix == "html" else "text/plain") for suffix, raw in data.items()}
        source = store.put("source", {"provider": "retained_primary_PMC12051542_amount027", "accession": "PMC12051542",
            "uri": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/", "artifact_ref": artifacts["html"],
            "text_ref": artifacts["txt"], "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")["id"]

        def witness(start, end, quote):
            assert data["txt"][start:end].decode() == quote
            return {"source_ref": source, "representation": "text", "start": start, "end": end, "quote": quote}
        target = witness(44824, 44867, "an approximate concentration of 5 mg/ml HFP")
        total = witness(44613, 44642, "7 mg/ml per Bradford analysis")
        hfp = witness(49870, 49877, "8.4 μM")
        imp = witness(49886, 49893, "8.8 μM")
        hfp_name = witness(49878, 49881, "HFP")
        imp_name = witness(49894, 49897, "IMP")
        nominal_pair = witness(49870, 49897, "8.4 μM HFP and 8.8 μM IMP")
        condition = witness(50036, 50052, "55 °C for 4.5 h")

        def subspan(parent, quote):
            char_start = parent["quote"].index(quote)
            start = parent["start"] + len(parent["quote"][:char_start].encode())
            return witness(start, start + len(quote.encode()), quote)
        def meaning(value, *witnesses):
            return {"value": value, "witnesses": list(witnesses)}
        def quantity(w, number, unit, role, kind, qualification):
            start = w["quote"].index(number)
            return {**dict.fromkeys(LITERAL_FIELDS), "measurement": {
                "number": {"witness": w, "number_start": start, "number_end": start + len(number)}, "unit": subspan(w, unit)},
                "amount_role": meaning(role, w), "amount_kind": meaning(kind, w), "qualification": meaning(qualification, w),
                "basis_status": meaning("supported", w), "reported_uncertainty": {"kind": meaning("unreported"), "statement": None}}
        stock = {"source_ref": source, "source_kind": "primary_source", "experiment": None, "intended_change": None,
            "comparison_kind": meaning("stock_target_mass_estimate_over_total_mass_estimate", target, total),
            "pair_relationship": meaning("supported", target, total), "stock_relationship": meaning("same", target, total),
            "quantities": {"numerator": quantity(target, "5", "mg/ml", "target_mass_estimate", "estimated", "source_qualified_approximate"),
                "denominator": quantity(total, "7", "mg/ml", "total_protein_mass_estimate", "estimated", "reported_point")},
            "covariance_source_ref": None}
        stock["quantities"]["numerator"]["subject"] = subspan(target, "HFP")
        stock["quantities"]["denominator"]["method"] = subspan(total, "Bradford analysis")
        stock["quantities"]["numerator"]["reported_basis"] = target
        stock["quantities"]["denominator"]["reported_basis"] = total
        nominal = {"source_ref": source, "source_kind": "primary_source", "experiment": nominal_pair,
            "intended_change": nominal_pair, "comparison_kind": meaning("between_arm_nominal_molar_amount", nominal_pair),
            "pair_relationship": meaning("supported", nominal_pair), "stock_relationship": meaning("not_applicable", nominal_pair),
            "quantities": {"numerator": quantity(hfp, "8.4", "μM", "nominal_molecule_amount", "nominal", "reported_point"),
                "denominator": quantity(imp, "8.8", "μM", "nominal_molecule_amount", "nominal", "reported_point")},
            "covariance_source_ref": None}
        for role, name in (("numerator", hfp_name), ("denominator", imp_name)):
            nominal["quantities"][role].update(subject=name, condition=condition, reported_basis=nominal_pair)
        host = SimpleNamespace(store=store, run_id="amount027-retained-witness-replay", tools=ToolRegistry(store))
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True)
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        selected = ["numerator_amount", "denominator_amount", "amount_difference", "amount_ratio",
            "reciprocal_amount_ratio", "conditional_mass_denominator_factor", "amount_ratio_variance"]
        context = BindingContext(host.run_id, "retained-witness-child", "literature", (("literature", "retained-witness-replay"),),
            store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [],
                "source_refs": [source], "requested_amount_components": selected}, {}, [source])
        form_schema = obj({"source_amounts": amount_cells_schema()})
        outputs = {}
        for name, arguments in (("stock", stock), ("nominal_arms", nominal)):
            outcome = asyncio.run(binding.execute(context, "literature.amount.populate", arguments, "case025-" + name))
            if outcome["status"] != "completed":
                outputs[name] = {"selection": arguments, "outcome": outcome, "typed_form": None, "saved": None}
                continue
            current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
            facts = binding.facts(current, {"committed_record_refs": [outcome["result"]["sheet_ref"]]})
            form = form_with_facts({}, form_schema, facts)
            binding.validate_report(current, form, form_schema)
            outputs[name] = {"selection": arguments, "outcome": outcome, "typed_form": form,
                "saved": binding.services.literature_amount_repository().read(outcome["result"]["sheet_ref"])}
        report = {"version": "amount027_case025_witness_replay_001", "source_sha256": EXPECTED,
            "lexical_dependency": LEXICAL_DEPENDENCY, "basis": "controlled_replay_of_previously_reviewed025_source_witnesses",
            "new_scientific_reading_or_interpretation": False, "model_inference": False, "source_acquisition": False,
            "runtime_observations": store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] if store.db.execute("SELECT 1 FROM sqlite_master WHERE name='runtime_observations'").fetchone() else 0,
            "scope_fixture_is_not_an_additional_annotation_target": True,
            "limits": ["supplement_not_inspected", "original_source_access_exception_preserved",
                "same_stock_and_nominal_assignments_come_from_retained025_review_not_model_extraction",
                "target_stock_method_not_newly_selected_in_this_bounded_replay",
                "mass_factor_not_applied_to_any_rate", "AMOUNT_TASK_draft_unwired", "global_credit_unchanged"],
            "outputs": outputs}
        (OUT / "CASE025_POPULATED_001.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({name: ({key: cell["value"] for key, cell in row["outcome"]["result"]["cells"].items()}
            if row["outcome"]["status"] == "completed" else row["outcome"]["feedback"])
            for name, row in outputs.items()}, indent=2))


if __name__ == "__main__":
    main()
