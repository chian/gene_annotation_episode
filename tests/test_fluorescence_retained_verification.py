"""One retained-data calculation authenticates both original049 complete returns.

The recovered047 Sheet has the exact original049 content identity. Neither its
producer controls nor its software declarations become049 execution authority.
The original049 failures, withdrawn payloads and063 skips remain unchanged.
"""
from contextlib import ExitStack, closing
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import stat
from types import SimpleNamespace

import pytest


SHEET_SHA256 = "67d318098f0b8a3eb49295d126d419d5fc1bddb5219ff66055b22116de32e08a"
COMPONENTS_SHA256 = "8eb934f61579165b418c5753062ef1bea11dbb8a351448e4172f55274f33c6bb"
PARTIAL_SHEET_SHA256 = "0ad9648aee76c4070e4b8580c36c05cd5822512d96b9b9f62135bbef5adea00d"
SOURCE047 = ("verification/tool_graders_hmmer_map_verification_2026-10-28_529/"
    "check047_fluorescence_prepared_integration/temporary/pytest/"
    "test_existing_selected_produce0/worker/sheet.json")
PINNED_CASES = (
    ("perform_facs_cell_sorting", "HMMER_NATIVE_ORACLE_FLUORESCENCE_RETAINED_FACS_CASE", {
        "CASE.json": "6d2caf08ec8c54dc4bd240e8de46bc4bb62c780a3c6d9704277fac24b62fadd9",
        "WITHDRAWAL_AND_REPLAY_INPUTS.json": "9b754f118046669c94232c567a179b730b0498f2c6be9f007e3fc4713c7074a8",
        "fixture-configuration.json": "4a7d3c2a822530afa2e504b5df71d9db442fde3fbd840066afeac53e95e8d089",
        "original-native-plan.json": "7e28de75b544eb971b2b419adfc046c62885ffb4c919d5d2bfb2638e08a2408a",
        "decision-1.json": "121f9db7a83fd1c0ab78adf7a934f516c5a9d95127a862c1c5a593a3f31d61f0",
        "decision-6.json": "649ce713189842abc47cf753c578fd8877fb286dfd903a749d119b92bfa50bba",
        "decision-8.json": "93a416adba1eca2c327c07e26ee89604d49a63375022313d9e68e8146953370e",
        "state/state.sqlite3": "5bafec0ca9882b2c32ec9b1a8f645149d4c1e6c79fd73a1e111d3c81ba0200c1"}),
    ("analyze_cytokine_production_in_cd4_tcells", "HMMER_NATIVE_ORACLE_FLUORESCENCE_RETAINED_CYTOKINE_CASE", {
        "CASE.json": "d96128a98341a59a3aca5664623d733c822fb017b2ada3457b53ff67865e8d2d",
        "WITHDRAWAL_AND_REPLAY_INPUTS.json": "a3b7f3579f9b640af2e73165abbae4b9d6063aea1c2b868a58e512c5f59c95a1",
        "fixture-configuration.json": "90325f3c70bc3d09fe9b91f425839a63c4093607dbb256961a23f6113444a5ba",
        "original-native-plan.json": "2d92f0639142d942df8b8e0c0728343492d449a662d457c3b852e691a23cfab9",
        "decision-1.json": "919a85f806389106cd4460b613cdf75b7e4718b5a1ea859053a375552f100504",
        "decision-6.json": "461d4750562b469827cdfa8de99ab009fe5790f46639923c2c665351caa7e314",
        "decision-8.json": "759052a6acaf9a94c5666867fb5b14fda3b3893baab4ce60490c829e19d9cd54",
        "state/state.sqlite3": "dfb2ac37a23533f6ecdb3edceaf73029635e62229ebed65a6c318672b8f8f18b"}),
)


def _retained_fluorescence_pin(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink()
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(sha256=sha, size_bytes=path.stat().st_size, mode=stat.S_IMODE(path.stat().st_mode))


def _retained_fluorescence_inventory(directory):
    return {str(path.relative_to(directory)): _retained_fluorescence_pin(path)
        for path in sorted(directory.rglob("*")) if path.is_file() and not path.is_symlink()}


def _retained_fluorescence_copy(source, destination, pins):
    """Copy the entire DB family before its first owned immutable reader opens."""
    assert source.is_absolute() and source.is_dir() and not source.is_symlink()
    for relative, expected in pins.items():
        assert _retained_fluorescence_pin(source / relative)["sha256"] == expected
    database = source / "state/state.sqlite3"
    family = sorted(path for path in database.parent.iterdir() if path.name.startswith(database.name))
    assert {path.name for path in family} <= {"state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"}
    assert all(path.is_file() and not path.is_symlink() for path in family)
    assert all(path.stat().st_size == 0 for path in family if path.name.endswith("-wal"))
    selected = sorted({source / relative for relative in pins} | set(family)
        | set((source / "run/archive").glob("*.json")))
    before = {str(path.relative_to(source)): _retained_fluorescence_pin(path) for path in selected}
    for path in selected:
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    assert {relative: _retained_fluorescence_pin(destination / relative) for relative in before} == before
    return before


def _retained_fluorescence_case(stack, directory, operation, checks):
    """Use the existing genuine-row reader, without constructing an execution owner."""
    from method_loop.archive import ArchivedRecord
    from gene_annotation_episode.episode_return_records import EpisodeReturnRecords

    read = lambda name: json.loads((directory / name).read_bytes())
    saved = read("CASE.json")
    assert saved["operation"] == operation
    db = stack.enter_context(closing(sqlite3.connect((directory / "state/state.sqlite3").as_uri()
        + "?mode=ro&immutable=1", uri=True)))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    run_id = saved["archive"]["run_id"]
    reader = EpisodeReturnRecords(SimpleNamespace(db=db), run_id, failure_prefix="retained_fluorescence_")
    records = list(checks.walk(saved["archive"]))
    assert len(records) == 7
    for record in records:
        row = db.execute("SELECT path,request,state,archive FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (run_id, record["episode_id"])).fetchone()
        assert row is not None and row["state"] == "yielded"
        checks.assert_equal(json.loads(row["request"]), record["request"])
        checks.assert_equal(json.loads(row["path"]), record["path"])
        descriptor = json.loads(row["archive"])
        assert Path(descriptor["file"]).name == descriptor["file"]
        archived = ArchivedRecord(directory / "run/archive" / descriptor["file"],
            descriptor["sha256"], descriptor["index_sha256"])
        checks.assert_equal(archived.load(), record)
    return SimpleNamespace(directory=directory, operation=operation, saved=saved, db=db, run_id=run_id,
        reader=reader, records=records, configuration=read("fixture-configuration.json"),
        withdrawal=read("WITHDRAWAL_AND_REPLAY_INPUTS.json"), plan=read("original-native-plan.json"))


def _retained_fluorescence_deliveries(case, receipts, checks):
    """Authenticate actual Results→SCI→annotation forms and their frozen rows."""
    from gene_annotation_episode.communication import validate_form
    from gene_annotation_episode.fluorescence_return_views import (
        PROJECTION_SOURCE, CONTEXT_SOURCE, requested_fluorescence_sources, select_fluorescence_return_facts,
    )

    science_record, = [record for record in case.records if record["scope_level"] == "scientific_process"]
    science = case.reader.context(science_record["episode_id"])
    forms = []
    for index, receipt in enumerate(receipts, 1):
        child, form, schema = case.reader._attempt(science, index)
        assert child.episode_id == receipt["intent"]["episode_id"]
        assert requested_fluorescence_sources(schema) == set(checks.FIELDS.values())
        validate_form(form, schema, lambda reference, namespace: namespace in (None, "artifact")
            and case.db.execute("SELECT 1 FROM artifacts WHERE id=?", (reference,)).fetchone() is not None)
        checks.assert_equal(form, case.saved["returned"][index-1])
        checks.assert_equal(form, science_record["units"][index]["child_result"]["form"])
        assert form["completed"] is receipt["delivery_complete"]
        for field, source in checks.FIELDS.items():
            checks.assert_equal(form[field], receipt["facts"][source])
        forms.append(form)
    for filename, form in (("decision-6.json", forms[0]), ("decision-8.json", forms[1])):
        checks.assert_equal(json.loads((case.directory / filename).read_bytes())["context"]["child_reports"][-1], form)
    expected = {field: [form[field][0] for form in forms] for field in ("measurements", "contexts")}
    root = case.reader.context(case.saved["archive"]["episode_id"])
    child, form, schema = case.reader._attempt(root, 0)
    assert child.episode_id == science.episode_id
    assert requested_fluorescence_sources(schema) == {PROJECTION_SOURCE, CONTEXT_SOURCE}
    validate_form(form, schema, lambda *_: False)
    for actual in (form, case.saved["forwarded"], case.saved["archive"]["units"][0]["child_result"]["form"]):
        checks.assert_equal(actual, expected)
    facts = json.loads(case.db.execute("SELECT facts FROM runtime_forms WHERE run_id=? AND episode_id=?",
        (case.run_id, science.episode_id)).fetchone()[0])
    checks.assert_equal(select_fluorescence_return_facts(facts, schema=schema),
        {PROJECTION_SOURCE: expected["measurements"], CONTEXT_SOURCE: expected["contexts"]})
    return expected


def test_original049_complete_sheet_hash_and_both_typed_deliveries_with_one_shared_calculation(tmp_path, monkeypatch):
    if os.environ.get("HMMER_NATIVE_ORACLE_FLUORESCENCE_RETAINED_CALCULATOR") != "1":
        pytest.skip("requires explicitly pinned original049 metadata and the exact recovered047 Sheet")
    from fluorescence_flowio_test_support import require_bounded_runtime
    require_bounded_runtime()
    from gene_annotation_episode import fluorescence_event_contracts as core
    from gene_annotation_episode import fluorescence_event_calculations as calculations
    from gene_annotation_episode.fluorescence_event_sheet import validate_fluorescence_sheet
    from gene_annotation_episode.fluorescence_result_views import project_fluorescence_result
    from gene_annotation_episode.fluorescence_context_views import project_fluorescence_context
    import test_fluorescence_saved_prepared_case as checks

    def forbidden(*args, **kwargs):
        raise AssertionError("retained verification attempted a producer, parser, worker, network or second calculation")

    for name in ("subprocess.Popen", "os.system", "socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex"):
        monkeypatch.setattr(name, forbidden)
    for name in ("__init__", "get_artifact", "artifact", "put"):
        monkeypatch.setattr("gene_annotation_episode.state.Store." + name, forbidden)
    monkeypatch.setattr(checks, "calculate_fluorescence_sheet", forbidden)
    for module, names in (
        ("native_lifecycle", ("prepare_job", "start_prepared", "resume_start", "status", "wait_job", "collect", "cancel", "release")),
        ("fluorescence_result_worker", ("execute_fluorescence_worker", "calculate_fluorescence_sheet")),
        ("fluorescence_event_preparation", ("prepare_fcs_scaling", "prepare_spill_compensation")),
        ("fluorescence_event_readers", ("parse_fluorescence_csv", "parse_fluorescence_table_snapshot")),
        ("fluorescence_fcs_reader", ("parse_fluorescence_fcs", "decode_selected_fcs")),
        ("fluorescence_native_reports", ("parse_fluorescence_native_reports",)),
        ("native_fluorescence_driver", ("run_fluorescence_driver",)),
        ("native_fluorescence_results", ("capture_fluorescence_native_files", "prepare_fluorescence_result_worker")),
    ):
        for name in names:
            monkeypatch.setattr("gene_annotation_episode." + module + "." + name, forbidden)
    original_calculator = calculations.calculate_fluorescence_sheet
    calls = []
    def once(sheet, *, parameters):
        assert calls == []
        calls.append(deepcopy(parameters))
        return original_calculator(sheet, parameters=parameters)
    monkeypatch.setattr(calculations, "calculate_fluorescence_sheet", once)
    fixture = Path(__file__).parent / "fixtures/fluorescence/retained_complete_sheet.json"
    raw = fixture.read_bytes()
    assert len(raw) == 11208 and hashlib.sha256(raw).hexdigest() == SHEET_SHA256
    source047 = Path(os.environ["HMMER_NATIVE_ORACLE_FLUORESCENCE_SOURCE047_SHEET"])
    assert source047.is_absolute()
    source047_before = _retained_fluorescence_pin(source047)
    assert source047_before["sha256"] == SHEET_SHA256 and source047_before["size_bytes"] == len(raw)
    assert source047.read_bytes() == raw
    provenance = json.loads(fixture.with_name("retained_complete_sheet.provenance.json").read_bytes())
    assert provenance["original_content_source"]["path"] == SOURCE047
    assert provenance["original049_declared_file"] == dict(artifact_ref="artifact_" + SHEET_SHA256,
        sha256=SHEET_SHA256, size_bytes=len(raw), format=core.SHEET_SCHEMA)
    sheet = validate_fluorescence_sheet(json.loads(raw))
    assert core.canonical(sheet) + b"\n" == raw
    original_inputs, copied_inputs, originals = [], [], []
    proof = dict(version="fluorescence_original049_retained_verification_v1", passed=False, calculator_calls=0,
        original_workers_repeated=0, original_stores_modified=False, original_failures_and_skips_preserved=True,
        qualification="Exact047 Sheet content matches049 declarations;047 capture/producer custody is not relabelled as049.")
    try:
        with ExitStack() as stack:
            cases = []
            for index, (operation, environment, pins) in enumerate(PINNED_CASES):
                source = Path(os.environ[environment])
                before = _retained_fluorescence_inventory(source)
                original_inputs.append((source, before))
                destination = tmp_path / "retained" / str(index)
                copied = _retained_fluorescence_copy(source, destination, pins)
                copied_inputs.append((destination, copied))
                case = _retained_fluorescence_case(stack, destination, operation, checks)
                receipts = checks.original_receipts(case)
                original = receipts[0]
                checks.assert_original_rows(original)
                checks.assert_original_associations(case, original)
                assert original["delivery_complete"] and original["facts"][checks.FAILURE_SOURCE] == []
                assert original["qualified_files"]["sheet"] == provenance["original049_declared_file"]
                assert original["qualified_files"]["calculations"]["sha256"] == COMPONENTS_SHA256
                assert original["qualified_files"]["calculations"]["size_bytes"] == 20760
                assert case.withdrawal["saved_sheet_file"]["sha256"] == PARTIAL_SHEET_SHA256
                assert not any((destination / "state/artifacts" / file["sha256"][:2] / file["sha256"]).exists()
                    for receipt in receipts for role, file in receipt["qualified_files"].items()
                    if role in {"sheet", "calculations"} and file is not None)
                forms = _retained_fluorescence_deliveries(case, receipts, checks)
                cases.append((case, original, forms))
            parameters = cases[0][0].plan["requested_job"]["native_fluorescence"]["parameters"]
            assert all(case.plan["requested_job"]["native_fluorescence"]["parameters"] == parameters for case, _, _ in cases)
            components = calculations.calculate_fluorescence_sheet(sheet, parameters=parameters)
            proof["calculator_calls"] = len(calls)
            component_raw = core.canonical(components) + b"\n"
            assert len(component_raw) == 20760 and hashlib.sha256(component_raw).hexdigest() == COMPONENTS_SHA256
            core.validate_components(components, sheet=sheet)
            for case, original, forms in cases:
                selector = original["intent"]["assignment"]["selector"]
                view = project_fluorescence_result(sheet, components, selection=selector["selection"])
                context = project_fluorescence_context(sheet, components, selection=selector["selection"],
                    context_fields=selector["context_fields"])
                checks.assert_equal(view, original["projection"])
                checks.assert_equal(context, original["context"])
                assert all(cell in components["cells"] for cell in view["rows"])
                checks.assert_equal(forms["measurements"][0], view)
                originals.append(dict(operation=case.operation, original_projection=view,
                    original_context=context, both_parent_deliveries_exact=True))
            assert len(calls) == 1
            proof.update(passed=True, calculator_calls=1, sheet_sha256=SHEET_SHA256,
                components_sha256=COMPONENTS_SHA256, operations=originals,
                partial_and_saved_sheet_body="absent_not_recreated_or_recalculated",
                new_workflows_actions_observations_sources_grants=0)
    except BaseException as error:
        proof["failure"] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        proof["calculator_calls"] = len(calls)
        proof["source047_file_unchanged"] = _retained_fluorescence_pin(source047) == source047_before
        proof["original_input_inventories"] = [dict(source=str(source), before=before,
            after=_retained_fluorescence_inventory(source)) for source, before in original_inputs]
        proof["copied_metadata_inventories"] = [dict(directory=str(directory), before=before,
            after={relative: _retained_fluorescence_pin(directory / relative) for relative in before})
            for directory, before in copied_inputs]
        proof["original_inventories_unchanged"] = all(row["before"] == row["after"]
            for row in proof["original_input_inventories"])
        proof["copied_metadata_files_unchanged"] = all(row["before"] == row["after"]
            for row in proof["copied_metadata_inventories"])
        (tmp_path / "FLUORESCENCE_RETAINED_VERIFICATION.json").write_text(json.dumps(proof,sort_keys=True,indent=2) + "\n")
        assert proof["source047_file_unchanged"] and proof["original_inventories_unchanged"] and proof["copied_metadata_files_unchanged"]
