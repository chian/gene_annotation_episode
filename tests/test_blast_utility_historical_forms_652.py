"""Exact legacy utility fact contracts from the sealed check101 source.

Run only in bounded529 with the check096/check101 packages and check096's
immutable saved state explicitly selected as support. No native command is rerun.
"""
from __future__ import annotations

from contextlib import closing
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.blast_utility_historical_fact_schemas import (
    blast_utility_historical_fact_schemas, blast_utility_historical_schema_provenance,
)
from gene_annotation_episode.blast_utility_result_views import blast_utility_fact_sources
from gene_annotation_episode.communication import (
    ReportBoundaryError, _compile_closed_schema, validate_closed_schema, validate_form,
)
from gene_annotation_episode.native_blast_utility_returns import NativeBLASTUtilityReturns


ROOT = Path(__file__).resolve().parents[1]
CHECK101 = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check101_mask_conversion_workflow"
CHECK096 = ROOT / "verification/tool_graders_hmmer_map_verification_2026-10-28_529/check096_blast_utility_full_workflow"
CASES = ("utility-workflow634",)


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _historical_registration(check):
    package = check / "source_snapshot/gene_annotation_episode"
    name = "_" + check.name + "_utility_schema_source"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, package / "__init__.py",
            submodule_search_locations=[str(package)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    views = importlib.import_module(name + ".blast_utility_result_views")
    schemas = {source: row["report_schema"]
               for source, row in views.blast_utility_fact_sources().items()}
    pins = {str(Path(module.__file__).relative_to(package)): _digest(Path(module.__file__).read_bytes())
            for key, module in tuple(sys.modules.items())
            if key == name or key.startswith(name + ".")}
    return schemas, pins


def _saved_forms():
    forms = []
    for case in CASES:
        path = CHECK096 / f"temporary/pytest/{case}0/state/state.sqlite3"
        before = _digest(path.read_bytes())
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute("SELECT run_id,parent_episode_id,child_episode_id,decision_index,contract,form "
                    "FROM runtime_report_attempts WHERE form IS NOT NULL AND failure IS NULL "
                    "ORDER BY run_id,parent_episode_id,decision_index"):
                schema = json.loads(row["contract"])["measurements"]["schema"]
                if not any(node.get("x-source", "").startswith("execution.blast_utility_")
                           for node in schema["properties"].values()):
                    continue
                forms.append({"case": case, "state_sha256": before,
                    **{key: row[key] for key in ("run_id", "parent_episode_id", "child_episode_id", "decision_index")},
                    "schema": schema, "form": json.loads(row["form"])})
        assert _digest(path.read_bytes()) == before
    return forms


def _reader(db=None, run_id="historical_schema_check"):
    return NativeBLASTUtilityReturns(SimpleNamespace(store=SimpleNamespace(db=db),
        run_id=run_id, native_blast_utility_results=None))


def _form_schema(node, name="rows"):
    return {"type": "object", "additionalProperties": False,
            "properties": {name: deepcopy(node)}, "required": [name]}


@pytest.fixture(scope="module")
def registrations():
    registrations = {}
    for check in (CHECK096, CHECK101):
        schemas, pins = _historical_registration(check)
        registrations[check.name] = {"source_files_sha256": pins,
            "schemas_sha256": _digest(_canonical(schemas).encode()), "schemas": schemas}
    return registrations


@pytest.fixture(scope="module")
def saved_forms():
    forms = _saved_forms()
    assert len(forms) == 6  # Five results children and the scientific-parent return.
    return forms


def test_registry_contains_only_exact_pinned_prior_registrations(registrations):
    expected = {}
    for record in registrations.values():
        assert len(record["schemas"]) == 11
        for source, schema in record["schemas"].items():
            expected.setdefault(source, set()).add(_canonical(schema))
    registry = blast_utility_historical_fact_schemas()
    assert {source: {_canonical(schema) for schema in variants}
            for source, variants in registry.items()} == expected
    assert sum(map(len, registry.values())) == 14
    assert blast_utility_historical_schema_provenance() == {
        name: {key: value for key, value in record.items() if key != "schemas"}
        for name, record in registrations.items()}


@pytest.mark.parametrize("source", tuple(blast_utility_fact_sources()))
def test_every_historical_and_current_registration_passes_real_values_reader(source, registrations):
    nodes = [record["schemas"][source] for record in registrations.values()]
    nodes.append(blast_utility_fact_sources()[source]["report_schema"])
    for node in nodes:
        schema = _form_schema(node)
        assert _compile_closed_schema(schema) == schema
        assert _reader()._values({"rows": []}, schema) == {source: []}


@pytest.mark.parametrize("index", range(6))
def test_actual_unchanged_saved_parent_forms_reach_values_reader(index, registrations, saved_forms):
    item = saved_forms[index]
    before = _canonical(item)
    schemas = registrations[CHECK096.name]["schemas"]
    expected = {}
    for name, node in item["schema"]["properties"].items():
        source = node.get("x-source")
        if source in schemas:
            assert _canonical(node) == _canonical(schemas[source])
            expected[source] = item["form"][name]
    assert _reader()._values(item["form"], item["schema"]) == expected
    assert _canonical(item) == before


def test_saved_return_examples_remain_actual_measurements(saved_forms):
    built, extracted = saved_forms[:2]
    assert {row["field_name"]: row["value"] for row in built["form"]["database_fields"]} == {
        "database_sequence_count": 3, "database_residue_count": 33}
    assert len(extracted["form"]["sequences"]) == 2
    for row in extracted["form"]["sequences"]:
        assert row["native_reported_length"] == 12 and row["returned_symbol_count"] == 6
        assert row["sequences"] == {"normalized_sequence": "ATTGCA"}


def test_saved_forms_also_validate_under_current_registered_forms(saved_forms):
    current = blast_utility_fact_sources()
    reader = _reader()
    for item in saved_forms:
        # This is a separate current-request test; the historical request is
        # neither modified nor replaced for the saved-form replay above.
        schema = deepcopy(item["schema"])
        for name, node in schema["properties"].items():
            source = node.get("x-source")
            if source in current:
                schema["properties"][name] = current[source]["report_schema"]
        assert reader._values(item["form"], schema) == reader._values(item["form"], item["schema"])


def test_new_v2_subject_values_are_current_only():
    source = "execution.blast_utility_database_fields"
    # Explicit synthetic value tests schema compatibility, not a native measurement.
    rows = [{"source_ref": "source_synthetic", "subject": {"kind": "identifier_list", "occurrence_id": "ids"},
        "field_name": "identifier_list_count", "value": 1, "unit": "identifiers",
        "value_basis": "native_reported_exact", "native_lexeme": "1", "occurrence_id": "output",
        "line_number": 2, "json_pointer": None, "missing_reason": None}]
    current = _form_schema(blast_utility_fact_sources()[source]["report_schema"])
    assert _reader()._values({"rows": rows}, current) == {source: rows}
    for node in blast_utility_historical_fact_schemas()[source]:
        with pytest.raises(ValueError, match="returned_form_invalid"):
            _reader()._values({"rows": rows}, _form_schema(node))


def test_prior_failure_enums_keep_their_exact_different_populations(registrations):
    source = "execution.blast_utility_failures"
    row = {"source_ref": "source_synthetic", "stage": "capture", "code": "output_writer_not_closed",
           "occurrence_id": None, "record_key": None, "line_number": None, "native_returncode": None}
    old = _form_schema(registrations[CHECK096.name]["schemas"][source])
    later = _form_schema(registrations[CHECK101.name]["schemas"][source])
    with pytest.raises(ValueError, match="returned_form_invalid"):
        _reader()._values({"rows": [row]}, old)
    assert _reader()._values({"rows": [row]}, later) == {source: [row]}


@pytest.mark.parametrize("mutation", ("narrower", "expanded", "open", "scalar_type", "wrong_source", "unknown_source"))
def test_mutated_historical_registration_is_rejected_even_for_empty_values(mutation):
    source = "execution.blast_utility_failures"
    node = blast_utility_historical_fact_schemas()[source][0]
    if mutation == "narrower":
        node["items"]["properties"]["code"]["enum"].pop()
    elif mutation == "expanded":
        node["items"]["properties"]["code"]["enum"].append("invented_failure")
    elif mutation == "open":
        node["items"]["additionalProperties"] = True
    elif mutation == "scalar_type":
        node["items"]["additionalProperties"] = 0
    elif mutation == "wrong_source":
        node["x-source"] = "execution.blast_utility_checks"
    else:
        node["x-source"] = "execution.blast_utility_unregistered"
    schema = _form_schema(node)
    with pytest.raises(ReportBoundaryError):
        _compile_closed_schema(schema)
    with pytest.raises(ValueError, match="returned_form_invalid"):
        _reader()._values({"rows": []}, schema)


def test_numeric_schema_mutation_cannot_pass_by_python_scalar_equality():
    node = blast_utility_historical_fact_schemas()["execution.blast_utility_artifacts"][0]
    node["items"]["properties"]["ordinal"]["minimum"] = 0.0
    with pytest.raises(ReportBoundaryError, match="registered source"):
        _compile_closed_schema(_form_schema(node))


@pytest.mark.parametrize("container", ("object", "array", "root"))
def test_historical_sources_still_require_whole_top_level_fields(container):
    node = blast_utility_historical_fact_schemas()["execution.blast_utility_status"][0]
    schema = (node if container == "root" else _form_schema(_form_schema(node)) if container == "object"
              else _form_schema({"type": "array", "items": node}))
    with pytest.raises(ReportBoundaryError):
        _compile_closed_schema(schema)


def test_unregistered_generic_free_text_grammar_remains_closed():
    with pytest.raises(ReportBoundaryError, match="declared semantic type"):
        _compile_closed_schema(_form_schema({"type": "string"}))


def test_registry_and_provenance_copies_cannot_mutate_registration():
    initial = blast_utility_historical_fact_schemas()
    original = _canonical(initial)
    node = initial["execution.blast_utility_status"][0]
    schema = _form_schema(node)
    validate_closed_schema(schema)  # Populate the existing compilation cache.
    node["items"].clear()
    initial.clear()
    metadata = blast_utility_historical_schema_provenance()
    metadata.clear()
    assert _canonical(blast_utility_historical_fact_schemas()) == original
    assert blast_utility_historical_schema_provenance()
    schema["properties"]["rows"]["items"].clear()
    with pytest.raises(ReportBoundaryError):
        validate_closed_schema(schema)


@pytest.mark.parametrize("case", ("status_relation", "bool_measurement", "artifact_identity", "record_identity", "nonfinite"))
def test_historical_forms_keep_current_strict_value_and_relationship_validation(case, saved_forms):
    index = 1 if case == "record_identity" else 0
    item = deepcopy(saved_forms[index])
    form = item["form"]
    if case == "status_relation":
        form["status"][0]["writer_closed"] = False
    elif case == "bool_measurement":
        form["database_fields"][0]["value"] = True
    elif case == "artifact_identity":
        form["artifacts"][0]["artifact_ref"] = "artifact_" + "0" * 64
    elif case == "record_identity":
        form["sequences"][0]["record_key"] += "wrong"
    else:
        form["database_fields"][0]["value"] = float("nan")
    with pytest.raises(ValueError, match="returned_form_invalid"):
        _reader()._values(form, item["schema"])


def test_saved_source_reference_resolution_remains_required(saved_forms):
    item = saved_forms[0]
    source = item["form"]["status"][0]["source_ref"]
    with pytest.raises(ReportBoundaryError) as failure:
        validate_form(item["form"], item["schema"], lambda ref, namespace: ref != source)
    assert failure.value.diagnostic["code"] == "unknown_reference"


def test_different_sources_cannot_fill_duplicate_fact_fields(saved_forms):
    item = saved_forms[0]
    node = item["schema"]["properties"]["status"]
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"first": node, "second": node}, "required": ["first", "second"]}
    rows = deepcopy(item["form"]["status"])
    other = deepcopy(rows)
    other[0]["source_ref"] = "source_foreign"
    with pytest.raises(ValueError, match="conflicting_fields"):
        _reader()._values({"first": rows, "second": other}, schema)


def test_frozen_actual_child_facts_reject_foreign_source_without_rewriting_state(saved_forms):
    item = saved_forms[0]
    path = CHECK096 / "temporary/pytest/utility-workflow6340/state/state.sqlite3"
    before = _digest(path.read_bytes())
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as db:
        db.row_factory = sqlite3.Row
        reader = _reader(db, item["run_id"])
        context = reader.context(item["child_episode_id"])
        values = reader._values(item["form"], item["schema"])
        assert reader._frozen(context, values)
        values["execution.blast_utility_status"][0]["source_ref"] = "source_foreign"
        with pytest.raises(ValueError, match="frozen_facts_conflict"):
            reader._frozen(context, values)
    assert _digest(path.read_bytes()) == before


def test_compatibility_registration_needs_no_snapshot_or_files_at_runtime(monkeypatch):
    import builtins
    def forbidden(*args, **kwargs):
        raise AssertionError("historical schema runtime attempted file access")
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    for source, variants in blast_utility_historical_fact_schemas().items():
        for node in variants:
            assert _reader()._values({"rows": []}, _form_schema(node)) == {source: []}
