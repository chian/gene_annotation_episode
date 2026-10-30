"""Selected delivery of retained native fixtures; no episode authority claim."""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_protein_structure_acquisition import retained_protein_structure_file
from gene_annotation_episode.protein_structure_projection_publication import publish_protein_structure_projection
from gene_annotation_episode.protein_structure_result_views import project_protein_structure_results
from gene_annotation_episode.state import Store


HELPERS = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
FIXTURES = Path(__file__).resolve().parents[1] / "verification/tool_graders_protein_structure_result_worker_2026-10-27_393/fixtures"


def forbidden(*args, **kwargs):
    pytest.fail("projection publication attempted scientific execution or unselected Store access")


@pytest.fixture(autouse=True)
def no_scientific_execution(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    for module, names in (
        ("protein_structure_calculations", ("calculate_protein_structure_components", "fit_ca_transform")),
        ("protein_structure_formats", ("parse_pdb_structure", "parse_mmcif_structure")),
        ("protein_structure_sequences", ("extract_structure_sequence",)),
        ("protein_structure_sheet", ("build_protein_structure_sheet", "parse_native_protein_comparison")),
    ):
        loaded = import_module("gene_annotation_episode." + module)
        for name in names:
            monkeypatch.setattr(loaded, name, forbidden)


def selected(kind="comparison", delivery="values", window=None):
    name = {"comparison": "held_out", "extraction": "extract", "inspection": "inspect",
            "unavailable": "extract_unavailable"}[kind]
    native = json.loads((FIXTURES / (name + ".json")).read_bytes())
    selection = {"projection_id": "parent_selected", "window": window, "delivery_kind": delivery}
    calculation = None
    if kind == "comparison":
        components = native["sheet"]["native_baseline"]
        value = {"kind": kind, "sheet": native["sheet"], "components": components}
        selection.update(family="comparison_summary", members={"kind": "comparison"},
                         fields=["evaluation_rmsd", "evaluation_used_count"])
        calculation = {"calculation_id": components["calculation_id"],
            "input_numerical_sha256": components["input_numerical_sha256"],
            "components_file": HELPERS.identity(canonical(components).encode(), "protein_structure_components_v1")}
    elif kind == "inspection":
        value = {"kind": kind, "inventory": native["inventory"]}
        selection.update(family="structure_inventory", members={"kind": "all_inventory_rows"},
                         fields=["model", "chain", "position", "native_metadata"])
    else:
        value = {"kind": "extraction", "sequence": native["sequence"], "metadata": native["metadata"],
                 "descriptor": None if kind == "unavailable" else HELPERS.sequence_descriptor(native["sequence"])}
        selection.update(family="extracted_sequence", members={"kind": "extracted_sequence",
            "residue_positions": {"kind": "all"}},
            fields=["sequence_length", "alignment_sequence"])
    return project_protein_structure_results(value, selection=[selection])[0], calculation


def publish(store, rows, calculation, custody=None):
    return publish_protein_structure_projection(store, rows=rows,
        custody=HELPERS.synthetic_custody() if custody is None else custody, calculation=calculation)


@pytest.mark.parametrize("kind", ["comparison", "extraction", "inspection", "unavailable"])
def test_selected_values_preserve_native_rows_and_never_access_store(kind):
    rows, calculation = selected(kind)
    original = deepcopy((rows, calculation))
    class NoStore:
        def __getattr__(self, name):
            forbidden()
    result = publish(NoStore(), rows, calculation)
    assert result["delivery"] == {"kind": "values", "rows": rows["rows"]}
    assert result["calculation"] == calculation
    for key in rows.keys() - {"version", "calculation_id", "rows"}:
        assert result[key] == rows[key]
    assert (rows, calculation) == original
    result["delivery"]["rows"].clear()
    assert (rows, calculation) == original


def test_retained_held_out_rmsd_has_its_original_unit_and_denominator():
    rows, calculation = selected()
    result = publish(None, rows, calculation)
    values = {row["field"]: row for row in result["delivery"]["rows"][0]["values"]}
    assert values["evaluation_rmsd"]["value"]["value"] == 1.9999999999999996
    assert values["evaluation_rmsd"]["value"]["unit"] == "angstrom"
    assert values["evaluation_rmsd"]["population"]["denominator"] == 1
    assert values["evaluation_used_count"]["value"]["value"] == 1
    assert values["evaluation_used_count"]["value"]["unit"] == "pair"


@pytest.mark.parametrize("kind", ["comparison", "extraction", "inspection", "unavailable"])
@pytest.mark.parametrize("window", [None, {"offset_0based": 1, "limit": 2}, {"offset_0based": 100, "limit": 1}])
def test_artifact_retains_exact_selected_rows_and_replays(tmp_path, monkeypatch, kind, window):
    rows, calculation = selected(kind, "artifact", window)
    with Store(tmp_path / "store") as store:
        result = publish(store, rows, calculation)
        delivery = result["delivery"]
        assert set(delivery) == {"kind", "table_file", "row_count", "allowed_use"}
        assert delivery["allowed_use"] == "read_exact_selected_table"
        raw = canonical({"version": "protein_structure_projection_table_v1", "rows": rows["rows"]}).encode()
        assert store.get_artifact(delivery["table_file"]["artifact_ref"]) == raw
        assert not raw.endswith(b"\n")
        assert delivery["table_file"] == HELPERS.identity(raw, "protein_structure_projection_table_v1")
        assert delivery["row_count"] == rows["returned_count"]
        assert "rows" not in result and "rows" not in delivery
        assert store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 1
        monkeypatch.setattr(store, "artifact", forbidden)
        assert publish(store, rows, calculation) == result
        (tmp_path / "filled-projection.json").write_text(json.dumps(result, indent=2) + "\n")


@pytest.mark.parametrize("change", ["row_count", "float_count", "calculation", "missing_calculation",
                                    "component_format", "custody", "nonfinite", "unrequested_field"])
def test_invalid_relationships_rejected_before_artifact_write(tmp_path, monkeypatch, change):
    rows, calculation = selected(delivery="artifact")
    custody = HELPERS.synthetic_custody()
    if change == "row_count": rows["returned_count"] = 2
    elif change == "float_count": rows["returned_count"] = 1.0
    elif change == "calculation": calculation["calculation_id"] = "a_different_calculation"
    elif change == "missing_calculation": calculation = None
    elif change == "component_format": calculation["components_file"]["format"] = "pdb_3x_text"
    elif change == "custody": custody["result_operation_key"] = "different_action"
    elif change == "nonfinite": rows["rows"][0]["values"][0]["value"]["value"] = float("nan")
    else: rows["rows"][0]["values"].append(deepcopy(rows["rows"][0]["values"][0]))
    with Store(tmp_path / "store") as store:
        monkeypatch.setattr(store, "artifact", forbidden)
        with pytest.raises(ValueError):
            publish(store, rows, calculation, custody)
        assert store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0


@pytest.mark.parametrize("damage,code", [("missing", "retained_artifact_missing"),
    ("bytes", "input_digest_mismatch"), ("size", "input_digest_mismatch")])
def test_existing_artifact_damage_is_reported_without_repair(tmp_path, monkeypatch, damage, code):
    rows, calculation = selected(delivery="artifact")
    with Store(tmp_path / "store") as store:
        result = publish(store, rows, calculation)
        table = result["delivery"]["table_file"]
        path = retained_protein_structure_file(store, table)
        if damage == "missing": path.unlink()
        elif damage == "bytes": path.write_bytes(b"x" * table["byte_length"])
        else: store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (table["artifact_ref"],))
        monkeypatch.setattr(store, "artifact", forbidden)
        with pytest.raises(ValueError, match=code):
            publish(store, rows, calculation)
        if damage == "missing": assert not path.exists()
        elif damage == "bytes": assert path.read_bytes() == b"x" * table["byte_length"]


@pytest.mark.parametrize("delivery", ["values", "artifact"])
def test_actual_publication_enters_only_requested_typed_form_field(tmp_path, delivery):
    from gene_annotation_episode.communication import form_with_facts, validate_form
    from gene_annotation_episode.episode_contract_information import expand_fact_form
    from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources
    source = "execution_protein_structure_projections"
    declaration = {"type": "object", "properties": {"answer": {"$ref": "episode-fact:" + source}},
                   "required": ["answer"], "additionalProperties": False}
    schema = expand_fact_form(json.dumps(declaration), child_role="results",
        facts_by_role={"results": protein_structure_fact_sources()},
        permitted_child_roles=["results"])["expanded_schema"]
    rows, calculation = selected(delivery=delivery)
    with Store(tmp_path / "store") as store:
        result = publish(store, rows, calculation)
        payload = form_with_facts({}, schema, {source: [result]})
        assert validate_form(payload, schema) == {"answer": [result]}
        if delivery == "artifact":
            assert "rows" not in payload["answer"][0]["delivery"]
        else:
            assert [value["field"] for value in payload["answer"][0]["delivery"]["rows"][0]["values"]] == [
                "evaluation_rmsd", "evaluation_used_count"]
