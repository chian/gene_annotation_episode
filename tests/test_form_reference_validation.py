"""Boundary-local reuse must not grant authority to a later form or context."""
from contextvars import copy_context
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError, validate_form
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


