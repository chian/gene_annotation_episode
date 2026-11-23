"""Selection over retained native D1 envelopes; synthetic corruptions labeled.

Native bytes are graded before projection. The projection purity test disables
all readers/calculators and IO after preparing saved envelopes. These tests do
not claim capture authentication or parent/child publication integration.
"""
from copy import deepcopy
import builtins
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.readers.profile_model_preparation.sequence_homology_evidence import hmmer_preparation_result_views as views
from gene_annotation_episode.episodic_workflow.episode_support.jobs.profile_model_preparation.sequence_homology_evidence import native_hmmer_preparation_worker as worker
from gene_annotation_episode.episodic_workflow.episode_support.forms.sequence_homology_evidence.communication import validate_form
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.domain import ContractError
from gene_annotation_episode.episodic_workflow.episode_support.forms.profile_model_preparation.sequence_homology_evidence.native_hmmer_preparation_contracts import PROGRAM_MODES
from gene_annotation_episode.episodic_workflow.episode_support.jobs.profile_model_preparation.sequence_homology_evidence.tests import test_native_hmmer_preparation_worker as native


MODES = [(program, mode) for program, modes in PROGRAM_MODES.items() for mode in modes]


def prepared(args):
    grading = worker.grade_hmmer_preparation(**args)
    occurrences = [{**item["occurrence"], "format": args["formats"][item["occurrence"]["occurrence_id"]],
        "relative_path": direction + "/" + role + "/" + str(item["occurrence"]["ordinal"])}
        for direction, group in (("input", args["inputs"]), ("output", args["outputs"]))
        for role, items in group.items() for item in items]
    return grading, occurrences


def selection(collection="calculations", *, quantities=None, checks=None, rows=None, artifacts=None):
    return {"version": "native_hmmer_preparation_result_selector", "acquisition": "complete_bound_bundle",
        "projection": None if collection is None else {"collection": collection,
            "rows": {"offset": 0, "limit": 100000} if rows is None else rows,
            "quantities": [] if quantities is None else quantities, "checks": [] if checks is None else checks},
        "artifacts": [] if artifacts is None else artifacts}


def project(grading, occurrences, selector):
    return views.project_preparation_result(grading, selector=selector, source_ref="source:original", occurrences=occurrences)


def all_selections(grading, occurrences):
    catalog = views.preparation_projection_catalog(**{k: grading["operation"][k] for k in ("program", "mode")})
    for collection, entry in catalog.items():
        yield collection, project(grading, occurrences, selection(collection, quantities=list(entry["quantities"]), checks=entry["checks"]))


@pytest.mark.parametrize("program,mode", MODES)
def test_direct_saved_mode_envelopes_cover_all_fixed_scalar_component_cells(program, mode):
    # D1's saved mode envelopes use actual270 corrected S1 operations, plus267.
    directory = native.ROOT / "gene_annotation_episode/episodic_workflow/episode_support/readers/profile_model_preparation/sequence_homology_evidence/tests/fixtures/hmmer_preparation_grading"
    manifest = json.loads((directory / "manifest.json").read_text())
    item = next(r for r in manifest if (r["program"], r["mode"]) == (program, mode))
    raw = (directory / item["grading"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item["grading_sha256"]
    grading = json.loads(raw)
    occurrences = [{**o, "format": grading["formats"][o["occurrence_id"]],
        "relative_path": o["direction"] + "/" + o["role"] + "/" + str(o["ordinal"])} for o in grading["sheet"]["artifact_occurrences"]]
    projected = {}
    for collection, result in all_selections(grading, occurrences):
        assert result["population"]["omitted_records"] == 0
        if collection == "calculations":
            projected = {r["record_key"]: {q["path"]: q for q in r["quantities"]} for r in result["rows"]}
    definitions, _ = views._definitions(program, mode)
    def cells(value, prefix=""):
        if type(value) is dict:
            if set(value) == {"value", "state", "unit", "inputs"}:
                yield prefix
            else:
                for key, child in value.items():
                    if key != "symbol_counts":  # A dynamic symbol table, retained like the other arrays.
                        yield from cells(child, (prefix + "." if prefix else "") + key)
    for row in grading["calculations"]["rows"]:
        kind = views._kind(row, views._FAMILIES[program], "calculations")
        assert set(cells(row)) <= set(definitions["calculations"][kind])
        key = views._key(row, views._FAMILIES[program], "calculations")
        for path in cells(row):
            original = row
            for part in path.split("."):
                original = original[part]
            assert projected[key][path] == {"path": path, **{field: original[field] for field in ("value", "state", "unit")}}


@pytest.mark.parametrize("mutation", ["unknown_path", "arbitrary_array", "duplicate_quantity", "bool_limit", "zero_limit", "bool_ordinal", "extra_field", "wrong_collection", "wrong_role", "duplicate_artifact"])
def test_selector_rejects_undeclared_or_ambiguous_requests(mutation):
    selector = selection(quantities=["decoded_model_count"])
    if mutation == "unknown_path": selector["projection"]["quantities"] = ["confidence"]
    elif mutation == "arbitrary_array": selector["projection"]["quantities"] = ["positions.0.match.cells.0.probability"]
    elif mutation == "duplicate_quantity": selector["projection"]["quantities"] *= 2
    elif mutation == "bool_limit": selector["projection"]["rows"]["limit"] = True
    elif mutation == "zero_limit": selector["projection"]["rows"]["limit"] = 0
    elif mutation == "bool_ordinal": selector["artifacts"] = [{"direction": "output", "role": "stdout", "ordinal": False}]
    elif mutation == "extra_field": selector["scores"] = []
    elif mutation == "wrong_collection": selector["projection"]["collection"] = "positions"
    elif mutation == "wrong_role": selector["artifacts"] = [{"direction": "input", "role": "queries", "ordinal": 0}]
    elif mutation == "duplicate_artifact": selector["artifacts"] = [{"direction": "output", "role": "stdout", "ordinal": 0}] * 2
    with pytest.raises(ContractError):
        views.validate_preparation_result_selector(selector, program="hmmconvert", mode="ascii")


def test_h1_repeated_check_names_keep_all_native_instances_and_outcomes():
    grading, occurrences = prepared(native.dna_statistics())
    # Synthetic contradiction demonstrates that projection does not collapse checks.
    extra = deepcopy(grading["calculations"]["checks"][0])
    extra["state"] = "fail"
    grading["calculations"]["checks"].append(extra)
    result = project(grading, occurrences, selection(checks=["native_rounding_agreement"]))
    checks = result["rows"][0]["checks"]
    assert len(checks) == 5
    assert [c["outcome"] for c in checks] == ["pass"] * 4 + ["fail"]
    assert all(len(c["occurrences"]) == 2 for c in checks)


def test_fact_schemas_and_catalogues_are_detached_and_closed():
    facts = views.preparation_fact_sources()
    assert set(facts) == {"execution_hmmer_preparation_" + k for k in ("rows", "artifacts", "population", "result_refs", "failures")}
    for source, descriptor in facts.items():
        validate_form({"facts": []}, {"type": "object", "additionalProperties": False,
            "properties": {"facts": descriptor["report_schema"]}, "required": ["facts"]}, lambda *_: True)
    facts["execution_hmmer_preparation_rows"]["report_schema"]["items"].clear()
    assert views.preparation_fact_sources()["execution_hmmer_preparation_rows"]["report_schema"]["items"]["type"] == "object"
    assert "preflight" in views.FAILURE_STAGES


