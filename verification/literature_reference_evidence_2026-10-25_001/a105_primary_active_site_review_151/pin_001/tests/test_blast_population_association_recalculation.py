"""U06 saved calculation uses frozen facts; no parser or metadata reacquisition."""
from copy import deepcopy
import json
import builtins
from pathlib import Path
import socket
import subprocess
import shutil

import pytest

from gene_annotation_episode import native_blast_database_population_metadata as population
from gene_annotation_episode import native_blast_standard_database_result_worker as worker
from gene_annotation_episode.blast_database_grader import calculate_database_probabilities
import test_native_blast_database_population_metadata as fixtures
import test_native_blast_standard_database_metadata as base
import test_native_blast_standard_database_result_worker as calls
from test_blast_fasta_record_identity_integration import forbid_reparse, rows, values


def supplied_inputs():
    inputs, payload = fixtures.fixture()
    base.subject(inputs, "ACDEFGHI")
    base.add_metadata(inputs, payload, "sequence_database", "population")
    return inputs


def iteration_inputs():
    from test_blast_sequence_population_association import sequence_inputs
    from test_native_blast_database_result_worker import collection_for
    from test_blast_iteration_inputs import from_collection
    scientific = sequence_inputs("psiblast")
    collection = collection_for(scientific["search"])
    args = from_collection(collection)
    key = collection["searches"][0]["search_key"]
    for name in ("reference_metadata", "description_bindings", "sequence_identity_bindings", "database_profile"):
        args["sequence_metadata"][0][name] = deepcopy(scientific[name])
    args["report_sources"][0]["report_source"] = deepcopy(scientific["report_source"])
    args["search_bindings"] = [deepcopy(scientific["search_binding"])]
    args["query_bindings"][0]["query_binding"] = deepcopy(scientific["query_binding"])
    args["database_population_associations"] = [dict(search_key=key, associations=scientific["database_population_associations"])]
    return args


def test_iteration_v3_preserves_complete_mapping_and_per_target_context():
    from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
    from gene_annotation_episode.blast_iteration_calculators import calculate_blast_iteration_components
    args = iteration_inputs()
    key = args["collection"]["searches"][0]["search_key"]
    args["target_contexts"] = [dict(search_key=key, target_context=dict(taxid=10,
        lineage=[dict(rank="genus", taxid=10, name=None)], source="supplied:target", independent_of_search=True))]
    sheet = populate_blast_iteration_sheet(**args)
    assert sheet["schema"] == "blast_iteration_sheet_v3"
    assert sheet["target_contexts"] == args["target_contexts"]
    result = calculate_blast_iteration_components(sheet)
    assert result["schema"] == "blast_iteration_components_v3"
    components = result["searches"][0]["sequence_components"]["components"]
    assert components["function_weights"]["representation_adjusted_probabilities"] == pytest.approx({"F": 2/7, "G": 5/7})
    assert components["database_sheet"]["database_population_context"]["search_key"] == key
    assert components["database_sheet"]["database_population_context"]["associations"] == args["database_population_associations"][0]["associations"]


@pytest.mark.parametrize("change", ["duplicate", "unrelated_artifact", "unrelated_member", "unrelated_pointer"])
def test_iteration_mapping_rejects_duplicate_or_nonexact_search_keys(change):
    from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
    args = iteration_inputs()
    if change == "duplicate": args["database_population_associations"] *= 2
    else:
        row = deepcopy(args["database_population_associations"][0]); args["database_population_associations"] = [row]
        field, value = {"unrelated_artifact": ("artifact_key", "another-report"),
            "unrelated_member": ("member_ordinal", 2), "unrelated_pointer": ("search_pointer", "/another/round")}[change]
        row["search_key"][field] = value
    with pytest.raises(ValueError, match="blast_iteration_population_search_key_(duplicate|unresolved)"):
        populate_blast_iteration_sheet(**args)


def test_delta_domain_stage_never_receives_sequence_population_context(monkeypatch):
    from gene_annotation_episode.blast_iteration_inputs import populate_blast_iteration_sheet
    from gene_annotation_episode import blast_iteration_calculators as iteration
    from test_blast_iteration_inputs import make_inputs
    args = make_inputs(program="deltablast", hit_sets=[["D1"], ["A", "B"]], stages=["domain_database", "sequence_database"])
    key = args["sequence_metadata"][1]["search_key"]
    args["database_population_associations"] = [dict(search_key=deepcopy(key), associations=[])]
    args["report_sources"][1]["report_source"]["source_ref"] = "original:sequence-report"
    sheet = populate_blast_iteration_sheet(**args)
    assert sheet["target_contexts"] == []
    assert sheet["sequence_metadata"][0]["database_population_associations"] is None
    assert "source_ref" not in sheet["report_sources"][0]["report_source"]
    result = iteration.calculate_blast_iteration_components(sheet)
    domain, sequence = result["searches"]
    assert domain["sequence_components"] is None and domain["profile_components"] is not None
    assert sequence["profile_components"] is None
    assert sequence["sequence_components"]["components"]["database_sheet"]["schema"] == "blast_database_sheet_v3"


def test_original_capture_size_and_saved_temperature_only_worker_reuse(tmp_path, monkeypatch):
    inputs = supplied_inputs()
    request = calls.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = calls.invoke(request)
    assert manifest["status"] == "complete", diagnostics
    sheets = json.loads((Path(request["output_directory"]) / "sheets.json").read_bytes())
    roots = [r for v in sheets["prepared_inputs"]["metadata"] for r in v.get("population_source_records", [])
        if r["artifact_ref"] == request["bundle_artifact_ref"]]
    assert roots and all(r["size_bytes"] == request["bundle_capture"]["size_bytes"] for r in roots)
    assert request["bundle_capture"]["size_bytes"] != len(base.encoded(request["bundle"]))
    before = {p.name: p.read_bytes() for p in Path(request["output_directory"]).iterdir()}
    revised = calls.reuse(request, manifest, tmp_path / "generation-2")
    with monkeypatch.context() as blocked:
        forbid_reparse(blocked)
        def forbidden(*args, **kwargs): pytest.fail("saved reuse attempted new population metadata")
        for name in ("extract_native_blast_database_population_associations", "_retain_document_records", "_retain_preparation_records"):
            blocked.setattr(population, name, forbidden)
        reused, diagnostics = calls.invoke(revised)
    assert reused["status"] == "complete", diagnostics
    assert diagnostics["metadata_issues"] == sheets["issues"] and diagnostics["failures"] == []
    assert reused["input_identity"] == manifest["input_identity"]
    assert reused["input_interpretation_id"] == manifest["input_interpretation_id"]
    assert reused["calculation_id"] != manifest["calculation_id"]
    for row in [r for r in rows(revised) if r["family"] == "sequence_function"]:
        f = row["identity"]["function"]; cell = values(row)
        assert cell["unadjusted_probability"] == pytest.approx(2/3 if f == "F" else 1/3)
        assert cell["representation_adjusted_probability"] == pytest.approx(1/6 if f == "F" else 5/6)
    assert before == {p.name: p.read_bytes() for p in Path(request["output_directory"]).iterdir()}


@pytest.mark.parametrize("change", ["root_size", "root_value", "manifest_value", "manifest_removed", "report_source", "envelope_removed", "envelope_downgraded", "descriptor_origin"])
def test_worker_capture_rejects_consistent_saved_facts_without_original_authority(tmp_path, change):
    inputs = supplied_inputs()
    request = calls.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = calls.invoke(request)
    assert manifest["status"] != "failed", diagnostics
    sheets = json.loads((Path(request["output_directory"]) / "sheets.json").read_bytes())
    catalog, _, _ = worker._catalog(request, [])
    records = [r for v in sheets["prepared_inputs"]["metadata"] for r in v.get("population_source_records", [])]
    if change == "report_source": sheets["sequence"][0]["sheet"]["report_source"]["source_ref"] = "fabricated"
    elif change.startswith("envelope_"):
        if change == "envelope_removed":
            sheets["prepared_inputs"]["metadata"] = [v for v in sheets["prepared_inputs"]["metadata"] if v["schema_id"] != fixtures.VERSION]
        else:
            next(v for v in sheets["prepared_inputs"]["metadata"] if v["schema_id"] == fixtures.VERSION)["schema_id"] = "native_blast_database_sequence_metadata_v2"
    elif change == "descriptor_origin":
        next(v for v in sheets["prepared_inputs"]["metadata"] if v["schema_id"] == fixtures.VERSION)["descriptor"]["origin"] = "original_job_input"
    elif change == "manifest_removed":
        for v in sheets["prepared_inputs"]["metadata"]:
            if "population_source_records" in v:
                v["population_source_records"] = [r for r in v["population_source_records"] if r["artifact_ref"] != "artifact-manifest"]
        sheets["sequence"][0]["sheet"]["database_population_associations"][0]["selected_database"] = None
    else:
        record = next(r for r in records if r["artifact_ref"] == (request["bundle_artifact_ref"] if change.startswith("root") else "artifact-manifest") and not r["pointer"])
        if change == "root_size": record["size_bytes"] += 1
        elif change == "root_value": record["value"]["synthetic_forgery"] = True
        else: record["value"]["identity"]["value"] = "fabricated"
    from gene_annotation_episode.native_blast_database_result_worker import _population_capture_binding
    with pytest.raises(ValueError, match="blast_database_population_saved_relation_conflict"):
        _population_capture_binding(sheets, request, catalog)


@pytest.mark.parametrize("change", ["direct_removed", "downgraded", "iteration_removed", "source_changed", "profile_changed"])
def test_native_saved_handoff_cannot_drop_or_rewrite_selected_population(tmp_path, change):
    from gene_annotation_episode.native_blast_database_result_worker import _population_sheet_binding
    native, prepared, catalog = fixtures.native_six_fixture(tmp_path)
    sheets = native.populate(prepared, catalog)
    _population_sheet_binding(sheets)
    scientific = sheets["sequence"][0]["sheet"]
    if change == "direct_removed": sheets["sequence"] = []
    elif change == "downgraded":
        scientific["schema"] = "blast_sequence_database_result_sheet_v2"
        del scientific["database_population_associations"]
        scientific["report_source"].pop("source_ref")
    elif change == "iteration_removed": sheets["iteration"]["sequence_metadata"][0]["database_population_associations"] = None
    elif change == "source_changed": scientific["report_source"]["source_ref"] = "different-source"
    else: scientific["database_profile"]["release"] = "different-release"
    with pytest.raises(ValueError, match="blast_database_population_saved_relation_conflict"):
        _population_sheet_binding(sheets)


def test_population_note_resolution_is_exact_and_keeps_original_issues(tmp_path):
    inputs = supplied_inputs()
    request = calls.request_for(tmp_path, inputs=inputs)
    manifest, diagnostics = calls.invoke(request)
    assert manifest["status"] == "complete", diagnostics
    directory = Path(request["output_directory"])
    sheets, calculations = [json.loads((directory / (name + ".json")).read_bytes()) for name in ("sheets", "calculations")]
    issues = deepcopy(sheets["issues"])
    assert len(issues) == 1 and issues == diagnostics["metadata_issues"]
    assert worker._resolved_population_failures(issues, sheets, calculations) == worker._metadata_failures(issues)
    # Another exact query/round cannot inherit this relation, even when its
    # generic metadata failure code and original report are the same.
    second = deepcopy(issues[0]); second["search_key"]["report_index"] += 1
    unrelated = deepcopy(issues[0]); unrelated["detail_code"] = "query_subject_unresolved"
    mixed = [second, unrelated, issues[0]]
    assert worker._resolved_population_failures(mixed, sheets, calculations) == [worker._metadata_failures(mixed)[2]]
    for change in ("v1", "v2", "empty", "uncalculated", "missing", "key", "context", "unknown", "conflicting", "sibling"):
        saved, computed = deepcopy(sheets), deepcopy(calculations)
        scientific = saved["sequence"][0]["sheet"]
        result = computed["sequence"][0]
        database = result["components"]["components"]["database_sheet"]
        if change in {"v1", "v2"}: scientific["schema"] = "blast_sequence_database_result_sheet_" + change
        elif change == "empty": scientific["database_population_associations"] = []
        elif change == "uncalculated": result["components"] = None
        elif change == "missing": computed["sequence"] = []
        elif change == "key": result["search_key"]["member_ordinal"] = 7
        elif change == "context": database["database_population_context"]["associations"] = []
        else:
            relation = database["database_population_relation"]
            if change == "sibling": relation["association_results"][0]["status"] = "unavailable"
            else: relation["status"] = "unavailable" if change == "unknown" else "incompatible"
        assert worker._resolved_population_failures(issues, saved, computed) == [], change
    assert sheets["issues"] == issues


def test_resolved_note_keeps_unrelated_failure_and_exception_index(tmp_path, monkeypatch):
    inputs = supplied_inputs()
    request = calls.request_for(tmp_path, inputs=inputs)
    original = worker.calculators._calculate
    def synthetic_failure(*args, diagnostics, **kwargs):
        calculated = original(*args, diagnostics=diagnostics, **kwargs)
        diagnostics.append(dict(issue_index=len(calculated["issues"]), exception_type="synthetic.UnrelatedError", message="explicitly injected test failure"))
        calculated["issues"].append(worker.calculators._failure(pointer="/synthetic_unrelated_failure"))
        return calculated
    monkeypatch.setattr(worker.calculators, "_calculate", synthetic_failure)
    manifest, diagnostics = calls.invoke(request)
    assert manifest["status"] == "partial" and manifest["failures"] == diagnostics["failures"]
    assert len(manifest["failures"]) == 1 and manifest["failures"][0]["pointer"] == "/synthetic_unrelated_failure"
    assert diagnostics["exceptions"][0]["failure_index"] == 0
    assert diagnostics["metadata_issues"][0]["detail_code"] == "native_path_semantic_identity_population_equality_unproven"


@pytest.mark.parametrize("program", ["blastp", "psiblast", "deltablast"])
def test_actual_quality_return_and_saved_reuse_keep_original_source_facts(tmp_path, monkeypatch, program):
    from blast_population_integration_fixtures import host, selection, frozen, saved_reuse, save
    from test_blast_fasta_record_identity_integration import assert_quality
    from test_native_blast_database_result_worker import reuse_request
    h = host(tmp_path, monkeypatch, program, supplied_quality=True)
    try:
        selected, _ = selection(h)
        selected["projections"].append(dict(family="sequence_record_quality", rows=dict(offset=0, limit=10),
            metrics=["completeness_fraction", "contamination_fraction", "contig_count", "contig_n50", "total_sequence_length"], booleans=[]))
        child = h.results(selected)
        body = h.select(child, 0, "execution.results.collect")["result"]
        assert body["complete"], body["failures"]
        returned, schema = h.returned(child)
        standard = program == "blastp"
        stem = "native_blast_standard_database" if standard else "native_blast_database"
        facts = getattr(h.family, stem + "_returns").received_facts(h.root, schema)
        prefix = "execution_blast_standard_database_" if standard else "execution_blast_database_"
        published = facts[prefix + "sequence_record_quality_rows"]
        assert_quality(published, same=False)
        module, original = frozen(h, child, body)
        request, manifest = original["request"], original["manifest"]
        old_directory = Path(request["output_directory"])
        before = {p.name: p.read_bytes() for p in old_directory.iterdir()}
        calculations = json.loads(before["calculations.json"])
        components = (calculations["sequence"][0]["components"] if standard else
            calculations["iteration"]["searches"][0]["sequence_components"])
        database = components["components"]["database_sheet"]
        def forbidden(*args, **kwargs):
            pytest.fail("saved public calculation attempted file, network, execution or population")
        with monkeypatch.context() as blocked:
            forbid_reparse(blocked)
            for target, name in [(builtins, "open"), (Path, "open"), (Path, "read_bytes"), (Path, "read_text"),
                    (population, "extract_native_blast_database_population_associations")]:
                blocked.setattr(target, name, forbidden)
            calculated = calculate_database_probabilities(database, model={"temperature_bits": 2})
        assert calculated["unadjusted_probabilities"] == pytest.approx({"F": 2/3, "G": 1/3})
        assert calculated["representation_adjusted_probabilities"] == pytest.approx({"F": 1/6, "G": 5/6})
        revised = calls.reuse(request, manifest, tmp_path / "saved-T2") if standard else reuse_request(request, manifest)
        reused = saved_reuse(tmp_path, revised, standard=standard)
        assert reused["status"] == "complete", reused["failures"]
        assert reused["input_identity"] == manifest["input_identity"]
        assert reused["input_interpretation_id"] == manifest["input_interpretation_id"]
        assert reused["calculation_id"] != manifest["calculation_id"]
        new_rows = rows(revised)
        assert_quality(new_rows, same=False)
        for row in [r for r in new_rows if r["family"] == "sequence_function"]:
            f, cells = row["identity"]["function"], values(row)
            assert cells["unadjusted_probability"] == pytest.approx(2/3 if f == "F" else 1/3)
            assert cells["representation_adjusted_probability"] == pytest.approx(1/6 if f == "F" else 5/6)
        assert before == {p.name: p.read_bytes() for p in old_directory.iterdir()}
        assert json.loads(before["sheets.json"]) == json.loads((Path(revised["output_directory"]) / "sheets.json").read_bytes())
        # Exercise the request/envelope boundary directly for both real routes,
        # then attempt a consistently re-sealed erased interpretation via reuse.
        from gene_annotation_episode import native_blast_database_result_worker as native_worker
        actual_worker = worker if standard else native_worker
        catalog = actual_worker._catalog(request, [])[0]
        original_sheets = json.loads(before["sheets.json"])
        for change in ("removed", "downgraded"):
            changed = deepcopy(original_sheets)
            if change == "removed":
                changed["prepared_inputs"]["metadata"] = [v for v in changed["prepared_inputs"]["metadata"] if v["schema_id"] != fixtures.VERSION]
            else:
                next(v for v in changed["prepared_inputs"]["metadata"] if v["schema_id"] == fixtures.VERSION)["schema_id"] = "native_blast_database_sequence_metadata_v2"
            with pytest.raises(ValueError, match="blast_database_population_saved_relation_conflict"):
                native_worker._population_capture_binding(changed, request, catalog)
        forged = tmp_path / "explicitly-forged-saved-generation"
        shutil.copytree(old_directory, forged)
        erased = deepcopy(original_sheets)
        erased["prepared_inputs"]["metadata"] = [v for v in erased["prepared_inputs"]["metadata"] if v["schema_id"] != fixtures.VERSION]
        for row in erased["sequence"]:
            scientific = row["sheet"]
            scientific["schema"] = "blast_sequence_database_result_sheet_v2"
            scientific.pop("database_population_associations")
            scientific["report_source"].pop("source_ref")
        if not standard:
            erased["iteration"]["schema"] = "blast_iteration_sheet_v2"
            for row in erased["iteration"]["sequence_metadata"]: row.pop("database_population_associations")
            for row in erased["iteration"]["report_sources"]: row["report_source"].pop("source_ref")
        bad_manifest = deepcopy(manifest)
        for role, value in (("sheets", erased), ("inputs", erased["prepared_inputs"])):
            raw = base.encoded(value)
            (forged / (role + ".json")).write_bytes(raw)
            record = next(a for a in bad_manifest["artifacts"] if a["role"] == role)
            record.update(sha256=base.sha(raw), size_bytes=len(raw))
        raw = base.encoded(bad_manifest)
        (forged / "worker-manifest.json").write_bytes(raw)
        rejected = deepcopy(revised)
        rejected["output_directory"] = str(tmp_path / "rejected-generation")
        rejected["reuse"] = dict(manifest_path=str(forged / "worker-manifest.json"), manifest_sha256=base.sha(raw),
            manifest_size_bytes=len(raw), collection_path=str(forged / "collection.json"), sheets_path=str(forged / "sheets.json"))
        failed = saved_reuse(tmp_path / "rejected-reuse", rejected, standard=standard, expect_failed=True)
        assert failed["failures"]
        changed_origin = deepcopy(revised)
        changed_origin["output_directory"] = str(tmp_path / "rejected-origin-generation")
        next(d for d in changed_origin["metadata_descriptors"] if d["schema_id"] == fixtures.VERSION)["origin"] = "original_job_input"
        failed_origin = saved_reuse(tmp_path / "rejected-origin-reuse", changed_origin, standard=standard, expect_failed=True)
        assert any("frozen_artifact_changed" in f["code"] for f in failed_origin["failures"])
        assert before == {p.name: p.read_bytes() for p in old_directory.iterdir()}
        assert len(list(h.workspace.rglob("synthetic-emitter-invoked"))) == 1
        actions = h.store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=?", (h.run_id, child.episode_id)).fetchall()
        assert len(actions) == 1
        validate = getattr(module, "validate_standard_blast_database_publication" if standard else "validate_native_blast_database_publication")
        with monkeypatch.context() as blocked:
            blocked.setattr(module, "run_local_job", forbidden)
            assert validate(h.store, context=child, publication=body["publication"]) == body["publication"]
        assert getattr(h.family, stem + "_returns").received_facts(h.root, schema)[prefix + "sequence_record_quality_rows"] == published
        save(tmp_path / "original-parent-form.json", returned)
        save(tmp_path / "received-parent-facts.json", facts)
        save(tmp_path / "saved-calculation-T2.json", calculated)
        save(tmp_path / "saved-T2-manifest.json", reused)
    finally:
        h.store.close()
