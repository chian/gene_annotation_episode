"""The actual A11035 subject literal cannot supply experiment identity."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_reaction_inputs import LITERAL_FIELDS, reaction_population_schema
from gene_annotation_episode.literature_reaction_source import populate_source, reaction_source_population_schema
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.state import Store
from test_literature_reaction_integration import setup_case, source, witness


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/literature_reaction/a11035-subject-as-experiment.json"


def actual_case(path):
    captured = json.loads(FIXTURE.read_text())
    store = Store(path)
    store.create_problem(raw_sequence="MAGRKLMN", molecule="protein")
    raw = (ROOT / captured["protocol_path"]).read_bytes()
    protocol = source(store, raw)
    dataset = source(store, (ROOT / captured["data_path"]).read_bytes(), parents=[protocol["id"]])
    args = {"source_ref": protocol["id"], "data_source_ref": dataset["id"],
        "source_kind": "synthetic_fixture", "literals": dict.fromkeys(LITERAL_FIELDS),
        "interpretation_witnesses": [witness(protocol["id"], raw, raw.decode())]}
    args["literals"]["molecule"] = witness(protocol["id"], raw,
        captured["subject_literal_record"]["label"])
    assignment = {"version": "literature_assignment_v1", "source_refs": [protocol["id"], dataset["id"]],
        "question_context_refs": [], "requested_reaction_components": ["ratio_mean", "resource_capacity"]}
    context = BindingContext("actual-a11035", "source-child", "literature",
        (("literature", "source-child"),), store.validate_scope(), assignment, {},
        (protocol["id"], dataset["id"]))
    return store, context, args, captured


def legacy_subject(store, context, args, captured):
    record = {key: value for key, value in captured["subject_literal_record"].items()
        if key not in {"id", "origin", "record_type"}}
    selected = args["literals"]["molecule"]
    record["source_ref"] = selected["source_ref"]
    record["anchor"] = {key: selected[key] for key in ("source_ref", "start", "end", "quote")}
    record["anchor"]["artifact_ref"] = store.get(selected["source_ref"])["artifact_ref"]
    record["accession"] = identity("reaction_literal", {"field": "molecule", **record["anchor"]})
    reference = store.put("reference", record, origin="tool", scope=plain(context.scope))["id"]
    return replace(context, received_record_refs=(*context.received_record_refs, reference)), reference


def test_actual_subject_literal_retains_unknown_biological_kind_without_becoming_an_assay(tmp_path):
    store, context, args, _ = actual_case(tmp_path)
    try:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "actual-original-components")
        saved = repo.read(outcome["result"]["sheet_ref"])
        subject = store.get(saved["experimental_bindings"]["assayed_subject_ref"])
        assert subject["reference_type"] == "literature_result"
        assert subject["label"] == "Synthetic subject S"
        assert subject["sequence_ref"] is subject["molecule"] is subject["length"] is None
        assert saved["experimental_bindings"]["experiment_ref"] is None
        assert saved["sheet"]["cells"]["ratio_mean"]["value"] == .8
        assert saved["sheet"]["cells"]["resource_capacity"]["value"] == 6
    finally:
        store.close()


def test_construct_and_experiment_literals_keep_distinct_roles(tmp_path):
    store, context, args = setup_case(tmp_path, primary=True)
    try:
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "actual-primary-literals")
        bindings = repo.read(outcome["result"]["sheet_ref"])["experimental_bindings"]
        assert store.get(bindings["construct_ref"])["reference_type"] == "construct"
        assert store.get(bindings["experiment_ref"])["reference_type"] == "assay"
        assert store.get(bindings["assayed_subject_ref"])["reference_type"] == "literature_result"
    finally:
        store.close()


@pytest.mark.parametrize("native", [False, True])
def test_actual_legacy_subject_handle_cannot_authorize_a_new_experiment_assessment(tmp_path, native):
    store, context, args, captured = actual_case(tmp_path)
    try:
        repo = LiteratureReactionRepository(store, context.run_id)
        original = repo.populate(context, args, "numbers-before-identity-request")
        saved = deepcopy(repo.read(original["result"]["sheet_ref"]))
        context, reference = legacy_subject(store, context, args, captured)
        context = replace(context, received_record_refs=(*context.received_record_refs, *original["record_refs"]))
        assessment = deepcopy(captured["source_population_arguments"]["experiment_assessment"])
        assessment["experiment_ref"] = reference
        if native:
            proposed = deepcopy(captured["source_population_arguments"])
            replacements = {captured["original_source_refs"]["protocol"]: args["source_ref"],
                captured["original_source_refs"]["data"]: args["data_source_ref"]}
            def received(value):
                if isinstance(value, dict):
                    return {key: received(child) for key, child in value.items()}
                if isinstance(value, list):
                    return [received(child) for child in value]
                return replacements.get(value, value) if isinstance(value, str) else value
            proposed = received(proposed)
            proposed["experiment_assessment"] = assessment
            execute = lambda: populate_source(repo, context, proposed, "invalid-native-identity")
        else:
            proposed = {**deepcopy(args), "experiment_assessment": assessment}
            execute = lambda: repo.populate(context, proposed, "invalid-retained-identity")
        with pytest.raises(ContractError, match="subject_or_construct_literal"):
            execute()
        assert repo.read(original["result"]["sheet_ref"]) == saved
        assert len(repo.current_assessments()) == 0
        assert store.db.execute("SELECT count(*) FROM literature_reaction_operations").fetchone()[0] == 1
        # Unknown experiment identity never blocks the existing numerical route.
        again = repo.populate(context, args, "numbers-with-identity-still-unknown")
        assert again["result"]["cells"] == original["result"]["cells"]
    finally:
        store.close()


def test_historical_accepted_identity_remains_readable_without_authorizing_new_work(tmp_path, monkeypatch):
    from gene_annotation_episode import literature_experiment_assessments as assessments
    store, context, args, captured = actual_case(tmp_path)
    try:
        context, reference = legacy_subject(store, context, args, captured)
        repo = LiteratureReactionRepository(store, context.run_id)
        proposed = {**deepcopy(args), "experiment_assessment": deepcopy(
            captured["source_population_arguments"]["experiment_assessment"])}
        proposed["experiment_assessment"]["experiment_ref"] = reference
        # Reproduce publication by the original producer, not a newly valid identity.
        with monkeypatch.context() as original:
            original.setattr(repo, "_authorize_assessment",
                lambda ctx, value: assessments.authorize_assessment(repo, ctx, value))
            old = repo.populate(context, proposed, "historical-operation")
        saved = deepcopy(repo.read(old["result"]["sheet_ref"]))
        assert repo.populate(context, proposed, "historical-operation") == old
        assert repo.read(old["result"]["sheet_ref"]) == saved
        with pytest.raises(ContractError, match="subject_or_construct_literal"):
            repo.populate(context, proposed, "new-operation")
        assert repo.read(old["result"]["sheet_ref"])["sheet"] == saved["sheet"]
    finally:
        store.close()


@pytest.mark.parametrize("schema", [reaction_population_schema(include_assessment=True),
    reaction_source_population_schema()])
def test_tool_contract_exposes_optional_assessment_and_distinct_subject_identity(schema):
    assert "experiment_assessment" not in schema["required"]
    description = schema["properties"]["experiment_assessment"].get("description", "")
    assert "optional" in description.lower()
    assert "subject" in description.lower() and "construct" in description.lower()
    assert "unknown" in description.lower()
