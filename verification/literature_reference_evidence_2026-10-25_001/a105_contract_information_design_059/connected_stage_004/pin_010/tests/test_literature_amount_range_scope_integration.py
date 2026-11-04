"""Controlled amount scope/typed-return checks, including saved027 facts."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_amount_inputs import LEXICAL_DEPENDENCY, validate_amount_extraction
from gene_annotation_episode.literature_amount_storage import LiteratureAmountRepository, amount_cells_schema
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_amount_inputs import fixture, meaning, witness
from test_literature_amount_storage import setup
from test_literature_amount_integration import binding_for
from test_runtime import FixtureController, ScriptedProvider


ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / "verification/literature_reference_evidence_2026-10-25_001"
SENTENCE = ("The mixture was divided between two flasks of 250 μl each and "
    "8.4 μM HFP and 8.8 μM IMP were added to each respective flask.")
COMPONENTS = ["numerator_amount", "denominator_amount", "amount_difference", "amount_ratio",
    "reciprocal_amount_ratio", "conditional_mass_denominator_factor", "amount_ratio_variance"]


def nominal_arguments(text=SENTENCE):
    args = fixture(text, first="8.4 μM", second="8.8 μM", n="8.4", d="8.8", nunit="μM", dunit="μM")[0]
    sentence = witness(text, SENTENCE)
    args.update(experiment=sentence, intended_change=sentence,
        comparison_kind=meaning("between_arm_nominal_molar_amount", text, SENTENCE),
        pair_relationship=meaning("supported", text, SENTENCE),
        stock_relationship=meaning("not_applicable", text, SENTENCE))
    for role, subject in (("numerator", "HFP"), ("denominator", "IMP")):
        row = args["quantities"][role]
        row.update(subject=witness(text, subject, occurrence=text[:text.index(SENTENCE)].count(subject)),
            reported_basis=sentence, amount_role=meaning("nominal_molecule_amount", text, SENTENCE),
            amount_kind=meaning("nominal", text, SENTENCE))
    return args


def retained_nominal_setup(path):
    """Mechanical replay of reviewed028 bytes/assignments, not a paper reader."""
    old = VERIFICATION / "amount_components_027/case025_replay_state_001/artifacts"
    hashes = {"original": "ccba0fb19356c840512ddcdc05924d00060fc4bcd52e31a79106932e7c6d649e",
        "text": "cdf6419babae49be1235b38b89370e16346766edf1483614cef3183b85898e12"}
    data = {key: (old / digest[:2] / digest).read_bytes() for key, digest in hashes.items()}
    assert {key: hashlib.sha256(raw).hexdigest() for key, raw in data.items()} == hashes
    text = data["text"].decode()
    assert data["text"][49807:49934].decode() == SENTENCE
    args = nominal_arguments(text)
    args["source_kind"] = "primary_source"
    # Fixture setup supplies scope/receipts only; scientific bytes below retain
    # original HTML plus its exact saved text projection in one source record.
    store, context, args = setup(path, text=text, arguments=args)
    original = store.artifact(data["original"], "text/html")
    projection = store.artifact(data["text"], "text/plain")
    source = store.put("source", {"provider": "retained_primary_PMC12051542_scope029",
        "accession": "PMC12051542", "uri": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/",
        "artifact_ref": original, "text_ref": projection, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")["id"]
    previous = args["source_ref"]
    def bind(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "source_ref" and child == previous:
                    value[key] = source
                elif key == "representation":
                    value[key] = "text"
                else:
                    bind(child)
        elif isinstance(value, list):
            for child in value:
                bind(child)
    bind(args)
    incubation = {**witness(text, "55 °C for 4.5 h"), "source_ref": source, "representation": "text"}
    for row in args["quantities"].values():
        row["condition"] = incubation
    context = replace(context, run_id="amount029-retained-nominal", received_record_refs=[source],
        assignment={**plain(context.assignment), "source_refs": [source], "requested_amount_components": COMPONENTS})
    return store, context, args, hashes


def test_selected_original_nominal_witnesses_deliver_saved_closed_cells(tmp_path, monkeypatch):
    store, context, args, _ = retained_nominal_setup(tmp_path)
    try:
        binding = binding_for(store, context)
        outcome = asyncio.run(binding.execute(context, "literature.amount.populate", args, "reviewed028-nominal"))
        assert outcome["status"] == "completed", outcome
        current = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        schema = obj({"amounts": amount_cells_schema()})
        form = form_with_facts({}, schema, binding.facts(current, {"committed_record_refs": [outcome["result"]["sheet_ref"]]}))
        binding.validate_report(current, form, schema)
        rows = {row["component"]: row for row in form["amounts"]}
        for component, value in [("numerator_amount", 8.4), ("denominator_amount", 8.8),
                ("amount_difference", -.4), ("amount_ratio", 21/22), ("reciprocal_amount_ratio", 22/21)]:
            assert rows[component]["value"] == pytest.approx(value)
        assert rows["conditional_mass_denominator_factor"]["unavailable_reason"] == "mass_factor_not_applicable"
        assert rows["amount_ratio_variance"]["unavailable_reason"] == "amount_covariance_unreported"
        saved = binding.services.literature_amount_repository().read(outcome["result"]["sheet_ref"])
        assert saved["extraction"]["lexical_dependency"] == LEXICAL_DEPENDENCY
        assert saved["selection"]["pair_relationship"]["witnesses"][0]["quote"] == SENTENCE
        assert saved["selection"]["experiment"]["start"] == 49807
        assert saved["selection"]["experiment"]["end"] == 49934
        parent = replace(current, role="annotation", episode_id="parent", assignment={}, path=(("annotation", "parent"),))
        binding.received_form_references(parent, form, schema, "closed-child")
        binding.received_form_references(parent, form, schema, "closed-child")
        assert binding.received_report_facts(parent)["literature_amount_cells"] == form["amounts"]
        def forbidden(*_args, **_kwargs):
            raise AssertionError("saved return must not parse or calculate again")
        monkeypatch.setattr("gene_annotation_episode.literature_amount_storage.read_amount_inputs", forbidden)
        monkeypatch.setattr("gene_annotation_episode.literature_amount_storage.populate_amount_components", forbidden)
        assert asyncio.run(binding.execute(context, "literature.amount.populate", args, "reviewed028-nominal")) == outcome
        assert not store.list("observation") and not store.list("assessment")
    finally:
        store.close()


def test_controlled_nominal_selected_action_returns_once_in_ordinary_episode_loop(tmp_path):
    store, context, args, _ = retained_nominal_setup(tmp_path / "state")
    controllers, received = [], []
    schema = obj({"amounts": amount_cells_schema()})
    child = {"selection": {"kind": "episode_child", "role": "literature",
        "assignment": plain(context.assignment), "goal": "Compare the reviewed nominal concentrations in the respective flasks.",
        "scope": plain(context.scope), "purpose": "Return the requested amount components with their original meanings.",
        "schema_json": json.dumps(schema), "initial_report_json": "{}"}, "report_update": {}}
    work = {"selection": {"kind": "tool", "tool": "literature.amount.populate", "arguments": args}, "report_update": {}}
    def receives(inputs):
        form, = inputs["child_reports"]
        rows = {row["component"]: row for row in form["amounts"]}
        assert rows["amount_ratio"]["value"] == pytest.approx(21/22)
        assert rows["amount_ratio"]["comparison_kind"] == "between_arm_nominal_molar_amount"
        assert rows["amount_ratio"]["variance_status"] == "unknown"
        assert rows["amount_ratio"]["numerator"]["amount_kind"] == "nominal"
        received.append(form)
        commit = {field: [] for field in store.reasoning_schema()["required"]}
        source = store.get(args["source_ref"])
        commit["source_subjects"] = [{"alias": "reviewed_nominal_comparison", "reference_type": "assay",
            "source_ref": args["source_ref"], "label": "HFP",
            "anchor": {"source_ref": args["source_ref"], "artifact_ref": source["text_ref"],
                "start": 49807, "end": 49934, "quote": SENTENCE}}]
        return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}
    def controller(path, initial):
        result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
        controllers.append(result)
        return result
    try:
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        asyncio.run(run_workflow(store, ToolRegistry(store), provider=ScriptedProvider([child, work, receives]),
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[args["source_ref"]]),), binding_definitions={"credit": scorer.as_record()}))
        assert len(received) == 1
        assert [row.scores for row in controllers] == [[0, 0], [0]]
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 3
        assert store.db.execute("SELECT count(*) FROM literature_amount_operations").fetchone()[0] == 1
        assert len(store.db.execute("SELECT form FROM runtime_forms").fetchall()) == 1
    finally:
        store.close()


def test_original027_saved_generation_reopens_without_source_read_or_reclassification(tmp_path, monkeypatch):
    original = VERIFICATION / "amount_components_027/case025_replay_state_001"
    copied = tmp_path / "old027-copy"
    before = {str(path.relative_to(original)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in original.rglob("*") if path.is_file()}
    shutil.copytree(original, copied)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("original027 facts must remain saved facts")
    monkeypatch.setattr("gene_annotation_episode.literature_amount_storage.read_amount_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_amount_storage.populate_amount_components", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs._number", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_rate_native_inputs._field_contexts", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_partner_source_fields._between_numeric_scope", forbidden)
    with Store(copied) as store:
        operation = store.db.execute("SELECT run_id,outcome FROM literature_amount_operations").fetchone()
        outcome = json.loads(operation["outcome"])
        ref = outcome["result"]["sheet_ref"]
        source = store.get(ref)
        expected = json.loads(store.get_artifact(source["artifact_ref"]))
        science = {store.get(ref)[key] for ref in expected["direct_input_source_refs"]
            for key in ("artifact_ref", "text_ref") if store.get(ref).get(key)}
        get_artifact = store.get_artifact
        def saved_only(reference):
            assert reference not in science, "do not open original scientific bytes"
            return get_artifact(reference)
        monkeypatch.setattr(store, "get_artifact", saved_only)
        repo = LiteratureAmountRepository(store, operation["run_id"])
        assert repo.read(ref) == expected
        assert expected["extraction"]["lexical_dependency"]["sha256_at_release"] == "264328313d32a8ed0315eb4a80388be775a8c7c2b51ad25041aad071a295dc67"
        assert repo.project_cells([ref], permitted_record_refs=[ref], components=["amount_ratio"])[0]["value"] == 5/7
        changed = deepcopy(expected["extraction"])
        changed["lexical_dependency"]["sha256_at_release"] = "0" * 64
        with pytest.raises(ValueError, match="amount_lexical_dependency_mismatch"):
            validate_amount_extraction(changed)
    after = {str(path.relative_to(original)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in original.rglob("*") if path.is_file()}
    assert before == after


def test_new_dependency_digests_match_actual_c7_fingerprinted_modules(tmp_path, monkeypatch):
    for name, field in (("literature_rate_native_inputs.py", "sha256_at_release"),
            ("literature_partner_source_fields.py", "scope_sha256_at_release")):
        assert hashlib.sha256((ROOT / "gene_annotation_episode" / name).read_bytes()).hexdigest() == LEXICAL_DEPENDENCY[field]
    store, context, _ = setup(tmp_path)
    try:
        binding = binding_for(store, context)
        before = binding.as_record()
        assert before["configuration"]["rate_population"] is True
        read_bytes = Path.read_bytes
        for name in ("literature_amount_inputs.py", "literature_rate_native_inputs.py", "literature_partner_source_fields.py"):
            def changed_bytes(path, selected=name):
                raw = read_bytes(path)
                return raw + b"\n# synthetic fingerprint contrast\n" if path.name == selected else raw
            with monkeypatch.context() as patch:
                patch.setattr(Path, "read_bytes", changed_bytes)
                assert binding.as_record()["implementation_sha256"] != before["implementation_sha256"]
        assert binding.as_record() == before
    finally:
        store.close()
