"""Controlled original-paper population through the existing shared episode loop.

Root supplies reviewed scientific selections. This is not an autonomous model
investigation. Original measurements are retained, not synthetic fixture values.
"""
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
from functools import partial
import asyncio
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = HERE.parent / "a105_primary_active_site_review_151/pin_001"
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / "tests")]
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_composition import compose_episode_bindings
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_active_site_calculations import COMPONENTS
from gene_annotation_episode.literature_active_site_storage import LiteratureActiveSiteRepository, active_site_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider

SOURCES = ROOT / "research/experimental_scoring_review_2026-10-23/a105_active_site_amount_case_150/source"
SI_TEXT = HERE.parent / "a105_primary_active_site_review_151/ROOT_SUPPLEMENT_TEXT_001.txt"
SHA = {"PMC11121168.xml": "f7fadd0ba7ac049f98c8e262de7873a396fc13922d01070ca362cc1db9d26a72",
       "mmc1.pdf": "1bc2a2107066d621e91f11e4293f90fdefff8fbfdb227e7c2ae40e2283c3ca82"}


def prepare(store):
    manifest = HERE / "source_only_manifest_001.json"
    manifest.write_text(json.dumps({"schema_version": 1, "entries": []}) + "\n")
    store.create_problem(manifest_path=manifest)
    raw = {}
    for name, digest in SHA.items():
        raw[name] = (SOURCES / name).read_bytes()
        assert hashlib.sha256(raw[name]).hexdigest() == digest
    article = ET.fromstring(raw["PMC11121168.xml"])
    main_text = "".join(article.find("body").itertext())
    supplement = SI_TEXT.read_text()
    assert hashlib.sha256(SI_TEXT.read_bytes()).hexdigest() == "dc1caaef296094af4b35a860d5369f121d8149718f9bab6883910eee7ce3b06a"
    texts = {"main": main_text, "si": supplement}
    main_artifact = store.artifact(raw["PMC11121168.xml"], "application/xml")
    main = store.put("source", {"provider": "caller_retained_primary", "accession": "PMC11121168",
        "uri": "https://doi.org/10.1016/j.apsb.2024.03.001", "artifact_ref": main_artifact,
        "text_ref": store.artifact(main_text, "text/plain"), "request_ref": None,
        "version": "root_etree_body_itertext_v1", "retrieved_at": None}, origin="caller")["id"]
    pdf_artifact = store.artifact(raw["mmc1.pdf"], "application/pdf")
    si = store.put("source", {"provider": "caller_retained_primary_supplement", "accession": None,
        "uri": "https://ars.els-cdn.com/content/image/1-s2.0-S2211383524000820-mmc1.pdf",
        "artifact_ref": pdf_artifact, "text_ref": store.artifact(supplement, "text/plain"),
        "request_ref": None, "version": "root_pdftotext_layout_v1", "retrieved_at": None,
        "parent_source_refs": [main]}, origin="caller")["id"]
    references = {"main": main, "si": si}

    def witness(key, quote, *, within=None):
        text = texts[key]
        base = text.index(within) if within is not None else 0
        end = base + len(within) if within is not None else len(text)
        position = text.index(quote, base, end)
        assert text.count(quote, base, end) == 1, (key, quote)
        return {"source_ref": references[key], "representation": "text",
            "start": len(text[:position].encode()), "end": len(text[:position + len(quote)].encode()), "quote": quote}

    def meaning(value, *witnesses):
        return {"value": value, "witnesses": list(witnesses)}

    fig2 = "".join(article.find(".//fig[@id='fig2']/caption").itertext())
    fig5 = supplement[supplement.index("Figure S5."):supplement.index("\f", supplement.index("Figure S5."))]
    methods = "".join(article.find(".//sec[@id='sec2.3']").itertext())
    mw_context = "For the calculation of the proportion of active enzyme, a mass of 34.21\u00a0kDa per monomer was assumed"
    mw = witness("main", "34.21\u00a0kDa", within=mw_context)
    assumptions = {
        "molecular_basis": meaning("per_monomer", witness("main", "per monomer was assumed", within=mw_context)),
        "active_estimate_meaning": meaning("titrated_active_sites", witness("main", "x-intercept which equals the active-site concentration", within=methods)),
        "titrant_concentration_basis": meaning("nominal_reported", witness("main", "the titrant solution in DMSO", within=methods)),
        "titrant_to_site_stoichiometry": meaning("reported_one_to_one", witness("main", "1:1 stoichiometry")),
        "site_stoichiometry": meaning("one_site_per_monomer", witness("main", "The catalytic dyad of each protomer")),
        "normalization_stage": meaning("active_sites", witness("main", "The active-site concentration [E]0 was accessible")),
    }
    intended = witness("main", "the His tag was cleaved off using an HRV 3C protease")
    other = witness("main", "Mpro batches were employed as solutions in concentrations ranging")
    condition = witness("main", "incubation was performed for 5\u00a0min (unless noted otherwise) at 37\u00a0°C", within=methods)

    def measured(key, quote, number, unit, within):
        selected = witness(key, quote, within=within)
        position = selected["quote"].index(number)
        return {"number": {"witness": selected, "number_start": position, "number_end": position + len(number)},
            "unit": witness(key, unit, within=quote)}

    arguments = []
    for key, caption, label, mass, active, spread, fraction in (
        ("main", fig2, "His-tagged SARS-CoV-2 Mpro", "2.0\u00a0ng/μL", "32.6", "3.8", "56%"),
        ("si", fig5, "purified native SARS-CoV-2 Mpro", "7.5 ng/µL", "43.0", "0.9", "20%")):
        experiment = witness(key, "Active-site titration of " + label, within=caption)
        subject = witness(key, "SARS-CoV-2 Mpro", within=caption)
        preparation = witness(key, "same enzyme preparation", within=caption)
        uncertainty = witness(key, "The standard deviations refer to the linear regression.", within=caption)
        repetition = witness(key, "aliquots from the same enzyme preparation", within=caption)
        titer_quote = "32.6\u00a0±\u00a03.8\u00a0nmol/L" if key == "main" else "43.0 ±0.9 nmol/L"
        data = (
            ("protein_mass_concentration", key, mass, mass.split()[0], mass.split()[1], caption),
            ("assumed_molecular_weight", "main", mw["quote"], "34.21", "kDa", mw_context),
            ("active_site_concentration", key, titer_quote, active, "nmol/L", caption),
            ("reported_active_fraction", key, fraction, fraction[:-1], "%", caption),
        )
        quantities = {}
        for role, source_key, quote, number, unit, context in data:
            measurement = measured(source_key, quote, number, unit, context)
            quantities[role] = {"subject": subject,
                "organism": witness(key, "SARS-CoV-2", within=caption),
                "construct": witness(key, label, within=caption), "preparation": preparation,
                "assay": experiment, "condition": condition,
                "endpoint": witness(key, "active enzyme concentration", within=caption),
                "measurement_identity": witness(source_key, quote, within=context),
                "measurement": measurement,
                "qualification": meaning("reported_point", measurement["number"]["witness"]),
                "reported_uncertainty": {"kind": meaning("unreported"), "measurement": None,
                    "sampling_basis": meaning("unknown"), "statement": None}}
        quantities["active_site_concentration"]["reported_uncertainty"] = {
            "kind": meaning("regression_sd", uncertainty),
            "measurement": measured(key, titer_quote, spread, "nmol/L", caption),
            "sampling_basis": meaning("same_preparation_aliquots", repetition), "statement": uncertainty}
        args = {"source_ref": references[key], "source_kind": "primary_source", "experiment": experiment,
            "intended_change": intended, "other_changes": [other],
            "interpretations": {**assumptions, "amount_linkage": meaning("same_preparation_and_assay", repetition)},
            "quantities": quantities}
        arguments.append(args)
    provenance = {"primary_sha256": SHA, "supplement_text_sha256": hashlib.sha256(SI_TEXT.read_bytes()).hexdigest(),
        "main_text_render": "ElementTree article/body itertext concatenation; exact text representation retained with original XML",
        "supplement_text_render": "Previously retained root pdftotext -layout extraction, preserved byte-for-byte with original PDF",
        "source_refs": references, "original_artifact_refs": [main_artifact, pdf_artifact],
        "viral_genotype": "not selected; no viral mutation or reference-genome sequence is inferred",
        "rate_scope": "Titration arms only; native kinetic5.65ng/uL is not native titer7.5ng/uL",
        "normalization_stage_scope": "Source downstream turnover convention, not an assertion that titer43nM equals the later kinetic concentration",
        "selection_author": "root scientific source read and reset, controlled verification choices; not model-authored autonomous choices"}
    return arguments, provenance


async def execute(directory):
    with Store(directory / "state") as store:
        arguments, provenance = prepare(store)
        refs = list(provenance["source_refs"].values())
        form = obj({"active_site_amounts": active_site_cells_schema()})
        assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": refs, "requested_active_site_components": list(COMPONENTS)}
        child = {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
            "goal": "Evaluate active-site amount denominators in separately assayed tagged and native SARS-CoV-2 Mpro preparations.",
            "scope": store.validate_scope(), "purpose": "Return the nine numerical amount components for each source titration with its actual preparation and uncertainty meanings.",
            "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}
        work = [{"selection": {"kind": "tool", "tool": "literature.active_site.populate", "arguments": args}, "report_update": {}}
            for args in arguments]
        returned = []
        def receive(inputs):
            result, = inputs["child_reports"]
            returned.extend(plain(result["active_site_amounts"]))
            assert len(returned) == 18
            commit = {field: [] for field in store.reasoning_schema()["required"]}
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
        controllers = []
        def controller(path, initial):
            value = FixtureController(str(path), initial, 2)
            controllers.append(value)
            return value
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = await run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, *work, receive]),
            run_dir=directory / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=refs,
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                active_site_population=True, reference_parent_sources=refs),),
            binding_definitions={"credit": scorer.as_record()},
            goal="Evaluate what the original active-site titration experiments establish about functional enzyme amount and rate normalization; no target correspondence or annotation credit.")
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 4
        assert store.db.execute("SELECT count(*) FROM literature_active_site_operations").fetchone()[0] == 2
        assert not store.list("observation") and not store.list("assessment")
        run_id, parent_id = store.db.execute("SELECT run_id,episode_id FROM literature_active_site_received").fetchone()
        sheets = list(dict.fromkeys(row["sheet_ref"] for row in returned))
        repo = LiteratureActiveSiteRepository(store, run_id)
        saved = [repo.read(reference) for reference in sheets]
        (directory / "populated_sheets.json").write_text(json.dumps(saved, indent=2) + "\n")
        (directory / "typed_return.json").write_text(json.dumps(returned, indent=2) + "\n")
        parent = BindingContext(run_id, parent_id, "annotation", (("annotation", parent_id),),
            store.validate_scope(), {}, {}, sheets)
        descriptor, = json.loads((directory / "run/run.json").read_text())["episode_bindings"]
        numbers = [{"preparation_source_ref": row["input_source_ref"],
            "cells": {name: cell["value"] for name, cell in row["sheet"]["cells"].items()},
            "fraction_uncertainty": row["sheet"]["fraction_uncertainty"]} for row in saved]
    with Store(directory / "state") as cold:
        original_get = cold.get_artifact
        forbidden_artifacts = set(provenance["original_artifact_refs"])
        forbidden_artifacts.update(cold.get(reference)["text_ref"] for reference in refs)
        def guarded(reference):
            assert reference not in forbidden_artifacts, "Reconstruction must not reacquire primary source bytes"
            return original_get(reference)
        cold.get_artifact = guarded
        import gene_annotation_episode.literature_active_site_storage as storage
        original_reader = storage.read_active_site_inputs
        def forbidden(*args, **kwargs):
            raise AssertionError("Reconstruction cannot reinterpret primary sources")
        storage.read_active_site_inputs = forbidden
        try:
            cold.db.execute("PRAGMA query_only=ON")
            before = cold.db.total_changes
            binding, = compose_episode_bindings(WorkflowServices(SimpleNamespace(store=cold, run_id=run_id)),
                store=cold, journal=SimpleNamespace(store=cold, run_id=run_id), execution_backend=None,
                descriptors=[descriptor], job_episodes=None, resource_estimator=None, role_credit_bindings={}).bindings
            assert binding.as_record() == descriptor
            adapter = binding._active_site_repository()
            assert adapter.received_cells(parent) == returned
            assert adapter.fact_cells(parent, sheets, components=list(COMPONENTS)) == returned
            assert cold.db.total_changes == before
        finally:
            storage.read_active_site_inputs = original_reader
    result = {"scope": "Original primary measurements; controlled source selections/provider/controller; actual existing shared episode loop, typed return and saved factory reconstruction",
        "actual_model_backed": False, "source_provenance": provenance, "numerical_results": numbers,
        "runtime_observations": 4, "selected_population_operations": 2, "returned_components": len(returned),
        "cold_reconstruction_without_source_or_reader": True, "cold_database_changes": 0,
        "a105_adequacy_established": False, "summary": summary}
    (directory / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: result[name] for name in ("scope", "numerical_results", "runtime_observations", "returned_components", "cold_reconstruction_without_source_or_reader")}, indent=2))


if __name__ == "__main__":
    directory = HERE / "primary_001"
    directory.mkdir(exist_ok=False)
    asyncio.run(execute(directory))
