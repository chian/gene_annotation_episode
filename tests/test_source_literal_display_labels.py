"""Publish original source selections without losing multiline literal custody."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from gene_annotation_episode.domain import LABEL, validate_schema
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import LiteraturePartnerRepository
from gene_annotation_episode.episodic_workflow.root.literature_reaction_source import populate_source
from gene_annotation_episode.episodic_workflow.root.a110.literature_reaction_storage import LiteratureReactionRepository
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.a107.tests.test_literature_partner_integration import setup_case as partner_case
from gene_annotation_episode.episodic_workflow.root.a110.tests.test_literature_reaction_integration import setup_case as reaction_case, witness
from gene_annotation_episode.episodic_workflow.root.a110.tests.test_literature_reaction_storage import source
from test_reaction_source_witness_labels import rebind_sources


FIXTURES = Path(__file__).resolve().parents[1] / "gene_annotation_episode/episodic_workflow/root/a110/tests/fixtures"


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
