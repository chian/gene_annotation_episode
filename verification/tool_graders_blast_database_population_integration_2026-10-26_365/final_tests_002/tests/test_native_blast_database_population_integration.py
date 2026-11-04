"""U06 real selected-child path over explicitly synthetic original reports."""
import json
from pathlib import Path

import pytest

from blast_population_integration_fixtures import host, selection, frozen, values, save, STANDARD


@pytest.mark.parametrize("program,kind,fmt,layout", [
    (p, "sequence", "json15", "single") for p in ("blastn", "blastp", "blastx", "tblastn", "tblastx", "psiblast", "deltablast")
] + [("tblastn", "pssm", "json15", "single"), ("psiblast", "pssm", "json15", "single"),
     ("psiblast", "msa", "json15", "single"), ("blastp", "sequence", "tabular7", "single"),
     ("blastp", "sequence", "tabular6", "single"), ("psiblast", "sequence", "json15", "rounds"),
     ("blastp", "sequence", "json15", "queries")])
def test_selected_children_preserve_population_numbers_and_original_typed_returns(tmp_path, monkeypatch, program, kind, fmt, layout):
    h = host(tmp_path, monkeypatch, program, kind=kind, fmt=fmt, layout=layout)
    try:
        selected, payload = selection(h)
        child = h.results(selected)
        outcome = h.select(child, 0, "execution.results.collect")
        assert outcome["status"] == "completed", outcome
        body = outcome["result"]
        save(tmp_path / "actual-result.json", body)
        assert body["publication"]["acquisition_complete"], body["failures"]
        assert body["complete"] and body["publication"]["projection_complete"], body["failures"]
        returned, schema = h.returned(child)
        stem = "native_blast_standard_database" if program in STANDARD else "native_blast_database"
        facts = getattr(h.family, stem + "_returns").received_facts(h.root, schema)
        prefix = "execution_blast_standard_database_" if program in STANDARD else "execution_blast_database_"
        function = facts[prefix + "sequence_function_rows"]
        count = 2 if layout != "single" else 1
        assert len(function) == 2 * count
        for row in function:
            f = row["identity"]["function"]
            assert values(row) == pytest.approx(dict(function_mass=1 if f == "F" else .25,
                unadjusted_probability=.8 if f == "F" else .2,
                representation_adjusted_probability=2/7 if f == "F" else 5/7))
            assert row["publication_status"] == "source_only" and row["observation_ref"] is None
        populations = facts[prefix + "sequence_population_rows"]
        for row in populations:
            f = row["identity"]["function"]
            assert values(row) == pytest.approx(dict(database_sequence_count=100 if f == "F" else 10,
                database_total_sequence_count=110, database_fraction=10/11 if f == "F" else 1/11))
        module, original = frozen(h, child, body)
        request = original["request"]
        sheets = json.loads(h.store.get_artifact(original["grading"]["artifact_refs"]["sheets"]))
        if program in STANDARD:
            assert {r["detail_code"] for r in sheets["issues"]} == (set() if fmt == "tabular6" else {"native_path_semantic_identity_population_equality_unproven"})
            diagnostics = json.loads(h.store.get_artifact(original["grading"]["artifact_refs"]["diagnostics"]))
            assert diagnostics["metadata_issues"] == sheets["issues"]
            assert diagnostics["failures"] == []
        assert all(r["sheet"]["schema"] == "blast_sequence_database_result_sheet_v3" for r in sheets["sequence"])
        for row in sheets["sequence"]:
            scientific = row["sheet"]
            association = scientific["database_population_associations"][0]
            assert association["search_key"] == row["search_key"]
            assert scientific["search"]["normalized"]["search"]["database"] == (None if fmt == "tabular6" else association["selected_database"]["native_database_operand"])
            assert scientific["search_binding"]["database_identity"]["value"] == "curated-proteins"
            assert scientific["report_source"]["source_ref"]
        records = [r for v in sheets["prepared_inputs"]["metadata"] for r in v.get("population_source_records", [])]
        root = [r for r in records if r["artifact_ref"] == request["bundle_artifact_ref"]]
        assert root and all(r["size_bytes"] == request["bundle_capture"]["size_bytes"] for r in root)
        modules = {r["module"] for r in request["implementation"]["files"]}
        assert {"gene_annotation_episode.blast_database_population_associations", "gene_annotation_episode.native_blast_database_population_metadata"} <= modules
        if program not in STANDARD:
            assert sheets["iteration"]["schema"] == "blast_iteration_sheet_v3"
            assert all(r["database_population_associations"] for r in sheets["iteration"]["sequence_metadata"])
        assert len(list(h.workspace.rglob("synthetic-emitter-invoked"))) == 1
        actions = h.store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=?", (h.run_id, child.episode_id)).fetchall()
        assert len(actions) == 1
        save(tmp_path / "requested-selector.json", selected)
        save(tmp_path / "selected-v3-payload.json", payload)
        save(tmp_path / "original-parent-form.json", returned)
        save(tmp_path / "original-parent-schema.json", schema)
        save(tmp_path / "received-parent-facts.json", facts)
    finally:
        h.store.close()


@pytest.mark.parametrize("program", ["blastp", "psiblast"])
def test_unreceived_selected_population_source_rejected_before_child(tmp_path, monkeypatch, program):
    h = host(tmp_path, monkeypatch, program)
    try:
        selected, _ = selection(h, receive=False)
        with pytest.raises(ValueError, match="selected_input_not_received"):
            h.results(selected)
    finally:
        h.store.close()


@pytest.mark.parametrize("program,case", [("blastp", "empty"), ("psiblast", "empty"),
    ("blastp", "partial"), ("psiblast", "partial"), ("blastp", "missing_pointer"),
    ("psiblast", "missing_pointer"), ("blastp", "absent"), ("psiblast", "absent"),
    ("blastp", "conflicting"), ("blastp", "malformed"), ("blastp", "unknown"),
    ("blastp", "unresolved_sibling"), ("blastp", "old_v2"), ("blastp", "aliased_report")])
def test_zero_partial_and_unavailable_associations_keep_original_result(tmp_path, monkeypatch, program, case):
    h = host(tmp_path, monkeypatch, program, empty=case == "empty", nonzero=case == "partial")
    try:
        selected, _ = selection(h, failure=case)
        child = h.results(selected)
        body = h.select(child, 0, "execution.results.collect")["result"]
        assert body["publication"] is not None, body["failures"]
        rows = body["publication"]["rows_by_family"]
        if case == "empty":
            assert rows["sequence_function"] == []
            assert values(rows["search"][0])["reported_hit_count"] == 0
            assert body["publication"]["acquisition_complete"], body["failures"]
        else:
            for row in rows["sequence_function"]:
                f = row["identity"]["function"]
                assert values(row)["unadjusted_probability"] == (.8 if f == "F" else .2)
                if case != "partial": assert values(row)["representation_adjusted_probability"] is None
            assert len(rows["sequence_function"]) == 2
            if case == "partial":
                assert not body["complete"] and not body["publication"]["native_execution_successful"]
            if program == "blastp" and case != "partial":
                assert not body["complete"] and not body["publication"]["projection_complete"]
                _, original = frozen(h, child, body)
                diagnostics = json.loads(h.store.get_artifact(original["grading"]["artifact_refs"]["diagnostics"]))
                notes = [i for i, issue in enumerate(diagnostics["metadata_issues"])
                    if issue["detail_code"] == "native_path_semantic_identity_population_equality_unproven"]
                assert notes and all(any(f["pointer"] == f"/sheets/issues/{i}" for f in diagnostics["failures"]) for i in notes)
                if case == "aliased_report":
                    sheets = json.loads(h.store.get_artifact(original["grading"]["artifact_refs"]["calculations"]))
                    relation = sheets["sequence"][0]["components"]["components"]["database_sheet"]["database_population_relation"]
                    assert "blast_database_population_report_used_as_population_source" in relation["reason_codes"]
        h.returned(child)
        save(tmp_path / "qualified-result.json", body)
    finally:
        h.store.close()
