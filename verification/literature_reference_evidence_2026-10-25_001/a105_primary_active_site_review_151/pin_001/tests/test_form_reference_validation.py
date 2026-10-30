"""Boundary-local reuse must not grant authority to a later form or context."""
from contextvars import copy_context
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_form
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.form_reference_validation import (
    _binding_key, form_reference_validation, form_validation_value,
)


FORM = {"type": "object", "properties": {"refs": {"type": "array",
    "items": {"type": "string", "format": "reference", "x-reference-namespace": "source"}}},
    "required": ["refs"], "additionalProperties": False}


def test_repeated_references_share_only_one_form_and_return_detached_values():
    calls, produced = [], []
    def produce():
        value = {"allowed": ["a", "b"]}
        calls.append(1)
        produced.append(value)
        return value
    def resolve(value, namespace):
        facts = form_validation_value(("provider",), produce)
        assert namespace == "source" and facts == {"allowed": ["a", "b"]}
        answer = value in facts["allowed"]
        facts["allowed"].clear()
        produced[0]["allowed"].clear()
        return answer
    payload = {"refs": ["a", "b", "a"]}
    assert validate_form(payload, FORM, resolve) == payload
    assert len(calls) == 1
    assert validate_form(payload, FORM, resolve) == payload
    assert len(calls) == 2
    form_validation_value(("provider",), produce)
    form_validation_value(("provider",), produce)
    assert len(calls) == 4


def test_invalid_form_clears_frame_and_same_resolver_sees_changed_facts():
    allowed, calls = ["a"], []
    def produce():
        calls.append(1)
        return {"allowed": list(allowed)}
    def resolve(value, _):
        return value in form_validation_value(("provider",), produce)["allowed"]
    with pytest.raises(ReportBoundaryError) as error:
        validate_form({"refs": ["a", "b"]}, FORM, resolve)
    assert error.value.diagnostic == {"category": "report_format", "code": "unknown_reference",
                                     "field": "report.refs[1]"}
    allowed[:] = ["b"]
    assert validate_form({"refs": ["b"]}, FORM, resolve) == {"refs": ["b"]}
    with pytest.raises(ReportBoundaryError):
        validate_form({"refs": ["a"]}, FORM, resolve)
    assert len(calls) == 3


def test_nested_form_has_separate_frame_and_restores_outer_snapshot():
    calls = []
    def produce():
        calls.append(1)
        return {"generation": len(calls)}
    with form_reference_validation():
        assert form_validation_value(("same",), produce)["generation"] == 1
        with form_reference_validation():
            assert form_validation_value(("same",), produce)["generation"] == 2
        assert form_validation_value(("same",), produce)["generation"] == 1
        with pytest.raises(RuntimeError):
            with form_reference_validation():
                assert form_validation_value(("same",), produce)["generation"] == 3
                raise RuntimeError("nested")
        assert form_validation_value(("same",), produce)["generation"] == 1
    assert form_validation_value(("same",), produce)["generation"] == 4


def test_failed_factory_is_not_remembered_and_copied_context_expires():
    calls = []
    def produce():
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("original_failure")
        return {"generation": len(calls)}
    with form_reference_validation():
        retained_context = copy_context()
        with pytest.raises(ValueError, match="^original_failure$"):
            form_validation_value(("same",), produce)
        assert form_validation_value(("same",), produce)["generation"] == 2
        assert form_validation_value(("same",), produce)["generation"] == 2
    assert retained_context.run(form_validation_value, ("same",), produce)["generation"] == 3
    assert retained_context.run(form_validation_value, ("same",), produce)["generation"] == 4


@pytest.mark.parametrize("field,value", [
    ("run_id", "other-run"), ("episode_id", "other-episode"),
    ("path", (("results", "other"),)), ("scope", {"target": "other"}),
    ("assignment", {"selector": "other"}), ("request", {"report_contract": "other"}),
    ("received_record_refs", ("source_other",)),
])
def test_binding_key_distinguishes_each_boundary_operand(field, value):
    context = BindingContext("run", "episode", "results", (("results", "one"),),
        {"target": "one"}, {"selector": "one"}, {"report_contract": "one"}, ("source_one",))
    assert _binding_key(context) == _binding_key(replace(context))
    assert _binding_key(context) != _binding_key(replace(context, **{field: value}))


def test_provider_direction_and_schema_are_independent_and_duck_contexts_do_not_share():
    context = BindingContext("run", "episode", "results", (("results", "one"),), {}, {}, {})
    calls = []
    def produce():
        calls.append(1)
        return {"generation": len(calls)}
    first, second = object(), object()
    with form_reference_validation():
        for i, key in enumerate((
            (first, "own", _binding_key(context), "schema-a"),
            (second, "own", _binding_key(context), "schema-a"),
            (first, "received", _binding_key(context), "schema-a"),
            (first, "own", _binding_key(context), "schema-b"),
        ), 1):
            assert form_validation_value(key, produce)["generation"] == i
    unknown = SimpleNamespace()
    assert _binding_key(unknown) != _binding_key(unknown)


@pytest.mark.parametrize("fail", [False, True])
def test_frame_object_is_empty_and_expired_after_exit(fail):
    from gene_annotation_episode.form_reference_validation import _current
    retained = None
    try:
        with form_reference_validation():
            retained = _current.get()
            form_validation_value(("one",), lambda: {"values": [1]})
            assert retained.active and retained.values
            if fail:
                raise RuntimeError("original_failure")
    except RuntimeError as error:
        assert fail and str(error) == "original_failure"
    assert retained is not None and retained.active is False and retained.values == {}
    assert _current.get() is None


def test_binding_key_includes_role_with_its_valid_path():
    import json
    context = BindingContext("run", "episode", "results", (("results", "one"),), {}, {}, {})
    other = replace(context, role="monitor", path=(("monitor", "one"),))
    assert json.loads(_binding_key(context))[0]["role"] == "results"
    assert json.loads(_binding_key(other))[0]["role"] == "monitor"
    assert _binding_key(context) != _binding_key(other)


def test_public_genome_resolvers_reuse_facts_but_preserve_possession_and_semantics(tmp_path, monkeypatch):
    """Real selected-operation host and custody; controlled transport, no Workflow."""
    from collections import Counter
    from copy import deepcopy
    from gene_annotation_episode.state import Store
    from test_bvbrc_genome_alignment_host import GenomeDriver, MEASUREMENTS
    from test_genome_alignment_saved_structure import scientific_barrier

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected live transport")
    monkeypatch.setattr("socket.create_connection", forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    with Store(tmp_path / "state") as store:
        driver = GenomeDriver(store, tmp_path)
        driver.start()
        driver.acquire_manifest()
        body = driver.acquire_native()
        form, _, references = driver.admit_numeric()
        assert references == [body["source_ref"]]
        assert form["fact0"][0]["value"]["value"]["value"] == 690 / 693
        sheet, components = deepcopy(driver.sheet), deepcopy(driver.components)
        tables = ("runtime_actions", "runtime_observations", "runtime_report_attempts", "runtime_record_receipts")
        before = {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name)] for name in tables}
        calls = Counter()
        provider = driver.api.genome_alignment_returns
        own, received = provider.facts, provider.received_context
        def counted_own(context, schema):
            calls["own"] += 1
            return own(context, schema)
        def counted_received(context):
            calls["received"] += 1
            return received(context)
        monkeypatch.setattr(provider, "facts", counted_own)
        monkeypatch.setattr(provider, "received_context", counted_received)
        scientific_barrier(monkeypatch)
        for resolve in (driver.family.resolve, driver.api.resolve):
            previous = calls["own"]
            assert validate_form(form, driver.schema,
                lambda ref, ns: resolve(driver.context, ref, ns)) == form
            assert calls["own"] == previous + 1
        for resolve in (driver.family.resolve_received_reference, driver.api.resolve):
            previous = calls["received"]
            assert validate_form(form, driver.schema,
                lambda ref, ns: resolve(driver.parent, ref, ns)) == form
            assert calls["received"] == previous + 1
        field = form["fact0"][0]["field"]
        previous = calls["own"]
        for _ in range(2):
            assert driver.family.resolve(driver.context, field, "bvbrc_genome_alignment_field")
        assert calls["own"] == previous + 2
        forged = deepcopy(form)
        forged["fact0"][0]["value"]["value"]["value"] += 1
        with pytest.raises(ValueError, match="returned_facts_conflict"):
            driver.family.validate_received_report(driver.context, forged, driver.schema)
        with pytest.raises(ValueError, match="returned_facts_conflict"):
            driver.family.validate_received_report(driver.parent, forged, driver.schema)

        # Facts can be shared, but each repeated source still proves possession.
        possession = driver.custody.possession
        checks = []
        def checked(context, reference, **kwargs):
            if context == driver.context and reference == body["source_ref"]:
                checks.append(reference)
            return possession(context, reference, **kwargs)
        monkeypatch.setattr(driver.custody, "possession", checked)
        source_schema = deepcopy(FORM)
        source_schema["properties"]["refs"]["items"].pop("x-reference-namespace")
        per_reference = []
        def resolve_source(reference, namespace):
            previous = len(checks)
            value = provider.resolve_own(driver.context, reference, namespace)
            per_reference.append(len(checks) - previous)
            return value
        repeated = {"refs": [body["source_ref"]] * 3}
        assert validate_form(repeated, source_schema, resolve_source) == repeated
        assert per_reference[0] >= 1 and per_reference[1:] == [1, 1]
        assert driver.sheet == sheet and driver.components == components
        assert {name: [dict(row) for row in store.db.execute("SELECT * FROM " + name)] for name in tables} == before


def test_public_alignment_resolvers_reuse_only_the_current_form(tmp_path, monkeypatch):
    """Real return provider/custody with an explicitly controlled publication."""
    from collections import Counter
    from copy import deepcopy
    from gene_annotation_episode.state import Store
    from test_bvbrc_alignment_returns import ReturnFixture, MEASUREMENTS, projection

    with Store(tmp_path / "state") as store:
        run = ReturnFixture(store)
        args = projection()
        child = run.child(run.saved.root, "results", args[0])
        run.publications.add(child, *args)
        form, schema, _, _ = run.admit(run.saved.root, child)
        expected = deepcopy(form)
        assert [row["value"]["value"] for row in form["selected_0"]] == [2, 0]
        own, received = run.host.facts, run.host.received_context
        calls = Counter()
        def counted_own(context, requested):
            calls["own"] += 1
            return own(context, requested)
        def counted_received(context):
            calls["received"] += 1
            return received(context)
        monkeypatch.setattr(run.host, "facts", counted_own)
        monkeypatch.setattr(run.host, "received_context", counted_received)
        for _ in range(2):
            previous = calls["own"]
            assert validate_form(form, schema,
                lambda ref, ns: run.host.resolve_own(child, ref, ns)) == expected
            assert calls["own"] == previous + 1
            previous = calls["received"]
            assert validate_form(form, schema,
                lambda ref, ns: run.host.resolve_received(run.saved.root, ref, ns)) == expected
            assert calls["received"] == previous + 1
        field = form["selected_0"][0]["field"]
        previous = calls["own"]
        for _ in range(2):
            assert run.host.resolve_own(child, field, "bvbrc_alignment_field")
        assert calls["own"] == previous + 2
        form["selected_0"][0]["value"]["value"] += 1
        with pytest.raises(ValueError, match="returned_facts_conflict"):
            run.host.validate_received_report(child, form, schema)
        assert run.host.facts(child, schema)[MEASUREMENTS] == expected["selected_0"]
