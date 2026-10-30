"""Independent synthetic contract/bound review against the captured runtime."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pin = args.pin.resolve()
    root = next(p for p in pin.parents if (p / "AGENTS.md").is_file())
    sys.path[:] = [str(pin), str(pin / "tests"), *[
        p for p in sys.path if p and Path(p).resolve() not in {root, root / "tests"}]]
    sys.dont_write_bytecode = True
    from gene_annotation_episode.communication import form_with_facts, validate_closed_schema, validate_form
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.literature_episodes import _population_catalog
    from gene_annotation_episode.literature_rate_storage import LiteratureRateRepository, rate_cells_schema, rate_source_cells_schema
    from gene_annotation_episode.state import Store
    from test_literature_rate_native_inputs import synthetic_case

    before = root / "verification/literature_reference_evidence_2026-10-25_001/native_rate_source_024/literature_rate_storage.py.before"
    name = "gene_annotation_episode._parent_review_rate_storage_before024"
    loader = importlib.machinery.SourceFileLoader(name, str(before))
    spec = importlib.util.spec_from_loader(name, loader)
    old = importlib.util.module_from_spec(spec)
    loader.exec_module(old)
    assert rate_cells_schema() == old.rate_cells_schema()
    legacy_count = len(rate_cells_schema()["items"]["required"])
    native_count = len(rate_source_cells_schema()["items"]["required"])
    assert (legacy_count, native_count) == (15, 24)
    schema = obj({"parent_selected_limits": rate_source_cells_schema()})
    validate_closed_schema(schema)
    baseline = json.loads((pin / "verification/literature_reference_evidence_2026-10-25_001/parent_population_information_023/population_catalog_before.json").read_bytes())
    catalog = _population_catalog()
    assert catalog[:-2] == baseline and len(catalog) == 16
    assert catalog[-2]["name"] == "literature.rate.source.populate"
    assert catalog[-1]["name"] == "literature.amount.populate"

    raw, selection = synthetic_case(reference="< approximately 12")
    selection["arms"]["reference"]["rate"]["number"]["number_start"] += len("< approximately ")
    with tempfile.TemporaryDirectory(prefix="unified030-parent-") as temporary:
        with Store(Path(temporary)) as store:
            store.create_problem(raw_sequence="ATGGCT", molecule="dna")
            artifact = store.artifact(raw, "text/plain")
            source = store.put("source", {"provider": "synthetic_parent_native_boundary", "accession": None,
                "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
                "version": None, "retrieved_at": None}, origin="caller")
            def bind(value):
                if isinstance(value, dict):
                    return {k: source["id"] if k == "source_ref" else bind(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [bind(v) for v in value]
                return value
            selection = bind(selection)
            context = BindingContext("parent-boundary-review", "child", "literature",
                (("literature", "synthetic"),), store.validate_scope(),
                {"version": "literature_assignment_v1", "question_context_refs": [],
                 "source_refs": [source["id"]]}, {}, (source["id"],))
            repo = LiteratureRateRepository(store, context.run_id).source_projection()
            outcome = repo.populate_native(context, selection, "source-selected")
            permitted = (*context.received_record_refs, *outcome["record_refs"])
            cells = repo.project_cells([outcome["result"]["sheet_ref"]],
                permitted_record_refs=permitted, components=("reference_rate",))
            row, = cells
            assert row["value"] is None and row["unavailable_reason"] == "censored_measurement"
            assert row["threshold"] == .012 and row["bound"] == "lt" and row["approximate"]
            assert row["unit"] == "umol/min/mg"
            form = form_with_facts({}, schema, {"literature_rate_source_cells": cells})
            admitted = validate_form(form, schema,
                lambda ref, namespace: ref in permitted and store.get(ref)["record_type"] == namespace)
            assert admitted["parent_selected_limits"] == cells
            parent = replace(context, episode_id="parent", role="annotation",
                path=(("annotation", "root"),), assignment={})
            repo.validate_returned_values(cells, permitted_record_refs=permitted)
            repo.receive_cells(parent, cells, "received")
            assert repo.received_cells(parent) == cells
            assert not store.list("observation") and not store.list("assessment")

    paths = {name: str(Path(module.__file__).resolve()) for name, module in sys.modules.items()
             if name.startswith(("gene_annotation_episode", "method_loop"))
             and getattr(module, "__file__", None)}
    assert all(Path(path).is_relative_to(pin) for path in paths.values())
    report = {"status": "passed", "legacy_schema_exact": True, "legacy_fields": legacy_count,
        "native_fields": native_count, "old_catalog_entries_exact": len(baseline),
        "new_operations": [row["name"] for row in catalog[-2:]], "amount_TASK_unwired": "gene_annotation_episode.literature_amount_prompt" not in sys.modules, "projected_and_admitted_censored_cell": row,
        "requested_subset_only": True, "model_calls": 0, "synthetic": True,
        "runtime_imports_under_pin": len(paths),
        "pin_manifest_sha256": hashlib.sha256((pin / "SOURCE_MANIFEST.json").read_bytes()).hexdigest(),
        "actual_model_numerical_execution_proved": False}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
