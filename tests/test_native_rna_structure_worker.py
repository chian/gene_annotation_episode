from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import native_rna_structure_worker as worker
from gene_annotation_episode.rna_structure_native import parse_rna_native_record, populate_rna_feature_sheet
from gene_annotation_episode.rna_structure_calculations import calculate_rna_feature_components
from test_native_rna_structure_contracts import model, parameters, rna_input, software


@pytest.fixture
def fake_rna(monkeypatch):
    calls = []
    class MD:
        temperature = 37.0
        dangles = 2
        noLP = noGU = noGUclosure = logML = circ = gquad = 0
        special_hp = 1
        min_loop_size = 3
        max_bp_span = -1
        salt = 1.021
    def make_md():
        calls.append("md")
        return MD()
    value = SimpleNamespace(__version__="fixture-1", INF=10000000, md=make_md)
    value.params_load_RNA_Turner2004 = lambda: (calls.append("load"), 1)[1]
    value.params_load = lambda path: (calls.append("load-file"), 1)[1]
    def save(path):
        calls.append("save")
        Path(path).write_text("fixture parameters\n")
        return 1
    value.params_save = save
    value.returned = ("(((...)))", -4.5)
    def fold(sequence, md):
        calls.append(("fold_compound", sequence, md.temperature))
        def mfe():
            calls.append("mfe")
            return value.returned
        def evaluate(structure):
            calls.append(("eval", structure))
            return value.returned[1]
        return SimpleNamespace(mfe=mfe, eval_structure=evaluate)
    value.fold_compound = fold
    monkeypatch.setattr(worker.importlib, "import_module", lambda name: value)
    monkeypatch.setattr(worker, "_check_software", lambda *args, **kwargs: None)
    return value, calls


def test_prediction_preserves_native_return_and_model(fake_rna, tmp_path, capsys):
    _, calls = fake_rna
    selected = model()
    value = worker.predict_rna_secondary_structure(rna_input(prediction=True), model=selected,
        parameter_input=None, output_directory=tmp_path)
    assert value["status"] == "complete" and value["native_mfe"]["value"] == -4.5
    assert value["native_mfe"]["numeric_text"] == "-4.5"
    assert value["native_evaluation"]["state"] == "not_requested"
    assert value["model"]["selected"] == selected
    assert calls[:3] == ["load", "md", "save"] and calls.count("mfe") == 1
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    raw = [row for row in lines if row["schema"] == "rna_raw_native_return_v1"]
    assert raw == [{"schema": "rna_raw_native_return_v1", "record_key": "original-record",
        "call": "fold_compound.mfe", "structure_value": "(((...)))", "energy_repr": "-4.5"}]


def test_evaluation_keeps_supplied_brackets_and_is_not_mfe(fake_rna, tmp_path):
    _, calls = fake_rna
    request = rna_input(energy=True)
    request["dot_bracket"] = "[{(...) }]".replace(" ", "")
    request["sequence"] = "GGGAAACCC"
    value = worker.analyze_rna_secondary_structure_features(request, energy_model=model(), parameter_input=None, output_directory=tmp_path)
    assert value["structure"]["dot_bracket"] == "[{(...)}]"
    assert value["structure"]["energy_dot_bracket"] == "(((...)))"
    assert ("eval", "(((...)))") in calls and "mfe" not in calls
    assert value["native_mfe"]["state"] == "not_requested"
    assert value["native_evaluation"]["value"] == -4.5


def test_topology_without_sequence_never_imports_RNA(monkeypatch, tmp_path):
    monkeypatch.setattr(worker.importlib, "import_module", lambda name: pytest.fail("native import in topology-only mode"))
    request = rna_input()
    request["sequence"] = None
    value = worker.analyze_rna_secondary_structure_features(request, energy_model=None, parameter_input=None, output_directory=tmp_path)
    assert value["status"] == "complete" and len(value["topology"]["pairs"]) == 3
    assert value["native_evaluation"]["state"] == "not_requested" and value["model"] is None


def test_missing_dependency_preserves_three_pairs_and_qualified_energy(monkeypatch, tmp_path):
    def missing(name):
        raise ModuleNotFoundError("synthetic missing RNA")
    monkeypatch.setattr(worker.importlib, "import_module", missing)
    request = rna_input(energy=True)
    value = worker.analyze_rna_secondary_structure_features(request, energy_model=model(), parameter_input=None, output_directory=tmp_path)
    assert value["status"] == "partial" and len(value["topology"]["pairs"]) == 3
    assert value["native_evaluation"]["reason"] == "rna_native_dependency_missing"
    native = parse_rna_native_record(json.dumps(value).encode(), format="rna_native_record_json_v1", expected_mode="supplied_features", record_key=request["record_key"])
    sheet = populate_rna_feature_sheet(native, record_key=request["record_key"], original_input=request, model_metadata=None, subject_binding=None)
    components = calculate_rna_feature_components(sheet, parameters=parameters())
    cells = {row["name"]: row for row in components["summary"]}
    assert cells["pair_count"]["value"] == 3 and cells["paired_fraction"]["value"] == 6 / 9
    assert cells["evaluated_energy_kcal_mol"]["reason"] == "rna_native_dependency_missing"


@pytest.mark.parametrize("energy,code", [(float("nan"), "rna_nonfinite_energy"), (float("inf"), "rna_nonfinite_energy"),
    (float("-inf"), "rna_nonfinite_energy"), (100000.0, "rna_native_failed")])
def test_native_rejected_return_is_lossless_diagnostic_not_energy(fake_rna, tmp_path, capsys, energy, code):
    fake_rna[0].returned = ("(((...)))", energy)
    value = worker.analyze_rna_secondary_structure_features(rna_input(energy=True), energy_model=model(), parameter_input=None, output_directory=tmp_path)
    assert value["status"] == "partial" and value["native_evaluation"]["value"] is None
    assert value["native_evaluation"]["reason"] == code
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    raw = next(row for row in rows if row["schema"] == "rna_raw_native_return_v1")
    assert raw["energy_repr"] == repr(energy) and raw["structure_value"] is None


@pytest.mark.parametrize("energy", [0.0, -0.0, 2.25, -4.5])
def test_native_finite_signed_values_are_not_clamped(fake_rna, tmp_path, energy):
    fake_rna[0].returned = ("(((...)))", energy)
    value = worker.analyze_rna_secondary_structure_features(rna_input(energy=True), energy_model=model(), parameter_input=None, output_directory=tmp_path)
    assert value["native_evaluation"]["value"] == energy and value["native_evaluation"]["numeric_text"] == repr(energy)


@pytest.mark.parametrize("change,code", [(lambda x: x.update(sequence="NNNAAANNN"), "rna_invalid_sequence_symbol"),
    (lambda x: x.update(sequence=""), "rna_empty_sequence"),
    (lambda x: x.update(sequence="GGG"), "rna_sequence_structure_length_mismatch"),
    (lambda x: x.update(dot_bracket="([)]....."), "rna_crossing_pairs_unsupported"),
    (lambda x: x.update(sequence=None), "no_sequence_supplied")])
def test_invalid_scientific_input_never_calls_energy(fake_rna, tmp_path, change, code):
    request = rna_input(energy=True)
    change(request)
    value = worker.analyze_rna_secondary_structure_features(request, energy_model=model(), parameter_input=None, output_directory=tmp_path)
    assert not fake_rna[1]
    assert value["native_evaluation"]["reason"] == code
    assert value["input"] == request


def test_parameter_load_failure_has_no_fallback(fake_rna, tmp_path):
    native, calls = fake_rna
    native.params_load = lambda path: 0
    selected = model()
    selected["parameters"] = {"kind": "supplied_parameter_file", "operand_role": "model_parameter_input"}
    value = worker.analyze_rna_secondary_structure_features(rna_input(energy=True), energy_model=selected,
        parameter_input=tmp_path / "missing.par", output_directory=tmp_path)
    assert value["native_evaluation"]["reason"] == "rna_parameter_load_failed"
    assert not calls and value["model"] is None


@pytest.mark.parametrize("field", ["python_executable", "python_sha256", "worker_source_sha256", "python_version",
    "viennarna_distribution_version", "rna_module_sha256", "rna_extension_sha256"])
def test_bound_software_fields_compare_actual_observations(monkeypatch, field):
    selected = software()
    selected.update(viennarna_distribution_version="fixture", rna_module_sha256="1" * 64, rna_extension_sha256="2" * 64)
    actual = deepcopy(selected)
    actual[field] = "different"
    monkeypatch.setattr(worker, "_software", lambda rna=None: actual)
    with pytest.raises(worker._NativeFailure) as caught:
        worker._check_software(selected, rna=SimpleNamespace(__version__="fixture"), native=True)
    assert caught.value.code == "rna_software_identity_mismatch" and caught.value.field == "/software/" + field


def test_missing_native_setting_is_explicit_not_ignored(fake_rna, tmp_path):
    fake_rna[0].md = lambda: SimpleNamespace()
    value = worker.predict_rna_secondary_structure(rna_input(prediction=True), model=model(), parameter_input=None, output_directory=tmp_path)
    assert value["native_mfe"]["reason"] == "rna_native_api_unsupported"
    assert "mfe" not in fake_rna[1]


def test_thrown_native_call_has_no_fabricated_return(fake_rna, tmp_path, capsys):
    def throws(*args):
        raise RuntimeError("complete synthetic native exception")
    fake_rna[0].fold_compound = throws
    value = worker.analyze_rna_secondary_structure_features(rna_input(energy=True), energy_model=model(), parameter_input=None, output_directory=tmp_path)
    output = capsys.readouterr()
    assert "rna_raw_native_return_v1" not in output.out
    assert "complete synthetic native exception" in output.err
    assert value["native_evaluation"]["reason"] == "rna_native_failed"
