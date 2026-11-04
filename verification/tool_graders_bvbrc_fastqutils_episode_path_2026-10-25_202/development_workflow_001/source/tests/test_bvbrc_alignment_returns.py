"""Real numerical bundles and controlled saved custody/typed-return records.

Scientific inputs below are synthetic or retained native bytes as identified.
Publication envelopes are controlled fixtures. Separate Workflow tests own full
HTTP/publication integration; these checks do not claim live BV-BRC execution.
"""
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from types import SimpleNamespace

import pytest

from gene_annotation_episode import bvbrc_alignment_bundle_contracts as contracts
from gene_annotation_episode.bvbrc_alignment_returns import (
    BVBRCAlignmentReturns, FACT_SOURCES, IDENTIFIER_NAMESPACES,
    alignment_fact_sources, project_alignment_facts,
)
from gene_annotation_episode.bvbrc_appservice_publication import (
    AppServicePublications, DATA_PROVIDER, RESULT_VERSION,
)
from gene_annotation_episode.communication import (
    ReportBoundaryError, plain, validate_closed_schema, validate_form,
)
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.state import Store
from test_bvbrc_alignment_bundle_resolution import (
    basic_fixture, meta_native_fixture, msa_native_fixture, slot, xmfa_native_fixture,
)
from test_bvbrc_appservice_custody import SavedRecords
from test_bvbrc_phylogeny_returns import (
    ControlledPublications as PriorControlledPublications,
    ReturnFixture as PriorReturnFixture,
)


MEASUREMENTS = "bvbrc_alignment_measurements"


def fact_form(*sources):
    available = alignment_fact_sources()
    fields = {"selected_" + str(index): available[name]["report_schema"]
        for index, name in enumerate(sources)}
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


def content(value, name):
    raw = canonical(value).encode("utf-8")
    sha = hashlib.sha256(raw).hexdigest()
    return {"source_ref": "source_" + digest([name, sha])[:24], "artifact_field": "artifact_ref",
        "artifact_ref": "artifact_" + sha, "sha256": sha, "byte_count": len(raw)}


def projection(fixture=None, fields=None):
    f = basic_fixture() if fixture is None else fixture
    fields = ({"members": {"kind": "measurement", "analysis_id": "analysis", "request_id": "alignment",
        "metric": "member_count", "selector": {}},
        "gaps": {"kind": "measurement", "analysis_id": "analysis", "request_id": "alignment",
        "metric": "gap_fraction", "selector": {}}} if fields is None else fields)
    result = f.consume(fields)
    schema = contracts.requested_form_schema(fields, provider=f.provider)
    adapter = {key: deepcopy(result[key]) for key in (
        "adapter_id", "adapter_version", "status", "facts", "missing_requirements", "diagnostics")}
    for key in ("sheet", "components"):
        adapter[key + "_content"] = None if result[key] is None else content(result[key], key)
    selection = {"version": "bvbrc_appservice_result_selector_v1", "endpoint": "requested_projection",
        "requirements": [{"requirement_id": row["role"], "role": row["role"], "required": True,
            "declared_format": row["declared_format"], "producer_rule_evidence": None, "exact_object": None}
            for row in f.bundle["artifacts"]],
        "adapter": {"adapter_id": result["adapter_id"], "adapter_version": "1", "parameters": f.parameters},
        "requested_schema": schema, "supplied_metadata": [], "supplied_capabilities": []}
    bundle_content = content(f.bundle, "bundle")
    reference = bundle_content["source_ref"]
    body = {"version": RESULT_VERSION, "reference": reference, "source_ref": reference,
        "record_refs": [reference], "assignment": {"selector": selection},
        "publication": {"bundle_content": bundle_content, "result_record_refs": [reference], "adapter_result": adapter},
        "publication_inputs": {"selector": selection, "adapter": deepcopy(selection["adapter"]),
            "adapter_implementation_sha256": "0" * 64}}
    return body, result["sheet"], result["components"]


def projected(args, sources=FACT_SOURCES):
    return project_alignment_facts(args[0], requested_sources=sources, sheet_set=args[1], component_set=args[2])


def test_all_fourteen_source_schemas_are_closed_and_preserve_frozen_names():
    assert len(FACT_SOURCES) == 14
    assert "bvbrc_alignment_xmfa_measurements" in FACT_SOURCES
    assert "bvbrc_alignment_xmfa_alignment_measurements" not in FACT_SOURCES
    assert validate_closed_schema(fact_form(*FACT_SOURCES))
    facts = projected(projection())
    assert [row["value"]["value"] for row in facts[MEASUREMENTS]] == [2, 0]
    assert all(not values for name, values in facts.items() if name != MEASUREMENTS)
    assert all(set(row) == {"source_ref", "field", "value"} for row in facts[MEASUREMENTS])
    form = fact_form(MEASUREMENTS)
    assert validate_form({"selected_0": facts[MEASUREMENTS]}, form, lambda *_: True)


@pytest.mark.parametrize("format_,valid", [
    ("alignment_symbol", "-"), ("alignment_symbol", "*"), ("alignment_symbol", "#"),
    ("alignment_symbol", "a"), ("alignment_symbol", "?"),
    ("alignment_strand", "+"), ("alignment_strand", "-"), ("alignment_strand", "unknown")])
def test_literal_symbols_and_strands_do_not_masquerade_as_record_identifiers(format_, valid):
    schema = {"type": "object", "properties": {"literal": {"type": ["string", "null"], "format": format_}},
        "required": ["literal"], "additionalProperties": False}
    def no_reference(*args):
        pytest.fail("literal data triggered a record lookup")
    assert validate_form({"literal": valid}, schema, no_reference) == {"literal": valid}
    assert validate_form({"literal": None}, schema, no_reference) == {"literal": None}


@pytest.mark.parametrize("format_,bad", [
    ("alignment_symbol", ""), ("alignment_symbol", "AA"), ("alignment_symbol", " "),
    ("alignment_symbol", "\n"), ("alignment_symbol", "α"), ("alignment_symbol", "\x7f"),
    ("alignment_strand", "forward"), ("alignment_strand", "+-"), ("alignment_strand", "unknown context")])
def test_literal_formats_reject_prose_multiple_symbols_and_unknown_strands(format_, bad):
    schema = {"type": "object", "properties": {"literal": {"type": "string", "format": format_}},
        "required": ["literal"], "additionalProperties": False}
    with pytest.raises(ReportBoundaryError):
        validate_form({"literal": bad}, schema)


@pytest.mark.parametrize("provider", ["msa", "metacats"])
def test_requested_scalar_completion_keeps_unrelated_missing_information(provider):
    args = projection(basic_fixture(provider))
    body, _, _ = args
    adapter = body["publication"]["adapter_result"]
    assert adapter["status"] == "ok" and adapter["missing_requirements"]
    status, missing = AppServicePublications._requested_status(body["publication_inputs"],
        {"status": "ok", "missing_requirements": []}, body["publication"]["bundle_content"], adapter)
    assert status == "satisfied" and missing == adapter["missing_requirements"]
    required = {"requirement_id": "required-output", "kind": "output_bytes", "role": "requested-matrix",
        "source_refs": [], "reason_code": "output_bytes_missing"}
    status, missing = AppServicePublications._requested_status(body["publication_inputs"],
        {"status": "partial", "missing_requirements": [required]}, body["publication"]["bundle_content"], adapter)
    assert status == "partial" and required in missing
    adapter["status"] = "partial"
    assert AppServicePublications._requested_status(body["publication_inputs"],
        {"status": "ok", "missing_requirements": []}, body["publication"]["bundle_content"], adapter)[0] == "partial"


def test_older_adapter_missing_requirement_completion_semantics_are_unchanged():
    body, _, _ = projection()
    adapter = body["publication"]["adapter_result"]
    adapter["adapter_id"] = "bvbrc_homology"
    assert AppServicePublications._requested_status(body["publication_inputs"],
        {"status": "ok", "missing_requirements": []}, body["publication"]["bundle_content"], adapter)[0] == "partial"


@pytest.mark.parametrize("kind", ["native_msa", "native_metacats", "native_xmfa"])
def test_retained_native_requested_values_survive_the_closed_return_contract(kind):
    if kind == "native_msa":
        fixture = msa_native_fixture()
        fields = {"entropy": {"kind": "msa_sites", "analysis_id": "analysis", "request_id": "entropy", "columns_0based": [1]},
            "score": {"kind": "native_measurement", "analysis_id": "analysis", "table": slot("analysis", "frequency"),
                "row_index": 1, "field": {"kind": "score"}}}
    elif kind == "native_metacats":
        fixture = meta_native_fixture()
        request = next(r for r in fixture.plan()["calculation_parameters"]["requests"] if r["request_id"] == "biological:stats")
        test = {"category_id": fixture.plan()["analysis"]["category_ids"][0], "column_0based": 1,
            "kind": "pairwise", "group_ids": request["selected_pairs"][0]}
        fields = {"tests": {"kind": "statistical_tests", "analysis_id": "analysis", "request_id": "biological:stats", "tests": [test]},
            "native_p": {"kind": "native_measurement", "analysis_id": "analysis", "table": slot("analysis", "chisq"),
                "row_index": 0, "field": {"kind": "p_value"}}}
    else:
        fixture = xmfa_native_fixture(False)
        fields = {"metrics": {"kind": "xmfa_alignment_measurements", "analysis_id": "analysis", "request_id": "metrics",
            "measurements": [{"metric": "identical_canonical", "block_index": 0, "member_a": 1, "member_b": 3}]},
            "coordinates": {"kind": "xmfa_coordinates", "analysis_id": "analysis", "request_id": "coordinates",
                "cells": [{"block_index": 0, "record_index": 0, "column_0based": i} for i in (0, 28, 48)]}}
    args = projection(fixture, fields)
    facts = projected(args)
    schema = fact_form(*FACT_SOURCES)
    form = {key: facts[node["x-source"]] for key, node in schema["properties"].items()}
    assert validate_form(form, schema, lambda *_: True) == form
    if kind == "native_msa":
        assert facts["bvbrc_alignment_msa_sites"][0]["value"][0]["literal_entropy_bits"] == pytest.approx(.9182958340544896)
    elif kind == "native_metacats":
        assert facts["bvbrc_alignment_statistical_tests"][0]["value"][0]["df"] == 1
        assert facts[MEASUREMENTS][0]["value"]["method_ref"] is None
    else:
        row = facts["bvbrc_alignment_xmfa_measurements"][0]["value"][0]
        assert row["measurement"]["value"] == 39
        assert row["selection"] == {"metric": "identical_canonical", "block_index": 0,
            "member_a": 1, "member_b": 3, "column_0based": None, "symbol": None}


@pytest.mark.parametrize("alter", ["sheet_hash", "component_hash", "missing_sheet", "missing_components", "value",
    "unrequested_fact", "missing_fact", "selector", "adapter", "pin", "source", "nonfinite"])
def test_saved_binding_original_selection_and_requested_values_cannot_be_forged(alter):
    body, sheet, components = projection()
    adapter = body["publication"]["adapter_result"]
    if alter == "sheet_hash":
        adapter["sheet_content"]["sha256"] = "f" * 64
    elif alter == "component_hash":
        adapter["components_content"]["byte_count"] += 1
    elif alter == "missing_sheet":
        sheet = None
    elif alter == "missing_components":
        components = None
    elif alter == "value":
        adapter["facts"]["members"]["value"] = 100
    elif alter == "unrequested_fact":
        adapter["facts"]["extra"] = adapter["facts"]["members"]
    elif alter == "missing_fact":
        del adapter["facts"]["members"]
    elif alter == "selector":
        body["assignment"] = {"selector": deepcopy(body["assignment"]["selector"])}
        body["assignment"]["selector"]["endpoint"] = "requested_artifacts"
    elif alter == "adapter":
        adapter["adapter_id"] = "bvbrc_homology"
    elif alter == "pin":
        body["publication_inputs"]["adapter_implementation_sha256"] = None
    elif alter == "source":
        body["reference"] = "source_" + "b" * 24
    else:
        adapter["facts"]["members"]["value"] = float("nan")
    with pytest.raises(ValueError):
        projected((body, sheet, components))


def test_saved_return_does_no_io_parsing_or_scientific_recalculation(monkeypatch):
    args = projection(msa_native_fixture())
    expected = projected(args)
    from gene_annotation_episode import bvbrc_alignment_bundle_resolution as resolver
    from gene_annotation_episode import bvbrc_msa_grader as msa
    from gene_annotation_episode import bvbrc_metacats_grader as metacats
    def forbidden(*args, **kwargs):
        raise AssertionError("saved return repeated acquisition/parsing/calculation")
    with monkeypatch.context() as patch:
        for owner, name in ((builtins, "open"), (io, "open"), (Path, "read_text"), (Path, "read_bytes"),
            (socket, "create_connection"), (subprocess, "run"), (subprocess, "Popen"),
            (resolver, "resolve_bundle"), (resolver, "consume_bundle"),
            (msa, "calculate_msa"), (metacats, "calculate_metacats")):
            patch.setattr(owner, name, forbidden)
        assert projected(args) == expected
        assert projected(args, (MEASUREMENTS,)) == {MEASUREMENTS: expected[MEASUREMENTS]}


class ControlledPublications(PriorControlledPublications):
    def __init__(self, saved):
        super().__init__(saved)
        self.host = SimpleNamespace(custody=saved.custody)
        self.api = SimpleNamespace(_own_outcomes=self.outcomes)
        self.reads = []

    def outcomes(self, context):
        for reference in self.own_results(context):
            yield None, {'result': {'result_record_refs': [reference]}}

    def read(self, reference, scope, *, episode_id=None):
        self.reads.append(reference)
        return super().read(reference, scope, episode_id=episode_id)

    def _content(self, binding, origin, kind, stamp):
        # Controlled fixture only; actual publication authentication is tested
        # separately against saved Workflow records.
        assert kind in ('sheet', 'components')
        matching = [body for body in self.bodies.values()
            if body['publication']['origin'] == origin
            and body['publication_inputs']['current_snapshot']['retrieved_at'] == stamp
            and body['publication']['adapter_result'][kind + '_content'] == binding]
        assert len(matching) == 1
        return self.read_content_source(binding['source_ref'], {})

    def add(self, context, body, sheet, components, *, index=0):
        body = deepcopy(body)
        for name, value in (("sheet", sheet), ("components", components)):
            binding = None if value is None else self.saved.source(canonical(value).encode(), provider=DATA_PROVIDER)
            body["publication"]["adapter_result"][name + "_content"] = binding
            if binding is not None:
                self.sheets[binding["source_ref"]] = binding
        bundle = self.saved.source(canonical({"body": body, "episode": context.episode_id, "index": index}).encode(), provider=DATA_PROVIDER)
        reference = bundle["source_ref"]
        body.update(reference=reference, source_ref=reference, record_refs=[reference], run_id=context.run_id,
            episode_id=context.episode_id, scope=plain(context.scope), assignment=plain(context.assignment))
        body["publication"].update(bundle_content=bundle, result_record_refs=[reference])
        body['publication']['origin'] = {'operation_key': f'{context.run_id}:{context.episode_id}:{index}'}
        body['publication_inputs']['current_snapshot'] = {'retrieved_at': 'fixture:' + str(index)}
        self.bodies[reference] = body
        self.saved.own(context, reference, index, tool="api.bvbrc_appservice.download")
        return body


class ReturnFixture(PriorReturnFixture):
    def __init__(self, store):
        self.saved, self.store = SavedRecords(store), store
        self.publications = ControlledPublications(self.saved)
        self.api = SimpleNamespace(store=store, run_id=self.saved.run_id)
        self.api.appservice = SimpleNamespace(publications=self.publications, custody=self.saved.custody, resolve=self.resolve_source)
        self.host = BVBRCAlignmentReturns(self.api)

    def child(self, parent, role, body, *, index=0, sources=(MEASUREMENTS,), schema=None):
        assignment = {} if role != "results" else {"version": "execution_results_assignment_v1",
            "handoff_ref": "source_" + "a" * 24, "selector": body["publication_inputs"]["selector"]}
        return self.saved.child(parent, role, assignment, index, schema=fact_form(*sources) if schema is None else schema)


@pytest.fixture
def run(tmp_path):
    with Store(tmp_path / "state") as store:
        yield ReturnFixture(store)


def test_real_recorded_return_and_recursive_forwarding_preserve_only_requested_values(run):
    args = projection()
    parent = run.child(run.saved.root, "scientific_process", args[0])
    child = run.child(parent, "results", args[0])
    body = run.publications.add(child, *args)
    first, _, _, refs = run.admit(parent, child)
    second, _, _, _ = run.admit(run.saved.root, parent)
    assert first == second
    assert refs == [body["source_ref"]]
    rows = run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))[MEASUREMENTS]
    assert [row["value"]["value"] for row in rows] == [2, 0]
    for row in rows:
        assert run.host.resolve_received(run.saved.root, row["field"], "bvbrc_alignment_field")
        assert run.host.resolve_received(run.saved.root, row["value"]["population_ref"], "bvbrc_alignment_population")
    before = run.store.db.execute("SELECT COUNT(*) FROM runtime_actions").fetchone()[0]
    assert run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))[MEASUREMENTS] == rows
    assert run.store.db.execute("SELECT COUNT(*) FROM runtime_actions").fetchone()[0] == before


def test_latest_numerical_action_order_and_unreceived_values_are_distinct(run):
    args = projection()
    child = run.child(run.saved.root, "results", args[0])
    first = run.publications.add(child, *args, index=2)
    second_args = projection(basic_fixture(data=b">a\nAC\n>b\nAT\n>c\nAT\n"))
    second = run.publications.add(child, *second_args, index=10)
    facts = run.host.facts(child, fact_form(MEASUREMENTS))[MEASUREMENTS]
    assert {row["source_ref"] for row in facts} == {second["source_ref"]}
    assert facts[0]["value"]["value"] == 3
    assert run.host.received_facts(run.saved.root, fact_form(MEASUREMENTS))[MEASUREMENTS] == []
    assert first["source_ref"] != second["source_ref"]
    assert run.publications.reads == [second['source_ref']]


def test_wired_latest_reader_keeps_original_selector_check(run):
    args = projection()
    child = run.child(run.saved.root, 'results', args[0])
    body = run.publications.add(child, *args)
    body['publication_inputs']['selector'] = deepcopy(body['publication_inputs']['selector'])
    body['publication_inputs']['selector']['endpoint'] = 'requested_artifacts'
    with pytest.raises(ValueError, match='publication_owner_conflict'):
        run.host._latest(child)


def test_wired_latest_reader_detects_changed_newest_sheet_without_older_fallback(run):
    args = projection()
    child = run.child(run.saved.root, 'results', args[0])
    run.publications.add(child, *args, index=2)
    newer = projection(basic_fixture(data=b'>a\nAC\n>b\nAT\n>c\nAT\n'))
    latest = run.publications.add(child, *newer, index=10)
    binding = latest['publication']['adapter_result']['sheet_content']
    run.publications.sheets[binding['source_ref']] = {**binding, 'sha256': '0' * 64}
    with pytest.raises(AssertionError):
        run.host._latest(child)
    assert run.publications.reads == [latest['source_ref']]


def test_forged_closed_child_value_cannot_be_forwarded(run):
    args = projection()
    child = run.child(run.saved.root, "results", args[0])
    run.publications.add(child, *args)
    form, schema = run.candidate(child)
    form["selected_0"][0]["value"]["value"] = 999
    with pytest.raises(ValueError, match="returned_facts_conflict"):
        run.host.validate_received_report(child, form, schema)
