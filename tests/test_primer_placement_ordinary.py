"""Retained234 projection and current metadata admission; no scientific rerun.

Lexical DTO identities and the explicitly unusable deployment below are shape
controls. No native handle, producing Source or old scientific custody is made.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import molecular_sequence_native as native
from gene_annotation_episode import molecular_sequence_driver as driver
from gene_annotation_episode import molecular_sequence_ordinary as ordinary
from gene_annotation_episode import molecular_sequence_result_contracts as shared
from gene_annotation_episode import molecular_sequence_tools as host
from gene_annotation_episode import primer_placement_measurements as science
from gene_annotation_episode import primer_placement_result_contracts as contracts
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.molecular_sequence_execution_contracts import SOFTWARE_VERSION
from gene_annotation_episode.molecular_sequence_results import MolecularSequenceResults
from gene_annotation_episode.runtime import ActionFailure, Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_molecular_provider_acquisition_host import _controller, _credit
from test_runtime import ScriptedProvider


SOURCE = "source_" + "b" * 24
FIXTURE = Path(__file__).parent / "fixtures/primer_placement234"
PINS = {"sheet.json": ("436ba7e78ac0821f8e7ed8d939c3e392880ce39a33ef73a23465cd3da3881f1f", 11127),
    "components.json": ("b51bbaae7a80f9238a7735b777031f34413f28dc3dd92a54852da1c56e473442", 18516)}


def _forbidden(*args, **kwargs):
    raise AssertionError("placement boundary attempted scientific/native/network work")


@pytest.fixture(autouse=True)
def no_scientific_work(monkeypatch):
    monkeypatch.setattr(science, "build_primer_placement_sheet", _forbidden)
    monkeypatch.setattr(science, "calculate_primer_placement_components", _forbidden)
    monkeypatch.setattr(native, "execute_molecular_sequence_request", _forbidden)
    for name in ("build_primer_placement_sheet", "calculate_primer_placement_components", "execute_molecular_sequence_request"):
        monkeypatch.setattr(driver, name, _forbidden)
    monkeypatch.setattr(science, "_populate", _forbidden)
    monkeypatch.setattr(science, "count_literal_alignment_columns", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.acquisition.PublicClients._http", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", _forbidden)


def _rows():
    return [dict(row_id={"kind": "summary"}, fields=["retained_native_hit_occurrence_count", "mismatch_count_sum", "mismatch_count_denominator_hits"]),
        dict(row_id={"kind": "placement_group", "group_ordinal": 0}, fields=["candidate_windows_per_orientation", "candidate_oriented_windows"]),
        dict(row_id={"kind": "placement_hit", "group_ordinal": 0, "native_hit_ordinal": 1}, fields=["target_interval", "mismatch_fraction.value"]),
        dict(row_id={"kind": "placement_mismatch", "group_ordinal": 0, "native_hit_ordinal": 1, "native_mismatch_ordinal": 0},
            fields=["oriented_primer_position", "original_primer_position", "target_position"])]


def _retained(rows=None):
    values, files = {}, {role: shared.empty_file_state("not_requested") for role in shared.FILE_ROLES}
    for role in ("sheet", "components"):
        raw = (FIXTURE / (role + ".json")).read_bytes()
        sha, size = PINS[role + ".json"]
        assert hashlib.sha256(raw).hexdigest() == sha and len(raw) == size
        values[role] = json.loads(raw)
        file = dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=size, format="json")
        files[role] = dict(state="retained_undeclared", file=file, declared=None,
            observed_identity=dict(sha256=sha, size_bytes=size), failure=None)
    raw = (FIXTURE / "provenance.json").read_bytes()
    assert len(raw) == 1184 and hashlib.sha256(raw).hexdigest() == "26e07e23ec7abe5a826b498ce948eb0633e87eebb70ec4a5dfa10974cd32163a"
    provenance = json.loads(raw)
    assert provenance["original_report_sha256"] == "b5b2984cbc3908a65fb3d06780d5bade9aea3099cad82b382459319849b84e16"
    assert provenance["actual_selected_source_calls"] == 1
    assert provenance["original_attempt_identity_scope"].startswith("engineering driver assertions")
    selected = _rows() if rows is None else rows
    selector = shared.validate_molecular_sequence_result_selector(dict(version=contracts.profile()["selector_version"],
        mode="original_attempt", operation=contracts.TOOL, saved_sheet_ref=None, rows=selected, return_files=[]))
    projection = shared.select_stored_molecular_sequence_values(operation=contracts.TOOL,
        sheet=values["sheet"], components=values["components"], selection=selector, source_files=files)
    custody = dict(intent=dict(arguments=dict(rows=selected)), projection=projection, source_files=files,
        failures=projection["public"]["failures"], context=contracts.context(
            sheet=values["sheet"], components=values["components"], source_files=files))
    return values, custody, contracts.packet(custody)


def _single(reference, sequence):
    raw = sequence.encode("ascii"); sha = hashlib.sha256(raw).hexdigest()
    return dict(version=contracts.profile()["operand_version"], subject=dict(id=reference, record_type="input"),
        sequence=sequence, parent_mapping=None, mapping_failure=dict(code="subregion_mapping_unavailable"),
        input_file=dict(artifact_ref="artifact_" + sha, sha256=sha, size_bytes=len(raw), format="ascii_sequence"),
        associations=dict(engineering_metadata=True), footprint=[])


def _operands(refs):
    args = dict(mode="run_native", target_ref="literal-target", primer_refs=deepcopy(refs), rows=[])
    original = {}
    records = []
    for ref in refs if type(refs) is list else [refs]:
        if ref not in original:
            original[ref] = _single(ref, "aAaA" if len(original) % 2 == 0 else "CcCc")
        records.append(deepcopy(original[ref]))
    return args, dict(version=contracts.OPERANDS_VERSION, target=_single(args["target_ref"], "aaaAccccAAAA"),
        primers=records if type(refs) is list else records[0])


def test_retained234_projection_uses_exact_saved_values_without_source_or_calculator_calls():
    values, custody, packet = _retained()
    assert [row["value"] for row in packet["values"]["rows"]] == [4, 2, 4, 9, 18, [1, 5], .25, 3, 3, 4]
    assert packet["context"]["input"] == {key: values["sheet"]["inputs"][key] for key in contracts._INPUT_KEYS}
    assert packet["context"]["input"]["primers"] == "AAAA"
    assert packet["context"]["original_operand_files"] is None
    assert packet["context"]["input"]["target_mapping"] is None
    assert packet["context"]["population"]["mismatch_count_denominator_hits"] == 4
    assert len(packet["context"]["issues"]) == 10
    assert packet["values"]["original_attempt_association"] == "unavailable"
    assert contracts.validate_packet(packet) == packet
    assert shared.ordinary_molecular_sequence_packet(custody, operation=contracts.TOOL) == packet
    returned = dict(source_ref=SOURCE, **packet)
    assert shared.validate_ordinary_molecular_sequence_return(returned, operation=contracts.TOOL) == returned


def test_empty_selection_keeps_original_operands_populations_definitions_and_missing_mappings():
    values, _custody, packet = _retained([])
    assert packet["values"]["rows"] == []
    assert packet["context"]["population"] == values["components"]["summary"]
    assert packet["context"]["definitions"] == values["components"]["definitions"]
    assert packet["context"]["input"]["primer_refs"] is None
    assert packet["context"]["input"]["primer_mappings"] is None
    assert host._n_context_partial(contracts.TOOL, packet) is True


def test_unavailable_output_keeps_actual_frozen_operands_without_inventing_zero_populations():
    args, operand = _operands(["primer-one", "primer-one"])
    files = {role: shared.empty_file_state("producer_unavailable") for role in shared.FILE_ROLES}
    frozen = dict(target_sequence=contracts.native_arguments(args, operand)["long_seq"],
        primers=contracts.native_arguments(args, operand)["short_seqs"], **contracts.scientific_context(args, operand))
    context = contracts.context(sheet=None, components=None, source_files=files,
        original_files=contracts.operand_files(operand), frozen_input=frozen)
    assert context["input"]["target_sequence"] == "aaaAccccAAAA"
    assert context["input"]["primer_refs"] == ["primer-one", "primer-one"]
    assert context["population"] is context["group_populations"] is context["definitions"] is None
    assert context["native_outcome"] is context["component_status"] is None
    projection = shared.select_stored_molecular_sequence_values(operation=contracts.TOOL, sheet=None, components=None,
        selection=contracts.selector(dict(rows=_rows())), source_files=files)
    value = contracts.packet(dict(intent=dict(arguments=dict(rows=_rows())), projection=projection,
        source_files=files, failures=projection["public"]["failures"], context=context))
    assert all(row["value"] is None and row["value_state"] == "source_unavailable" for row in value["values"]["rows"])
    assert contracts.validate_packet(value) == value


def test_retained_sheet_operands_must_equal_the_original_frozen_selected_input():
    values, custody, _packet = _retained([])
    original = deepcopy(custody["context"]["input"])
    changed = deepcopy(values["sheet"])
    changed["inputs"]["target_sequence"] = "different input with otherwise unchanged File metadata"
    with pytest.raises(ValueError, match="sheet_operand_conflict"):
        contracts.context(sheet=changed, components=values["components"], source_files=custody["source_files"], frozen_input=original)


@pytest.mark.parametrize("saved", [False, True])
def test_pure_source_payload_excludes_every_original_operand_file_even_on_role_collision(saved):
    """Exercise the pure payload builder, not publication/producer authority."""
    args, operand = _operands(["primer-one", "primer-two", "primer-one"])
    files = contracts.operand_files(operand)
    refs = {row["input_file"]["artifact_ref"] for row in contracts.operand_records(operand)}
    retained = dict(artifact_ref="artifact_" + "e" * 64)
    custody = dict(version=contracts.profile()["saved_custody_version" if saved else "custody_version"],
        intent=dict(tool_name=contracts.TOOL), public_packet_file=dict(artifact_ref="artifact_" + "d" * 64), retrieved_at="fixture",
        source_files=dict(components=dict(file=files["primers"][0]), sheet=dict(file=files["target"])),
        request=dict(input_binding_file=retained, source_admission_file=retained),
        original={}, context=dict(original_operand_files=files), original_source=dict(source_ref=SOURCE),
        calculation={key: retained for key in ("started_file", "result_file", "diagnostic_file")})
    owner = SimpleNamespace(_ordinary_value=lambda file: dict(frozen_operand=operand), _ordinary_failed_capture_refs=lambda states: [])
    record = MolecularSequenceResults._ordinary_molecular_sequence_source_record(owner, custody, retained)
    assert refs.isdisjoint(record["auxiliary_artifact_refs"])
    assert retained["artifact_ref"] in record["auxiliary_artifact_refs"]


def test_all_exported_schemas_conform_and_only_top_source_is_semantic():
    for kind in ("Arguments", "Context", "Packet", "Return"):
        Draft202012Validator.check_schema(contracts.schema(kind))
    fact = contracts.fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    Draft202012Validator.check_schema(fact)
    assert shared.ordinary_molecular_sequence_fact_sources(contracts.TOOL) == contracts.fact_sources()
    refs = []
    def walk(value, path=()):
        if type(value) is dict:
            if "x-reference-namespace" in value or value.get("format") == "reference": refs.append(path)
            for key, child in value.items(): walk(child, (*path, key))
        elif type(value) is list:
            for index, child in enumerate(value): walk(child, (*path, index))
    walk(contracts.schema())
    assert refs == [("properties", "source_ref")]


@pytest.mark.parametrize("change", [
    lambda packet: packet["context"]["population"].update(mismatch_count_sum=True),
    lambda packet: packet["context"]["population"].update(retained_native_hit_occurrence_count=999),
    lambda packet: packet["values"]["rows"][0].update(value=True),
    lambda packet: packet["values"]["rows"][0].update(unit="probability"),
    lambda packet: packet["context"].update(source_assumptions="PCR confidence"),
    lambda packet: packet["context"].update(worker_request={}),
])
def test_public_contract_rejects_changed_population_types_cells_meanings_and_controls(change):
    _values, _custody, packet = _retained()
    change(packet)
    with pytest.raises(ValueError): contracts.validate_packet(packet)


@pytest.mark.parametrize("refs", ["primer-one", ["primer-one", "primer-two", "primer-one"], []])
def test_exact_scalar_list_occurrences_case_and_empty_list_reach_native_request_without_normalization(refs):
    args, operand = _operands(refs)
    before = deepcopy((args, operand))
    assert contracts.validate_arguments(args) == args
    assert ordinary._arguments(args, operation=contracts.TOOL) == args
    actual = ordinary._native_arguments(contracts.TOOL, args, operand)
    assert actual["long_seq"] == "aaaAccccAAAA"
    assert actual["short_seqs"] == ([row["sequence"] for row in operand["primers"]] if type(refs) is list else "aAaA")
    context = ordinary._scientific_context(contracts.TOOL, args, operand)
    assert context["primer_refs"] == (refs if type(refs) is list else [refs])
    assert context["primer_mappings"] == [None] * (len(refs) if type(refs) is list else 1)
    assert (args, operand) == before
    assert shared.ordinary_molecular_sequence_intent_version(contracts.TOOL, args) == contracts.profile()["intent_version"]


@pytest.mark.parametrize("change", [
    lambda args, operand: args.update(primer_refs=True),
    lambda args, operand: args.update(short_seqs="unselected"),
    lambda args, operand: args.update(mode="native"),
    lambda args, operand: args["rows"].append(dict(row_id=dict(kind="placement_group", group_ordinal=True), fields=["reported_hit_count"])),
    lambda args, operand: operand["primers"].reverse(),
    lambda args, operand: operand["primers"][0].update(sequence="AAAA"),
    lambda args, operand: operand["primers"].pop(),
])
def test_closed_arguments_and_ordered_operand_identity_cannot_be_substituted(change):
    args, operand = _operands(["primer-one", "primer-two"])
    change(args, operand)
    with pytest.raises((ValueError, TypeError)):
        contracts.validate_arguments(args)
        contracts.validate_operands(operand, args)


def _metadata_configuration(tmp_path):
    """Deliberately unusable deployment; admission must precede any execution."""
    root = tmp_path / "engineering-deployment"; root.mkdir()
    pin = dict(path=str(root / "not-an-interpreter"), sha256="0" * 64, size_bytes=0)
    manifest = dict(path=str(root / "unavailable-manifest.json"), sha256="1" * 64, size_bytes=0)
    software = dict(version=SOFTWARE_VERSION, python=pin, python_home=str(root),
        python_version="engineered metadata only; never selected for execution", import_roots=[str(root)],
        software_files_file=manifest, software_files_ref="artifact_" + manifest["sha256"])
    deployment = dict(version=native.DEPLOYMENT_VERSION, runtime=dict(executable=pin, home=str(root)),
        module=dict(path=str(root / "unavailable-source.py"), sha256=native.SOURCE_SHA256, size_bytes=91223),
        import_roots=[str(root)], software_files_file=manifest, software_files_ref=software["software_files_ref"])
    workspace = tmp_path / "workspace"; workspace.mkdir()
    resources = {"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY),
        native_molecular_sequence=[dict(version=host.BINDING_VERSION, operation=contracts.TOOL, deployment=deployment, software=software)])}
    environments = [dict(operation=contracts.TOOL, resource_id="ordinary", binding_ordinal_0based=0,
        environment=deepcopy(ordinary.ENVIRONMENT_SELECTION))]
    return resources, environments


def _current(tmp_path, store, *, known, native_configured=True):
    if native_configured:
        resources, environments = _metadata_configuration(tmp_path)
    else:
        workspace = tmp_path / "workspace"; workspace.mkdir()
        resources, environments = {"ordinary": dict(kind="local", workspace=str(workspace), policy=deepcopy(ordinary.POLICY))}, []
    factory = ExecutionServiceFactory(resources, {}, 2, .25, .5,
        molecular_sequence_environments=tuple(environments), molecular_sequence_saved_modes=True)
    registry = ToolRegistry(store, job_limits=deepcopy(ordinary.POLICY))
    application = factory(store, run_id="placement-metadata-control", directory=tmp_path / "run", tool_registry=registry)
    flow = Workflow(store, registry, ScriptedProvider([]), tmp_path / "run", "placement-metadata-control", _controller, _credit,
        project_child_credit=_credit, root_role="improvement", episode_binding_descriptors=application.episode_binding_descriptors,
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider,
        episode_record_receipts=True, initial_known_record_refs=known)
    root = flow.build("improvement", "caller", "Inspect only the selected placement operands or admitted retained result.", store.validate_scope())
    return flow, registry, root, factory


def test_real_current_unreceived_primer_denies_before_any_operand_body_or_native_dispatch(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="AAAACCCCAAAA", molecule="dna")["subject_refs"]
        # A caller-declared extracted primer is in this target's scope, but a
        # root's original target receipt does not grant every related product.
        primer = store.put("product", dict(parent_refs=[target], molecule="dna",
            sequence_ref=store.artifact("AAAA", "text/plain"), derivation="extraction", context_refs=[],
            footprint=[dict(target_ref=target, start=0, end=4, unit="nt")]), origin="caller")["id"]
        _flow, registry, root, factory = _current(tmp_path, store, known=[target])
        assert ExecutionServiceFactory.from_record(factory.as_record()).as_record() == factory.as_record()
        assert contracts.TOOL in registry.catalog(root.source.scope)
        known = set(_flow.receipts.known(root.source.episode_id))
        assert target in known and primer not in known
        assert store.reference_subset([primer], plain(root.source.scope)) == [primer]
        monkeypatch.setattr(Store, "get_artifact", _forbidden)
        monkeypatch.setattr(registry, "_prepare_molecular_sequence_operand", _forbidden)
        with pytest.raises(ActionFailure):
            asyncio.run(root.source.execute(dict(kind="tool", tool=contracts.TOOL, arguments=dict(
                mode="run_native", target_ref=target, primer_refs=[primer], rows=[])), 0))
        result = json.loads(store.db.execute("SELECT result FROM tool_operations WHERE name=?", (contracts.TOOL,)).fetchone()[0])
        assert result["status"] == "invalid" and result["record_refs"] == [] and result["result"] is None
        assert "subject_not_received" in result["feedback"]["code"]
        assert not list(store.path.rglob("native.json"))


@pytest.mark.parametrize("mode", ["read_stored", "calculate_saved"])
def test_received_caller_source_cannot_masquerade_as_a_placement_producer_before_private_bytes(tmp_path, monkeypatch, mode):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="AAAA", molecule="dna")
        supplied = store.register_material(data=b"not a placement publication", use="evidence", name="caller evidence")
        source = supplied["source_ref"]
        _flow, registry, root, _factory = _current(tmp_path, store, known=[source], native_configured=False)
        monkeypatch.setattr(Store, "get_artifact", _forbidden)
        with pytest.raises(ActionFailure):
            asyncio.run(root.source.execute(dict(kind="tool", tool=contracts.TOOL,
                arguments=dict(mode=mode, result_ref=source, rows=[])), 0))
        result = json.loads(store.db.execute("SELECT result FROM tool_operations WHERE name=?", (contracts.TOOL,)).fetchone()[0])
        assert result["status"] == "invalid" and result["record_refs"] == [] and result["result"] is None
        assert not list(store.path.rglob("ordinary-calculation-started.json"))


def _inspection_rows():
    return [dict(row_id=dict(kind="placement_group", group_ordinal=0),
            fields=["native_group", "primer_occurrence_ordinal", "native_group_ordinal", "native_sequence_matches_occurrence"]),
        dict(row_id=dict(kind="placement_hit", group_ordinal=0, native_hit_ordinal=1),
            fields=["native_hit", "oriented_source_primer", "target_window", "target_mapping", "primer_mapping"]),
        dict(row_id=dict(kind="placement_mismatch", group_ordinal=0, native_hit_ordinal=1, native_mismatch_ordinal=0),
            fields=["native_triple", "target_source_intervals", "primer_source_intervals"])]


def _inspection(components=None, *, rows=None):
    """Pure supplied-document controls; edited documents establish no custody."""
    rows = _inspection_rows() if rows is None else rows
    values, custody, packet = _retained(rows)
    if components is None:
        return values["components"], packet
    projection = shared.select_stored_molecular_sequence_values(operation=contracts.TOOL,
        sheet=values["sheet"], components=components, selection=contracts.selector(dict(rows=rows)),
        source_files=custody["source_files"])
    context = contracts.context(sheet=values["sheet"], components=components, source_files=custody["source_files"])
    return components, contracts.packet(dict(intent=dict(arguments=dict(rows=rows)), projection=projection,
        source_files=custody["source_files"], failures=projection["public"]["failures"], context=context))


def test_native_inspection_copies_retained234_original_groups_hits_triples_and_checked_mappings():
    before = {name: (FIXTURE / name).read_bytes() for name in PINS}
    components, packet = _inspection()
    group, hit = components["groups"][0], components["groups"][0]["hits"][1]
    expected = [group[name] for name in ("native_group", "primer_occurrence_ordinal", "native_group_ordinal", "native_sequence_matches_occurrence")]
    expected += [hit[name] for name in ("native_hit", "oriented_source_primer", "target_window", "target_mapping", "primer_mapping")]
    expected += [hit["mismatches"][0][name] for name in ("native_triple", "target_source_intervals", "primer_source_intervals")]
    assert [cell["value"] for cell in packet["values"]["rows"]] == expected
    assert hit["mismatches"][0]["native_triple"] == [3, "A", "C"]
    assert packet["values"]["schema"] == shared.PLACEMENT_PUBLIC_VERSION
    assert contracts.selector(dict(rows=_inspection_rows()))["version"] == shared.PLACEMENT_SELECTOR_VERSION
    assert contracts.validate_packet(packet) == packet
    assert {name: (FIXTURE / name).read_bytes() for name in PINS} == before


def test_literal_native_conflict_is_not_replaced_by_checked_values_or_another_alignment():
    components, _packet = _inspection()
    changed = deepcopy(components)
    hit = changed["groups"][0]["hits"][1]
    hit["native_hit"] = {"position": -91, "strand": "native-unknown", "mismatches": [[3, "native-A", "native-C"]], "extra": {"missing": None}}
    hit["mismatches"][0]["native_triple"] = ["malformed", {"symbols": "literal"}, False]
    _components, packet = _inspection(changed)
    assert packet["values"]["rows"][4]["value"] == hit["native_hit"]
    assert packet["values"]["rows"][9]["value"] == hit["mismatches"][0]["native_triple"]
    assert hit["mismatch_count"] == components["groups"][0]["hits"][1]["mismatch_count"] == 1
    assert hit["target_interval"] == [1, 5]
    assert contracts.validate_packet(packet) == packet


@pytest.mark.parametrize("state", ["null", "empty_array", "empty_object", "missing", "non_json"])
def test_native_literal_null_empty_missing_and_invalid_type_are_distinct_without_sheet_fallback(state):
    components, _packet = _inspection()
    changed = deepcopy(components)
    if state == "missing": changed["groups"][0].pop("native_group")
    else: changed["groups"][0]["native_group"] = {"null": None, "empty_array": [], "empty_object": {}, "non_json": ("tuple",)}[state]
    _components, packet = _inspection(changed, rows=[_inspection_rows()[0]])
    cell = packet["values"]["rows"][0]
    assert cell["value_state"] == {"null": "stored_null", "empty_array": "stored_value", "empty_object": "stored_value", "missing": "path_missing", "non_json": "invalid_type"}[state]
    assert cell["value"] == ([] if state == "empty_array" else {} if state == "empty_object" else None)
    assert contracts.validate_packet(packet) == packet


@pytest.mark.parametrize("native_ordinal", [0, None])
def test_native_null_group_and_missing_native_slot_keep_their_separate_ordinal_context(native_ordinal):
    components, _packet = _inspection()
    changed = deepcopy(components)
    changed["groups"][0].update(native_group=None, native_group_ordinal=native_ordinal)
    _components, packet = _inspection(changed, rows=[_inspection_rows()[0]])
    assert packet["values"]["rows"][0]["value_state"] == "stored_null"
    assert packet["values"]["rows"][0]["value"] is None
    assert packet["context"]["group_populations"][0]["native_group_ordinal"] == native_ordinal
    assert contracts.validate_packet(packet) == packet


@pytest.mark.parametrize("mapping", [dict(state="available", intervals=[]), dict(state="unavailable", intervals=None),
    dict(state="incompatible", intervals=None), dict(state="available", intervals=[dict(subject_ref="literal-source", start=2, end=5, unit="symbol", strand="-")])])
def test_checked_mapping_copies_original_state_and_ordered_nt_or_symbol_intervals(mapping):
    components, _packet = _inspection()
    changed = deepcopy(components)
    changed["groups"][0]["hits"][1]["target_mapping"] = mapping
    _components, packet = _inspection(changed)
    cell = packet["values"]["rows"][7]
    assert cell["value_state"] == "stored_value" and cell["value"] == mapping
    assert cell["unit"] == "per_segment_nt_or_symbol"
    assert contracts.validate_packet(packet) == packet


@pytest.mark.parametrize("mapping", [dict(state="available", intervals=None), dict(state="unavailable", intervals=[]),
    dict(state="incompatible", intervals=[]), dict(state="unrecorded", intervals=None),
    dict(state="available", intervals=[dict(subject_ref="literal-source", start=3, end=2, unit="nt", strand="+")]),
    dict(state="available", intervals=[dict(subject_ref="literal-source", start=0, end=2, unit="aa", strand="+")]),
    dict(state="available", intervals=[dict(subject_ref="literal-source", start=False, end=2, unit="nt", strand="+")])])
def test_checked_mapping_contradictions_are_invalid_types_not_repaired_or_recalculated(mapping):
    assert shared.valid_type(mapping, "placement_mapping") is False
    components, _packet = _inspection()
    changed = deepcopy(components);changed["groups"][0]["hits"][1]["target_mapping"] = mapping
    _components, packet = _inspection(changed)
    assert packet["values"]["rows"][7]["value_state"] == "invalid_type"
    assert packet["values"]["rows"][7]["value"] is None


def test_new_profile_is_align_only_and_legacy_fields_and_versions_remain_literal():
    values, custody, _packet = _retained()
    old_selector = dict(version=shared.SELECTOR_VERSION, mode="original_attempt", operation=contracts.TOOL,
        saved_sheet_ref=None, rows=_rows(), return_files=[])
    old = shared.select_stored_molecular_sequence_values(operation=contracts.TOOL, sheet=values["sheet"],
        components=values["components"], selection=old_selector, source_files=custody["source_files"])
    assert old["schema"] == shared.PROJECTION_VERSION and old["public"]["schema"] == shared.PUBLIC_VERSION
    assert [row["value"] for row in old["public"]["rows"]] == [4, 2, 4, 9, 18, [1, 5], .25, 3, 3, 4]
    for identity in (dict(kind="summary"), *[row["row_id"] for row in _inspection_rows()]):
        prior = shared.field_table(contracts.TOOL, identity)
        current = shared.field_table(contracts.TOOL, identity, profile=shared._PLACEMENT_PROFILE)
        assert {name: current[name] for name in prior} == prior
        assert "native_group" not in prior and "native_hit" not in prior and "native_triple" not in prior
    with pytest.raises(ValueError):
        shared.validate_molecular_sequence_result_selector(dict(old_selector, rows=[_inspection_rows()[0]]))
    with pytest.raises(ValueError):
        shared.validate_molecular_sequence_result_selector(dict(old_selector, version=shared.PLACEMENT_SELECTOR_VERSION, operation="annotate_open_reading_frames"))
    for profile in (shared._LEGACY_PROFILE, shared._N_PROFILE, shared._O_PROFILE, shared._PROTEASE_PROFILE):
        assert "$defs" not in shared.molecular_sequence_fact_sources(profile=profile)[shared.PROJECTION_SOURCE]["report_schema"]
