"""Publish original source selections without losing multiline literal custody."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import LABEL, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository
from gene_annotation_episode.literature_reaction_source import populate_source
from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.state import Store
from test_literature_partner_integration import setup_case as partner_case
from test_literature_reaction_integration import setup_case as reaction_case, witness
from test_literature_reaction_storage import source
from test_reaction_source_witness_labels import rebind_sources


FIXTURES = Path(__file__).parent / "fixtures"


def test_original_a11037_endpoint_selection_publishes_unchanged_science(tmp_path):
    args = json.loads((FIXTURES / "literature_reaction/a11037-multiline-endpoint.json").read_text())
    raw = (FIXTURES / "a110_evaluation/declared-reaction-protocol.txt").read_bytes()
    with Store(tmp_path / "state") as store:
        store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")
        protocol = source(store, raw)
        rebind_sources(args, args["source_ref"], protocol["id"])
        original = deepcopy(args)
        context = BindingContext("original-a11037", "source-child", "literature",
            (("literature", "source-child"),), store.validate_scope(),
            {"version": "literature_assignment_v1", "source_refs": [protocol["id"]],
             "question_context_refs": [], "requested_reaction_components": ["reaction_comparison"]},
            {}, (protocol["id"],))
        repo = LiteratureReactionRepository(store, context.run_id)
        outcome = populate_source(repo, context, args, "original-source11")
        saved = repo.read(outcome["result"]["sheet_ref"])
        endpoint = store.get(saved["experimental_bindings"]["endpoint_ref"])
        selected = original["literals"]["endpoint"]
        assert (selected["start"], selected["end"]) == (468, 560)
        assert "\n" in selected["quote"]
        assert endpoint["anchor"] == {**{key: selected[key] for key in
            ("source_ref", "start", "end", "quote")}, "artifact_ref": protocol["artifact_ref"]}
        assert raw[468:560].decode() == endpoint["anchor"]["quote"]
        validate_schema(endpoint["label"], LABEL)
        assert saved["extraction"]["literals"]["endpoint"]["value"] == selected["quote"]
        cells = saved["sheet"]["cells"]
        assert cells["ratio_mean"]["value"] == .8
        assert cells["claim_mean_squared_error"]["value"] == pytest.approx(.05)
        assert cells["reaction_comparison"]["value"] == pytest.approx(1 / 3)
        assert cells["resource_capacity"]["value"] is None
        assert saved["experimental_bindings"]["experiment_ref"] is None
        assert "experiment_assessment" not in saved
        rows = repo.semantic_projection().project_cells([outcome["result"]["sheet_ref"]],
            permitted_record_refs=outcome["record_refs"], components=["reaction_comparison"])
        assert len(rows) == 1
        assert rows[0]["value"] == pytest.approx(1 / 3)
        assert args == original
        assert populate_source(repo, context, args, "original-source11") == outcome


@pytest.mark.parametrize("axis", ["A107", "A110"])
@pytest.mark.parametrize("kind", ["reference", "term", "context"])
@pytest.mark.parametrize("quote", [
    "A retained source literal\r\nwith original line wrapping.",
    "A retained source literal. " * 40,
    "  An existing\t literal  with α and preserved spacing.  ",
])
def test_literal_publication_retains_full_value_and_exact_anchor(tmp_path, axis, kind, quote):
    if axis == "A107":
        store, context, args = partner_case(tmp_path, case="matched")
        repository = LiteraturePartnerRepository
        literal, binding = {"reference": ("subject", "subject_ref"),
            "term": ("endpoint", "endpoint_ref"),
            "context": ("reference_condition", "reference_condition_ref")}[kind]
    else:
        store, context, args = reaction_case(tmp_path)
        repository = LiteratureReactionRepository
        literal, binding = {"reference": ("molecule", "assayed_subject_ref"),
            "term": ("endpoint", "endpoint_ref"),
            "context": ("condition", "condition_ref")}[kind]
    with store:
        repo = repository(store, context.run_id)
        baseline = repo.read(repo.populate(context, args, "baseline")["result"]["sheet_ref"])
        paper = source(store, quote)
        refs = (*context.received_record_refs, paper["id"])
        context = replace(context, received_record_refs=refs,
            assignment={**context.assignment, "source_refs": list(refs)})
        args["literals"][literal] = witness(paper["id"], quote.encode(), quote)
        original = deepcopy(args)
        outcome = repo.populate(context, args, "selected-literal")
        saved = repo.read(outcome["result"]["sheet_ref"])
        record = store.get(saved["experimental_bindings"][binding])
        assert record["record_type"] == kind
        assert saved["sheet"]["cells"] == baseline["sheet"]["cells"]
        assert saved["extraction"]["literals"][literal]["value"] == quote
        assert record["anchor"]["quote"] == quote
        assert (record["anchor"]["start"], record["anchor"]["end"]) == (0, len(quote.encode()))
        assert record["anchor"]["artifact_ref"] == paper["artifact_ref"]
        label = record["name" if kind == "context" else "label"]
        validate_schema(label, LABEL)
        if len(quote) <= LABEL["maxLength"]:
            assert " ".join(label.split()) in " ".join(quote.split())
        if "\n" not in quote and "\r" not in quote and len(quote) <= LABEL["maxLength"]:
            assert label == quote
        if axis == "A107" and kind == "context":
            role = store.get(record["related_refs"][0])
            assert role["anchor"] == record["anchor"]
            validate_schema(role["label"], LABEL)
        assert args == original
        assert repo.populate(context, args, "selected-literal") == outcome
