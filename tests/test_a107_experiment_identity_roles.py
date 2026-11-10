"""Partner subject/partner roles cannot supply experiment identity.

The archived retained/native publications predate this correction. Their exact
rows and source records remain readable without extraction or recalculation.
These are deterministic custody cases, not autonomous workflow evidence.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tarfile

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_partner_inputs import partner_population_schema
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository, partner_source_population_schema
from gene_annotation_episode.state import Store
from test_literature_partner_integration import setup_case
from test_literature_partner_native_integration import setup_case as native_case
from test_literature_partner_defined_integration import setup_case as defined_case
from test_literature_perturbation_assessments import identify


ARCHIVE = Path(__file__).parent / "fixtures/literature_partner/legacy_literal_roles_v2.tgz"
CASES = [("retained", setup_case, "matched"), ("native", native_case, "matched_native"),
    ("defined_native", defined_case, "nadh")]


def original_manifest():
    with tarfile.open(ARCHIVE) as stream:
        return json.load(stream.extractfile("manifest.json"))


@pytest.mark.parametrize("name,build,case", CASES)
def test_new_literal_roles_preserve_original_numbers_without_creating_experiments(tmp_path, name, build, case):
    store, context, args = build(tmp_path, case=case)
    try:
        repo = LiteraturePartnerRepository(store, context.run_id)
        outcome = repo.populate(context, args, "new-literal-roles")
        saved = repo.read(outcome["result"]["sheet_ref"])
        assert saved["literal_reference_roles_version"] == "partner_literal_reference_roles_v1"
        for field in ("subject_ref", "partner_ref"):
            reference = saved["experimental_bindings"][field]
            if reference is not None:
                role = store.get(reference)
                assert role["reference_type"] == "literature_result"
                assert role["sequence_ref"] is role["molecule"] is role["length"] is None
        experiment = saved["experimental_bindings"]["experiment_ref"]
        assert experiment is None or store.get(experiment)["reference_type"] == "assay"
        rows = repo.project_cells([outcome["result"]["sheet_ref"]], permitted_record_refs=outcome["record_refs"])
        original = next(row for row in original_manifest()["cases"] if row["directory"] == name)
        fields = ("component", "value", "unit", "status", "unavailable_reason", "conditional_on", "formula_code")
        assert [{key: row.get(key) for key in fields} for row in rows] == [
            {key: row.get(key) for key in fields} for row in original["components"]]
    finally:
        store.close()


@pytest.mark.parametrize("name", [row[0] for row in CASES])
def test_original_retained_and_native_roles_remain_exact_without_recalculation(tmp_path, monkeypatch, name):
    with tarfile.open(ARCHIVE) as stream:
        stream.extractall(tmp_path, filter="data")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    original = next(row for row in manifest["cases"] if row["directory"] == name)
    store = Store(tmp_path / name)
    try:
        repo = LiteraturePartnerRepository(store, original["run_id"])
        source = store.get(original["sheet_ref"])
        allowed = {source["artifact_ref"], source["request_ref"]}
        read = store.get_artifact
        def saved_only(reference):
            assert reference in allowed, "original-source bytes must not be reread"
            return read(reference)
        def forbidden(*args, **kwargs):
            raise AssertionError("historical roles must not be re-extracted or recalculated")
        monkeypatch.setattr(store, "get_artifact", saved_only)
        monkeypatch.setattr("gene_annotation_episode.literature_partner_storage.read_partner_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_partner_calculations.populate_partner_components", forbidden)
        store.db.execute("pragma query_only=ON")
        before = store.db.total_changes
        saved = repo.read(original["sheet_ref"])
        assert "literal_reference_roles_version" not in saved
        for field in ("subject_ref", "partner_ref"):
            reference = saved["experimental_bindings"][field]
            assert reference is None or store.get(reference)["reference_type"] == "assay"
        rows = repo.project_cells([original["sheet_ref"]], permitted_record_refs=[original["sheet_ref"]])
        assert rows == original["components"]
        assert store.db.total_changes == before
    finally:
        store.close()


@pytest.mark.parametrize("name,build,case", CASES)
@pytest.mark.parametrize("field", ["subject_ref", "partner_ref"])
def test_legacy_subject_or_partner_cannot_authorize_new_experiment_identity(tmp_path, name, build, case, field):
    store, context, args = build(tmp_path, case=case)
    try:
        repo = LiteraturePartnerRepository(store, context.run_id)
        original = repo.populate(context, args, "original-numbers")
        saved = deepcopy(repo.read(original["result"]["sheet_ref"]))
        role = store.get(saved["experimental_bindings"][field])
        legacy = {key: value for key, value in role.items() if key not in {"id", "origin", "record_type"}}
        legacy["reference_type"] = "assay"
        reference = store.put("reference", legacy, origin="tool", scope=plain(context.scope))["id"]
        context, proposed = identify(store, context, args)
        proposed["experiment_assessment"].update(experiment_ref=reference, experiment_type="partner_requirement")
        context = replace(context, received_record_refs=tuple(dict.fromkeys([
            *context.received_record_refs, *original["record_refs"], reference])))
        with pytest.raises(ContractError, match="subject_or_partner_literal"):
            repo.populate(context, proposed, "invalid-experiment-role")
        assert repo.read(original["result"]["sheet_ref"]) == saved
        assert not repo.current_assessments()
    finally:
        store.close()


@pytest.mark.parametrize("schema", [partner_population_schema(include_assessment=True),
    partner_source_population_schema()])
def test_actual_tool_contract_retains_numbers_with_unknown_experiment_identity(schema):
    assert "experiment_assessment" not in schema["required"]
    description = schema["properties"]["experiment_assessment"].get("description", "").lower()
    assert "optional" in description and "unknown" in description
    assert "subject" in description and "partner" in description


def test_original_condition_role_is_not_experiment_identity(tmp_path):
    with tarfile.open(ARCHIVE) as stream:
        stream.extractall(tmp_path, filter="data")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    original = next(row for row in manifest["cases"] if row["directory"] == "retained")
    store = Store(tmp_path / "retained")
    try:
        repo = LiteraturePartnerRepository(store, original["run_id"])
        saved = repo.read(original["sheet_ref"])
        source = store.get(original["sheet_ref"])
        request = json.loads(store.get_artifact(source["request_ref"]))
        known = tuple(row[0] for row in store.db.execute("SELECT id FROM records"))
        context = BindingContext(original["run_id"], "new-identity-question", "literature",
            (("literature", "new-identity-question"),), request["scope"],
            {"source_refs": saved["direct_input_source_refs"]}, {}, known)
        context, proposed = identify(store, context, request["arguments"])
        condition = store.get(saved["experimental_bindings"]["reference_condition_ref"])
        proposed["experiment_assessment"].update(experiment_type="partner_requirement",
            experiment_ref=condition["related_refs"][0])
        with pytest.raises(ContractError, match="condition_literal"):
            repo.populate(context, proposed, "condition-is-not-experiment")
        assert repo.read(original["sheet_ref"]) == saved
    finally:
        store.close()
