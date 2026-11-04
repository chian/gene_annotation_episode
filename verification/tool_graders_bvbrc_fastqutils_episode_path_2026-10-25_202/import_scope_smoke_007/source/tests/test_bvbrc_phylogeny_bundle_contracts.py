"""Closed selectors and finite semantic identities; no scientific rerun."""
from copy import deepcopy
import ast
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_phylogeny_bundle_contracts as c
from gene_annotation_episode.bvbrc_appservice_contracts import ContractValidationError


def selected(metric, **fields):
    spec = c.SCALAR_CATALOG[metric]
    examples = {"analysis_id": "a", "population_id": "population", "tree": {"analysis_id": "a", "slot_id": "tree", "tree_index": 0},
        "column_0based": 0, "row_index": 0, "row_a": 0, "row_b": 1, "node_index": 1, "node_a": 1, "node_b": 2,
        "input_binding_id": "input", "member_id": "member", "function_key": "F", "rank": "genus", "taxon_id": "T",
        "comparison_id": "comparison", "family_population_id": "families", "genome_population_id": "genomes",
        "family_id": "PF", "genome_id": "G", "feature_id": "fig|1.1.peg.1"}
    return {key: metric if key == "metric" else fields.get(key, examples[key]) for key in spec["selector_keys"]}


@pytest.mark.parametrize("metric", list(c.SCALAR_CATALOG))
def test_every_finite_scalar_exact_schema_and_no_extra_selector_language(metric):
    selection = selected(metric)
    form = c.requested_form_schema({"value": selection})
    assert c.selector_kind(selection) == c.SCALAR_CATALOG[metric]["kind"]
    assert c.validate_requested_form(form) == form
    assert form["properties"]["value"]["type"] == [c.SCALAR_CATALOG[metric]["kind"], "null"]
    with pytest.raises(ContractValidationError):
        c.selector_kind({**selection, "path": "/components/0"})
    with pytest.raises(ContractValidationError):
        c.selector_kind({**selection, "metric": "evaluate_expression"})


@pytest.mark.parametrize("kind", c.REFERENCE_KINDS)
def test_reference_codec_is_canonical_and_scoped(kind):
    ref = c.encode_reference(kind, "analysis/α%", "raw#tree/tree/1")
    assert c.decode_reference(ref, expected_kind=kind) == (kind, "analysis/α%", "raw#tree/tree/1")
    with pytest.raises(ContractValidationError):
        c.decode_reference(ref.replace("%2F", "%2f"))
    with pytest.raises(ContractValidationError):
        c.decode_reference(ref, expected_kind="tree" if kind != "tree" else "alignment")


def test_original_schema_is_exact_and_contracts_import_no_calculator():
    form = c.requested_form_schema({"n": selected("tree_tip_count"), "needs": {"metric": "missing_requirements"},
        "q": {"metric": "qualifications", "analysis_id": "a", "slot_id": None}})
    original = deepcopy(form)
    assert c.validate_requested_form(form) == original and form == original
    form["properties"]["n"]["description"] = "new context"
    with pytest.raises(ContractValidationError):
        c.validate_requested_form(form)
    tree = ast.parse(Path(c.__file__).read_text())
    assert all("calculator" not in (node.module or "") and "grader" not in (node.module or "") for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
    assert c.QUALIFICATION_CODES and all(type(s) is str for s in c.QUALIFICATION_CODES)
    assert not c.QUALIFICATION_CODES.intersection({"bvbrc_phylogeny_", "bvbrc_phylogeny_assembly_v1",
        "bvbrc_phylogeny_component_set_v1", "raxml_run_log", "raxml_runs", "supplemental_documents"})


def test_boolean_indices_and_cross_analysis_slots_are_rejected():
    for value in (True, -1, 1.5):
        with pytest.raises(ContractValidationError):
            c.selector_kind(selected("branch_length", node_index=value))
    with pytest.raises(ContractValidationError):
        c.selector_kind(selected("branch_length", tree={"analysis_id": "other", "slot_id": "tree", "tree_index": 0}))


@pytest.mark.parametrize("provider", ["gene_tree", "codon_tree"])
def test_public_parameter_schema_has_validator_shape_parity(provider):
    from test_bvbrc_phylogeny_bundle_resolution import fixture
    from gene_annotation_episode.bvbrc_appservice_contracts import _Validator
    parameters = fixture(provider)[3]
    schema = c.parameters_schema(provider=provider)
    assert _Validator(schema).is_valid(parameters)
    assert c.validate_parameters(parameters, provider=provider) == parameters
    mutations = []
    p = deepcopy(parameters); p["extra"] = True; mutations.append(p)
    p = deepcopy(parameters); p["analyses"][0]["analysis"]["raw_tree_id"]["tree_index"] = True; mutations.append(p)
    p = deepcopy(parameters); p["artifact_selection"][0]["reader"]["id_rule"] = "guess_header"; mutations.append(p)
    p = deepcopy(parameters); p["analyses"][0]["calculation_parameters"]["alignment_requests"][0]["pairs"] = [[0]]; mutations.append(p)
    p = deepcopy(parameters); p["analyses"][0]["population_plans"].append({"kind": "explicit", "population_type": "genomes", "population": {"population_id": "fake"}}); mutations.append(p)
    for mutated in mutations:
        assert not _Validator(schema).is_valid(mutated)
        with pytest.raises(ContractValidationError):
            c.validate_parameters(mutated, provider=provider)
